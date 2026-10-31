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

    def test_license_candidates_cover_actual_prefixed_suffixed_and_family_names(self):
        names = (
            "APPLE_LICENSE", "MIT.license", "MIT-LICENSE", "ADDITIONAL_LICENSE_INFO",
            "MozillaPublicLicense1.1.html", "unicode-license.txt", "LIBDWARFCOPYRIGHT",
            "HTML_COPYRIGHT", "MAN_COPYRIGHT", "crtlicense.txt", "xlicense.txt",
            "page-COPYING.ri", "template.copyright", "GPL", "GPLv3", "LGPL2.1",
            "AGPL-3.0.txt", "MPL-2.0.txt", "BSD-MIT", "Apache-2.0", "ISC.txt",
            "LEGAL", "PATENTS", "ASSEMBLY_EXCEPTION", "Acknowledgements.rtf",
            "ACKNOWLEDGMENTS", "acknowledgements.pl", "UNLICENSE", "UNLICENCE",
            # A name can be a candidate while its contents are source/test code.
            "LicenseTypeTest.java", "addNotices.sh", "kxld_copyright.c", "Legal.java",
        )
        expected = {}
        for name in names:
            data = ("Candidate fixture: " + name + "\n").encode()
            (self.repo / name).write_bytes(data)
            expected[name] = data
        (self.repo / "submit.py").write_text("not a license filename\n")
        (self.repo / "gplibrary.c").write_text("not a license filename\n")
        self.commit(self.repo)
        manifest, _ = self.inspect(require_clean=True)
        candidates = {entry["path"]: entry for entry in manifest["repositories"][0]["licenses"]}
        self.assertEqual(set(candidates), set(expected) | {"LICENSE"})
        for name, data in expected.items():
            with self.subTest(name=name):
                record = candidates[name]
                self.assertEqual(record["bytes"], len(data))
                self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(record["git_blob"], self.git(self.repo, "rev-parse", "HEAD:" + name))
                self.assertEqual(record["content_kind"], "regular_file")
                self.assertTrue(record["discovery_reasons"])
                self.assertEqual(record["classification"], "filename/path candidate; not a legal determination")
        self.assertEqual(manifest["inventory_status"], "VALID")

    def test_license_directory_candidates_include_unmarked_basenames(self):
        paths = (
            "package/LICENSE/pnpoly.txt", "package/licences/terms.txt",
            "package/LiCeNsEs/CC0-1.0.txt", "src/java.base/share/legal/asm.md",
            "package/LEGAL/Makefile", "package/Notices/third-party.txt",
            "package/third_party_licenses/terms.txt", "package/licensing/terms.txt",
        )
        for path in paths:
            destination = self.repo / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"Directory candidate fixture.\n")
        self.commit(self.repo)
        manifest, _ = self.inspect(require_clean=True)
        candidates = {entry["path"]: entry for entry in manifest["repositories"][0]["licenses"]}
        self.assertEqual(set(candidates), set(paths) | {"LICENSE"})
        for path in paths:
            self.assertIn("license_notice_or_legal_directory", candidates[path]["discovery_reasons"])

    def test_license_symlink_records_committed_target_text_without_dereferencing(self):
        outside = self.base / "outside-private.txt"
        outside.write_bytes(b"Private external contents must never be inventoried.\n")
        targets = {"License": str(outside), "NOTICE": "../missing-external-target"}
        directory = self.repo / "links"
        directory.mkdir()
        for name, target in targets.items():
            (directory / name).symlink_to(target)
        self.commit(self.repo)
        manifest, _ = self.inspect(require_clean=True)
        self.assertEqual(manifest["inventory_status"], "VALID")
        candidates = {entry["path"]: entry for entry in manifest["repositories"][0]["licenses"]}
        for name, target in targets.items():
            with self.subTest(name=name):
                record = candidates["links/" + name]
                raw_target = os.fsencode(target)
                self.assertEqual(record["mode"], "120000")
                self.assertEqual(record["content_kind"], "symlink_target_text")
                self.assertEqual(record["symlink_target"], target)
                self.assertFalse(record["target_dereferenced"])
                self.assertEqual(record["bytes"], len(raw_target))
                self.assertEqual(record["sha256"], hashlib.sha256(raw_target).hexdigest())
        self.assertNotIn("Private external contents", json.dumps(manifest))
        # Discovery and content remain tied to the commit even if the live link changes.
        (directory / "License").unlink()
        (directory / "License").symlink_to(self.base / "different-missing-target")
        changed, _ = self.inspect()
        changed_candidates = {entry["path"]: entry for entry in changed["repositories"][0]["licenses"]}
        self.assertEqual(changed_candidates, candidates)
        self.assertFalse(changed["repositories"][0]["worktree_clean"])

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

    def test_strict_recursion_rejects_unavailable_direct_contents(self):
        self.add_gitlink(self.repo, "dep", "a" * 40)
        manifest, _ = self.inspect(require_clean=True, require_recursive=True)
        self.assertEqual(manifest["inventory_status"], "INVALID")
        self.assertIn("recursive_source_unavailable", self.codes(manifest))
        self.assertFalse(manifest["summary"]["recursive_content_complete"])
        self.assertEqual(manifest["requirements"], {"clean_checkout": True, "recursive_source": True})

    def test_cli_recursive_gate_returns_failure_for_missing_source(self):
        self.add_gitlink(self.repo, "dep", "a" * 40)
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo),
                                 "--require-clean", "--require-recursive", "--output", str(self.base / "strict.json")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads((self.base / "strict.json").read_text())["inventory_status"], "INVALID")

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

    def test_strict_recursion_rejects_missing_grandchild(self):
        source = self.new_repo("dependency")
        self.add_gitlink(source, "nested", "b" * 40, "../nested.git")
        self.add_gitlink(self.repo, "dep", self.git(source, "rev-parse", "HEAD"))
        self.git(self.repo, "clone", "--no-hardlinks", str(source), "dep")
        manifest, _ = self.inspect(require_clean=True, require_recursive=True)
        self.assertEqual(manifest["inventory_status"], "INVALID")
        missing = [e for e in manifest["issues"] if e["code"] == "recursive_source_unavailable"]
        self.assertEqual([(e["repository"], e["path"]) for e in missing], [("dep", "nested")])

    def test_strict_complete_nested_graph_preserves_original_and_actual_origins(self):
        grandchild = self.new_repo("nested-source")
        source = self.new_repo("dependency")
        self.add_gitlink(source, "nested", self.git(grandchild, "rev-parse", "HEAD"), "../nested.git")
        self.add_gitlink(self.repo, "dep", self.git(source, "rev-parse", "HEAD"))
        self.git(self.repo, "clone", "--no-hardlinks", str(source), "dep")
        self.git(self.repo / "dep", "remote", "set-url", "origin", "https://github.com/upstream/dependency.git")
        self.git(self.repo / "dep", "clone", "--no-hardlinks", str(grandchild), "nested")
        self.git(self.repo / "dep/nested", "remote", "set-url", "origin", "https://github.com/upstream/nested.git")
        manifest, _ = self.inspect(require_clean=True, require_recursive=True)
        self.assertEqual(manifest["inventory_status"], "VALID")
        self.assertTrue(manifest["summary"]["recursive_content_complete"])
        child = manifest["submodules"][1]
        self.assertEqual(child["resolved_url"], "https://github.com/fork/nested.git")
        self.assertEqual(child["effective_resolved_url"], "https://github.com/upstream/nested.git")
        self.assertEqual(child["resolution_base_url"], "https://github.com/upstream/dependency.git")
        self.assertEqual(child["source_origin"], "https://github.com/upstream/nested.git")
        self.assertEqual(child["source_origin_provenance"], "child_remote_origin_configuration")
        self.assertEqual(manifest["repositories"][1]["effective_remote_provenance"], "configured_origin")

    def test_dirty_checkout_is_recorded_but_optional_gate_fails(self):
        expected = self.git(self.repo, "rev-parse", "HEAD:README.md")
        (self.repo / "README.md").write_text("uncommitted mutation")
        relaxed, files = self.inspect()
        strict, _ = self.inspect(require_clean=True)
        self.assertEqual(relaxed["inventory_status"], "VALID")
        self.assertFalse(relaxed["repositories"][0]["worktree_clean"])
        self.assertEqual(next(entry["object"] for entry in files if entry["path"] == "README.md"), expected)
        self.assertIn("checkout_not_clean_at_requested_revision", self.codes(strict))

    def test_hidden_index_flags_cannot_hide_dirty_physical_bytes(self):
        for flag in ("--assume-unchanged", "--skip-worktree"):
            with self.subTest(flag=flag):
                self.git(self.repo, "update-index", flag, "README.md")
                (self.repo / "README.md").write_text("hidden uncommitted mutation")
                manifest, _ = self.inspect(require_clean=True, require_recursive=True)
                self.assertEqual(manifest["inventory_status"], "INVALID")
                self.assertEqual(manifest["repositories"][0]["materialization"]["status"], "FAIL")
                self.git(self.repo, "update-index", "--no-assume-unchanged", "--no-skip-worktree", "README.md")
                (self.repo / "README.md").write_text("Fixture source baseline.\n")

    def test_core_filemode_false_cannot_hide_executable_mode_change(self):
        self.git(self.repo, "config", "core.filemode", "false")
        (self.repo / "README.md").chmod(0o755)
        manifest, _ = self.inspect(require_clean=True)
        self.assertEqual(manifest["inventory_status"], "INVALID")
        self.assertFalse(manifest["repositories"][0]["worktree_clean"])

    def test_physical_inventory_never_invokes_configured_clean_filter(self):
        (self.repo / ".gitattributes").write_text("README.md filter=marker\n")
        self.commit(self.repo)
        marker = self.base / "filter-must-not-run"
        self.git(self.repo, "config", "filter.marker.clean", f"touch {marker}; cat")
        self.git(self.repo, "config", "filter.marker.required", "true")
        (self.repo / "README.md").write_text("changed input that would trigger a clean filter")
        manifest, _ = self.inspect(require_clean=True)
        self.assertEqual(manifest["inventory_status"], "INVALID")
        self.assertFalse(marker.exists())

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
