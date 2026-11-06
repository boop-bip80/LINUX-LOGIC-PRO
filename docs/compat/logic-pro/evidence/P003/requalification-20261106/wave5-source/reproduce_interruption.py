#!/usr/bin/env python3
"""Reproduce only the P003 controller's interrupted-initialization receipt.

Uses an exact committed runner, temporary paths and a controlled constructor
interruption. It never starts Darling or claims a runtime/phase result.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest import mock

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", type=Path, required=True)
parser.add_argument("--commit", required=True)
parser.add_argument("--working-tree", action="store_true",
                    help="Review the current uncommitted runner by byte hash, with --commit as its base")
parser.add_argument("--expected-status", choices=("PASSED", "FAILED"), required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
source_path = args.repo / "tools/compat/logic-pro/run_build_probes.py"
source = (source_path.read_bytes() if args.working_tree else subprocess.check_output([
    "git", "-C", str(args.repo), "show", args.commit + ":tools/compat/logic-pro/run_build_probes.py"]))
with tempfile.TemporaryDirectory(prefix="p003-wave5-interrupt-") as temporary:
    root = Path(temporary)
    runner = root / "exact_runner.py"
    runner.write_bytes(source)
    spec = importlib.util.spec_from_file_location("wave5_exact_runner", runner)
    probes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probes)
    installation = root / "installation"
    installation.mkdir()
    parameters = argparse.Namespace(installation=installation, output=root / "evidence", prefix=root / "prefix")
    propagated = False
    try:
        with mock.patch.object(probes, "Campaign", side_effect=KeyboardInterrupt("independent interruption control")):
            probes.run(parameters)
    except KeyboardInterrupt as error:
        propagated = str(error) == "independent interruption control"
    report = json.loads((parameters.output / "report.json").read_text())
    assert propagated
    assert report["status"] == args.expected_status
    assert report["passed"] is (args.expected_status == "PASSED")
    assert report["cases"] == report["commands"] == []
    assert report["controlled_home"] is None and report["lifecycle"] is None
    if args.expected_status == "FAILED":
        assert report["errors"] == ["KeyboardInterrupt: independent interruption control"]
    else:
        assert report["errors"] == []
    result = {"schema": "darling.p003.wave5-interruption-control.v1", "reviewer": "/root/wave5_source",
              "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_commit": None if args.working_tree else args.commit,
              "base_commit": args.commit,
              "source_kind": "working-tree patch by byte hash" if args.working_tree else "exact committed runner",
              "runner_sha256": hashlib.sha256(source).hexdigest(),
              "control": "KeyboardInterrupt during Campaign construction",
              "original_exception_propagated": propagated, "report_status": report["status"],
              "passed": report["passed"], "errors": report["errors"],
              "cases": report["cases"], "commands": report["commands"],
              "controlled_home": report["controlled_home"], "lifecycle": report["lifecycle"],
              "phase_acceptance": False,
              "scope": "Controller-only interruption control. The interrupted process and absent required cases cannot establish an overall P003 pass."}
if args.working_tree:
    assert source_path.read_bytes() == source
args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps(result, sort_keys=True))
