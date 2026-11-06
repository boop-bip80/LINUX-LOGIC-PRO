"""Compile the legacy and header-derived objc4 debug contracts with real CMake."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]


class ObjectiveCBuildConfigurationTests(unittest.TestCase):
    def exercise(self, configuration, repaired, *, header_derived=False,
                 custom_flags=None, expected_debug=None, invalid_definition=None,
                 header_definition="DEBUG"):
        self.assertIsNotNone(shutil.which("cmake"), "CMake is required for this regression")
        self.assertIsNotNone(shutil.which("c++"), "A real C++ compiler is required for this regression")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / "runtime"
            child.mkdir()
            integration = (ROOT / "cmake/darling_objc_configuration.cmake").as_posix()
            parent = ('cmake_minimum_required(VERSION 3.13)\nproject(objc_configuration CXX)\n'
                      'add_subdirectory(runtime)\n')
            if repaired:
                parent += f'include("{integration}")\ndarling_configure_objc_runtime("${{CMAKE_CURRENT_SOURCE_DIR}}/runtime")\n'
            (root / "CMakeLists.txt").write_text(parent)
            # Minimal build contracts for the old 1a12df76 layout and the
            # current 092352ca layout. These fixtures exercise compiler output;
            # the complete pinned runtime is compiled by the hosted campaign.
            debug_flag = "" if header_derived else " -DOBJC_IS_DEBUG_BUILD=1"
            directory_flag = "" if header_derived else " -DOBJC_IS_DEBUG_BUILD=1"
            if invalid_definition is not None:
                directory_flag = " -D" + invalid_definition
            (child / "CMakeLists.txt").write_text(
                f'set(CMAKE_CXX_FLAGS_DEBUG "-ggdb{debug_flag}")\n'
                f'add_definitions(-DOBJC_NO_GC{directory_flag})\n'
                'add_executable(objc_configuration main.cpp)\n')
            (child / "objc-config.h").write_text(
                '#if !NDEBUG\n#define DEBUG 1\n#else\n#define DEBUG 0\n#endif\n'
                + (f'#define OBJC_IS_DEBUG_BUILD {header_definition}\n'
                   if header_derived and header_definition is not None else ''))
            (child / "main.cpp").write_text(
                '#include <cstdio>\n#include "objc-config.h"\n'
                '#if DEBUG != OBJC_IS_DEBUG_BUILD\n#error mismatch in debug-ness macros\n#endif\n'
                'int main() { std::printf("%d %d\\n", DEBUG, OBJC_IS_DEBUG_BUILD); }\n')
            build = root / "build"
            arguments = ["cmake", "-S", str(root), "-B", str(build),
                         "-DCMAKE_BUILD_TYPE=" + configuration, "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
            if custom_flags is not None:
                arguments.append("-DCMAKE_CXX_FLAGS_" + configuration.upper() + "=" + custom_flags)
            configured = subprocess.run(arguments,
                capture_output=True, text=True, timeout=30)
            if invalid_definition is not None or (header_derived and header_definition != "DEBUG"):
                self.assertNotEqual(configured.returncode, 0)
                self.assertIn("Pinned objc4 debug definition changed", configured.stdout + configured.stderr)
                return
            self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
            built = subprocess.run(["cmake", "--build", str(build)],
                                   capture_output=True, text=True, timeout=30)
            if not repaired:
                self.assertNotEqual(built.returncode, 0)
                self.assertIn("mismatch in debug-ness macros", built.stdout + built.stderr)
                return
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            expected = (expected_debug if expected_debug is not None else
                        "0" if configuration in ("Release", "RelWithDebInfo", "MinSizeRel") else "1")
            commands = json.loads((build / "compile_commands.json").read_text())
            values = re.findall(r"-DOBJC_IS_DEBUG_BUILD=([01])", commands[0]["command"])
            if header_derived:
                self.assertEqual(values, [], "Header-derived runtime must not receive an injected definition")
            else:
                self.assertTrue(values)
                self.assertEqual(set(values), {expected}, "Compiler received conflicting debug definitions")
            executed = subprocess.run([str(build / "runtime/objc_configuration")],
                                     capture_output=True, text=True, timeout=5)
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, f"{expected} {expected}\n")

    def test_original_release_mismatch_is_reproduced(self):
        self.exercise("Release", repaired=False)

    def test_configuration_repair_preserves_debug_and_release_contracts(self):
        for configuration in ("", "Debug", "Release", "RelWithDebInfo", "MinSizeRel"):
            with self.subTest(configuration=configuration):
                self.exercise(configuration, repaired=True)

    def test_current_header_derived_runtime_preserves_all_build_configurations(self):
        for configuration in ("", "Debug", "Release", "RelWithDebInfo", "MinSizeRel"):
            with self.subTest(configuration=configuration):
                self.exercise(configuration, repaired=True, header_derived=True)

    def test_current_runtime_obeys_ndebug_when_release_flags_are_customized(self):
        for configuration in ("Release", "RelWithDebInfo", "MinSizeRel"):
            with self.subTest(configuration=configuration):
                self.exercise(configuration, repaired=True, header_derived=True,
                              custom_flags="-O2 -g", expected_debug="1")

    def test_unreviewed_compile_definitions_remain_fatal(self):
        for definition in ("OBJC_IS_DEBUG_BUILD=0", "OBJC_IS_DEBUG_BUILD=2", "OBJC_IS_DEBUG_BUILD"):
            with self.subTest(definition=definition):
                self.exercise("Release", repaired=True, header_derived=True,
                              invalid_definition=definition)

    def test_missing_changed_or_duplicate_header_derivation_remains_fatal(self):
        for definition in (None, "1", "DEBUG\n#define OBJC_IS_DEBUG_BUILD DEBUG"):
            with self.subTest(definition=definition):
                self.exercise("Release", repaired=True, header_derived=True,
                              header_definition=definition)


if __name__ == "__main__":
    unittest.main()
