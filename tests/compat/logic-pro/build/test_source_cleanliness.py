"""Exercise the real producer EXIT handler and aggregate source-status gate.

Temporary Git repositories and parser fixtures are regression inputs, not
Darling build or runtime qualification evidence.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import compare_p003 as gate


class ProducerSourceCleanlinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="p003-source-cleanliness-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.lock = self.root / "toolchain.lock.json"
        self.lock.write_text("{}\n")
        source_lock = self.source / "docs/compat/logic-pro/submodules.lock.json"
        source_lock.parent.mkdir(parents=True)
        source_lock.write_text("{}\n")
        self.generated = self.source / "generated.txt"
        self.generated.write_text("tracked original\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.commit_source()
        script = (ROOT / "ci/logic-pro/build-p003.sh").read_text()
        self.finish = "finish() {\n" + script.split("finish() {\n", 1)[1].split(
            "\ntrap finish EXIT", 1)[0]

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.source), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    def commit_source(self):
        self.git("-c", "user.name=P003 Test", "-c", "user.email=p003@example.invalid",
                 "commit", "-qm", "source fixture")
        self.commit = self.git("rev-parse", "HEAD").decode().strip()

    def raw_status(self):
        return self.git("status", "--porcelain=v1", "--untracked-files=all",
                        "--ignore-submodules=none")

    def finish_build(self, exit_code=0, stage="complete", umask="022"):
        harness = "\n".join((
            "set -euo pipefail", "source_root=$1", "evidence=$2", "source_commit=$3",
            'lock=$4', 'stage=$5', 'umask "$7"', "export SOURCE_DATE_EPOCH=0", self.finish,
            "trap finish EXIT", 'exit "$6"', ""))
        result = subprocess.run(
            ["bash", "-s", "--", str(self.source), str(self.evidence), self.commit,
             str(self.lock), stage, str(exit_code), umask], input=harness, text=True,
            capture_output=True, timeout=10)
        summary = json.loads((self.evidence / "build-summary.json").read_text())
        return result, summary

    def assert_dirty_failure(self):
        expected = self.raw_status()
        self.assertTrue(expected)
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["last_stage"], "source-cleanliness")
        self.assertEqual(summary["exit_code"], 1)
        self.assertEqual((self.evidence / "source-status-after.txt").read_bytes(), expected)

    def test_clean_source_produces_empty_regular_status_and_pass(self):
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["last_stage"], "complete")
        self.assertEqual(summary["exit_code"], 0)
        status = self.evidence / "source-status-after.txt"
        self.assertTrue(status.is_file())
        self.assertFalse(status.is_symlink())
        self.assertEqual(status.read_bytes(), b"")

    def test_generated_tracked_mutation_fails_and_preserves_raw_status(self):
        self.generated.write_text("generated during build\n")
        self.assert_dirty_failure()

    def test_captured_status_is_uploader_readable_under_restrictive_umasks(self):
        status = self.evidence / "source-status-after.txt"
        for umask in ("022", "077"):
            for dirty in (False, True):
                for original_code in (0, 42):
                    with self.subTest(umask=umask, dirty=dirty, original_code=original_code):
                        self.generated.write_text(
                            "generated during build\n" if dirty else "tracked original\n")
                        expected_status = self.raw_status()
                        original_stage = "compile" if original_code else "complete"
                        result, summary = self.finish_build(
                            exit_code=original_code, stage=original_stage, umask=umask)
                        expected_code = original_code or int(dirty)
                        self.assertEqual(result.returncode, expected_code, result.stderr)
                        self.assertEqual(summary["exit_code"], expected_code)
                        self.assertEqual(summary["status"], "FAIL" if expected_code else "PASS")
                        self.assertEqual(summary["last_stage"],
                                         "source-cleanliness" if dirty and not original_code
                                         else original_stage)
                        self.assertEqual(status.read_bytes(), expected_status)
                        self.assertEqual(stat.S_IMODE(status.stat().st_mode), 0o644)
                        self.assertFalse(status.is_symlink())
                        status.unlink()

    def test_untracked_mutation_fails_and_preserves_raw_status(self):
        (self.source / "untracked-output").write_text("generated during build\n")
        self.assert_dirty_failure()

    def test_submodule_mutation_cannot_be_hidden_by_ignore_configuration(self):
        dependency = self.root / "dependency"
        dependency.mkdir()
        subprocess.run(["git", "init", "-q", str(dependency)], check=True)
        (dependency / "generated.txt").write_text("original\n")
        subprocess.run(["git", "-C", str(dependency), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(dependency), "-c", "user.name=P003 Test", "-c",
            "user.email=p003@example.invalid", "commit", "-qm", "dependency fixture"],
            check=True)
        self.git("-c", "protocol.file.allow=always", "submodule", "add", "-q",
                 str(dependency), "dependency")
        self.commit_source()
        self.git("config", "submodule.dependency.ignore", "all")
        (self.source / "dependency/generated.txt").write_text("mutated\n")
        self.assertEqual(self.git("status", "--porcelain=v1"), b"")
        self.assert_dirty_failure()

    def test_original_failure_code_and_stage_survive_clean_or_dirty_source(self):
        for dirty in (False, True):
            with self.subTest(dirty=dirty):
                if dirty:
                    self.generated.write_text("generated during failed build\n")
                expected = self.raw_status()
                result, summary = self.finish_build(exit_code=42, stage="compile")
                self.assertEqual(result.returncode, 42, result.stderr)
                self.assertEqual(summary["status"], "FAIL")
                self.assertEqual(summary["exit_code"], 42)
                self.assertEqual(summary["last_stage"], "compile")
                status = self.evidence / "source-status-after.txt"
                self.assertEqual(status.read_bytes(), expected)
                status.unlink()

    def test_preexisting_regular_status_is_not_overwritten(self):
        status = self.evidence / "source-status-after.txt"
        status.write_bytes(b"existing evidence\n")
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(status.read_bytes(), b"existing evidence\n")

    def test_symlink_status_is_rejected_without_writing_its_target(self):
        target = self.root / "redirect-target"
        target.write_bytes(b"")
        status = self.evidence / "source-status-after.txt"
        status.symlink_to(target)
        self.generated.write_text("changed\n")
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(summary["status"], "FAIL")
        self.assertTrue(status.is_symlink())
        self.assertEqual(target.read_bytes(), b"")

    def test_directory_status_is_rejected(self):
        status = self.evidence / "source-status-after.txt"
        status.mkdir()
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(summary["status"], "FAIL")
        self.assertTrue(status.is_dir())

    def test_fifo_status_is_rejected_without_blocking(self):
        os.mkfifo(self.evidence / "source-status-after.txt")
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(summary["status"], "FAIL")

    def test_git_status_failure_cannot_pass_as_empty_status(self):
        (self.source / ".git").rename(self.source / "removed-git")
        result, summary = self.finish_build()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["last_stage"], "source-cleanliness")
        self.assertEqual((self.evidence / "source-status-after.txt").read_bytes(), b"")


class AggregateSourceCleanlinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="p003-status-gate-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.commit = "a" * 40

        def write_json(name, value):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value) + "\n")

        write_json("toolchain.lock.json", {"environment": {}})
        lock_sha = gate.digest(self.root / "toolchain.lock.json")
        write_json("build-summary.json", {
            "status": "PASS", "exit_code": 0, "last_stage": "complete",
            "source_commit": self.commit, "toolchain_sha256": lock_sha})
        write_json("toolchain-host-observation.json", {
            "status": "PASSED", "lock_sha256": lock_sha, "identity_differences": [],
            "raw_observation_differences": [], "environment": {}})
        write_json("source-lock-verification.json", {
            "result": "PASS", "root_commit": self.commit, "verified_gitlinks": 160,
            "verified_repositories": 161, "verified_lfs_payloads": 44,
            "uninitialized": 0, "mismatched": 0, "conflicted": 0,
            "dirty_repositories": 0})
        for name in ("first", "second"):
            write_json(f"install-{name}.json", {
                "status": "PASSED", "errors": [], "source_commit": self.commit,
                "frameworks": [{"name": framework} for framework in gate.probes.FRAMEWORKS]})
            write_json(f"probes-{name}/report.json", {"source_revision": self.commit})
        write_json("uninstall.json", {"status": "PASSED", "prefix_absent": True})
        for name in ("configure.log", "build.log", "install-first.log", "install-second.log",
                     "CMakeCache.txt", "compile_commands.json", "source-built-linker.json"):
            (self.root / name).write_text("raw fixture evidence\n")
        for name in ("before", "after"):
            (self.root / f"source-status-{name}.txt").write_bytes(b"")

        # Isolate the status gate while retaining campaign's real file reads,
        # status checks, result construction and evidence hashing.
        patches = ExitStack()
        self.addCleanup(patches.close)
        patches.enter_context(mock.patch.object(gate.toolchain, "environment_identity", return_value={}))
        patches.enter_context(mock.patch.object(gate.toolchain, "identity_differences", return_value=[]))
        for name in ("validate_source_classifications", "validate_unwind_codegen", "entries",
                     "validate_native", "validate_probes"):
            patches.enter_context(mock.patch.object(gate, name, return_value={}))

    def test_clean_before_and_after_are_accepted_and_hashed(self):
        result = gate.campaign(self.root, self.commit)
        for name in ("before", "after"):
            relative = f"source-status-{name}.txt"
            self.assertEqual(result["evidence"][relative], gate.digest(self.root / relative))

    def test_missing_before_or_after_is_rejected(self):
        for name in ("before", "after"):
            with self.subTest(status=name):
                status = self.root / f"source-status-{name}.txt"
                status.unlink()
                with self.assertRaisesRegex(ValueError, "Missing regular source status evidence"):
                    gate.campaign(self.root, self.commit)
                status.write_bytes(b"")

    def test_dirty_before_or_after_is_rejected_without_altering_raw_status(self):
        for name, message in (("before", "Build started from dirty source"),
                              ("after", "Build changed source")):
            with self.subTest(status=name):
                status = self.root / f"source-status-{name}.txt"
                status.write_bytes(b" M generated.txt\n")
                with self.assertRaisesRegex(ValueError, message):
                    gate.campaign(self.root, self.commit)
                self.assertEqual(status.read_bytes(), b" M generated.txt\n")
                status.write_bytes(b"")

    def test_symlink_before_or_after_to_empty_file_is_rejected(self):
        target = self.root / "empty-target"
        target.write_bytes(b"")
        for name in ("before", "after"):
            with self.subTest(status=name):
                status = self.root / f"source-status-{name}.txt"
                status.unlink()
                status.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "Missing regular source status evidence"):
                    gate.campaign(self.root, self.commit)
                self.assertEqual(target.read_bytes(), b"")
                status.unlink()
                status.write_bytes(b"")

    def test_directory_before_or_after_is_rejected(self):
        for name in ("before", "after"):
            with self.subTest(status=name):
                status = self.root / f"source-status-{name}.txt"
                status.unlink()
                status.mkdir()
                with self.assertRaisesRegex(ValueError, "Missing regular source status evidence"):
                    gate.campaign(self.root, self.commit)
                status.rmdir()
                status.write_bytes(b"")


if __name__ == "__main__":
    unittest.main()
