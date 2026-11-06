#!/usr/bin/env python3
"""Offline Wave 4 runtime evidence calculation; never launches Darling.

This reviewer helper imports no production runner, comparator, image decoder,
or probe code. It reads originals without modifying them. A successful result
verifies one campaign's retained evidence, not all P003 phase gates.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import zlib


DRIVER_SHA256 = "d2cf2a5d4d50d7c3e8574dbb696a7f076c2d2cb4543972ccbe3f935968ad6edc"
INSTALLATION = "/opt/darling-p003"
PROBES = "libexec/darling/usr/libexec/p003/"
OWNERS = (("AppKit", "C"), ("Foundation", "C"), ("CoreGraphics", "A"),
          ("CoreText", "A"), ("ImageIO", "A"), ("QuartzCore", "A"),
          ("AudioToolbox", "A"))
EXITS = {name: 0 for name in (
    "macho-known-vector", "macho-nonce", "macho-boundary-64", "foundation",
    "gui", "gui-focus", "gui-move", "gui-click", "gui-type",
    "gui-acknowledge", "shutdown")}
EXITS.update({name: 64 for name in (
    "macho-reject-65", "macho-invalid", "foundation-invalid", "gui-invalid")})
STUB = re.compile(r"\bSTUB(?:\s|:)|\blibxpc stub called:|\bunimplemented in\b|"
                  r"only defined for abstract class\. Define")


class Rejected(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise Rejected(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bound(root, reference):
    name = reference["file"]
    need(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
         "evidence reference is not a plain filename")
    path = root / name
    need(path.is_file() and not path.is_symlink(), f"missing or linked evidence: {name}")
    data = path.read_bytes()
    need(sha(data) == reference["sha256"], f"SHA-256 mismatch: {name}")
    if "bytes" in reference:
        need(len(data) == reference["bytes"], f"byte count mismatch: {name}")
    return data


def fnv32(value):
    accumulator = 2166136261
    for octet in value.encode("ascii"):
        accumulator = ((accumulator ^ octet) * 16777619) & 0xffffffff
    return f"{accumulator:08x}"


def markers(text):
    return [line for line in text.splitlines() if line.startswith("P003_")]


def decode_xwd(data):
    need(len(data) >= 100, "short XWD header")
    fields = struct.unpack_from(">25I", data)
    header, version, form, depth, width, height, xoffset, order = fields[:8]
    bits, stride, visual = fields[11:14]
    masks, colors = fields[14:17], fields[19]
    need(version == 7 and form == 2 and visual == 4, "unexpected XWD format")
    need(200 <= width <= 1024 and 120 <= height <= 768, "unexpected XWD dimensions")
    need(depth in (24, 32) and bits in (24, 32) and depth <= bits
         and order in (0, 1) and xoffset == 0, "unexpected XWD pixel layout")
    unit = bits // 8
    need(100 < header <= len(data) and colors <= 4096, "invalid XWD header/table length")
    need(width * unit <= stride <= width * 8, "invalid XWD stride")
    start = header + 12 * colors
    need(start + stride * height == len(data), "invalid XWD payload length")
    need(all(0 < mask < 1 << bits for mask in masks)
         and not (masks[0] & masks[1] or masks[0] & masks[2] or masks[1] & masks[2]),
         "invalid XWD channel masks")
    channels = []
    for mask in masks:
        shift = (mask & -mask).bit_length() - 1
        maximum = mask >> shift
        need(maximum & (maximum + 1) == 0, "non-contiguous XWD channel")
        channels.append((mask, shift, maximum))
    rgb = bytearray()
    for y in range(height):
        row = data[start + y * stride:start + y * stride + width * unit]
        for x in range(width):
            pixel = int.from_bytes(row[x * unit:(x + 1) * unit], "little" if order == 0 else "big")
            rgb.extend(((pixel & mask) >> shift) * 255 // maximum
                       for mask, shift, maximum in channels)
    return width, height, depth, bytes(rgb)


def decode_png(data):
    need(data[:8] == b"\x89PNG\r\n\x1a\n", "invalid PNG signature")
    offset, chunks = 8, []
    while offset < len(data):
        need(offset + 12 <= len(data), "short PNG chunk")
        size = int.from_bytes(data[offset:offset + 4], "big")
        end = offset + 12 + size
        need(end <= len(data), "truncated PNG payload")
        kind, payload = data[offset + 4:offset + 8], data[offset + 8:end - 4]
        need(zlib.crc32(kind + payload) == int.from_bytes(data[end - 4:end], "big"),
             "PNG chunk CRC mismatch")
        chunks.append((kind, payload))
        offset = end
    need(chunks and chunks[0][0] == b"IHDR" and chunks[-1] == (b"IEND", b""),
         "missing PNG boundary chunks")
    need(len(chunks[0][1]) == 13, "invalid PNG IHDR")
    width, height, bits, color, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1])
    need(200 <= width <= 1024 and 120 <= height <= 768, "unexpected PNG dimensions")
    need((bits, color, compression, filtering, interlace) == (8, 2, 0, 0, 0),
         "expected non-interlaced 8-bit RGB PNG")
    need(all(kind == b"IDAT" for kind, _ in chunks[1:-1]) and len(chunks) >= 3,
         "unexpected PNG chunk sequence")
    inflater = zlib.decompressobj()
    expected = height * (1 + width * 3)
    packed = inflater.decompress(b"".join(payload for _, payload in chunks[1:-1]), expected + 1)
    need(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail
         and len(packed) == expected, "invalid PNG scanline payload")
    stride, previous, rgb = width * 3, bytearray(width * 3), bytearray()
    for y in range(height):
        at = y * (stride + 1)
        kind = packed[at]
        need(kind in range(5), "unsupported PNG filter")
        row = bytearray(packed[at + 1:at + stride + 1])
        for x in range(stride):
            left = row[x - 3] if x >= 3 else 0
            above = previous[x]
            upper_left = previous[x - 3] if x >= 3 else 0
            if kind == 1:
                prediction = left
            elif kind == 2:
                prediction = above
            elif kind == 3:
                prediction = (left + above) // 2
            elif kind == 4:
                predictor = left + above - upper_left
                candidates = (left, above, upper_left)
                prediction = min(candidates, key=lambda item: abs(predictor - item))
            else:
                prediction = 0
            row[x] = (row[x] + prediction) & 255
        rgb.extend(row)
        previous = row
    return width, height, bytes(rgb)


def inspect_images(root, report):
    images = {}
    for state, targets in (("before", ((255, 0, 0), (0, 0, 255))),
                           ("after", ((0, 255, 0), (255, 255, 0)))):
        item = report["screenshots"][state]
        width, height, depth, rgb = decode_xwd(bound(root, item))
        png_width, png_height, png_rgb = decode_png(bound(root, item["png"]))
        need((width, height, rgb) == (png_width, png_height, png_rgb),
             f"{state}: PNG differs from original XWD RGB raster")
        samples = []
        for x, target in zip((width // 4, 3 * width // 4), targets):
            center = 3 * (height // 2 * width + x)
            samples.append(list(rgb[center:center + 3]))
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    at = 3 * ((height // 2 + dy) * width + x + dx)
                    actual = rgb[at:at + 3]
                    need(all((value >= 200 if goal == 255 else value <= 40)
                             for value, goal in zip(actual, target)),
                         f"{state}: wrong rendered color at ({x + dx}, {height // 2 + dy})")
        observed = dict(width=width, height=height, depth=depth,
                        left_rgb=samples[0], right_rgb=samples[1])
        need(report["screenshots"][state]["pixels"] == observed,
             f"{state}: declared pixel sample differs from decoded XWD")
        images[state] = {**observed, "patch_pixels_checked": 50,
                         "rgb_sha256": sha(rgb), "rgb_bytes_compared": len(rgb),
                         "xwd_sha256": item["sha256"], "png_sha256": item["png"]["sha256"]}
    return images


def read_commands(root, rows, exits):
    need(len(rows) == len(exits) and {row["label"] for row in rows} == set(exits),
         "missing, duplicate or unexpected command evidence")
    streams, receipts = {}, []
    for row in rows:
        label, expected = row["label"], exits[row["label"]]
        need(row["exit_code"] == expected and row.get("expected_exit_code", 0) == expected
             and row.get("timed_out", False) is False, f"{label}: wrong actual/expected exit or timeout")
        pair = {}
        for stream in ("stdout", "stderr"):
            pair[stream] = bound(root, row[stream]).decode("utf-8")
            need(not STUB.search(pair[stream]), f"{label}: raw {stream} contains a stub diagnostic")
        streams[label] = pair
        receipts.append({"label": label, "argv": row["argv"], "exit_code": row["exit_code"],
                         "stdout_sha256": row["stdout"]["sha256"],
                         "stderr_sha256": row["stderr"]["sha256"]})
    return streams, receipts


def review(report_path, manifest_path, commit):
    report_bytes, manifest_bytes = report_path.read_bytes(), manifest_path.read_bytes()
    report, manifest = json.loads(report_bytes), json.loads(manifest_bytes)
    root = report_path.parent
    independent = report.get("schema") == "darling.p003.independent-runtime.v1"
    need(independent or report.get("schema") == "logic-pro-p003-probes-v1", "unrecognized report schema")
    need(report.get("source_commit" if independent else "source_revision") == commit,
         "report has a different source commit")
    need(report["status"] == ("PASS" if independent else "PASSED")
         and report["passed"] is True and report["errors"] == [], "report is not successful")
    need(manifest["source_commit"] == commit and manifest["status"] == "PASSED"
         and manifest["errors"] == [], "installation manifest is not successful for this commit")
    names = {"macho-known-vector", "macho-boundary-64", "macho-reject-65",
             "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
             "gui-event-roundtrip", "runtime-shutdown"}
    names.update(("macho-fresh-nonce", "foundation-fresh-nonce") if independent
                 else ("macho-nonce", "foundation-objects"))
    need(len(report["cases"]) == 10 and {row["name"] for row in report["cases"]} == names
         and all(row["status"] == ("PASS" if independent else "PASSED") for row in report["cases"]),
         "ten required cases were not completed exactly once")
    nonce = report["nonce"]
    need(re.fullmatch(r"[0-9a-f]{16}", nonce) is not None, "invalid campaign nonce")
    need(report["stub_diagnostics"] == {"enabled": True, "environment": {"STUB_VERBOSE": "1"}, "hits": []},
         "stub logging was not explicitly enabled and empty")
    streams, receipts = read_commands(root, report["commands"], EXITS)
    commands = {row["label"]: row for row in report["commands"]}
    launcher = INSTALLATION + "/bin/darling"
    inputs = {"macho-known-vector": ("macho", ["foobar" if independent else "hello"]),
              "macho-nonce": ("macho", [nonce]), "macho-boundary-64": ("macho", ["a" * 64]),
              "macho-reject-65": ("macho", ["a" * 65]), "macho-invalid": ("macho", []),
              "foundation-invalid": ("foundation", []), "gui-invalid": ("gui", []),
              "foundation": ("foundation", [nonce]), "gui": ("gui", [nonce])}
    for label, (name, arguments) in inputs.items():
        need(commands[label]["argv"] == [launcher, "exec", INSTALLATION + "/" + PROBES + "p003_" + name] + arguments,
             f"{label}: actual invocation differs from the required input")
    calculations = {}
    need(fnv32("hello") == "4f9f2cab" and fnv32("foobar") == "bf9cf968"
         and fnv32("a") == "e40c292c", "reviewer FNV fixed-vector failure")
    for label in ("macho-known-vector", "macho-nonce", "macho-boundary-64"):
        value = inputs[label][1][0]
        expected = f"P003_MACHO nonce={value} hash={fnv32(value)}"
        need(markers(streams[label]["stdout"]) == [expected], f"{label}: independently computed FNV differs")
        calculations[label] = {"input": value, "length": len(value), "fnv1a32": fnv32(value)}
    for label in ("macho-reject-65", "macho-invalid", "foundation-invalid", "gui-invalid"):
        probe = inputs[label][0]
        reason = "challenge" if probe == "gui" else "arguments"
        need(markers(streams[label]["stdout"]) == [] and markers(streams[label]["stderr"]) ==
             [f"P003_{probe.upper()}_ERROR invalid {reason}"], f"{label}: missing explicit invalid-input rejection")
    foundation = [f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil",
                  f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0"]
    need(markers(streams["foundation"]["stdout"]) == foundation, "Foundation objects or live transaction deltas differ")
    frameworks = [f"/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}" for name, version in OWNERS]
    need(markers(streams["gui"]["stdout"]) == ["P003_IMAGE " + path for path in frameworks] +
         [f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1"],
         "GUI acknowledgement or canonical framework images differ")
    for label, expected in EXITS.items():
        if expected == 0:
            need(not markers(streams[label]["stderr"]), f"{label}: positive command emitted a probe error")
    images = inspect_images(root, report)
    focus = commands["gui-focus"]["argv"]
    need(len(focus) == 4 and focus[:3] == ["xdotool", "windowfocus", "--sync"]
         and re.fullmatch(r"[1-9][0-9]*", focus[3]) is not None, "invalid external window focus command")
    window = focus[3]
    width, height = images["before"]["width"], images["before"]["height"]
    required = {"gui-move": ["xdotool", "mousemove", "--window", window, str(width // 2), str(height // 2)],
                "gui-click": ["xdotool", "click", "1"],
                "gui-type": ["xdotool", "type", "--clearmodifiers", "--delay", "45" if independent else "35", nonce],
                "gui-acknowledge": ["xdotool", "key", "Return"], "shutdown": [launcher, "shutdown"]}
    for label, arguments in required.items():
        need(commands[label]["argv"] == arguments, f"{label}: required external command differs")
    sequence = [row["label"] for row in report["commands"]]
    positions = [sequence.index(label) for label in ("gui-focus", "gui-move", "gui-click", "gui-type", "gui-acknowledge", "shutdown")]
    need(positions == sorted(positions), "external input and shutdown order differs")
    lifecycle = report["lifecycle"]
    need(lifecycle["server_exited"] is True and lifecycle["mount_namespace_released"] is True
         and lifecycle["namespace_holders_after"] == [], "server or mount namespace retained after shutdown")
    identity = lifecycle["server_before"]
    need(type(identity["pid"]) is int and identity["pid"] > 1 and type(identity["starttime"]) is int
         and identity["starttime"] > 0 and identity["state"] not in ("Z", "X")
         and re.fullmatch(r"mnt:\[[0-9]+\]", identity["mount_namespace"]) is not None,
         "invalid pre-shutdown live server identity")
    need(report["controlled_home"] == report["prefix"] + ".home", "unexpected controlled HOME")
    need("Setting up a new Darling prefix at " + report["prefix"] in streams["macho-known-vector"]["stderr"],
         "raw startup stream lacks fresh-prefix creation")
    startup = None
    if not independent:
        reference = report["startup_processes"]
        trace = json.loads(bound(root, reference))
        need(trace["schema"] == "darling.p003.startup-processes.v1"
             and len(trace["samples"]) == reference["sample_count"] > 0, "invalid startup process evidence")
        observed = {sample["init_pid"] for sample in trace["samples"] if sample["init_pid"] is not None}
        need(not observed or observed == {identity["pid"]}, "startup and shutdown server PID differ")
        startup = {"sha256": reference["sha256"], "samples": len(trace["samples"]), "observed_init_pids": sorted(observed)}
    entries = {entry["path"]: entry for entry in manifest["entries"]}
    need(set(report["binaries"]) == {"p003_macho", "p003_foundation", "p003_gui"}, "probe binary set differs")
    for name, binary in report["binaries"].items():
        installed = entries[PROBES + name]
        need(binary["path"] == INSTALLATION + "/" + PROBES + name and installed["kind"] == "file"
             and binary["sha256"] == installed["sha256"] and binary["bytes"] == installed["size"]
             and binary["format"] == "Mach-O 64-bit x86_64 MH_EXECUTE", f"{name}: manifest/probe binding differs")
    extra = review_independent(root, report, window) if independent else {}
    return {"schema": "darling.p003.wave4-offline-runtime-audit.v1", "status": "PASS",
            "review_scope": "one original campaign; offline evidence verification",
            "phase_acceptance": False, "source_commit": commit, "cases_checked": 10,
            "case_names": sorted(names), "report_sha256": sha(report_bytes), "manifest_sha256": sha(manifest_bytes),
            "nonce": nonce, "server_before": identity, "lifecycle": lifecycle,
            "controlled_home": report["controlled_home"], "prefix": report["prefix"],
            "calculations": calculations, "foundation_records": foundation, "frameworks": frameworks,
            "window_id": window, "images": images, "command_receipts": receipts,
            "startup": startup, "binaries": report["binaries"], **extra}


def review_independent(root, report, window):
    rows = report["host_commands"]
    labels = [row["label"] for row in rows]
    need(len(set(labels)) == len(labels) and all(re.fullmatch(
        r"gui-(?:search-(?:wait|ready)|capture-(?:before|after)-[1-9][0-9]*)", label) for label in labels),
        "unexpected or duplicate independent host command")
    need({"gui-search-wait", "gui-search-ready"}.issubset(labels), "missing external window search")
    streams, receipts = read_commands(root, rows, dict.fromkeys(labels, 0))
    commands = {row["label"]: row for row in rows}
    for state, title in (("wait", "WAIT"), ("ready", "READY")):
        label = "gui-search-" + state
        need(commands[label]["argv"] == ["xdotool", "search", "--sync", "--onlyvisible", "--name",
                                        "^P003_" + title + "_" + report["nonce"] + "$"]
             and streams[label]["stdout"].splitlines() == [window], "external window identity or title differs")
    need(report["window_id"] == int(window), "independent recorded window ID differs")
    for state in ("before", "after"):
        item = report["screenshots"][state]
        count = item["capture_attempts"]
        expected = {f"gui-capture-{state}-{attempt}" for attempt in range(1, count + 1)}
        need(expected and {label for label in labels if label.startswith("gui-capture-" + state + "-")} == expected,
             "incomplete independent screenshot command sequence")
        for label in expected:
            argv = commands[label]["argv"]
            need(len(argv) == 6 and argv[:5] == ["xwd", "-silent", "-id", window, "-out"]
                 and Path(argv[5]).name == label + ".xwd", "independent XWD capture argv differs")
        need(item["file"] == f"gui-capture-{state}-{count}.xwd", "selected screenshot was not captured by its command")
    isolation = report["isolation"]
    need(isolation["source_and_build_absent"] is True
         and isolation["forbidden_paths"] == ["/p003/source", "/p003/build"], "source/build absence is not established")
    driver = bound(root, isolation["driver"])
    need(sha(driver) == isolation["driver_sha256"] == report["driver_sha256"] == DRIVER_SHA256,
         "independent driver bytes differ from the reviewed source")
    mountinfo = bound(root, isolation["mountinfo"]).decode("utf-8")
    need(bool(mountinfo.strip()), "empty source/build isolation mount table")
    for line in mountinfo.splitlines():
        fields = line.split()
        need("-" in fields, "invalid mountinfo record")
        separator = fields.index("-")
        need(separator >= 6 and len(fields) == separator + 4
             and fields[0].isdecimal() and fields[1].isdecimal()
             and re.fullmatch(r"[0-9]+:[0-9]+", fields[2]), "invalid mountinfo fields")
        locations = [re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[index])
                     for index in (3, 4, separator + 2)]
        need(locations[0].startswith("/") and locations[1].startswith("/"), "non-absolute mount root/destination")
        allowed_file = locations[1] in ("/p003/review_installed_runtime.py", "/p003/review_package_archive.py")
        for location in locations:
            need(not any(location == path or location.startswith(path + "/") for path in ("/p003/source", "/p003/build")),
                 "source/build location retained in original mountinfo")
            need(allowed_file or ("/MAC-OS-EMULATION/" not in location and not location.endswith("/MAC-OS-EMULATION")),
                 "checkout mount retained in original mountinfo")
    environment = isolation["environment"]
    need(environment["STUB_VERBOSE"] == "1" and environment["DPREFIX"] == report["prefix"]
         and environment["HOME"] == report["controlled_home"], "independent controlled environment differs")
    need(isolation["caller_mount_namespace"] != report["lifecycle"]["server_before"]["mount_namespace"],
         "server retained caller mount namespace")
    stat = bound(root, report["lifecycle"]["server_stat"]).decode("utf-8")
    identity = report["lifecycle"]["server_before"]
    tail = stat.rsplit(") ", 1)
    need(len(tail) == 2 and stat.startswith(str(identity["pid"]) + " (")
         and len(tail[1].split()) >= 20 and int(tail[1].split()[19]) == identity["starttime"],
         "raw /proc stat differs from pre-shutdown server identity")
    for reference in report["evidence"]:
        bound(root, reference)
    return {"host_command_receipts": receipts, "isolation_mountinfo_sha256": sha(mountinfo.encode()),
            "independent_driver_sha256": sha(driver), "server_stat_sha256": sha(stat.encode())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    try:
        result = review(args.report, args.manifest, args.commit)
    except (Rejected, KeyError, TypeError, ValueError, OSError, struct.error, zlib.error) as error:
        result = {"schema": "darling.p003.wave4-offline-runtime-audit.v1", "status": "FAIL",
                  "phase_acceptance": False, "reason": f"{type(error).__name__}: {error}"}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
