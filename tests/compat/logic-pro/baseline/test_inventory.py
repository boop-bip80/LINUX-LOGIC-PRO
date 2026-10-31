"""Executable P001 source-inventory assertions using isolated real Git repos."""

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
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/inventory.py"
SPEC = importlib.util.spec_from_file_location("p001_inventory", SCRIPT)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p001-inventory-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.environment = mock.patch.dict(os.environ, {
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_AUTHOR_NAME": "P001 test", "GIT_AUTHOR_EMAIL": "p001@example.invalid",
            "GIT_COMMITTER_NAME": "P001 test", "GIT_COMMITTER_EMAIL": "p001@example.invalid",
            "GIT_AUTHOR_DATE": "2026-10-31T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-10-31T00:00:00+00:00",
            "GIT_TERMINAL_PROMPT": "0",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.repo = self.new_repo("root")

    def git(self, repo, *arguments):
        result = subprocess.run(["git", "-C", str(repo), *arguments], capture_output=True, check=False)
        if result.returncode:
            self.fail(f"fixture git {arguments}: {result.stderr.decode(errors='replace')}")
        return result.stdout.decode().strip()

    def new_repo(self, name):
        repo = self.base / name
        repo.mkdir(parents=True)
        self.git(repo, "init", "--initial-branch=master")
        (repo / "LICENSE").write_text("Fixture license notice only.\n")
        (repo / "README.md").write_text("Fixture source baseline.\n")
        self.commit(repo)
        return repo

    def commit(self, repo):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-m", "fixture")
        return self.git(repo, "rev-parse", "HEAD")

    def add_gitlink(self, repo, path, pin, declared_url="../dependency.git", name=None):
        module_file = repo / ".gitmodules"
        old = module_file.read_text() if module_file.exists() else ""
        module_file.write_text(old + f'[submodule "{name or path}"]\n\tpath = {path}\n\turl = {declared_url}\n')
        self.git(repo, "add", ".gitmodules")
        self.git(repo, "update-index", "--add", "--cacheinfo", "160000", pin, path)
        self.git(repo, "commit", "-m", "add pinned dependency")
        (repo / path).mkdir(parents=True, exist_ok=True)

    def inspect(self, **kwargs):
        return inventory.snapshot(self.repo, kwargs.pop("revision", "HEAD"),
                                  remote_url="https://github.com/fork/runtime.git", **kwargs)

    def codes(self, manifest):
        return {issue["code"] for issue in manifest["issues"]}

    def test_committed_tree_paths_licenses_and_deterministic_output(self):
        (self.repo / "file with spaces\tand tab.txt").write_text("source\n")
        pin = self.commit(self.repo)
        first, files = self.inspect(require_clean=True)
        second, files_again = self.inspect(require_clean=True)
        self.assertEqual(first, second)
        self.assertEqual(files, files_again)
        self.assertEqual(first["source"]["commit"], pin)
        self.assertEqual(first["source"]["tree"], self.git(self.repo, "rev-parse", "HEAD^{tree}"))
        self.assertIn("file with spaces\tand tab.txt", [entry["path"] for entry in files])
        license_entry = first["repositories"][0]["licenses"][0]
        self.assertEqual(license_entry["sha256"], hashlib.sha256(b"Fixture license notice only.\n").hexdigest())
        self.assertEqual(first["inventory_status"], "VALID")

    def test_uninitialized_gitlink_is_not_remote_failure(self):
        source = self.new_repo("dependency")
        pin = self.git(source, "rev-parse", "HEAD")
        self.add_gitlink(self.repo, "sub modules/dep", pin)
        manifest, files = self.inspect(require_clean=True)
        self.assertEqual(manifest["summary"]["gitlinks"], 1)
        self.assertEqual(manifest["inventory_status"], "VALID")
        submodule = manifest["submodules"][0]
        self.assertEqual(submodule["commit"], pin)
        self.assertEqual(submodule["resolved_url"], "https://github.com/fork/dependency.git")
        self.assertEqual(submodule["content_status"], "not_checked_out")
        self.assertEqual(submodule["remote_availability"], "not_checked")
        self.assertEqual(sum(entry["mode"] == "160000" for entry in files), 1)

    def test_missing_declaration_and_extra_declaration_are_errors(self):
        self.git(self.repo, "update-index", "--add", "--cacheinfo", "160000", "a" * 40, "undeclared")
        (self.repo / ".gitmodules").write_text('[submodule "extra"]\npath = no-gitlink\nurl = ../extra.git\n')
        self.git(self.repo, "add", ".gitmodules")
        self.git(self.repo, "commit", "-m", "malformed source")
        manifest, _ = self.inspect()
        self.assertEqual(manifest["inventory_status"], "INVALID")
        self.assertTrue({"gitlink_without_declaration", "declaration_without_gitlink"}.issubset(self.codes(manifest)))

    def test_duplicate_path_is_rejected_without_duplicating_inventory(self):
        self.add_gitlink(self.repo, "dep", "a" * 40)
        with (self.repo / ".gitmodules").open("a") as stream:
            stream.write('[submodule "second"]\npath = dep\nurl = ../different.git\n')
        self.commit(self.repo)
        manifest, _ = self.inspect()
        self.assertIn("duplicate_submodule_path", self.codes(manifest))
        self.assertEqual(len(manifest["submodules"]), 1)

    def test_duplicate_url_and_incomplete_section_are_rejected(self):
        self.add_gitlink(self.repo, "dep", "a" * 40)
        with (self.repo / ".gitmodules").open("a") as stream:
            stream.write('url = ../other.git\n[submodule "empty"]\nbranch = main\n')
        self.commit(self.repo)
        manifest, _ = self.inspect()
        errors = [value for value in manifest["issues"] if value["code"] == "invalid_submodule_declaration"]
        self.assertEqual(len(errors), 3)
        self.assertEqual(manifest["inventory_status"], "INVALID")

    def test_wrong_initialized_pin_is_rejected(self):
        source = self.new_repo("dependency")
        original = self.git(source, "rev-parse", "HEAD")
        self.add_gitlink(self.repo, "dep", original)
        (source / "new-source.c").write_text("int changed;\n")
        changed = self.commit(source)
        self.git(self.repo, "clone", "--no-hardlinks", str(source), "dep")
        manifest, _ = self.inspect()
        self.assertIn("submodule_pin_mismatch", self.codes(manifest))
        self.assertEqual(manifest["submodules"][0]["checkout_head"], changed)
        self.assertEqual(manifest["submodules"][0]["content_status"], "checkout_mismatch")
        self.assertEqual(len(manifest["repositories"]), 1)

    def test_staged_gitlink_change_fails_clean_gate_even_if_git_status_hides_it(self):
        self.add_gitlink(self.repo, "dep", "a" * 40)
        self.git(self.repo, "update-index", "--cacheinfo", "160000", "b" * 40, "dep")
        self.assertEqual(self.git(self.repo, "status", "--porcelain=v1", "--ignore-submodules=all"), "")
        relaxed, _ = self.inspect()
        strict, _ = self.inspect(require_clean=True)
        self.assertEqual(relaxed["submodules"][0]["commit"], "a" * 40)
        self.assertEqual(relaxed["repositories"][0]["index_gitlinks"][0]["object"], "b" * 40)
        self.assertFalse(relaxed["repositories"][0]["worktree_clean"])
        self.assertEqual(strict["inventory_status"], "INVALID")

    def test_recursion_records_nested_unknown_and_exact_available_parent(self):
        source = self.new_repo("dependency")
        self.add_gitlink(source, "nested", "b" * 40, "../nested.git")
        parent_pin = self.git(source, "rev-parse", "HEAD")
        self.add_gitlink(self.repo, "dep", parent_pin)
        self.git(self.repo, "clone", "--no-hardlinks", str(source), "dep")
        manifest, files = self.inspect(require_clean=True)
        self.assertEqual(manifest["inventory_status"], "VALID")
        self.assertEqual(manifest["summary"]["gitlinks"], 2)
        self.assertEqual(manifest["summary"]["available_gitlinks"], 1)
        self.assertEqual(manifest["submodules"][1]["path"], "dep/nested")
        self.assertEqual(manifest["submodules"][1]["resolved_url"], "https://github.com/fork/nested.git")
        self.assertIn("dep/LICENSE", [entry["path"] for entry in files])
        self.assertEqual(len(manifest["repositories"][1]["licenses"]), 1)

    def test_dirty_checkout_is_recorded_but_optional_gate_fails(self):
        expected = self.git(self.repo, "rev-parse", "HEAD:README.md")
        (self.repo / "README.md").write_text("uncommitted mutation")
        relaxed, files = self.inspect()
        strict, _ = self.inspect(require_clean=True)
        self.assertEqual(relaxed["inventory_status"], "VALID")
        self.assertFalse(relaxed["repositories"][0]["worktree_clean"])
        self.assertEqual(next(entry["object"] for entry in files if entry["path"] == "README.md"), expected)
        self.assertIn("checkout_not_clean_at_requested_revision", self.codes(strict))

    def test_requested_old_ref_is_distinguished_from_current_checkout(self):
        old = self.git(self.repo, "rev-parse", "HEAD")
        (self.repo / "new.c").write_text("int later;\n")
        new = self.commit(self.repo)
        relaxed, files = self.inspect(revision=old)
        strict, _ = self.inspect(revision=old, require_clean=True)
        self.assertEqual(relaxed["source"]["commit"], old)
        self.assertEqual(relaxed["source"]["checkout_head"], new)
        self.assertNotIn("new.c", [entry["path"] for entry in files])
        self.assertEqual(strict["inventory_status"], "INVALID")

    def test_uncommitted_gitmodules_does_not_replace_committed_declaration(self):
        self.add_gitlink(self.repo, "dep", "a" * 40)
        (self.repo / ".gitmodules").write_text("unparseable local edit [[[\n")
        manifest, _ = self.inspect()
        self.assertEqual(manifest["submodules"][0]["declared_url"], "../dependency.git")
        self.assertEqual(manifest["inventory_status"], "VALID")

    def test_symlink_gitlink_never_recurses_outside_repository(self):
        source = self.new_repo("outside")
        self.add_gitlink(self.repo, "dep", self.git(source, "rev-parse", "HEAD"))
        (self.repo / "dep").rmdir()
        (self.repo / "dep").symlink_to(source, target_is_directory=True)
        manifest, _ = self.inspect()
        self.assertIn("symlink_in_gitlink_path", self.codes(manifest))
        self.assertEqual(manifest["summary"]["inspected_repositories"], 1)
        self.assertEqual(manifest["submodules"][0]["content_status"], "unsafe_symlink")

    def test_symlink_gitmodules_is_not_followed(self):
        outside = self.base / "external-config"
        outside.write_text('[submodule "external"]\npath = external\nurl = ../external\n')
        (self.repo / ".gitmodules").symlink_to(outside)
        # Git intentionally forbids adding a symlink .gitmodules; inject the tree
        # via plumbing to exercise hostile historical repository contents.
        result = subprocess.run(["git", "-C", str(self.repo), "hash-object", "-w", "--stdin"],
                                input=str(outside).encode(), capture_output=True, check=True)
        oid = result.stdout.decode().strip()
        tree_records = subprocess.run(["git", "-C", str(self.repo), "ls-tree", "-z", "HEAD"], capture_output=True, check=True).stdout
        tree_result = subprocess.run(["git", "-C", str(self.repo), "mktree", "-z"],
                                     input=tree_records + f"120000 blob {oid}\t.gitmodules\0".encode(), capture_output=True, check=True)
        new_commit = self.git(self.repo, "commit-tree", tree_result.stdout.decode().strip(), "-p", "HEAD", "-m", "hostile historical symlink")
        self.git(self.repo, "update-ref", "refs/heads/master", new_commit)
        manifest, _ = self.inspect()
        self.assertIn("nonregular_gitmodules", self.codes(manifest))
        self.assertEqual(manifest["submodules"], [])

    def test_gitmodules_include_and_update_command_are_never_executed(self):
        marker = self.base / "must-not-exist"
        self.add_gitlink(self.repo, "dep", "a" * 40)
        with (self.repo / ".gitmodules").open("a") as stream:
            stream.write(f'update = !touch {marker}\n[include]\npath = /does/not/exist\n')
        self.git(self.repo, "add", ".gitmodules")
        tree = self.git(self.repo, "write-tree")
        commit = self.git(self.repo, "commit-tree", tree, "-p", "HEAD", "-m", "hostile update command")
        self.git(self.repo, "update-ref", "refs/heads/master", commit)
        manifest, _ = self.inspect()
        self.assertEqual(manifest["inventory_status"], "VALID")
        self.assertFalse(marker.exists())

    def test_ambient_git_selectors_cannot_change_inspected_repository(self):
        other = self.new_repo("ambient")
        (other / "other-file.txt").write_text("unrelated")
        self.commit(other)
        expected = self.git(self.repo, "rev-parse", "HEAD")
        with mock.patch.dict(os.environ, {"GIT_DIR": str(other / ".git"), "GIT_WORK_TREE": str(other),
                                          "GIT_INDEX_FILE": str(other / ".git/index"),
                                          "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "remote.origin.url",
                                          "GIT_CONFIG_VALUE_0": "https://secret@invalid.example/private"}):
            manifest, files = self.inspect(require_clean=True)
        self.assertEqual(manifest["source"]["commit"], expected)
        self.assertEqual(manifest["inventory_status"], "VALID")
        self.assertNotIn("other-file.txt", [entry["path"] for entry in files])

    def test_replace_objects_cannot_change_committed_inventory(self):
        original = self.git(self.repo, "rev-parse", "HEAD")
        original_tree = self.git(self.repo, "rev-parse", "HEAD^{tree}")
        (self.repo / "replacement.txt").write_text("must not appear in original")
        replacement = self.commit(self.repo)
        self.git(self.repo, "replace", original, replacement)
        manifest, files = self.inspect(revision=original)
        self.assertEqual(manifest["source"]["tree"], original_tree)
        self.assertNotIn("replacement.txt", [entry["path"] for entry in files])

    def test_url_resolution_and_credential_redaction(self):
        cases = [
            ("https://github.com/owner/project.git", "../dep.git", "https://github.com/owner/dep.git"),
            ("git@github.com:owner/project.git", "../dep.git", "git@github.com:owner/dep.git"),
            ("ssh://git@github.com/owner/project.git", "../dep.git", "ssh://git@github.com/owner/dep.git"),
            ("https://github.com/owner/project.git", "./nested.git", "https://github.com/owner/project.git/nested.git"),
            ("/repos/owner/project.git", "../dep.git", "/repos/owner/dep.git"),
            (None, "../dep.git", None),
            (None, "https://user:secret@github.com/owner/dep.git?token=hidden#token", "https://github.com/owner/dep.git"),
            ("https://github.com/owner/project.git", "../dep.git?token=hidden#secret", "https://github.com/owner/dep.git"),
        ]
        for remote, declared, expected in cases:
            with self.subTest(remote=remote, declared=declared):
                self.assertEqual(inventory.resolve_submodule_url(remote, declared), expected)
        self.assertEqual(inventory.redact_url("../dep.git?token=hidden#secret"), "../dep.git")

    def test_cli_writes_hashed_tracked_file_and_fails_clean_gate(self):
        output = self.base / "evidence/inventory.json"
        tracked_output = self.base / "evidence/tracked-files.json"
        command = [sys.executable, str(SCRIPT), "--repo", str(self.repo), "--ref", "HEAD",
                   "--output", str(output), "--tracked-output", str(tracked_output), "--require-clean"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(output.read_text())
        self.assertEqual(manifest["tracked_files"]["path"], "tracked-files.json")
        self.assertEqual(manifest["tracked_files"]["sha256"], hashlib.sha256(tracked_output.read_bytes()).hexdigest())
        (self.repo / "README.md").write_text("mutation")
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertEqual(json.loads(output.read_text())["inventory_status"], "INVALID")

    def test_invalid_ref_returns_error_without_claiming_success(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo),
                                 "--ref", "no-such-commit", "--output", str(self.base / "bad.json")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.base / "bad.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
