#!/usr/bin/env python3
"""Transport an original public CI toolchain ZIP in bounded, lossless pieces.

The concatenated pieces must match GitHub's original artifact size and SHA-256.
This creates no new build evidence and grants no phase acceptance. It permits
independent reviewers whose download clients limit individual artifact sizes to
inspect the same original bytes, including the original ZIP member metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

from check_gates import SafeArtifactRedirectHandler

PART_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * PART_BYTES
WORKFLOWS = {
    ".github/workflows/phase3-build.yml": "p003-toolchain-",
    ".github/workflows/compat.yml": "p004-toolchain-",
}


def json_get(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "User-Agent": "darling-original-artifact-transport",
    })
    opener = urllib.request.build_opener(SafeArtifactRedirectHandler())
    with opener.open(request, timeout=30) as response:
        return json.load(response)


def validate_origin(repository: str, run_id: int, run: dict, artifact: dict) -> None:
    prefix = WORKFLOWS.get(run.get("path"))
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or type(run_id) is not int or run_id <= 0
            or run.get("id") != run_id or not prefix
            or run.get("event") != "push" or run.get("head_branch") != "main"
            or run.get("status") != "completed"
            or run.get("repository", {}).get("full_name") != repository
            or run.get("head_repository", {}).get("full_name") != repository
            or not re.fullmatch(r"[0-9a-f]{40}", run.get("head_sha", ""))):
        raise ValueError("Only completed, same-repository main-push P003/P004 runs may be exported")
    identity = artifact.get("workflow_run", {})
    size = artifact.get("size_in_bytes")
    if (type(artifact.get("id")) is not int or artifact["id"] <= 0
            or not re.fullmatch(re.escape(prefix) + r"[0-9a-f]{40}", artifact.get("name", ""))
            or artifact.get("expired") is not False
            or identity.get("id") != run_id or identity.get("head_sha") != run["head_sha"]
            or type(size) is not int or not 0 < size <= MAX_ARCHIVE_BYTES
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact.get("digest", ""))):
        raise ValueError("Missing, expired, oversized or mismatched original toolchain artifact")


def split_original(archive: Path, output: Path, origin: dict, *, part_bytes: int = PART_BYTES) -> dict:
    """Verify the original before publishing any transport parts."""
    if type(part_bytes) is not int or not 0 < part_bytes <= PART_BYTES:
        raise ValueError("Invalid bounded part size")
    artifact = origin["artifact"]
    h = hashlib.sha256()
    size = 0
    with archive.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    if size != artifact["size_in_bytes"] or "sha256:" + h.hexdigest() != artifact["digest"]:
        raise ValueError("Downloaded bytes differ from GitHub's original artifact metadata")
    output.mkdir(parents=True, exist_ok=False)
    parts = []
    with archive.open("rb") as source:
        ordinal = 0
        while True:
            chunk = source.read(min(part_bytes, 1024 * 1024))
            if not chunk:
                break
            directory = output / f"part-{ordinal:03d}"
            directory.mkdir()
            target = directory / "original.zip.part"
            part_hash = hashlib.sha256()
            part_size = 0
            with target.open("xb") as stream:
                while chunk:
                    stream.write(chunk)
                    part_hash.update(chunk)
                    part_size += len(chunk)
                    remaining = part_bytes - part_size
                    if not remaining:
                        break
                    chunk = source.read(min(remaining, 1024 * 1024))
            parts.append({"ordinal": ordinal, "path": target.relative_to(output).as_posix(),
                          "size_bytes": part_size, "sha256": part_hash.hexdigest()})
            ordinal += 1
    result = {"schema": "darling.original-artifact-transport.v1",
              "status": "TRANSPORT_ONLY", "phase_acceptance": "NOT_EVALUATED",
              "origin": origin, "original_size_bytes": size,
              "original_sha256": h.hexdigest(), "parts": parts,
              "reassembly": "Concatenate original.zip.part files in ordinal order; verify the original GitHub digest before opening the ZIP."}
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (output / "index.json").write_text(raw)
    for part in parts:
        (output / part["path"]).with_name("index.json").write_text(raw)
    return result


def export(repository: str, run_id: int, output: Path) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or run_id <= 0:
        raise ValueError("Invalid repository/run identity")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("Authenticated GitHub read access is required")
    base = f"https://api.github.com/repos/{repository}"
    run = json_get(f"{base}/actions/runs/{run_id}", token)
    prefix = WORKFLOWS.get(run.get("path"))
    if prefix is None:
        raise ValueError("Run is outside the public synthetic toolchain workflows")
    artifacts = []
    page = 1
    while True:
        batch = json_get(f"{base}/actions/runs/{run_id}/artifacts?per_page=100&page={page}", token)
        records = batch["artifacts"]
        artifacts.extend(a for a in records if a.get("name", "").startswith(prefix))
        if len(records) < 100:
            break
        page += 1
    if len(artifacts) != 1:
        raise ValueError("Original toolchain artifact is missing or ambiguous")
    artifact = artifacts[0]
    validate_origin(repository, run_id, run, artifact)
    request = urllib.request.Request(f"{base}/actions/artifacts/{artifact['id']}/zip", headers={
        "Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
        "User-Agent": "darling-original-artifact-transport",
    })
    opener = urllib.request.build_opener(SafeArtifactRedirectHandler())
    with tempfile.TemporaryDirectory(prefix="original-artifact-") as temporary:
        archive = Path(temporary) / "original.zip"
        size = 0
        with opener.open(request, timeout=120) as response, archive.open("xb") as stream:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                size += len(chunk)
                if size > artifact["size_in_bytes"]:
                    raise ValueError("Original download exceeds its authenticated byte count")
                stream.write(chunk)
        origin = {"repository": repository, "run_id": run_id,
                  "run_attempt": run["run_attempt"], "publication_commit": run["head_sha"],
                  "workflow_path": run["path"], "conclusion": run.get("conclusion"),
                  "artifact": {k: artifact[k] for k in
                               ("id", "name", "digest", "size_in_bytes", "created_at", "expires_at")}}
        return split_original(archive, output, origin)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = export(args.repository, args.run_id, args.output)
    print(json.dumps({"status": result["status"], "part_count": len(result["parts"]),
                      "original_sha256": result["original_sha256"]}, sort_keys=True))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as stream:
            stream.write(f"part_count={len(result['parts'])}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
