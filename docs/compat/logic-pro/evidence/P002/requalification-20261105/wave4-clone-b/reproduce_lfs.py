#!/usr/bin/env python3
"""Wave 4 LFS failures/recoveries in disposable local repositories, without network.

Uses the tested fixture's repository construction, but explicit review-owned
mutations, rejection expectations and recovered-byte assertions. No real payload
checkout is modified. The cached checkout executes the installed Git LFS binary.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from unittest.mock import patch


def run(repo):
    sys.path[:0] = [str(repo / "tests/compat/logic-pro/submodules"), str(repo / "tools/compat/logic-pro")]
    import test_lfs as fixtures
    import lfs_manifest as lfs
    results = []

    def fixture():
        case = fixtures.RealLFSRepository("test_verified_physical_payload_passes")
        case.setUp()
        return case

    def corrupt(case):
        data = bytearray(case.payload)
        data[len(data) // 2] ^= 0x80
        case.file.write_bytes(data)

    def flagged(case, flag):
        fixtures.git(case.repo, "update-index", flag, "runtime.bin")
        corrupt(case)

    def symlink(case):
        case.file.unlink()
        target = case.repo / "alternate.bin"
        target.write_bytes(case.payload)
        target.chmod(0o755)
        case.file.symlink_to(target)

    def fifo(case):
        case.file.unlink()
        os.mkfifo(case.file)

    mutations = [
        ("unhydrated_pointer", lambda c: c.file.write_bytes(c.pointer)),
        ("same_size_corruption", corrupt),
        ("truncated_payload", lambda c: c.file.write_bytes(c.payload[:-1])),
        ("missing_payload", lambda c: c.file.unlink()),
        ("wrong_executable_mode", lambda c: c.file.chmod(0o644)),
        ("assume_unchanged_corruption", lambda c: flagged(c, "--assume-unchanged")),
        ("skip_worktree_corruption", lambda c: flagged(c, "--skip-worktree")),
        ("leaf_symlink", symlink),
        ("fifo", fifo),
    ]
    for name, mutate in mutations:
        case = fixture()
        try:
            case.materialize()
            assert lfs.verify_payload(case.root, case.record)["status"] == "PASS"
            mutate(case)
            try:
                lfs.verify_payload(case.root, case.record)
            except lfs.LFSError as error:
                rejection = str(error)
            else:
                raise AssertionError("false PASS: " + name)
            if os.path.lexists(case.file):
                case.file.unlink()
            fixtures.git(case.repo, "update-index", "--no-assume-unchanged", "--no-skip-worktree", "runtime.bin")
            case.materialize()
            recovered = lfs.verify_payload(case.root, case.record)
            assert recovered["status"] == "PASS" and case.file.read_bytes() == case.payload
            results.append({"case": name, "corruption": "REJECTED", "reason": rejection, "recovery": recovered})
        finally:
            case.doCleanups()

    case = fixture()
    try:
        case.materialize()
        moved = case.repo.with_name("owner-real")
        case.repo.rename(moved)
        case.repo.symlink_to(moved, target_is_directory=True)
        try:
            lfs.verify_payload(case.root, case.record)
        except lfs.LFSError as error:
            rejection = str(error)
        else:
            raise AssertionError("parent symlink accepted")
        case.repo.unlink()
        moved.rename(case.repo)
        results.append({"case": "parent_symlink", "corruption": "REJECTED", "reason": rejection, "recovery": lfs.verify_payload(case.root, case.record)})
    finally:
        case.doCleanups()

    case = fixture()
    try:
        cache = case.repo / ".git/lfs/objects" / case.oid[:2] / case.oid[2:4] / case.oid
        cache.parent.mkdir(parents=True)
        cache.write_bytes(case.payload)
        argv = lfs._lfs_command(case.repo, case.endpoint, "checkout", "--", "runtime.bin")
        completed = subprocess.run(argv, env=lfs.hydration_environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert completed.returncode == 0
        recovered = lfs.verify_payload(case.root, case.record)
        assert case.file.read_bytes() == case.payload
        results.append({"case": "real_git_lfs_cached_checkout", "command": argv, "exit_code": completed.returncode, "output": completed.stdout.decode(), "output_sha256": hashlib.sha256(completed.stdout).hexdigest(), "recovery": recovered, "scope": "locally seeded synthetic cache; actual Git LFS checkout; no network acquisition claim"})
    finally:
        case.doCleanups()

    for name, side_effect in [("zero_exit_with_pointer_left", None), ("network_failure_no_fallback", ["version", lfs.LFSError("review fixture endpoint unavailable")])]:
        case = fixture()
        try:
            report = fixtures.empty_report()
            with patch.object(lfs, "_run", return_value="version", side_effect=side_effect) as command:
                try:
                    lfs.hydrate(case.root, case.manifest, report)
                except lfs.LFSError as error:
                    rejection = str(error)
                else:
                    raise AssertionError("hydration false PASS: " + name)
                calls = command.call_count
            assert report["result"] == "FAIL" and report["verified_lfs_objects"] == 0
            assert calls == (3 if side_effect is None else 2)
            results.append({"case": name, "result": "REJECTED", "reason": rejection, "hydration_result": report["result"], "verified_payloads": report["verified_lfs_objects"], "command_calls": calls, "scope": "mock command outcome; real physical verification and hydration decision"})
        finally:
            case.doCleanups()
    return {"result": "PASS", "tested_source": "d58cca513559cfef0ff9af59aa5dc3b6341bdf77", "python": platform.python_version(), "git": subprocess.check_output(["git", "--version"]).decode().strip(), "git_lfs": subprocess.check_output(["git", "lfs", "version"]).decode().strip(), "cases": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.repo.resolve())
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: 10 physical corruption/recovery cases; real Git LFS cached checkout; zero-exit pointer and network-failure rejection")
