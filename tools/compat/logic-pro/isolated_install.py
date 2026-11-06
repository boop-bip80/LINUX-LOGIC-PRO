#!/usr/bin/env python3
"""Own and remove only a dedicated P003 test installation, failing closed."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys

from verify_build_install import CONTROL_FILE, VerificationError, require, snapshot


def checked_prefix(prefix):
    prefix = Path(prefix)
    require(prefix.is_absolute() and str(prefix) == os.path.normpath(prefix), "prefix must be absolute and normalized")
    require(".." not in prefix.parts, "parent traversal is forbidden")
    require(len(prefix.parts) >= 3 and prefix.parts[1] in ("opt", "tmp"), "only a dedicated child of /opt or /tmp is permitted")
    require(prefix.name.startswith(("darling-p003", "p003-")), "isolated prefix basename must start with darling-p003 or p003-")
    require(prefix.resolve() == prefix, "prefix or its parent is a symlink")
    return prefix


def outside_output(output, prefix):
    output = Path(output).absolute()
    # The lexical path alone is insufficient: an outside symlink (including an
    # ancestor directory) can redirect a marker or manifest into the prefix.
    # Keep the caller's path for ordinary outputs, but check both identities.
    prefix = Path(prefix).absolute()
    resolved_output = output.resolve(strict=False)
    require(not output.is_relative_to(prefix)
            and not resolved_output.is_relative_to(prefix)
            and not resolved_output.is_relative_to(prefix.resolve(strict=False)),
            "ownership/evidence output must be outside install prefix")
    return output


def mark(prefix, output):
    prefix = checked_prefix(prefix)
    output = outside_output(output, prefix)
    require(not prefix.exists() or (prefix.is_dir() and not any(prefix.iterdir())), "initial installation prefix is not empty")
    prefix.mkdir(parents=True, exist_ok=True)
    identity = prefix.stat()
    marker = {"schema_version": 1, "phase": "P003", "prefix": str(prefix),
              "device": identity.st_dev, "inode": identity.st_ino, "nonce": secrets.token_hex(32)}
    (prefix / CONTROL_FILE).write_text(json.dumps(marker, sort_keys=True) + "\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(marker, sort_keys=True) + "\n")
    return {"status": "PASSED", "prefix": str(prefix), "initial_prefix_empty": True}


def remove_owned_tree(prefix, device, inode):
    """Quarantine an inode-checked tree before any recursive deletion.

    Even after checking prefix/contents, a rename of its parent followed by a
    symlink replacement could redirect path-based deletion to another tree. A
    same-parent basename swap between an lstat and rmtree is dangerous too.
    Move the selected entry into a private fd-pinned staging directory *first*,
    and never delete it unless its identity matches the ownership marker.
    """
    require(os.name == "posix" and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW")
            and os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd
            and os.mkdir in os.supports_dir_fd and os.rename in os.supports_dir_fd
            and os.rmdir in os.supports_dir_fd and hasattr(os, "fchmod")
            and shutil.rmtree.avoids_symlink_attacks,
            "safe fd-relative tree removal is unsupported on this platform")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    parent_fd = os.open("/", flags)
    try:
        # Open each ancestor relative to the preceding open fd. O_NOFOLLOW on
        # the final component alone would not protect intermediate symlinks.
        for component in prefix.parent.parts[1:]:
            next_fd = os.open(component, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd

        target = os.stat(prefix.name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISDIR(target.st_mode) and target.st_dev == device and target.st_ino == inode,
                "installation prefix changed before deletion")

        stage_name = ".p003-uninstall-quarantine-" + secrets.token_hex(16)
        stage_fd = None
        stage_created = False
        moved = False
        try:
            # The staging name is unpredictable, and its 0700 permissions
            # exclude other users from replacing the entry before rmtree.
            os.mkdir(stage_name, mode=0o700, dir_fd=parent_fd)
            stage_created = True
            stage_fd = os.open(stage_name, flags, dir_fd=parent_fd)
            os.fchmod(stage_fd, 0o700)
            stage_stat = os.fstat(stage_fd)
            require(stat.S_ISDIR(stage_stat.st_mode) and stage_stat.st_uid == os.geteuid()
                    and stat.S_IMODE(stage_stat.st_mode) == 0o700,
                    "private uninstall quarantine lacks required ownership/permissions")

            # Atomic rename moves one exact directory entry. Recheck *after*
            # the move: a concurrent swap may have inserted an unrelated tree.
            os.rename(prefix.name, "owned", src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
            moved = True
            staged = os.stat("owned", dir_fd=stage_fd, follow_symlinks=False)
            require(stat.S_ISDIR(staged.st_mode) and staged.st_dev == device and staged.st_ino == inode,
                    "prefix changed during quarantine; unexpected entry preserved in "
                    + str(prefix.parent / stage_name / "owned"))

            shutil.rmtree("owned", dir_fd=stage_fd)
            moved = False
            try:
                os.stat("owned", dir_fd=stage_fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise VerificationError("uninstall left a staged installation prefix behind")
        finally:
            if stage_fd is not None:
                os.close(stage_fd)
            if stage_created and not moved:
                # An unexpected entry is deliberately *not* removed/overwritten
                # when ownership fails. Leave it quarantined for recovery.
                os.rmdir(stage_name, dir_fd=parent_fd)
    finally:
        os.close(parent_fd)


def remove(prefix, marker_path, manifest_path):
    prefix = checked_prefix(prefix)
    require(prefix.is_dir() and not prefix.is_symlink(), "installation prefix missing or redirected")
    marker_path = outside_output(marker_path, prefix)
    manifest_path = outside_output(manifest_path, prefix)
    marker = json.loads(marker_path.read_text())
    control = prefix / CONTROL_FILE
    require(control.is_file() and not control.is_symlink(), "missing real ownership marker")
    require(marker == json.loads(control.read_text()), "ownership marker mismatch")
    require(marker.get("schema_version") == 1 and marker.get("phase") == "P003" and marker.get("prefix") == str(prefix), "invalid ownership marker")
    require(isinstance(marker.get("nonce"), str) and len(marker["nonce"]) == 64, "invalid ownership nonce")
    identity = prefix.stat()
    require(marker["device"] == identity.st_dev and marker["inode"] == identity.st_ino, "installation prefix replaced since ownership was recorded")
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema_version") == 1 and manifest.get("gate") == "installed-framework-provenance" and manifest.get("status") == "PASSED", "a passed installation provenance manifest is required")
    require(manifest.get("configuration", {}).get("install_prefix") == str(prefix), "manifest belongs to another installation prefix")
    current = snapshot(prefix)
    require(current == manifest.get("entries") and bool(current), "installation contents changed since manifest; refusing to delete")
    # The prefix was created/marked by this campaign; delete through the pinned
    # parent directory only after an inode/device check against the owner marker.
    remove_owned_tree(prefix, identity.st_dev, identity.st_ino)
    require(not prefix.exists() and not prefix.is_symlink(), "uninstall left the installation prefix behind")
    return {"schema_version": 1, "phase": "P003", "gate": "isolated-uninstall", "status": "PASSED",
            "prefix": str(prefix), "prefix_absent": True, "removed_entries": len(current),
            "manifest_source_commit": manifest.get("source_commit"), "errors": []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("mark", "remove"):
        child = subparsers.add_parser(command)
        child.add_argument("--prefix", type=Path, required=True)
        child.add_argument("--output", type=Path, required=True)
        if command == "remove":
            child.add_argument("--marker", type=Path, required=True)
            child.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        outside_output(args.output, checked_prefix(args.prefix))
        result = mark(args.prefix, args.output) if args.command == "mark" else remove(args.prefix, args.marker, args.manifest)
    except (OSError, ValueError, KeyError) as error:
        result = {"schema_version": 1, "phase": "P003", "gate": "isolated-" + args.command, "status": "FAILED", "errors": [str(error)]}
    if args.command == "remove":
        # A bad --output must not cause us to create files in an unowned prefix.
        try:
            output = outside_output(args.output, args.prefix.absolute())
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        except (OSError, ValueError) as error:
            print(f"cannot write uninstall evidence: {error}", file=sys.stderr)
            return 1
    print(f"P003 isolated install {args.command}: {result['status']}")
    for error in result.get("errors", []):
        print(error, file=sys.stderr)
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
