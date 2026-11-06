#!/usr/bin/env python3
"""Verify or reconstruct every original hosted artifact member in this archive.

This checks retained evidence bytes. It does not replace independent P001/P002
source review or declare phase acceptance.
"""

import argparse
import hashlib
import json
import lzma
from pathlib import Path, PurePosixPath


def relative(root, name):
    path = PurePosixPath(name)
    if (not isinstance(name, str) or not name or path.is_absolute()
            or str(path) != name or any(part in ("..", ".git") for part in path.parts)):
        raise ValueError("unsafe archive member path")
    result = root / name
    if root.resolve() not in result.resolve().parents:
        raise ValueError("archive member escapes its directory")
    return result


def checked(data, size, digest, label):
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("retained evidence bytes differ: " + label)
    return data


def verify(root, destination=None):
    manifest = json.loads((root / "artifact-manifest.json").read_bytes())
    expected = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"
    if manifest["schema_version"] != 1 or manifest["implementation_commit"] != expected:
        raise ValueError("archive schema or implementation differs")
    labels = {"p001-ubuntu-22.04", "p001-ubuntu-24.04", "p002-clone-a", "p002-clone-b"}
    observed = [record["label"] for record in manifest["artifacts"]]
    if set(observed) != labels or len(observed) != len(labels):
        raise ValueError("the four original hosted artifacts are required exactly once")
    if destination is not None and (destination.exists() or destination.is_symlink()):
        raise ValueError("extraction destination must not already exist")
    cache = {}
    verified = {}
    for artifact in manifest["artifacts"]:
        label = artifact["label"]
        metadata = artifact["metadata"]
        if (metadata["workflow_run"]["head_sha"] != expected
                or metadata["digest"] != "sha256:" + artifact["original_zip_sha256"]
                or metadata["size_in_bytes"] != artifact["original_zip_bytes"]):
            raise ValueError("original GitHub artifact identity differs")
        if "original_zip_stored_path" in artifact:
            data = relative(root, artifact["original_zip_stored_path"]).read_bytes()
            checked(data, artifact["original_zip_bytes"], artifact["original_zip_sha256"], label + ".zip")
        for name, member in artifact["members"].items():
            if "stored_path" in member:
                data = relative(root, member["stored_path"]).read_bytes()
            else:
                key = member["payload"]
                if key not in cache:
                    payload = manifest["payloads"][key]
                    if payload["encoding"] != "xz" or payload["raw_sha256"] != key:
                        raise ValueError("unsupported or mislabeled compressed payload")
                    parts = []
                    for part in payload["parts"]:
                        raw = relative(root, part["path"]).read_bytes()
                        parts.append(checked(raw, part["bytes"], part["sha256"], part["path"]))
                    packed = checked(b"".join(parts), payload["compressed_bytes"],
                                     payload["compressed_sha256"], key + " compressed")
                    cache[key] = checked(lzma.decompress(packed), payload["raw_bytes"], key, key)
                data = cache[key]
            verified[label + "/" + name] = checked(data, member["bytes"], member["sha256"], label + "/" + name)
    if len(verified) != 70:
        raise ValueError("all 70 original raw artifact members are required")
    if destination is not None:
        destination.mkdir(parents=True)
        for name, data in verified.items():
            path = relative(destination, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return {"implementation_commit": expected, "artifacts_verified": len(observed),
            "raw_members_verified": len(verified), "unique_compressed_payloads": len(cache),
            "phase_acceptance": "REQUIRES_INDEPENDENT_REVIEW"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path,
                        help="optional new directory for the reconstructed original raw members")
    args = parser.parse_args()
    print(json.dumps(verify(Path(__file__).resolve().parent, args.destination), indent=2, sort_keys=True))
