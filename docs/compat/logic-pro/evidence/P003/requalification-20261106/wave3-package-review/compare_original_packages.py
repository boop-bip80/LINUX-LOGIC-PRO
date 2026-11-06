#!/usr/bin/env python3
"""Independent P003 archive review; stdlib only, no production verifier imports.

Archives are read as data. No archive member is extracted or executed. This is
an evidence helper, not a phase gate or a replacement for independent review.
"""

import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tarfile
import zipfile


MAX_MEMBER = 256 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024 * 1024
MAX_ENTRIES = 100000
DATE = rb"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (?: [1-9]|[12][0-9]|3[01]) [0-9]{4}"
TIME = rb"[0-2][0-9]:[0-5][0-9]:[0-5][0-9]"
SOURCES = {
    "corefoundation": ("CFVersion.c", "14748415cdbf66e4f65b1d039ac7c0d190eb877a7feeca079ec34c1e5ff7e366"),
    "IOKitUser": ("kext.subproj/OSKext.c", "eee18819e7a5348073d0c382a1b03565e53f5eb00e00e8dd7dff794fa05f2046"),
    "nano": ("src/nano.c", "612842cb483fc8560bbfb2d035407e3645cc5b7f0ab066f99956521eb8ea07c5"),
    "vim": ("src/version.c", "cc2f592f4ecd3ad001ef3d4e40f3853b74cc80097e4265281278c22418664557"),
    "uuid": ("cctools/ld64/src/ld/OutputFile.cpp", "052e1e7411c88dc8391a30f489c924d6e244734c067f72698eeac5284ce2a4e4"),
    "stabs": ("cctools/ld64/src/ld/LinkEditClassic.hpp", "f407611ea2ec16577b36bd510fd169bd572da4509b677b4d42d9d83115a7cd54"),
    "headers": ("cctools/ld64/src/ld/HeaderAndLoadCommands.hpp", "e862083250232792991eecbc9b672f5ae8e1583d84509e2db1e743eddb3dfce3"),
    "linker_banner": ("cctools/ld64/src/ld/Options.cpp", "30f1d76fef5d7698f21b377ad87bf995b95ae300efe1292cc737d8722ece3a5b"),
}
RULES = {
    "libexec/darling/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation":
        ("corefoundation", "__const", [(rb"@\(#\)PROGRAM:CoreFoundation  PROJECT:CoreFoundation-1153\.18  SYSTEM:Darwin  DEVELOPER:unknown  BUILT:(" + DATE + b" " + TIME + rb")\n\x00", "%b %d %Y %H:%M:%S")]),
    "libexec/darling/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit":
        ("IOKitUser", "__cstring", [(rb"OSKEXT_BUILD_DATE (" + TIME + b" " + DATE + rb")\x00", "%H:%M:%S %b %d %Y")]),
    "libexec/darling/usr/bin/nano":
        ("nano", "__cstring", [(rb"(?:^|\x00)(" + TIME + rb")\x00", "%H:%M:%S"), (rb"(?:^|\x00)(" + DATE + rb")\x00", "%b %d %Y")]),
    "libexec/darling/usr/bin/vim":
        ("vim", "__cstring", [(rb"(?:^|\x00)(" + DATE + b" " + TIME + rb")\x00", "%b %d %Y %H:%M:%S")]),
}


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_record(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(Invalid(value)))


def safe_path(value, archive=False):
    require(isinstance(value, str) and value and "\x00" not in value and "\\" not in value, "invalid member path")
    if archive and value.startswith("./"):
        value = value[2:]
    if archive and value == ".":
        return value
    require(not value.startswith("/") and all(p not in ("", ".", "..") for p in value.split("/")), "noncanonical member path: " + value)
    return value


