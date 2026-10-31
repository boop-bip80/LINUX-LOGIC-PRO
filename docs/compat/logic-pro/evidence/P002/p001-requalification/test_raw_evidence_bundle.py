"""Focused offline tests for the archival reader, using synthetic raw byte streams."""

import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location("p001_archival_reader", Path(__file__).with_name("raw_evidence_bundle.py"))
READER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(READER)


class MultipartReaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p001-multipart-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.checkout = self.base / "checkout"
        self.checkout.mkdir()
        (self.checkout / ".git").mkdir()
        self.evidence = self.checkout / "evidence"
        self.evidence.mkdir()
        self.parts = self.evidence / READER.PARTS_DIRECTORY
        self.parts.mkdir()
        self.raw = bytes(range(256)) * (READER.PART_BYTES * 2 // 256) + b"last-thirteen"
        self.expected = {"path": READER.ARCHIVE, **READER.digest(io.BytesIO(self.raw))}
        self.mapping = {
            "schema_version": 1, "archive_path": READER.ARCHIVE,
            "archive_bytes": len(self.raw), "archive_sha256": self.expected["sha256"],
            "part_bytes": READER.PART_BYTES, "parts": [],
        }
        for index, offset in enumerate(range(0, len(self.raw), READER.PART_BYTES)):
            chunk = self.raw[offset:offset + READER.PART_BYTES]
            name = f"part-{index:03d}.bin"
            (self.parts / name).write_bytes(chunk)
            self.mapping["parts"].append({"path": name, "bytes": len(chunk),
                                         "sha256": hashlib.sha256(chunk).hexdigest()})
        self.write_mapping()

    def write_mapping(self, mapping=None):
        (self.parts / READER.PARTS_MANIFEST).write_text(json.dumps(self.mapping if mapping is None else mapping))

    def reject(self, pattern=None):
        with self.assertRaisesRegex(ValueError, pattern or "."):
            with READER.archive_source(self.evidence, self.expected):
                self.fail("invalid multipart source was yielded")

    def whole(self):
        (self.evidence / READER.ARCHIVE).write_bytes(self.raw)

    def test_whole_only_remains_supported(self):
        self.whole()
        shutil.rmtree(self.parts)
        with READER.archive_source(self.evidence, self.expected) as (path, storage):
            self.assertEqual(path, self.evidence / READER.ARCHIVE)
            self.assertEqual(path.read_bytes(), self.raw)
            self.assertEqual(storage, {"kind": "whole_file", "parts_verified": 0})

    def test_parts_only_exact_bytes_external_temporary_and_cleanup(self):
        before = sorted(str(path.relative_to(self.checkout)) for path in self.checkout.rglob("*"))
        with READER.archive_source(self.evidence, self.expected) as (path, storage):
            self.assertFalse(path.is_relative_to(self.checkout))
            self.assertEqual(path.read_bytes(), self.raw)
            self.assertEqual(storage, {"kind": "ordered_parts", "parts_verified": 3})
            temporary = path.parent
        self.assertFalse(temporary.exists())
        self.assertEqual(before, sorted(str(path.relative_to(self.checkout)) for path in self.checkout.rglob("*")))

    def test_whole_and_parts_both_verified(self):
        self.whole()
        with READER.archive_source(self.evidence, self.expected) as (path, storage):
            self.assertEqual(path.read_bytes(), self.raw)
            self.assertEqual(storage, {"kind": "whole_file_and_ordered_parts", "parts_verified": 3})

    def test_missing_both_representations_rejected(self):
        shutil.rmtree(self.parts)
        self.reject("missing whole archive")

    def test_missing_part_rejected(self):
        (self.parts / "part-001.bin").unlink()
        self.reject("missing, extra, or misnamed")

    def test_extra_part_rejected(self):
        (self.parts / "part-003.bin").write_bytes(b"extra")
        self.reject("missing, extra, or misnamed")

    def test_extra_nonpart_file_rejected(self):
        (self.parts / "unexpected.txt").write_bytes(b"extra")
        self.reject("missing, extra, or misnamed")

    def test_renamed_file_even_with_changed_mapping_rejected(self):
        (self.parts / "part-000.bin").rename(self.parts / "part-zero.bin")
        self.mapping["parts"][0]["path"] = "part-zero.bin"
        self.write_mapping()
        self.reject("missing, extra, or misnamed")

    def test_reordered_mapping_rejected(self):
        self.mapping["parts"].reverse()
        self.write_mapping()
        self.reject("reordered, duplicated, or misnamed")

    def test_duplicate_mapping_rejected(self):
        self.mapping["parts"][1] = copy.deepcopy(self.mapping["parts"][0])
        self.write_mapping()
        self.reject("reordered, duplicated, or misnamed")

    def test_path_escape_rejected(self):
        self.mapping["parts"][0]["path"] = "../part-000.bin"
        self.write_mapping()
        self.reject("reordered, duplicated, or misnamed")

    def test_missing_mapping_entry_rejected(self):
        self.mapping["parts"].pop()
        self.write_mapping()
        self.reject("member count")

    def test_corrupt_part_rejected(self):
        (self.parts / "part-000.bin").write_bytes(b"x" * READER.PART_BYTES)
        self.reject("member digest")

    def test_swapped_last_part_bytes_rejected(self):
        first, last = self.parts / "part-000.bin", self.parts / "part-002.bin"
        original_first, original_last = first.read_bytes(), last.read_bytes()
        first.write_bytes(original_last)
        last.write_bytes(original_first)
        self.reject("member digest")

    def test_false_part_digest_rejected(self):
        self.mapping["parts"][0]["sha256"] = "0" * 64
        self.write_mapping()
        self.reject("member digest")

    def test_nontext_part_digest_rejected(self):
        self.mapping["parts"][0]["sha256"] = ["0" * 64]
        self.write_mapping()
        self.reject("invalid multipart member digest")

    def test_false_part_size_rejected(self):
        self.mapping["parts"][0]["bytes"] -= 1
        self.write_mapping()
        self.reject("member size")

    def test_boolean_part_size_rejected(self):
        self.mapping["parts"][0]["bytes"] = True
        self.write_mapping()
        self.reject("member size")

    def test_wrong_chunk_size_rejected(self):
        self.mapping["part_bytes"] += 1
        self.write_mapping()
        self.reject("chunk size")

    def test_wrong_archive_size_rejected(self):
        self.mapping["archive_bytes"] += 1
        self.write_mapping()
        self.reject("archive identity")

    def test_wrong_archive_digest_rejected(self):
        self.mapping["archive_sha256"] = "0" * 64
        self.write_mapping()
        self.reject("archive identity")

    def test_forged_part_hash_cannot_hide_wrong_assembled_hash(self):
        wrong = b"x" * READER.PART_BYTES
        (self.parts / "part-000.bin").write_bytes(wrong)
        self.mapping["parts"][0]["sha256"] = hashlib.sha256(wrong).hexdigest()
        self.write_mapping()
        created = []
        original = tempfile.TemporaryDirectory
        def observed(*args, **kwargs):
            context = original(*args, **kwargs)
            created.append(Path(context.name))
            return context
        with mock.patch.object(READER.tempfile, "TemporaryDirectory", side_effect=observed):
            self.reject("assembled archive digest")
        self.assertEqual(len(created), 1)
        self.assertFalse(created[0].exists())

    def test_valid_whole_file_does_not_hide_invalid_parts(self):
        self.whole()
        (self.parts / "part-000.bin").write_bytes(b"x" * READER.PART_BYTES)
        self.reject("member digest")

    def test_invalid_whole_file_does_not_hide_behind_valid_parts(self):
        self.whole()
        (self.evidence / READER.ARCHIVE).write_bytes(b"wrong")
        self.reject("compressed archive digest")

    def test_missing_manifest_rejected(self):
        (self.parts / READER.PARTS_MANIFEST).unlink()
        self.reject("multipart manifest")

    def test_nonobject_manifest_rejected(self):
        self.write_mapping([])
        self.reject("manifest must be an object")

    def test_symlinked_manifest_rejected(self):
        original = self.parts / READER.PARTS_MANIFEST
        outside = self.base / "original-manifest.json"
        original.rename(outside)
        original.symlink_to(outside)
        self.reject("multipart manifest")

    def test_symlinked_part_rejected(self):
        original = self.parts / "part-000.bin"
        outside = self.base / "original-part.bin"
        original.rename(outside)
        original.symlink_to(outside)
        self.reject("regular files")

    def test_directory_as_part_rejected(self):
        original = self.parts / "part-000.bin"
        original.unlink()
        original.mkdir()
        self.reject("regular files")

    def test_symlinked_parts_directory_rejected(self):
        outside = self.base / "original-parts"
        self.parts.rename(outside)
        self.parts.symlink_to(outside, target_is_directory=True)
        self.reject("real directory")

    def test_symlinked_whole_file_rejected(self):
        outside = self.base / "original-archive"
        outside.write_bytes(self.raw)
        (self.evidence / READER.ARCHIVE).symlink_to(outside)
        self.reject("regular file")

    def test_in_checkout_tmpdir_is_not_used(self):
        unsafe = self.checkout / "unsafe-temp"
        unsafe.mkdir()
        with mock.patch.object(READER.tempfile, "gettempdir", return_value=str(unsafe)):
            with READER.archive_source(self.evidence, self.expected) as (path, _):
                self.assertFalse(path.is_relative_to(self.checkout))
                self.assertEqual(path.read_bytes(), self.raw)
        self.assertEqual(list(unsafe.iterdir()), [])

    def test_no_external_temp_location_fails_closed(self):
        with mock.patch.object(READER, "protected_roots", return_value={Path("/")}):
            self.reject("outside the source checkout")


if __name__ == "__main__":
    unittest.main(verbosity=2)
