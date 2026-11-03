#!/usr/bin/env python3
"""Verify source-audit citations against committed Git objects, never runtime claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


class EvidenceError(ValueError):
    pass


# P001's original scope is a gate, not a caller-supplied list that can be
# shortened along with the evidence. Source semantics still require review.
REQUIRED_CATEGORIES = (
    "native_linux_host", "macho_runtime_component", "implemented_body_unqualified",
    "partial_framework", "developer_link_stub", "generated_stub_tooling",
    "generated_style_stub_body", "architecture_constraint",
)
REQUIRED_STAGES = {
    "host_launch": ((".", "src/startup/darling.c"),),
    "mldr_mapping_and_dyld_handoff": (
        (".", "src/startup/mldr/loader.c"), (".", "src/startup/mldr/mldr.c")),
    "dyld_dependency_loading": (
        ("src/external/dyld", "src/dyld2.cpp"),
        ("src/external/dyld", "src/ImageLoader.cpp")),
    "system_library_initialization": (("src/external/libsystem", "init.c"),),
    "server_checkin_and_rpc_dispatch": (
        ("src/external/darlingserver", "src/call.cpp"),
        ("src/external/darlingserver", "src/darlingserver.cpp")),
    "framework_initialization": (
        ("src/external/objc4", "runtime/objc-os.mm"),
        ("src/external/corefoundation", "CFRuntime.c")),
}

# Preserve the original P001 citations. These five records have separately
# reviewed P003 CMake integrations; no other source drift is permitted. The
# transformations below retain every original byte and spell out every added
# byte, so a new hash plus matching substrings cannot waive arbitrary edits.
P003_BUILD_CITATIONS = {
    "core-runtime-owners": ("src/CMakeLists.txt", "build_ownership"),
    "gui-source-owners": ("src/CMakeLists.txt", "build_ownership"),
    "host-build-restrictions": ("CMakeLists.txt", "architecture_constraint"),
    "python-bytecode-is-conditional": ("CMakeLists.txt", "build_ownership"),
    "metal-and-setcap-build-prerequisites": ("CMakeLists.txt", "build_ownership"),
}
P003_BUILD_ADDITIONS = {
    "CMakeLists.txt": (
        (b'option(ENABLE_TESTS "Install in-prefix unit tests" OFF)\n',
         b'option(DARLING_P003_PROBES "Build installed-runtime P003 qualification probes" OFF)\n'),
    ),
    "src/CMakeLists.txt": (
        (b"add_subdirectory(external/libxpc)\n",
         b"# The pinned libxpc's transaction.m still logs xpc_transaction_begin/end as\n"
         b"# placeholders, even though liblaunch already implements their shared process\n"
         b"# lifecycle counter. Supply the real bridge in this root-owned source tree; do\n"
         b"# not rewrite a pinned submodule checkout or silently change its gitlink.\n"
         b"# Retain every unrelated libxpc source and all target options/dependencies.\n"
         b"include(darling_xpc_transaction)\n"
         b'darling_replace_libxpc_transaction(xpc_obj "${CMAKE_CURRENT_SOURCE_DIR}/compat/logic-pro/libxpc_transaction.m")\n'
         b'target_include_directories(xpc_obj PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/launchd/liblaunch")\n'),
        (b"add_subdirectory(external/libunwind)\n",
         b"include(darling_unwind_configuration)\n"
         b"darling_configure_static_unwind(unwind_static)\n"),
        (b"add_subdirectory(external/objc4/runtime)\n",
         b"include(darling_objc_configuration)\n"
         b'darling_configure_objc_runtime("${CMAKE_CURRENT_SOURCE_DIR}/external/objc4/runtime")\n'),
        (b"#add_subdirectory(external/WebCore)\n",
         b"\nif (DARLING_P003_PROBES)\n"
         b'\tadd_subdirectory("${CMAKE_SOURCE_DIR}/tests/compat/logic-pro/build"\n'
         b'\t\t"${CMAKE_BINARY_DIR}/p003-probe-build")\n'
         b"endif()\n"),
    ),
}

# Only the exact reviewed upstream commit may be layered on top of the previously
# accepted P003 root CMake integration. The historical P001 source object and
# P003 pre-merge object remain mandatory byte-for-byte predecessors.
P004_UPSTREAM_COMMIT = "5e08de551ae51ea8415bfad875ea95f0e44cda51"
P004_P003_ROOT_CMAKE_BLOB = "6e5320117349ab0edead8ef0ee84ef41fd487e82"
P004_UPSTREAM_CMAKE_ADDITIONS = (
    (b'SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${IGNORED_WARNINGS}")\n',
     b"\n# newer Clang emits ObjC literals as constant objects (NSConstantArray, etc.) that our Foundation does not provide\n"
     b"include(CheckCCompilerFlag)\n"
     b"check_c_compiler_flag(-fno-objc-constant-literals HAS_NO_OBJC_CONSTANT_LITERALS)\n"
     b"if(HAS_NO_OBJC_CONSTANT_LITERALS)\n"
     b'\tset(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fno-objc-constant-literals")\n'
     b'\tset(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fno-objc-constant-literals")\n'
     b"endif()\n\n"),
)


def git(repo: Path, *args: str) -> bytes:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
                "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0"})
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=" + os.devnull, "-C", str(repo), *args],
        capture_output=True, timeout=30, check=False, env=env,
    )
    if result.returncode:
        raise EvidenceError(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout


def safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\n" in value:
        raise EvidenceError("source path must be a nonempty single-line string")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("..", ".git") for p in path.parts) or str(path) != value:
        raise EvidenceError(f"unsafe or noncanonical source path: {value!r}")
    return value


def source_repository(repo: Path, record: dict, original: str, current: str | None) -> tuple[Path, str, str, list]:
    """Bind a child citation to each committed gitlink, including nested hops."""
    owner = record.get("repository", ".")
    chain = record.get("gitlink_chain", [])
    if owner == ".":
        if chain or record.get("repository_commit", original) != original:
            raise EvidenceError("parent source has inconsistent repository metadata")
        return repo, original, owner, []
    owner = safe_path(owner)
    if not isinstance(chain, list) or not chain:
        raise EvidenceError("child source needs an explicit nonempty gitlink chain")
    folder, pinned, now = repo, original, current
    parts = []
    for hop in chain:
        if not isinstance(hop, dict):
            raise EvidenceError("invalid gitlink chain record")
        path, expected = safe_path(hop.get("path")), hop.get("commit")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
            raise EvidenceError("gitlink chain needs an exact commit SHA")
        wanted = b"160000 commit " + expected.encode("ascii") + b"\t" + path.encode("utf-8") + b"\0"
        for revision in {pinned, now} - {None}:
            if git(folder, "--literal-pathspecs", "ls-tree", "-z", revision, "--", path) != wanted:
                raise EvidenceError("source gitlink chain differs from the committed original or current pin")
        child = folder
        for component in PurePosixPath(path).parts:
            child = child / component
            if child.is_symlink():
                raise EvidenceError("symlink in source repository path")
        if (child / ".git").is_symlink() or not (child / ".git").exists():
            raise EvidenceError("child source checkout is missing or unsafe")
        if Path(git(child, "rev-parse", "--show-toplevel").decode().strip()).resolve() != child.resolve():
            raise EvidenceError("child source is not an independent checkout")
        if git(child, "rev-parse", "HEAD").decode().strip() != expected:
            raise EvidenceError("child source checkout is not at its committed pin")
        if git(child, "rev-parse", "--verify", expected + "^{commit}").decode().strip() != expected:
            raise EvidenceError("child commit does not resolve exactly")
        folder, pinned, now = child, expected, expected if current is not None else None
        parts.append(path)
    if "/".join(parts) != owner or record.get("repository_commit") != pinned:
        raise EvidenceError("source repository does not match its full gitlink chain")
    return folder, pinned, owner, chain


def phase_coverage(checked: list[dict], required: bool) -> dict:
    categories = sorted({entry["category"] for entry in checked})
    satisfied = []
    missing_sources = {}
    for stage, sources in REQUIRED_STAGES.items():
        observed = {(entry["repository"], entry["path"]) for entry in checked
                    if stage in entry["launch_stages"]}
        missing = [{"repository": owner, "path": path} for owner, path in sources
                   if (owner, path) not in observed]
        if missing:
            missing_sources[stage] = missing
        else:
            satisfied.append(stage)
    missing_categories = sorted(set(REQUIRED_CATEGORIES) - set(categories))
    return {"required": required,
            "status": "PASS" if not missing_categories and not missing_sources else "FAIL" if required else "NOT_REQUIRED",
            "required_categories": list(REQUIRED_CATEGORIES), "categories": categories,
            "missing_categories": missing_categories, "required_stages": list(REQUIRED_STAGES),
            "launch_stages": satisfied, "missing_stages": sorted(missing_sources),
            "missing_stage_sources": missing_sources}


def verify_url_reaudit(original: bytes, updated: bytes, current_blob: str,
                       record: dict) -> dict:
    """Preserve the P001 citation while re-auditing P002's URL-only relocation.

    This is deliberately narrow: only the root .gitmodules may change, every
    non-URL byte must remain identical, and each rewritten URL must be exactly
    the old relative sibling path at the recorded Darling upstream origin.
    Changed pins are *not* licensed by this exception (the P002 lock verifies
    them separately). All other citations retain the strict original rule.
    """
    audit = record.get("current_reaudit")
    if record.get("path") != ".gitmodules" or record.get("repository", ".") != ".":
        raise EvidenceError("current-source re-audit is only supported for root .gitmodules")
    if not isinstance(audit, dict) or audit.get("phase") != "P002":
        raise EvidenceError("changed .gitmodules needs an explicit P002 current-source re-audit")
    before, after = original.splitlines(keepends=True), updated.splitlines(keepends=True)
    if len(before) != len(after):
        raise EvidenceError("P002 .gitmodules added or removed source lines")
    changed = 0
    prefix = b"\turl = "
    for old, new in zip(before, after):
        if old == new:
            continue
        if not old.startswith(prefix + b"../") or new != prefix + b"https://github.com/darlinghq/" + old[len(prefix) + 3:]:
            raise EvidenceError("P002 changed non-URL source or changed a dependency target")
        changed += 1
    if (type(audit.get("expected_url_rewrites")) is not int or changed == 0
            or changed != audit["expected_url_rewrites"]):
        raise EvidenceError("P002 URL-only relocation count differs from re-audit")
    if current_blob != audit.get("blob_sha1"):
        raise EvidenceError("P002 current .gitmodules blob has changed since re-audit")
    start, end = audit.get("line_start"), audit.get("line_end")
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(after):
        raise EvidenceError("invalid current-source citation range")
    excerpt = b"".join(after[start - 1:end])
    if hashlib.sha256(excerpt).hexdigest() != audit.get("excerpt_sha256"):
        raise EvidenceError("P002 re-audited excerpt hash mismatch")
    assertions = audit.get("contains")
    if not isinstance(assertions, list) or not assertions or any(not isinstance(s, str) or not s or s.encode() not in excerpt for s in assertions):
        raise EvidenceError("P002 re-audited source assertions failed")
    return {"phase": "P002", "blob_sha1": current_blob,
            "excerpt_sha256": audit["excerpt_sha256"], "url_rewrites_verified": changed}


def verify_build_reaudit(original: bytes, updated: bytes, current_blob: str,
                         record: dict) -> dict:
    """Permit only reviewed P003 integration and the exact P004 upstream CMake addition."""
    identity = (record.get("path"), record.get("category"))
    if (record.get("repository", ".") != "."
            or P003_BUILD_CITATIONS.get(record.get("id")) != identity):
        raise EvidenceError("P003/P004 current-source re-audit is not allowed for this citation")
    audit = record.get("current_reaudit")
    if not isinstance(audit, dict) or audit.get("phase") not in ("P003", "P004"):
        raise EvidenceError("changed CMake source needs an explicit scoped current-source re-audit")
    phase = audit["phase"]
    if phase == "P003":
        if audit.get("kind") != "additive-build-integration":
            raise EvidenceError("invalid P003 build re-audit kind")
    elif (record["path"] != "CMakeLists.txt"
          or audit.get("kind") != "p003-plus-reviewed-upstream-merge"
          or audit.get("upstream_merge_commit") != P004_UPSTREAM_COMMIT
          or audit.get("prior_p003_blob_sha1") != P004_P003_ROOT_CMAKE_BLOB):
        raise EvidenceError("P004 current-source re-audit must bind the exact reviewed upstream delta")

    additions = P003_BUILD_ADDITIONS[record["path"]]
    expected = original
    for anchor, addition in additions:
        if expected.count(anchor) != 1:
            raise EvidenceError("P003 build integration anchor is missing or ambiguous")
        expected = expected.replace(anchor, anchor + addition, 1)

    if phase == "P004":
        # Recompute the accepted pre-merge Git blob from original historical
        # source plus *only* the reviewed P003 additions. Never use a caller
        # supplied hash as the sole authority for predecessor identity.
        prefix = b"blob " + str(len(expected)).encode("ascii") + b"\0"
        if hashlib.sha1(prefix + expected).hexdigest() != P004_P003_ROOT_CMAKE_BLOB:
            raise EvidenceError("P004 predecessor differs from accepted P003 CMake source")
        for anchor, addition in P004_UPSTREAM_CMAKE_ADDITIONS:
            if expected.count(anchor) != 1:
                raise EvidenceError("P004 upstream integration anchor is missing or ambiguous")
            expected = expected.replace(anchor, anchor + addition, 1)

    if updated != expected:
        raise EvidenceError("CMake source differs beyond the reviewed byte-exact P003/P004 integrations")
    if current_blob != audit.get("blob_sha1"):
        raise EvidenceError("current CMake blob has changed since reviewed re-audit")
    lines = updated.splitlines(keepends=True)
    start, end = audit.get("line_start"), audit.get("line_end")
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise EvidenceError("invalid current-source citation range")
    excerpt = b"".join(lines[start - 1:end])
    if hashlib.sha256(excerpt).hexdigest() != audit.get("excerpt_sha256"):
        raise EvidenceError("re-audited current-source excerpt hash mismatch")
    assertions = audit.get("contains")
    if (assertions != record.get("contains") or not isinstance(assertions, list) or not assertions
            or any(not isinstance(value, str) or not value or value.encode() not in excerpt for value in assertions)):
        raise EvidenceError("current source does not preserve the original citation assertions")
    result = {"phase": phase, "kind": audit["kind"], "blob_sha1": current_blob,
              "excerpt_sha256": audit["excerpt_sha256"],
              "additions_verified": len(additions) + (len(P004_UPSTREAM_CMAKE_ADDITIONS) if phase == "P004" else 0),
              "original_assertions_preserved": True}
    if phase == "P004":
        result["upstream_merge_commit"] = P004_UPSTREAM_COMMIT
        result["prior_p003_blob_sha1"] = P004_P003_ROOT_CMAKE_BLOB
    return result


def verify(repo: Path, manifest: dict, current_ref: str | None = None, require_phase_coverage: bool = False) -> dict:
    if not isinstance(manifest, dict):
        raise EvidenceError("classification manifest must be a JSON object")
    if manifest.get("schema_version") != 1:
        raise EvidenceError("unsupported classification schema_version")
    commit = manifest.get("inspected_commit", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise EvidenceError("inspected_commit must be a full SHA-1 commit ID")
    resolved = git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    if resolved != commit:
        raise EvidenceError("inspected commit does not resolve exactly")
    current = None
    if current_ref is not None:
        current = git(repo, "rev-parse", "--verify", "--end-of-options", f"{current_ref}^{{commit}}").decode().strip()
    records = manifest.get("evidence")
    if not isinstance(records, list) or not records:
        raise EvidenceError("empty classification evidence cannot pass")
    cache: dict[tuple[str, str], tuple[str, bytes]] = {}
    seen: set[str] = set()
    checked = []
    failures = []
    for record in records:
        record_id = record.get("id") if isinstance(record, dict) else None
        try:
            if not isinstance(record_id, str) or not record_id or record_id in seen:
                raise EvidenceError("missing or duplicate evidence ID")
            seen.add(record_id)
            if record.get("observation") != "STATIC_SOURCE_INSPECTION":
                raise EvidenceError("classification must explicitly identify static source inspection")
            if not isinstance(record.get("category"), str) or not record["category"]:
                raise EvidenceError("missing category")
            stages = record.get("launch_stages", [])
            if not isinstance(stages, list) or any(s not in REQUIRED_STAGES for s in stages):
                raise EvidenceError("invalid launch stage")
            folder, source_commit, owner, chain = source_repository(repo, record, commit, current)
            path = safe_path(record.get("path"))
            start, end = record.get("line_start"), record.get("line_end")
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise EvidenceError("invalid inclusive source line range")
            contains = record.get("contains")
            if not isinstance(contains, list) or not contains or any(not isinstance(s, str) or not s for s in contains):
                raise EvidenceError("contains must have at least one nonempty assertion")
            key = (owner, path)
            if key not in cache:
                obj = git(folder, "rev-parse", "--verify", f"{source_commit}:{path}").decode().strip()
                if git(folder, "cat-file", "-t", obj).strip() != b"blob":
                    raise EvidenceError("source evidence must refer to a blob")
                data = git(folder, "cat-file", "blob", obj)
                cache[key] = (obj, data)
            obj, data = cache[key]
            if obj != record.get("blob_sha1"):
                raise EvidenceError("source blob SHA-1 mismatch")
            lines = data.splitlines(keepends=True)
            if end > len(lines):
                raise EvidenceError("citation extends beyond source file")
            excerpt = b"".join(lines[start - 1:end])
            if hashlib.sha256(excerpt).hexdigest() != record.get("excerpt_sha256"):
                raise EvidenceError("source excerpt SHA-256 mismatch")
            if any(s.encode("utf-8") not in excerpt for s in contains):
                raise EvidenceError("required source text is missing from cited lines")
            current_audit = None
            if current is not None:
                now = git(folder, "rev-parse", "--verify", f"{current if owner == '.' else source_commit}:{path}").decode().strip()
                if now != obj:
                    revised = git(folder, "cat-file", "blob", now)
                    audit = record.get("current_reaudit")
                    if isinstance(audit, dict) and audit.get("phase") in ("P003", "P004"):
                        current_audit = verify_build_reaudit(data, revised, now, record)
                    else:
                        current_audit = verify_url_reaudit(data, revised, now, record)
            checked.append({"id": record_id, "category": record["category"], "path": path,
                            "repository": owner, "repository_commit": source_commit,
                            "gitlink_chain": chain, "launch_stages": stages,
                            "blob_sha1": obj, "line_start": start, "line_end": end,
                            "excerpt_sha256": record["excerpt_sha256"],
                            "current_reaudit": current_audit})
        except (EvidenceError, UnicodeError, TypeError) as exc:
            failures.append({"id": record_id, "error": str(exc)})
    coverage = phase_coverage(checked, require_phase_coverage)
    if require_phase_coverage:
        if coverage["status"] != "PASS":
            failures.append({"id": "P001-coverage", "error": "required classification categories or launch-stage sources are missing"})
        if manifest.get("runtime_executed") is not False:
            failures.append({"id": "P001-observation", "error": "static audit must explicitly disclaim runtime execution"})
    return {
        "schema_version": 1, "status": "PASS" if not failures else "FAIL",
        "scope": "Pinned source-citation integrity; no runtime execution or framework completeness claim.",
        "inspected_commit": commit, "current_commit": current,
        "checked_count": len(checked), "source_file_count": len(cache),
        "coverage": coverage,
        "checked": checked, "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--current-ref")
    parser.add_argument("--require-phase-coverage", action="store_true",
                        help="require P001's fixed classification categories and launch-stage source owners")
    args = parser.parse_args(argv)
    try:
        result = verify(args.repo, json.loads(args.manifest.read_text()), args.current_ref, args.require_phase_coverage)
    except (EvidenceError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result = {"schema_version": 1, "status": "FAIL", "failures": [{"error": str(exc)}]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"source classifications: {result['status']}; {result.get('checked_count', 0)} citations verified")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
