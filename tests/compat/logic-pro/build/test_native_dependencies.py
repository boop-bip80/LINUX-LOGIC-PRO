"""Native dependency audit fixtures; never qualify a Darling build by themselves."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro"
sys.path.insert(0, str(TOOLS))
import native_dependencies as native

HEADER = """ELF Header:
  Class:                             ELF64
  Type:                              DYN (Position-Independent Executable file)
  Machine:                           Advanced Micro Devices X86-64
      [Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]
 0x000000000000001d (RUNPATH)            Library runpath: [$ORIGIN/../lib:/usr/lib]
"""
LDD = """    linux-vdso.so.1 (0x00007fffa0000000)
    libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f0000000000)
    /lib64/ld-linux-x86-64.so.2 (0x00007f0000200000)
"""


class NativeDependencyTests(unittest.TestCase):
    def test_real_elf_header_and_search_paths(self):
        result = native.parse_readelf(HEADER)
        self.assertEqual(result["needed"], ["libc.so.6"])
        self.assertEqual(result["interpreter"], "/lib64/ld-linux-x86-64.so.2")
        self.assertEqual(result["runpath"], ["$ORIGIN/../lib", "/usr/lib"])

    def test_foreign_architecture_or_invalid_type_rejected(self):
        for value in (HEADER.replace("ELF64", "ELF32"), HEADER.replace("Advanced Micro Devices X86-64", "AArch64"), HEADER.replace("DYN", "REL")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                native.parse_readelf(value)

    def test_dynamic_resolution_and_kernel_vdso(self):
        result = native.parse_ldd(LDD)
        self.assertEqual([item["name"] for item in result], ["libc.so.6", "ld-linux-x86-64.so.2"])

    def test_missing_dependency_never_counts_as_resolved(self):
        for value in (LDD + "    libbroken.so => not found\n", "statically linked\n", "", "unexpected loader diagnostic\n"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                native.parse_ldd(value)

    def test_duplicate_resolution_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            native.parse_ldd(LDD + "libc.so.6 => /other/libc.so.6 (0x00001)\n")

    def test_source_library_and_symlink_borrowing_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, prefix = root / "source", root / "prefix"
            source.mkdir()
            prefix.mkdir()
            library = source / "libbad.so"
            library.write_bytes(b"\x7fELF" + bytes(64))
            (prefix / "libbad.so").symlink_to(library)
            with self.assertRaisesRegex(ValueError, "borrowed"):
                native.dependency_identity("libbad.so", prefix / "libbad.so", prefix, source)

    def test_relative_or_escaping_runtime_search_paths_rejected(self):
        prefix, source = Path("/opt/darling-p003"), Path("/p003/source")
        binary = prefix / "bin/darling"
        native.validate_search_paths(["$ORIGIN/../lib", "${ORIGIN}/../lib", "/usr/lib"], binary, prefix, source)
        for entry in ("", ".", "../build", "$ORIGIN/../../..", "/p003/build", "/p003/source", "$UNRECOGNIZED/lib"):
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                native.validate_search_paths([entry], binary, prefix, source)

    def test_wrapper_declarations_ignore_comments_and_bind_source_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, relative in enumerate(native.WRAPPER_SOURCES):
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text(f"# wrap_elf(bad libabsent.so)\nwrap_elf(test libtest{index}.so)\n")
            names, inputs = native.declared_wrappers(root)
            self.assertEqual(names, ["libtest0.so", "libtest1.so"])
            self.assertTrue(all(len(item["sha256"]) == 64 for item in inputs))

    def test_nonliteral_wrapper_soname_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in native.WRAPPER_SOURCES:
                path = root / relative
                path.parent.mkdir(parents=True)
                path.write_text("wrap_elf(test ${UNKNOWN_LIBRARY})\n")
            with self.assertRaisesRegex(ValueError, "literal"):
                native.declared_wrappers(root)

    def test_failed_command_preserves_failure_and_raw_logs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            collector = native.Collector(root / "prefix", root / "source", root / "evidence.json")
            failed = subprocess.CompletedProcess(["ldd"], 1, b"", b"not a dynamic executable\n")
            with patch.object(native.subprocess, "run", return_value=failed), self.assertRaisesRegex(ValueError, "failed"):
                collector.command(["ldd", "bad"])
            self.assertEqual(collector.commands[0]["exit_code"], 1)
            reference = collector.commands[0]["stderr"]
            self.assertEqual(native.sha256(root / reference["file"]), reference["sha256"])

    def test_real_system_elf_parser_and_glibc_wrapper_resolution(self):
        # A Linux host oracle for the audit machinery, not a Darling probe.
        completed = subprocess.run(["readelf", "-W", "-h", "-l", "-d", "/usr/bin/true"],
                                   check=True, capture_output=True, text=True, env=native.SAFE_ENV)
        self.assertTrue(native.parse_readelf(completed.stdout)["needed"])
        loaded = subprocess.run([sys.executable, "-c", native.LOAD_WRAPPER, "libm.so.6"],
                                check=True, capture_output=True, text=True, env=native.SAFE_ENV)
        identity = json.loads(loaded.stdout)
        self.assertEqual(identity["soname"], "libm.so.6")
        self.assertTrue(Path(identity["resolved"]).is_file())

    def test_real_host_fixture_campaign_and_missing_entrypoint_rejection(self):
        # Three copied host executables exercise the collector, never Darling.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prefix, source = root / "prefix", root / "source"
            source.mkdir()
            for relative in native.WRAPPER_SOURCES:
                path = source / relative
                path.parent.mkdir(parents=True)
                path.write_text("wrap_elf(test libm.so.6)\n")
            for relative in native.REQUIRED_ENTRYPOINTS:
                path = prefix / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile("/usr/bin/true", path)
            for arguments in (("init", "--quiet"), ("add", "."),
                              ("-c", "user.name=P003 fixture", "-c", "user.email=fixture@example.invalid",
                               "commit", "--quiet", "-m", "Synthetic native collector fixture")):
                subprocess.run(["git", "-C", str(source), *arguments], check=True, capture_output=True)
            report = native.collect(prefix, source, root / "first.json")
            self.assertEqual(report["status"], "PASSED", report["errors"])
            self.assertEqual(len(report["entries"]), 3)
            self.assertEqual(len(report["wrapped_libraries"]), 1)
            (prefix / "bin/darlingserver").unlink()
            report = native.collect(prefix, source, root / "second.json")
            self.assertEqual(report["status"], "FAILED")
            self.assertIn("entrypoints absent", report["errors"][0])


if __name__ == "__main__":
    unittest.main()
