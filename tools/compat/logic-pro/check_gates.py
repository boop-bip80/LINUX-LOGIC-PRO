#!/usr/bin/env python3
"""Fail-closed P004 phase gate: structural, behavioral and GitHub-run verification.

The collected manifest is *evidence*, not an authority to grant a phase pass.
A green outcome requires real files, real recorded assertions, authenticated
GitHub Actions predecessor and current-job results, and independent reviews.
No flag bypasses online verification in the production CLI.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile
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
            "phase_acceptance": "READY FOR REVIEW" if self.status == "PASS" else "NOT ACCEPTED",
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
    if not valid_sha(inventory.get("source_tree"), HEX40):
        findings.fail("inventory.json: missing authentic checked-out source tree")
    if not valid_sha(inventory.get("source_lock_sha256")):
        findings.fail("inventory.json: missing checked-out recursive source lock SHA")
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
        for field in ("schema", "phase", "name", "role", "source_commit", "publication_commit", "runner", "status",
                      "discovered", "executed", "passed", "failed", "skipped", "timed_out",
                      "exit_code", "assertions", "source_tree", "source_lock_sha256",
                      "github_run_id", "github_run_attempt"):
            expected = JOB_SCHEMA if field == "schema" else ("P004" if field == "phase" else name if field in ("name", "role") else job.get(field))
            if stage_job.get(field) != expected:
                findings.fail(f"{name}: stage p004-job.json disagrees on {field}")
        if job.get("status") != "PASS":
            findings.block(f"{name}: status is not PASS ({job.get('status')})")
        if job.get("source_commit") != commit:
            findings.fail(f"{name}: source SHA mismatch")
        if job.get("source_tree") != findings.expected_source_tree:
            findings.fail(f"{name}: source tree differs from authenticated inventory")
        if not valid_sha(job.get("source_lock_sha256")) or job.get("source_lock_sha256") != findings.expected_source_lock:
            findings.fail(f"{name}: recursive dependency lock differs from independently audited inventory")
        if job.get("publication_commit") != findings.expected_publication_commit:
            findings.fail(f"{name}: stage source was produced for another documentation publication")
        if job.get("github_run_id") != findings.expected_run_id or job.get("github_run_attempt") != findings.expected_run_attempt:
            findings.fail(f"{name}: stage receipt belongs to another workflow run/attempt")
        if job.get("runner") != "ubuntu-22.04":
            findings.fail(f"{name}: unsupported or unidentified runner")
        discovered, executed, passed = job.get("discovered"), job.get("executed"), job.get("passed")
        minimum = contract.get("minimum_job_counts", {}).get(name, 1)
        if not positive_int(discovered) or not positive_int(executed) or discovered < minimum:
            findings.block(f"{name}: missing/insufficient actual discovered or executed assertions")
        elif type(passed) is not int or discovered != executed or passed != executed:
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
                    oracle = contract.get("required_assertion_expected", {}).get(name, {}).get(required_id)
                    if (oracle is None or required_record.get("kind") != "equals"
                            or type(required_record.get("expected")) is not type(oracle)
                            or type(required_record.get("actual")) is not type(oracle)
                            or required_record.get("expected") != oracle or required_record.get("actual") != oracle):
                        findings.fail(f"{name}: mandatory assertion {required_id} failed frozen typed oracle")
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




P003_INSTALLED_CASES = {
    "macho-known-vector", "macho-nonce", "macho-boundary-64", "macho-reject-65",
    "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-objects", "gui-event-roundtrip", "runtime-shutdown",
}
P003_SOURCE_FREE_CASES = {
    "macho-known-vector", "macho-fresh-nonce", "macho-boundary-64", "macho-reject-65",
    "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-fresh-nonce", "gui-event-roundtrip", "runtime-shutdown",
}


def assert_p003_runtime_report(report, required_cases, expected_status, findings, label):
    cases = report.get("cases")
    if not isinstance(cases, list) or len(cases) != 10 or any(not isinstance(c, dict) for c in cases):
        findings.fail(f"{label}: ten original real cases not evidenced")
        return
    names = [c.get("name") for c in cases]
    if set(names) != required_cases or len(set(names)) != 10:
        findings.fail(f"{label}: wrong/duplicate P003 case IDs substituted for required behavior")
    if any(c.get("status") != expected_status for c in cases):
        findings.fail(f"{label}: one or more original P003 cases not successful")
    if report.get("passed") is not True or report.get("errors") != []:
        findings.fail(f"{label}: original P003 runtime errors or false pass")
    diagnostics = report.get("stub_diagnostics")
    if not isinstance(diagnostics, dict) or diagnostics.get("enabled") is not True or diagnostics.get("hits") != []:
        findings.fail(f"{label}: reached generic success/null stubs or no active stub scanner")
    lifecycle = report.get("lifecycle")
    if (not isinstance(lifecycle, dict) or lifecycle.get("server_exited") is not True
            or lifecycle.get("mount_namespace_released") is not True
            or lifecycle.get("namespace_holders_after") != []):
        findings.fail(f"{label}: true Darling server and namespace teardown not demonstrated")
    screenshots = report.get("screenshots")
    if not isinstance(screenshots, dict):
        findings.fail(f"{label}: missing original asserted GUI pixel evidence")
        return
    before = (screenshots.get("before") or {}).get("png")
    after = (screenshots.get("after") or {}).get("png")
    if not isinstance(before, dict) or not isinstance(after, dict):
        findings.fail(f"{label}: missing original before/after rendered PNGs")
        return
    left, right = before.get("sha256"), after.get("sha256")
    if not valid_sha(left) or not valid_sha(right) or left == right:
        findings.fail(f"{label}: no authentic pixel-state transition after external input")


def validate_raw_stages(root, stages, listed, contract, commit, findings):
    """Check real stage outputs instead of trusting receipt assertions alone."""
    def file_for(role, relative):
        stage = stages.get(role)
        if not isinstance(stage, dict) or not isinstance(stage.get("path"), str):
            findings.block(f"{role}: missing stage")
            return None, None
        path = stage["path"] + "/" + relative
        if path not in listed or listed[path][2] != role:
            findings.block(f"{role}: required raw evidence not inventoried: {relative}")
            return None, None
        return path, root / path

    def json_for(role, relative):
        path, absolute = file_for(role, relative)
        if absolute is None:
            return None
        return read_json(absolute, findings, f"{role}/{relative}")

    source = json_for("source", "source-summary.json")
    floors = {"baseline": 130, "submodules": 97, "build": 151, "harness": 41, "evidence": 28}
    if isinstance(source, dict):
        if (source.get("schema") != "darling.p004.source-suites.v1"
                or source.get("phase") != "P004" or source.get("source_commit") != commit):
            findings.fail("source-summary: schema/phase/source SHA mismatch")
        suites = source.get("suites")
        if not isinstance(suites, list):
            findings.block("source-summary: no discovered/executed suites")
        else:
            seen = set()
            for suite in suites:
                if not isinstance(suite, dict) or suite.get("suite") not in floors:
                    findings.fail("source-summary: unknown/invalid suite")
                    continue
                name = suite["suite"]
                if name in seen:
                    findings.fail(f"source-summary: duplicate {name} suite")
                seen.add(name)
                count = suite.get("count")
                discovered = suite.get("discovered")
                passed = suite.get("passed")
                if (not positive_int(count) or count < floors[name] or discovered != count
                        or passed != count or type(passed) is not int or suite.get("skipped") != 0
                        or type(suite.get("skipped")) is not int or suite.get("exit_code") != 0
                        or type(suite.get("exit_code")) is not int):
                    findings.fail(f"source-summary: {name} missing required real test coverage")
                path, _ = file_for("source", name + ".log")
                if path is not None:
                    observed = findings.file_hashes.get(path)
                    if observed is None or observed[1] != suite.get("sha256"):
                        findings.fail(f"source-summary: {name} log hash not bound to original suite")
                    else:
                        try:
                            transcript = (root / path).read_text("utf-8")
                            summaries = re.findall(r"(?m)^Ran ([0-9]+) tests? in [^\n]+$", transcript)
                            terminal = re.search(r"(?:^|\n)Ran ([1-9][0-9]*) tests? in [^\n]+\n\nOK\s*\Z", transcript)
                            announcements = re.findall(r"(?m)^(test\S+ \([^\n)]+\) \.\.\.)", transcript)
                            if (len(summaries) != 1 or terminal is None
                                    or int(terminal.group(1)) != count
                                    or int(summaries[0]) != count
                                    or len(announcements) != count
                                    or len(set(announcements)) != count):
                                findings.fail(f"source-summary: {name} raw unittest transcript incomplete/forged/skipped")
                        except (OSError, UnicodeError, ValueError):
                            findings.fail(f"source-summary: {name} raw transcript unreadable")
            if seen != set(floors):
                findings.block("source-summary: required suite missing " + ",".join(sorted(set(floors) - seen)))

    lock = json_for("toolchain", "toolchain.lock.json")
    image_path, _ = file_for("toolchain", "toolchain-image.tar.gz")
    lock_sha = None
    if isinstance(lock, dict):
        expected_image = (lock.get("image_archive") or {}).get("sha256")
        if not valid_sha(expected_image):
            findings.fail("toolchain: frozen image SHA missing")
        elif image_path is not None and findings.file_hashes.get(image_path, (0, None))[1] != expected_image:
            findings.fail("toolchain: archived frozen image differs from pinned lock")
    lock_path, _ = file_for("toolchain", "toolchain.lock.json")
    if lock_path is not None and lock_path in findings.file_hashes:
        lock_sha = findings.file_hashes[lock_path][1]

    for role, build_id in (("build-a", "a"), ("build-b", "b")):
        summary = json_for(role, "build-summary.json")
        if isinstance(summary, dict):
            if (summary.get("schema") != "darling.p003.build.v1"
                    or summary.get("phase") != "P003"
                    or summary.get("source_commit") != commit
                    or summary.get("build_id") != build_id
                    or summary.get("status") != "PASS"
                    or summary.get("last_stage") != "complete"
                    or summary.get("exit_code") != 0):
                findings.fail(f"{role}: actual P003 build did not finish successfully")
            if lock_sha is not None and summary.get("toolchain_sha256") != lock_sha:
                findings.fail(f"{role}: build used a different toolchain")
        for cycle in ("first", "second"):
            report = json_for(role, f"probes-{cycle}/report.json")
            if not isinstance(report, dict):
                continue
            if report.get("status") != "PASSED" or report.get("source_revision") != commit:
                findings.fail(f"{role}: {cycle} installed runtime not qualified")
            assert_p003_runtime_report(report, P003_INSTALLED_CASES, "PASSED", findings, f"{role}: {cycle}")
        archive_path, _ = file_for(role, "runtime-prefix.tar.gz")
        marker_path, marker_abs = file_for(role, "runtime-prefix.sha256")
        if archive_path is not None and marker_abs is not None:
            try:
                expected = marker_abs.read_text("utf-8").strip().split()[0]
            except (OSError, IndexError, UnicodeError):
                expected = None
            actual = findings.file_hashes.get(archive_path, (0, None))[1]
            if not valid_sha(expected) or expected != actual:
                findings.fail(f"{role}: installed package hash not reproducible")
        file_for(role, "install-first.json")
        file_for(role, "install-second.json")

    summary = json_for("independent-runtime", "runtime-summary.json")
    if isinstance(summary, dict):
        if (summary.get("schema") != "darling.p004.independent-runtime-summary.v1"
                or summary.get("phase") != "P004" or summary.get("source_commit") != commit
                or summary.get("status") != "PASS" or summary.get("package_review") != "PASS"
                or summary.get("runtime_cases") != 10
                or summary.get("source_free_replay") is not True or summary.get("errors") != []):
            findings.fail("independent-runtime: replay did not pass all expected behaviors")
    package = json_for("independent-runtime", "package-review.json")
    if isinstance(package, dict) and package.get("status") not in ("PASS", "PASSED"):
        findings.fail("independent-runtime: package review did not pass")
    report = json_for("independent-runtime", "runtime/report.json")
    if isinstance(report, dict):
        if report.get("source_commit") != commit or report.get("status") not in ("PASS", "PASSED"):
            findings.fail("independent-runtime: original real runtime report not accepted")
        assert_p003_runtime_report(report, P003_SOURCE_FREE_CASES, "PASS", findings, "independent-runtime")

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


def github_run_checker(repo, run_id, commit, workflow_path, expected_job_names):
    token = os.environ.get("GITHUB_TOKEN")
    obj = github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", token)
    if not isinstance(obj, dict):
        return False, "invalid GitHub Actions response"
    if ((obj.get("repository") or {}).get("full_name") != repo or obj.get("head_sha") != commit
            or obj.get("path") != workflow_path):
        return False, "predecessor Actions run is for another repo/source/workflow"
    if obj.get("status") != "completed" or obj.get("conclusion") != "success":
        return False, "predecessor Actions run did not complete successfully"
    if obj.get("event") != "push" or obj.get("head_branch") != "master":
        return False, "predecessor was not qualified on the master push"
    observed = read_github_jobs(repo, run_id, expected_job_names, token)
    return observed


def read_github_jobs(repo, run_id, expected_names, token):
    seen = {}
    for page in range(1, 6):
        obj = github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}", token)
        jobs = obj.get("jobs") if isinstance(obj, dict) else None
        if not isinstance(jobs, list):
            return False, "GitHub Actions job listing unavailable"
        for job in jobs:
            if isinstance(job, dict) and job.get("name") in expected_names:
                seen.setdefault(job["name"], []).append(job)
        if len(jobs) < 100:
            break
    for name in expected_names:
        matching = seen.get(name, [])
        if len(matching) != 1:
            return False, f"missing/ambiguous hosted job: {name}"
        if matching[0].get("status") != "completed" or matching[0].get("conclusion") != "success":
            return False, f"hosted prerequisite failed/skipped: {name}"
    return True, "all required named GitHub Actions jobs completed successfully"


def verify_original_zip(repo, artifact_id, digest_text, stage, listed, token, *, expected_members=None):
    """Download the authentic uploaded ZIP and independently verify every entry."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "darling-p004-original-artifact"}
        | ({"Authorization": "Bearer " + token} if token else {}),
    )
    with tempfile.TemporaryFile(mode="w+b") as temporary:
        digest = hashlib.sha256()
        with urllib.request.urlopen(request, timeout=120) as response:
            for part in iter(lambda: response.read(1024 * 1024), b""):
                digest.update(part)
                temporary.write(part)
        if digest.hexdigest() != digest_text[7:]:
            return False, f"original ZIP SHA-256 mismatch for {stage['role']}"
        temporary.seek(0)
        expected = (expected_members if expected_members is not None else {
            p[len(stage["path"]) + 1:]: (sha, size)
            for p, (sha, size, role) in listed.items()
            if role == stage["role"] and p.startswith(stage["path"] + "/")
        })
        if not expected:
            return False, f"no expected original ZIP members for {stage['role']}"
        seen, seen_directories = set(), set()
        try:
            with zipfile.ZipFile(temporary, "r") as archive:
                for member in archive.infolist():
                    name = member.filename
                    if name.startswith(stage["path"] + "/"):
                        name = name[len(stage["path"]) + 1:]
                    is_directory = member.is_dir()
                    # ZIPs are never extracted, but also cannot conceal a
                    # traversal, symlink, special inode, or unrelated directory.
                    raw_path = name[:-1] if is_directory and name.endswith("/") else name
                    pure = PurePosixPath(raw_path)
                    mode = (member.external_attr >> 16) & 0o170000
                    if (not raw_path or "\\" in raw_path or pure.is_absolute()
                            or pure.as_posix() != raw_path
                            or any(part in (".", "..") for part in pure.parts)):
                        return False, f"unsafe original ZIP entry: {name}"
                    if is_directory:
                        if mode not in (0, 0o040000) or raw_path in seen_directories:
                            return False, f"special/duplicate original ZIP directory: {name}"
                        if not any(path.startswith(raw_path + "/") for path in expected):
                            return False, f"unlisted original ZIP directory: {name}"
                        seen_directories.add(raw_path)
                        continue
                    if (mode not in (0, 0o100000)
                            or name in seen or name not in expected):
                        return False, f"unexpected, duplicate or nonregular ZIP member: {name}"
                    if member.file_size != expected[name][1]:
                        return False, f"original ZIP member byte count changed: {name}"
                    seen.add(name)
                    observed_digest = hashlib.sha256()
                    observed_size = 0
                    with archive.open(member) as reader:
                        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                            observed_digest.update(chunk)
                            observed_size += len(chunk)
                    if (observed_size, observed_digest.hexdigest()) != (expected[name][1], expected[name][0]):
                        return False, f"original Actions ZIP member changed since upload: {name}"
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError):
            return False, f"corrupt original ZIP archive for {stage['role']}"
        if seen != set(expected):
            return False, f"original uploaded ZIP omits required stage files for {stage['role']}"
    return True, f"original uploaded ZIP/member hashes verified: {stage['role']}"


