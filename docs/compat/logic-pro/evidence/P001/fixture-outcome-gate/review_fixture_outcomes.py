#!/usr/bin/env python3
"""Independent, offline P001 result-gate review using real unittest processes.

The full source/recovery stages are neutralized only for the narrow integration
experiment; their behavior is independently qualified by the hosted campaigns.
The unittest process and its return code/transcript are real in every case.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from unittest import mock


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
SCRIPT = SOURCE / "tools/compat/logic-pro/run_baseline.py"
SPEC = importlib.util.spec_from_file_location("independently_reviewed_p001", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
HEAD = "f7bd711013d3c41c3eee4ec76926bfe3a152cb46"

CASES = {
    "one_success": ("def test_one(self): self.assertEqual(7 * 6, 42)", True, 1),
    "two_successes": ("def test_one(self): self.assertEqual(7 * 6, 42)\n"
                       "    def test_two(self): self.assertTrue(True)", True, 2),
    "expected_failure": ("@unittest.expectedFailure\n"
                         "    def test_one(self): self.fail('required assertion is false')", False, 1),
    "mixed_expected_failure": ("def test_one(self): self.assertTrue(True)\n"
                               "    @unittest.expectedFailure\n"
                               "    def test_two(self): self.fail('required assertion is false')", False, 2),
    "skipped": ("@unittest.skip('required dependency unavailable')\n"
                "    def test_one(self): self.fail('not executed')", False, 1),
    "mixed_skip": ("def test_one(self): self.assertTrue(True)\n"
                   "    @unittest.skip('required dependency unavailable')\n"
                   "    def test_two(self): self.fail('not executed')", False, 2),
    "unexpected_success": ("@unittest.expectedFailure\n"
                           "    def test_one(self): self.assertTrue(True)", False, 1),
    "failure": ("def test_one(self): self.fail('observable failure')", False, 1),
    "error": ("def test_one(self): raise RuntimeError('observable error')", False, 1),
    "empty": ("pass", False, 0),
}


def execute_case(body: str) -> subprocess.CompletedProcess:
    program = "import unittest\nclass Required(unittest.TestCase):\n    " + body + "\nunittest.main(verbosity=2)\n"
    return subprocess.run([sys.executable, "-B", "-c", program], capture_output=True, check=False, timeout=30)


def gate_accepts(transcript: str) -> tuple[bool, int | None]:
    try:
        return True, MODULE.verify_fixture_transcript(transcript)
    except ValueError:
        return False, None


def campaign_with_fixture(fixture: subprocess.CompletedProcess) -> dict:
    """Exercise the real main() result wiring with independent stages neutral."""
    with tempfile.TemporaryDirectory(prefix="isolated-main-", dir=ROOT) as tmp:
        base = Path(tmp)
        repo, output = base / "repo", base / "evidence"
        docs = repo / "docs/compat/logic-pro"
        (docs / "evidence/P001").mkdir(parents=True)
        (docs / "evidence/P001/remote-snapshot.json").write_text("{}\n")
        retrieval = base / "source-retrieval.json"
        retrieval.write_text("{}\n")

        def neutral_subprocess(command, **kwargs):
            if "unittest" in command:
                return fixture
            if "rev-parse" in command:
                return subprocess.CompletedProcess(command, 0, (HEAD + "\n").encode(), b"")
            if any(str(part).endswith("/inventory.py") for part in command):
                path = Path(command[command.index("--output") + 1])
                manifest = {"source": {"commit": HEAD}, "repositories": [], "submodules": [],
                            "issues": [], "summary": {}, "requirements": {}, "inventory_status": "VALID",
                            "tracked_files": {"sha256": "fixture-independent-stable-manifest"}}
                path.write_text(json.dumps(manifest))
            return subprocess.CompletedProcess(command, 0, b"", b"")

        with mock.patch.object(MODULE.subprocess, "run", side_effect=neutral_subprocess), \
                mock.patch.object(MODULE, "check_reports", return_value={"neutralized_source_review": True}), \
                contextlib.redirect_stdout(io.StringIO()):
            exit_code = MODULE.main(["--repo", str(repo), "--output-dir", str(output),
                                     "--retrieval-report", str(retrieval)])
        summary = json.loads((output / "summary.json").read_text())
        return {"exit_code": exit_code, "result": summary["result"],
                "fixture_tests_executed": summary["fixture_tests_executed"], "failures": summary["failures"]}


def main() -> int:
    records, integration, completed = [], [], {}
    for name, (body, expected, expected_count) in CASES.items():
        result = execute_case(body)
        completed[name] = result
        transcript = (result.stdout + result.stderr).decode("utf-8")
        (ROOT / (name + ".log")).write_text(transcript)
        accepted, count = gate_accepts(transcript)
        assert accepted == expected, (name, accepted, transcript)
        if expected:
            assert count == expected_count
        actual = campaign_with_fixture(result)
        assert (actual["result"] == "PASS") == expected, (name, actual)
        assert (actual["exit_code"] == 0) == expected
        records.append({"case": name, "unittest_exit_code": result.returncode,
                        "expected_acceptance": expected, "parser_acceptance": accepted,
                        "verified_count": count, "transcript_sha256": hashlib.sha256(transcript.encode()).hexdigest()})
        integration.append({"case": name, **actual})

    passed = completed["one_success"]
    contradicted = subprocess.CompletedProcess(passed.args, 7, passed.stdout, passed.stderr)
    actual = campaign_with_fixture(contradicted)
    assert actual["result"] == "FAIL" and actual["exit_code"] == 1
    assert "fixture-tests: exit 7" in actual["failures"]
    integration.append({"case": "plain_OK_but_nonzero_process_exit", **actual})

    plain = (passed.stdout + passed.stderr).decode()
    boundary_cases = {
        "empty_output": "",
        "summary_truncated": plain.removesuffix("OK\n"),
        "qualified_OK_tail": plain.replace("\nOK\n", "\nOK (expected failures=1)\n"),
        "post_summary_error": plain + "ERROR: runner aborted after summary\n",
        "nonzero_count_without_verdict": "Ran 9 tests in 0.001s\n",
    }
    for name, transcript in boundary_cases.items():
        accepted, _ = gate_accepts(transcript)
        assert not accepted, name
        records.append({"case": name, "expected_acceptance": False, "parser_acceptance": accepted})
    historical = "old unrelated diagnostics\nRan 999 tests in 0.1s\n\nOK\n"
    assert gate_accepts(historical + plain) == (True, 1)
    records.append({"case": "earlier_diagnostic_cannot_supply_current_count", "parser_acceptance": True,
                    "verified_count": 1})

    old_helper = MODULE.verify_fixture_transcript

    def historical_predicate(transcript: str) -> int:
        count = re.search(r"Ran ([1-9][0-9]*) tests? in ", transcript)
        if not count or "skipped=" in transcript:
            raise ValueError("historical skipped/empty check")
        return int(count.group(1))

    try:
        MODULE.verify_fixture_transcript = historical_predicate
        old = campaign_with_fixture(completed["expected_failure"])
        assert old["result"] == "PASS" and old["exit_code"] == 0, old
    finally:
        MODULE.verify_fixture_transcript = old_helper
    repaired = campaign_with_fixture(completed["expected_failure"])
    assert repaired["result"] == "FAIL" and repaired["exit_code"] == 1

    report = {
        "schema_version": 1,
        "reviewer": "/root/negative_case_review",
        "base_commit": HEAD,
        "candidate_files_sha256": {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in [SCRIPT, SOURCE / "tests/compat/logic-pro/baseline/test_baseline_gate.py"]},
        "verdict": "PASS_SCOPED_FIX_REVIEW_PENDING_HOSTED_CANDIDATE_REQUALIFICATION",
        "parser_cases": records,
        "campaign_result_cases": integration,
        "mutation": {"name": "restore_original_expected_failure_acceptance",
                     "original_predicate_campaign": old, "fixed_predicate_campaign": repaired,
                     "killed": True},
        "limits": ["Main-path isolation supplies neutral source/inventory evidence; it is not a new full-repository campaign.",
                   "Real subprocess unittest outputs and return codes are the independent verdict oracle.",
                   "No held archive publication or whole-phase acceptance is included."],
    }
    target = ROOT / "review.json"
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"report": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                      "parser_cases": len(records), "campaign_cases": len(integration), "mutation_killed": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
