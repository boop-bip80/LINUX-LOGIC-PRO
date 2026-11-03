#!/usr/bin/env python3
"""Fail-closed P004 phase gate: structural, behavioral and GitHub-run verification.

The collected manifest is *evidence*, not an authority to grant a phase pass.
A green outcome requires real files, real recorded assertions, authenticated
GitHub Actions predecessor and current-job results, and independent reviews.
No flag bypasses online verification in the production CLI.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import urllib.error
import urllib.request

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
POSITIVE = re.compile(r"^[1-9][0-9]*$")
INVENTORY_SCHEMA = "darling.p004.evidence-inventory.v1"
JOB_SCHEMA = "darling.p004.job.v1"


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_json_constant(value):
    raise ValueError("non-finite JSON constant: " + value)


class Findings:
    def __init__(self):
        self.failures: list[str] = []
        self.blockers: list[str] = []
        self.file_hashes: dict[str, tuple[int, str]] = {}
        self.github_checks: list[dict] = []

    def fail(self, message: str) -> None:
        if message not in self.failures:
            self.failures.append(message)

    def block(self, message: str) -> None:
        if message not in self.blockers:
            self.blockers.append(message)

    @property
    def status(self) -> str:
        if self.failures:
            return "FAIL"
        if self.blockers:
            return "BLOCKED"
        return "PASS"

    def report(self, commit: str, phase: str) -> dict:
        return {
            "schema": "darling.p004.gate-result.v1",
            "phase": phase,
            "tested_source_commit": commit,
            "status": self.status,
            "failures": sorted(self.failures),
            "blockers": sorted(self.blockers),
            "github_checks": self.github_checks,
            "checked_file_count": len(self.file_hashes),
            "note": "Only PASS after all predecessor, artifact, behavioral and authenticated GitHub checks."
        }


def object_field(obj, key, label, findings):
    if not isinstance(obj, dict) or key not in obj:
        findings.fail(f"{label}: missing {key}")
        return None
    return obj[key]


def positive_int(value) -> bool:
    return type(value) is int and value > 0


def nonnegative_int(value) -> bool:
    return type(value) is int and value >= 0


def valid_sha(value, pattern=HEX64) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def read_json(path: Path, findings: Findings, label: str, *, missing_block=True):
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=reject_duplicate_keys, parse_constant=reject_json_constant)
    except FileNotFoundError:
        (findings.block if missing_block else findings.fail)(f"{label}: missing {path.name}")
    except (OSError, ValueError, UnicodeError) as exc:
        findings.fail(f"{label}: cannot read JSON ({type(exc).__name__})")
    return None


def safe_file(root: Path, name, findings: Findings, label: str):
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        findings.fail(f"{label}: unsafe path")
        return None
    rel = PurePosixPath(name)
    if rel.is_absolute() or rel.as_posix() != name or any(part in (".", "..", "") for part in rel.parts):
        findings.fail(f"{label}: traversal or absolute path")
        return None
    target = root.joinpath(*rel.parts)
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            findings.fail(f"{label}: symlink not allowed: {name}")
            return None
    if not target.is_file():
        findings.block(f"{label}: absent regular file: {name}")
        return None
    return target


def hash_file(root: Path, name, findings: Findings, label: str):
    target = safe_file(root, name, findings, label)
    if target is None:
        return None
    if name not in findings.file_hashes:
        digest = hashlib.sha256()
        size = 0
        try:
            with target.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
        except OSError as exc:
            findings.fail(f"{label}: unreadable {name}: {type(exc).__name__}")
            return None
        findings.file_hashes[name] = (size, digest.hexdigest())
    return findings.file_hashes[name]


def verify_record(root, record, findings, label, *, size_key="size_bytes"):
    if not isinstance(record, dict):
        findings.fail(f"{label}: expected object")
        return None
    name = record.get("path")
    expected_sha = record.get("sha256")
    expected_size = record.get(size_key)
    if not valid_sha(expected_sha):
        findings.fail(f"{label}: invalid sha256")
    if not nonnegative_int(expected_size):
        findings.fail(f"{label}: missing/invalid {size_key}")
    if not isinstance(name, str):
        findings.fail(f"{label}: missing path")
        return None
    actual = hash_file(root, name, findings, label)
    if actual is not None:
        size, sha = actual
        if size != expected_size:
            findings.fail(f"{label}: byte count mismatch for {name}")
        if sha != expected_sha:
            findings.fail(f"{label}: sha256 mismatch for {name}")
    return name


def validate_inventory(root, inventory, contract, commit, run_id, findings):
    if not isinstance(inventory, dict):
        findings.block("inventory.json: no usable evidence inventory")
        return {}, {}
    for key, wanted in [
        ("schema", INVENTORY_SCHEMA), ("phase", "P004"),
        ("status", "EVIDENCE_INVENTORY_VERIFIED"), ("source_commit", commit),
        ("github_run_id", run_id),
    ]:
        if inventory.get(key) != wanted:
            findings.fail(f"inventory.json: {key} differs from required source/run identity")
    if not positive_int(inventory.get("github_run_attempt")):
        findings.fail("inventory.json: missing GitHub run attempt")
    if not positive_int(inventory.get("retention_days")) or inventory["retention_days"] < contract.get("retention_days_min", 90):
        findings.fail("inventory.json: inadequate artifact retention")
    stages = inventory.get("artifacts")
    if not isinstance(stages, list):
        findings.fail("inventory.json: missing stage inventory")
        return {}, {}
    by_role, listed, count, bytes_total = {}, {}, 0, 0
    for stage in stages:
        if not isinstance(stage, dict):
            findings.fail("inventory.json: non-object stage")
            continue
        role, dirname, files = stage.get("role"), stage.get("path"), stage.get("files")
        if role in by_role:
            findings.fail(f"inventory.json: duplicate role {role}")
            continue
        if not isinstance(role, str) or role not in contract["required_jobs"]:
            findings.fail(f"inventory.json: unexpected role {role}")
            continue
        by_role[role] = stage
        if not isinstance(dirname, str) or "/" in dirname or ".." in dirname:
            findings.fail(f"inventory.json: unsafe stage directory for {role}")
            continue
        if not dirname.startswith("p004-") or not dirname.endswith("-" + commit):
            findings.fail(f"inventory.json: stage directory not SHA-bound for {role}")
        if not isinstance(files, list) or not files:
            findings.block(f"inventory.json: no files for {role}")
            continue
        has_job = False
        for entry in files:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                findings.fail(f"inventory.json: malformed file for {role}")
                continue
            if entry["path"] == "p004-job.json":
                has_job = True
            full = dirname + "/" + entry["path"]
            if full in listed:
                findings.fail(f"inventory.json: duplicate file {full}")
                continue
            record = {"path": full, "sha256": entry.get("sha256"), "size": entry.get("size")}
            verify_record(root, record, findings, f"inventory.{role}", size_key="size")
            listed[full] = (entry.get("sha256"), entry.get("size"), role)
            count += 1
            if nonnegative_int(entry.get("size")):
                bytes_total += entry["size"]
        if not has_job:
            findings.block(f"inventory.json: {role} missing p004-job.json")
    if set(by_role) != set(contract["required_jobs"]):
        findings.block("inventory.json: missing required stage roles: " + ",".join(sorted(set(contract["required_jobs"]) - set(by_role))))
    if inventory.get("file_count") != count or inventory.get("total_bytes") != bytes_total:
        findings.fail("inventory.json: file count or total byte claim incorrect")
    return by_role, listed


def check_assertion(a, findings, label):
    if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"]:
        findings.fail(f"{label}: malformed assertion")
        return
    kind = a.get("kind")
    if kind == "equals":
        if "expected" not in a or "actual" not in a or a["expected"] != a["actual"]:
            findings.fail(f"{label}/{a['id']}: expected result differs from actual")
    elif kind == "not_equals":
        if "expected" not in a or "actual" not in a or a["expected"] == a["actual"]:
            findings.fail(f"{label}/{a['id']}: expected difference missing")
    elif kind == "min_count":
        if not positive_int(a.get("minimum")) or not nonnegative_int(a.get("observed")) or a["observed"] < a["minimum"]:
            findings.fail(f"{label}/{a['id']}: callback/observation count below minimum")
    elif kind == "changed_sha256":
        if not valid_sha(a.get("before_sha256")) or not valid_sha(a.get("after_sha256")) or a["before_sha256"] == a["after_sha256"]:
            findings.fail(f"{label}/{a['id']}: no proven state change")
    else:
        findings.fail(f"{label}/{a['id']}: unknown assertion type {kind}")


def validate_jobs(root, jobs, stages, listed, contract, commit, findings):
    if not isinstance(jobs, list):
        findings.fail("manifest: missing jobs list")
        return
    found = set()
    required = set(contract["required_jobs"])
    for job in jobs:
        if not isinstance(job, dict):
            findings.fail("manifest: non-object job")
            continue
        name = job.get("name")
        if name in found:
            findings.fail(f"manifest: duplicate job {name}")
            continue
        found.add(name)
        if name not in required:
            findings.fail(f"manifest: unknown job {name}")
            continue
        stage = stages.get(name)
        if stage is None:
            findings.block(f"{name}: no stage inventory")
            continue
        stage_job_path = stage["path"] + "/p004-job.json"
        stage_job = read_json(root / stage_job_path, findings, stage_job_path)
        if not isinstance(stage_job, dict):
            continue
        for field in ("schema", "phase", "name", "role", "source_commit", "runner", "status",
                      "discovered", "executed", "passed", "failed", "skipped", "timed_out",
                      "exit_code", "assertions"):
            expected = JOB_SCHEMA if field == "schema" else ("P004" if field == "phase" else name if field in ("name", "role") else job.get(field))
            if stage_job.get(field) != expected:
                findings.fail(f"{name}: stage p004-job.json disagrees on {field}")
        if job.get("status") != "PASS":
            findings.block(f"{name}: status is not PASS ({job.get('status')})")
        if job.get("source_commit") != commit:
            findings.fail(f"{name}: source SHA mismatch")
        if job.get("runner") != "ubuntu-22.04":
            findings.fail(f"{name}: unsupported or unidentified runner")
        discovered, executed, passed = job.get("discovered"), job.get("executed"), job.get("passed")
        if not positive_int(discovered) or not positive_int(executed):
            findings.block(f"{name}: zero/missing discovered or executed assertions")
        elif discovered != executed or passed != executed:
            findings.fail(f"{name}: discovered/executed/passed counts disagree")
        if type(job.get("failed")) is not int or type(job.get("skipped")) is not int or job["failed"] != 0 or job["skipped"] != 0:
            findings.fail(f"{name}: failed or skipped cases")
        if job.get("timed_out") is not False or type(job.get("exit_code")) is not int or job["exit_code"] != 0:
            findings.fail(f"{name}: timed out, cancelled, or nonzero exit")
        assertions = job.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            findings.fail(f"{name}: no behavioral assertions")
        else:
            ids = [a.get("id") for a in assertions if isinstance(a, dict)]
            if len(ids) != len(set(ids)):
                findings.fail(f"{name}: duplicate assertion IDs")
            for a in assertions:
                check_assertion(a, findings, name)
            for required_id in contract.get("required_assertions", {}).get(name, []):
                if required_id not in ids:
                    findings.block(f"{name}: mandatory assertion {required_id} missing")
                else:
                    required_record = next(a for a in assertions if isinstance(a, dict) and a.get("id") == required_id)
                    if (required_record.get("kind") != "equals" or required_record.get("expected") is not True or required_record.get("actual") is not True):
                        findings.fail(f"{name}: mandatory assertion {required_id} must be actual true, not a vacuous equality")
        artifacts = job.get("artifacts")
        expected_paths = {p for p, value in listed.items() if value[2] == name}
        if not isinstance(artifacts, list):
            findings.fail(f"{name}: missing artifacts")
            continue
        actual_paths = set()
        for artifact in artifacts:
            path = verify_record(root, artifact, findings, f"{name}.artifact")
            if path is None:
                continue
            if path in actual_paths:
                findings.fail(f"{name}: duplicate artifact path")
            actual_paths.add(path)
            inv = listed.get(path)
            if inv is None or inv[2] != name:
                findings.fail(f"{name}: artifact not in independent inventory {path}")
            elif artifact.get("sha256") != inv[0] or artifact.get("size_bytes") != inv[1]:
                findings.fail(f"{name}: artifact identity differs from inventory: {path}")
        if actual_paths != expected_paths:
            findings.block(f"{name}: incomplete stage artifact list")
    if found != required:
        findings.block("manifest: missing required jobs " + ",".join(sorted(required - found)))


def valid_review_time(raw):
    if not isinstance(raw, str) or not raw.endswith("Z"):
        return False
    try:
        when = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return when.tzinfo is not None
    except ValueError:
        return False


def github_json(url, token=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "darling-p004-gates"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def github_run_checker(repo, run_id, commit, workflow_path):
    token = os.environ.get("GITHUB_TOKEN")
    obj = github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", token)
    if not isinstance(obj, dict):
        return False, "invalid GitHub Actions response"
    got_repo = (obj.get("repository") or {}).get("full_name")
    if got_repo != repo or obj.get("head_sha") != commit:
        return False, "GitHub Actions run is for another repository/source SHA"
    if obj.get("status") != "completed" or obj.get("conclusion") != "success":
        return False, "GitHub Actions predecessor run did not complete successfully"
    if obj.get("path") != workflow_path:
        return False, "GitHub Actions predecessor workflow path mismatch"
    return True, "authenticated source, workflow and successful conclusion"


def github_jobs_checker(repo, run_id, expected_names):
    token = os.environ.get("GITHUB_TOKEN")
    seen = {}
    page = 1
    while page <= 5:
        obj = github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}", token)
        jobs = obj.get("jobs") if isinstance(obj, dict) else None
        if not isinstance(jobs, list):
            return False, "GitHub Actions job listing unavailable"
        for job in jobs:
            if isinstance(job, dict) and job.get("name") in expected_names:
                seen.setdefault(job["name"], []).append(job)
        if len(jobs) < 100:
            break
        page += 1
    for name in expected_names:
        matching = seen.get(name, [])
        if len(matching) != 1:
            return False, f"missing/ambiguous completed GitHub job: {name}"
        job = matching[0]
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            return False, f"GitHub job did not pass: {name}"
    return True, "all required upstream workflow jobs completed successfully"


def validate_predecessors(root, predecessors, contract, commit, findings, run_checker):
    required = contract["predecessor_phases"]
    if not isinstance(predecessors, list) or len(predecessors) != len(required):
        findings.block("predecessors: incomplete ordered independent acceptance")
        return
    if [p.get("phase") if isinstance(p, dict) else None for p in predecessors] != required:
        findings.fail("predecessors: phase order must be P001 then P002 then P003")
    for p in predecessors:
        if not isinstance(p, dict):
            findings.fail("predecessors: malformed record")
            continue
        phase = p.get("phase")
        if p.get("status") != "PASS":
            findings.block(f"{phase}: not independently accepted")
        if p.get("source_commit") != commit:
            findings.fail(f"{phase}: acceptance belongs to different tested source")
        if not positive_int(p.get("run_id")) or not isinstance(p.get("workflow_path"), str) or not p["workflow_path"].startswith(".github/workflows/"):
            findings.fail(f"{phase}: missing authenticated Actions run identity")
            continue
        if p.get("conclusion") != "success":
            findings.block(f"{phase}: reported Actions conclusion not successful")
        reviewer, author = p.get("reviewer"), p.get("author")
        if not isinstance(reviewer, str) or not reviewer.strip() or not isinstance(author, str) or not author.strip() or reviewer == author:
            findings.fail(f"{phase}: no independent non-author reviewer")
        if not valid_review_time(p.get("reviewed_at")):
            findings.fail(f"{phase}: missing UTC reviewer timestamp")
        verify_record(root, p.get("evidence"), findings, f"{phase}.review")
        try:
            ok, reason = run_checker(contract["repository"], p["run_id"], commit, p["workflow_path"])
            findings.github_checks.append({"phase": phase, "run_id": p["run_id"], "ok": ok, "detail": reason})
            if not ok:
                findings.fail(f"{phase}: {reason}")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            findings.block(f"{phase}: cannot authenticate original Actions run ({type(exc).__name__})")


def validate_faults(root, faults, contract, findings, listed):
    expected = set(contract["required_faults"])
    if not isinstance(faults, list):
        findings.block("fault_matrix: no fault-injection results")
        return
    seen = set()
    for fault in faults:
        if not isinstance(fault, dict):
            findings.fail("fault_matrix: malformed case")
            continue
        ident = fault.get("id")
        if ident in seen or ident not in expected:
            findings.fail(f"fault_matrix: duplicate/unknown case {ident}")
            continue
        seen.add(ident)
        if fault.get("status") != "DETECTED":
            findings.fail(f"fault_matrix/{ident}: deliberate failure escaped detection")
        if not isinstance(fault.get("detector_exit_code"), int) or isinstance(fault.get("detector_exit_code"), bool) or fault.get("detector_exit_code") == 0:
            findings.fail(f"fault_matrix/{ident}: no nonzero detector failure")
        record = fault.get("artifact")
        path = verify_record(root, record, findings, f"fault_matrix/{ident}")
        if path not in listed:
            findings.fail(f"fault_matrix/{ident}: raw trace absent from hashed inventory")
    if seen != expected:
        findings.block("fault_matrix: missing deliberate faults " + ",".join(sorted(expected - seen)))


def validate_document(manifest, inventory, root: Path, contract, commit, *, run_checker=None, jobs_checker=None):
    """Validate data and real hashes. Tests may inject fake GitHub *responses*.

    The command-line path never injects an alternate checker, so an actual
    GitHub Actions response is mandatory for PASS.
    """
    findings = Findings()
    if not isinstance(contract, dict) or contract.get("schema_version") != 1 or contract.get("phase") != "P004":
        findings.fail("contract: unsupported gate contract")
        return findings
    if not isinstance(manifest, dict):
        findings.block("manifest: missing or malformed evidence")
        return findings
    if manifest.get("schema_version") != 1 or manifest.get("phase") != "P004":
        findings.fail("manifest: invalid schema/phase")
    if not valid_sha(commit, HEX40) or manifest.get("source_commit") != commit:
        findings.fail("manifest: source identity is not the exact tested commit")
    publication = manifest.get("evidence_publication_commit")
    if publication is not None and not valid_sha(publication, HEX40):
        findings.fail("manifest: invalid optional documentation publication SHA")
    run_id = manifest.get("run_id")
    if not positive_int(run_id):
        findings.fail("manifest: missing positive GitHub Actions run ID")
    stages, listed = validate_inventory(root, inventory, contract, commit, run_id, findings)
    validate_jobs(root, manifest.get("jobs"), stages, listed, contract, commit, findings)
    validate_faults(root, manifest.get("fault_matrix"), contract, findings, listed)
    validate_predecessors(root, manifest.get("predecessors"), contract, commit, findings, run_checker or github_run_checker)
    if positive_int(run_id):
        try:
            expected_names = list(contract.get("github_job_names", {}).values())
            if len(expected_names) != len(contract.get("required_jobs", [])):
                findings.fail("contract: incomplete GitHub job-name mapping")
            else:
                ok, message = (jobs_checker or github_jobs_checker)(contract["repository"], run_id, expected_names)
                findings.github_checks.append({"phase": "P004", "run_id": run_id, "ok": ok, "detail": message})
                if not ok:
                    findings.fail("P004: " + message)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            findings.block(f"P004: cannot authenticate hosted prerequisite jobs ({type(exc).__name__})")
    return findings


def collect_document(root: Path, inventory, contract, commit, findings):
    """Assemble real stage reports; never invent a PASS when data are absent."""
    manifest = {
        "schema_version": 1, "phase": "P004", "source_commit": commit,
        "run_id": inventory.get("github_run_id") if isinstance(inventory, dict) else None,
        "predecessors": [], "jobs": [], "fault_matrix": []
    }
    if not isinstance(inventory, dict) or not isinstance(inventory.get("artifacts"), list):
        findings.block("collect: inventory missing")
        return manifest
    for stage in inventory["artifacts"]:
        if not isinstance(stage, dict) or stage.get("role") not in contract["required_jobs"]:
            continue
        name = stage["role"]
        dirname = stage.get("path")
        if not isinstance(dirname, str) or "/" in dirname or ".." in dirname:
            findings.fail(f"collect: unsafe stage for {name}")
            continue
        job_path = root / dirname / "p004-job.json"
        job = read_json(job_path, findings, f"collect.{name}")
        if not isinstance(job, dict):
            continue
        job = dict(job)
        job["artifacts"] = []
        for entry in stage.get("files", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                findings.fail(f"collect: invalid file entry in {name}")
                continue
            job["artifacts"].append({
                "path": dirname + "/" + entry["path"],
                "sha256": entry.get("sha256"),
                "size_bytes": entry.get("size"),
            })
        manifest["jobs"].append(job)
    pred = read_json(root / "predecessors.json", findings, "collect.predecessors")
    if isinstance(pred, dict):
        manifest["predecessors"] = pred.get("phases", [])
    elif isinstance(pred, list):
        manifest["predecessors"] = pred
    source_stages = [stage for stage in inventory["artifacts"] if isinstance(stage, dict) and stage.get("role") == "source"]
    if source_stages:
        matrix = read_json(root / source_stages[0]["path"] / "fault-matrix.json", findings, "collect.fault-matrix")
        if isinstance(matrix, list):
            manifest["fault_matrix"] = matrix
        elif isinstance(matrix, dict):
            manifest["fault_matrix"] = matrix.get("cases", [])
    return manifest


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("collect", "validate"):
        cmd = sub.add_parser(action)
        cmd.add_argument("--contract", required=True, type=Path)
        cmd.add_argument("--evidence", required=True, type=Path)
        cmd.add_argument("--commit", required=True)
        cmd.add_argument("--phase", required=True, choices=["P004"])
        cmd.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    findings = Findings()
    contract = read_json(args.contract, findings, "contract", missing_block=False)
    root = args.evidence.resolve()
    if not root.is_dir():
        findings.block("evidence root absent")
    inventory = read_json(root / "inventory.json", findings, "inventory")
    if args.command == "collect":
        manifest = collect_document(root, inventory, contract or {}, args.commit, findings)
        write_json(args.output, manifest)
        print(f"P004 collect: {findings.status}; {len(findings.failures)} failures, {len(findings.blockers)} blockers")
        return 1 if findings.failures else 2 if findings.blockers else 0
    manifest = read_json(root / "manifest.json", findings, "manifest")
    if contract is not None:
        checked = validate_document(manifest, inventory, root, contract, args.commit)
        checked.failures.extend(item for item in findings.failures if item not in checked.failures)
        checked.blockers.extend(item for item in findings.blockers if item not in checked.blockers)
        findings = checked
    write_json(args.output, findings.report(args.commit, args.phase))
    print(f"P004 gate: {findings.status}; {len(findings.failures)} failures, {len(findings.blockers)} blockers")
    for message in findings.failures + findings.blockers:
        print("  " + message, file=sys.stderr)
    return 0 if findings.status == "PASS" else 1 if findings.status == "FAIL" else 2


if __name__ == "__main__":
    sys.exit(main())
