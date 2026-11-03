#!/usr/bin/env python3
"""Prove that a P004 evidence-publication commit changed documentation only.

The installed Darling and compatibility CI run at the exact tested implementation
commit A. Independent evidence is subsequently published at descendant commit B.
This verifier rules out any code, CI, pinned dependency, toolchain or test changes
between A and B, without treating documentation publication as a new build pass.

PASS here means source equivalence only; it NEVER accepts P004 or any predecessor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


class ProofError(ValueError):
    pass


P004_EVIDENCE_PREFIX = "docs/compat/logic-pro/evidence/P004/"
TESTED_SOURCE_PATH = P004_EVIDENCE_PREFIX + "tested-source.json"
MAX_DOCUMENT_BYTES = 2_000_000
MAX_DOCUMENT_CHANGES = 64
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
JSON_FILENAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.json\Z")


def git(repo: Path, *args: str, accepted=(0,)) -> tuple[int, bytes]:
    """Git reads with no caller-supplied configuration, shell or source filters."""
    env = {key: val for key, val in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "file",
    })
    command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
               "-c", "core.hooksPath=" + os.devnull, "-C", str(repo), *args]
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             check=False, timeout=60, env=env)
    if process.returncode not in accepted:
        message = process.stderr.decode("utf-8", "replace")[:400]
        raise ProofError(f"git {args[0]} exit {process.returncode}: {message}")
    return process.returncode, process.stdout


def require_commit(repo: Path, value: str) -> str:
    if not isinstance(value, str) or COMMIT_RE.fullmatch(value) is None:
        raise ProofError("tested and publication commits must be exact lowercase 40-hex SHA-1 identities")
    _, payload = git(repo, "rev-parse", "--verify", "--end-of-options", value + "^{commit}")
    actual = payload.decode("ascii").strip()
    if actual != value:
        raise ProofError("a supplied SHA does not resolve to the exact commit")
    return actual


def tree_entries(repo: Path, commit: str) -> dict[bytes, tuple[str, str, str]]:
    """Read Git tree objects, including gitlink modes, without checking out files."""
    _, data = git(repo, "ls-tree", "--full-tree", "-r", "-z", commit)
    entries: dict[bytes, tuple[str, str, str]] = {}
    for raw in data.split(b"\0"):
        if not raw:
            continue
        try:
            fields, path = raw.split(b"\t", 1)
            mode, kind, oid = fields.decode("ascii").split(" ")
        except (UnicodeError, ValueError) as exc:
            raise ProofError("invalid or unparseable git tree entry") from exc
        if (not path or path.startswith(b"/") or b"\0" in path
                or path in entries or b"/../" in path or path.startswith(b"../")):
            raise ProofError("ambiguous or unsafe git tree path")
        if mode not in {"100644", "100755", "120000", "160000"}:
            raise ProofError("unsupported git tree entry mode")
        if kind not in {"blob", "commit"} or re.fullmatch(r"[0-9a-f]{40}", oid) is None:
            raise ProofError("invalid git tree entry type or object identity")
        if (mode == "160000") != (kind == "commit"):
            raise ProofError("gitlink mode/type disagreement")
        entries[path] = (mode, kind, oid)
    if not entries:
        raise ProofError("source tree is empty")
    return entries


def allowed_documentation_path(path: bytes) -> bool:
    if path == b"README.md":
        return True
    prefix = P004_EVIDENCE_PREFIX.encode("ascii")
    if not path.startswith(prefix):
        return False
    name = path[len(prefix):]
    if not name or b"/" in name:
        return False
    try:
        decoded = name.decode("ascii")
    except UnicodeDecodeError:
        return False
    return JSON_FILENAME_RE.fullmatch(decoded) is not None


def strict_json(data: bytes) -> dict:
    try:
        text = data.decode("utf-8")
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ProofError(f"duplicate JSON key {key!r}")
                result[key] = value
            return result
        result = json.loads(text, object_pairs_hook=unique_pairs)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProofError(f"invalid UTF-8 JSON documentation: {exc}") from exc
    if not isinstance(result, dict):
        raise ProofError("evidence JSON must have a top-level object")
    return result


def read_document(repo: Path, path: bytes, entry: tuple[str, str, str]) -> tuple[dict, bytes]:
    mode, kind, oid = entry
    if mode != "100644" or kind != "blob":
        raise ProofError("documentation may only be an ordinary nonexecutable regular Git blob")
    _, data = git(repo, "cat-file", "blob", oid)
    if len(data) > MAX_DOCUMENT_BYTES:
        raise ProofError("documentation file exceeds the two-megabyte review limit")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProofError("documentation is not valid UTF-8") from exc
    if b"\0" in data:
        raise ProofError("documentation contains a NUL byte")
    parsed = strict_json(data) if path.endswith(b".json") else {}
    return parsed, data


def protected_manifest_digest(entries: dict[bytes, tuple[str, str, str]]) -> str:
    digest = hashlib.sha256()
    for path in sorted(entries):
        if allowed_documentation_path(path):
            continue
        mode, kind, oid = entries[path]
        digest.update(path + b"\0" + mode.encode("ascii") + b"\0"
                      + kind.encode("ascii") + b"\0" + oid.encode("ascii") + b"\n")
    return digest.hexdigest()


def prove(repo: Path, tested: str, publication: str) -> dict:
    """Return an independently reproducible report; never mark phases accepted."""
    report = {
        "schema_version": 1, "phase": "P004", "status": "FAIL",
        "scope": "Git source-tree equivalence across documentation-only publication; not phase acceptance",
        "tested_commit": tested, "publication_commit": publication,
        "tested_tree_sha": None, "publication_tree_sha": None,
        "ancestor_verified": False, "code_tree_identical": False,
        "code_tree_manifest_sha256": None,
        "protected_entries": 0, "change_count": 0,
        "allowed_documentation_changes": [], "failures": [],
    }
    try:
        tested = require_commit(repo, tested)
        publication = require_commit(repo, publication)
        if tested == publication:
            raise ProofError("publication must be a distinct descendant containing new reviewed evidence")
        code, _ = git(repo, "merge-base", "--is-ancestor", tested, publication, accepted=(0, 1))
        if code != 0:
            raise ProofError("tested implementation is not an ancestor of publication")
        report["ancestor_verified"] = True

        _, a_tree_sha = git(repo, "rev-parse", "--verify", tested + "^{tree}")
        _, b_tree_sha = git(repo, "rev-parse", "--verify", publication + "^{tree}")
        report["tested_tree_sha"] = a_tree_sha.decode("ascii").strip()
        report["publication_tree_sha"] = b_tree_sha.decode("ascii").strip()
        a = tree_entries(repo, tested)
        b = tree_entries(repo, publication)
        protected_a = {path: entry for path, entry in a.items() if not allowed_documentation_path(path)}
        protected_b = {path: entry for path, entry in b.items() if not allowed_documentation_path(path)}
        report["protected_entries"] = len(protected_a)
        report["code_tree_manifest_sha256"] = protected_manifest_digest(a)
        report["code_tree_identical"] = protected_a == protected_b
        if not report["code_tree_identical"]:
            report["failures"].append("code/source, workflow, test, toolchain, or pinned dependency differs")

        changes = sorted(path for path in a.keys() | b.keys() if a.get(path) != b.get(path))
        report["change_count"] = len(changes)
        _, raw_paths = git(repo, "diff-tree", "--no-commit-id", "--no-renames",
                           "-r", "--name-only", "-z", tested, publication)
        diff_paths = {path for path in raw_paths.split(b"\0") if path}
        if diff_paths != set(changes):
            report["failures"].append("independent git diff-tree disagrees with tree-object comparison")
        if not changes:
            report["failures"].append("no evidence-publication change exists")
        if len(changes) > MAX_DOCUMENT_CHANGES:
            report["failures"].append("too many documentation changes for bounded review")

        for path in changes:
            name = path.decode("utf-8", "backslashreplace")
            if not allowed_documentation_path(path):
                report["failures"].append(f"unapproved changed path: {name}")
                continue
            old, new = a.get(path), b.get(path)
            if old is not None and new is None:
                report["failures"].append(f"document deletion forbidden: {name}")
                continue
            if path == b"README.md" and old is None:
                report["failures"].append("README cannot be newly created as a substitute for the accepted plan")
                continue
            if new is None:
                report["failures"].append(f"missing new documentation entry: {name}")
                continue
            if old is not None and old[:2] != ("100644", "blob"):
                report["failures"].append(f"original documentation mode/type invalid: {name}")
                continue
            try:
                _, data = read_document(repo, path, new)
            except ProofError as exc:
                report["failures"].append(f"{name}: {exc}")
                continue
            change = "added" if old is None else "modified"
            report["allowed_documentation_changes"].append({
                "path": name, "change": change, "mode": new[0],
                "blob_sha1": new[2], "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            })

        # The publication itself must bind to the exact tested candidate, not
        # an invented baseline. This file has a deliberately tiny closed schema.
        entry = b.get(TESTED_SOURCE_PATH.encode("ascii"))
        if entry is None:
            report["failures"].append("missing P004/tested-source.json binding")
        else:
            try:
                parsed, _ = read_document(repo, TESTED_SOURCE_PATH.encode("ascii"), entry)
                if (set(parsed) != {"schema_version", "phase", "tested_sha"}
                        or type(parsed["schema_version"]) is not int or parsed["schema_version"] != 1
                        or parsed["phase"] != "P004" or parsed["tested_sha"] != tested):
                    report["failures"].append("tested-source.json does not bind the exact tested implementation")
            except (ProofError, KeyError, TypeError) as exc:
                report["failures"].append(f"invalid tested-source.json: {exc}")

        if not report["failures"]:
            report["status"] = "PASS"
    except (ProofError, OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        report["failures"].append(str(exc))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--tested", required=True, help="exact implementation commit SHA")
    parser.add_argument("--publication", required=True, help="descendant evidence-publication commit SHA")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = prove(args.repo.resolve(), args.tested, args.publication)
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        print(f"source equivalence report output failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": report["status"], "tested": report["tested_commit"],
                      "publication": report["publication_commit"],
                      "changed": report["change_count"], "failures": report["failures"]},
                     sort_keys=True), flush=True)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
