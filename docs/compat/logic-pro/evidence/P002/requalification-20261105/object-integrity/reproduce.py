#!/usr/bin/env python3
"""Run against a source checkout: python -B reproduce.py /path/to/source."""

from pathlib import Path
import subprocess
import sys
import tempfile
import zlib

source = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(source / "tools/compat/logic-pro"))
import check_submodules
import inventory

with tempfile.TemporaryDirectory(prefix="p002-blob-repro-") as temporary:
    root = Path(temporary)

    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "core.autocrlf=false", "-c", "core.hooksPath=/dev/null",
             "-C", str(root), *args], stderr=subprocess.STDOUT,
            env=inventory.git_environment())

    git("init", "-q", "-b", "main", "--object-format=sha1")
    git("config", "user.name", "P002 Test")
    git("config", "user.email", "fixture@example.invalid")
    (root / ".gitattributes").write_bytes(b"project.vcxproj text eol=crlf\n")
    (root / "project.vcxproj").write_bytes(b"original\n")
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")
    entries = inventory.tree_entries(root, "HEAD")
    oid = next(entry["object"] for entry in entries if entry["path"] == "project.vcxproj")
    forged = b"forged!!\n"
    obj = root / ".git" / "objects" / oid[:2] / oid[2:]
    obj.chmod(0o644)
    obj.write_bytes(zlib.compress(b"blob " + str(len(forged)).encode() + b"\0" + forged))
    (root / "project.vcxproj").write_bytes(forged.replace(b"\n", b"\r\n"))
    print("expected object ID:", oid)
    try:
        print("read_blobs trusts forged bytes:", inventory.read_blobs(root, [oid])[oid] == forged)
    except inventory.InventoryError as exc:
        print("read_blobs rejected:", type(exc).__name__, str(exc))
    try:
        print("verify_checkout:", check_submodules.verify_checkout(root, entries, [], root))
    except inventory.InventoryError as exc:
        print("verify_checkout rejected:", type(exc).__name__, str(exc))
    checked = subprocess.run(["git", "-C", str(root), "fsck", "--full"],
                             capture_output=True, text=True, env=inventory.git_environment())
    print("git fsck exit:", checked.returncode)
    print((checked.stdout + checked.stderr).strip())
