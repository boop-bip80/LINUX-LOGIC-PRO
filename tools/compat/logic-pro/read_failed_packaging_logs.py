#!/usr/bin/env python3
"""Preserve original failed public packaging logs and bounded error context.

Large compiler logs can exceed interactive log clients' response limits. The
raw bytes remain intact inside gzip files; the excerpts are navigation aids,
not build evidence or a compatibility verdict.
"""
from __future__ import annotations

import argparse
from collections import deque
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

from check_gates import SafeArtifactRedirectHandler
from export_original_artifact import json_get

ERROR_LINE = re.compile(r"error:|fatal|FAILED|Killed|No space left|undefined reference|Error [1-9]", re.I)


def preserve_stream(source, destination: Path) -> dict:
    digest = hashlib.sha256()
    size = 0
    count = 0
    errors = deque(maxlen=100)
    tail = deque(maxlen=60)
    with destination.open("xb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            for raw in source:
                digest.update(raw)
                size += len(raw)
                count += 1
                compressed.write(raw)
                line = raw.decode("utf-8", "replace").rstrip("\r\n")
                excerpt = {"line": count, "text": line[:4096], "truncated": len(line) > 4096}
                tail.append(excerpt)
                if ERROR_LINE.search(line):
                    errors.append(excerpt)
    compressed_hash = hashlib.sha256()
    with destination.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            compressed_hash.update(chunk)
    return {"file": destination.name, "raw_size_bytes": size, "raw_sha256": digest.hexdigest(),
            "gzip_size_bytes": destination.stat().st_size, "gzip_sha256": compressed_hash.hexdigest(),
            "line_count": count, "error_context": list(errors), "tail": list(tail)}


def validate_run(repository: str, run_id: int, run: dict) -> None:
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or type(run_id) is not int or run_id <= 0 or run.get("id") != run_id
            or run.get("path") != ".github/workflows/actions.yaml"
            or run.get("event") != "push" or run.get("head_branch") != "main"
            or run.get("status") != "completed" or run.get("conclusion") != "failure"
            or run.get("repository", {}).get("full_name") != repository
            or run.get("head_repository", {}).get("full_name") != repository
            or not re.fullmatch(r"[0-9a-f]{40}", run.get("head_sha", ""))):
        raise ValueError("Only failed same-repository main-push Darling CI runs may be read back")


def readback(repository: str, run_id: int, output: Path) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or run_id <= 0:
        raise ValueError("Invalid repository/run identity")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("Authenticated GitHub Actions read access is required")
    base = f"https://api.github.com/repos/{repository}"
    run = json_get(f"{base}/actions/runs/{run_id}", token)
    validate_run(repository, run_id, run)
    jobs = {}
    page = 1
    while True:
        # Include original failed jobs when only another job was re-run.
        batch = json_get(f"{base}/actions/runs/{run_id}/jobs?filter=all&per_page=100&page={page}", token)
        for job in batch["jobs"]:
            if job.get("conclusion") == "failure":
                if (type(job.get("id")) is not int or job["id"] <= 0
                        or job.get("run_id") != run_id or job.get("head_sha") != run["head_sha"]):
                    raise ValueError("Failed job identity does not belong to the requested source")
                jobs[job["id"]] = job
        if len(batch["jobs"]) < 100:
            break
        page += 1
    if not jobs or len(jobs) > 20:
        raise ValueError("Failed job set is empty or exceeds the bounded diagnostic scope")
    output.mkdir(parents=True, exist_ok=False)
    records = []
    opener = urllib.request.build_opener(SafeArtifactRedirectHandler())
    for job_id, job in sorted(jobs.items()):
        request = urllib.request.Request(f"{base}/actions/jobs/{job_id}/logs", headers={
            "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
            "User-Agent": "darling-failed-packaging-log-readback",
        })
        with opener.open(request, timeout=120) as source:
            record = preserve_stream(source, output / f"job-{job_id}.log.gz")
        record.update({"job_id": job_id, "job_name": job["name"], "conclusion": "failure",
                       "run_attempt": job.get("run_attempt"), "completed_at": job.get("completed_at")})
        records.append(record)
    result = {"schema": "darling.failed-packaging-log-readback.v1",
              "status": "FAILED_JOB_LOGS_RETRIEVED", "phase_acceptance": "NOT_EVALUATED",
              "repository": repository, "run_id": run_id, "source_commit": run["head_sha"],
              "workflow_path": run["path"], "jobs": records}
    (output / "index.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = readback(args.repository, args.run_id, args.output)
    print(json.dumps({"status": result["status"], "failed_jobs": len(result["jobs"]),
                      "run_id": args.run_id}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
