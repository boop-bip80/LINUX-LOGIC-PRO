#!/usr/bin/env python3
"""Prepare the exact four reviewed CI artifacts for explicit publication review.

This never uploads data. Original member bytes are deduplicated by SHA-256;
the mapping retains every original filename, host, size and content digest.
"""
import argparse
import hashlib
import io
import json
import lzma
from pathlib import Path
import tarfile
import zipfile

COMMIT = "b628085a19bae2d467fd9549ec0767636423a90a"
SOURCES = [
    ("P001", "ubuntu-22.04", "p001-b628085-ubuntu-22.04.zip", 13063666566, 22167948,
     "af9a315592bf6f203e125f06d20729e15500944ec289954231800c260364c1d8"),
    ("P001", "ubuntu-24.04", "p001-b628085-ubuntu-24.04.zip", 13062918782, 22167665,
     "5f2cc6c620d250147b5e537f4fbaeb1c61618fa2475f9f99a75efc2995d96694"),
    ("P002", "clone-a", "p002-b628085-host-a.zip", 13063572615, 52899,
     "2615667b47864b103147b705ce192f1d0551c884579f75947c5cc48e21e9a219"),
    ("P002", "clone-b", "p002-b628085-host-b.zip", 13062978587, 53339,
     "a1b200168b0a6003c29967d0b73331d3b27cfc5c562c37aa16b5898c67057d8a"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.archive.exists() or args.manifest.exists():
        parser.error("output files must not exist; previous evidence is never overwritten")
    objects, sources = {}, []
    for phase, host, filename, artifact_id, size, expected in SOURCES:
        raw = (args.artifacts / filename).read_bytes()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("ZIP differs from independently verified GitHub artifact: " + filename)
        members = []
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            expected_count = 16 if phase == "P001" else 18
            if len(entries) != expected_count or len({e.filename for e in entries}) != expected_count:
                raise ValueError("unexpected or duplicated raw members")
            for entry in sorted(entries, key=lambda e: e.filename):
                if Path(entry.filename).name != entry.filename or entry.is_dir() or entry.flag_bits & 1:
                    raise ValueError("noncanonical raw member")
                data = archive.read(entry)
                data.decode("utf-8", "strict")
                digest = hashlib.sha256(data).hexdigest()
                if digest in objects and objects[digest] != data:
                    raise ValueError("digest collision")
                objects[digest] = data
                members.append({"path": entry.filename, "bytes": len(data), "sha256": digest,
                                "object": "objects/" + digest})
        sources.append({"phase": phase, "host": host, "artifact_id": artifact_id,
                        "zip_file": filename, "zip_bytes": size, "zip_sha256": expected,
                        "members": members})
    with args.archive.open("xb") as raw, lzma.LZMAFile(raw, "wb", preset=6,
                                                   check=lzma.CHECK_CRC64) as compressed:
        with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for digest, data in sorted(objects.items()):
                entry = tarfile.TarInfo("objects/" + digest)
                entry.size, entry.mode = len(data), 0o644
                entry.uid = entry.gid = entry.mtime = 0
                entry.uname = entry.gname = ""
                archive.addfile(entry, io.BytesIO(data))
    archive_data = args.archive.read_bytes()
    manifest = {
        "schema_version": 1,
        "tested_implementation_commit": COMMIT,
        "source_head_commit": "da1000be001711f80d6880eed9eeca916f6d0a23",
        "tested_source_tree": "37761104d97e824a2567f91dff2dea391bb635dd",
        "workflow_runs": {"P001": 41256694734, "P002": 41256694572},
        "publication_status": "PREPARED_NOT_PUBLISHED; explicit approval requested for this exact bundle",
        "preservation_scope": "Every exact uncompressed member of all four original ZIPs; ZIP containers are not reconstructed",
        "historical_hold": "The separately held 9667936-byte historical archive is not an input and is not reconstructed or uploaded",
        "archive": {"path": args.archive.name, "bytes": len(archive_data),
                    "sha256": hashlib.sha256(archive_data).hexdigest(),
                    "format": "USTAR, sorted objects/SHA256 regular files, canonical 0644 uid/gid/mtime=0; XZ preset 6 CRC64"},
        "member_count": sum(len(s["members"]) for s in sources),
        "member_bytes": sum(m["bytes"] for s in sources for m in s["members"]),
        "unique_objects": len(objects),
        "unique_bytes": sum(len(data) for data in objects.values()),
        "sources": sources,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: manifest[key] for key in ("archive", "member_count", "member_bytes", "unique_objects", "unique_bytes")}, indent=2))


if __name__ == "__main__":
    main()
