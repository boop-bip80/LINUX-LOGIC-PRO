#!/usr/bin/env python3
"""Independent Wave 5 source-continuity and original-report counterexample audit.

The older producer reports are parser controls, never current build evidence.
No original report, working source file or dependency is modified.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

CANDIDATE = "b6f4d9bf04dd4a15a1b349845f962295ff350b7d"
PREDECESSOR = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"
CHANGES = {
    ".github/workflows/phase3-build.yml", "ci/logic-pro/acquire-toolchain.sh",
    "ci/logic-pro/build-p003.sh", "cmake/darling_objc_configuration.cmake",
    "docs/compat/logic-pro/retained-toolchain.json",
    "tests/compat/logic-pro/build/test_objc_configuration.py",
    "tests/compat/logic-pro/build/test_probes.py",
    "tests/compat/logic-pro/build/test_retained_toolchain.py",
    "tests/compat/logic-pro/build/test_source_classifications.py",
    "tests/compat/logic-pro/build/test_source_cleanliness.py",
    "tools/compat/logic-pro/compare_p003.py", "tools/compat/logic-pro/restore_toolchain.py",
    "tools/compat/logic-pro/run_build_probes.py",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--evidence-repo", type=Path,
                        help="Later documentation checkout containing the original retained ZIPs; defaults to --repo")
    parser.add_argument("--producer-root", type=Path,
                        help="Optional extracted build-a/build-b copies, required to match the retained original ZIP members")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    evidence_repo = (args.evidence_repo or args.repo).resolve()

    def git(*command):
        return subprocess.check_output(["git", "-C", str(repo), *command])

    def blob(commit, path):
        return git("show", f"{commit}:{path}")

    def tree(commit):
        output = {}
        for entry in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
            if entry:
                metadata, name = entry.split(b"\t", 1)
                mode, kind, identity = metadata.decode().split()
                output[name.decode()] = {"mode": mode, "kind": kind, "identity": identity}
        return output

    older, current = tree(PREDECESSOR), tree(CANDIDATE)
    changed = {path for path in set(older) | set(current) if older.get(path) != current.get(path)}
    documentation = {path for path in changed if path == "README.md" or
                     path.startswith("docs/compat/logic-pro/evidence/")}
    assert changed - documentation == CHANGES, sorted(changed - documentation)
    preserved = {path: entry for path, entry in older.items()
                 if path not in CHANGES and path != "README.md" and
                 not path.startswith("docs/compat/logic-pro/evidence/")}
    assert all(current.get(path) == entry for path, entry in preserved.items())
    links = {path: entry["identity"] for path, entry in current.items() if entry["kind"] == "commit"}
    assert links == {path: entry["identity"] for path, entry in older.items() if entry["kind"] == "commit"}
    assert len(links) == 149
    code_hashes = {}
    for path in sorted(CHANGES):
        expected = blob(CANDIDATE, path)
        assert (repo / path).read_bytes() == expected, "Working input differs: " + path
        code_hashes[path] = digest(expected)
    source_lock = json.loads(blob(CANDIDATE, "docs/compat/logic-pro/submodules.lock.json"))
    assert len(source_lock["submodules"]) == source_lock["expected_recursive_gitlinks"] == 160
    assert len(source_lock["lfs_objects"]) == source_lock["expected_lfs_objects"] == 44
    protected_names = ["AGENTS.md", ".gitmodules", "tools/compat/logic-pro/verify_classifications.py",
                       "tools/compat/logic-pro/classifications.json", "docs/compat/logic-pro/submodules.lock.json",
                       "docs/compat/logic-pro/toolchain.lock.json", "ci/logic-pro/Dockerfile.p003"]
    protected = {}
    for path in protected_names:
        before, after = blob(PREDECESSOR, path), blob(CANDIDATE, path)
        assert before == after
        protected[path] = digest(after)
    classification = json.loads(blob(CANDIDATE, "tools/compat/logic-pro/classifications.json"))
    root_citations = sorted({item["path"] for item in classification["evidence"]
                             if item.get("repository", ".") == "."})
    assert len(root_citations) == 24
    cited_blobs = {}
    for path in root_citations:
        assert older[path] == current[path]
        cited_blobs[path] = current[path]["identity"]

    acceptance_root = evidence_repo / "docs/compat/logic-pro/evidence/P002/requalification-20261105"
    acceptance = json.loads((acceptance_root / "ordered-acceptance.json").read_text())
    decisions = []
    for decision in acceptance["decisions"]:
        raw = (acceptance_root / decision["record"]).read_bytes()
        assert digest(raw) == decision["record_sha256"]
        assert decision["implementation_commit"] == PREDECESSOR
        assert decision["decision"] == "ACCEPTED"
        assert decision["gates"] == {"G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "PASS"}
        assert decision["reviewer_authored_production_changes"] is False
        decisions.append({key: decision[key] for key in
                          ("phase", "accepted_at_utc", "reviewer", "record", "record_sha256")})
    assert [item["phase"] for item in decisions] == ["P001", "P002"]
    assert decisions[0]["accepted_at_utc"] < decisions[1]["accepted_at_utc"]

    original_fixture = evidence_repo / "docs/compat/logic-pro/evidence/P003/requalification-20261106/attempt-b6f4d9b/fixtures.zip"
    fixture_bytes = original_fixture.read_bytes()
    assert len(fixture_bytes) == 11674
    assert digest(fixture_bytes) == "c3e9124012f7b9a4ea8249022bfe8ffbd6d8e8740c381b940aca69aea0f6b085"
    fixture_results = {}
    with zipfile.ZipFile(original_fixture) as bundle:
        assert set(bundle.namelist()) == {"baseline.log", "submodules.log", "build.log", "summary.json"}
        assert len(bundle.infolist()) == 4 and bundle.testzip() is None
        summary = json.loads(bundle.read("summary.json"))
        for suite, count in (("baseline", 174), ("submodules", 115), ("build", 200)):
            raw = bundle.read(suite + ".log")
            text = raw.decode()
            named = re.findall(r"^(test_\w+) \(([^\n)]+)\) \.\.\.", text, re.M)
            assert len(named) == len(set(named)) == count, (suite, len(named), count)
            assert len(re.findall(rf"^Ran {count} tests in [0-9.]+s$", text, re.M)) == 1
            assert re.search(r"^OK$", text, re.M)
            assert not re.search(r"^FAILED|^OK \(|\.\.\. (skipped|expected failure|unexpected success)", text, re.M)
            assert next(item for item in summary if item["suite"] == suite) == {"suite": suite, "count": count, "exit_code": 0}
            fixture_results[suite] = {"unique_named_cases": count, "sha256": digest(raw), "terminal": "OK", "skipped": 0}

    sys.path.insert(0, str(repo / "tools/compat/logic-pro"))
    import compare_p003 as consumer
    controls = []
    rejections = []
    with tempfile.TemporaryDirectory(prefix="p003-wave5-citations-") as temporary:
        destination = Path(temporary)
        for host in ("a", "b"):
            archive = evidence_repo / f"docs/compat/logic-pro/evidence/P003/requalification-20261106/attempt-8a222c7/build-{host}.zip"
            archive_bytes = archive.read_bytes()
            expected_sha = {"a": "898a8d27df78822a190ba28b9369e250d77075ccb9659f23efdb86c3962d117b",
                            "b": "7594e2aeca0e4c82e7ac09da1aee6bbba6e4673f908771c75b8e3743a84fe76a"}[host]
            assert digest(archive_bytes) == expected_sha
            with zipfile.ZipFile(archive) as bundle:
                assert bundle.testzip() is None
                report_bytes = bundle.read("source-classifications.json")
                log_bytes = bundle.read("source-classifications.log")
                members = len(bundle.infolist())
            origin = args.producer_root / ("build-" + host) if args.producer_root else None
            if origin:
                assert (origin / "source-classifications.json").read_bytes() == report_bytes
                assert (origin / "source-classifications.log").read_bytes() == log_bytes
            data = json.loads(report_bytes)
            (destination / "source-classifications.json").write_bytes(report_bytes)
            (destination / "source-classifications.log").write_bytes(log_bytes)
            observed = consumer.validate_source_classifications(destination, data["current_commit"])
            assert observed["checked_count"] == 63 and observed["source_file_count"] == 41
            controls.append({"host": host, "actual_source": data["current_commit"],
                             "original_zip_sha256": expected_sha, "original_zip_bytes": len(archive_bytes),
                             "CRC_members": members,
                             "report_sha256": digest(report_bytes), "log_sha256": digest(log_bytes),
                             "status": "ORIGINAL_OLDER_PRODUCER_ACCEPTED_AS_PARSER_CONTROL"})
            root_index = next(i for i, row in enumerate(data["checked"]) if row["repository"] == ".")
            child_index = next(i for i, row in enumerate(data["checked"]) if row["repository"] != ".")
            mutations = {
                "missing_current_source": lambda value: value["checked"][root_index].pop("current_source"),
                "root_bound_to_historical_commit": lambda value: value["checked"][root_index]["current_source"].update(repository_commit=value["inspected_commit"]),
                "child_bound_to_root_commit": lambda value: value["checked"][child_index]["current_source"].update(repository_commit=value["current_commit"]),
                "missing_child_gitlink_chain": lambda value: value["checked"][child_index]["current_source"].update(gitlink_chain=[]),
                "boolean_assertion_replaced_by_integer": lambda value: value["checked"][root_index]["current_source"].update(original_assertions_preserved=1),
                "line_number_replaced_by_float": lambda value: value["checked"][root_index]["current_source"].update(line_start=float(value["checked"][root_index]["current_source"]["line_start"])),
                "unexpected_current_source_key": lambda value: value["checked"][root_index]["current_source"].update(unreviewed=True),
                "coverage_boolean_replaced_by_integer": lambda value: value["coverage"].update(required=1),
                "historical_binding_replaced_by_current": lambda value: value["checked"][root_index].update(repository_commit=value["current_commit"]),
                "reported_citation_count_replaced_by_float": lambda value: value.update(checked_count=63.0),
                "reported_file_count_replaced_by_float": lambda value: value.update(source_file_count=41.0),
                "duplicate_citation_with_same_total": lambda value: value["checked"].__setitem__(-1, copy.deepcopy(value["checked"][0])),
                "forged_top_level_anchor": lambda value: value.update(current_source_anchor="0" * 40),
            }
            for name, mutation in mutations.items():
                altered = copy.deepcopy(data)
                mutation(altered)
                (destination / "source-classifications.json").write_text(json.dumps(altered))
                try:
                    consumer.validate_source_classifications(destination, data["current_commit"])
                except ValueError as error:
                    rejections.append({"host": host, "case": name, "rejected": True, "reason": str(error)})
                else:
                    raise AssertionError("Accepted forged provenance: " + name)
            (destination / "source-classifications.json").write_bytes(report_bytes)
            (destination / "source-classifications.log").write_bytes(b"source classifications: PASS; 63 citations verified\nforged extra record\n")
            try:
                consumer.validate_source_classifications(destination, data["current_commit"])
            except ValueError as error:
                rejections.append({"host": host, "case": "contradictory_raw_log", "rejected": True, "reason": str(error)})
            else:
                raise AssertionError("Accepted contradictory raw log")
            if origin:
                assert (origin / "source-classifications.json").read_bytes() == report_bytes
                assert (origin / "source-classifications.log").read_bytes() == log_bytes
            assert archive.read_bytes() == archive_bytes
    assert len(rejections) == 28
    output = {"schema": "darling.p003.wave5-source-checkpoint.v1", "reviewer": "/root/wave5_source",
              "observed_at_utc": datetime.now(timezone.utc).isoformat(), "candidate": CANDIDATE,
              "candidate_tree": git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
              "local_head_at_observation": git("rev-parse", "HEAD").decode().strip(),
              "predecessor": PREDECESSOR, "ordered_decisions": decisions,
              "protected_predecessor_entries_unchanged": len(preserved),
              "protected_predecessor_entries_inventory_sha256": digest(json.dumps(preserved, sort_keys=True, separators=(",", ":")).encode()),
              "unchanged_direct_gitlinks": links, "locked_recursive_gitlinks": 160, "locked_lfs_payloads": 44,
              "protected_input_sha256": protected, "unchanged_root_cited_blobs": cited_blobs,
              "reviewed_scoped_file_sha256": code_hashes,
              "original_fixture_zip": {"artifact_id": 13483523427, "bytes": len(fixture_bytes),
                                       "sha256": digest(fixture_bytes), "CRC_members": 4, "suites": fixture_results},
              "older_original_parser_controls": controls, "independent_counterexamples": rejections,
              "current_build_source_acceptance": "PENDING_ORIGINAL_FRESH_A_B_ARTIFACTS",
              "phase_acceptance": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "BOUNDED_SOURCE_CHECKS_PASS; CURRENT_GATES_PENDING",
                      "protected_entries": len(preserved), "direct_gitlinks": len(links),
                      "original_parser_controls": len(controls), "rejected_counterexamples": len(rejections),
                      "fixture_counts": {key: value["unique_named_cases"] for key, value in fixture_results.items()}}))


if __name__ == "__main__":
    main()
