#!/usr/bin/env python3
"""P003 installed-runtime qualification; absence, timeouts and errors fail closed.

The caller supplies a genuine X11 display (normally Xvfb). Input originates in
the host X server via xdotool/XTest, not by calling a probe's event handler.
Two raw XWD snapshots independently prove the displayed colors changed only
after the nonce input. No Apple or Logic Pro binaries are used.
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
import time
import zlib


FRAMEWORKS = {"AppKit": "C", "Foundation": "C", "CoreGraphics": "A",
              "CoreText": "A", "ImageIO": "A", "QuartzCore": "A", "AudioToolbox": "A"}


class ProbeFailure(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fnv1a(text: str) -> int:
    value = 2166136261
    for byte in text.encode("ascii"):
        value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
    return value


def assert_record(stdout: str, expected: str) -> None:
    records = [line for line in stdout.splitlines() if line.startswith(expected.split(" ")[0])]
    if records != [expected]:
        raise ProbeFailure(f"missing, duplicated or incorrect output record: expected {expected!r}; actual {records!r}")


def stub_diagnostics(text: str) -> list[dict]:
    """Find the actual placeholder diagnostics used by the pinned frameworks.

    Scan runtime output only, after the persistent server has stopped. Compiler
    source paths and comments mentioning stubs are not execution evidence.
    """
    # libxpc's pinned xpc_stub() emits lower-case `libxpc stub called:`.
    # This is a reached placeholder just as surely as an upper-case STUB.
    pattern = re.compile(r"\bSTUB(?::|\s)|\blibxpc stub called:|\bunimplemented in\b|only defined for abstract class\. Define")
    return [{"line": number, "text": line} for number, line in enumerate(text.splitlines(), 1)
            if pattern.search(line)]


def assert_macho(path: Path) -> dict:
    with path.open("rb") as stream:
        header = stream.read(32)
    if len(header) != 32:
        raise ProbeFailure(f"truncated Mach-O executable: {path}")
    magic, cpu, _subtype, filetype = struct.unpack("<IIII", header[:16])
    if magic != 0xFEEDFACF or cpu != 0x01000007 or filetype != 2:
        raise ProbeFailure(f"expected thin x86_64 Mach-O executable: {path}")
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size,
            "format": "Mach-O 64-bit x86_64 MH_EXECUTE"}


def xwd_sample(data: bytes) -> dict:
    """Read XWD version 7 ZPixmap TrueColor without an image dependency.

    XWD integers are network order. Pixel byte order is declared in the header;
    24/32-bit TrueColor masks are decoded rather than assuming RGB byte order.
    """
    if len(data) < 100:
        raise ProbeFailure("truncated XWD header")
    header = struct.unpack(">25I", data[:100])
    (header_size, version, pixmap_format, depth, width, height, xoffset,
     byte_order, _unit, _bitorder, _pad, bits, stride, visual, red, green,
     blue, _rgb, _entries, ncolors, *_rest) = header
    if (version != 7 or pixmap_format != 2 or depth != 24 or bits not in (24, 32)
            or visual != 4 or byte_order not in (0, 1) or xoffset != 0
            or not 200 <= width <= 1024 or not 120 <= height <= 768
            or header_size < 100 or header_size > len(data)
            or not (red and green and blue) or red & green or red & blue or green & blue
            or stride < width * (bits // 8) or stride > width * 8):
        raise ProbeFailure("unsupported or invalid XWD geometry/format")
    offset = header_size + ncolors * 12
    if len(data) != offset + height * stride:
        raise ProbeFailure("truncated or trailing XWD payload")

    def channel(pixel: int, mask: int) -> int:
        shift = (mask & -mask).bit_length() - 1
        maximum = mask >> shift
        if maximum & (maximum + 1):
            raise ProbeFailure("non-contiguous XWD color mask")
        return ((pixel & mask) >> shift) * 255 // maximum

    samples = []
    for x in (width // 4, width * 3 // 4):
        position = offset + (height // 2) * stride + x * (bits // 8)
        pixel = int.from_bytes(data[position:position + bits // 8], "little" if byte_order == 0 else "big")
        samples.append([channel(pixel, red), channel(pixel, green), channel(pixel, blue)])
    return {"width": width, "height": height, "depth": depth, "left_rgb": samples[0],
            "right_rgb": samples[1]}


def assert_colors(sample: dict, ready: bool) -> None:
    left, right = sample["left_rgb"], sample["right_rgb"]
    if ready:
        valid = left[1] >= 200 and max(left[0], left[2]) <= 40 and min(right[0], right[1]) >= 200 and right[2] <= 40
    else:
        valid = left[0] >= 200 and max(left[1], left[2]) <= 40 and right[2] >= 200 and max(right[0], right[1]) <= 40
    if not valid:
        raise ProbeFailure(f"rendered pixel assertions failed (ready={ready}): {sample}")


def xwd_png(data: bytes) -> bytes:
    """Lossless viewable copy; raw XWD remains the primary screenshot evidence."""
    sample = xwd_sample(data)
    header = struct.unpack(">25I", data[:100])
    offset, byte_order, bits, stride = header[0] + header[19] * 12, header[7], header[11], header[12]
    masks = header[14:17]
    shifts = [(mask & -mask).bit_length() - 1 for mask in masks]
    width, height = sample["width"], sample["height"]
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG filter None
        for x in range(width):
            position = offset + y * stride + x * (bits // 8)
            pixel = int.from_bytes(data[position:position + bits // 8], "little" if byte_order == 0 else "big")
            for mask, shift in zip(masks, shifts):
                rows.append(((pixel & mask) >> shift) * 255 // (mask >> shift))

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def assert_images(stdout: str) -> None:
    actual = [line for line in stdout.splitlines() if line.startswith("P003_IMAGE ")]
    expected = [f"P003_IMAGE /System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
                for name, version in FRAMEWORKS.items()]
    if sorted(actual) != sorted(expected):
        raise ProbeFailure(f"loaded framework paths differ: {actual!r}")


def process_identity(pid: int, proc_root: Path = Path("/proc")) -> dict | None:
    try:
        directory = proc_root / str(pid)
        text = (directory / "stat").read_text()
        fields = text[text.rindex(")") + 2:].split()
        return {"pid": pid, "starttime": int(fields[19]), "state": fields[0],
                "mount_namespace": os.readlink(directory / "ns/mnt")}
    except (FileNotFoundError, ProcessLookupError):
        return None
    except (IndexError, ValueError) as error:
        raise ProbeFailure(f"Invalid process identity for PID {pid}") from error


def namespace_users(namespace: str, proc_root: Path = Path("/proc")) -> list[int]:
    users = []
    for directory in proc_root.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            if os.readlink(directory / "ns/mnt") == namespace:
                users.append(int(directory.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return sorted(users)


def startup_snapshot(prefix: Path, launcher_pid: int, proc_root: Path = Path("/proc")) -> dict:
    """Observe the real process tree while launchd starts, without changing it.

    A missing shellspawn socket otherwise leaves only a 15-second timeout
    message. Capture the native init/launchd descendants *before* shutdown
    reaps them. This is diagnostic evidence, never a substitute for a probe.
    """
    pidfile = prefix / ".init.pid"
    init_pid = None
    if pidfile.is_file() and not pidfile.is_symlink():
        try:
            value = pidfile.read_text().strip()
            if value.isdecimal() and int(value) > 1:
                init_pid = int(value)
        except OSError:
            pass
    records = []
    todo = [launcher_pid] + ([init_pid] if init_pid is not None else [])
    seen = set()
    while todo and len(seen) < 64:
        pid = todo.pop(0)
        if pid in seen:
            continue
        seen.add(pid)
        proc = proc_root / str(pid)
        try:
            status = {}
            for line in (proc / "status").read_text().splitlines():
                if line.startswith(("Name:", "State:", "PPid:", "NSpid:", "Uid:", "Gid:", "Threads:")):
                    name, value = line.split(":", 1)
                    status[name] = value.strip()
            command = (proc / "cmdline").read_bytes()[:512].replace(b"\x00", b" ").decode("utf-8", "replace").strip()
            children = [int(value) for value in (proc / "task" / str(pid) / "children").read_text().split()
                        if value.isdecimal()]
            todo.extend(children[:64])
            try:
                executable = os.readlink(proc / "exe")
            except OSError:
                executable = None
            records.append({"pid": pid, "status": status, "cmdline": command,
                            "exe": executable, "children": children[:64]})
        except (OSError, ValueError):
            records.append({"pid": pid, "vanished_or_inaccessible": True})
    return {"launcher_pid": launcher_pid, "init_pid": init_pid,
            "shellspawn_socket": (prefix / "var/run/shellspawn.sock").is_socket(),
            "processes": records}


class Campaign:
    def __init__(self, installation: Path, output: Path, prefix: Path):
        self.installation, self.output, self.prefix = installation, output, prefix
        self.darling = installation / "bin/darling"
        self.records: list[dict] = []
        self.started = False
        self.lifecycle = None
        self.startup_trace = None
        self.home = prefix.with_name(prefix.name + ".home")
        if self.home.exists() or self.home.is_symlink():
            raise ProbeFailure("controlled runtime HOME must be absent")
        self.home.mkdir(parents=True)
        # Never pass account secrets, LD_PRELOAD or DYLD search overrides into
        # qualification. The display and host command path are intentional.
        self.env = {key: os.environ[key] for key in ("PATH", "DISPLAY", "XAUTHORITY", "LANG", "LC_ALL") if key in os.environ}
        self.env["DPREFIX"] = str(prefix)
        self.env["HOME"] = str(self.home)
        self.env["LC_ALL"] = "C"
        self.env["STUB_VERBOSE"] = "1"

    def command(self, label: str, argv: list[str], timeout: int = 40, expected: int = 0) -> str:
        started = time.monotonic()
        timed_out = False
        paths = [self.output / f"{label}.stdout.log", self.output / f"{label}.stderr.log"]
        # The persistent runtime server inherits descriptors. Regular files
        # avoid waiting for a daemon's pipe EOF after the launcher has exited.
        with paths[0].open("wb") as stdout, paths[1].open("wb") as stderr:
            process = subprocess.Popen(argv, env=self.env, stdin=subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, start_new_session=True)
            startup_samples = []
            try:
                if label == "macho-known-vector":
                    deadline = time.monotonic() + timeout
                    while True:
                        startup_samples.append({"elapsed_ms": round((time.monotonic() - started) * 1000),
                                                **startup_snapshot(self.prefix, process.pid)})
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(argv, timeout)
                        try:
                            code = process.wait(timeout=min(0.5, remaining))
                            break
                        except subprocess.TimeoutExpired:
                            continue
                else:
                    code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                code = None
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
            finally:
                if startup_samples:
                    trace_file = self.output / "startup-processes.json"
                    trace_file.write_text(json.dumps({"schema": "darling.p003.startup-processes.v1",
                        "samples": startup_samples}, indent=2, sort_keys=True) + "\n")
                    self.startup_trace = {"file": trace_file.name, "sha256": sha256(trace_file),
                                          "sample_count": len(startup_samples)}
        record = {"label": label, "argv": argv, "exit_code": code, "expected_exit_code": expected,
                  "timed_out": timed_out, "seconds": round(time.monotonic() - started, 3),
                  "stdout": {"file": paths[0].name, "sha256": sha256(paths[0])},
                  "stderr": {"file": paths[1].name, "sha256": sha256(paths[1])}}
        self.records.append(record)
        if timed_out or code != expected:
            raise ProbeFailure(f"{label}: expected exit {expected}; actual {code}; timeout={timed_out}")
        return paths[0].read_text(encoding="utf-8", errors="strict")

    def probe(self, name: str, args: list[str], label: str, expected: int = 0) -> str:
        self.started = True
        path = self.installation / "libexec/darling/usr/libexec/p003" / name
        return self.command(label, [str(self.darling), "exec", str(path), *args], expected=expected)

    def window(self, title: str, process: subprocess.Popen) -> str:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise ProbeFailure(f"GUI exited before visible window {title}")
            result = subprocess.run(["xdotool", "search", "--onlyvisible", "--name", f"^{re.escape(title)}$"],
                                    env=self.env, capture_output=True, timeout=3)
            if result.returncode == 0:
                windows = result.stdout.decode("ascii").splitlines()
                if len(windows) != 1 or not re.fullmatch(r"[1-9][0-9]*", windows[0]):
                    raise ProbeFailure(f"ambiguous visible window selection: {windows!r}")
                return windows[0]
            if result.returncode != 1:
                raise ProbeFailure(f"xdotool window search failed: {result.returncode}")
            time.sleep(0.1)
        raise ProbeFailure(f"visible GUI window timeout: {title}")

    def screenshot(self, label: str, window: str, ready: bool) -> dict:
        path = self.output / f"{label}.xwd"
        # The title is set just before a queued draw. A fixed, bounded deadline
        # accepts actual rendered pixels, never the title alone.
        deadline = time.monotonic() + 5
        while True:
            completed = subprocess.run(["xwd", "-silent", "-id", window, "-out", str(path)],
                                       env=self.env, capture_output=True, timeout=5)
            if completed.returncode != 0:
                raise ProbeFailure(f"xwd failed: {completed.stderr.decode(errors='replace')}")
            sample = xwd_sample(path.read_bytes())
            try:
                assert_colors(sample, ready)
                png_path = self.output / f"{label}.png"
                png_path.write_bytes(xwd_png(path.read_bytes()))
                return {"file": path.name, "sha256": sha256(path), "pixels": sample,
                        "png": {"file": png_path.name, "sha256": sha256(png_path)},
                        "asserted_state": "green/yellow after input" if ready else "red/blue before input"}
            except ProbeFailure:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.1)

    def gui(self, nonce: str) -> dict:
        argv = [str(self.darling), "exec", str(self.installation / "libexec/darling/usr/libexec/p003/p003_gui"), nonce]
        stdout_path, stderr_path = self.output / "gui.stdout.log", self.output / "gui.stderr.log"
        shots = {}
        started = time.monotonic()
        with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
            process = subprocess.Popen(argv, env=self.env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True)
            try:
                window = self.window("P003_WAIT_" + nonce, process)
                shots["before"] = self.screenshot("gui-before", window, False)
                self.command("gui-focus", ["xdotool", "windowfocus", "--sync", window], timeout=5)
                pixels = shots["before"]["pixels"]
                self.command("gui-move", ["xdotool", "mousemove", "--window", window,
                             str(pixels["width"] // 2), str(pixels["height"] // 2)], timeout=5)
                self.command("gui-click", ["xdotool", "click", "1"], timeout=5)
                self.command("gui-type", ["xdotool", "type", "--clearmodifiers", "--delay", "35", nonce], timeout=5)
                ready_window = self.window("P003_READY_" + nonce, process)
                if ready_window != window:
                    raise ProbeFailure("GUI replaced the window instead of handling input")
                shots["after"] = self.screenshot("gui-after", window, True)
                self.command("gui-acknowledge", ["xdotool", "key", "Return"], timeout=5)
                if process.wait(timeout=10) != 0:
                    raise ProbeFailure(f"GUI failed with exit {process.returncode}")
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=3)
                self.records.append({"label": "gui", "argv": argv, "exit_code": process.returncode,
                    "seconds": round(time.monotonic() - started, 3),
                    "stdout": {"file": stdout_path.name, "sha256": sha256(stdout_path)},
                    "stderr": {"file": stderr_path.name, "sha256": sha256(stderr_path)}})
        stdout = stdout_path.read_text()
        assert_images(stdout)
        assert_record(stdout, f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1")
        if "P003_" in stderr_path.read_text():
            raise ProbeFailure("GUI reported a probe error")
        return shots

    def shutdown(self) -> None:
        if self.started:
            pid = int((self.prefix / ".init.pid").read_text().strip())
            if pid <= 1:
                raise ProbeFailure("invalid recorded runtime server PID")
            identity = process_identity(pid)
            if identity is None:
                raise ProbeFailure("runtime server vanished before required shutdown")
            namespace = identity["mount_namespace"]
            if namespace == os.readlink("/proc/self/ns/mnt"):
                raise ProbeFailure("runtime server did not create its required private mount namespace")
            self.command("shutdown", [str(self.darling), "shutdown"], timeout=15)
            # The server's private mounts are invisible in our mountinfo. Wait
            # for the exact server identity and all namespace holders to exit.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                current = process_identity(pid)
                holders = namespace_users(namespace)
                same_server = current is not None and current["starttime"] == identity["starttime"]
                if not same_server and not holders:
                    self.lifecycle = {"server_before": identity, "server_exited": True,
                                      "namespace_holders_after": [], "mount_namespace_released": True}
                    return
                time.sleep(0.1)
            raise ProbeFailure("runtime server or private mount namespace survived shutdown")


def run(args: argparse.Namespace) -> int:
    for path in (args.installation, args.output, args.prefix):
        if not path.is_absolute():
            raise ProbeFailure("installation, output and prefix paths must be absolute")
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": "logic-pro-p003-probes-v1", "status": "FAILED", "passed": False,
              "installation": str(args.installation), "prefix": str(args.prefix),
              "kernel": platform.release(), "machine": platform.machine(),
              "source_revision": os.environ.get("P003_SOURCE_REVISION"),
              "oracle": "fixed FNV-1a/32, Foundation object values, X11 pixels and externally injected nonce input"}
    campaign = Campaign(args.installation, args.output, args.prefix)
    errors = []
    cases = []

    def case(name, operation):
        record = {"name": name, "status": "FAILED"}
        cases.append(record)
        value = operation()
        record["status"] = "PASSED"
        return value

    try:
        if args.prefix.exists() and (not args.prefix.is_dir() or any(args.prefix.iterdir())):
            raise ProbeFailure("runtime prefix must be absent or empty")
        if str(args.prefix) in ("/", str(args.installation)):
            raise ProbeFailure("runtime prefix must be separate from installation")
        if not os.environ.get("DISPLAY"):
            raise ProbeFailure("a real X11 DISPLAY is mandatory")
        for name in ("xdotool", "xwd"):
            if shutil.which(name) is None:
                raise ProbeFailure(f"required host command missing: {name}")
        if not campaign.darling.is_file() or not os.access(campaign.darling, os.X_OK):
            raise ProbeFailure("installed Darling launcher missing or not executable")
        if platform.machine() not in ("x86_64", "amd64"):
            raise ProbeFailure("P003 qualified runtime host must be x86_64")
        binaries = {}
        for name in ("p003_macho", "p003_foundation", "p003_gui"):
            path = args.installation / "libexec/darling/usr/libexec/p003" / name
            if not path.resolve().is_relative_to(args.installation.resolve()):
                raise ProbeFailure(f"probe escapes installation: {path}")
            binaries[name] = assert_macho(path)
        report["binaries"] = binaries
        nonce = secrets.token_hex(8)
        report["nonce"] = nonce
        # Known standard vector checks the independent host calculation too.
        if fnv1a("hello") != 0x4F9F2CAB:
            raise ProbeFailure("host FNV reference failed its fixed vector")
        def computation(value, label):
            stdout = campaign.probe("p003_macho", [value], label)
            assert_record(stdout, f"P003_MACHO nonce={value} hash={fnv1a(value):08x}")

        def rejection(name, arguments, label):
            stdout = campaign.probe("p003_" + name, arguments, label, expected=64)
            stderr = (args.output / f"{label}.stderr.log").read_text()
            expected = "P003_" + name.upper() + "_ERROR invalid " + ("challenge" if name == "gui" else "arguments")
            errors_found = [line for line in stderr.splitlines() if line.startswith("P003_")]
            if errors_found != [expected] or any(line.startswith("P003_") for line in stdout.splitlines()):
                raise ProbeFailure(f"{label}: expected the probe's own argument rejection, got {errors_found!r}")

        case("macho-known-vector", lambda: computation("hello", "macho-known-vector"))
        case("macho-nonce", lambda: computation(nonce, "macho-nonce"))
        case("macho-boundary-64", lambda: computation("a" * 64, "macho-boundary-64"))
        case("macho-reject-65", lambda: rejection("macho", ["a" * 65], "macho-reject-65"))
        for name in ("macho", "foundation", "gui"):
            case(name + "-invalid-arguments", lambda name=name: rejection(name, [], name + "-invalid"))

        def foundation():
            stdout = campaign.probe("p003_foundation", [nonce], "foundation")
            assert_record(stdout, f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil")
            assert_record(stdout, f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0")

        case("foundation-objects", foundation)
        report["screenshots"] = case("gui-event-roundtrip", lambda: campaign.gui(nonce))
    except (ProbeFailure, OSError, ValueError, subprocess.SubprocessError) as error:
        errors.append(str(error))
    finally:
        try:
            if campaign.started:
                case("runtime-shutdown", campaign.shutdown)
        except (ProbeFailure, OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append("shutdown: " + str(error))
        report["commands"] = campaign.records
        if campaign.startup_trace is not None:
            report["startup_processes"] = campaign.startup_trace
        # Persistent server diagnostics may append to its inherited first
        # command logs until shutdown; bind their final, stable bytes now.
        diagnostics = []
        for command in report["commands"]:
            for name in ("stdout", "stderr"):
                path = args.output / command[name]["file"]
                command[name]["sha256"] = sha256(path)
                diagnostics.extend({"command": command["label"], "stream": name,
                                    "file": path.name, **hit}
                                   for hit in stub_diagnostics(path.read_text(errors="replace")))
        report["stub_diagnostics"] = {"enabled": True, "environment": {"STUB_VERBOSE": "1"},
                                      "hits": diagnostics}
        if diagnostics:
            errors.append(f"Reached {len(diagnostics)} generic stub or unimplemented-operation diagnostics; see stub_diagnostics and original command logs")
        report["lifecycle"] = campaign.lifecycle
        report["controlled_home"] = str(campaign.home)
        report["cases"] = cases
        report["errors"] = errors
        report["passed"] = not errors
        report["status"] = "PASSED" if not errors else "FAILED"
        (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "report": str(args.output / "report.json"), "errors": errors}))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