def manifest_entries(manifest, source):
    require(manifest.get("source_commit") == source, "manifest source mismatch")
    require(manifest.get("status") == "PASSED" and manifest.get("errors") == [], "manifest reports failure")
    result = {}
    entries = manifest["entries"]
    require(isinstance(entries, list) and 0 < len(entries) < MAX_ENTRIES, "manifest entry count outside bound")
    for entry in entries:
        name = safe_path(entry["path"])
        require(name not in result, "duplicate manifest path: " + name)
        require(entry["kind"] in ("file", "directory", "symlink"), "unsupported manifest entry")
        require(type(entry["mode"]) is int and 0 <= entry["mode"] <= 0o7777, "invalid mode")
        if entry["kind"] == "file":
            require(type(entry["size"]) is int and 0 <= entry["size"] <= MAX_MEMBER, "invalid file size")
            require(re.fullmatch("[0-9a-f]{64}", entry["sha256"]) is not None, "invalid SHA256")
        elif entry["kind"] == "symlink":
            require(isinstance(entry["target"], str), "invalid link target")
        result[name] = entry
    return result


def changes(left, right):
    result = []
    for path in sorted(left.keys() | right.keys()):
        a, b = left.get(path), right.get(path)
        if a != b:
            result.append({"path": path, "a": a, "b": b})
    return result


def inventory(path, wanted):
    entries, metadata, contents = {}, {}, {}
    total = 0
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            require(len(metadata) < MAX_ENTRIES, "archive entry bound exceeded")
            name = safe_path(member.name, archive=True)
            require(name not in metadata, "duplicate archive path: " + name)
            require(not member.issparse(), "sparse member unsupported")
            require(member.isfile() or member.isdir() or member.issym(), "unsupported archive type: " + name)
            require(0 <= member.size <= MAX_MEMBER, "archive member size bound exceeded")
            total += member.size
            require(total <= MAX_TOTAL, "archive expansion bound exceeded")
            kind = "file" if member.isfile() else "directory" if member.isdir() else "symlink"
            item = {"path": name, "kind": kind, "mode": member.mode}
            metadata[name] = {"uid": member.uid, "gid": member.gid, "uname": member.uname,
                              "gname": member.gname, "mtime": member.mtime,
                              "typeflag": member.type.hex(), "size": member.size,
                              "linkname": member.linkname, "devmajor": member.devmajor,
                              "devminor": member.devminor, "pax_headers": member.pax_headers}
            if kind == "file":
                with archive.extractfile(member) as stream:
                    data = stream.read(MAX_MEMBER + 1)
                require(len(data) == member.size, "truncated member: " + name)
                item.update(size=len(data), sha256=sha(data))
                if name in wanted:
                    contents[name] = data
            else:
                require(member.size == 0, "non-file has payload")
                if kind == "symlink":
                    item["target"] = member.linkname
            if name == ".":
                require(kind == "directory", "archive root is not a directory")
                metadata[name]["mode"] = member.mode
            else:
                entries[name] = item
    require("." in metadata, "missing explicit archive root")
    return entries, metadata, contents


def bounded(data, start, size):
    require(0 <= start <= len(data) and 0 <= size <= len(data) - start, "Mach-O range outside slice")
    return data[start:start + size]


