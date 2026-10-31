#!/usr/bin/env python3
"""Regenerate the P002 lock from immutable P001 exact-pin provenance.

The generator is intentionally conservative. It refuses any changed gitlink,
unproved acquisition URL, or unexpected nested dependency. Later pin changes
must first receive their own auditable source/provenance evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import inventory
import lfs_manifest
from check_submodules import SCHEMA, canonical_url, committed_modules, gitlinks, safe_url, validate_lock


def working_modules(root: Path) -> dict[str, str]:
    if (root / ".gitmodules").is_symlink() or (root / ".gitmodules").read_bytes() != inventory.git(root, "show", "HEAD:.gitmodules"):
        raise ValueError("lock generation requires the exact committed root .gitmodules")
    return committed_modules(root)


def generate(root: Path, evidence: dict) -> dict:
    if evidence.get("result") != "PASS" or evidence.get("recursive_content_complete") is not True:
        raise ValueError("P001 recursive retrieval evidence must be fully passed")
    records = evidence.get("submodules", [])
    if len(records) != 160 or sum(x["parent_path"] == "." for x in records) != 149:
        raise ValueError("expected the exact P001 149+11 dependency graph")
    declared = working_modules(root)
    pinned = gitlinks(root)
    direct = {x["path"]: x for x in records if x["parent_path"] == "."}
    if set(direct) != set(declared) or set(direct) != set(pinned):
        raise ValueError("current root paths differ from P001 evidence")
    for path, entry in direct.items():
        if pinned[path] != entry["commit"]:
            raise ValueError(f"pin changed without new source evidence: {path}")
        if canonical_url(declared[path]) != canonical_url(entry["acquisition_resolved_url"]):
            raise ValueError(f"unrepaired or unjustified root URL: {path}")
        safe_url(declared[path], allow_local=False)

    resolved_by_path = {".": "https://github.com/boop-bip80/MAC-OS-EMULATION.git"}
    submodules = []
    for record in sorted(records, key=lambda item: (item["path"].count("/"), item["path"])):
        path, parent = record["path"], record["parent_path"]
        if parent not in resolved_by_path:
            raise ValueError(f"missing nested parent: {path}")
        url = declared[path] if parent == "." else record["declared_url"]
        resolved = inventory.resolve_submodule_url(resolved_by_path[parent], url)
        observed = record["acquisition_resolved_url"]
        if canonical_url(resolved) != canonical_url(observed):
            raise ValueError(f"new URL resolves differently from recorded exact source: {path}")
        safe_url(resolved, allow_local=False)
        if record.get("status") != "PASS" or record.get("retrieval") != "FETCHED_EXACT_PIN":
            raise ValueError(f"source pin lacks successful retrieval: {path}")
        submodules.append({"path": path, "parent_path": parent, "declared_url": url,
                           "resolved_url": resolved, "commit": record["commit"],
                           "tree": record["tree"], "provenance": "P001 exact-pin hosted source retrieval"})
        resolved_by_path[path] = resolved
    provenance = json.loads((root / "docs/compat/logic-pro/lfs-provenance.json").read_text())
    repositories, objects = lfs_manifest.validate_manifest(provenance, submodules)
    lock = {"schema_version": SCHEMA, "phase": "P002",
            "purpose": "Complete reproducible Git and LFS dependency lock; original P001 pins and trees are unchanged",
            "baseline_implementation": "4707a919ef304945f7685390a68429242657eb54",
            "provenance_report": "docs/compat/logic-pro/evidence/P001/source-retrieval.json",
            "root_origin": "https://github.com/boop-bip80/MAC-OS-EMULATION.git",
            "root_gitmodules_blob_sha1": inventory.git(root, "rev-parse", "HEAD:.gitmodules").decode().strip(),
            "expected_direct_gitlinks": 149, "expected_recursive_gitlinks": 160,
            "expected_lfs_objects": len(objects), "lfs_repositories": repositories,
            "lfs_objects": objects, "submodules": submodules}
    validate_lock(lock, False)
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--evidence", type=Path, default=Path("docs/compat/logic-pro/evidence/P001/source-retrieval.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/compat/logic-pro/submodules.lock.json"))
    args = parser.parse_args()
    lock = generate(args.repo.resolve(), json.loads(args.evidence.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(f"Locked {lock['expected_direct_gitlinks']} direct and {len(lock['submodules']) - lock['expected_direct_gitlinks']} nested exact pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
