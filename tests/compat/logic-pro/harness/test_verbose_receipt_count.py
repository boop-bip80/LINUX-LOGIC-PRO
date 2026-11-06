"""The P004 receipt floor must count real unittest passes, not silence.

Silent ``... ok`` lines and passes whose stdout pushed ``ok`` onto the next
line are the same result. A stdout line that says PASS or ok must not invent
a pass, and a later FAIL must win over an earlier stdout line equal to ok.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[4]
SCRIPT = REPO / "ci" / "logic-pro" / "p004-stage-receipt.py"


def load_receipt():
    spec = importlib.util.spec_from_file_location("p004_verbose_receipt_count", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


receipt = load_receipt()


def announce(name: str, status: str = "ok", stdout: str | None = None) -> str:
    qual = f"test_stage_receipt.ReceiptAdversarialTests.{name}"
    if stdout is None:
        return f"{name} ({qual}) ... {status}\n"
    return f"{name} ({qual}) ... {stdout}\n{status}\n"


class VerboseReceiptCountTests(unittest.TestCase):
    def test_multiline_cli_stdout_still_counts_as_one_pass(self):
        transcript = "".join([
            announce(f"test_silent_{index:02d}") for index in range(34)
        ]) + "".join([
            announce("test_real_cli_corrupt_input_never_emits_pass_receipt",
                     stdout="P004 source receipt BLOCKED/FAIL: Missing regular report"),
            announce("test_real_cli_emits_pass_receipt_only_for_verified_stage",
                     stdout='{"status": "PASS", "role": "source"}'),
            announce("test_real_cli_invalid_source_tree_never_emits_pass_receipt",
                     stdout="P004 source receipt BLOCKED/FAIL: Job did not checkout exact source commit and tree"),
            announce("test_real_cli_refuses_existing_success_receipt_overwrite",
                     stdout='{"status": "PASS"}\nP004 source receipt BLOCKED/FAIL: Never overwrite'),
            announce("test_real_cli_wrong_checked_out_commit_never_emits_pass_receipt",
                     stdout="P004 source receipt BLOCKED/FAIL: Job did not checkout exact source commit and tree"),
        ])
        passed = receipt.passing_verbose_unittests(transcript, "test_stage_receipt.")
        self.assertEqual(len(passed), 39)
        self.assertEqual(len(set(passed)), 39)
        self.assertEqual(
            passed.count("test_real_cli_emits_pass_receipt_only_for_verified_stage"), 1)

    def test_stdout_ok_cannot_hide_a_failure(self):
        transcript = announce(
            "test_build_wrong_case_names_cannot_fake_ten_passing_probes",
            status="FAIL",
            stdout="ok",
        )
        passed = receipt.passing_verbose_unittests(transcript, "test_stage_receipt.")
        self.assertEqual(passed, [])

    def test_fail_token_inside_stdout_is_not_the_result_when_ok_follows(self):
        transcript = announce(
            "test_runtime_source_isolation_absent_rejected",
            stdout="P004 source receipt BLOCKED/FAIL: isolation absent",
        )
        passed = receipt.passing_verbose_unittests(transcript, "test_stage_receipt.")
        self.assertEqual(passed, ["test_runtime_source_isolation_absent_rejected"])

    def test_other_modules_and_skipped_cases_do_not_inflate_the_floor(self):
        transcript = (
            "test_other (test_fault_matrix.FaultTests.test_other) ... ok\n"
            "test_skipped (test_stage_receipt.ReceiptAdversarialTests.test_skipped) ... skipped 'no'\n"
            "test_error (test_stage_receipt.ReceiptAdversarialTests.test_error) ... ERROR\n"
        )
        self.assertEqual(receipt.passing_verbose_unittests(transcript, "test_stage_receipt."), [])

    def test_glued_stdout_is_not_treated_as_ok(self):
        transcript = (
            "test_glued (test_stage_receipt.ReceiptAdversarialTests.test_glued) ... notok\n"
        )
        self.assertEqual(receipt.passing_verbose_unittests(transcript, "test_stage_receipt."), [])


if __name__ == "__main__":
    unittest.main()
