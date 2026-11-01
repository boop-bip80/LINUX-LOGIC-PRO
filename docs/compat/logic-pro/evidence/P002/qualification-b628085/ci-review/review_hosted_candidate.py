#!/usr/bin/env python3
"""Independent artifact review; no production gate imports or remote writes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

MERGE = "b628085a19bae2d467fd9549ec0767636423a90a"
HEAD = "da1000be001711f80d6880eed9eeca916f6d0a23"
TREE = "37761104d97e824a2567f91dff2dea391bb635dd"
BASE = "f7bd711013d3c41c3eee4ec76926bfe3a152cb46"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def zip_digests(z):
    result = {}
    for info in z.infolist():
        h = hashlib.sha256()
        count = 0
        with z.open(info) as stream:
            while block := stream.read(1024 * 1024):
                count += len(block)
                h.update(block)
        result[info.filename] = {"bytes": count, "sha256": h.hexdigest()}
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--artifacts", type=Path, required=True, help="JSON array of API metadata plus local_path and phase")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    lock_bytes = (args.repo / "docs/compat/logic-pro/submodules.lock.json").read_bytes()
    lock = json.loads(lock_bytes)
    pins = {s["path"]: s for s in lock["submodules"]}
    results, checks = [], []
    def check(case, passed):
        checks.append({"case": case, "passed": bool(passed)})
        if not passed:
            raise AssertionError(case)
    for artifact in json.loads(args.artifacts.read_text()):
        prefix = artifact["name"]
        check(prefix + ": official run/head identity", artifact["workflow_run"]["head_sha"] == HEAD and artifact["workflow_run"]["id"] == (41256694734 if artifact["phase"] == "P001" else 41256694572) and prefix.endswith(MERGE) and artifact["expired"] is False)
        raw = Path(artifact["local_path"]).read_bytes()
        check(prefix + ": official ZIP digest", digest(raw) == artifact["digest"].removeprefix("sha256:"))
        check(prefix + ": official ZIP size", len(raw) == artifact["size_in_bytes"])
        with zipfile.ZipFile(artifact["local_path"]) as z:
            names = z.namelist()
            check(prefix + ": unique regular root members", len(names) == len(set(names)) and all(Path(n).name == n and not n.startswith(".") for n in names))
            members = zip_digests(z)
            parsed = lambda name: json.loads(z.read(name))
            summary = parsed("summary.json")
            check(prefix + ": successful exact merge candidate", summary["implementation_commit"] == MERGE and summary["result"] == "PASS" and summary["failures"] == [])
            fixtures = z.read("fixture-tests.log").decode()
            final_summary = re.search(r"\nRan (\d+) tests? in [^\n]+\n\nOK\s*\Z", fixtures)
            expected_tests = 120 if artifact["phase"] == "P001" else 96
            check(prefix + ": unqualified actual fixture result", final_summary is not None and int(final_summary[1]) == expected_tests and summary["fixture_tests_executed"] == expected_tests)
            commands = parsed("commands.json")
            if artifact["phase"] == "P001":
                checksum = parsed("checksums.json")
                check(prefix + ": complete checksum coverage", set(checksum) == set(names) - {"checksums.json"})
                for name, metadata in checksum.items():
                    check(prefix + ": member " + name, members[name] == metadata)
                check(prefix + ": command coverage", {c["label"] for c in commands} == {"revision", "fixture-tests", "inventory", "recovery", "classifications", "final-source-verification"})
                for command in commands:
                    check(prefix + ": command " + command["label"], command["exit_code"] == 0 and members[command["log"]]["sha256"] == command["log_sha256"])
                check(prefix + ": exact executed revision", z.read("revision.log").decode().strip() == MERGE)
                initial, final = parsed("inventory.json"), parsed("final-inventory.json")
                check(prefix + ": source identity", initial["source"]["commit"] == MERGE and initial["source"]["tree"] == TREE and initial["source"]["checkout_head"] == MERGE)
                check(prefix + ": stable physical tree", all(initial[k] == final[k] for k in ["source", "repositories", "submodules", "issues", "summary", "requirements", "inventory_status"]))
                check(prefix + ": stable full tracked manifests", members["tracked-files.json"] == members["final-tracked-files.json"] and initial["tracked_files"]["sha256"] == members["tracked-files.json"]["sha256"])
                check(prefix + ": all recursive source available", initial["inventory_status"] == "VALID" and initial["summary"]["gitlinks"] == 160 and initial["summary"]["inspected_repositories"] == 161 and initial["summary"]["unavailable_gitlinks"] == 0 and initial["summary"]["error_count"] == 0 and initial["summary"]["warning_count"] == 0)
                observed = {s["path"]: s["commit"] for s in initial["submodules"]}
                check(prefix + ": original dependency pin identity", observed == {path: s["commit"] for path, s in pins.items()})
                repositories = {r["path"]: r for r in initial["repositories"]}
                check(prefix + ": exact dependency trees", all(repositories[path]["tree"] == s["tree"] for path, s in pins.items()))
                retrieval = parsed("source-retrieval.json")
                check(prefix + ": successful acquisition record", retrieval["result"] == "PASS" and retrieval["failures"] == [] and summary["source_retrieval_sha256"] == members["source-retrieval.json"]["sha256"])
                recovery = parsed("recovery.json")
                check(prefix + ": two isolated historical restorations", recovery["result"] == "PASS" and len(recovery["snapshots"]) == 2 and all(s["result"] == "PASS" and s["independent_object_store"] and s["working_tree_clean"] and s["verified_blobs"] == 27125 for s in recovery["snapshots"]))
                historical = {s["commit"]: s["tree"] for s in recovery["snapshots"]}
                check(prefix + ": unchanged historical trees", historical == {"3447ff5ab8e837ea54a13a506c60d34d77e2bd15": "cfa2352b7296ef5667a8f8c5a11a5718bb3453a0", "b25035fce2cd1c038c567d34ea0797371947d95d": "43461175ff5cfc470f1c1dbf1e4e202aa93a2123"})
                check(prefix + ": all static citations", summary["checks"]["source_citations_verified"] == 63 and summary["checks"]["unavailable_submodule_contents"] == 0)
                check(prefix + ": truthful scope", summary["checks"]["logic_executed"] is False and summary["checks"]["runtime_executed"] is False)
            else:
                checksum = dict(line.split("  ", 1)[::-1] for line in z.read("checksums.sha256").decode().splitlines())
                check(prefix + ": complete checksum coverage", set(checksum) == set(names) - {"checksums.sha256"})
                for name, sha in checksum.items():
                    check(prefix + ": member " + name, members[name]["sha256"] == sha)
                labels = [c["label"] for c in commands]
                check(prefix + ": command stages unique", len(labels) == len(set(labels)))
                check(prefix + ": all acquisition/validation stages", {"git-version", "source-head", "clone-root", "locate-exact-commit", "checkout-exact-commit", "verify-exact-head", "ordinary-recursive-submodules", "fixture-tests", "git-lfs-version", "hydrate-locked-lfs", "native-recursive-status", "strict-lock-verifier", "regenerate-lock"}.issubset(labels))
                for command in commands:
                    data = z.read(command["log"])[command["log_offset"]:command["log_offset"] + command["log_bytes"]]
                    check(prefix + ": command segment " + command["label"], len(data) == command["log_bytes"] and digest(data) == command["output_sha256"])
                    optional_miss = command["label"] == "locate-exact-commit" and command["exit_code"] != 0
                    check(prefix + ": command outcome " + command["label"], command["exit_code"] == 0 or (optional_miss and "fetch-exact-commit" in labels and next(c for c in commands if c["label"] == "fetch-exact-commit")["exit_code"] == 0))
                check(prefix + ": exact source and fresh clone", z.read("head.sha").decode().strip() == MERGE and z.read("source-head.sha").decode().strip() == MERGE)
                check(prefix + ": unchanged locked source", z.read("regenerated-lock.json") == lock_bytes and parsed("lock-regeneration.json")["byte_identical"] is True)
                native = z.read("native-git-status.txt").decode().splitlines()
                check(prefix + ": native complete initialized source", len(native) == 160 and all(line.startswith(" ") and pins[line[42:].split(" (")[0]]["commit"] == line[1:41] for line in native))
                hydration = parsed("lfs-hydration.json")
                expected_objects = [{k:s[k] for k in ("path", "oid_sha256", "size", "mode")} for s in lock["lfs_objects"]]
                observed_objects = [{k:s[k] for k in ("path", "oid_sha256", "size", "mode")} for s in hydration["objects"]]
                check(prefix + ": complete locked LFS objects", hydration["result"] == "PASS" and observed_objects == expected_objects and all(s["status"] == "PASS" for s in hydration["objects"]))
                check(prefix + ": actual payload totals", summary["verified_lfs_objects"] == 44 and summary["verified_lfs_payload_bytes"] == 16128448 and hydration["verified_payload_bytes"] == 16128448)
                check(prefix + ": full physical source scope", summary["verified_gitlinks"] == 160 and summary["verified_repositories"] == 161 and summary["ordinary_git_acquisition"] is True and summary["credential_or_reference_cache_used"] is False)
                verifier = parsed("verification-" + summary["host_id"] + ".json")
                check(prefix + ": physical verifier exact merge", verifier["root_commit"] == MERGE and verifier["result"] == "PASS" and verifier["verified_physical_blobs"] == summary["verified_physical_blobs"] and verifier["verified_lfs_payloads"] == 44 and verifier["verified_lfs_bytes"] == 16128448)
            results.append({"artifact_id": artifact["id"], "artifact_name": prefix, "phase": artifact["phase"], "zip_sha256": digest(raw), "zip_bytes": len(raw), "members": members, "summary": summary, "command_exit_codes": [{"label": c["label"], "exit_code": c["exit_code"]} for c in commands]})
    check("four independent hosted artifacts", len(results) == 4 and len({r["artifact_id"] for r in results}) == 4)
    p1 = [r for r in results if r["phase"] == "P001"]
    p2 = [r for r in results if r["phase"] == "P002"]
    check("two hosts for each phase", len(p1) == len(p2) == 2)
    check("both P001 full source manifests identical", p1[0]["members"]["tracked-files.json"] == p1[1]["members"]["tracked-files.json"])
    check("both P002 physical counts identical", p2[0]["summary"]["verified_physical_blobs"] == p2[1]["summary"]["verified_physical_blobs"])
    candidate_api = json.loads((Path(__file__).parent / "candidate-api.json").read_text())
    static_review = json.loads((Path(__file__).parent / "static-review.json").read_text())
    check("published head and tested merge have identical reviewed tree", candidate_api["head_commit"]["sha"] == HEAD and candidate_api["merge_commit"]["sha"] == MERGE and candidate_api["head_commit"]["tree"] == candidate_api["merge_commit"]["tree"] == TREE)
    changed = {f["path"]: f for f in candidate_api["changed_files"]}
    for path in [".github/workflows/phase2-submodules.yml", "tools/compat/logic-pro/run_baseline.py", "tests/compat/logic-pro/baseline/test_baseline_gate.py"]:
        check("published code equals independent review: " + path, changed[path]["sha"] == static_review["files"][path]["git_blob"])
    check("unchanged original dependencies", all(not path.startswith("src/external/") and path not in [".gitmodules", "docs/compat/logic-pro/submodules.lock.json", "docs/compat/logic-pro/lfs-provenance.json"] for path in changed))
    from datetime import datetime, timezone
    report = {"schema_version":1,"reviewer":"/root/ci_requalification_review","reviewed_at_utc":datetime.now(timezone.utc).isoformat(),"verdict":"PASS_EXACT_CANDIDATE_HOSTED_QUALIFICATION","tested_merge_commit":MERGE,"candidate_head_commit":HEAD,"candidate_tree":TREE,"default_master_at_review":BASE,"pull_request":1,"checks_passed":len(checks),"checks":checks,"artifacts":results,"api_metadata_sha256":digest(args.artifacts.read_bytes()),"candidate_api_metadata_sha256":digest((Path(__file__).parent / "candidate-api.json").read_bytes()),"static_review_sha256":digest((Path(__file__).parent / "static-review.json").read_bytes()),"limits":["This report approves actual hosted source/integrity qualification at the stated PR merge SHA; it is not a default-branch merge or whole-phase acceptance.","Historical raw-evidence publication and default-branch update approvals remain separate unresolved boundaries.","GitHub artifact retention is finite; durable evidence publication must be recorded separately.","No Darling build, Logic execution, audio/graphics or ARM compatibility is established."]}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"result":report["verdict"],"checks":len(checks),"report":str(args.output)},sort_keys=True))

if __name__ == "__main__":
    main()
