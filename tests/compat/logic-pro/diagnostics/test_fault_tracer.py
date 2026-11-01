"""Real-kernel safety tests for the artifact-only fault observer.

These tests are not Darling runtime acceptance. Every traced PID is a child
created here; the C fixture alone sets RLIMIT_CORE=0. Missing compiler, ptrace
permissions, or an unsupported kernel must fail, never silently skip the tests.

Run on Linux x86_64 with:
    python3 -m unittest discover -s tests/compat/logic-pro/diagnostics -v
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
OBSERVER = ROOT / "tools/compat/logic-pro/trace_launchd_fault.py"
FIXTURE = Path(__file__).with_name("fault_tracer_fixture.c")
POLL = threading.Event()
LIMITS = {"max_faults": 8, "stack_bytes": 4096, "instruction_bytes": 256}
OBSERVATION_LIMITS = {"maps_bytes": 262144, "threads": 64, "wait_events": 4096}


def proc_starttime(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text()
    _, separator, fields = raw.rpartition(") ")
    if not separator:
        raise AssertionError("Malformed /proc stat for our fixture")
    return int(fields.split()[19])


def proc_status(tid: int) -> dict[str, str]:
    result = {}
    for line in Path(f"/proc/{tid}/status").read_text().splitlines():
        key, separator, value = line.partition(":")
        if separator:
            result[key] = value.strip()
    return result


def number(value) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def finish_owned_child(process: subprocess.Popen) -> None:
    """Popen retains child ownership; never send a signal to an arbitrary PID."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=7)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()


class NativeFixture:
    def __init__(self, case: unittest.TestCase, binary: Path, mode: str):
        self.case = case
        self.process = subprocess.Popen(
            [str(binary), mode], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0, start_new_session=True)
        case.addCleanup(self.close)
        self.pending = bytearray()
        self.events: list[str] = []
        ready = self.expect("READY ")
        _, pid, main_tid, address, page_size = ready.split()
        self.pid = int(pid)
        self.main_tid = int(main_tid)
        self.page_address = int(address, 0)
        self.page_size = int(page_size)
        case.assertEqual(self.pid, self.process.pid)
        case.assertEqual(self.main_tid, self.pid)
        self.starttime = proc_starttime(self.pid)

    def close(self):
        # Observers are registered after the fixture, so unittest detaches them
        # first. EOF then gives this fixture a chance to join its worker.
        if self.process.stdin is not None:
            self.process.stdin.close()
            self.process.stdin = None
        if self.process.poll() is None:
            try:
                self.process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
        finish_owned_child(self.process)

    def send(self, command: str):
        self.case.assertIsNone(self.process.poll(), self.events)
        self.process.stdin.write(command.encode("ascii"))
        self.process.stdin.flush()

    def line(self, timeout: float = 6) -> str:
        deadline = time.monotonic() + timeout
        while b"\n" not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"Fixture handshake timed out: {self.events}")
            readable, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not readable:
                raise AssertionError(f"Fixture handshake timed out: {self.events}")
            data = os.read(self.process.stdout.fileno(), 4096)
            if not data:
                status = self.process.poll()
                detail = self.process.stderr.read().decode("utf-8", "replace") if status is not None else ""
                raise AssertionError(
                    f"Fixture closed its event pipe; status={status}, "
                    f"events={self.events}, stderr={detail}")
            self.pending.extend(data)
        raw, _, tail = self.pending.partition(b"\n")
        self.pending = bytearray(tail)
        value = raw.decode("ascii")
        self.events.append(value)
        return value

    def expect(self, prefix: str, timeout: float = 6) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.line(max(0.001, deadline - time.monotonic()))
            if value.startswith(prefix):
                return value
        raise AssertionError(f"No fixture event {prefix!r}: {self.events}")

    def worker_tid(self) -> int:
        workers = [line for line in self.events if line.startswith("WORKER ")]
        self.case.assertTrue(workers, self.events)
        return int(workers[-1].split()[1])

    def recover(self, expected_count: int):
        self.send("R")
        self.case.assertEqual(self.expect("SEGV"), "SEGV")
        self.case.assertEqual(
            self.expect("RECOVERED "), f"RECOVERED {expected_count}")

    def normal_exit(self):
        self.send("Q")
        self.case.assertEqual(self.process.wait(timeout=8), 37)

    def assert_untraced(self):
        self.case.assertEqual(proc_starttime(self.pid), self.starttime)
        tids = [int(path.name) for path in Path(f"/proc/{self.pid}/task").iterdir()]
        for tid in tids:
            self.case.assertEqual(int(proc_status(tid)["TracerPid"]), 0)


