#!/usr/bin/env python3
"""Adversarial, synthetic-only tests for the P004 evidence byte inventory.

These fixtures test the verifier; they do NOT claim any Darling binary ran or
that the repository has completed P004. Genuine Actions artifacts are required.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/p004_evidence.py"
SPEC = importlib.util.spec_from_file_location("p004_evidence", MODULE)
assert SPEC and SPEC.loader
p004 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p004)

SHA = "a" * 40
TREE = "b" * 40
RUN = 123456
ATTEMPT = 2


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class P004EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="p004-evidence-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for role, (prefix, anchors) in p004.STAGES.items():
            directory = self.root / (prefix + SHA)
            directory.mkdir()
            for name in anchors:
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic-only-test-fixture\n")
            job = {
                "schema": "darling.p004.job.v1", "phase": "P004",
                "role": role, "name": role,
                "source_commit": SHA, "source_tree": TREE,
                "github_run_id": RUN, "github_run_attempt": ATTEMPT,
                "status": "PASS", "exit_code": 0, "timed_out": False,
                "assertions": [{"name": "synthetic-only", "expected": 1, "actual": 1}],
            }
            if role in ("source", "build-a", "build-b"):
                job["submodule_pin_count"] = 160
            else:
                job["submodule_pin_count"] = None
                job["submodule_verification"] = "bound-to-source-sha-and-tree"
            write_json(directory / "p004-job.json", job)
            for name in ("source-summary.json", "build-summary.json",
                         "runtime-summary.json"):
                if name in anchors:
                    write_json(directory / name, {"source_commit": SHA, "status": "PASS"})
            if role == "source":
                write_json(directory / "fault-matrix.json", {"cases": ["synthetic"]})
            if role == "toolchain":
                image = b"synthetic-container-image-for-parser-test"
                (directory / "toolchain-image.tar.gz").write_bytes(image)
                write_json(directory / "toolchain.lock.json",
                           {"image_archive": {"sha256": sha(image)}})
            if role in ("build-a", "build-b"):
                archive = b"synthetic-runtime-archive-for-parser-test"
                (directory / "runtime-prefix.tar.gz").write_bytes(archive)
                (directory / "runtime-prefix.sha256").write_text(
                    sha(archive) + "  runtime-prefix.tar.gz\n", encoding="utf-8")
            if role == "independent-runtime":
                write_json(directory / "runtime/report.json", {
                    "source_commit": SHA, "status": "PASS",
                    "cases": [{"status": "PASS", "case": str(index)} for index in range(10)],
                })

    def stage(self, role: str) -> Path:
        return self.root / (p004.STAGES[role][0] + SHA)

    def job(self, role: str) -> dict:
        return p004.read_json(self.stage(role) / "p004-job.json")

    def change_job(self, role: str, **changes: object) -> None:
        job = self.job(role)
        job.update(changes)
        write_json(self.stage(role) / "p004-job.json", job)

    def inventory(self) -> dict:
        return p004.inventory(self.root, SHA, RUN, ATTEMPT)

    def test_positive_receipt_cannot_claim_phase_pass(self) -> None:
        report = self.inventory()
        self.assertEqual(report["status"], "EVIDENCE_INVENTORY_VERIFIED")
        self.assertEqual(report["phase_verdict"], "NOT_EVALUATED")
        self.assertTrue(report["requires_independent_review"])
        self.assertEqual(report["source_tree"], TREE)
        self.assertEqual(report["github_run_id"], RUN)
        self.assertEqual(report["retention_days"], 90)
        self.assertEqual({row["role"] for row in report["artifacts"]},
                         set(p004.STAGES))
        self.assertGreater(report["file_count"], 20)
        self.assertGreater(report["total_bytes"], 0)
        self.assertTrue(all(
            len(entry["sha256"]) == 64 and entry["size"] >= 0
            for artifact in report["artifacts"] for entry in artifact["files"]))

    def test_missing_stage_is_rejected(self) -> None:
        self.stage("source").rename(self.root / "missing-source")
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_missing_anchor_is_rejected(self) -> None:
        (self.stage("source") / "fault-matrix.json").unlink()
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_empty_anchor_is_rejected(self) -> None:
        (self.stage("source") / "harness.log").write_bytes(b"")
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_wrong_source_commit_is_rejected(self) -> None:
        self.change_job("toolchain", source_commit="e" * 40)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_wrong_run_id_is_rejected(self) -> None:
        self.change_job("build-a", github_run_id=RUN + 1)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_wrong_run_attempt_is_rejected(self) -> None:
        self.change_job("build-b", github_run_attempt=ATTEMPT - 1)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_different_root_tree_is_rejected(self) -> None:
        self.change_job("independent-runtime", source_tree="f" * 40)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_wrong_submodule_count_is_rejected(self) -> None:
        self.change_job("source", submodule_pin_count=159)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_unverified_runtime_must_not_claim_physical_clone(self) -> None:
        self.change_job("independent-runtime", submodule_pin_count=160)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_producer_fake_zero_exit_boolean_is_rejected(self) -> None:
        self.change_job("build-a", exit_code=False)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_missing_observable_assertions_is_rejected(self) -> None:
        self.change_job("build-b", assertions=[])
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_skipped_or_failing_stage_is_rejected(self) -> None:
        for status in ("SKIPPED", "BLOCKED", "FAIL", "UNKNOWN"):
            with self.subTest(status=status):
                self.change_job("source", status=status)
                with self.assertRaises(p004.EvidenceError):
                    self.inventory()

    def test_timeout_is_rejected(self) -> None:
        self.change_job("build-b", timed_out=True)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_runtime_missing_case_is_rejected(self) -> None:
        path = self.stage("independent-runtime") / "runtime/report.json"
        content = p004.read_json(path)
        content["cases"].pop()
        write_json(path, content)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_runtime_fake_case_status_is_rejected(self) -> None:
        path = self.stage("independent-runtime") / "runtime/report.json"
        content = p004.read_json(path)
        content["cases"][3]["status"] = "SKIPPED"
        write_json(path, content)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_modified_runtime_tar_is_rejected(self) -> None:
        with (self.stage("build-b") / "runtime-prefix.tar.gz").open("ab") as f:
            f.write(b"tampered")
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_modified_toolchain_image_is_rejected(self) -> None:
        (self.stage("toolchain") / "toolchain-image.tar.gz").write_bytes(b"tampered")
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_symlink_artifact_is_rejected(self) -> None:
        target = self.stage("source") / "baseline.log"
        (self.stage("source") / "alias.log").symlink_to(target)
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_hardlinked_artifact_is_rejected(self) -> None:
        import os
        target = self.stage("source") / "baseline.log"
        os.link(target, self.stage("source") / "alias.log")
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_private_key_path_is_rejected(self) -> None:
        (self.stage("source") / "activation.privatekey").write_bytes(b"fake")
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_unexpected_stage_is_rejected(self) -> None:
        (self.root / ("p004-unverified-" + SHA)).mkdir()
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_duplicate_json_keys_are_rejected(self) -> None:
        path = self.stage("source") / "p004-job.json"
        path.write_text('{"source_commit":"a","source_commit":"b"}\n')
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_nonfinite_json_is_rejected(self) -> None:
        path = self.stage("source") / "p004-job.json"
        path.write_text('{"source_commit":NaN}\n')
        with self.assertRaises(p004.EvidenceError):
            self.inventory()

    def test_parent_traversal_is_rejected(self) -> None:
        with self.assertRaises(p004.EvidenceError):
            p004.safe_relative("../hidden")

    def test_bad_source_sha_is_rejected(self) -> None:
        with self.assertRaises(p004.EvidenceError):
            p004.inventory(self.root, "unresolved-master", RUN, ATTEMPT)

    def test_bad_run_identity_is_rejected(self) -> None:
        with self.assertRaises(p004.EvidenceError):
            p004.inventory(self.root, SHA, 0, ATTEMPT)


if __name__ == "__main__":
    unittest.main()
