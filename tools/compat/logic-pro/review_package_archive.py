#!/usr/bin/env python3
"""Independently verify and safely unpack a P003 installed runtime archive.

No production package verifier is imported. Every archived entry is checked
against the exact installation manifest before extraction. Directory-relative
operations never follow archived symlinks, including absolute Darwin guest
links. The independent runtime job establishes absence of source/build trees;
debug strings embedded in binaries are not treated as runtime dependencies.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile

SCHEMA = "darling.p003.package-archive-review.v1"
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stream_digest(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def file_digest(path):
    require(path.is_file() and not path.is_symlink(), f"Expected regular input: {path}")
    with path.open("rb") as stream:
        return stream_digest(stream)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def relative_path(raw, archive=False):
    require(isinstance(raw, str) and "\0" not in raw, "Invalid entry path")
    name = raw[2:] if archive and raw.startswith("./") else raw
    if archive:
        name = name.rstrip("/")
    path = PurePosixPath(name)
    require(name not in ("", ".") and not path.is_absolute()
            and ".." not in path.parts and str(path) == name,
            f"Unsafe or noncanonical entry path: {raw!r}")
    return name


def read_manifest(path, commit, destination):
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "An exact source commit is required")
    require(path.is_file() and not path.is_symlink(), "Manifest must be a regular file")
    report = json.loads(path.read_text(), object_pairs_hook=unique_object)
    require(report.get("status") == "PASSED" and report.get("errors") == []
            and report.get("source_commit") == commit,
            "Installation manifest failed or belongs to another source commit")
    require(report.get("configuration", {}).get("install_prefix") == str(destination),
            "Destination differs from the verified installation prefix")
    entries = {}
    for item in report["entries"]:
        name = relative_path(item["path"])
        require(name not in entries, f"Duplicate manifest path: {name}")
        require(item["kind"] in ("file", "directory", "symlink"), f"Unsupported manifest kind: {name}")
        require(type(item["mode"]) is int and 0 <= item["mode"] <= 0o7777,
                f"Invalid manifest permissions: {name}")
        if item["kind"] == "file":
            require(type(item["size"]) is int and item["size"] >= 0
                    and re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is not None,
                    f"Invalid manifest file identity: {name}")
        if item["kind"] == "symlink":
            require(isinstance(item["target"], str) and item["target"] and "\0" not in item["target"]
                    and item["mode"] == 0o777, f"Invalid Linux symlink metadata: {name}")
        entries[name] = item
    require(bool(entries), "Empty installations cannot qualify")
    for name in entries:
        for parent in PurePosixPath(name).parents:
            if parent.as_posix() != ".":
                require(entries.get(parent.as_posix(), {}).get("kind") == "directory",
                        f"Manifest path traverses a missing directory or symlink: {name}")
    return entries


def member_metadata(member, expected):
    name = relative_path(member.name, archive=True)
    require(name in expected, f"Unexpected archive path: {name}")
    item = expected[name]
    require(member.uid == 0 and member.gid == 0, f"Noncanonical archive ownership: {name}")
    require(member.mode == item["mode"], f"Archive permissions differ: {name}")
    require(isinstance(member.mtime, (int, float)) and math.isfinite(member.mtime),
            f"Invalid archive timestamp: {name}")
    result = {"mtime": member.mtime, "mode": member.mode}
    if member.isdir():
        require(item["kind"] == "directory" and member.size == 0, f"Archive directory differs: {name}")
        result["kind"] = "directory"
    elif member.issym():
        require(item["kind"] == "symlink" and member.size == 0
                and member.linkname == item["target"], f"Archive symlink differs: {name}")
        result.update(kind="symlink", target=member.linkname)
    elif member.islnk():
        require(item["kind"] == "file" and member.size == 0, f"Archive hardlink differs: {name}")
        result.update(kind="hardlink", target=relative_path(member.linkname, archive=True))
    elif member.type in (tarfile.REGTYPE, tarfile.AREGTYPE):
        require(item["kind"] == "file" and member.size == item["size"], f"Archive file differs: {name}")
        result.update(kind="file", size=member.size)
    else:
        raise ValueError(f"Unsupported special archive entry: {name}")
    return name, result


def validate_archive(archive, expected):
    layout, content, root_metadata = {}, {}, None
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            if member.name in (".", "./"):
                require(root_metadata is None and member.isdir() and member.size == 0
                        and member.uid == 0 and member.gid == 0 and member.mode == 0o755
                        and isinstance(member.mtime, (int, float)) and math.isfinite(member.mtime),
                        "Invalid or repeated archive root")
                root_metadata = {"mtime": member.mtime, "mode": member.mode}
                continue
            name, metadata = member_metadata(member, expected)
            require(name not in layout, f"Repeated archive entry: {name}")
            layout[name] = metadata
            if metadata["kind"] == "file":
                payload = stream.extractfile(member)
                require(payload is not None, f"Missing archive payload: {name}")
                content[name] = stream_digest(payload)
                require(content[name] == expected[name]["sha256"], f"Archive file bytes differ: {name}")
    require(root_metadata is not None, "Missing archive root directory")
    require(set(layout) == set(expected), "Archive path set differs from the installation manifest")
    for name, metadata in layout.items():
        if metadata["kind"] != "hardlink":
            continue
        target, walked = metadata["target"], {name}
        while target in layout and layout[target]["kind"] == "hardlink":
            require(target not in walked, f"Cyclic archive hardlink: {name}")
            walked.add(target)
            target = layout[target]["target"]
        require(target in content, f"Hardlink target is not an archived regular file: {name}")
        require(expected[name]["sha256"] == content[target]
                and expected[name]["size"] == expected[target]["size"]
                and expected[name]["mode"] == expected[target]["mode"],
                f"Hardlink content or permissions differ: {name}")
        metadata["resolved_target"] = target
    return layout, root_metadata


@contextmanager
def parent_directory(root_fd, relative):
    parts = PurePosixPath(relative).parts
    descriptor = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        yield descriptor, parts[-1]
    finally:
        os.close(descriptor)


def root_ownership(descriptor):
    # The public CLI requires root in its fresh qualification container. Keeping
    # this conditional also permits focused extraction tests as an ordinary user.
    if os.geteuid() == 0:
        os.fchown(descriptor, 0, 0)


def verify_installed(root_fd, expected):
    seen = set()

    def visit(directory_fd, prefix=""):
        for basename in os.listdir(directory_fd):
            name = prefix + basename
            require(name in expected and name not in seen, f"Unexpected extracted path: {name}")
            seen.add(name)
            item = expected[name]
            metadata = os.stat(basename, dir_fd=directory_fd, follow_symlinks=False)
            require(stat.S_IMODE(metadata.st_mode) == item["mode"], f"Extracted permissions differ: {name}")
            if item["kind"] == "symlink":
                require(stat.S_ISLNK(metadata.st_mode)
                        and os.readlink(basename, dir_fd=directory_fd) == item["target"],
                        f"Extracted symlink differs: {name}")
            elif item["kind"] == "directory":
                require(stat.S_ISDIR(metadata.st_mode), f"Extracted directory differs: {name}")
                child = os.open(basename, DIRECTORY_FLAGS, dir_fd=directory_fd)
                try:
                    visit(child, name + "/")
                finally:
                    os.close(child)
            else:
                require(stat.S_ISREG(metadata.st_mode) and metadata.st_size == item["size"],
                        f"Extracted file differs: {name}")
                descriptor = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd)
                with os.fdopen(descriptor, "rb") as stream:
                    require(stream_digest(stream) == item["sha256"], f"Extracted file bytes differ: {name}")
    visit(root_fd)
    require(seen == set(expected), "Extraction omitted required installation paths")


def extract_archive(archive, expected, layout, root_metadata, destination):
    require(destination.is_absolute() and destination.name not in ("", ".", ".."),
            "An absolute isolated destination is required")
    # Open every ancestor without following symlinks, then create one new leaf.
    ancestor = os.open("/", DIRECTORY_FLAGS)
    try:
        for part in destination.parts[1:-1]:
            require(part not in (".", ".."), "Invalid extraction destination")
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=ancestor)
            os.close(ancestor)
            ancestor = child
        os.mkdir(destination.name, 0o700, dir_fd=ancestor)
        root_fd = os.open(destination.name, DIRECTORY_FLAGS, dir_fd=ancestor)
    finally:
        os.close(ancestor)
    try:
        root_ownership(root_fd)
        directories = sorted((name for name, item in expected.items() if item["kind"] == "directory"),
                             key=lambda name: (len(PurePosixPath(name).parts), name))
        for name in directories:
            with parent_directory(root_fd, name) as (parent_fd, basename):
                os.mkdir(basename, 0o700, dir_fd=parent_fd)
        seen, saw_root = set(), False
        with tarfile.open(archive, "r|gz") as stream:
            for member in stream:
                if member.name in (".", "./"):
                    require(not saw_root and member.isdir() and member.size == 0
                            and member.uid == 0 and member.gid == 0
                            and {"mtime": member.mtime, "mode": member.mode} == root_metadata,
                            "Archive root changed between verification and extraction")
                    saw_root = True
                    continue
                name, metadata = member_metadata(member, expected)
                require(name not in seen and name in layout
                        and metadata == {key: value for key, value in layout[name].items() if key != "resolved_target"},
                        f"Archive changed between verification and extraction: {name}")
                seen.add(name)
                with parent_directory(root_fd, name) as (parent_fd, basename):
                    if metadata["kind"] == "file":
                        descriptor = os.open(basename, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                                             | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent_fd)
                        payload = stream.extractfile(member)
                        require(payload is not None, f"Missing extraction payload: {name}")
                        digest = hashlib.sha256()
                        with os.fdopen(descriptor, "wb") as target:
                            for block in iter(lambda: payload.read(1024 * 1024), b""):
                                target.write(block)
                                digest.update(block)
                            target.flush()
                            require(digest.hexdigest() == expected[name]["sha256"], f"Extraction bytes changed: {name}")
                            root_ownership(target.fileno())
                            os.fchmod(target.fileno(), expected[name]["mode"])
                            os.utime(target.fileno(), (metadata["mtime"], metadata["mtime"]))
                    elif metadata["kind"] == "symlink":
                        os.symlink(metadata["target"], basename, dir_fd=parent_fd)
                        if os.geteuid() == 0:
                            os.chown(basename, 0, 0, dir_fd=parent_fd, follow_symlinks=False)
                        os.utime(basename, (metadata["mtime"], metadata["mtime"]),
                                 dir_fd=parent_fd, follow_symlinks=False)
        require(saw_root and seen == set(expected), "Archive lost entries between verification and extraction")
        for name, metadata in layout.items():
            if metadata["kind"] == "hardlink":
                with parent_directory(root_fd, metadata["resolved_target"]) as (source_fd, source_name):
                    with parent_directory(root_fd, name) as (parent_fd, basename):
                        os.link(source_name, basename, src_dir_fd=source_fd,
                                dst_dir_fd=parent_fd, follow_symlinks=False)
        for name in reversed(directories):
            with parent_directory(root_fd, name) as (parent_fd, basename):
                descriptor = os.open(basename, DIRECTORY_FLAGS, dir_fd=parent_fd)
                try:
                    root_ownership(descriptor)
                    os.fchmod(descriptor, expected[name]["mode"])
                    os.utime(descriptor, (layout[name]["mtime"], layout[name]["mtime"]))
                finally:
                    os.close(descriptor)
        os.fchmod(root_fd, root_metadata["mode"])
        os.utime(root_fd, (root_metadata["mtime"], root_metadata["mtime"]))
        verify_installed(root_fd, expected)
    finally:
        os.close(root_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("archive", "manifest", "destination", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    report = {"schema": SCHEMA, "status": "FAIL", "source_commit": args.commit,
              "archive_sha256": None, "archive_bytes": None, "manifest_sha256": None,
              "entry_count": 0, "destination": str(args.destination),
              "driver_sha256": file_digest(Path(__file__).resolve()), "errors": []}
    output_allowed = False
    try:
        output = args.output.resolve()
        require(output not in (args.archive.resolve(), args.manifest.resolve(), Path(__file__).resolve())
                and not output.is_relative_to(args.destination.resolve()),
                "Review output must be separate from inputs and installed package")
        output_allowed = True
        require(os.geteuid() == 0, "Archive replay requires root inside the disposable qualification container")
        require(not os.path.lexists(args.destination), "Extraction destination must not already exist")
        report["manifest_sha256"] = file_digest(args.manifest)
        expected = read_manifest(args.manifest, args.commit, args.destination)
        report["archive_sha256"] = file_digest(args.archive)
        report["archive_bytes"] = args.archive.stat().st_size
        layout, root_metadata = validate_archive(args.archive, expected)
        extract_archive(args.archive, expected, layout, root_metadata, args.destination)
        require(file_digest(args.archive) == report["archive_sha256"]
                and file_digest(args.manifest) == report["manifest_sha256"],
                "Archive or installation manifest changed during replay")
        report["entry_count"] = len(expected)
        report["counts"] = {label: sum(item["kind"] == kind for item in expected.values())
                            for label, kind in (("files", "file"), ("directories", "directory"),
                                                ("symlinks", "symlink"))}
        report["counts"]["hardlinks"] = sum(item["kind"] == "hardlink" for item in layout.values())
        report["installed_readback"] = "PASS"
        report["status"] = "PASS"
    except (OSError, ValueError, KeyError, TypeError, OverflowError, EOFError, tarfile.TarError) as error:
        report["errors"].append(str(error))
    if output_allowed:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
