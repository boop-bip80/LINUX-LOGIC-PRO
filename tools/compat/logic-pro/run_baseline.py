#!/usr/bin/env python3
"""Run the P001 source-evidence campaign; this does not qualify the runtime."""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import sys
import time
import zlib


REQUIRED_CATEGORIES = frozenset({
    "native_linux_host", "macho_runtime_component", "implemented_body_unqualified", "partial_framework",
    "developer_link_stub", "generated_stub_tooling", "generated_style_stub_body", "architecture_constraint",
})
REQUIRED_STAGES = frozenset({
    "host_launch", "mldr_mapping_and_dyld_handoff", "dyld_dependency_loading",
    "system_library_initialization", "server_checkin_and_rpc_dispatch", "framework_initialization",
})

INVENTORY_SPEC = importlib.util.spec_from_file_location("p001_inventory_policy", Path(__file__).with_name("inventory.py"))
assert INVENTORY_SPEC and INVENTORY_SPEC.loader
INVENTORY_POLICY = importlib.util.module_from_spec(INVENTORY_SPEC)
INVENTORY_SPEC.loader.exec_module(INVENTORY_POLICY)


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def check_reports(output: Path, snapshot: dict) -> dict:
    """Compare separately produced evidence with the recorded GitHub object list."""
    inventory = read_json(output / "inventory.json")
    retrieval = read_json(output / "source-retrieval.json")
    recovery = read_json(output / "recovery.json")
    citations = read_json(output / "classifications.json")
    tracked_bytes = (output / "tracked-files.json").read_bytes()
    tracked = json.loads(tracked_bytes)

    def unique(records: list[dict], label: str) -> dict[str, dict]:
        if not isinstance(records, list) or any(not isinstance(e, dict) or not isinstance(e.get("path"), str) for e in records):
            raise ValueError(f"invalid {label} records")
        result = {entry["path"]: entry for entry in records}
        if len(result) != len(records):
            raise ValueError(f"duplicate {label} records")
        return result

    def full_path(repository: str, local: str) -> str:
        if not isinstance(local, str) or not local or str(PurePosixPath(local)) != local or PurePosixPath(local).is_absolute():
            raise ValueError("noncanonical repository-relative path")
        if any(part in ("..", ".git") for part in PurePosixPath(local).parts) or local == ".":
            raise ValueError("unsafe repository-relative path")
        return local if repository == "." else repository + "/" + local

    def count_is(value: object, expected: int, label: str) -> None:
        if type(value) is not int or value != expected:
            raise ValueError(f"{label} count mismatch")

    expected = {entry["path"]: entry["sha"] for entry in snapshot["external_tree"]["gitlinks"]}
    modules = inventory["submodules"]
    root_modules = [entry for entry in modules if entry["repository"] == "."]
    actual = {entry["path"]: entry["commit"] for entry in root_modules}
    if not expected or len(expected) != len(snapshot["external_tree"]["gitlinks"]):
        raise ValueError("missing or duplicate independently recorded gitlink oracle")
    if actual != expected or len(actual) != len(root_modules):
        raise ValueError("source inventory differs from the independent baseline gitlink list")
    module_by_path = unique(modules, "recursive dependency")
    repositories = unique(inventory["repositories"], "source repository")
    if set(repositories) != {".", *module_by_path}:
        raise ValueError("every recursive gitlink must have exactly one inspected source repository")
    summary = inventory["summary"]
    issues = inventory["issues"]
    if not isinstance(issues, list) or any(issue.get("severity") not in ("warning", "error") for issue in issues):
        raise ValueError("invalid inventory issue records")
    if inventory["inventory_status"] != "VALID" or any(issue["severity"] == "error" for issue in issues):
        raise ValueError("inventory recorded errors")
    count_is(summary["error_count"], 0, "inventory error")
    count_is(summary["warning_count"], len(issues), "inventory warning")
    if (inventory["requirements"].get("clean_checkout") is not True
            or inventory["requirements"].get("recursive_source") is not True):
        raise ValueError("strict clean and recursive inventory requirements were not enabled")
    if summary["recursive_content_complete"] is not True:
        raise ValueError("recursive dependency contents are incomplete")
    count_is(summary["gitlinks"], len(modules), "recursive gitlink")
    count_is(summary["available_gitlinks"], len(modules), "available gitlink")
    count_is(summary["unavailable_gitlinks"], 0, "unavailable gitlink")
    count_is(summary["inspected_repositories"], len(repositories), "inspected repository")
    if hashlib.sha256(tracked_bytes).hexdigest() != inventory["tracked_files"]["sha256"]:
        raise ValueError("tracked-file manifest hash mismatch")
    if tracked["source_commit"] != inventory["source"]["commit"]:
        raise ValueError("tracked-file and source revisions differ")
    tracked_by_path = unique(tracked["entries"], "tracked-file inventory")
    count_is(summary["tracked_entries"], len(tracked_by_path), "tracked-file")
    count_is(inventory["tracked_files"]["entries"], len(tracked_by_path), "tracked-file metadata")
    entries_by_repo = {name: [] for name in repositories}
    tracked_links = {}
    for entry in tracked["entries"]:
        owner = entry["repository"]
        if owner not in repositories or full_path(owner, entry["repository_path"]) != entry["path"]:
            raise ValueError("tracked-file path or repository ownership mismatch")
        entries_by_repo[owner].append(entry)
        if entry["mode"] == "160000":
            if entry["type"] != "commit":
                raise ValueError("gitlink mode and type disagree")
            tracked_links[entry["path"]] = entry
        elif entry["type"] != "blob" or entry["mode"] not in ("100644", "100755", "120000"):
            raise ValueError("unsupported tracked-file mode or type")
    if set(tracked_links) != set(module_by_path):
        raise ValueError("recursive dependency records do not match every tracked gitlink")
    license_objects = {}
    license_candidates_verified = 0
    for name, repository in repositories.items():
        if (repository["worktree_clean"] is not True or repository["checkout_matches_ref"] is not True
                or repository["checkout_head"] != repository["commit"]
                or repository["working_tree_status"] != [] or repository["staged_index_changes"] != []):
            raise ValueError("inventory source repository was dirty or not at its recorded pin")
        count_is(repository["tracked_entries"], len(entries_by_repo[name]), "per-repository tracked-file")
        physical = repository["materialization"]
        blob_count = sum(entry["type"] == "blob" for entry in entries_by_repo[name])
        if physical["status"] != "PASS" or physical["reference_commit"] != repository["commit"]:
            raise ValueError("physical source bytes were not verified at the recorded revision")
        count_is(physical["expected_blobs"], blob_count, "physical source blob")
        count_is(physical["verified_blobs"], blob_count, "verified physical source blob")
        # Candidate metadata is required even when a repository has no matches.
        # The tracked paths supply the completeness oracle; report counts do not.
        expected_licenses = {
            entry["repository_path"]: (entry, reasons)
            for entry in entries_by_repo[name] if entry["type"] == "blob"
            if (reasons := INVENTORY_POLICY.license_candidate_reasons(entry["repository_path"]))
        }
        licenses = unique(repository.get("licenses"), "license candidate")
        if set(licenses) != set(expected_licenses):
            raise ValueError("license candidate records do not match the tracked filename/path policy")
        for local, record in licenses.items():
            entry, reasons = expected_licenses[local]
            symlink = entry["mode"] == "120000"
            if (record.get("git_blob") != entry["object"] or record.get("mode") != entry["mode"]
                    or record.get("content_kind") != ("symlink_target_text" if symlink else "regular_file")
                    or record.get("discovery_reasons") != reasons
                    or record.get("classification") != "filename/path candidate; not a legal determination"):
                raise ValueError("license candidate object, mode, type or discovery metadata mismatch")
            if (type(record.get("bytes")) is not int or record["bytes"] < 0
                    or not isinstance(record.get("sha256"), str)
                    or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None
                    or not isinstance(record["git_blob"], str)
                    or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", record["git_blob"]) is None):
                raise ValueError("invalid license candidate size or digest")
            signature = (record["bytes"], record["sha256"])
            if license_objects.setdefault(record["git_blob"], signature) != signature:
                raise ValueError("license candidates disagree about the same committed blob")
            if symlink:
                if not isinstance(record.get("symlink_target"), str) or record.get("target_dereferenced") is not False:
                    raise ValueError("license symlink must record target text without dereferencing")
                raw = record["symlink_target"].encode("utf-8", "surrogateescape")
                algorithm = "sha1" if len(record["git_blob"]) == 40 else "sha256"
                object_digest = hashlib.new(algorithm, b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
                if (signature != (len(raw), hashlib.sha256(raw).hexdigest()) or object_digest != record["git_blob"]):
                    raise ValueError("license symlink target text disagrees with committed object or digest")
            elif "symlink_target" in record or "target_dereferenced" in record:
                raise ValueError("regular license candidate is incorrectly labeled as a symlink")
        license_candidates_verified += len(licenses)
        expected_index = {entry["repository_path"]: entry["object"] for entry in entries_by_repo[name] if entry["mode"] == "160000"}
        index_links = repository["index_gitlinks"]
        actual_index = {entry["path"]: entry["object"] for entry in index_links}
        if (actual_index != expected_index or len(actual_index) != len(index_links)
                or any(type(e["stage"]) is not int or e["stage"] != 0 or e["mode"] != "160000" for e in index_links)):
            raise ValueError("repository index gitlinks disagree with committed inventory")
        if name == ".":
            if (repository["commit"] != inventory["source"]["commit"]
                    or repository["tree"] != inventory["source"]["tree"]
                    or repository["checkout_head"] != inventory["source"]["checkout_head"]):
                raise ValueError("root repository and source snapshot disagree")
            continue
        module = module_by_path[name]
        tracked_link = tracked_links[name]
        owner = module["repository"]
        if (owner not in repositories or full_path(owner, module["repository_path"]) != name
                or tracked_link["repository"] != owner or tracked_link["repository_path"] != module["repository_path"]
                or tracked_link["object"] != module["commit"] or repository["commit"] != module["commit"]):
            raise ValueError("recursive gitlink pin or source ownership mismatch")
        if (module["content_status"] != "available_at_pin" or module["recursive_inventory"] != "inspected"
                or module.get("checkout_head") != module["commit"]):
            raise ValueError("missing or mismatched recursive dependency contents")
        if (not module.get("declared_url") or not module.get("resolved_url")
                or module.get("source_origin") != repository.get("configured_origin")
                or not repository.get("configured_origin")
                or module.get("source_origin_provenance") != "child_remote_origin_configuration"
                or module.get("resolution_base_url") != repositories[owner]["effective_remote_url"]
                or module.get("resolution_base_provenance") != repositories[owner]["effective_remote_provenance"]
                or repository.get("effective_remote_url") != repository["configured_origin"]
                or repository.get("effective_remote_provenance") != "configured_origin"):
            raise ValueError("dependency source-origin provenance is incomplete or inconsistent")
    if (retrieval["result"] != "PASS" or retrieval["failures"] != []
            or retrieval["source"]["commit"] != inventory["source"]["commit"]
            or retrieval["source"]["tree"] != inventory["source"]["tree"]
            or retrieval["source"].get("parent_source_unchanged") is not True
            or retrieval["recursive_content_complete"] is not True):
        raise ValueError("source retrieval failed or refers to a different implementation")
    retrieved = unique(retrieval["submodules"], "retrieved source")
    if set(retrieved) != set(module_by_path):
        raise ValueError("retrieval report does not cover exactly the recursive dependency graph")
    count_is(retrieval["recursive_submodules_observed"], len(modules), "retrieved submodule")
    for name, source in retrieved.items():
        module, repository = module_by_path[name], repositories[name]
        # Retrieval's resolved_url is relative to the actual configured parent
        # origin, matching inventory's effective_resolved_url. Its separate
        # acquisition_resolved_url records any root upstream override; fetch_url
        # and source_origin identify the actual acquired child. Inventory's
        # resolved_url additionally preserves the original logical fork mapping.
        if (source["status"] != "PASS" or source["commit"] != module["commit"] or source["tree"] != repository["tree"]
                or source["configured_origin"] != module["source_origin"]
                or source["fetch_url"] != module["source_origin"]
                or source["parent_path"] != module["repository"]
                or source["declared_url"] != module["declared_url"]
                or source["resolved_url"] != module["effective_resolved_url"]):
            raise ValueError("retrieval source pin, tree, URL or provenance disagrees with inventory")
    if recovery["result"] != "PASS" or len(recovery["snapshots"]) != 2:
        raise ValueError("both original source and original plan must be recovered")
    if {s["label"] for s in recovery["snapshots"]} != {"baseline", "integration"}:
        raise ValueError("recovery snapshots are incomplete or duplicated")
    for restored in recovery["snapshots"]:
        label = restored["label"]
        if restored["commit"] != snapshot[f"{label}_commit"] or restored["tree"] != snapshot[f"{label}_tree"]:
            raise ValueError("recovered snapshot differs from the independent commit/tree oracle")
        if not restored["working_tree_clean"] or not restored["independent_object_store"] or restored["verified_blobs"] <= 0:
            raise ValueError("recovery did not verify a complete isolated materialization")
        restored_links = {e["path"]: e["commit"] for e in restored["gitlinks"]}
        if restored_links != expected or len(restored["gitlinks"]) != len(expected):
            raise ValueError("recovered baseline gitlinks differ from independent source oracle")
    if citations["status"] != "PASS" or citations["checked_count"] <= 0:
        raise ValueError("source citations did not pass")
    if citations["current_commit"] != inventory["source"]["commit"]:
        raise ValueError("source citation and inventory implementation revisions differ")
    coverage = citations["coverage"]
    if coverage["required"] is not True or coverage["status"] != "PASS":
        raise ValueError("mandatory P001 category and launch-stage coverage did not pass")
    if (set(coverage["required_categories"]) != REQUIRED_CATEGORIES
            or set(coverage["required_stages"]) != REQUIRED_STAGES
            or coverage["missing_categories"] != [] or coverage["missing_stages"] != []
            or coverage["missing_stage_sources"] != {}):
        raise ValueError("phase coverage requirements were weakened or are incomplete")
    count_is(citations["checked_count"], len(citations["checked"]), "checked citation")
    checked_categories = {citation["category"] for citation in citations["checked"]}
    checked_stages = {stage for citation in citations["checked"] for stage in citation["launch_stages"]}
    if (not REQUIRED_CATEGORIES.issubset(checked_categories) or not REQUIRED_STAGES.issubset(checked_stages)
            or set(coverage["categories"]) != checked_categories or set(coverage["launch_stages"]) != checked_stages):
        raise ValueError("phase coverage summary differs from verified citation records")
    for citation in citations["checked"]:
        owner = citation["repository"]
        if owner not in repositories:
            raise ValueError("source citation owner is missing from recursive inventory")
        if owner != "." and citation["repository_commit"] != repositories[owner]["commit"]:
            raise ValueError("child source citation is not bound to the inventoried gitlink pin")
        source_path = full_path(owner, citation["path"])
        source_entry = tracked_by_path.get(source_path)
        # P001's immutable citation still binds to its original Git object.
        # A separately verified P002 URL-only re-audit may bind precisely one
        # different current object: the root .gitmodules after all 149 fork-
        # relative URLs were repaired. Do not waive or generalize any other
        # original source citation: both old and new blobs are pinned by the
        # source verifier, and this independent crosscheck binds the NEW blob
        # to the actual current recursive tracked inventory.
        current_reaudit = citation.get("current_reaudit")
        expected_blob = citation["blob_sha1"]
        if current_reaudit is not None:
            if (owner != "." or citation["path"] != ".gitmodules"
                    or not isinstance(current_reaudit, dict)
                    or set(current_reaudit) != {"phase", "blob_sha1", "excerpt_sha256", "url_rewrites_verified"}
                    or current_reaudit["phase"] != "P002"
                    or type(current_reaudit["url_rewrites_verified"]) is not int
                    or current_reaudit["url_rewrites_verified"] != 149
                    or not isinstance(current_reaudit["blob_sha1"], str)
                    or re.fullmatch(r"[0-9a-f]{40}", current_reaudit["blob_sha1"]) is None
                    or not isinstance(current_reaudit["excerpt_sha256"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", current_reaudit["excerpt_sha256"]) is None
                    or current_reaudit["blob_sha1"] == expected_blob):
                raise ValueError("invalid or inapplicable P002 current-source re-audit")
            expected_blob = current_reaudit["blob_sha1"]
        if (source_entry is None or source_entry["repository"] != owner
                or source_entry["type"] != "blob" or source_entry["object"] != expected_blob):
            raise ValueError("source citation blob is not present in the recursive tracked inventory")
    return {
        "known_gitlinks_verified": len(expected),
        "recursive_gitlinks_verified": len(modules),
        "source_repositories_verified": len(repositories),
        "unavailable_submodule_contents": 0,
        "tracked_entries": len(tracked_by_path),
        "license_candidates_verified": license_candidates_verified,
        "source_citations_verified": citations["checked_count"],
        "restored_snapshots": [{"label": s["label"], "commit": s["commit"],
                                "tree": s["tree"], "verified_blobs": s["verified_blobs"],
                                "gitlinks": len(s["gitlinks"])} for s in recovery["snapshots"]],
        "runtime_executed": False, "logic_executed": False,
        "recursive_dependency_closure": "COMPLETE_AT_RECORDED_PINS",
        "independent_review": "REQUIRED_BEFORE_PHASE_ADVANCEMENT",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--retrieval-report", type=Path, required=True,
                        help="prepare_sources.py report for this exact checkout and recursive source graph")
    parser.add_argument("--export-small-evidence", action="store_true",
                        help="emit compressed, checksummed small reports for connector retrieval")
    args = parser.parse_args(argv)
    repo, output = args.repo.resolve(), args.output_dir.resolve()
    if output == repo or repo in output.parents:
        parser.error("--output-dir must be outside the source checkout")
    if output.exists() and any(output.iterdir()):
        parser.error("--output-dir must be absent or empty; stale evidence is not accepted")
    output.mkdir(parents=True, exist_ok=True)
    tool = repo / "tools/compat/logic-pro"
    docs = repo / "docs/compat/logic-pro"
    env = os.environ.copy()
    for key in list(env):
        if key in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                   "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                   "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT"} or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            env.pop(key, None)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
                "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0"})
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    safe_git = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
                "-c", "core.hooksPath=" + os.devnull]
    transcript = []
    report = {"schema_version": 1, "phase": "P001", "result": "FAIL",
              "scope": "Source inventory, recovery, and static evidence only.",
              "environment": {"system": platform.system(), "machine": platform.machine(),
                              "release": platform.release(), "python": platform.python_version()},
              "failures": []}
    try:
        retrieval_bytes = args.retrieval_report.resolve().read_bytes()
        (output / "source-retrieval.json").write_bytes(retrieval_bytes)
        report["source_retrieval_sha256"] = hashlib.sha256(retrieval_bytes).hexdigest()
    except OSError as exc:
        report["failures"].append(f"source retrieval report unavailable: {exc}")

    def run(label: str, command: list[str], timeout: int = 900) -> int:
        print(f"P001: {label}", flush=True)
        started = time.monotonic()
        try:
            result = subprocess.run(command, cwd=repo, env=env, capture_output=True,
                                    check=False, timeout=timeout)
            data = result.stdout + result.stderr
            code = result.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            data, code = str(exc).encode(), 125
        (output / f"{label}.log").write_bytes(data)
        transcript.append({"label": label, "command": command, "exit_code": code,
                           "duration_seconds": round(time.monotonic() - started, 3),
                           "log": f"{label}.log", "log_sha256": hashlib.sha256(data).hexdigest()})
        print(data.decode("utf-8", "replace"), end="", flush=True)
        if code:
            report["failures"].append(f"{label}: exit {code}")
        return code

    python = sys.executable
    run("revision", [*safe_git, "rev-parse", "HEAD"])
    report["implementation_commit"] = (output / "revision.log").read_text().strip()
    run("fixture-tests", [python, "-m", "unittest", "discover", "-s",
                           "tests/compat/logic-pro/baseline", "-p", "test_*.py", "-v"])
    tests = (output / "fixture-tests.log").read_text()
    count = re.search(r"Ran ([1-9][0-9]*) tests? in ", tests)
    report["fixture_tests_executed"] = int(count.group(1)) if count else 0
    if not count or "skipped=" in tests:
        report["failures"].append("fixture tests were empty, unreported, or skipped")
    run("inventory", [python, str(tool / "inventory.py"), "--repo", str(repo), "--ref", "HEAD",
                       "--remote-url", "https://github.com/boop-bip80/MAC-OS-EMULATION.git",
                       "--output", str(output / "inventory.json"),
                       "--tracked-output", str(output / "tracked-files.json"), "--require-clean", "--require-recursive"])
    run("recovery", [python, str(tool / "recover_baseline.py"), "--repo", str(repo),
                      "--manifest", str(docs / "baseline.json"), "--output", str(output / "recovery.json")])
    run("classifications", [python, str(tool / "verify_classifications.py"), "--repo", str(repo),
                             "--manifest", str(tool / "classifications.json"), "--current-ref", "HEAD",
                             "--output", str(output / "classifications.json"), "--require-phase-coverage"])
    try:
        report["checks"] = check_reports(output, read_json(docs / "evidence/P001/remote-snapshot.json"))
        if read_json(output / "inventory.json")["source"]["commit"] != report["implementation_commit"]:
            raise ValueError("campaign and inventory implementation revisions differ")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["failures"].append(f"independent object crosscheck: {exc}")
    # Recheck actual bytes after all evidence commands. Git status alone can
    # conceal assume-unchanged edits and may run configured clean filters.
    run("final-source-verification", [python, str(tool / "inventory.py"), "--repo", str(repo), "--ref", "HEAD",
                                     "--remote-url", "https://github.com/boop-bip80/MAC-OS-EMULATION.git",
                                     "--output", str(output / "final-inventory.json"),
                                     "--tracked-output", str(output / "final-tracked-files.json"),
                                     "--require-clean", "--require-recursive"])
    try:
        initial, final = read_json(output / "inventory.json"), read_json(output / "final-inventory.json")
        stable = ("source", "repositories", "submodules", "issues", "summary", "requirements", "inventory_status")
        if (any(initial[key] != final[key] for key in stable)
                or initial["tracked_files"]["sha256"] != final["tracked_files"]["sha256"]
                or final["inventory_status"] != "VALID"):
            raise ValueError("source bytes, pins, origins or checkout state changed during the campaign")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["failures"].append(f"final source verification: {exc}")
    report["result"] = "PASS" if not report["failures"] else "FAIL"
    (output / "commands.json").write_text(json.dumps(transcript, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    checksums = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                 for p in sorted(output.iterdir()) if p.is_file()}
    (output / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    if args.export_small_evidence:
        for name in ("inventory.json", "source-retrieval.json", "recovery.json", "classifications.json", "summary.json", "checksums.json", "commands.json"):
            path = output / name
            if path.exists():
                data = path.read_bytes()
                encoded = base64.b64encode(zlib.compress(data, 9)).decode("ascii")
                print(f"P001_EVIDENCE {name} {hashlib.sha256(data).hexdigest()} {encoded}", flush=True)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
