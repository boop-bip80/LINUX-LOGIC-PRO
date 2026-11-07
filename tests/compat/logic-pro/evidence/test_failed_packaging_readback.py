"""Oversized packaging logs retain exact bytes and independently usable context."""
import gzip
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("failed_packaging_readback", TOOLS / "read_failed_packaging_logs.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PackagingReadbackTests(unittest.TestCase):
    def test_compression_preserves_every_original_byte(self):
        raw = b"compiler output\r\nsource.cc:2: error: broken\nnon-utf8 \xff\n"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "job.log.gz"
            result = MODULE.preserve_stream(io.BytesIO(raw), target)
            self.assertEqual(gzip.decompress(target.read_bytes()), raw)
            self.assertEqual(result["raw_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["raw_size_bytes"], len(raw))
            self.assertEqual(result["error_context"][0]["line"], 2)

    def test_excerpts_are_bounded_without_truncating_original_log(self):
        raw = (b"error: " + b"a" * 5000 + b"\n") * 150
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "job.log.gz"
            result = MODULE.preserve_stream(io.BytesIO(raw), target)
            self.assertEqual(gzip.decompress(target.read_bytes()), raw)
            self.assertEqual(result["line_count"], 150)
            self.assertEqual(len(result["error_context"]), 100)
            self.assertEqual(len(result["tail"]), 60)
            self.assertEqual(result["error_context"][0]["line"], 51)
            self.assertTrue(all(e["truncated"] and len(e["text"]) == 4096 for e in result["tail"]))

    def test_previous_log_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "job.log.gz"
            target.write_bytes(b"previous")
            with self.assertRaises(FileExistsError):
                MODULE.preserve_stream(io.BytesIO(b"new\n"), target)
            self.assertEqual(target.read_bytes(), b"previous")

    def test_only_failed_public_packaging_main_pushes_are_selected(self):
        run = {"id": 123, "path": ".github/workflows/actions.yaml", "event": "push",
               "head_branch": "main", "status": "completed", "conclusion": "failure",
               "repository": {"full_name": "owner/repository"},
               "head_repository": {"full_name": "owner/repository"}, "head_sha": "a" * 40}
        MODULE.validate_run("owner/repository", 123, run)
        for key, value in (("path", ".github/workflows/private-reference.yml"),
                           ("event", "pull_request"), ("head_branch", "untrusted"),
                           ("conclusion", "success"), ("status", "in_progress"),
                           ("head_repository", {"full_name": "other/repository"})):
            with self.subTest(key=key), self.assertRaises(ValueError):
                MODULE.validate_run("owner/repository", 123, dict(run, **{key: value}))


if __name__ == "__main__":
    unittest.main()
