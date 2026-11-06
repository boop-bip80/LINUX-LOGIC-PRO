#!/usr/bin/env python3
"""Independent stdlib audit of original hosted clone artifacts and physical LFS bytes.

Inputs are read only. Supply the original ZIPs and their extracted sibling folders.
The Swift-only checkout is supplemental and never substitutes for a hosted clone.
"""
import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path

SHA = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"
RUN = 42155822754
LOCK = "docs/compat/logic-pro/submodules.lock.json"
METHOD = "physical_committed_bytes_modes_symlinks_and_lfs_sha256_without_filters"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def git(repo, *args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(repo), *args])


def audit(repo, raw, physical):
    official = json.loads((Path(__file__).parent / "official-identities.json").read_text())
    run = official["run"]["response"]
    jobs = official["jobs"]["response"]["jobs"]
    artifacts = official["artifacts"]["response"]["artifacts"]
    require(run["id"] == RUN and run["head_sha"] == SHA and run["conclusion"] == "success", "official run")
    require(len(jobs) == 2 and len({j["runner_id"] for j in jobs}) == 2, "separate official runners")
    require(all(j["run_id"] == RUN and j["head_sha"] == SHA and j["conclusion"] == "success" for j in jobs), "official jobs")
    lock_bytes = (repo / LOCK).read_bytes()
    require(lock_bytes == git(repo, "show", SHA + ":" + LOCK), "current lock differs from tested source")
    lock = json.loads(lock_bytes)
    expected_graph = [{k: r[k] for k in ("commit", "path", "resolved_url", "tree")} for r in lock["submodules"]]
    expected_payloads = [{k: r[k] for k in ("path", "oid_sha256", "size", "mode")} | {"status": "PASS"} for r in lock["lfs_objects"]]
    reports = {}
    for host in ("a", "b"):
        folder = raw / ("p002-clone-" + host)
        zip_path = folder.with_suffix(".zip")
        metadata = json.loads(folder.with_name(folder.name + "-artifact.json").read_text())
        artifact = next(x for x in artifacts if x["name"] == "p002-clone-" + host + "-" + SHA)
        archive_bytes = zip_path.read_bytes()
        require(len(archive_bytes) == artifact["size_in_bytes"], "official ZIP size")
        require("sha256:" + digest(archive_bytes) == artifact["digest"], "official ZIP digest")
        require(all(artifact[k] == v for k, v in metadata["metadata"].items()), "original metadata differs from independent API response")
        members = {}
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            require(len(names) == len(set(names)) == 18, "18 unique original members")
            require(archive.testzip() is None, "ZIP CRC failure")
            for name in names:
                data = archive.read(name)
                require(data == (folder / name).read_bytes(), "extraction differs: " + name)
                members[name] = {"bytes": len(data), "sha256": digest(data)}
                require(members[name] == metadata["members"][name], "original member digest: " + name)
        checksums = (folder / "checksums.sha256").read_text().splitlines()
        require(len(checksums) == 17, "17 internal checksums")
        listed = set()
        for line in checksums:
            expected, name = line.split("  ", 1)
            require(members[name]["sha256"] == expected and name not in listed, "internal checksum " + name)
            listed.add(name)
        require(listed == set(members) - {"checksums.sha256"}, "complete checksum coverage")
        commands = json.loads((folder / "commands.json").read_text())
        require(len(commands) == 13 and all(x["exit_code"] == 0 for x in commands), "13 successful commands")
        command_results = []
        ranges = {}
        for command in commands:
            data = (folder / command["log"]).read_bytes()
            start, size = command["log_offset"], command["log_bytes"]
            segment = data[start:start + size]
            require(len(segment) == size and digest(segment) == command["output_sha256"], "command segment " + command["label"])
            ranges.setdefault(command["log"], []).append((start, size))
            command_results.append({k: command[k] for k in ("label", "exit_code", "log", "log_offset", "log_bytes", "output_sha256")})
        for name, intervals in ranges.items():
            end = 0
            for start, size in intervals:
                require(start == end, "command log gap/overlap " + name)
                end = start + size
            require(end == members[name]["bytes"], "unaccounted command log bytes")
        labels = {c["label"]: c for c in commands}
        clone = labels["clone-root"]["command"]
        require(clone[-9:-1] == ["clone", "--no-local", "--no-hardlinks", "--no-checkout", "--no-recurse-submodules", "--origin", "origin", lock["root_origin"]], "ordinary clone flags and URL")
        destination = clone[-1]
        require(destination.endswith("p002-independent-clone-" + host), "separate fresh destination")
        require(not any(x.startswith(("--reference", "--shared")) for x in clone), "shared store flags")
        require(labels["ordinary-recursive-submodules"]["command"][-6:] == ["submodule", "update", "--init", "--recursive", "--jobs", "12"], "ordinary recursion")
        for name in ("source-head.sha", "head.sha"):
            require((folder / name).read_text().strip() == SHA, "exact runner and clone source")
        transcript = (folder / "fixture-tests.log").read_text()
        starts = re.findall(r"^test_[^\n]+", transcript, re.M)
        successes = len(re.findall(r"\.\.\. ok$|^ok$", transcript, re.M))
        require(len(starts) == successes == 115 and len(set(x.split(" ...", 1)[0] for x in starts)) == 115, "115 distinct actual successful cases")
        require(re.search(r"Ran 115 tests in [0-9.]+s\n\nOK\s*\Z", transcript), "unqualified fixture result")
        require(not re.search(r"\.\.\. (?:skipped|expected failure|unexpected success|FAIL|ERROR)", transcript), "qualified fixture result")
        verification = json.loads((folder / ("verification-" + host + ".json")).read_text())
        require(len(verification["submodules"]) == 160 and sorted(verification["submodules"], key=lambda r: r["path"]) == sorted(expected_graph, key=lambda r: r["path"]), "complete exact source graph")
        expected_counts = {"direct_gitlinks": 149, "verified_gitlinks": 160, "verified_repositories": 161, "verified_physical_blobs": 293500, "verified_lfs_payloads": 44, "verified_lfs_bytes": 16128448}
        require(all(verification[k] == v for k, v in expected_counts.items()), "physical counts")
        require(verification["root_commit"] == SHA and verification["result"] == "PASS" and verification["verification_method"] == METHOD, "physical verdict")
        require(all(verification[k] == 0 for k in ("conflicted", "dirty_repositories", "mismatched", "uninitialized")), "physical failures")
        native = (folder / "native-git-status.txt").read_text().splitlines()
        require(len(native) == 160 and all(line.startswith(" ") for line in native), "160 native clean gitlinks")
        observed_pins = {line[1:].split(" ", 2)[1]: line[1:].split(" ", 2)[0] for line in native}
        require(observed_pins == {r["path"]: r["commit"] for r in lock["submodules"]}, "native pins match lock")
        hydration = json.loads((folder / "lfs-hydration.json").read_text())
        require(hydration["objects"] == expected_payloads, "every LFS OID/size/mode")
        require(hydration["repositories"] == [r | {"status": "PASS"} for r in lock["lfs_repositories"]], "LFS endpoint provenance")
        require(hydration["result"] == "PASS" and not hydration["errors"] and hydration["verified_payload_bytes"] == 16128448 and hydration["verified_lfs_objects"] == 44, "LFS totals")
        require(hydration["implementation_sha256"] == digest((repo / "tools/compat/logic-pro/lfs_manifest.py").read_bytes()), "exact LFS implementation hash")
        require(len(hydration["commands"]) == 3 and all(c["exit_code"] == 0 for c in hydration["commands"]), "three successful LFS commands")
        hydration_log = (folder / "lfs-hydration.log").read_text()
        for i, c in enumerate(hydration["commands"]):
            marker = "+ " + " ".join(c["argv"]) + "\n"
            output = hydration_log.split(marker, 1)[1].split("\n+ ", 1)[0]
            if i == 2:
                output = output.split("LFS hydration PASS:", 1)[0]
            elif not output.endswith("\n"):
                output += "\n"
            require(digest(output.encode()) == c["output_sha256"], "LFS command output digest")
        require((folder / "regenerated-lock.json").read_bytes() == lock_bytes, "byte-identical regenerated current lock")
        regeneration = json.loads((folder / "lock-regeneration.json").read_text())
        require(regeneration["result"] == "PASS" and regeneration["byte_identical"] and regeneration["committed_sha256"] == regeneration["regenerated_sha256"] == digest(lock_bytes), "lock regeneration receipt")
        summary = json.loads((folder / "summary.json").read_text())
        require(summary["result"] == "PASS" and not summary["failures"] and summary["ordinary_git_acquisition"] and not summary["credential_or_reference_cache_used"], "campaign result")
        job = next(j for j in jobs if j["name"].startswith("Independent clone " + host + " "))
        reports[host] = {"artifact_id": artifact["id"], "job_id": job["id"], "runner_id": job["runner_id"], "zip_sha256": digest(archive_bytes), "zip_bytes": len(archive_bytes), "crc": "PASS", "internal_hashes": len(checksums), "members": members, "command_segments": command_results, "successful_tests": successes, "destination": destination, "environment": json.loads((folder / "environment.txt").read_text()), "counts": expected_counts}
    require(reports["a"]["environment"]["image_os"] != reports["b"]["environment"]["image_os"], "separate hosted images")
    require(reports["a"]["destination"] != reports["b"]["destination"], "separate clone paths")
    payloads = []
    swift = physical / "src/external/swift"
    provenance = lock["lfs_repositories"][0]
    require(git(swift, "rev-parse", "HEAD").decode().strip() == provenance["repository_commit"], "supplementary Swift commit")
    require(git(swift, "remote", "get-url", "origin").decode().strip() == provenance["origin"], "supplementary origin")
    config = git(swift, "show", "HEAD:.lfsconfig")
    require(digest(config) == provenance["lfsconfig_sha256"] and hashlib.sha1(b"blob " + str(len(config)).encode() + b"\0" + config).hexdigest() == provenance["lfsconfig_blob_sha1"], "committed LFS URL provenance bytes")
    for record in lock["lfs_objects"]:
        file = physical / record["path"]
        info = file.lstat()
        require(stat.S_ISREG(info.st_mode), "physical regular LFS file")
        mode = "100755" if info.st_mode & stat.S_IXUSR else "100644"
        data = file.read_bytes()
        require(len(data) == record["size"] and digest(data) == record["oid_sha256"] and mode == record["mode"], "independent physical LFS bytes: " + record["path"])
        pointer = git(swift, "cat-file", "blob", record["pointer_blob_sha1"])
        expected = ("version https://git-lfs.github.com/spec/v1\noid sha256:" + record["oid_sha256"] + "\nsize " + str(record["size"]) + "\n").encode()
        require(pointer == expected, "canonical committed pointer")
        entry = git(swift, "ls-tree", "HEAD", "--", record["repository_path"]).decode().strip()
        require(entry == record["mode"] + " blob " + record["pointer_blob_sha1"] + "\t" + record["repository_path"], "pointer tree identity and mode")
        payloads.append({k: record[k] for k in ("path", "mode", "oid_sha256", "size", "pointer_blob_sha1")} | {"status": "PASS"})
    return {"result": "PASS", "reviewer": "wave4_clone_b_lfs", "tested_source": SHA, "run_id": RUN, "lock_sha256": digest(lock_bytes), "hosts": reports, "source_graph_match": True, "separate_official_runner_ids": True, "supplementary_physical_checkout": str(physical), "supplementary_lfs_payloads": payloads, "supplementary_verified_bytes": sum(x["size"] for x in payloads), "limit": "Supplementary Swift-only bytes are not a third full hosted clone; whole-phase acceptance requires the other reviews and Wave 5."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--physical-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.repo, args.raw, args.physical_root)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: two original ZIPs; 36 members; 34 internal hashes; 26 command segments; 230 successful hosted cases; exact source graph; 44 physical LFS payloads / 16128448 bytes")
