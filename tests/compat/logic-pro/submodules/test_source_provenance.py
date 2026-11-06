#!/usr/bin/env python3
"""Regressions for the explicit current-source provenance boundary."""

import copy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import source_provenance as provenance  # noqa: E402
from make_submodule_lock import generate  # noqa: E402


class ReviewedSource(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loaded = provenance.load_reviewed_source(ROOT)

    def check(self, historical=None, current=None, review=None):
        return provenance.validate_reviewed_graphs(
            self.loaded["historical_evidence"] if historical is None else historical,
            self.loaded["current_evidence"] if current is None else current,
            self.loaded["review"] if review is None else review)

    def test_complete_review_preserves_history_and_covers_fourteen_changes(self):
        old, new = self.check()
        changed = {path for path in old if old[path] != new[path]}
        self.assertEqual(len(old), 160)
        self.assertEqual(len(new), 160)
        self.assertEqual(len(changed), 14)
        self.assertEqual(sum(new[path]["parent_path"] == "." for path in changed), 13)
        self.assertIn("src/external/metal/deps/indium", changed)
        self.assertEqual(self.loaded["historical_source_anchor"], "4707a919ef304945f7685390a68429242657eb54")
        self.assertEqual(self.loaded["historical_acceptance_anchor"], "89c6c9d85aba6ed1662035e6366298c92ef9c970")
        self.assertEqual(self.loaded["current_source_anchor"], "c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a")

    def test_omitted_extra_duplicate_and_stale_review_records_fail(self):
        for change in ("omitted", "extra", "duplicate", "stale"):
            review = copy.deepcopy(self.loaded["review"])
            if change == "omitted":
                review["records"].pop()
            elif change == "extra":
                review["records"].append(copy.deepcopy(review["records"][0]))
            elif change == "duplicate":
                review["records"][-1] = copy.deepcopy(review["records"][0])
            else:
                review["records"][-1]["path"] = "src/external/AvailabilityVersions"
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(review=review)

    def test_every_reviewed_identity_field_is_binding(self):
        replacements = {"parent_path": "src/external/metal", "public_url": "https://github.com/darlinghq/wrong.git",
                        "old_commit": "0" * 40, "old_tree": "0" * 40,
                        "new_commit": "0" * 40, "new_tree": "0" * 40}
        for field, replacement in replacements.items():
            review = copy.deepcopy(self.loaded["review"])
            review["records"][0][field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(review=review)

    def test_review_anchors_counts_and_digests_are_binding(self):
        replacements = {"source_anchor": "0" * 40, "source_tree": "0" * 40,
                        "historical_lock_source": "0" * 40, "historical_lock_sha256": "0" * 64,
                        "source_retrieval_sha256": "0" * 64, "recursive_pin_changes": 13,
                        "direct_pin_changes": 14, "source_retrieval_recursive_count": 159,
                        "source_retrieval_result": "FAIL", "status": "PASSED"}
        for field, replacement in replacements.items():
            review = copy.deepcopy(self.loaded["review"])
            review[field] = replacement
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(review=review)

    def test_unreviewed_fifteenth_change_fails(self):
        current = copy.deepcopy(self.loaded["current_evidence"])
        current["submodules"][0]["tree"] = "0" * 40
        with self.assertRaises(ValueError):
            self.check(current=current)

    def test_changed_historical_pin_cannot_rewrite_review(self):
        historical = copy.deepcopy(self.loaded["historical_evidence"])
        row = next(row for row in historical["submodules"] if row["path"] == self.loaded["review"]["records"][0]["path"])
        row["commit"] = "0" * 40
        with self.assertRaises(ValueError):
            self.check(historical=historical)

    def test_report_anchors_cannot_move(self):
        for which in ("historical", "current"):
            for field in ("commit", "tree"):
                evidence = copy.deepcopy(self.loaded[which + "_evidence"])
                evidence["source"][field] = "0" * 40
                with self.subTest(which=which, field=field), self.assertRaises(ValueError):
                    self.check(**{which: evidence})

    def test_incomplete_duplicate_or_reparented_source_graph_fails(self):
        for change in ("omitted", "duplicate", "parent", "retrieval"):
            current = copy.deepcopy(self.loaded["current_evidence"])
            if change == "omitted":
                current["submodules"].pop()
            elif change == "duplicate":
                current["submodules"][-1] = copy.deepcopy(current["submodules"][0])
            elif change == "parent":
                row = next(row for row in current["submodules"] if row["parent_path"] != ".")
                row["parent_path"] = "."
            else:
                current["submodules"][0]["retrieval"] = "CACHED"
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(current=current)

    def test_all_evidence_files_require_the_frozen_byte_digest(self):
        files = (provenance.HISTORICAL_REPORT, provenance.CURRENT_REPORT,
                 provenance.CURRENT_MANIFEST, provenance.SOURCE_REVIEW)
        with tempfile.TemporaryDirectory(prefix="p002-provenance-") as directory:
            root = Path(directory)
            for relative in files:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, root / relative)
            for relative in files:
                original = (root / relative).read_bytes()
                (root / relative).write_bytes(original + b"\n")
                with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, "digest differs"):
                    provenance.load_reviewed_source(root)
                (root / relative).write_bytes(original)

    def test_modified_caller_report_cannot_authorize_a_nested_pin(self):
        evidence = copy.deepcopy(self.loaded["current_evidence"])
        row = next(row for row in evidence["submodules"] if row["path"] == "src/external/metal/deps/indium")
        row["tree"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "immutable reviewed source report"):
            generate(ROOT, evidence)

    def test_cli_defaults_use_script_repository_from_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory(prefix="p002-lock-cli-") as directory:
            output = Path(directory) / "lock.json"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/compat/logic-pro/make_submodule_lock.py"),
                                     "--output", str(output)], cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), (ROOT / "docs/compat/logic-pro/submodules.lock.json").read_bytes())

    def test_cli_historical_mode_rejects_current_source_without_output(self):
        with tempfile.TemporaryDirectory(prefix="p002-lock-cli-") as directory:
            output = Path(directory) / "lock.json"
            result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/compat/logic-pro/make_submodule_lock.py"),
                                     "--repo", str(ROOT), "--evidence-mode", "historical", "--output", str(output)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pin changed without new source evidence", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
