#!/usr/bin/env python3
"""Compare P003 clean builds and check the raw evidence behind their reports.

This establishes that the automated campaign completed. The README gate still
requires a different reviewer to accept the exact implementation and any
enumerated output nondeterminism before P003 can be marked PASSED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import run_build_probes as probes
import native_dependencies as native
import lock_toolchain as toolchain
import verify_classifications as source_audit

SHA = re.compile(r"[0-9a-f]{64}")
CLASSIFICATION_MANIFEST = Path(__file__).with_name("classifications.json")
CLASSIFICATION_COUNT = 63
UNWIND_SOURCE_HASHES = {
    "/p003/source/src/external/libunwind/libunwind/src/Registers.hpp":
        "32423fef71c163f1315b031ed14f34f7e7d1e08b68732041b8d39efbf2e5ef30",
    "/p003/source/src/external/libunwind/libunwind/include/libunwind.h":
        "09e29df5f6d80f0555a0a3839f836052ded9698e4a91607e5cb033bd10401f2e",
}
CASES = {"macho-known-vector", "macho-nonce", "macho-boundary-64", "macho-reject-65",
         "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
         "foundation-objects", "gui-event-roundtrip", "runtime-shutdown"}
COMMAND_EXITS = {name: 0 for name in (
    "macho-known-vector", "macho-nonce", "macho-boundary-64", "foundation",
    "gui-focus", "gui-move", "gui-click", "gui-type", "gui-acknowledge", "gui", "shutdown")}
COMMAND_EXITS.update({name: 64 for name in (
    "macho-reject-65", "macho-invalid", "foundation-invalid", "gui-invalid")})


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read(path: Path) -> dict:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def bound_file(root: Path, reference: dict) -> Path:
    name = reference["file"]
    require(isinstance(name, str) and PurePosixPath(name).name == name
            and name not in ("", ".", ".."), "Evidence filename must be one plain basename")
    path = root / name
    require(path.is_file() and not path.is_symlink(), f"Missing regular evidence file: {path}")
    require(SHA.fullmatch(reference["sha256"]) is not None, "Invalid evidence SHA-256")
    require(digest(path) == reference["sha256"], f"Evidence digest mismatch: {path}")
    return path


def assert_xwd_challenge_title(data: bytes, ready: bool, nonce: str) -> None:
    """Bind the original XWD window name to its challenge and capture state.

    P003's original 10 XWD captures carry an exact NUL-terminated
    ``P003_WAIT_<nonce>`` or ``P003_READY_<nonce>`` name immediately after the
    100-byte XWD v7 header. The independently reviewed original-image decoder
    also checks this exact on-disk field, not a producer JSON assertion.
    """
    require(len(data) >= 100, "Truncated XWD window-title header")
    header_size = int.from_bytes(data[:4], "big")
    require(100 < header_size <= len(data), "Missing XWD window title")
    state = "READY" if ready else "WAIT"
    expected = f"P003_{state}_{nonce}".encode("ascii") + b"\0"
    require(data[100:header_size] == expected,
            "XWD window title does not match runtime nonce and capture state")


def entries(report: dict) -> dict:
    result = {}
    for item in report["entries"]:
        name = item["path"]
        require(isinstance(name, str) and name not in ("", ".")
                and not name.startswith("/") and ".." not in PurePosixPath(name).parts
                and str(PurePosixPath(name)) == name, "Invalid install entry path")
        require(name not in result, f"Duplicate install entry: {name}")
        require(item["kind"] in ("file", "directory", "symlink"), "Invalid installed file kind")
        if item["kind"] == "file":
            require(SHA.fullmatch(item["sha256"]) is not None and item["size"] >= 0,
                    "Invalid installed file size/digest")
        result[name] = item
    require(bool(result), "An empty installation cannot qualify")
    return result


def validate_source_classifications(root: Path, commit: str) -> dict:
    """Bind every original/current P001 citation to this candidate's manifest."""
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
            "Source classifications require an exact current commit")
    path, log = root / "source-classifications.json", root / "source-classifications.log"
    require(path.is_file() and not path.is_symlink(), "Missing regular source-classification report")
    require(log.is_file() and not log.is_symlink() and log.stat().st_size > 0,
            "Missing raw source-classification log")
    manifest, report = read(CLASSIFICATION_MANIFEST), read(path)
    require(type(manifest.get("schema_version")) is int and manifest["schema_version"] == 1
            and manifest.get("runtime_executed") is False, "Invalid current classification manifest")
    require(type(report.get("schema_version")) is int and report["schema_version"] == 1
            and report.get("status") == "PASS" and report.get("failures") == [],
            "Source-classification verification failed")
    require(report.get("current_commit") == commit
            and report.get("inspected_commit") == manifest.get("inspected_commit"),
            "Source classifications tested a different current or inspected commit")

    def canonical(value):
        # JSON distinguishes booleans and integers, unlike Python dict equality.
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)

    expected = {}
    records = manifest.get("evidence")
    require(isinstance(records, list) and len(records) == CLASSIFICATION_COUNT,
            "Current manifest does not contain the accepted 63 citations")
    current_audit = manifest.get("current_source_reaudit")
    require(isinstance(current_audit, dict)
            and type(current_audit.get("schema_version")) is int
            and current_audit["schema_version"] == 1,
            "Missing complete current-source re-audit")
    try:
        anchor, current_records = source_audit.current_source_records(
            CLASSIFICATION_MANIFEST.parent, manifest, resolve_anchor=False)
    except source_audit.EvidenceError as exc:
        raise ValueError(str(exc)) from exc
    require(report.get("current_source_anchor") == anchor,
            "Source classifications used a different current source anchor")
    for record in records:
        require(isinstance(record, dict), "Invalid current manifest citation")
        identity = record.get("id")
        require(isinstance(identity, str) and identity and identity not in expected,
                "Current manifest has missing or duplicate citation IDs")
        require(record.get("observation") == "STATIC_SOURCE_INSPECTION",
                "Source classification is not a static inspection")
        current = None
        audit = record.get("current_reaudit")
        if audit is not None:
            require(isinstance(audit, dict), f"Invalid current re-audit: {identity}")
            current = {"phase": audit["phase"], "blob_sha1": audit["blob_sha1"],
                       "excerpt_sha256": audit["excerpt_sha256"]}
            if audit["phase"] == "P002":
                require(record.get("repository", ".") == "." and record["path"] == ".gitmodules"
                        and type(audit.get("expected_url_rewrites")) is int
                        and audit["expected_url_rewrites"] > 0,
                        "Invalid URL-only current-source re-audit")
                current["url_rewrites_verified"] = audit["expected_url_rewrites"]
            elif audit["phase"] in ("P003", "P004"):
                require(record.get("repository", ".") == "."
                        and source_audit.P003_BUILD_CITATIONS.get(identity)
                        == (record["path"], record["category"]),
                        "Unreviewed current build-source re-audit")
                additions = len(source_audit.P003_BUILD_ADDITIONS[record["path"]])
                if audit["phase"] == "P003":
                    require(audit.get("kind") == "additive-build-integration",
                            "Unreviewed current build-source re-audit")
                else:
                    # P001 already verifies this exact historical upstream delta
                    # byte for byte. Consuming its current report does not accept
                    # P004 or allow arbitrary later-phase source modifications.
                    require(record["path"] == "CMakeLists.txt"
                            and audit.get("kind") == "p003-plus-reviewed-upstream-merge"
                            and audit.get("upstream_merge_commit") == source_audit.P004_UPSTREAM_COMMIT
                            and audit.get("prior_p003_blob_sha1") == source_audit.P004_P003_ROOT_CMAKE_BLOB,
                            "Unreviewed current upstream build-source re-audit")
                    additions += len(source_audit.P004_UPSTREAM_CMAKE_ADDITIONS)
                    current.update(upstream_merge_commit=source_audit.P004_UPSTREAM_COMMIT,
                                   prior_p003_blob_sha1=source_audit.P004_P003_ROOT_CMAKE_BLOB)
                current.update(kind=audit["kind"], additions_verified=additions,
                               original_assertions_preserved=True)
            else:
                raise ValueError(f"Unsupported current-source re-audit: {identity}")
        source = current_records[identity]
        owner = record.get("repository", ".")
        require(source.get("repository") == owner and source.get("path") == record["path"],
                f"Current source identity differs from the original citation: {identity}")
        require(owner != "." or (source.get("repository_commit") == anchor
                                and source.get("gitlink_chain") == []),
                f"Current root source does not bind the reviewed anchor: {identity}")
        assertions = source.get("contains")
        required_assertions = (audit.get("contains") if audit and audit["phase"] == "P002"
                               else record.get("contains"))
        require(isinstance(assertions, list) and assertions
                and all(isinstance(value, str) and value for value in assertions)
                and assertions == required_assertions,
                f"Current source does not preserve original or reviewed URL assertions: {identity}")
        current_source = {
            "source_anchor": anchor, "repository": owner, "path": source["path"],
            "repository_commit": commit if owner == "." else source["repository_commit"],
            "gitlink_chain": source["gitlink_chain"], "blob_sha1": source["blob_sha1"],
            "line_start": source["line_start"], "line_end": source["line_end"],
            "excerpt_sha256": source["excerpt_sha256"], "assertions_verified": len(assertions),
            "original_assertions_preserved": True,
        }
        expected[identity] = {
            "id": identity, "category": record["category"], "path": record["path"],
            "repository": record.get("repository", "."),
            "repository_commit": record.get("repository_commit", manifest["inspected_commit"]),
            "gitlink_chain": record.get("gitlink_chain", []),
            "launch_stages": record.get("launch_stages", []),
            "blob_sha1": record["blob_sha1"], "line_start": record["line_start"],
            "line_end": record["line_end"], "excerpt_sha256": record["excerpt_sha256"],
            "current_reaudit": current, "current_source": current_source,
        }
    checked = report.get("checked")
    require(isinstance(checked, list) and len(checked) == CLASSIFICATION_COUNT
            and type(report.get("checked_count")) is int
            and report["checked_count"] == CLASSIFICATION_COUNT,
            "Source-classification report omitted accepted citations")
    seen = set()
    for record in checked:
        require(isinstance(record, dict), "Invalid checked source citation")
        identity = record.get("id")
        require(isinstance(identity, str) and identity in expected and identity not in seen,
                "Missing, duplicate or unexpected checked citation ID")
        require(canonical(record) == canonical(expected[identity]),
                f"Checked citation differs from the current manifest: {identity}")
        seen.add(identity)
    require(seen == set(expected), "Checked source citation IDs differ from the current manifest")
    source_count = len({(record["repository"], record["path"]) for record in checked})
    require(type(report.get("source_file_count")) is int and report["source_file_count"] == source_count,
            "Source-classification file coverage differs from checked citations")

    categories = sorted({record["category"] for record in checked})
    missing_categories = sorted(set(source_audit.REQUIRED_CATEGORIES) - set(categories))
    satisfied, missing_sources = [], {}
    for stage, required_sources in source_audit.REQUIRED_STAGES.items():
        actual = {(record["repository"], record["path"]) for record in checked
                  if stage in record["launch_stages"]}
        absent = [{"repository": owner, "path": path} for owner, path in required_sources
                  if (owner, path) not in actual]
        if absent:
            missing_sources[stage] = absent
        else:
            satisfied.append(stage)
    require(not missing_categories and not missing_sources,
            "Actual checked citations do not cover the required P001 categories and launch sources")
    coverage = {"required": True, "status": "PASS",
                "required_categories": list(source_audit.REQUIRED_CATEGORIES), "categories": categories,
                "missing_categories": [], "required_stages": list(source_audit.REQUIRED_STAGES),
                "launch_stages": satisfied, "missing_stages": [], "missing_stage_sources": {}}
    require(canonical(report.get("coverage")) == canonical(coverage),
            "Claimed source-classification coverage differs from the checked citations")
    require(log.read_text().splitlines() == [f"source classifications: PASS; {CLASSIFICATION_COUNT} citations verified"],
            "Raw source-classification log contradicts the required successful audit")
    return {"current_commit": commit, "inspected_commit": manifest["inspected_commit"],
            "current_source_anchor": anchor,
            "checked_count": len(checked), "source_file_count": source_count,
            "manifest_sha256": digest(CLASSIFICATION_MANIFEST),
            "report_sha256": digest(path), "log_sha256": digest(log)}


