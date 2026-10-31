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
from check_submodules import canonical_url, gitlinks, safe_url


def working_modules(root: Path) -> dict[str, str]:
    config = inventory.git(root, "config", "--null", "--file", "-",
                           "--get-regexp", r"^submodule\..*\.(path|url)$",
                           input_bytes=(root / ".gitmodules").read_bytes())
    fields: dict[str, dict[str, str]] = {}
    for record in config.split(b"\x00"):
        if not record:
            continue
        key, value = record.split(b"\n", 1)
        key = key.decode()
        name, field = key[len("submodule."):].rsplit(".", 1)
        fields.setdefault(name, {})[field] = value.decode()
    if any(set(item) != {"path", "url"} for item in fields.values()):
        raise ValueError("incomplete root .gitmodules declaration")
    result = {item["path"]: item["url"] for item in fields.values()}
    if len(result) != len(fields):
        raise ValueError("duplicate root .gitmodules path")
    return result


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
    return {"schema_version": 1, "phase": "P002",
            "purpose": "Complete reproducible dependency lock; original P001 pins and trees are unchanged",
            "baseline_implementation": "4707a919ef304945f7685390a68429242657eb54",
            "provenance_report": "docs/compat/logic-pro/evidence/P001/source-retrieval.json",
            "root_origin": "https://github.com/boop-bip80/MAC-OS-EMULATION.git",
            "expected_direct_gitlinks": 149, "expected_recursive_gitlinks": 160,
            "submodules": submodules}


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
