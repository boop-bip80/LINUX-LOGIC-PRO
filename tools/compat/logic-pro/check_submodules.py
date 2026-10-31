#!/usr/bin/env python3
"""Verify the P002 lock against an ordinary *fully recursive* Git clone.

This is intentionally read-only: it never initializes, fetches, repairs, or
silently ignores a child. A missing child, changed gitlink, URL, origin, dirty
index, or inconsistent lock is a hard failure. P001's separate inventory tool
is used only for read-only Git plumbing and Git-compatible URL resolution.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import inventory
import lfs_manifest


SHA = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = 2


class LockFailure(ValueError):
    pass


def safe_path(path: str, *, allow_root: bool = False) -> str:
    if allow_root and path == ".":
        return path
    if (not isinstance(path, str) or not path or path == "." or "\\" in path
            or any(ord(char) < 32 or ord(char) == 127 for char in path)):
        raise LockFailure("invalid submodule path")
    parts = PurePosixPath(path).parts
    if path.startswith("/") or any(p in ("", ".", "..", ".git") for p in parts) or str(PurePosixPath(path)) != path:
        raise LockFailure(f"unsafe or noncanonical path: {path!r}")
    return path


def safe_url(url: str, *, allow_local: bool) -> str:
    if not isinstance(url, str) or not url or any(x in url for x in "\n\r\x00"):
        raise LockFailure("missing or invalid remote URL")
    parsed = urlsplit(url)
    if parsed.scheme == "https" and parsed.hostname == "github.com" and not (parsed.username or parsed.password or parsed.query or parsed.fragment):
        if (parsed.port not in (None, 443)
                or re.fullmatch(r"/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/?", parsed.path) is None
                or parsed.path.strip("/").split("/")[-1] in (".", "..", ".git")):
            raise LockFailure("GitHub URL must identify a repository")
        return url.rstrip("/")
    if allow_local and parsed.scheme == "file" and not (parsed.netloc or parsed.query or parsed.fragment):
        return url.rstrip("/")
    raise LockFailure("submodule origins must be public HTTPS GitHub URLs")


def canonical_url(url: str) -> str:
    """Compare Git's harmless optional .git suffix without hiding URL changes."""
    return url.rstrip("/").removesuffix(".git")


def checked_origin(repo: Path, *, allow_local: bool) -> str:
    """Check the configured origin AND its effective URL; rewrites cannot hide it."""
    configured = inventory.git(repo, "config", "--no-includes", "--local", "--null",
                               "--get-all", "remote.origin.url").split(b"\0")
    urls = [item.decode("utf-8", "surrogateescape") for item in configured if item]
    if len(urls) != 1:
        raise LockFailure("each source must have exactly one configured origin URL")
    raw = safe_url(urls[0], allow_local=allow_local)
    effective = safe_url(inventory.git(repo, "remote", "get-url", "origin").decode().strip(),
                         allow_local=allow_local)
    if canonical_url(raw) != canonical_url(effective):
        raise LockFailure("configured origin is masked by a Git URL rewrite")
    return raw


