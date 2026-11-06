#!/usr/bin/env python3
"""Observe one retained startup failure. This program is never a P003 gate."""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import urllib.request

SOURCE_COMMIT = "0f7f34f32de7a2b403df3d38a656b979a1a3ee7c"
SOURCE_RUN = 41281586902
REPOSITORY = "boop-bip80/MAC-OS-EMULATION"
ARTIFACTS = (
    (13074088205, "p003-build-a-" + SOURCE_COMMIT, 86691566,
     "4300110a890551c14212f38445799654938baa405082d32b06820b646640dec4"),
    (13073481591, "p003-toolchain-" + SOURCE_COMMIT, 583809890,
     "1991c3d8b49b8b00b4f3d3c553aedb785ef73e1f93fd21a8a10976384b5ae5b6"),
)
EXPECTED = {
    "package": "bb05a9f4cd3c324485bca5754640e6d32d2758e1c4c49bc75165ec90bc7e7049",
    "manifest": "6749c4019eafb98d5be9aacd968a30fd73380abc2234a704ca174c32f9e4a37d",
    "summary": "61fcecfa33f6609d4dd11e2c9cdb2903ae7c2d79f76c168d7576e882fbd013cd",
    "lock": "3a6e40c7ff65c43b554278c2b4a3adebcee84f8918f54f795bc71b632be5bd08",
    "image": "5e4ac537078188ee0a503bd6667f481536a59680eda0d2d709cc7281bab11094",
}
IMAGE_ID = "sha256:91b5d6e793b78c0206bfd7316d5ee982451b2d3f66ad6d1495be246420f25b59"
LOG_LIMIT = 256 * 1024
GUEST_LOGS = (
    "var/log/launchd-pid1.crash", "var/log/system.log",
    "private/var/log/launchd-pid1.crash", "private/var/log/system.log",
    "private/var/log/com.apple.launchd/launchd-lowlevel.system.log",
    "private/var/log/asl.log",
    "private/var/log/com.apple.launchd/launchd-debug.system.log",
    "private/var/log/com.apple.launchd/launchd-shutdown.system.log",
    "private/var/log/com.apple.launchd/launchd-perf.system.log",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def reference(path, root):
    return {"file": str(path.relative_to(root)), "bytes": path.stat().st_size,
            "sha256": digest(path)}


def prepare(args):
    """Bind downloaded payload bytes, original Actions metadata and this checkout."""
    require(re.fullmatch("[0-9a-f]{40}", args.diagnostic_commit), "Exact diagnostic SHA required")
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Unexpected Actions repository")
    require(os.environ.get("GITHUB_SHA") == args.diagnostic_commit, "Actions SHA differs")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    require(head == args.diagnostic_commit, "Checkout differs from diagnostic commit")
    source_hashes = {}
    for name in ("debug_launchd_startup.py", "review_package_archive.py", "trace_launchd_fault.py"):
        path = Path(__file__).with_name(name)
        committed = subprocess.check_output(
            ["git", "show", args.diagnostic_commit + ":tools/compat/logic-pro/" + name])
        require(path.is_file() and not path.is_symlink() and path.read_bytes() == committed,
                "Diagnostic source file differs from its declared commit: " + name)
        source_hashes[name] = hashlib.sha256(committed).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = []
    for artifact_id, name, size, sha in ARTIFACTS:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact_id}",
            headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(request, timeout=30) as response:
            item = json.load(response)
        require(item["id"] == artifact_id and item["name"] == name
                and item["size_in_bytes"] == size and item["digest"] == "sha256:" + sha
                and item["expired"] is False and item["workflow_run"]["id"] == SOURCE_RUN
                and item["workflow_run"]["head_sha"] == SOURCE_COMMIT,
                "Original Actions artifact identity differs")
        metadata.append(item)
    paths = {"package": args.package / "diagnostic-installed-prefix.tar.gz",
             "manifest": args.package / "install-first.json",
             "summary": args.package / "build-summary.json",
             "lock": args.toolchain / "toolchain.lock.json",
             "image": args.toolchain / "toolchain-image.tar.gz"}
    for key, path in paths.items():
        require(path.is_file() and not path.is_symlink() and digest(path) == EXPECTED[key],
                f"Retained {key} bytes differ from the reviewed artifact")
    require(digest(args.package / "toolchain.lock.json") == EXPECTED["lock"],
            "Build and replay toolchains differ")
    summary = json.loads(paths["summary"].read_text())
    require(summary["source_commit"] == SOURCE_COMMIT and summary["status"] == "FAIL"
            and summary["last_stage"] == "probes-first" and summary["exit_code"] == 1
            and summary["toolchain_sha256"] == EXPECTED["lock"],
            "Replay requires the exact observed startup failure")
    lock = json.loads(paths["lock"].read_text())
    require(lock["image_id"] == IMAGE_ID and lock["image_archive"]["sha256"] == EXPECTED["image"],
            "Frozen image identity differs")
    for key, name in (("manifest", "install-first.json"), ("summary", "build-summary.json"),
                      ("lock", "toolchain.lock.json")):
        shutil.copyfile(paths[key], args.output / name)
    write_json(args.output / "binding.json", {
        "schema": "darling.startup-debug.binding.v1", "acceptance_status": "NOT_EVALUATED",
        "source_commit": SOURCE_COMMIT, "source_run": SOURCE_RUN,
        "diagnostic_commit": args.diagnostic_commit, "repository": REPOSITORY,
        "artifacts": metadata, "payload_sha256": EXPECTED, "image_id": IMAGE_ID,
        "driver_sha256": source_hashes["debug_launchd_startup.py"],
        "package_reviewer_sha256": source_hashes["review_package_archive.py"],
        "fault_observer_sha256": source_hashes["trace_launchd_fault.py"],
        "host_kernel": platform.uname()._asdict(),
        "zip_identity_source": "GitHub metadata; downloaded replay payloads independently hashed",
    })
    print("Diagnostic source and retained payload bindings verified.")
    return 0