def macho(data):
    magic = data[:4]
    fats = {b"\xca\xfe\xba\xbe": (">", 20), b"\xbe\xba\xfe\xca": ("<", 20),
            b"\xca\xfe\xba\xbf": (">", 32), b"\xbf\xba\xfe\xca": ("<", 32)}
    slices = [(0, len(data))]
    if magic in fats:
        endian, width = fats[magic]
        count, = struct.unpack(endian + "I", bounded(data, 4, 4))
        require(0 < count <= 32, "fat slice count outside bound")
        bounded(data, 8, count * width)
        slices = []
        for i in range(count):
            start, size = struct.unpack_from(endian + ("II" if width == 20 else "QQ"), data, 8 + i * width + 8)
            bounded(data, start, size)
            require(start >= 8 + count * width and size >= 28, "invalid fat slice")
            require(all(start + size <= s or s + n <= start for s, n in slices), "overlapping fat slices")
            slices.append((start, size))
    thin = {b"\xce\xfa\xed\xfe": ("<", 32), b"\xcf\xfa\xed\xfe": ("<", 64),
            b"\xfe\xed\xfa\xce": (">", 32), b"\xfe\xed\xfa\xcf": (">", 64)}
    result = []
    for base, size in slices:
        view = bounded(data, base, size)
        require(view[:4] in thin, "not a supported Mach-O file")
        endian, bits = thin[view[:4]]
        header = 32 if bits == 64 else 28
        bounded(view, 0, header)
        cpu, subtype, filetype, count, command_bytes = struct.unpack_from(endian + "IIIII", view, 4)
        require(count <= 65536 and count * 8 <= command_bytes, "invalid Mach-O command count")
        bounded(view, header, command_bytes)
        item = {"base": base, "size": size, "bits": bits, "endian": endian, "cpu": cpu,
                "subtype": subtype, "filetype": filetype, "oso": [], "uuids": [],
                "sections": [], "stabs": [], "symtab": None, "linkedit_command": None}
        pos = header
        for _ in range(count):
            command, length = struct.unpack(endian + "II", bounded(view, pos, 8))
            require(length >= 8 and length % 4 == 0 and pos + length <= header + command_bytes, "invalid load command bounds")
            if command == 0x1b:
                require(length == 24 and not item["uuids"], "invalid/duplicate UUID command")
                item["uuids"].append(base + pos + 8)
            elif command == 2:
                require(length == 24 and item["symtab"] is None, "invalid/duplicate symbol table")
                item["symtab"] = list(struct.unpack_from(endian + "IIII", view, pos + 8))
                item["symtab_command"] = [pos, length]
            elif command in (1, 0x19):
                wide = command == 0x19
                fixed, swidth, n_offset = (72, 80, 64) if wide else (56, 68, 48)
                require(length >= fixed, "truncated segment")
                segment = bounded(view, pos + 8, 16).split(b"\0")[0].decode("ascii")
                number, = struct.unpack_from(endian + "I", view, pos + n_offset)
                require(length == fixed + swidth * number, "invalid section table")
                if segment == "__LINKEDIT":
                    require(item["linkedit_command"] is None, "duplicate LINKEDIT")
                    item["linkedit_command"] = [pos, fixed]
                require(segment != "__LLVM", "embedded bitcode UUID policy unsupported")
                for j in range(number):
                    at = pos + fixed + j * swidth
                    section = bounded(view, at, 16).split(b"\0")[0].decode("ascii")
                    nbytes, offset = struct.unpack_from(endian + ("QI" if wide else "II"), view, at + (40 if wide else 36))
                    flags, = struct.unpack_from(endian + "I", view, at + (64 if wide else 56))
                    if flags & 0xff not in (1, 0xc, 0x12):
                        bounded(view, offset, nbytes)
                        item["sections"].append({"segment": segment, "name": section, "start": base + offset, "size": nbytes})
            pos += length
        require(pos == header + command_bytes, "load command count/size mismatch")
        if item["symtab"]:
            start, count, strings, strings_size = item["symtab"]
            width = 16 if bits == 64 else 12
            require(count <= 1000000, "symbol table count outside bound")
            bounded(view, start, count * width)
            bounded(view, strings, strings_size)
            for i in range(count):
                at = start + i * width
                index, = struct.unpack_from(endian + "I", view, at)
                kind = view[at + 4]
                require(index < strings_size, "symbol string index outside table")
                if kind & 0xe0:
                    end = view.find(b"\0", strings + index, strings + strings_size)
                    require(end >= 0, "unterminated STABS symbol name")
                    item["stabs"].append([at, index, end + 1 - strings])
                if kind == 0x66:
                    name = view[strings + index:end].decode("utf-8", "strict")
                    require(name, "empty N_OSO object name")
                    item["oso"].append({"offset": base + at + 8, "size": width - 8, "object": name,
                                        "n_sect": view[at + 5], "n_desc": struct.unpack_from(endian + "H", view, at + 6)[0]})
        result.append(item)
    return result


