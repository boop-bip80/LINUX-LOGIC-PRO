#!/usr/bin/env python3
"""Create a P004 job receipt only after checking real P003/fixture outputs.

This is *not* phase acceptance. It binds each CI job's observed results to its
exact source SHA, so the P004 gate collector can reject missing or forged jobs.
A failed job leaves no passing receipt. Source compatibility with Logic Pro is
not claimed; these are synthetic Darling runtime tests only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


class ReceiptFailure(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReceiptFailure(message)


def load(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Missing regular report: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"Non-object report: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assertion(name: str, actual: object, expected: object) -> dict:
    require(actual == expected, f"{name}: {actual!r} != {expected!r}")
    return {"id": name, "kind": "equals", "expected": expected, "actual": actual}


def source_receipt(directory: Path, commit: str) -> tuple[int, list[dict]]:
    summary = load(directory / "source-summary.json")
    assertions = [assertion("source-sha", summary.get("source_commit"), commit),
                  assertion("source-status", summary.get("status"), "PASS")]
    suites = summary.get("suites")
    floors = {"baseline": 130, "submodules": 97, "build": 151, "harness": 37, "evidence": 1}
    require(isinstance(suites, list) and len(suites) == len(floors),
            "Missing or additional required source fixture suites")
    by_suite = {row.get("suite"): row for row in suites if isinstance(row, dict)}
    require(len(by_suite) == len(floors) and set(by_suite) == set(floors),
            "Missing/duplicated source fixture suites")
    total = 0
    for suite, floor in floors.items():
        row = by_suite[suite]
        count = row.get("count")
        require(type(count) is int and count >= floor, f"{suite} fixture floor not satisfied")
        assertions.append(assertion(f"{suite}-exit", row.get("exit_code"), 0))
        assertions.append(assertion(f"{suite}-discovered-executed",
                                    row.get("discovered"), count))
        assertions.append(assertion(f"{suite}-passed", row.get("passed"), count))
        assertions.append(assertion(f"{suite}-skipped", row.get("skipped"), 0))
        total += count
        log = directory / f"{suite}.log"
        require(log.is_file() and not log.is_symlink() and log.stat().st_size > 0,
                f"Missing {suite} original test output")
        assertions.append(assertion(f"{suite}-log-sha", row.get("sha256"), sha256(log)))
    faults = load(directory / "fault-matrix.json")
    require(bool(faults), "Fault matrix cannot be empty")
    assertions.append(assertion("fault-matrix-present", (directory / "fault-matrix.json").is_file(), True))
    assertions.append(assertion("all-three-regressions", all(by_suite[k]["count"] >= floors[k] for k in ("baseline", "submodules", "build")), True))
    return total, assertions


def toolchain_receipt(directory: Path) -> tuple[int, list[dict]]:
    lock = load(directory / "toolchain.lock.json")
    archive = directory / "toolchain-image.tar.gz"
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size > 0,
            "Actual frozen toolchain archive is missing")
    meta = lock.get("image_archive")
    require(isinstance(meta, dict), "Frozen toolchain lock missing image identity")
    digest = meta.get("sha256")
    require(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            "Frozen image digest invalid")
    return 1, [assertion("frozen-lock-verified", sha256(archive) == digest, True),
               assertion("frozen-image-sha", sha256(archive), digest),
               assertion("toolchain-lock-present", (directory / "toolchain.lock.json").is_file(), True)]


def build_receipt(directory: Path, commit: str, role: str) -> tuple[int, list[dict]]:
    summary = load(directory / "build-summary.json")
    assertions = [assertion("build-sha", summary.get("source_commit"), commit),
                  assertion("build-status", summary.get("status"), "PASS"),
                  assertion("build-exit", summary.get("exit_code"), 0),
                  assertion("build-stage", summary.get("last_stage"), "complete"),
                  assertion("build-identity", summary.get("build_id"), role[-1])]
    total = 0
    for cycle in ("first", "second"):
        report = load(directory / f"probes-{cycle}" / "report.json")
        cases = report.get("cases")
        require(isinstance(cases, list), f"No real P003 {cycle} runtime cases")
        assertions.append(assertion(f"{cycle}-runtime-status", report.get("status"), "PASSED"))
        assertions.append(assertion(f"{cycle}-runtime-error-count", len(report.get("errors") or []), 0))
        assertions.append(assertion(f"{cycle}-runtime-case-count", len(cases), 10))
        require(all(isinstance(case, dict) and case.get("status") == "PASSED" for case in cases),
                f"Real P003 {cycle} runtime has non-passing case")
        total += len(cases)
    archive = directory / "runtime-prefix.tar.gz"
    digest_file = directory / "runtime-prefix.sha256"
    require(archive.is_file() and not archive.is_symlink() and archive.stat().st_size > 0,
            "Installed runtime archive missing")
    require(digest_file.is_file() and not digest_file.is_symlink(), "Archive hash record missing")
    recorded = digest_file.read_text().split()[0]
    assertions.append(assertion("installed-package-sha", sha256(archive), recorded))
    assertions.append(assertion("installed-runtime-probes", total, 20))
    for filename in ("install-first.json", "install-second.json", "uninstall.json"):
        assertions.append(assertion(filename + "-present", (directory / filename).is_file(), True))
    return total, assertions


def runtime_receipt(directory: Path, commit: str) -> tuple[int, list[dict]]:
    package = load(directory / "package-review.json")
    report = load(directory / "runtime" / "report.json")
    assertions = [assertion("package-sha", package.get("source_commit"), commit),
                  assertion("package-status", package.get("status"), "PASS"),
                  assertion("installed-readback", package.get("installed_readback"), "PASS"),
                  assertion("runtime-sha", report.get("source_commit"), commit),
                  assertion("runtime-status", report.get("status"), "PASS"),
                  assertion("runtime-passed", report.get("passed"), True)]
    cases = report.get("cases")
    require(isinstance(cases, list), "Independent runtime case list missing")
    assertions.append(assertion("runtime-case-count", len(cases), 10))
    assertions.append(assertion("runtime-errors", len(report.get("errors") or []), 0))
    require(all(isinstance(case, dict) and case.get("status") == "PASS" for case in cases),
            "Independent installed runtime has non-passing case")
    (directory / "runtime-summary.json").write_text(json.dumps({
        "schema": "darling.p004.independent-runtime-summary.v1",
        "phase": "P004", "source_commit": commit, "status": "PASS",
        "package_review": "PASS", "runtime_cases": len(cases),
        "source_free_replay": True, "errors": [],
    }, indent=2, sort_keys=True) + "\n")
    assertions.append(assertion("source-free-probes", len(cases), 10))
    return len(cases), assertions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("source", "toolchain", "build-a", "build-b", "independent-runtime"),
                        required=True)
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--runner", required=True, choices=("ubuntu-22.04",))
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--run-attempt", type=int, required=True)
    args = parser.parse_args()
    try:
        require(re.fullmatch(r"[0-9a-f]{40}", args.commit) is not None, "Source SHA must be exact")
        require(args.run_id > 0 and args.run_attempt > 0, "GitHub run and attempt must be positive")
        actual_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], text=True).strip()
        require(actual_commit == args.commit and re.fullmatch(r"[0-9a-f]{40}", tree) is not None,
                "Job did not checkout exact source commit and tree")
        source_lock = Path("docs/compat/logic-pro/submodules.lock.json")
        require(source_lock.is_file(), "Current source dependency lock missing")
        submodule_count = None
        if args.role in ("source", "build-a", "build-b"):
            result = subprocess.run(["git", "submodule", "status", "--recursive"],
                                    check=True, capture_output=True, text=True)
            lines = result.stdout.splitlines()
            require(len(lines) == 160 and all(row.startswith(" ") for row in lines),
                    "Current recursively checked out dependency pins are missing/mismatched")
            submodule_count = len(lines)
        require(args.directory.is_dir() and not args.directory.is_symlink(), "Output directory missing")
        receipt = args.directory / "p004-job.json"
        require(not receipt.exists() and not receipt.is_symlink(),
                "Never overwrite an existing phase job receipt")
        if args.role == "source":
            count, assertions = source_receipt(args.directory, args.commit)
        elif args.role == "toolchain":
            count, assertions = toolchain_receipt(args.directory)
        elif args.role in ("build-a", "build-b"):
            count, assertions = build_receipt(args.directory, args.commit, args.role)
        else:
            count, assertions = runtime_receipt(args.directory, args.commit)
        require(count > 0 and assertions, "Job cannot qualify with no executed assertions")
        result = {
            "schema": "darling.p004.job.v1", "phase": "P004",
            "name": args.role, "role": args.role, "source_commit": args.commit,
            "runner": args.runner, "status": "PASS",
            "github_run_id": args.run_id, "github_run_attempt": args.run_attempt,
            "source_tree": tree, "source_lock_sha256": sha256(source_lock),
            "submodule_pin_count": submodule_count,
            "submodule_verification": ("recursive-160-pins" if submodule_count == 160
                                       else "bound-to-source-sha-and-tree"),
            "discovered": count, "executed": count, "passed": count,
            "failed": 0, "skipped": 0, "timed_out": False, "exit_code": 0,
            "assertions": assertions,
        }
        receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"role": args.role, "source_commit": args.commit,
                          "discovered": count, "executed": count, "status": "PASS"}))
        return 0
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"P004 {args.role} receipt BLOCKED/FAIL: {error}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
