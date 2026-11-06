#!/usr/bin/env python3
"""Review original paired P003 source/build evidence without accepting other gates."""
import argparse
import copy
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
import stat
import struct
import subprocess
import sys
import zipfile

CANDIDATE = "4622a9396c5c9fbe0014bdf6a2f695dcc491233c"
RUN_ID = 42180484781
ORIGINALS = {
    "a": (13485932962, 87409741, "27b4a147ff1993bc6756172767cb4d60a8d4e437d5f9d85effe039571d5aa038"),
    "b": (13486009301, 87410244, "a7c394d71cc4d83857c0dd2988291c0b9e4bf31cb1555785c2e71dfcd6387759"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalized_environment(environment):
    result = copy.deepcopy(environment)
    banner = result["tools"]["dsymutil"]["version_output"]
    result["tools"]["dsymutil"]["version_output"], count = re.subn(
        r"(?m)^(  Host CPU: )[^\r\n]+$", r"\1<host-cpu>", banner)
    assert count == 1
    return result


def object_observation(data):
    """Read the real object section relocation tables and relative-table names."""
    header = struct.unpack_from("<8I", data)
    assert (header[0], header[1], header[3]) == (0xFEEDFACF, 0x01000007, 1)
    offset, sections, table_names = 32, [], []
    end = offset + header[5]
    assert end <= len(data)
    for _ in range(header[4]):
        command, length = struct.unpack_from("<II", data, offset)
        assert length >= 8 and offset + length <= end
        if command == 0x19:
            count, = struct.unpack_from("<I", data, offset + 64)
            assert length >= 72 + 80 * count
            for n in range(count):
                s = offset + 72 + 80 * n
                name = data[s:s+16].split(b"\0", 1)[0].decode("ascii")
                reloc_offset, count = struct.unpack_from("<II", data, s + 56)
                assert reloc_offset + count * 8 <= len(data)
                relative_subtractors = 0
                for i in range(count):
                    _, bits = struct.unpack_from("<II", data, reloc_offset + i * 8)
                    if bits >> 28 == 5 and ((bits >> 25) & 3) == 2 and not (bits & (1 << 24)):
                        relative_subtractors += 1
                sections.append({"section": name, "relocations": count, "non_pc_relative_32bit_subtractors": relative_subtractors})
        elif command == 2:
            symbols, count, strings, size = struct.unpack_from("<4I", data, offset + 8)
            assert symbols + count * 16 <= len(data) and strings + size <= len(data)
            for i in range(count):
                string_index, = struct.unpack_from("<I", data, symbols + i * 16)
                assert string_index < size
                name = data[strings+string_index:strings+size].split(b"\0", 1)[0].decode("ascii")
                if "reltable." in name:
                    table_names.append(name)
        offset += length
    assert offset == end
    return {"sha256": sha(data), "relative_table_symbols": table_names, "sections": sections,
            "data_32bit_subtractors": sum(x["non_pc_relative_32bit_subtractors"] for x in sections if x["section"] != "__text")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--originals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()

    def git(*command, owner="."):
        return subprocess.check_output(["git", "-C", str(repo / owner), *command])

    blob_cache = {}

    def blob(commit, name, owner="."):
        key = (commit, name, owner)
        if key not in blob_cache:
            blob_cache[key] = git("show", commit + ":" + name, owner=owner)
        return blob_cache[key]

    head = git("rev-parse", "HEAD").decode().strip()
    changes = git("diff", "--name-only", CANDIDATE, head).decode().splitlines()
    assert all(x == "README.md" or x.startswith("docs/compat/logic-pro/evidence/") for x in changes)
    assert not git("diff", "--name-only", CANDIDATE, "--", ".", ":(exclude)README.md", ":(exclude)docs/compat/logic-pro/evidence")
    metadata_bytes = (args.originals / "metadata-final.json").read_bytes()
    metadata = json.loads(metadata_bytes)
    jobs = metadata["jobs"]["jobs"]
    assert len(jobs) == 6 and len({j["id"] for j in jobs}) == 6
    assert all(j["head_sha"] == CANDIDATE and j["run_id"] == RUN_ID and j["status"] == "completed" and j["conclusion"] == "success" for j in jobs)
    artifacts = {x["id"]: x for x in metadata["artifacts"]["artifacts"]}
    lock_bytes = blob(CANDIDATE, "docs/compat/logic-pro/submodules.lock.json")
    source_lock = json.loads(lock_bytes)
    pins = {x["path"]: x for x in source_lock["submodules"]}
    assert len(pins) == len(source_lock["submodules"]) == 160
    # The hosted originals scan all 160 children. Locally bind the 149 direct
    # pins and the six cited owner objects; unrelated child stores are absent.
    direct_pins = 0
    for path, pin in pins.items():
        parent = pin["parent_path"]
        if parent != ".":
            continue
        row = git("ls-tree", CANDIDATE, "--", path).decode().strip()
        assert row.split("\t")[0] == "160000 commit " + pin["commit"], path
        direct_pins += 1
    assert direct_pins == 149
    manifest = json.loads(blob(CANDIDATE, "tools/compat/logic-pro/classifications.json"))
    audited = {x["id"]: x for x in manifest["current_source_reaudit"]["evidence"]}
    cited_owners = sorted({x["repository"] for x in audited.values()} - {"."})
    assert len(cited_owners) == 6
    for owner in cited_owners:
        assert git("rev-parse", pins[owner]["commit"] + "^{tree}", owner=owner).decode().strip() == pins[owner]["tree"]
    frozen = json.loads(blob(CANDIDATE, "docs/compat/logic-pro/toolchain.lock.json"))
    origin = json.loads((repo / "docs/compat/logic-pro/evidence/P003/requalification-20261106/attempt-4622a93/original-retained-origin.json").read_bytes())
    sys.path.insert(0, str(repo / "tools/compat/logic-pro"))
    import compare_p003 as consumer
    imported_hashes = {}
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__file__", None)
        if name and Path(name).resolve().is_relative_to(repo / "tools/compat/logic-pro"):
            path = Path(name).resolve()
            relative = str(path.relative_to(repo))
            assert path.read_bytes() == blob(CANDIDATE, relative)
            imported_hashes[relative] = sha(path.read_bytes())
    build_results = {}
    for label, (artifact_id, expected_size, expected_hash) in ORIGINALS.items():
        archive_path = args.originals / f"build-{label}.zip"
        archive_bytes = archive_path.read_bytes()
        assert len(archive_bytes) == expected_size and sha(archive_bytes) == expected_hash
        remote = artifacts[artifact_id]
        assert remote["size_in_bytes"] == expected_size and remote["digest"] == "sha256:" + expected_hash
        assert remote["workflow_run"]["head_sha"] == CANDIDATE and remote["workflow_run"]["id"] == RUN_ID
        extracted = args.originals / f"build-{label}"
        evidence = {}
        with zipfile.ZipFile(archive_path) as archive:
            assert len(archive.infolist()) == len(set(archive.namelist())) == 459
            assert archive.testzip() is None

            def raw(name):
                data = archive.read(name)
                path = extracted / name
                assert path.is_file() and not path.is_symlink() and path.read_bytes() == data, name
                evidence[name] = {"bytes": len(data), "sha256": sha(data), "zip_mode": oct(archive.getinfo(name).external_attr >> 16)}
                return data

            def read(name):
                return json.loads(raw(name))

            summary = read("build-summary.json")
            assert summary["source_commit"] == CANDIDATE and summary["build_id"] == label
            assert summary["status"] == "PASS" and summary["exit_code"] == 0 and summary["last_stage"] == "complete"
            assert summary["source_lock_sha256"] == sha(lock_bytes)
            assert summary["source_date_epoch"] == git("show", "-s", "--format=%ct", CANDIDATE).decode().strip()
            source = read("source-lock-verification.json")
            assert source["root_commit"] == CANDIDATE and source["result"] == "PASS"
            assert (source["direct_gitlinks"], source["verified_gitlinks"], source["verified_repositories"], source["verified_lfs_payloads"]) == (149, 160, 161, 44)
            assert source["verified_lfs_bytes"] == sum(x["size"] for x in source_lock["lfs_objects"])
            assert all(source[k] == 0 for k in ("conflicted", "dirty_repositories", "mismatched", "uninitialized"))
            observed_pins = {x["path"]: x for x in source["submodules"]}
            expected_pins = {p: {k: v[k] for k in ("path", "commit", "tree", "resolved_url")} for p, v in pins.items()}
            assert len(source["submodules"]) == 160 and observed_pins == expected_pins
            assert json.loads(raw("source-lock-verification.log")) == {k: v for k, v in source.items() if k != "submodules"}
            heads = raw("submodule-heads.txt").decode().splitlines()
            parsed_heads = [re.fullmatch(r" ([0-9a-f]{40}) (\S+) \([^\n]*\)", line) for line in heads]
            assert len(heads) == 160 and all(parsed_heads)
            assert {m.group(2): m.group(1) for m in parsed_heads} == {p: x["commit"] for p, x in pins.items()}
            for when in ("before", "after"):
                name = f"source-status-{when}.txt"
                assert raw(name) == b"" and stat.S_ISREG(archive.getinfo(name).external_attr >> 16)
                assert archive.getinfo(name).external_attr >> 16 == 0o100644

            classification = read("source-classifications.json")
            raw("source-classifications.log")
            assert classification["current_commit"] == CANDIDATE
            assert len(classification["checked"]) == classification["checked_count"] == 63
            citation_hashes = []
            for record in classification["checked"]:
                current = record["current_source"]
                expected = audited[record["id"]]
                owner, path = current["repository"], current["path"]
                assert "corecrypto" not in (owner + "/" + path).lower()
                revision = CANDIDATE if owner == "." else pins[owner]["commit"]
                assert current["repository_commit"] == revision
                assert current["blob_sha1"] == expected["blob_sha1"]
                assert current["gitlink_chain"] == expected["gitlink_chain"]
                for link in current["gitlink_chain"]:
                    assert pins[link["path"]]["commit"] == link["commit"]
                data = blob(revision, path, owner)
                git_hash = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
                assert git_hash == current["blob_sha1"]
                excerpt = b"".join(data.splitlines(keepends=True)[current["line_start"]-1:current["line_end"]])
                assert sha(excerpt) == current["excerpt_sha256"] == expected["excerpt_sha256"]
                assert current["original_assertions_preserved"] is True
                assert current["assertions_verified"] == len(expected["contains"])
                assert all(value.encode() in excerpt for value in expected["contains"])
                citation_hashes.append({"id": record["id"], "repository": owner, "path": path, "blob_sha1": git_hash, "excerpt_sha256": sha(excerpt)})
            classification_validation = consumer.validate_source_classifications(extracted, CANDIDATE)

            toolchain = read("toolchain.lock.json")
            observation = read("toolchain-host-observation.json")
            assert sha(raw("toolchain.lock.json")) == summary["toolchain_sha256"] == origin["original_files_sha256"]["toolchain.lock.json"]
            assert observation["status"] == "PASSED" and observation["identity_differences"] == []
            assert observation["lock_sha256"] == summary["toolchain_sha256"]
            assert normalized_environment(frozen["environment"]) == normalized_environment(toolchain["environment"]) == normalized_environment(observation["environment"])
            assert toolchain["recipe_sha256"] == sha(blob(CANDIDATE, "ci/logic-pro/Dockerfile.p003"))
            assert toolchain["base_image"] == frozen["base_image"] and toolchain["ubuntu_snapshot"] == frozen["ubuntu_snapshot"]
            assert toolchain["image_id"] == origin["restored_image_id"]
            assert toolchain["image_archive"]["sha256"] == origin["original_files_sha256"]["toolchain-image.tar.gz"]
            assert raw("toolchain-verification.log") == b"P003 toolchain verify: PASS\n"

            proof = read("unwind-codegen/report.json")
            raw("unwind-codegen.log")
            assert proof["status"] == "PASS" and proof["errors"] == []
            assert proof["compiler"]["sha256"] == toolchain["environment"]["tools"]["clang"]["sha256"]
            assert proof["helper_sha256"] == sha(blob(CANDIDATE, "cmake/darling_unwind_configuration.cmake"))
            assert proof["source_inputs"] == consumer.UNWIND_SOURCE_HASHES
            for name, expected_hash in proof["evidence"].items():
                assert sha(raw("unwind-codegen/" + name)) == expected_hash
            assert raw("unwind-codegen/compiler-version.stdout.log").decode() == proof["compiler"]["version"]
            objects = {}
            for name, target in (("control", "control_static"), ("repaired", "unwind_static")):
                objects[name] = object_observation(raw(f"unwind-codegen/macho/build/CMakeFiles/{target}.dir/register_names.cpp.o"))
                assert objects[name]["sha256"] == proof["macho"][name]["sha256"]
                assert objects[name]["relative_table_symbols"] == proof["macho"][name]["relative_table_symbols"]
            assert objects["control"]["data_32bit_subtractors"] == 35 and objects["control"]["relative_table_symbols"]
            assert objects["repaired"]["data_32bit_subtractors"] == 0 and not objects["repaired"]["relative_table_symbols"]
            register_names = dict(enumerate("rax rdx rcx rbx rsi rdi rbp rsp r8 r9 r10 r11 r12 r13 r14 r15".split()))
            register_names.update({-2: "rsp", -1: "rip", **{17+i: f"xmm{i}" for i in range(16)}})
            inputs = list(range(-8, 41)) + [-(2**31), 2**31-1]
            expected_behavior = "".join(f"{n} {register_names.get(n, 'unknown register')}\n" for n in inputs).encode()
            assert raw("unwind-codegen/control-behavior.stdout.log") == raw("unwind-codegen/repaired-behavior.stdout.log") == expected_behavior
            proof_validation = consumer.validate_unwind_codegen(extracted, toolchain, summary["toolchain_sha256"])

            commands = read("compile_commands.json")
            assert len(commands) == 15399
            objc = [x for x in commands if "/src/external/objc4/runtime/" in x["file"]]
            assert len(objc) == 48
            for command in objc:
                flags = shlex.split(command["command"])
                assert "-DNDEBUG" in flags and not any(x.startswith(("-DOBJC_IS_DEBUG_BUILD", "-DDEBUG")) for x in flags)
            affected = [x for x in commands if "-fno-jump-tables" in x["command"]]
            assert len(affected) == 4 and all("unwind_static.dir/" in x["command"] and x["file"].endswith(".cpp") for x in affected)
            cache = raw("CMakeCache.txt").decode()
            for entry in ("CMAKE_BUILD_TYPE:STRING=Release", "COMPONENTS:STRING=cli,gui", "TARGET_x86_64:BOOL=ON", "TARGET_i386:BOOL=OFF", "DARLING_NO_CCACHE:BOOL=ON", "DARLING_P003_PROBES:BOOL=ON", "CMAKE_INSTALL_PREFIX:PATH=/opt/darling-p003"):
                assert entry in cache.splitlines()
            configure = raw("configure.log").decode()
            assert "-- The CXX compiler identification is Clang 14.0.0" in configure and "-- Build files have been written to: /p003/build" in configure
            build = raw("build.log").decode()
            steps = re.findall(r"^\[(\d+)/(\d+)\]", build, re.M)
            assert steps == [(str(i), "16594") for i in range(1, 16595)]
            assert not re.search(r"^FAILED:|^ninja: build stopped", build, re.M)
            assert raw("cmake-install-manifest-first.txt") == raw("cmake-install-manifest-second.txt")
            for when in ("first", "second"):
                log = raw(f"install-{when}.log").decode()
                assert "-- Installing: /opt/darling-p003/libexec/darling/usr/libexec/p003/p003_gui" in log
            linker = read("source-built-linker.json")
            assert len(linker) == 1 and linker[0]["version_exit_code"] == 0
            build_results[label] = {
                "artifact_id": artifact_id, "archive_bytes": expected_size, "archive_sha256": expected_hash, "CRC_checked_members": 459,
                "summary": summary, "source_verification": {k: v for k, v in source.items() if k != "submodules"},
                "all_160_pin_tree_rows_and_raw_heads_match_accepted_lock": True,
                "local_superproject_direct_gitlinks_checked": direct_pins,
                "local_cited_owner_commit_trees_checked": cited_owners,
                "current_citation_blobs_and_excerpts": citation_hashes,
                "classification_validator": classification_validation,
                "toolchain_environment_matches_committed_lock_and_frozen_input": True,
                "raw_toolchain_observation_differences": observation["raw_observation_differences"],
                "compiler_sha256": proof["compiler"]["sha256"], "codegen_bound_files": len(proof["evidence"]),
                "codegen_objects": objects, "register_behavior_inputs_independently_checked": len(inputs), "codegen_validator": proof_validation,
                "compile_commands": len(commands), "objc_runtime_commands_with_NDEBUG_and_no_override": len(objc),
                "private_static_unwind_CXX_commands": [x["file"] for x in affected], "completed_ninja_commands": len(steps),
                "source_built_linker_observation": linker,
                "original_members_read_and_extracted_copy_verified": evidence,
            }
    a, b = build_results["a"], build_results["b"]
    for key in ("source_commit", "toolchain_sha256", "source_lock_sha256", "configuration", "installation_prefix", "source_date_epoch"):
        assert a["summary"][key] == b["summary"][key]
    assert a["current_citation_blobs_and_excerpts"] == b["current_citation_blobs_and_excerpts"]
    assert a["codegen_objects"] == b["codegen_objects"]
    result = {
        "schema": "darling.p003.wave5-current-source-review.v1", "reviewer": "/root/wave5_source",
        "reviewed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": CANDIDATE, "source_tree": git("rev-parse", CANDIDATE + "^{tree}").decode().strip(),
        "run_id": RUN_ID, "documentation_boundary_commit": head,
        "original_final_metadata": {"bytes": len(metadata_bytes), "sha256": sha(metadata_bytes), "six_exact_source_jobs_succeeded": True},
        "production_validator_file_hashes": imported_hashes,
        "builds": build_results, "paired_source_toolchain_and_configuration_identity": True,
        "source_scope_verdict": "APPROVED", "phase_acceptance": False,
        "limitations": ["The complete retained image ZIP was not locally rehashed; actual hosted restoration and both original frozen-environment observations are bound instead.", "The 293755-file physical checkout scan is the original hosted observation. Locally the reviewer checks 149 direct Git objects, six cited owner commit trees and all 63 current cited blobs/excerpts; all 160 original pin/tree rows and raw heads match the accepted lock. No new full physical checkout scan is claimed.", "Unwind source-input hashes match the exact reviewed pinned-source constants and original hosted scan; the two source headers are not separately reread locally. All 61 codegen files, actual Mach-O objects and all 51 behavioral inputs are independently checked.", "Source-built linker bytes were not archived; the two original digest/version observations are retained, and package nondeterminism belongs to the separate package review.", "Whole-phase acceptance still requires the independent package, runtime/lifecycle and final adjudication verdicts."]
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"source_scope_verdict": result["source_scope_verdict"], "source_commit": CANDIDATE, "builds": {k: {"CRC_members": v["CRC_checked_members"], "current_citations": len(v["current_citation_blobs_and_excerpts"]), "bound_original_members": len(v["original_members_read_and_extracted_copy_verified"]), "compile_commands": v["compile_commands"], "ninja_commands": v["completed_ninja_commands"]} for k, v in build_results.items()}, "output_sha256": sha(args.output.read_bytes())}, sort_keys=True))


if __name__ == "__main__":
    main()
