#!/usr/bin/env python3
"""Restore a retained P003 input archive without relaxing the frozen recipe."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import stat
import tempfile
import zipfile

import lock_toolchain as lock

MEMBERS = {"base-pull.log", "toolchain-build.log", "toolchain.lock.json",
           "toolchain-image.tar.gz", "SHA256SUMS"}


def inputs(manifest_path: Path, committed_path: Path, recipe: Path):
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "darling.p003.retained-toolchain.v1":
        raise ValueError("Unsupported retained toolchain manifest")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", manifest.get("repository", "")):
        raise ValueError("Invalid retained repository")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("source_commit", "")):
        raise ValueError("Invalid retained source revision")
    if manifest.get("artifact_name") != "p003-toolchain-" + manifest["source_commit"]:
        raise ValueError("Retained artifact name does not identify its source")
    for field in ("run_id", "artifact_id", "artifact_bytes"):
        if type(manifest.get(field)) is not int or manifest[field] <= 0:
            raise ValueError("Invalid retained artifact identity: " + field)
    for field in ("artifact_sha256", "committed_lock_sha256", "recipe_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", manifest.get(field, "")):
            raise ValueError("Invalid retained digest: " + field)
    if lock.sha256(committed_path) != manifest["committed_lock_sha256"]:
        raise ValueError("Retained archive belongs to a different committed lock")
    committed = json.loads(committed_path.read_text())
    lock.validate(committed)
    if lock.sha256(recipe) != manifest["recipe_sha256"] or committed["recipe_sha256"] != manifest["recipe_sha256"]:
        raise ValueError("Retained archive belongs to a different recipe")
    return manifest, committed


def restore(archive: Path, manifest_path: Path, committed_path: Path,
            recipe: Path, output: Path) -> dict:
    manifest, committed = inputs(manifest_path, committed_path, recipe)
    if output.exists() or output.is_symlink():
        raise ValueError("Restoration output must not exist")
    info = archive.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != manifest["artifact_bytes"]:
        raise ValueError("Retained artifact is not the pinned regular archive")
    if lock.sha256(archive) != manifest["artifact_sha256"]:
        raise ValueError("Retained artifact SHA256 mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".p003-toolchain-", dir=output.parent) as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive) as bundle:
            entries = bundle.infolist()
            if len(entries) != len(MEMBERS) or {entry.filename for entry in entries} != MEMBERS:
                raise ValueError("Retained artifact has missing, duplicate or unexpected members")
            for entry in entries:
                kind = stat.S_IFMT(entry.external_attr >> 16)
                if entry.is_dir() or kind not in (0, stat.S_IFREG):
                    raise ValueError("Retained artifact member is not a regular file")
                with bundle.open(entry) as source, (staging / entry.filename).open("xb") as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
        restored_path = staging / "toolchain.lock.json"
        restored = json.loads(restored_path.read_text())
        lock.validate(restored)
        changes = [field for field in ("base_image", "ubuntu_snapshot", "recipe_sha256")
                   if restored[field] != committed[field]]
        changes += lock.identity_differences(
            lock.environment_identity(committed["environment"]),
            lock.environment_identity(restored["environment"]), "environment")
        if changes:
            raise ValueError("Retained toolchain differs from committed inputs: " + ", ".join(changes))
        image = staging / "toolchain-image.tar.gz"
        if image.stat().st_size != restored["image_archive"]["bytes"] or lock.sha256(image) != restored["image_archive"]["sha256"]:
            raise ValueError("Retained image does not match its sealed lock")
        hashes = {name: lock.sha256(staging / name) for name in sorted(MEMBERS)}
        recorded = {}
        for line in (staging / "SHA256SUMS").read_text().splitlines():
            digest, path = line.split(None, 1)
            name = Path(path).name
            if name in recorded:
                raise ValueError("Duplicate retained checksum")
            recorded[name] = digest
        if recorded != {name: hashes[name] for name in ("toolchain.lock.json", "toolchain-image.tar.gz")}:
            raise ValueError("Retained checksum receipt differs from the original files")
        receipt = {"schema": "darling.p003.retained-acquisition.v1", "status": "PASSED",
                   "origin": manifest, "original_files_sha256": hashes,
                   "restored_image_id": restored["image_id"],
                   "scope": "Frozen toolchain inputs only; every source checkout, build, installation and runtime campaign must be fresh."}
        (staging / "retained-acquisition.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        # Exclusive directory creation preserves any preexisting destination.
        # Validation finishes before publishing any restored input files.
        output.mkdir()
        for entry in staging.iterdir():
            entry.rename(output / entry.name)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("origin", "restore"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--committed-lock", required=True, type=Path)
    parser.add_argument("--recipe", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "origin":
            manifest, _ = inputs(args.manifest, args.committed_lock, args.recipe)
            print(f"https://api.github.com/repos/{manifest['repository']}/actions/artifacts/{manifest['artifact_id']}/zip")
        else:
            if args.archive is None or args.output is None:
                raise ValueError("Restoration requires archive and output paths")
            receipt = restore(args.archive, args.manifest, args.committed_lock, args.recipe, args.output)
            print(json.dumps(receipt, sort_keys=True))
            print("P003 retained frozen toolchain: PASS")
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(f"P003 retained frozen toolchain: FAIL: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