def source_bindings(repo, manifest, source):
    bindings, errors = {}, []
    pins = {x["path"]: x["sha"] for x in manifest["submodules"]}
    gitdir = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"], text=True).strip()
    for key, (path, expected) in SOURCES.items():
        owner = key if key in ("corefoundation", "IOKitUser", "nano", "vim") else "cctools-port"
        module = "src/external/" + owner
        try:
            pin = pins[module]
            tree = subprocess.check_output(["git", "-C", str(repo), "ls-tree", source, module], text=True).split()
            require(tree[:2] == ["160000", "commit"] and tree[2] == pin, "root gitlink differs from install manifest")
            content = subprocess.check_output(["git", "--git-dir=" + str(Path(gitdir) / "modules" / module), "show", pin + ":" + path], stderr=subprocess.PIPE)
            require(sha(content) == expected, "source bytes outside reviewed binding")
            lines = [i for i, line in enumerate(content.decode().splitlines(), 1) if "__DATE__" in line or "__TIME__" in line]
            bindings[key] = {"module": module, "commit": pin, "path": path, "sha256": expected,
                             "git_blob_sha1": hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest(),
                             "date_time_macro_lines": lines}
        except (KeyError, Invalid, subprocess.CalledProcessError) as exc:
            errors.append({"binding": key, "error": str(exc)})
    return bindings, errors


def uuid_proof(data, image, leaf):
    require(len(image["uuids"]) == 1, "UUID absent")
    base = image["base"]
    view = bytearray(data[base:base + image["size"]])
    offset = image["uuids"][0] - base
    actual = bytes(view[offset:offset + 16])
    view[offset:offset + 16] = bytes(16)
    excluded = []
    prefix = b""
    if image["stabs"]:
        records = image["stabs"]
        width = 16 if image["bits"] == 64 else 12
        require([r[0] for r in records] == list(range(records[0][0], records[-1][0] + width, width)), "noncontiguous STABS")
        strings, strings_size = image["symtab"][2:]
        names = [r for r in records if r[1] > 1]
        require(names and image["linkedit_command"], "unsupported STABS UUID layout")
        first = min(r[1] for r in names)
        end = max(r[2] for r in names)
        if strings_size - end < image["bits"] // 8:
            end = strings_size
        excluded = [(records[0][0], records[-1][0] + width), (strings + first, strings + end)]
        excluded += [(p, p + n) for p, n in (image["linkedit_command"], image["symtab_command"])]
        prefix = b"/" + leaf.encode()
    cursor = 0
    digest = hashlib.md5(prefix)
    for start, end in sorted(excluded):
        require(cursor <= start <= end <= len(view), "overlapping UUID exclusion")
        digest.update(view[cursor:start])
        cursor = end
    digest.update(view[cursor:])
    value = bytearray(digest.digest())
    value[6] = (value[6] & 0xf) | 0x30
    value[8] = (value[8] & 0x3f) | 0x80
    return {"actual": actual.hex(), "computed": value.hex(), "matches": actual == value,
            "excluded_slice_ranges": excluded, "hash_prefix_hex": prefix.hex()}


def spans(left, right, labels=None):
    result, start, last = [], None, None
    for i in range(max(len(left), len(right))):
        different = i >= len(left) or i >= len(right) or left[i] != right[i]
        label = labels.get(i, "UNCLASSIFIED") if labels is not None else "raw"
        if start is not None and (not different or label != last):
            result.append({"offset": start, "end": i, "a_hex": left[start:i].hex(), "b_hex": right[start:i].hex(), "classification": last})
            start = None
        if different and start is None:
            start, last = i, label
    if start is not None:
        i = max(len(left), len(right))
        result.append({"offset": start, "end": i, "a_hex": left[start:i].hex(), "b_hex": right[start:i].hex(), "classification": last})
    return result


