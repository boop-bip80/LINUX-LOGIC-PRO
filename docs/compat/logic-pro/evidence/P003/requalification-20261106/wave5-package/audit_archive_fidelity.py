#!/usr/bin/env python3
"""Wave 5 data-only original ZIP, complete tar and reinstall audit; no production imports."""
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import zipfile

SOURCE = "4622a9396c5c9fbe0014bdf6a2f695dcc491233c"
TREE = "9db3623bd2c81d18b17b29c921b1d6212ca1339d"
RUN = 42180484781
BASE = Path("/workspace/scratch/430a9939323d/p003-work/run-42180484781")
OUT = Path(__file__).resolve().parent
EXPECTED = {
    "build-a": (87409741, "27b4a147ff1993bc6756172767cb4d60a8d4e437d5f9d85effe039571d5aa038"),
    "build-b": (87410244, "a7c394d71cc4d83857c0dd2988291c0b9e4bf31cb1555785c2e71dfcd6387759"),
    "independent-runtime": (36170, "c77fdb0085e892cd39ea30b36c2e5e352a87f3f17e0d05234b5395b8c32a46a9"),
    "comparison": (35804, "92fac49f42ffc2e03d267cef76f4bdc2841803b0a429c38b9f216475e8012915"),
}

def check(condition, message):
    if not condition:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def stream_hash(stream):
    h, size = hashlib.sha256(), 0
    while chunk := stream.read(1024 * 1024):
        h.update(chunk)
        size += len(chunk)
    return size, h.hexdigest()

def file_record(path):
    with path.open("rb") as f:
        size, sha = stream_hash(f)
    return {"bytes": size, "sha256": sha}

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result

def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def canonical(name, tar=False):
    if tar and name.startswith("./"):
        name = name[2:]
    if tar and name == ".":
        return name
    check(isinstance(name, str) and name and not name.startswith("/") and
          "\\" not in name and "\0" not in name and
          all(p not in ("", ".", "..") for p in name.split("/")), "unsafe archive path")
    check(str(PurePosixPath(name)) == name, "noncanonical archive path")
    return name

def audit_zip(name, official):
    path, directory = BASE / (name + ".zip"), BASE / name
    record = file_record(path)
    check((record["bytes"], record["sha256"]) == EXPECTED[name], name + " input identity")
    check(official["size_in_bytes"] == record["bytes"] and official["digest"] == "sha256:" + record["sha256"], "official artifact identity")
    check(official["workflow_run"]["id"] == RUN and official["workflow_run"]["head_sha"] == SOURCE and not official["expired"], "official artifact source/run")
    members = {}
    with zipfile.ZipFile(path) as z:
        check(z.testzip() is None, "ZIP CRC error")
        check(len(z.infolist()) < 100000 and sum(i.file_size for i in z.infolist()) < 4 * 1024**3, "ZIP expansion bound")
        for info in z.infolist():
            member = canonical(info.filename)
            check(member not in members and not info.is_dir(), "duplicate or directory ZIP member")
            check(not info.flag_bits & 1 and 0 <= info.file_size <= 256 * 1024**2, "encrypted or oversized ZIP member")
            mode = info.external_attr >> 16
            check(stat.S_IFMT(mode) in (0, stat.S_IFREG), "nonregular ZIP member")
            local = directory / member
            check(local.is_file() and not local.is_symlink(), "missing/nonregular extracted member: " + member)
            with z.open(info) as f:
                size, sha = stream_hash(f)
            check(size == info.file_size and file_record(local) == {"bytes": size, "sha256": sha}, "ZIP/extracted bytes mismatch: " + member)
            members[member] = {"bytes": size, "sha256": sha, "crc32": f"{info.CRC:08x}", "mode": mode,
                               "compressed_bytes": info.compress_size, "compression": info.compress_type}
    local_files = {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file() or p.is_symlink()}
    check(local_files == set(members), "extracted member inventory differs")
    required = ({"install-first.json", "install-second.json", "runtime-prefix.tar.gz", "runtime-prefix.sha256",
                 "cmake-install-manifest-first.txt", "cmake-install-manifest-second.txt", "compile_commands.json",
                 "source-built-linker.json", "source-classifications.json", "native-first.json", "native-second.json",
                 "probes-first/report.json", "probes-second/report.json", "toolchain.lock.json", "build-summary.json"}
                if name.startswith("build-") else
                {"package-review.json", "runtime/report.json", "toolchain.lock.json"} if name == "independent-runtime" else
                {"p003-comparison.json"})
    check(required <= set(members), "required original member absent")
    return {**record, "official_artifact_id": official["id"], "member_count": len(members),
            "crc_all_members": "PASSED", "all_original_and_extracted_members_match": True,
            "required_members_present": sorted(required), "members": members}

