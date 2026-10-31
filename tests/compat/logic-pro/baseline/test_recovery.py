"""P001 recovery tests use real synthetic Git histories and deliberate damage."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "tools" / "compat" / "logic-pro" / "recover_baseline.py"
SPEC = importlib.util.spec_from_file_location("p001_recovery", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="p001-recovery-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "source repo"
        self.repo.mkdir()
        self.git("init", "-b", "master")
        self.git("config", "user.name", "Recovery Fixture")
        self.git("config", "user.email", "recovery@example.invalid")
        (self.repo / "README.md").write_bytes(b"# Original source README\n")
        (self.repo / "filename with spaces.txt").write_bytes(b"ordinary\x00binary\n")
        (self.repo / "executable.sh").write_bytes(b"#!/bin/sh\nexit 0\n")
        (self.repo / "executable.sh").chmod(0o755)
        # Recovery hashes the link text and must not follow the external target.
        (self.repo / "outside-link").symlink_to("/not-a-real-external-location")
        (self.repo / ".gitmodules").write_text(
            '[submodule "missing dependency"]\n'
            '\tpath = external/missing dependency\n'
            '\turl = ../missing-dependency.git\n', encoding="utf-8",
        )
        self.git("add", ".")
        self.git("update-index", "--add", "--cacheinfo",
                 "160000," + "a" * 40 + ",external/missing dependency")
        self.git("commit", "-m", "original source baseline")
        self.baseline = self.snapshot()
        (self.repo / "README.md").write_bytes(b"# New implementation plan\n")
        self.git("add", "README.md")
        self.git("commit", "-m", "record plan without changing sources")
        self.integration = self.snapshot()
        self.manifest = {
            "schema_version": 1,
            "repository_url": "https://github.com/example/recovery-fixture.git",
            "baseline": self.baseline,
            "integration": self.integration,
        }
        self.manifest_file = self.root / "baseline.json"
        self.save_manifest()

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args], env=recovery.environment(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        return result.stdout.decode().strip()

    def snapshot(self) -> dict:
        commit = self.git("rev-parse", "HEAD")
        return {
            "commit": commit,
            "tree": self.git("rev-parse", "HEAD^{tree}"),
            "readme": {
                "path": "README.md",
                "sha256": hashlib.sha256((self.repo / "README.md").read_bytes()).hexdigest(),
                "source_url": f"https://github.com/example/recovery-fixture/blob/{commit}/README.md",
            },
        }

    def save_manifest(self) -> None:
        self.manifest_file.write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_recovers_exact_history_blobs_modes_symlinks_and_separate_stores(self) -> None:
        report = recovery.recover(self.repo, recovery.load_manifest(self.manifest_file), self.root)
        self.assertEqual(report["result"], "PASS", report.get("error"))
        self.assertEqual(len(report["snapshots"]), 2)
        self.assertTrue(report["source"]["unchanged_after_recovery"])
        workspace = Path(report["workspace"])
        for index, label in enumerate(("baseline", "integration")):
            snapshot = report["snapshots"][index]
            self.assertEqual(snapshot["commit"], self.manifest[label]["commit"])
            self.assertEqual(snapshot["tree"], self.manifest[label]["tree"])
            self.assertEqual(snapshot["readme"]["verified_sha256"], self.manifest[label]["readme"]["sha256"])
            self.assertEqual(snapshot["counts"], {"regular_files": 3, "executables": 1, "symlinks": 1, "gitlinks": 1})
            self.assertEqual(snapshot["verified_blobs"], 5)
            self.assertEqual(snapshot["gitlinks"][0]["status"], "NOT_INITIALIZED")
            self.assertEqual(os.readlink(workspace / label / "outside-link"), "/not-a-real-external-location")
        first = recovery.object_inodes(workspace / "baseline" / ".git" / "objects")
        second = recovery.object_inodes(workspace / "integration" / ".git" / "objects")
        self.assertTrue(first)
        self.assertTrue(second)
        self.assertFalse(first.intersection(second))
        self.assertNotEqual(report["snapshots"][0]["materialized_entries_sha256"],
                            report["snapshots"][1]["materialized_entries_sha256"])

    def test_source_local_edits_are_recorded_and_not_imported_or_destroyed(self) -> None:
        (self.repo / "README.md").write_text("uncommitted user work\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("keep me\n", encoding="utf-8")
        report = recovery.recover(self.repo, self.manifest, self.root)
        self.assertEqual(report["result"], "PASS", report.get("error"))
        self.assertFalse(report["source"]["working_tree_clean"])
        self.assertTrue(report["source"]["unchanged_after_recovery"])
        self.assertEqual((self.repo / "README.md").read_text(), "uncommitted user work\n")
        self.assertEqual((self.repo / "untracked.txt").read_text(), "keep me\n")
        self.assertFalse((Path(report["workspace"]) / "integration" / "untracked.txt").exists())

    def test_wrong_tree_is_a_failure(self) -> None:
        self.manifest["baseline"]["tree"] = "b" * 40
        report = recovery.recover(self.repo, self.manifest)
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("tree mismatch", report["error"])

    def test_wrong_original_readme_checksum_is_a_failure(self) -> None:
        self.manifest["baseline"]["readme"]["sha256"] = "0" * 64
        report = recovery.recover(self.repo, self.manifest)
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("README checksum mismatch", report["error"])

    def test_missing_blob_cannot_pass_as_an_empty_clean_checkout(self) -> None:
        blob = self.git("rev-parse", self.baseline["commit"] + ":filename with spaces.txt")
        (self.repo / ".git" / "objects" / blob[:2] / blob[2:]).unlink()
        report = recovery.recover(self.repo, self.manifest)
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("Git command failed", report["error"])
        self.assertLess(len(report["snapshots"]), 2)

    def test_checkout_damage_is_detected_by_independent_blob_and_mode_checks(self) -> None:
        cases = (
            ("deleted-file", lambda p: (p / "README.md").unlink(), "Cannot read restored entry"),
            ("changed-file", lambda p: (p / "README.md").write_text("changed\n"), "Restored blob mismatch"),
            ("removed-executable", lambda p: (p / "executable.sh").chmod(0o644), "executable bit differs"),
            ("changed-symlink", self.change_symlink, "Restored blob mismatch"),
        )
        for name, mutation, expected_error in cases:
            with self.subTest(name=name):
                report = recovery.recover(self.repo, self.manifest, self.root)
                self.assertEqual(report["result"], "PASS", report.get("error"))
                checkout = Path(report["workspace"]) / "baseline"
                mutation(checkout)
                with self.assertRaisesRegex(recovery.RecoveryError, expected_error):
                    recovery.materialization(recovery.Git(), checkout, self.baseline["commit"])

    @staticmethod
    def change_symlink(checkout: Path) -> None:
        (checkout / "outside-link").unlink()
        (checkout / "outside-link").symlink_to("/different-external-target")

    def test_recovery_workspace_inside_source_is_rejected(self) -> None:
        report = recovery.recover(self.repo, self.manifest, self.repo)
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("outside the source worktree", report["error"])

    def test_manifest_requires_immutable_source_and_safe_readme_path(self) -> None:
        self.manifest["baseline"]["readme"]["source_url"] = "https://github.com/example/recovery-fixture/blob/master/README.md"
        self.save_manifest()
        with self.assertRaisesRegex(recovery.RecoveryError, "immutable source URL"):
            recovery.load_manifest(self.manifest_file)
        self.manifest["baseline"]["readme"]["path"] = "../outside"
        self.save_manifest()
        with self.assertRaisesRegex(recovery.RecoveryError, "Unsafe"):
            recovery.load_manifest(self.manifest_file)

    def test_cli_returns_nonzero_and_writes_failed_evidence(self) -> None:
        self.manifest["integration"]["tree"] = "c" * 40
        self.save_manifest()
        output = self.root / "recovery-report.json"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo),
             "--manifest", str(self.manifest_file), "--output", str(output)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(output.read_text())["result"], "FAIL")
        self.assertIn(b"tree mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
