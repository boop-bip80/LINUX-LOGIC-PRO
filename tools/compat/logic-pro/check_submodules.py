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
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import inventory


SHA = re.compile(r"^[0-9a-f]{40}$")
SCHEMA = 1


class LockFailure(ValueError):
    pass


def safe_path(path: str, *, allow_root: bool = False) -> str:
    if allow_root and path == ".":
        return path
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise LockFailure("invalid submodule path")
    parts = PurePosixPath(path).parts
    if path.startswith("/") or any(p in ("", ".", "..") for p in parts) or str(PurePosixPath(path)) != path:
        raise LockFailure(f"unsafe or noncanonical path: {path!r}")
    return path


def safe_url(url: str, *, allow_local: bool) -> str:
    if not isinstance(url, str) or not url or any(x in url for x in "\n\r\x00"):
        raise LockFailure("missing or invalid remote URL")
    parsed = urlsplit(url)
    if parsed.scheme == "https" and parsed.hostname == "github.com" and not (parsed.username or parsed.password or parsed.query or parsed.fragment):
        if len(parsed.path.strip("/").split("/")) != 2:
            raise LockFailure("GitHub URL must identify a repository")
        return url.rstrip("/")
    if allow_local and parsed.scheme == "file" and not (parsed.netloc or parsed.query or parsed.fragment):
        return url.rstrip("/")
    raise LockFailure("submodule origins must be public HTTPS GitHub URLs")


def canonical_url(url: str) -> str:
    """Compare Git's harmless optional .git suffix without hiding URL changes."""
    return url.rstrip("/").removesuffix(".git")


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
    try:
        blob = inventory.git(repo, "show", "HEAD:.gitmodules")
    except inventory.InventoryError:
        return {}
    config = inventory.git(repo, "config", "--null", "--file", "-",
                           "--get-regexp", r"^submodule\..*\.(path|url)$", input_bytes=blob)
    fields: dict[str, dict[str, str]] = defaultdict(dict)
    for record in config.split(b"\x00"):
        if not record:
            continue
        key, value = record.split(b"\n", 1)
        name, field = key.decode("utf-8", "surrogateescape").removeprefix("submodule.").rsplit(".", 1)
        if field in fields[name]:
            raise LockFailure("duplicate .gitmodules key")
        fields[name][field] = value.decode("utf-8", "surrogateescape")
    result: dict[str, str] = {}
    for record in fields.values():
        if set(record) != {"path", "url"}:
            raise LockFailure("incomplete .gitmodules entry")
        path = safe_path(record["path"])
        if path in result:
            raise LockFailure(f"duplicate .gitmodules path: {path}")
        result[path] = record["url"]
    return result


def validate_lock(lock: dict, allow_local: bool) -> dict[str, dict]:
    if lock.get("schema_version") != SCHEMA or lock.get("phase") != "P002":
        raise LockFailure("unsupported P002 lock schema")
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
        if not isinstance(url, str) or not url:
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
    return expected


def verify(repo: Path, lock: dict, *, allow_local: bool = False) -> dict:
    root = repo.resolve(strict=True)
    expected = validate_lock(lock, allow_local)
    root_origin = inventory.git(root, "remote", "get-url", "origin").decode().strip()
    if canonical_url(safe_url(root_origin, allow_local=allow_local)) != canonical_url(safe_url(lock["root_origin"], allow_local=allow_local)):
        raise LockFailure("root origin differs from lock")
    parent_to_children: dict[str, list[dict]] = defaultdict(list)
    for entry in expected.values():
        parent_to_children[entry["parent_path"]].append(entry)
    pending = [(".", root, root_origin)]
    visited: set[str] = set()
    verified: list[dict] = []
    while pending:
        parent_path, parent_repo, parent_origin = pending.pop(0)
        if parent_path in visited:
            raise LockFailure(f"duplicate recursive ownership: {parent_path}")
        visited.add(parent_path)
        real_top = Path(inventory.git(parent_repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        if real_top != parent_repo:
            raise LockFailure(f"uninitialized or incorrect Git repository: {parent_path}")
        dirty = inventory.git(parent_repo, "status", "--porcelain=v1", "--untracked-files=no", "--ignore-submodules=none")
        if dirty:
            raise LockFailure(f"index or tracked checkout is dirty: {parent_path}")
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
            child = (root / path).resolve()
            if not child.is_relative_to(root) or not child.is_dir():
                raise LockFailure(f"missing or escaping checkout: {path}")
            child_top = Path(inventory.git(child, "rev-parse", "--show-toplevel").decode().strip()).resolve()
            if child_top != child:
                raise LockFailure(f"uninitialized checkout: {path}")
            head = inventory.git(child, "rev-parse", "HEAD").decode().strip()
            tree = inventory.git(child, "rev-parse", "HEAD^{tree}").decode().strip()
            if head != entry["commit"] or tree != entry["tree"]:
                raise LockFailure(f"checkout commit/tree mismatch: {path}")
            child_origin = inventory.git(child, "remote", "get-url", "origin").decode().strip()
            if canonical_url(safe_url(child_origin, allow_local=allow_local)) != canonical_url(entry["resolved_url"]):
                raise LockFailure(f"checkout origin differs from lock: {path}")
            verified.append({"path": path, "commit": head, "tree": tree, "resolved_url": entry["resolved_url"]})
            pending.append((path, child, child_origin))
    if len(verified) != len(expected) or len(visited) != len(expected) + 1:
        raise LockFailure("recursive traversal did not visit every pinned source")
    return {"schema_version": 1, "phase": "P002", "result": "PASS",
            "root_commit": inventory.git(root, "rev-parse", "HEAD").decode().strip(),
            "verified_gitlinks": len(verified), "verified_repositories": len(visited),
            "direct_gitlinks": len(parent_to_children["."]), "uninitialized": 0,
            "mismatched": 0, "conflicted": 0, "dirty_repositories": 0,
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
        result = {"schema_version": 1, "phase": "P002", "result": "FAIL", "error": str(error)}
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(json.dumps({key: value for key, value in result.items() if key != "submodules"}, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
