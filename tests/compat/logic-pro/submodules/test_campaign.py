"""P002 campaign lifecycle, immutable acquisition and failure-evidence fixtures."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
from run_submodule_campaign import (CampaignFailure, Commands, acquire_checkout, checksums,
                                   environment, run_campaign, validate_commit,
                                   verify_hydration_report, verify_lock_regeneration,
                                   verify_native_status, verify_physical_report)


def git(where, *args):
    command = ["git", "-c", "protocol.file.allow=always"]
    if where is not None:
        command += ["-C", str(where)]
    return subprocess.check_output(command + list(args), stderr=subprocess.PIPE,
                                   env=environment(allow_local=True)).decode().strip()


def init(path):
    git(None, "init", "-q", "-b", "main", str(path))
    git(path, "config", "user.name", "P002 Campaign Fixture")
    git(path, "config", "user.email", "fixture@example.invalid")


def commit(path, name):
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", name)
    return git(path, "rev-parse", "HEAD")


class CampaignStructure(unittest.TestCase):
    def test_environment_removes_git_selectors_credentials_and_keeps_network_trust(self):
        inherited = {"PATH": "/usr/bin", "HTTPS_PROXY": "http://session-proxy.invalid:8080",
                     "SSL_CERT_FILE": "/session/ca.pem", "GIT_DIR": "/other/repo",
                     "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "credential.helper",
                     "GIT_CONFIG_VALUE_0": "injected", "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/cache",
                     "GITHUB_TOKEN": "not-a-real-token", "GH_TOKEN": "not-a-real-token",
                     "SSH_AUTH_SOCK": "/agent", "SSH_ASKPASS": "/askpass"}
        with patch.dict(os.environ, inherited, clear=True):
            actual = environment()
        for name in ("GIT_DIR", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0",
                     "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GITHUB_TOKEN", "GH_TOKEN", "SSH_AUTH_SOCK", "SSH_ASKPASS"):
            self.assertNotIn(name, actual)
        self.assertEqual(actual["HTTPS_PROXY"], inherited["HTTPS_PROXY"])
        self.assertEqual(actual["SSL_CERT_FILE"], inherited["SSL_CERT_FILE"])
        self.assertEqual(actual["GIT_ALLOW_PROTOCOL"], "https")
        self.assertEqual(actual["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(actual["GIT_TERMINAL_PROMPT"], "0")

    def test_netrc_credentials_are_refused_without_reading_the_file(self):
        with patch("run_submodule_campaign.os.path.lexists", return_value=True):
            with self.assertRaisesRegex(CampaignFailure, "netrc credential"):
                environment()

    def test_ref_names_and_shell_text_cannot_replace_immutable_sha(self):
        self.assertEqual(validate_commit("a" * 40), "a" * 40)
        for value in ("master", "refs/pull/42/merge", "HEAD", "A" * 40, "a" * 39, "a" * 40 + "; true", None):
            with self.subTest(value=value), self.assertRaises(CampaignFailure):
                validate_commit(value)

    def test_native_git_status_is_an_independent_exact_path_and_pin_oracle(self):
        lock = {"expected_recursive_gitlinks": 2, "submodules": [
            {"path": "a", "commit": "1" * 40}, {"path": "a/nested", "commit": "2" * 40}]}
        good = f" {'1' * 40} a (heads/main)\n {'2' * 40} a/nested\n".encode()
        self.assertEqual(verify_native_status(good, lock), 2)
        for bad in (good.replace(b" a ", b" wrong "), good.replace(b"1" * 40, b"9" * 40),
                    b"-" + good[1:], b"+" + good[1:], b"U" + good[1:], b"",
                    good.splitlines(keepends=True)[0], good + good):
            with self.subTest(bad=bad), self.assertRaises(CampaignFailure):
                verify_native_status(bad, lock)

    def test_lock_regeneration_is_byte_exact_not_only_semantic_json(self):
        with tempfile.TemporaryDirectory(prefix="p002-campaign-lock-") as tmp:
            out = Path(tmp)
            before, after = out / "expected.json", out / "actual.json"
            before.write_text('{"lock": 1}\n')
            after.write_text(before.read_text())
            verify_lock_regeneration(before, after, out)
            self.assertEqual(json.loads((out / "lock-regeneration.json").read_text())["result"], "PASS")
            after.write_text('{"lock":1}\n')
            with self.assertRaises(CampaignFailure):
                verify_lock_regeneration(before, after, out)
            self.assertEqual(json.loads((out / "lock-regeneration.json").read_text())["result"], "FAIL")

    def test_hydration_report_must_prove_exact_locked_payloads(self):
        record = {"path": "sub/data.bin", "oid_sha256": "a" * 64, "mode": "100644", "size": 23}
        lock = {"expected_lfs_objects": 1, "lfs_objects": [record]}
        good = {"result": "PASS", "expected_lfs_objects": 1, "verified_lfs_objects": 1,
                "verified_payload_bytes": 23, "objects": [dict(record, status="PASS")], "errors": []}
        self.assertEqual(verify_hydration_report(good, lock), (1, 23))
        for field, bad in (("result", "FAIL"), ("expected_lfs_objects", 0), ("verified_lfs_objects", 0),
                           ("verified_payload_bytes", 22), ("objects", []), ("errors", ["retrieval failed"]),
                           ("objects", [dict(record, oid_sha256="b" * 64, status="PASS")]),
                           ("objects", [dict(record, status="FAIL")])):
            with self.subTest(field=field, bad=bad), self.assertRaises(CampaignFailure):
                verify_hydration_report(dict(good, **{field: bad}), lock)

    def test_physical_verifier_report_must_match_complete_campaign(self):
        lock = {"expected_lfs_objects": 1, "lfs_objects": [{"size": 23}], "submodules": [{}, {}]}
        good = {"result": "PASS", "root_commit": "a" * 40, "schema_version": 2, "verified_gitlinks": 2,
                "verified_repositories": 3, "verified_physical_blobs": 10, "verified_lfs_payloads": 1,
                "verified_lfs_bytes": 23,
                "verification_method": "physical_committed_bytes_modes_symlinks_and_lfs_sha256_without_filters"}
        verify_physical_report(good, lock, "a" * 40)
        for field, bad in (("result", "FAIL"), ("root_commit", "b" * 40), ("schema_version", 1),
                           ("verified_gitlinks", 1), ("verified_repositories", 2),
                           ("verified_physical_blobs", 2), ("verified_physical_blobs", None),
                           ("verified_lfs_payloads", 0), ("verified_lfs_bytes", 22),
                           ("verification_method", "index_status_only")):
            with self.subTest(field=field, bad=bad), self.assertRaises(CampaignFailure):
                verify_physical_report(dict(good, **{field: bad}), lock, "a" * 40)

    def test_failure_keeps_raw_output_exit_code_command_and_checksums(self):
        with tempfile.TemporaryDirectory(prefix="p002-campaign-failure-") as tmp:
            out = Path(tmp)
            commands = Commands(out)
            with self.assertRaises(CampaignFailure):
                commands.run("fixture-failure", [sys.executable, "-B", "-c", "print('failure evidence'); raise SystemExit(23)"],
                             "fixture-tests.log")
            self.assertEqual((out / "fixture-tests.log").read_text(), "failure evidence\n")
            records = json.loads((out / "commands.json").read_text())
            self.assertEqual(records[-1]["exit_code"], 23)
            self.assertEqual(records[-1]["output_sha256"], hashlib.sha256(b"failure evidence\n").hexdigest())
            checksums(out)
            self.assertIn("  fixture-tests.log\n", (out / "checksums.sha256").read_text())
            self.assertIn("  commands.json\n", (out / "checksums.sha256").read_text())

    def test_command_timeout_and_append_logs_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix="p002-campaign-timeout-") as tmp:
            out = Path(tmp)
            commands = Commands(out)
            commands.run("first", [sys.executable, "-B", "-c", "print('first')"], "clone-a.log")
            with self.assertRaises(CampaignFailure):
                commands.run("timeout", [sys.executable, "-B", "-c", "import time; print('started',flush=True); time.sleep(2)"],
                             "clone-a.log", append=True, timeout=0.05)
            self.assertIn("first\n", (out / "clone-a.log").read_text())
            self.assertIn("P002 command timed out", (out / "clone-a.log").read_text())
            self.assertEqual(commands.records[-1]["exit_code"], 124)
            self.assertGreater(commands.records[-1]["log_offset"], 0)


class ImmutableAcquisition(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p002-campaign-git-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.child_source, self.root_source = self.base / "child-source", self.base / "root-source"
        self.child_bare, self.root_bare = self.base / "child.git", self.base / "root.git"
        init(self.child_source)
        (self.child_source / "data.txt").write_text("old child\n")
        self.child_old = commit(self.child_source, "old child")
        git(None, "clone", "-q", "--bare", str(self.child_source), str(self.child_bare))
        init(self.root_source)
        (self.root_source / "data.txt").write_text("old root\n")
        git(self.root_source, "submodule", "add", "-q", self.child_bare.as_uri(), "sub")
        self.old = commit(self.root_source, "old root")
        (self.child_source / "data.txt").write_text("new child\n")
        self.child_new = commit(self.child_source, "new child")
        git(self.child_source, "push", "-q", self.child_bare.as_uri(), "HEAD:main")
        git(self.root_source / "sub", "fetch", "-q", "origin")
        git(self.root_source / "sub", "checkout", "-q", self.child_new)
        (self.root_source / "data.txt").write_text("new root\n")
        self.latest = commit(self.root_source, "advanced root")
        git(None, "clone", "-q", "--bare", str(self.root_source), str(self.root_bare))
        self.output = self.base / "evidence"
        self.output.mkdir()
        self.commands = Commands(self.output, allow_local=True)

    def test_advanced_branch_cannot_change_requested_root_or_child_pin(self):
        destination = self.base / "clone"
        head = acquire_checkout(self.root_bare.as_uri(), self.old, destination, self.commands, jobs=2)
        self.assertEqual(head, self.old)
        self.assertNotEqual(head, self.latest)
        self.assertEqual(git(destination / "sub", "rev-parse", "HEAD"), self.child_old)
        self.assertEqual((destination / "sub/data.txt").read_text(), "old child\n")
        self.assertEqual(git(destination, "remote", "get-url", "origin"), self.root_bare.as_uri())
        self.assertFalse((destination / ".git/objects/info/alternates").exists())
        self.assertEqual((self.output / "head.sha").read_text().strip(), self.old)

    def test_public_pr_only_commit_is_fetched_by_exact_sha_not_master(self):
        isolated = self.base / "pr-source"
        init(isolated)
        (isolated / "pull-request.txt").write_text("public merge object\n")
        pull_sha = commit(isolated, "pull-only root")
        git(isolated, "push", "-q", self.root_bare.as_uri(), "HEAD:refs/pull/42/merge")
        destination = self.base / "pr-clone"
        acquire_checkout(self.root_bare.as_uri(), pull_sha, destination, self.commands, jobs=2)
        self.assertEqual(git(destination, "rev-parse", "HEAD"), pull_sha)
        fetches = [x for x in self.commands.records if x["label"] == "fetch-exact-commit"]
        self.assertEqual(len(fetches), 1)
        self.assertEqual(fetches[0]["command"][-1], pull_sha)
        self.assertNotIn("master", fetches[0]["command"])

    def test_unavailable_commit_fails_and_keeps_acquisition_evidence(self):
        with self.assertRaises(CampaignFailure):
            acquire_checkout(self.root_bare.as_uri(), "f" * 40, self.base / "missing", self.commands)
        self.assertTrue((self.output / "clone-a.log").is_file())
        self.assertNotEqual(self.commands.records[-1]["exit_code"], 0)
        self.assertEqual(self.commands.records[-1]["label"], "fetch-exact-commit")

    def test_existing_destination_is_never_removed_or_reused(self):
        destination = self.base / "owned-by-user"
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_text("preserve me\n")
        with self.assertRaises(CampaignFailure):
            acquire_checkout(self.root_bare.as_uri(), self.old, destination, self.commands)
        self.assertEqual(marker.read_text(), "preserve me\n")
        self.assertEqual(self.commands.records, [])

    def test_wrong_source_head_fails_with_a_persisted_campaign_report(self):
        output = self.base / "failed-campaign"
        result = run_campaign(self.root_source, self.base / "campaign-clone", output, self.old,
                              url=self.root_bare.as_uri(), allow_local=True)
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("source HEAD differs", result["failures"][0])
        self.assertEqual(json.loads((output / "summary.json").read_text())["result"], "FAIL")
        self.assertTrue((output / "commands.json").is_file())
        self.assertTrue((output / "checksums.sha256").is_file())
        self.assertFalse((self.base / "campaign-clone").exists())

    def test_stale_evidence_and_overlapping_paths_are_rejected_without_deletion(self):
        marker = self.output / "keep.txt"
        marker.write_text("old evidence\n")
        with self.assertRaises(FileExistsError):
            run_campaign(self.root_source, self.base / "campaign-clone", self.output, self.latest,
                         url=self.root_bare.as_uri(), allow_local=True)
        self.assertEqual(marker.read_text(), "old evidence\n")
        with self.assertRaises(CampaignFailure):
            run_campaign(self.root_source, self.root_source / "clone", self.base / "fresh-output", self.latest,
                         url=self.root_bare.as_uri(), allow_local=True)

    def test_dangling_clone_and_evidence_symlinks_are_rejected_without_following(self):
        dangling = self.base / "dangling"
        absent = self.base / "absent-target"
        dangling.symlink_to(absent, target_is_directory=True)
        for destination, output in ((dangling, self.base / "fresh-evidence"),
                                    (self.base / "fresh-clone", dangling)):
            with self.subTest(destination=destination), self.assertRaises(CampaignFailure):
                run_campaign(self.root_source, destination, output, self.latest,
                             url=self.root_bare.as_uri(), allow_local=True)
        self.assertTrue(dangling.is_symlink())
        self.assertFalse(absent.exists())


if __name__ == "__main__":
    unittest.main()
