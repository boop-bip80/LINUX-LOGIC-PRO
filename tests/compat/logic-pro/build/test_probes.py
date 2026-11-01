"""Adversarial checks for P003 evidence parsing, not substitute runtime proof."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location("run_build_probes", ROOT / "tools/compat/logic-pro/run_build_probes.py")
probes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probes)


def make_xwd(ready=False, byte_order=0, bits=32):
    width, height = 200, 120
    stride = width * (bits // 8)
    header = [100, 7, 2, 24, width, height, 0, byte_order, 32, 0, 32, bits,
              stride, 4, 0xff0000, 0xff00, 0xff, 8, 256, 0, width, height, 0, 0, 0]
    left, right = (0x00ff00, 0xffff00) if ready else (0xff0000, 0x0000ff)
    order = "little" if byte_order == 0 else "big"
    row = left.to_bytes(bits // 8, order) * (width // 2) + right.to_bytes(bits // 8, order) * (width // 2)
    return struct.pack(">25I", *header) + row * height


class EvidenceTests(unittest.TestCase):
    def test_fnv_reference_vectors(self):
        self.assertEqual(probes.fnv1a(""), 0x811c9dc5)
        self.assertEqual(probes.fnv1a("a"), 0xe40c292c)
        self.assertEqual(probes.fnv1a("hello"), 0x4f9f2cab)

    def test_exact_output_required(self):
        probes.assert_record("warning\nP003_MACHO nonce=hello hash=4f9f2cab\n", "P003_MACHO nonce=hello hash=4f9f2cab")
        for output in ("", "P003_MACHO nonce=hello hash=00000000\n", "P003_MACHO nonce=old hash=4f9f2cab\n"):
            with self.assertRaises(probes.ProbeFailure):
                probes.assert_record(output, "P003_MACHO nonce=hello hash=4f9f2cab")

    def test_duplicate_success_not_accepted(self):
        with self.assertRaises(probes.ProbeFailure):
            probes.assert_record("P003_MACHO ok\nP003_MACHO ok\n", "P003_MACHO ok")

    def test_missing_framework_image(self):
        with self.assertRaises(probes.ProbeFailure):
            probes.assert_images("P003_IMAGE /System/Library/Frameworks/AppKit.framework/Versions/C/AppKit\n")

    def test_framework_image_paths(self):
        lines = [f"P003_IMAGE /System/Library/Frameworks/{name}.framework/Versions/{version}/{name}" for name, version in probes.FRAMEWORKS.items()]
        probes.assert_images("\n".join(lines))
        for bad in (lines + [lines[0]], [line.replace("/System/", "/build/dev-stubs/System/") for line in lines]):
            with self.assertRaises(probes.ProbeFailure):
                probes.assert_images("\n".join(bad))

    def test_xwd_little_and_big_endian_pixels(self):
        for order in (0, 1):
            for bits in (24, 32):
                for ready in (False, True):
                    probes.assert_colors(probes.xwd_sample(make_xwd(ready, order, bits)), ready)

    def test_wrong_state_does_not_pass_pixels(self):
        for ready in (False, True):
            with self.assertRaises(probes.ProbeFailure):
                probes.assert_colors(probes.xwd_sample(make_xwd(ready)), not ready)

    def test_blank_window_does_not_pass(self):
        sample = probes.xwd_sample(make_xwd())
        sample["left_rgb"] = sample["right_rgb"] = [0, 0, 0]
        with self.assertRaises(probes.ProbeFailure):
            probes.assert_colors(sample, False)

    def test_truncated_and_trailing_xwd_rejected(self):
        good = make_xwd()
        for bad in (b"", good[:99], good[:-1], good + b"extra"):
            with self.assertRaises(probes.ProbeFailure):
                probes.xwd_sample(bad)

    def test_bad_xwd_metadata_rejected(self):
        good = make_xwd()
        for index, value in ((0, 1), (1, 8), (2, 1), (3, 8), (4, 0), (6, 1),
                             (7, 9), (11, 8), (12, 1), (13, 3), (14, 0), (15, 0xff0000), (19, 100000)):
            bad = bytearray(good)
            bad[index * 4:index * 4 + 4] = struct.pack(">I", value)
            with self.assertRaises(probes.ProbeFailure, msg=f"XWD header field {index}"):
                probes.xwd_sample(bytes(bad))

    def test_png_copy_signature(self):
        png = probes.xwd_png(make_xwd())
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (200, 120))

    def test_elf_or_foreign_macho_not_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe"
            for data in (b"\x7fELF" + b"\0" * 28, b"short", struct.pack("<8I", 0xfeedfacf, 0x0100000c, 0, 2, 0, 0, 0, 0)):
                path.write_bytes(data)
                with self.assertRaises(probes.ProbeFailure):
                    probes.assert_macho(path)
            path.write_bytes(struct.pack("<8I", 0xfeedfacf, 0x01000007, 3, 2, 0, 0, 0, 0))
            self.assertEqual(probes.assert_macho(path)["format"], "Mach-O 64-bit x86_64 MH_EXECUTE")

    def test_missing_display_writes_failure_not_success(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=root / "prefix")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(probes.run(args), 1)
            report = json.loads((args.output / "report.json").read_text())
            self.assertEqual(report["status"], "FAILED")
            self.assertFalse(report["passed"])
            self.assertIn("DISPLAY", report["errors"][0])

    def test_dirty_prefix_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / "prefix"
            prefix.mkdir()
            (prefix / "old-library").write_text("previous installation")
            args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=prefix)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(probes.run(args), 1)
            self.assertIn("absent or empty", json.loads((args.output / "report.json").read_text())["errors"][0])

    def test_command_failure_and_timeout_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = probes.Campaign(root / "installation", root, root / "prefix")
            with self.assertRaises(probes.ProbeFailure):
                campaign.command("failure", ["/bin/sh", "-c", "exit 7"])
            self.assertEqual(campaign.records[-1]["exit_code"], 7)
            with self.assertRaises(probes.ProbeFailure):
                campaign.command("timeout", [sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.05)
            self.assertTrue(campaign.records[-1]["timed_out"])


if __name__ == "__main__":
    unittest.main()