def validate_unwind_codegen(root: Path, lock: dict, toolchain_sha256: str) -> dict:
    """Require the frozen-compiler regression and its existing raw artifacts."""
    proof_root = root / "unwind-codegen"
    require(proof_root.is_dir() and not proof_root.is_symlink()
            and proof_root.resolve().is_relative_to(root.resolve()),
            "Static-unwind evidence directory is missing or redirected")
    path, log = proof_root / "report.json", root / "unwind-codegen.log"
    require(path.is_file() and not path.is_symlink() and log.is_file()
            and not log.is_symlink() and log.stat().st_size > 0,
            "Required raw static-unwind compiler regression is missing")
    proof = read(path)
    require(proof.get("schema") == "darling.p003.unwind-codegen.v1"
            and proof.get("status") == "PASS" and proof.get("errors") == [],
            "Static-unwind compiler regression failed")
    helper = Path(__file__).resolve().parents[3] / "cmake/darling_unwind_configuration.cmake"
    require(proof.get("compiler", {}).get("sha256") == lock["environment"]["tools"]["clang"]["sha256"]
            and proof.get("toolchain_sha256") == toolchain_sha256
            and proof.get("helper_sha256") == digest(helper),
            "Static-unwind proof used a different compiler, toolchain or configuration helper")
    require(proof.get("source_inputs") == UNWIND_SOURCE_HASHES,
            "Static-unwind proof did not use the exact pinned register-name sources")
    evidence = proof.get("evidence")
    required = {"compiler-version.stdout.log", "control-behavior.stdout.log", "repaired-behavior.stdout.log",
                "macho/build/compile_commands.json",
                "macho/build/CMakeFiles/control_static.dir/register_names.cpp.o",
                "macho/build/CMakeFiles/unwind_static.dir/register_names.cpp.o"}
    require(isinstance(evidence, dict) and required.issubset(evidence),
            "Static-unwind proof omitted its critical compiler artifacts")
    for name, expected_hash in evidence.items():
        require(isinstance(name, str) and name not in ("", ".", "report.json")
                and not name.startswith("/") and ".." not in PurePosixPath(name).parts
                and str(PurePosixPath(name)) == name, "Unsafe static-unwind evidence path")
        artifact = proof_root / name
        require(artifact.is_file() and not artifact.is_symlink()
                and artifact.resolve().is_relative_to(proof_root.resolve()),
                f"Missing regular static-unwind evidence: {name}")
        require(isinstance(expected_hash, str) and SHA.fullmatch(expected_hash) is not None
                and digest(artifact) == expected_hash, f"Static-unwind evidence digest mismatch: {name}")
    return {"report_sha256": digest(path), "log_sha256": digest(log), "evidence_files": len(evidence)}