def compare_bytes(path, a, b, bindings):
    labels, fields, errors = {}, [], []
    na, nb = bytearray(a), bytearray(b)
    def accept(offset, length, kind, detail):
        require(0 <= offset and offset + length <= min(len(a), len(b)), "normalization outside file")
        require(not any(i in labels for i in range(offset, offset + length)), "overlapping normalization fields")
        if a[offset:offset + length] == b[offset:offset + length]:
            return
        fields.append({"offset": offset, "size": length, "kind": kind,
                       "a_hex": a[offset:offset + length].hex(), "b_hex": b[offset:offset + length].hex(), **detail})
        for i in range(offset, offset + length):
            labels[i] = kind
        na[offset:offset + length] = bytes(length)
        nb[offset:offset + length] = bytes(length)
    try:
        require(len(a) == len(b), "file lengths differ")
        ma, mb = macho(a), macho(b)
        require(ma == mb, "Mach-O metadata/field positions differ")
        for image in ma:
            for field in image["oso"]:
                offset, length = field["offset"], field["size"]
                if a[offset:offset + length] == b[offset:offset + length]:
                    continue
                values = [int.from_bytes(d[offset:offset + length], "little" if image["endian"] == "<" else "big") for d in (a, b)]
                require(all(946684800 <= v <= 4102444800 for v in values), "N_OSO value is outside bounded timestamp policy")
                accept(offset, length, "N_OSO_n_value", {"object": field["object"], "values": values})
        if path in RULES:
            binding, section_name, patterns = RULES[path]
            require(binding in bindings, "missing exact source binding: " + binding)
            require(all(k in bindings for k in ("uuid", "stabs", "headers")), "missing linker UUID source binding")
            for image in ma:
                sections = [s for s in image["sections"] if s["segment"] == "__TEXT" and s["name"] == section_name]
                require(len(sections) == 1, "time-string section is ambiguous")
                section = sections[0]
                for pattern, date_format in patterns:
                    matches = [list(re.finditer(pattern, d[section["start"]:section["start"] + section["size"]])) for d in (a, b)]
                    require(all(len(m) == 1 for m in matches), "time-string occurrence is ambiguous")
                    x, y = matches[0][0], matches[1][0]
                    require(x.span(1) == y.span(1), "time-string offsets differ")
                    for m in (x, y):
                        datetime.datetime.strptime(m.group(1).decode(), date_format)
                    start, end = x.span(1)
                    accept(section["start"] + start, end - start, "source_bound_build_time", {"source_binding": binding, "a_text": x.group(1).decode(), "b_text": y.group(1).decode()})
                for offset in image["uuids"]:
                    if a[offset:offset + 16] != b[offset:offset + 16]:
                        proofs = [uuid_proof(d, image, PurePosixPath(path).name) for d in (a, b)]
                        require(all(p["matches"] for p in proofs), "content-derived UUID proof failed: " + json.dumps(proofs))
                        require(any(f["kind"] == "source_bound_build_time" for f in fields), "UUID changed without source-bound time change")
                        accept(offset, 16, "content_derived_LC_UUID", {"proof_a": proofs[0], "proof_b": proofs[1]})
    except (Invalid, ValueError, UnicodeError, struct.error) as exc:
        errors.append(str(exc))
    differences = spans(a, b, labels)
    unknown = [s for s in differences if s["classification"] == "UNCLASSIFIED"]
    return {"path": path, "sha256_a": sha(a), "sha256_b": sha(b), "size_a": len(a), "size_b": len(b),
            "changed_bytes": sum(s["end"] - s["offset"] for s in differences), "fields": fields,
            "all_changed_byte_spans": differences, "unclassified_byte_spans": unknown,
            "unclassified_bytes": sum(s["end"] - s["offset"] for s in unknown),
            "normalized_sha256_a": sha(na), "normalized_sha256_b": sha(nb),
            "normalized_equal": na == nb, "errors": errors}