def bounded_text(path, limit=8192):
    try:
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        return {"text": data[:limit].decode("utf-8", "replace"), "truncated": len(data) > limit}
    except OSError as error:
        return {"error": str(error), "errno": error.errno}


def parse_stat(raw):
    head, separator, tail = raw.rpartition(") ")
    require(separator and " (" in head, "Malformed /proc stat")
    pid, _, comm = head.partition(" (")
    fields = tail.split()
    require(pid.isdecimal() and len(fields) >= 50, "Incomplete /proc stat")
    code = int(fields[49])  # Linux /proc/[pid]/stat field 52, a wait(2) status.
    result = {"pid": int(pid), "comm": comm, "state": fields[0], "ppid": int(fields[1]),
              "starttime": int(fields[19]), "exit_signal": int(fields[35]), "exit_code": code}
    if fields[0] == "Z":
        result["wait_status"] = {
            "raw": code, "exited": os.WIFEXITED(code), "signaled": os.WIFSIGNALED(code),
            "exit_status": os.WEXITSTATUS(code) if os.WIFEXITED(code) else None,
            "signal": os.WTERMSIG(code) if os.WIFSIGNALED(code) else None,
            "core_dumped": bool(os.WCOREDUMP(code)),
        }
    return result


def process_record(pid, proc_root=Path("/proc")):
    directory = proc_root / str(pid)
    result = {"pid": pid, "stat": bounded_text(directory / "stat")}
    if "text" not in result["stat"]:
        return result
    try:
        result["identity"] = parse_stat(result["stat"]["text"])
    except ValueError as error:
        result["stat_error"] = str(error)
        return result
    for name in ("wchan", "syscall"):
        result[name] = bounded_text(directory / name)
    command = bounded_text(directory / "cmdline", 4096)
    if "text" in command:
        command["text"] = command["text"].replace("\0", " ").strip()
    result["cmdline"] = command
    result["status"] = {}
    for line in bounded_text(directory / "status").get("text", "").splitlines():
        if line.startswith(("Name:", "State:", "PPid:", "NSpid:", "Uid:", "Gid:", "Threads:", "TracerPid:",
                            "SigPnd:", "ShdPnd:", "SigBlk:", "SigIgn:", "SigCgt:")):
            key, value = line.split(":", 1)
            result["status"][key] = value.strip()
    result["links"] = {}
    for name in ("exe", "ns/mnt", "ns/pid", "fd/0", "fd/1", "fd/2"):
        try:
            result["links"][name] = os.readlink(directory / name)
        except OSError as error:
            result["links"][name] = {"error": str(error), "errno": error.errno}
    children = bounded_text(directory / "task" / str(pid) / "children")
    result["children"] = [int(value) for value in children.get("text", "").split()
                          if value.isdecimal()][:64]
    return result


