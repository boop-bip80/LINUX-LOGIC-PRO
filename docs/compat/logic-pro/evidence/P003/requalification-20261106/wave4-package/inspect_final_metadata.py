#!/usr/bin/env python3
"""Record independent original-package metadata observations; no phase approval.

The unchanged Wave 3 comparator supplies the independently reviewed Mach-O parser
and exhaustive installed-byte comparison. This collector reads load commands,
archive alias chains, pinned build owners, original native logs and live paths.
It never executes an installed artifact or imports a production verifier.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import runpy
import struct
import subprocess
import tarfile
import zipfile


FRAMEWORKS = {
    "AppKit": ("C", "src/external/cocotron/AppKit", "AppKit"),
    "Foundation": ("C", "src/external/foundation", "Foundation_obj"),
    "CoreGraphics": ("A", "src/external/cocotron/CoreGraphics", "CoreGraphics"),
    "CoreText": ("A", "src/external/cocotron/CoreText", "CoreText"),
    "ImageIO": ("A", "src/frameworks/ImageIO", "ImageIO"),
    "QuartzCore": ("A", "src/external/cocotron/QuartzCore", "QuartzCore"),
    "AudioToolbox": ("A", "src/CoreAudio/AudioToolbox", "AudioToolbox"),
}
NATIVE = {"bin/darling", "bin/darling-coredump", "bin/darlingserver",
          "libexec/darling/usr/libexec/darling/mldr"}
PROBES = {"libexec/darling/usr/libexec/p003/p003_" + n
          for n in ("macho", "foundation", "gui")}
HELPER_SHA = "0115737614c47266678af87da2bb9c681af4c009c061b538299eacaef4104d62"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_file(repo, source, path):
    return subprocess.check_output(["git", "show", source + ":" + path], cwd=repo)


def readelf_metadata(raw):
    text = raw.decode("utf-8", "strict")
    typ = re.search(r"^\s*Type:\s+(\S+)", text, re.M)
    require(typ is not None, "missing ELF type")
    interpreter = re.findall(r"Requesting program interpreter: ([^\]]+)\]", text)
    require(len(interpreter) <= 1, "multiple ELF interpreters")
    result = {"type": typ.group(1), "interpreter": interpreter[0] if interpreter else None,
              "needed": re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", text)}
    for tag in ("RPATH", "RUNPATH"):
        result[tag.lower()] = [part for value in re.findall(
            r"\(" + tag + r"\).*?\[([^\]]+)\]", text) for part in value.split(":")]
    return result


def ldd_resolution(raw):
    rows = []
    for line in raw.decode("utf-8", "strict").splitlines():
        if not line.strip():
            continue
        if re.fullmatch(r"\s*linux-vdso\.so\.1\s+\(0x[0-9a-f]+\)\s*", line):
            continue
        match = re.fullmatch(r"\s*(\S+)\s+=>\s+(/\S+)\s+\(0x[0-9a-f]+\)\s*", line)
        if match:
            name, path = match.groups()
        else:
            match = re.fullmatch(r"\s*(/\S+)\s+\(0x[0-9a-f]+\)\s*", line)
            require(match is not None, "unexplained ldd output: " + line)
            path = match.group(1)
            name = PurePosixPath(path).name
        require(not path.startswith(("/p003/source", "/p003/build")), "native build-tree dependency")
        rows.append({"name": name, "path": path})
    require(rows and len({x["name"] for x in rows}) == len(rows), "empty or duplicate ldd identities")
    return rows


def load_commands(data, parser):
    result = []
    for image in parser(data):
        base, endian = image["base"], image["endian"]
        header = 32 if image["bits"] == 64 else 28
        count, size = struct.unpack_from(endian + "II", data, base + 16)
        at = base + header
        ids, dependencies, rpaths = [], [], []
        for _ in range(count):
            command, length = struct.unpack_from(endian + "II", data, at)
            kind = command & 0x7fffffff
            if kind in (12, 13, 24, 31, 32, 35, 28):
                offset, = struct.unpack_from(endian + "I", data, at + 8)
                require(12 <= offset < length, "bad load-command string offset")
                end = data.index(b"\0", at + offset, at + length)
                text = data[at + offset:end].decode("utf-8", "strict")
                if kind == 28:
                    rpaths.append(text)
                else:
                    require(length >= 24 and offset >= 24, "short dylib command")
                    timestamp, current, compatible = struct.unpack_from(endian + "III", data, at + 12)
                    item = {"path": text, "command": command, "timestamp": timestamp,
                            "current_version": current, "compatibility_version": compatible,
                            "weak": kind == 24}
                    (ids if kind == 13 else dependencies).append(item)
            at += length
        require(at == base + header + size, "load-command range mismatch")
        result.append({"bits": image["bits"], "cpu_type": image["cpu"],
                       "cpu_subtype": image["subtype"], "file_type": image["filetype"],
                       "install_names": ids, "dependencies": dependencies, "rpaths": rpaths})
    return result


def resolve(entries, virtual):
    require(virtual.startswith("/"), "nonabsolute dependency: " + virtual)
    path = "libexec/darling" + virtual
    chain = []
    for _ in range(41):
        parts = path.split("/")
        changed = False
        for i in range(1, len(parts) + 1):
            key = "/".join(parts[:i])
            require(key in entries, "missing installed path: " + key)
            row = entries[key]
            if row["kind"] == "symlink":
                target = ("libexec/darling" + row["target"] if row["target"].startswith("/")
                          else posixpath.normpath(posixpath.dirname(key) + "/" + row["target"]))
                require(target.startswith("libexec/darling/"), "alias leaves runtime root")
                chain.append({"path": key, "target": row["target"]})
                path = target + ("/" + "/".join(parts[i:]) if parts[i:] else "")
                changed = True
                break
        if not changed:
            require(entries[path]["kind"] == "file", "dependency is not a regular file")
            return {"resolved": path, "alias_chain": chain}
    raise ValueError("alias loop")


def native_review(z, phase, contents, wrappers, repo, source):
    name = "native-" + phase + ".json"
    report = json.loads(z.read(name))
    require(report["source_commit"] == source and not report["errors"], "native source/errors")
    require({e["installed_path"] for e in report["entries"]} == NATIVE, "native entry set")
    require({e["soname"] for e in report["wrapped_libraries"]} == set(wrappers), "wrapper source set")
    commands = report["commands"]
    require(len(commands) == 73, "incomplete native command record")
    raw = {}
    for index, command in enumerate(commands):
        require(command["exit_code"] == 0 and not command["timed_out"], "native command failed")
        for stream in ("stdout", "stderr"):
            data = z.read(command[stream]["file"])
            require(sha(data) == command[stream]["sha256"], "native raw-log hash mismatch")
            raw[index, stream] = data
    require(raw[0, "stdout"].decode().strip() == source, "native raw source commit")
    for item in report["wrapper_source_inputs"]:
        require(sha(source_file(repo, source, item["path"])) == item["sha256"], "native wrapper source hash")
    rows = []
    for entry in report["entries"] + report["wrapped_libraries"]:
        elf_index, ldd_index = entry["command_indices"]
        require(commands[elf_index]["argv"] == ["readelf", "-W", "-h", "-l", "-d", entry["path"]], "native readelf argv")
        require(commands[ldd_index]["argv"] == ["ldd", entry["path"]], "native ldd argv")
        elf = readelf_metadata(raw[elf_index, "stdout"])
        require(elf == entry["elf"], "raw ELF metadata differs from report")
        resolved = ldd_resolution(raw[ldd_index, "stdout"])
        require(resolved == [{"name": d["name"], "path": d["path"]} for d in entry["dependencies"]], "raw ldd differs from identity records")
        require(set(elf["needed"]) <= {d["name"] for d in resolved}, "missing direct NEEDED resolution")
        for identity in entry["dependencies"]:
            require(identity["realpath"].startswith(("/usr/lib/", "/lib/", "/lib64/")) and identity["bytes"] > 0
                    and re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]), "bad native identity")
        row = {"path": entry["path"], "recorded_sha256": entry["sha256"], "actual_raw_elf": elf,
               "raw_ldd_resolution": resolved, "recorded_dependencies": entry["dependencies"],
               "readelf_command": commands[elf_index], "ldd_command": commands[ldd_index]}
        if "installed_path" in entry:
            require(sha(contents[entry["installed_path"]]) == entry["sha256"], "actual installed ELF hash")
            require(entry["interpreter"]["path"] == elf["interpreter"], "ELF interpreter identity")
            row["installed_path"] = entry["installed_path"]
        else:
            soname = entry["soname"]
            dynamic_sonames = re.findall(r"\(SONAME\).*?\[([^\]]+)\]", raw[elf_index, "stdout"].decode())
            require(dynamic_sonames == [wrappers[soname]["elf_soname"]], "actual wrapper __elfname differs from host DT_SONAME")
            cache_rows = [{"abi": abi, "path": path} for abi, path in re.findall(
                r"(?m)^\s*" + re.escape(dynamic_sonames[0]) + r"\s+\(([^)]*)\)\s+=>\s+(\S+)\s*$",
                raw[1, "stdout"].decode())]
            require(any("x86-64" in row["abi"] for row in cache_rows), "versioned wrapper name missing from x86_64 loader cache")
            dlopen_index = elf_index - 1
            require(commands[dlopen_index]["argv"][-1] == soname, "dlopen requested soname")
            loaded = json.loads(raw[dlopen_index, "stdout"])
            identity = entry["resolved_identity"]
            require(loaded == {"soname": soname, "resolved": identity["path"]}, "raw dlopen resolution")
            require(identity["name"] == soname and identity["realpath"] == entry["path"]
                    and identity["sha256"] == entry["sha256"] and identity["bytes"] > 0, "wrapped canonical identity")
            require(re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), "wrapped hash format")
            row.update({"soname": soname, "dlopen": loaded, "resolved_identity": identity,
                        "dlopen_command": commands[dlopen_index], "wrapper": wrappers[soname],
                        "raw_dt_soname": dynamic_sonames[0], "versioned_loader_cache": cache_rows})
        rows.append(row)
    return {"file": name, "sha256": sha(z.read(name)), "raw_logs_verified": 146,
            "entries": rows, "wrapper_source_inputs": report["wrapper_source_inputs"]}


def runtime_binding(z, report_path, contents, expected_images, source):
    report = json.loads(z.read(report_path))
    root = report_path.rsplit("/", 1)[0]
    require(report.get("source_revision", report.get("source_commit")) == source, "runtime source")
    commands = [c for c in report["commands"] if c["label"] == "gui"]
    require(len(commands) == 1 and commands[0]["exit_code"] == 0, "missing successful live GUI command")
    command = commands[0]
    stdout = z.read(root + "/" + command["stdout"]["file"])
    require(sha(stdout) == command["stdout"]["sha256"], "GUI stdout original hash")
    images = [line[len("P003_IMAGE "):] for line in stdout.decode().splitlines() if line.startswith("P003_IMAGE ")]
    require(images == expected_images, "live image set/order differs from actual install IDs")
    if "loaded_framework_paths" in report:
        require(report["loaded_framework_paths"] == images, "reported live paths disagree with raw stdout")
    binaries = []
    for name, identity in report["binaries"].items():
        path = identity["path"].removeprefix("/opt/darling-p003/")
        require(path in PROBES and len(contents[path]) == identity["bytes"] and sha(contents[path]) == identity["sha256"], "runtime binary differs from package")
        binaries.append({"name": name, **identity})
    require(len(binaries) == 3, "missing probe binary identities")
    return {"report": report_path, "report_sha256": sha(z.read(report_path)), "nonce": report["nonce"],
            "gui_command": command, "loaded_framework_paths": images, "binaries": binaries}


def run(args, report):
    repo, out = args.repo, args.output
    method_path = repo / "docs/compat/logic-pro/evidence/P003/requalification-20261106/wave3-package-review/compare_original_packages.py"
    require(sha(method_path.read_bytes()) == HELPER_SHA, "inherited helper changed")
    method = runpy.run_path(str(method_path))
    comparison = json.loads((out / "original-package-comparison.json").read_text())
    require(comparison["expected_source"] == args.source and comparison["status"] == "INSTALLED_PACKAGE_BYTES_CLASSIFIED", "byte comparison incomplete")
    require(not comparison["tar_metadata_differences"] and not comparison["structural_inventory_differences"], "tar/structural differences require separate adjudication")
    for host in comparison["hosts"]:
        require(host["manifest_second"] is not None and host["first_second_manifest_changes"] == []
                and not host["archive_manifest_mismatches"], "missing or differing install manifest")
    report["byte_comparison_sha256"] = sha((out / "original-package-comparison.json").read_bytes())
    report["tar_metadata_adjudication"] = {"differences": [], "scope": "All enumerated original tar member metadata"}
    report["linker_adjudication"] = comparison["source_built_linker_differences"]
    require(all(x.get("source_bound_timestamp_banner_only") for x in report["linker_adjudication"]), "unexplained linker banner difference")
    report["linker_byte_limitation"] = comparison["linker_byte_limitation"]
    gitdir = Path(subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=repo, text=True).strip())
    owners = {}
    for name, (version, owner, target) in FRAMEWORKS.items():
        module = next((m for m in ("src/external/cocotron", "src/external/foundation")
                       if owner == m or owner.startswith(m + "/")), None)
        path = owner + "/CMakeLists.txt"
        if module:
            pin = subprocess.check_output(["git", "ls-tree", args.source, "--", module], cwd=repo, text=True).split()[2]
            data = subprocess.check_output(["git", "--git-dir=" + str(gitdir / "modules" / module), "show", pin + ":" + path[len(module) + 1:]], cwd=repo)
        else:
            pin, data = args.source, source_file(repo, args.source, path)
        owners[name] = {"owner": owner, "target": target, "module": module, "commit": pin,
                        "path": path, "sha256": sha(data), "bytes": len(data),
                        "target_version_lines": [{"line": i, "text": line} for i, line in enumerate(data.decode().splitlines(), 1)
                                                 if re.search(r"add_framework|add_separated_framework|VERSION|" + re.escape(name), line)]}
    report["source_owners"] = owners
    wrappers = {}
    report["source_bindings"] = []
    for path in ("src/native/CMakeLists.txt", "src/CoreAudio/CMakeLists.txt"):
        data = source_file(repo, args.source, path)
        report["source_bindings"].append({"path": path, "sha256": sha(data), "bytes": len(data)})
        for match in re.finditer(r'^\s*wrap_elf\((\w+)\s+(\S+?)(?:\s+"([^"]+)")?\)\s*$', data.decode(), re.M):
            name, soname, destination = match.groups()
            require(soname not in wrappers, "duplicate wrapper soname")
            installed = "libexec/darling/" + (destination or "usr/lib/native") + "/lib" + name + ".dylib"
            wrappers[soname] = {"source": path, "module": name, "installed_path": installed}
    require(len(wrappers) == 21, "source does not define the required 21 wrappers")
    for path in ("tests/compat/logic-pro/build/images.h", "tests/compat/logic-pro/build/gui.m",
                 "tools/compat/logic-pro/review_installed_runtime.py", "tools/compat/logic-pro/review_package_archive.py",
                 "cmake/wrap_elf.cmake", "src/libelfloader/wrapgen/wrapgen.cpp",
                 "src/libelfloader/wrapgen/print_wrapped_elf.cpp"):
        data = source_file(repo, args.source, path)
        report["source_bindings"].append({"path": path, "sha256": sha(data), "bytes": len(data)})
    paths = {n: "libexec/darling/System/Library/Frameworks/" + n + ".framework/Versions/" + v + "/" + n
             for n, (v, _, _) in FRAMEWORKS.items()}
    images = [paths[n][len("libexec/darling"):] for n in FRAMEWORKS]
    report["hosts"] = []
    contents_a = None
    for label in ("a", "b"):
        with zipfile.ZipFile(args.originals / ("build-" + label + ".zip")) as z:
            first, second = [json.loads(z.read("install-" + phase + ".json")) for phase in ("first", "second")]
            require(first["source_commit"] == second["source_commit"] == args.source, "manifest source")
            require(z.read("install-first.json") == z.read("install-second.json"), "install reports differ")
            entries, contents = {}, {}
            wanted = set(paths.values()) | NATIVE | PROBES | {w["installed_path"] for w in wrappers.values()}
            with tarfile.open(fileobj=z.open("runtime-prefix.tar.gz"), mode="r|gz") as tar:
                for member in tar:
                    path = member.name.removeprefix("./")
                    if path == ".":
                        continue
                    require(path not in entries, "duplicate archive path")
                    entries[path] = {"kind": "file" if member.isfile() else "symlink" if member.issym() else "directory" if member.isdir() else "other",
                                     "mode": member.mode, "bytes": member.size, "target": member.linkname}
                    if path in wanted:
                        require(member.isfile(), "selected member is not regular")
                        contents[path] = tar.extractfile(member).read()
            require(set(contents) == wanted, "missing selected package images")
            actual_manifest = {e["path"]: e for e in first["entries"]}
            frames = {f["name"]: f for f in first["frameworks"]}
            require(set(frames) == set(FRAMEWORKS), "framework set")
            compile_commands = json.loads(z.read("compile_commands.json"))
            install_lines = z.read("cmake-install-manifest-first.txt").decode().splitlines()
            framework_rows = []
            for name, (version, owner, target) in FRAMEWORKS.items():
                path, claimed = paths[name], frames[name]
                data = contents[path]
                require(claimed["installed_path"] == path and claimed["source_owner"] == owner
                        and claimed["cmake_source_target"] == target and claimed["sha256"] == sha(data), "framework identity/owner")
                parsed = load_commands(data, method["macho"])
                require(len(parsed) == 1 and parsed[0]["bits"] == 64 and parsed[0]["cpu_type"] == 16777223 and parsed[0]["file_type"] == 6, "framework Mach-O type")
                actual = parsed[0]
                require(len(actual["install_names"]) == 1 and actual["install_names"][0]["path"] == path[len("libexec/darling"):], "framework install ID")
                original = claimed["macho"]["architectures"]
                require(len(original) == 1 and original[0]["install_name"] == actual["install_names"][0]["path"]
                        and original[0]["rpaths"] == actual["rpaths"], "manifest load metadata")
                require([(d["path"], d["weak"]) for d in actual["dependencies"]]
                        == [(d["path"], d["weak"]) for d in original[0]["dependencies"]], "manifest dependencies")
                alias = resolve(entries, "/System/Library/Frameworks/" + name + ".framework/" + name)
                require(alias["resolved"] == path, "public framework alias")
                dependencies = []
                for dependency in actual["dependencies"]:
                    resolved = resolve(entries, dependency["path"])
                    dependencies.append({**dependency, **resolved, "installed_identity": actual_manifest[resolved["resolved"]]})
                commands = [c for c in compile_commands if c["file"].startswith("/p003/source/" + owner + "/")
                            and ("CMakeFiles/" + target + ".dir/") in c.get("command", "")]
                require(commands, "no actual compile-owner command")
                require(install_lines.count("/opt/darling-p003/" + path) == 1, "multiple framework installation records")
                framework_rows.append({"name": name, "installed_path": path, "bytes": len(data), "sha256": sha(data),
                                       "macho": actual, "public_alias": alias, "direct_dependencies": dependencies,
                                       "source_owner": owners[name], "compile_owner_commands": len(commands), "compile_owner_example": commands[0]})
            wrapper_rows = {}
            for soname, wrapper in wrappers.items():
                data = contents[wrapper["installed_path"]]
                parsed = method["macho"](data)
                sections = [s for i in parsed for s in i["sections"] if (s["segment"], s["name"]) == ("__TEXT", "__elfname")]
                require(len(sections) == 1, "wrapper has no unique source-defined __elfname section")
                section = sections[0]
                value = data[section["start"]:section["start"] + section["size"]]
                require(1 < len(value) <= 100 and value.endswith(b"\0") and value.count(b"\0") == 1,
                        "wrapper __elfname is not the generated NUL-terminated string")
                wrapper_rows[soname] = {**wrapper, "sha256": sha(data), "bytes": len(data),
                                       "lookup_soname": soname, "elf_soname": value[:-1].decode("ascii"),
                                       "elfname_section": section, "elfname_bytes_hex": value.hex(),
                                       "source_contract": "wrapgen.cpp emits resolved DT_SONAME in __TEXT,__elfname and passes it to dlopen_fatal"}
            native = [native_review(z, phase, contents, wrapper_rows, repo, args.source) for phase in ("first", "second")]
            require([n["recorded_sha256"] for n in native[0]["entries"]] == [n["recorded_sha256"] for n in native[1]["entries"]], "native reinstall identity difference")
            readback = []
            for entry in native[0]["entries"]:
                if "installed_path" not in entry:
                    continue
                path = entry["installed_path"]
                fd = os.memfd_create("p003-original-ELF", 0)
                try:
                    require(os.write(fd, contents[path]) == len(contents[path]), "short in-memory ELF write")
                    command = ["readelf", "-W", "-h", "-l", "-d", "/proc/self/fd/" + str(fd)]
                    completed = subprocess.run(command, pass_fds=(fd,), capture_output=True)
                finally:
                    os.close(fd)
                require(completed.returncode == 0 and not completed.stderr, "independent readelf failed")
                actual = readelf_metadata(completed.stdout)
                require(actual == entry["actual_raw_elf"], "actual ELF metadata differs from original native record")
                filename = "readelf-" + label + "-" + PurePosixPath(path).name + ".txt"
                (out / filename).write_bytes(completed.stdout)
                readback.append({"installed_path": path, "sha256": sha(contents[path]), "actual_elf": actual,
                                 "readelf_command": command, "raw_output": filename, "raw_output_sha256": sha(completed.stdout)})
            uninstall = json.loads(z.read("uninstall.json"))
            require(uninstall["manifest_source_commit"] == args.source and uninstall["prefix"] == "/opt/darling-p003"
                    and uninstall["prefix_absent"] and uninstall["removed_entries"] == len(entries)
                    and not uninstall["errors"], "uninstall inventory/source mismatch")
            ownership = [json.loads(z.read(f)) for f in ("install-owner.json", "install-owner-second.json")]
            require(all(o["prefix"] == "/opt/darling-p003" for o in ownership) and ownership[0]["nonce"] != ownership[1]["nonce"], "reused installation ownership")
            live = [runtime_binding(z, "probes-" + phase + "/report.json", contents, images, args.source) for phase in ("first", "second")]
            summary = json.loads(z.read("build-summary.json"))
            lock = json.loads(z.read("source-lock-verification.json"))
            require(summary["source_commit"] == lock["root_commit"] == args.source and summary["exit_code"] == 0, "build source/exit mismatch")
            report["hosts"].append({"host": label.upper(), "frameworks": framework_rows, "native": native,
                                    "actual_elf_readback": readback, "live_runtime": live, "uninstall": uninstall,
                                    "install_ownership": ownership, "entry_counts": dict(collections.Counter(e["kind"] for e in entries.values())),
                                    "install_manifest_sha256": sha(z.read("install-first.json")),
                                    "compile_commands_sha256": sha(z.read("compile_commands.json")),
                                    "cmake_install_manifest_duplicate_paths": [p for p, count in collections.Counter(install_lines).items() if count > 1],
                                    "source_lock_sha256": summary["source_lock_sha256"],
                                    "toolchain_lock_sha256": sha(z.read("toolchain.lock.json")), "build_summary": summary})
            if label == "a":
                contents_a = contents
    a, b = report["hosts"]
    require(a["toolchain_lock_sha256"] == b["toolchain_lock_sha256"] and a["source_lock_sha256"] == b["source_lock_sha256"], "paired build input mismatch")
    for phase in range(2):
        for left, right in zip(a["native"][phase]["entries"], b["native"][phase]["entries"]):
            require(left["path"] == right["path"] and left["recorded_sha256"] == right["recorded_sha256"]
                    and left["recorded_dependencies"] == right["recorded_dependencies"] and left["actual_raw_elf"] == right["actual_raw_elf"], "cross-host native provenance mismatch")
    with zipfile.ZipFile(args.originals / "independent-runtime.zip") as z:
        package = json.loads(z.read("package-review.json"))
        expected_a = comparison["hosts"][0]
        require(package["source_commit"] == args.source and package["archive_sha256"] == expected_a["tar"]["sha256"]
                and package["archive_bytes"] == expected_a["tar"]["bytes"]
                and package["manifest_sha256"] == expected_a["manifest_first"]["sha256"]
                and package["entry_count"] == sum(expected_a["entry_counts"].values()) and not package["errors"]
                and package["installed_readback"] == "PASS", "independent replay package binding")
        require(package["driver_sha256"] == sha(source_file(repo, args.source, "tools/compat/logic-pro/review_package_archive.py")), "package driver source")
        live = runtime_binding(z, "runtime/report.json", contents_a, images, args.source)
        runtime = json.loads(z.read("runtime/report.json"))
        driver = z.read("runtime/reviewer-driver.py")
        require(sha(driver) == runtime["driver_sha256"] == sha(source_file(repo, args.source, "tools/compat/logic-pro/review_installed_runtime.py")), "runtime reviewer source")
        isolation = runtime["isolation"]
        mounts = z.read("runtime/" + isolation["mountinfo"]["file"])
        require(sha(mounts) == isolation["mountinfo"]["sha256"] and isolation["source_and_build_absent"], "replay isolation record")
        require(b"/p003/source" not in mounts and b"/p003/build" not in mounts, "source/build path in replay mounts")
        require(sha(z.read("toolchain.lock.json")) == a["toolchain_lock_sha256"], "replay toolchain input")
        report["independent_replay"] = {"package": package, "package_report_sha256": sha(z.read("package-review.json")),
                                        "live_runtime": live, "isolation": isolation, "mountinfo_sha256": sha(mounts)}
    report["status"] = "OBSERVATIONS_CHECKED"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "originals", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"schema": "p003.wave4.final-metadata-observations.v1", "reviewer": "/root/wave4_package",
              "source": args.source, "run": 42180484781, "phase_acceptance": False,
              "helper_sha256": sha(Path(__file__).read_bytes()), "status": "IN_PROGRESS",
              "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "limitations": ["External host-library size/hash identities are original host measurements; their raw dlopen/readelf/ldd resolution is independently reconstructed, but those external library bytes are not in the installed-prefix archives.",
                              "The seven frameworks' direct load dependencies and all encountered alias chains are inspected; no recursively parsed transitive Mach-O graph is claimed.",
                              "Framework build-tree LC_RPATH values are retained verbatim. Inspected direct dependencies are absolute installed paths, and the separate live replay has no source/build mounts."]}
    try:
        run(args, report)
    except BaseException as error:
        report["status"] = "FAILED"
        report["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        report["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (args.output / "framework-native-lifecycle.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "source": report["source"], "hosts": [
        {"host": h["host"], "frameworks": len(h["frameworks"]),
         "direct_framework_dependencies": sum(len(f["direct_dependencies"]) for f in h["frameworks"]),
         "native_records_each_install": len(h["native"][0]["entries"]),
         "raw_native_logs": sum(n["raw_logs_verified"] for n in h["native"]),
         "actual_elf_readback": len(h["actual_elf_readback"]), "entry_counts": h["entry_counts"]}
        for h in report["hosts"]], "live_campaigns": 5}, indent=2))
