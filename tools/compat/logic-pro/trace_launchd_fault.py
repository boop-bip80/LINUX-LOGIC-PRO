#!/usr/bin/env python3
"""Bounded, signal-preserving Linux observer; never a Darling acceptance gate.

Run in a separate process: waitpid(__WALL) belongs exclusively to this tracer.
PTRACE_SEIZE does not stop the target. Only its thread group is observed; forked
bootstrap programs are outside the scope. No target register, memory, signal
disposition, core limit, or global kernel setting is changed.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import stat
import struct
import sys
import time

PTRACE_CONT = 7
PTRACE_GETREGS = 12
PTRACE_DETACH = 17
PTRACE_GETEVENTMSG = 0x4201
PTRACE_GETSIGINFO = 0x4202
PTRACE_SEIZE = 0x4206
PTRACE_INTERRUPT = 0x4207
PTRACE_LISTEN = 0x4208
PTRACE_EVENT_CLONE = 3
PTRACE_EVENT_EXEC = 4
PTRACE_EVENT_EXIT = 6
PTRACE_EVENT_STOP = 128
OPTIONS = (1 << PTRACE_EVENT_CLONE) | (1 << PTRACE_EVENT_EXEC) | (1 << PTRACE_EVENT_EXIT)
WALL = 0x40000000
STOP_SIGNALS = {signal.SIGSTOP, signal.SIGTSTP, signal.SIGTTIN, signal.SIGTTOU}
LIMITS = {"max_faults": 8, "stack_bytes": 4096, "instruction_bytes": 256,
          "maps_bytes": 262144, "threads": 64, "wait_events": 4096}
REGISTERS = ("r15", "r14", "r13", "r12", "rbp", "rbx", "r11", "r10", "r9",
             "r8", "rax", "rcx", "rdx", "rsi", "rdi", "orig_rax", "rip", "cs",
             "eflags", "rsp", "ss", "fs_base", "gs_base", "ds", "es", "fs", "gs")
STATUS_FIELDS = {"Name", "State", "Tgid", "Pid", "PPid", "TracerPid", "NSpid",
                 "Uid", "Gid", "Threads", "SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt"}
LIBC = ctypes.CDLL(None, use_errno=True)
LIBC.ptrace.restype = ctypes.c_long
LIBC.ptrace.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]


def ptrace(request, tid, data=0):
    ctypes.set_errno(0)
    value = ctypes.c_void_p(data) if isinstance(data, int) else ctypes.cast(data, ctypes.c_void_p)
    result = LIBC.ptrace(request, tid, None, value)
    if result == -1:
        number = ctypes.get_errno()
        if number:
            raise OSError(number, os.strerror(number), "ptrace(%d, %d)" % (request, tid))
    return result


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def read_bounded(path, limit):
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        return {"text": data[:limit].decode("utf-8", "replace"), "truncated": len(data) > limit}
    except OSError as error:
        return {"error": str(error), "errno": error.errno}


def identity(tid):
    try:
        raw = (Path("/proc") / str(tid) / "stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    head, separator, tail = raw.rpartition(") ")
    fields = tail.split()
    if not separator or len(fields) < 20 or " (" not in head:
        raise ValueError("Malformed proc stat for " + str(tid))
    return {"pid": int(head.partition(" (")[0]), "state": fields[0],
            "ppid": int(fields[1]), "starttime": int(fields[19])}


def status(tid):
    raw = read_bounded(Path("/proc") / str(tid) / "status", 16384)
    if "error" in raw:
        return raw
    result = {}
    for line in raw["text"].splitlines():
        key, separator, value = line.partition(":")
        if separator and key in STATUS_FIELDS:
            result[key] = value.strip()
    return result


def tracer_pid(tid):
    value = status(tid)
    if "error" in value:
        if value.get("errno") in (errno.ENOENT, errno.ESRCH):
            return None
        raise OSError(value.get("errno"), value["error"])
    if not value.get("TracerPid", "").isdecimal():
        raise ValueError("Missing TracerPid for " + str(tid))
    return int(value["TracerPid"])


def thread_snapshot(tid):
    base = Path("/proc") / str(tid)
    record = {"tid": tid, "status": status(tid)}
    for name, limit in (("stat", 8192), ("wchan", 1024), ("syscall", 2048)):
        record[name] = read_bounded(base / name, limit)
    for name in ("exe", "ns/mnt", "ns/pid"):
        try:
            record[name] = os.readlink(base / name)
        except OSError as error:
            record[name] = {"error": str(error), "errno": error.errno}
    return record


def task_ids(pid):
    try:
        return sorted(int(path.name) for path in (Path("/proc") / str(pid) / "task").iterdir()
                      if path.name.isdecimal())
    except (FileNotFoundError, ProcessLookupError):
        return []


def read_server_pid(prefix):
    directory = leaf = None
    try:
        directory = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        leaf = os.open(".init.pid", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                       dir_fd=directory)
        metadata = os.fstat(leaf)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > 64:
            raise ValueError("Unsafe prefix PID file")
        raw = os.read(leaf, 65).strip()
        if not raw.isdigit() or not 1 < int(raw) < (1 << 30):
            return None
        return int(raw)
    except FileNotFoundError:
        return None
    finally:
        if leaf is not None:
            os.close(leaf)
        if directory is not None:
            os.close(directory)


def terminal_event(tid, value):
    return {"tid": tid, "status": value, "exited": os.WIFEXITED(value),
            "exit_status": os.WEXITSTATUS(value) if os.WIFEXITED(value) else None,
            "signaled": os.WIFSIGNALED(value),
            "signal": os.WTERMSIG(value) if os.WIFSIGNALED(value) else None,
            "core_dumped": bool(os.WCOREDUMP(value)) if os.WIFSIGNALED(value) else False}


class Observer:
    def __init__(self, args):
        self.args = args
        self.output = args.output
        self.started = time.monotonic()
        self.deadline = self.started + args.timeout
        self.cancel_signal = None
        self.pid = None
        self.starttime = None
        self.owned = {}
        self.seen = set()
        self.detached = []
        self.initial = set()
        self.report = {
            "schema": "darling.startup-debug.ptrace.v1", "acceptance_status": "NOT_EVALUATED",
            "diagnostic_status": "INCOMPLETE", "errors": [], "tracer_pid": os.getpid(),
            "kernel": platform.uname()._asdict(),
            "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "limits": {key: LIMITS[key] for key in ("max_faults", "stack_bytes", "instruction_bytes")},
            "observation_limits": {key: LIMITS[key] for key in ("maps_bytes", "threads", "wait_events")},
            "ptrace_options": {"TRACECLONE": True, "TRACEEXEC": True, "TRACEEXIT": True,
                               "TRACEFORK": False, "TRACEVFORK": False, "EXITKILL": False},
            "scope": "one thread group; bootstrap child processes are not followed",
            "faults": [], "fault_count": 0, "omitted_faults": 0,
            "wait_events": [], "omitted_wait_events": 0, "initial_threads": [],
            "attachment": [], "traced_tids": [], "discovery": [],
        }

    def milliseconds(self):
        return round((time.monotonic() - self.started) * 1000, 3)

    def error(self, message):
        if message not in self.report["errors"]:
            if len(self.report["errors"]) < 128:
                self.report["errors"].append(message)
            else:
                self.report["omitted_errors"] = self.report.get("omitted_errors", 0) + 1

    def cancel(self, number, _frame):
        self.cancel_signal = number

    def artifact(self, name, data):
        path = self.output / name
        with path.open("xb") as stream:
            stream.write(data)
        return {"file": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def initial_snapshot(self, tid):
        if tid not in self.initial and len(self.initial) < LIMITS["threads"]:
            self.initial.add(tid)
            value = thread_snapshot(tid)
            value["elapsed_ms"] = self.milliseconds()
            self.report["initial_threads"].append(value)

    def find_target(self):
        if self.args.pid is not None:
            current = identity(self.args.pid)
            if not current or current["starttime"] != self.args.starttime:
                raise ValueError("Target PID/starttime differs or process has exited")
            if current["state"] in ("Z", "X"):
                raise ValueError("Target already exited before attachment")
            target_status = status(self.args.pid)
            if target_status.get("Tgid") != str(self.args.pid):
                raise ValueError("Explicit PID must be the thread group leader")
            return current
        prefix = self.args.prefix
        write_json(self.output / "watching.json", {"tracer_pid": os.getpid(), "prefix": str(prefix)})
        server_seen = set()
        while not self.cancel_signal and time.monotonic() < self.deadline:
            server = read_server_pid(prefix)
            if server:
                server_identity = identity(server)
                if server_identity:
                    command = read_bounded(Path("/proc") / str(server) / "cmdline", 4096)
                    argv = command.get("text", "").split("\0")
                    try:
                        executable = os.readlink(Path("/proc") / str(server) / "exe")
                    except (FileNotFoundError, ProcessLookupError):
                        executable = None
                    # The fresh prefix is created only by this replay. Bind its server's
                    # executable and argv before selecting its nested PID-namespace init.
                    if executable == "/opt/darling-p003/bin/darlingserver" and len(argv) > 1 and argv[1] == str(prefix):
                        key = (server, server_identity["starttime"])
                        if key not in server_seen:
                            server_seen.add(key)
                            if len(server_seen) > 4:
                                raise ValueError("Too many server identities during discovery")
                            self.report["discovery"].append({
                                "elapsed_ms": self.milliseconds(), "server": server_identity,
                                "snapshot": thread_snapshot(server)})
                        children = read_bounded(Path("/proc") / str(server) / "task" / str(server) / "children", 4096)
                        values = children.get("text", "").split()
                        if len(values) > LIMITS["threads"]:
                            raise ValueError("Too many server children")
                        for value in values:
                            if not value.isdecimal():
                                continue
                            child = int(value)
                            child_identity, child_status = identity(child), status(child)
                            nspid = child_status.get("NSpid", "").split()
                            if (child_identity and child_identity["ppid"] == server
                                    and len(nspid) >= 2 and nspid[-1] == "1"
                                    and child_status.get("Tgid") == str(child)
                                    and (identity(server) or {}).get("starttime") == server_identity["starttime"]):
                                self.report["server_identity"] = server_identity
                                self.report["discovery"].append({
                                    "elapsed_ms": self.milliseconds(), "target": child_identity,
                                    "snapshot": thread_snapshot(child)})
                                return child_identity
            time.sleep(0.005)
        raise TimeoutError("Cancelled or timed out before discovering namespace PID 1")

    def remember(self, tid, source):
        if tid not in self.owned:
            self.owned[tid] = {"state": "running", "signal": 0}
        if tid not in self.seen:
            self.seen.add(tid)
            if len(self.seen) > LIMITS["threads"]:
                self.error("Thread observation limit exceeded")
            else:
                self.report["attachment"].append(
                    {"tid": tid, "source": source, "elapsed_ms": self.milliseconds()})
        self.initial_snapshot(tid)

    def attach_all(self):
        for _ in range(8):
            current = identity(self.pid)
            if not current or current["starttime"] != self.starttime:
                raise ValueError("Target identity changed during attachment")
            tids = task_ids(self.pid)
            if not tids or len(tids) > LIMITS["threads"]:
                raise ValueError("Missing or excessive target thread set")
            for tid in tids:
                if tid in self.owned:
                    continue
                self.initial_snapshot(tid)
                owner = tracer_pid(tid)
                if owner is None:
                    continue
                if owner == os.getpid():
                    self.remember(tid, "automatic-clone")
                    continue
                if owner:
                    raise PermissionError("Thread %d is already traced by %d" % (tid, owner))
                try:
                    ptrace(PTRACE_SEIZE, tid, OPTIONS)
                except OSError as error:
                    owner = tracer_pid(tid)
                    if owner == os.getpid():
                        self.remember(tid, "automatic-clone-race")
                        continue
                    if owner is None or error.errno == errno.ESRCH:
                        continue
                    raise
                self.remember(tid, "seize")
            # Threads created by any seized thread inherit tracing. A second
            # enumeration closes the gap from threads that were not seized yet.
            checked = task_ids(self.pid)
            if checked and all(tracer_pid(tid) == os.getpid() for tid in checked):
                for tid in checked:
                    self.remember(tid, "automatic-clone")
                again = task_ids(self.pid)
                if again and all(tid in self.owned and tracer_pid(tid) == os.getpid() for tid in again):
                    write_json(self.output / "ready.json", {
                        "pid": self.pid, "starttime": self.starttime, "tracer_pid": os.getpid(),
                        "tids": sorted(again), "elapsed_ms": self.milliseconds()})
                    return
        raise RuntimeError("Target thread set did not become fully attached")

    def append_event(self, value):
        value["elapsed_ms"] = self.milliseconds()
        if len(self.report["wait_events"]) < LIMITS["wait_events"]:
            self.report["wait_events"].append(value)
        else:
            self.report["omitted_wait_events"] += 1
            self.error("Wait event limit exceeded")

    def event_message(self, tid):
        data = ctypes.c_ulong()
        ptrace(PTRACE_GETEVENTMSG, tid, ctypes.byref(data))
        return data.value

    def signal_info(self, tid):
        data = (ctypes.c_ubyte * 128)()
        ptrace(PTRACE_GETSIGINFO, tid, ctypes.byref(data))
        raw = bytes(data)
        signo, number, code = struct.unpack_from("=iii", raw)
        return {"signo": signo, "errno": number, "code": code,
                "address": struct.unpack_from("=Q", raw, 16)[0], "raw_hex": raw.hex()}

    def memory(self, tid, address, count, name):
        result = {"address": address, "requested_bytes": count}
        descriptor = None
        try:
            descriptor = os.open("/proc/%d/mem" % tid, os.O_RDONLY | os.O_CLOEXEC)
            data = os.pread(descriptor, count, address)
            result.update(self.artifact(name, data))
            result["partial"] = len(data) != count
        except (OSError, OverflowError) as error:
            result.update({"error": str(error), "errno": getattr(error, "errno", None), "bytes": 0})
        finally:
            if descriptor is not None:
                os.close(descriptor)
        return result

    def fault(self, tid, info):
        self.report["fault_count"] += 1
        count = self.report["fault_count"]
        if count > LIMITS["max_faults"]:
            self.report["omitted_faults"] += 1
            self.error("Fault capture limit exceeded; all signals still forwarded")
            return
        name = "fault-%02d-tid-%d" % (count, tid)
        value = {"tid": tid, "signal": signal.SIGSEGV, "elapsed_ms": self.milliseconds(),
                 "siginfo": info, "thread": thread_snapshot(tid)}
        self.report["faults"].append(value)
        data = (ctypes.c_ulonglong * len(REGISTERS))()
        ptrace(PTRACE_GETREGS, tid, ctypes.byref(data))
        value["registers"] = dict(zip(REGISTERS, map(int, data)))
        value["registers_raw_hex"] = bytes(data).hex()
        try:
            with (Path("/proc") / str(tid) / "maps").open("rb") as stream:
                maps = stream.read(LIMITS["maps_bytes"] + 1)
            value["maps"] = self.artifact(name + ".maps", maps[:LIMITS["maps_bytes"]])
            value["maps"]["truncated"] = len(maps) > LIMITS["maps_bytes"]
            if value["maps"]["truncated"]:
                self.error("Fault memory-map capture truncated")
        except OSError as error:
            value["maps"] = {"error": str(error), "errno": error.errno}
            self.error("Cannot read faulting thread memory maps")
        # An unmapped faulting address may be unreadable by definition. Preserve
        # that error with the registers/maps; never synthesize instruction bytes.
        value["stack"] = self.memory(tid, int(data[19]), LIMITS["stack_bytes"], name + ".stack.bin")
        value["instruction"] = self.memory(tid, int(data[16]), LIMITS["instruction_bytes"], name + ".instruction.bin")

    def restart(self, tid, operation, delivered=0):
        try:
            ptrace(operation, tid, delivered)
        except OSError as error:
            if error.errno == errno.ESRCH and tracer_pid(tid) in (None, 0):
                self.owned.pop(tid, None)
                return
            raise
        if operation == PTRACE_DETACH:
            self.detached.append(tid)
            self.owned.pop(tid, None)
        elif tid in self.owned:
            self.owned[tid] = {"state": "listening" if operation == PTRACE_LISTEN else "running", "signal": 0}

    def handle_wait(self, tid, wait_status, cleaning=False):
        if os.WIFEXITED(wait_status) or os.WIFSIGNALED(wait_status):
            self.append_event(terminal_event(tid, wait_status))
            self.owned.pop(tid, None)
            return
        if not os.WIFSTOPPED(wait_status):
            self.append_event({"tid": tid, "status": wait_status, "kind": "unexpected"})
            self.error("Unexpected nonterminal wait status")
            return
        event, stop_signal = wait_status >> 16, os.WSTOPSIG(wait_status)
        self.remember(tid, "wait")
        # Set pending delivery before any fallible capture so cleanup can still
        # detach with the original signal if observation itself raises.
        delivered = stop_signal if event == 0 else 0
        self.owned[tid] = {"state": "stopped", "signal": delivered}
        row = {"tid": tid, "status": wait_status, "kind": "stop", "event": event,
               "stop_signal": stop_signal}
        listening = False
        try:
            if event == PTRACE_EVENT_CLONE:
                child = self.event_message(tid)
                row["new_tid"] = child
                self.remember(child, "clone-event")
            elif event == PTRACE_EVENT_EXEC:
                old = self.event_message(tid)
                row["old_tid"] = old
                if old != tid:
                    self.owned.pop(old, None)
                row["thread"] = thread_snapshot(tid)
            elif event == PTRACE_EVENT_EXIT:
                code = self.event_message(tid)
                row["exit_event"] = terminal_event(tid, code)
            elif event == PTRACE_EVENT_STOP:
                listening = stop_signal in STOP_SIGNALS
                if stop_signal != signal.SIGTRAP and not listening:
                    self.error("Unexpected PTRACE_EVENT_STOP signal: " + str(stop_signal))
            elif event != 0:
                self.error("Unexpected ptrace event: " + str(event))
            else:
                try:
                    info = self.signal_info(tid)
                    row["siginfo"] = info
                    if info["signo"] != stop_signal:
                        self.error("Signal-delivery stop/signo mismatch")
                    if stop_signal == signal.SIGSEGV:
                        self.fault(tid, info)
                except OSError as error:
                    if error.errno == errno.EINVAL and stop_signal in STOP_SIGNALS:
                        listening, delivered = True, 0
                        self.owned[tid]["signal"] = 0
                    else:
                        raise
        except Exception as error:
            self.error("Stopped-thread observation: %s: %s" % (type(error).__name__, error))
        finally:
            self.append_event(row)
            # TRACECLONE can also report non-thread clone variants. Detach such
            # children at their first stop; this observer is scoped to launchd.
            group = status(tid).get("Tgid")
            outside_group = group is not None and group != str(self.pid)
            if cleaning or outside_group:
                self.restart(tid, PTRACE_DETACH, delivered)
            elif listening:
                self.restart(tid, PTRACE_LISTEN)
            else:
                self.restart(tid, PTRACE_CONT, delivered)

    def drain(self, cleaning=False):
        progressed = False
        for _ in range(256):
            try:
                tid, value = os.waitpid(-1, os.WNOHANG | WALL)
            except ChildProcessError:
                break
            except InterruptedError:
                continue
            if not tid:
                break
            progressed = True
            self.handle_wait(tid, value, cleaning)
        return progressed

    def cleanup(self):
        deadline = time.monotonic() + 5
        interrupted = set()
        while self.owned and time.monotonic() < deadline:
            try:
                self.drain(cleaning=True)
            except Exception as error:
                self.error("Cleanup wait: %s: %s" % (type(error).__name__, error))
            for tid, record in list(self.owned.items()):
                try:
                    owner = tracer_pid(tid)
                    if owner != os.getpid():
                        self.owned.pop(tid, None)
                        continue
                    if record["state"] == "stopped":
                        self.restart(tid, PTRACE_DETACH, record["signal"])
                    elif tid not in interrupted:
                        try:
                            ptrace(PTRACE_INTERRUPT, tid)
                            interrupted.add(tid)
                        except OSError as error:
                            if error.errno not in (errno.ESRCH, errno.EIO):
                                raise
                except Exception as error:
                    self.error("Cleanup thread %d: %s: %s" % (tid, type(error).__name__, error))
            if self.owned:
                time.sleep(0.005)
        remaining = []
        candidates = self.seen | set(self.owned)
        if self.pid is not None:
            candidates.update(task_ids(self.pid))
        for tid in sorted(candidates):
            try:
                if tracer_pid(tid) == os.getpid():
                    remaining.append(tid)
            except Exception as error:
                self.error("Cleanup ownership check: %s: %s" % (type(error).__name__, error))
        if remaining:
            self.error("Tracer-owned threads survived bounded detach")
        self.report["cleanup"] = {"owned_remaining_tids": remaining,
                                  "detached_tids": sorted(set(self.detached))}

    def run(self):
        previous = {number: signal.signal(number, self.cancel) for number in (signal.SIGTERM, signal.SIGINT)}
        try:
            self.report["core_settings"] = {
                name: read_bounded(Path(path), 8192) for name, path in (
                    ("core_pattern", "/proc/sys/kernel/core_pattern"),
                    ("core_uses_pid", "/proc/sys/kernel/core_uses_pid"),
                    ("suid_dumpable", "/proc/sys/fs/suid_dumpable"),
                    ("tracer_limits", "/proc/self/limits"))}
            current = self.find_target()
            self.pid, self.starttime = current["pid"], current["starttime"]
            self.report["target"] = current
            self.report["target_limits"] = read_bounded(Path("/proc") / str(self.pid) / "limits", 8192)
            self.attach_all()
            while self.owned:
                self.drain()
                if not self.owned:
                    break
                if self.cancel_signal:
                    self.report["cancel_signal"] = self.cancel_signal
                    self.error("Tracing cancelled before all observed threads exited")
                    break
                if time.monotonic() >= self.deadline:
                    self.report["timed_out"] = True
                    self.error("Tracing deadline expired before target exit")
                    break
                if len(self.seen) > LIMITS["threads"]:
                    break
                time.sleep(0.002)
        except Exception as error:
            self.error("%s: %s" % (type(error).__name__, error))
        finally:
            self.cleanup()
            for number, handler in previous.items():
                signal.signal(number, handler)
            self.report["traced_tids"] = sorted(self.seen)
            self.report["seconds"] = round(time.monotonic() - self.started, 6)
            self.report["diagnostic_status"] = "COLLECTED" if not self.report["errors"] else "COLLECTION_ERROR"
            self.report["evidence"] = [
                {"file": path.name, "bytes": path.stat().st_size,
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in sorted(self.output.iterdir()) if path.is_file() and path.name != "report.json"]
            write_json(self.output / "report.json", self.report)
        return 0 if not self.report["errors"] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pid", type=int)
    target.add_argument("--prefix", type=Path)
    parser.add_argument("--starttime", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() != "x86_64" or sys.byteorder != "little":
        parser.error("This register/siginfo observer requires Linux x86_64 little endian")
    if args.pid is not None and (args.pid <= 1 or args.starttime is None or args.starttime < 0):
        parser.error("--pid requires a positive exact --starttime")
    if args.prefix is not None and args.starttime is not None:
        parser.error("--starttime is only valid with --pid")
    if not 0.1 <= args.timeout <= 60:
        parser.error("--timeout must be between 0.1 and 60 seconds")
    if not args.output.is_absolute() or args.output.resolve() != args.output or args.output.exists():
        parser.error("--output must be a fresh canonical absolute directory")
    if args.prefix is not None and (not args.prefix.is_absolute() or args.prefix.resolve() != args.prefix):
        parser.error("--prefix must be a canonical absolute path")
    args.output.mkdir(parents=True, exist_ok=False)
    observer = Observer(args)
    result = observer.run()
    print(json.dumps({"diagnostic_status": observer.report["diagnostic_status"],
                      "acceptance_status": "NOT_EVALUATED",
                      "fault_count": observer.report["fault_count"],
                      "errors": observer.report["errors"]}, sort_keys=True))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