def gitlinks(repo: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for record in inventory.git(repo, "ls-tree", "-rz", "--full-tree", "HEAD").split(b"\x00"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, kind, sha = header.decode("ascii").split(" ")
        if mode == "160000":
            if kind != "commit" or not SHA.fullmatch(sha):
                raise LockFailure("invalid committed gitlink")
            path = name.decode("utf-8", "surrogateescape")
            safe_path(path)
            found[path] = sha
    return found


def indexed_gitlinks(repo: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    for record in inventory.git(repo, "ls-files", "--stage", "-z").split(b"\x00"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, sha, stage = header.decode("ascii").split(" ")
        if mode == "160000":
            path = name.decode("utf-8", "surrogateescape")
            if stage != "0" or path in found:
                raise LockFailure(f"conflicted gitlink index: {path}")
            found[path] = sha
    return found


def committed_modules(repo: Path) -> dict[str, str]:
    """Parse committed .gitmodules through Git, never trusting a worktree edit."""
    metadata = [entry for entry in inventory.tree_entries(repo, "HEAD") if entry["path"] == ".gitmodules"]
    if not metadata:
        return {}
    if len(metadata) != 1 or metadata[0]["type"] != "blob" or metadata[0]["mode"] not in ("100644", "100755"):
        raise LockFailure("committed .gitmodules must be a regular Git blob")
    blob = inventory.read_blobs(repo, [metadata[0]["object"]])[metadata[0]["object"]]
    config = inventory.git(repo, "config", "--no-includes", "--null", "--file", "-",
                           "--list", input_bytes=blob)
    fields: dict[str, dict[str, str]] = defaultdict(dict)
    for record in config.split(b"\x00"):
        if not record:
            continue
        key, _, value = record.partition(b"\n")
        key_text = key.decode("utf-8", "surrogateescape")
        if not key_text.startswith("submodule.") or "." not in key_text[len("submodule."):]:
            raise LockFailure("unsupported non-submodule .gitmodules configuration")
        name, field = key_text.removeprefix("submodule.").rsplit(".", 1)
        if field in fields[name]:
            raise LockFailure("duplicate .gitmodules key")
        fields[name][field] = value.decode("utf-8", "surrogateescape")
    result: dict[str, str] = {}
    for record in fields.values():
        if not {"path", "url"}.issubset(record):
            raise LockFailure("incomplete .gitmodules entry")
        if set(record) - {"path", "url", "branch", "shallow", "update", "ignore", "fetchrecursesubmodules"}:
            raise LockFailure("unsupported submodule acquisition configuration")
        if record.get("update", "checkout") != "checkout" or record.get("ignore", "none") != "none":
            raise LockFailure("submodules must use pinned checkout updates without ignored state")
        path = safe_path(record["path"])
        if path in result:
            raise LockFailure(f"duplicate .gitmodules path: {path}")
        result[path] = record["url"]
    return result


def assert_no_checkout_overrides(repo: Path) -> None:
    """P002 cannot borrow P001's private attributes or another checkout's objects."""
    for name in ("info/attributes", "objects/info/alternates", "objects/info/http-alternates"):
        path = Path(inventory.git(repo, "rev-parse", "--git-path", name).decode().strip())
        if not path.is_absolute():
            path = repo / path
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size:
            raise LockFailure("local checkout attributes or shared object-store overrides are not permitted")


def committed_attributes(repo: Path, paths: list[str]) -> dict[str, dict[str, str]]:
    """Read indexed attributes, never a dirty worktree/global file or a filter."""
    if not paths:
        return {}
    environment = inventory.git_environment()
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    command = ["git", "--no-optional-locks", "--literal-pathspecs",
               "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null",
               "-c", "core.attributesFile=/dev/null", "-C", str(repo),
               "check-attr", "--cached", "-z", "--stdin",
               "text", "eol", "filter", "ident", "working-tree-encoding"]
    result = subprocess.run(command, env=environment,
                            input=b"\0".join(p.encode("utf-8", "surrogateescape") for p in paths) + b"\0",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, check=False)
    if result.returncode:
        raise LockFailure("could not inspect committed checkout attributes")
    fields = result.stdout.split(b"\0")
    if fields[-1:] != [b""] or (len(fields) - 1) % 3:
        raise LockFailure("invalid committed attribute response")
    attributes: dict[str, dict[str, str]] = defaultdict(dict)
    for pos in range(0, len(fields) - 1, 3):
        path, name, value = (item.decode("utf-8", "surrogateescape") for item in fields[pos:pos + 3])
        if path not in paths or name in attributes[path]:
            raise LockFailure("unexpected or duplicate committed attribute response")
        attributes[path][name] = value
    if set(attributes) != set(paths):
        raise LockFailure("incomplete committed attribute response")
    return attributes


def read_regular_checkout(repo: Path, relative: str, mode: str) -> bytes:
    """Read exact bytes with no-follow descriptors and no Git clean filters."""
    safe_path(relative)
    parent_fd = os.open(repo, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            child_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child_fd
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or ("100755" if before.st_mode & stat.S_IXUSR else "100644") != mode:
                raise LockFailure("checkout type or executable bit differs from committed source")
            data = stream.read()
            after = os.fstat(stream.fileno())
            if (before.st_size, before.st_mode, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mode, after.st_mtime_ns, after.st_ctime_ns):
                raise LockFailure("source changed during physical verification")
            return data
    finally:
        os.close(parent_fd)


def verify_checkout(repo: Path, entries: list[dict], large_files: list[dict], root: Path) -> dict:
    """Check all index entries and physical blobs, including hidden dirty state.

    The sole non-LFS transform needed by the pinned source is Git's built-in
    LF-to-CRLF checkout for libffi's four Windows project files. Permit that
    exact transform only when the immutable indexed attributes request it;
    arbitrary clean/smudge commands are never invoked and cannot waive edits.
    """
    expected = {(e["path"], e["mode"], e["object"], 0) for e in entries}
    indexed = inventory.index_entries(repo)
    actual = {(e["path"], e["mode"], e["object"], e["stage"]) for e in indexed}
    if actual != expected or len(indexed) != len(entries):
        raise LockFailure("complete Git index differs from committed tree")
    assert_no_checkout_overrides(repo)
    large_paths = {item["repository_path"] for item in large_files}
    ordinary = [entry for entry in entries if entry["path"] not in large_paths]
    changes, physical = inventory.physical_worktree(repo, ordinary)
    by_path = {entry["path"]: entry for entry in ordinary}
    changed_bytes = [item["path"] for item in changes if item.get("reason") == "physical bytes differ from committed blob"
                     and by_path[item["path"]]["mode"] in ("100644", "100755")]
    attributes = committed_attributes(repo, changed_bytes)
    converted = []
    for path in changed_bytes:
        attrs = attributes[path]
        if (attrs.get("text") != "set" or attrs.get("eol") != "crlf"
                or any(attrs.get(key) not in ("unset", "unspecified") for key in ("filter", "ident", "working-tree-encoding"))):
            continue
        entry = by_path[path]
        blob = inventory.read_blobs(repo, [entry["object"]])[entry["object"]]
        if b"\r" in blob or b"\0" in blob or b"\n" not in blob:
            continue
        if read_regular_checkout(repo, path, entry["mode"]) == blob.replace(b"\n", b"\r\n"):
            converted.append(path)
    remaining = [item for item in changes if item["path"] not in converted]
    if remaining:
        raise LockFailure(f"physical checkout is dirty: {remaining[0]['path']}")
    if inventory.git(repo, "ls-files", "--others", "-z"):
        raise LockFailure("untracked files, including ignored inputs, are not permitted in a clean source checkout")
    for record in large_files:
        lfs_manifest.verify_payload(root, record)
    return {"verified_blobs": physical["verified_blobs"] + len(converted) + len(large_files),
            "standard_crlf_paths": converted, "verified_lfs_payloads": len(large_files)}


def validate_lock(lock: dict, allow_local: bool) -> dict[str, dict]:
    if (not isinstance(lock, dict) or type(lock.get("schema_version")) is not int
            or lock.get("schema_version") != SCHEMA or lock.get("phase") != "P002"):
        raise LockFailure("unsupported P002 lock schema")
    if not isinstance(lock.get("root_gitmodules_blob_sha1"), str) or not SHA.fullmatch(lock["root_gitmodules_blob_sha1"]):
        raise LockFailure("lock must pin the complete root .gitmodules blob")
    safe_url(lock.get("root_origin"), allow_local=allow_local)
    if any(type(lock.get(field)) is not int for field in ("expected_recursive_gitlinks", "expected_direct_gitlinks")):
        raise LockFailure("lock counts must be integers")
    entries = lock.get("submodules")
    if not isinstance(entries, list) or not entries:
        raise LockFailure("empty P002 submodule lock")
    expected: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise LockFailure("invalid lock record")
        path = safe_path(entry.get("path"))
        parent = safe_path(entry.get("parent_path"), allow_root=True)
        if parent != "." and (parent not in expected or not path.startswith(parent + "/")):
            raise LockFailure(f"missing or out-of-order parent for {path}")
        if path in expected:
            raise LockFailure(f"duplicate lock path: {path}")
        for field in ("commit", "tree"):
            if not isinstance(entry.get(field), str) or not SHA.fullmatch(entry[field]):
                raise LockFailure(f"missing exact {field} for {path}")
        url = entry.get("declared_url")
        if (not isinstance(url, str) or not url or "\\" in url or "?" in url or "#" in url
                or any(ord(char) <= 32 or ord(char) == 127 for char in url)):
            raise LockFailure(f"missing declared URL for {path}")
        if not url.startswith(("../", "./")):
            safe_url(url, allow_local=allow_local)
        safe_url(entry.get("resolved_url"), allow_local=allow_local)
        if parent == "." and url.startswith(("../", "./")) and not allow_local:
            raise LockFailure("fork-relative root URLs are prohibited in P002")
        expected[path] = entry
    if len(expected) != lock.get("expected_recursive_gitlinks"):
        raise LockFailure("lock count disagrees with manifest")
    direct = sum(x["parent_path"] == "." for x in entries)
    if direct != lock.get("expected_direct_gitlinks"):
        raise LockFailure("root count disagrees with manifest")
    lfs_manifest.validate_manifest(lock, entries)
    return expected


def verify(repo: Path, lock: dict, *, allow_local: bool = False) -> dict:
    root = repo.resolve(strict=True)
    expected = validate_lock(lock, allow_local)
    root_origin = checked_origin(root, allow_local=allow_local)
    if canonical_url(safe_url(root_origin, allow_local=allow_local)) != canonical_url(safe_url(lock["root_origin"], allow_local=allow_local)):
        raise LockFailure("root origin differs from lock")
    parent_to_children: dict[str, list[dict]] = defaultdict(list)
    for entry in expected.values():
        parent_to_children[entry["parent_path"]].append(entry)
    lfs_repositories, lfs_objects = lfs_manifest.validate_manifest(lock, list(expected.values()))
    lfs_owners = {entry["repository"]: entry for entry in lfs_repositories}
    owner_objects: dict[str, list[dict]] = defaultdict(list)
    for record in lfs_objects:
        owner_objects[record["repository"]].append(record)
    pending = [(".", root, root_origin)]
    visited: set[str] = set()
    verified: list[dict] = []
    physical_blobs = 0
    verified_lfs = 0
    converted_paths: list[str] = []
    while pending:
        parent_path, parent_repo, parent_origin = pending.pop(0)
        if parent_path in visited:
            raise LockFailure(f"duplicate recursive ownership: {parent_path}")
        visited.add(parent_path)
        real_top = Path(inventory.git(parent_repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if real_top != parent_repo:
            raise LockFailure(f"uninitialized or incorrect Git repository: {parent_path}")
        entries = inventory.tree_entries(parent_repo, "HEAD")
        for entry in entries:
            safe_path(entry["path"])
        if parent_path == ".":
            metadata = [entry for entry in entries if entry["path"] == ".gitmodules"]
            if len(metadata) != 1 or metadata[0]["object"] != lock["root_gitmodules_blob_sha1"]:
                raise LockFailure("complete root .gitmodules metadata differs from lock")
        discovered_lfs = lfs_manifest.scan_repository(parent_repo, parent_path, parent_origin)
        if discovered_lfs != owner_objects[parent_path]:
            raise LockFailure(f"committed LFS pointer inventory differs from lock: {parent_path}")
        if discovered_lfs and lfs_manifest.repository_metadata(parent_repo, parent_path, parent_origin) != lfs_owners[parent_path]:
            raise LockFailure(f"committed LFS endpoint provenance differs from lock: {parent_path}")
        physical = verify_checkout(parent_repo, entries, discovered_lfs, root)
        physical_blobs += physical["verified_blobs"]
        verified_lfs += physical["verified_lfs_payloads"]
        converted_paths.extend(path if parent_path == "." else parent_path + "/" + path
                               for path in physical["standard_crlf_paths"])
        links, modules = gitlinks(parent_repo), committed_modules(parent_repo)
        if indexed_gitlinks(parent_repo) != links:
            raise LockFailure(f"staged, missing or conflicted gitlink index: {parent_path}")
        children = parent_to_children[parent_path]
        expected_rel = {item["path"] if parent_path == "." else item["path"][len(parent_path) + 1:]: item for item in children}
        if set(links) != set(expected_rel):
            raise LockFailure(f"gitlink paths disagree with lock in {parent_path}: missing={sorted(set(expected_rel)-set(links))[:3]}, extra={sorted(set(links)-set(expected_rel))[:3]}")
        if set(modules) != set(links):
            raise LockFailure(f"committed .gitmodules paths disagree with gitlinks in {parent_path}")
        for relative, entry in sorted(expected_rel.items()):
            path = entry["path"]
            if links[relative] != entry["commit"]:
                raise LockFailure(f"wrong pinned gitlink for {path}")
            if modules[relative] != entry["declared_url"]:
                raise LockFailure(f"wrong committed URL for {path}")
            resolved = inventory.resolve_submodule_url(parent_origin, modules[relative])
            if canonical_url(safe_url(resolved, allow_local=allow_local)) != canonical_url(entry["resolved_url"]):
                raise LockFailure(f"incorrect recursive URL resolution for {path}")
            child = inventory.safe_child(root, path)
            if child is None or not child.is_dir():
                raise LockFailure(f"missing or escaping checkout: {path}")
            child_top = Path(inventory.git(child, "rev-parse", "--show-toplevel").decode().strip()).resolve()
            if child_top != child:
                raise LockFailure(f"uninitialized checkout: {path}")
            head = inventory.git(child, "rev-parse", "HEAD").decode().strip()
            tree = inventory.git(child, "rev-parse", "HEAD^{tree}").decode().strip()
            if head != entry["commit"] or tree != entry["tree"]:
                raise LockFailure(f"checkout commit/tree mismatch: {path}")
            child_origin = checked_origin(child, allow_local=allow_local)
            if canonical_url(safe_url(child_origin, allow_local=allow_local)) != canonical_url(entry["resolved_url"]):
                raise LockFailure(f"checkout origin differs from lock: {path}")
            verified.append({"path": path, "commit": head, "tree": tree, "resolved_url": entry["resolved_url"]})
            pending.append((path, child, child_origin))
    if (len(verified) != len(expected) or len(visited) != len(expected) + 1
            or verified_lfs != lock["expected_lfs_objects"]):
        raise LockFailure("recursive traversal did not visit every pinned source")
    return {"schema_version": SCHEMA, "phase": "P002", "result": "PASS",
            "root_commit": inventory.git(root, "rev-parse", "HEAD").decode().strip(),
            "verified_gitlinks": len(verified), "verified_repositories": len(visited),
            "direct_gitlinks": len(parent_to_children["."]), "uninitialized": 0,
            "mismatched": 0, "conflicted": 0, "dirty_repositories": 0,
            "verified_physical_blobs": physical_blobs,
            "verified_lfs_payloads": verified_lfs,
            "verified_lfs_bytes": sum(record["size"] for record in lfs_objects),
            "standard_crlf_paths": sorted(converted_paths),
            "verification_method": "physical_committed_bytes_modes_symlinks_and_lfs_sha256_without_filters",
            "submodules": verified}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--lock", type=Path, default=Path("docs/compat/logic-pro/submodules.lock.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-local-fixtures", action="store_true", help="Tests only: allow file:// remotes")
    args = parser.parse_args()
    try:
        result = verify(args.repo, json.loads(args.lock.read_text()), allow_local=args.allow_local_fixtures)
    except (ValueError, OSError, KeyError, inventory.InventoryError) as error:
        result = {"schema_version": SCHEMA, "phase": "P002", "result": "FAIL", "error": str(error)}
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(json.dumps({key: value for key, value in result.items() if key != "submodules"}, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
