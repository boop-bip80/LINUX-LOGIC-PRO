#!/usr/bin/env python3
"""Read every original build ZIP member and bind its extracted copy exactly.

This reviewer-owned helper does not extract, rewrite, execute or repair any
producer artifact. Its receipt alone does not establish a build gate.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile
import zlib


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def require(condition: bool, description: str) -> None:
    if not condition:
        raise ValueError(description)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--extracted", required=True, type=Path)
    parser.add_argument("--artifact-id", required=True, type=int)
    parser.add_argument("--expected-bytes", required=True, type=int)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--job-id", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(stat.S_ISREG(args.archive.lstat().st_mode), "Original ZIP is not regular")
    require(args.archive.stat().st_size == args.expected_bytes, "Original ZIP byte count differs")
    actual = digest(args.archive)
    require(actual == args.expected_sha256, "Original ZIP SHA-256 differs")
    members = []
    names = set()
    with zipfile.ZipFile(args.archive) as archive:
        for member in archive.infolist():
            name = member.filename
            path = PurePosixPath(name)
            require(name not in names and not path.is_absolute() and ".." not in path.parts
                    and str(path) == name.rstrip("/") and path.parts,
                    "Duplicate or unsafe original ZIP path: " + name)
            names.add(name)
            target = args.extracted / path
            require(not target.is_symlink(), "Extracted member is redirected: " + name)
            kind = stat.S_IFMT(member.external_attr >> 16)
            if member.is_dir():
                require(target.is_dir() and kind in (0, stat.S_IFDIR), "Invalid directory: " + name)
                continue
            require(kind in (0, stat.S_IFREG) and stat.S_ISREG(target.lstat().st_mode),
                    "Original or extracted member is not regular: " + name)
            value = hashlib.sha256()
            crc, size = 0, 0
            with archive.open(member) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    value.update(block)
                    crc = zlib.crc32(block, crc)
                    size += len(block)
            require(size == member.file_size and crc == member.CRC, "Size/CRC mismatch: " + name)
            member_hash = value.hexdigest()
            require(target.stat().st_size == size and digest(target) == member_hash,
                    "Extracted bytes differ from original ZIP: " + name)
            members.append({"name": name, "bytes": size, "sha256": member_hash,
                            "crc32": f"{crc:08x}"})
    extracted = {p.relative_to(args.extracted).as_posix()
                 for p in args.extracted.rglob("*") if p.is_file() or p.is_symlink()}
    require(extracted == {row["name"] for row in members}, "Extracted file inventory differs")
    report = {"schema": "darling.p003.wave4.original-archive.v1",
              "reviewer": "/root/wave4_build", "non_author": True,
              "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "implementation": args.commit, "run_id": args.run_id, "job_id": args.job_id,
              "artifact_id": args.artifact_id, "artifact_bytes": args.expected_bytes,
              "artifact_sha256": actual, "archive": str(args.archive),
              "extracted": str(args.extracted), "verified_members": len(members),
              "members": members, "status": "ALL_ORIGINAL_MEMBERS_MATCH",
              "identity_source": "Coordinator supplied original artifact identity; final official metadata must independently corroborate before two-host acceptance.",
              "phase_acceptance": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "members": len(members),
                      "artifact_sha256": actual, "receipt_sha256": digest(args.output)}))


if __name__ == "__main__":
    main()
