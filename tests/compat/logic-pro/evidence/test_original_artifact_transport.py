"""The readback transport preserves original ZIP bytes and their identity."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("original_artifact_transport", TOOLS / "export_original_artifact.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OriginalArtifactTransportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = self.root / "original.zip"
        self.raw = bytes(range(251)) * 3
        self.archive.write_bytes(self.raw)
        self.origin = {"artifact": {"size_in_bytes": len(self.raw),
                                   "digest": "sha256:" + hashlib.sha256(self.raw).hexdigest()}}

    def test_parts_reassemble_the_original_without_repacking(self):
        output = self.root / "parts"
        result = MODULE.split_original(self.archive, output, self.origin, part_bytes=200)
        self.assertEqual(result["status"], "TRANSPORT_ONLY")
        self.assertEqual(result["phase_acceptance"], "NOT_EVALUATED")
        self.assertEqual([p["ordinal"] for p in result["parts"]], [0, 1, 2, 3])
        pieces = []
        for part in result["parts"]:
            raw = (output / part["path"]).read_bytes()
            pieces.append(raw)
            self.assertEqual(len(raw), part["size_bytes"])
            self.assertLessEqual(len(raw), 200)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), part["sha256"])
            self.assertEqual(json.loads((output / part["path"]).with_name("index.json").read_text()), result)
        self.assertEqual(b"".join(pieces), self.raw)

    def test_changed_original_digest_prevents_part_publication(self):
        self.archive.write_bytes(self.raw[::-1])
        output = self.root / "parts"
        with self.assertRaisesRegex(ValueError, "original artifact metadata"):
            MODULE.split_original(self.archive, output, self.origin)
        self.assertFalse(output.exists())

    def test_truncated_original_prevents_part_publication(self):
        self.archive.write_bytes(self.raw[:-1])
        with self.assertRaises(ValueError):
            MODULE.split_original(self.archive, self.root / "parts", self.origin)

    def test_existing_destination_is_not_overwritten(self):
        output = self.root / "parts"
        output.mkdir()
        marker = output / "keep"
        marker.write_text("prior evidence")
        with self.assertRaises(FileExistsError):
            MODULE.split_original(self.archive, output, self.origin)
        self.assertEqual(marker.read_text(), "prior evidence")

    def test_invalid_chunk_bound_is_rejected(self):
        for value in (0, -1, True, MODULE.PART_BYTES + 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MODULE.split_original(self.archive, self.root / "parts", self.origin, part_bytes=value)

    def test_exact_chunk_boundary_produces_no_empty_part(self):
        result = MODULE.split_original(self.archive, self.root / "parts", self.origin, part_bytes=251)
        self.assertEqual([p["size_bytes"] for p in result["parts"]], [251, 251, 251])


class OriginalArtifactIdentityTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.run = {"id": 321, "path": ".github/workflows/compat.yml", "event": "push",
                    "head_branch": "main", "status": "completed", "head_sha": self.sha,
                    "repository": {"full_name": "owner/repository"},
                    "head_repository": {"full_name": "owner/repository"}}
        self.artifact = {"id": 654, "name": "p004-toolchain-" + "b" * 40, "expired": False,
                         "workflow_run": {"id": 321, "head_sha": self.sha},
                         "size_in_bytes": 500, "digest": "sha256:" + "c" * 64}

    def test_docs_publication_may_name_its_distinct_tested_source(self):
        MODULE.validate_origin("owner/repository", 321, self.run, self.artifact)

    def test_pr_wrong_branch_unfinished_or_unrelated_workflow_is_rejected(self):
        for key, value in (("event", "pull_request"), ("head_branch", "untrusted"),
                           ("status", "in_progress"), ("path", ".github/workflows/private-fixtures.yml"),
                           ("head_repository", {"full_name": "other/repository"})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate_origin("owner/repository", 321, dict(self.run, **{key: value}), self.artifact)

    def test_expired_wrong_origin_or_unbounded_archive_is_rejected(self):
        for key, value in (("expired", True), ("name", "unrelated"),
                           ("size_in_bytes", MODULE.MAX_ARCHIVE_BYTES + 1),
                           ("size_in_bytes", True), ("digest", "sha256:bad"),
                           ("workflow_run", {"id": 999, "head_sha": self.sha})):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                MODULE.validate_origin("owner/repository", 321, self.run, dict(self.artifact, **{key: value}))


if __name__ == "__main__":
    unittest.main()
