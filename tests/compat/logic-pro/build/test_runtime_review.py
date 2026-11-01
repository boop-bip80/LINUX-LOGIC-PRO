"""Independent regressions for real runtime startup and shutdown hazards.

These tests reproduce problems at the host/probe boundary. They do not replace
the required installed Darling execution, X11 screenshots, or clean builds.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "runtime_review_probes", ROOT / "tools/compat/logic-pro/run_build_probes.py")
probes = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probes)


def fake_process(root, pid, starttime=123456, namespace="mnt:[12345]", name="server with ) brackets"):
    directory = root / str(pid)
    (directory / "ns").mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(starttime)] + ["0"] * 30
    (directory / "stat").write_text(f"{pid} ({name}) " + " ".join(fields) + "\n")
    (directory / "ns/mnt").symlink_to(namespace)
    return directory


class RuntimeBoundaryReview(unittest.TestCase):
    def test_startup_receives_fresh_explicit_home_without_private_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.dict(os.environ, {"HOME": "/unrelated-private-home",
                                              "LD_PRELOAD": "/unrelated-injection",
                                              "API_TOKEN": "dummy-fixture"}, clear=True):
                campaign = probes.Campaign(root / "installation", root, root / "prefix")
            self.assertEqual(campaign.env["HOME"], str(root / "prefix.home"))
            self.assertTrue(campaign.home.is_dir())
            self.assertEqual(list(campaign.home.iterdir()), [])
            self.assertNotIn("LD_PRELOAD", campaign.env)
            self.assertNotIn("API_TOKEN", campaign.env)

    def test_old_controlled_home_cannot_supply_reinstall_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            home = root / "prefix.home"
            home.mkdir()
            (home / "previous-library").write_text("stale dependency")
            with self.assertRaises(probes.ProbeFailure):
                probes.Campaign(root / "installation", root, root / "prefix")

    def test_process_identity_parses_kernel_comm_with_spaces_and_parentheses(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            fake_process(proc, 123)
            self.assertEqual(probes.process_identity(123, proc),
                             {"pid": 123, "starttime": 123456, "state": "S",
                              "mount_namespace": "mnt:[12345]"})
            self.assertIsNone(probes.process_identity(124, proc))

    def test_namespace_holders_are_checked_outside_caller_mountinfo(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            fake_process(proc, 9, namespace="mnt:[caller]")
            fake_process(proc, 33)
            fake_process(proc, 17)
            (proc / "self").mkdir()
            (proc / "200").mkdir()  # process vanished during the enumeration
            self.assertEqual(probes.namespace_users("mnt:[12345]", proc), [17, 33])

    def test_malformed_process_identity_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            target = fake_process(proc, 123)
            (target / "stat").write_text("incomplete\n")
            with self.assertRaises(probes.ProbeFailure):
                probes.process_identity(123, proc)

    def test_persistent_daemon_descriptors_do_not_timeout_completed_command(self):
        # Darling starts a persistent server inheriting standard descriptors.
        # communicate() with pipes waits for that daemon's EOF even when the
        # actual launcher has already returned. A regular evidence file does
        # not have that accidental lifetime dependency.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child_file = root / "daemon.pid"
            script = root / "daemon_fixture.py"
            script.write_text(
                "import os, pathlib, time\n"
                "pid = os.fork()\n"
                "if pid == 0:\n"
                "    time.sleep(5)\n"
                "    os._exit(0)\n"
                f"pathlib.Path({str(child_file)!r}).write_text(str(pid))\n"
                "print('launcher finished', flush=True)\n")
            campaign = probes.Campaign(root / "installation", root, root / "prefix")
            try:
                result = campaign.command("persistent-descriptor", [sys.executable, str(script)], timeout=1)
                self.assertEqual(result, "launcher finished\n")
                self.assertEqual(campaign.records[-1]["exit_code"], 0)
                self.assertFalse(campaign.records[-1]["timed_out"])
            finally:
                if child_file.exists():
                    try:
                        os.kill(int(child_file.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_shutdown_rejects_surviving_private_namespace_holder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / "prefix"
            prefix.mkdir()
            (prefix / ".init.pid").write_text("123\n")
            campaign = probes.Campaign(root / "installation", root, prefix)
            campaign.started = True
            identity = {"pid": 123, "starttime": 999, "state": "S", "mount_namespace": "mnt:[private]"}
            with mock.patch.object(campaign, "command", return_value=""), \
                 mock.patch.object(probes, "process_identity", side_effect=[identity, None]), \
                 mock.patch.object(probes, "namespace_users", return_value=[456]), \
                 mock.patch.object(probes.os, "readlink", return_value="mnt:[caller]"), \
                 mock.patch.object(probes.time, "monotonic", side_effect=[0, 0, 11]), \
                 mock.patch.object(probes.time, "sleep"):
                with self.assertRaisesRegex(probes.ProbeFailure, "survived shutdown"):
                    campaign.shutdown()
            self.assertIsNone(campaign.lifecycle)

    def test_shutdown_requires_server_exit_and_no_namespace_holders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / "prefix"
            prefix.mkdir()
            (prefix / ".init.pid").write_text("123\n")
            campaign = probes.Campaign(root / "installation", root, prefix)
            campaign.started = True
            identity = {"pid": 123, "starttime": 999, "state": "S", "mount_namespace": "mnt:[private]"}
            with mock.patch.object(campaign, "command", return_value=""), \
                 mock.patch.object(probes, "process_identity", side_effect=[identity, None]), \
                 mock.patch.object(probes, "namespace_users", return_value=[]), \
                 mock.patch.object(probes.os, "readlink", return_value="mnt:[caller]"):
                campaign.shutdown()
            self.assertTrue(campaign.lifecycle["server_exited"])
            self.assertTrue(campaign.lifecycle["mount_namespace_released"])
            self.assertEqual(campaign.lifecycle["namespace_holders_after"], [])


if __name__ == "__main__":
    unittest.main()