def tree_snapshot(launcher_pid, init_pid, proc_root=Path("/proc"), prefix=None):
    todo = [launcher_pid] + ([init_pid] if init_pid else [])
    seen, processes = set(), []
    while todo and len(seen) < 64:
        pid = todo.pop(0)
        if pid in seen:
            continue
        seen.add(pid)
        record = process_record(pid, proc_root)
        processes.append(record)
        todo.extend(record.get("children", []))
    result = {"launcher_pid": launcher_pid, "init_pid": init_pid, "processes": processes,
              "process_limit": 64, "limit_reached": bool(todo)}
    if prefix is not None:
        socket_path = prefix / "var/run/shellspawn.sock"
        try:
            mode = socket_path.lstat().st_mode
            result["shellspawn_socket"] = stat.S_ISSOCK(mode)
            result["shellspawn_path"] = {"path": str(socket_path), "exists": True,
                                        "file_type": stat.S_IFMT(mode)}
        except OSError as error:
            result["shellspawn_socket"] = False
            result["shellspawn_path"] = {"path": str(socket_path), "exists": False,
                                        "errno": error.errno, "error": str(error)}
    return result


def safe_regular_bytes(root, relative, limit=LOG_LIMIT):
    """Never follow a directory/leaf symlink, or read a device, socket or FIFO."""
    path = PurePosixPath(relative)
    require(not path.is_absolute() and path.parts and ".." not in path.parts
            and str(path) == relative, "Unsafe diagnostic log path")
    directory = descriptor = None
    try:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        for part in path.parts[:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                              dir_fd=directory)
            os.close(directory)
            directory = next_fd
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC,
                             dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            return {"status": "not_regular", "mode": stat.S_IFMT(before.st_mode)}, b""
        offset = max(0, before.st_size - limit)
        os.lseek(descriptor, offset, os.SEEK_SET)
        data = os.read(descriptor, limit)
        after = os.fstat(descriptor)
        return {"status": "captured", "original_bytes": before.st_size, "offset": offset,
                "limit": limit, "truncated": offset > 0 or after.st_size > offset + len(data),
                "size_after": after.st_size, "device": before.st_dev, "inode": before.st_ino,
                "mode": stat.S_IMODE(before.st_mode)}, data
    except OSError as error:
        return {"status": "missing" if error.errno == errno.ENOENT else "refused_or_unreadable",
                "errno": error.errno, "error": str(error)}, b""
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory is not None:
            os.close(directory)


def prefix_pid(prefix):
    record, data = safe_regular_bytes(prefix, ".init.pid", 64)
    if record["status"] != "captured":
        return None
    value = data.decode("ascii", "replace").strip()
    return int(value) if value.isdecimal() and int(value) > 1 else None


def collect_logs(prefix, output):
    records = []
    sources = [(Path("/dev"), "console", "native-console")]
    sources.extend((prefix, path, "guest-" + str(index)) for index, path in enumerate(GUEST_LOGS, 1))
    for root, relative, label in sources:
        record, data = safe_regular_bytes(root, relative)
        record["source"] = str(root / relative)
        if record["status"] == "captured":
            destination = output / (label + ".log")
            destination.write_bytes(data)
            record["capture"] = reference(destination, output)
        records.append(record)
    return records


