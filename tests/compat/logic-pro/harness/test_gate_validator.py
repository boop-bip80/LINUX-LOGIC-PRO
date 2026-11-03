#!/usr/bin/env python3
"""P004 adversarial integration tests against the *production* gate validator.

Only the external GitHub REST confirmation functions are replaced in these
unit tests. Artifact checks, required job semantics, independent evidence,
hashes, and fault-case checking execute the real production functions.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[4]
GATE_PATH = REPO / "tools/compat/logic-pro/check_gates.py"
CONTRACT_PATH = REPO / "docs/compat/logic-pro/gates.json"
if not GATE_PATH.is_file() or not CONTRACT_PATH.is_file():
    raise RuntimeError("P004 gate integration requires the actual check_gates.py and gates.json")

spec = importlib.util.spec_from_file_location("p004_real_gate", GATE_PATH)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fault_matrix import run_matrix

COMMIT = "a" * 40
RUN_ID = 65432112345
CONTRACT = json.loads(CONTRACT_PATH.read_text())


def write_json(root: Path, rel: str, data) -> dict:
    raw = (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8")
    dest = root / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return {
        "path": rel,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    }


def make_fixture(root: Path) -> tuple[dict, dict]:
    """Assemble actual on-disk reports and a complete synthetic gate manifest."""
    jobs = []
    stages = []
    run_summary = None
    frozen_lock_sha = None
    for role in CONTRACT["required_jobs"]:
        dirname = f"p004-{role}-{COMMIT}"
        expected_result = {
            "source": True,
            "toolchain": True,
            "build-a": 20,
            "build-b": 20,
            "independent-runtime": 10,
        }[role]
        assertions = [
            {
                "id": name, "kind": "equals",
                "expected": expected_result, "actual": expected_result,
            }
            for name in CONTRACT["required_assertions"][role]
        ]
        executed_count = {
            "source": 448, "toolchain": 1,
            "build-a": 20, "build-b": 20,
            "independent-runtime": 10,
        }[role]
        report = {
            "schema": "darling.p004.job.v1", "phase": "P004",
            "name": role, "role": role, "source_commit": COMMIT,
            "runner": "ubuntu-22.04", "status": "PASS",
            "discovered": executed_count, "executed": executed_count,
            "passed": executed_count,
            "failed": 0, "skipped": 0, "timed_out": False,
            "exit_code": 0, "assertions": assertions,
        }
        write_json(root, dirname + "/p004-job.json", report)
        write_json(root, dirname + "/probe.json", {
            "observed": True, "source_commit": COMMIT, "role": role
        })
        if role == "source":
            # These logs are purpose-built unit-test inputs, not claims of
            # actual CI execution. The real CLI can only pass with verified
            # live GitHub Actions evidence, which these tests inject.
            suite_floors = {
                "baseline": 130, "submodules": 97, "build": 151,
                "harness": 42, "evidence": 28,
            }
            suites = []
            for suite, count in suite_floors.items():
                lines = [f"# synthetic gate unit-test transcript: {suite}"]
                lines.extend(
                    f"test_{suite}_{number:04d} (p004.synthetic.{suite}) ... ok"
                    for number in range(count)
                )
                lines.extend(["", f"Ran {count} tests in 0.001s", "", "OK"])
                text = "\n".join(lines) + "\n"
                log = root / dirname / (suite + ".log")
                log.parent.mkdir(parents=True, exist_ok=True)
                log.write_text(text, encoding="utf-8")
                suites.append({
                    "suite": suite, "count": count, "discovered": count,
                    "passed": count, "skipped": 0, "exit_code": 0,
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                })
            write_json(root, dirname + "/source-summary.json", {
                "schema": "darling.p004.source-suites.v1", "phase": "P004",
                "source_commit": COMMIT, "suites": suites,
            })
            run_summary = run_matrix(
                root / dirname, timeout_seconds=0.15, artifact_prefix=dirname
            )
            if run_summary["status"] != "PASS":
                raise AssertionError("live synthetic fault matrix failed positive control")
        elif role == "toolchain":
            image = b"synthetic-p004-toolchain-archive-for-gate-unittests\n"
            (root / dirname / "toolchain-image.tar.gz").write_bytes(image)
            frozen = write_json(root, dirname + "/toolchain.lock.json", {
                "image_archive": {"sha256": hashlib.sha256(image).hexdigest()},
            })
            frozen_lock_sha = frozen["sha256"]
        elif role in ("build-a", "build-b"):
            if frozen_lock_sha is None:
                raise AssertionError("toolchain stage must precede both builds")
            write_json(root, dirname + "/build-summary.json", {
                "schema": "darling.p003.build.v1", "phase": "P003",
                "source_commit": COMMIT, "build_id": role[-1],
                "status": "PASS", "last_stage": "complete",
                "exit_code": 0, "toolchain_sha256": frozen_lock_sha,
            })
            for cycle in ("first", "second"):
                write_json(root, dirname + f"/probes-{cycle}/report.json", {
                    "status": "PASSED", "source_revision": COMMIT,
                    "cases": [
                        {"id": index, "status": "PASSED"}
                        for index in range(10)
                    ],
                })
                write_json(root, dirname + f"/install-{cycle}.json", {
                    "source_commit": COMMIT, "cycle": cycle,
                    "entries": 11941, "synthetic_fixture": True,
                })
            archive = ("synthetic-installed-prefix-" + role + "\n").encode()
            (root / dirname / "runtime-prefix.tar.gz").write_bytes(archive)
            archive_hash = hashlib.sha256(archive).hexdigest()
            (root / dirname / "runtime-prefix.sha256").write_text(
                archive_hash + "  runtime-prefix.tar.gz\n", encoding="utf-8"
            )
        elif role == "independent-runtime":
            write_json(root, dirname + "/runtime-summary.json", {
                "schema": "darling.p004.independent-runtime-summary.v1",
                "phase": "P004", "source_commit": COMMIT,
                "status": "PASS", "package_review": "PASS",
                "runtime_cases": 10, "source_free_replay": True, "errors": [],
            })
            write_json(root, dirname + "/package-review.json", {
                "status": "PASS", "synthetic_fixture": True,
            })
            write_json(root, dirname + "/runtime/report.json", {
                "source_commit": COMMIT, "status": "PASSED",
                "cases": [
                    {"id": index, "status": "PASSED"}
                    for index in range(10)
                ],
            })
        entries = []
        for file in sorted((root / dirname).rglob("*")):
            if not file.is_file():
                continue
            relative = file.relative_to(root / dirname).as_posix()
            raw = file.read_bytes()
            entries.append({
                "path": relative, "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            })
        stages.append({"role": role, "path": dirname, "files": entries})
        jobs.append({
            **report,
            "artifacts": [
                {
                    "path": dirname + "/" + entry["path"],
                    "sha256": entry["sha256"],
                    "size_bytes": entry["size"],
                }
                for entry in entries
            ],
        })
    pred = []
    for phase, workflow in [
        ("P001", ".github/workflows/phase1-baseline.yml"),
        ("P002", ".github/workflows/phase2-submodules.yml"),
        ("P003", ".github/workflows/phase3-build.yml"),
    ]:
        reviewed = write_json(root, "predecessors/" + phase + ".json", {
            "phase": phase, "commit": COMMIT, "reviewer": "independent-reviewer",
        })
        pred.append({
            "phase": phase, "status": "PASS", "source_commit": COMMIT,
            "run_id": RUN_ID + len(pred) + 1,
            "workflow_path": workflow,
            "conclusion": "success",
            "reviewer": "independent-reviewer", "author": "separate-author",
            "reviewed_at": "2026-11-03T17:00:00Z",
            "evidence": reviewed,
        })
    inventory = {
        "schema": "darling.p004.evidence-inventory.v1", "phase": "P004",
        "status": "EVIDENCE_INVENTORY_VERIFIED",
        "source_commit": COMMIT, "github_run_id": RUN_ID,
        "github_run_attempt": 1, "retention_days": 90,
        "artifacts": stages,
        "file_count": sum(len(x["files"]) for x in stages),
        "total_bytes": sum(entry["size"] for x in stages for entry in x["files"]),
    }
    manifest = {
        "schema_version": 1, "phase": "P004",
        "source_commit": COMMIT, "run_id": RUN_ID,
        "predecessors": pred, "jobs": jobs,
        "fault_matrix": run_summary["fault_matrix"],
        "fault_control": run_summary["control"],
    }
    write_json(root, "manifest.json", manifest)
    write_json(root, "inventory.json", inventory)
    return manifest, inventory


class RealGateAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._fixture = tempfile.TemporaryDirectory(prefix="p004-gate-fixture-")
        cls._source = Path(cls._fixture.name)
        cls._manifest, cls._inventory = make_fixture(cls._source)

    @classmethod
    def tearDownClass(cls):
        cls._fixture.cleanup()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="p004-gate-case-")
        self.root = Path(self._tmp.name) / "evidence"
        shutil.copytree(self._source, self.root)
        self.manifest = copy.deepcopy(self._manifest)
        self.inventory = copy.deepcopy(self._inventory)

    def tearDown(self):
        self._tmp.cleanup()

    @staticmethod
    def confirmed_run(*_args):
        return True, "synthetic unit-test GitHub confirmation only"

    def check(self):
        return gate.validate_document(
            self.manifest, self.inventory, self.root, CONTRACT, COMMIT,
            run_checker=self.confirmed_run, jobs_checker=self.confirmed_run,
        )

    def assert_rejected(self, expected_reason: str | None = None):
        findings = self.check()
        self.assertIn(findings.status, ("FAIL", "BLOCKED"), findings.report(COMMIT, "P004"))
        if expected_reason is not None:
            details = "\n".join(findings.failures + findings.blockers)
            self.assertIn(expected_reason, details, findings.report(COMMIT, "P004"))
        return findings

    def job(self, name="source"):
        return next(x for x in self.manifest["jobs"] if x["name"] == name)

    def _retie_stage_file(self, relpath: str):
        """Rehash tampered physical bytes across both manifest and inventory.

        This removes a mere stale-hash explanation for semantic test failures.
        """
        raw = (self.root / relpath).read_bytes()
        sha, size = hashlib.sha256(raw).hexdigest(), len(raw)
        role = next(x["role"] for x in self.inventory["artifacts"]
                    if relpath.startswith(x["path"] + "/"))
        stage = next(x for x in self.inventory["artifacts"] if x["role"] == role)
        internal = relpath[len(stage["path"]) + 1:]
        entry = next(x for x in stage["files"] if x["path"] == internal)
        old_size = entry["size"]
        entry.update(sha256=sha, size=size)
        self.inventory["total_bytes"] += size - old_size
        for artifact in self.job(role)["artifacts"]:
            if artifact["path"] == relpath:
                artifact.update(sha256=sha, size_bytes=size)
        for fault in self.manifest["fault_matrix"]:
            if fault["artifact"]["path"] == relpath:
                fault["artifact"].update(sha256=sha, size_bytes=size)

    def test_valid_complete_fixture_passes_local_gate(self):
        self.assertEqual(self.check().status, "PASS")

    def test_wrong_result_even_with_zero_process_exit_is_rejected(self):
        self.job("build-a")["assertions"][0]["actual"] = False
        self.assertEqual(self.assert_rejected("expected result differs from actual").status, "FAIL")

    def test_crashed_job_with_nonzero_exit_is_rejected(self):
        self.job("build-b")["exit_code"] = -6
        self.assertEqual(self.assert_rejected("timed out, cancelled, or nonzero exit").status, "FAIL")

    def test_timed_out_job_is_rejected(self):
        self.job("independent-runtime")["timed_out"] = True
        self.assertEqual(self.assert_rejected("timed out, cancelled, or nonzero exit").status, "FAIL")

    def test_missing_callback_assertion_is_not_a_pass(self):
        self.job("source")["assertions"][0] = {
            "id": "all-three-regressions", "kind": "min_count",
            "minimum": 1, "observed": 0,
        }
        self.assertEqual(self.assert_rejected("callback/observation count below minimum").status, "FAIL")

    def test_missing_executable_artifact_blocks_gate(self):
        source = next(x for x in self.inventory["artifacts"] if x["role"] == "source")
        (self.root / source["path"] / "p004-job.json").unlink()
        self.assert_rejected("absent regular file")

    def test_fake_success_without_state_change_is_rejected(self):
        self.job("source")["assertions"][0] = {
            "id": "all-three-regressions", "kind": "changed_sha256",
            "before_sha256": "1" * 64,
            "after_sha256": "1" * 64,
        }
        self.assertEqual(self.assert_rejected("no proven state change").status, "FAIL")

    def test_missing_fault_is_blocking(self):
        self.manifest["fault_matrix"].pop()
        self.assert_rejected("missing deliberate faults")

    def test_detectors_cannot_claim_detected_when_status_is_missing(self):
        self.manifest["fault_matrix"][0]["status"] = "UNDETECTED"
        self.assertEqual(self.assert_rejected("deliberate failure escaped detection").status, "FAIL")

    def test_honest_hash_mismatch_is_not_tolerated(self):
        self.manifest["fault_matrix"][0]["artifact"]["sha256"] = "f" * 64
        self.assertEqual(self.assert_rejected("sha256 mismatch").status, "FAIL")

    def test_forged_raw_fault_trace_rejected_even_when_rehashed(self):
        fault = self.manifest["fault_matrix"][0]
        path = fault["artifact"]["path"]
        trace = json.loads((self.root / path).read_text())
        trace["observed_detection"] = "success"
        write_json(self.root, path, trace)
        self._retie_stage_file(path)
        self.assertEqual(self.assert_rejected("independent raw detection reason mismatch").status, "FAIL")

    def test_forged_source_log_rejected_even_with_coherent_hashes(self):
        stage = next(x for x in self.inventory["artifacts"] if x["role"] == "source")
        prefix = stage["path"]
        path = prefix + "/baseline.log"
        (self.root / path).write_text(
            "synthetic forged green log with no actual unittest cases\n",
            encoding="utf-8",
        )
        self._retie_stage_file(path)
        summary_path = prefix + "/source-summary.json"
        summary = json.loads((self.root / summary_path).read_text())
        replaced = (self.root / path).read_bytes()
        entry = next(x for x in summary["suites"] if x["suite"] == "baseline")
        entry["sha256"] = hashlib.sha256(replaced).hexdigest()
        write_json(self.root, summary_path, summary)
        self._retie_stage_file(summary_path)
        self.assertEqual(
            self.assert_rejected("raw unittest transcript incomplete/forged/skipped").status,
            "FAIL",
        )

    def test_invented_positive_control_rejected_even_when_rehashed(self):
        source = next(x for x in self.inventory["artifacts"] if x["role"] == "source")
        prefix = source["path"]
        path = prefix + "/faults/control.json"
        raw = json.loads((self.root / path).read_text())
        raw["oracle_rejected"] = True
        raw["observed_detection"] = "fake-success"
        write_json(self.root, path, raw)
        self._retie_stage_file(path)
        # Keep fault-matrix.json internally consistent with the changed hash.
        matrix_rel = prefix + "/fault-matrix.json"
        matrix = json.loads((self.root / matrix_rel).read_text())
        changed = (self.root / path).read_bytes()
        matrix["control"]["artifact"].update({
            "sha256": hashlib.sha256(changed).hexdigest(),
            "size_bytes": len(changed),
        })
        self.manifest["fault_control"]["artifact"].update(matrix["control"]["artifact"])
        write_json(self.root, matrix_rel, matrix)
        self._retie_stage_file(matrix_rel)
        self.assert_rejected("raw positive control lacks genuine success")

    def test_skipped_tests_do_not_count_as_green(self):
        self.job("toolchain")["skipped"] = 1
        self.assertEqual(self.assert_rejected("failed or skipped cases").status, "FAIL")

    def test_empty_test_discovery_is_blocked(self):
        self.job("source")["discovered"] = 0
        self.assert_rejected("zero/missing discovered or executed assertions")

    def test_runner_unavailable_is_not_eligible(self):
        self.job("source")["runner"] = "missing-self-hosted-runner"
        self.assertEqual(self.assert_rejected("unsupported or unidentified runner").status, "FAIL")

    def test_predecessor_missing_blocks_phase_advance(self):
        self.manifest["predecessors"].pop(1)
        self.assert_rejected("incomplete ordered independent acceptance")

    def test_predecessor_wrong_source_sha_fails(self):
        self.manifest["predecessors"][0]["source_commit"] = "b" * 40
        self.assertEqual(self.assert_rejected("acceptance belongs to different tested source").status, "FAIL")

    def test_github_confirmed_failure_cannot_pass(self):
        findings = gate.validate_document(
            self.manifest, self.inventory, self.root, CONTRACT, COMMIT,
            run_checker=lambda *_: (False, "authentic failure"),
            jobs_checker=lambda *_: (False, "authentic failure"),
        )
        self.assertEqual(findings.status, "FAIL")

    def test_unavailable_authenticated_github_run_is_blocked(self):
        import urllib.error
        def unreachable(*_args):
            raise urllib.error.URLError("offline")
        findings = gate.validate_document(
            self.manifest, self.inventory, self.root, CONTRACT, COMMIT,
            run_checker=unreachable, jobs_checker=self.confirmed_run,
        )
        self.assertEqual(findings.status, "BLOCKED")

    def test_not_applicable_required_job_is_not_a_pass(self):
        self.job("source")["status"] = "NATIVE_NOT_APPLICABLE"
        self.assert_rejected("status is not PASS")

    def test_out_of_order_predecessors_are_rejected(self):
        self.manifest["predecessors"][0], self.manifest["predecessors"][1] = (
            self.manifest["predecessors"][1],
            self.manifest["predecessors"][0],
        )
        self.assertEqual(self.assert_rejected("phase order must be P001 then P002 then P003").status, "FAIL")

    def test_missing_positive_control_is_rejected(self):
        self.manifest["fault_control"] = {}
        self.assertEqual(self.assert_rejected("positive control did not pass").status, "FAIL")

    def test_symlinked_or_traversing_artifact_path_is_rejected(self):
        self.manifest["fault_matrix"][0]["artifact"]["path"] = "../outside.json"
        self.assertEqual(self.assert_rejected("traversal or absolute path").status, "FAIL")

    def test_duplicate_job_is_rejected(self):
        self.manifest["jobs"].append(copy.deepcopy(self.manifest["jobs"][0]))
        self.assertEqual(self.assert_rejected("duplicate job").status, "FAIL")


if __name__ == "__main__":
    unittest.main()
