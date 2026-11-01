"""Execute the loader's actual x86_64 stack-switch asm under Clang and GCC.

The retained 0f7f34f package contains mldr SHA256
e1c37512cdd756609f00c14885ee5c807a78808abd228a1ae679f0a54bfa60d2.
Its darling_thread_entry loads entry_point into RBP at 0x4e77, clears RBP at
0x4e84, switches RSP, pushes zero, and jumps through RBP at 0x4e8c:
488b6c24384c89ff488b4c24304831ed4889c46a00ffe5.
Two real launchd workers consequently faulted at RIP=0. The negative control
below reproduces that historical instruction order with a legal RBP input.

Positive cases extract the live production register bindings, fallback argument,
alignment function, and complete asm statement. Only the operand expression is
bound to an explicit register in allocation cases; production instructions and
constraints are not copied or rewritten. Native RPC/thread creation is outside
this boundary test. The complete installed runtime remains a separate gate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "src/startup/mldr/elfcalls/threads.c"

HISTORICAL_ASM = r'''
asm volatile(
    "xorq %%rbp, %%rbp\n"
    "movq %[stack_ptr], %%rsp\n"
    "pushq $0\n"
    "jmp *%[entry_point]" ::
    "r"(arg1), "r"(arg2), "r"(arg3), "r"(arg4), "r"(arg5), "r"(arg6),
    [entry_point] "r"(entry_operand), [stack_ptr] "r"(stack_ptr)
);
'''

# No compiler-private headers are needed: these are the Linux x86_64 libc ABI
# declarations used only by the fixture. This also allows the exact frozen
# Clang executable to run from its independently verified extracted package.
FIXTURE = r'''
typedef __UINTPTR_TYPE__ uintptr_t;
typedef __SIZE_TYPE__ size_t;
typedef _Bool bool;
typedef const struct callback_fixture *darling_thread_create_callbacks_t;
extern void *malloc(size_t);
extern int printf(const char *, ...);
extern void _Exit(int) __attribute__((noreturn));
struct core_limit { unsigned long current, maximum; };
extern int setrlimit(int, const struct core_limit *);

@STRUCTURE@
@ALIGNMENT@

volatile uintptr_t observed[9];
static uintptr_t allocation, requested_top, pthread_object, stack_bottom;
static int is_workqueue;
static void sentinel_callback(void) { _Exit(71); }

void verify_and_exit(void) __attribute__((used, noinline, noreturn));
void verify_and_exit(void) {
    printf("{\"mode\":\"%s\",\"registers\":[\"%lx\",\"%lx\",\"%lx\",\"%lx\",\"%lx\",\"%lx\"],"
           "\"rsp\":\"%lx\",\"rbp\":\"%lx\",\"return\":\"%lx\","
           "\"allocation\":\"%lx\",\"allocation_bytes\":131072,"
           "\"requested_top\":\"%lx\",\"pth\":\"%lx\",\"callback\":\"%lx\","
           "\"stack_bottom\":\"%lx\"}\n",
           is_workqueue ? "workqueue" : "normal",
           observed[0], observed[1], observed[2], observed[3], observed[4], observed[5],
           observed[6], observed[7], observed[8],
           allocation, requested_top, pthread_object, (uintptr_t)sentinel_callback, stack_bottom);
    /* exit(), unlike _Exit(), flushes this small stdout record. */
    extern void exit(int) __attribute__((noreturn));
    exit(0);
}

void receiver(void) __attribute__((naked, used, noinline, noreturn));
void receiver(void) {
    __asm__ volatile(
        "movq %rdi, observed+0(%rip)\n"
        "movq %rsi, observed+8(%rip)\n"
        "movq %rdx, observed+16(%rip)\n"
        "movq %rcx, observed+24(%rip)\n"
        "movq %r8, observed+32(%rip)\n"
        "movq %r9, observed+40(%rip)\n"
        "movq %rsp, observed+48(%rip)\n"
        "movq %rbp, observed+56(%rip)\n"
        "movq (%rsp), %r10\n"
        "movq %r10, observed+64(%rip)\n"
        "subq $8, %rsp\n"
        "call verify_and_exit\n"
        "ud2\n"
    );
}

static void transfer(struct arg_struct args) __attribute__((noinline, noreturn));
static void transfer(struct arg_struct args) {
    @STACK_DECLARATION@
    @REGISTERS@
    @FALLBACK@
    @ENTRY_DECLARATION@
    @TRANSFER@
    __builtin_unreachable();
}

int main(int argc, char **argv) {
    const struct core_limit no_core = {0, 0};
    if (setrlimit(4, &no_core) != 0) return 72; /* child-only RLIMIT_CORE */
    is_workqueue = argc == 2 && argv[1][0] == 'w';
    void *memory = malloc(131072);
    if (!memory) return 73;
    allocation = (uintptr_t)memory;
    requested_top = allocation + 65549; /* deliberately requires align_16 */
    pthread_object = allocation + 65664;
    stack_bottom = allocation + 4096;
    struct arg_struct args = {0};
    args.entry_point = (thread_ep)receiver;
    args.real_entry_point = is_workqueue ? 0 : (uintptr_t)sentinel_callback;
    args.pth = (void *)pthread_object;
    args.port = 0x713246ab;
    args.stack_addr = requested_top;
    args.stack_bottom = stack_bottom;
    args.arg1 = is_workqueue ? 0x778899aabbccdde0UL : 0x1122334455667788UL;
    args.arg2 = is_workqueue ? 0x1122334455667788UL : requested_top;
    args.arg3 = is_workqueue ? 0xaabbccddeeff0011UL : 0x190008ffUL;
    transfer(args);
}
'''


def one_match(pattern, source, label):
    matches = re.findall(pattern, source, flags=re.DOTALL)
    if len(matches) != 1:
        raise AssertionError(f"Expected one production {label}, found {len(matches)}")
    return matches[0]


def source_fragments():
    source = SOURCE.read_text()
    structure = one_match(
        r"(typedef void \(\*thread_ep\).*?\nstruct arg_struct\n\{.*?\n\};)",
        source, "argument structure")
    alignment = one_match(
        r"(static inline void \*align_16\(uintptr_t ptr\) \{.*?\n\})",
        source, "alignment helper")
    registers = one_match(
        r"#if __x86_64__\n(\s*register void\*.*?)(?=#elif __i386__)",
        source, "ABI register binding")
    fallback = one_match(
        r"(\tif \(arg3 == 0\) \{.*?\n\t\})\n\n#ifdef __x86_64__",
        source, "workqueue argument fallback")
    transfer = one_match(
        r"#ifdef __x86_64__\n(\tasm volatile\(.*?\n\t\);)\n#elif defined\(__i386__\)",
        source, "stack-switch statement")
    if transfer.count('"r"(args.entry_point)') != 1:
        raise AssertionError("Entry operand expression changed; review allocation fixture binding")
    return {"STRUCTURE": structure, "ALIGNMENT": alignment, "REGISTERS": registers,
            "FALLBACK": fallback, "TRANSFER": transfer}


def fixture_source(binding, historical=False):
    parts = source_fragments()
    parts["STACK_DECLARATION"] = (
        'register void *stack_ptr asm("rbp") = align_16(args.stack_addr);'
        if binding == "stack-rbp" else "void *stack_ptr = align_16(args.stack_addr);")
    parts["ENTRY_DECLARATION"] = ""
    if binding == "entry-rbp" or historical:
        parts["ENTRY_DECLARATION"] = 'register thread_ep entry_operand asm("rbp") = args.entry_point;'
        parts["TRANSFER"] = parts["TRANSFER"].replace(
            '"r"(args.entry_point)', '"r"(entry_operand)')
    if historical:
        parts["TRANSFER"] = HISTORICAL_ASM
    result = FIXTURE
    for key, value in parts.items():
        result = result.replace("@" + key + "@", value)
    if re.search(r"@[A-Z_]+@", result):
        raise AssertionError("Unexpanded fixture placeholder")
    return result


class MldrThreadEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise AssertionError("Native loader ABI regression requires Linux x86_64; cannot skip")
        cls.compilers = {}
        for family in ("clang", "gcc"):
            candidate = os.environ.get("MLDR_TEST_" + family.upper()) or shutil.which(family)
            if not candidate or not Path(candidate).is_file():
                raise AssertionError(f"Required {family} compiler unavailable; cannot skip")
            result = subprocess.run([candidate, "--version"], text=True, capture_output=True, timeout=15)
            if result.returncode or family not in result.stdout.lower():
                raise AssertionError(f"Unexpected {family} compiler: {result.stdout} {result.stderr}")
            cls.compilers[family] = candidate
            print(f"mldr native compiler {family}: {result.stdout.splitlines()[0]}")
        print("mldr thread source SHA256:", hashlib.sha256(SOURCE.read_bytes()).hexdigest())

    def compile_case(self, directory, family, configuration, binding, historical=False):
        stem = "-".join((family, configuration, binding, "historical" if historical else "current"))
        source, binary = directory / (stem + ".c"), directory / stem
        source.write_text(fixture_source(binding, historical))
        flags = (["-O0", "-g", "-fno-omit-frame-pointer"] if configuration == "debug"
                 else ["-O3", "-DNDEBUG", "-fomit-frame-pointer"])
        command = [self.compilers[family], "-std=gnu11", "-fPIC", "-fPIE", "-pthread",
                   "-Wall", "-Wextra", "-Werror", *flags, str(source), "-o", str(binary)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, {"command": command, "stderr": result.stderr})
        return binary

    def check_execution(self, binary, mode):
        result = subprocess.run([str(binary), mode], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0,
                         {"binary": str(binary), "mode": mode, "stdout": result.stdout, "stderr": result.stderr})
        value = json.loads(result.stdout)
        self.assertEqual(value["mode"], mode)
        registers = [int(item, 16) for item in value["registers"]]
        pth, callback, top, bottom = [int(value[key], 16)
                                      for key in ("pth", "callback", "requested_top", "stack_bottom")]
        self.assertNotEqual(callback, 0)
        expected = ([pth, 0x713246ab, callback, 0x1122334455667788, top, 0x190008ff]
                    if mode == "normal" else
                    [pth, 0x713246ab, bottom, 0x778899aabbccdde0,
                     0x1122334455667788, 0xaabbccddeeff0011])
        self.assertEqual(registers, expected)
        rsp, rbp, fake_return = [int(value[key], 16) for key in ("rsp", "rbp", "return")]
        self.assertEqual(rsp, (top & ~15) - 8)
        self.assertEqual(rsp % 16, 8)
        self.assertEqual(rbp, 0)
        self.assertEqual(fake_return, 0)
        base = int(value["allocation"], 16)
        self.assertLess(base, rsp)
        self.assertLess(rsp, base + value["allocation_bytes"])

    def test_actual_source_preserves_six_arguments_and_switches_stack(self):
        with tempfile.TemporaryDirectory(prefix="mldr-entry-regression-") as temporary:
            directory = Path(temporary)
            for family in self.compilers:
                for configuration, binding in (
                    ("debug", "allocator"), ("optimized", "allocator"),
                    ("optimized", "entry-rbp"), ("optimized", "stack-rbp"),
                ):
                    with self.subTest(compiler=family, configuration=configuration, binding=binding):
                        binary = self.compile_case(directory, family, configuration, binding)
                        for mode in ("normal", "workqueue"):
                            self.check_execution(binary, mode)

    def test_archived_instruction_order_reproduces_null_transfer(self):
        with tempfile.TemporaryDirectory(prefix="mldr-entry-negative-") as temporary:
            for family in self.compilers:
                with self.subTest(compiler=family):
                    binary = self.compile_case(Path(temporary), family, "optimized", "entry-rbp", True)
                    result = subprocess.run([str(binary), "normal"], capture_output=True,
                                            text=True, timeout=5)
                    self.assertEqual(result.returncode, -signal.SIGSEGV,
                                     {"stdout": result.stdout, "stderr": result.stderr})
                    self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
