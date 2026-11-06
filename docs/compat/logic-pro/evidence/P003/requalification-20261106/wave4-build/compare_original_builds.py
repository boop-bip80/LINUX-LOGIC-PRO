#!/usr/bin/env python3
"""Bind the two independently read original build receipts to official metadata."""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metadata_path = args.run / "metadata-final.json"
    metadata = read(metadata_path)
    jobs = metadata["jobs"]["jobs"]
    artifacts = metadata["artifacts"]["artifacts"]
    archives, builds, matching_jobs, matching_artifacts = [], [], [], []
    for host in ("a", "b"):
        archive = read(args.receipts / ("final-" + host + "-archive.json"))
        build = read(args.receipts / ("final-" + host + "-build.json"))
        require(build["build_id"] == host and build["status"] == "OWNED_SOURCE_BUILD_LIFECYCLE_CHECKS_PASSED",
                "Wrong or incomplete independent host review")
        require(build["archive_receipt_sha256"] == sha(args.receipts / ("final-" + host + "-archive.json")),
                "Host review receipt binding changed")
        artifact = next(row for row in artifacts if row["id"] == archive["artifact_id"])
        require(artifact["size_in_bytes"] == archive["artifact_bytes"]
                and artifact["digest"] == "sha256:" + archive["artifact_sha256"]
                and artifact["name"] == "p003-build-" + host + "-" + archive["implementation"]
                and artifact["workflow_run"]["head_sha"] == archive["implementation"]
                and artifact["workflow_run"]["id"] == archive["run_id"], "Official artifact identity differs")
        job = next(row for row in jobs if row["id"] == archive["job_id"])
        require(job["head_sha"] == archive["implementation"] and job["run_id"] == archive["run_id"]
                and job["name"] == "Clean build, install and runtime probes " + host
                and job["status"] == "completed" and job["conclusion"] == "success",
                "Official original build job differs or failed")
        for number in (2, 3, 5, 6, 7):
            step = next(row for row in job["steps"] if row["number"] == number)
            require(step["conclusion"] == "success", "Source/build/artifact publication step failed")
        archives.append(archive)
        builds.append(build)
        matching_jobs.append(job)
        matching_artifacts.append(artifact)
    commit, run_id = archives[0]["implementation"], archives[0]["run_id"]
    require(archives[1]["implementation"] == commit and archives[1]["run_id"] == run_id,
            "The two originals are not the same candidate/run")
    require(len(jobs) == 6 and all(row["head_sha"] == commit and row["run_id"] == run_id
                                 and row["conclusion"] == "success" for row in jobs),
            "Current campaign metadata is incomplete")
    require(matching_jobs[0]["runner_id"] != matching_jobs[1]["runner_id"], "Builds reused one runner identity")
    require(builds[0]["summary"]["host_kernel"]["node"] != builds[1]["summary"]["host_kernel"]["node"],
            "Builds reused one container identity")
    for key in ("source_commit", "toolchain_sha256", "source_lock_sha256", "configuration",
                "installation_prefix", "source_date_epoch"):
        require(builds[0]["summary"][key] == builds[1]["summary"][key], "Build input mismatch: " + key)
    for key in ("source", "actual_build", "codegen"):
        require(builds[0][key] == builds[1][key], "Independent source/build/codegen observations differ: " + key)
    hashes = [{row["name"]: row["sha256"] for row in archive["members"]} for archive in archives]
    require(set(hashes[0]) == set(hashes[1]), "Original evidence member sets differ")
    same_raw = {}
    for name in ("toolchain.lock.json", "source-lock-verification.json", "submodule-heads.txt",
                 "source-classifications.json", "source-classifications.log", "source-status-before.txt",
                 "source-status-after.txt", "compile_commands.json"):
        require(hashes[0][name] == hashes[1][name], "Critical raw input/configuration differs: " + name)
        same_raw[name] = hashes[0][name]
    cache_text, cache_identity = [], []
    for host, build in zip(("a", "b"), builds):
        raw = (args.run / ("build-" + host) / "CMakeCache.txt").read_text()
        sites = re.findall(r"^SITE:STRING=(.*)$", raw, re.M)
        require(sites == [build["summary"]["host_kernel"]["node"]],
                "CMake SITE does not identify the actual container")
        cache_text.append(raw)
        cache_identity.append(re.sub(r"^SITE:STRING=.*$", "SITE:STRING=<observed container>", raw, flags=re.M))
    require(cache_identity[0] == cache_identity[1], "CMake cache differs beyond exact observed SITE hostname")
    cache_delta = {"rule": "Only the single SITE:STRING value may identify its independently observed container; all other cache bytes remain exact.",
                   "raw_sha256": {host: values["CMakeCache.txt"] for host, values in zip(("a", "b"), hashes)},
                   "site_values": {host: build["summary"]["host_kernel"]["node"] for host, build in zip(("a", "b"), builds)},
                   "exact_diff": "".join(difflib.unified_diff(cache_text[0].splitlines(keepends=True),
                                                              cache_text[1].splitlines(keepends=True),
                                                              fromfile="A/CMakeCache.txt", tofile="B/CMakeCache.txt"))}
    ownership = [row["nonce"] for build in builds for row in build["installation_lifecycle"]["owners"]]
    challenges = [row["nonce"] for build in builds for row in build["installation_lifecycle"]["campaigns"]]
    require(len(set(ownership)) == 4 and len(set(challenges)) == 4, "Cross-host lifecycle state was reused")
    shapes = []
    for host in ("a", "b"):
        install = read(args.run / ("build-" + host) / "install-first.json")
        shapes.append([{key: value for key, value in row.items() if key not in ("sha256", "size")}
                       for row in install["entries"]])
    require(shapes[0] == shapes[1], "Cross-host installed path/type/mode/link layout differs")
    observed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = {"schema": "darling.p003.wave4.paired-build-review.v1", "reviewer": "/root/wave4_build",
              "non_author": True, "observed_at": observed_at, "implementation": commit, "run_id": run_id,
              "official_metadata_sha256": sha(metadata_path),
              "original_artifact_metadata": matching_artifacts, "original_build_jobs": matching_jobs,
              "same_raw_input_and_configuration_sha256": same_raw,
              "cmake_cache_host_observation": cache_delta,
              "source_build_codegen_observations_identical": True,
              "distinct_hosted_runners_and_containers": True,
              "four_distinct_installation_ownership_nonces": ownership,
              "four_distinct_runtime_challenges": challenges,
              "within_host_reinstall_entries": [build["installation_lifecycle"]["installed_entries"] for build in builds],
              "cross_host_path_type_mode_link_layout_equal": True,
              "build_receipts_sha256": {host: sha(args.receipts / ("final-" + host + "-build.json")) for host in ("a", "b")},
              "archive_receipts_sha256": {host: sha(args.receipts / ("final-" + host + "-archive.json")) for host in ("a", "b")},
              "review_helpers_sha256": {name: sha(Path(__file__).with_name(name)) for name in
                                         ("verify_original_archive.py", "audit_original_build.py", "compare_original_builds.py")},
              "verdict": "APPROVED_SOURCE_FROZEN_TOOLCHAIN_TWO_FRESH_BUILDS_AND_PER_HOST_LIFECYCLE",
              "phase_acceptance": False,
              "limitations": ["G1 package-byte nondeterminism enumeration is reviewed separately.",
                              "G2/G3 live framework/runtime outputs and source-free replay are reviewed separately.",
                              "G4 full phase decision also requires the independent replay review.",
                              "Large frozen image ZIP was not locally replayed; exact hosted restoration and both host observations were verified.",
                              "Source-built linker binary is not archived; only original per-host hashes/version outputs are available.",
                              "Kernel mount namespace numbers may be reused after teardown; fresh state is bound by owner nonce, runtime challenge, prefix/HOME and server PID/starttime, not global namespace-number uniqueness."]}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"verdict": report["verdict"], "observed_at": observed_at,
                      "receipt_sha256": sha(args.output), "source": commit, "run": run_id}))


if __name__ == "__main__":
    main()
