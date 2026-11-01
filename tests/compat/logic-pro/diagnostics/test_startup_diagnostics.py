"""Focused observation safety tests; these are not Darling runtime acceptance."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "startup_debug", ROOT / "tools/compat/logic-pro/debug_launchd_startup.py")
debug = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(debug)


def stat_text(pid, parent=1, state="S", code=0, name="process ) with spaces"):
    fields = ["0"] * 50
    fields[0], fields[1], fields[19], fields[35], fields[49] = state, str(parent), "123", "17", str(code)
    return f"{pid} ({name}) " + " ".join(fields) + "\n"


class ProcessObservationTests(unittest.TestCase):
    def test_zombie_exit_status_is_parsed_at_kernel_field_52(self):
        result = debug.parse_stat(stat_text(42, state="Z", code=37 << 8))
        self.assertEqual(result["pid"], 42)
        self.assertEqual(result["comm"], "process ) with spaces")
        self.assertEqual(result["starttime"], 123)
        self.assertEqual(result["exit_code"], 37 << 8)
        self.assertEqual(result["wait_status"]["exit_status"], 37)
        self.assertFalse(result["wait_status"]["signaled"])

    def test_signal_and_core_status_are_preserved_without_guessing(self):
        result = debug.parse_stat(stat_text(42, state="Z", code=11 | 128))
        self.assertTrue(result["wait_status"]["signaled"])
        self.assertEqual(result["wait_status"]["signal"], 11)
        self.assertTrue(result["wait_status"]["core_dumped"])
        self.assertNotIn("wait_status", debug.parse_stat(stat_text(42, code=11 | 128)))
        with self.assertRaises(ValueError):
            debug.parse_stat("42 (short) S 1 0\n")

    def test_fake_proc_tree_preserves_children_streams_and_vanished_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pid, parent, children in [(40, 1, "41"), (41, 40, "42"), (42, 41, "")]:
                proc = root / str(pid)
                (proc / "task" / str(pid)).mkdir(parents=True)
                (proc / "fd").mkdir()
                (proc / "stat").write_text(stat_text(pid, parent))
                (proc / "status").write_text(f"Name:\tmldr\nNSpid:\t{pid}\t1\nThreads:\t1\n")
                (proc / "cmdline").write_bytes(b"/sbin/launchd\0")
                (proc / "wchan").write_text("hrtimer_nanosleep")
                (proc / "syscall").write_text("230 0 0 0 0 0 0 0 0")
                (proc / "task" / str(pid) / "children").write_text(children)
                (proc / "fd/2").symlink_to("/dev/console")
            value = debug.tree_snapshot(40, 41, root)
            self.assertEqual([row["pid"] for row in value["processes"]], [40, 41, 42])
            self.assertEqual(value["processes"][1]["links"]["fd/2"], "/dev/console")
            self.assertEqual(value["processes"][2]["wchan"]["text"], "hrtimer_nanosleep")
            self.assertIn("error", debug.process_record(99, root)["stat"])
            self.assertFalse(value["limit_reached"])


class SafeLogObservationTests(unittest.TestCase):
    def test_regular_files_are_bounded_and_capture_the_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "crash.log").write_bytes(b"0123456789")
            metadata, data = debug.safe_regular_bytes(root, "crash.log", 4)
            self.assertEqual(data, b"6789")
            self.assertEqual(metadata["offset"], 6)
            self.assertEqual(metadata["original_bytes"], 10)
            self.assertTrue(metadata["truncated"])

    def test_symlink_leaf_and_ancestor_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real").mkdir()
            (root / "real/log").write_text("fixture")
            (root / "leaf").symlink_to(root / "real/log")
            (root / "ancestor").symlink_to(root / "real", target_is_directory=True)
            for relative in ("leaf", "ancestor/log"):
                metadata, data = debug.safe_regular_bytes(root, relative)
                self.assertEqual(metadata["status"], "refused_or_unreadable")
                self.assertEqual(data, b"")
            for relative in ("../escape", "/absolute", "real/../leaf"):
                with self.assertRaises(ValueError):
                    debug.safe_regular_bytes(root, relative)

    def test_fifo_directory_and_device_are_never_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os.mkfifo(root / "fifo")
            (root / "directory").mkdir()
            for relative in ("fifo", "directory"):
                metadata, data = debug.safe_regular_bytes(root, relative)
                self.assertEqual(metadata["status"], "not_regular")
                self.assertEqual(data, b"")
            metadata, data = debug.safe_regular_bytes(Path("/dev"), "null")
            self.assertEqual(metadata["status"], "not_regular")
            self.assertEqual(data, b"")
            metadata, data = debug.safe_regular_bytes(root, "absent")
            self.assertEqual(metadata["status"], "missing")
            self.assertEqual(data, b"")


if __name__ == "__main__":
    unittest.main()
