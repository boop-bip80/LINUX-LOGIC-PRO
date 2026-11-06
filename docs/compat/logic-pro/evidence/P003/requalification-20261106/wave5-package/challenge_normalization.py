#!/usr/bin/env python3
"""Independent nano UUID calculation and a fully rehashed, complete-package negative challenge."""
import contextlib
import copy
import datetime
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import zipfile

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[6]
BASE = Path("/workspace/scratch/430a9939323d/p003-work/run-42180484781")
SOURCE = "4622a9396c5c9fbe0014bdf6a2f695dcc491233c"
NANO = "libexec/darling/usr/bin/nano"
HELPER = OUT.parent / "wave3-package-review/compare_original_packages.py"

def check(value, message):
    if not value:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def record(path):
    with path.open("rb") as f:
        h, size = hashlib.sha256(), 0
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": h.hexdigest()}

def nano_bytes(directory):
    with tarfile.open(directory / "runtime-prefix.tar.gz", "r|gz") as t:
        for member in t:
            if member.name.removeprefix("./") == NANO:
                return t.extractfile(member).read()
    raise ValueError("nano absent")

def independent_layout(data):
    # Independently decode this concrete little-endian x86_64 image, without the helper parser.
    check(data[:4] == b"\xcf\xfa\xed\xfe", "nano is not thin Mach-O 64")
    cpu, subtype, kind, ncmds, sizeofcmds = struct.unpack_from("<5I", data, 4)
    check(cpu == 0x01000007 and kind == 2 and 0 < ncmds < 1000, "unexpected nano header")
    symtab, symcmd, uuid, linkedit = None, None, None, None
    cursor = 32
    for _ in range(ncmds):
        cmd, size = struct.unpack_from("<II", data, cursor)
        check(size >= 8 and size % 4 == 0 and cursor + size <= 32 + sizeofcmds, "load command bounds")
        if cmd == 2:
            check(symtab is None and size == 24, "symbol table command")
            symtab = struct.unpack_from("<4I", data, cursor + 8)
            symcmd = (cursor, cursor + size)
        if cmd == 0x1b:
            check(uuid is None and size == 24, "UUID command")
            uuid = cursor + 8
        if cmd == 0x19 and data[cursor + 8:cursor + 24].rstrip(b"\0") == b"__LINKEDIT":
            check(linkedit is None, "duplicate LINKEDIT")
            linkedit = (cursor, cursor + 72)
        cursor += size
    check(cursor == 32 + sizeofcmds and all(x is not None for x in (symtab, symcmd, uuid, linkedit)), "required commands")
    symoff, nsyms, stroff, strsize = symtab
    check(symoff + nsyms * 16 <= len(data) and stroff + strsize <= len(data), "symbol bounds")
    stabs, oso = [], []
    for i in range(nsyms):
        at = symoff + 16 * i
        idx, typ, sect, desc, value = struct.unpack_from("<IBBHQ", data, at)
        check(idx < strsize, "symbol name bound")
        if typ & 0xe0:
            end = data.index(b"\0", stroff + idx, stroff + strsize)
            stabs.append({"record": at, "index": idx, "string_start": stroff + idx, "string_end": end + 1, "type": typ})
            if typ == 0x66:
                oso.append({"offset": at + 8, "value": value, "string_start": stroff + idx, "string_end": end + 1})
    check(stabs and [s["record"] for s in stabs] == list(range(stabs[0]["record"], stabs[-1]["record"] + 16, 16)), "noncontiguous STABS")
    named = [s for s in stabs if s["index"] > 1]
    first = min(s["string_start"] for s in named)
    last = max(s["string_end"] for s in named)
    if stroff + strsize - last < 8:
        last = stroff + strsize
    exclusions = sorted([symcmd, linkedit, (stabs[0]["record"], stabs[-1]["record"] + 16), (first, last)])
    check(all(a[1] <= b[0] for a, b in zip(exclusions, exclusions[1:])), "overlapping exclusions")
    return {"uuid_offset": uuid, "exclusions": exclusions, "stabs": stabs, "oso": oso}

def independent_uuid(data):
    layout = independent_layout(data)
    buffer = bytearray(data)
    uuid = layout["uuid_offset"]
    actual = bytes(buffer[uuid:uuid + 16])
    buffer[uuid:uuid + 16] = bytes(16)
    include = bytearray(b"\1") * len(buffer)
    for start, end in layout["exclusions"]:
        include[start:end] = bytes(end - start)
    # This independently constructs the exact content stream rather than calling helper.uuid_proof.
    content = bytes(value for i, value in enumerate(buffer) if include[i])
    computed = bytearray(hashlib.md5(b"/nano" + content).digest())
    computed[6] = computed[6] % 16 + 0x30
    computed[8] = computed[8] % 64 + 0x80
    return {"actual": actual.hex(), "computed": computed.hex(), "matches": actual == computed,
            "excluded_ranges": layout["exclusions"], "hashed_content_sha256": sha(content)}

