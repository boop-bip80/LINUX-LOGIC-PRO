#!/usr/bin/env python3
"""Record actual Linux ELF and dlopen dependencies of the P003 installation.

This audits trusted binaries just built from the pinned source and the pinned
Ubuntu packages. It does not treat an ELF dependency audit as a Darwin runtime
or Logic compatibility test. Every probe remains mandatory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

REQUIRED_ENTRYPOINTS = {
    "bin/darling", "bin/darlingserver",
    "libexec/darling/usr/libexec/darling/mldr",
}
WRAPPER_SOURCES = ("src/native/CMakeLists.txt", "src/CoreAudio/CMakeLists.txt")
SAFE_ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C", "LANG": "C"}
LOAD_WRAPPER = r'''
import ctypes, json, os, sys
class LinkMapHead(ctypes.Structure):
    _fields_ = [("address", ctypes.c_void_p), ("name", ctypes.c_char_p)]
library = ctypes.CDLL(sys.argv[1], mode=os.RTLD_NOW | os.RTLD_LOCAL)
loader = ctypes.CDLL("libdl.so.2")
loader.dlinfo.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
loader.dlinfo.restype = ctypes.c_int
mapping = ctypes.c_void_p()
if loader.dlinfo(library._handle, 2, ctypes.byref(mapping)) or not mapping.value:
    raise SystemExit("dlinfo(RTLD_DI_LINKMAP) failed")
name = LinkMapHead.from_address(mapping.value).name
if not name:
    raise SystemExit("loader returned no library filename")
print(json.dumps({"soname": sys.argv[1], "resolved": name.decode("utf-8")}))
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def parse_readelf(text):
    require(re.search(r"^\s*Class:\s+ELF64\s*$", text, re.M), "Native runtime ELF must be 64-bit")
    require(re.search(r"^\s*Machine:\s+Advanced Micro Devices X86-64\s*$", text, re.M),
            "Native runtime ELF must be x86_64")
    kind = re.search(r"^\s*Type:\s+(EXEC|DYN)\b", text, re.M)
    require(kind is not None, "Native runtime must be an ELF executable or shared object")
    interpreters = re.findall(r"\[Requesting program interpreter:\s*([^\]]+)\]", text)
    require(len(interpreters) <= 1, "Ambiguous ELF interpreter")
    result = {"type": kind.group(1), "interpreter": interpreters[0] if interpreters else None,
              "needed": re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", text), "rpath": [], "runpath": []}
    for tag in ("RPATH", "RUNPATH"):
        values = re.findall(r"\(" + tag + r"\).*?\[([^\]]*)\]", text)
        require(len(values) <= 1, f"Ambiguous ELF {tag}")
        result[tag.lower()] = values[0].split(":") if values else []
    return result


def parse_ldd(text):
    require("not found" not in text, "Native dependency is not found")
    records, seen = [], set()
    for line in text.splitlines():
        if not line.strip():
            continue
        virtual = re.fullmatch(r"\s*(linux-vdso\.so\.\d+)\s+\(0x[0-9a-fA-F]+\)\s*", line)
        if virtual:
            continue
        found = re.fullmatch(r"\s*(\S+)\s+=>\s+(/\S+)\s+\(0x[0-9a-fA-F]+\)\s*", line)
        if found:
            name, path = found.groups()
        else:
            direct = re.fullmatch(r"\s*(/\S+)\s+\(0x[0-9a-fA-F]+\)\s*", line)
            require(direct is not None, f"Unrecognized dynamic loader result: {line}")
            path = direct.group(1)
            name = Path(path).name
        require(name not in seen, f"Duplicate dependency resolution: {name}")
        seen.add(name)
        records.append({"name": name, "path": path})
    require(bool(records), "Empty dynamic dependency resolution")
    return records


def declared_wrappers(source):
    names, inputs = set(), []
    for relative in WRAPPER_SOURCES:
        path = source / relative
        text = "\n".join(line.split("#", 1)[0] for line in path.read_text().splitlines())
        found = re.findall(r"\bwrap_elf\s*\(\s*[A-Za-z0-9_]+\s+([^\s)]+)", text)
        require(bool(found), f"No native wrapper declarations in {relative}")
        for name in found:
            require(re.fullmatch(r"lib[A-Za-z0-9_.+-]+\.so(?:\.[0-9]+)*", name),
                    f"Wrapper SONAME must be literal: {name}")
            names.add(name)
        inputs.append({"path": relative, "sha256": sha256(path)})
    return sorted(names), inputs


def dependency_identity(name, path, prefix, source):
    path = Path(path)
    require(path.is_absolute(), f"Non-absolute dependency resolution: {name}")
    resolved = path.resolve(strict=True)
    require(resolved.is_file(), f"Dependency is not a regular file: {name}")
    forbidden = (source.resolve(), Path("/p003/source"), Path("/p003/build"))
    require(not any(resolved.is_relative_to(item) for item in forbidden),
            f"Dependency borrowed from source/build tree: {name}: {resolved}")
    allowed = (prefix.resolve(), Path("/usr/lib"), Path("/lib"), Path("/lib64"))
    require(any(resolved.is_relative_to(item) for item in allowed),
            f"Dependency outside installed runtime or pinned OS libraries: {name}: {resolved}")
    with resolved.open("rb") as stream:
        require(stream.read(4) == b"\x7fELF", f"Resolved native dependency is not ELF: {name}")
    return {"name": name, "path": str(path), "realpath": str(resolved),
            "bytes": resolved.stat().st_size, "sha256": sha256(resolved)}


def validate_search_paths(paths, binary, prefix, source):
    allowed = (prefix.resolve(), Path("/usr/lib"), Path("/lib").resolve(), Path("/lib64").resolve())
    forbidden = (source.resolve(), Path("/p003/source"), Path("/p003/build"))
    for entry in paths:
        require(bool(entry), "ELF search path cannot contain the current directory")
        expanded = entry.replace("${ORIGIN}", str(binary.parent)).replace("$ORIGIN", str(binary.parent))
        require("$" not in expanded and Path(expanded).is_absolute(),
                f"ELF search path must be absolute or use a bounded $ORIGIN: {entry!r}")
        resolved = Path(expanded).resolve()
        require(not any(resolved.is_relative_to(root) for root in forbidden),
                f"ELF search path borrows from the source/build tree: {entry!r}")
        require(any(resolved.is_relative_to(root) for root in allowed),
                f"ELF search path escapes installed runtime or pinned OS libraries: {entry!r}")


class Collector:
    def __init__(self, prefix, source, output):
        self.prefix, self.source, self.output = prefix, source, output
        self.logs = output.parent / (output.stem + ".logs")
        self.logs.mkdir(parents=True, exist_ok=False)
        self.commands = []

    def command(self, argv):
        number = len(self.commands)
        record = {"argv": argv, "exit_code": None, "timed_out": False}
        try:
            result = subprocess.run(argv, env=SAFE_ENV, stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=30)
            record["exit_code"] = result.returncode
            stdout, stderr = result.stdout, result.stderr
        except subprocess.TimeoutExpired as error:
            record["timed_out"] = True
            stdout, stderr = error.stdout or b"", error.stderr or b""
        for channel, data in (("stdout", stdout), ("stderr", stderr)):
            path = self.logs / f"{number:04d}.{channel}.log"
            path.write_bytes(data)
            record[channel] = {"file": str(path.relative_to(self.output.parent)), "sha256": sha256(path)}
        self.commands.append(record)
        require(not record["timed_out"] and record["exit_code"] == 0,
                f"Native dependency command failed: {argv[0]} (exit {record['exit_code']})")
        return stdout.decode("utf-8", "strict")

    def inspect(self, path):
        start = len(self.commands)
        metadata = parse_readelf(self.command(["readelf", "-W", "-h", "-l", "-d", str(path)]))
        validate_search_paths(metadata["rpath"] + metadata["runpath"], path, self.prefix, self.source)
        dependencies = []
        if metadata["interpreter"] or metadata["needed"]:
            resolved = parse_ldd(self.command(["ldd", str(path)]))
            dependencies = [dependency_identity(item["name"], item["path"], self.prefix, self.source)
                            for item in resolved]
            names = {item["name"] for item in dependencies}
            require(set(metadata["needed"]).issubset(names), "Not every DT_NEEDED dependency was resolved")
        interpreter = None
        if metadata["interpreter"]:
            interpreter = dependency_identity("ELF interpreter", metadata["interpreter"], self.prefix, self.source)
        return {"path": str(path), "sha256": sha256(path), "elf": metadata,
                "interpreter": interpreter, "dependencies": dependencies,
                "command_indices": list(range(start, len(self.commands)))}


def collect(prefix, source, output):
    report = {"schema": "darling.p003.native-dependencies.v1", "phase": "P003", "status": "FAILED",
              "installation_prefix": str(prefix), "entries": [], "wrapped_libraries": [], "errors": []}
    collector = None
    try:
        require(prefix.is_absolute() and prefix.resolve(strict=True) == prefix,
                "Installation prefix must be an absolute real directory")
        require(prefix.is_dir(), "Installation prefix missing")
        require(output.is_absolute() and not output.resolve().is_relative_to(prefix),
                "Evidence must be outside the installation")
        collector = Collector(prefix, source, output)
        report["source_commit"] = collector.command(["git", "-C", str(source), "rev-parse", "HEAD"]).strip()
        require(re.fullmatch(r"[0-9a-f]{40}", report["source_commit"]), "Invalid source revision")
        collector.command(["ldconfig", "-p"])
        found = set()
        for directory, dirs, files in os.walk(prefix, followlinks=False):
            dirs[:] = sorted(name for name in dirs if not (Path(directory) / name).is_symlink())
            for name in sorted(files):
                path = Path(directory) / name
                if path.is_symlink() or not path.is_file():
                    continue
                with path.open("rb") as stream:
                    native = stream.read(4) == b"\x7fELF"
                if native:
                    relative = str(path.relative_to(prefix))
                    found.add(relative)
                    item = collector.inspect(path)
                    item["installed_path"] = relative
                    report["entries"].append(item)
        require(REQUIRED_ENTRYPOINTS.issubset(found),
                "Required native runtime entrypoints absent: " + ", ".join(sorted(REQUIRED_ENTRYPOINTS - found)))
        wrappers, report["wrapper_source_inputs"] = declared_wrappers(source)
        for soname in wrappers:
            # Resolve the exact unversioned SONAME used by wrapgen through the
            # actual glibc loader. A guessed cache basename is insufficient.
            loaded = json.loads(collector.command([sys.executable, "-c", LOAD_WRAPPER, soname]))
            require(loaded.get("soname") == soname, "Wrapper resolution identity mismatch")
            identity = dependency_identity(soname, loaded["resolved"], prefix, source)
            item = collector.inspect(Path(identity["realpath"]))
            item["soname"] = soname
            item["resolved_identity"] = identity
            report["wrapped_libraries"].append(item)
        report["status"] = "PASSED"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report["errors"].append(str(error))
    if collector:
        report["commands"] = collector.commands
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    report = collect(args.prefix, args.source, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "errors": report["errors"],
                      "native_entries": len(report["entries"]), "wrapped_libraries": len(report["wrapped_libraries"])}))
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
