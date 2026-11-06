"""Adversarial parser tests for the separately executed P003 package review.

Every report and screenshot produced here is a synthetic parser fixture. No
Darling binary is executed, and passing these tests is never runtime evidence
or permission to mark P003 passed. The live archive replay remains mandatory.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import compare_p003 as gate
from test_comparison import fixture as probe_fixture

_receipt_spec = importlib.util.spec_from_file_location(
    "p004_stage_receipt", ROOT / "ci/logic-pro/p004-stage-receipt.py")
assert _receipt_spec and _receipt_spec.loader
receipt = importlib.util.module_from_spec(_receipt_spec)
_receipt_spec.loader.exec_module(receipt)

COMMIT = "a" * 40
REVIEW_CASES = {
    "macho-known-vector", "macho-fresh-nonce", "macho-boundary-64", "macho-reject-65",
    "macho-invalid-arguments", "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-fresh-nonce", "gui-event-roundtrip", "runtime-shutdown",
}


def visible_xwd(ready: bool) -> bytes:
    """Match the reviewer's real window profile, including the XWD name field."""
    width, height = 400, 240
    name = b"synthetic-parser-fixture\0"
    header = [100 + len(name), 7, 2, 24, width, height, 0, 0, 32, 0, 32, 32,
              width * 4, 4, 0xff0000, 0xff00, 0xff, 8, 256, 0, width, height, 0, 0, 0]
    colors = (0x00ff00, 0xffff00) if ready else (0xff0000, 0x0000ff)
    row = b"".join(color.to_bytes(4, "little") * (width // 2) for color in colors)
    return struct.pack(">25I", *header) + name + row * height


class IndependentReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root, self.first, self.second = (base / name for name in ("review", "first", "second"))
        self.runtime = self.root / "runtime"
        self.report, installation = probe_fixture(self.runtime)
        self.first.mkdir()
        self.second.mkdir()
        for ordinal, folder in enumerate((self.first, self.second)):
            for offset, suffix in enumerate(("first", "second")):
                campaign = folder / ("probes-" + suffix)
                campaign.mkdir()
                (campaign / "report.json").write_text(json.dumps({"nonce": str(ordinal * 2 + offset) * 16}))
        installation.update(status="PASSED", errors=[], source_commit=COMMIT,
                            configuration={"install_prefix": "/opt/darling-p003"})
        (self.first / "install-first.json").write_text(json.dumps(installation))
        # The aggregate checks the archive identity, while the separate archive
        # helper's tests exercise actual tar extraction. This is not a package.
        (self.first / "runtime-prefix.tar.gz").write_bytes(b"SYNTHETIC PARSER INPUT; NOT A DARLING PACKAGE\n")
        toolchain = b'{"synthetic_parser_fixture": true}\n'
        (self.first / "toolchain.lock.json").write_bytes(toolchain)
        (self.root / "toolchain.lock.json").write_bytes(toolchain)
        self.package = {
            "schema": "darling.p003.package-archive-review.v1", "status": "PASS",
            "source_commit": COMMIT, "errors": [], "destination": "/opt/darling-p003",
            "archive_sha256": gate.digest(self.first / "runtime-prefix.tar.gz"),
            "archive_bytes": (self.first / "runtime-prefix.tar.gz").stat().st_size,
            "manifest_sha256": gate.digest(self.first / "install-first.json"),
            "entry_count": len(installation["entries"]), "installed_readback": "PASS",
            "driver_sha256": gate.digest(ROOT / "tools/compat/logic-pro/review_package_archive.py"),
        }
        self.report.update(schema="darling.p003.independent-runtime.v1", phase="P003",
                           reviewer="independent-installed-runtime", status="PASS", source_commit=COMMIT,
                           installation="/opt/darling-p003", prefix="/p003/runtime-review",
                           controlled_home="/p003/runtime-review.home")
        self.report.pop("source_revision")
        self.report["cases"] = [{"name": name, "status": "PASS"} for name in sorted(REVIEW_CASES)]
        self.replace_stream("macho-known-vector", "stdout", b"P003_MACHO nonce=foobar hash=bf9cf968\n")
        for state, ready in (("before", False), ("after", True)):
            raw = visible_xwd(ready)
            colors = [[0, 255, 0], [255, 255, 0]] if ready else [[255, 0, 0], [0, 0, 255]]
            self.report["screenshots"][state] = {
                **self.reference("gui-capture-" + state + "-1.xwd", raw),
                "pixels": gate.probes.xwd_sample(raw),
                "png": self.reference("gui-" + state + ".png", gate.probes.xwd_png(raw)),
                "patches": {"pixels_per_half": 25, "maximum_channel_error": [0, 0],
                            "maximum_allowed_error": 40, "expected_rgb": colors},
                "capture_attempts": 1,
            }
        self.report["host_commands"] = []
        for label in ("gui-search-wait", "gui-search-ready", "gui-capture-before-1", "gui-capture-after-1"):
            self.report["host_commands"].append({
                "label": label, "argv": ["synthetic-parser-fixture", label],
                "exit_code": 0, "expected_exit_code": 0, "timed_out": False,
                "stdout": self.reference(label + ".stdout.log", b"12345\n" if "search" in label else b""),
                "stderr": self.reference(label + ".stderr.log", b""),
            })
        self.report["window_id"] = 12345
        driver = (ROOT / "tools/compat/logic-pro/review_installed_runtime.py").read_bytes()
        self.report["driver_sha256"] = hashlib.sha256(driver).hexdigest()
        self.report["isolation"] = {
            "source_and_build_absent": True, "forbidden_paths": ["/p003/source", "/p003/build"],
            "driver_sha256": self.report["driver_sha256"],
            "driver": self.reference("reviewer-driver.py", driver),
            "mountinfo": self.reference("isolation.mountinfo", b"1 0 0:1 / / rw - overlay overlay rw\n"),
            "working_directory": "/", "caller_mount_namespace": "mnt:[100]",
            "environment": {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
                            "HOME": "/p003/runtime-review.home", "DPREFIX": "/p003/runtime-review",
                            "STUB_VERBOSE": "1", "DISPLAY": ":99"},
        }
        server_stat = "12345 (synthetic fixture server) " + " ".join(["S"] + ["0"] * 18 + ["67890"] + ["0"] * 30) + "\n"
        self.report["lifecycle"].update(
            server_before={"pid": 12345, "starttime": 67890, "state": "S", "mount_namespace": "mnt:[200]"},
            server_stat=self.reference("server-before.stat", server_stat.encode()))
        self.save()

    def reference(self, name, data):
        path = self.runtime / name
        path.write_bytes(data)
        return {"file": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

    def command(self, label):
        return next(row for row in self.report["commands"] if row["label"] == label)

    def replace_stream(self, label, stream, data):
        row = self.command(label)
        row[stream] = self.reference(row[stream]["file"], data)

    def save(self):
        (self.root / "package-review.json").write_text(json.dumps(self.package))
        (self.runtime / "report.json").write_text(json.dumps(self.report))

    def validate(self):
        self.save()
        return gate.validate_independent_review(self.root, self.first, self.second, COMMIT)

    def rejected(self, message=None):
        with self.assertRaisesRegex((ValueError, KeyError, gate.probes.ProbeFailure), message or ".*"):
            self.validate()

    def test_complete_synthetic_parser_fixture_is_accepted(self):
        result = self.validate()
        receipt.verify_screenshots(self.runtime, self.report, independent=True)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["cases"], 10)
        self.assertEqual(result["source_commit"], COMMIT)
        self.assertEqual(result["archive_sha256"], self.package["archive_sha256"])
        self.assertIn("runtime/isolation.mountinfo", result["evidence"])

    def test_rehashed_corrupted_gui_field_outside_center_patches_is_rejected_by_receipt(self):
        """A five-by-five correct island is not proof of a rendered color field.

        This edits original XWD pixels away from the 50 center probe pixels,
        updates both hashes and the PNG, and leaves old center oracles intact.
        """
        before = self.report["screenshots"]["before"]
        raw = bytearray((self.runtime / before["file"]).read_bytes())
        size = struct.unpack_from(">I", raw)[0]
        stride = 400 * 4
        for y in range(50, 190):
            for x in range(35, 85):
                index = size + y * stride + x * 4
                raw[index:index + 4] = (0x00ff00).to_bytes(4, "little")
        self.report["screenshots"]["before"] = {
            **before,
            **self.reference(before["file"], bytes(raw)),
            "pixels": gate.probes.xwd_sample(bytes(raw)),
            "png": self.reference(before["png"]["file"], gate.probes.xwd_png(bytes(raw))),
        }
        with self.assertRaisesRegex(receipt.ReceiptFailure, "interior color field"):
            receipt.verify_screenshots(self.runtime, self.report, independent=True)

    def test_archive_manifest_size_destination_and_count_are_exact(self):
        for key, value in (("archive_sha256", "0" * 64), ("manifest_sha256", "0" * 64),
                           ("archive_bytes", self.package["archive_bytes"] + 1),
                           ("destination", "/some/other/install"), ("entry_count", 2)):
            with self.subTest(field=key):
                original = self.package[key]
                self.package[key] = value
                self.rejected("exact verified installation")
                self.package[key] = original

    def test_changed_archive_and_manifest_bytes_are_rejected(self):
        for name in ("runtime-prefix.tar.gz", "install-first.json"):
            with self.subTest(file=name):
                path = self.first / name
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                self.rejected("exact verified installation")
                path.write_bytes(original)

    def test_review_must_use_exact_source_commit_and_drivers(self):
        for record, key in ((self.package, "source_commit"), (self.report, "source_commit"),
                            (self.package, "driver_sha256"), (self.report["isolation"], "driver_sha256")):
            with self.subTest(record="archive" if record is self.package else "runtime", field=key):
                original = record[key]
                record[key] = "0" * len(original)
                self.rejected()
                record[key] = original

    def test_different_frozen_toolchain_is_rejected(self):
        (self.root / "toolchain.lock.json").write_text('{"different_toolchain": true}\n')
        self.rejected("different toolchain")

    def test_forged_unhashed_raw_output_is_rejected(self):
        (self.runtime / self.command("foundation")["stdout"]["file"]).write_text("forged\n")
        self.rejected("digest mismatch")

    def test_rehashed_wrong_runtime_results_are_rejected(self):
        for label, result in (("macho-known-vector", b"P003_MACHO nonce=foobar hash=00000000\n"),
                              ("foundation", b"P003_FOUNDATION nonce=0123456789abcdef items=alpha|beta|gamma count=3 answer=41 bytes=007fff missing=nil\n"),
                              ("gui", b"P003_GUI nonce=0123456789abcdef clicks=0 keys=16 rendered=2 acknowledged=1\n")):
            with self.subTest(command=label):
                row = self.command(label)
                original = (self.runtime / row["stdout"]["file"]).read_bytes()
                self.replace_stream(label, "stdout", result)
                self.rejected()
                self.replace_stream(label, "stdout", original)

    def test_successful_exit_without_required_operation_record_is_rejected(self):
        self.replace_stream("foundation", "stdout", b"")
        self.rejected()

    def test_rehashed_foundation_with_real_objects_but_no_transaction_interop_is_rejected(self):
        row = self.command("foundation")
        original = (self.runtime / row["stdout"]["file"]).read_bytes()
        retained = b"\n".join(line for line in original.splitlines()
                              if not line.startswith(b"P003_TRANSACTION ")) + b"\n"
        self.assertNotEqual(retained, original)
        self.replace_stream("foundation", "stdout", retained)
        self.rejected("P003_TRANSACTION")
        self.replace_stream("foundation", "stdout", original)

    def test_empty_placeholder_summary_cannot_hide_raw_stub_diagnostics(self):
        for label, stream, diagnostic in (("foundation", "stderr", b"STUB: synthetic operation called\n"),
                                           ("macho-known-vector", "stdout", b"libxpc stub called: void xpc_transaction_begin(void)\n"),
                                           ("gui", "stderr", b"SyntheticView unimplemented in synthetic.m\n"),
                                           ("shutdown", "stderr", b"synthetic only defined for abstract class. Define implementation\n")):
            with self.subTest(command=label):
                row = self.command(label)
                original = (self.runtime / row[stream]["file"]).read_bytes()
                self.replace_stream(label, stream, original + diagnostic)
                self.rejected("raw log contains a placeholder")
                self.replace_stream(label, stream, original)

    def test_placeholder_detection_must_be_enabled(self):
        original = self.report["stub_diagnostics"]
        for diagnostic in (None, {"enabled": False, "environment": {"STUB_VERBOSE": "1"}, "hits": []},
                            {"enabled": True, "environment": {"STUB_VERBOSE": "0"}, "hits": []}):
            with self.subTest(diagnostic=diagnostic):
                self.report["stub_diagnostics"] = diagnostic
                self.rejected("placeholder")
        self.report["stub_diagnostics"] = original

    def test_all_required_cases_must_be_present_once_and_pass(self):
        original = copy.deepcopy(self.report["cases"])
        for replacement in (original[:-1], original + [original[0]],
                             [{**row, "status": "FAIL"} if index == 0 else row
                              for index, row in enumerate(original)]):
            with self.subTest(case_count=len(replacement)):
                self.report["cases"] = replacement
                self.rejected("cases are incomplete")
        self.report["cases"] = original

    def test_no_required_runtime_command_can_be_omitted(self):
        original = self.report["commands"]
        for missing in gate.COMMAND_EXITS:
            with self.subTest(command=missing):
                self.report["commands"] = [row for row in original if row["label"] != missing]
                self.rejected("command evidence is missing")
        self.report["commands"] = original

    def test_duplicate_command_and_redefined_expected_exit_are_rejected(self):
        self.report["commands"].append(copy.deepcopy(self.command("shutdown")))
        self.rejected("command set")
        self.report["commands"].pop()
        negative = self.command("macho-reject-65")
        negative["exit_code"] = negative["expected_exit_code"] = 0
        self.rejected("command failed")

    def test_each_external_window_and_capture_command_is_required(self):
        original = self.report["host_commands"]
        for missing in (row["label"] for row in original):
            with self.subTest(command=missing):
                self.report["host_commands"] = [row for row in original if row["label"] != missing]
                self.rejected("visible-window/capture commands are missing")
        self.report["host_commands"] = original

    def test_independent_runtime_cannot_reuse_any_prior_nonce(self):
        for ordinal in range(4):
            with self.subTest(campaign=ordinal):
                self.report["nonce"] = str(ordinal) * 16
                self.rejected("reused an earlier challenge")

    def test_different_installed_executable_is_rejected(self):
        self.report["binaries"]["p003_gui"]["sha256"] = "0" * 64
        self.rejected("different executable")

    def test_missing_shutdown_or_retained_namespace_is_rejected(self):
        original = copy.deepcopy(self.report["lifecycle"])
        for key, value in (("server_exited", False), ("mount_namespace_released", False),
                           ("namespace_holders_after", [12345])):
            with self.subTest(field=key):
                self.report["lifecycle"] = {**original, key: value}
                self.rejected("did not fully stop")
        self.report["lifecycle"] = {}
        self.rejected("did not fully stop")

    def test_source_and_build_absence_cannot_be_skipped(self):
        self.report["isolation"]["source_and_build_absent"] = False
        self.rejected("source isolation")

    def test_retained_source_or_build_mount_is_rejected_in_all_locations(self):
        for path in ("/p003/source", "/p003/build"):
            for line in (f"2 1 0:2 / {path} rw - ext4 /dev/vda rw\n",
                         f"2 1 0:2 {path} /retained-tree rw - ext4 /dev/vda rw\n",
                         f"2 1 0:2 / /retained-tree rw - bind {path} rw\n"):
                with self.subTest(mount=line.strip()):
                    self.report["isolation"]["mountinfo"] = self.reference("isolation.mountinfo", line.encode())
                    self.rejected()

    def test_malformed_raw_mountinfo_is_rejected(self):
        self.report["isolation"]["mountinfo"] = self.reference("isolation.mountinfo", b"1 0 0:1 / / rw\n")
        self.rejected()

    def test_escaped_source_path_and_alternate_checkout_mount_are_rejected(self):
        for line in (b"2 1 0:2 /p003/sour\\143e /retained-tree rw - ext4 /dev/vda rw\n",
                     b"2 1 0:2 /work/MAC-OS-EMULATION /retained-tree rw - ext4 /dev/vda rw\n"):
            with self.subTest(mount=line):
                self.report["isolation"]["mountinfo"] = self.reference("isolation.mountinfo", line)
                self.rejected()

    def test_exact_reviewer_script_mounts_do_not_look_like_retained_checkout(self):
        lines = b"1 0 0:1 / / rw - overlay overlay rw\n"
        for index, name in enumerate(("review_installed_runtime.py", "review_package_archive.py"), 2):
            lines += (f"{index} 1 0:2 /work/MAC-OS-EMULATION/tools/compat/logic-pro/{name} "
                      f"/p003/{name} ro - ext4 /dev/vda rw\n").encode()
        self.report["isolation"]["mountinfo"] = self.reference("isolation.mountinfo", lines)
        self.assertEqual(self.validate()["status"], "PASS")

    def test_modified_archived_driver_cannot_claim_current_driver_identity(self):
        self.report["isolation"]["driver"] = self.reference("reviewer-driver.py", b"raise SystemExit(0)\n")
        self.rejected()


if __name__ == "__main__":
    unittest.main()
