#!/usr/bin/env python3
"""Verify both complete P001/P002 evidence archives from a fresh Git checkout."""

import argparse
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile


HISTORICAL = (
    "docs/compat/logic-pro/evidence/P002/p001-requalification",
    "raw-reports.tar.xz",
    9667936,
    "5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d",
)
CURRENT = (
    "docs/compat/logic-pro/evidence/P002/qualification-b628085",
    "p001-p002-b628085-raw-reports.tar.xz",
    9594676,
    "8a614792dc1558ecc9584d9e00013f8a6c02cdc2dd7f00e570117e3b8e74e7a5",
)
REVIEWED_INPUTS = {
    "docs/compat/logic-pro/evidence/P002/p001-requalification/raw-reports.manifest.json":
        "edf0a93a938e23f521bc29161b6971b3fa4f7fafe64bdce6f6fc8adeb3fea61a",
    "docs/compat/logic-pro/evidence/P002/p001-requalification/raw_evidence_bundle.py":
        "8a0b2369aa7f7918e9ac413ce7d1bcd38353689fd18cbc86ee14a237cf8a9108",
    "docs/compat/logic-pro/evidence/P002/qualification-b628085/raw-bundle.manifest.json":
        "e1d2feadae6aa0852552a4711f507ad4f3f5991ca9fd7504e1489e1c494e2944",
}
EXPECTED_GIT_BLOBS = {
    HISTORICAL[0] + "/" + HISTORICAL[1]: "d7743e5d60c9075aafd12859bd61436b70fd9262",
    CURRENT[0] + "/" + CURRENT[1]: "8b5ffd70237895540e0ea263545d323916f3eab2",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_output(root, *arguments):
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True, stderr=subprocess.DEVNULL,
    ).strip()


def verify_committed_inputs(root, expected_commit):
    head = git_output(root, "rev-parse", "HEAD")
    if expected_commit:
        require(head == expected_commit, "Checked-out commit differs from the requested commit")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        require(os.environ.get("GITHUB_SHA") == head, "Checkout HEAD differs from workflow SHA")

    for name in (*REVIEWED_INPUTS, *EXPECTED_GIT_BLOBS):
        path = root / name
        require(path.is_file() and not path.is_symlink(), f"Missing or nonregular committed input: {name}")
        try:
            tree_info = git_output(root, "ls-tree", "-r", "HEAD", "--", name)
            fields = tree_info.split(maxsplit=3)
            require(len(fields) == 4 and fields[0] in ("100644", "100755")
                    and fields[1] == "blob" and fields[3] == name,
                    f"Input is not a committed regular file: {name}")
            stored_kind = git_output(root, "cat-file", "-t", "HEAD:" + name)
            stored_sha = git_output(root, "rev-parse", "HEAD:" + name)
            require(fields[2] == stored_sha, f"Committed tree/blob identity differs: {name}")
            working_sha = git_output(root, "hash-object", "--no-filters", "--", name)
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"Input is absent from the checked-out commit: {name}") from exc
        require(stored_kind == "blob" and stored_sha == working_sha,
                f"Working input differs from the committed Git blob: {name}")
        if name in REVIEWED_INPUTS:
            require(digest(path.read_bytes()) == REVIEWED_INPUTS[name],
                    f"Reviewed manifest or original reader changed: {name}")
        if name in EXPECTED_GIT_BLOBS:
            require(stored_sha == EXPECTED_GIT_BLOBS[name],
                    f"Original approved archive Git identity differs: {name}")
    return head


def verify_identity(root, entry):
    directory, name, count, sha = entry
    path = root / directory / name
    require(path.is_file() and not path.is_symlink(), f"Missing regular archive: {path}")
    raw = path.read_bytes()
    require(len(raw) == count, f"Archive byte count differs: {name}")
    require(digest(raw) == sha, f"Archive SHA-256 differs: {name}")
    return raw


