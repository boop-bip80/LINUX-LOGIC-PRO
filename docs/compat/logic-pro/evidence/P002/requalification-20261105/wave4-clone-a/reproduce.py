#!/usr/bin/env python3
"""Independent synthetic repositories exercise the exact tested verifier.

No dependency source or network is read. Every mutated object belongs to a
temporary fixture; production code is imported without modification.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zlib


TESTED = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.repo / "tools/compat/logic-pro"))
    import check_submodules
    import inventory
    import run_submodule_campaign

    environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1",
                   "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "file",
                   "GIT_AUTHOR_NAME": "Independent P002 Reviewer", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                   "GIT_COMMITTER_NAME": "Independent P002 Reviewer", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                   "GIT_AUTHOR_DATE": "2026-11-06T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-11-06T00:00:00+00:00"}

    def command(repo, *argv, data=None, must_succeed=True):
        result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                                 "-c", "core.autocrlf=false", "-C", str(repo), *argv],
                                input=data, capture_output=True, env=environment, timeout=30)
        if must_succeed and result.returncode:
            raise AssertionError(f"fixture setup git {argv}: {result.stderr.decode(errors='replace')}")
        return result

    def git(repo, *argv, data=None):
        return command(repo, *argv, data=data).stdout

    source_hashes = {}
    for name in ("inventory.py", "check_submodules.py", "lfs_manifest.py", "run_submodule_campaign.py"):
        path = "tools/compat/logic-pro/" + name
        expected = git(args.repo, "show", TESTED + ":" + path)
        require((args.repo / path).read_bytes() == expected, "fixture must use exact tested " + name)
        source_hashes[path] = hashlib.sha256(expected).hexdigest()

    results = []

    def record(name, **details):
        results.append({"case": name, "result": "PASS", **details})
        print(name + ": PASS", flush=True)

    def rejects(name, action, expected_text):
        try:
            action()
        except (inventory.InventoryError, check_submodules.LockFailure, OSError, ValueError) as error:
            require(expected_text in str(error), name + " failed for an unexpected reason: " + str(error))
            record(name, rejection_type=type(error).__name__, rejection=str(error))
        else:
            raise AssertionError(name + " falsely accepted")

    def initialize(repo, object_format="sha1"):
        repo.mkdir(parents=True)
        git(repo, "init", "-q", "-b", "main", "--object-format=" + object_format)
        git(repo, "config", "core.filemode", "true")
        git(repo, "config", "core.symlinks", "true")

    def commit(repo):
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "synthetic reviewer fixture")

    def replace_object(repo, oid, kind, data):
        loose = repo / ".git/objects" / oid[:2] / oid[2:]
        loose.chmod(0o644)
        loose.write_bytes(zlib.compress(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data))

    with tempfile.TemporaryDirectory(prefix="p002-independent-wave4-a-") as temporary:
        base = Path(temporary)

        # Both supported object algorithms: valid binary/empty reads and corrupt
        # content under a real expected object name. The corrupt bytes also have
        # a valid framing/size, so header-only validation would falsely accept.
        for algorithm in ("sha1", "sha256"):
            repo = base / ("blobs-" + algorithm)
            initialize(repo, algorithm)
            objects = {}
            for value in (b"", b"first\nsecond\n", b"\0binary\xff\r\n"):
                oid = git(repo, "hash-object", "-w", "--stdin", data=value).decode().strip()
                objects[oid] = value
            require(inventory.read_blobs(repo, list(objects) * 2) == objects, "valid canonical blobs")
            record("valid_blob_controls_" + algorithm, object_count=3)
            original = b"reviewer-original\n"
            forged = b"reviewer-forged!!\n"
            oid = git(repo, "hash-object", "-w", "--stdin", data=original).decode().strip()
            replace_object(repo, oid, "blob", forged)
            raw = git(repo, "cat-file", "--batch", data=(oid + "\n").encode())
            require(raw == f"{oid} blob {len(forged)}\n".encode() + forged + b"\n", "actual native batch trust behavior")
            rejects("forged_loose_blob_" + algorithm,
                    lambda: inventory.read_blobs(repo, [oid]), "content does not match its object ID")
            results[-1]["native_batch_returns_forged_bytes_under_expected_oid"] = True
            fsck = command(repo, "fsck", "--full", must_succeed=False)
            require(fsck.returncode != 0, "fsck should reject forged blob")
            results[-1]["fsck_exit"] = fsck.returncode

        def recursive_fixture(name):
            root = base / name
            initialize(root)
            child = root / "dep"
            initialize(child)
            (child / "child.txt").write_bytes(b"reviewer child content\n")
            commit(child)
            root_url = "https://github.com/reviewer-fixture/root.git"
            child_url = "https://github.com/reviewer-fixture/child.git"
            git(root, "remote", "add", "origin", root_url)
            git(child, "remote", "add", "origin", child_url)
            (root / ".gitmodules").write_text('[submodule "dep"]\n\tpath = dep\n\turl = ' + child_url + '\n')
            (root / ".gitattributes").write_bytes(b"project.txt text eol=crlf\n")
            (root / "project.txt").write_bytes(b"first\nsecond\n")
            (root / "plain.txt").write_bytes(b"unchanged plain file\n")
            (root / "run.sh").write_bytes(b"#!/bin/sh\nexit 0\n")
            (root / "run.sh").chmod(0o755)
            (root / "link").symlink_to("plain.txt")
            (root / "directory").mkdir()
            (root / "directory/file.txt").write_bytes(b"nested regular file\n")
            commit(root)
            (root / "project.txt").write_bytes(b"first\r\nsecond\r\n")
            lock = {"schema_version": 2, "phase": "P002", "root_origin": root_url,
                    "root_gitmodules_blob_sha1": git(root, "rev-parse", "HEAD:.gitmodules").decode().strip(),
                    "expected_lfs_objects": 0, "lfs_repositories": [], "lfs_objects": [],
                    "expected_direct_gitlinks": 1, "expected_recursive_gitlinks": 1,
                    "submodules": [{"path": "dep", "parent_path": ".", "declared_url": child_url,
                                    "resolved_url": child_url,
                                    "commit": git(child, "rev-parse", "HEAD").decode().strip(),
                                    "tree": git(child, "rev-parse", "HEAD^{tree}").decode().strip()}]}
            return root, lock

        root, lock = recursive_fixture("positive")
        positive = check_submodules.verify(root, lock)
        require(positive["verified_repositories"] == 2 and positive["verified_gitlinks"] == 1 and
                positive["verified_physical_blobs"] == 8 and positive["standard_crlf_paths"] == ["project.txt"],
                "full positive verifier with mode, symlink, and CRLF")
        record("full_verifier_positive", verified_repositories=2, verified_physical_blobs=8,
               verified_gitlinks=1, standard_crlf_paths=["project.txt"])

        root, lock = recursive_fixture("hidden-dirty")
        (root / "project.txt").write_bytes(b"first\nsecond\n")
        git(root, "update-index", "--assume-unchanged", "plain.txt")
        (root / "plain.txt").write_bytes(b"concealed modified file\n")
        status = git(root, "status", "--porcelain")
        require(not status, "assume-unchanged must actually conceal mutation from status: " + repr(status))
        rejects("hidden_dirty_bytes", lambda: check_submodules.verify(root, lock), "physical checkout is dirty: plain.txt")
        results[-1]["native_status_empty"] = True

        root, lock = recursive_fixture("executable-mode")
        (root / "run.sh").chmod(0o644)
        rejects("executable_bit_changed", lambda: check_submodules.verify(root, lock), "physical checkout is dirty: run.sh")

        root, lock = recursive_fixture("symlink-target")
        (root / "link").unlink()
        (root / "link").symlink_to("project.txt")
        rejects("symlink_target_changed", lambda: check_submodules.verify(root, lock), "physical checkout is dirty: link")

        root, lock = recursive_fixture("symlink-parent")
        outside = base / "outside-parent"
        shutil.move(str(root / "directory"), outside)
        (root / "directory").symlink_to(outside, target_is_directory=True)
        rejects("symlink_parent_escape", lambda: check_submodules.verify(root, lock), "physical checkout is dirty: directory/file.txt")

        root, lock = recursive_fixture("forged-crlf")
        oid = git(root, "rev-parse", "HEAD:project.txt").decode().strip()
        forged = b"forged source\nsecond\n"
        replace_object(root, oid, "blob", forged)
        (root / "project.txt").write_bytes(forged.replace(b"\n", b"\r\n"))
        # Exercise both the narrow waiver and the complete verifier.
        entries = inventory.tree_entries(root, "HEAD")
        rejects("forged_crlf_waiver", lambda: check_submodules.verify_checkout(root, entries, [], root),
                "content does not match its object ID")
        rejects("forged_crlf_full_verifier", lambda: check_submodules.verify(root, lock),
                "content does not match its object ID")

        root, lock = recursive_fixture("corrupt-gitlink")
        child = root / "dep"
        git(child, "commit", "-q", "--allow-empty", "-m", "changed pin")
        changed = git(child, "rev-parse", "HEAD").decode().strip()
        git(root, "update-index", "--cacheinfo", "160000," + changed + ",dep")
        git(root, "commit", "-q", "-m", "wrong committed pin")
        rejects("committed_gitlink_changed", lambda: check_submodules.verify(root, lock), "wrong pinned gitlink for dep")

        root, lock = recursive_fixture("corrupt-url")
        git(root, "config", "-f", ".gitmodules", "submodule.dep.url", "https://github.com/reviewer-fixture/other.git")
        commit(root)
        rejects("committed_url_changed", lambda: check_submodules.verify(root, lock), "complete root .gitmodules metadata differs from lock")

        root, lock = recursive_fixture("existing-clone")
        class NoCommands:
            allow_local = False
            def run(self, *args, **kwargs):
                raise AssertionError("existing destination should fail before any command")
        rejects("existing_clone_is_not_reused", lambda: run_submodule_campaign.acquire_checkout(
            lock["root_origin"], TESTED, root, NoCommands()), "existing objects are never reused")

        root, lock = recursive_fixture("corrupt-tree")
        # Make a distinct valid tree and matching index/worktree first, then
        # store its actual raw bytes under the original HEAD tree's expected OID.
        # If native tree reading trusted the loose filename, every physical
        # file and index entry would agree with that forged interpretation.
        original_tree = git(root, "rev-parse", "HEAD^{tree}").decode().strip()
        (root / "plain.txt").write_bytes(b"forged tree selects this blob\n")
        git(root, "add", "plain.txt")
        forged_tree = git(root, "write-tree").decode().strip()
        require(original_tree != forged_tree, "tree corruption must change the canonical object")
        forged_tree_bytes = git(root, "cat-file", "tree", forged_tree)
        replace_object(root, original_tree, "tree", forged_tree_bytes)
        outcomes = {}
        for name, argv in (("ls_tree", ("ls-tree", "-r", "HEAD")),
                           ("status", ("status", "--porcelain")), ("fsck", ("fsck", "--full"))):
            result = command(root, *argv, must_succeed=False)
            require(result.returncode != 0, "native " + name + " accepted corrupt tree")
            outcomes[name] = {"exit_code": result.returncode,
                              "diagnostic": (result.stdout + result.stderr).decode(errors="replace").replace(str(base), "<fixture>")}
        rejects("forged_tree_with_matching_index_and_worktree", lambda: check_submodules.verify(root, lock),
                "git ls-tree failed")
        results[-1].update(native_git=outcomes, original_tree=original_tree, forged_tree=forged_tree)

    output = {"result": "PASS", "scope": "independent synthetic clone A integrity reproductions",
              "tested_commit": TESTED, "git_version": git(args.repo, "--version").decode().strip(),
              "reviewed_source_sha256": source_hashes, "cases": results,
              "total_cases": len(results), "network_used": False, "production_changes": False}
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "PASS", "total_cases": len(results)}, sort_keys=True))


if __name__ == "__main__":
    main()
