"""Real CMake and compiler regressions for dyld's static unwind dependency.

Ordinary discovery tests target/type guards and option scoping with the host
compiler. The separately required ``clang14`` mode uses the frozen compiler,
builds actual Mach-O control/repaired objects, and executes both native variants.
It never substitutes a skipped test for the pinned compiler reproduction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
HELPER = ROOT / "cmake/darling_unwind_configuration.cmake"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run_command(arguments, directory, output=None, label=None):
    result = subprocess.run(arguments, cwd=directory, capture_output=True, text=True, timeout=40)
    if output is not None:
        (output / (label + ".stdout.log")).write_text(result.stdout)
        (output / (label + ".stderr.log")).write_text(result.stderr)
    require(result.returncode == 0,
            f"Command failed ({result.returncode}): {shlex.join(arguments)}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def register_source(registers_header, unwind_header):
    original = registers_header.read_text()
    definition = re.search(
        r"inline const char \*Registers_x86_64::getRegisterName\(int regNum\) \{.*?\n\}",
        original, re.DOTALL)
    require(definition is not None, "Pinned x86_64 register-name function changed; review this reproducer")
    values = dict(re.findall(r"^\s*(UNW_(?:REG_IP|REG_SP|X86_64_\w+))\s*=\s*(-?\d+)\s*[,}]",
                             unwind_header.read_text(), re.MULTILINE))
    used = set(re.findall(r"\bUNW_\w+\b", definition[0]))
    require(used <= values.keys() and {"UNW_REG_IP", "UNW_REG_SP"} <= used,
            "Pinned register enum declarations changed; review this reproducer")
    enums = ",\n".join(f"{name} = {values[name]}" for name in sorted(used))
    return ("// Function and enum values extracted unchanged from pinned LLVM libunwind.\n"
            "// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception\n"
            "// https://llvm.org/LICENSE.txt\nnamespace libunwind {\nenum {\n" + enums + "\n};\n"
            "class Registers_x86_64 { public: static const char *getRegisterName(int); };\n"
            + definition[0] + "\n}\n"
            'extern "C" __attribute__((noinline)) const char *register_name(int number) {\n'
            "  return libunwind::Registers_x86_64::getRegisterName(number);\n}\n")


def macho_layout(path):
    data = path.read_bytes()
    require(len(data) >= 32, "Truncated Mach-O compiler output")
    magic, cpu, subtype, kind, command_count, command_bytes, flags, reserved = struct.unpack_from("<8I", data)
    require((magic, cpu, kind) == (0xFEEDFACF, 0x01000007, 1), "Expected an x86_64 Mach-O object")
    require(32 + command_bytes <= len(data), "Truncated Mach-O command table")
    offset, sections, symbols = 32, [], []
    for _ in range(command_count):
        require(offset + 8 <= 32 + command_bytes, "Missing Mach-O load command")
        command, size = struct.unpack_from("<II", data, offset)
        require(size >= 8 and offset + size <= 32 + command_bytes, "Invalid Mach-O load command length")
        if command == 0x19:  # LC_SEGMENT_64
            require(size >= 72, "Invalid Mach-O segment")
            count = struct.unpack_from("<I", data, offset + 64)[0]
            require(72 + count * 80 <= size, "Truncated Mach-O sections")
            for index in range(count):
                position = offset + 72 + 80 * index
                name = data[position:position + 16].split(b"\0")[0].decode("ascii")
                relocations_at, relocation_count = struct.unpack_from("<II", data, position + 56)
                require(relocations_at + relocation_count * 8 <= len(data), "Truncated Mach-O relocations")
                relocations = []
                for relocation in range(relocation_count):
                    address, bits = struct.unpack_from("<iI", data, relocations_at + relocation * 8)
                    relocations.append({"address": address, "type": bits >> 28,
                                        "bytes": 1 << ((bits >> 25) & 3),
                                        "pc_relative": bool((bits >> 24) & 1)})
                sections.append({"name": name, "relocations": relocations})
        elif command == 2:  # LC_SYMTAB
            require(size == 24, "Unexpected Mach-O symbol table command")
            location, count, strings_at, strings_size = struct.unpack_from("<4I", data, offset + 8)
            require(location + count * 16 <= len(data) and strings_at + strings_size <= len(data),
                    "Truncated Mach-O symbols")
            for index in range(count):
                string_index = struct.unpack_from("<I", data, location + index * 16)[0]
                require(string_index < strings_size, "Invalid Mach-O symbol name offset")
                name = data[strings_at + string_index:strings_at + strings_size].split(b"\0")[0].decode("ascii")
                symbols.append(name)
        offset += size
    require(offset == 32 + command_bytes, "Mach-O command sizes disagree")
    return {"file": str(path), "sha256": digest(path), "sections": sections,
            "relative_table_symbols": [name for name in symbols if "reltable." in name]}


def forbidden_relative_data(layout):
    return [relocation for section in layout["sections"] if section["name"] == "__const"
            for relocation in section["relocations"]
            if relocation["type"] in (0, 5) and relocation["bytes"] == 4 and not relocation["pc_relative"]]


def create_project(directory, helper, source, cross):
    directory.mkdir()
    (directory / "register_names.cpp").write_text(source)
    text = ("cmake_minimum_required(VERSION 3.13)\nproject(unwind_codegen CXX)\n"
            "add_library(control_static STATIC register_names.cpp)\n"
            "add_library(unwind_static STATIC register_names.cpp)\n")
    for target in ("control_static", "unwind_static"):
        options = "-fPIC -fno-rtti -fno-exceptions -funwind-tables"
        if cross:
            options += " -target x86_64-apple-darwin20 -mmacosx-version-min=11.0 -nostdinc -nostdinc++"
        text += f"target_compile_options({target} PRIVATE {options})\n"
    text += f'include("{helper.as_posix()}")\ndarling_configure_static_unwind(unwind_static)\n'
    if not cross:
        # Volatile input prevents constant folding of the calls. The entire
        # valid range, its hole at16, out-of-range values and int limits run.
        (directory / "main.cpp").write_text(
            'extern "C" int printf(const char *, ...);\n'
            'extern "C" const char *register_name(int);\n'
            'int main() {\n'
            '  for (volatile int value = -8; value <= 40; ++value)\n'
            '    printf("%d %s\\n", value, register_name(value));\n'
            '  volatile int lower = (-2147483647 - 1), upper = 2147483647;\n'
            '  printf("%d %s\\n", lower, register_name(lower));\n'
            '  printf("%d %s\\n", upper, register_name(upper));\n'
            '  return 0;\n}\n')
        for kind, library in (("control", "control_static"), ("repaired", "unwind_static")):
            text += (f"add_executable({kind}_behavior main.cpp)\n"
                     f"target_link_libraries({kind}_behavior PRIVATE {library})\n")
    (directory / "CMakeLists.txt").write_text(text)


def expected_behavior():
    general = ["rax", "rdx", "rcx", "rbx", "rsi", "rdi", "rbp", "rsp",
               "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
    known = dict(enumerate(general))
    known.update({-2: "rsp", -1: "rip"})
    known.update({17 + index: "xmm" + str(index) for index in range(16)})
    inputs = list(range(-8, 41)) + [-2147483648, 2147483647]
    return "".join(f"{number} {known.get(number, 'unknown register')}\n" for number in inputs)


def pinned_compiler_regression(args):
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"schema": "darling.p003.unwind-codegen.v1", "status": "FAIL", "errors": []}
    try:
        require(shutil.which("cmake") and shutil.which("ninja"), "Real CMake and Ninja are mandatory")
        require(args.compiler.is_file(), "Pinned Clang14 compiler is missing")
        lock = json.loads(args.toolchain_lock.read_text())
        compiler_hash = digest(args.compiler.resolve())
        require(compiler_hash == lock["environment"]["tools"]["clang"]["sha256"],
                "Compiler executable differs from the frozen toolchain")
        version = run_command([str(args.compiler), "--version"], args.output, args.output, "compiler-version")
        require(re.search(r"clang version 14\.", version) is not None, "Regression requires actual Clang14")
        report.update(compiler={"path": str(args.compiler), "sha256": compiler_hash, "version": version},
                      helper_sha256=digest(args.helper), toolchain_sha256=digest(args.toolchain_lock),
                      source_inputs={str(path): digest(path) for path in (args.registers_header, args.unwind_header)})
        source = register_source(args.registers_header, args.unwind_header)
        for kind, cross in (("macho", True), ("native", False)):
            project = args.output / kind
            create_project(project, args.helper, source, cross)
            build = project / "build"
            run_command(["cmake", "-G", "Ninja", "-S", str(project), "-B", str(build),
                         "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                         "-DCMAKE_CXX_COMPILER=" + str(args.compiler)], args.output, args.output, kind + "-configure")
            run_command(["cmake", "--build", str(build)], args.output, args.output, kind + "-build")
            commands = json.loads((build / "compile_commands.json").read_text())
            for target, required in (("control_static", False), ("unwind_static", True)):
                records = [row for row in commands if f"CMakeFiles/{target}.dir/" in row["command"]]
                require(len(records) == 1, "Unexpected register-name compilation set")
                arguments = shlex.split(records[0]["command"])
                require(("-fno-jump-tables" in arguments) == required,
                        "Actual compiler options do not match the private target setting")
            for command in commands:
                if "CMakeFiles/unwind_static.dir/" not in command["command"]:
                    require("-fno-jump-tables" not in shlex.split(command["command"]),
                            "Static unwind option leaked to another target or a linked consumer")
            if cross:
                control = macho_layout(build / "CMakeFiles/control_static.dir/register_names.cpp.o")
                repaired = macho_layout(build / "CMakeFiles/unwind_static.dir/register_names.cpp.o")
                require(control["relative_table_symbols"] and forbidden_relative_data(control),
                        "Control compiler output did not reproduce the failing relative lookup table")
                require(not repaired["relative_table_symbols"] and not forbidden_relative_data(repaired),
                        "Repaired compiler output still contains unsupported relative table fixups")
                report["macho"] = {"control": control, "repaired": repaired}
            else:
                expected = expected_behavior()
                observed = {}
                for variant in ("control", "repaired"):
                    output = run_command([str(build / (variant + "_behavior"))], args.output,
                                         args.output, variant + "-behavior")
                    require(output == expected, f"{variant} register-name behavior changed")
                    observed[variant] = hashlib.sha256(output.encode()).hexdigest()
                report["behavior"] = {"inputs": 51, "all_valid_registers": True,
                                       "default_hole_16": True, "int_min_max": True,
                                       "stdout_sha256": observed}
        report["status"] = "PASS"
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report["errors"].append(str(error))
    report["evidence"] = {str(path.relative_to(args.output)): digest(path)
                          for path in sorted(args.output.rglob("*")) if path.is_file()}
    (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "errors": report["errors"],
                      "report": str(args.output / "report.json")}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


class UnwindConfigurationTests(unittest.TestCase):
    def configure(self, root, content):
        self.assertIsNotNone(shutil.which("cmake"), "Real CMake is required")
        (root / "CMakeLists.txt").write_text(content)
        return subprocess.run(["cmake", "-S", str(root), "-B", str(root / "build"),
                               "-DCMAKE_BUILD_TYPE=Release", "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
                              capture_output=True, text=True, timeout=40)

    def test_missing_and_nonstatic_target_fail_closed(self):
        for declaration, message in (("", "Pinned static libunwind target changed"),
                                     ("add_library(unwind_static INTERFACE)\n", "Expected a static libunwind library")):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                result = self.configure(root, 'cmake_minimum_required(VERSION 3.13)\nproject(unwind_guards NONE)\n'
                                        + declaration + f'include("{HELPER.as_posix()}")\n'
                                        + 'darling_configure_static_unwind(unwind_static)\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stdout + result.stderr)

    def test_option_is_private_to_static_unwind_cpp_and_matching_compiler(self):
        self.assertIsNotNone(shutil.which("c++"), "A real C++ compiler is required")
        self.assertIsNotNone(shutil.which("cc"), "A real C compiler is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "names.cpp").write_text('extern "C" const char *name(int v) {\n'
                                            'switch (v) { case 0: return "rax"; case 1: return "rdx";\n'
                                            'case 2: return "rcx"; default: return "unknown"; } }\n')
            (root / "scope.c").write_text("int c_scope(void) { return 42; }\n")
            (root / "main.cpp").write_text('extern "C" int c_scope(void);\n'
                                           'int main() { return c_scope() == 42 ? 0 : 1; }\n')
            result = self.configure(root, 'cmake_minimum_required(VERSION 3.13)\nproject(unwind_scope C CXX)\n'
                                    'add_library(unwind_static STATIC names.cpp scope.c)\n'
                                    'add_library(unwind_shared SHARED names.cpp)\n'
                                    + f'include("{HELPER.as_posix()}")\n'
                                    + 'darling_configure_static_unwind(unwind_static)\n'
                                    + 'add_executable(consumer main.cpp)\n'
                                    + 'target_link_libraries(consumer PRIVATE unwind_static)\n'
                                    + 'file(WRITE "${CMAKE_BINARY_DIR}/compiler.id" "${CMAKE_CXX_COMPILER_ID}")\n')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            build = root / "build"
            built = subprocess.run(["cmake", "--build", str(build)], capture_output=True, text=True, timeout=40)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            compiler = (build / "compiler.id").read_text()
            commands = json.loads((build / "compile_commands.json").read_text())
            self.assertEqual(len(commands), 4)
            for command in commands:
                enabled = ("unwind_static.dir/" in command["command"]
                           and command["file"].endswith(".cpp") and compiler in ("Clang", "AppleClang"))
                self.assertEqual("-fno-jump-tables" in shlex.split(command["command"]), enabled)
            executed = subprocess.run([str(build / "consumer")], capture_output=True, text=True, timeout=5)
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clang14":
        parser = argparse.ArgumentParser(description="Required frozen-Clang14 relative-lookup-table regression")
        parser.add_argument("--compiler", type=Path, required=True)
        parser.add_argument("--toolchain-lock", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        parser.add_argument("--helper", type=Path, default=HELPER)
        parser.add_argument("--registers-header", type=Path,
                            default=ROOT / "src/external/libunwind/libunwind/src/Registers.hpp")
        parser.add_argument("--unwind-header", type=Path,
                            default=ROOT / "src/external/libunwind/libunwind/include/libunwind.h")
        raise SystemExit(pinned_compiler_regression(parser.parse_args(sys.argv[2:])))
    unittest.main()
