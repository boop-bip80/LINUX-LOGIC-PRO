#!/usr/bin/env python3
"""Run the P001 source-evidence campaign; this does not qualify the runtime."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import zlib


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def check_reports(output: Path, snapshot: dict) -> dict:
    """Compare separately produced evidence with the recorded GitHub object list."""
    inventory = read_json(output / "inventory.json")
    recovery = read_json(output / "recovery.json")
    citations = read_json(output / "classifications.json")
    tracked_bytes = (output / "tracked-files.json").read_bytes()
    tracked = json.loads(tracked_bytes)
    expected = {entry["path"]: entry["sha"] for entry in snapshot["external_tree"]["gitlinks"]}
    modules = inventory["submodules"]
    root_modules = [entry for entry in modules if entry["repository"] == "."]
    actual = {entry["path"]: entry["commit"] for entry in root_modules}
    if not expected or len(expected) != len(snapshot["external_tree"]["gitlinks"]):
        raise ValueError("missing or duplicate independently recorded gitlink oracle")
    if actual != expected or len(actual) != len(root_modules):
        raise ValueError("source inventory differs from the independent baseline gitlink list")
    if len({entry["path"] for entry in modules}) != len(modules):
        raise ValueError("duplicate recursive dependency records")
    if inventory["summary"]["error_count"] != 0:
        raise ValueError("inventory recorded errors")
    if any(not r["worktree_clean"] for r in inventory["repositories"]):
        raise ValueError("inventory source worktree was dirty")
    if hashlib.sha256(tracked_bytes).hexdigest() != inventory["tracked_files"]["sha256"]:
        raise ValueError("tracked-file manifest hash mismatch")
    if len(tracked["entries"]) != inventory["summary"]["tracked_entries"]:
        raise ValueError("tracked-file count mismatch")
    if len({(e["repository"], e["path"]) for e in tracked["entries"]}) != len(tracked["entries"]):
        raise ValueError("duplicate tracked-file inventory records")
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
    return {
        "known_gitlinks_verified": len(expected),
        "unavailable_submodule_contents": inventory["summary"]["unavailable_gitlinks"],
        "tracked_entries": inventory["summary"]["tracked_entries"],
        "source_citations_verified": citations["checked_count"],
        "restored_snapshots": [{"label": s["label"], "commit": s["commit"],
                                "tree": s["tree"], "verified_blobs": s["verified_blobs"],
                                "gitlinks": len(s["gitlinks"])} for s in recovery["snapshots"]],
        "runtime_executed": False, "logic_executed": False,
        "recursive_dependency_closure": "UNKNOWN_BEYOND_UNINITIALIZED_GITLINKS",
        "independent_review": "REQUIRED_BEFORE_PHASE_ADVANCEMENT",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
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
                       "--tracked-output", str(output / "tracked-files.json"), "--require-clean"])
    run("recovery", [python, str(tool / "recover_baseline.py"), "--repo", str(repo),
                      "--manifest", str(docs / "baseline.json"), "--output", str(output / "recovery.json")])
    run("classifications", [python, str(tool / "verify_classifications.py"), "--repo", str(repo),
                             "--manifest", str(tool / "classifications.json"), "--current-ref", "HEAD",
                             "--output", str(output / "classifications.json")])
    try:
        report["checks"] = check_reports(output, read_json(docs / "evidence/P001/remote-snapshot.json"))
        if read_json(output / "inventory.json")["source"]["commit"] != report["implementation_commit"]:
            raise ValueError("campaign and inventory implementation revisions differ")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["failures"].append(f"independent object crosscheck: {exc}")
    run("final-source-status", [*safe_git, "status", "--porcelain=v1", "--untracked-files=all"])
    if (output / "final-source-status.log").read_bytes().strip():
        report["failures"].append("source checkout changed during the campaign")
    report["result"] = "PASS" if not report["failures"] else "FAIL"
    (output / "commands.json").write_text(json.dumps(transcript, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    checksums = {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                 for p in sorted(output.iterdir()) if p.is_file()}
    (output / "checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    if args.export_small_evidence:
        for name in ("inventory.json", "recovery.json", "classifications.json", "summary.json", "checksums.json", "commands.json"):
            path = output / name
            if path.exists():
                data = path.read_bytes()
                encoded = base64.b64encode(zlib.compress(data, 9)).decode("ascii")
                print(f"P001_EVIDENCE {name} {hashlib.sha256(data).hexdigest()} {encoded}", flush=True)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
