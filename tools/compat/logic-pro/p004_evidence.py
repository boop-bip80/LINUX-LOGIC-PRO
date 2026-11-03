#!/usr/bin/env python3
"""Inventory *original* P004 hosted artifacts; never declare phase acceptance.

This verifier intentionally does not infer compatibility from an exit code,
a producer's PASS field, or the presence of a report. It inventories the exact
bytes and cross-checks source/run identity and required primary anchors.
The separate P004 gate engine must independently validate behavior, missing
prerequisites, fault injection and non-author acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA = "darling.p004.evidence-inventory.v1"
RETENTION_DAYS = 90
STAGES = {
    "source": ("p004-source-", (
        "p004-job.json", "source-summary.json", "baseline.log", "submodules.log",
        "build.log", "harness.log", "fault-matrix.json")),
    "toolchain": ("p004-toolchain-", (
        "p004-job.json", "toolchain.lock.json", "toolchain-image.tar.gz")),
    "build-a": ("p004-build-a-", (
        "p004-job.json", "build-summary.json", "runtime-prefix.tar.gz",
        "runtime-prefix.sha256", "install-first.json", "install-second.json",
        "probes-first/report.json", "probes-second/report.json")),
    "build-b": ("p004-build-b-", (
        "p004-job.json", "build-summary.json", "runtime-prefix.tar.gz",
        "runtime-prefix.sha256", "install-first.json", "install-second.json",
        "probes-first/report.json", "probes-second/report.json")),
    "independent-runtime": ("p004-runtime-", (
        "p004-job.json", "package-review.json", "runtime/report.json",
        "runtime-summary.json")),
}
PRIVATE_PARTS = {".git", ".ssh", ".aws", ".gnupg", "credentials",
                 "secrets", "license-keys", "proprietary-bundles"}
PRIVATE_SUFFIXES = (".p12", ".pfx", ".mobileprovision", ".privatekey")


class EvidenceError(ValueError):
    """A required artifact or provenance invariant was not satisfied."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        require(key not in out, f"Duplicate JSON field: {key}")
        out[key] = value
    return out


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              EvidenceError(f"Non-finite JSON value: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"Unreadable JSON evidence: {path}: {exc}") from exc
    require(isinstance(data, dict), f"JSON evidence is not an object: {path}")
    return data


def safe_relative(value: str) -> None:
    require(isinstance(value, str) and value and "\0" not in value,
            "Evidence path must be a nonempty string")
    candidate = PurePosixPath(value)
    require(not candidate.is_absolute() and candidate.as_posix() == value
            and not any(part in (".", "..") for part in candidate.parts),
            f"Unsafe evidence path: {value}")
    lowered = [part.lower() for part in candidate.parts]
    require(not any(part in PRIVATE_PARTS for part in lowered)
            and not lowered[-1].endswith(PRIVATE_SUFFIXES),
            f"Non-public or credential-like evidence path: {value}")


def inspect_stage(stage: Path, root: Path) -> list[dict]:
    """Reject symlinks/special files; hash every byte, not only claimed anchors."""
    require(stage.is_dir() and not stage.is_symlink(),
            f"Missing genuine artifact directory: {stage}")
    output = []
    for directory, dirs, files in os.walk(stage, topdown=True, followlinks=False):
        directory_path = Path(directory)
        for name in dirs:
            candidate = directory_path / name
            rel = candidate.relative_to(stage).as_posix()
            safe_relative(rel)
            entry = candidate.lstat()
            require(stat.S_ISDIR(entry.st_mode) and not stat.S_ISLNK(entry.st_mode),
                    f"Unsafe evidence directory: {candidate}")
        for name in files:
            candidate = directory_path / name
            rel = candidate.relative_to(stage).as_posix()
            safe_relative(rel)
            entry = candidate.lstat()
            require(stat.S_ISREG(entry.st_mode) and not stat.S_ISLNK(entry.st_mode)
                    and entry.st_nlink == 1,
                    f"Artifact must be a standalone regular file: {candidate}")
            output.append({"path": rel, "size": entry.st_size, "sha256": digest(candidate)})
    output.sort(key=lambda entry: entry["path"])
    require(output, f"Artifact directory is empty: {stage}")
    require(len({entry["path"] for entry in output}) == len(output),
            f"Duplicate artifact entry: {stage}")
    return output


def confirm_anchor(stage: Path, files: list[dict], name: str) -> Path:
    by_name = {row["path"]: row for row in files}
    require(name in by_name and by_name[name]["size"] > 0,
            f"Required evidence anchor is absent or empty: {stage / name}")
    return stage / name


def validate_stage(role: str, stage: Path, files: list[dict], commit: str) -> None:
    for anchor in STAGES[role][1]:
        confirm_anchor(stage, files, anchor)
    job = read_json(stage / "p004-job.json")
    require(job.get("schema") == "darling.p004.job.v1" and job.get("phase") == "P004"
            and job.get("role") == role and job.get("name") == role
            and job.get("source_commit") == commit,
            f"{role} job is not bound to the exact P004 source and role")
    require(job.get("status") == "PASS" and job.get("exit_code") == 0
            and job.get("timed_out") is False,
            f"{role} did not produce an unambiguous completed job")
    require(isinstance(job.get("assertions"), (dict, list))
            and bool(job["assertions"]),
            f"{role} has no recorded behavioral assertions")
    for name in ("source-summary.json", "build-summary.json", "runtime-summary.json",
                 "runtime/report.json"):
        if name in {row["path"] for row in files}:
            summary = read_json(stage / name)
            require(summary.get("source_commit") == commit,
                    f"Unbound {role} report: {name}")
            require(summary.get("status") == "PASS",
                    f"{role} report has no authentic positive result: {name}")
    by_name = {row["path"]: row for row in files}
    if role == "toolchain":
        lock = read_json(stage / "toolchain.lock.json")
        image = lock.get("image_archive")
        require(isinstance(image, dict) and isinstance(image.get("sha256"), str)
                and DIGEST_RE.fullmatch(image["sha256"]) is not None
                and image["sha256"] == by_name["toolchain-image.tar.gz"]["sha256"],
                "Frozen toolchain image does not match its exact lock")
    if role in ("build-a", "build-b"):
        expected = (stage / "runtime-prefix.sha256").read_text(encoding="utf-8").split()
        require(bool(expected) and DIGEST_RE.fullmatch(expected[0]) is not None
                and expected[0] == by_name["runtime-prefix.tar.gz"]["sha256"],
                f"{role} runtime archive failed its original digest check")
        report = read_json(stage / "build-summary.json")
        require(report.get("status") == "PASS",
                f"{role} real build/install/runtime campaign failed")
    if role == "independent-runtime":
        report = read_json(stage / "runtime/report.json")
        cases = report.get("cases")
        require(isinstance(cases, list) and len(cases) == 10
                and all(isinstance(row, dict) and row.get("status") == "PASS"
                        for row in cases),
                "Independent installed-runtime replay omitted a critical case")


def inventory(artifacts: Path, commit: str, run_id: int, attempt: int) -> dict:
    require(COMMIT_RE.fullmatch(commit) is not None, "Expected full 40-hex tested commit")
    require(type(run_id) is int and run_id > 0 and type(attempt) is int and attempt > 0,
            "GitHub run identity must contain positive integers")
    require(artifacts.is_absolute() and artifacts.is_dir()
            and not artifacts.is_symlink() and artifacts.resolve() == artifacts,
            "Artifact root must be a real canonical absolute directory")
    expected_dirs = {prefix + commit for prefix, _ in STAGES.values()}
    for item in artifacts.iterdir():
        if item.is_dir() or item.is_symlink():
            require(item.name in expected_dirs and not item.is_symlink(),
                    f"Unexpected stage directory or symlink: {item}")
    stages = []
    file_count = total_bytes = 0
    for role, (prefix, _) in STAGES.items():
        dirname = prefix + commit
        stage = artifacts / dirname
        files = inspect_stage(stage, artifacts)
        validate_stage(role, stage, files, commit)
        stages.append({"role": role, "path": dirname, "files": files})
        file_count += len(files)
        total_bytes += sum(row["size"] for row in files)
    return {
        "schema": SCHEMA,
        "phase": "P004",
        "status": "EVIDENCE_INVENTORY_VERIFIED",
        "source_commit": commit,
        "github_run_id": run_id,
        "github_run_attempt": attempt,
        "retention_days": RETENTION_DAYS,
        "artifacts": stages,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "phase_verdict": "NOT_EVALUATED",
        "requires_independent_review": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inventory(args.artifacts, args.commit, args.run_id, args.run_attempt)
        require(args.output.is_absolute() and not args.output.is_symlink()
                and args.output.parent.is_dir(),
                "Receipt target must have an existing real absolute parent directory")
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True,
                                          allow_nan=False) + "\n", encoding="utf-8")
    except (EvidenceError, OSError) as exc:
        print(f"P004 EVIDENCE BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": result["status"],
                      "source_commit": result["source_commit"],
                      "github_run_id": result["github_run_id"],
                      "file_count": result["file_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
