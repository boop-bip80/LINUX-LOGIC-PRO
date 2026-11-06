#!/usr/bin/env python3
"""Independently inspect original P003 source/build/lifecycle evidence.

Reads an untouched extracted build and a separately checked ZIP member receipt.
It never calls the aggregate P003 PASS verifier, runs Darling, or edits inputs.
Package nondeterminism and live runtime outputs belong to separate reviewers.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import stat
import struct
import subprocess


REPO = Path(__file__).resolve().parents[7]
FROZEN_LOCK = "9438c463449752b1e84b45706bf0cbeec25f803eb1e46870f23908e53183421e"
FROZEN_IMAGE = "6d98365bd067b28c8e8b71e1b34a7200bca5aad0c790cbdd808fe2f14f67d4d5"
IMAGE_ID = "sha256:eddd66602086a48927c87aff7b086c338f86fe6b67690b2f91f663e7646441de"


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def git(commit, path):
    return subprocess.run(["git", "show", commit + ":" + path], cwd=REPO,
                          check=True, stdout=subprocess.PIPE).stdout


def identity(environment):
    result = copy.deepcopy(environment)
    dsym = result["tools"]["dsymutil"]
    pattern = r"(?m)^([ \t]*Host CPU:)[^\r\n]*$"
    require(len(re.findall(pattern, dsym["version_output"])) <= 1, "Ambiguous CPU observation")
    dsym["version_output"] = re.sub(pattern, r"\1 <host observation>", dsym["version_output"])
    return result


def differences(first, second, prefix=""):
    if isinstance(first, dict) and isinstance(second, dict):
        return [item for key in sorted(set(first) | set(second))
                for item in differences(first.get(key), second.get(key),
                                        prefix + "." + key if prefix else key)]
    return [] if canonical(first) == canonical(second) else [prefix]


def macho_object(path):
    """Decode only public object headers/sections/relocations/symbol names."""
    data = path.read_bytes()
    header = struct.unpack_from("<IiiIIIII", data)
    require(header[0] == 0xFEEDFACF and header[1] == 0x1000007 and header[3] == 1,
            "Expected generated x86_64 Mach-O object")
    require(32 + header[5] <= len(data), "Truncated object commands")
    position, sections, symbols = 32, [], []
    for _ in range(header[4]):
        command, length = struct.unpack_from("<II", data, position)
        require(length >= 8 and position + length <= 32 + header[5], "Invalid object command")
        if command == 0x19:
            count = struct.unpack_from("<I", data, position + 64)[0]
            require(72 + count * 80 <= length, "Truncated section array")
            for index in range(count):
                at = position + 72 + index * 80
                name = data[at:at + 16].split(b"\0", 1)[0].decode()
                relocation_offset, relocation_count = struct.unpack_from("<II", data, at + 56)
                require(relocation_offset + relocation_count * 8 <= len(data), "Truncated relocations")
                relocations = []
                for number in range(relocation_count):
                    address, bits = struct.unpack_from("<iI", data, relocation_offset + number * 8)
                    relocations.append({"address": address, "type": bits >> 28,
                                        "bytes": 1 << ((bits >> 25) & 3),
                                        "pc_relative": bool((bits >> 24) & 1)})
                sections.append({"name": name, "relocations": relocations})
        elif command == 2:
            offset, count, strings, size = struct.unpack_from("<IIII", data, position + 8)
            require(offset + count * 16 <= len(data) and strings + size <= len(data),
                    "Truncated symbol table")
            for number in range(count):
                string_index = struct.unpack_from("<I", data, offset + number * 16)[0]
                require(string_index < size, "Invalid symbol string index")
                end = data.find(b"\0", strings + string_index, strings + size)
                require(end >= 0, "Unterminated symbol")
                name = data[strings + string_index:end].decode()
                if "reltable" in name:
                    symbols.append(name)
        position += length
    require(position == 32 + header[5], "Object command size mismatch")
    bad = [row for section in sections if section["name"] == "__const"
           for row in section["relocations"] if row["type"] in (0, 5)
           and row["bytes"] == 4 and not row["pc_relative"]]
    return {"sha256": sha(data), "sections": sections, "relative_table_symbols": symbols,
            "unsupported_relative_fixups": len(bad)}


def source_checks(root, commit, pinned, classifications):
    source = load(root / "source-lock-verification.json")
    require(source["root_commit"] == commit and source["result"] == "PASS", "Wrong source revision")
    expected = {row["path"]: {key: row[key] for key in ("path", "commit", "tree", "resolved_url")}
                for row in pinned["submodules"]}
    actual = {row["path"]: row for row in source["submodules"]}
    require(len(source["submodules"]) == len(actual) == len(expected) == 160,
            "Wrong recursive pin inventory")
    require(canonical(actual) == canonical(expected), "Actual child identities differ from committed pins")
    require(source["verified_gitlinks"] == 160 and source["verified_repositories"] == 161
            and source["direct_gitlinks"] == 149 and source["verified_lfs_payloads"] == 44,
            "Missing repository/LFS coverage")
    require(source["verified_lfs_bytes"] == sum(row["size"] for row in pinned["lfs_objects"]),
            "LFS payload byte coverage differs")
    require(all(source[key] == 0 for key in ("uninitialized", "mismatched", "conflicted", "dirty_repositories")),
            "Incomplete or dirty source")
    heads = {}
    for line in (root / "submodule-heads.txt").read_text().splitlines():
        match = re.fullmatch(r" ([0-9a-f]{40}) (\S+)(?: \(.*\))?", line)
        require(match and match[2] not in heads, "Malformed/dirty/duplicate raw submodule status")
        heads[match[2]] = match[1]
    require(heads == {name: row["commit"] for name, row in expected.items()}, "Raw child HEADs differ")
    for when in ("before", "after"):
        path = root / ("source-status-" + when + ".txt")
        require(stat.S_ISREG(path.lstat().st_mode) and path.read_bytes() == b"",
                "Source status is dirty, missing or redirected")

    report = load(root / "source-classifications.json")
    originals = {row["id"]: row for row in classifications["evidence"]}
    current = {row["id"]: row for row in classifications["current_source_reaudit"]["evidence"]}
    checked = {row["id"]: row for row in report["checked"]}
    require(len(report["checked"]) == len(checked) == len(originals) == len(current) == 63
            and set(checked) == set(originals) == set(current), "Classification ID set differs")
    anchor = classifications["current_source_reaudit"]["source_anchor"]
    require(report["current_commit"] == commit and report["current_source_anchor"] == anchor
            and report["inspected_commit"] == classifications["inspected_commit"]
            and report["failures"] == [] and report["status"] == "PASS", "Classification identity/failure")
    for name, row in checked.items():
        original, now = originals[name], current[name]
        for key in ("id", "category", "path", "blob_sha1", "line_start", "line_end", "excerpt_sha256"):
            require(canonical(row[key]) == canonical(original[key]), "Changed original citation: " + name)
        require(row["repository"] == original.get("repository", ".")
                and row["repository_commit"] == original.get("repository_commit", classifications["inspected_commit"])
                and row["gitlink_chain"] == original.get("gitlink_chain", [])
                and row["launch_stages"] == original.get("launch_stages", []), "Changed historical ownership")
        expected_current = {"source_anchor": anchor, "repository": now["repository"],
                            "path": now["path"],
                            "repository_commit": commit if now["repository"] == "." else now["repository_commit"],
                            "gitlink_chain": now["gitlink_chain"], "blob_sha1": now["blob_sha1"],
                            "line_start": now["line_start"], "line_end": now["line_end"],
                            "excerpt_sha256": now["excerpt_sha256"],
                            "assertions_verified": len(now["contains"]), "original_assertions_preserved": True}
        require(canonical(row["current_source"]) == canonical(expected_current),
                "Complete current citation differs: " + name)
        if now["repository"] != ".":
            require(expected[now["repository"]]["commit"] == now["repository_commit"],
                    "Citation owner not at pinned child")
    files = len({(row["repository"], row["path"]) for row in checked.values()})
    require(report["checked_count"] == 63 and report["source_file_count"] == files,
            "Classification counts disagree")
    require((root / "source-classifications.log").read_text() ==
            "source classifications: PASS; 63 citations verified\n", "Contradictory raw classification log")
    return {"source_summary": {key: value for key, value in source.items() if key != "submodules"},
            "all_160_commit_tree_url_rows_match": True, "all_160_raw_heads_match": True,
            "classification_count": 63, "source_file_count": files, "source_anchor": anchor,
            "all_historical_and_current_citation_identities_match": True,
            "clean_before_and_after": True}


def codegen_checks(root, commit, lock, hashes):
    folder = root / "unwind-codegen"
    proof = load(folder / "report.json")
    require(proof["status"] == "PASS" and proof["errors"] == []
            and proof["toolchain_sha256"] == FROZEN_LOCK, "Codegen proof not successful/bound")
    require(proof["compiler"]["sha256"] == lock["environment"]["tools"]["clang"]["sha256"]
            and re.search(r"clang version 14\.0\.0", proof["compiler"]["version"]), "Unpinned codegen compiler")
    require(proof["helper_sha256"] == sha(git(commit, "cmake/darling_unwind_configuration.cmake")),
            "Changed codegen helper")
    require(proof["source_inputs"] == {
        "/p003/source/src/external/libunwind/libunwind/src/Registers.hpp":
            "32423fef71c163f1315b031ed14f34f7e7d1e08b68732041b8d39efbf2e5ef30",
        "/p003/source/src/external/libunwind/libunwind/include/libunwind.h":
            "09e29df5f6d80f0555a0a3839f836052ded9698e4a91607e5cb033bd10401f2e"}, "Different register source inputs")
    for name, expected in proof["evidence"].items():
        require(hashes["unwind-codegen/" + name] == expected, "Changed raw codegen evidence: " + name)
    layouts = {}
    for variant, target in (("control", "control_static"), ("repaired", "unwind_static")):
        layout = macho_object(folder / ("macho/build/CMakeFiles/" + target + ".dir/register_names.cpp.o"))
        for key in ("sha256", "sections", "relative_table_symbols"):
            require(canonical(layout[key]) == canonical(proof["macho"][variant][key]),
                    "Claimed object layout differs from raw bytes")
        layouts[variant] = layout
    require(layouts["control"]["relative_table_symbols"]
            and layouts["control"]["unsupported_relative_fixups"] > 0
            and not layouts["repaired"]["relative_table_symbols"]
            and layouts["repaired"]["unsupported_relative_fixups"] == 0,
            "Actual generated objects do not show control/repair distinction")
    registers = dict(enumerate(["rax", "rdx", "rcx", "rbx", "rsi", "rdi", "rbp", "rsp",
                                "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]))
    registers.update({-2: "rsp", -1: "rip"})
    registers.update({17 + n: "xmm" + str(n) for n in range(16)})
    numbers = list(range(-8, 41)) + [-2147483648, 2147483647]
    expected = "".join(str(n) + " " + registers.get(n, "unknown register") + "\n" for n in numbers).encode()
    for variant in ("control", "repaired"):
        actual = (folder / (variant + "-behavior.stdout.log")).read_bytes()
        require(actual == expected and proof["behavior"]["stdout_sha256"][variant] == sha(actual),
                "Register behavior differs from 51 fixed vectors")
    for kind in ("macho", "native"):
        rows = load(folder / kind / "build/compile_commands.json")
        for row in rows:
            args = shlex.split(row["command"])
            require(("-fno-jump-tables" in args) == ("CMakeFiles/unwind_static.dir/" in row["command"]),
                    "Proof flag not private to repaired target")
    return {"compiler": proof["compiler"], "raw_evidence_files": len(proof["evidence"]),
            "native_vectors": len(numbers), "native_stdout_sha256": sha(expected),
            "control_object_sha256": layouts["control"]["sha256"],
            "repaired_object_sha256": layouts["repaired"]["sha256"],
            "control_relative_fixups": layouts["control"]["unsupported_relative_fixups"],
            "repaired_relative_fixups": layouts["repaired"]["unsupported_relative_fixups"],
            "control_symbols": layouts["control"]["relative_table_symbols"],
            "repaired_symbols": layouts["repaired"]["relative_table_symbols"]}


def build_checks(root, commit):
    commands = load(root / "compile_commands.json")
    compilers = Counter(row["command"].split(maxsplit=1)[0] for row in commands)
    require(set(compilers) == {"/usr/bin/clang-14", "/usr/bin/clang++-14"}, "Unexpected compilation driver")
    objc = [row for row in commands if "/src/external/objc4/runtime/" in row["file"]]
    require(objc, "No actual pinned objc4 compilation")
    for row in objc:
        args = shlex.split(row["command"])
        require("-DNDEBUG" in args and not any(re.match(r"-D(?:DEBUG|OBJC_IS_DEBUG_BUILD)(?:=|$)", arg)
                                              for arg in args), "objc4 header mode overridden")
        require("-target" in args and args[args.index("-target") + 1] == "x86_64-apple-darwin20",
                "objc4 target differs")
    jump = [row for row in commands if "-fno-jump-tables" in row["command"]]
    expected_jump = [row for row in commands if "CMakeFiles/unwind_static.dir/" in row["command"]
                     and Path(row["file"]).suffix in (".cpp", ".cc", ".cxx")]
    require(jump == expected_jump and jump, "Private static C++ unwind option changed scope")
    cache = {}
    for line in (root / "CMakeCache.txt").read_text().splitlines():
        if line and not line.startswith(("#", "//")) and ":" in line and "=" in line:
            name, value = line.split("=", 1)
            cache[name.split(":", 1)[0]] = value
    expected_cache = {"CMAKE_BUILD_TYPE": "Release", "CMAKE_C_COMPILER": "/usr/bin/clang-14",
                      "CMAKE_CXX_COMPILER": "/usr/bin/clang++-14", "CMAKE_INSTALL_PREFIX": "/opt/darling-p003",
                      "COMPONENTS": "cli,gui", "DARLING_NO_CCACHE": "ON", "DARLING_P003_PROBES": "ON",
                      "DEBIAN_PACKAGING": "ON", "ENABLE_METAL": "ON", "TARGET_i386": "OFF", "TARGET_x86_64": "ON"}
    require(all(cache[key] == value for key, value in expected_cache.items()), "Actual CMake cache differs")
    configure = (root / "configure.log").read_text()
    require("-- The C compiler identification is Clang 14.0.0" in configure
            and "-- The CXX compiler identification is Clang 14.0.0" in configure
            and configure.rstrip().endswith("-- Build files have been written to: /p003/build"),
            "Incomplete/mismatched real configure log")
    build = (root / "build.log").read_text()
    progress = [(int(a), int(b)) for a, b in re.findall(r"^\[(\d+)/(\d+)\]", build, re.M)]
    require(progress, "No actual Ninja build steps")
    total = progress[-1][1]
    require(progress == [(n, total) for n in range(1, total + 1)], "Missing/reordered/incomplete build steps")
    require(not re.search(r"^(?:FAILED:|ninja: build stopped)", build, re.M), "Compile failure in raw log")
    return {"compile_commands": len(commands), "compiler_drivers": dict(compilers),
            "complete_ninja_steps": total, "configure_complete": True,
            "actual_cache": expected_cache, "objc4_commands": len(objc),
            "objc4_all_ndebug_without_injected_debug_macro": True,
            "private_unwind_cxx_commands": len(jump)}


def lifecycle_checks(root, commit, pinned):
    reports = [load(root / ("install-" + when + ".json")) for when in ("first", "second")]
    expected_pins = {row["path"]: row["commit"] for row in pinned["submodules"] if row["parent_path"] == "."}
    for report in reports:
        require(report["status"] == "PASSED" and report["errors"] == [] and report["source_commit"] == commit,
                "Install report failed or belongs to another source")
        require(report["configuration"] == {"components": "cli,gui", "install_prefix": "/opt/darling-p003",
                                              "source_dir": "/p003/source"}, "Install configuration differs")
        actual_pins = {row["path"]: row["sha"] for row in report["submodules"]}
        require(actual_pins == expected_pins and len(report["submodules"]) == 149, "Install source pins differ")
        require(len(report["entries"]) == len({row["path"] for row in report["entries"]}) > 0,
                "Empty or duplicate installation inventory")
    require(canonical(reports[0]["entries"]) == canonical(reports[1]["entries"]), "Reinstall inventory differs")
    first, second = [(root / ("cmake-install-manifest-" + when + ".txt")).read_bytes() for when in ("first", "second")]
    require(first == second and first, "Actual CMake install manifests differ/missing")
    logs = [(root / ("install-" + when + ".log")).read_bytes() for when in ("first", "second")]
    require(logs[0] == logs[1] and logs[0].startswith(b'-- Install configuration: "Release"\n'),
            "Actual install/reinstall logs differ or are incomplete")
    require(logs[0].rstrip().endswith(b"/usr/libexec/p003/p003_gui"), "Install log ends prematurely")
    uninstall = load(root / "uninstall.json")
    require(uninstall == {"schema_version": 1, "phase": "P003", "gate": "isolated-uninstall", "status": "PASSED",
                          "prefix": "/opt/darling-p003", "prefix_absent": True,
                          "removed_entries": len(reports[0]["entries"]), "manifest_source_commit": commit,
                          "errors": []}, "Removal does not bind the full current installation")
    owners = [load(root / filename) for filename in ("install-owner.json", "install-owner-second.json")]
    for owner in owners:
        require(owner["phase"] == "P003" and owner["prefix"] == "/opt/darling-p003"
                and re.fullmatch(r"[0-9a-f]{64}", owner["nonce"]), "Invalid installation ownership")
    require(owners[0]["nonce"] != owners[1]["nonce"], "Reinstallation reused ownership state")
    campaigns = []
    for when in ("first", "second"):
        report = load(root / ("probes-" + when) / "report.json")
        require(report["source_revision"] == commit and report["prefix"] == "/p003/runtime-" + when
                and report["controlled_home"] == "/p003/runtime-" + when + ".home", "Reused/wrong runtime paths")
        life = report["lifecycle"]
        require(life["server_exited"] is True and life["mount_namespace_released"] is True
                and life["namespace_holders_after"] == [], "Runtime lifecycle not fully stopped")
        campaigns.append({"prefix": report["prefix"], "controlled_home": report["controlled_home"],
                          "nonce": report["nonce"], "lifecycle": life})
    require(campaigns[0]["nonce"] != campaigns[1]["nonce"]
            and campaigns[0]["lifecycle"]["server_before"] != campaigns[1]["lifecycle"]["server_before"],
            "Runtime campaign identity reused")
    return {"installed_entries": len(reports[0]["entries"]),
            "entry_kinds": dict(Counter(row["kind"] for row in reports[0]["entries"])),
            "first_reinstall_inventory_equal": True, "cmake_manifest_bytes_equal": True,
            "cmake_manifest_lines": len(first.splitlines()), "install_logs_equal": True,
            "install_log_lines": len(logs[0].splitlines()), "uninstall": uninstall,
            "owners": owners, "campaigns": campaigns,
            "scope": "State identity/removal only; separate runtime reviewer verifies asserted execution outputs."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--archive-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    archive = load(args.archive_receipt)
    require(archive["implementation"] == args.commit and archive["status"] == "ALL_ORIGINAL_MEMBERS_MATCH",
            "Archive receipt does not identify this candidate")
    hashes = {row["name"]: row["sha256"] for row in archive["members"]}
    root, commit = args.root, args.commit
    summary = load(root / "build-summary.json")
    require(summary["source_commit"] == commit and summary["status"] == "PASS"
            and summary["exit_code"] == 0 and summary["last_stage"] == "complete", "Build did not complete")
    source_lock_bytes = git(commit, "docs/compat/logic-pro/submodules.lock.json")
    require(summary["source_lock_sha256"] == sha(source_lock_bytes), "Source lock identity changed")
    epoch = subprocess.run(["git", "show", "-s", "--format=%ct", commit], cwd=REPO,
                           check=True, stdout=subprocess.PIPE).stdout.decode().strip()
    require(summary["source_date_epoch"] == epoch, "Build source epoch differs")
    lock = load(root / "toolchain.lock.json")
    committed = json.loads(git(commit, "docs/compat/logic-pro/toolchain.lock.json"))
    observation = load(root / "toolchain-host-observation.json")
    require(hashes["toolchain.lock.json"] == FROZEN_LOCK == summary["toolchain_sha256"]
            and observation["lock_sha256"] == FROZEN_LOCK and lock["image_id"] == IMAGE_ID
            and lock["image_archive"]["sha256"] == FROZEN_IMAGE, "Not the verified frozen input")
    require(all(lock[key] == committed[key] for key in ("base_image", "ubuntu_snapshot", "recipe_sha256")),
            "Frozen acquisition inputs changed")
    require(canonical(identity(lock["environment"])) == canonical(identity(committed["environment"]))
            == canonical(identity(observation["environment"])), "Actual host compiler/package identity differs")
    require(observation["status"] == "PASSED" and observation["identity_differences"] == []
            and observation["raw_observation_differences"] == differences(lock["environment"], observation["environment"]),
            "Incorrect host observation difference receipt")
    pinned = json.loads(source_lock_bytes)
    report = {"schema": "darling.p003.wave4.original-build-review.v1", "reviewer": "/root/wave4_build",
              "non_author": True, "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "implementation": commit, "build_id": summary["build_id"],
              "artifact_id": archive["artifact_id"], "artifact_sha256": archive["artifact_sha256"],
              "archive_receipt_sha256": sha(args.archive_receipt.read_bytes()),
              "producer_sha256": sha(git(commit, "ci/logic-pro/build-p003.sh")), "summary": summary,
              "toolchain": {"lock_sha256": FROZEN_LOCK, "image_sha256": FROZEN_IMAGE,
                            "image_id": IMAGE_ID, "package_count": len(lock["environment"]["packages"]),
                            "tool_count": len(lock["environment"]["tools"]),
                            "actual_host_environment_matches_frozen_inputs": True,
                            "raw_observation_differences": observation["raw_observation_differences"]},
              "source": source_checks(root, commit, pinned,
                                      json.loads(git(commit, "tools/compat/logic-pro/classifications.json"))),
              "codegen": codegen_checks(root, commit, lock, hashes),
              "actual_build": build_checks(root, commit),
              "installation_lifecycle": lifecycle_checks(root, commit, pinned),
              "source_built_linker_observation": load(root / "source-built-linker.json"),
              "status": "OWNED_SOURCE_BUILD_LIFECYCLE_CHECKS_PASSED",
              "phase_acceptance": False,
              "limitations": ["One original host only; two-host comparison is separate.",
                              "Compiler environment observed on the real host; large frozen image ZIP not locally replayed.",
                              "Source-built linker binary not retained, so its reported hash cannot be independently rehashed.",
                              "Package nondeterminism and real runtime outputs have separate reviewers."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "build_id": report["build_id"],
                      "source": report["source"], "build": report["actual_build"],
                      "codegen": report["codegen"], "installed_entries": report["installation_lifecycle"]["installed_entries"],
                      "receipt_sha256": sha(args.output.read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
