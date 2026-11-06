#!/usr/bin/env python3
"""Read-only, bounded acceptance-ledger audit; this does not run phase tests."""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
from pathlib import Path
import posixpath
import re
import subprocess

HISTORICAL = "89c6c9d85aba6ed1662035e6366298c92ef9c970"
STARTING = "c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a"
TESTED = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"
EVIDENCE = "docs/compat/logic-pro/evidence/P002/requalification-20261105"
TEST_PATHS = ("tests/compat/logic-pro/baseline", "tests/compat/logic-pro/submodules")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--publication-ref", required=True)
    parser.add_argument("--draft-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def git(*parts):
        return subprocess.check_output(["git", "-C", str(args.repo), *parts])

    def blob(revision, path):
        return git("show", f"{revision}:{path}")

    def read_current(path):
        if args.draft_root:
            return (args.draft_root / path).read_bytes()
        return blob(args.publication_ref, path)

    files = set(git("ls-tree", "-r", "--name-only", args.publication_ref).decode().splitlines())
    if args.draft_root:
        files.update(git("ls-files", "--cached", "--others", "--exclude-standard").decode().splitlines())

    def exists(path):
        if args.draft_root:
            return (args.draft_root / path).exists()
        return path in files or any(p.startswith(path.rstrip("/") + "/") for p in files)

    def gate_records(text):
        result = {}
        for phase, next_phase in (("P001", "P002"), ("P002", "P003")):
            section = text.split(f"### {phase} —", 1)[1].split(f"### {next_phase} —", 1)[0]
            gates = section.split("**Verification and pass gate:**", 1)[1].split("**Required evidence:**", 1)[0]
            result[phase] = [
                {"checked": line.startswith("- [x]"),
                 "original_requirement": re.sub(r"^- \[[ x]\] ", "", line).split(" — ")[0].rstrip(".")}
                for line in gates.splitlines() if line.startswith("- [")
            ]
        return result

    def tests(revision):
        records, skipped = {}, []
        paths = git("ls-tree", "-r", "--name-only", revision, "--", *TEST_PATHS).decode().splitlines()
        for path in paths:
            if not path.endswith(".py"):
                continue
            module = ast.parse(blob(revision, path))
            for cls in module.body:
                if not isinstance(cls, ast.ClassDef):
                    continue
                for node in cls.body:
                    if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                        continue
                    name = f"{path}::{cls.name}::{node.name}"
                    records[name] = ast.dump(node, include_attributes=False)
                    for decorator in node.decorator_list:
                        value = ast.unparse(decorator)
                        if "skip" in value.lower() or "expectedfailure" in value.lower():
                            skipped.append({"test": name, "decorator": value})
        return records, skipped

    current_readme = read_current("README.md").decode()
    current_gates = gate_records(current_readme)
    original_requirements = lambda records: {p: [g["original_requirement"] for g in v] for p, v in records.items()}
    gate_comparisons = []
    for revision in (HISTORICAL, STARTING, TESTED, args.publication_ref):
        records = gate_records(blob(revision, "README.md").decode())
        gate_comparisons.append({"revision": revision, "gates": records,
                                 "same_original_requirements_as_current": original_requirements(records) == original_requirements(current_gates)})

    snapshots = {}
    links = []
    snapshot_paths = ["README.md", f"{EVIDENCE}/README.md", f"{EVIDENCE}/wave-ledger.json"]
    if exists(f"{EVIDENCE}/ordered-acceptance.json"):
        snapshot_paths.append(f"{EVIDENCE}/ordered-acceptance.json")
    for path in snapshot_paths:
        raw = read_current(path)
        snapshots[path] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if not path.endswith(".md"):
            continue
        text = raw.decode()
        if path == "README.md":
            text = text[:text.index("### P003 —")]
        local = []
        for target in re.findall(r"\]\(([^)]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            local.append(posixpath.normpath(posixpath.join(posixpath.dirname(path), target)))
        links.append({"path": path, "scope": "before P003 detail" if path == "README.md" else "whole file",
                      "local_links": len(local), "unique_local_links": len(set(local)),
                      "missing": sorted({p for p in local if not exists(p)})})

    test_inventory = {}
    for revision in (STARTING, TESTED, args.publication_ref):
        methods, skipped = tests(revision)
        test_inventory[revision] = {"methods": methods, "skip_expected_failure_decorators": skipped}
    before = test_inventory[STARTING]["methods"]
    after = test_inventory[TESTED]["methods"]
    test_comparison = {
        "counts": {r: len(v["methods"]) for r, v in test_inventory.items()},
        "removed_or_renamed": sorted(before.keys() - after.keys()),
        "added_or_renamed": sorted(after.keys() - before.keys()),
        "changed_existing_methods": sorted(n for n in before.keys() & after.keys() if before[n] != after[n]),
        "skip_expected_failure_decorators": {r: v["skip_expected_failure_decorators"] for r, v in test_inventory.items()},
        "post_tested_test_diff": git("diff", "--name-only", TESTED, args.publication_ref, "--", "tests/compat/logic-pro").decode().splitlines(),
    }

    changed = git("diff", "--name-only", TESTED, args.publication_ref).decode().splitlines()
    disallowed = [p for p in changed if p != "README.md" and not p.startswith(EVIDENCE + "/")]
    draft_disallowed = None
    if args.draft_root:
        draft_changed = subprocess.check_output(["git", "-C", str(args.draft_root), "diff", "--name-only", TESTED]).decode().splitlines()
        draft_disallowed = [p for p in draft_changed if p != "README.md" and not p.startswith(EVIDENCE + "/")]
    def mandatory_contract(text):
        return text.split("## Mandatory instructions for every agent and contributor", 1)[1].split("## Source ownership and implementation map", 1)[0]
    policy_comparisons = {revision: mandatory_contract(blob(revision, "README.md").decode()) == mandatory_contract(current_readme)
                          for revision in (STARTING, TESTED, args.publication_ref)}
    artifact_changes = git("diff", "--name-status", STARTING, args.publication_ref, "--",
                           "docs/compat/logic-pro/evidence/P001", "docs/compat/logic-pro/evidence/P002").decode().splitlines()
    historical_artifact_changes = [p for p in artifact_changes if not p.startswith("A\t" + EVIDENCE + "/")]
    citations_path = "tools/compat/logic-pro/classifications.json"
    original_citations = json.loads(blob(STARTING, citations_path))["evidence"]
    citation_comparisons = {revision: json.loads(blob(revision, citations_path))["evidence"] == original_citations
                            for revision in (TESTED, args.publication_ref)}
    ledger = json.loads(read_current(f"{EVIDENCE}/wave-ledger.json"))
    assignments = [a for w in ledger["waves"] for a in w.get("assignments", [])]
    agents = [a["agent"] for a in assignments]
    assignment_evidence = [{"agent": a["agent"], "path": a["evidence"],
                            "exists": exists(posixpath.normpath(EVIDENCE + "/" + a["evidence"]))}
                           for a in assignments if a.get("evidence")]
    decisions = {}
    for phase, path in (("P001", "wave4-p001/acceptance.json"), ("P002", "wave5-replay/acceptance.json")):
        full_path = f"{EVIDENCE}/{path}"
        if exists(full_path):
            raw = read_current(full_path)
            decisions[phase] = {"path": full_path, "sha256": hashlib.sha256(raw).hexdigest(), "record": json.loads(raw)}
    ordered = None
    if "P002" in decisions:
        p1, p2 = (decisions[p]["record"] for p in ("P001", "P002"))
        time_value = lambda value: datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        source_path = p2["source_approval"]["record"]
        source_bytes = read_current(source_path)
        source_record = json.loads(source_bytes)
        ordered = {"same_tested_implementation": p1["implementation_commit"] == p2["implementation_commit"] == TESTED,
                   "same_tested_tree": p1["implementation_tree"] == p2["implementation_tree"] == git("rev-parse", TESTED + "^{tree}").decode().strip(),
                   "P001_strictly_before_P002": time_value(p1["accepted_at_utc"]) < time_value(p2["accepted_at_utc"]),
                   "both_accepted_original_four_gates": all(p["decision"] == "ACCEPTED" and p["gates"] == {f"G{i}": "PASS" for i in range(1, 5)} for p in (p1, p2)),
                   "both_reviewers_are_production_non_authors": all(p["reviewer_authored_production_changes"] is False for p in (p1, p2)),
                   "distinct_phase_reviewers": p1["reviewer"] != p2["reviewer"],
                   "predecessor_hash_matches_actual_P001_record": p2["P001_ordered_predecessor"]["record_sha256"] == decisions["P001"]["sha256"],
                   "source_approval_hash_matches_actual_record": p2["source_approval"]["record_sha256"] == hashlib.sha256(source_bytes).hexdigest(),
                   "source_approval_at_same_tested_source": source_record["verdict"] == "SOURCE_APPROVED" and source_record["tested_source"] == TESTED,
                   "source_approval_precedes_P002": time_value(source_record["reviewed_at"]) < time_value(p2["accepted_at_utc"]),
                   "no_later_phase_or_runtime_acceptance": all(p2[key] is False for key in ("P003_accepted", "P004_accepted", "later_phases_accepted", "runtime_executed", "logic_pro_executed"))}

    report = {
        "schema_version": 1, "reviewer": "/root/wave5_ledger_consistency",
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "published_revision_inspected": args.publication_ref,
        "published_tree_inspected": git("rev-parse", args.publication_ref + "^{tree}").decode().strip(),
        "draft_root": str(args.draft_root) if args.draft_root else None,
        "tested_implementation": TESTED,
        "method": "Git object comparisons, AST test-method inventory, Markdown link resolution, direct JSON/README ledger inspection; no phase-suite rerun",
        "reviewed_live_file_snapshots": snapshots,
        "current_gate_records": current_gates,
        "original_gate_comparisons": gate_comparisons,
        "post_tested_changed_file_count": len(changed), "post_tested_changes_outside_readme_and_campaign_evidence": disallowed,
        "draft_changes_outside_readme_and_campaign_evidence": draft_disallowed,
        "mandatory_contract_retained": policy_comparisons,
        "AGENTS_unchanged_from_starting_source": blob(STARTING, "AGENTS.md") == read_current("AGENTS.md"),
        "preexisting_P001_P002_artifact_changes_since_starting_source": historical_artifact_changes,
        "immutable_historical_citation_records": {"count": len(original_citations), "retained": citation_comparisons},
        "test_retention": test_comparison, "relative_link_checks": links,
        "waves": {"count": len(ledger["waves"]), "states": [{"wave": w["wave"], "status": w["status"], "assignments": len(w.get("assignments", []))} for w in ledger["waves"]],
                  "assignments": len(agents), "distinct_agents": len(set(agents)), "agents": agents, "evidence_paths": assignment_evidence},
        "acceptance_records": decisions, "ordered_acceptance": ordered,
        "phase_index": [line for line in current_readme.splitlines() if re.match(r"\| \[P00[1-4]\]", line)],
        "dashboard": [line for line in current_readme.splitlines() if any(line.startswith("| " + s + " |") for s in ("Phases passed", "Current phase", "Actual Logic execution on this fork", "Last accepted P001/P002 verification", "Next required action"))],
        "publication_limit": "A working draft is not publication evidence. This record does not assert publication of this audit or later commits; root must confirm the final remote commit after integration.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "original_gate_requirements_retained": all(v["same_original_requirements_as_current"] for v in gate_comparisons),
                      "out_of_scope_production_changes": disallowed, "wave_count": len(ledger["waves"]), "assignments": len(agents), "distinct_agents": len(set(agents)),
                      "missing_links": [p for v in links for p in v["missing"]], "ordered_acceptance": ordered}))


if __name__ == "__main__":
    main()
