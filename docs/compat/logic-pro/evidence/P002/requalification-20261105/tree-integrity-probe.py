#!/usr/bin/env python3
"""Confirm native Git rejects a corrupt tree despite matching index/files.

Creates only a temporary fixture. This is a bounded source-integrity review
case, not a new production verifier or phase acceptance command.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zlib


def main():
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       GIT_NO_REPLACE_OBJECTS="1")
    with tempfile.TemporaryDirectory(prefix="p002-tree-object-probe-") as folder:
        root = Path(folder)
        command = ["git", "-c", "core.hooksPath=" + os.devnull,
                   "-c", "core.fsmonitor=false", "-c", "core.autocrlf=false", "-C", folder]

        def git(*args, data=None):
            return subprocess.check_output(command + list(args), env=environment,
                                           input=data, stderr=subprocess.PIPE).decode().strip()

        git("init", "-q", "-b", "main")
        git("config", "user.name", "Object fixture")
        git("config", "user.email", "fixture@example.invalid")
        (root / "file").write_bytes(b"old\n")
        git("add", "file")
        git("commit", "-q", "-m", "fixture")
        expected_tree = git("rev-parse", "HEAD^{tree}")
        replacement = git("hash-object", "-w", "--stdin", data=b"new\n")
        raw = b"100644 file\0" + bytes.fromhex(replacement)
        framed = b"tree " + str(len(raw)).encode() + b"\0" + raw
        actual_tree = hashlib.sha1(framed).hexdigest()
        assert actual_tree != expected_tree
        stored = root / ".git/objects" / expected_tree[:2] / expected_tree[2:]
        stored.chmod(0o644)
        stored.write_bytes(zlib.compress(framed))
        (root / "file").write_bytes(b"new\n")
        git("update-index", "--cacheinfo", "100644," + replacement + ",file")
        checks = []
        for args in [("ls-tree", "-r", "HEAD"), ("status", "--porcelain"), ("fsck", "--full")]:
            result = subprocess.run(command + list(args), env=environment, capture_output=True)
            stdout, stderr = result.stdout.decode(), result.stderr.decode()
            assert result.returncode != 0
            assert "hash-path mismatch" in stderr if args[0] == "fsck" else "hash mismatch" in stderr
            checks.append({"command": list(args), "exit_code": result.returncode,
                           "stdout": stdout, "stderr": stderr})
        print(json.dumps({"git_version": git("--version"), "expected_tree": expected_tree,
                          "forged_tree_content_hash": actual_tree, "checks": checks,
                          "result": "CORRUPT_TREE_REJECTED", "production_change_required": False},
                         indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
