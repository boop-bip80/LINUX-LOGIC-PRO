"""Pinned recursive retrieval tests use local Git repositories, never a network."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/prepare_sources.py"
SPEC = importlib.util.spec_from_file_location("p001_prepare_sources", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrepareSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p001-source-fixtures-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.new_repo("project.git")
        self.child = self.new_repo("dependency.git")
        self.nested = self.new_repo("nested.git")
        self.nested_pin = self.git(self.nested, "rev-parse", "HEAD")
        self.link(self.child, "vendor/nested child", self.nested_pin, "../nested.git")
        self.child_pin = self.git(self.child, "rev-parse", "HEAD")
        self.link(self.repo, "external/child", self.child_pin, "../dependency.git")

    def git(self, repo, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "P001 fixture", "GIT_AUTHOR_EMAIL": "p001@example.invalid",
                    "GIT_COMMITTER_NAME": "P001 fixture", "GIT_COMMITTER_EMAIL": "p001@example.invalid"})
        return subprocess.check_output(["git", "-C", str(repo), *args], env=env, stderr=subprocess.PIPE).decode().strip()

    def new_repo(self, name):
        repo = self.base / name
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "master")
        (repo / "README.md").write_text("source fixture\n")
        self.git(repo, "add", "README.md")
        self.git(repo, "commit", "-qm", "initial")
        return repo

    def link(self, repo, path, pin, url):
        (repo / ".gitmodules").write_text(f'[submodule "dependency"]\npath = {path}\nurl = {url}\n')
        self.git(repo, "add", ".gitmodules")
        self.git(repo, "update-index", "--add", "--cacheinfo", "160000", pin, path)
        self.git(repo, "commit", "-qm", "pin dependency")
        (repo / path).mkdir(parents=True, exist_ok=True)

    def prepare(self):
        return MODULE.prepare(self.repo, str(self.repo), jobs=2, allow_local=True)

    def add_transforming_attributes(self):
        project = self.child / "msvc_build/aarch64/Ffi_staticLib.vcxproj"
        project.parent.mkdir(parents=True)
        project.write_bytes(b"<Project>\n</Project>\n")
        (self.child / "identity.ident").write_bytes(b"source $Id$\n")
        (self.child / "encoded.txt").write_bytes("source encoding\n".encode("utf-16le"))
        (self.child / "filtered.txt").write_bytes(b"source filter fixture\n")
        attributes = (b"*.vcxproj text eol=crlf\n*.ident ident\n"
                      b"encoded.txt text working-tree-encoding=UTF-16LE\nfiltered.txt filter=fixture\n")
        (self.child / ".gitattributes").write_bytes(attributes)
        self.git(self.child, "add", ".gitattributes", "msvc_build", "identity.ident", "encoded.txt", "filtered.txt")
        self.git(self.child, "commit", "-qm", "legitimate checkout transformations")
        self.child_pin = self.git(self.child, "rev-parse", "HEAD")
        self.git(self.repo, "update-index", "--cacheinfo", "160000", self.child_pin, "external/child")
        self.git(self.repo, "commit", "-qm", "pin transforming source")
        return attributes

    def test_fetches_recursive_exact_pins_with_actual_origins_and_no_source_changes(self):
        before = self.git(self.repo, "rev-parse", "HEAD^{tree}")
        # The newer branch tip must not replace the recorded gitlink.
        (self.child / "later.txt").write_text("not the pinned source\n")
        self.git(self.child, "add", "later.txt")
        self.git(self.child, "commit", "-qm", "later unpinned revision")
        report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        self.assertEqual(report["recursive_submodules_observed"], 2)
        self.assertTrue(report["recursive_content_complete"])
        self.assertTrue(report["source"]["parent_source_unchanged"])
        self.assertEqual(self.git(self.repo, "rev-parse", "HEAD^{tree}"), before)
        self.assertEqual([r["path"] for r in report["submodules"]], ["external/child", "external/child/vendor/nested child"])
        for record, pin, remote in zip(report["submodules"], [self.child_pin, self.nested_pin], [self.child, self.nested]):
            target = self.repo / record["path"]
            self.assertEqual(record["status"], "PASS")
            self.assertEqual(record["commit"], pin)
            self.assertEqual(self.git(target, "rev-parse", "HEAD"), pin)
            self.assertEqual(record["configured_origin"], str(remote))
            self.assertEqual(self.git(target, "config", "remote.origin.url"), str(remote))
            self.assertTrue((target / ".git").is_dir())
        self.assertFalse((self.repo / "external/child/later.txt").exists())
        self.assertTrue(any("fetch" in c["command"] for c in report["commands"]))

    def test_clean_pinned_existing_children_are_reused(self):
        self.assertEqual(self.prepare()["result"], "PASS")
        report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        self.assertTrue(all(r["retrieval"] == "REUSED_CLEAN_EXACT_PIN" for r in report["submodules"]))
        self.assertFalse(any("fetch" in c["command"] for c in report["commands"]))

    def test_source_inspection_override_prevents_crlf_ident_and_encoding_transforms(self):
        attributes = self.add_transforming_attributes()
        ordinary = self.base / "ordinary-checkout"
        self.git(self.base, "clone", "--quiet", "--no-local", str(self.child), str(ordinary))
        self.assertIn(b"\r\n", (ordinary / "msvc_build/aarch64/Ffi_staticLib.vcxproj").read_bytes())
        self.assertIn(b"$Id: ", (ordinary / "identity.ident").read_bytes())
        self.assertEqual((ordinary / "encoded.txt").read_bytes(), "source encoding\n".encode("utf-16le"))
        report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        actual = self.repo / "external/child"
        self.assertEqual((actual / "msvc_build/aarch64/Ffi_staticLib.vcxproj").read_bytes(), b"<Project>\n</Project>\n")
        self.assertEqual((actual / "identity.ident").read_bytes(), b"source $Id$\n")
        self.assertEqual((actual / "encoded.txt").read_bytes(), b"source encoding\n")
        self.assertEqual((actual / ".gitattributes").read_bytes(), attributes)
        self.assertEqual((actual / ".git/info/attributes").read_bytes(), MODULE.INSPECTION_ATTRIBUTES)
        self.assertTrue(report["submodules"][0]["checkout_policy"]["applied_to_fresh_checkout"])
        self.assertEqual(report["submodules"][0]["checkout_policy"]["attributes_sha256"],
                         report["fresh_checkout_policy"]["attributes_sha256"])
        self.assertFalse(report["fresh_checkout_policy"]["committed_attributes_modified"])

    def test_preexisting_transformed_bytes_are_refused_and_not_normalized(self):
        self.add_transforming_attributes()
        target = self.repo / "external/child"
        self.git(self.repo, "clone", "--quiet", "--no-local", str(self.child), str(target))
        old = (target / "encoded.txt").read_bytes()
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("tracked bytes differ at 'encoded.txt'", report["failures"][0]["error"])
        self.assertEqual((target / "encoded.txt").read_bytes(), old)
        self.assertFalse((target / ".git/info/attributes").exists())

    def test_fresh_checkout_override_prevents_configured_smudge_filter_execution(self):
        self.add_transforming_attributes()
        marker = self.base / "smudge-must-not-run"
        original = MODULE.Commands.run
        def with_filter(commands, repo, *args, **kwargs):
            result = original(commands, repo, *args, **kwargs)
            if args[:2] == ("init", "--quiet"):
                self.git(repo, "config", "filter.fixture.smudge", f"touch '{marker}'; cat")
                self.git(repo, "config", "filter.fixture.clean", f"touch '{marker}'; cat")
            return result
        with mock.patch.object(MODULE.Commands, "run", new=with_filter):
            report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        self.assertFalse(marker.exists())
        self.assertEqual((self.repo / "external/child/filtered.txt").read_bytes(), b"source filter fixture\n")

    def test_fork_resolution_and_upstream_acquisition_are_distinct(self):
        self.git(self.repo, "remote", "add", "origin", "https://github.com/fork/project.git")
        report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        parent, nested = report["submodules"]
        self.assertEqual(parent["resolved_url"], "https://github.com/fork/dependency.git")
        self.assertEqual(parent["acquisition_resolved_url"], str(self.child))
        self.assertEqual(parent["fetch_url"], str(self.child))
        self.assertEqual(nested["resolved_url"], str(self.nested))

    def test_dirty_existing_child_is_preserved_and_fails(self):
        self.assertEqual(self.prepare()["result"], "PASS")
        source = self.repo / "external/child/README.md"
        source.write_text("uncommitted user work\n")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("local or staged changes", report["failures"][0]["error"])
        self.assertEqual(source.read_text(), "uncommitted user work\n")

    def test_hidden_dirty_bytes_cannot_pass_reuse(self):
        self.assertEqual(self.prepare()["result"], "PASS")
        child = self.repo / "external/child"
        self.git(child, "update-index", "--assume-unchanged", "README.md")
        (child / "README.md").write_text("dirty bytes hidden from git status\n")
        self.assertEqual(self.git(child, "status", "--porcelain"), "")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("tracked bytes differ", report["failures"][0]["error"])
        self.assertEqual((child / "README.md").read_text(), "dirty bytes hidden from git status\n")

    def test_core_filemode_cannot_hide_executable_change(self):
        self.assertEqual(self.prepare()["result"], "PASS")
        child = self.repo / "external/child"
        self.git(child, "config", "core.filemode", "false")
        (child / "README.md").chmod(0o755)
        self.assertEqual(self.git(child, "status", "--porcelain"), "")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("executable bit differs", report["failures"][0]["error"])

    def test_tracked_symlinks_survive_publication_without_staging_residue(self):
        (self.child / "README-link").symlink_to("README.md")
        self.git(self.child, "add", "README-link")
        self.git(self.child, "commit", "-qm", "tracked symlink")
        pin = self.git(self.child, "rev-parse", "HEAD")
        self.git(self.repo, "update-index", "--cacheinfo", "160000", pin, "external/child")
        self.git(self.repo, "commit", "-qm", "new child pin")
        report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        self.assertTrue((self.repo / "external/child/README-link").is_symlink())
        self.assertEqual(list((self.repo / "external").glob(".p001-source-*")), [])

    def test_mismatched_existing_pin_is_preserved_and_fails(self):
        self.assertEqual(self.prepare()["result"], "PASS")
        target = self.repo / "external/child"
        (target / "README.md").write_text("new local commit\n")
        self.git(target, "commit", "-qam", "local revision")
        changed = self.git(target, "rev-parse", "HEAD")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("committed gitlink", report["failures"][0]["error"])
        self.assertEqual(self.git(target, "rev-parse", "HEAD"), changed)

    def test_existing_origin_mismatch_is_not_silently_rewritten(self):
        self.assertEqual(self.prepare()["result"], "PASS")
        target = self.repo / "external/child"
        self.git(target, "remote", "set-url", "origin", "https://example.invalid/wrong.git")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("origin differs", report["failures"][0]["error"])
        self.assertEqual(self.git(target, "config", "remote.origin.url"), "https://example.invalid/wrong.git")

    def test_missing_pin_is_reported_and_temporary_checkout_removed(self):
        self.git(self.repo, "update-index", "--cacheinfo", "160000", "a" * 40, "external/child")
        self.git(self.repo, "commit", "-qm", "unavailable pin")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertFalse(report["recursive_content_complete"])
        self.assertIn("fetch failed", report["failures"][0]["error"])
        self.assertFalse(list((self.repo / "external").glob(".p001-source-*")))
        self.assertEqual(list((self.repo / "external/child").iterdir()), [])

    def test_symlink_parent_cannot_escape_root(self):
        (self.repo / "external/child").rmdir()
        (self.repo / "external").rmdir()
        outside = self.base / "outside"
        outside.mkdir()
        (self.repo / "external").symlink_to(outside, target_is_directory=True)
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("symlink", report["failures"][0]["error"])
        self.assertEqual(list(outside.iterdir()), [])

    def test_root_pin_or_declaration_edits_block_before_any_retrieval(self):
        self.git(self.repo, "update-index", "--cacheinfo", "160000", "b" * 40, "external/child")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("staged gitlink", report["failures"][0]["error"])
        self.assertEqual(report["submodules"], [])

    def test_concurrent_staged_pin_change_is_detected_at_final_check(self):
        original_obtain = MODULE.obtain
        def mutation(task, commands):
            result = original_obtain(task, commands)
            if task["path"] == "external/child":
                self.git(self.repo, "update-index", "--cacheinfo", "160000", "b" * 40, "external/child")
            return result
        with mock.patch.object(MODULE, "obtain", side_effect=mutation):
            report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertIn("staged pins changed", report["failures"][-1]["error"])
        self.assertNotIn("parent_source_unchanged", report["source"])

    def test_unrelated_root_edits_and_ambient_git_selector_are_preserved(self):
        source = self.repo / "README.md"
        source.write_text("development notes\n")
        with mock.patch.dict(os.environ, {"GIT_DIR": str(self.nested / ".git"), "GIT_WORK_TREE": str(self.nested)}):
            report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        self.assertEqual(source.read_text(), "development notes\n")
        self.assertEqual(report["source"]["commit"], self.git(self.repo, "rev-parse", "HEAD"))

    def test_root_clean_filter_is_never_executed(self):
        (self.repo / ".gitattributes").write_text("README.md filter=fixture\n")
        self.git(self.repo, "add", ".gitattributes")
        self.git(self.repo, "commit", "-qm", "filter fixture declaration")
        marker = self.base / "filter-must-not-run"
        self.git(self.repo, "config", "filter.fixture.clean", f"touch '{marker}'; cat")
        (self.repo / "README.md").write_text("pre-existing local notes\n")
        report = self.prepare()
        self.assertEqual(report["result"], "PASS", report["failures"])
        self.assertFalse(marker.exists())

    def test_private_urls_and_default_local_transport_are_rejected(self):
        with self.assertRaises(MODULE.RetrievalError):
            MODULE.public_url("https://user:supersecret@github.com/owner/repo.git")
        with self.assertRaises(MODULE.RetrievalError):
            MODULE.public_url(str(self.child))
        self.assertEqual(MODULE.public_url("git@github.com:owner/repo.git"), "https://github.com/owner/repo.git")
        self.assertEqual(MODULE.public_url("git://github.com/owner/repo.git"), "https://github.com/owner/repo.git")
        self.assertEqual(MODULE.public_url("ssh://git@github.com/owner/repo.git"), "https://github.com/owner/repo.git")
        (self.repo / ".gitmodules").write_text('[submodule "dependency"]\npath = external/child\nurl = https://user:supersecret@github.com/owner/repo.git\n')
        self.git(self.repo, "add", ".gitmodules")
        self.git(self.repo, "commit", "-qm", "unsafe URL fixture")
        report = self.prepare()
        self.assertEqual(report["result"], "FAIL")
        self.assertNotIn("supersecret", json.dumps(report))

    def test_cli_writes_atomic_failed_report_and_nonzero_status(self):
        output = self.base / "report.json"
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo),
                                 "--upstream-url", str(self.repo), "--output", str(output)],
                                capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(output.read_text())["result"], "FAIL")
        self.assertFalse(list(self.base.glob(".p001-report-*")))


if __name__ == "__main__":
    unittest.main()
