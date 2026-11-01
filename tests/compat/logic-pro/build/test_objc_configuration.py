"""Reproduce the pinned objc4 Release failure with real CMake/compiler output."""
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
    def exercise(self, configuration, repaired):
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
            # These are the relevant original definitions at objc4 pin
            # 1a12df76, with its actual DEBUG/NDEBUG consistency assertion.
            (child / "CMakeLists.txt").write_text(
                'set(CMAKE_CXX_FLAGS_DEBUG "-ggdb -DOBJC_IS_DEBUG_BUILD=1")\n'
                'add_definitions(-DOBJC_NO_GC -DOBJC_IS_DEBUG_BUILD=1)\n'
                'add_executable(objc_configuration main.cpp)\n')
            (child / "main.cpp").write_text(
                '#include <cstdio>\n#if !NDEBUG\n#define DEBUG 1\n#else\n#define DEBUG 0\n#endif\n'
                '#if DEBUG != OBJC_IS_DEBUG_BUILD\n#error mismatch in debug-ness macros\n#endif\n'
                'int main() { std::printf("%d %d\\n", DEBUG, OBJC_IS_DEBUG_BUILD); }\n')
            build = root / "build"
            configured = subprocess.run(["cmake", "-S", str(root), "-B", str(build),
                "-DCMAKE_BUILD_TYPE=" + configuration, "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
            built = subprocess.run(["cmake", "--build", str(build)],
                                   capture_output=True, text=True, timeout=30)
            if not repaired:
                self.assertNotEqual(built.returncode, 0)
                self.assertIn("mismatch in debug-ness macros", built.stdout + built.stderr)
                return
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            expected = "0" if configuration in ("Release", "RelWithDebInfo", "MinSizeRel") else "1"
            commands = json.loads((build / "compile_commands.json").read_text())
            values = re.findall(r"-DOBJC_IS_DEBUG_BUILD=([01])", commands[0]["command"])
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


if __name__ == "__main__":
    unittest.main()
