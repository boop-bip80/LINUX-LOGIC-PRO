"""Real Git object corruption must not satisfy the restricted CRLF waiver."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import check_submodules
import inventory


class CommittedBlobIntegrity(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="p002-object-integrity-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def git(self, repo, *args, data=None):
        return subprocess.check_output(
            ["git", "-c", "core.autocrlf=false", "-c", "core.hooksPath=/dev/null",
             "-C", str(repo), *args], input=data, stderr=subprocess.PIPE,
            env=inventory.git_environment())

    def repository(self, object_format="sha1"):
        repo = self.root / object_format
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main", "--object-format=" + object_format)
        self.git(repo, "config", "user.name", "P002 Integrity Fixture")
        self.git(repo, "config", "user.email", "fixture@example.invalid")
        return repo

    def corrupt_blob(self, repo, oid, data):
        loose = repo / ".git" / "objects" / oid[:2] / oid[2:]
        loose.chmod(0o644)
        loose.write_bytes(zlib.compress(b"blob " + str(len(data)).encode("ascii") + b"\0" + data))

    def crlf_repository(self):
        repo = self.repository()
        (repo / ".gitattributes").write_bytes(b"project.vcxproj text eol=crlf\n")
        (repo / "project.vcxproj").write_bytes(b"original\n")
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", "fixture")
        return repo, inventory.tree_entries(repo, "HEAD")

    def test_valid_empty_binary_and_duplicate_blobs_in_both_object_formats(self):
        for object_format in ("sha1", "sha256"):
            with self.subTest(object_format=object_format):
                repo = self.repository(object_format)
                expected = {}
                for data in (b"", b"ordinary\n", b"\0binary\r\n\xff"):
                    oid = self.git(repo, "hash-object", "-w", "--stdin", data=data).decode().strip()
                    expected[oid] = data
                self.assertEqual(inventory.read_blobs(repo, list(expected) * 2), expected)
                self.assertEqual(inventory.read_blobs(repo, []), {})

    def test_rejects_real_corrupt_loose_blobs_in_both_object_formats(self):
        for object_format in ("sha1", "sha256"):
            with self.subTest(object_format=object_format):
                repo = self.repository(object_format)
                oid = self.git(repo, "hash-object", "-w", "--stdin", data=b"original\n").decode().strip()
                self.corrupt_blob(repo, oid, b"forged!!\n")
                # cat-file reports the requested OID even when its bytes are corrupt.
                self.assertEqual(self.git(repo, "cat-file", "blob", oid), b"forged!!\n")
                with self.assertRaisesRegex(inventory.InventoryError, "content does not match its object ID"):
                    inventory.read_blobs(repo, [oid])

    def test_valid_committed_crlf_checkout_remains_accepted(self):
        repo, entries = self.crlf_repository()
        (repo / "project.vcxproj").write_bytes(b"original\r\n")
        actual = check_submodules.verify_checkout(repo, entries, [], repo)
        self.assertEqual(actual["verified_blobs"], 2)
        self.assertEqual(actual["standard_crlf_paths"], ["project.vcxproj"])

    def test_corrupt_object_cannot_authorize_forged_crlf_checkout(self):
        repo, entries = self.crlf_repository()
        oid = next(entry["object"] for entry in entries if entry["path"] == "project.vcxproj")
        self.corrupt_blob(repo, oid, b"forged!!\n")
        (repo / "project.vcxproj").write_bytes(b"forged!!\r\n")
        with self.assertRaisesRegex(inventory.InventoryError, "content does not match its object ID"):
            check_submodules.verify_checkout(repo, entries, [], repo)


if __name__ == "__main__":
    unittest.main()
