#!/usr/bin/env python3
"""Losslessly preserve and restore the two original P001 requalification artifacts.

Only exact original member bytes are stored. The ZIP container is not reproduced.
Build emits the deterministic mapping to stdout; verify and restore are offline.
"""

import argparse
from contextlib import contextmanager
import hashlib
import json
import lzma
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
import zipfile
import zlib


DIRECTORY = Path(__file__).resolve().parent
ARCHIVE = "raw-reports.tar.xz"
MANIFEST = "raw-reports.manifest.json"
PARTS_DIRECTORY = "raw-reports-parts"
PARTS_MANIFEST = "manifest.json"
PART_BYTES = 196608
COMMIT = "3043fdfe9ef4ce3c1a8485fcecbd42ebb355dde7"
RUN = "https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41246526024"
SOURCES = {
    "a": {
        "runner_os": "ubuntu-22.04",
        "artifact_id": 13059652667,
        "job_id": 124671003730,
        "runner_id": 1000000073,
        "original_zip_bytes": 22159243,
        "original_zip_sha256": "0d74179fd13f3544bc6e1f150fe29a2d9f4fcfe895d6aca421d465595e393cbf",
    },
    "b": {
        "runner_os": "ubuntu-24.04",
        "artifact_id": 13059608360,
        "job_id": 124671003576,
        "runner_id": 1000000072,
        "original_zip_bytes": 22159502,
        "original_zip_sha256": "e100f49d7cb30a65c315a2acdb007e47dfb9abe163cb550f7b98863327a64970",
    },
}
MEMBERS = {
    "checksums.json", "classifications.json", "classifications.log",
    "commands.json", "final-inventory.json", "final-source-verification.log",
    "final-tracked-files.json", "fixture-tests.log", "inventory.json",
    "inventory.log", "recovery.json", "recovery.log", "revision.log",
    "source-retrieval.json", "summary.json", "tracked-files.json",
}
DIRECT = {
    "checksums.json", "classifications.json", "commands.json", "summary.json",
    "classifications.log", "final-source-verification.log", "fixture-tests.log",
    "inventory.log", "recovery.log", "revision.log",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream, destination=None):
    sha, size, crc = hashlib.sha256(), 0, 0
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        sha.update(block)
        size += len(block)
        crc = zlib.crc32(block, crc)
        if destination is not None:
            destination.write(block)
    return {"sha256": sha.hexdigest(), "bytes": size, "crc32": f"{crc:08x}"}


def file_digest(path):
    with path.open("rb") as stream:
        return digest(stream)


def protected_roots(directory):
    """Locate enclosing checkouts without invoking Git or trusting TMPDIR."""
    roots = {directory.resolve()}
    for location in (directory.resolve(), DIRECTORY, Path.cwd().resolve()):
        for parent in (location, *location.parents):
            marker = parent / ".git"
            if marker.exists() or marker.is_symlink():
                roots.add(parent)
                break
    return roots


