"""Prove failed startup retains real process evidence without changing outcomes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools/compat/logic-pro"))
import run_build_probes as probes


class StartupObservationTests(unittest.TestCase):
    def test_actual_init_and_descendants_are_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prefix, proc_root = root / "runtime", root / "proc"
            prefix.mkdir()
            (prefix / ".init.pid").write_text("301\n")
            for pid, parent, children in ((300, "0", "301"), (301, "300", "302"), (302, "301", "")):
                path = proc_root / str(pid)
                (path / "task" / str(pid)).mkdir(parents=True)
                (path / "status").write_text(
                    f"Name:\tprobe-{pid}\nState:\tS (sleeping)\nPPid:\t{parent}\n"
                    f"NSpid:\t{pid} {pid-300+1}\nUid:\t1000 1000 1000 1000\n")
                (path / "cmdline").write_bytes(f"/opt/probe-{pid}\0arg\0".encode())
                (path / "task" / str(pid) / "children").write_text(children)
            observed = probes.startup_snapshot(prefix, 300, proc_root)
            self.assertEqual(observed["init_pid"], 301)
            self.assertEqual([row["pid"] for row in observed["processes"]], [300, 301, 302])
            self.assertEqual(observed["processes"][2]["status"]["PPid"], "301")
            self.assertEqual(observed["processes"][0]["cmdline"], "/opt/probe-300 arg")
            self.assertFalse(observed["shellspawn_socket"])

    def test_socket_reports_a_real_unix_socket(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            sock = prefix / "var/run/shellspawn.sock"
            sock.parent.mkdir(parents=True)
            # This host sandbox may forbid AF_UNIX creation. Require the real
            # Path.is_socket check and the exact guest-prefix socket path.
            with mock.patch.object(Path, "is_socket", autospec=True,
                                   side_effect=lambda path: path == sock) as checked:
                self.assertTrue(probes.startup_snapshot(prefix, 41)["shellspawn_socket"])
                checked.assert_called_once_with(sock)

    def test_missing_processes_are_explicit_not_an_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "prefix"
            prefix.mkdir()
            (prefix / ".init.pid").write_text("999999999\n")
            observed = probes.startup_snapshot(prefix, 999999998, Path(tmp) / "proc")
            self.assertEqual(observed["init_pid"], 999999999)
            self.assertTrue(all(row["vanished_or_inaccessible"] for row in observed["processes"]))

    def test_only_first_real_startup_command_gets_bounded_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaign = probes.Campaign(root / "install", root, root / "runtime")
            self.assertEqual(campaign.command(
                "macho-known-vector",
                [sys.executable, "-B", "-c", "import time; time.sleep(0.7)"], timeout=3), "")
            trace = campaign.startup_trace
            self.assertIsNotNone(trace)
            path = root / trace["file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), trace["sha256"])
            rows = json.loads(path.read_text())["samples"]
            self.assertEqual(trace["sample_count"], len(rows))
            self.assertGreaterEqual(len(rows), 2)
            self.assertTrue(all("launcher_pid" in row for row in rows))
            previous_sha = trace["sha256"]
            self.assertEqual(campaign.command("other", [sys.executable, "-B", "-c", "pass"]), "")
            self.assertEqual(campaign.startup_trace["sha256"], previous_sha)

    def test_initial_failure_is_not_overridden_by_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaign = probes.Campaign(root / "install", root, root / "runtime")
            with self.assertRaisesRegex(probes.ProbeFailure, "expected exit 0; actual 7"):
                campaign.command("macho-known-vector", [sys.executable, "-B", "-c",
                                  "raise SystemExit(7)"], timeout=2)
            self.assertEqual(campaign.records[0]["exit_code"], 7)
            self.assertIsNotNone(campaign.startup_trace)
            self.assertTrue((root / "startup-processes.json").is_file())


if __name__ == "__main__":
    unittest.main()
