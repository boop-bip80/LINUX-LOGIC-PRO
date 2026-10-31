#!/usr/bin/env python3
"""Verify source-audit citations against committed Git objects, never runtime claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


class EvidenceError(ValueError):
    pass


def git(repo: Path, *args: str) -> bytes:
    env = os.environ.copy()
    for key in list(env):
        if key in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                   "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                   "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT"} or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            env.pop(key, None)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
                "GIT_ALLOW_PROTOCOL": "", "GIT_TERMINAL_PROMPT": "0"})
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
         "-c", "core.hooksPath=" + os.devnull, "-C", str(repo), *args],
        capture_output=True, timeout=30, check=False, env=env,
    )
    if result.returncode:
        raise EvidenceError(f"git {args[0]} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def safe_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\n" in value:
        raise EvidenceError("source path must be a nonempty single-line string")
    path = PurePosixPath(value)
    if path.is_absolute() or any(p in ("..", ".git") for p in path.parts) or str(path) != value:
        raise EvidenceError(f"unsafe or noncanonical source path: {value!r}")
    return value


def verify(repo: Path, manifest: dict, current_ref: str | None = None) -> dict:
    if not isinstance(manifest, dict):
        raise EvidenceError("classification manifest must be a JSON object")
    if manifest.get("schema_version") != 1:
        raise EvidenceError("unsupported classification schema_version")
    commit = manifest.get("inspected_commit", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise EvidenceError("inspected_commit must be a full SHA-1 commit ID")
    resolved = git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip()
    if resolved != commit:
        raise EvidenceError("inspected commit does not resolve exactly")
    current = None
    if current_ref is not None:
        current = git(repo, "rev-parse", "--verify", "--end-of-options", f"{current_ref}^{{commit}}").decode().strip()
    records = manifest.get("evidence")
    if not isinstance(records, list) or not records:
        raise EvidenceError("empty classification evidence cannot pass")
    cache: dict[str, tuple[str, bytes]] = {}
    seen: set[str] = set()
    checked = []
    failures = []
    for record in records:
        record_id = record.get("id") if isinstance(record, dict) else None
        try:
            if not isinstance(record_id, str) or not record_id or record_id in seen:
                raise EvidenceError("missing or duplicate evidence ID")
            seen.add(record_id)
            if record.get("observation") != "STATIC_SOURCE_INSPECTION":
                raise EvidenceError("classification must explicitly identify static source inspection")
            if not isinstance(record.get("category"), str) or not record["category"]:
                raise EvidenceError("missing category")
            path = safe_path(record.get("path"))
            start, end = record.get("line_start"), record.get("line_end")
            if type(start) is not int or type(end) is not int or not 1 <= start <= end:
                raise EvidenceError("invalid inclusive source line range")
            contains = record.get("contains")
            if not isinstance(contains, list) or not contains or any(not isinstance(s, str) or not s for s in contains):
                raise EvidenceError("contains must have at least one nonempty assertion")
            if path not in cache:
                obj = git(repo, "rev-parse", "--verify", f"{commit}:{path}").decode().strip()
                if git(repo, "cat-file", "-t", obj).strip() != b"blob":
                    raise EvidenceError("source evidence must refer to a blob")
                data = git(repo, "cat-file", "blob", obj)
                cache[path] = (obj, data)
            obj, data = cache[path]
            if obj != record.get("blob_sha1"):
                raise EvidenceError("source blob SHA-1 mismatch")
            lines = data.splitlines(keepends=True)
            if end > len(lines):
                raise EvidenceError("citation extends beyond source file")
            excerpt = b"".join(lines[start - 1:end])
            if hashlib.sha256(excerpt).hexdigest() != record.get("excerpt_sha256"):
                raise EvidenceError("source excerpt SHA-256 mismatch")
            if any(s.encode("utf-8") not in excerpt for s in contains):
                raise EvidenceError("required source text is missing from cited lines")
            if current is not None:
                now = git(repo, "rev-parse", "--verify", f"{current}:{path}").decode().strip()
                if now != obj:
                    raise EvidenceError("current source differs from the audited blob; re-audit required")
            checked.append({"id": record_id, "category": record["category"], "path": path,
                            "blob_sha1": obj, "line_start": start, "line_end": end,
                            "excerpt_sha256": record["excerpt_sha256"]})
        except (EvidenceError, UnicodeError, TypeError) as exc:
            failures.append({"id": record_id, "error": str(exc)})
    return {
        "schema_version": 1, "status": "PASS" if not failures else "FAIL",
        "scope": "Pinned source-citation integrity; no runtime execution or framework completeness claim.",
        "inspected_commit": commit, "current_commit": current,
        "checked_count": len(checked), "source_file_count": len(cache),
        "checked": checked, "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--current-ref")
    args = parser.parse_args(argv)
    try:
        result = verify(args.repo, json.loads(args.manifest.read_text()), args.current_ref)
    except (EvidenceError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result = {"schema_version": 1, "status": "FAIL", "failures": [{"error": str(exc)}]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"source classifications: {result['status']}; {result.get('checked_count', 0)} citations verified")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
