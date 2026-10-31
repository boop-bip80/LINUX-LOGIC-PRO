"""Mutation tests ensure a citation check cannot turn absent evidence into success."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/verify_classifications.py"
SPEC = importlib.util.spec_from_file_location("classification_verifier", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.content = b"// example\nint result() { return 0; }\n"
        (self.repo / "source.c").write_bytes(self.content)
        self.git("add", "source.c")
        self.git("commit", "-qm", "fixture")
        self.commit = self.git("rev-parse", "HEAD")
        self.manifest = {"schema_version": 1, "inspected_commit": self.commit,
            "evidence": [{"id": "result", "category": "partial_implementation",
                "observation": "STATIC_SOURCE_INSPECTION", "path": "source.c",
                "line_start": 2, "line_end": 2, "blob_sha1": self.git("rev-parse", "HEAD:source.c"),
                "excerpt_sha256": hashlib.sha256(self.content.splitlines(keepends=True)[1]).hexdigest(),
                "contains": ["return 0;"]}]}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def test_exact_pinned_citation_passes(self):
        result = MODULE.verify(self.repo, self.manifest, "HEAD")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked_count"], 1)

    def test_corrupted_hashes_range_assertion_and_path_fail(self):
        for key, value in (("blob_sha1", "0" * 40), ("excerpt_sha256", "0" * 64),
                           ("line_end", 99), ("contains", ["returns real audio"]),
                           ("contains", []), ("path", "../outside"),
                           ("observation", "EXECUTED")):
            with self.subTest(key=key, value=value):
                modified = copy.deepcopy(self.manifest)
                modified["evidence"][0][key] = value
                self.assertEqual(MODULE.verify(self.repo, modified)["status"], "FAIL")

    def test_empty_evidence_rejected(self):
        self.manifest["evidence"] = []
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.verify(self.repo, self.manifest)

    def test_nonobject_manifest_rejected(self):
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.verify(self.repo, [])

    def test_inherited_git_directory_cannot_redirect_inspection(self):
        with patch.dict("os.environ", {"GIT_DIR": "/not/the/source/git",
                                       "GIT_WORK_TREE": "/not/the/source"}):
            self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")

    def test_duplicate_evidence_rejected(self):
        self.manifest["evidence"] *= 2
        self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "FAIL")

    def test_uncommitted_file_cannot_replace_pinned_source(self):
        (self.repo / "source.c").write_text("uncommitted changed source\n")
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "PASS")

    def test_current_source_drift_requires_new_audit(self):
        (self.repo / "source.c").write_text("int result() { return 1; }\n")
        self.git("commit", "-qam", "changed source")
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "FAIL")
        self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