def main():
    spec = importlib.util.spec_from_file_location("wave3_comparator_for_challenge", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    check(sha(HELPER.read_bytes()) == "0115737614c47266678af87da2bb9c681af4c009c061b538299eacaef4104d62", "helper changed")
    original_report = json.loads((OUT / "final-installed-byte-comparison.json").read_text())
    bindings = original_report["source_bindings"]
    a, b = nano_bytes(BASE / "build-a"), nano_bytes(BASE / "build-b")
    proofs = {"A": independent_uuid(a), "B": independent_uuid(b)}
    check(all(p["matches"] for p in proofs.values()), "independent original UUID mismatch")
    real_review = helper.compare_bytes(NANO, a, b, bindings)
    check(real_review["unclassified_bytes"] == 0 and real_review["normalized_equal"] and not real_review["errors"], "real source-bound comparison failed")
    layout = independent_layout(a)
    field = layout["oso"][0]
    timestamp_variant = bytearray(a)
    struct.pack_into("<Q", timestamp_variant, field["offset"], field["value"] + 1)
    allowed = helper.compare_bytes(NANO, a, bytes(timestamp_variant), bindings)
    check(allowed["normalized_equal"] and allowed["unclassified_bytes"] == 0 and {f["kind"] for f in allowed["fields"]} == {"N_OSO_n_value"} and independent_uuid(timestamp_variant)["matches"], "timestamp positive control failed")
    offset = next(i for s in layout["stabs"] if s["type"] != 0x66 and s["index"] > 1
                  for i in range(s["string_start"], s["string_end"] - 1)
                  if 65 <= a[i] <= 122 and not any(o["string_start"] <= i < o["string_end"] for o in layout["oso"]))
    corrupted = bytearray(a)
    corrupted[offset] ^= 1
    corrupt_proof = independent_uuid(corrupted)
    check(corrupt_proof["matches"] and corrupt_proof["actual"] == proofs["A"]["actual"], "excluded-string mutation unexpectedly changes derived UUID")
    corrupt_review = helper.compare_bytes(NANO, a, bytes(corrupted), bindings)
    check(corrupt_review["unclassified_bytes"] == 1 and not corrupt_review["normalized_equal"] and not corrupt_review["errors"], "excluded string wrongly normalized")
    absent_binding = helper.compare_bytes(NANO, a, b, {k:v for k,v in bindings.items() if k != "nano"})
    check(absent_binding["errors"] == ["missing exact source binding: nano"] and not absent_binding["normalized_equal"], "missing source binding did not reject")

    with tempfile.TemporaryDirectory(prefix="rehashed-negative-", dir=OUT) as tmp:
        fixture = Path(tmp) / "mutated-build"
        fixture.mkdir()
        with (fixture / "runtime-prefix.tar.gz").open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as gz:
                with tarfile.open(fileobj=gz, mode="w|", format=tarfile.GNU_FORMAT) as target:
                    with tarfile.open(BASE / "build-a/runtime-prefix.tar.gz", "r|gz") as source:
                        for member in source:
                            if member.name.removeprefix("./") == NANO:
                                target.addfile(member, io.BytesIO(corrupted))
                            else:
                                target.addfile(member, source.extractfile(member) if member.isfile() else None)
        for stage in ("first", "second"):
            manifest = json.loads((BASE / "build-a" / ("install-" + stage + ".json")).read_text())
            matched = [e for e in manifest["entries"] if e["path"] == NANO]
            check(len(matched) == 1 and matched[0]["sha256"] == sha(a), "original nano manifest hash")
            matched[0]["sha256"] = sha(corrupted)
            (fixture / ("install-" + stage + ".json")).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        shutil.copyfile(BASE / "build-a/source-built-linker.json", fixture / "source-built-linker.json")
        tar_record = record(fixture / "runtime-prefix.tar.gz")
        (fixture / "runtime-prefix.sha256").write_text(tar_record["sha256"] + "  runtime-prefix.tar.gz\n")
        replacements = {"runtime-prefix.tar.gz", "runtime-prefix.sha256", "install-first.json", "install-second.json"}
        with zipfile.ZipFile(BASE / "build-a.zip") as source, zipfile.ZipFile(fixture.with_suffix(".zip"), "w") as target:
            for original in source.infolist():
                info = copy.copy(original)
                info.compress_type = zipfile.ZIP_STORED
                with target.open(info, "w") as out:
                    if original.filename in replacements:
                        with (fixture / original.filename).open("rb") as stream:
                            shutil.copyfileobj(stream, out)
                    else:
                        with source.open(original) as stream:
                            shutil.copyfileobj(stream, out)
        with zipfile.ZipFile(fixture.with_suffix(".zip")) as z:
            check(len(z.infolist()) == 459 and z.testzip() is None, "derived fixture ZIP fidelity")
        fixture_identity = {"zip": record(fixture.with_suffix(".zip")), "tar": tar_record,
                            "manifest_first": record(fixture / "install-first.json"), "manifest_second": record(fixture / "install-second.json"),
                            "original_zip_member_inventory_preserved": 459, "replacement_members": sorted(replacements)}
        args = SimpleNamespace(a=BASE / "build-a", b=fixture, repo=REPO, output=OUT / "final-rehashed-corruption-comparison.json",
                               expected_source=SOURCE, purpose="candidate-package-review", counterexample=False)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = helper.run(args)
        negative = json.loads(args.output.read_text())
        check(code == 1 and negative["status"] == "UNCLASSIFIED_OR_MISMATCH" and negative["unclassified_bytes"] == 1 and negative["differing_regular_files"] == 1, "full rehashed negative did not reject exactly one byte")
        check(not negative["source_binding_errors"] and not negative["structural_inventory_differences"], "negative failed for unrelated source/structure reason")
        check(all(h["archive_manifest_mismatches"] == [] and h["first_second_manifest_changes"] == [] and h["original_zip"]["selected_inputs_match_zip"] and h["original_zip"]["crc_all_members"] == "PASSED" for h in negative["hosts"]), "negative failed only stale hashes")
        check(all(not r["errors"] for r in negative["byte_reviews"]), "negative had parser error")

    gd = Path(subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], text=True).strip()) / "modules/src/external/cctools-port"
    source_files = {}
    for binding in ("uuid", "linker_banner"):
        row = bindings[binding]
        data = subprocess.check_output(["git", "--git-dir=" + str(gd), "show", row["commit"] + ":" + row["path"]])
        check(sha(data) == row["sha256"], "pinned linker source differs")
        source_files[binding] = {**row, "independently_read_sha256": sha(data)}
        if binding == "linker_banner":
            check(b'__TIME__' in data and b'__DATE__' in data, "linker banner source macros absent")
    linkers = [json.loads((BASE / n / "source-built-linker.json").read_text())[0] for n in ("build-a", "build-b")]
    check(all(l["version_exit_code"] == 0 for l in linkers), "linker version command failed")
    pattern = r"(?m)^BUILD \d\d:\d\d:\d\d [A-Z][a-z]{2} [ \d]\d \d{4}$"
    check(all(len(re.findall(pattern, l["version_output"])) == 1 for l in linkers), "ambiguous linker banner")
    check(re.sub(pattern, "BUILD <date/time>", linkers[0]["version_output"]) == re.sub(pattern, "BUILD <date/time>", linkers[1]["version_output"]), "linker nonbanner metadata differs")
    report = {"reviewer": "/root/wave5_package", "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "source": SOURCE, "run": 42180484781, "status": "PASSED", "phase_acceptance": False,
              "script": record(Path(__file__)), "helper": record(HELPER), "independent_original_UUIDs": proofs,
              "real_nano_source_bound_comparison": real_review, "timestamp_positive_control": allowed,
              "missing_exact_source_binding_negative": absent_binding,
              "excluded_string_mutation": {"offset": offset, "before_hex": a[offset:offset+1].hex(), "after_hex": bytes(corrupted[offset:offset+1]).hex(),
                                           "original_member_sha256": sha(a), "mutated_member_sha256": sha(corrupted), "UUID_still_valid": corrupt_proof,
                                           "byte_comparison": corrupt_review},
              "full_rehashed_negative_fixture": {**fixture_identity, "exit_code": code, "rejection": "one unclassified byte; all actual tar/manifest and ZIP integrity checks pass",
                                                 "temporary_fixture_removed": True, "report": record(OUT / "final-rehashed-corruption-comparison.json")},
              "pinned_linker_sources": source_files, "linker_reports": linkers,
              "linker_metadata_adjudication": "Only the reported BUILD date/time line differs; each original command exited zero. Actual linker binaries are absent, so their differing hashes are not an exhaustive byte classification.",
              "whole_build_byte_identity": "NOT_PROVED"}
    (OUT / "final-normalization-challenge.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASSED", "independent_original_UUIDs_match": True, "timestamp_positive_control": "CLASSIFIED",
                      "excluded_string_offset": offset, "excluded_string_UUID_valid": True, "full_rehashed_negative_exit": code,
                      "negative_unclassified_bytes": negative["unclassified_bytes"], "negative_archive_manifest_mismatches": 0,
                      "negative_ZIP_members": 459, "missing_source_binding": "REJECTED", "whole_build_byte_identity": "NOT_PROVED"}, indent=2))

if __name__ == "__main__":
    main()
