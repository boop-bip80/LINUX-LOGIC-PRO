#!/usr/bin/env python3
"""P004 adversarial integration tests against the *production* gate validator.

Only the external GitHub REST confirmation functions are replaced in these
unit tests. Artifact checks, required job semantics, independent evidence,
hashes, and fault-case checking execute the real production functions.
"""
from __future__ import annotations

import copy
import io
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest import mock

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
from test_stage_receipt import BUILD_CASES, RUNTIME_CASES, make_p003_observations, harness_case_names

COMMIT = "a" * 40
SOURCE_TREE = "c" * 40
SOURCE_LOCK_SHA256 = "d" * 64
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
            "source": 525, "toolchain": 1,
            "build-a": 20, "build-b": 20,
            "independent-runtime": 10,
        }[role]
        report = {
            "schema": "darling.p004.job.v1", "phase": "P004",
            "name": role, "role": role, "source_commit": COMMIT,
            "runner": "ubuntu-22.04", "status": "PASS",
            "source_tree": SOURCE_TREE,
            "source_lock_sha256": SOURCE_LOCK_SHA256,
            "publication_commit": COMMIT,
            "github_run_id": RUN_ID, "github_run_attempt": 1,
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
                "baseline": 143, "submodules": 97, "build": 151,
                "harness": 95, "evidence": 39,
            }
            suites = []
            for suite, count in suite_floors.items():
                lines = [f"# synthetic gate unit-test transcript: {suite}"]
                if suite == "harness":
                    lines.extend(harness_case_names())
                else:
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
                "source_commit": COMMIT, "publication_commit": COMMIT,
                "status": "PASS", "suites": suites,
            })
            run_summary = run_matrix(
                root / dirname, timeout_seconds=1.5, artifact_prefix=dirname
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
                observed = make_p003_observations(
                    root / dirname / f"probes-{cycle}",
                    "0123456789abcdef", independent=False,
                )
                write_json(root, dirname + f"/probes-{cycle}/report.json", {
                    "status": "PASSED", "source_revision": COMMIT,
                    "passed": True, "errors": [],
                    "nonce": "0123456789abcdef",
                    "stub_diagnostics": {"enabled": True,
                                         "environment": {"STUB_VERBOSE": "1"},
                                         "hits": []},
                    "lifecycle": {
                        "server_before": {"pid": 4321, "mount_namespace": "mnt:[12345]"},
                        "server_exited": True,
                        "mount_namespace_released": True,
                        "namespace_holders_after": [],
                    },
                    **observed,
                    "cases": [{"name": name, "status": "PASSED"} for name in BUILD_CASES],
                })
                write_json(root, dirname + f"/install-{cycle}.json", {
                    "source_commit": COMMIT, "cycle": cycle,
                    "entries": 11941, "synthetic_fixture": True,
                })
            write_json(root, dirname + "/uninstall.json", {
                "source_commit": COMMIT, "status": "PASS",
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
                "status": "PASS", "installed_readback": "PASS",
                "source_commit": COMMIT, "synthetic_fixture": True,
            })
            observed = make_p003_observations(
                root / dirname / "runtime",
                "abcdef0123456789", independent=True,
            )
            write_json(root, dirname + "/runtime/report.json", {
                "source_commit": COMMIT, "status": "PASS",
                "passed": True, "errors": [],
                "nonce": "abcdef0123456789",
                "isolation": {"source_and_build_absent": True},
                "stub_diagnostics": {"enabled": True,
                                     "environment": {"STUB_VERBOSE": "1"},
                                     "hits": []},
                "lifecycle": {
                    "server_before": {"pid": 4321, "mount_namespace": "mnt:[12345]"},
                    "server_exited": True,
                    "mount_namespace_released": True,
                    "namespace_holders_after": [],
                },
                **observed,
                "cases": [{"name": name, "status": "PASS"} for name in RUNTIME_CASES],
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
    publication_reviews = []
    for phase, workflow in [
        ("P001", ".github/workflows/phase1-baseline.yml"),
        ("P002", ".github/workflows/phase2-submodules.yml"),
        ("P003", ".github/workflows/phase3-build.yml"),
    ]:
        basename = phase.lower() + "-review.json"
        publication_path = "publication/" + basename
        reviewed = write_json(root, publication_path, {
            "schema_version": 1, "phase": phase, "source_commit": COMMIT,
            "reviewer": "independent-reviewer",
            "author": "separate-author", "verdict": "PASS",
            "reviewed_at": "2026-11-03T17:00:00Z",
            "run_id": RUN_ID + len(pred) + 1, "workflow_path": workflow,
            "conclusion": "success", "event": "push", "head_branch": "main",
            "jobs": [{"name": name, "conclusion": "success"}
                     for name in CONTRACT["predecessor_jobs"][phase]],
            "synthetic_fixture": True,
        })
        original = (root / publication_path).read_bytes()
        publication_reviews.append({
            "path": publication_path,
            "source_repo_path": "docs/compat/logic-pro/evidence/P004/" + basename,
            "sha256": reviewed["sha256"],
            "size_bytes": reviewed["size_bytes"],
            "git_blob_sha1": hashlib.sha1(
                b"blob " + str(len(original)).encode("ascii") + b"\0" + original
            ).hexdigest(),
            "git_mode": "100644",
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
    write_json(root, "predecessors.json", {"phases": pred})
    inventory = {
        "schema": "darling.p004.evidence-inventory.v1", "phase": "P004",
        "status": "EVIDENCE_INVENTORY_VERIFIED",
        "source_commit": COMMIT, "source_tree": SOURCE_TREE,
        "source_lock_sha256": SOURCE_LOCK_SHA256,
        "github_run_id": RUN_ID,
        "github_run_attempt": 1, "retention_days": 90,
        "publication_commit": COMMIT,
        "publication_reviews": publication_reviews,
        "publication_file_count": len(publication_reviews),
        "publication_total_bytes": sum(item["size_bytes"] for item in publication_reviews),
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
        "publication_reviews": [],
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
            publication_checker=self.confirmed_run,
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

    def _reset_to_honest_fixture(self) -> None:
        """Make every semantic mutation independent of a previous subtest."""
        shutil.rmtree(self.root)
        shutil.copytree(self._source, self.root)
        self.manifest = copy.deepcopy(self._manifest)
        self.inventory = copy.deepcopy(self._inventory)

    @staticmethod
    def _change_stdout(raw: dict, **changes) -> None:
        payload = json.loads(raw["stdout"].strip())
        payload.update(changes)
        raw["stdout"] = json.dumps(payload, sort_keys=True) + "\n"
        raw["stdout_sha256"] = hashlib.sha256(raw["stdout"].encode()).hexdigest()

    @staticmethod
    def _forge_output(raw: dict) -> None:
        raw["stdout"] = '{"fake":"nonreturning process wrote success"}\n'
        raw["stdout_sha256"] = hashlib.sha256(raw["stdout"].encode()).hexdigest()

    def _reuse_positive_control_nonce(self, raw: dict) -> None:
        stage = next(x for x in self.inventory["artifacts"] if x["role"] == "source")
        source = json.loads((self.root / stage["path"] / "faults/control.json").read_text())
        reused = source["nonce"]
        raw["nonce"] = reused
        raw["nonce_sha256"] = hashlib.sha256(reused.encode()).hexdigest()
        self._change_stdout(raw, nonce=reused)

    def _rewrite_fault_raw_and_retie_every_digest(self, case: str, mutate) -> None:
        """Mutate the original trace and rebind the physical source matrix.

        A failure must arise from gate semantics, not accidentally stale
        artifact hashes or a missing inventory entry.
        """
        source = next(x for x in self.inventory["artifacts"] if x["role"] == "source")
        prefix = source["path"]
        relative = prefix + "/faults/" + case + ".json"
        raw = json.loads((self.root / relative).read_text(encoding="utf-8"))
        mutate(raw)
        write_json(self.root, relative, raw)
        self._retie_stage_file(relative)

        bytes_now = (self.root / relative).read_bytes()
        artifact = {"path": relative,
                    "sha256": hashlib.sha256(bytes_now).hexdigest(),
                    "size_bytes": len(bytes_now)}
        matrix_path = prefix + "/fault-matrix.json"
        matrix = json.loads((self.root / matrix_path).read_text(encoding="utf-8"))
        if case == "control":
            matrix["control"]["artifact"].update(artifact)
            self.manifest["fault_control"]["artifact"].update(artifact)
        else:
            item = next(x for x in matrix["fault_matrix"] if x["id"] == case)
            item["artifact"].update(artifact)
        write_json(self.root, matrix_path, matrix)
        self._retie_stage_file(matrix_path)

    def test_missing_candidate_equivalence_report_is_never_ready(self):
        """A==B must BLOCK phase acceptance, though every raw local stage passes."""
        blocked = self.check()
        self.assertEqual(blocked.status, "BLOCKED")
        self.assertIn(
            "A==B candidate requires independent docs-only publication B",
            "\n".join(blocked.blockers),
        )
        self.assertIn(
            "missing preliminary candidate report",
            "\n".join(blocked.blockers),
        )

        # Component-only positive: prove that all five actual physical stage
        # reports, their inventories, assertions, and six original deliberate
        # faults validate independently of later GitHub A->B publication.
        local = gate.Findings()
        stages, listed = gate.validate_inventory(
            self.root, self.inventory, CONTRACT, COMMIT,
            self.manifest["run_id"], local,
        )
        local.expected_source_tree = self.inventory["source_tree"]
        local.expected_source_lock = self.inventory["source_lock_sha256"]
        local.expected_publication_commit = self.inventory["publication_commit"]
        local.expected_run_id = self.manifest["run_id"]
        local.expected_run_attempt = self.inventory["github_run_attempt"]
        gate.validate_jobs(
            self.root, self.manifest["jobs"], stages, listed, CONTRACT, COMMIT, local,
        )
        gate.validate_raw_stages(
            self.root, stages, listed, CONTRACT, COMMIT, local,
        )
        gate.validate_faults(
            self.root, self.manifest["fault_matrix"],
            self.manifest["fault_control"], CONTRACT, local, listed,
        )
        self.assertEqual(local.failures, [], local.report(COMMIT, "P004"))
        self.assertEqual(local.blockers, [], local.report(COMMIT, "P004"))
        self.assertEqual(local.status, "PASS")

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


    def _mutate_raw_p003_report(self, role: str, relative: str, mutate) -> None:
        stage = next(x for x in self.inventory["artifacts"] if x["role"] == role)
        path = stage["path"] + "/" + relative
        report = json.loads((self.root / path).read_text(encoding="utf-8"))
        mutate(report)
        write_json(self.root, path, report)
        self._retie_stage_file(path)

    def test_duplicate_gui_case_rejected_even_with_coherent_file_hashes(self):
        self._mutate_raw_p003_report(
            "build-a", "probes-first/report.json",
            lambda report: report["cases"][8].update(name="macho-known-vector"),
        )
        self.assertEqual(
            self.assert_rejected("wrong/duplicate P003 case IDs").status, "FAIL"
        )

    def test_source_free_faked_foundation_case_rejected_even_when_rehashed(self):
        self._mutate_raw_p003_report(
            "independent-runtime", "runtime/report.json",
            lambda report: report["cases"][7].update(name="fake-success"),
        )
        self.assertEqual(
            self.assert_rejected("wrong/duplicate P003 case IDs").status, "FAIL"
        )

    def test_gui_missing_after_pixel_capture_rejected_even_when_rehashed(self):
        self._mutate_raw_p003_report(
            "build-b", "probes-second/report.json",
            lambda report: report["screenshots"].pop("after"),
        )
        self.assertEqual(
            self.assert_rejected("missing original before/after rendered PNGs").status,
            "FAIL",
        )

    def test_stubbing_runtime_value_rejected_even_when_rehashed(self):
        self._mutate_raw_p003_report(
            "build-a", "probes-second/report.json",
            lambda report: report["stub_diagnostics"]["hits"].append(
                {"stream": "stderr", "text": "libxpc stub called: fake-success"}
            ),
        )
        self.assertEqual(
            self.assert_rejected("reached generic success/null stubs").status, "FAIL"
        )

    def test_runtime_leaked_mount_namespace_rejected_even_when_rehashed(self):
        self._mutate_raw_p003_report(
            "independent-runtime", "runtime/report.json",
            lambda report: report["lifecycle"].update(mount_namespace_released=False),
        )
        self.assertEqual(
            self.assert_rejected("true Darling server and namespace teardown").status,
            "FAIL",
        )

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
        """Seven coherent forgeries must fail on independent semantic oracles."""
        scenarios = (
            ("wrong-result", lambda raw: raw.update(observed_detection="success"),
             "independent raw detection reason mismatch"),
            ("wrong-result", lambda raw: self._change_stdout(raw, value=42),
             "raw stdout payload contradicts frozen"),
            ("missing-callback", lambda raw: self._change_stdout(
                raw, callbacks=["initialized", "rendered", "completed"]),
             "raw stdout payload contradicts frozen"),
            ("fake-success", lambda raw: raw.update(
                effect_hex=b"hidden-effect".hex(),
                effect_size_bytes=len(b"hidden-effect"),
                effect_sha256=hashlib.sha256(b"hidden-effect").hexdigest()),
             "observable effect bytes/hash contradict frozen"),
            ("wrong-result", lambda raw: raw.update(
                nonce="0" * 32,
                nonce_sha256=hashlib.sha256(("0" * 32).encode()).hexdigest()),
             "stdout nonce not bound"),
            ("wrong-result", self._reuse_positive_control_nonce,
             "reused nonce"),
            ("crash", self._forge_output,
             "nonreturning/missing process unexpectedly produced stdout"),
            ("hang", self._forge_output,
             "nonreturning/missing process unexpectedly produced stdout"),
            ("missing-executable", self._forge_output,
             "nonreturning/missing process unexpectedly produced stdout"),
        )
        for case, mutate, reason in scenarios:
            with self.subTest(case=case, expected=reason):
                self._reset_to_honest_fixture()
                self._rewrite_fault_raw_and_retie_every_digest(case, mutate)
                self.assertEqual(self.assert_rejected(reason).status, "FAIL")

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

    def test_fault_deadline_and_elapsed_forgeries_fail_after_all_hashes_are_retied(self):
        for case in ("hang", "wrong-result", "control"):
            for field, value, reason in (
                ("timeout_seconds", None, "deadline must be finite and bounded"),
                ("timeout_seconds", True, "deadline must be finite and bounded"),
                ("timeout_seconds", "1.5", "deadline must be finite and bounded"),
                ("timeout_seconds", 0.05, "deadline must be finite and bounded"),
                ("timeout_seconds", 10000000, "deadline must be finite and bounded"),
                ("elapsed_ms", -1, "elapsed time must be finite and nonnegative"),
                ("elapsed_ms", True, "elapsed time must be finite and nonnegative"),
                ("elapsed_ms", "1500", "elapsed time must be finite and nonnegative"),
            ):
                with self.subTest(case=case, field=field, value=value):
                    self._reset_to_honest_fixture()
                    self._rewrite_fault_raw_and_retie_every_digest(
                        case, lambda raw: raw.update({field: value}))
                    self.assertEqual(self.assert_rejected(reason).status, "FAIL")
        self._reset_to_honest_fixture()
        self._rewrite_fault_raw_and_retie_every_digest("hang", lambda raw: raw.update(elapsed_ms=0))
        self.assertEqual(self.assert_rejected("does not establish the claimed deadline expiry").status, "FAIL")

    def test_invented_positive_control_rejected_even_when_rehashed(self):
        """Success claims cannot contradict the real callback, result, or effect."""
        scenarios = (
            (lambda raw: raw.update(
                oracle_rejected=True, observed_detection="fake-success"),
             "raw positive control lacks genuine success"),
            (lambda raw: self._change_stdout(raw, value=41),
             "raw stdout payload contradicts frozen"),
            (lambda raw: self._change_stdout(raw, callbacks=[]),
             "raw stdout payload contradicts frozen"),
            (lambda raw: raw.update(
                effect_hex=(b"not-the-rendered-effect" ).hex(),
                effect_size_bytes=len(b"not-the-rendered-effect"),
                effect_sha256=hashlib.sha256(b"not-the-rendered-effect").hexdigest()),
             "observable effect bytes/hash contradict frozen"),
        )
        for mutate, reason in scenarios:
            with self.subTest(expected=reason):
                self._reset_to_honest_fixture()
                self._rewrite_fault_raw_and_retie_every_digest("control", mutate)
                self.assertEqual(self.assert_rejected(reason).status, "FAIL")

    def test_skipped_tests_do_not_count_as_green(self):
        self.job("toolchain")["skipped"] = 1
        self.assertEqual(self.assert_rejected("failed or skipped cases").status, "FAIL")

    def test_empty_test_discovery_is_blocked(self):
        self.job("source")["discovered"] = 0
        self.assert_rejected("source: missing/insufficient actual discovered or executed assertions")

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
            publication_checker=self.confirmed_run,
        )
        self.assertEqual(findings.status, "FAIL")

    def test_unavailable_authenticated_github_run_is_blocked(self):
        import urllib.error
        def unreachable(*_args):
            raise urllib.error.URLError("offline")
        findings = gate.validate_document(
            self.manifest, self.inventory, self.root, CONTRACT, COMMIT,
            run_checker=unreachable, jobs_checker=self.confirmed_run,
            publication_checker=self.confirmed_run,
        )
        self.assertEqual(findings.status, "BLOCKED")
        self.assertIn("cannot authenticate original Actions run",
                      "\n".join(findings.blockers))

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

        # Exercise the *real* Actions ZIP verifier with only the GitHub HTTP
        # download replaced by in-memory bytes. It never extracts archives.
        source = b'{"status":"PASS","physical":true}\n'
        sha = hashlib.sha256(source).hexdigest()
        expected = {"source-summary.json": (sha, len(source))}
        stage = {"role": "source", "path": f"p004-source-{COMMIT}"}
        regular = 0o100644
        symlink = 0o120777
        directory = 0o040755

        def archive(entries) -> bytes:
            result = io.BytesIO()
            with warnings.catch_warnings(), zipfile.ZipFile(result, "w") as zipped:
                warnings.simplefilter("ignore", UserWarning)
                for name, raw, mode in entries:
                    member = zipfile.ZipInfo(name)
                    member.external_attr = mode << 16
                    zipped.writestr(member, raw)
            return result.getvalue()

        def inspect_original(raw_zip, entry_stage=stage, wanted=expected):
            digest = "sha256:" + hashlib.sha256(raw_zip).hexdigest()
            in_memory = mock.Mock(open=lambda *_args, **_kwargs: io.BytesIO(raw_zip))
            with mock.patch.object(gate.tempfile, "TemporaryFile",
                                   side_effect=lambda **kwargs: io.BytesIO()), \
                 mock.patch.object(gate.urllib.request, "build_opener",
                                   return_value=in_memory):
                return gate.verify_original_zip(
                    "boop-bip80/MAC-OS-EMULATION", 123456, digest,
                    entry_stage, {}, None, expected_members=wanted,
                )

        valid = archive([("source-summary.json", source, regular)])
        ok, detail = inspect_original(valid)
        self.assertTrue(ok, detail)
        cases = (
            ("path-traversal", archive([
                ("source-summary.json", source, regular),
                ("../escape", b"x", regular)]), "unsafe original ZIP entry"),
            ("unlisted-directory", archive([
                ("source-summary.json", source, regular),
                ("unlisted/", b"", directory)]), "unlisted original ZIP directory"),
            ("duplicate-member", archive([
                ("source-summary.json", source, regular),
                ("source-summary.json", source, regular)]),
             "unexpected, duplicate or nonregular ZIP member"),
            ("symlink-disguised-as-file", archive([
                ("source-summary.json", source, symlink)]),
             "unexpected, duplicate or nonregular ZIP member"),
            ("corrupt-zip", b"not-a-zip-file",
             "corrupt original ZIP archive"),
            ("wrong-uploaded-bytes", archive([
                ("source-summary.json", b"different\n", regular)]),
             "original ZIP member byte count changed"),
        )
        for label, raw_zip, expected_failure in cases:
            with self.subTest(archive=label):
                passed, detail = inspect_original(raw_zip)
                self.assertFalse(passed, detail)
                self.assertIn(expected_failure, detail)

        # Resolver ZIP is separately bound to the independently inventoried
        # source-equivalence proof, never to arbitrary resolver metadata.
        resolver = {"role": "resolver", "path": f"p004-resolver-{COMMIT}"}
        proof = b'{"source_equivalence":"PASS"}\n'
        proof_members = {"source-equivalence.json": (
            hashlib.sha256(proof).hexdigest(), len(proof))}
        control = archive([("source-equivalence.json", proof, regular)])
        accepted, detail = inspect_original(control, resolver, proof_members)
        self.assertTrue(accepted, detail)
        forged = archive([("source-equivalence.json", proof, regular),
                          ("unlisted-extra.json", b"fake", regular)])
        accepted, detail = inspect_original(forged, resolver, proof_members)
        self.assertFalse(accepted, detail)
        self.assertIn("unexpected, duplicate or nonregular ZIP member", detail)

        # GitHub API artifact downloads redirect to a signed blob host.
        # The redirected request must never leak credentials cross-origin.
        protected = gate.urllib.request.Request(
            "https://api.github.com/repos/boop-bip80/MAC-OS-EMULATION/actions/artifacts/123/zip",
            headers={
                "Authorization": "Bearer synthetic-token",
                "Proxy-Authorization": "Basic synthetic-proxy",
                "Cookie": "synthetic-session=1",
                "Accept": "application/vnd.github+json",
            },
        )
        handler = gate.SafeArtifactRedirectHandler()
        same = handler.redirect_request(
            protected, None, 302, "Found", {},
            "https://api.github.com/repos/boop-bip80/MAC-OS-EMULATION/same-host",
        )
        self.assertEqual(same.get_header("Authorization"), "Bearer synthetic-token")
        self.assertEqual(same.get_header("Cookie"), "synthetic-session=1")
        self.assertEqual(same.get_header("Proxy-authorization"), "Basic synthetic-proxy")
        external = handler.redirect_request(
            protected, None, 302, "Found", {},
            "https://objects.githubusercontent.com/signed-zip",
        )
        for secret in ("Authorization", "Proxy-authorization", "Cookie"):
            with self.subTest(redirect_header=secret):
                self.assertIsNone(external.get_header(secret))
        self.assertEqual(external.get_header("Accept"), "application/vnd.github+json")
        with self.assertRaisesRegex(gate.urllib.error.URLError, "non-HTTPS"):
            handler.redirect_request(
                protected, None, 302, "Found", {},
                "http://objects.githubusercontent.com/insecure-download",
            )

    def test_duplicate_job_is_rejected(self):
        self.manifest["jobs"].append(copy.deepcopy(self.manifest["jobs"][0]))
        self.assertEqual(self.assert_rejected("duplicate job").status, "FAIL")


class PredecessorReviewSemanticsTests(unittest.TestCase):
    """Rehash contradictory review bytes so rejection cannot be a stale hash."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p004-review-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.records = []
        self.reviews = []
        for index, phase in enumerate(CONTRACT["predecessor_phases"]):
            review = {
                "schema_version": 1, "phase": phase, "source_commit": COMMIT,
                "verdict": "PASS", "reviewer": "independent-reviewer",
                "author": "separate-author", "reviewed_at": "2026-11-03T17:00:00Z",
                "run_id": RUN_ID + index + 1,
                "workflow_path": CONTRACT["predecessor_workflows"][phase],
                "conclusion": "success", "event": "push", "head_branch": "main",
                "jobs": [{"name": name, "conclusion": "success"}
                         for name in CONTRACT["predecessor_jobs"][phase]],
            }
            self.reviews.append(review)
            record = {key: review[key] for key in (
                "phase", "source_commit", "reviewer", "author", "reviewed_at",
                "run_id", "workflow_path", "conclusion")}
            record["status"] = "PASS"
            record["evidence"] = write_json(self.root, phase + ".json", review)
            self.records.append(record)

    def check(self, first_review=None):
        if first_review is not None:
            self.records[0]["evidence"] = write_json(self.root, "P001.json", first_review)
        findings = gate.Findings()
        gate.validate_predecessors(self.root, self.records, CONTRACT, COMMIT, findings,
                                   lambda *_: (True, "unit-test authenticated-run response"))
        return findings

    def test_genuine_complete_review_schema_is_accepted(self):
        findings = self.check()
        self.assertEqual(findings.status, "PASS", findings.failures)

    def test_empty_or_nonobject_review_cannot_be_acceptance(self):
        for review in ({}, [], "PASS"):
            with self.subTest(review=review):
                self.assertEqual(self.check(review).status, "FAIL")

    def test_review_verdict_schema_and_identity_are_bound(self):
        for field, value in (
            ("schema_version", True), ("schema_version", 2), ("verdict", "FAIL"),
            ("phase", "P003"), ("source_commit", "b" * 40),
            ("run_id", RUN_ID + 99), ("run_id", True),
            ("workflow_path", ".github/workflows/unrelated.yml"),
            ("conclusion", "failure"), ("reviewer", "another-reviewer"),
            ("author", "another-author"), ("reviewed_at", "2026-11-04T17:00:00Z"),
            ("event", "pull_request"), ("head_branch", "unreviewed-branch"),
        ):
            with self.subTest(field=field):
                review = copy.deepcopy(self.reviews[0])
                review[field] = value
                self.assertEqual(self.check(review).status, "FAIL")

    def test_review_requires_exact_unique_successful_jobs(self):
        jobs = self.reviews[0]["jobs"]
        for replacement in (None, [], jobs[:-1], [jobs[0], jobs[0]],
                            [{**job, "conclusion": "skipped"} for job in jobs],
                            [{"name": "unrelated", "conclusion": "success"}],
                            [{"name": [], "conclusion": "success"}]):
            with self.subTest(jobs=replacement):
                review = copy.deepcopy(self.reviews[0])
                review["jobs"] = replacement
                findings = self.check(review)
                self.assertEqual(findings.status, "FAIL")
                self.assertTrue(any("prerequisite jobs" in reason for reason in findings.failures))


if __name__ == "__main__":
    unittest.main()
