#!/usr/bin/env python3
"""Independent immutable-object LFS and standard-CRLF oracle; no project imports."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

POINTER = re.compile(rb"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize ([0-9]+)\n")
ENDPOINT = "https://git-lfs.darlinghq.org/lubos/darling-swift"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-hydrated", action="store_true")
    args = parser.parse_args()
    root = args.repo.resolve(strict=True)
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                       GIT_ATTR_NOSYSTEM="1", GIT_NO_REPLACE_OBJECTS="1")
    commands = []
    errors = []

    def git(repo: Path, *parts: str, input_bytes: bytes | None = None, absent_ok: bool = False) -> bytes:
        command = ["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
                   "-c", "core.fsmonitor=false", "-c", "core.attributesFile=/dev/null",
                   "-C", str(repo), *parts]
        result = subprocess.run(command, env=environment, input=input_bytes, capture_output=True, timeout=180)
        commands.append({"argv": command, "exit_code": result.returncode,
                         "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                         "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
        if result.returncode and not (absent_ok and result.returncode == 1):
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return result.stdout

    head = git(root, "rev-parse", "HEAD").decode().strip()
    native_status = git(root, "submodule", "status", "--recursive").decode()
    repositories = [(".", head)]
    for line in native_status.splitlines():
        match = re.fullmatch(r" ([0-9a-f]{40}) ([^ ]+)(?: \(.*\))?", line)
        if not match:
            raise RuntimeError("Native recursive status is missing/mismatched/conflicted: " + line)
        repositories.append((match[2], match[1]))
    if len(repositories) != 161 or len({owner for owner, _ in repositories}) != 161:
        raise RuntimeError("Expected exactly 161 unique repositories from native Git traversal")

    pointers = []
    endpoints = []
    for owner, commit in repositories:
        repo = root if owner == "." else root / owner
        output = git(repo, "grep", "-I", "-l", "-z", "-e",
                     "^version https://git-lfs.github.com/spec/v1$", "HEAD", "--", absent_ok=True)
        candidates = [item for item in output.split(b"\0") if item]
        if candidates:
            config = git(repo, "show", "HEAD:.lfsconfig")
            endpoint = git(repo, "config", "--no-includes", "--file", "-", "--get", "lfs.url",
                           input_bytes=config).decode().strip()
            endpoint_blob = git(repo, "rev-parse", "HEAD:.lfsconfig").decode().strip()
            if owner != "src/external/swift" or endpoint != ENDPOINT:
                errors.append("Unexpected LFS owner or committed acquisition endpoint: " + owner)
            endpoints.append({"owner": owner, "commit": commit, "endpoint": endpoint,
                              "config_blob": endpoint_blob, "config_sha256": hashlib.sha256(config).hexdigest(),
                              "config_text": config.decode()})
        for candidate in candidates:
            prefix, path_bytes = candidate.split(b":", 1)
            if prefix != b"HEAD":
                raise RuntimeError("Invalid native Git grep object prefix")
            relative = os.fsdecode(path_bytes)
            raw = git(repo, "show", "HEAD:" + relative)
            match = POINTER.fullmatch(raw)
            if not match:
                errors.append("Malformed or unsupported LFS candidate: " + owner + "/" + relative)
                continue
            pointer_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            reported_blob = git(repo, "rev-parse", "HEAD:" + relative).decode().strip()
            if pointer_blob != reported_blob:
                raise RuntimeError("Native pointer bytes do not reproduce the committed blob ID")
            path = repo / relative
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                errors.append("LFS target is not a physical regular file: " + str(path))
                continue
            materialized = path.read_bytes()
            physical_sha256 = hashlib.sha256(materialized).hexdigest()
            expected_sha256 = match[1].decode()
            expected_size = int(match[2])
            matched = len(materialized) == expected_size and physical_sha256 == expected_sha256
            row = {"owner": owner, "repository_commit": commit, "repository_path": relative,
                   "path": owner + "/" + relative, "pointer_git_blob": pointer_blob,
                   "pointer_bytes": len(raw), "pointer_sha256": hashlib.sha256(raw).hexdigest(),
                   "oid_sha256": expected_sha256, "payload_bytes": expected_size,
                   "physical_bytes": len(materialized), "physical_sha256": physical_sha256,
                   "physical_mode": "100755" if info.st_mode & stat.S_IXUSR else "100644",
                   "payload_matches": matched, "still_pointer_text": materialized == raw}
            pointers.append(row)
            if args.require_hydrated and not matched:
                errors.append("Missing or invalid required payload: " + row["path"])
    if len(pointers) != 44 or sum(row["payload_bytes"] for row in pointers) != 16128448:
        errors.append("Expected exactly 44 immutable LFS pointers and 16128448 payload bytes")

    crlf = []
    libffi = root / "src/external/libffi"
    for suffix in ("sln", "vcxproj", "vcxproj.filters", "vcxproj.user"):
        relative = "msvc_build/aarch64/Ffi_staticLib." + suffix
        blob = git(libffi, "show", "HEAD:" + relative)
        physical = (libffi / relative).read_bytes()
        attrs = git(libffi, "check-attr", "--cached", "-z", "text", "eol", "filter", "ident",
                    "working-tree-encoding", "--", relative).split(b"\0")
        attribute_values = {attrs[i + 1].decode(): attrs[i + 2].decode() for i in range(0, len(attrs) - 1, 3)}
        correct = (attribute_values == {"text": "set", "eol": "crlf", "filter": "unspecified",
                                       "ident": "unspecified", "working-tree-encoding": "unspecified"}
                   and b"\r" not in blob and physical == blob.replace(b"\n", b"\r\n"))
        crlf.append({"path": "src/external/libffi/" + relative,
                     "committed_blob": git(libffi, "rev-parse", "HEAD:" + relative).decode().strip(),
                     "blob_bytes": len(blob), "physical_bytes": len(physical),
                     "attributes": attribute_values, "exact_committed_crlf_checkout": correct})
        if not correct:
            errors.append("Unexpected physical CRLF materialization: " + relative)

    report = {"schema_version": 1, "reviewer": "/root/p002_acceptance",
              "reviewed_at": datetime.now(timezone.utc).isoformat(), "tested_commit": head,
              "result": "PASS" if not errors else "FAIL", "errors": errors,
              "scope": "Independent native-Git discovery and raw SHA-256 verification; no implementation imports",
              "require_hydrated": args.require_hydrated, "repositories": len(repositories),
              "lfs_pointer_files": len(pointers), "payload_bytes": sum(x["payload_bytes"] for x in pointers),
              "verified_payloads": sum(x["payload_matches"] for x in pointers),
              "endpoints": endpoints, "pointers": pointers, "standard_crlf": crlf, "commands": commands}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("commands", "pointers", "endpoints", "standard_crlf")}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
