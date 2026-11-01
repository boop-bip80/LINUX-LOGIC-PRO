#!/usr/bin/env python3
"""Capture, seal and verify the P003 toolchain; never infer pass from a tag."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

SCHEMA = "darling.p003.toolchain.v1"
TOOLS = {
    "clang": ["clang-14", "--version"],
    "clang++": ["clang++-14", "--version"],
    "llvm-config": ["llvm-config-14", "--version"],
    "dsymutil": ["dsymutil-14", "--version"],
    "native-linker": ["ld", "--version"],
    "cmake": ["cmake", "--version"],
    "ninja": ["ninja", "--version"],
    "bison": ["bison", "--version"],
    "flex": ["flex", "--version"],
    "python": ["python3", "--version"],
    "git": ["git", "--version"],
    "git-lfs": ["git", "lfs", "version"],
    "pkg-config": ["pkg-config", "--version"],
}


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def command(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, env={**os.environ, "LC_ALL": "C"}).stdout.strip()


def parse_packages(text: str) -> list[dict[str, str]]:
    packages = []
    seen = set()
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) != 4:
            raise ValueError("Malformed dpkg package record")
        name, version, arch, status = fields
        if status != "ii ":
            raise ValueError(f"Non-installed or incomplete package: {name} {status!r}")
        key = (name, arch)
        if not name or not version or not arch or key in seen:
            raise ValueError("Empty or duplicate package record")
        seen.add(key)
        packages.append({"name": name, "version": version, "architecture": arch})
    if not packages:
        raise ValueError("Empty package manifest")
    return sorted(packages, key=lambda p: (p["name"], p["architecture"]))


def observed() -> dict:
    tools = {}
    for name, argv in TOOLS.items():
        resolved = shutil.which(argv[0])
        if resolved is None:
            raise ValueError(f"Missing required tool: {argv[0]}")
        # git-lfs is a separate executable selected by `git lfs`.
        if name == "git-lfs":
            resolved = shutil.which("git-lfs")
            if resolved is None:
                raise ValueError("Missing git-lfs executable")
        path = Path(resolved).resolve(strict=True)
        tools[name] = {"command": argv, "path": str(path),
                       "sha256": sha256(path), "version_output": command(argv)}
    packages = subprocess.run(
        ["dpkg-query", "--show", "--showformat=${Package}\t${Version}\t${Architecture}\t${db:Status-Abbrev}\n"],
        check=True, text=True, stdout=subprocess.PIPE).stdout
    return {"os_release": Path("/etc/os-release").read_text(),
            "architecture": command(["dpkg", "--print-architecture"]),
            "packages": parse_packages(packages), "tools": tools,
            "apt_sources": Path("/etc/apt/sources.list").read_text()}


def validate(lock: dict, sealed: bool = True) -> None:
    if lock.get("schema") != SCHEMA:
        raise ValueError("Unsupported toolchain schema")
    if not re.fullmatch(r"ubuntu@sha256:[0-9a-f]{64}", lock.get("base_image", "")):
        raise ValueError("Ubuntu base must be pinned by observed digest")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", lock.get("image_id", "")):
        raise ValueError("Missing immutable toolchain image config digest")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", lock.get("ubuntu_snapshot", "")):
        raise ValueError("Invalid Ubuntu snapshot")
    if not re.fullmatch(r"[0-9a-f]{64}", lock.get("recipe_sha256", "")):
        raise ValueError("Missing build recipe hash")
    environment = lock.get("environment", {})
    if environment.get("architecture") != "amd64":
        raise ValueError("The supported toolchain is amd64")
    if 'VERSION_ID="22.04"' not in environment.get("os_release", ""):
        raise ValueError("The supported distribution is Ubuntu 22.04")
    if not environment.get("packages") or set(environment.get("tools", {})) != set(TOOLS):
        raise ValueError("Incomplete package/tool manifest")
    seen = set()
    for package in environment["packages"]:
        key = (package["name"], package["architecture"])
        if key in seen or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", package["name"]):
            raise ValueError("Invalid or duplicate pinned package")
        seen.add(key)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", package["architecture"]):
            raise ValueError("Invalid pinned architecture")
        if not re.fullmatch(r"[A-Za-z0-9.+:~_-]+", package["version"]):
            raise ValueError("Invalid pinned package version")
    for tool in environment["tools"].values():
        if not re.fullmatch(r"[0-9a-f]{64}", tool["sha256"]) or not tool.get("version_output"):
            raise ValueError("Incomplete tool identity")
    if sealed:
        archive = lock.get("image_archive", {})
        if archive.get("file") != "toolchain-image.tar.gz" or not isinstance(archive.get("bytes"), int) or archive["bytes"] <= 0:
            raise ValueError("Missing immutable image archive")
        if not re.fullmatch(r"[0-9a-f]{64}", archive.get("sha256", "")):
            raise ValueError("Missing image archive digest")


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    capture = commands.add_parser("capture")
    for name in ("base-image", "image-id", "snapshot", "recipe", "output"):
        capture.add_argument("--" + name, required=True)
    seal = commands.add_parser("seal")
    seal.add_argument("--lock", type=Path, required=True)
    seal.add_argument("--archive", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--lock", type=Path, required=True)
    verify.add_argument("--recipe", type=Path, required=True)
    archive = commands.add_parser("verify-archive")
    archive.add_argument("--lock", type=Path, required=True)
    archive.add_argument("--archive", type=Path, required=True)
    pins = commands.add_parser("recipe-pins")
    pins.add_argument("--lock", type=Path, required=True)
    compare = commands.add_parser("compare-environment")
    compare.add_argument("--lock", type=Path, required=True)
    compare.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "capture":
            lock = {"schema": SCHEMA, "base_image": args.base_image,
                    "image_id": args.image_id, "ubuntu_snapshot": args.snapshot,
                    "recipe_sha256": sha256(Path(args.recipe)), "environment": observed()}
            validate(lock, sealed=False)
            write(Path(args.output), lock)
        else:
            lock = json.loads(args.lock.read_text())
            validate(lock, sealed=args.action != "seal")
            if args.action == "seal":
                if args.archive.name != "toolchain-image.tar.gz":
                    raise ValueError("Unexpected image archive name")
                lock["image_archive"] = {"file": args.archive.name,
                                   "bytes": args.archive.stat().st_size,
                                   "sha256": sha256(args.archive)}
                validate(lock)
                write(args.lock, lock)
            elif args.action == "verify-archive":
                if args.archive.stat().st_size != lock["image_archive"]["bytes"] or sha256(args.archive) != lock["image_archive"]["sha256"]:
                    raise ValueError("Image archive does not match the frozen lock")
            elif args.action == "verify":
                if sha256(args.recipe) != lock["recipe_sha256"]:
                    raise ValueError("Toolchain Dockerfile differs from the frozen recipe")
                current = observed()
                if current != lock["environment"]:
                    changed = sorted(k for k in current if current[k] != lock["environment"].get(k))
                    raise ValueError("Toolchain changed: " + ", ".join(changed))
            elif args.action == "recipe-pins":
                print(lock["base_image"])
                print(lock["ubuntu_snapshot"])
                print(" ".join(f"{p['name']}:{p['architecture']}={p['version']}"
                               for p in lock["environment"]["packages"]))
                return 0
            elif args.action == "compare-environment":
                candidate = json.loads(args.candidate.read_text())
                validate(candidate)
                fields = ("base_image", "ubuntu_snapshot", "recipe_sha256", "environment")
                changed = [field for field in fields if candidate[field] != lock[field]]
                if changed:
                    raise ValueError("Rebuilt toolchain differs from committed pins: " + ", ".join(changed))
        print(f"P003 toolchain {args.action}: PASS")
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError, TypeError) as exc:
        print(f"P003 toolchain {args.action}: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
