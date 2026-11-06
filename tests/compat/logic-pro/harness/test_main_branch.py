#!/usr/bin/env python3
"""Exercise the production Actions validators with mocked API responses only."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "p004_main_gate", ROOT / "tools/compat/logic-pro/check_gates.py")
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

REPOSITORY = "boop-bip80/LINUX-LOGIC-PRO"
SOURCE = "a" * 40
PUBLICATION = "b" * 40
RUN_ID = 123456789
PREDECESSOR_WORKFLOW = ".github/workflows/phase3-build.yml"


class MainBranchRunTests(unittest.TestCase):
    def check_run(self, current, changes=None, **kwargs):
        """Keep metadata, job checks, and actual ZIP hashing/member checks real."""
        run = {
            "repository": {"full_name": REPOSITORY},
            "head_sha": PUBLICATION if current else SOURCE,
            "path": ".github/workflows/compat.yml" if current else PREDECESSOR_WORKFLOW,
            "run_attempt": 1,
            "head_branch": "main",
            "event": "push",
            "status": "completed",
            "conclusion": "success",
        }
        run.update(changes or {})
        proof = b'{"source_equivalence":"PASS"}\n'
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("source-equivalence.json", proof)
        zip_bytes = archive.getvalue()
        stage_path = "p004-source-" + SOURCE
        stages = {"source": {"role": "source", "path": stage_path}}
        listed = {stage_path + "/source-equivalence.json": (
            hashlib.sha256(proof).hexdigest(), len(proof), "source")}
        jobs = [{"name": name, "status": "completed", "conclusion": "success"}
                for name in ("source", "resolve")]
        artifacts = [{
            "id": index,
            "name": name,
            "expired": False,
            "size_in_bytes": len(zip_bytes),
            "digest": "sha256:" + hashlib.sha256(zip_bytes).hexdigest(),
        } for index, name in enumerate(
            (stage_path, "p004-resolver-" + PUBLICATION), start=1)]
        run_url = f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{RUN_ID}"

        def api_response(url, _token=None):
            if url == run_url:
                return run
            if url == run_url + "/jobs?per_page=100&page=1":
                return {"jobs": jobs}
            if url == run_url + "/artifacts?per_page=100&page=1":
                return {"artifacts": artifacts}
            self.fail("Unexpected GitHub API URL: " + url)

        def download(request, timeout):
            self.assertIn(request.full_url, [
                f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{index}/zip"
                for index in (1, 2)])
            return io.BytesIO(zip_bytes)

        opener = mock.Mock(open=download)
        with mock.patch.object(gate, "github_json", side_effect=api_response), \
                mock.patch.object(gate.urllib.request, "build_opener", return_value=opener):
            if current:
                return gate.github_jobs_checker(
                    REPOSITORY, RUN_ID, ["source"], SOURCE, PUBLICATION, 1,
                    stages, listed, **kwargs)
            return gate.github_run_checker(
                REPOSITORY, RUN_ID, SOURCE, PREDECESSOR_WORKFLOW, ["source"], **kwargs)

    def test_active_contract_uses_current_repository(self):
        contract = json.loads((ROOT / "docs/compat/logic-pro/gates.json").read_text())
        self.assertEqual(contract["repository"], REPOSITORY)

    def test_exact_main_push_is_accepted(self):
        for current in (False, True):
            with self.subTest(current=current):
                ok, detail = self.check_run(current)
                self.assertTrue(ok, detail)

    def test_old_feature_and_pull_request_branches_are_rejected(self):
        for current in (False, True):
            for branch in ("master", "feature/qualification", "refs/pull/10/merge"):
                with self.subTest(current=current, branch=branch):
                    ok, detail = self.check_run(current, {"head_branch": branch})
                    self.assertFalse(ok, detail)
                    self.assertIn("main", detail)

    def test_non_push_events_are_rejected_even_on_main(self):
        for current in (False, True):
            for event in ("pull_request", "pull_request_target", "workflow_dispatch"):
                with self.subTest(current=current, event=event):
                    ok, detail = self.check_run(current, {"event": event})
                    self.assertFalse(ok, detail)
                    self.assertIn("push", detail)

    def test_different_repository_sha_and_workflow_are_rejected(self):
        for current in (False, True):
            for changes in (
                {"repository": {"full_name": "boop-bip80/MAC-OS-EMULATION"}},
                {"head_sha": "c" * 40},
                {"path": ".github/workflows/other.yml"},
            ):
                with self.subTest(current=current, changes=changes):
                    ok, detail = self.check_run(current, changes)
                    self.assertFalse(ok, detail)

    def test_current_run_requires_exact_publication_attempt(self):
        ok, detail = self.check_run(True, {"run_attempt": 2})
        self.assertFalse(ok, detail)
        self.assertIn("attempt", detail)

    def test_failed_runs_are_rejected(self):
        for current in (False, True):
            with self.subTest(current=current):
                ok, detail = self.check_run(current, {"conclusion": "failure"})
                self.assertFalse(ok, detail)

    def test_historical_branch_requires_explicit_expectation(self):
        for current in (False, True):
            with self.subTest(current=current):
                ok, detail = self.check_run(
                    current, {"head_branch": "master"}, expected_branch="master")
                self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
