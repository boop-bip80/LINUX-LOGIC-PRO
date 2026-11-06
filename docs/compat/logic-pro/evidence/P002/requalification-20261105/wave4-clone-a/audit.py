#!/usr/bin/env python3
"""Independent, offline audit of the original P002 clone A artifact.

This script does not import the campaign's own evidence validators. It audits
original bytes, exact commands, and cross-record identities; it cannot recreate
the hosted checkout from the small evidence ZIP.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile


TESTED = "d58cca513559cfef0ff9af59aa5dc3b6341bdf77"
ZIP_SHA = "cca5a057713e7b5688cb1c2f03a7adfd12606b21a70b5bdac8c7def36171296d"
LOCK_SHA = "2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f"
ROOT_URL = "https://github.com/boop-bip80/MAC-OS-EMULATION.git"
METHOD = "physical_committed_bytes_modes_symlinks_and_lfs_sha256_without_filters"
MEMBERS = {
    "checksums.sha256", "clone-a.log", "commands.json", "environment.txt",
    "fixture-tests.log", "git-lfs-version.txt", "git-version.txt", "head.sha",
    "lfs-hydration.json", "lfs-hydration.log", "lock-regeneration.json",
    "lock-regeneration.log", "native-git-status.txt", "regenerated-lock.json",
    "source-head.sha", "summary.json", "verification-a.json", "verifier-a.log",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--extracted", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="")

    def git(*argv):
        return subprocess.check_output(["git", "-C", str(args.repo), *argv], env=env)

    archive = args.zip.read_bytes()
    require(len(archive) == 53657 and sha(archive) == ZIP_SHA, "original ZIP identity")
    with zipfile.ZipFile(args.zip) as zipped:
        names = zipped.namelist()
        require(len(names) == 18 and set(names) == MEMBERS, "18 exact unique ZIP members")
        require(all(PurePosixPath(name).name == name for name in names), "flat safe member paths")
        require(zipped.testzip() is None, "ZIP CRC verification")
        files = {name: zipped.read(name) for name in names}
    require(set(path.name for path in args.extracted.iterdir()) == MEMBERS, "exact extraction membership")
    require(all((args.extracted / name).read_bytes() == data for name, data in files.items()),
            "extracted bytes equal original ZIP members")
    manifest = {}
    for line in files["checksums.sha256"].decode().splitlines():
        digest, name = line.split("  ", 1)
        require(name not in manifest and re.fullmatch(r"[0-9a-f]{64}", digest), "checksum syntax/uniqueness")
        manifest[name] = digest
    require(set(manifest) == MEMBERS - {"checksums.sha256"}, "17 internal checksum coverage")
    require(all(sha(files[name]) == digest for name, digest in manifest.items()), "all internal digests")
    metadata = json.loads(args.metadata.read_text())
    official = metadata["metadata"]
    require(official["id"] == 13475330560 and official["size_in_bytes"] == len(archive), "artifact ID/size")
    require(official["digest"] == "sha256:" + ZIP_SHA and not official["expired"], "official digest/expiry")
    require(official["workflow_run"]["id"] == 42155822754, "official run identity")
    require(official["workflow_run"]["head_sha"] == TESTED, "official tested revision")
    require(official["name"] == "p002-clone-a-" + TESTED, "official host artifact name")
    member_inventory = {name: {"bytes": len(data), "sha256": sha(data)} for name, data in sorted(files.items())}
    require(metadata["members"] == member_inventory, "acquisition inventory agrees with original ZIP")

    records = {name: json.loads(files[name]) for name in (
        "summary.json", "verification-a.json", "regenerated-lock.json", "lfs-hydration.json",
        "environment.txt", "lock-regeneration.json")}
    summary, verification = records["summary.json"], records["verification-a.json"]
    lock, lfs = records["regenerated-lock.json"], records["lfs-hydration.json"]
    runner = records["environment.txt"]
    require(files["head.sha"] == files["source-head.sha"] == (TESTED + "\n").encode(), "source and clone HEAD")
    require(summary["implementation_commit"] == verification["root_commit"] == TESTED, "report revisions")
    require(summary["host_id"] == "a" and summary["failures"] == [] and summary["result"] == "PASS", "host A summary")
    require(summary["ordinary_git_acquisition"] is True and summary["credential_or_reference_cache_used"] is False,
            "summary acquisition assertions")
    require(runner["image_os"] == "ubuntu22" and runner["runner_os"] == "Linux" and
            runner["runner_arch"] == "X64" and runner["python"] == "3.10.12", "runner OS/runtime")
    require(files["git-version.txt"].decode().strip() == runner["git"] == "git version 2.56.0", "Git version")
    require(files["git-lfs-version.txt"].decode().strip() == runner["git_lfs"] == lfs["git_lfs_version"], "LFS version")

    source = "/home/runner/work/MAC-OS-EMULATION/MAC-OS-EMULATION"
    clone = "/home/runner/work/_temp/p002-independent-clone-a"
    evidence = "/home/runner/work/_temp/p002-evidence"
    prefix = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
              "-c", "credential.helper=", "-c", "http.extraHeader=", "-c", "core.attributesFile=/dev/null",
              "-c", "core.autocrlf=false", "-c", "core.symlinks=true", "-c", "core.filemode=true"]
    py = ["/usr/bin/python3", "-B"]
    expected = [
        ("git-version", prefix + ["--version"]),
        ("source-head", prefix + ["-C", source, "rev-parse", "HEAD"]),
        ("clone-root", prefix + ["clone", "--no-local", "--no-hardlinks", "--no-checkout",
                                "--no-recurse-submodules", "--origin", "origin", ROOT_URL, clone]),
        ("locate-exact-commit", prefix + ["-C", clone, "cat-file", "-e", TESTED + "^{commit}"]),
        ("checkout-exact-commit", prefix + ["-C", clone, "checkout", "--detach", TESTED]),
        ("verify-exact-head", prefix + ["-C", clone, "rev-parse", "HEAD"]),
        ("ordinary-recursive-submodules", prefix + ["-C", clone, "submodule", "update", "--init", "--recursive", "--jobs", "12"]),
        ("fixture-tests", py + ["-m", "unittest", "discover", "-s", clone + "/tests/compat/logic-pro/submodules", "-v"]),
        ("git-lfs-version", prefix + ["lfs", "version"]),
        ("hydrate-locked-lfs", py + [clone + "/tools/compat/logic-pro/lfs_manifest.py", "hydrate", "--repo", clone,
                                    "--lock", clone + "/docs/compat/logic-pro/submodules.lock.json",
                                    "--output", evidence + "/lfs-hydration.json"]),
        ("native-recursive-status", prefix + ["-C", clone, "submodule", "status", "--recursive"]),
        ("strict-lock-verifier", py + [clone + "/tools/compat/logic-pro/check_submodules.py", "--repo", clone,
                                      "--lock", clone + "/docs/compat/logic-pro/submodules.lock.json",
                                      "--output", evidence + "/verification-a.json"]),
        ("regenerate-lock", py + [clone + "/tools/compat/logic-pro/make_submodule_lock.py", "--repo", clone,
                                 "--evidence-mode", "reviewed-current", "--output", evidence + "/regenerated-lock.json"]),
    ]
    commands = json.loads(files["commands.json"])
    require(len(commands) == len(expected) == 13, "13 command records")
    covered, segments = {}, []
    for item, (label, command) in zip(commands, expected):
        require(item["label"] == label and item["command"] == command, "exact command " + label)
        require(item["exit_code"] == 0, "successful command " + label)
        require(item["cwd"] == (clone if command[0] == "/usr/bin/python3" else None), "command cwd " + label)
        name, offset, size = item["log"], item["log_offset"], item["log_bytes"]
        require(offset == covered.get(name, 0) and size >= 0, "gap-free log segments " + label)
        data = files[name][offset:offset + size]
        require(len(data) == size and sha(data) == item["output_sha256"], "segment digest " + label)
        covered[name] = offset + size
        segments.append({key: item[key] for key in ("label", "log", "log_offset", "log_bytes", "output_sha256", "exit_code")})
    require(all(end == len(files[name]) for name, end in covered.items()), "complete command log coverage")

    committed_lock = git("show", TESTED + ":docs/compat/logic-pro/submodules.lock.json")
    require(committed_lock == files["regenerated-lock.json"] and sha(committed_lock) == LOCK_SHA,
            "regenerated lock equals exact tested committed bytes")
    regeneration = records["lock-regeneration.json"]
    require(regeneration == {"byte_identical": True, "committed_sha256": LOCK_SHA,
                             "regenerated_sha256": LOCK_SHA, "result": "PASS"}, "regeneration result")
    require(lock["expected_direct_gitlinks"] == 149 and lock["expected_recursive_gitlinks"] == 160, "lock counts")
    locked = {item["path"]: item for item in lock["submodules"]}
    require(len(locked) == len(lock["submodules"]) == 160, "unique locked paths")
    native = {}
    for line in files["native-git-status.txt"].decode().splitlines():
        match = re.fullmatch(r" ([0-9a-f]{40}) ([^ ]+)(?: \(.*\))?", line)
        require(match is not None, "native initialized, matching, unconflicted line")
        oid, path = match.groups()
        require(path not in native, "native unique path")
        native[path] = oid
    require(native == {path: item["commit"] for path, item in locked.items()}, "all 160 native pins")
    checkouts = re.findall(r"^Submodule path '([^']+)': checked out '([0-9a-f]{40})'$",
                           files["clone-a.log"].decode(), re.M)
    require(len(checkouts) == 160 and dict(checkouts) == native, "160 actual recursive checkout log records")
    projection = lambda items: sorted(({key: item[key] for key in ("path", "commit", "tree", "resolved_url")}
                                      for item in items), key=lambda item: item["path"])
    require(projection(verification["submodules"]) == projection(lock["submodules"]), "all pins, trees, URLs")
    root_links = {}
    for entry in git("ls-tree", "-rz", TESTED).split(b"\0"):
        if not entry:
            continue
        header, path = entry.split(b"\t")
        mode, kind, oid = header.decode().split()
        if mode == "160000":
            root_links[path.decode()] = oid
    require(root_links == {path: item["commit"] for path, item in locked.items() if item["parent_path"] == "."},
            "149 direct pins equal exact implementation tree")
    require(git("rev-parse", TESTED + ":.gitmodules").decode().strip() == lock["root_gitmodules_blob_sha1"],
            "complete root .gitmodules identity")

    transcript = files["fixture-tests.log"].decode()
    starts = list(re.finditer(r"^(test_\S+ \([^\n]+\)) \.\.\. ", transcript, re.M))
    completed = []
    for number, start in enumerate(starts):
        end = starts[number + 1].start() if number + 1 < len(starts) else transcript.index("\n----------------------------------------------------------------------", start.end())
        body = transcript[start.end():end].strip()
        require(body == "ok" or body.endswith("\nok"), "actual terminal success for " + start.group(1))
        completed.append(start.group(1))
    require(len(completed) == len(set(completed)) == 115, "115 unique actual successful fixture lines")
    require(re.search(r"\nRan 115 tests in [0-9.]+s\n\nOK\s*\Z", transcript) is not None, "fixture terminal success")
    require(not re.search(r"\.\.\. (?:skipped|FAIL|ERROR|expected failure|unexpected success)|^FAILED", transcript, re.M),
            "no skipped, failed, or expected-failure tests")
    require(summary["fixture_tests_executed"] == 115, "summary fixture count")
    counts = {"verified_gitlinks": 160, "verified_repositories": 161, "verified_physical_blobs": 293500}
    require(all(summary[key] == verification[key] == value for key, value in counts.items()), "physical report counts")
    require(summary["native_gitlinks_verified"] == 160 and verification["direct_gitlinks"] == 149, "native/direct counts")
    require(all(verification[key] == 0 for key in ("conflicted", "mismatched", "uninitialized", "dirty_repositories")), "zero checkout defects")
    require(summary["verification_method"] == verification["verification_method"] == METHOD and
            verification["schema_version"] == 2 and verification["result"] == "PASS", "physical verifier method")
    verifier_stdout = json.loads(files["verifier-a.log"])
    require(verifier_stdout == {key: value for key, value in verification.items() if key != "submodules"}, "verifier stdout matches report")
    crlf_paths = ["src/external/libffi/msvc_build/aarch64/Ffi_staticLib." + suffix
                  for suffix in ("sln", "vcxproj", "vcxproj.filters", "vcxproj.user")]
    require(verification["standard_crlf_paths"] == crlf_paths, "four explicit standard CRLF paths")
    expected_lfs = [{key: item[key] for key in ("path", "mode", "oid_sha256", "size")} for item in lock["lfs_objects"]]
    require(lfs["objects"] == [dict(item, status="PASS") for item in expected_lfs], "44 LFS identities/modes/sizes")
    require(lfs["repositories"] == [dict(item, status="PASS") for item in lock["lfs_repositories"]], "LFS endpoint provenance")
    require(len(expected_lfs) == len({item["path"] for item in expected_lfs}) == 44 and
            sum(item["size"] for item in expected_lfs) == 16128448, "LFS inventory total")
    require(lfs["result"] == "PASS" and lfs["errors"] == [] and lfs["expected_lfs_objects"] == 44 and
            lfs["verified_lfs_objects"] == verification["verified_lfs_payloads"] == summary["verified_lfs_objects"] == 44,
            "LFS count agreement")
    require(lfs["verified_payload_bytes"] == verification["verified_lfs_bytes"] == summary["verified_lfs_payload_bytes"] == 16128448,
            "LFS byte agreement")
    require(len(lfs["commands"]) == 3 and all(item["exit_code"] == 0 for item in lfs["commands"]), "LFS command successes")

    reviewed = [".github/workflows/phase2-submodules.yml"] + ["tools/compat/logic-pro/" + name for name in (
        "inventory.py", "check_submodules.py", "run_submodule_campaign.py", "make_submodule_lock.py",
        "lfs_manifest.py", "source_provenance.py", "run_baseline.py")]
    source_hashes = {}
    for path in reviewed:
        data = git("show", TESTED + ":" + path)
        require(data == (args.repo / path).read_bytes(), "reviewed source equals tested source: " + path)
        source_hashes[path] = sha(data)
    require(lfs["implementation_sha256"] == source_hashes["tools/compat/logic-pro/lfs_manifest.py"], "executed LFS implementation hash")
    result = {
        "result": "PASS", "scope": "clone A original evidence audit; not whole P002 acceptance",
        "tested_commit": TESTED, "run_id": 42155822754, "job_id": 127689585878,
        "artifact_id": official["id"], "zip_bytes": len(archive), "zip_sha256": ZIP_SHA,
        "members": member_inventory, "internal_checksums_verified": len(manifest),
        "command_segments": segments, "runner": runner,
        "native_gitlinks_verified": len(native), "actual_checkout_log_records": len(checkouts),
        "direct_pins_matched_to_source_tree": len(root_links), "fixture_tests_successful": len(completed),
        "lock_sha256": LOCK_SHA, "lock_byte_identical": True, "hosted_physical_counts": counts,
        "lfs_objects": 44, "lfs_payload_bytes": 16128448, "standard_crlf_paths": crlf_paths,
        "reviewed_source_sha256": source_hashes,
        "limits": ["The artifact contains reports and logs, not all 293500 source blobs or LFS payload bytes.",
                   "Physical checkout totals are corroborated hosted measurements, not a new full local acquisition.",
                   "P001 predecessor acceptance and independent clone B scope are outside this audit."],
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("result", "tested_commit", "internal_checksums_verified",
        "native_gitlinks_verified", "actual_checkout_log_records", "fixture_tests_successful", "lock_byte_identical")}, sort_keys=True))


if __name__ == "__main__":
    main()
