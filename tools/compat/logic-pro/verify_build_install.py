#!/usr/bin/env python3
"""Verify P003 installed framework provenance; this is not a runtime pass.

Requires a CMake codemodel-v2 query before configure, and an unstripped install.
The independent runtime probes must additionally verify actual loaded images.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct
import subprocess
import sys

CONTROL_FILE = ".p003-isolated-install.json"
FRAMEWORKS = {
    "AppKit": ("C", "src/external/cocotron/AppKit", "NSApplication.m"),
    "CoreGraphics": ("A", "src/external/cocotron/CoreGraphics", "CGContext.m"),
    "CoreText": ("A", "src/external/cocotron/CoreText", "CTFont.m"),
    "QuartzCore": ("A", "src/external/cocotron/QuartzCore", "CALayer.m"),
    "ImageIO": ("A", "src/frameworks/ImageIO", "src/CGImageSource.m"),
    "AudioToolbox": ("A", "src/CoreAudio/AudioToolbox", "AudioConverter.cpp"),
    "Foundation": ("C", "src/external/foundation", "src/NSString.m"),
}


class VerificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(prefix):
    """lstat only: never traverse an installed absolute/guest symlink."""
    prefix = Path(prefix)
    require(prefix.is_dir() and not prefix.is_symlink(), "install prefix must be a real directory")
    entries = []

    def visit(directory):
        for child in sorted(directory.iterdir(), key=lambda p: p.name):
            relative = child.relative_to(prefix).as_posix()
            if relative == CONTROL_FILE:
                require(child.is_file() and not child.is_symlink(), "invalid ownership control file")
                continue
            metadata = child.lstat()
            entry = {"path": relative, "mode": stat.S_IMODE(metadata.st_mode)}
            if stat.S_ISLNK(metadata.st_mode):
                entry.update(kind="symlink", target=os.readlink(child))
            elif stat.S_ISREG(metadata.st_mode):
                entry.update(kind="file", size=metadata.st_size, sha256=sha256(child))
            elif stat.S_ISDIR(metadata.st_mode):
                entry.update(kind="directory")
            else:
                raise VerificationError(f"unexpected special file in installation: {relative}")
            entries.append(entry)
            if entry["kind"] == "directory":
                visit(child)

    visit(prefix)
    return sorted(entries, key=lambda item: item["path"])


def guest_resolve(root, image):
    """Resolve symlinks using Darwin guest absolute paths, never the host root."""
    require(image.startswith("/"), f"expected absolute guest image path: {image}")
    root = Path(root).resolve(strict=True)
    pending = list(PurePosixPath(image).parts[1:])
    resolved = []
    symlinks = 0
    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            require(bool(resolved), f"guest path escapes root: {image}")
            resolved.pop()
            continue
        candidate = root.joinpath(*resolved, part)
        if candidate.is_symlink():
            symlinks += 1
            require(symlinks <= 40, f"symlink loop in guest path: {image}")
            target = os.readlink(candidate)
            if target.startswith("/"):
                resolved = []
                parts = list(PurePosixPath(target).parts[1:])
            else:
                parts = list(PurePosixPath(target).parts)
            pending = parts + pending
        else:
            require(candidate.exists(), f"missing installed guest path: {image} ({candidate})")
            resolved.append(part)
    return root.joinpath(*resolved)


def macho(data):
    """Read bounded Mach-O load commands without trusting external tool output."""
    require(len(data) >= 4, "truncated Mach-O magic")
    magic = data[:4]
    slices = []
    if magic in (b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"):
        endian = ">" if magic in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf") else "<"
        fat64 = magic in (b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca")
        require(len(data) >= 8, "truncated fat header")
        count = struct.unpack_from(endian + "I", data, 4)[0]
        stride = 32 if fat64 else 20
        table_end = 8 + count * stride
        require(0 < count <= 64 and table_end <= len(data), "invalid fat architecture table")
        ranges = []
        for index in range(count):
            offset = 8 + index * stride
            cpu, subtype = struct.unpack_from(endian + "II", data, offset)
            start, size = struct.unpack_from(endian + ("QQ" if fat64 else "II"), data, offset + 8)
            require(size >= 28 and start >= table_end and start + size <= len(data), "fat slice outside file")
            require(all(start + size <= a or start >= b for a, b in ranges), "overlapping fat slices")
            ranges.append((start, start + size))
            slices.append((cpu, data[start:start + size]))
    else:
        slices = [(None, data)]
    result = []
    for expected_cpu, section in slices:
        magic = section[:4]
        require(magic in (b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf"), "not a Mach-O image")
        endian = "<" if magic in (b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe") else ">"
        is64 = magic in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")
        header_size = 32 if is64 else 28
        require(len(section) >= header_size, "truncated Mach-O header")
        cpu, subtype, filetype, ncmds, command_bytes, flags = struct.unpack_from(endian + "IIIIII", section, 4)
        require(expected_cpu is None or cpu == expected_cpu, "fat and thin CPU types differ")
        require(ncmds <= command_bytes // 8 and header_size + command_bytes <= len(section), "invalid load-command bounds")
        position = header_size
        install_names, dependencies, rpaths, uuids = [], [], [], []
        for _ in range(ncmds):
            require(position + 8 <= header_size + command_bytes, "truncated load command")
            command, length = struct.unpack_from(endian + "II", section, position)
            require(length >= 8 and length % 4 == 0 and position + length <= header_size + command_bytes, "invalid load-command size")
            if command in (0x0D, 0x0C, 0x80000018, 0x8000001F, 0x80000023, 0x20, 0x8000001C):
                minimum = 12 if command == 0x8000001C else 24
                require(length >= minimum, "short dylib/rpath command")
                string_offset = struct.unpack_from(endian + "I", section, position + 8)[0]
                require(minimum <= string_offset < length, "invalid dylib/rpath string offset")
                raw = section[position + string_offset:position + length]
                require(b"\0" in raw, "unterminated dylib/rpath string")
                value = raw.split(b"\0", 1)[0].decode("utf-8", "strict")
                require(bool(value), "empty dylib/rpath string")
                if command == 0x0D:
                    install_names.append(value)
                elif command == 0x8000001C:
                    rpaths.append(value)
                else:
                    dependencies.append({"path": value, "weak": command == 0x80000018})
            elif command == 0x1B:
                require(length == 24, "invalid UUID command")
                uuids.append(section[position + 8:position + 24].hex())
            position += length
        require(position == header_size + command_bytes, "load-command count/size mismatch")
        require(len(install_names) == 1, "framework must have exactly one LC_ID_DYLIB")
        require(filetype == 6, "framework must be MH_DYLIB")
        result.append({"cpu_type": cpu, "cpu_subtype": subtype, "bits": 64 if is64 else 32,
                       "install_name": install_names[0], "dependencies": dependencies,
                       "rpaths": rpaths, "uuids": uuids, "slice_sha256": hashlib.sha256(section).hexdigest()})
    require(sum(item["cpu_type"] == 0x01000007 for item in result) == 1, "framework needs exactly one x86_64 slice")
    require(len({item["cpu_type"] for item in result}) == len(result), "duplicate architecture slice")
    return {"architectures": result}


def load_codemodel(build, source):
    reply = build / ".cmake/api/v1/reply"
    indices = sorted(reply.glob("index-*.json"))
    require(bool(indices), "missing CMake codemodel-v2 reply; query before configuring")
    index = json.loads(indices[-1].read_text())
    references = [item for item in index.get("objects", []) if item.get("kind") == "codemodel" and item.get("version", {}).get("major") == 2]
    require(len(references) == 1, "missing or ambiguous CMake codemodel-v2")
    model = json.loads((reply / references[0]["jsonFile"]).read_text())
    require(Path(model["paths"]["source"]).resolve() == source, "CMake codemodel uses a different source tree")
    require(Path(model["paths"]["build"]).resolve() == build, "CMake codemodel uses a different build tree")
    configurations = model.get("configurations", [])
    require(len(configurations) == 1, "P003 requires one explicit build configuration")
    targets = {}
    for item in configurations[0].get("targets", []):
        name = item["name"]
        require(name not in targets, f"duplicate CMake target: {name}")
        targets[name] = json.loads((reply / item["jsonFile"]).read_text())
    return targets


def read_cache(build):
    result = {}
    for line in (build / "CMakeCache.txt").read_text().splitlines():
        if not line or line.startswith(("#", "//")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.split(":", 1)[0]] = value
    return result


def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()


def verify(source, build, prefix, destdir=None):
    source, build = Path(source).resolve(strict=True), Path(build).resolve(strict=True)
    prefix = Path(prefix)
    require(prefix.is_absolute() and ".." not in prefix.parts, "install prefix must be absolute and normalized")
    installed = (Path(destdir).resolve(strict=True) / prefix.relative_to("/")) if destdir else prefix
    require(installed.resolve(strict=True) == installed, "installed prefix or parent traverses a host symlink")
    cache = read_cache(build)
    require(cache.get("CMAKE_INSTALL_PREFIX") == str(prefix), "CMake install prefix differs from checked prefix")
    require(cache.get("TARGET_x86_64") == "ON", "x86_64 target was not enabled")
    targets = load_codemodel(build, source)
    report = {"schema_version": 1, "phase": "P003", "gate": "installed-framework-provenance", "status": "FAILED",
              "source_commit": git(source, "rev-parse", "HEAD"), "submodules": [],
              "configuration": {"components": cache.get("COMPONENTS"), "install_prefix": str(prefix), "source_dir": str(source)},
              "frameworks": [], "entries": [], "excluded_control_files": [CONTROL_FILE], "errors": []}
    for line in git(source, "ls-tree", "-r", "HEAD").splitlines():
        metadata, path = line.split("\t", 1)
        mode, kind, revision = metadata.split(" ")
        if mode == "160000":
            report["submodules"].append({"path": path, "sha": revision})
    guest = installed / "libexec/darling"
    for name, (version, owner, sentinel) in FRAMEWORKS.items():
        try:
            # Foundation is built through add_separated_framework: its public
            # target is IMPORTED, its final image a lipo byproduct. Bind the real
            # object/link targets and compare the linked x86_64 slice below.
            target_name = "Foundation_x86_64" if name == "Foundation" else name
            source_target = "Foundation_obj" if name == "Foundation" else name
            require(target_name in targets and source_target in targets, f"missing actual CMake target {target_name}/{source_target}")
            target = targets[target_name]
            target_source = Path(target["paths"]["source"])
            if not target_source.is_absolute():
                target_source = source / target_source
            require(target_source.resolve() == source / owner, f"{name}: CMake source owner is not {owner}")
            sources = [item["path"] for item in targets[source_target].get("sources", [])]
            require(bool(sources) and not any("/dev-stubs/" in path for path in sources), f"{name}: developer stub or empty source list")
            if sentinel:
                require(any((source / path).resolve() == source / owner / sentinel for path in sources), f"{name}: real implementation source missing: {sentinel}")
                require((source / owner / sentinel).is_file(), f"{name}: implementation source is missing on disk")
            artifact = build / owner / name
            linked_artifact = build / owner / target_name
            artifacts = [(build / item["path"]).resolve() for item in target.get("artifacts", [])]
            require(linked_artifact in artifacts, f"{name}: expected build artifact absent from codemodel")
            require(artifact.is_file() and not artifact.is_symlink(), f"{name}: build artifact missing or symlink")
            image = f"/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
            actual = guest_resolve(guest, image)
            require(actual == guest / image.lstrip("/"), f"{name}: versioned main image is redirected")
            alias = guest_resolve(guest, f"/System/Library/Frameworks/{name}.framework/{name}")
            require(alias == actual, f"{name}: public framework alias selects competing implementation")
            require(actual.is_file() and not actual.is_symlink(), f"{name}: installed artifact missing or symlink")
            built_hash = sha256(artifact)
            require(sha256(actual) == built_hash, f"{name}: installed bytes differ from actual-owner build target")
            load_commands = macho(actual.read_bytes())
            if name == "Foundation":
                require(linked_artifact.is_file() and not linked_artifact.is_symlink(), "Foundation: missing linked x86_64 artifact")
                linked = macho(linked_artifact.read_bytes())["architectures"]
                installed_x64 = [arch for arch in load_commands["architectures"] if arch["cpu_type"] == 0x01000007][0]
                linked_x64 = [arch for arch in linked if arch["cpu_type"] == 0x01000007][0]
                require(installed_x64["slice_sha256"] == linked_x64["slice_sha256"], "Foundation: installed x86_64 slice differs from actual link target")
            for arch in load_commands["architectures"]:
                require(arch["install_name"] == image, f"{name}: LC_ID_DYLIB does not match installed framework path")
                for dependency in arch["dependencies"]:
                    try:
                        dep = dependency["path"]
                        if dep.startswith("@loader_path/"):
                            dep = str(PurePosixPath(image).parent / dep[len("@loader_path/"):])
                        resolved = guest_resolve(guest, dep)
                        require(resolved.is_file(), f"dependency is not a file: {dep}")
                        dependency["installed"] = True
                    except VerificationError:
                        dependency["installed"] = False
                        if not dependency["weak"]:
                            raise
            report["frameworks"].append({"name": name, "source_owner": owner,
                                         "cmake_target": target_name, "cmake_source_target": source_target,
                                         "build_artifact": artifact.relative_to(build).as_posix(),
                                         "installed_path": actual.relative_to(installed).as_posix(),
                                         "sha256": built_hash, "macho": load_commands})
        except (OSError, KeyError, ValueError) as error:
            report["errors"].append(f"{name}: {error}")
    report["entries"] = snapshot(installed)
    require(bool(report["entries"]), "empty installed manifest")
    if not report["errors"] and len(report["frameworks"]) == len(FRAMEWORKS):
        report["status"] = "PASSED"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--destdir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.source, args.build, args.prefix, args.destdir)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        result = {"schema_version": 1, "phase": "P003", "gate": "installed-framework-provenance", "status": "FAILED", "errors": [str(error)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"P003 installed framework provenance: {result['status']}")
    for error in result["errors"]:
        print(error, file=sys.stderr)
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