def tar_envelope(path, ranges):
    """Hash every decompressed byte, and independently all bytes outside regular-file payloads."""
    raw, other = hashlib.sha256(), hashlib.sha256()
    cursor = 0
    with gzip.open(path, "rb") as stream:
        def consume(length, is_payload):
            nonlocal cursor
            while length:
                data = stream.read(min(length, 1024 * 1024))
                check(data, "truncated gzip stream")
                raw.update(data)
                if not is_payload:
                    other.update(data)
                cursor += len(data)
                length -= len(data)
        for start, size in ranges:
            check(start >= cursor, "overlapping tar file payloads")
            consume(start - cursor, False)
            consume(size, True)
        while data := stream.read(1024 * 1024):
            raw.update(data)
            other.update(data)
            cursor += len(data)
    with path.open("rb") as f:
        header = f.read(10)
    check(header[:3] == b"\x1f\x8b\x08" and header[3] == 0, "unexpected gzip header")
    return {"decompressed_bytes": cursor, "decompressed_sha256": raw.hexdigest(),
            "all_non_regular_payload_bytes_sha256": other.hexdigest(), "gzip_header_hex": header.hex(),
            "gzip_full_stream_crc_read": "PASSED"}

def audit_tar(name):
    directory = BASE / name
    first, second = [read_json(directory / ("install-" + n + ".json")) for n in ("first", "second")]
    for m in (first, second):
        check(m["source_commit"] == SOURCE and m["status"] == "PASSED" and m["errors"] == [], "manifest status/source")
        check(m["excluded_control_files"] == [".p003-isolated-install.json"], "unexpected manifest exclusion")
        check(m["configuration"] == {"components": "cli,gui", "install_prefix": "/opt/darling-p003", "source_dir": "/p003/source"}, "manifest configuration")
    check(first == second, "first/reinstall manifests differ")
    expected = {canonical(e["path"]): e for e in first["entries"]}
    check(len(expected) == len(first["entries"]), "duplicate manifest entry")
    path = directory / "runtime-prefix.tar.gz"
    archive_record = file_record(path)
    check((directory / "runtime-prefix.sha256").read_text().split()[0] == archive_record["sha256"], "tar checksum file differs")
    entries, metadata, order, payload_ranges = {}, {}, [], []
    with tarfile.open(path, "r|gz") as archive:
        for m in archive:
            name_in_tar = canonical(m.name, tar=True)
            check(name_in_tar not in metadata and not m.issparse(), "duplicate or sparse tar member")
            check(m.isfile() or m.isdir() or m.issym(), "special/hardlink tar member")
            check(0 <= m.size <= 256 * 1024**2 and len(metadata) < 100000, "tar bound exceeded")
            kind = "file" if m.isfile() else "directory" if m.isdir() else "symlink"
            record = {"path": name_in_tar, "kind": kind, "mode": m.mode}
            if kind == "file":
                with archive.extractfile(m) as stream:
                    size, sha = stream_hash(stream)
                check(size == m.size, "tar file size mismatch")
                record.update(size=size, sha256=sha)
                payload_ranges.append((m.offset_data, m.size))
            else:
                check(m.size == 0, "nonfile payload")
                if kind == "symlink":
                    record["target"] = m.linkname
            metadata[name_in_tar] = {"mode": m.mode, "uid": m.uid, "gid": m.gid, "uname": m.uname,
                                     "gname": m.gname, "mtime": m.mtime, "type": m.type.hex(),
                                     "size": m.size, "linkname": m.linkname, "devmajor": m.devmajor,
                                     "devminor": m.devminor, "pax": m.pax_headers}
            order.append(name_in_tar)
            if name_in_tar == ".":
                check(kind == "directory", "tar root type")
            else:
                entries[name_in_tar] = record
    check("." in metadata and entries == expected, "complete tar/manifest inventory differs")
    check((directory / "cmake-install-manifest-first.txt").read_bytes() == (directory / "cmake-install-manifest-second.txt").read_bytes(), "CMake reinstall inventory differs")
    report = {"archive": archive_record, "manifest_first": file_record(directory / "install-first.json"),
              "manifest_second": file_record(directory / "install-second.json"), "entire_first_second_manifests_equal": True,
              "complete_tar_manifest_equal": True, "entry_count": len(entries), "kind_counts": dict(collections.Counter(e["kind"] for e in entries.values())),
              "metadata_sha256": digest(json.dumps(metadata, sort_keys=True).encode()), "member_order_sha256": digest(json.dumps(order).encode()),
              "metadata_value_sets": {k: sorted({json.dumps(v[k], sort_keys=True) for v in metadata.values()}) for k in ("uid", "gid", "uname", "gname", "mtime", "devmajor", "devminor", "pax")},
              **tar_envelope(path, payload_ranges)}
    return report, entries, metadata