def github_jobs_checker(repo, run_id, expected_names, commit, publication_commit, attempt, stages, listed):
    """Prove source A, documentation publication B, and original artifacts all agree."""
    token = os.environ.get("GITHUB_TOKEN")
    run = github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", token)
    if ((run.get("repository") or {}).get("full_name") != repo
            or run.get("head_sha") != publication_commit
            or run.get("path") != ".github/workflows/compat.yml"
            or run.get("run_attempt") != attempt):
        return False, "current Actions run differs from exact publication source/workflow/attempt"
    if run.get("event") != "push" or run.get("head_branch") != "master":
        return False, "only the exact master-branch publication push can qualify P004"
    if run.get("status") not in ("completed", "in_progress") or run.get("conclusion") not in (None, "success"):
        return False, "current Actions run failed or never executed"
    ok, message = read_github_jobs(repo, run_id, list(expected_names) + ["resolve"], token)
    if not ok:
        return ok, message
    aliases = {"independent-runtime": "runtime"}
    wanted = {"p004-" + aliases.get(role, role) + "-" + commit: role for role in stages}
    wanted["p004-resolver-" + publication_commit] = "resolver"
    uploaded = {}
    for page in range(1, 6):
        data = github_json(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100&page={page}", token)
        items = data.get("artifacts") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return False, "original uploaded GitHub artifacts unavailable"
        for item in items:
            if isinstance(item, dict) and item.get("name") in wanted:
                uploaded.setdefault(item["name"], []).append(item)
        if len(items) < 100:
            break
    for name, role in wanted.items():
        matches = uploaded.get(name, [])
        if len(matches) != 1:
            return False, f"missing/ambiguous uploaded Actions artifact {name}"
        art = matches[0]
        digest_text = art.get("digest")
        if (art.get("expired") is not False or not positive_int(art.get("size_in_bytes"))
                or not positive_int(art.get("id")) or not isinstance(digest_text, str)
                or not digest_text.startswith("sha256:") or not valid_sha(digest_text[7:])):
            return False, f"GitHub artifact {name} lacks original hash/size/retention"
        if role == "resolver":
            original_source = stages.get("source")
            if not isinstance(original_source, dict):
                return False, "resolver proof cannot be bound without original source stage"
            proof = listed.get(original_source["path"] + "/source-equivalence.json")
            if proof is None or proof[2] != "source":
                return False, "original source stage omitted resolver-equivalence proof"
            proof_stage = {"role": "resolver", "path": "p004-resolver-" + publication_commit}
            valid, detail = verify_original_zip(
                repo, art["id"], digest_text, proof_stage, listed, token,
                expected_members={"source-equivalence.json": (proof[0], proof[1])},
            )
        else:
            valid, detail = verify_original_zip(repo, art["id"], digest_text, stages[role], listed, token)
        if not valid:
            return False, detail
    return True, "exact publication SHA/attempt, all completed jobs and original artifact ZIP/member bytes verified"



def verify_source_equivalence(root, manifest, contract, commit, listed, findings):
    """A tested source A may be published at B only for independently proven docs-only delta."""
    publication = manifest.get("evidence_publication_commit") or commit
    if not valid_sha(publication, HEX40):
        findings.fail("source-equivalence: publication SHA invalid")
        return commit
    record = manifest.get("source_equivalence")
    if publication == commit:
        if record is not None:
            path = verify_record(root, record, findings, "source-equivalence.candidate")
            if path not in listed or listed[path][2] != "source":
                findings.fail("source-equivalence: candidate report not hash-bound to source stage")
            else:
                candidate = read_json(root / path, findings, "source-equivalence.candidate")
                if not isinstance(candidate, dict) or candidate.get("status") != "CANDIDATE_ONLY":
                    findings.fail("source-equivalence: unexpected same-source proof status")
                findings.block("source-equivalence: preliminary A==B candidate is not final independent acceptance")
        return publication
    path = verify_record(root, record, findings, "source-equivalence.proof")
    if path not in listed or listed[path][2] != "source":
        findings.fail("source-equivalence: proof not in original source-stage artifact")
        return publication
    raw = read_json(root / path, findings, "source-equivalence.proof")
    if not isinstance(raw, dict):
        return publication
    if (raw.get("schema_version") != 1 or raw.get("phase") != "P004"
            or raw.get("status") != "PASS" or raw.get("tested_commit") != commit
            or raw.get("publication_commit") != publication or raw.get("ancestor_verified") is not True
            or raw.get("code_tree_identical") is not True or raw.get("failures") != []):
        findings.fail("source-equivalence: source equivalence report did not pass")
    history_count = raw.get("intermediate_commits_verified")
    recorded_history = raw.get("publication_history")
    if (type(history_count) is not int or history_count < 1
            or not isinstance(recorded_history, list) or history_count != len(recorded_history)):
        findings.fail("source-equivalence: incomplete intermediate commit history verification")
    if (not valid_sha(raw.get("tested_tree_sha"), HEX40)
            or not valid_sha(raw.get("publication_tree_sha"), HEX40)
            or not valid_sha(raw.get("code_tree_manifest_sha256"))):
        findings.fail("source-equivalence: missing distinct source/tree identity and full code manifest")
    changes = raw.get("allowed_documentation_changes")
    if not isinstance(changes, list) or raw.get("change_count") != len(changes):
        findings.fail("source-equivalence: malformed documentation delta")
        return publication
    reviewed_paths = {}
    for item in changes:
        if not isinstance(item, dict):
            findings.fail("source-equivalence: malformed changed file")
            continue
        name = item.get("path")
        valid_path = (name == "README.md"
                      or (isinstance(name, str)
                          and re.fullmatch(r"docs/compat/logic-pro/evidence/P004/[^/]+\.json", name)))
        if (not valid_path or item.get("change") not in ("added", "modified")
                or item.get("mode") != "100644"
                or not valid_sha(item.get("blob_sha1"), HEX40)
                or not valid_sha(item.get("sha256"))
                or not nonnegative_int(item.get("bytes")) or name in reviewed_paths):
            findings.fail(f"source-equivalence: change outside exact documentation allowlist: {name}")
        reviewed_paths[name] = item
    try:
        token = os.environ.get("GITHUB_TOKEN")
        repo = contract["repository"]
        comparison = github_json(f"https://api.github.com/repos/{repo}/compare/{commit}...{publication}", token)
        changed = comparison.get("files")
        if (comparison.get("status") != "ahead"
                or (comparison.get("base_commit") or {}).get("sha") != commit
                or (comparison.get("merge_base_commit") or {}).get("sha") != commit
                or not isinstance(changed, list) or len(changed) >= 300
                or len(changed) != len(reviewed_paths)):
            findings.fail("source-equivalence: authenticated compare not exact descendant/documentation delta")
        else:
            for item in changed:
                name = item.get("filename")
                review = reviewed_paths.get(name)
                if (not review or item.get("status") != review.get("change")
                        or item.get("sha") != review.get("blob_sha1")):
                    findings.fail(f"source-equivalence: GitHub original file differs from reviewed delta: {name}")
        history = raw.get("publication_history")
        if (not isinstance(history, list) or not history
                or comparison.get("total_commits") != len(history)
                or len(comparison.get("commits", [])) != len(history)):
            findings.fail("source-equivalence: incomplete original per-commit history")
        else:
            ancestor = commit
            for step, returned in zip(history, comparison["commits"]):
                if (not isinstance(step, dict) or step.get("parent_commit") != ancestor
                        or step.get("commit") != returned.get("sha")):
                    findings.fail("source-equivalence: history changed, omitted or reordered a commit")
                    break
                actual_commit = github_json(
                    f"https://api.github.com/repos/{repo}/commits/{step['commit']}", token)
                parents = actual_commit.get("parents")
                if (not isinstance(parents, list) or len(parents) != 1
                        or parents[0].get("sha") != ancestor):
                    findings.fail("source-equivalence: merge or non-linear history in supposedly docs-only publication")
                raw_files = step.get("documentation_changes")
                api_files = actual_commit.get("files")
                if not isinstance(raw_files, list) or not isinstance(api_files, list) or len(raw_files) != len(api_files):
                    findings.fail("source-equivalence: per-commit changed file list incomplete")
                else:
                    claimed = {x.get("path"): x for x in raw_files if isinstance(x, dict)}
                    if len(claimed) != len(raw_files):
                        findings.fail("source-equivalence: duplicate/malformed per-commit changed path")
                    for changed_file in api_files:
                        name = changed_file.get("filename")
                        proof_file = claimed.get(name)
                        if (not proof_file or changed_file.get("status") not in ("added", "modified")
                                or (name != "README.md" and
                                    (not isinstance(name, str) or re.fullmatch(
                                        r"docs/compat/logic-pro/evidence/P004/[^/]+\.json", name) is None))
                                or proof_file.get("mode") != "100644"
                                or proof_file.get("blob_sha1") != changed_file.get("sha")
                                or not valid_sha(proof_file.get("sha256"))
                                or not nonnegative_int(proof_file.get("bytes"))):
                            findings.fail(f"source-equivalence: forbidden intermediate commit edit: {name}")
                ancestor = step["commit"]
            if ancestor != publication:
                findings.fail("source-equivalence: final history commit is not publication head")
        for key, tested in (("tested_tree_sha", commit), ("publication_tree_sha", publication)):
            commit_data = github_json(f"https://api.github.com/repos/{repo}/commits/{tested}", token)
            actual_tree = ((commit_data.get("commit") or {}).get("tree") or {}).get("sha")
            if actual_tree != raw.get(key):
                findings.fail(f"source-equivalence: authenticated {key} differs from original commit")
        findings.github_checks.append({
            "phase": "P004 source-equivalence", "tested": commit, "publication": publication,
            "ok": not any(x.startswith("source-equivalence:") for x in findings.failures),
        })
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        findings.block(f"source-equivalence: cannot authenticate GitHub tree/compare ({type(exc).__name__})")
    return publication



def github_publication_file_checker(repo, publication, repo_path, expected_bytes):
    from urllib.parse import quote
    token = os.environ.get("GITHUB_TOKEN")
    encoded = quote(repo_path, safe="/")
    obj = github_json(f"https://api.github.com/repos/{repo}/contents/{encoded}?ref={publication}", token)
    if not isinstance(obj, dict) or obj.get("type") != "file" or obj.get("encoding") != "base64":
        return False, "original GitHub publication file unavailable"
    original = base64.b64decode(obj.get("content", ""), validate=False)
    computed_blob = hashlib.sha1(b"blob " + str(len(original)).encode("ascii") + b"\0" + original).hexdigest()
    if obj.get("sha") != computed_blob or original != expected_bytes:
        return False, "original GitHub published bytes/blob differ"
    return True, "exact original published Git blob byte-verified"


def validate_publication_provenance(root, inventory, manifest, contract, publication, findings, checker=None):
    """Publication B review files are outside immutable A-stage artifacts."""
    if not isinstance(inventory, dict):
        findings.block("publication: inventory unavailable")
        return
    if inventory.get("publication_commit") != publication:
        findings.fail("publication: inventory does not bind exact Git publication SHA")
    entries = inventory.get("publication_reviews")
    if not isinstance(entries, list):
        findings.block("publication: original independent review inventory absent")
        return
    predecessor_records = manifest.get("predecessors") if isinstance(manifest, dict) else None
    wanted = ({p.get("evidence", {}).get("path") for p in predecessor_records if isinstance(p, dict)}
              if isinstance(predecessor_records, list) else set())
    seen = set()
    byte_count = 0
    verification = checker or github_publication_file_checker
    for entry in entries:
        if not isinstance(entry, dict):
            findings.fail("publication: malformed independent review record")
            continue
        rel, original = entry.get("path"), entry.get("source_repo_path")
        if not isinstance(rel, str) or re.fullmatch(r"publication/[^/]+\.json", rel) is None:
            findings.fail("publication: review path outside isolated publication directory")
            continue
        if original != "docs/compat/logic-pro/evidence/P004/" + rel.split("/")[-1]:
            findings.fail(f"publication: untrusted source repository path for {rel}")
        if rel in seen:
            findings.fail(f"publication: duplicate review {rel}")
            continue
        seen.add(rel)
        if (entry.get("git_mode") != "100644"
                or not valid_sha(entry.get("git_blob_sha1"), HEX40)
                or not positive_int(entry.get("size_bytes"))
                or entry["size_bytes"] > 2 * 1024 * 1024):
            findings.fail(f"publication: invalid review blob/mode/size: {rel}")
        verify_record(root, entry, findings, f"publication/{rel}")
        path = safe_file(root, rel, findings, f"publication/{rel}")
        if path is not None:
            data = path.read_bytes()
            local_blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            if local_blob != entry.get("git_blob_sha1"):
                findings.fail(f"publication: blob SHA differs from original Git identity for {rel}")
            try:
                ok, reason = verification(contract["repository"], publication, original, data)
                if not ok:
                    findings.fail(f"publication: {rel}: {reason}")
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                findings.block(f"publication: cannot authenticate original B blob for {rel} ({type(exc).__name__})")
        if positive_int(entry.get("size_bytes")):
            byte_count += entry["size_bytes"]
    if seen != wanted or len(seen) != 3:
        findings.block("publication: three exact original predecessor reviewer blobs required")
    if inventory.get("publication_file_count") != len(seen) or inventory.get("publication_total_bytes") != byte_count:
        findings.fail("publication: independent review inventory totals invalid")
    predecessor_file = root / "predecessors.json"
    try:
        raw_predecessors = predecessor_file.read_bytes()
    except OSError:
        findings.block("publication: original predecessors.json not available")
        return
    if not raw_predecessors:
        findings.block("publication: empty original predecessors.json")
        return
    try:
        ok, reason = verification(
            contract["repository"], publication,
            "docs/compat/logic-pro/evidence/P004/predecessors.json", raw_predecessors)
        if not ok:
            findings.fail("publication: predecessors.json is not the exact original Git blob")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        findings.block(f"publication: cannot verify original B predecessors.json ({type(exc).__name__})")


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
        if (not positive_int(p.get("run_id"))
                or p.get("workflow_path") != contract.get("predecessor_workflows", {}).get(phase)):
            findings.fail(f"{phase}: wrong or missing original phase workflow")
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
            ok, reason = run_checker(contract["repository"], p["run_id"], commit, p["workflow_path"], contract.get("predecessor_jobs", {}).get(phase, []))
            findings.github_checks.append({"phase": phase, "run_id": p["run_id"], "ok": ok, "detail": reason})
            if not ok:
                findings.fail(f"{phase}: {reason}")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            findings.block(f"{phase}: cannot authenticate original Actions run ({type(exc).__name__})")


FAULT_DETECTIONS = {
    "wrong-result": "wrong-result",
    "crash": "process-crash",
    "hang": "deadline-exceeded",
    "missing-callback": "missing-callback",
    "missing-executable": "missing-executable",
    "fake-success": "no-observable-side-effect",
}


# Frozen public fixture behavior. Neither the detector's self-reported
# detection label nor its claimed hashes establish these semantics by itself.
FAULT_EXPECTED_CALLBACKS = ["initialized", "rendered", "completed"]
FAULT_EXPECTED_EFFECT = b"p004-rendered-value=42\n"
FAULT_NO_STDOUT_CASES = frozenset(("crash", "hang", "missing-executable"))


def validate_frozen_fault_observation(raw, case, findings):
    """Reconstruct the public probe oracle from raw bytes, not detector labels."""
    label = "fault_matrix.control" if case == "control" else f"fault_matrix/{case}"
    nonce = raw.get("nonce")
    if (not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{32}", nonce) is None
            or hashlib.sha256(nonce.encode("ascii")).hexdigest() != raw.get("nonce_sha256")):
        findings.fail(f"{label}: raw nonce not bound to original SHA")
    expected_effect = (b"" if case in FAULT_NO_STDOUT_CASES or case == "fake-success"
                       else FAULT_EXPECTED_EFFECT)
    effect_hex = raw.get("effect_hex")
    try:
        effect = bytes.fromhex(effect_hex)
    except (TypeError, ValueError):
        effect = None
    if (not isinstance(effect_hex, str) or effect is None
            or effect_hex != effect.hex() or effect != expected_effect
            or type(raw.get("effect_size_bytes")) is not int
            or raw["effect_size_bytes"] != len(effect)
            or raw.get("effect_sha256") != hashlib.sha256(effect).hexdigest()):
        findings.fail(f"{label}: observable effect bytes/hash contradict frozen oracle")
    for stream in ("stdout", "stderr"):
        observed, claimed = raw.get(stream), raw.get(stream + "_sha256")
        if (not isinstance(observed, str) or not valid_sha(claimed)
                or hashlib.sha256(observed.encode("utf-8", "replace")).hexdigest() != claimed):
            findings.fail(f"{label}: {stream} transcript/hash not authentic")
    if case in FAULT_NO_STDOUT_CASES:
        if raw.get("stdout") != "":
            findings.fail(f"{label}: nonreturning/missing process unexpectedly produced stdout")
        if (case == "missing-executable"
                and (not isinstance(raw.get("stderr"), str)
                     or "executable-that-must-not-exist" not in raw["stderr"])):
            findings.fail("fault_matrix/missing-executable: actual missing executable not named in stderr")
        return
    stdout = raw.get("stdout")
    if (not isinstance(stdout, str) or not stdout.endswith("\n")
            or len(stdout.splitlines()) != 1):
        findings.fail(f"{label}: raw stdout payload contradicts frozen single-line JSON oracle")
        return
    try:
        payload = json.loads(stdout, object_pairs_hook=reject_duplicate_keys,
                             parse_constant=reject_json_constant)
    except (TypeError, ValueError, UnicodeError):
        findings.fail(f"{label}: raw stdout payload contradicts frozen JSON oracle")
        return
    if not isinstance(payload, dict) or set(payload) != {"nonce", "value", "callbacks"}:
        findings.fail(f"{label}: raw stdout payload contradicts frozen JSON object oracle")
        return
    if payload.get("nonce") != nonce:
        findings.fail(f"{label}: stdout nonce not bound to original recorded nonce")
    wanted_value = 41 if case == "wrong-result" else 42
    wanted_callbacks = [] if case == "missing-callback" else FAULT_EXPECTED_CALLBACKS
    if (type(payload.get("value")) is not int or payload["value"] != wanted_value
            or payload.get("callbacks") != wanted_callbacks):
        findings.fail(f"{label}: raw stdout payload contradicts frozen value/callback oracle")


def validate_faults(root, faults, control, contract, findings, listed):
    expected = set(contract["required_faults"])
    if not isinstance(faults, list):
        findings.block("fault_matrix: no fault-injection results")
        return
    seen = set()
    observed_nonces = set()
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
        if type(fault.get("detector_exit_code")) is not int or fault["detector_exit_code"] != 1:
            findings.fail(f"fault_matrix/{ident}: detector must exit 1, not timeout or claim success")
        record = fault.get("artifact")
        path = verify_record(root, record, findings, f"fault_matrix/{ident}")
        if path not in listed or listed[path][2] != "source":
            findings.fail(f"fault_matrix/{ident}: raw trace absent from hashed source inventory")
            continue
        if not isinstance(path, str):
            continue
        raw = read_json(root / path, findings, f"fault_matrix/{ident}.raw")
        if not isinstance(raw, dict):
            continue
        detected = FAULT_DETECTIONS[ident]
        if raw.get("case") != ident or raw.get("expected_detection") != detected or raw.get("observed_detection") != detected:
            findings.fail(f"fault_matrix/{ident}: independent raw detection reason mismatch")
        if raw.get("oracle_rejected") is not True or raw.get("detected") is not True:
            findings.fail(f"fault_matrix/{ident}: raw oracle did not reject deliberately defective behavior")
        if not valid_sha(raw.get("nonce_sha256")):
            findings.fail(f"fault_matrix/{ident}: missing per-case unpredictable nonce")
        for stream_name in ("stdout", "stderr"):
            value = raw.get(stream_name)
            digest = raw.get(stream_name + "_sha256")
            if not isinstance(value, str) or not valid_sha(digest):
                findings.fail(f"fault_matrix/{ident}: missing {stream_name} transcript/hash")
            elif hashlib.sha256(value.encode("utf-8")).hexdigest() != digest:
                findings.fail(f"fault_matrix/{ident}: {stream_name} transcript hash differs")
        if not nonnegative_int(raw.get("effect_size_bytes")) or not valid_sha(raw.get("effect_sha256")):
            findings.fail(f"fault_matrix/{ident}: invalid observable-effect proof")
        observed_exit = raw.get("observed_process_exit_code")
        if ident == "hang":
            if raw.get("timed_out") is not True or observed_exit is not None:
                findings.fail("fault_matrix/hang: real deadline expiry not observed")
        elif ident == "crash":
            if raw.get("timed_out") is not False or type(observed_exit) is not int or observed_exit >= 0:
                findings.fail("fault_matrix/crash: no crashing process status")
        elif ident == "missing-executable":
            if observed_exit is not None or raw.get("timed_out") is not False:
                findings.fail("fault_matrix/missing-executable: executable absence not established")
        else:
            if observed_exit != 0 or raw.get("timed_out") is not False:
                findings.fail(f"fault_matrix/{ident}: expected a misleading successful exit")
        if ident == "fake-success" and raw.get("effect_size_bytes") != 0:
            findings.fail("fault_matrix/fake-success: supposed unchanged output has side effects")
        validate_frozen_fault_observation(raw, ident, findings)
        fault_nonce = raw.get("nonce")
        if isinstance(fault_nonce, str):
            if fault_nonce in observed_nonces:
                findings.fail(f"fault_matrix/{ident}: reused nonce across independent process fixtures")
            observed_nonces.add(fault_nonce)
    if seen != expected:
        findings.block("fault_matrix: missing deliberate faults " + ",".join(sorted(expected - seen)))
    if not isinstance(control, dict) or control.get("status") != "PASS" or control.get("detector_exit_code") != 0:
        findings.fail("fault_matrix: positive control did not pass with detector exit zero")
        return
    ctl_path = verify_record(root, control.get("artifact"), findings, "fault_matrix.control")
    if ctl_path not in listed or listed[ctl_path][2] != "source":
        findings.fail("fault_matrix: positive control missing from hashed source inventory")
        return
    raw_ctl = read_json(root / ctl_path, findings, "fault_matrix.control.raw")
    if not isinstance(raw_ctl, dict):
        return
    if (raw_ctl.get("case") != "control" or raw_ctl.get("detected") is not True
            or raw_ctl.get("oracle_rejected") is not False
            or raw_ctl.get("expected_detection") is not None
            or raw_ctl.get("observed_detection") is not None
            or raw_ctl.get("observed_process_exit_code") != 0
            or raw_ctl.get("timed_out") is not False
            or not positive_int(raw_ctl.get("effect_size_bytes"))
            or not valid_sha(raw_ctl.get("effect_sha256"))
            or not valid_sha(raw_ctl.get("nonce_sha256"))):
        findings.fail("fault_matrix: raw positive control lacks genuine success and visible effect")
    validate_frozen_fault_observation(raw_ctl, "control", findings)
    control_nonce = raw_ctl.get("nonce")
    if isinstance(control_nonce, str) and control_nonce in observed_nonces:
        findings.fail("fault_matrix.control: reused nonce from a negative fixture")


def validate_document(manifest, inventory, root: Path, contract, commit, *, run_checker=None, jobs_checker=None, publication_checker=None):
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
    findings.expected_source_tree = inventory.get("source_tree") if isinstance(inventory, dict) else None
    findings.expected_source_lock = inventory.get("source_lock_sha256") if isinstance(inventory, dict) else None
    findings.expected_publication_commit = inventory.get("publication_commit") if isinstance(inventory, dict) else None
    findings.expected_run_id = run_id
    findings.expected_run_attempt = inventory.get("github_run_attempt") if isinstance(inventory, dict) else None
    validate_jobs(root, manifest.get("jobs"), stages, listed, contract, commit, findings)
    validate_raw_stages(root, stages, listed, contract, commit, findings)
    validate_faults(root, manifest.get("fault_matrix"), manifest.get("fault_control"), contract, findings, listed)
    publication = verify_source_equivalence(root, manifest, contract, commit, listed, findings)
    validate_publication_provenance(root, inventory, manifest, contract, publication, findings, publication_checker)
    validate_predecessors(root, manifest.get("predecessors"), contract, commit, findings, run_checker or github_run_checker)
    if positive_int(run_id):
        try:
            expected_names = list(contract.get("github_job_names", {}).values())
            if len(expected_names) != len(contract.get("required_jobs", [])):
                findings.fail("contract: incomplete GitHub job-name mapping")
            else:
                ok, message = (jobs_checker or github_jobs_checker)(contract["repository"], run_id, expected_names, commit,
                    manifest.get("evidence_publication_commit") or commit,
                    inventory.get("github_run_attempt") if isinstance(inventory, dict) else None,
                    stages, listed)
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
        "predecessors": [], "jobs": [], "fault_matrix": [], "fault_control": {}
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
            manifest["fault_matrix"] = matrix.get("fault_matrix", matrix.get("cases", []))
            manifest["fault_control"] = matrix.get("control", {})
            if matrix.get("status") != "PASS":
                findings.fail("collect: fault-matrix campaign not successful")
    if source_stages:
        source_stage = source_stages[0]
        source_dir = source_stage["path"]
        eq_entry = next((entry for entry in source_stage.get("files", [])
                         if isinstance(entry, dict) and entry.get("path") == "source-equivalence.json"), None)
        if eq_entry is not None:
            equivalence_path = source_dir + "/source-equivalence.json"
            equivalence = read_json(root / equivalence_path, findings, "collect.source-equivalence")
            if isinstance(equivalence, dict):
                manifest["evidence_publication_commit"] = equivalence.get("publication_commit")
                manifest["source_equivalence"] = {
                    "path": equivalence_path,
                    "sha256": eq_entry.get("sha256"),
                    "size_bytes": eq_entry.get("size"),
                }
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