def external_temporary_base(directory):
    roots = protected_roots(directory)
    for candidate in (Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp")):
        candidate = candidate.resolve()
        if candidate.is_dir() and not any(candidate.is_relative_to(root) for root in roots):
            return candidate
    raise ValueError("no temporary directory outside the source checkout is available")


@contextmanager
def archive_source(directory, expected):
    """Yield an authenticated whole archive or an external temporary assembly.

    When both representations exist, validate both. A corrupt/extra part set
    must never be concealed by a valid whole-file fallback.
    """
    directory = directory.resolve()
    require(expected["path"] == ARCHIVE, "invalid archive path")
    expected_digest = {key: expected[key] for key in ("bytes", "sha256", "crc32")}
    whole, parts_directory = directory / ARCHIVE, directory / PARTS_DIRECTORY
    has_whole = whole.exists() or whole.is_symlink()
    has_parts = parts_directory.exists() or parts_directory.is_symlink()
    require(has_whole or has_parts, "missing whole archive and multipart archive")
    if has_whole:
        require(whole.is_file() and not whole.is_symlink(), "whole archive must be a regular file")
        require(file_digest(whole) == expected_digest, "compressed archive digest differs")
        if not has_parts:
            yield whole, {"kind": "whole_file", "parts_verified": 0}
            return
    require(parts_directory.is_dir() and not parts_directory.is_symlink(),
            "multipart archive directory must be a real directory")
    mapping_path = parts_directory / PARTS_MANIFEST
    require(mapping_path.is_file() and not mapping_path.is_symlink(),
            "missing or nonregular multipart manifest")
    mapping = json.loads(mapping_path.read_bytes())
    require(isinstance(mapping, dict), "multipart manifest must be an object")
    require(type(mapping.get("schema_version")) is int and mapping["schema_version"] == 1,
            "unsupported multipart manifest")
    require(mapping.get("archive_path") == ARCHIVE
            and type(mapping.get("archive_bytes")) is int
            and mapping["archive_bytes"] == expected["bytes"]
            and mapping.get("archive_sha256") == expected["sha256"], "multipart archive identity differs")
    require(type(mapping.get("part_bytes")) is int and mapping["part_bytes"] == PART_BYTES,
            "noncanonical multipart chunk size")
    parts = mapping.get("parts")
    expected_count = (expected["bytes"] + PART_BYTES - 1) // PART_BYTES
    require(isinstance(parts, list) and len(parts) == expected_count, "multipart member count differs")
    expected_names = [f"part-{index:03d}.bin" for index in range(expected_count)]
    require({entry.name for entry in parts_directory.iterdir()} == {PARTS_MANIFEST, *expected_names},
            "missing, extra, or misnamed multipart files")
    for index, (part, name) in enumerate(zip(parts, expected_names)):
        require(isinstance(part, dict) and part.get("path") == name,
                "multipart members are reordered, duplicated, or misnamed")
        expected_size = min(PART_BYTES, expected["bytes"] - index * PART_BYTES)
        require(type(part.get("bytes")) is int and part["bytes"] == expected_size,
                "multipart member size differs")
        require(isinstance(part.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", part["sha256"]) is not None,
                "invalid multipart member digest")
        source = parts_directory / name
        require(source.is_file() and not source.is_symlink(), "multipart members must be regular files")
    with tempfile.TemporaryDirectory(prefix="p001-archive-assembly-",
                                     dir=external_temporary_base(directory)) as temporary:
        assembled = Path(temporary) / ARCHIVE
        with assembled.open("xb") as destination:
            for part in parts:
                with (parts_directory / part["path"]).open("rb") as source:
                    actual = digest(source, destination)
                require(actual["bytes"] == part["bytes"] and actual["sha256"] == part["sha256"],
                        f"multipart member digest differs: {part['path']}")
        require(file_digest(assembled) == expected_digest, "assembled archive digest differs")
        yield assembled, {"kind": "whole_file_and_ordered_parts" if has_whole else "ordered_parts",
                          "parts_verified": len(parts)}


def direct_name(member, host):
    path = Path(member)
    return f"{path.stem}-{host}{path.suffix}"


def install_exact(source, target):
    """Never overwrite an existing file, even when the caller reruns a build."""
    if target.exists():
        require(file_digest(source) == file_digest(target), f"existing file differs: {target}")
        return
    with source.open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst)


def validate_reports(members, read):
    """Check raw checksum/command/reference closure without rewriting any reports."""
    checksums = json.loads(read("checksums.json"))
    require(set(checksums) == MEMBERS - {"checksums.json"}, "incomplete original checksum manifest")
    for name, expected in checksums.items():
        require(expected == {key: members[name][key] for key in ("bytes", "sha256")},
                f"original checksum disagrees: {name}")
    commands = json.loads(read("commands.json"))
    expected_logs = {name for name in MEMBERS if name.endswith(".log")}
    require(len(commands) == len(expected_logs), "unexpected original command count")
    require({entry["log"] for entry in commands} == expected_logs, "incomplete command log mapping")
    for entry in commands:
        require(entry["exit_code"] == 0, f"original command failed: {entry['label']}")
        require(entry["log_sha256"] == members[entry["log"]]["sha256"],
                f"command log digest differs: {entry['log']}")
    require(read("revision.log") == (COMMIT + "\n").encode(), "original revision differs")
    summary = json.loads(read("summary.json"))
    require(summary["result"] == "PASS" and summary["failures"] == [], "original summary is not PASS")
    require(summary["implementation_commit"] == COMMIT, "original summary revision differs")
    require(summary["fixture_tests_executed"] == 113, "original fixture test count differs")
    require(summary["source_retrieval_sha256"] == members["source-retrieval.json"]["sha256"],
            "source retrieval reference differs")
    for prefix in ("", "final-"):
        inventory = json.loads(read(prefix + "inventory.json"))
        require(inventory["tracked_files"]["sha256"] == members[prefix + "tracked-files.json"]["sha256"],
                f"tracked inventory reference differs: {prefix or 'initial'}")
    return {"original_checksums_verified": len(checksums), "command_logs_verified": len(commands)}


def build(args):
    directory = args.directory.resolve()
    require(directory.is_dir(), f"output directory must already exist: {directory}")
    with tempfile.TemporaryDirectory(prefix="p001-raw-bundle-") as temporary:
        workspace = Path(temporary)
        hosts, objects = {}, {}
        for host, source in SOURCES.items():
            zip_path = getattr(args, "zip_" + host)
            zip_hash = file_digest(zip_path)
            require(zip_hash["sha256"] == source["original_zip_sha256"]
                    and zip_hash["bytes"] == source["original_zip_bytes"],
                    f"not the recorded original ZIP for host {host}")
            members = {}
            with zipfile.ZipFile(zip_path) as archive:
                infos = archive.infolist()
                require(len(infos) == len(MEMBERS) and {info.filename for info in infos} == MEMBERS,
                        f"unexpected or duplicate ZIP members for host {host}")
                for info in sorted(infos, key=lambda item: item.filename):
                    require(not info.is_dir() and not info.flag_bits & 1,
                            f"unsupported ZIP entry: {info.filename}")
                    temporary_member = workspace / "member.tmp"
                    with archive.open(info) as src, temporary_member.open("xb") as dst:
                        metadata = digest(src, dst)
                    require(metadata["bytes"] == info.file_size
                            and metadata["crc32"] == f"{info.CRC:08x}", f"ZIP member differs: {info.filename}")
                    sha = metadata["sha256"]
                    object_file = workspace / sha
                    if sha in objects:
                        require(objects[sha] == metadata, "content-addressed metadata collision")
                        temporary_member.unlink()
                    else:
                        temporary_member.rename(object_file)
                        objects[sha] = metadata
                    members[info.filename] = {**metadata, "object": "objects/" + sha}
                    if info.filename in DIRECT:
                        members[info.filename]["direct_copy"] = direct_name(info.filename, host)
            validate_reports(members, lambda name: (workspace / members[name]["sha256"]).read_bytes())
            hosts[host] = {
                **source,
                "artifact_name": f"p001-{source['runner_os']}-{COMMIT}",
                "artifact_download_url": (
                    "https://api.github.com/repos/boop-bip80/MAC-OS-EMULATION/actions/artifacts/"
                    f"{source['artifact_id']}/zip"
                ),
                "members": members,
            }
        output = workspace / ARCHIVE
        with lzma.LZMAFile(output, "wb", preset=6, check=lzma.CHECK_CRC64) as compressed, \
                tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for sha in sorted(objects):
                info = tarfile.TarInfo("objects/" + sha)
                info.size, info.mode = objects[sha]["bytes"], 0o644
                info.mtime, info.uid, info.gid = 0, 0, 0
                info.uname, info.gname = "", ""
                with (workspace / sha).open("rb") as stream:
                    archive.addfile(info, stream)
        install_exact(output, directory / ARCHIVE)
        for host in hosts.values():
            for member in host["members"].values():
                if "direct_copy" in member:
                    install_exact(workspace / member["sha256"], directory / member["direct_copy"])
        manifest = {
            "schema_version": 1,
            "workflow_run_url": RUN,
            "implementation_commit": COMMIT,
            "preservation_scope": "Exact uncompressed member bytes; original ZIP containers are not reconstructed.",
            "archive": {
                "path": ARCHIVE, **file_digest(output),
                "format": "USTAR with lexicographically sorted SHA-256 object paths; XZ preset 6, CRC64",
                "canonical_metadata": {"mode": "0644", "uid": 0, "gid": 0, "mtime": 0, "uname": "", "gname": ""},
            },
            "original_member_count": sum(len(host["members"]) for host in hosts.values()),
            "original_member_bytes": sum(member["bytes"] for host in hosts.values() for member in host["members"].values()),
            "unique_object_count": len(objects),
            "unique_object_bytes": sum(item["bytes"] for item in objects.values()),
            "hosts": hosts,
        }
        print(json.dumps(manifest, indent=2, sort_keys=True))


def verify(directory):
    manifest = json.loads((directory / MANIFEST).read_bytes())
    require(manifest["schema_version"] == 1 and manifest["implementation_commit"] == COMMIT,
            "unsupported preservation manifest")
    require(manifest["workflow_run_url"] == RUN, "workflow provenance differs")
    require(set(manifest["hosts"]) == set(SOURCES), "unexpected host mapping")
    objects, small, direct_count = {}, {}, 0
    for host, source in SOURCES.items():
        recorded = manifest["hosts"][host]
        require(all(recorded[key] == value for key, value in source.items()), "ZIP provenance differs")
        members = recorded["members"]
        require(set(members) == MEMBERS, f"incomplete member mapping for host {host}")
        for name, member in members.items():
            sha = member["sha256"]
            require(re.fullmatch(r"[0-9a-f]{64}", sha) is not None, "invalid object digest")
            require(member["object"] == "objects/" + sha, "invalid object path")
            metadata = {key: member[key] for key in ("bytes", "sha256", "crc32")}
            require(sha not in objects or objects[sha] == metadata, "inconsistent duplicate object")
            objects[sha] = metadata
            if name in DIRECT:
                require(member["direct_copy"] == direct_name(name, host), "invalid direct-copy path")
                require(file_digest(directory / member["direct_copy"]) == metadata,
                        f"direct copy differs: {member['direct_copy']}")
                direct_count += 1
            else:
                require("direct_copy" not in member, "unexpected direct-copy mapping")
    archive_metadata = manifest["archive"]
    seen = []
    with archive_source(directory, archive_metadata) as (archive_path, storage), \
            tarfile.open(archive_path, "r:xz") as archive:
        for info in archive:
            sha = info.name.removeprefix("objects/")
            require(info.name == "objects/" + sha and sha in objects, "unexpected archive member")
            require(info.isfile() and not info.pax_headers and info.mode == 0o644
                    and info.uid == info.gid == info.mtime == 0 and info.uname == info.gname == "",
                    f"noncanonical archive metadata: {info.name}")
            with archive.extractfile(info) as stream:
                require(digest(stream) == objects[sha], f"archive object differs: {sha}")
            if info.size < 4 * 1024 * 1024:
                with archive.extractfile(info) as stream:
                    small[sha] = stream.read()
            seen.append(sha)
    require(seen == sorted(objects), "duplicate, missing, or unordered archive members")
    require(manifest["original_member_count"] == len(MEMBERS) * len(SOURCES), "member count differs")
    require(manifest["original_member_bytes"] == sum(
        member["bytes"] for host in manifest["hosts"].values() for member in host["members"].values()
    ), "raw byte count differs")
    require(manifest["unique_object_count"] == len(objects), "object count differs")
    require(manifest["unique_object_bytes"] == sum(item["bytes"] for item in objects.values()),
            "unique byte count differs")
    closure = {}
    for host, recorded in manifest["hosts"].items():
        members = recorded["members"]
        closure[host] = validate_reports(members, lambda name: small[members[name]["sha256"]])
    report = {
        "result": "PASS", "archive_sha256": archive_metadata["sha256"],
        "archive_bytes": archive_metadata["bytes"], "members_verified": manifest["original_member_count"],
        "objects_verified": len(objects), "direct_copies_verified": direct_count, "closure": closure,
        "archive_storage": storage,
    }
    return manifest, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="action", required=True)
    build_parser = subcommands.add_parser("build")
    build_parser.add_argument("--zip-a", type=Path, required=True)
    build_parser.add_argument("--zip-b", type=Path, required=True)
    verify_parser = subcommands.add_parser("verify")
    restore_parser = subcommands.add_parser("restore")
    restore_parser.add_argument("--host", choices=sorted(SOURCES), required=True)
    restore_parser.add_argument("--output", type=Path, required=True)
    for subcommand in (build_parser, verify_parser, restore_parser):
        subcommand.add_argument("--directory", type=Path, default=DIRECTORY)
    args = parser.parse_args()
    if args.action == "build":
        build(args)
        return
    manifest, report = verify(args.directory)
    if args.action == "restore":
        require(not any(args.output.resolve().is_relative_to(root) for root in protected_roots(args.directory)),
                "restore output must be outside the source checkout and evidence directory")
        args.output.mkdir(exist_ok=False)
        members = manifest["hosts"][args.host]["members"]
        with archive_source(args.directory, manifest["archive"]) as (archive_path, _), \
                tarfile.open(archive_path, "r:xz") as archive:
            for info in archive:
                names = [name for name, member in members.items() if member["object"] == info.name]
                for name in names:
                    with archive.extractfile(info) as src, (args.output / name).open("xb") as dst:
                        metadata = digest(src, dst)
                    require(metadata == {key: members[name][key] for key in ("bytes", "sha256", "crc32")},
                            f"restored member differs: {name}")
        report.update({"restored_host": args.host, "restored_members": len(members), "output": str(args.output)})
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
