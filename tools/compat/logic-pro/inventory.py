#!/usr/bin/env python3
"""Inventory a committed source tree without fetching or executing its contents.

This is a P001 source-evidence tool, not a compatibility or P002 clone gate.
Uninitialized submodules are explicitly unknown, not remotely unreachable. The
snapshot is read from Git objects; working-tree files never replace committed
contents. The only dependencies are Python 3.9+ and Git 2.20+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import re
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit


SCHEMA_VERSION = 1
LICENSE_NAME = re.compile(r"^(?:licen[cs]e|copying|copyright|notice)(?:[._-].*)?$", re.I)


class InventoryError(Exception):
    """An inspected source or Git operation could not be represented safely."""


def decode(value: bytes) -> str:
    return value.decode("utf-8", "surrogateescape")


def git_environment() -> dict[str, str]:
    """Ignore ambient repository selectors, replacements and transport settings."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "", "GIT_OPTIONAL_LOCKS": "0",
    })
    return environment


def git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    """Use builtin, read-only Git commands with hooks/fsmonitor disabled."""
    command = [
        "git", "--no-optional-locks", "--literal-pathspecs", "-c", "core.fsmonitor=false",
        "-c", "core.hooksPath=/dev/null", "-c", "core.quotePath=false", "-C", str(repo), *args,
    ]
    result = subprocess.run(command, input=input_bytes, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=120, check=False, env=git_environment())
    if result.returncode:
        # Do not echo stderr: a configured remote could contain credentials.
        raise InventoryError(f"git {args[0]} failed (exit {result.returncode})")
    return result.stdout


def redact_url(url: str) -> str:
    """Do not persist URL passwords, query tokens, or fragments in evidence."""
    if "://" in url:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        if parts.port is not None:
            host += f":{parts.port}"
        # SSH usernames name the transport account; HTTP userinfo may be a token.
        if parts.scheme in ("ssh", "git+ssh") and parts.username == "git":
            host = "git@" + host
        return urlunsplit((parts.scheme, host, parts.path, "", ""))
    url = url.split("?", 1)[0].split("#", 1)[0]
    scp = re.fullmatch(r"(?:(?P<user>[^/@:]+)@)?(?P<host>[^/:]+):(?P<path>.+)", url)
    if scp:
        user = "git@" if scp.group("user") == "git" else ""
        return user + scp.group("host") + ":" + scp.group("path")
    return url


def resolve_submodule_url(remote: str | None, declared: str) -> str | None:
    """Resolve Git's ./ and ../ URLs against the repository, not its parent.

    Git treats https://host/owner/project.git as a directory for this purpose:
    ../dependency.git resolves to https://host/owner/dependency.git.
    """
    if not declared.startswith(("./", "../")):
        return redact_url(declared)
    if not remote:
        return None
    if "://" in remote:
        parts = urlsplit(remote)
        joined = posixpath.normpath(posixpath.join(parts.path, declared))
        return redact_url(urlunsplit((parts.scheme, parts.netloc, joined, "", "")))
    scp = re.fullmatch(r"(?P<host>(?:[^/@:]+@)?[^/:]+):(?P<path>.+)", remote)
    if scp:
        joined = posixpath.normpath(posixpath.join(scp.group("path"), declared))
        return redact_url(scp.group("host") + ":" + joined)
    return posixpath.normpath(posixpath.join(remote, declared))


def tree_entries(repo: Path, revision: str) -> list[dict]:
    entries = []
    for record in git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
        if not record:
            continue
        header, path = record.split(b"\t", 1)
        mode, kind, oid = decode(header).split(" ")
        entries.append({"path": decode(path), "mode": mode, "type": kind, "object": oid})
    return sorted(entries, key=lambda entry: entry["path"])


def index_entries(repo: Path) -> list[dict]:
    entries = []
    for record in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        header, path = record.split(b"\t", 1)
        mode, oid, stage = decode(header).split(" ")
        entries.append({"path": decode(path), "mode": mode, "object": oid, "stage": int(stage)})
    return entries


def read_blobs(repo: Path, objects: list[str]) -> dict[str, bytes]:
    """One cat-file process per repository, not one process per tracked file."""
    if not objects:
        return {}
    ids = sorted(set(objects))
    raw = git(repo, "cat-file", "--batch", input_bytes=("\n".join(ids) + "\n").encode("ascii"))
    blobs = {}
    cursor = 0
    for expected in ids:
        end = raw.find(b"\n", cursor)
        header = raw[cursor:end].split(b" ")
        if end < 0 or len(header) != 3 or decode(header[0]) != expected or header[1] != b"blob":
            raise InventoryError("required committed blob is missing or has an invalid type")
        size = int(header[2])
        cursor = end + 1
        data = raw[cursor:cursor + size]
        if len(data) != size or raw[cursor + size:cursor + size + 1] != b"\n":
            raise InventoryError("incomplete committed blob")
        blobs[expected] = data
        cursor += size + 1
    return blobs


