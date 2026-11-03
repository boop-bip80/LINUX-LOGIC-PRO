#!/usr/bin/env python3
"""Adversarial executable tests of P004's real synthetic fault runner.

These tests do not use unittest skip/expectedFailure and never count a fault
fixture's nonzero exit as a successful application workload. The negative
control is only successful when an independent oracle detects it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_fault_matrix import FAULT_EXPECTATIONS, run_case, run_detector, run_matrix


class LiveFaultProcessTests(unittest.TestCase):
    def test_positive_control_has_real_result_and_side_effect(self):
        result = run_case("control")
        self.assertTrue(result["detected"], result)
        self.assertIsNone(result["observed_detection"])
        self.assertFalse(result["oracle_rejected"])
        self.assertEqual(result["observed_process_exit_code"], 0)
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["effect_size_bytes"], len(b"p004-rendered-value=42\n"))

    def test_wrong_result_detected(self):
        result = run_case("wrong-result")
        self.assertTrue(result["detected"], result)
        self.assertEqual(result["observed_detection"], "wrong-result")
        self.assertEqual(result["observed_process_exit_code"], 0)
        self.assertTrue(result["oracle_rejected"])

    def test_crash_detected(self):
        result = run_case("crash")
        self.assertTrue(result["detected"], result)
        self.assertEqual(result["observed_detection"], "process-crash")
        self.assertLess(result["observed_process_exit_code"], 0)
        self.assertTrue(result["oracle_rejected"])

    def test_hang_detected(self):
        result = run_case("hang", timeout_seconds=0.3)
        self.assertTrue(result["detected"], result)
        self.assertEqual(result["observed_detection"], "deadline-exceeded")
        self.assertTrue(result["timed_out"])
        self.assertIsNone(result["observed_process_exit_code"])
        self.assertTrue(result["oracle_rejected"])

    def test_missing_callback_detected(self):
        result = run_case("missing-callback")
        self.assertTrue(result["detected"], result)
        self.assertEqual(result["observed_detection"], "missing-callback")
        self.assertEqual(result["observed_process_exit_code"], 0)
        self.assertGreater(result["effect_size_bytes"], 0)

    def test_missing_executable_detected(self):
        result = run_case("missing-executable")
        self.assertTrue(result["detected"], result)
        self.assertEqual(result["observed_detection"], "missing-executable")
        self.assertIsNone(result["observed_process_exit_code"])
        self.assertFalse(result["timed_out"])

    def test_false_success_without_output_detected(self):
        result = run_case("fake-success")
        self.assertTrue(result["detected"], result)
        self.assertEqual(result["observed_detection"], "no-observable-side-effect")
        self.assertEqual(result["observed_process_exit_code"], 0)
        self.assertEqual(result["effect_size_bytes"], 0)

    def test_all_faults_refuse_undetected_success(self):
        self.assertEqual(len(FAULT_EXPECTATIONS), 6)
        for case, expected in FAULT_EXPECTATIONS.items():
            with self.subTest(case=case):
                result = run_case(case, timeout_seconds=0.3)
                self.assertTrue(result["detected"], result)
                self.assertEqual(result["observed_detection"], expected)
                self.assertTrue(result["oracle_rejected"])

    def test_distinct_runs_have_distinct_challenges(self):
        first = run_case("control")
        second = run_case("control")
        self.assertTrue(first["detected"] and second["detected"])
        self.assertNotEqual(first["nonce_sha256"], second["nonce_sha256"])

    def test_live_detector_cli_exits_are_not_synthesized(self):
        with tempfile.TemporaryDirectory(prefix="p004-cli-") as directory:
            root = Path(directory)
            good_exit, good_report = run_detector(
                "control", root / "control.json", timeout_seconds=0.3
            )
            bad_exit, bad_report = run_detector(
                "wrong-result", root / "bad.json", timeout_seconds=0.3
            )
            self.assertEqual(good_exit, 0)
            self.assertEqual(bad_exit, 1)
            self.assertFalse(good_report["oracle_rejected"])
            self.assertTrue(bad_report["oracle_rejected"])
            self.assertEqual(bad_report["observed_detection"], "wrong-result")

    def test_unsupported_fault_is_not_accepted(self):
        with self.assertRaisesRegex(ValueError, "unknown fault"):
            run_case("arbitrary-green-result")

    def test_unbounded_deadline_is_rejected(self):
        for unsafe in [0.0, 0.05, 30.0]:
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(ValueError, "bounded"):
                    run_case("control", timeout_seconds=unsafe)


class DurableFaultEvidenceTests(unittest.TestCase):
    def test_fault_matrix_status_requires_all_six_observed_failures(self):
        with tempfile.TemporaryDirectory(prefix="p004-test-") as directory:
            summary = run_matrix(Path(directory), timeout_seconds=0.3)
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(summary["control"]["status"], "PASS")
            self.assertEqual(
                {entry["id"] for entry in summary["fault_matrix"]},
                set(FAULT_EXPECTATIONS),
            )
            for entry in summary["fault_matrix"]:
                self.assertEqual(entry["status"], "DETECTED", entry)
                self.assertEqual(entry["detector_exit_code"], 1)

    def test_fault_matrix_artifacts_have_exact_bytes_and_hashes(self):
        with tempfile.TemporaryDirectory(prefix="p004-test-") as directory:
            root = Path(directory)
            summary = run_matrix(root, timeout_seconds=0.3)
            for item in [summary["control"], *summary["fault_matrix"]]:
                artifact = item["artifact"]
                file = (root / artifact["path"]).resolve()
                self.assertTrue(file.is_relative_to(root.resolve()))
                self.assertTrue(file.is_file())
                raw = file.read_bytes()
                self.assertEqual(len(raw), artifact["size_bytes"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), artifact["sha256"])
                report = json.loads(raw)
                self.assertEqual(report["detected"], True)

    def test_written_matrix_matches_returned_matrix(self):
        with tempfile.TemporaryDirectory(prefix="p004-test-") as directory:
            root = Path(directory)
            summary = run_matrix(root, timeout_seconds=0.3)
            self.assertEqual(
                json.loads((root / "fault-matrix.json").read_text()),
                summary,
            )
            self.assertEqual(len(summary["fault_matrix"]), 6)

    def test_runner_preserves_unrelated_staged_evidence(self):
        with tempfile.TemporaryDirectory(prefix="p004-test-") as directory:
            root = Path(directory)
            staged = root / "p004-job.json"
            staged.write_text('{"unrelated":true}\n')
            run_matrix(root, timeout_seconds=0.3)
            self.assertEqual(staged.read_text(), '{"unrelated":true}\n')

    def test_fault_reports_preserve_original_process_exit_semantics(self):
        with tempfile.TemporaryDirectory(prefix="p004-test-") as directory:
            root = Path(directory)
            summary = run_matrix(root, timeout_seconds=0.3)
            reports = {
                item["id"]: json.loads((root / item["artifact"]["path"]).read_text())
                for item in summary["fault_matrix"]
            }
            self.assertEqual(reports["wrong-result"]["observed_process_exit_code"], 0)
            self.assertEqual(reports["fake-success"]["observed_process_exit_code"], 0)
            self.assertLess(reports["crash"]["observed_process_exit_code"], 0)
            self.assertTrue(reports["hang"]["timed_out"])
            self.assertIsNone(reports["missing-executable"]["observed_process_exit_code"])


if __name__ == "__main__":
    unittest.main()
