#!/usr/bin/env python3
"""Independently bind the corrected P003 preflight originals and docs boundary."""
import argparse
import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile


CANDIDATE = "4622a9396c5c9fbe0014bdf6a2f695dcc491233c"
DOCS_COMMIT = "1e71e36b1e5d6d37921b19bed1d74e1549526c08"
RUN_ID = 42180484781
PREFIX = "docs/compat/logic-pro/evidence/P003/requalification-20261106/"
ATTEMPT = PREFIX + "attempt-4622a93/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--originals", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def git(*argv):
        return subprocess.check_output(["git", "-C", str(args.repo), *argv])

    def blob(commit, path):
        return git("show", commit + ":" + path)

    def protected_tree(commit):
        result = {}
        for entry in git("ls-tree", "-r", "-z", commit).split(b"\0"):
            if not entry:
                continue
            identity, path = entry.split(b"\t", 1)
            name = path.decode()
            if name != "README.md" and not name.startswith("docs/compat/logic-pro/evidence/"):
                result[name] = identity.decode()
        return result

    before, after = protected_tree(CANDIDATE), protected_tree(DOCS_COMMIT)
    assert before == after
    readme_diff = git("diff", CANDIDATE, DOCS_COMMIT, "--", "README.md")
    changed = git("diff", "--name-only", CANDIDATE, DOCS_COMMIT).decode().splitlines()
    assert all(x == "README.md" or x.startswith("docs/compat/logic-pro/evidence/") for x in changed)

    metadata_bytes = args.metadata.read_bytes()
    if metadata_bytes[:2] == b"\x1f\x8b":
        metadata_bytes = gzip.decompress(metadata_bytes)
    assert sha(metadata_bytes) == "9095a5cad655f2e10d759247832024e603f4ff228804d1f6952fc2df133ef006"
    metadata = json.loads(metadata_bytes)
    jobs = {job["id"]: job for job in metadata["jobs"]["jobs"]}
    for number in (127768690555, 127768690781):
        job = jobs[number]
        assert (job["run_id"], job["head_sha"], job["status"], job["conclusion"]) == (RUN_ID, CANDIDATE, "completed", "success")
    artifacts = {artifact["id"]: artifact for artifact in metadata["artifacts"]["artifacts"]}
    fixture_artifact = artifacts[13485460372]
    fixture_zip = blob(DOCS_COMMIT, ATTEMPT + "fixtures.zip")
    assert len(fixture_zip) == fixture_artifact["size_in_bytes"] == 11686
    assert sha(fixture_zip) == "155fcbc2432969eca8248a4f8166c1d55c2e584a95dce3650f8793bd77cf00ed"
    assert fixture_artifact["digest"] == "sha256:" + sha(fixture_zip)
    assert fixture_artifact["workflow_run"]["head_sha"] == CANDIDATE
    assert fixture_artifact["workflow_run"]["id"] == RUN_ID
    members, suites = {}, {}
    with zipfile.ZipFile(io.BytesIO(fixture_zip)) as archive:
        assert len(archive.infolist()) == 4
        assert set(archive.namelist()) == {"baseline.log", "submodules.log", "build.log", "summary.json"}
        assert archive.testzip() is None
        summary = json.loads(archive.read("summary.json"))
        for member in archive.infolist():
            raw = archive.read(member)
            members[member.filename] = {"bytes": len(raw), "sha256": sha(raw), "CRC32": f"{member.CRC:08x}"}
            if args.originals:
                assert (args.originals / "fixtures" / member.filename).read_bytes() == raw
        for suite, expected in (("baseline", 174), ("submodules", 115), ("build", 201)):
            text = archive.read(suite + ".log").decode()
            named = re.findall(r"^(test_\w+) \(([^\n)]+)\) \.\.\.", text, re.M)
            assert len(named) == len(set(named)) == expected
            terminal = re.findall(r"^Ran (\d+) tests in ([0-9.]+)s\n\nOK\s*\Z", text, re.M)
            assert len(terminal) == 1 and int(terminal[0][0]) == expected
            assert not re.search(r"^FAILED|^OK \(|\.\.\. (skipped|expected failure|unexpected success)", text, re.M)
            assert next(item for item in summary if item["suite"] == suite) == {"suite": suite, "count": expected, "exit_code": 0}
            suites[suite] = {"unique_named_cases": expected, "seconds": float(terminal[0][1]), "terminal": "OK", "skipped": 0}
        assert len(summary) == 3
        assert ("test_initialization_abort_records_failure_and_preserves_original_abort", "test_probes.EvidenceTests") in re.findall(r"^(test_\w+) \(([^\n)]+)\) \.\.\.", archive.read("build.log").decode(), re.M)

    compressed_log = blob(DOCS_COMMIT, ATTEMPT + "toolchain-job.log.gz")
    log_bytes = gzip.decompress(compressed_log)
    assert sha(log_bytes) == "a75ed922fa945e31cf7bdd9ff5905b6ee52a2b0914c6d2db2b12d52343ff0ab3"
    log = log_bytes.decode("utf-8-sig")
    if args.originals:
        assert (args.originals / "fixtures.zip").read_bytes() == fixture_zip
        assert (args.originals / "toolchain-job.log").read_bytes() == log_bytes
    assert re.search(r"^\S+Z " + CANDIDATE + r"$", log, re.M)
    assert "P003 retained frozen toolchain: PASS" in log
    records = []
    for line in log.splitlines():
        timestamp, _, payload = line.partition(" ")
        if payload.startswith('{"origin":'):
            records.append((timestamp, json.loads(payload)))
    assert len(records) == 1
    verified_at, origin = records[0]
    assert origin == json.loads(blob(DOCS_COMMIT, ATTEMPT + "original-retained-origin.json"))
    assert origin == json.loads(blob(DOCS_COMMIT, PREFIX + "attempt-b6f4d9b/original-retained-origin.json"))
    manifest = json.loads(blob(CANDIDATE, "docs/compat/logic-pro/retained-toolchain.json"))
    assert origin["origin"] == manifest and origin["status"] == "PASSED"
    assert sha(blob(CANDIDATE, "docs/compat/logic-pro/toolchain.lock.json")) == manifest["committed_lock_sha256"]
    assert sha(blob(CANDIDATE, "ci/logic-pro/Dockerfile.p003")) == manifest["recipe_sha256"]
    assert set(origin["original_files_sha256"]) == {"SHA256SUMS", "base-pull.log", "toolchain-build.log", "toolchain-image.tar.gz", "toolchain.lock.json"}
    toolchain_artifact = artifacts[13485057920]
    assert toolchain_artifact["workflow_run"]["head_sha"] == CANDIDATE
    assert toolchain_artifact["workflow_run"]["id"] == RUN_ID
    assert "SHA256 digest of uploaded artifact zip is " + toolchain_artifact["digest"].removeprefix("sha256:") in log
    assert "Final size is " + str(toolchain_artifact["size_in_bytes"]) + " bytes. Artifact ID is 13485057920" in log

    receipt = {
        "schema": "darling.p003.wave5-corrected-preflight-review.v1",
        "reviewer": "/root/wave5_source",
        "recorded_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": CANDIDATE,
        "source_tree": git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
        "run_id": RUN_ID,
        "original_metadata": {"bytes": len(metadata_bytes), "sha256": sha(metadata_bytes)},
        "documentation_boundary": {"commit": DOCS_COMMIT, "protected_tree_entries_unchanged": len(before), "all_changed_paths_are_readme_or_evidence": True, "README_diff_sha256": sha(readme_diff)},
        "original_fixture_zip": {"artifact_id": 13485460372, "bytes": len(fixture_zip), "sha256": sha(fixture_zip), "CRC_checked_members": members, "suites": suites, "abort_regression_present": True},
        "toolchain": {"raw_job_log_bytes": len(log_bytes), "raw_job_log_sha256": sha(log_bytes), "gzip_sha256": sha(compressed_log), "hosted_verification_time": verified_at, "hosted_origin": origin, "published_receipt_matches_raw_log": True, "frozen_inputs_match_prior_acquisition": True, "current_artifact_id": 13485057920, "current_artifact_bytes": toolchain_artifact["size_in_bytes"], "current_artifact_sha256": toolchain_artifact["digest"].removeprefix("sha256:"), "complete_image_zip_locally_verified": False},
        "status": "PREFLIGHT_VERIFIED; FINAL_SOURCE_EVIDENCE_PENDING",
        "current_G1_G4": "PENDING",
        "phase_acceptance": False,
        "limitations": ["The complete image ZIP exceeds the connector download limit; this verifies the hosted raw restoration record, not local full-image bytes/CRCs.", "Fresh complete A/B source, codegen, compile and install evidence has not yet been supplied to this reviewer."]
    }
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "source_commit": CANDIDATE, "fixture_counts": {k: v["unique_named_cases"] for k, v in suites.items()}, "protected_tree_entries_unchanged": len(before), "output_sha256": sha(args.output.read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
