"""Independent rejection tests for P003 aggregate evidence validation.

Fixtures here are deliberately synthetic parser inputs, never claimed as a
Darling runtime result. Their mutations reproduce missing-evidence false passes.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import compare_p003 as gate


def xwd(ready):
    width, height = 200, 120
    header = [100, 7, 2, 24, width, height, 0, 0, 32, 0, 32, 32,
              width * 4, 4, 0xff0000, 0xff00, 0xff, 8, 256, 0, width, height, 0, 0, 0]
    colors = (0x00ff00, 0xffff00) if ready else (0xff0000, 0x0000ff)
    row = b"".join(value.to_bytes(4, "little") * (width // 2) for value in colors)
    return struct.pack(">25I", *header) + row * height


def fixture(root):
    root.mkdir(parents=True)
    nonce = "0123456789abcdef"

    def file(name, data):
        path = root / name
        path.write_bytes(data)
        return {"file": name, "sha256": hashlib.sha256(data).hexdigest()}

    def command(label, output="", expected=0, error=""):
        return {"label": label, "argv": ["fixture", label], "exit_code": expected,
                "expected_exit_code": expected, "timed_out": False,
                "stdout": file(label + ".stdout.log", output.encode()),
                "stderr": file(label + ".stderr.log", error.encode())}

    commands = []
    for label, value in (("macho-known-vector", "hello"), ("macho-nonce", nonce),
                         ("macho-boundary-64", "a" * 64)):
        commands.append(command(label, f"P003_MACHO nonce={value} hash={gate.probes.fnv1a(value):08x}\n"))
    for label, name in (("macho-reject-65", "macho"), ("macho-invalid", "macho"),
                        ("foundation-invalid", "foundation"), ("gui-invalid", "gui")):
        error = "P003_" + name.upper() + "_ERROR invalid " + ("challenge" if name == "gui" else "arguments") + "\n"
        commands.append(command(label, expected=64, error=error))
    commands.append(command("foundation", f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil\n"))
    for label in ("gui-focus", "gui-move", "gui-click", "gui-type", "gui-acknowledge"):
        commands.append(command(label))
    images = "".join(f"P003_IMAGE /System/Library/Frameworks/{name}.framework/Versions/{version}/{name}\n"
                     for name, version in gate.probes.FRAMEWORKS.items())
    commands.append(command("gui", images + f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1\n"))
    commands.append(command("shutdown"))
    screenshots = {}
    for name, ready in (("before", False), ("after", True)):
        data = xwd(ready)
        screenshots[name] = {**file("gui-" + name + ".xwd", data),
                             "pixels": gate.probes.xwd_sample(data),
                             "png": file("gui-" + name + ".png", gate.probes.xwd_png(data))}
    binaries, entries = {}, []
    for name in ("p003_macho", "p003_foundation", "p003_gui"):
        value = hashlib.sha256(name.encode()).hexdigest()
        binaries[name] = {"path": "/opt/darling-p003/libexec/darling/usr/libexec/p003/" + name,
                          "sha256": value, "bytes": 100, "format": "Mach-O 64-bit x86_64 MH_EXECUTE"}
        entries.append({"path": "libexec/darling/usr/libexec/p003/" + name,
                        "kind": "file", "mode": 0o755, "sha256": value, "size": 100})
    report = {"schema": "logic-pro-p003-probes-v1", "status": "PASSED", "passed": True,
              "errors": [], "source_revision": "a" * 40, "nonce": nonce,
              "lifecycle": {"server_exited": True, "mount_namespace_released": True,
                            "namespace_holders_after": []},
              "cases": [{"name": name, "status": "PASSED"} for name in sorted(gate.CASES)],
              "commands": commands, "screenshots": screenshots, "binaries": binaries}
    (root / "report.json").write_text(json.dumps(report))
    return report, {"entries": entries}


class ProbeEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "runtime"
        self.report, self.install = fixture(self.root)

    def save(self):
        (self.root / "report.json").write_text(json.dumps(self.report))

    def test_complete_synthetic_report_is_accepted_for_parser_testing(self):
        self.assertEqual(gate.validate_probes(self.root, self.install)["cases"], 10)

    def test_claimed_negative_case_without_raw_command_is_rejected(self):
        for missing in ("macho-reject-65", "macho-invalid", "foundation-invalid", "gui-invalid"):
            with self.subTest(missing=missing):
                original = self.report["commands"]
                self.report["commands"] = [row for row in original if row["label"] != missing]
                self.save()
                with self.assertRaises((ValueError, KeyError)):
                    gate.validate_probes(self.root, self.install)
                self.report["commands"] = original

    def test_claimed_shutdown_without_raw_command_is_rejected(self):
        self.report["commands"] = [row for row in self.report["commands"] if row["label"] != "shutdown"]
        self.save()
        with self.assertRaises((ValueError, KeyError)):
            gate.validate_probes(self.root, self.install)

    def test_required_external_input_command_cannot_be_omitted(self):
        self.report["commands"] = [row for row in self.report["commands"] if row["label"] != "gui-click"]
        self.save()
        with self.assertRaises((ValueError, KeyError)):
            gate.validate_probes(self.root, self.install)

    def test_report_cannot_redefine_a_failed_positive_exit_as_expected(self):
        row = next(row for row in self.report["commands"] if row["label"] == "macho-known-vector")
        row["exit_code"] = row["expected_exit_code"] = 42
        self.save()
        with self.assertRaises(ValueError):
            gate.validate_probes(self.root, self.install)

    def test_report_cannot_redefine_a_negative_success_as_expected(self):
        row = next(row for row in self.report["commands"] if row["label"] == "macho-reject-65")
        row["exit_code"] = row["expected_exit_code"] = 0
        self.save()
        with self.assertRaises(ValueError):
            gate.validate_probes(self.root, self.install)

    def test_modified_raw_log_is_rejected(self):
        (self.root / "macho-known-vector.stdout.log").write_text("forged\n")
        with self.assertRaises(ValueError):
            gate.validate_probes(self.root, self.install)

    def test_same_size_wrong_probe_binary_is_rejected(self):
        self.install["entries"][0]["sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            gate.validate_probes(self.root, self.install)

    def test_screenshot_cannot_borrow_another_file_through_symlink(self):
        path = self.root / "gui-before.xwd"
        destination = path.with_name("other.xwd")
        path.rename(destination)
        path.symlink_to(destination.name)
        with self.assertRaises(ValueError):
            gate.validate_probes(self.root, self.install)


class CrossBuildGateTests(unittest.TestCase):
    def baseline(self):
        return {"summary": {"build_id": "a", "toolchain_sha256": "a" * 64, "source_lock_sha256": "b" * 64,
                            "configuration": {"components": "cli,gui"}, "installation_prefix": "/opt/darling-p003",
                            "source_date_epoch": "123"}, "source": {"submodules": []},
                "entries": {"binary": {"path": "binary", "kind": "file", "mode": 0o755,
                                        "size": 4, "sha256": "c" * 64}},
                "runtime": [{"nonce": "0" * 16, "cases": 10}, {"nonce": "1" * 16, "cases": 10}],
                "evidence": {}}

    def test_output_nondeterminism_is_enumerated_without_claiming_phase_pass(self):
        a = self.baseline()
        b = copy.deepcopy(a)
        b["summary"]["build_id"] = "b"
        b["runtime"] = [{"nonce": "2" * 16, "cases": 10}, {"nonce": "3" * 16, "cases": 10}]
        b["entries"]["binary"]["sha256"] = "d" * 64
        with mock.patch.object(gate, "campaign", side_effect=[a, b]):
            result = gate.compare(Path("first"), Path("second"), "a" * 40)
        self.assertEqual(result["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(len(result["output_nondeterminism"]), 1)
        self.assertEqual(result["output_nondeterminism"][0]["path"], "binary")

    def test_copied_runtime_campaigns_cannot_count_as_two_builds(self):
        a = self.baseline()
        b = copy.deepcopy(a)
        b["summary"]["build_id"] = "b"
        with mock.patch.object(gate, "campaign", side_effect=[a, b]):
            with self.assertRaises(ValueError):
                gate.compare(Path("first"), Path("second"), "a" * 40)

    def test_changed_toolchain_cannot_count_as_reproducible(self):
        a = self.baseline()
        b = copy.deepcopy(a)
        b["summary"]["build_id"] = "b"
        b["summary"]["toolchain_sha256"] = "e" * 64
        with mock.patch.object(gate, "campaign", side_effect=[a, b]):
            with self.assertRaises(ValueError):
                gate.compare(Path("first"), Path("second"), "a" * 40)


if __name__ == "__main__":
    unittest.main()
