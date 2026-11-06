"""Real Git fixtures for P002, including deliberately corrupted recursive clones."""

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import inventory  # noqa: E402
from check_submodules import SCHEMA, LockFailure, safe_path, safe_url, validate_lock, verify  # noqa: E402
from make_submodule_lock import generate  # noqa: E402
from source_provenance import load_reviewed_source  # noqa: E402


def git(where, *args):
    cmd = ["git", "-c", "protocol.file.allow=always"]
    if where is not None:
        cmd += ["-C", str(where)]
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(cmd + list(args), stderr=subprocess.PIPE, env=env).decode().strip()


def init(path):
    git(None, "init", "-q", "-b", "main", str(path))
    git(path, "config", "user.name", "P002 Test")
    git(path, "config", "user.email", "fixture@example.invalid")


def commit(path, message="fixture"):
    git(path, "add", "-A")
    git(path, "commit", "-q", "--allow-empty", "-m", message)


class RealRecursiveClone(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p002-fixture-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        remotes = base / "remotes"
        remotes.mkdir()
        grand = base / "grand-src"
        init(grand)
        (grand / "data.txt").write_text("grandchild\n")
        commit(grand)
        git(None, "clone", "-q", "--bare", str(grand), str(remotes / "grand.git"))
        grand_url = (remotes / "grand.git").as_uri()
        child = base / "child-src"
        init(child)
        (child / "data.txt").write_text("child\n")
        commit(child)
        git(child, "submodule", "add", "-q", grand_url, "nested")
        git(child, "config", "-f", ".gitmodules", "submodule.nested.url", "../grand.git")
        commit(child, "nested submodule")
        git(None, "clone", "-q", "--bare", str(child), str(remotes / "child.git"))
        child_url = (remotes / "child.git").as_uri()
        root = base / "root-src"
        init(root)
        (root / "data.txt").write_text("root\n")
        commit(root)
        git(root, "submodule", "add", "-q", child_url, "sub")
        commit(root, "child submodule")
        git(None, "clone", "-q", "--bare", str(root), str(remotes / "root.git"))
        root_url = (remotes / "root.git").as_uri()
        self.clone = base / "clone"
        git(None, "clone", "-q", "--recurse-submodules", root_url, str(self.clone))
        self.lock = {"schema_version": SCHEMA, "phase": "P002", "root_origin": root_url,
                     "root_gitmodules_blob_sha1": git(self.clone, "rev-parse", "HEAD:.gitmodules"),
                     "expected_lfs_objects": 0, "lfs_repositories": [], "lfs_objects": [],
                     "expected_direct_gitlinks": 1, "expected_recursive_gitlinks": 2,
                     "submodules": [
                         {"path": "sub", "parent_path": ".", "declared_url": child_url,
                          "resolved_url": child_url, "commit": git(self.clone / "sub", "rev-parse", "HEAD"),
                          "tree": git(self.clone / "sub", "rev-parse", "HEAD^{tree}")},
                         {"path": "sub/nested", "parent_path": "sub", "declared_url": "../grand.git",
                          "resolved_url": grand_url, "commit": git(self.clone / "sub/nested", "rev-parse", "HEAD"),
                          "tree": git(self.clone / "sub/nested", "rev-parse", "HEAD^{tree}")}]}

    def check(self, lock=None):
        return verify(self.clone, lock or self.lock, allow_local=True)

    def test_full_recursive_clone_passes(self):
        self.assertEqual(self.check()["verified_gitlinks"], 2)

    def test_repository_migration_requires_the_current_locked_root_origin(self):
        self.lock["root_origin"] = "https://github.com/boop-bip80/LINUX-LOGIC-PRO.git"
        git(self.clone, "remote", "set-url", "origin", "https://github.com/boop-bip80/MAC-OS-EMULATION.git")
        with self.assertRaisesRegex(LockFailure, "root origin differs from lock"):
            self.check()
        git(self.clone, "remote", "set-url", "origin", self.lock["root_origin"])
        self.assertEqual(self.check()["verified_gitlinks"], 2)

    def test_dirty_url_fails(self):
        file = self.clone / ".gitmodules"
        file.write_text(file.read_text().replace(self.lock["submodules"][0]["declared_url"], "https://github.com/other/repo.git"))
        with self.assertRaises(LockFailure):
            self.check()

    def test_committed_url_corruption_fails(self):
        file = self.clone / ".gitmodules"
        file.write_text(file.read_text().replace(self.lock["submodules"][0]["declared_url"], "https://github.com/other/repo.git"))
        git(self.clone, "config", "user.name", "P002 Test")
        git(self.clone, "config", "user.email", "fixture@example.invalid")
        commit(self.clone, "corrupt URL")
        with self.assertRaises(LockFailure):
            self.check()

    def test_changed_pin_fails(self):
        git(self.clone, "config", "user.name", "P002 Test")
        git(self.clone, "config", "user.email", "fixture@example.invalid")
        other = git(self.clone / "sub/nested", "rev-parse", "HEAD")
        git(self.clone, "update-index", "--add", "--cacheinfo", "160000", other, "sub")
        git(self.clone, "commit", "-q", "-m", "corrupt gitlink")
        with self.assertRaises(LockFailure):
            self.check()

    def test_uninitialized_direct_child_fails(self):
        git(self.clone, "submodule", "deinit", "-f", "--", "sub")
        with self.assertRaises((LockFailure, inventory.InventoryError)):
            self.check()

    def test_uninitialized_nested_child_fails(self):
        git(self.clone / "sub", "submodule", "deinit", "-f", "--", "nested")
        with self.assertRaises((LockFailure, inventory.InventoryError)):
            self.check()

    def test_changed_child_head_fails(self):
        child = self.clone / "sub"
        git(child, "config", "user.name", "P002 Test")
        git(child, "config", "user.email", "fixture@example.invalid")
        git(child, "commit", "-q", "--allow-empty", "-m", "different HEAD")
        with self.assertRaises(LockFailure):
            self.check()

    def test_wrong_origin_fails(self):
        git(self.clone / "sub", "remote", "set-url", "origin", self.lock["submodules"][1]["resolved_url"])
        with self.assertRaises(LockFailure):
            self.check()

    def test_removed_nested_lock_fails(self):
        broken = copy.deepcopy(self.lock)
        broken["submodules"].pop()
        broken["expected_recursive_gitlinks"] = 1
        with self.assertRaises(LockFailure):
            self.check(broken)

    def test_corrupt_sha_fails(self):
        broken = copy.deepcopy(self.lock)
        broken["submodules"][0]["commit"] = "0" * 40
        with self.assertRaises(LockFailure):
            self.check(broken)

    def configure_author(self, repo=None):
        repo = repo or self.clone
        git(repo, "config", "user.name", "P002 Test")
        git(repo, "config", "user.email", "fixture@example.invalid")

    def test_assume_unchanged_cannot_hide_root_metadata_edit(self):
        git(self.clone, "update-index", "--assume-unchanged", ".gitmodules")
        with (self.clone / ".gitmodules").open("a") as stream:
            stream.write("\n# undeclared metadata\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_skip_worktree_cannot_hide_root_metadata_edit(self):
        git(self.clone, "update-index", "--skip-worktree", ".gitmodules")
        (self.clone / ".gitmodules").write_text("corrupted\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_assume_unchanged_cannot_hide_nested_blob_edit(self):
        repo = self.clone / "sub/nested"
        git(repo, "update-index", "--assume-unchanged", "data.txt")
        (repo / "data.txt").write_text("not the pinned grandchild\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_skip_worktree_cannot_hide_nested_blob_edit(self):
        repo = self.clone / "sub/nested"
        git(repo, "update-index", "--skip-worktree", "data.txt")
        (repo / "data.txt").write_text("not the pinned grandchild\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_disabled_filemode_cannot_hide_changed_executable(self):
        repo = self.clone / "sub"
        git(repo, "config", "core.filemode", "false")
        (repo / "data.txt").chmod(0o755)
        with self.assertRaises(LockFailure):
            self.check()

    def test_untracked_root_input_fails(self):
        (self.clone / "runtime-input.txt").write_text("not in source\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_local_exclude_cannot_hide_untracked_root_input(self):
        (self.clone / "runtime-input.txt").write_text("not in source\n")
        (self.clone / ".git/info/exclude").write_text("runtime-input.txt\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_wrong_raw_origin_masked_by_rewrite_fails(self):
        repo = self.clone / "sub"
        correct = self.lock["submodules"][0]["resolved_url"]
        wrong = correct.replace("child.git", "wrong.git")
        git(repo, "remote", "set-url", "origin", wrong)
        git(repo, "config", "url." + correct + ".insteadOf", wrong)
        self.assertEqual(git(repo, "remote", "get-url", "origin"), correct)
        with self.assertRaises(LockFailure):
            self.check()

    def test_multiple_configured_origins_fail(self):
        git(self.clone / "sub", "config", "--add", "remote.origin.url", self.lock["submodules"][0]["resolved_url"])
        with self.assertRaises(LockFailure):
            self.check()

    def test_private_attribute_override_fails_without_running_filter(self):
        marker = Path(self.temp.name) / "filter-executed"
        (self.clone / ".git/info/attributes").write_text("data.txt filter=review\n")
        git(self.clone, "config", "filter.review.clean", "touch '" + str(marker) + "'; printf 'root\\n'")
        (self.clone / "data.txt").write_text("evil\n")
        with self.assertRaises(LockFailure):
            self.check()
        self.assertFalse(marker.exists(), "read-only verifier executed a clean filter")

    def test_committed_filter_cannot_hide_edit_or_execute(self):
        self.configure_author()
        (self.clone / ".gitattributes").write_text("data.txt filter=review\n")
        commit(self.clone, "declare filter without installing it")
        marker = Path(self.temp.name) / "filter-executed"
        git(self.clone, "config", "filter.review.clean", "touch '" + str(marker) + "'; printf 'root\\n'")
        (self.clone / "data.txt").write_text("evil\n")
        with self.assertRaises(LockFailure):
            self.check()
        self.assertFalse(marker.exists(), "read-only verifier executed a clean filter")

    def test_complete_index_blob_mismatch_fails(self):
        different = git(self.clone, "rev-parse", "HEAD:.gitmodules")
        git(self.clone, "update-index", "--cacheinfo", "100644", different, "data.txt")
        with self.assertRaises(LockFailure):
            self.check()

    def test_committed_update_none_fails_even_with_initialized_children(self):
        self.configure_author()
        git(self.clone, "config", "--file", ".gitmodules", "submodule.sub.update", "none")
        commit(self.clone, "uncloneable update policy")
        self.lock["root_gitmodules_blob_sha1"] = git(self.clone, "rev-parse", "HEAD:.gitmodules")
        with self.assertRaises(LockFailure):
            self.check()

    def test_committed_ignore_all_fails(self):
        self.configure_author()
        git(self.clone, "config", "--file", ".gitmodules", "submodule.sub.ignore", "all")
        commit(self.clone, "hidden submodule state")
        self.lock["root_gitmodules_blob_sha1"] = git(self.clone, "rev-parse", "HEAD:.gitmodules")
        with self.assertRaises(LockFailure):
            self.check()

    def test_duplicate_metadata_key_fails(self):
        self.configure_author()
        git(self.clone, "config", "--file", ".gitmodules", "--add", "submodule.sub.url", self.lock["submodules"][0]["declared_url"])
        commit(self.clone, "duplicate declaration")
        self.lock["root_gitmodules_blob_sha1"] = git(self.clone, "rev-parse", "HEAD:.gitmodules")
        with self.assertRaises(LockFailure):
            self.check()

    def test_symlinked_submodule_directory_fails(self):
        target = Path(self.temp.name) / "displaced-child"
        shutil.move(self.clone / "sub", target)
        (self.clone / "sub").symlink_to(target, target_is_directory=True)
        with self.assertRaises((LockFailure, inventory.InventoryError)):
            self.check()

    def test_standard_committed_crlf_conversion_passes(self):
        self.configure_author()
        (self.clone / ".gitattributes").write_text("data.txt text eol=crlf\n")
        commit(self.clone, "standard Git checkout conversion")
        (self.clone / "data.txt").write_bytes(b"root\r\n")
        report = self.check()
        self.assertEqual(report["standard_crlf_paths"], ["data.txt"])

    def test_crlf_conversion_does_not_waive_corruption(self):
        self.configure_author()
        (self.clone / ".gitattributes").write_text("data.txt text eol=crlf\n")
        commit(self.clone, "standard Git checkout conversion")
        (self.clone / "data.txt").write_bytes(b"evil\r\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_private_crlf_override_does_not_waive_corruption(self):
        (self.clone / ".git/info/attributes").write_text("data.txt text eol=crlf\n")
        (self.clone / "data.txt").write_bytes(b"root\r\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_dirty_indexed_attributes_do_not_waive_conversion(self):
        self.configure_author()
        (self.clone / ".gitattributes").write_text("data.txt -text\n")
        commit(self.clone, "no conversion")
        (self.clone / ".gitattributes").write_text("data.txt text eol=crlf\n")
        git(self.clone, "add", ".gitattributes")
        (self.clone / "data.txt").write_bytes(b"root\r\n")
        with self.assertRaises(LockFailure):
            self.check()

    def test_git_object_alternate_fails(self):
        (self.clone / ".git/objects/info/alternates").write_text(str(self.clone / "sub/.git") + "\n")
        with self.assertRaises((LockFailure, inventory.InventoryError)):
            self.check()

    def test_missing_lfs_inventory_fails(self):
        broken = copy.deepcopy(self.lock)
        del broken["lfs_objects"]
        with self.assertRaises(inventory.InventoryError):
            self.check(broken)

    def test_unlocked_lfs_pointer_fails(self):
        self.configure_author()
        (self.clone / "undeclared.bin").write_text("version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 5\n")
        commit(self.clone, "unlocked large object")
        with self.assertRaises((LockFailure, inventory.InventoryError)):
            self.check()


class Structure(unittest.TestCase):
    def test_unsafe_paths_rejected(self):
        for value in (".", "../escape", "/root", "module/../escape", "bad\\path", "", ".git/config", "module/.git/object", "line\nbreak"):
            with self.subTest(value=value), self.assertRaises(LockFailure):
                safe_path(value)

    def test_nonpublic_urls_rejected(self):
        for url in ("https://token@github.com/owner/repo", "http://github.com/owner/repo", "https://evil.test/owner/repo", "file:///tmp/foo", "https://github.com:8443/owner/repo", "https://github.com/owner/../repo"):
            with self.subTest(url=url), self.assertRaises(LockFailure):
                safe_url(url, allow_local=False)

    def test_empty_lock_rejected(self):
        with self.assertRaises(LockFailure):
            validate_lock({"phase": "P002", "schema_version": SCHEMA, "submodules": []}, False)

    def test_actual_lock_is_reproducible_from_reviewed_current_source(self):
        evidence = load_reviewed_source(ROOT)["current_evidence"]
        lock = json.loads((ROOT / "docs/compat/logic-pro/submodules.lock.json").read_text())
        generated = generate(ROOT, evidence)
        self.assertEqual(generated, lock)
        self.assertEqual((json.dumps(generated, indent=2, sort_keys=True) + "\n").encode(),
                         (ROOT / "docs/compat/logic-pro/submodules.lock.json").read_bytes())
        self.assertEqual(len(lock["submodules"]), 160)
        self.assertEqual(len(lock["lfs_objects"]), 44)

    def test_original_p001_report_cannot_authorize_current_pins(self):
        evidence = json.loads((ROOT / "docs/compat/logic-pro/evidence/P001/source-retrieval.json").read_text())
        with self.assertRaisesRegex(ValueError, "pin changed without new source evidence"):
            generate(ROOT, evidence)


if __name__ == "__main__":
    unittest.main()
