#!/usr/bin/env python3
"""Obtain exact recursive gitlink contents for P001 source inspection.

Committed .gitmodules files and pins are never edited. Relative root URLs are
resolved against the explicitly supplied public upstream; nested URLs use the
parent's actual fetched origin. This is a source-inventory prerequisite, not the
P002 lock/URL-repair/two-clean-clone qualification.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from urllib.parse import urlsplit, urlunsplit

_SPEC = importlib.util.spec_from_file_location("p001_inventory_support", Path(__file__).with_name("inventory.py"))
assert _SPEC and _SPEC.loader
inventory = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(inventory)

INSPECTION_ATTRIBUTES = b"* -text -eol -ident -filter -working-tree-encoding\n"
INSPECTION_POLICY = {
    "name": "raw_committed_bytes_for_source_inspection_v1",
    "scope": "Fresh task-owned source-inspection checkouts only; existing checkouts are verified without rewriting files or configuration.",
    "attributes_path": ".git/info/attributes",
    "attributes": INSPECTION_ATTRIBUTES.decode("ascii"),
    "attributes_sha256": hashlib.sha256(INSPECTION_ATTRIBUTES).hexdigest(),
    "committed_attributes_modified": False,
}


class RetrievalError(RuntimeError):
    pass


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def public_url(value: str, allow_local: bool = False) -> str:
    """Reject embedded credentials; normalize public GitHub transports to HTTPS."""
    if not isinstance(value, str) or not value or any(c in value for c in "\r\n\x00"):
        raise RetrievalError("Source URL is empty or contains control characters")
    if value.startswith("git@github.com:"):
        value = "https://github.com/" + value[len("git@github.com:"):]
    parts = urlsplit(value)
    if parts.query or parts.fragment or parts.password:
        raise RetrievalError("Source URL contains credentials, query parameters, or fragments")
    if parts.scheme in ("git", "ssh") and parts.hostname == "github.com" and parts.username in (None, "git"):
        value = urlunsplit(("https", "github.com", parts.path, "", ""))
        parts = urlsplit(value)
    if parts.scheme == "https" and parts.hostname and parts.username is None:
        if not parts.path or parts.path == "/":
            raise RetrievalError("HTTPS source must include a repository path")
        return value
    if allow_local and parts.scheme == "file" and parts.netloc in ("", "localhost"):
        return value
    if allow_local and not parts.scheme and Path(value).is_absolute():
        return str(Path(value).resolve())
    raise RetrievalError("Only public HTTPS source URLs are permitted (local fixtures require --allow-local-fixtures)")


def safe_child(parent: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if (not relative or relative == "." or parts.is_absolute() or str(parts) != relative
            or any(p in (".", "..", ".git") for p in parts.parts)
            or any(c in relative for c in "\x00\r\n")):
        raise RetrievalError("Unsafe or noncanonical submodule path")
    child = inventory.safe_child(parent, relative)
    if child is None:
        raise RetrievalError("Submodule path contains a symlink or escapes its parent")
    return child


class Commands:
    def __init__(self, allow_local: bool) -> None:
        self.allow_local = allow_local
        self.records: list[dict] = []
        self.lock = threading.Lock()

    def run(self, repo: Path | None, *args: str, input_bytes: bytes | None = None) -> bytes:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false",
            "GIT_ALLOW_PROTOCOL": "https:file" if self.allow_local else "https",
        })
        command = ["git", "--no-optional-locks", "-c", "core.hooksPath=" + os.devnull,
                   "-c", "core.fsmonitor=false", "-c", "credential.helper=",
                   "-c", "http.extraHeader=", "-c", "submodule.recurse=false"]
        if repo is not None:
            command += ["-C", str(repo)]
        command += list(args)
        record = {"command": command, "started_at": timestamp()}
        try:
            completed = subprocess.run(command, env=env, input=input_bytes, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, timeout=300, check=False)
            stderr = completed.stderr.decode("utf-8", "replace")
            # Accepted network URLs contain no authentication material. Never
            # export command stdout, which may read a pre-existing remote URL.
            record.update({"exit_code": completed.returncode,
                           "stdout_bytes": len(completed.stdout),
                           "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
                           "stderr": stderr[:16384], "stderr_bytes": len(completed.stderr)})
            if completed.returncode:
                raise RetrievalError(f"git {args[0]} failed (exit {completed.returncode})")
            return completed.stdout
        except (OSError, subprocess.TimeoutExpired) as exc:
            record["error"] = type(exc).__name__
            raise RetrievalError(f"git {args[0]} could not complete: {type(exc).__name__}") from exc
        finally:
            record["finished_at"] = timestamp()
            with self.lock:
                self.records.append(record)


def origin(commands: Commands, repo: Path) -> str | None:
    try:
        return commands.run(repo, "config", "--no-includes", "--get", "remote.origin.url").decode().strip()
    except RetrievalError:
        return None


def tree_entries(repo: Path, pin: str, commands: Commands) -> list[dict]:
    result = []
    for raw in commands.run(repo, "ls-tree", "-rz", "--full-tree", pin).split(b"\0"):
        if raw:
            metadata, path = raw.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split(" ")
            result.append({"path": os.fsdecode(path), "mode": mode, "type": kind, "object": oid})
    return result


def index_entries(repo: Path, commands: Commands) -> list[dict]:
    result = []
    for raw in commands.run(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if raw:
            metadata, path = raw.split(b"\t", 1)
            mode, oid, stage = metadata.decode("ascii").split(" ")
            result.append({"path": os.fsdecode(path), "mode": mode, "object": oid, "stage": int(stage)})
    return result


def physical_blob(path: Path, algorithm: str) -> tuple[str, str]:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        data = os.readlink(os.fsencode(path))
        return "120000", hashlib.new(algorithm, b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if not stat.S_ISREG(info.st_mode):
        return "unsupported", ""
    digest = hashlib.new(algorithm, b"blob " + str(info.st_size).encode() + b"\0")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "100755" if info.st_mode & stat.S_IXUSR else "100644", digest.hexdigest()


def parent_state(repo: Path, tracked: list[dict], commands: Commands) -> str:
    """Fingerprint parent files/index without consulting status or clean filters."""
    names = {entry["path"] for entry in tracked if entry["mode"] != "160000"}
    names.update(os.fsdecode(path) for path in commands.run(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if path)
    digest = hashlib.sha256()
    for name in sorted(names):
        relative = PurePosixPath(name)
        parent = repo if str(relative.parent) == "." else safe_child(repo, str(relative.parent))
        try:
            mode, oid = physical_blob(parent / relative.name, "sha256")
        except FileNotFoundError:
            mode, oid = "missing", ""
        digest.update(json.dumps([name, mode, oid], ensure_ascii=True).encode() + b"\n")
    digest.update(commands.run(repo, "ls-files", "--stage", "-z"))
    return digest.hexdigest()


def declarations_match(repo: Path, tracked: list[dict], commands: Commands) -> bool:
    entry = next((item for item in tracked if item["path"] == ".gitmodules"), None)
    path = repo / ".gitmodules"
    if entry is None:
        return not path.exists() and not path.is_symlink()
    algorithm = commands.run(repo, "rev-parse", "--show-object-format").decode().strip()
    return physical_blob(path, algorithm) == (entry["mode"], entry["object"])


def assert_clean(repo: Path, pin: str, commands: Commands) -> str:
    actual = commands.run(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if actual != pin:
        raise RetrievalError("Existing checkout does not match its committed gitlink; no reset performed")
    entries = tree_entries(repo, pin, commands)
    expected = {(e["path"], e["mode"], e["object"], 0) for e in entries}
    indexed = {(e["path"], e["mode"], e["object"], e["stage"]) for e in index_entries(repo, commands)}
    untracked = commands.run(repo, "ls-files", "--others", "--exclude-standard", "-z")
    if untracked or expected != indexed:
        raise RetrievalError("Existing checkout has local or staged changes; no reset performed")
    # Git status can hide edits behind assume-unchanged/skip-worktree flags,
    # core.filemode=false or clean filters. Verify raw bytes and modes directly;
    # never invoke a configured source filter while deciding whether reuse is safe.
    algorithm = commands.run(repo, "rev-parse", "--show-object-format").decode().strip()
    if algorithm not in ("sha1", "sha256"):
        raise RetrievalError("Unsupported source Git object format")
    for entry in entries:
        relative = PurePosixPath(entry["path"])
        if relative.is_absolute() or any(part in ("..", ".git") for part in relative.parts):
            raise RetrievalError("Unsafe tracked source path")
        parent = repo if str(relative.parent) == "." else safe_child(repo, str(relative.parent))
        path = parent / relative.name
        if entry["mode"] == "160000":
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise RetrievalError("Existing checkout has an unsafe gitlink path")
            continue
        mode, oid = physical_blob(path, algorithm)
        if mode != entry["mode"]:
            raise RetrievalError(f"Existing checkout has local or staged changes: file type or executable bit differs at {entry['path']!r}")
        if oid != entry["object"]:
            raise RetrievalError(f"Existing checkout has local or staged changes: tracked bytes differ at {entry['path']!r}")
    return commands.run(repo, "rev-parse", "HEAD^{tree}").decode().strip()


def discover(repo: Path, pin: str, fetched_origin: str, prefix: str,
             allow_local: bool, commands: Commands, ancestors: tuple = (), declared_origin: str | None = None) -> list[dict]:
    entries = tree_entries(repo, pin, commands)
    gitlinks = [entry for entry in entries if entry["mode"] == "160000"]
    module_entry = next((entry for entry in entries if entry["path"] == ".gitmodules"), None)
    if module_entry and module_entry["mode"] not in ("100644", "100755"):
        raise RetrievalError("Committed .gitmodules must be a regular file")
    content = commands.run(repo, "cat-file", "blob", module_entry["object"]) if module_entry else b""
    sections = {}
    if content:
        config = commands.run(repo, "config", "--no-includes", "--file", "-", "--null", "--list", input_bytes=content)
        for item in config.split(b"\0"):
            if not item:
                continue
            raw_key, _, raw_value = item.partition(b"\n")
            key, value = os.fsdecode(raw_key), os.fsdecode(raw_value)
            if key.startswith("submodule.") and "." in key[len("submodule."):]:
                name, field = key[len("submodule."):].rsplit(".", 1)
                fields = sections.setdefault(name, {})
                if field in ("path", "url"):
                    fields.setdefault(field, []).append(value)
    modules = []
    for name, fields in sections.items():
        if any(len(fields.get(field, [])) != 1 for field in ("path", "url")):
            raise RetrievalError("Invalid or duplicate committed .gitmodules fields")
        modules.append({"name": name, "path": fields["path"][0], "declared_url": fields["url"][0]})
    by_path = {module["path"]: module for module in modules}
    if len(by_path) != len(modules) or set(by_path) != {entry["path"] for entry in gitlinks}:
        raise RetrievalError("Committed gitlinks and unique .gitmodules declarations do not match")
    tasks = []
    for entry in gitlinks:
        module = by_path[entry["path"]]
        safe_child(repo, entry["path"])
        if not module["declared_url"] or any(c in module["declared_url"] for c in "\x00\r\n"):
            raise RetrievalError("Committed submodule URL is empty or contains control characters")
        declared_parts = urlsplit(module["declared_url"])
        if (declared_parts.query or declared_parts.fragment or declared_parts.password
                or (declared_parts.username is not None and declared_parts.scheme == "https")):
            raise RetrievalError("Committed submodule URL contains authentication material or query/fragment data")
        resolved = inventory.resolve_submodule_url(declared_origin or fetched_origin, module["declared_url"])
        acquisition = inventory.resolve_submodule_url(fetched_origin, module["declared_url"])
        url = public_url(acquisition or "", allow_local)
        if (url, entry["object"]) in ancestors or len(ancestors) >= 32:
            raise RetrievalError("Recursive source dependency cycle or excessive nesting")
        tasks.append({"parent": repo, "parent_path": prefix, "local_path": entry["path"],
                      "path": entry["path"] if prefix == "." else prefix + "/" + entry["path"],
                      "name": module["name"], "declared_url": module["declared_url"],
                      "resolved_url": resolved, "acquisition_resolved_url": acquisition,
                      "fetch_url": url, "commit": entry["object"],
                      "ancestors": ancestors + ((url, entry["object"]),)})
    return tasks


def obtain(task: dict, commands: Commands) -> dict:
    record = {key: value for key, value in task.items() if key not in ("parent", "local_path", "ancestors")}
    record.update({"status": "FAIL", "started_at": timestamp(),
                   "checkout_policy": {"name": INSPECTION_POLICY["name"], "applied_to_fresh_checkout": False}})
    staging = None
    try:
        child = safe_child(task["parent"], task["local_path"])
        if child.exists() and not child.is_dir():
            raise RetrievalError("Submodule destination is not a directory")
        if child.is_dir() and any(child.iterdir()):
            if not (child / ".git").exists() or (child / ".git").is_symlink():
                raise RetrievalError("Submodule destination contains unrelated files; left untouched")
            if Path(commands.run(child, "rev-parse", "--show-toplevel").decode().strip()).resolve() != child.resolve():
                raise RetrievalError("Existing submodule is not an independent checkout")
            tree = assert_clean(child, task["commit"], commands)
            configured = origin(commands, child)
            if configured != task["fetch_url"]:
                raise RetrievalError("Existing origin differs from requested public source; left untouched")
            record["retrieval"] = "REUSED_CLEAN_EXACT_PIN"
        else:
            child.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=".p001-source-", dir=child.parent))
            commands.run(staging, "init", "--quiet")
            commands.run(staging, "config", "core.hooksPath", os.devnull)
            commands.run(staging, "config", "core.autocrlf", "false")
            commands.run(staging, "config", "core.symlinks", "true")
            commands.run(staging, "config", "core.filemode", "true")
            # core.autocrlf=false does not override committed eol/ident/encoding
            # attributes. P001 inspects Git blobs, so disable all transformations
            # in this new repository's private highest-precedence attributes file.
            # Never alter tracked .gitattributes or an existing user's checkout.
            attributes = staging / ".git" / "info" / "attributes"
            attributes.parent.mkdir(parents=True, exist_ok=True)
            attributes.write_bytes(INSPECTION_ATTRIBUTES)
            record["checkout_policy"].update({"applied_to_fresh_checkout": True,
                                               "attributes_path": INSPECTION_POLICY["attributes_path"],
                                               "attributes_sha256": hashlib.sha256(attributes.read_bytes()).hexdigest()})
            commands.run(staging, "remote", "add", "origin", task["fetch_url"])
            commands.run(staging, "fetch", "--depth=1", "--no-tags", "--no-recurse-submodules", "origin", task["commit"])
            actual = commands.run(staging, "rev-parse", "--verify", task["commit"] + "^{commit}").decode().strip()
            if actual != task["commit"]:
                raise RetrievalError("Fetched object does not resolve to the exact pinned commit")
            commands.run(staging, "checkout", "--quiet", "--detach", task["commit"])
            tree = assert_clean(staging, task["commit"], commands)
            # Revalidate containment before publication; never replace a populated
            # destination or delete a pre-existing checkout.
            child = safe_child(task["parent"], task["local_path"])
            if child.exists():
                child.rmdir()
            staging.rename(child)
            staging = None
            configured = origin(commands, child)
            if configured != task["fetch_url"]:
                raise RetrievalError("Fetched origin does not match recorded public URL")
            record["retrieval"] = "FETCHED_EXACT_PIN"
        record.update({"status": "PASS", "tree": tree, "configured_origin": configured})
    except (RetrievalError, inventory.InventoryError, OSError, ValueError) as exc:
        record["error"] = str(exc)
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        record["finished_at"] = timestamp()
    print(f"P001 source {record['status']}: {record['path']}", flush=True)
    return record



def fetch_historical_citations(repo: Path, manifest_path: Path, current: list[dict],
                               upstream_url: str, commands: Commands, report: dict) -> None:
    """Fetch each frozen cited owner explicitly, without moving current HEADs.

    A depth-one current checkout need not contain the historical citation pin.
    Always request that exact historical object, even when a local cache happens
    to contain it, and verify every original parent-to-child chain independently.
    """
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RetrievalError("Historical citation manifest has an unsupported schema")
    original = manifest.get("inspected_commit")
    if not isinstance(original, str) or not re.fullmatch(r"[0-9a-f]{40}", original):
        raise RetrievalError("Historical citations require an exact inspected commit")
    records = manifest.get("evidence")
    if not isinstance(records, list) or not records:
        raise RetrievalError("Historical citation evidence cannot be empty")
    history = {"status": "FAIL", "inspected_commit": original,
               "requested_citations": len(records), "verified_citations": 0,
               "submodules": [], "retrieval_policy": "EXPLICIT_EXACT_FROZEN_PIN_FETCH"}
    report["historical_citations"] = history
    try:
        resolved = commands.run(repo, "rev-parse", "--verify", original + "^{commit}").decode().strip()
    except RetrievalError:
        commands.run(repo, "fetch", "--depth=1", "--no-tags", "--no-recurse-submodules", upstream_url, original)
        resolved = commands.run(repo, "rev-parse", "--verify", original + "^{commit}").decode().strip()
    if resolved != original:
        raise RetrievalError("Historical inspected commit does not resolve exactly")
    current_by_path = {item["path"]: item for item in current if item.get("status") == "PASS"}
    fetched = {}
    seen = set()
    for citation in records:
        if (not isinstance(citation, dict) or not isinstance(citation.get("id"), str)
                or not citation["id"] or citation["id"] in seen):
            raise RetrievalError("Historical citation IDs must be nonempty and unique")
        seen.add(citation["id"])
        owner = citation.get("repository", ".")
        chain = citation.get("gitlink_chain", [])
        if not isinstance(chain, list) or (owner == ".") != (not chain):
            raise RetrievalError("Historical source needs its complete original gitlink chain")
        folder, parent_pin, prefix = repo, original, ""
        for hop in chain:
            if not isinstance(hop, dict):
                raise RetrievalError("Invalid historical gitlink hop")
            relative, pin = hop.get("path"), hop.get("commit")
            if not isinstance(relative, str) or not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin):
                raise RetrievalError("Historical gitlink needs a safe path and exact commit")
            child = safe_child(folder, relative)
            wanted = b"160000 commit " + pin.encode("ascii") + b"\t" + relative.encode("utf-8") + b"\0"
            if commands.run(folder, "--literal-pathspecs", "ls-tree", "-z", parent_pin, "--", relative) != wanted:
                raise RetrievalError("Historical gitlink differs from its frozen parent chain")
            prefix = prefix + "/" + relative if prefix else relative
            present = current_by_path.get(prefix)
            if present is None:
                raise RetrievalError("Historical source owner has no verified current checkout")
            key = (prefix, pin)
            if key not in fetched:
                before = commands.run(child, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
                if before != present["commit"]:
                    raise RetrievalError("Current source HEAD moved before historical fetch")
                fetch_url = public_url(origin(commands, child), commands.allow_local)
                if fetch_url != present["fetch_url"]:
                    raise RetrievalError("Current source origin moved before historical fetch")
                commands.run(child, "fetch", "--depth=1", "--no-tags", "--no-recurse-submodules", fetch_url, pin)
                if commands.run(child, "rev-parse", "--verify", pin + "^{commit}").decode().strip() != pin:
                    raise RetrievalError("Fetched historical citation pin does not resolve exactly")
                after = commands.run(child, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
                if after != before:
                    raise RetrievalError("Historical fetch moved the current source HEAD")
                fetched[key] = {"path": prefix, "commit": pin, "status": "PASS", "fetch_url": fetch_url,
                                "tree": commands.run(child, "rev-parse", pin + "^{tree}").decode().strip(),
                                "current_commit": before, "current_head_unchanged": True,
                                "retrieval": "FETCHED_FROZEN_CITATION_PIN", "citation_ids": []}
                history["submodules"].append(fetched[key])
            if citation["id"] not in fetched[key]["citation_ids"]:
                fetched[key]["citation_ids"].append(citation["id"])
            folder, parent_pin = child, pin
        if (prefix or ".") != owner or citation.get("repository_commit", original) != parent_pin:
            raise RetrievalError("Historical citation owner differs from its complete gitlink chain")
        source = citation.get("path")
        if not isinstance(source, str):
            raise RetrievalError("Historical citation path is missing")
        safe_child(folder, source)
        blob = commands.run(folder, "rev-parse", "--verify", f"{parent_pin}:{source}").decode().strip()
        if blob != citation.get("blob_sha1") or commands.run(folder, "cat-file", "-t", blob).strip() != b"blob":
            raise RetrievalError("Historical citation blob differs from its frozen source object")
        history["verified_citations"] += 1
    history["submodules"].sort(key=lambda item: (item["path"], item["commit"]))
    history["status"] = "PASS"


def prepare(repo: Path, upstream_url: str, jobs: int = 6, allow_local: bool = False,
            classification_manifest: Path | None = None) -> dict:
    commands = Commands(allow_local)
    report = {"schema_version": 1, "result": "FAIL", "scope": "P001 recursive pinned source inspection prerequisite; not P002 qualification",
              "started_at": timestamp(), "environment": {"system": platform.system(), "architecture": platform.machine(),
              "python": platform.python_version()}, "fresh_checkout_policy": INSPECTION_POLICY,
              "submodules": [], "commands": commands.records, "failures": [],
              "historical_citations": {"status": "NOT_REQUESTED"}}
    try:
        if jobs < 1 or jobs > 32:
            raise RetrievalError("--jobs must be between 1 and 32")
        repo = repo.resolve(strict=True)
        if Path(commands.run(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve() != repo:
            raise RetrievalError("--repo must be the root of a Git worktree")
        upstream_url = public_url(upstream_url, allow_local)
        pin = commands.run(repo, "rev-parse", "HEAD^{commit}").decode().strip()
        tree = commands.run(repo, "rev-parse", "HEAD^{tree}").decode().strip()
        tracked = tree_entries(repo, pin, commands)
        before = parent_state(repo, tracked, commands)
        original = origin(commands, repo)
        report["source"] = {"commit": pin, "tree": tree, "original_origin": inventory.redact_url(original) if original else None,
                            "upstream_url": upstream_url, "initial_parent_state_sha256": before}
        # Unrelated development edits are retained. Source declarations and pins
        # must agree with HEAD before any dependency checkout is created.
        indexed = index_entries(repo, commands)
        relevant = {e["path"] for e in tracked if e["mode"] == "160000" or e["path"] == ".gitmodules"}
        relevant.update(e["path"] for e in indexed if e["mode"] == "160000" or e["path"] == ".gitmodules")
        expected = {(e["path"], e["mode"], e["object"], 0) for e in tracked if e["path"] in relevant}
        actual = {(e["path"], e["mode"], e["object"], e["stage"]) for e in indexed if e["path"] in relevant}
        if expected != actual or not declarations_match(repo, tracked, commands):
            raise RetrievalError("Parent .gitmodules or staged gitlink pins differ from committed source")
        pending = discover(repo, pin, upstream_url, ".", allow_local, commands,
                           ((upstream_url, pin),), declared_origin=original)
        seen_paths = set()
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            while pending:
                tasks = []
                for task in pending:
                    if task["path"] in seen_paths:
                        raise RetrievalError("Duplicate recursive submodule path")
                    seen_paths.add(task["path"])
                    tasks.append(task)
                pending = []
                futures = {pool.submit(obtain, task, commands): task for task in tasks}
                for future in as_completed(futures):
                    task = futures[future]
                    record = future.result()
                    report["submodules"].append(record)
                    if record["status"] != "PASS":
                        report["failures"].append({"path": record["path"], "error": record["error"]})
                        continue
                    try:
                        child = safe_child(task["parent"], task["local_path"])
                        pending.extend(discover(child, task["commit"], record["configured_origin"], task["path"], allow_local, commands, task["ancestors"]))
                    except (RetrievalError, inventory.InventoryError, OSError, ValueError) as exc:
                        record["status"] = "FAIL"
                        record["error"] = "Nested inventory failed: " + str(exc)
                        report["failures"].append({"path": record["path"], "error": record["error"]})
        manifest_path = classification_manifest or repo / "tools/compat/logic-pro/classifications.json"
        if classification_manifest is not None or manifest_path.exists():
            fetch_historical_citations(repo, manifest_path, report["submodules"], upstream_url, commands, report)
        final_index = index_entries(repo, commands)
        final_relevant = relevant | {entry["path"] for entry in final_index
                                     if entry["mode"] == "160000" or entry["path"] == ".gitmodules"}
        final_pins = {(entry["path"], entry["mode"], entry["object"], entry["stage"])
                      for entry in final_index if entry["path"] in final_relevant}
        if final_pins != expected or not declarations_match(repo, tracked, commands):
            raise RetrievalError("Parent source declarations or staged pins changed during retrieval")
        if before != parent_state(repo, tracked, commands) or commands.run(repo, "rev-parse", "HEAD^{commit}").decode().strip() != pin:
            raise RetrievalError("Parent source or working state changed during retrieval")
        report["source"]["parent_source_unchanged"] = True
        report["result"] = "FAIL" if report["failures"] else "PASS"
    except (RetrievalError, inventory.InventoryError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        report["failures"].append({"path": ".", "error": str(exc)})
    report["submodules"].sort(key=lambda item: item["path"])
    report["failures"].sort(key=lambda item: (item["path"], item["error"]))
    report["recursive_submodules_observed"] = len(report["submodules"])
    report["recursive_content_complete"] = report["result"] == "PASS"
    report["finished_at"] = timestamp()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--upstream-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--allow-local-fixtures", action="store_true")
    parser.add_argument("--classification-manifest", type=Path,
                        help="frozen citation manifest; defaults to the repository classifications.json when present")
    args = parser.parse_args(argv)
    report = prepare(args.repo, args.upstream_url, args.jobs, args.allow_local_fixtures, args.classification_manifest)
    temporary = None
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".p001-report-",
                                         dir=args.output.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, args.output)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        print(f"Cannot write source retrieval report: {exc}", file=sys.stderr)
        return 1
    print(f"P001 source retrieval: {report['result']}; {len(report['submodules'])} recursive gitlinks")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
