#!/usr/bin/env python3
"""Independent P003 replay of an already verified installation archive.

Run this copied, standalone reviewer in a fresh privileged container using the
frozen qualification image. Mount the archive, reviewer scripts and evidence
directory only; neither the source checkout nor the build tree may be present.
This program deliberately imports no production verifier or probe runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import struct
import subprocess
import sys
import time
import zlib


class ReviewFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewFailure(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def fnv_reference(value: str) -> int:
    # Independent implementation of the specified FNV-1a/32 recurrence.
    result = 0x811C9DC5
    for character in value:
        result ^= ord(character)
        result = (result * 0x01000193) % (1 << 32)
    return result


def unescape_mount_field(value: str) -> str:
    return re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), value)


def process_snapshot(pid: int) -> dict | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        prefix, separator, tail = raw.rpartition(") ")
        require(bool(separator) and prefix.startswith(f"{pid} ("),
                f"Malformed process identity for PID {pid}")
        fields = tail.split()
        require(len(fields) >= 20, f"Incomplete process identity for PID {pid}")
        return {"pid": pid, "starttime": int(fields[19]), "state": fields[0],
                "mount_namespace": os.readlink(f"/proc/{pid}/ns/mnt")}
    except (FileNotFoundError, ProcessLookupError):
        return None


def mount_namespace_holders(namespace: str) -> list[int]:
    holders = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if os.readlink(entry / "ns/mnt") == namespace:
                holders.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return sorted(holders)


def decode_xwd(data: bytes) -> tuple[dict, bytes]:
    """Decode a real XWD into RGB bytes independently of the production parser."""
    require(len(data) >= 100, "XWD has no complete header")
    header = struct.unpack_from("!25I", data)
    size, version, pixmap, depth, width, height, offset, order = header[:8]
    bits, stride, visual = header[11:14]
    masks = header[14:17]
    colors = header[19]
    require(version == 7 and pixmap == 2 and visual == 4,
            "Screenshot must be XWD v7 ZPixmap TrueColor")
    require(depth in (24, 32) and bits in (24, 32) and bits >= depth
            and order in (0, 1) and offset == 0,
            "Unsupported screenshot pixel layout")
    require(320 <= width <= 1024 and 200 <= height <= 768,
            "Unexpected GUI window dimensions")
    require(100 < size <= len(data) and colors <= 4096,
            "Invalid XWD header or color table length")
    bytes_per_pixel = bits // 8
    require(width * bytes_per_pixel <= stride <= width * 8,
            "Invalid XWD row stride")
    payload_start = size + colors * 12
    require(payload_start + stride * height == len(data),
            "XWD pixel payload has missing or trailing bytes")
    require(all(masks) and not (masks[0] & masks[1] or masks[0] & masks[2]
                               or masks[1] & masks[2]), "Invalid XWD RGB masks")
    channel_specs = []
    for mask in masks:
        require(mask < (1 << bits), "XWD color mask exceeds its pixel")
        shift = 0
        while not (mask >> shift) & 1:
            shift += 1
        maximum = mask >> shift
        require(maximum & (maximum + 1) == 0, "Non-contiguous XWD RGB channel")
        channel_specs.append((mask, shift, maximum))
    rgb = bytearray(width * height * 3)
    byte_order = "little" if order == 0 else "big"
    target = 0
    for row in range(height):
        position = payload_start + row * stride
        for column in range(width):
            pixel = int.from_bytes(data[position:position + bytes_per_pixel], byte_order)
            for mask, shift, maximum in channel_specs:
                rgb[target] = ((pixel & mask) >> shift) * 255 // maximum
                target += 1
            position += bytes_per_pixel

    def at(x: int, y: int) -> list[int]:
        index = (y * width + x) * 3
        return list(rgb[index:index + 3])

    samples = {"width": width, "height": height, "depth": depth,
               "left_rgb": at(width // 4, height // 2),
               "right_rgb": at(3 * width // 4, height // 2)}
    return samples, bytes(rgb)


def inspect_color_patches(samples: dict, rgb: bytes, ready: bool) -> dict:
    targets = ([0, 255, 0], [255, 255, 0]) if ready else ([255, 0, 0], [0, 0, 255])
    width, height = samples["width"], samples["height"]
    deviations = []
    # Check 25 independent displayed pixels in each half, beyond the two
    # center samples recorded for comparison by the aggregate reviewer.
    for center, target in zip((width // 4, 3 * width // 4), targets):
        maximum = 0
        for y in range(height // 2 - 2, height // 2 + 3):
            for x in range(center - 2, center + 3):
                position = 3 * (y * width + x)
                maximum = max(maximum, *(abs(rgb[position + channel] - target[channel])
                                          for channel in range(3)))
        deviations.append(maximum)
    require(max(deviations) <= 40,
            f"Displayed colors do not match ready={ready}: {samples}; errors={deviations}")
    return {"pixels_per_half": 25, "maximum_channel_error": deviations,
            "maximum_allowed_error": 40, "expected_rgb": targets}


def encode_png(samples: dict, rgb: bytes) -> bytes:
    width, height = samples["width"], samples["height"]
    scanlines = b"".join(b"\0" + rgb[y * width * 3:(y + 1) * width * 3]
                         for y in range(height))

    def block(name: bytes, content: bytes) -> bytes:
        return (len(content).to_bytes(4, "big") + name + content
                + (zlib.crc32(name + content) & 0xFFFFFFFF).to_bytes(4, "big"))

    return (b"\x89PNG\r\n\x1a\n"
            + block(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + block(b"IDAT", zlib.compress(scanlines, 9)) + block(b"IEND", b""))


class InstalledRuntimeReview:
    def __init__(self, args: argparse.Namespace):
        self.installation, self.output, self.prefix = args.installation, args.output, args.prefix
        self.home = self.prefix.with_name(self.prefix.name + ".home")
        self.launcher = self.installation / "bin/darling"
        self.probe_root = self.installation / "libexec/darling/usr/libexec/p003"
        self.environment = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
                            "HOME": str(self.home), "DPREFIX": str(self.prefix),
                            "STUB_VERBOSE": "1"}
        for key in ("DISPLAY", "XAUTHORITY"):
            if key in os.environ:
                self.environment[key] = os.environ[key]
        self.launched = False
        self.report = {
            "schema": "darling.p003.independent-runtime.v1", "phase": "P003",
            "reviewer": "independent-installed-runtime", "source_commit": args.commit,
            "status": "FAIL", "passed": False, "errors": [], "cases": [],
            "commands": [], "host_commands": [], "screenshots": {}, "binaries": {},
            "installation": str(self.installation), "prefix": str(self.prefix),
            "controlled_home": str(self.home), "nonce": secrets.token_hex(8),
            "kernel": platform.release(), "machine": platform.machine(),
            "driver_sha256": digest(Path(__file__)), "lifecycle": None,
            "oracle": "independent FNV recurrence, exact Foundation values, external X11 events and 50 displayed pixels per state",
        }

    def reference(self, path: Path) -> dict:
        return {"file": str(path.relative_to(self.output)), "sha256": digest(path),
                "bytes": path.stat().st_size}

    def preflight(self) -> None:
        require(os.getuid() == 0, "Review requires root in the fresh privileged container")
        require(platform.machine() in ("x86_64", "amd64"), "Review requires an x86_64 runtime host")
        require(self.installation == Path("/opt/darling-p003"),
                "Reviewed package must use the frozen /opt/darling-p003 installation prefix")
        forbidden = [Path("/p003/source"), Path("/p003/build")]
        for path in forbidden:
            require(not path.exists() and not path.is_symlink(), f"Source/build path is present: {path}")
        mountinfo = Path("/proc/self/mountinfo").read_text()
        allowed_review_files = {str(Path(__file__).resolve()),
                                str(Path(__file__).resolve().with_name("review_package_archive.py"))}
        for line in mountinfo.splitlines():
            fields = line.split()
            require("-" in fields and len(fields) >= 10, "Cannot interpret mount isolation evidence")
            separator = fields.index("-")
            locations = [unescape_mount_field(fields[index]) for index in (3, 4, separator + 2)]
            mountpoint = Path(locations[1])
            reviewer_file_only = str(mountpoint) in allowed_review_files and mountpoint.is_file()
            if mountpoint.is_dir():
                require(not (mountpoint / ".git").exists() and not (mountpoint / "CMakeCache.txt").exists(),
                        f"Source checkout or build directory is mounted at {mountpoint}")
            for location in locations:
                for path in forbidden:
                    require(location != str(path) and not location.startswith(str(path) + "/"),
                            f"Source/build mount is present: {location}")
                require(reviewer_file_only or ("/MAC-OS-EMULATION/" not in location
                                               and not location.endswith("/MAC-OS-EMULATION")),
                        f"Repository checkout appears in the review mount table: {location}")
        mount_path = self.output / "isolation.mountinfo"
        mount_path.write_text(mountinfo)
        driver_copy = self.output / "reviewer-driver.py"
        shutil.copyfile(Path(__file__), driver_copy)
        self.report["isolation"] = {
            "source_and_build_absent": True, "forbidden_paths": [str(path) for path in forbidden],
            "mountinfo": self.reference(mount_path), "driver": self.reference(driver_copy),
            "driver_sha256": self.report["driver_sha256"],
            "working_directory": str(Path.cwd()), "environment": self.environment,
            "caller_mount_namespace": os.readlink("/proc/self/ns/mnt"),
        }
        for path in (self.prefix, self.home, self.prefix.with_name(self.prefix.name + ".workdir")):
            require(not path.exists() and not path.is_symlink(), f"Fresh runtime path already exists: {path}")
        self.home.mkdir(parents=True)
        require(bool(self.environment.get("DISPLAY")), "A real external X11 DISPLAY is required")
        for executable in ("xdotool", "xwd"):
            require(shutil.which(executable, path=self.environment["PATH"]) is not None,
                    f"Host X11 tool is missing: {executable}")
        require(self.launcher.is_file() and os.access(self.launcher, os.X_OK),
                "Verified installed Darling launcher is missing or not executable")
        for name in ("p003_macho", "p003_foundation", "p003_gui"):
            path = self.probe_root / name
            require(path.resolve().is_relative_to(self.installation), f"Probe escapes installation: {name}")
            require(path.is_file() and os.access(path, os.X_OK), f"Installed probe is missing: {name}")
            with path.open("rb") as binary:
                header = binary.read(32)
            require(len(header) == 32, f"Truncated installed Mach-O probe: {name}")
            magic, cpu, subtype, filetype = struct.unpack_from("<4I", header)
            require((magic, cpu, filetype) == (0xFEEDFACF, 0x01000007, 2),
                    f"Probe is not an x86_64 Mach-O executable: {name}")
            self.report["binaries"][name] = {"path": str(path), "sha256": digest(path),
                                                    "bytes": path.stat().st_size,
                                                    "format": "Mach-O 64-bit x86_64 MH_EXECUTE"}
        require(fnv_reference("foobar") == 0xBF9CF968 and fnv_reference("a") == 0xE40C292C,
                "Independent FNV reference failed published fixed vectors")

    def begin(self, label: str, argv: list[str], expected: int = 0, host: bool = False) -> tuple:
        table = self.report["host_commands" if host else "commands"]
        require(not any(row["label"] == label for row in self.report["commands"] + self.report["host_commands"]),
                f"Duplicate command evidence label: {label}")
        paths = [self.output / f"{label}.{name}.log" for name in ("stdout", "stderr")]
        record = {"label": label, "argv": argv, "expected_exit_code": expected,
                  "exit_code": None, "timed_out": False, "seconds": None,
                  "stdout": {"file": paths[0].name}, "stderr": {"file": paths[1].name}}
        table.append(record)
        started = time.monotonic()
        # A persistent server inherits these descriptors. Files preserve every
        # byte without making launcher completion depend on the server's EOF.
        with paths[0].open("xb") as stdout, paths[1].open("xb") as stderr:
            process = subprocess.Popen(argv, env=self.environment, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
        return process, record, started

    @staticmethod
    def terminate(process: subprocess.Popen, sig: int) -> None:
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass

    def wait(self, job: tuple, timeout: float) -> str:
        process, record, started = job
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            record["timed_out"] = True
            self.terminate(process, signal.SIGKILL)
            process.wait(timeout=5)
        finally:
            record["exit_code"] = process.poll()
            record["seconds"] = round(time.monotonic() - started, 6)
        require(not record["timed_out"] and record["exit_code"] == record["expected_exit_code"],
                f"{record['label']}: exit={record['exit_code']}, expected={record['expected_exit_code']}, timeout={record['timed_out']}")
        return (self.output / record["stdout"]["file"]).read_text(encoding="utf-8")

    def command(self, label: str, argv: list[str], timeout: float = 40,
                expected: int = 0, host: bool = False) -> str:
        return self.wait(self.begin(label, argv, expected, host), timeout)

    def probe(self, binary: str, arguments: list[str], label: str, expected: int = 0) -> str:
        self.launched = True
        return self.command(label, [str(self.launcher), "exec", str(self.probe_root / binary), *arguments],
                            expected=expected)

    def case(self, name: str, operation) -> None:
        record = {"name": name, "status": "FAIL"}
        self.report["cases"].append(record)
        operation()
        record["status"] = "PASS"

    @staticmethod
    def exact_record(output: str, marker: str, expected: str) -> None:
        lines = [line for line in output.splitlines() if line.startswith(marker)]
        require(lines == [expected], f"Wrong or duplicate {marker} record: {lines!r}")

    def computation(self, value: str, label: str, fixed: int | None = None) -> None:
        output = self.probe("p003_macho", [value], label)
        reference = fnv_reference(value) if fixed is None else fixed
        self.exact_record(output, "P003_MACHO", f"P003_MACHO nonce={value} hash={reference:08x}")

    def rejection(self, name: str, arguments: list[str], label: str) -> None:
        output = self.probe("p003_" + name, arguments, label, expected=64)
        errors = (self.output / f"{label}.stderr.log").read_text()
        reason = "challenge" if name == "gui" else "arguments"
        expected = f"P003_{name.upper()}_ERROR invalid {reason}"
        require([line for line in errors.splitlines() if line.startswith("P003_")] == [expected]
                and not any(line.startswith("P003_") for line in output.splitlines()),
                f"{label}: the probe did not perform its own explicit rejection")

    def foundation(self) -> None:
        nonce = self.report["nonce"]
        output = self.probe("p003_foundation", [nonce], "foundation")
        self.exact_record(output, "P003_FOUNDATION",
                          f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil")

    def visible_window(self, title: str, label: str, job: tuple) -> str:
        require(job[0].poll() is None, "GUI exited before its visible window was observed")
        output = self.command(label, ["xdotool", "search", "--sync", "--onlyvisible", "--name",
                                      "^" + re.escape(title) + "$"], timeout=20, host=True)
        windows = output.splitlines()
        require(len(windows) == 1 and re.fullmatch(r"[1-9][0-9]*", windows[0]) is not None,
                f"Ambiguous or invalid external X11 window selection: {windows!r}")
        require(job[0].poll() is None, "GUI exited before the external event round trip")
        return windows[0]

    def capture(self, state: str, window: str) -> dict:
        deadline = time.monotonic() + 5
        attempt = 0
        while True:
            attempt += 1
            label = f"gui-capture-{state}-{attempt}"
            path = self.output / (label + ".xwd")
            self.command(label, ["xwd", "-silent", "-id", window, "-out", str(path)], timeout=5, host=True)
            samples, rgb = decode_xwd(path.read_bytes())
            try:
                patches = inspect_color_patches(samples, rgb, ready=(state == "after"))
            except ReviewFailure:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
                continue
            png = self.output / f"gui-{state}.png"
            png.write_bytes(encode_png(samples, rgb))
            return {**self.reference(path), "pixels": samples, "patches": patches,
                    "png": self.reference(png), "capture_attempts": attempt}

    def gui(self) -> None:
        nonce = self.report["nonce"]
        self.launched = True
        job = self.begin("gui", [str(self.launcher), "exec", str(self.probe_root / "p003_gui"), nonce])
        try:
            window = self.visible_window("P003_WAIT_" + nonce, "gui-search-wait", job)
            before = self.capture("before", window)
            self.report["screenshots"]["before"] = before
            self.command("gui-focus", ["xdotool", "windowfocus", "--sync", window], timeout=5)
            self.command("gui-move", ["xdotool", "mousemove", "--window", window,
                                       str(before["pixels"]["width"] // 2),
                                       str(before["pixels"]["height"] // 2)], timeout=5)
            self.command("gui-click", ["xdotool", "click", "1"], timeout=5)
            self.command("gui-type", ["xdotool", "type", "--clearmodifiers", "--delay", "45", nonce], timeout=5)
            ready_window = self.visible_window("P003_READY_" + nonce, "gui-search-ready", job)
            require(ready_window == window, "GUI replaced the window during the required input round trip")
            self.report["screenshots"]["after"] = self.capture("after", window)
            self.report["window_id"] = int(window)
            self.command("gui-acknowledge", ["xdotool", "key", "Return"], timeout=5)
            output = self.wait(job, timeout=10)
            self.exact_record(output, "P003_GUI",
                              f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1")
            owners = [("AppKit", "C"), ("Foundation", "C"), ("CoreGraphics", "A"),
                      ("CoreText", "A"), ("ImageIO", "A"), ("QuartzCore", "A"), ("AudioToolbox", "A")]
            expected = [f"P003_IMAGE /System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
                        for name, version in owners]
            loaded = [line for line in output.splitlines() if line.startswith("P003_IMAGE")]
            require(sorted(loaded) == sorted(expected), "GUI did not load exactly the seven canonical framework owners")
            errors = (self.output / "gui.stderr.log").read_text()
            require(not any(line.startswith("P003_") for line in errors.splitlines()),
                    "GUI emitted a probe error despite its exit status")
            self.report["loaded_framework_paths"] = [line.removeprefix("P003_IMAGE ") for line in loaded]
        finally:
            process, record, started = job
            if process.poll() is None:
                self.terminate(process, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.terminate(process, signal.SIGKILL)
                    process.wait(timeout=3)
            record["exit_code"] = process.poll()
            record["seconds"] = round(time.monotonic() - started, 6)

    def shutdown(self) -> None:
        pid_text = (self.prefix / ".init.pid").read_text().strip()
        require(pid_text.isdecimal() and int(pid_text) > 1, "Invalid recorded Darling server PID")
        pid = int(pid_text)
        before = process_snapshot(pid)
        require(before is not None, "Darling server disappeared before the required shutdown")
        namespace = before["mount_namespace"]
        require(namespace != os.readlink("/proc/self/ns/mnt"), "Darling did not create its own mount namespace")
        raw_stat = self.output / "server-before.stat"
        raw_stat.write_bytes(Path(f"/proc/{pid}/stat").read_bytes())
        lifecycle = {"server_before": before, "server_stat": self.reference(raw_stat),
                     "server_exited": False, "namespace_holders_after": None,
                     "mount_namespace_released": False}
        self.report["lifecycle"] = lifecycle
        self.command("shutdown", [str(self.launcher), "shutdown"], timeout=15)
        deadline = time.monotonic() + 10
        while True:
            after = process_snapshot(pid)
            holders = mount_namespace_holders(namespace)
            exited = after is None or after["starttime"] != before["starttime"]
            lifecycle.update(server_exited=exited, namespace_holders_after=holders,
                             mount_namespace_released=not holders)
            if exited and not holders:
                return
            require(time.monotonic() < deadline, "Darling server or private mount namespace survived shutdown")
            time.sleep(0.05)

    def execute(self) -> None:
        self.case("macho-known-vector", lambda: self.computation("foobar", "macho-known-vector", 0xBF9CF968))
        self.case("macho-fresh-nonce", lambda: self.computation(self.report["nonce"], "macho-nonce"))
        self.case("macho-boundary-64", lambda: self.computation("a" * 64, "macho-boundary-64"))
        self.case("macho-reject-65", lambda: self.rejection("macho", ["a" * 65], "macho-reject-65"))
        self.case("macho-invalid-arguments", lambda: self.rejection("macho", [], "macho-invalid"))
        self.case("foundation-invalid-arguments", lambda: self.rejection("foundation", [], "foundation-invalid"))
        self.case("gui-invalid-arguments", lambda: self.rejection("gui", [], "gui-invalid"))
        self.case("foundation-fresh-nonce", self.foundation)
        self.case("gui-event-roundtrip", self.gui)

    def finish(self) -> int:
        if self.launched:
            try:
                self.case("runtime-shutdown", self.shutdown)
            except Exception as error:
                self.report["errors"].append(f"shutdown: {type(error).__name__}: {error}")
        diagnostics = []
        patterns = [re.compile(r"\bSTUB(?:\s|:)"), re.compile(r"\bunimplemented in\b"),
                    re.compile(r"only defined for abstract class\. Define")]
        for record in self.report["commands"] + self.report["host_commands"]:
            for stream in ("stdout", "stderr"):
                path = self.output / record[stream]["file"]
                if not path.is_file():
                    self.report["errors"].append(f"Missing original command log: {path.name}")
                    continue
                record[stream] = self.reference(path)
                with path.open(encoding="utf-8", errors="replace") as log:
                    for number, line in enumerate(log, 1):
                        original = line.rstrip("\r\n")
                        if any(pattern.search(original) for pattern in patterns):
                            diagnostics.append({"command": record["label"], "stream": stream,
                                                "file": path.name, "line": number, "text": original})
        self.report["stub_diagnostics"] = {"enabled": True, "environment": {"STUB_VERBOSE": "1"},
                                           "hits": diagnostics}
        if diagnostics:
            self.report["errors"].append(f"Reached {len(diagnostics)} stub or unimplemented-operation diagnostics")
        if not self.report["errors"]:
            if len(self.report["cases"]) != 10 or any(row["status"] != "PASS" for row in self.report["cases"]):
                self.report["errors"].append("Independent replay did not complete all ten critical cases")
        self.report["passed"] = not self.report["errors"]
        self.report["status"] = "PASS" if self.report["passed"] else "FAIL"
        self.report["evidence"] = [self.reference(path) for path in sorted(self.output.iterdir()) if path.is_file()]
        report_path = self.output / "report.json"
        report_path.write_text(json.dumps(self.report, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": self.report["status"], "source_commit": self.report["source_commit"],
                          "report": str(report_path), "errors": self.report["errors"]}, sort_keys=True))
        return 0 if self.report["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installation", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--prefix", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        parser.error("--commit must be the exact 40-character lowercase source SHA")
    paths = (args.installation, args.output, args.prefix)
    for path in paths:
        if not path.is_absolute() or path.resolve() != path or path == Path("/"):
            parser.error("installation, output and prefix must be distinct canonical absolute paths")
    for index, path in enumerate(paths):
        for other in paths[index + 1:]:
            if path.is_relative_to(other) or other.is_relative_to(path):
                parser.error("installation, output and prefix must not overlap")
    try:
        args.output.mkdir(parents=True, exist_ok=False)
        review = InstalledRuntimeReview(args)
    except Exception as error:
        print(f"Independent runtime review setup failed: {error}", file=sys.stderr)
        return 1
    try:
        review.preflight()
        review.execute()
    except Exception as error:
        review.report["errors"].append(f"{type(error).__name__}: {error}")
    return review.finish()


if __name__ == "__main__":
    raise SystemExit(main())