def validate_probes(root: Path, install: dict) -> dict:
    report = read(root / "report.json")
    require(report.get("status") == "PASSED" and report.get("passed") is True
            and report.get("errors") == [], f"Runtime probe campaign did not pass: {root}")
    require(report.get("stub_diagnostics") == {"enabled": True,
            "environment": {"STUB_VERBOSE": "1"}, "hits": []},
            "Runtime placeholder diagnostics were disabled, missing, or nonempty")
    cases = report["cases"]
    require(len(cases) == len(CASES) and {row["name"] for row in cases} == CASES
            and all(row["status"] == "PASSED" for row in cases), "Missing or failed runtime case")
    nonce = report["nonce"]
    require(re.fullmatch(r"[0-9a-f]{16}", nonce) is not None, "Missing runtime challenge")
    records = {}
    for command in report["commands"]:
        name = command["label"]
        require(name not in records, f"Duplicate runtime command: {name}")
        require(name in COMMAND_EXITS, f"Unexpected runtime command: {name}")
        require(command.get("timed_out", False) is False, f"Timed-out command: {name}")
        require(command["exit_code"] == COMMAND_EXITS[name]
                and command.get("expected_exit_code", 0) == COMMAND_EXITS[name],
                f"Unexpected runtime exit: {name}")
        out = bound_file(root, command["stdout"]).read_text()
        error = bound_file(root, command["stderr"]).read_text()
        require(not probes.stub_diagnostics(out) and not probes.stub_diagnostics(error),
                f"Reached generic stub or unimplemented operation: {name}")
        if COMMAND_EXITS[name] == 0:
            probes.assert_no_probe_errors(out, error)
        if COMMAND_EXITS[name] == 64:
            kind = name.split("-")[0].upper()
            reason = "challenge" if kind == "GUI" else "arguments"
            require([line for line in error.splitlines() if line.startswith("P003_")]
                    == [f"P003_{kind}_ERROR invalid {reason}"]
                    and not any(line.startswith("P003_") for line in out.splitlines()),
                    f"Required explicit invalid-argument rejection missing: {name}")
        records[name] = out
    require(set(records) == set(COMMAND_EXITS), "Required runtime command evidence missing")
    lifecycle = report["lifecycle"]
    require(lifecycle.get("server_exited") is True and lifecycle.get("mount_namespace_released") is True
            and lifecycle.get("namespace_holders_after") == [], "Runtime namespace shutdown was not proved")
    for name, value in (("macho-known-vector", "hello"), ("macho-nonce", nonce),
                        ("macho-boundary-64", "a" * 64)):
        probes.assert_record(records[name], f"P003_MACHO nonce={value} hash={probes.fnv1a(value):08x}")
    probes.assert_record(records["foundation"], f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil")
    probes.assert_record(records["foundation"], f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0")
    probes.assert_record(records["gui"], f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1")
    probes.assert_images(records["gui"])
    for state, ready in (("before", False), ("after", True)):
        reference = report["screenshots"][state]
        raw = bound_file(root, reference).read_bytes()
        sample = probes.xwd_sample(raw)
        require(sample == reference["pixels"], "Screenshot metadata differs from actual pixels")
        probes.assert_colors(sample, ready)
        probes.assert_xwd_coverage(raw, ready)
        assert_xwd_challenge_title(raw, ready, nonce)
        png = bound_file(root, reference["png"])
        require(png.read_bytes() == probes.xwd_png(raw),
                "PNG does not preserve the asserted X11 screenshot")
    require(set(report["binaries"]) == {"p003_macho", "p003_foundation", "p003_gui"},
            "Missing installed Mach-O probe identity")
    package = entries(install)
    for name, binary in report["binaries"].items():
        item = package["libexec/darling/usr/libexec/p003/" + name]
        require(item["sha256"] == binary["sha256"] and item["size"] == binary["bytes"],
                f"Runtime did not use the verified installed probe: {name}")
    return {"nonce": nonce, "cases": len(cases), "report_sha256": digest(root / "report.json")}


def validate_native(root: Path, name: str, commit: str, installation: dict) -> None:
    report = read(root / f"native-{name}.json")
    require(report.get("status") == "PASSED" and report.get("errors") == []
            and report.get("source_commit") == commit, "Native dependency audit failed")
    package = entries(installation)
    seen = set()
    for item in report["entries"]:
        relative = item["installed_path"]
        require(relative not in seen and package[relative]["sha256"] == item["sha256"],
                "Native executable identity differs from installed package")
        seen.add(relative)
    require(native.REQUIRED_ENTRYPOINTS.issubset(seen), "Native runtime entrypoints were not inspected")
    expected_wrappers, expected_inputs = native.declared_wrappers(Path(__file__).resolve().parents[3])
    require(len(report["wrapped_libraries"]) == len(expected_wrappers)
            and {item["soname"] for item in report["wrapped_libraries"]} == set(expected_wrappers),
            "Required native wrappers were not inspected exactly once")
    require(report["wrapper_source_inputs"] == expected_inputs, "Wrapper source identity differs")
    require(bool(report["commands"]), "Missing native dependency command evidence")
    for command in report["commands"]:
        require(command.get("exit_code") == 0 and command.get("timed_out") is False,
                "Native inspection command did not succeed")
        for stream in ("stdout", "stderr"):
            reference = command[stream]
            relative = PurePosixPath(reference["file"])
            require(relative.parent.as_posix() == f"native-{name}.logs", "Native log escaped its campaign")
            bound_file(root / relative.parent, {"file": relative.name, "sha256": reference["sha256"]})


def campaign(root: Path, commit: str) -> dict:
    summary = read(root / "build-summary.json")
    require(summary.get("status") == "PASS" and summary.get("exit_code") == 0
            and summary.get("last_stage") == "complete", "A clean build campaign failed")
    require(summary.get("source_commit") == commit, "Build tested a different source revision")
    require(digest(root / "toolchain.lock.json") == summary["toolchain_sha256"],
            "Recorded toolchain lock changed")
    lock = read(root / "toolchain.lock.json")
    observation = read(root / "toolchain-host-observation.json")
    require(observation.get("status") == "PASSED"
            and observation.get("lock_sha256") == summary["toolchain_sha256"]
            and observation.get("identity_differences") == [],
            "Per-host toolchain verification is missing or failed")
    require(toolchain.environment_identity(lock["environment"])
            == toolchain.environment_identity(observation["environment"]),
            "Actual host toolchain does not match the frozen lock")
    require(observation.get("raw_observation_differences")
            == toolchain.identity_differences(lock["environment"], observation["environment"]),
            "Raw host observation differences were not preserved accurately")
    source = read(root / "source-lock-verification.json")
    require(source.get("result") == "PASS" and source.get("root_commit") == commit,
            "Source lock verification failed or tested a different commit")
    require(source.get("verified_gitlinks") == 160 and source.get("verified_repositories") == 161
            and source.get("verified_lfs_payloads") == 44,
            "Pinned source/dependency coverage differs from accepted P002")
    require(all(source.get(field) == 0 for field in
                ("uninitialized", "mismatched", "conflicted", "dirty_repositories")),
            "Incomplete or dirty source checkout")
    classifications = validate_source_classifications(root, commit)
    unwind = validate_unwind_codegen(root, lock, summary["toolchain_sha256"])
    installations, runtime = [], []
    for name in ("first", "second"):
        install = read(root / f"install-{name}.json")
        require(install.get("status") == "PASSED" and install.get("errors") == []
                and install.get("source_commit") == commit, "Installed implementation audit failed")
        require({item["name"] for item in install["frameworks"]} == set(probes.FRAMEWORKS)
                and len(install["frameworks"]) == len(probes.FRAMEWORKS),
                "Not all required genuine frameworks were audited")
        installations.append(entries(install))
        validate_native(root, name, commit, install)
        require(read(root / f"probes-{name}" / "report.json").get("source_revision") == commit,
                "Probe source revision does not match the tested implementation")
        runtime.append(validate_probes(root / f"probes-{name}", install))
    require(installations[0] == installations[1],
            "Reinstallation changed package contents or borrowed stale installed files")
    uninstall = read(root / "uninstall.json")
    require(uninstall.get("status") == "PASSED" and uninstall.get("prefix_absent") is True,
            "Uninstall did not remove the isolated installation")
    for name, message in (("before", "Build started from dirty source"),
                          ("after", "Build changed source")):
        path = root / f"source-status-{name}.txt"
        require(path.is_file() and not path.is_symlink(),
                f"Missing regular source status evidence: {path.name}")
        require(path.read_bytes() == b"", message)
    for name in ("configure.log", "build.log", "install-first.log", "install-second.log",
                 "CMakeCache.txt", "compile_commands.json", "source-built-linker.json"):
        require((root / name).is_file() and (root / name).stat().st_size > 0,
                f"Required raw build evidence missing: {name}")
    return {"summary": summary, "source": source, "classifications": classifications, "unwind_codegen": unwind,
            "entries": installations[0], "runtime": runtime,
            "evidence": {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*")) if p.is_file()}}


def compare(first: Path, second: Path, commit: str) -> dict:
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Expected exact implementation commit")
    require(first.resolve() != second.resolve(), "Two different build evidence directories are required")
    a, b = campaign(first, commit), campaign(second, commit)
    require({a["summary"].get("build_id"), b["summary"].get("build_id")} == {"a", "b"},
            "Two distinct hosted build identities are required")
    for key in ("toolchain_sha256", "source_lock_sha256", "configuration", "installation_prefix", "source_date_epoch"):
        require(a["summary"][key] == b["summary"][key], f"Build input differs: {key}")
    require(a["source"]["submodules"] == b["source"]["submodules"], "Source pins differ between builds")
    require(set(a["entries"]) == set(b["entries"]), "Installed path sets differ between builds")
    nonces = [x["nonce"] for run in (a, b) for x in run["runtime"]]
    require(len(set(nonces)) == 4, "Runtime lifecycle challenges were reused")
    differences = []
    for path in sorted(a["entries"]):
        left, right = a["entries"][path], b["entries"][path]
        require(left["kind"] == right["kind"] and left["mode"] == right["mode"],
                f"Installed kind/permissions differ: {path}")
        if left["kind"] == "symlink":
            require(left["target"] == right["target"], f"Installed symlink differs: {path}")
        if left != right:
            require(left["kind"] == "file", f"Non-file installation metadata differs: {path}")
            differences.append({"path": path, "first": left, "second": right})
    return {"schema": "darling.p003.comparison.v1", "phase": "P003",
            "status": "READY_FOR_INDEPENDENT_REVIEW", "automated_checks": "PASS",
            "implementation_commit": commit, "toolchain_sha256": a["summary"]["toolchain_sha256"],
            "installed_entries": len(a["entries"]), "runtime_campaigns": 4,
            "asserted_runtime_cases": sum(x["cases"] for run in (a, b) for x in run["runtime"]),
            "byte_identical": not differences, "output_nondeterminism": differences,
            "first_evidence_sha256": a["evidence"], "second_evidence_sha256": b["evidence"],
            "review_requirement": "Independent reviewer must inspect these exact reports, reproduce critical cases, and explain any differing output files before the README phase can pass."}


def validate_independent_review(root: Path, first: Path, second: Path, commit: str) -> dict:
    """Replay the separately authored reviewer's raw package/runtime evidence."""
    package = read(root / "package-review.json")
    installation = read(first / "install-first.json")
    inventory = entries(installation)
    require(package.get("schema") == "darling.p003.package-archive-review.v1"
            and package.get("status") == "PASS" and package.get("errors") == []
            and package.get("source_commit") == commit, "Independent archive review did not pass")
    require(package.get("archive_sha256") == digest(first / "runtime-prefix.tar.gz")
            and package.get("archive_bytes") == (first / "runtime-prefix.tar.gz").stat().st_size
            and package.get("manifest_sha256") == digest(first / "install-first.json")
            and package.get("entry_count") == len(inventory)
            and package.get("destination") == "/opt/darling-p003",
            "Independent review did not unpack the exact verified installation")
    require(package.get("driver_sha256") == digest(Path(__file__).with_name("review_package_archive.py")),
            "Independent archive review used a different driver")
    require(digest(root / "toolchain.lock.json") == digest(first / "toolchain.lock.json"),
            "Independent runtime used a different toolchain")
    runtime = root / "runtime"
    report = read(runtime / "report.json")
    require(report.get("schema") == "darling.p003.independent-runtime.v1"
            and report.get("status") == "PASS" and report.get("passed") is True
            and report.get("errors") == [] and report.get("source_commit") == commit,
            "Independent installed runtime did not pass")
    required_cases = {"macho-known-vector", "macho-fresh-nonce", "macho-boundary-64", "macho-reject-65",
                      "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
                      "foundation-fresh-nonce", "gui-event-roundtrip", "runtime-shutdown"}
    cases = report["cases"]
    require(len(cases) == len(required_cases) and {item["name"] for item in cases} == required_cases
            and all(item["status"] == "PASS" for item in cases), "Independent runtime cases are incomplete")
    require(report.get("stub_diagnostics") == {"enabled": True,
            "environment": {"STUB_VERBOSE": "1"}, "hits": []}, "Independent runtime reached a placeholder")
    nonce = report["nonce"]
    require(re.fullmatch(r"[0-9a-f]{16}", nonce) is not None, "Independent challenge is invalid")
    prior_nonces = {read(folder / f"probes-{name}" / "report.json")["nonce"]
                    for folder in (first, second) for name in ("first", "second")}
    require(nonce not in prior_nonces, "Independent runtime reused an earlier challenge")
    records = {}
    for command in report["commands"]:
        name = command["label"]
        require(name in COMMAND_EXITS and name not in records, "Invalid independent runtime command set")
        require(command.get("exit_code") == COMMAND_EXITS[name]
                and command.get("expected_exit_code") == COMMAND_EXITS[name]
                and command.get("timed_out") is False, f"Independent command failed: {name}")
        out = bound_file(runtime, command["stdout"]).read_text()
        error = bound_file(runtime, command["stderr"]).read_text()
        require(not probes.stub_diagnostics(out) and not probes.stub_diagnostics(error),
                f"Independent runtime raw log contains a placeholder: {name}")
        if COMMAND_EXITS[name] == 0:
            probes.assert_no_probe_errors(out, error)
        if COMMAND_EXITS[name] == 64:
            kind = name.split("-")[0].upper()
            reason = "challenge" if kind == "GUI" else "arguments"
            require([line for line in error.splitlines() if line.startswith("P003_")]
                    == [f"P003_{kind}_ERROR invalid {reason}"]
                    and not any(line.startswith("P003_") for line in out.splitlines()),
                    f"Independent negative case lacked its rejection: {name}")
        records[name] = out
    require(set(records) == set(COMMAND_EXITS), "Independent runtime command evidence is missing")
    host_names = set()
    for command in report["host_commands"]:
        name = command["label"]
        require(name not in host_names and re.fullmatch(r"gui-(?:search-(?:wait|ready)|capture-(?:before|after)-[1-9][0-9]*)", name),
                "Unexpected independent X11 helper command")
        host_names.add(name)
        require(command.get("exit_code") == 0 and command.get("expected_exit_code") == 0
                and command.get("timed_out") is False, "Independent X11 helper failed")
        for stream in ("stdout", "stderr"):
            require(not probes.stub_diagnostics(bound_file(runtime, command[stream]).read_text()),
                    "Independent X11 helper log contains a placeholder")
    require({"gui-search-wait", "gui-search-ready"}.issubset(host_names)
            and any(name.startswith("gui-capture-before-") for name in host_names)
            and any(name.startswith("gui-capture-after-") for name in host_names),
            "Independent visible-window/capture commands are missing")
    for name, value in (("macho-known-vector", "foobar"), ("macho-nonce", nonce),
                        ("macho-boundary-64", "a" * 64)):
        probes.assert_record(records[name], f"P003_MACHO nonce={value} hash={probes.fnv1a(value):08x}")
    probes.assert_record(records["foundation"], f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil")
    probes.assert_record(records["foundation"], f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0")
    probes.assert_record(records["gui"], f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1")
    probes.assert_images(records["gui"])
    for state, ready in (("before", False), ("after", True)):
        reference = report["screenshots"][state]
        raw = bound_file(runtime, reference).read_bytes()
        sample = probes.xwd_sample(raw)
        require(sample == reference["pixels"], "Independent screenshot description differs from pixels")
        probes.assert_colors(sample, ready)
        probes.assert_xwd_coverage(raw, ready)
        assert_xwd_challenge_title(raw, ready, nonce)
        require(bound_file(runtime, reference["png"]).read_bytes() == probes.xwd_png(raw),
                "Independent PNG differs from the original X11 capture")
    require(set(report["binaries"]) == {"p003_macho", "p003_foundation", "p003_gui"},
            "Independent executable identities are missing")
    for name, binary in report["binaries"].items():
        item = inventory["libexec/darling/usr/libexec/p003/" + name]
        require(binary["sha256"] == item["sha256"] and binary["bytes"] == item["size"],
                "Independent runtime used a different executable")
    lifecycle = report["lifecycle"]
    require(lifecycle.get("server_exited") is True and lifecycle.get("mount_namespace_released") is True
            and lifecycle.get("namespace_holders_after") == [], "Independent runtime did not fully stop")
    isolation = report["isolation"]
    require(isolation.get("source_and_build_absent") is True
            and isolation.get("driver_sha256") == digest(Path(__file__).with_name("review_installed_runtime.py")),
            "Independent source isolation or driver identity is missing")
    require(digest(bound_file(runtime, isolation["driver"])) == isolation["driver_sha256"],
            "Archived independent driver differs from the tested source")
    mounts = bound_file(runtime, isolation["mountinfo"]).read_text()
    require(bool(mounts.strip()), "Independent mount namespace evidence is empty")
    allowed_files = {"/p003/review_installed_runtime.py", "/p003/review_package_archive.py"}
    for line in mounts.splitlines():
        fields = line.split()
        require(len(fields) >= 10 and "-" in fields, "Independent mount namespace evidence is invalid")
        separator = fields.index("-")
        require(separator >= 6 and len(fields) == separator + 4
                and fields[0].isdigit() and fields[1].isdigit()
                and re.fullmatch(r"[0-9]+:[0-9]+", fields[2]) is not None,
                "Independent mount namespace evidence has invalid fields")
        locations = [re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[index])
                     for index in (3, 4, separator + 2)]
        require(locations[0].startswith("/") and locations[1].startswith("/"),
                "Independent mount root and mount point must be absolute")
        reviewer_file_only = locations[1] in allowed_files
        for location in locations:
            require(not any(location == forbidden or location.startswith(forbidden + "/")
                            for forbidden in ("/p003/source", "/p003/build")),
                    "Independent runtime retained a source/build mount")
            require(reviewer_file_only or ("/MAC-OS-EMULATION/" not in location
                    and not location.endswith("/MAC-OS-EMULATION")),
                    "Independent runtime retained a repository checkout mount")
    return {"status": "PASS", "source_commit": commit, "nonce": nonce, "cases": len(cases),
            "archive_sha256": package["archive_sha256"],
            "evidence": {str(path.relative_to(root)): digest(path)
                         for path in sorted(root.rglob("*")) if path.is_file()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--independent-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.first, args.second, args.commit)
        review = validate_independent_review(args.independent_review, args.first, args.second, args.commit)
        result["independent_runtime_review"] = review
        result["runtime_campaigns"] += 1
        result["asserted_runtime_cases"] += review["cases"]
        code = 0
    except (OSError, ValueError, KeyError, TypeError, probes.ProbeFailure) as error:
        result = {"schema": "darling.p003.comparison.v1", "phase": "P003", "status": "FAILED",
                  "automated_checks": "FAIL", "implementation_commit": args.commit, "error": str(error)}
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("first_evidence_sha256", "second_evidence_sha256", "output_nondeterminism")}, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
