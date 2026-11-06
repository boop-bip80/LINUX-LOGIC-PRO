"""Adversarial checks for P003 evidence parsing, not substitute runtime proof."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
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
    def test_framework_images_reject_non_framework_competing_basename(self):
        # A dyld-loaded Foundation from a stub directory must not coexist
        # with the intended one. Compile the production probe against a tiny
        # fake dyld image inventory on Linux, without claiming Darling runtime.
        compiler = shutil.which("cc")
        if compiler is None:
            self.fail("Required C compiler unavailable for dyld image-selection fixture")
        expected = [
            f"/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
            for name, version in probes.FRAMEWORKS.items()
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            include = root / "include" / "mach-o"
            include.mkdir(parents=True)
            (include / "dyld.h").write_text(
                "#include <stdint.h>\n"
                "uint32_t _dyld_image_count(void);\n"
                "const char *_dyld_get_image_name(uint32_t);\n"
            )
            source = root / "images-test.c"
            executable = root / "images-test"
            for competitor in (None, "/developer/dev-stubs/Foundation"):
                inventory = expected + ([competitor] if competitor else [])
                entries = ",\n    ".join(json.dumps(path) for path in inventory)
                source.write_text(
                    '#include <stdint.h>\n#include <dlfcn.h>\n'
                    f'static const char *const loaded[] = {{ {entries} }};\n'
                    'uint32_t _dyld_image_count(void) { return sizeof(loaded) / sizeof(loaded[0]); }\n'
                    'const char *_dyld_get_image_name(uint32_t i) { return loaded[i]; }\n'
                    'void *dlopen(const char *path, int flags) { (void)path; (void)flags; return (void *)1; }\n'
                    '#include "images.h"\n'
                    'int main(void) { return p003_framework_images(); }\n'
                )
                compiled = subprocess.run(
                    [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                     "-I", str(root / "include"), "-I", str(Path(__file__).resolve().parent),
                     str(source), "-o", str(executable)],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                result = subprocess.run([str(executable)], capture_output=True, text=True, check=False)
                if competitor is None:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.count("P003_IMAGE "), len(expected))
                else:
                    self.assertEqual(result.returncode, 32, result.stderr)
                    self.assertIn("P003_IMAGE_ERROR competing path", result.stderr)
                    self.assertIn(competitor, result.stderr)

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
            report = json.loads((args.output / "report.json").read_text())
            self.assertIn("absent or empty", report["errors"][0])
            self.assertEqual(report["cases"], [])
            self.assertEqual(report["commands"], [])
            self.assertEqual((prefix / "old-library").read_text(), "previous installation")
            self.assertFalse((root / "prefix.home").exists())

    def test_controlled_home_collision_writes_failure_and_preserves_paths(self):
        for kind in ("directory", "file", "symlink", "dangling-symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prefix = root / "prefix"
                prefix.mkdir()
                home = root / "prefix.home"
                target = root / "home-target"
                if kind == "directory":
                    home.mkdir()
                    (home / "sentinel").write_bytes(b"unowned home contents")
                elif kind == "file":
                    home.write_bytes(b"unowned home file")
                elif kind == "symlink":
                    target.mkdir()
                    (target / "sentinel").write_bytes(b"unowned target contents")
                    home.symlink_to(target, target_is_directory=True)
                else:
                    home.symlink_to(target, target_is_directory=True)
                args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=prefix)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(probes.run(args), 1)
                report = json.loads((args.output / "report.json").read_text())
                self.assertEqual(report["status"], "FAILED")
                self.assertFalse(report["passed"])
                self.assertEqual(report["errors"], ["controlled runtime HOME must be absent"])
                self.assertEqual(report["cases"], [])
                self.assertEqual(report["commands"], [])
                self.assertIsNone(report["lifecycle"])
                self.assertIsNone(report["controlled_home"])
                self.assertNotIn("startup_processes", report)
                self.assertEqual(list(prefix.iterdir()), [])
                if kind == "directory":
                    self.assertEqual((home / "sentinel").read_bytes(), b"unowned home contents")
                    self.assertEqual(list(home.iterdir()), [home / "sentinel"])
                elif kind == "file":
                    self.assertEqual(home.read_bytes(), b"unowned home file")
                else:
                    self.assertTrue(home.is_symlink())
                    self.assertEqual(home.readlink(), target)
                    if kind == "symlink":
                        self.assertEqual((target / "sentinel").read_bytes(), b"unowned target contents")
                    else:
                        self.assertFalse(target.exists())

    def test_initialization_oserror_writes_failure_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=root / "prefix")
            with mock.patch.object(probes, "Campaign", side_effect=OSError("controlled HOME creation denied")), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(probes.run(args), 1)
            report = json.loads((args.output / "report.json").read_text())
            self.assertEqual(report["status"], "FAILED")
            self.assertFalse(report["passed"])
            self.assertEqual(report["errors"], ["controlled HOME creation denied"])
            self.assertEqual(report["cases"], [])
            self.assertEqual(report["commands"], [])
            self.assertIsNone(report["lifecycle"])
            self.assertFalse(args.prefix.exists())
            self.assertFalse((root / "prefix.home").exists())

    def test_unexpected_initialization_error_records_failure_and_preserves_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=root / "prefix")
            failure = KeyError("constructor state missing")

            def fail_initialization(installation, output, prefix):
                raise failure

            with mock.patch.object(probes, "Campaign", side_effect=fail_initialization), contextlib.redirect_stdout(io.StringIO()):
                try:
                    probes.run(args)
                except KeyError as error:
                    self.assertIs(error, failure)
                    frames = []
                    traceback = error.__traceback__
                    while traceback is not None:
                        frames.append(traceback.tb_frame.f_code.co_name)
                        traceback = traceback.tb_next
                    self.assertIn("fail_initialization", frames)
                else:
                    self.fail("unexpected constructor error must propagate")
            report = json.loads((args.output / "report.json").read_text())
            self.assertEqual(report["status"], "FAILED")
            self.assertFalse(report["passed"])
            self.assertEqual(report["errors"], ["KeyError: 'constructor state missing'"])
            self.assertEqual(report["cases"], [])
            self.assertEqual(report["commands"], [])
            self.assertIsNone(report["lifecycle"])
            self.assertIsNone(report["controlled_home"])
            self.assertNotIn("startup_processes", report)
            self.assertFalse(args.prefix.exists())
            self.assertFalse((root / "prefix.home").exists())

    def test_initialization_abort_records_failure_and_preserves_original_abort(self):
        for failure in (KeyboardInterrupt(), SystemExit(0), SystemExit(42), GeneratorExit()):
            with self.subTest(abort=type(failure).__name__, arguments=failure.args), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=root / "prefix")

                def abort_initialization(installation, output, prefix):
                    raise failure

                with mock.patch.object(probes, "Campaign", side_effect=abort_initialization), contextlib.redirect_stdout(io.StringIO()):
                    try:
                        probes.run(args)
                    except BaseException as error:
                        self.assertIs(error, failure)
                        frames = []
                        traceback = error.__traceback__
                        while traceback is not None:
                            frames.append(traceback.tb_frame.f_code.co_name)
                            traceback = traceback.tb_next
                        self.assertIn("abort_initialization", frames)
                    else:
                        self.fail("the original initialization abort must propagate")
                report = json.loads((args.output / "report.json").read_text())
                self.assertEqual(report["status"], "FAILED")
                self.assertFalse(report["passed"])
                self.assertEqual(report["errors"], [f"{type(failure).__name__}: {failure}"])
                self.assertEqual(report["cases"], [])
                self.assertEqual(report["commands"], [])
                self.assertIsNone(report["lifecycle"])
                self.assertIsNone(report["controlled_home"])
                self.assertNotIn("startup_processes", report)
                self.assertFalse(args.prefix.exists())
                self.assertFalse((root / "prefix.home").exists())

    def test_output_collision_preserves_existing_evidence(self):
        for kind in ("directory", "file", "symlink", "dangling-symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "evidence"
                target = root / "evidence-target"
                if kind == "directory":
                    output.mkdir()
                    (output / "report.json").write_bytes(b"existing report")
                    (output / "sentinel").write_bytes(b"existing evidence")
                elif kind == "file":
                    output.write_bytes(b"existing evidence file")
                elif kind == "symlink":
                    target.mkdir()
                    (target / "report.json").write_bytes(b"existing linked report")
                    output.symlink_to(target, target_is_directory=True)
                else:
                    output.symlink_to(target, target_is_directory=True)
                args = argparse.Namespace(installation=root / "installation", output=output, prefix=root / "prefix")
                with self.assertRaises(FileExistsError):
                    probes.run(args)
                self.assertFalse(args.prefix.exists())
                self.assertFalse((root / "prefix.home").exists())
                if kind == "directory":
                    self.assertEqual((output / "report.json").read_bytes(), b"existing report")
                    self.assertEqual((output / "sentinel").read_bytes(), b"existing evidence")
                    self.assertEqual({item.name for item in output.iterdir()}, {"report.json", "sentinel"})
                elif kind == "file":
                    self.assertEqual(output.read_bytes(), b"existing evidence file")
                else:
                    self.assertTrue(output.is_symlink())
                    self.assertEqual(output.readlink(), target)
                    if kind == "symlink":
                        self.assertEqual((target / "report.json").read_bytes(), b"existing linked report")
                    else:
                        self.assertFalse(target.exists())

    def test_late_report_collision_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = argparse.Namespace(installation=root / "installation", output=root / "evidence", prefix=root / "prefix")

            def fail_after_report_appears(installation, output, prefix):
                (output / "report.json").write_bytes(b"concurrent evidence")
                raise probes.ProbeFailure("initialization failed")

            with mock.patch.object(probes, "Campaign", side_effect=fail_after_report_appears), self.assertRaises(FileExistsError):
                probes.run(args)
            self.assertEqual((args.output / "report.json").read_bytes(), b"concurrent evidence")
            self.assertFalse(args.prefix.exists())
            self.assertFalse((root / "prefix.home").exists())

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
