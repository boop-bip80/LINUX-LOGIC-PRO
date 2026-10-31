#!/usr/bin/env python3
"""Read-only provenance, text/schema and bounded secret-pattern audit of P001 evidence.

This program never reads credentials or host secret files. It reads only the
named report archive, its manifest, and previously acquired official ZIPs. It
does not upload, re-encode, extract, or alter any archive or source content.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import lzma
from pathlib import Path
import re
import tarfile
import zipfile


PATTERNS = {
    "private_key_pem": rb"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----",
    "github_classic_token": rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
    "github_fine_grained_token": rb"\bgithub_pat_[A-Za-z0-9_]{30,}\b",
    "slack_token": rb"\bxox[baprs]-[A-Za-z0-9-]{15,}\b",
    "aws_access_key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "google_api_key": rb"\bAIza[A-Za-z0-9_-]{30,}\b",
    "openai_style_key": rb"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b",
    "jwt_literal": rb"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b",
    "authorization_value": rb"(?i)\bauthorization\s*[:=]\s*[\"']?(?:bearer|basic)\s+[A-Za-z0-9+/=_-]{12,}",
    "url_embedded_password": rb"[A-Za-z][A-Za-z0-9+.-]*://[^\s/\"'<>:]+:[^\s/\"'<>@]+@",
    "credential_assignment": rb"(?i)[\"']?(?:password|passwd|aws_secret_access_key|client_secret|access_token|refresh_token|api_key|github_token|gh_token)[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}[\"']",
    "host_secret_file_reference": rb"/(?:root|home/runner)/(?:\.aws/credentials|\.ssh/id_[^\s\"']+|\.config/gh/hosts\.yml|\.netrc)\b",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def shape(document):
    kinds = Counter()
    fields = Counter()
    sensitive_fields = Counter()
    literal_strings = 0
    sensitive_key = re.compile(r"(?i)(?:secret|token|password|passwd|authorization|cookie|credential|environment|^env$)")
    stack = [("$", document)]
    while stack:
        path, value = stack.pop()
        kinds[type(value).__name__] += 1
        if isinstance(value, dict):
            for key, child in value.items():
                fields[key] += 1
                if sensitive_key.search(key):
                    sensitive_fields[(key, type(child).__name__)] += 1
                stack.append((path + "." + key, child))
        elif isinstance(value, list):
            stack.extend((path + "[]", child) for child in value)
        elif isinstance(value, str):
            literal_strings += 1
    return {"root_type": type(document).__name__,
            "root_keys": sorted(document) if isinstance(document, dict) else None,
            "value_types": dict(kinds), "string_values": literal_strings,
            "field_names_and_counts": dict(sorted(fields.items())),
            "sensitive_named_fields_without_values": [{"key": key, "type": kind, "count": count}
                for (key, kind), count in sorted(sensitive_fields.items())]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--zip-a", type=Path, required=True)
    parser.add_argument("--zip-b", type=Path, required=True)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.directory.resolve(strict=True)
    mapping_raw = (base / "raw-reports.manifest.json").read_bytes()
    mapping = json.loads(mapping_raw)
    official_raw = args.official.read_bytes()
    official = json.loads(official_raw)
    assert official["repository"]["private"] is False and official["repository"]["visibility"] == "public"
    archive_raw = (base / "raw-reports.tar.xz").read_bytes()
    assert len(archive_raw) == mapping["archive"]["bytes"] == 9667936
    assert sha(archive_raw) == mapping["archive"]["sha256"] == "5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d"
    decoder = lzma.LZMADecompressor()
    tar_raw = decoder.decompress(archive_raw)
    assert decoder.eof and decoder.unused_data == b""
    origins = {}
    zip_records = []
    original_members = {}
    for host, zip_path in (("a", args.zip_a), ("b", args.zip_b)):
        provenance = mapping["hosts"][host]
        official_row = next(row for row in official["artifacts"] if row["id"] == provenance["artifact_id"])
        raw = zip_path.read_bytes()
        assert len(raw) == provenance["original_zip_bytes"] == official_row["size_in_bytes"]
        assert sha(raw) == provenance["original_zip_sha256"] == official_row["digest"].removeprefix("sha256:")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert len(archive.namelist()) == len(set(archive.namelist())) == 16
            assert set(archive.namelist()) == set(provenance["members"])
            for name in archive.namelist():
                content = archive.read(name)
                record = provenance["members"][name]
                assert len(content) == record["bytes"] and sha(content) == record["sha256"]
                object_path = record["object"]
                if object_path in original_members:
                    assert original_members[object_path] == content
                original_members[object_path] = content
                origins.setdefault(object_path, []).append({"host": host, "member": name,
                    "official_artifact_id": official_row["id"], "zip_sha256": sha(raw)})
        zip_records.append({"host": host, "artifact_id": official_row["id"], "zip_bytes": len(raw),
                            "zip_sha256": sha(raw), "members": 16,
                            "official_api": official_row["url"], "run": official_row["workflow_run"]})
    details, findings = [], []
    patterns = {name: re.compile(pattern) for name, pattern in PATTERNS.items()}
    with tarfile.open(fileobj=io.BytesIO(tar_raw), mode="r:") as archive:
        entries = archive.getmembers()
        assert len(entries) == 22 and len({row.name for row in entries}) == 22
        assert {row.name for row in entries} == set(original_members)
        assert entries[-1].offset_data + ((entries[-1].size + 511) // 512) * 512 <= len(tar_raw)
        tail_start = entries[-1].offset_data + ((entries[-1].size + 511) // 512) * 512
        assert not any(tar_raw[tail_start:])
        for entry in entries:
            assert entry.isfile() and not entry.pax_headers
            assert entry.mode == 0o644 and entry.uid == entry.gid == entry.mtime == 0
            assert entry.uname == entry.gname == "" and not entry.linkname
            content = archive.extractfile(entry).read()
            assert content == original_members[entry.name]
            assert entry.name == "objects/" + sha(content)
            text = content.decode("utf-8", "strict")
            assert "\x00" not in text
            object_findings = []
            for name, pattern in patterns.items():
                matches = list(pattern.finditer(content))
                if matches:
                    # Values and excerpts are deliberately never written out.
                    record = {"object": entry.name, "pattern": name, "count": len(matches),
                              "byte_offsets": [match.start() for match in matches[:25]]}
                    findings.append(record)
                    object_findings.append(record)
            names = [row["member"] for row in origins[entry.name]]
            is_json = all(name.endswith(".json") for name in names)
            is_log = all(name.endswith(".log") for name in names)
            assert is_json or is_log
            schema = shape(json.loads(text)) if is_json else None
            details.append({"object": entry.name, "bytes": len(content), "sha256": sha(content),
                            "origins": origins[entry.name], "utf8": True, "nul_bytes": 0,
                            "format": "JSON" if is_json else "UTF-8 command/test log",
                            "json_schema_summary": schema, "line_count": len(text.splitlines()),
                            "bounded_pattern_matches": object_findings})
            print(entry.name, len(content), "JSON" if is_json else "TEXT", "matches", len(object_findings), flush=True)
    report = {"schema_version": 1, "reviewer": "/root/p002_acceptance",
              "reviewed_at": datetime.now(timezone.utc).isoformat(),
              "result": "NO_LISTED_SECRET_PATTERNS_FOUND" if not findings else "MANUAL_REVIEW_REQUIRED",
              "scope": "Read-only complete archive-member provenance, UTF-8/JSON structure, and bounded literal credential/content screening; not an upload authorization or a universal secret-free guarantee",
              "archive_bytes": len(archive_raw), "archive_sha256": sha(archive_raw),
              "raw_mapping_sha256": sha(mapping_raw), "official_metadata_sha256": sha(official_raw),
              "public_repository": official["repository"], "zip_provenance": zip_records,
              "objects": details, "object_count": len(details), "original_member_count": 32,
              "unique_content_bytes": sum(row["bytes"] for row in details),
              "no_extra_archive_object": True, "no_embedded_archive_symlink_or_special_file": True,
              "no_compressed_trailing_stream_or_tar_tail_payload": True,
              "patterns_checked": {name: value.decode("ascii") for name, value in PATTERNS.items()},
              "findings": findings,
              "limitations": ["Regex screening cannot prove the absence of every possible secret encoding or novel token format.",
                              "Artifact origin in a public repository does not by itself prove every logged string public or safe.",
                              "No credential files or host secret values were read for comparison.",
                              "This review does not grant permission to bypass an upload denial."]}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ("objects", "patterns_checked", "zip_provenance")}, indent=2))


if __name__ == "__main__":
    main()
