"""Independent physical-payload and immutable-provenance fixtures for P002 LFS."""

import copy
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
import lfs_manifest as lfs  # noqa: E402


def git(repo, *arguments):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"})
    command = ["git", "-c", "user.name=P002 LFS fixture", "-c", "user.email=fixture@example.invalid",
               "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
    if repo is not None:
        command += ["-C", str(repo)]
    return subprocess.check_output(command + list(arguments), env=environment,
                                   stderr=subprocess.PIPE).decode().strip()


def empty_report():
    return {"result": "FAIL", "commands": [], "repositories": [], "objects": [],
            "errors": [], "expected_lfs_objects": 0, "verified_lfs_objects": 0,
            "verified_payload_bytes": 0}


class PointerParsing(unittest.TestCase):
    def setUp(self):
        self.pointer = (lfs.POINTER_PREFIX + b"\noid sha256:" + b"a" * 64 + b"\nsize 123\n")

    def test_canonical_metadata(self):
        self.assertEqual(lfs.parse_pointer(self.pointer), {"oid_sha256": "a" * 64, "size": 123})

    def test_regular_small_file_is_not_a_pointer(self):
        self.assertIsNone(lfs.parse_pointer(b"This is not a Git LFS pointer.\n"))

    def test_malformed_pointers_fail(self):
        variants = [self.pointer.replace(b"size 123", b"size -1"),
                    self.pointer.replace(b"size 123", b"size 0123"),
                    self.pointer.replace(b"sha256:", b"sha1:"),
                    self.pointer.replace(b"a" * 64, b"A" * 64),
                    self.pointer.replace(b"a" * 64, b"a" * 63),
                    self.pointer.replace(b"\n", b"\r\n"), self.pointer.rstrip(b"\n"),
                    self.pointer + b"size 123\n", self.pointer + b"x" * 1024,
                    self.pointer.replace(b"size 123", b"size 9223372036854775808"),
                    self.pointer.replace(b"spec/v1", b"spec/v9")]
        for content in variants:
            with self.subTest(content=content[:80]), self.assertRaises(lfs.LFSError):
                lfs.parse_pointer(content)

    def test_paths_fail_closed(self):
        for path in ("", ".", "..", "../file", "a/../file", "/file", "a//file", "a/./file",
                     "a\\file", "a/.git/file", "a\nfile", "a\x00file"):
            with self.subTest(path=path), self.assertRaises(lfs.LFSError):
                lfs.safe_path(path)
        self.assertEqual(lfs.safe_path(".", root=True), ".")

    def test_https_endpoint_rejects_credentials_and_nonpublic_addresses(self):
        for url in ("http://example.invalid/lfs", "https://token@example.invalid/lfs",
                    "https://example.invalid/lfs?token=secret", "https://example.invalid/lfs#token",
                    "file:///tmp/lfs", "https://127.0.0.1/lfs", "https://localhost/lfs",
                    "https://10.0.0.1/lfs", "https://2130706433/lfs", "https://127.1/lfs",
                    "https://0x7f000001/lfs", "https://example.invalid:444/lfs", "https://example.invalid/a/../lfs"):
            with self.subTest(url=url), self.assertRaises(lfs.LFSError):
                lfs.safe_https(url)


class RealLFSRepository(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p002-lfs-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "root"
        self.repo = self.root / "owner"
        self.repo.parent.mkdir()
        git(None, "init", "-q", "-b", "main", str(self.repo))
        self.origin = "https://example.invalid/project.git"
        self.endpoint = "https://lfs.example.invalid/project"
        git(self.repo, "remote", "add", "origin", self.origin)
        self.payload = b"real runtime payload\x00\xff\n" * 128
        self.oid = hashlib.sha256(self.payload).hexdigest()
        self.pointer = (lfs.POINTER_PREFIX + b"\noid sha256:" + self.oid.encode()
                        + b"\nsize " + str(len(self.payload)).encode() + b"\n")
        self.file = self.repo / "runtime.bin"
        self.file.write_bytes(self.pointer)
        self.file.chmod(0o755)
        (self.repo / ".lfsconfig").write_text("[lfs]\n\turl = " + self.endpoint + "\n")
        (self.repo / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n")
        self.commit()
        self.metadata = lfs.repository_metadata(self.repo, "owner", self.origin)
        self.objects = lfs.scan_repository(self.repo, "owner", self.origin)
        self.record = self.objects[0]
        self.pin = {"path": "owner", "commit": self.metadata["repository_commit"], "resolved_url": self.origin}
        self.manifest = {"expected_lfs_objects": 1, "lfs_repositories": [self.metadata],
                         "lfs_objects": self.objects, "submodules": [self.pin]}

    def commit(self):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "immutable LFS fixture")

    def materialize(self):
        self.file.write_bytes(self.payload)
        self.file.chmod(0o755)

    def test_inventory_binds_every_pointer_field_to_committed_blob(self):
        self.assertEqual(len(self.objects), 1)
        self.assertEqual(self.record["pointer_blob_sha1"], git(self.repo, "rev-parse", "HEAD:runtime.bin"))
        self.assertEqual(self.record["repository_commit"], git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(self.record["oid_sha256"], self.oid)
        self.assertEqual(self.record["size"], len(self.payload))
        self.assertEqual(self.record["mode"], "100755")
        self.assertEqual(lfs.validate_manifest(self.manifest, [self.pin]), ([self.metadata], self.objects))

    def test_inventory_uses_committed_not_dirty_or_staged_bytes(self):
        self.file.write_bytes(b"corrupt working pointer")
        git(self.repo, "add", "runtime.bin")
        self.assertEqual(lfs.scan_repository(self.repo, "owner", self.origin), self.objects)

    def test_pointer_discovery_is_not_limited_to_lfs_attributes(self):
        (self.repo / "unexpected.data").write_bytes(self.pointer)
        self.commit()
        records = lfs.scan_repository(self.repo, "owner", self.origin)
        self.assertEqual([item["repository_path"] for item in records], ["runtime.bin", "unexpected.data"])

    def test_committed_malformed_pointer_fails(self):
        self.file.write_bytes(self.pointer.replace(b"size ", b"size -"))
        self.commit()
        with self.assertRaises(lfs.LFSError):
            lfs.scan_repository(self.repo, "owner", self.origin)

    def test_unhydrated_pointer_fails(self):
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(self.root, self.record)

    def test_verified_physical_payload_passes(self):
        self.materialize()
        self.assertEqual(lfs.verify_payload(self.root, self.record)["status"], "PASS")

    def test_corrupt_same_size_payload_fails(self):
        self.materialize()
        self.file.write_bytes(b"X" + self.payload[1:])
        with self.assertRaisesRegex(lfs.LFSError, "SHA-256"):
            lfs.verify_payload(self.root, self.record)

    def test_wrong_size_payload_fails(self):
        self.file.write_bytes(self.payload + b"X")
        with self.assertRaisesRegex(lfs.LFSError, "size"):
            lfs.verify_payload(self.root, self.record)

    def test_missing_payload_fails(self):
        self.file.unlink()
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(self.root, self.record)

    def test_wrong_executable_mode_fails(self):
        self.materialize()
        self.file.chmod(0o644)
        git(self.repo, "config", "core.filemode", "false")
        with self.assertRaisesRegex(lfs.LFSError, "mode"):
            lfs.verify_payload(self.root, self.record)

    def test_index_flags_cannot_hide_corrupt_payload(self):
        self.materialize()
        git(self.repo, "update-index", "--assume-unchanged", "runtime.bin")
        git(self.repo, "update-index", "--skip-worktree", "runtime.bin")
        self.file.write_bytes(b"X" + self.payload[1:])
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(self.root, self.record)

    def test_leaf_symlink_fails_without_following_it(self):
        outside = Path(self.temp.name) / "outside.bin"
        outside.write_bytes(self.payload)
        outside.chmod(0o755)
        self.file.unlink()
        self.file.symlink_to(outside)
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(self.root, self.record)

    def test_parent_symlink_fails_without_following_it(self):
        self.materialize()
        moved = Path(self.temp.name) / "moved-owner"
        self.repo.rename(moved)
        self.repo.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(self.root, self.record)

    def test_root_ancestor_symlink_fails(self):
        self.materialize()
        alias = Path(self.temp.name) / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(alias, self.record)

    def test_fifo_fails_without_blocking(self):
        self.file.unlink()
        os.mkfifo(self.file)
        with self.assertRaises(lfs.LFSError):
            lfs.verify_payload(self.root, self.record)

    def test_verifier_does_not_execute_clean_smudge_or_fsmonitor(self):
        self.materialize()
        marker = Path(self.temp.name) / "must-not-run"
        command = "touch " + str(marker)
        git(self.repo, "config", "filter.lfs.clean", command)
        git(self.repo, "config", "filter.lfs.smudge", command)
        git(self.repo, "config", "core.fsmonitor", command)
        self.assertEqual(lfs.scan_repository(self.repo, "owner", self.origin), self.objects)
        self.assertEqual(lfs.verify_payload(self.root, self.record)["status"], "PASS")
        self.assertFalse(marker.exists())

    def test_provenance_does_not_read_worktree_lfsconfig(self):
        (self.repo / ".lfsconfig").write_text("[lfs]\nurl=https://other.invalid/changed\n")
        self.assertEqual(lfs.repository_metadata(self.repo, "owner", self.origin), self.metadata)

    def test_lfsconfig_duplicate_url_include_and_transfer_settings_fail(self):
        variants = ["[lfs]\nurl=" + self.endpoint + "\nurl=" + self.endpoint + "\n",
                    "[lfs]\nurl=" + self.endpoint + "\n[include]\npath=/does/not/exist\n",
                    "[lfs]\nurl=" + self.endpoint + "\nstandalonetransferagent=evil\n"]
        for content in variants:
            with self.subTest(content=content):
                (self.repo / ".lfsconfig").write_text(content)
                self.commit()
                with self.assertRaises(lfs.LFSError):
                    lfs.repository_metadata(self.repo, "owner", self.origin)

    def test_duplicate_missing_and_extra_metadata_fail(self):
        for field, operation in (("lfs_objects", "duplicate"), ("lfs_repositories", "duplicate"),
                                 ("lfs_objects", "remove"), ("lfs_repositories", "remove")):
            broken = copy.deepcopy(self.manifest)
            if operation == "duplicate":
                broken[field].append(copy.deepcopy(broken[field][0]))
            else:
                broken[field].pop()
            if field == "lfs_objects":
                broken["expected_lfs_objects"] = len(broken[field])
            with self.subTest(field=field, operation=operation), self.assertRaises(lfs.LFSError):
                lfs.validate_manifest(broken, [self.pin])

    def test_invalid_metadata_fields_fail(self):
        for key, value in (("oid_sha256", "g" * 64), ("pointer_blob_sha1", "0" * 39),
                           ("repository_commit", "0" * 40), ("size", True), ("size", -1),
                           ("size", 9223372036854775808), ("mode", "120000"),
                           ("path", "elsewhere/runtime.bin"), ("repository_path", "../runtime.bin")):
            broken = copy.deepcopy(self.manifest)
            broken["lfs_objects"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(lfs.LFSError):
                lfs.validate_manifest(broken, [self.pin])

    def test_owner_pin_or_origin_drift_fails(self):
        for field, value in (("commit", "0" * 40), ("resolved_url", "https://other.invalid/repo.git")):
            pin = dict(self.pin, **{field: value})
            with self.subTest(field=field), self.assertRaises(lfs.LFSError):
                lfs.validate_manifest(self.manifest, [pin])

    def test_hydration_rejects_changed_committed_pointer_metadata_before_fetch(self):
        for field, value in (("oid_sha256", "a" * 64), ("pointer_blob_sha1", "0" * 40),
                             ("size", len(self.payload) + 1), ("mode", "100644")):
            broken = copy.deepcopy(self.manifest)
            broken["lfs_objects"][0][field] = value
            with self.subTest(field=field), patch.object(lfs, "_run", return_value="version") as run:
                with self.assertRaises(lfs.LFSError):
                    lfs.hydrate(self.root, broken, empty_report())
                self.assertLessEqual(run.call_count, 1)  # At most version, never fetch/checkout.

    def test_hydration_rejects_endpoint_provenance_drift_before_fetch(self):
        for field, value in (("endpoint", "https://other.invalid/lfs"),
                             ("lfsconfig_blob_sha1", "0" * 40), ("lfsconfig_sha256", "0" * 64)):
            broken = copy.deepcopy(self.manifest)
            broken["lfs_repositories"][0][field] = value
            with self.subTest(field=field), patch.object(lfs, "_run", return_value="version") as run:
                with self.assertRaises(lfs.LFSError):
                    lfs.hydrate(self.root, broken, empty_report())
                self.assertEqual(run.call_count, 1)

    def test_hydration_rejects_extra_or_missing_discovered_records(self):
        (self.repo / "unlisted.bin").write_bytes(self.pointer)
        self.commit()
        self.metadata = lfs.repository_metadata(self.repo, "owner", self.origin)
        broken = copy.deepcopy(self.manifest)
        broken["lfs_repositories"] = [self.metadata]
        for item in broken["lfs_objects"]:
            item["repository_commit"] = self.metadata["repository_commit"]
        broken["submodules"][0]["commit"] = self.metadata["repository_commit"]
        with patch.object(lfs, "_run", return_value="version") as run:
            with self.assertRaisesRegex(lfs.LFSError, "pointer inventory"):
                lfs.hydrate(self.root, broken, empty_report())
            self.assertEqual(run.call_count, 1)

    def test_hydration_rejects_dirty_lfsconfig_before_fetch(self):
        (self.repo / ".lfsconfig").write_text("[lfs]\nurl=https://other.invalid/lfs\n")
        with patch.object(lfs, "_run", return_value="version") as run:
            with self.assertRaisesRegex(lfs.LFSError, "physical .lfsconfig"):
                lfs.hydrate(self.root, self.manifest, empty_report())
            self.assertEqual(run.call_count, 1)

    def test_hydration_rejects_staged_extra_pointer_before_fetch(self):
        (self.repo / "extra.bin").write_bytes(self.pointer)
        git(self.repo, "add", "extra.bin")
        with patch.object(lfs, "_run", return_value="version") as run:
            with self.assertRaisesRegex(lfs.LFSError, "index"):
                lfs.hydrate(self.root, self.manifest, empty_report())
            self.assertEqual(run.call_count, 1)

    def test_hydration_rejects_staged_pointer_drift_before_fetch(self):
        self.file.write_bytes(self.pointer.replace(self.oid.encode(), b"0" * 64))
        git(self.repo, "add", "runtime.bin")
        with patch.object(lfs, "_run", return_value="version") as run:
            with self.assertRaisesRegex(lfs.LFSError, "index"):
                lfs.hydrate(self.root, self.manifest, empty_report())
            self.assertEqual(run.call_count, 1)

    def test_hydration_rejects_local_config_helpers_rewrites_and_transfers(self):
        for name in ("credential.helper", "http.extraHeader", "url.https://evil.invalid/.insteadOf",
                     "filter.lfs.clean", "lfs.standalonetransferagent", "lfs.customtransfer.evil.path",
                     "include.path", "extensions.worktreeConfig"):
            git(self.repo, "config", name, "true" if name == "extensions.worktreeConfig" else "unsafe")
            with self.subTest(name=name), self.assertRaises(lfs.LFSError):
                lfs._check_local_config(self.repo, self.origin)
            git(self.repo, "config", "--unset", name)

    def test_hydration_rejects_private_attributes_and_object_stores_before_fetch(self):
        for relative in ("info/attributes", "objects/info/alternates", "objects/info/http-alternates", "info/grafts"):
            path = self.repo / ".git" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("unapproved private override\n")
            with self.subTest(path=relative), patch.object(lfs, "_run", return_value="version") as run:
                with self.assertRaises(lfs.LFSError):
                    lfs.hydrate(self.root, self.manifest, empty_report())
                self.assertEqual(run.call_count, 1)
            path.unlink()

    def test_hydration_rejects_dirty_attributes_before_fetch(self):
        (self.repo / ".gitattributes").write_text("*.bin filter=attacker\n")
        with patch.object(lfs, "_run", return_value="version") as run:
            with self.assertRaisesRegex(lfs.LFSError, "attributes"):
                lfs.hydrate(self.root, self.manifest, empty_report())
            self.assertEqual(run.call_count, 1)

    def test_real_git_lfs_checkout_materializes_cached_bytes_without_global_installation(self):
        # Only network fetch is stubbed. The installed Git LFS binary executes
        # checkout and its index refresh against a real committed pointer/cache.
        cache = self.repo / ".git/lfs/objects" / self.oid[:2] / self.oid[2:4] / self.oid
        cache.parent.mkdir(parents=True)
        cache.write_bytes(self.payload)
        real_run = lfs._run

        def offline_run(command, environment, report, **kwargs):
            if "fetch" in command:
                return "fixture: verified payload already in isolated local cache"
            return real_run(command, environment, report, **kwargs)

        report = empty_report()
        with patch.object(lfs, "_run", side_effect=offline_run):
            lfs.hydrate(self.root, self.manifest, report)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(self.file.read_bytes(), self.payload)
        self.assertEqual(lfs.scan_repository(self.repo, "owner", self.origin), self.objects)
        lfs._check_index(self.repo)
        lfs._check_local_config(self.repo, self.origin)

    def test_lfs_internal_attribute_selector_finds_committed_pointer(self):
        # Git LFS 3.8.1 uses this magic pathspec internally on Git >= 2.42.
        # A global --literal-pathspecs flag silently turns it into a nonexistent
        # literal filename, even when the public checkout argument is safe.
        command = lfs._lfs_command(self.repo, self.endpoint, "checkout", "--", "runtime.bin")
        probe = command[:command.index("lfs")] + [
            "ls-files", "--cached", "--full-name", "-z", ":(top,attr:filter=lfs)",
        ]
        selected = subprocess.check_output(probe, env=lfs.hydration_environment(), stderr=subprocess.PIPE)
        self.assertEqual(selected, b"runtime.bin\0")

    def test_successful_explicit_hydration_reports_verified_bytes(self):
        commands = []

        def fake_run(command, environment, report, **kwargs):
            commands.append(command)
            if "checkout" in command:
                self.materialize()
            return "git-lfs/fixture"

        report = empty_report()
        with patch.object(lfs, "_run", side_effect=fake_run):
            lfs.hydrate(self.root, self.manifest, report)
        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["verified_lfs_objects"], 1)
        self.assertEqual(report["verified_payload_bytes"], len(self.payload))
        self.assertEqual(commands[1][-6:], ["lfs", "fetch", "--include=", "--exclude=", "origin",
                                           self.metadata["repository_commit"]])
        self.assertIn("lfs.url=" + self.endpoint, commands[1])
        self.assertIn("lfs.basictransfersonly=true", commands[1])
        self.assertIn("credential.helper=", commands[1])
        self.assertIn("http.extraHeader=", commands[1])
        self.assertEqual(commands[2][-4:], ["lfs", "checkout", "--", "runtime.bin"])

    def test_successful_command_exit_with_remaining_pointer_still_fails(self):
        report = empty_report()
        with patch.object(lfs, "_run", return_value="version"):
            with self.assertRaises(lfs.LFSError):
                lfs.hydrate(self.root, self.manifest, report)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["verified_lfs_objects"], 0)

    def test_network_failure_never_falls_back_or_reports_pass(self):
        report = empty_report()
        with patch.object(lfs, "_run", side_effect=["version", lfs.LFSError("endpoint unavailable")]) as run:
            with self.assertRaises(lfs.LFSError):
                lfs.hydrate(self.root, self.manifest, report)
            self.assertEqual(run.call_count, 2)
        self.assertEqual(report["result"], "FAIL")


class AnonymousEnvironment(unittest.TestCase):
    def test_ambient_credentials_and_git_injection_are_removed(self):
        injected = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "credential.helper",
                    "GIT_CONFIG_VALUE_0": "evil", "GIT_LFS_SKIP_DOWNLOAD_ERRORS": "1",
                    "GIT_LITERAL_PATHSPECS": "1", "GIT_GLOB_PATHSPECS": "1",
                    "GITHUB_TOKEN": "secret", "GH_TOKEN": "secret", "CUSTOM_PASSWORD": "secret",
                    "SSH_AUTH_SOCK": "/unsafe", "NETRC": "/unsafe"}
        with patch.dict(os.environ, injected), patch.object(os.path, "lexists", return_value=False):
            environment = lfs.hydration_environment()
        for key in injected:
            self.assertNotIn(key, environment)
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(environment["GIT_ALLOW_PROTOCOL"], "https")

    def test_netrc_presence_is_refused_without_reading_credentials(self):
        with patch.object(os.path, "lexists", return_value=True):
            with self.assertRaisesRegex(lfs.LFSError, "netrc"):
                lfs.hydration_environment()

    def test_committed_provenance_has_exact_swift_inventory(self):
        document = json.loads((ROOT / "docs/compat/logic-pro/lfs-provenance.json").read_text())
        repositories, objects = lfs.validate_manifest(document)
        self.assertEqual(len(repositories), 1)
        self.assertEqual(len(objects), 44)
        self.assertEqual(sum(item["size"] for item in objects), 16128448)
        self.assertEqual(repositories[0]["repository_commit"], "471514f4b4985a604b192e1facac9bbc53dedad3")
        self.assertEqual(repositories[0]["endpoint"], "https://git-lfs.darlinghq.org/lubos/darling-swift")


if __name__ == "__main__":
    unittest.main()
