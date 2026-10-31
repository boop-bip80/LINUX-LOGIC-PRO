#!/usr/bin/env python3
"""Reproduce the P001 source baseline in two independent, isolated checkouts.

No network, submodule initialization, source-tree reset, or runtime execution is
performed.  The source repository may be dirty: recovery uses only the two exact
commits in the manifest and records the source status before and after.  Every
ordinary tracked file, executable and symlink in each restored tree is checked
against its Git blob object ID.  Uninitialized gitlinks are explicitly recorded;
they are the P002 dependency-retrieval gate, not silently recovered contents.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any


class RecoveryError(RuntimeError):
    """A required recovery assertion failed."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def environment() -> dict[str, str]:
    """Keep recovery local and independent of user Git filters/hooks/replacements."""
    env = os.environ.copy()
    for name in (
        "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
    ):
        env.pop(name, None)
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "LC_ALL": "C",
    })
    return env


class Git:
    def __init__(self) -> None:
        self.transcript: list[dict[str, Any]] = []

    def run(self, repo: Path | None, *args: str) -> bytes:
        command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
                   "-c", "core.hooksPath=" + os.devnull]
        if repo is not None:
            command.extend(["-C", str(repo)])
        command.extend(args)
        try:
            result = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=environment(), check=False, timeout=600,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.transcript.append({"command": command, "error": str(exc)})
            raise RecoveryError(f"Git command could not complete: {exc}") from exc
        entry: dict[str, Any] = {
            "command": command, "exit_code": result.returncode,
            "stdout_bytes": len(result.stdout),
            "stdout_sha256": sha256(result.stdout),
            "stderr": result.stderr.decode("utf-8", "replace"),
        }
        if len(result.stdout) <= 16384:
            entry["stdout"] = result.stdout.decode("utf-8", "replace")
        self.transcript.append(entry)
        if result.returncode:
            raise RecoveryError(
                f"Git command failed ({result.returncode}): {' '.join(command)}\n"
                + result.stderr.decode("utf-8", "replace")
            )
        return result.stdout


def safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value or "\x00" in value or path.is_absolute()
        or any(part in ("", ".", "..", ".git") for part in value.split("/"))
    ):
        raise RecoveryError(f"Unsafe tracked or README path: {value!r}")
    return path


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryError(f"Cannot read recovery manifest: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RecoveryError("Recovery manifest must have schema_version 1")
    repository_url = value.get("repository_url")
    if not isinstance(repository_url, str) or not repository_url.startswith("https://"):
        raise RecoveryError("Manifest repository_url must identify its HTTPS source")
    for label in ("baseline", "integration"):
        snapshot = value.get(label)
        if not isinstance(snapshot, dict):
            raise RecoveryError(f"Manifest is missing {label}")
        for key in ("commit", "tree"):
            if not isinstance(snapshot.get(key), str) or not re.fullmatch(
                r"(?:[0-9a-f]{40}|[0-9a-f]{64})", snapshot[key]
            ):
                raise RecoveryError(f"{label}.{key} must be a complete object ID")
        readme = snapshot.get("readme")
        if not isinstance(readme, dict):
            raise RecoveryError(f"Manifest is missing {label}.readme")
        if not isinstance(readme.get("path"), str):
            raise RecoveryError(f"Manifest is missing {label}.readme.path")
        safe_path(readme["path"])
        if not isinstance(readme.get("sha256"), str) or not re.fullmatch(
            r"[0-9a-f]{64}", readme["sha256"]
        ):
            raise RecoveryError(f"{label}.readme.sha256 must be a SHA-256 digest")
        source_url = readme.get("source_url")
        base_url = repository_url.removesuffix(".git").rstrip("/")
        expected_url = f"{base_url}/blob/{snapshot['commit']}/{readme['path']}"
        if source_url != expected_url:
            raise RecoveryError(f"{label}.readme.source_url is not its immutable source URL")
    return value


def blob_hash(data: bytes, algorithm: str) -> str:
    return hashlib.new(
        algorithm, b"blob " + str(len(data)).encode("ascii") + b"\x00" + data
    ).hexdigest()


def materialization(git: Git, repo: Path, commit: str) -> dict[str, Any]:
    entries = git.run(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\x00")
    algorithm = git.run(repo, "rev-parse", "--show-object-format").decode().strip()
    if algorithm not in ("sha1", "sha256"):
        raise RecoveryError(f"Unsupported Git object format: {algorithm}")
    digest = hashlib.sha256()
    counts = {"regular_files": 0, "executables": 0, "symlinks": 0, "gitlinks": 0}
    gitlinks: list[dict[str, str]] = []
    readme_candidates: dict[str, str] = {}
    for raw in entries:
        if not raw:
            continue
        try:
            metadata, raw_path = raw.split(b"\t", 1)
            raw_mode, raw_type, raw_oid = metadata.split(b" ")
            mode, kind, oid = (part.decode("ascii") for part in (raw_mode, raw_type, raw_oid))
            relative = os.fsdecode(raw_path)
        except (ValueError, UnicodeError) as exc:
            raise RecoveryError("Malformed ls-tree record") from exc
        parts = safe_path(relative)
        path = repo.joinpath(*parts.parts)
        # Never dereference a tracked symlink, including one in a parent path.
        parent = path.parent
        while parent != repo:
            if parent.is_symlink():
                raise RecoveryError(f"Symlink parent in tracked path: {relative!r}")
            parent = parent.parent
        if mode == "160000" and kind == "commit":
            counts["gitlinks"] += 1
            if path.is_symlink() or (path.exists() and not path.is_dir()):
                raise RecoveryError(f"Invalid uninitialized gitlink path: {relative!r}")
            if path.is_dir() and any(path.iterdir()):
                raise RecoveryError(f"Unexpected populated submodule in isolated clone: {relative!r}")
            gitlinks.append({"path": relative, "commit": oid, "status": "NOT_INITIALIZED"})
            record = {"path": relative, "mode": mode, "object": oid, "kind": "gitlink"}
        else:
            try:
                metadata_stat = path.lstat()
                if mode == "120000" and kind == "blob":
                    if not stat.S_ISLNK(metadata_stat.st_mode):
                        raise RecoveryError(f"Tracked symlink was not restored: {relative!r}")
                    data = os.readlink(os.fsencode(path))
                    counts["symlinks"] += 1
                elif mode in ("100644", "100755") and kind == "blob":
                    if not stat.S_ISREG(metadata_stat.st_mode):
                        raise RecoveryError(f"Tracked regular file was not restored: {relative!r}")
                    executable = bool(metadata_stat.st_mode & stat.S_IXUSR)
                    if executable != (mode == "100755"):
                        raise RecoveryError(f"Tracked executable bit differs: {relative!r}")
                    data = path.read_bytes()
                    counts["executables" if executable else "regular_files"] += 1
                else:
                    raise RecoveryError(f"Unsupported tracked entry mode/type: {mode}/{kind}")
            except OSError as exc:
                raise RecoveryError(f"Cannot read restored entry {relative!r}: {exc}") from exc
            actual_oid = blob_hash(data, algorithm)
            if actual_oid != oid:
                raise RecoveryError(f"Restored blob mismatch at {relative!r}: {actual_oid} != {oid}")
            content_sha256 = sha256(data)
            readme_candidates[relative] = content_sha256
            record = {
                "path": relative, "mode": mode, "object": oid,
                "sha256": content_sha256, "bytes": len(data),
            }
        digest.update(json.dumps(record, sort_keys=True, ensure_ascii=True).encode("ascii") + b"\n")
    return {
        "object_format": algorithm,
        "counts": counts,
        "tracked_entries": sum(counts.values()),
        "verified_blobs": sum(counts.values()) - counts["gitlinks"],
        "materialized_entries_sha256": digest.hexdigest(),
        "gitlinks": gitlinks,
        "readme_candidates": readme_candidates,
    }


def object_inodes(objects_dir: Path) -> set[tuple[int, int]]:
    if objects_dir.is_symlink() or not objects_dir.is_dir():
        raise RecoveryError("Clone object directory is absent or a symlink")
    alternate = objects_dir / "info" / "alternates"
    if alternate.exists() and alternate.read_bytes().strip():
        raise RecoveryError("Recovered clone uses an alternate object store")
    result: set[tuple[int, int]] = set()
    for directory, dirs, files in os.walk(objects_dir, followlinks=False):
        dirs.sort()
        for name in dirs + files:
            path = Path(directory) / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise RecoveryError("Recovered clone object store contains a symlink")
            if stat.S_ISREG(info.st_mode):
                result.add((info.st_dev, info.st_ino))
    return result


def recover(repo: Path, manifest: dict[str, Any], work_parent: Path | None = None) -> dict[str, Any]:
    git = Git()
    report: dict[str, Any] = {
        "schema_version": 1,
        "scope": "P001 source recovery only; no submodule or runtime qualification",
        "result": "FAIL",
        "snapshots": [],
        "commands": git.transcript,
    }
    work: Path | None = None
    source_before: bytes | None = None
    try:
        repo = repo.resolve(strict=True)
        git.run(repo, "rev-parse", "--is-inside-work-tree")
        source_head = git.run(repo, "rev-parse", "HEAD").decode().strip()
        source_before = git.run(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        report["source"] = {
            "head": source_head,
            "working_tree_clean": not bool(source_before),
            "working_tree_status": source_before.decode("utf-8", "replace").split("\x00")[:-1],
            "policy": "Read committed objects only; local edits and untracked files are excluded",
            "git_version": git.run(None, "--version").decode().strip(),
        }
        if work_parent is not None:
            work_parent = work_parent.resolve(strict=True)
            if not work_parent.is_dir():
                raise RecoveryError("--work-dir must be an existing temporary parent directory")
            if work_parent == repo or repo in work_parent.parents:
                raise RecoveryError("--work-dir must be outside the source worktree")
        work = Path(tempfile.mkdtemp(prefix="p001-recovery-", dir=work_parent))
        report["temporary_workspaces_retained"] = work_parent is not None
        if work_parent is not None:
            report["workspace"] = str(work)
        seen_inodes: set[tuple[int, int]] = set()
        common_dir = git.run(repo, "rev-parse", "--git-common-dir").decode().strip()
        source_objects = (repo / common_dir / "objects").resolve()
        # Sources may use alternates; isolation is asserted on new clones.  Do
        # not traverse source alternates or change its configuration.
        if source_objects.is_dir():
            for directory, _, files in os.walk(source_objects, followlinks=False):
                for name in files:
                    info = (Path(directory) / name).lstat()
                    if stat.S_ISREG(info.st_mode):
                        seen_inodes.add((info.st_dev, info.st_ino))
        for label in ("baseline", "integration"):
            expected = manifest[label]
            commit, tree = expected["commit"], expected["tree"]
            if git.run(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip() != commit:
                raise RecoveryError(f"{label} commit does not resolve exactly")
            actual_tree = git.run(repo, "rev-parse", f"{commit}^{{tree}}").decode().strip()
            if actual_tree != tree:
                raise RecoveryError(f"{label} tree mismatch: {actual_tree} != {tree}")
            destination = work / label
            git.run(
                None, "clone", "--no-local", "--no-hardlinks", "--no-checkout",
                "--no-recurse-submodules", "--config", "core.hooksPath=" + os.devnull,
                "--config", "core.autocrlf=false", "--config", "core.symlinks=true",
                "--config", "core.filemode=true", "--", str(repo), str(destination),
            )
            inodes = object_inodes(destination / ".git" / "objects")
            if seen_inodes.intersection(inodes):
                raise RecoveryError(f"{label} shares hardlinked Git objects with another repository")
            seen_inodes.update(inodes)
            git.run(destination, "checkout", "--detach", commit)
            actual_commit = git.run(destination, "rev-parse", "HEAD").decode().strip()
            recovered_tree = git.run(destination, "rev-parse", "HEAD^{tree}").decode().strip()
            if actual_commit != commit or recovered_tree != tree:
                raise RecoveryError(f"{label} restored revision differs from manifest")
            verified = materialization(git, destination, commit)
            readme = expected["readme"]
            readme_sha256 = verified.pop("readme_candidates").get(readme["path"])
            if readme_sha256 != readme["sha256"]:
                raise RecoveryError(f"{label} restored README checksum mismatch")
            final_status = git.run(destination, "status", "--porcelain=v1", "-z", "--untracked-files=all")
            if final_status:
                raise RecoveryError(f"{label} recovered worktree is not clean")
            report["snapshots"].append({
                "label": label, "result": "PASS", "commit": commit, "tree": tree,
                "readme": {**readme, "verified_sha256": readme_sha256},
                "working_tree_clean": True, "independent_object_store": True,
                **verified,
            })
        source_after = git.run(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        final_head = git.run(repo, "rev-parse", "HEAD").decode().strip()
        unchanged = source_before == source_after and final_head == source_head
        report["source"]["unchanged_after_recovery"] = unchanged
        if not unchanged:
            raise RecoveryError("Source HEAD or worktree status changed during recovery")
        report["result"] = "PASS"
    except (RecoveryError, OSError, KeyError, ValueError) as exc:
        report["error"] = str(exc)
    finally:
        if work is not None and work_parent is None:
            shutil.rmtree(work)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path,
                        help="existing parent outside source; retain isolated checkouts here")
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        report = recover(args.repo, manifest, args.work_dir)
    except RecoveryError as exc:
        report = {"schema_version": 1, "result": "FAIL", "error": str(exc), "commands": []}
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"FAIL: could not write recovery evidence: {exc}", file=sys.stderr)
        return 1
    print(f"P001 recovery: {report['result']}; evidence: {args.output}")
    if report["result"] != "PASS":
        print(report.get("error", "Recovery failed"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
