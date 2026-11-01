"""Real-source regression for the pinned libxpc-to-liblaunch lifecycle bridge.

These local tests prove source forwarding and CMake source ownership only. The
installed Mach-O/Foundation counter observations and independent archive-only
runtime replay remain mandatory; a native mock is not phase acceptance.
"""
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
BRIDGE = ROOT / "src/compat/logic-pro/libxpc_transaction.m"
HELPER = ROOT / "cmake/darling_xpc_transaction.cmake"


class LibxpcTransactionRegression(unittest.TestCase):
    def test_actual_root_source_forwards_both_exported_calls_to_liblaunch(self):
        source = BRIDGE.read_text()
        functions = []
        for name in ("begin", "end"):
            match = re.search(
                rf"XPC_EXPORT\s+(void xpc_transaction_{name}\(void\)\s*\{{([^{{}}]*)\}});",
                source,
            )
            self.assertIsNotNone(match, f"xpc_transaction_{name} export absent")
            self.assertEqual(match.group(2).strip(), f"_vproc_transaction_{name}();")
            functions.append(match.group(1))
            self.assertIn(f"_vproc_transaction_{name}(void);",
                          (ROOT / "src/launchd/liblaunch/vproc_priv.h").read_text())

        cc = shutil.which("cc")
        self.assertIsNotNone(cc, "A native compiler is required to check the actual source")
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "native-interop.c"
            binary = Path(directory) / "native-interop"
            source_path.write_text("\n".join([
                "#include <assert.h>",
                "static unsigned counter;",
                "void _vproc_transaction_begin(void) { ++counter; }",
                "void _vproc_transaction_end(void) { assert(counter); --counter; }",
                *functions,
                "int main(void) {",
                "    xpc_transaction_begin(); assert(counter == 1);",
                "    _vproc_transaction_begin(); assert(counter == 2);",
                "    xpc_transaction_end(); assert(counter == 1);",
                "    _vproc_transaction_end(); assert(counter == 0);",
                "    return 0;",
                "}",
            ]) + "\n")
            run = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2",
                                  str(source_path), "-o", str(binary)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(subprocess.run([str(binary)], check=False).returncode, 0)

    def test_cmake_preserves_source_context_and_fails_closed_on_drift(self):
        cmake = shutil.which("cmake")
        self.assertIsNotNone(cmake, "CMake source replacement must be configured")
        for original, should_pass in (("src/transaction.m src/other.c", True),
                                      ("src/other.c", False),
                                      ("src/transaction.m src/transaction.m src/other.c", False)):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "source"
                pinned = source / "pinned"
                (pinned / "src").mkdir(parents=True)
                (pinned / "src/transaction.m").write_text("/* pinned original */\n")
                (pinned / "src/other.c").write_text("int other(void) { return 0; }\n")
                (pinned / "CMakeLists.txt").write_text(
                    f"add_library(xpc_obj OBJECT {original})\n"
                    "set_source_files_properties(src/transaction.m PROPERTIES LANGUAGE C)\n")
                (source / "CMakeLists.txt").write_text(
                    "cmake_minimum_required(VERSION 3.20)\n"
                    "project(transaction_source LANGUAGES C)\n"
                    "add_subdirectory(pinned)\n"
                    f"include(\"{HELPER}\")\n"
                    f"darling_replace_libxpc_transaction(xpc_obj \"{BRIDGE}\")\n"
                    "get_target_property(actual xpc_obj SOURCES)\n"
                    "file(WRITE \"${CMAKE_BINARY_DIR}/actual.txt\" \"${actual}\")\n")
                build = Path(directory) / "build"
                run = subprocess.run([cmake, "-S", str(source), "-B", str(build)],
                                     capture_output=True, text=True, check=False)
                if should_pass:
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                    sources = (build / "actual.txt").read_text().split(";")
                    self.assertEqual(sources, [str(BRIDGE), str(pinned / "src/other.c")])
                else:
                    self.assertNotEqual(run.returncode, 0)
                    self.assertIn("Expected exactly one pinned libxpc", run.stderr)

    def test_upstream_libxpc_pin_remains_unchanged(self):
        run = subprocess.run(["git", "ls-tree", "HEAD", "src/external/libxpc"],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(run.stdout.strip(),
                         "160000 commit 394e033333d3c253a12f08a99090c113b0917d00\tsrc/external/libxpc")

    def test_x11_diagnostic_fix_keeps_private_display_and_real_input_checks(self):
        producer = (ROOT / "ci/logic-pro/build-p003.sh").read_text()
        hosted = (ROOT / ".github/workflows/phase3-build.yml").read_text()
        live = (ROOT / "tools/compat/logic-pro/run_build_probes.py").read_text()
        independent = (ROOT / "tools/compat/logic-pro/review_installed_runtime.py").read_text()
        self.assertEqual(producer.count("xvfb-run -a -s '-screen 0 1024x768x24 -nolisten tcp -ac'"), 2)
        self.assertIn('xvfb-run -a -s "-screen 0 1024x768x24 -nolisten tcp -ac"', hosted)
        self.assertGreaterEqual(hosted.count("--network none"), 2)
        for driver in (live, independent):
            for required in ("xdotool", "xwd", "gui-event-roundtrip"):
                self.assertIn(required, driver)
        self.assertIn("assert_colors", live)
        self.assertIn("inspect_color_patches", independent)
        self.assertIn("decode_xwd", independent)


if __name__ == "__main__":
    unittest.main()
