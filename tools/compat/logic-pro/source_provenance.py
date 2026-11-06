#!/usr/bin/env python3
"""Load the explicitly reviewed P002 source update without replacing P001 history.

These constants identify already archived evidence, not a moving upstream ref.
Changing them requires a new source review. This module establishes source
identity only; it does not establish ordinary-clone or phase acceptance.
"""

from __future__ import annotations

import hashlib
import json
import lzma
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit


HISTORICAL_SOURCE_ANCHOR = "4707a919ef304945f7685390a68429242657eb54"
HISTORICAL_SOURCE_TREE = "8fb4a8c4b7855d2dec827a9e4d6499cb113b3776"
HISTORICAL_ACCEPTANCE_ANCHOR = "89c6c9d85aba6ed1662035e6366298c92ef9c970"
HISTORICAL_LOCK_SHA256 = "1540d2552f36bd5ed29a640dbe12dfe0e37c618c02ed7fd1d59d4264a8ba5f1b"
HISTORICAL_REPORT = "docs/compat/logic-pro/evidence/P001/source-retrieval.json"
HISTORICAL_REPORT_SHA256 = "cb1c652b6563f7d60225a5faaba605afa3acfb4628a579b14a98b2957385a59d"
CURRENT_SOURCE_ANCHOR = "c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a"
CURRENT_SOURCE_TREE = "8f3700d4cf59d47449ab7d8243d0d3599a32a6ac"
EVIDENCE_DIRECTORY = "docs/compat/logic-pro/evidence/P002/requalification-20261105"
CURRENT_REPORT = EVIDENCE_DIRECTORY + "/source-inspection-c7ef7fe4.json.xz"
CURRENT_ARCHIVE_SHA256 = "438897a514b67a3b104fbdb963c5a4d453c07c39c42f01d2d3d22ced2347022d"
CURRENT_REPORT_SHA256 = "ca8cdbf9d9fdc32eac96294d78169eb0250d123f254874e32a7d8adb81a763ef"
CURRENT_MANIFEST = EVIDENCE_DIRECTORY + "/source-inspection-c7ef7fe4.manifest.json"
CURRENT_MANIFEST_SHA256 = "593b465aadebd99c3fc24c13f5ca7ddf09e393ac4e91a330443ca6f9d51d9a67"
SOURCE_REVIEW = EVIDENCE_DIRECTORY + "/upstream-pin-review.json"
SOURCE_REVIEW_SHA256 = "1b58d81925a15918f1dec4cb8e590e1fcd5fceb2731b5d253a9b83b78ba15457"
SHA1 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def _read_verified(root: Path, relative: str, digest: str) -> bytes:
    data = (root / relative).read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f"source provenance digest differs: {relative}")
    return data


def _public_url(value: str) -> str:
    if (not isinstance(value, str) or not value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError("source provenance URL must be a string")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.netloc != "github.com"
            or parsed.query or parsed.fragment
            or re.fullmatch(r"/[A-Za-z0-9-]+/[A-Za-z0-9_.-]+/?", parsed.path) is None
            or parsed.path.strip("/").split("/")[-1] in (".", "..", ".git")):
        raise ValueError("source provenance requires a public GitHub repository URL")
    return value.rstrip("/").removesuffix(".git")


def _records(evidence: dict, anchor: str, tree: str) -> dict[str, dict]:
    source = evidence.get("source", {})
    if (evidence.get("result") != "PASS" or evidence.get("recursive_content_complete") is not True
            or evidence.get("recursive_submodules_observed") != 160 or evidence.get("failures") != []
            or source.get("commit") != anchor or source.get("tree") != tree
            or source.get("parent_source_unchanged") is not True):
        raise ValueError("source provenance anchor or completed retrieval differs")
    rows = evidence.get("submodules")
    if not isinstance(rows, list) or len(rows) != 160:
        raise ValueError("source provenance requires all 160 recursive gitlinks")
    records = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid source provenance record")
        path, parent = row.get("path"), row.get("parent_path")
        if (not isinstance(path, str) or not path or path in records or path.startswith("/")
                or "\\" in path or any(ord(char) < 32 or ord(char) == 127 for char in path)
                or any(part in (".", "..", ".git") for part in PurePosixPath(path).parts)
                or str(PurePosixPath(path)) != path or not isinstance(parent, str)
                or row.get("status") != "PASS" or row.get("retrieval") != "FETCHED_EXACT_PIN"
                or not isinstance(row.get("commit"), str) or not SHA1.fullmatch(row["commit"])
                or not isinstance(row.get("tree"), str) or not SHA1.fullmatch(row["tree"])):
            raise ValueError("invalid, duplicate or incomplete source provenance record")
        records[path] = {"path": path, "parent_path": parent, "commit": row["commit"],
                         "tree": row["tree"], "resolved_url": _public_url(row.get("acquisition_resolved_url"))}
    if sum(row["parent_path"] == "." for row in records.values()) != 149:
        raise ValueError("source provenance requires 149 direct and 11 nested gitlinks")
    for path, row in records.items():
        ancestors = [candidate for candidate in records if path.startswith(candidate + "/")]
        expected_parent = max(ancestors, key=len) if ancestors else "."
        if row["parent_path"] != expected_parent:
            raise ValueError(f"source provenance parent differs: {path}")
    return records


