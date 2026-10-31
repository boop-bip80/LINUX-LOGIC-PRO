"""The source-evidence campaign must reject incomplete or inconsistent reports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/run_baseline.py"
SPEC = importlib.util.spec_from_file_location("baseline_campaign", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CampaignEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.snapshot = {"external_tree": {"gitlinks": [{"path": "dep", "sha": "pin"}]},
                         "baseline_commit": "original", "baseline_tree": "original-tree",
                         "integration_commit": "plan", "integration_tree": "plan-tree"}
        self.write("tracked-files.json", {"entries": [{"repository": ".", "path": "dep"}]})
        digest = hashlib.sha256((self.out / "tracked-files.json").read_bytes()).hexdigest()
        self.write("inventory.json", {"source": {"commit": "implementation"},
            "submodules": [{"path": "dep", "commit": "pin", "repository": "."}],
            "summary": {"error_count": 0, "tracked_entries": 1, "unavailable_gitlinks": 1},
            "repositories": [{"worktree_clean": True}], "tracked_files": {"sha256": digest}})
        snapshots = [{"label": label, "commit": self.snapshot[f"{label}_commit"],
                      "tree": self.snapshot[f"{label}_tree"], "working_tree_clean": True,
                      "independent_object_store": True, "verified_blobs": 2,
                      "gitlinks": [{"path": "dep", "commit": "pin"}]} for label in ("baseline", "integration")]
        self.write("recovery.json", {"result": "PASS", "snapshots": snapshots})
        self.write("classifications.json", {"status": "PASS", "checked_count": 3,
                                            "current_commit": "implementation"})

    def write(self, name, value):
        (self.out / name).write_text(json.dumps(value))

    def mutate(self, name, callback):
        value = json.loads((self.out / name).read_text())
        callback(value)
        self.write(name, value)

    def test_consistent_source_reports_pass_without_claiming_runtime(self):
        result = MODULE.check_reports(self.out, self.snapshot)
        self.assertEqual(result["known_gitlinks_verified"], 1)
        self.assertFalse(result["runtime_executed"])
        self.assertIn("REQUIRED", result["independent_review"])

    def test_missing_report_is_not_success(self):
        (self.out / "recovery.json").unlink()
        with self.assertRaises(OSError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_changed_dependency_pin_is_rejected(self):
        self.mutate("inventory.json", lambda v: v["submodules"][0].update(commit="wrong"))
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_forged_recovered_revision_is_rejected(self):
        self.mutate("recovery.json", lambda v: v["snapshots"][0].update(commit="wrong"))
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_shared_object_store_is_rejected(self):
        self.mutate("recovery.json", lambda v: v["snapshots"][1].update(independent_object_store=False))
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_truncated_tracked_manifest_is_rejected(self):
        self.write("tracked-files.json", {"entries": []})
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_stale_citation_revision_is_rejected(self):
        self.mutate("classifications.json", lambda v: v.update(current_commit="stale"))
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_additional_nested_gitlinks_do_not_change_parent_oracle(self):
        self.mutate("inventory.json", lambda v: v["submodules"].append(
            {"path": "dep/child", "commit": "child-pin", "repository": "dep"}))
        self.assertEqual(MODULE.check_reports(self.out, self.snapshot)["known_gitlinks_verified"], 1)

    def test_duplicate_recursive_gitlink_is_rejected(self):
        self.mutate("inventory.json", lambda v: v["submodules"].append(dict(v["submodules"][0])))
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)


if __name__ == "__main__":
    unittest.main()
