#!/usr/bin/env python3
"""Producer-side full multipart restoration checks; independent review is separate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--evidence", type=Path, required=True)
ap.add_argument("--zip-a", type=Path, required=True)
ap.add_argument("--zip-b", type=Path, required=True)
args = ap.parse_args()
evidence = args.evidence.resolve()
helper = evidence / "raw_evidence_bundle.py"
manifest = json.loads((evidence / "raw-reports.manifest.json").read_text())


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def snapshot(directory):
    return {str(path.relative_to(directory)): digest(path)
            for path in directory.rglob("*") if path.is_file()}


records = []
with tempfile.TemporaryDirectory(prefix="p001-parts-roundtrip-") as temporary:
    base = Path(temporary)
    checkout = base / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    target = checkout / "evidence"
    target.mkdir()
    unsafe_tmp = checkout / "configured-temp"
    unsafe_tmp.mkdir()
    names = {"raw-reports.manifest.json"}
    for host in manifest["hosts"].values():
        names.update(member["direct_copy"] for member in host["members"].values() if "direct_copy" in member)
    for name in names:
        shutil.copyfile(evidence / name, target / name)
    shutil.copytree(evidence / "raw-reports-parts", target / "raw-reports-parts")
    assert not (target / "raw-reports.tar.xz").exists()
    before = snapshot(checkout)
    env = dict(os.environ, TMPDIR=str(unsafe_tmp), PYTHONDONTWRITEBYTECODE="1")
    def run(label, *words, expected_exit=0):
        command = [sys.executable, "-B", str(helper), *words, "--directory", str(target)]
        result = subprocess.run(command, cwd=checkout, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=180)
        assert result.returncode == expected_exit, (label, result.returncode, result.stdout)
        record = {"label": label, "command": command, "exit_code": result.returncode}
        if result.returncode == 0:
            report = json.loads(result.stdout)
            assert report["result"] == "PASS"
            assert report["archive_storage"] == {"kind": "ordered_parts", "parts_verified": 50}
            record["report"] = report
        else:
            assert "restore output must be outside" in result.stdout
            record["rejection"] = result.stdout
        records.append(record)
    run("parts_only_verify", "verify")
    for host in ("a", "b"):
        run("parts_only_restore_" + host, "restore", "--host", host, "--output", str(base / ("restored-" + host)))
    forbidden = checkout / "must-not-be-created"
    run("in_checkout_restore_rejected", "restore", "--host", "a", "--output", str(forbidden), expected_exit=1)
    assert not forbidden.exists()
    compared = {}
    for host in ("a", "b"):
        zip_path = getattr(args, "zip_" + host)
        provenance = manifest["hosts"][host]
        assert zip_path.stat().st_size == provenance["original_zip_bytes"]
        assert digest(zip_path) == provenance["original_zip_sha256"]
        restored = base / ("restored-" + host)
        members, total = 0, 0
        with zipfile.ZipFile(zip_path) as archive:
            assert set(archive.namelist()) == {path.name for path in restored.iterdir()}
            for item in archive.infolist():
                path = restored / item.filename
                assert path.stat().st_size == item.file_size
                assert digest(path) == provenance["members"][item.filename]["sha256"]
                with archive.open(item) as original, path.open("rb") as recovered:
                    while True:
                        expected = original.read(1024 * 1024)
                        actual = recovered.read(1024 * 1024)
                        assert expected == actual, (host, item.filename)
                        if not expected:
                            break
                        total += len(expected)
                members += 1
        compared[host] = {"original_zip_sha256": provenance["original_zip_sha256"],
                          "member_count": members, "bytes_compared": total,
                          "every_restored_byte_matches_original_zip": True}
    assert before == snapshot(checkout)
    assert list(unsafe_tmp.iterdir()) == []
    assert not (target / "raw-reports.tar.xz").exists()
    result = {"result": "PASS", "helper_sha256": digest(helper),
              "manifest_sha256": digest(evidence / "raw-reports.manifest.json"),
              "parts_manifest_sha256": digest(evidence / "raw-reports-parts/manifest.json"),
              "whole_archive_absent_from_test_checkout": True,
              "test_checkout_bytes_unchanged": True, "in_checkout_tmpdir_left_empty": True,
              "restore_into_checkout_rejected_without_creating_output": True,
              "original_zip_comparisons": compared, "commands": records}
print(json.dumps(result, indent=2, sort_keys=True))