def main():
    check(subprocess.check_output(["git", "rev-parse", SOURCE + "^{tree}"], text=True).strip() == TREE, "candidate tree mismatch")
    official = read_json(BASE / "metadata-final.json")
    jobs = official["jobs"]["jobs"]
    check(len(jobs) == 6 and all(j["run_id"] == RUN and j["head_sha"] == SOURCE and j["status"] == "completed" and j["conclusion"] == "success" for j in jobs), "official jobs/source status")
    artifacts = {a["name"]: a for a in official["artifacts"]["artifacts"]}
    zips = {name: audit_zip(name, artifacts["p003-" + name + "-" + SOURCE]) for name in EXPECTED}
    comparison = read_json(BASE / "comparison/p003-comparison.json")
    check(comparison["implementation_commit"] == SOURCE and comparison["status"] == "READY_FOR_INDEPENDENT_REVIEW" and comparison["automated_checks"] == "PASS", "comparison source/status")
    for label, name in (("first", "build-a"), ("second", "build-b")):
        check(comparison[label + "_evidence_sha256"] == {n: r["sha256"] for n, r in zips[name]["members"].items()}, "comparison all-member digest map differs")
    tar_results = [audit_tar(name) for name in ("build-a", "build-b")]
    a, b = tar_results
    check(a[2] == b[2], "cross-build tar metadata differences require adjudication")
    check(a[0]["all_non_regular_payload_bytes_sha256"] == b[0]["all_non_regular_payload_bytes_sha256"], "unclassified nonpayload tar bytes")
    check(a[0]["member_order_sha256"] == b[0]["member_order_sha256"], "tar member order differs")
    replay = read_json(BASE / "independent-runtime/package-review.json")
    check(replay["source_commit"] == SOURCE and replay["status"] == "PASS" and replay["errors"] == [] and replay["installed_readback"] == "PASS", "replay source/readback")
    check(replay["archive_sha256"] == a[0]["archive"]["sha256"] and replay["archive_bytes"] == a[0]["archive"]["bytes"] and replay["manifest_sha256"] == a[0]["manifest_first"]["sha256"] and replay["entry_count"] == a[0]["entry_count"], "replay original package binding")
    report = {"reviewer": "/root/wave5_package", "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "source": SOURCE, "tree": TREE, "run": RUN, "status": "PASSED", "phase_acceptance": False,
              "script": file_record(Path(__file__)), "official_metadata": file_record(BASE / "metadata-final.json"),
              "jobs": [{k:j[k] for k in ("id", "name", "head_sha", "run_id", "status", "conclusion")} for j in jobs],
              "originals": zips, "tar_and_reinstall": {"A": a[0], "B": b[0]},
              "cross_build_tar_metadata_equal": True, "all_non_regular_payload_tar_bytes_equal": True,
              "comparison_all_original_member_maps_equal": True, "replay_original_A_binding": replay,
              "limits": "Data-only audit; no archive executables run. Compressed artifacts are identity-bound; whole-build byte identity is not claimed."}
    (OUT / "final-archive-fidelity.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "original_member_counts": {k:v["member_count"] for k,v in zips.items()},
                      "tar_counts": a[0]["kind_counts"], "all_nonpayload_tar_bytes_equal": True,
                      "both_complete_reinstall_manifests_equal": True, "tar_metadata_value_sets": a[0]["metadata_value_sets"]}, indent=2))

if __name__ == "__main__":
    main()
