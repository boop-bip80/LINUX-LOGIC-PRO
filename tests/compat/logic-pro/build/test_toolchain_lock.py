"""Adversarial checks for immutable P003 package/image/tool identity."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "tools/compat/logic-pro/lock_toolchain.py"
SPEC = importlib.util.spec_from_file_location("p003_lock_toolchain", SCRIPT)
LOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOCK)


def valid_lock():
    return {
        "schema": LOCK.SCHEMA,
        "base_image": "ubuntu@sha256:" + "a" * 64,
        "image_id": "sha256:" + "b" * 64,
        "ubuntu_snapshot": "20261031T000000Z",
        "recipe_sha256": hashlib.sha256(b"recipe").hexdigest(),
        "environment": {
            "architecture": "amd64", "os_release": 'ID=ubuntu\nVERSION_ID="22.04"\n',
            "apt_sources": "snapshot-fixture",
            "packages": [{"name": "clang-14", "version": "1:14.0.0-1ubuntu1.1", "architecture": "amd64"}],
            "tools": {name: {"sha256": "d" * 64, "version_output": "fixture", "path": "/usr/bin/fixture", "command": argv}
                      for name, argv in LOCK.TOOLS.items()},
        },
        "image_archive": {"file": "toolchain-image.tar.gz", "bytes": 7,
                          "sha256": hashlib.sha256(b"archive").hexdigest()},
    }


class ToolchainLockTests(unittest.TestCase):
    def test_only_explicit_llvm_host_cpu_value_is_host_dependent(self):
        frozen = valid_lock()["environment"]
        frozen["tools"]["dsymutil"]["version_output"] = "Ubuntu LLVM version 14.0.0\n  Default target: x86_64-pc-linux-gnu\n  Host CPU: (unknown)"
        actual = copy.deepcopy(frozen)
        actual["tools"]["dsymutil"]["version_output"] = frozen["tools"]["dsymutil"]["version_output"].replace("(unknown)", "znver3")
        self.assertEqual(LOCK.environment_identity(frozen), LOCK.environment_identity(actual))
        self.assertIn("Host CPU: (unknown)", frozen["tools"]["dsymutil"]["version_output"])
        for field, value in (("version_output", "LLVM version 15\n  Host CPU: znver3"),
                             ("sha256", "e" * 64), ("path", "/tmp/other-tool")):
            changed = copy.deepcopy(actual)
            changed["tools"]["dsymutil"][field] = value
            self.assertNotEqual(LOCK.environment_identity(frozen), LOCK.environment_identity(changed))

    def test_repeated_host_cpu_lines_and_missing_static_fields_are_rejected(self):
        value = valid_lock()["environment"]
        value["tools"]["dsymutil"]["version_output"] = "LLVM14\nHost CPU: first\nHost CPU: second"
        with self.assertRaises(ValueError):
            LOCK.environment_identity(value)
        value["tools"]["dsymutil"]["version_output"] = "LLVM14\nHost CPU: first"
        changed = copy.deepcopy(value)
        changed["tools"]["dsymutil"]["version_output"] = "LLVM14"
        self.assertNotEqual(LOCK.environment_identity(value), LOCK.environment_identity(changed))

    def test_complete_observed_identity_is_accepted(self):
        LOCK.validate(valid_lock())

    def test_tag_only_and_nonubuntu_digest_are_rejected(self):
        for image in ("ubuntu:22.04", "ubuntu@sha256:" + "a" * 63,
                      "untrusted@sha256:" + "a" * 64):
            with self.subTest(image=image):
                value = valid_lock()
                value["base_image"] = image
                with self.assertRaises(ValueError):
                    LOCK.validate(value)

    def test_apt_command_injection_is_rejected(self):
        for field, bad in (("name", "--allow-unauthenticated"), ("version", "1;touch /tmp/injected"),
                           ("architecture", "amd64 --yes"), ("version", "$(id)")):
            with self.subTest(field=field, bad=bad):
                value = valid_lock()
                value["environment"]["packages"][0][field] = bad
                with self.assertRaises(ValueError):
                    LOCK.validate(value)

    def test_missing_and_duplicate_packages_are_rejected(self):
        for packages in ([], valid_lock()["environment"]["packages"] * 2):
            value = valid_lock()
            value["environment"]["packages"] = packages
            with self.assertRaises(ValueError):
                LOCK.validate(value)

    def test_incomplete_tool_identity_is_rejected(self):
        value = valid_lock()
        value["environment"]["tools"]["clang"]["sha256"] = "not-a-hash"
        with self.assertRaises(ValueError):
            LOCK.validate(value)
        del value["environment"]["tools"]["clang"]
        with self.assertRaises(ValueError):
            LOCK.validate(value)

    def test_half_installed_packages_fail(self):
        for record in ("clang\t14\tamd64\tiU ", "clang\t14\tamd64\trc ", "", "clang\t14\tamd64"):
            with self.subTest(record=record), self.assertRaises(ValueError):
                LOCK.parse_packages(record)

    def test_package_order_is_canonical_and_duplicates_fail(self):
        parsed = LOCK.parse_packages("zlib1g\t1.2\tamd64\tii \nclang\t14\tamd64\tii \n")
        self.assertEqual([p["name"] for p in parsed], ["clang", "zlib1g"])
        with self.assertRaises(ValueError):
            LOCK.parse_packages("clang\t14\tamd64\tii \nclang\t15\tamd64\tii \n")

    def test_archive_byte_mutation_is_rejected_even_with_same_length(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock.json"
            archive = root / "toolchain-image.tar.gz"
            lock.write_text(json.dumps(valid_lock()))
            archive.write_bytes(b"archive")
            command = [sys.executable, str(SCRIPT), "verify-archive", "--lock", str(lock), "--archive", str(archive)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            archive.write_bytes(b"archivE")
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_same_packages_different_compiler_bytes_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock.json"
            recipe = root / "Dockerfile"
            value = valid_lock()
            lock.write_text(json.dumps(value))
            recipe.write_bytes(b"recipe")
            altered = copy.deepcopy(value["environment"])
            altered["tools"]["clang"]["sha256"] = "e" * 64
            argv = [str(SCRIPT), "verify", "--lock", str(lock), "--recipe", str(recipe)]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(LOCK, "observed", return_value=altered):
                self.assertEqual(LOCK.main(), 1)

    def test_rebuild_allows_image_serialization_changes_but_not_package_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = valid_lock()
            new = copy.deepcopy(old)
            new["image_id"] = "sha256:" + "f" * 64
            new["image_archive"]["sha256"] = "c" * 64
            lock, candidate = root / "old.json", root / "new.json"
            lock.write_text(json.dumps(old))
            candidate.write_text(json.dumps(new))
            command = [sys.executable, str(SCRIPT), "compare-environment", "--lock", str(lock), "--candidate", str(candidate)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            new["environment"]["packages"][0]["version"] = "999"
            candidate.write_text(json.dumps(new))
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_pin_output_preserves_epoch_architecture_and_exact_version(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "lock.json"
            lock.write_text(json.dumps(valid_lock()))
            result = subprocess.run([sys.executable, str(SCRIPT), "recipe-pins", "--lock", str(lock)],
                                    capture_output=True, text=True, check=True)
            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 3)
            self.assertEqual(lines[2], "clang-14:amd64=1:14.0.0-1ubuntu1.1")


if __name__ == "__main__":
    unittest.main()
