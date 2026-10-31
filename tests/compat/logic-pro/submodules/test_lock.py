"""Real Git fixtures for P002, including deliberately corrupted recursive clones."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import inventory  # noqa: E402
from check_submodules import LockFailure, safe_path, safe_url, validate_lock, verify  # noqa: E402
from make_submodule_lock import generate  # noqa: E402


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
        self.lock = {"schema_version": 1, "phase": "P002", "root_origin": root_url,
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


class Structure(unittest.TestCase):
    def test_unsafe_paths_rejected(self):
        for value in ("../escape", "/root", "module/../escape", "bad\\path", ""):
            with self.subTest(value=value), self.assertRaises(LockFailure):
                safe_path(value)

    def test_nonpublic_urls_rejected(self):
        for url in ("https://token@github.com/owner/repo", "http://github.com/owner/repo", "https://evil.test/owner/repo", "file:///tmp/foo"):
            with self.subTest(url=url), self.assertRaises(LockFailure):
                safe_url(url, allow_local=False)

    def test_empty_lock_rejected(self):
        with self.assertRaises(LockFailure):
            validate_lock({"phase": "P002", "schema_version": 1, "submodules": []}, False)

    def test_actual_lock_is_reproducible_from_p001(self):
        evidence = json.loads((ROOT / "docs/compat/logic-pro/evidence/P001/source-retrieval.json").read_text())
        lock = json.loads((ROOT / "docs/compat/logic-pro/submodules.lock.json").read_text())
        self.assertEqual(generate(ROOT, evidence), lock)
        self.assertEqual(len(lock["submodules"]), 160)


if __name__ == "__main__":
    unittest.main()
