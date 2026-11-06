#!/usr/bin/env python3
"""Bounded final replay of original hosted evidence and published review inputs.

This reuses the published independent Wave 4 auditors without changing them.
It does not acquire a substitute full clone or declare phase acceptance.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

TESTED = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"
PUBLIC = "ef6e43b6862cba0a8642d38c8e103421e7142369"
BASE = "docs/compat/logic-pro/evidence/P002/requalification-20261105/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--originals", type=Path, required=True)
    parser.add_argument("--reconstructed", type=Path, required=True)
    parser.add_argument("--physical-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    def published(name):
        return subprocess.check_output(["git", "-C", str(args.repo), "show", PUBLIC + ":" + BASE + name])
    manifest = json.loads((args.repo / BASE / "hosted-d58cca51/artifact-manifest.json").read_bytes())
    result = {"reviewer": "/root/wave5_final_replay", "tested_source": TESTED,
              "published_reviews_commit": PUBLIC, "original_artifacts": [], "auditor_commands": [],
              "scope": "Final retained-evidence replay; no replacement acquisition or runtime acceptance"}
    total = 0
    for record in manifest["artifacts"]:
        label = record["label"]
        raw = (args.originals / (label + ".zip")).read_bytes()
        original_receipt = json.loads((args.originals / (label + "-artifact.json")).read_bytes())
        metadata = original_receipt["metadata"]
        assert metadata == record["metadata"], label + " original official metadata differs"
        assert original_receipt["zip_sha256"] == record["original_zip_sha256"]
        assert original_receipt["members"] == {name: {"bytes": item["bytes"], "sha256": item["sha256"]}
            for name, item in record["members"].items()}
        assert len(raw) == record["original_zip_bytes"]
        assert digest(raw) == record["original_zip_sha256"] == metadata["digest"].removeprefix("sha256:")
        assert metadata["workflow_run"]["head_sha"] == TESTED
        with zipfile.ZipFile(args.originals / (label + ".zip")) as archive:
            assert archive.testzip() is None
            assert len(archive.namelist()) == len(set(archive.namelist())) == len(record["members"])
            assert set(archive.namelist()) == set(record["members"])
            for name, member in record["members"].items():
                data = archive.read(name)
                assert data == (args.originals / label / name).read_bytes()
                assert data == (args.reconstructed / label / name).read_bytes()
                assert len(data) == member["bytes"] and digest(data) == member["sha256"]
                total += 1
        summary = json.loads((args.reconstructed / label / "summary.json").read_bytes())
        assert summary["result"] == "PASS" and summary["failures"] == []
        assert summary["implementation_commit"] == TESTED
        expected_tests = 174 if label.startswith("p001") else 115
        assert summary["fixture_tests_executed"] == expected_tests
        fixture = (args.reconstructed / label / "fixture-tests.log").read_text()
        assert re.search(r"^Ran " + str(expected_tests) + r" tests in .+\n\nOK\s*$", fixture, re.M)
        assert not re.search(r"^FAILED|^OK \(|\.\.\. (skipped|expected failure|unexpected success|FAIL|ERROR)", fixture, re.M)
        commands = json.loads((args.reconstructed / label / "commands.json").read_bytes())
        assert all(c["exit_code"] == 0 for c in commands)
        if label.startswith("p001"):
            for command in commands:
                assert digest((args.reconstructed / label / command["log"]).read_bytes()) == command["log_sha256"]
        result["original_artifacts"].append({"label": label, "artifact_id": metadata["id"],
            "run_id": metadata["workflow_run"]["id"], "zip_sha256": digest(raw),
            "zip_bytes": len(raw), "original_members_compared": len(record["members"]),
            "recorded_tests": expected_tests, "commands_with_zero_exit": len(commands)})
    assert total == 70
    result["original_members_compared"] = total
    checksums = json.loads(published("wave4-p001/review-checksums.json"))
    for name, item in checksums.items():
        data = published("wave4-p001/" + name)
        assert len(data) == item["bytes"] and digest(data) == item["sha256"]
    acceptance_bytes = published("wave4-p001/acceptance.json")
    predecessor = json.loads(acceptance_bytes)
    assert predecessor["decision"] == "ACCEPTED" and predecessor["implementation_commit"] == TESTED
    assert predecessor["gates"] == {"G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "PASS"}
    result["P001_predecessor"] = {"published_commit": PUBLIC, "acceptance_sha256": digest(acceptance_bytes),
        "accepted_at_utc": predecessor["accepted_at_utc"], "reviewer": predecessor["reviewer"],
        "published_review_files_rehashed": len(checksums)}
    jobs = json.loads((args.repo / BASE / "hosted-d58cca51/github-jobs-42155822754.json").read_bytes())["jobs"]
    assert len(jobs) == 2 and len({j["runner_id"] for j in jobs}) == 2
    assert {tuple(j["labels"]) for j in jobs} == {("ubuntu-22.04",), ("ubuntu-24.04",)}
    assert all(j["head_sha"] == TESTED and j["status"] == "completed" and j["conclusion"] == "success" for j in jobs)
    result["original_hosted_jobs"] = [{k: j[k] for k in ("id", "runner_id", "labels", "head_sha", "conclusion")} for j in jobs]
    with tempfile.TemporaryDirectory(prefix="p002-wave5-auditors-") as temporary:
        temporary = Path(temporary)
        inputs = {}
        for name in ["wave4-clone-a/audit.py", "wave4-clone-b/replay_review.py", "wave4-clone-b/official-identities.json"]:
            data = published(name)
            target = temporary / Path(name).name
            target.write_bytes(data)
            inputs[name] = digest(data)
        commands = [
            ["python3", "-B", str(temporary / "audit.py"), "--repo", str(args.repo),
             "--zip", str(args.originals / "p002-clone-a.zip"), "--extracted", str(args.originals / "p002-clone-a"),
             "--metadata", str(args.originals / "p002-clone-a-artifact.json"), "--output", str(args.output / "clone-a-replay.json")],
            ["python3", "-B", str(temporary / "replay_review.py"), "--repo", str(args.repo),
             "--raw", str(args.originals), "--physical-root", str(args.physical_root),
             "--output", str(args.output / "cross-host-replay.json")],
        ]
        for command in commands:
            process = subprocess.run(command, text=True, capture_output=True)
            result["auditor_commands"].append({"argv": command, "exit_code": process.returncode,
                "stdout": process.stdout, "stderr": process.stderr})
            print(process.stdout, end="")
            assert process.returncode == 0, process.stderr
        result["unchanged_published_auditor_sha256"] = inputs
    result["result"] = "PASS"
    result["completed_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (args.output / "replay-results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: all 70 original ZIP, original extracted, and reconstructed members match; published P001 predecessor and two original hosted jobs verified")


if __name__ == "__main__":
    main()