def parse_modules(repo: Path, content: bytes) -> tuple[list[dict], list[dict]]:
    """Parse committed .gitmodules using Git syntax, without includes or updates."""
    issues = []
    if not content:
        return [], issues
    raw = git(repo, "config", "--no-includes", "--file", "-", "--null", "--list", input_bytes=content)
    sections: dict[str, dict[str, list[str]]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        key, _, value = record.partition(b"\n")
        key_text = decode(key)
        if not key_text.startswith("submodule.") or "." not in key_text[len("submodule."):]:
            continue
        name, field = key_text[len("submodule."):].rsplit(".", 1)
        sections.setdefault(name, {})
        if field in ("path", "url"):
            sections[name].setdefault(field, []).append(decode(value))
    modules = []
    for name, fields in sorted(sections.items()):
        valid = True
        for field in ("path", "url"):
            if len(fields.get(field, [])) != 1:
                issues.append({"code": "invalid_submodule_declaration", "severity": "error",
                               "name": name, "field": field, "count": len(fields.get(field, []))})
                valid = False
        if not valid:
            continue
        path, url = fields["path"][0], fields["url"][0]
        parts = PurePosixPath(path).parts
        if not path or path.startswith("/") or any(p in ("..", ".git") for p in parts) or str(PurePosixPath(path)) != path:
            issues.append({"code": "unsafe_submodule_path", "severity": "error", "name": name, "path": path})
            continue
        if not url or "\n" in url or "\r" in url:
            issues.append({"code": "invalid_submodule_url", "severity": "error", "name": name, "path": path})
            continue
        modules.append({"name": name, "path": path, "declared_url": redact_url(url)})
    return modules, issues


def working_status(repo: Path) -> list[dict]:
    # Inspect children ourselves only after validating their paths and pins.
    records = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=all").split(b"\0")
    result = []
    i = 0
    while i < len(records):
        record = records[i]
        i += 1
        if not record:
            continue
        entry = {"code": decode(record[:2]), "path": decode(record[3:])}
        if record[:1] in (b"R", b"C") or record[1:2] in (b"R", b"C"):
            if i >= len(records):
                raise InventoryError("truncated Git rename status")
            entry["original_path"] = decode(records[i])
            i += 1
        result.append(entry)
    return result


def configured_remote(repo: Path, name: str = "origin") -> str | None:
    try:
        return redact_url(decode(git(repo, "config", "--no-includes", "--get", f"remote.{name}.url")).strip()) or None
    except InventoryError:
        return None


def safe_child(root: Path, relative: str) -> Path | None:
    """Never follow a symlink in a gitlink path, even when its target is inside."""
    current = root
    for component in PurePosixPath(relative).parts:
        current = current / component
        if current.is_symlink():
            return None
    if not current.resolve().is_relative_to(root.resolve()):
        return None
    return current


def snapshot(repo: Path, revision: str, remote_url: str | None = None, require_clean: bool = False) -> tuple[dict, list[dict]]:
    root = repo.resolve()
    actual_root = Path(decode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
    if actual_root != root:
        raise InventoryError("--repo must identify the repository root")
    inspected = decode(git(root, "rev-parse", "--verify", "--end-of-options", revision + "^{commit}")).strip()
    inventory: dict = {
        "schema_version": SCHEMA_VERSION,
        "scope": "P001 committed source inventory; no runtime or remote availability claim",
        "environment": {
            "system": platform.system(), "architecture": platform.machine(),
            "kernel": platform.release(), "python": platform.python_version(),
            "git": decode(git(root, "--version")).strip(),
        },
        "source": {"commit": inspected, "remote_url": redact_url(remote_url) if remote_url else configured_remote(root)},
        "repositories": [], "submodules": [], "issues": [],
    }
    tracked: list[dict] = []
    visited: set[Path] = set()

    def issue(code: str, repository: str, severity: str = "error", **details: object) -> None:
        inventory["issues"].append({"code": code, "severity": severity, "repository": repository, **details})

    def visit(path: Path, commit: str, prefix: str, effective_remote: str | None) -> None:
        if path.resolve() in visited:
            issue("recursive_repository_cycle", prefix)
            return
        visited.add(path.resolve())
        entries = tree_entries(path, commit)
        head = decode(git(path, "rev-parse", "HEAD")).strip()
        head_entries = entries if head == commit else tree_entries(path, head)
        indexed = index_entries(path)
        head_by_path = {entry["path"]: {"mode": entry["mode"], "object": entry["object"], "stage": 0}
                        for entry in head_entries}
        index_by_path: dict[str, list[dict]] = {}
        for entry in indexed:
            index_by_path.setdefault(entry["path"], []).append({key: entry[key] for key in ("mode", "object", "stage")})
        index_changes = [{"path": name, "head": head_by_path.get(name), "index": index_by_path.get(name, [])}
                         for name in sorted(set(head_by_path) | set(index_by_path))
                         if index_by_path.get(name, []) != ([head_by_path[name]] if name in head_by_path else [])]
        try:
            status = working_status(path)
        except InventoryError:
            status = None
            issue("unreadable_worktree_status", prefix)
        if require_clean and (status is None or status or index_changes or head != commit):
            issue("checkout_not_clean_at_requested_revision", prefix, head=head, requested_commit=commit,
                  changed_paths=len(status) if status is not None else None, staged_changes=len(index_changes))
        tree = decode(git(path, "rev-parse", commit + "^{tree}")).strip()
        repo_data = {
            "path": prefix, "commit": commit, "tree": tree, "checkout_head": head,
            "checkout_matches_ref": head == commit,
            "worktree_clean": not status and not index_changes if status is not None else None,
            "working_tree_status": status,
            "working_tree_status_scope": "non-submodule files; child checkouts inspected explicitly",
            "staged_index_changes": index_changes,
            "index_gitlinks": [entry for entry in indexed if entry["mode"] == "160000"],
            "shallow": decode(git(path, "rev-parse", "--is-shallow-repository")).strip() == "true",
            "remote_url": effective_remote, "configured_origin": configured_remote(path),
            "tracked_entries": len(entries), "licenses": [],
        }
        inventory["repositories"].append(repo_data)
        local_by_path = {entry["path"]: entry for entry in entries}
        if len(local_by_path) != len(entries):
            issue("duplicate_tracked_path", prefix)
        for entry in entries:
            full = entry["path"] if prefix == "." else prefix + "/" + entry["path"]
            tracked.append({**entry, "path": full, "repository": prefix, "repository_path": entry["path"]})
        licenses = [entry for entry in entries if entry["type"] == "blob" and entry["mode"] != "120000"
                    and (LICENSE_NAME.fullmatch(PurePosixPath(entry["path"]).name) or "LICENSES" in PurePosixPath(entry["path"]).parts)]
        modules_entry = local_by_path.get(".gitmodules")
        if modules_entry and modules_entry["mode"] not in ("100644", "100755"):
            issue("nonregular_gitmodules", prefix)
            modules_entry = None
        blobs = read_blobs(path, [entry["object"] for entry in licenses] + ([modules_entry["object"]] if modules_entry else []))
        for entry in licenses:
            data = blobs[entry["object"]]
            repo_data["licenses"].append({"path": entry["path"], "git_blob": entry["object"],
                                         "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                                         "classification": "license-like filename; not a legal determination"})
        try:
            modules, module_issues = parse_modules(path, blobs[modules_entry["object"]] if modules_entry else b"")
        except InventoryError:
            modules, module_issues = [], [{"code": "unparseable_gitmodules", "severity": "error"}]
        for detail in module_issues:
            inventory["issues"].append({**detail, "repository": prefix})
        declarations: dict[str, dict] = {}
        for module in modules:
            if module["path"] in declarations:
                issue("duplicate_submodule_path", prefix, path=module["path"])
                continue
            declarations[module["path"]] = module
        gitlinks = [entry for entry in entries if entry["mode"] == "160000"]
        gitlink_paths = {entry["path"] for entry in gitlinks}
        for declared_path in sorted(set(declarations) - gitlink_paths):
            issue("declaration_without_gitlink", prefix, path=declared_path)
        for entry in gitlinks:
            local = entry["path"]
            full = local if prefix == "." else prefix + "/" + local
            module = declarations.get(local)
            resolved = resolve_submodule_url(effective_remote, module["declared_url"]) if module else None
            record = {
                "path": full, "repository": prefix, "repository_path": local,
                "commit": entry["object"], "name": module["name"] if module else None,
                "declared_url": module["declared_url"] if module else None, "resolved_url": resolved,
                "remote_availability": "not_checked", "content_status": "not_checked_out",
                "recursive_inventory": "unavailable_until_exact_submodule_content_is_obtained",
            }
            inventory["submodules"].append(record)
            if not module:
                issue("gitlink_without_declaration", prefix, path=local)
            elif resolved is None:
                issue("relative_url_without_remote", prefix, severity="warning", path=local)
            child = safe_child(path, local)
            if child is None:
                record["content_status"] = "unsafe_symlink"
                issue("symlink_in_gitlink_path", prefix, path=local)
                continue
            marker = child / ".git"
            if marker.is_symlink():
                record["content_status"] = "unsafe_git_marker"
                issue("symlink_submodule_git_marker", prefix, path=local)
                continue
            if not marker.exists():
                continue
            try:
                child_root = Path(decode(git(child, "rev-parse", "--show-toplevel")).strip()).resolve()
                if child_root != child.resolve():
                    raise InventoryError("gitlink is not an independent checkout")
                child_head = decode(git(child, "rev-parse", "HEAD")).strip()
                record["checkout_head"] = child_head
                if child_head != entry["object"]:
                    record["content_status"] = "checkout_mismatch"
                    issue("submodule_pin_mismatch", prefix, path=local, expected=entry["object"], actual=child_head)
                    continue
                record["content_status"] = "available_at_pin"
                record["recursive_inventory"] = "inspected"
                visit(child, child_head, full, resolved)
            except InventoryError as error:
                record["content_status"] = "unreadable_checkout"
                record["recursive_inventory"] = "unavailable"
                issue("unreadable_submodule_checkout", prefix, path=local, detail=str(error))

    visit(root, inspected, ".", inventory["source"]["remote_url"])
    root_data = inventory["repositories"][0]
    inventory["source"]["tree"] = root_data["tree"]
    inventory["source"]["checkout_head"] = root_data["checkout_head"]
    refs = []
    for line in git(root, "for-each-ref", "--format=%(refname)%00%(objectname)%00%(upstream)", "refs/heads", "refs/remotes", "refs/tags").splitlines():
        ref, oid, upstream = decode(line).split("\0")
        refs.append({"ref": ref, "object": oid, "upstream": upstream or None})
    inventory["source"]["observed_refs"] = refs
    inventory["source"]["ref_scope"] = "locally available refs only; not a remote branch listing"
    inventory["repositories"].sort(key=lambda value: value["path"])
    inventory["submodules"].sort(key=lambda value: value["path"])
    inventory["issues"].sort(key=lambda value: (value["repository"], value.get("path", ""), value["code"]))
    tracked.sort(key=lambda value: value["path"])
    errors = sum(value["severity"] == "error" for value in inventory["issues"])
    inventory["inventory_status"] = "INVALID" if errors else "VALID"
    inventory["summary"] = {
        "inspected_repositories": len(inventory["repositories"]), "tracked_entries": len(tracked),
        "gitlinks": len(inventory["submodules"]),
        "available_gitlinks": sum(value["content_status"] == "available_at_pin" for value in inventory["submodules"]),
        "unavailable_gitlinks": sum(value["content_status"] != "available_at_pin" for value in inventory["submodules"]),
        "recursive_content_complete": all(value["content_status"] == "available_at_pin" for value in inventory["submodules"]),
        "gitlink_count_scope": "all gitlinks in inspected repositories; descendants of unavailable gitlinks are unknown",
        "error_count": errors,
        "warning_count": sum(value["severity"] == "warning" for value in inventory["issues"]),
    }
    return inventory, tracked


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--ref", default="HEAD", help="Exact committed snapshot to inspect; defaults to HEAD")
    parser.add_argument("--remote-url", help="Public source remote used to resolve relative .gitmodules URLs")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tracked-output", type=Path, help="Separate full tracked-entry inventory; otherwise embedded")
    parser.add_argument("--require-clean", action="store_true", help="Fail unless every inspected checkout is clean and at the requested pin")
    args = parser.parse_args(argv)
    try:
        if args.tracked_output and args.tracked_output.resolve() == args.output.resolve():
            raise InventoryError("--output and --tracked-output must be different files")
        inventory, tracked = snapshot(args.repo, args.ref, args.remote_url, args.require_clean)
        if args.tracked_output:
            payload = json_bytes({"schema_version": SCHEMA_VERSION, "source_commit": inventory["source"]["commit"], "entries": tracked})
            args.tracked_output.parent.mkdir(parents=True, exist_ok=True)
            args.tracked_output.write_bytes(payload)
            inventory["tracked_files"] = {"path": os.path.relpath(args.tracked_output.resolve(), args.output.parent.resolve()),
                                          "sha256": hashlib.sha256(payload).hexdigest(), "entries": len(tracked)}
        else:
            inventory["tracked_files"] = tracked
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(json_bytes(inventory))
        print(json.dumps({"inventory_status": inventory["inventory_status"], **inventory["summary"]}, sort_keys=True))
        return 1 if inventory["summary"]["error_count"] else 0
    except (InventoryError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"inventory: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
