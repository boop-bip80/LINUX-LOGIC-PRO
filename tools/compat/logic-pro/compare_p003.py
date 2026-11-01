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

SHA = re.compile(r"[0-9a-f]{64}")
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


def validate_probes(root: Path, install: dict) -> dict:
    report = read(root / "report.json")
    require(report.get("status") == "PASSED" and report.get("passed") is True
            and report.get("errors") == [], f"Runtime probe campaign did not pass: {root}")
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
    probes.assert_record(records["gui"], f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1")
    probes.assert_images(records["gui"])
    for state, ready in (("before", False), ("after", True)):
        reference = report["screenshots"][state]
        sample = probes.xwd_sample(bound_file(root, reference).read_bytes())
        require(sample == reference["pixels"], "Screenshot metadata differs from actual pixels")
        probes.assert_colors(sample, ready)
        png = bound_file(root, reference["png"])
        require(png.read_bytes() == probes.xwd_png(bound_file(root, reference).read_bytes()),
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
    source = read(root / "source-lock-verification.json")
    require(source.get("result") == "PASS" and source.get("root_commit") == commit,
            "Source lock verification failed or tested a different commit")
    require(source.get("verified_gitlinks") == 160 and source.get("verified_repositories") == 161
            and source.get("verified_lfs_payloads") == 44,
            "Pinned source/dependency coverage differs from accepted P002")
    require(all(source.get(field) == 0 for field in
                ("uninitialized", "mismatched", "conflicted", "dirty_repositories")),
            "Incomplete or dirty source checkout")
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
    require((root / "source-status-before.txt").read_bytes() == b"", "Build started from dirty source")
    for name in ("configure.log", "build.log", "install-first.log", "install-second.log",
                 "CMakeCache.txt", "compile_commands.json", "source-built-linker.json"):
        require((root / name).is_file() and (root / name).stat().st_size > 0,
                f"Required raw build evidence missing: {name}")
    return {"summary": summary, "source": source, "entries": installations[0], "runtime": runtime,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.first, args.second, args.commit)
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