def validate_reviewed_graphs(historical: dict, current: dict, review: dict) -> tuple[dict, dict]:
    """Require the reviewed changes to equal the complete old/new graph delta.

    Callers needing the trusted evidence must use ``load_reviewed_source``;
    this separate semantic check also permits focused adversarial fixtures.
    """
    old = _records(historical, HISTORICAL_SOURCE_ANCHOR, HISTORICAL_SOURCE_TREE)
    new = _records(current, CURRENT_SOURCE_ANCHOR, CURRENT_SOURCE_TREE)
    if set(old) != set(new):
        raise ValueError("reviewed source update must preserve the dependency paths")
    if (review.get("schema_version") != 1 or review.get("phase") != "P002"
            or review.get("status") != "SOURCE_REVIEW_ONLY_NOT_PHASE_ACCEPTANCE"
            or review.get("source_anchor") != CURRENT_SOURCE_ANCHOR
            or review.get("source_tree") != CURRENT_SOURCE_TREE
            or review.get("historical_lock_source") != HISTORICAL_ACCEPTANCE_ANCHOR
            or review.get("historical_lock_sha256") != HISTORICAL_LOCK_SHA256
            or review.get("source_retrieval_sha256") != CURRENT_REPORT_SHA256
            or review.get("source_retrieval_result") != "PASS"
            or review.get("source_retrieval_recursive_count") != 160
            or review.get("recursive_pin_changes") != 14 or review.get("direct_pin_changes") != 13):
        raise ValueError("reviewed source update anchors or counts differ")
    changes = {path for path in old if old[path] != new[path]}
    rows = review.get("records")
    if not isinstance(rows, list) or len(rows) != 14 or len(changes) != 14:
        raise ValueError("reviewed source update must contain exactly 14 changes")
    reviewed = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("path") not in changes or row["path"] in reviewed:
            raise ValueError("omitted, extra, duplicate or stale reviewed source change")
        path = row["path"]
        before, after = old[path], new[path]
        if (before["parent_path"] != after["parent_path"] or before["resolved_url"] != after["resolved_url"]
                or row.get("parent_path") != before["parent_path"]
                or _public_url(row.get("public_url")) != before["resolved_url"]
                or row.get("old_commit") != before["commit"] or row.get("old_tree") != before["tree"]
                or row.get("new_commit") != after["commit"] or row.get("new_tree") != after["tree"]
                or not isinstance(row.get("diff_sha256"), str) or not SHA256.fullmatch(row["diff_sha256"])
                or type(row.get("diff_bytes")) is not int or row["diff_bytes"] <= 0
                or not row.get("review_summary") or not row.get("scope_verdict")):
            raise ValueError(f"reviewed source change differs from exact old/new graph: {path}")
        reviewed.add(path)
    if reviewed != changes or sum(new[path]["parent_path"] == "." for path in changes) != 13:
        raise ValueError("reviewed source changes do not cover the complete graph delta")
    return old, new


def load_reviewed_source(root: Path) -> dict:
    """Load frozen historical/current reports and their exact reviewed graph.

    ``historical_source_anchor`` is the original retrieval's root; the later
    ``historical_acceptance_anchor`` identifies the preserved accepted lock.
    Record mappings use full repository paths and canonical acquisition URLs.
    """
    historical = json.loads(_read_verified(root, HISTORICAL_REPORT, HISTORICAL_REPORT_SHA256))
    archive = _read_verified(root, CURRENT_REPORT, CURRENT_ARCHIVE_SHA256)
    manifest = json.loads(_read_verified(root, CURRENT_MANIFEST, CURRENT_MANIFEST_SHA256))
    raw = lzma.decompress(archive)
    if (hashlib.sha256(raw).hexdigest() != CURRENT_REPORT_SHA256
            or manifest.get("archive_sha256") != CURRENT_ARCHIVE_SHA256
            or manifest.get("raw_sha256") != CURRENT_REPORT_SHA256
            or manifest.get("archive_bytes") != len(archive) or manifest.get("raw_bytes") != len(raw)
            or manifest.get("source_commit") != CURRENT_SOURCE_ANCHOR
            or manifest.get("recursive_gitlinks") != 160 or manifest.get("result") != "PASS"):
        raise ValueError("current source inspection archive manifest differs")
    current = json.loads(raw)
    review = json.loads(_read_verified(root, SOURCE_REVIEW, SOURCE_REVIEW_SHA256))
    historical_records, current_records = validate_reviewed_graphs(historical, current, review)
    return {"historical_source_anchor": HISTORICAL_SOURCE_ANCHOR,
            "historical_acceptance_anchor": HISTORICAL_ACCEPTANCE_ANCHOR,
            "current_source_anchor": CURRENT_SOURCE_ANCHOR,
            "historical_evidence": historical, "current_evidence": current,
            "historical_records": historical_records, "current_records": current_records, "review": review}


load_source_provenance = load_reviewed_source