def kill_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def namespace_holders(namespace):
    holders = []
    for path in Path("/proc").iterdir():
        if path.name.isdecimal():
            try:
                if os.readlink(path / "ns/mnt") == namespace:
                    holders.append(int(path.name))
            except (FileNotFoundError, ProcessLookupError):
                pass
    return sorted(holders)


def run(args):
    output, prefix, installation = args.output, args.prefix, args.installation
    require(os.geteuid() == 0, "Run in the disposable privileged container")
    require(installation == Path("/opt/darling-p003"), "Unexpected installed prefix")
    for path in (output, prefix, installation):
        require(path.is_absolute() and path.resolve() == path and path != Path("/"),
                "Canonical absolute paths required")
    require(not any(a.is_relative_to(b) or b.is_relative_to(a)
                    for a, b in ((output, prefix), (output, installation), (prefix, installation))),
            "Output, runtime and installation must not overlap")
    home = prefix.with_name(prefix.name + ".home")
    for path in (prefix, home, prefix.with_name(prefix.name + ".workdir")):
        require(not path.exists() and not path.is_symlink(), "Fresh runtime paths required")
    for path in (Path("/p003/source"), Path("/p003/build")):
        require(not path.exists() and not path.is_symlink(), "Source/build tree present")
    binding = json.loads(args.binding.read_text())
    review = json.loads(args.package_review.read_text())
    require(binding["source_commit"] == SOURCE_COMMIT
            and binding["diagnostic_commit"] == args.diagnostic_commit
            and binding["payload_sha256"] == EXPECTED
            and binding["driver_sha256"] == digest(Path(__file__))
            and binding["fault_observer_sha256"] == digest(Path(__file__).with_name("trace_launchd_fault.py")),
            "Driver/source binding differs")
    require(review["status"] == "PASS" and review["errors"] == []
            and review["source_commit"] == SOURCE_COMMIT
            and review["archive_sha256"] == EXPECTED["package"]
            and review["manifest_sha256"] == EXPECTED["manifest"]
            and review["driver_sha256"] == binding["package_reviewer_sha256"]
            and review["destination"] == str(installation), "Verified installed archive required")
    require(digest(args.toolchain_lock) == EXPECTED["lock"], "Frozen lock differs")
    output.mkdir(parents=True, exist_ok=False)
    home.mkdir()
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(home), "DPREFIX": str(prefix),
                   "LANG": "C", "LC_ALL": "C", "STUB_VERBOSE": "1"}
    for key in ("DISPLAY", "XAUTHORITY"):
        if key in os.environ:
            environment[key] = os.environ[key]
    launcher = installation / "bin/darling"
    probe = installation / "libexec/darling/usr/libexec/p003/p003_macho"
    report = {"schema": "darling.startup-debug.replay.v1", "acceptance_status": "NOT_EVALUATED",
              "source_commit": SOURCE_COMMIT, "diagnostic_commit": args.diagnostic_commit,
              "diagnostic_status": "INCOMPLETE", "errors": [], "environment": environment,
              "binding_sha256": digest(args.binding), "package_review_sha256": digest(args.package_review),
              "driver_sha256": digest(Path(__file__)), "kernel": platform.uname()._asdict(),
              "fault_observer_sha256": binding["fault_observer_sha256"],
              "probe_sha256": digest(probe), "source_and_build_absent": True}
    (output / "mountinfo.log").write_bytes(Path("/proc/self/mountinfo").read_bytes())
    argv = [str(launcher), "exec", str(probe), "hello"]
    paths = [output / ("startup." + stream + ".log") for stream in ("stdout", "stderr")]
    samples, process, startup_code, timed_out = [], None, None, False
    observer = None
    observer_output = output / "fault-observer"
    observer_paths = [output / ("observer." + stream + ".log") for stream in ("stdout", "stderr")]
    observer_argv = [sys.executable, "-u", "-B", str(Path(__file__).with_name("trace_launchd_fault.py")),
                     "--prefix", str(prefix), "--output", str(observer_output), "--timeout", "35"]
    started = time.monotonic()
    try:
        # Launch the independent waiter before the real launcher: launchd's
        # fatal handler sleeps after its first fault, leaving no safe late-attach window.
        try:
            with observer_paths[0].open("xb") as out, observer_paths[1].open("xb") as err:
                observer = subprocess.Popen(observer_argv, stdin=subprocess.DEVNULL, stdout=out,
                    stderr=err, env=environment, start_new_session=True)
            watcher_deadline = time.monotonic() + 3
            while not (observer_output / "watching.json").is_file():
                require(observer.poll() is None, "Fault observer exited before watching the prefix")
                require(time.monotonic() < watcher_deadline, "Fault observer watcher handshake timed out")
                time.sleep(0.005)
            watching = json.loads((observer_output / "watching.json").read_text())
            require(watching == {"tracer_pid": observer.pid, "prefix": str(prefix)},
                    "Fault observer watcher identity differs")
        except Exception as error:
            # Preserve the original startup/shutdown even if diagnostic attachment fails.
            report["errors"].append(f"fault observer startup: {type(error).__name__}: {error}")
        with paths[0].open("xb") as out, paths[1].open("xb") as err:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                       env=environment, start_new_session=True)
        while process.poll() is None:
            elapsed = time.monotonic() - started
            snapshot = tree_snapshot(process.pid, prefix_pid(prefix), prefix=prefix)
            snapshot["elapsed_ms"] = round(elapsed * 1000)
            samples.append(snapshot)
            if elapsed >= 40:
                timed_out = True
                kill_group(process)
                break
            time.sleep(0.1)
        startup_code = process.wait(timeout=5)
    except Exception as error:
        report["errors"].append(f"startup observation: {type(error).__name__}: {error}")
    finally:
        if process is not None and process.poll() is None:
            try:
                kill_group(process)
            except Exception as error:
                report["errors"].append(f"launcher cleanup: {type(error).__name__}: {error}")
        if process is not None:
            startup_code = process.returncode
        # Finish/detach the observer before installed shutdown; its SIGKILL
        # must never be mistaken for the original launchd failure.
        try:
            if observer is not None:
                try:
                    observer.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    observer.terminate()
                try:
                    observer.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    report["errors"].append("Fault observer did not finish bounded detach")
                    kill_group(observer)
                report["fault_observer"] = {"argv": observer_argv, "exit_code": observer.returncode}
            observer_report = observer_output / "report.json"
            value = json.loads(observer_report.read_text())
            report.setdefault("fault_observer", {}).update({
                "report": reference(observer_report, output),
                "diagnostic_status": value["diagnostic_status"],
                "fault_count": value["fault_count"], "omitted_faults": value["omitted_faults"],
                "target": value.get("target"), "cleanup": value["cleanup"]})
            require(value["schema"] == "darling.startup-debug.ptrace.v1"
                    and value["acceptance_status"] == "NOT_EVALUATED"
                    and value["driver_sha256"] == binding["fault_observer_sha256"],
                    "Fault observer evidence binding differs")
            require(value["fault_count"] > 0 and bool(value["faults"]),
                    "No fault delivery captured; startup fault not localized")
            require(observer is not None and observer.returncode == 0
                    and value["diagnostic_status"] == "COLLECTED" and value["errors"] == []
                    and value["cleanup"]["owned_remaining_tids"] == [],
                    "Fault observation incomplete: " + "; ".join(value.get("errors", [])))
        except Exception as error:
            report["errors"].append(f"fault observer collection: {type(error).__name__}: {error}")
        try:
            if process is not None:
                final = tree_snapshot(process.pid, prefix_pid(prefix), prefix=prefix)
                final["elapsed_ms"] = round((time.monotonic() - started) * 1000)
                write_json(output / "processes-before-shutdown.json", final)
            write_json(output / "startup-processes.json",
                       {"schema": "darling.startup-debug.processes.v1", "samples": samples})
        except Exception as error:
            report["errors"].append(f"process evidence: {type(error).__name__}: {error}")
        report["startup"] = {"argv": argv, "exit_code": startup_code, "timed_out": timed_out,
                             "seconds": round(time.monotonic() - started, 6)}
        # A failed observation must never skip the actual installed shutdown.
        try:
            report["logs_before_shutdown"] = collect_logs(prefix, output)
        except Exception as error:
            report["errors"].append(f"log evidence: {type(error).__name__}: {error}")
        try:
            pid = prefix_pid(prefix)
            before = process_record(pid) if pid else None
            report["server_before_shutdown"] = before
            if pid:
                shutdown_paths = [output / ("shutdown." + stream + ".log") for stream in ("stdout", "stderr")]
                with shutdown_paths[0].open("xb") as out, shutdown_paths[1].open("xb") as err:
                    shutdown = subprocess.Popen([str(launcher), "shutdown"], env=environment,
                        stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
                shutdown_timeout = False
                try:
                    shutdown.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    shutdown_timeout = True
                    kill_group(shutdown)
                report["shutdown"] = {"exit_code": shutdown.returncode, "timed_out": shutdown_timeout}
                namespace = before.get("links", {}).get("ns/mnt")
                identity = before.get("identity")
                require(identity is not None and isinstance(namespace, str),
                        "Cannot identify server for namespace teardown")
                deadline = time.monotonic() + 10
                while True:
                    now = process_record(pid).get("identity")
                    holders = namespace_holders(namespace)
                    exited = now is None or now["starttime"] != identity["starttime"]
                    report["cleanup"] = {"server_exited": exited, "namespace_holders": holders,
                                         "mount_namespace_released": not holders}
                    if exited and not holders:
                        break
                    require(time.monotonic() < deadline, "Server or namespace survived shutdown")
                    time.sleep(0.1)
                require(shutdown.returncode == 0 and not shutdown_timeout, "Installed shutdown failed")
            else:
                report["errors"].append("No recorded server PID available for installed shutdown")
        except Exception as error:
            report["errors"].append(f"cleanup observation: {type(error).__name__}: {error}")
        # The daemon inherited the startup descriptors; bind their final bytes after teardown.
        for stream, path in zip(("stdout", "stderr"), paths):
            if path.is_file():
                report["startup"][stream] = reference(path, output)
        report["diagnostic_status"] = "COLLECTED" if not report["errors"] else "COLLECTION_ERROR"
        report["evidence"] = [reference(path, output) for path in sorted(output.rglob("*")) if path.is_file()]
        write_json(output / "report.json", report)
    print(json.dumps({"diagnostic_status": report["diagnostic_status"],
                      "acceptance_status": "NOT_EVALUATED", "startup_exit_code": startup_code,
                      "report": str(output / "report.json"), "errors": report["errors"]}, sort_keys=True))
    # A successfully observed failure stays a failed Actions step.
    if report["errors"] or timed_out or startup_code is None:
        return 2
    return startup_code if startup_code >= 0 else 128 - startup_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    host = modes.add_parser("prepare")
    for name in ("package", "toolchain", "output"):
        host.add_argument("--" + name, type=Path, required=True)
    host.add_argument("--diagnostic-commit", required=True)
    runtime = modes.add_parser("run")
    for name in ("installation", "prefix", "output", "binding", "package-review", "toolchain-lock"):
        runtime.add_argument("--" + name, type=Path, required=True)
    runtime.add_argument("--diagnostic-commit", required=True)
    args = parser.parse_args()
    try:
        return prepare(args) if args.mode == "prepare" else run(args)
    except Exception as error:
        print(f"Startup diagnostic setup failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
