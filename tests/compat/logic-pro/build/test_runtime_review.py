"""Independent regressions for real runtime startup and shutdown hazards.

These tests reproduce problems at the host/probe boundary. They do not replace
the required installed Darling execution, X11 screenshots, or clean builds.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import signal
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zlib

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "runtime_review_probes", ROOT / "tools/compat/logic-pro/run_build_probes.py")
probes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probes)
INDEPENDENT_SPEC = importlib.util.spec_from_file_location(
    "independent_runtime_review", ROOT / "tools/compat/logic-pro/review_installed_runtime.py")
independent = importlib.util.module_from_spec(INDEPENDENT_SPEC)
INDEPENDENT_SPEC.loader.exec_module(independent)


def fake_process(root, pid, starttime=123456, namespace="mnt:[12345]", name="server with ) brackets"):
    directory = root / str(pid)
    (directory / "ns").mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(starttime)] + ["0"] * 30
    (directory / "stat").write_text(f"{pid} ({name}) " + " ".join(fields) + "\n")
    (directory / "ns/mnt").symlink_to(namespace)
    return directory


class RuntimeBoundaryReview(unittest.TestCase):
    def test_startup_receives_fresh_explicit_home_without_private_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.dict(os.environ, {"HOME": "/unrelated-private-home",
                                              "LD_PRELOAD": "/unrelated-injection",
                                              "API_TOKEN": "dummy-fixture"}, clear=True):
                campaign = probes.Campaign(root / "installation", root, root / "prefix")
            self.assertEqual(campaign.env["HOME"], str(root / "prefix.home"))
            self.assertTrue(campaign.home.is_dir())
            self.assertEqual(list(campaign.home.iterdir()), [])
            self.assertNotIn("LD_PRELOAD", campaign.env)
            self.assertNotIn("API_TOKEN", campaign.env)
            self.assertEqual(campaign.env["STUB_VERBOSE"], "1")

    def test_stub_logging_cannot_be_disabled_by_inherited_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.dict(os.environ, {"STUB_VERBOSE": "0"}, clear=True):
                campaign = probes.Campaign(root / "installation", root, root / "prefix")
            self.assertEqual(campaign.env["STUB_VERBOSE"], "1")

    def test_real_framework_placeholder_diagnostics_preserve_original_lines(self):
        # Forms emitted by the pinned libcache, LaunchServices, CoreAudio,
        # AudioToolbox, CoreGraphics, ImageIO, and Foundation NSRaise helpers.
        messages = [
            "STUB: cache_create called",
            "STUB: LSRegisterURL",
            "CoreAudio STUB: AudioObjectGetPropertyData called",
            "AudioToolbox STUB: AudioQueueNewOutput called",
            "STUB CGContextDrawLinearGradient",
            "STUB CGImageSourceRef CGImageSourceCreateIncremental(CFDictionaryRef)",
            "libxpc stub called: void xpc_transaction_begin(void)",
            "libxpc stub called: void xpc_transaction_end(void)",
            "2026-11-01 12:00:00 P003[123] -[NSView example] unimplemented in NSView.m at 10",
            "2026-11-01 12:00:00 P003[123] ExampleFunction() unimplemented in example.m at 20",
            "-example only defined for abstract class. Define -[Example example] in example.m:30!",
        ]
        output = "P003 initialization started\n" + "\n".join(messages) + "\nP003 initialization done\n"
        self.assertEqual(probes.stub_diagnostics(output), [
            {"line": number, "text": message}
            for number, message in enumerate(messages, 2)
        ])

    def test_success_records_and_environment_metadata_are_not_stub_calls(self):
        output = ("STUB_VERBOSE=1\n"
                  "P003_MACHO nonce=0123456789abcdef hash=87bc333d\n"
                  "P003_FOUNDATION count=3 answer=42 missing=nil\n"
                  "P003_IMAGE name=AppKit path=/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit\n"
                  "P003_GUI clicks=1 draws=3 visible=1 ready=1 acknowledged=1\n")
        self.assertEqual(probes.stub_diagnostics(output), [])

    def test_old_controlled_home_cannot_supply_reinstall_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "prefix.home"
            home.mkdir()
            (home / "previous-library").write_text("stale dependency")
            with self.assertRaises(probes.ProbeFailure):
                probes.Campaign(root / "installation", root, root / "prefix")

    def test_process_identity_parses_kernel_comm_with_spaces_and_parentheses(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            fake_process(proc, 123)
            self.assertEqual(probes.process_identity(123, proc),
                             {"pid": 123, "starttime": 123456, "state": "S",
                              "mount_namespace": "mnt:[12345]"})
            self.assertIsNone(probes.process_identity(124, proc))

    def test_namespace_holders_are_checked_outside_caller_mountinfo(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            fake_process(proc, 9, namespace="mnt:[caller]")
            fake_process(proc, 33)
            fake_process(proc, 17)
            (proc / "self").mkdir()
            (proc / "200").mkdir()  # process vanished during the enumeration
            self.assertEqual(probes.namespace_users("mnt:[12345]", proc), [17, 33])

    def test_malformed_process_identity_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            target = fake_process(proc, 123)
            (target / "stat").write_text("incomplete\n")
            with self.assertRaises(probes.ProbeFailure):
                probes.process_identity(123, proc)

    def test_persistent_daemon_descriptors_do_not_timeout_completed_command(self):
        # Darling starts a persistent server inheriting standard descriptors.
        # communicate() with pipes waits for that daemon's EOF even when the
        # actual launcher has already returned. A regular evidence file does
        # not have that accidental lifetime dependency.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child_file = root / "daemon.pid"
            script = root / "daemon_fixture.py"
            script.write_text(
                "import os, pathlib, time\n"
                "pid = os.fork()\n"
                "if pid == 0:\n"
                "    time.sleep(5)\n"
                "    os._exit(0)\n"
                f"pathlib.Path({str(child_file)!r}).write_text(str(pid))\n"
                "print('launcher finished', flush=True)\n")
            campaign = probes.Campaign(root / "installation", root, root / "prefix")
            try:
                result = campaign.command("persistent-descriptor", [sys.executable, str(script)], timeout=1)
                self.assertEqual(result, "launcher finished\n")
                self.assertEqual(campaign.records[-1]["exit_code"], 0)
                self.assertFalse(campaign.records[-1]["timed_out"])
            finally:
                if child_file.exists():
                    try:
                        os.kill(int(child_file.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_shutdown_rejects_surviving_private_namespace_holder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / "prefix"
            prefix.mkdir()
            (prefix / ".init.pid").write_text("123\n")
            campaign = probes.Campaign(root / "installation", root, prefix)
            campaign.started = True
            identity = {"pid": 123, "starttime": 999, "state": "S", "mount_namespace": "mnt:[private]"}
            with mock.patch.object(campaign, "command", return_value=""), \
                 mock.patch.object(probes, "process_identity", side_effect=[identity, None]), \
                 mock.patch.object(probes, "namespace_users", return_value=[456]), \
                 mock.patch.object(probes.os, "readlink", return_value="mnt:[caller]"), \
                 mock.patch.object(probes.time, "monotonic", side_effect=[0, 0, 11]), \
                 mock.patch.object(probes.time, "sleep"):
                with self.assertRaisesRegex(probes.ProbeFailure, "survived shutdown"):
                    campaign.shutdown()
            self.assertIsNone(campaign.lifecycle)

    def test_shutdown_requires_server_exit_and_no_namespace_holders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / "prefix"
            prefix.mkdir()
            (prefix / ".init.pid").write_text("123\n")
            campaign = probes.Campaign(root / "installation", root, prefix)
            campaign.started = True
            identity = {"pid": 123, "starttime": 999, "state": "S", "mount_namespace": "mnt:[private]"}
            with mock.patch.object(campaign, "command", return_value=""), \
                 mock.patch.object(probes, "process_identity", side_effect=[identity, None]), \
                 mock.patch.object(probes, "namespace_users", return_value=[]), \
                 mock.patch.object(probes.os, "readlink", return_value="mnt:[caller]"):
                campaign.shutdown()
            self.assertTrue(campaign.lifecycle["server_exited"])
            self.assertTrue(campaign.lifecycle["mount_namespace_released"])
            self.assertEqual(campaign.lifecycle["namespace_holders_after"], [])


class IndependentRuntimeDriverReview(unittest.TestCase):
    def test_pixel_layouts_png_bytes_and_noncentral_patch_corruption(self):
        width, height = 400, 240
        name = b"independent-XWD-fixture\0"
        for ready in (False, True):
            colors = (0x00FF00, 0xFFFF00) if ready else (0xFF0000, 0x0000FF)
            expected_left = [0, 255, 0] if ready else [255, 0, 0]
            expected_right = [255, 255, 0] if ready else [0, 0, 255]
            expected_row = bytes(expected_left) * (width // 2) + bytes(expected_right) * (width // 2)
            for bits, depth, order in ((24, 24, 0), (24, 24, 1), (32, 24, 0), (32, 32, 1)):
                with self.subTest(ready=ready, bits=bits, depth=depth, byte_order=order):
                    header = [100 + len(name), 7, 2, depth, width, height, 0, order,
                              32, order, 32, bits, width * (bits // 8), 4,
                              0xFF0000, 0x00FF00, 0x0000FF, 8, 256, 0,
                              width, height, 0, 0, 0]
                    row = b"".join(color.to_bytes(bits // 8, "little" if order == 0 else "big")
                                   * (width // 2) for color in colors)
                    raw = struct.pack("!25I", *header) + name + row * height
                    samples, rgb = independent.decode_xwd(raw)
                    self.assertEqual(samples["left_rgb"], expected_left)
                    self.assertEqual(samples["right_rgb"], expected_right)
                    self.assertEqual(rgb, expected_row * height)
                    patches = independent.inspect_color_patches(samples, rgb, ready)
                    self.assertEqual(patches["maximum_channel_error"], [0, 0])
                    png = independent.encode_png(samples, rgb)
                    self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
                    cursor, chunks = 8, []
                    while cursor < len(png):
                        size = int.from_bytes(png[cursor:cursor + 4], "big")
                        kind = png[cursor + 4:cursor + 8]
                        payload = png[cursor + 8:cursor + 8 + size]
                        crc = int.from_bytes(png[cursor + 8 + size:cursor + 12 + size], "big")
                        self.assertEqual(crc, zlib.crc32(kind + payload) & 0xFFFFFFFF)
                        chunks.append((kind, payload))
                        cursor += size + 12
                    self.assertEqual(cursor, len(png))
                    self.assertEqual([kind for kind, _ in chunks], [b"IHDR", b"IDAT", b"IEND"])
                    self.assertEqual(zlib.decompress(chunks[1][1]), (b"\0" + expected_row) * height)
                    # The center samples remain unchanged: a different pixel
                    # inside the independently checked 5x5 patch is corrupted.
                    damaged = bytearray(rgb)
                    position = 3 * ((height // 2 - 1) * width + width // 4 - 1)
                    damaged[position:position + 3] = b"\0\0\0"
                    with self.assertRaises(independent.ReviewFailure):
                        independent.inspect_color_patches(samples, bytes(damaged), ready)
                    with self.assertRaises(independent.ReviewFailure):
                        independent.decode_xwd(raw[:-1])

    def test_independent_capture_handles_daemon_descriptors_and_kills_timeout(self):
        # Exercise the separate review driver's actual child-process handling.
        # These local Python children are fixtures, not Darling acceptance.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            driver = independent.InstalledRuntimeReview(SimpleNamespace(
                installation=root / "installation", output=root,
                prefix=root / "prefix", commit="a" * 40))
            child_file = root / "daemon.pid"
            code = ("import os, pathlib, time\n"
                    "pid = os.fork()\n"
                    "if pid == 0:\n"
                    "    time.sleep(5)\n"
                    "    os._exit(0)\n"
                    f"pathlib.Path({str(child_file)!r}).write_text(str(pid))\n"
                    "print('independent launcher finished', flush=True)\n")
            try:
                self.assertEqual(driver.command("descriptor-fixture", [sys.executable, "-c", code], timeout=1),
                                 "independent launcher finished\n")
                self.assertEqual(driver.report["commands"][-1]["exit_code"], 0)
                self.assertFalse(driver.report["commands"][-1]["timed_out"])
            finally:
                if child_file.exists():
                    try:
                        os.kill(int(child_file.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            with self.assertRaises(independent.ReviewFailure):
                driver.command("timeout-fixture", [sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.1)
            command = driver.report["commands"][-1]
            self.assertTrue(command["timed_out"])
            self.assertEqual(command["exit_code"], -signal.SIGKILL)
            self.assertEqual(command["expected_exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