def original_zip(directory):
    path = directory.with_suffix(".zip")
    if not path.is_file():
        return {"status": "ZIP_NOT_PROVIDED"}
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        require(0 < len(members) < MAX_ENTRIES and sum(m.file_size for m in members) <= MAX_TOTAL,
                "original ZIP expansion bound exceeded")
        require(all(0 <= m.file_size <= MAX_MEMBER for m in members), "original ZIP member bound exceeded")
        names = archive.namelist()
        require(len(set(names)) == len(names), "duplicate original ZIP member")
        require(archive.testzip() is None, "original ZIP CRC failure")
        for name in ("runtime-prefix.tar.gz", "install-first.json", "install-second.json", "source-built-linker.json"):
            if (directory / name).is_file():
                require(sha(archive.read(name)) == file_record(directory / name)["sha256"], "local input differs from original ZIP: " + name)
    return {**file_record(path), "member_count": len(names), "crc_all_members": "PASSED", "selected_inputs_match_zip": True,
            "source_linker_binary_members": [n for n in names if PurePosixPath(n).name == "x86_64-apple-darwin20-ld"]}


def run(args):
    manifests = [read_json(d / "install-first.json") for d in (args.a, args.b)]
    expected = [manifest_entries(m, args.expected_source) for m in manifests]
    bindings, source_errors = source_bindings(args.repo, manifests[0], args.expected_source)
    require(manifests[0]["submodules"] == manifests[1]["submodules"], "source manifests have different submodule pins")
    wanted = {x["path"] for x in changes(*expected)}
    wanted.add("libexec/darling/usr/bin/nano")
    archives = [inventory(d / "runtime-prefix.tar.gz", wanted) for d in (args.a, args.b)]
    inventory_diffs = changes(archives[0][0], archives[1][0])
    byte_paths = {r["path"] for r in inventory_diffs if r["a"] and r["b"] and r["a"]["kind"] == r["b"]["kind"] == "file" and r["a"]["sha256"] != r["b"]["sha256"]}
    for i, directory in enumerate((args.a, args.b)):
        missing = byte_paths - archives[i][2].keys()
        if missing:
            archives[i][2].update(inventory(directory / "runtime-prefix.tar.gz", missing)[2])
    byte_reviews = [compare_bytes(p, archives[0][2][p], archives[1][2][p], bindings) for p in sorted(byte_paths)]
    hosts = []
    for index, directory in enumerate((args.a, args.b)):
        first = manifests[index]
        second_path = directory / "install-second.json"
        second = manifest_entries(read_json(second_path), args.expected_source) if second_path.is_file() else None
        hosts.append({"build": "AB"[index], "original_zip": original_zip(directory),
                      "tar": file_record(directory / "runtime-prefix.tar.gz"),
                      "manifest_first": file_record(directory / "install-first.json"),
                      "manifest_second": file_record(second_path) if second else None,
                      "entry_counts": dict(collections.Counter(e["kind"] for e in archives[index][0].values())),
                      "archive_manifest_mismatches": changes(expected[index], archives[index][0]),
                      "first_second_manifest_changes": changes(expected[index], second) if second else "SECOND_MANIFEST_NOT_PROVIDED",
                      "inventory_sha256": sha(json.dumps(archives[index][0], sort_keys=True, separators=(",", ":")).encode()),
                      "linker_report_file": file_record(directory / "source-built-linker.json"),
                      "linker_report": read_json(directory / "source-built-linker.json")})
    metadata_changes = changes(archives[0][1], archives[1][1])
    linker_changes = changes(*[{r["path"]: r for r in h["linker_report"]} for h in hosts])
    for difference in linker_changes:
        left, right = difference["a"], difference["b"]
        if left and right:
            pattern = rb"(?m)^BUILD " + TIME + b" " + DATE + rb"$"
            banners = [r["version_output"].encode() for r in (left, right)]
            difference["source_bound_timestamp_banner_only"] = (
                "linker_banner" in bindings and
                all(len(list(re.finditer(pattern, b))) == 1 for b in banners) and
                re.sub(pattern, b"BUILD <date/time>", banners[0]) == re.sub(pattern, b"BUILD <date/time>", banners[1]))
        difference["raw_binary_byte_comparison"] = "UNAVAILABLE_IN_SUPPLIED_ORIGINAL_ZIPS" if not any(h["original_zip"].get("source_linker_binary_members") for h in hosts) else "ARCHIVED_BYTES_REQUIRE_SEPARATE_REVIEW"
    structural = []
    for difference in inventory_diffs:
        a, b = difference["a"], difference["b"]
        if not a or not b or {k: v for k, v in a.items() if k != "sha256"} != {k: v for k, v in b.items() if k != "sha256"}:
            structural.append(difference)
    failed = bool(source_errors or structural or any(h["archive_manifest_mismatches"] for h in hosts)
                  or any(not h["original_zip"].get("selected_inputs_match_zip") for h in hosts)
                  or any(isinstance(h["first_second_manifest_changes"], list) and h["first_second_manifest_changes"] for h in hosts)
                  or any(r["errors"] or r["unclassified_bytes"] or not r["normalized_equal"] for r in byte_reviews))
    report = {"schema": "p003.independent-original-package-review.v1", "reviewer": "/root/wave3_package",
              "purpose": args.purpose, "expected_source": args.expected_source,
              "byte_count_scope": "Installed regular-file contents only; intermediate linker and gzip envelope limits are separate.",
              "reviewed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "helper": file_record(Path(__file__).resolve()), "phase_acceptance": False,
              "status": "UNCLASSIFIED_OR_MISMATCH" if failed else "INSTALLED_PACKAGE_BYTES_CLASSIFIED",
              "source_bindings": bindings, "source_binding_errors": source_errors, "hosts": hosts,
              "differing_regular_files": len(byte_reviews),
              "identical_regular_files": sum(x["kind"] == "file" for x in archives[0][0].values()) - len(byte_reviews),
              "changed_bytes": sum(x["changed_bytes"] for x in byte_reviews),
              "unclassified_bytes": sum(x["unclassified_bytes"] for x in byte_reviews),
              "field_counts": dict(collections.Counter(f["kind"] for r in byte_reviews for f in r["fields"])),
              "structural_inventory_differences": structural, "byte_reviews": byte_reviews,
              "tar_metadata_differences": metadata_changes,
              "source_built_linker_differences": linker_changes,
              "whole_build_byte_reproducibility": "NOT_PROVED; differing intermediate linker bytes unavailable" if linker_changes else "NOT_CLAIMED; installed-prefix scope only",
              "linker_byte_limitation": "Intermediate linker bytes are not contained in the installed-prefix archives. Both source-built-linker.json reports are retained verbatim above; hashes and banner differences do not prove exhaustive binary classification.",
              "archive_envelope_limitation": "Raw gzip archives are hash-bound. Tar member metadata differences are enumerated; compressed-stream byte differences are not interpreted as installed executable differences."}
    if args.counterexample:
        path = "libexec/darling/usr/bin/nano"
        original = archives[0][2][path]
        mutated = bytearray(original)
        offset = 4096
        require(not any(f["offset"] <= offset < f["offset"] + f["size"] for r in byte_reviews if r["path"] == path for f in r["fields"]), "counterexample overlaps known field")
        mutated[offset] ^= 1
        review = compare_bytes(path, original, bytes(mutated), bindings)
        require(review["unclassified_bytes"] == 1 and review["unclassified_byte_spans"][0]["offset"] == offset and not review["normalized_equal"], "counterexample unexpectedly classified")
        report["counterexample"] = {"scope": "in-memory original A member; original archive untouched", "rejected": True, "review": review}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "purpose", "expected_source", "differing_regular_files", "changed_bytes", "unclassified_bytes", "field_counts")}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("a", "b", "repo", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--purpose", choices=("historical-method-qa", "candidate-package-review"), required=True)
    parser.add_argument("--counterexample", action="store_true")
    options = parser.parse_args()
    try:
        raise SystemExit(run(options))
    except (Invalid, KeyError, OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "REVIEW_ERROR", "error": str(exc)}))
        raise SystemExit(2)