def verify_current(root, compressed):
    directory = root / CURRENT[0]
    manifest_raw = (directory / "raw-bundle.manifest.json").read_bytes()
    require(digest(manifest_raw) == REVIEWED_INPUTS[
        "docs/compat/logic-pro/evidence/P002/qualification-b628085/raw-bundle.manifest.json"
    ], "Current source/member mapping differs from independently reviewed manifest")
    manifest = json.loads(manifest_raw)
    require(manifest["archive"]["bytes"] == len(compressed), "Current manifest archive size differs")
    require(manifest["archive"]["sha256"] == digest(compressed), "Current manifest archive SHA differs")
    require(manifest["archive"]["path"] == CURRENT[1], "Current manifest archive name differs")
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    content = decoder.decompress(compressed)
    require(decoder.eof and not decoder.unused_data, "Incomplete or trailing XZ stream")
    require(decoder.check == lzma.CHECK_CRC64, "Incorrect XZ integrity check")

    objects = {}
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:") as archive:
        entries = archive.getmembers()
        require(len(entries) == manifest["unique_objects"], "Object count differs")
        require([x.name for x in entries] == sorted(x.name for x in entries), "Object order differs")
        cursor = 0
        for info in entries:
            require(re.fullmatch(r"objects/[0-9a-f]{64}", info.name) is not None, "Unexpected object name")
            require(info.isfile() and not info.pax_headers, "Nonregular or extended object metadata")
            require(info.offset == cursor and info.offset_data == cursor + 512, "Tar offset differs")
            require(info.mode == 0o644 and info.uid == info.gid == info.mtime == 0, "Tar metadata differs")
            require(info.uname == info.gname == info.linkname == "", "Tar name metadata differs")
            reference = tarfile.TarInfo(info.name)
            reference.size = info.size
            reference.mode = 0o644
            require(content[cursor:cursor + 512] == reference.tobuf(format=tarfile.USTAR_FORMAT),
                    "Noncanonical tar header")
            value = content[info.offset_data:info.offset_data + info.size]
            require(digest(value) == info.name.split("/")[1], "Object content differs")
            value.decode("utf-8", "strict")
            objects[info.name] = value
            end = info.offset_data + info.size
            cursor = end + (-info.size) % 512
            require(not any(content[end:cursor]), "Nonzero object padding")
        require(len(content) % 10240 == 0 and len(content) - cursor >= 1024,
                "Invalid tar ending")
        require(not any(content[cursor:]), "Nonzero tar trailer")

    occurrences, used = 0, set()
    require(len(manifest["sources"]) == 4, "Four source artifacts are required")
    for source in manifest["sources"]:
        members = source["members"]
        require(len(members) in (16, 18), "Unexpected source member count")
        for member in members:
            name = member["object"]
            require(name in objects, f"Missing referenced object: {name}")
            value = objects[name]
            require(len(value) == member["bytes"] and digest(value) == member["sha256"],
                    "Mapped source member differs")
            used.add(name)
            occurrences += 1
    require(occurrences == manifest["member_count"] == 68, "Source member count differs")
    require(used == set(objects), "Unreferenced archive object")
    require(sum(len(value) for value in objects.values()) == manifest["unique_bytes"],
            "Unique object byte total differs")
    require(sum(member["bytes"] for source in manifest["sources"] for member in source["members"])
            == manifest["member_bytes"], "Member byte total differs")
    return {"objects": len(objects), "original_members": occurrences,
            "unique_bytes": manifest["unique_bytes"], "member_bytes": manifest["member_bytes"],
            "xz_crc64_verified": True, "canonical_ustar_verified": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-commit", help="Optional exact commit to require in addition to its Git blobs")
    args = parser.parse_args()
    root = args.repo.resolve()
    require((root / ".git").exists(), "A real Git checkout is required")
    head = verify_committed_inputs(root, args.expected_commit)

    historical = verify_identity(root, HISTORICAL)
    current = verify_identity(root, CURRENT)
    verify_script = root / HISTORICAL[0] / "raw_evidence_bundle.py"
    completed = subprocess.run(
        [sys.executable, "-B", str(verify_script), "verify", "--directory", str(root / HISTORICAL[0])],
        cwd=root, text=True, capture_output=True, check=True,
    )
    historical_result = json.loads(completed.stdout)
    require(historical_result["archive_bytes"] == len(historical), "Historical reader size differs")
    require(historical_result["members_verified"] == 32, "Historical report mappings incomplete")
    current_result = verify_current(root, current)

    report = {
        "schema_version": 1,
        "verdict": (
            "PASS_PUBLIC_GIT_CHECKOUT_EXACT_ARCHIVE_READBACK"
            if os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_RUN_ID")
            else "PASS_LOCAL_EXACT_ARCHIVE_VERIFICATION"
        ),
        "checkout_commit": head,
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "historical": {"bytes": len(historical), "sha256": digest(historical),
                       "original_members": historical_result["members_verified"],
                       "verified_by_original_reader": True},
        "current": {"bytes": len(current), "sha256": digest(current), **current_result},
        "source_scope": "Durable exact report preservation only; no Logic runtime or GUI compatibility claim",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        failure = {"schema_version": 1, "verdict": "FAIL_EXACT_ARCHIVE_READBACK",
                   "error_type": type(exc).__name__, "reason": str(exc),
                   "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                   "github_sha": os.environ.get("GITHUB_SHA")}
        if "--report" in sys.argv and sys.argv.index("--report") + 1 < len(sys.argv):
            report_path = Path(sys.argv[sys.argv.index("--report") + 1])
            try:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            except OSError:
                pass
        print(json.dumps(failure, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
