"""Check real CMake binfmt configuration against its installed loader targets.

These two discovered cases add two tests to the P003 fixture floor: 136 -> 138
before the separately owned failure-diagnostics tests. This is configuration
evidence only: the optional mldr32 target is neither built nor executed here.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
REGISTRATIONS = {
    "Mach-O-64-bit": (r"\xcf\xfa\xed\xfe", "mldr"),
    "Mach-O-32-bit": (r"\xce\xfa\xed\xfe", "mldr32"),
    "Fat-Mach-O": (r"\xca\xfe\xba\xbe", "mldr"),
}


class BinfmtConfigurationTests(unittest.TestCase):
    def configure(self, directory: Path, enable_32bit: bool):
        cmake, compiler = shutil.which("cmake"), shutil.which("cc")
        self.assertIsNotNone(cmake, "CMake is required for this regression")
        self.assertIsNotNone(compiler, "A native C compiler is required for CMake configuration")
        source, build = directory / "source", directory / "build"
        prefix = directory / "relocated" / "darling-runtime"
        source.mkdir()
        query = build / ".cmake" / "api" / "v1" / "query"
        query.mkdir(parents=True)
        (query / "codemodel-v2").touch()
        # These unrelated generated prerequisites are not executed. The actual
        # repository CMakeLists declares the loader targets and install rules.
        (source / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.16)\n"
            "project(p003_binfmt_configuration C)\n"
            "add_custom_target(generate_dserver_rpc_wrappers)\n"
            "add_custom_target(rtsig_h)\n"
            f"set(BUILD_TARGET_32BIT {'ON' if enable_32bit else 'OFF'})\n"
            f'add_subdirectory("{(ROOT / "src/startup/mldr").as_posix()}" mldr)\n'
        )
        configured = subprocess.run(
            [cmake, "-S", str(source), "-B", str(build),
             "-DCMAKE_C_COMPILER=" + compiler,
             "-DCMAKE_INSTALL_PREFIX=" + str(prefix)],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
        rendered = (build / "mldr" / "darling.conf").read_text()
        self.assertNotIn("@", rendered, "Binfmt template contains an unresolved CMake variable")
        registrations = {}
        for line in rendered.splitlines():
            if not line:
                continue
            fields = line.split(":")
            self.assertEqual(len(fields), 8, "Binfmt registration must retain all eight fields")
            empty, name, kind, offset, magic, mask, interpreter, flags = fields
            self.assertNotIn(name, registrations, "Duplicate binfmt registration")
            self.assertIn(name, REGISTRATIONS, "Unexpected binfmt registration")
            self.assertEqual((empty, kind, offset, magic, mask, flags),
                             ("", "M", "", REGISTRATIONS[name][0], "", "P"),
                             "Registration identity, magic, mask, or argv-preservation flag changed")
            self.assertTrue(Path(interpreter).is_absolute(), "Interpreter path must be absolute")
            registrations[name] = interpreter
        self.assertEqual(set(registrations), set(REGISTRATIONS),
                         "Existing Mach-O architecture handlers must not disappear")

        reply = build / ".cmake" / "api" / "v1" / "reply"
        indexes = list(reply.glob("index-*.json"))
        self.assertEqual(len(indexes), 1, "Expected one fresh CMake file-API index")
        index = json.loads(indexes[0].read_text())
        codemodel = json.loads((reply / index["reply"]["codemodel-v2"]["jsonFile"]).read_text())
        self.assertEqual(len(codemodel["configurations"]), 1)
        installed_targets = {}
        for reference in codemodel["configurations"][0]["targets"]:
            if reference["name"] not in ("mldr", "mldr32"):
                continue
            target = json.loads((reply / reference["jsonFile"]).read_text())
            self.assertEqual(target["type"], "EXECUTABLE")
            self.assertEqual(target["install"]["prefix"]["path"], str(prefix))
            destinations = target["install"]["destinations"]
            self.assertEqual(len(destinations), 1, "Loader must have one unambiguous install destination")
            artifacts = target["artifacts"]
            self.assertEqual(len(artifacts), 1)
            filename = PurePosixPath(artifacts[0]["path"]).name
            self.assertEqual(filename, reference["name"])
            destination = PurePosixPath(destinations[0]["path"])
            self.assertFalse(destination.is_absolute(), "Install destination must honor the relocated prefix")
            self.assertNotIn("..", destination.parts)
            installed_targets[reference["name"]] = str(prefix / destination / filename)
        self.assertEqual(set(installed_targets), {"mldr", "mldr32"} if enable_32bit else {"mldr"})
        return registrations, installed_targets

    def assert_installed_handler(self, registrations, targets, name):
        target = REGISTRATIONS[name][1]
        self.assertEqual(registrations[name], targets[target],
                         f"{name} interpreter must resolve to the actual CMake-installed {target} target")

    def test_64bit_and_fat_handlers_match_relocated_install_target(self):
        with tempfile.TemporaryDirectory(prefix="p003-binfmt-") as directory:
            registrations, targets = self.configure(Path(directory), enable_32bit=False)
            for name in ("Mach-O-64-bit", "Fat-Mach-O"):
                with self.subTest(handler=name):
                    self.assert_installed_handler(registrations, targets, name)
            # The pre-existing 32-bit registration is preserved, but this
            # configuration has no mldr32 target and makes no 32-bit claim.
            self.assertNotIn("mldr32", targets)

    def test_32bit_handler_matches_target_only_when_target_is_configured(self):
        with tempfile.TemporaryDirectory(prefix="p003-binfmt-") as directory:
            registrations, targets = self.configure(Path(directory), enable_32bit=True)
            for name in REGISTRATIONS:
                with self.subTest(handler=name):
                    self.assert_installed_handler(registrations, targets, name)


if __name__ == "__main__":
    unittest.main()