class ObserverProcess:
    def __init__(self, case: unittest.TestCase, fixture: NativeFixture,
                 output: Path, timeout: float = 12, starttime: int | None = None):
        self.case = case
        self.output = output
        case.assertFalse(output.exists(), "Observer output must be fresh")
        self.stdout_path = output.with_suffix(".stdout.log")
        self.stderr_path = output.with_suffix(".stderr.log")
        self.stdout = self.stdout_path.open("wb")
        self.stderr = self.stderr_path.open("wb")
        self.process = subprocess.Popen([
            sys.executable, str(OBSERVER),
            "--pid", str(fixture.pid),
            "--starttime", str(fixture.starttime if starttime is None else starttime),
            "--output", str(output), "--timeout", str(timeout),
        ], stdout=self.stdout, stderr=self.stderr, start_new_session=True)
        case.addCleanup(self.close)

    def close(self):
        finish_owned_child(self.process)
        self.stdout.close()
        self.stderr.close()

    def log_text(self) -> str:
        return self.stdout_path.read_text(errors="replace") + self.stderr_path.read_text(
            errors="replace")

    def ready(self, fixture: NativeFixture):
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            try:
                result = json.loads((self.output / "ready.json").read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                result = None
            if result is not None:
                self.case.assertIsInstance(result, dict)
                self.case.assertEqual(proc_starttime(fixture.pid), fixture.starttime)
                tids = [int(path.name)
                        for path in Path(f"/proc/{fixture.pid}/task").iterdir()]
                self.case.assertTrue(tids)
                for tid in tids:
                    self.case.assertEqual(
                        int(proc_status(tid)["TracerPid"]), self.process.pid,
                        f"ready.json published before TID {tid} was owned")
                return result
            if self.process.poll() is not None:
                report = self.output / "report.json"
                detail = report.read_text() if report.exists() else self.log_text()
                raise AssertionError("Observer failed before attachment: " + detail)
            POLL.wait(0.005)
        raise AssertionError("Observer attachment handshake timed out: " + self.log_text())

    def report(self, successful: bool = True) -> dict:
        code = self.process.wait(timeout=8)
        self.stdout.flush()
        self.stderr.flush()
        path = self.output / "report.json"
        self.case.assertTrue(path.is_file(), self.log_text())
        value = json.loads(path.read_text())
        self.case.assertEqual(value["schema"], "darling.startup-debug.ptrace.v1")
        self.case.assertEqual(value["acceptance_status"], "NOT_EVALUATED")
        self.case.assertEqual(value["limits"], LIMITS)
        self.case.assertEqual(value["observation_limits"], OBSERVATION_LIMITS)
        self.case.assertEqual(value["cleanup"]["owned_remaining_tids"], [])
        self.case.assertIsInstance(value["cleanup"]["detached_tids"], list)
        if successful:
            self.case.assertEqual(code, 0, value)
            self.case.assertEqual(value["errors"], [], value)
            self.case.assertEqual(value["omitted_faults"], 0, value)
        else:
            self.case.assertNotEqual(code, 0, value)
            self.case.assertTrue(value["errors"], value)
        return value


class FaultObserverNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if sys.platform != "linux" or platform.machine() not in ("x86_64", "amd64"):
            raise AssertionError("Fault observer tests require Linux x86_64")
        compiler = shutil.which("cc")
        if compiler is None:
            raise AssertionError("A native C compiler is required; tests cannot skip")
        if not OBSERVER.is_file():
            raise AssertionError(f"Required observer module missing: {OBSERVER}")
        cls.build = tempfile.TemporaryDirectory(prefix="p003-fault-fixture-")
        cls.addClassCleanup(cls.build.cleanup)
        cls.binary = Path(cls.build.name) / "fault-fixture"
        result = subprocess.run([
            compiler, "-std=c11", "-O0", "-g", "-fno-omit-frame-pointer",
            "-pthread", "-Wall", "-Wextra", "-Werror",
            str(FIXTURE), "-o", str(cls.binary),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if result.returncode != 0:
            raise AssertionError("Native fixture compilation failed:\n" + result.stderr)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="p003-fault-observer-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def fixture(self, mode="existing") -> NativeFixture:
        return NativeFixture(self, self.binary, mode)

    def observer(self, fixture, name="capture", timeout=12, starttime=None):
        return ObserverProcess(self, fixture, self.root / name, timeout, starttime)

    def assert_terminal(self, report, fixture, *, signal_number=None, exit_status=None):
        events = [row for row in report["wait_events"]
                  if row["tid"] == fixture.pid
                  and (row.get("signaled") or row.get("exited"))]
        self.assertTrue(events, report["wait_events"])
        final = events[-1]
        if signal_number is not None:
            self.assertTrue(final["signaled"], final)
            self.assertEqual(final["signal"], signal_number)
            self.assertTrue(os.WIFSIGNALED(final["status"]))
            self.assertEqual(os.WTERMSIG(final["status"]), signal_number)
            self.assertEqual(final["core_dumped"], bool(os.WCOREDUMP(final["status"])))
        else:
            self.assertTrue(final["exited"], final)
            self.assertEqual(final["exit_status"], exit_status)
            self.assertTrue(os.WIFEXITED(final["status"]))
            self.assertEqual(os.WEXITSTATUS(final["status"]), exit_status)

    def assert_blob(self, observer, metadata, limit):
        relative = Path(metadata["file"])
        self.assertFalse(relative.is_absolute())
        self.assertNotIn("..", relative.parts)
        path = observer.output / relative
        self.assertFalse(path.is_symlink())
        self.assertTrue(path.resolve().is_relative_to(observer.output.resolve()))
        data = path.read_bytes()
        self.assertEqual(len(data), metadata["bytes"])
        self.assertGreater(len(data), 0)
        self.assertLessEqual(len(data), limit)
        self.assertEqual(hashlib.sha256(data).hexdigest(), metadata["sha256"])
        return data

    def assert_fault(self, observer, fault, fixture, tid):
        self.assertEqual(fault["tid"], tid)
        self.assertEqual(fault["signal"], signal.SIGSEGV)
        self.assertEqual(fault["siginfo"]["signo"], signal.SIGSEGV)
        self.assertEqual(fault["siginfo"]["code"], 2)  # SEGV_ACCERR, PROT_NONE.
        self.assertEqual(number(fault["siginfo"]["address"]), fixture.page_address)
        self.assertEqual(len(bytes.fromhex(fault["siginfo"]["raw_hex"])), 128)
        rip, rsp = number(fault["registers"]["rip"]), number(fault["registers"]["rsp"])
        self.assertGreater(rip, 0)
        self.assertGreater(rsp, 0)
        self.assertEqual(number(fault["stack"]["address"]), rsp)
        self.assertEqual(number(fault["instruction"]["address"]), rip)
        self.assert_blob(observer, fault["stack"], LIMITS["stack_bytes"])
        self.assert_blob(observer, fault["instruction"], LIMITS["instruction_bytes"])
        maps = self.assert_blob(observer, fault["maps"], OBSERVATION_LIMITS["maps_bytes"]).decode()
        executable_matches = []
        for line in maps.splitlines():
            fields = line.split(maxsplit=5)
            low, high = [int(value, 16) for value in fields[0].split("-")]
            if low <= rip < high and "x" in fields[1]:
                executable_matches.append(fields)
        self.assertEqual(len(executable_matches), 1)
        self.assertEqual(Path(executable_matches[0][5]).resolve(), self.binary.resolve())

    def test_preexisting_worker_fault_is_captured_and_original_signal_terminates(self):
        fixture = self.fixture()
        worker = fixture.worker_tid()
        observer = self.observer(fixture)
        observer.ready(fixture)
        fixture.send("F")
        self.assertEqual(fixture.process.wait(timeout=8), -signal.SIGSEGV)
        report = observer.report()
        self.assertEqual(report["fault_count"], 1)
        self.assertEqual(len(report["faults"]), 1)
        self.assert_fault(observer, report["faults"][0], fixture, worker)
        self.assert_terminal(report, fixture, signal_number=signal.SIGSEGV)
        self.assertIn(worker, report["traced_tids"])

    def test_new_and_short_lived_threads_are_followed_without_losing_worker_fault(self):
        fixture = self.fixture("late")
        observer = self.observer(fixture)
        observer.ready(fixture)
        fixture.send("B")
        self.assertEqual(fixture.expect("CHURNED"), "CHURNED")
        fixture.send("C")
        worker = int(fixture.expect("WORKER ").split()[1])
        self.assertEqual(int(proc_status(worker)["TracerPid"]), observer.process.pid)
        fixture.send("F")
        self.assertEqual(fixture.process.wait(timeout=8), -signal.SIGSEGV)
        report = observer.report()
        self.assertEqual(report["fault_count"], 1)
        self.assert_fault(observer, report["faults"][0], fixture, worker)
        self.assertIn(worker, report["traced_tids"])
        self.assertGreaterEqual(len(set(report["traced_tids"])), 10)
        self.assert_terminal(report, fixture, signal_number=signal.SIGSEGV)

    def test_real_sigtrap_is_forwarded_exactly_once(self):
        fixture = self.fixture()
        observer = self.observer(fixture)
        observer.ready(fixture)
        fixture.send("T")
        self.assertEqual(fixture.expect("TRAP"), "TRAP")
        self.assertEqual(fixture.expect("TRAP_RETURN "), "TRAP_RETURN 1")
        fixture.normal_exit()
        report = observer.report()
        self.assertEqual(fixture.events.count("TRAP"), 1)
        self.assertEqual(report["faults"], [])
        self.assertEqual(report["fault_count"], 0)
        self.assert_terminal(report, fixture, exit_status=37)

    def test_guest_fatal_handler_runs_before_repeated_fault_terminates(self):
        fixture = self.fixture("fatal")
        worker = fixture.worker_tid()
        observer = self.observer(fixture)
        observer.ready(fixture)
        fixture.send("F")
        self.assertEqual(fixture.expect("FATAL_HANDLER"), "FATAL_HANDLER")
        self.assertEqual(fixture.process.wait(timeout=8), -signal.SIGSEGV)
        report = observer.report()
        self.assertEqual(report["fault_count"], 2)
        self.assertEqual(len(report["faults"]), 2)
        for fault in report["faults"]:
            self.assert_fault(observer, fault, fixture, worker)
        self.assert_terminal(report, fixture, signal_number=signal.SIGSEGV)

    def test_fault_before_attachment_is_not_claimed_and_later_fault_can_recover(self):
        fixture = self.fixture("recover")
        fixture.recover(1)
        observer = self.observer(fixture)
        observer.ready(fixture)
        fixture.recover(2)
        fixture.normal_exit()
        report = observer.report()
        self.assertEqual(report["fault_count"], 1)
        self.assertEqual(len(report["faults"]), 1)
        self.assert_fault(observer, report["faults"][0], fixture, fixture.pid)
        self.assert_terminal(report, fixture, exit_status=37)

    def test_capture_quota_is_bounded_but_all_original_faults_reach_handler(self):
        fixture = self.fixture("recover")
        observer = self.observer(fixture)
        observer.ready(fixture)
        for count in range(1, 12):
            fixture.recover(count)
        fixture.normal_exit()
        report = observer.report(successful=False)
        self.assertEqual(report["fault_count"], 11)
        self.assertEqual(report["omitted_faults"], 3)
        self.assertEqual(len(report["faults"]), 8)
        self.assertEqual(fixture.events.count("SEGV"), 11)
        for fault in report["faults"]:
            self.assert_fault(observer, fault, fixture, fixture.pid)
        self.assert_terminal(report, fixture, exit_status=37)

    def test_another_tracers_ownership_is_refused_without_disturbing_it(self):
        fixture = self.fixture()
        first = self.observer(fixture, "first")
        first.ready(fixture)
        second = self.observer(fixture, "second")
        report = second.report(successful=False)
        self.assertFalse((second.output / "ready.json").exists())
        self.assertEqual(report["faults"], [])
        self.assertEqual(int(proc_status(fixture.pid)["TracerPid"]), first.process.pid)
        fixture.send("T")
        self.assertEqual(fixture.expect("TRAP"), "TRAP")
        self.assertEqual(fixture.expect("TRAP_RETURN "), "TRAP_RETURN 1")
        fixture.normal_exit()
        first_report = first.report()
        self.assert_terminal(first_report, fixture, exit_status=37)

    def test_starttime_mismatch_never_attaches_or_signals_target(self):
        fixture = self.fixture()
        observer = self.observer(fixture, starttime=fixture.starttime + 1)
        report = observer.report(successful=False)
        self.assertFalse((observer.output / "ready.json").exists())
        self.assertEqual(report["traced_tids"], [])
        self.assertEqual(report["faults"], [])
        fixture.assert_untraced()
        fixture.send("T")
        self.assertEqual(fixture.expect("TRAP"), "TRAP")
        self.assertEqual(fixture.expect("TRAP_RETURN "), "TRAP_RETURN 1")
        fixture.normal_exit()

    def test_timeout_detaches_all_owned_threads_and_fixture_still_runs(self):
        fixture = self.fixture()
        observer = self.observer(fixture, timeout=1.5)
        observer.ready(fixture)
        began = time.monotonic()
        report = observer.report(successful=False)
        self.assertLess(time.monotonic() - began, 6)
        self.assertTrue(report["cleanup"]["detached_tids"], report)
        fixture.assert_untraced()
        fixture.send("T")
        self.assertEqual(fixture.expect("TRAP"), "TRAP")
        self.assertEqual(fixture.expect("TRAP_RETURN "), "TRAP_RETURN 1")
        fixture.normal_exit()

    def test_group_stop_is_preserved_until_original_parent_continues_child(self):
        fixture = self.fixture("late")
        observer = self.observer(fixture)
        observer.ready(fixture)
        fixture.send("SP")
        self.assertEqual(fixture.expect("STOPPING"), "STOPPING")
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if proc_status(fixture.pid)["State"].startswith(("T", "t")):
                break
            POLL.wait(0.005)
        else:
            self.fail("SIGSTOP did not become a preserved group stop")
        self.assertNotIn(b"RESUMED", fixture.pending)
        readable, _, _ = select.select([fixture.process.stdout], [], [], 0.1)
        self.assertEqual(readable, [], "Observer suppressed the group stop")
        fixture.process.send_signal(signal.SIGCONT)
        self.assertEqual(fixture.expect("RESUMED"), "RESUMED")
        self.assertEqual(fixture.expect("PONG"), "PONG")
        fixture.normal_exit()
        report = observer.report()
        self.assert_terminal(report, fixture, exit_status=37)

    def test_observer_does_not_consume_the_launchers_other_child_wait_status(self):
        fixture = self.fixture()
        observer = self.observer(fixture)
        observer.ready(fixture)
        other = subprocess.Popen(
            [sys.executable, "-c", "raise SystemExit(23)"],
            start_new_session=True)
        self.addCleanup(finish_owned_child, other)
        fixture.send("T")
        self.assertEqual(fixture.expect("TRAP"), "TRAP")
        self.assertEqual(fixture.expect("TRAP_RETURN "), "TRAP_RETURN 1")
        self.assertEqual(other.wait(timeout=5), 23)
        fixture.send("F")
        self.assertEqual(fixture.process.wait(timeout=8), -signal.SIGSEGV)
        report = observer.report()
        self.assert_terminal(report, fixture, signal_number=signal.SIGSEGV)


class FaultObserverStateTests(unittest.TestCase):
    """Exercise dangerous stop transitions without touching a real process."""

    @classmethod
    def setUpClass(cls):
        specification = importlib.util.spec_from_file_location(
            "p003_fault_observer_for_tests", OBSERVER)
        cls.module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.module)

    def setUp(self):
        self.tid = 1234567  # Never passed to a real syscall; ptrace is mocked below.
        args = SimpleNamespace(output=Path("/unused-p003-unit-test"), timeout=1,
                               pid=self.tid, starttime=1, prefix=None)
        self.observer = self.module.Observer(args)
        self.observer.pid = self.tid
        self.observer.starttime = 1
        self.observer.initial_snapshot = mock.Mock()
        self.observer.signal_info = mock.Mock(
            return_value={"signo": signal.SIGSEGV, "code": 2, "address": 4096,
                          "raw_hex": "00" * 128})
        self.observer.fault = mock.Mock()
        self.backend = mock.patch.object(self.module, "ptrace").start()
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(self.module, "status",
                          return_value={"Tgid": str(self.tid)}).start()

    @staticmethod
    def stopped(signum, event=0):
        return (event << 16) | (signum << 8) | 0x7f

    def test_observation_failure_still_forwards_original_sigsegv(self):
        self.observer.fault.side_effect = OSError(5, "fixture artifact read failed")
        self.observer.handle_wait(self.tid, self.stopped(signal.SIGSEGV))
        self.backend.assert_called_once_with(self.module.PTRACE_CONT, self.tid,
                                             signal.SIGSEGV)
        self.assertTrue(self.observer.report["errors"])
        self.assertEqual(self.observer.owned[self.tid]["state"], "running")

    def test_cleanup_interrupt_racing_real_sigsegv_detaches_with_original_signal(self):
        self.observer.fault.side_effect = OSError(5, "fixture capture failed")
        self.observer.handle_wait(
            self.tid, self.stopped(signal.SIGSEGV), cleaning=True)
        self.backend.assert_called_once_with(self.module.PTRACE_DETACH, self.tid,
                                             signal.SIGSEGV)
        self.assertEqual(self.observer.owned, {})
        self.assertEqual(self.observer.detached, [self.tid])

    def test_real_sigtrap_delivery_is_not_swallowed_as_a_synthetic_stop(self):
        self.observer.signal_info.return_value = {
            "signo": signal.SIGTRAP, "code": -6, "address": 0, "raw_hex": "00" * 128}
        self.observer.handle_wait(self.tid, self.stopped(signal.SIGTRAP))
        self.backend.assert_called_once_with(self.module.PTRACE_CONT, self.tid,
                                             signal.SIGTRAP)
        self.observer.fault.assert_not_called()
        self.assertEqual(self.observer.report["errors"], [])

    def test_synthetic_interrupt_trap_is_never_injected(self):
        self.observer.handle_wait(
            self.tid, self.stopped(signal.SIGTRAP, self.module.PTRACE_EVENT_STOP))
        self.backend.assert_called_once_with(self.module.PTRACE_CONT, self.tid, 0)
        self.observer.signal_info.assert_not_called()
        self.assertEqual(self.observer.report["errors"], [])

    def test_group_stop_uses_listen_without_inventing_a_continue_signal(self):
        self.observer.handle_wait(
            self.tid, self.stopped(signal.SIGSTOP, self.module.PTRACE_EVENT_STOP))
        self.backend.assert_called_once_with(self.module.PTRACE_LISTEN, self.tid, 0)
        self.assertEqual(self.observer.owned[self.tid]["state"], "listening")
        self.observer.signal_info.assert_not_called()
        self.assertEqual(self.observer.report["errors"], [])

    def test_clone_event_remembers_new_thread_before_resuming_parent(self):
        child = self.tid + 1
        self.observer.event_message = mock.Mock(return_value=child)
        self.observer.handle_wait(
            self.tid, self.stopped(signal.SIGTRAP, self.module.PTRACE_EVENT_CLONE))
        self.backend.assert_called_once_with(self.module.PTRACE_CONT, self.tid, 0)
        self.assertIn(child, self.observer.owned)
        self.assertIn(child, self.observer.seen)
        self.observer.signal_info.assert_not_called()
        self.assertEqual(self.observer.report["errors"], [])

    def test_failed_siginfo_read_does_not_swallow_real_signal(self):
        self.observer.signal_info.side_effect = OSError(5, "fixture GETSIGINFO error")
        self.observer.handle_wait(self.tid, self.stopped(signal.SIGTRAP))
        self.backend.assert_called_once_with(self.module.PTRACE_CONT, self.tid,
                                             signal.SIGTRAP)
        self.assertTrue(self.observer.report["errors"])


if __name__ == "__main__":
    unittest.main()
