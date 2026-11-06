"""Real ZIP and shell-path regressions for retained frozen input acquisition."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

from test_toolchain_lock import valid_lock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import restore_toolchain as restore


class RetainedToolchainTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="p003-retained-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / "retained.zip"
        self.manifest = self.root / "retained-toolchain.json"
        self.committed = self.root / "committed.json"
        self.recipe = self.root / "Dockerfile.p003"
        self.output = self.root / "restored"
        self.recipe.write_bytes(b"recipe")
        self.frozen = valid_lock()
        self.committed.write_text(json.dumps(self.frozen))
        self.members = {"base-pull.log": b"original base acquisition\n",
                        "toolchain-build.log": b"original image acquisition\n",
                        "toolchain.lock.json": self.committed.read_bytes(),
                        "toolchain-image.tar.gz": b"archive"}
        self.checksums()
        self.bundle()

    def checksums(self):
        self.members["SHA256SUMS"] = "".join(
            hashlib.sha256(self.members[name]).hexdigest() + "  /original/" + name + "\n"
            for name in ("toolchain.lock.json", "toolchain-image.tar.gz")).encode()

    def bundle(self, extra=()):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_STORED) as bundle:
                for name, content in self.members.items():
                    bundle.writestr(name, content)
                for name, content in extra:
                    bundle.writestr(name, content)
        manifest = {"schema": "darling.p003.retained-toolchain.v1",
                    "repository": "owner/repository", "source_commit": "a" * 40,
                    "run_id": 123, "artifact_id": 456,
                    "artifact_name": "p003-toolchain-" + "a" * 40,
                    "artifact_bytes": self.archive.stat().st_size,
                    "artifact_sha256": restore.lock.sha256(self.archive),
                    "committed_lock_sha256": restore.lock.sha256(self.committed),
                    "recipe_sha256": restore.lock.sha256(self.recipe)}
        self.manifest.write_text(json.dumps(manifest))

    def run_restore(self):
        return restore.restore(self.archive, self.manifest, self.committed, self.recipe, self.output)

    def assert_rejected(self, pattern):
        with self.assertRaisesRegex((ValueError, zipfile.BadZipFile), pattern):
            self.run_restore()
        self.assertFalse(self.output.exists())

    def test_original_files_are_restored_exactly_with_origin_receipt(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/compat/logic-pro/restore_toolchain.py"),
             "restore", "--manifest", str(self.manifest), "--committed-lock", str(self.committed),
             "--recipe", str(self.recipe), "--archive", str(self.archive), "--output", str(self.output)],
            text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        receipt = json.loads(result.stdout.splitlines()[0])
        self.assertEqual(receipt["status"], "PASSED")
        self.assertEqual(receipt["origin"]["artifact_id"], 456)
        for name, content in self.members.items():
            self.assertEqual((self.output / name).read_bytes(), content)
            self.assertEqual(receipt["original_files_sha256"][name], hashlib.sha256(content).hexdigest())
        self.assertEqual(json.loads((self.output / "retained-acquisition.json").read_text()), receipt)

    def test_host_cpu_observation_can_differ_without_losing_original_lock(self):
        self.frozen["environment"]["tools"]["dsymutil"]["version_output"] = "LLVM14\nHost CPU: first"
        self.committed.write_text(json.dumps(self.frozen))
        candidate = copy.deepcopy(self.frozen)
        candidate["environment"]["tools"]["dsymutil"]["version_output"] = "LLVM14\nHost CPU: second"
        candidate["image_id"] = "sha256:" + "f" * 64
        self.members["toolchain.lock.json"] = json.dumps(candidate).encode()
        self.checksums()
        self.bundle()
        self.run_restore()
        self.assertEqual((self.output / "toolchain.lock.json").read_bytes(), self.members["toolchain.lock.json"])

    def test_outer_archive_byte_and_size_changes_are_rejected(self):
        original = self.archive.read_bytes()
        for changed in (original[:-1], bytes([original[0] ^ 1]) + original[1:]):
            with self.subTest(size=len(changed)):
                self.archive.write_bytes(changed)
                self.assert_rejected("pinned regular archive|SHA256 mismatch")

    def test_image_tampering_is_rejected_even_with_rehashed_outer_archive(self):
        for changed in (b"Archive", b"archiv"):
            with self.subTest(image=changed):
                self.members["toolchain-image.tar.gz"] = changed
                self.checksums()
                self.bundle()
                self.assert_rejected("image does not match its sealed lock")

    def test_changed_frozen_inputs_cannot_be_hidden_by_rehashing(self):
        for field in ("compiler", "package", "base_image", "ubuntu_snapshot", "recipe_sha256"):
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.frozen)
                if field == "compiler":
                    candidate["environment"]["tools"]["clang"]["sha256"] = "e" * 64
                elif field == "package":
                    candidate["environment"]["packages"][0]["version"] = "changed"
                else:
                    candidate[field] = {"base_image": "ubuntu@sha256:" + "c" * 64,
                                        "ubuntu_snapshot": "20261101T000000Z",
                                        "recipe_sha256": "c" * 64}[field]
                self.members["toolchain.lock.json"] = json.dumps(candidate).encode()
                self.checksums()
                self.bundle()
                self.assert_rejected("differs from committed inputs")

    def test_missing_duplicate_extra_and_traversing_members_are_rejected(self):
        original = dict(self.members)
        for name in ("missing", "base-pull.log", "unexpected", "../escaped"):
            with self.subTest(member=name):
                self.members = dict(original)
                if name == "missing":
                    self.members.pop("base-pull.log")
                    self.bundle()
                else:
                    self.bundle(extra=((name, b"unexpected"),))
                self.assert_rejected("missing, duplicate or unexpected members")
                self.assertFalse((self.root.parent / "escaped").exists())

    def test_symlink_and_directory_members_are_rejected(self):
        content = self.members.pop("base-pull.log")
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFDIR | 0o755):
            with self.subTest(mode=mode):
                info = zipfile.ZipInfo("base-pull.log")
                info.create_system = 3
                info.external_attr = mode << 16
                self.bundle(extra=((info, content),))
                self.assert_rejected("not a regular file")

    def test_existing_output_and_symlink_targets_are_preserved(self):
        for kind in ("directory", "file", "symlink"):
            with self.subTest(kind=kind):
                sentinel = self.root / "sentinel"
                sentinel.write_bytes(b"keep")
                if kind == "directory":
                    self.output.mkdir()
                    (self.output / "owned").write_bytes(b"keep")
                elif kind == "file":
                    self.output.write_bytes(b"keep")
                else:
                    self.output.symlink_to(sentinel)
                with self.assertRaisesRegex(ValueError, "must not exist"):
                    self.run_restore()
                self.assertEqual(sentinel.read_bytes(), b"keep")
                if kind == "directory":
                    self.assertEqual((self.output / "owned").read_bytes(), b"keep")
                    shutil.rmtree(self.output)
                else:
                    self.assertEqual(self.output.read_bytes(), b"keep")
                    self.output.unlink()

    def test_changed_checksum_receipt_is_rejected(self):
        self.members["SHA256SUMS"] = b"a  /original/toolchain.lock.json\n"
        self.bundle()
        self.assert_rejected("checksum receipt differs")

    def test_stale_committed_lock_and_recipe_are_rejected_before_restoring(self):
        for path in (self.committed, self.recipe):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.assert_rejected("different committed lock|different recipe")
                path.write_bytes(original)

    def test_zip_crc_corruption_is_rejected_after_outer_digest_is_updated(self):
        data = bytearray(self.archive.read_bytes())
        index = data.index(b"original base acquisition")
        data[index] ^= 1
        self.archive.write_bytes(data)
        manifest = json.loads(self.manifest.read_text())
        manifest["artifact_sha256"] = restore.lock.sha256(self.archive)
        self.manifest.write_text(json.dumps(manifest))
        self.assert_rejected("Bad CRC")

    def test_real_acquisition_shell_falls_back_only_for_download_failure(self):
        repo = self.root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        for relative in ("tools/compat/logic-pro/restore_toolchain.py",
                         "tools/compat/logic-pro/lock_toolchain.py", "ci/logic-pro/acquire-toolchain.sh"):
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        configs = repo / "docs/compat/logic-pro"
        configs.mkdir(parents=True)
        shutil.copyfile(self.committed, configs / "toolchain.lock.json")
        shutil.copyfile(self.manifest, configs / "retained-toolchain.json")
        shutil.copyfile(self.recipe, repo / "ci/logic-pro/Dockerfile.p003")
        (repo / "ci/logic-pro/prepare-toolchain.sh").write_text(
            '#!/usr/bin/env bash\nset -eu\nmkdir "$1"\nprintf fallback > "$1/fallback"\n')
        binary = self.root / "bin"
        binary.mkdir()
        curl = binary / "curl"
        curl.write_text('#!/usr/bin/env python3\nimport os,sys\nfrom pathlib import Path\n'
                        'if os.environ["P003_TEST_TRANSFER"] == "unavailable": sys.exit(22)\n'
                        'Path(sys.argv[sys.argv.index("-o")+1]).write_bytes(b"wrong archive")\n')
        curl.chmod(0o755)
        for transfer in ("unavailable", "corrupt"):
            with self.subTest(transfer=transfer):
                output = self.root / transfer
                env = {**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                       "GITHUB_TOKEN": "", "P003_TEST_TRANSFER": transfer}
                result = subprocess.run(["bash", "ci/logic-pro/acquire-toolchain.sh", str(output)],
                                        cwd=repo, env=env, text=True, capture_output=True, timeout=15)
                if transfer == "unavailable":
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual((output / "fallback").read_bytes(), b"fallback")
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
