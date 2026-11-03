"""Adversarial, offline tests for review-only original Actions ZIP reader."""
import io
import json
import stat
import unittest
from unittest import mock
import zipfile
import zlib

import verify_original_zips as audit


def zipped(entries):
    """Entries are (name, bytes, mode-or-None) for exact ZIP member attacks."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data, mode in entries:
            member = zipfile.ZipInfo(name)
            member.compress_type = zipfile.ZIP_DEFLATED
            if mode is not None:
                member.create_system = 3
                member.external_attr = mode << 16
            archive.writestr(member, data)
    return io.BytesIO(output.getvalue())


def valid():
    return zipped([("summary.json", b'{"phase":"P001","result":"PASS"}',
                    stat.S_IFREG | 0o644),
                   ("fixture-tests.log", b"17 tests passed", stat.S_IFREG | 0o644)])


class ZipSecurity(unittest.TestCase):
    def test_good_original_member_hash_and_crc(self):
        members, capture, total = audit.inspect_zip(valid(), "artifact")
        self.assertEqual(members["fixture-tests.log"]["sha256"],
                         audit.sha256(b"17 tests passed"))
        self.assertEqual(capture["summary.json"],
                         b'{"phase":"P001","result":"PASS"}')
        self.assertEqual(members["fixture-tests.log"]["crc32"],
                         f"{zlib.crc32(b'17 tests passed'):08x}")
        self.assertEqual(total, sum(v["size"] for v in members.values()))

    def assert_unsafe(self, name, is_dir=False):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([(name, b"" if is_dir else b"x", None)]),
                              "artifact")

    def test_traversal_file(self):
        self.assert_unsafe("../evil.json")

    def test_traversal_directory(self):
        self.assert_unsafe("../../evil/", True)

    def test_absolute_path(self):
        self.assert_unsafe("/outside")

    def test_windows_separator(self):
        self.assert_unsafe(r"folder\secret.txt")

    def test_redundant_component(self):
        self.assert_unsafe("one/./two.txt")

    def test_duplicate_file(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([("same", b"one", None),
                                       ("same", b"two", None)]), "artifact")

    def test_duplicate_directory(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([("same/", b"", None),
                                       ("same/", b"", None)]), "artifact")

    def test_symlink_member(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([("target", b"secret",
                                       stat.S_IFLNK | 0o777)]), "artifact")

    def test_special_device(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([("disk", b"abc",
                                       stat.S_IFBLK | 0o644)]), "artifact")

    def test_uncompressed_byte_limit(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([("huge", b"abc", None)]),
                              "artifact", max_unpacked=2)

    def test_empty_archive(self):
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(zipped([]), "artifact")

    def test_optional_exact_stage_prefix(self):
        member, _, _ = audit.inspect_zip(
            zipped([("artifact/file.txt", b"original", None)]), "artifact")
        self.assertIn("file.txt", member)

    def test_corrupt_original_crc(self):
        image = zipped([("payload.txt", b"hello-data", None)]).getvalue()
        corrupted = image.replace(b"hello-data", b"jello-data")
        # DEFLATE bytes may not contain cleartext: mutate CRC in local header
        # using a stored member if the first replacement has no effect.
        if corrupted == image:
            image_io = io.BytesIO()
            with zipfile.ZipFile(image_io, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("payload.txt", b"hello-data")
            image = image_io.getvalue()
            corrupted = image.replace(b"hello-data", b"jello-data", 1)
        with self.assertRaises(audit.AuditError):
            audit.inspect_zip(io.BytesIO(corrupted), "artifact")


class OriginalMetadata(unittest.TestCase):
    def setUp(self):
        self.item = {
            "id": 123, "name": "p001-ubuntu-22.04-" + "a" * 40,
            "size_in_bytes": 100,
            "digest": "sha256:" + "b" * 64,
            "expired": False,
            "created_at": "2026-11-03T00:00:00Z",
            "expires_at": "2027-02-01T00:00:00Z",
            "workflow_run": {"id": 321},
        }

    def test_original_run_binding(self):
        with mock.patch.object(audit, "pages", return_value=[self.item]):
            record = audit.get_artifact_metadata(
                audit.REPO, 321, (self.item["name"],), "token")
        self.assertEqual(record[self.item["name"]]["id"], 123)

    def test_short_retention_rejected(self):
        item = dict(self.item, expires_at="2026-11-04T00:00:00Z")
        with mock.patch.object(audit, "pages", return_value=[item]):
            with self.assertRaises(audit.AuditError):
                audit.get_artifact_metadata(audit.REPO, 321, (item["name"],), "token")

    def test_wrong_run_id_rejected(self):
        with mock.patch.object(audit, "pages", return_value=[self.item]):
            with self.assertRaises(audit.AuditError):
                audit.get_artifact_metadata(
                    audit.REPO, 999, (self.item["name"],), "token")

    def test_duplicate_upload_rejected(self):
        with mock.patch.object(audit, "pages", return_value=[self.item, self.item]):
            with self.assertRaises(audit.AuditError):
                audit.get_artifact_metadata(
                    audit.REPO, 321, (self.item["name"],), "token")

    def test_original_zip_bytes_and_members_verified(self):
        data = valid().getvalue()
        item = dict(self.item, size_in_bytes=len(data),
                    digest="sha256:" + audit.sha256(data))
        with mock.patch.object(audit.urllib.request, "urlopen",
                               return_value=io.BytesIO(data)), \
             mock.patch.object(audit.tempfile, "TemporaryFile",
                               return_value=io.BytesIO()):
            record = audit.read_archive(audit.REPO, "token", item)
        self.assertEqual(record["original_zip_sha256"], audit.sha256(data))
        self.assertIn("fixture-tests.log", record["members"])

    def test_original_zip_digest_tampering_detected(self):
        data = valid().getvalue()
        item = dict(self.item, size_in_bytes=len(data),
                    digest="sha256:" + "c" * 64)
        with mock.patch.object(audit.urllib.request, "urlopen",
                               return_value=io.BytesIO(data)), \
             mock.patch.object(audit.tempfile, "TemporaryFile",
                               return_value=io.BytesIO()):
            with self.assertRaises(audit.AuditError):
                audit.read_archive(audit.REPO, "token", item)

    def test_original_zip_size_tampering_detected(self):
        data = valid().getvalue()
        item = dict(self.item, size_in_bytes=len(data) + 1,
                    digest="sha256:" + audit.sha256(data))
        with mock.patch.object(audit.urllib.request, "urlopen",
                               return_value=io.BytesIO(data)), \
             mock.patch.object(audit.tempfile, "TemporaryFile",
                               return_value=io.BytesIO()):
            with self.assertRaises(audit.AuditError):
                audit.read_archive(audit.REPO, "token", item)

    def test_missing_archive_blocks(self):
        with mock.patch.object(audit, "pages", return_value=[]):
            with self.assertRaises(audit.EvidenceUnavailable):
                audit.get_artifact_metadata(
                    audit.REPO, 321, (self.item["name"],), "token")

    def test_pr_run_rejected_as_predecessor(self):
        run = {"repository": {"full_name": audit.REPO},
               "path": audit.WORKFLOWS["P001"], "head_sha": "a" * 40,
               "event": "pull_request", "head_branch": "master",
               "status": "completed", "conclusion": "success", "run_attempt": 1}
        with mock.patch.object(audit, "get_json", return_value=run):
            with self.assertRaises(audit.AuditError):
                audit.validate_run(audit.REPO, "P001", 321, "a" * 40, "token")

    def test_queued_run_blocks(self):
        run = {"repository": {"full_name": audit.REPO},
               "path": audit.WORKFLOWS["P001"], "head_sha": "a" * 40,
               "event": "push", "head_branch": "master", "status": "queued",
               "conclusion": None, "run_attempt": 1}
        with mock.patch.object(audit, "get_json", return_value=run):
            with self.assertRaises(audit.EvidenceUnavailable):
                audit.validate_run(audit.REPO, "P001", 321, "a" * 40, "token")


class CrossEvidence(unittest.TestCase):
    def test_bad_p001_checksum_detected(self):
        record = {"name": "p001-test", "members": {
            "checksums.json": {"size": 2, "sha256": "x"},
            "summary.json": {"size": 3, "sha256": "bad"}},
            "_captured": {"checksums.json": json.dumps({
                name: {"bytes": 4, "sha256": "a" * 64}
                for name in ("summary.json", "other1", "other2", "other3", "other4")
            }).encode()}}
        with self.assertRaises(audit.AuditError):
            audit.verify_hash_list(record, p001=True)

    def test_wrong_p004_inventory_member_detected(self):
        source, pub, run = "a" * 40, "b" * 40, 99
        role = "source"
        prefix = f"p004-{role}-{source}"
        stage = {
            "role": role, "files": [
                {"path": "p004-job.json", "sha256": "0" * 64, "size": 10}
            ],
        }
        inventory = {"schema": "darling.p004.evidence-inventory.v1",
                     "source_commit": source, "publication_commit": pub,
                     "github_run_id": run, "github_run_attempt": 1,
                     "artifacts": [stage] * 5}
        resolver = {"name": f"p004-resolver-{pub}",
                    "members": {"source-equivalence.json": {}},
                    "_captured": {"source-equivalence.json": json.dumps({
                        "status": "PASS", "tested_commit": source,
                        "publication_commit": pub}).encode()}}
        source_item = {"name": prefix,
                       "members": {"source-equivalence.json": {}},
                       "_captured": {"source-equivalence.json":
                                     resolver["_captured"]["source-equivalence.json"]}}
        gate = {"name": f"p004-gate-{source}",
                "members": {"inventory.json": {}},
                "_captured": {"inventory.json": json.dumps(inventory).encode()}}
        with self.assertRaises(audit.AuditError):
            audit.review_p004({
                resolver["name"]: resolver,
                source_item["name"]: source_item,
                gate["name"]: gate,
            }, source, pub, run, 1)

    def test_non_doc_publication_diff_rejected(self):
        response = {"status": "ahead", "ahead_by": 1, "behind_by": 0,
                    "files": [{"filename": "tools/compat/logic-pro/check_gates.py",
                               "status": "modified"}]}
        with mock.patch.object(audit, "get_json", return_value=response):
            with self.assertRaises(audit.AuditError):
                audit.review_publication_delta(
                    audit.REPO, "a" * 40, "b" * 40, "token")


if __name__ == "__main__":
    unittest.main()
