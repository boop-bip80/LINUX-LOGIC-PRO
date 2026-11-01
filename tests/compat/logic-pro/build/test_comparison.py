"""Independent rejection tests for P003 aggregate evidence validation.

Fixtures here are deliberately synthetic parser inputs, never claimed as a
Darling runtime result. Their mutations reproduce missing-evidence false passes.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import compare_p003 as gate
import review_package_archive as archive_review


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
    commands.append(command("foundation", f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil\n"
                    f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0\n"))
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
              "stub_diagnostics": {"enabled": True, "environment": {"STUB_VERBOSE": "1"},
                                   "hits": []},
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

    def test_rehashed_foundation_without_live_transaction_interop_is_rejected(self):
        record = next(item for item in self.report["commands"] if item["label"] == "foundation")
        path = self.root / record["stdout"]["file"]
        original = path.read_text()
        self.assertIn("P003_TRANSACTION nonce=", original)
        without_bridge = "\n".join(line for line in original.splitlines()
                                   if not line.startswith("P003_TRANSACTION ")) + "\n"
        path.write_text(without_bridge)
        record["stdout"]["sha256"] = hashlib.sha256(without_bridge.encode()).hexdigest()
        self.save()
        with self.assertRaisesRegex((ValueError, gate.probes.ProbeFailure), "P003_TRANSACTION"):
            gate.validate_probes(self.root, self.install)

    def test_placeholder_diagnostics_must_be_enabled_and_empty(self):
        invalid = [None,
                   {"enabled": False, "environment": {"STUB_VERBOSE": "1"}, "hits": []},
                   {"enabled": True, "environment": {}, "hits": []},
                   {"enabled": True, "environment": {"STUB_VERBOSE": "0"}, "hits": []},
                   {"enabled": True, "environment": {"STUB_VERBOSE": "1"},
                    "hits": [{"text": "STUB: synthetic reached operation"}]}]
        for diagnostics in invalid:
            with self.subTest(diagnostics=diagnostics):
                if diagnostics is None:
                    self.report.pop("stub_diagnostics", None)
                else:
                    self.report["stub_diagnostics"] = diagnostics
                self.save()
                with self.assertRaisesRegex(ValueError, "placeholder diagnostics"):
                    gate.validate_probes(self.root, self.install)

    def test_empty_summary_cannot_hide_hashed_raw_placeholder_execution(self):
        cases = (("foundation", "stdout", "STUB: synthetic operation called\n"),
                 ("macho-known-vector", "stdout", "libxpc stub called: void xpc_transaction_end(void)\n"),
                 ("gui", "stderr", "-[SyntheticView drawRect:] unimplemented in synthetic.m\n"),
                 ("shutdown", "stderr", "synthetic method only defined for abstract class. Define implementation\n"))
        for label, stream, diagnostic in cases:
            with self.subTest(label=label, stream=stream):
                command = next(row for row in self.report["commands"] if row["label"] == label)
                reference = command[stream]
                path = self.root / reference["file"]
                original = path.read_bytes()
                changed = original + diagnostic.encode()
                path.write_bytes(changed)
                # Keep the digest and every successful P003 output legitimate:
                # rejection must come from the raw execution diagnostic.
                reference["sha256"] = hashlib.sha256(changed).hexdigest()
                self.save()
                with self.assertRaisesRegex(ValueError, "Reached generic stub or unimplemented operation"):
                    gate.validate_probes(self.root, self.install)
                path.write_bytes(original)
                reference["sha256"] = hashlib.sha256(original).hexdigest()

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


class IndependentArchiveTests(unittest.TestCase):
    """Synthetic content exercises filesystem boundaries, not Darling behavior."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.destination = self.root / "installed"
        self.archive = self.root / "runtime-prefix.tar.gz"
        self.manifest = self.root / "install.json"
        self.payload = b"synthetic installed bytes\n"
        identity = {"kind": "file", "mode": 0o755, "size": len(self.payload),
                    "sha256": hashlib.sha256(self.payload).hexdigest()}
        self.report = {"status": "PASSED", "errors": [], "source_commit": "a" * 40,
                       "configuration": {"install_prefix": str(self.destination)},
                       "entries": [{"path": "bin", "kind": "directory", "mode": 0o755},
                                   {"path": "bin/probe", **identity},
                                   {"path": "bin/alias", **identity},
                                   {"path": "guest-link", "kind": "symlink", "mode": 0o777,
                                    "target": "/System/Library/Frameworks"}]}
        self.save_manifest()

    def save_manifest(self):
        self.manifest.write_text(json.dumps(self.report))

    def make_archive(self, mutation=None):
        with tarfile.open(self.archive, "w:gz") as archive:
            root = tarfile.TarInfo(".")
            root.type, root.mode = tarfile.DIRTYPE, 0o755
            archive.addfile(root)
            # Forward hardlink tests independent graph resolution.
            for item in sorted(self.report["entries"], key=lambda row: row["path"]):
                member = tarfile.TarInfo("./" + item["path"])
                member.mode = item["mode"]
                data = None
                if item["kind"] == "directory":
                    member.type = tarfile.DIRTYPE
                elif item["kind"] == "symlink":
                    member.type, member.linkname = tarfile.SYMTYPE, item["target"]
                elif item["path"] == "bin/alias":
                    member.type, member.linkname = tarfile.LNKTYPE, "./bin/probe"
                else:
                    member.size, data = len(self.payload), self.payload
                if mutation:
                    member, data = mutation(member, data)
                archive.addfile(member, io.BytesIO(data) if data is not None else None)

    def expected(self):
        return archive_review.read_manifest(self.manifest, "a" * 40, self.destination)

    def test_faithful_extraction_preserves_guest_absolute_symlink_and_forward_hardlink(self):
        self.make_archive()
        expected = self.expected()
        layout, root = archive_review.validate_archive(self.archive, expected)
        archive_review.extract_archive(self.archive, expected, layout, root, self.destination)
        self.assertEqual((self.destination / "bin/probe").read_bytes(), self.payload)
        self.assertEqual(stat.S_IMODE((self.destination / "bin/probe").stat().st_mode), 0o755)
        self.assertEqual(os.readlink(self.destination / "guest-link"), "/System/Library/Frameworks")
        self.assertEqual((self.destination / "bin/probe").stat().st_ino,
                         (self.destination / "bin/alias").stat().st_ino)

    def test_changed_archive_content_permissions_and_traversal_fail_before_extraction(self):
        for mutation_name in ("bytes", "mode", "path", "hardlink"):
            with self.subTest(mutation=mutation_name):
                def mutate(member, data):
                    if member.name == "./bin/probe":
                        if mutation_name == "bytes":
                            data = b"x" * len(self.payload)
                        elif mutation_name == "mode":
                            member.mode = 0o777
                        elif mutation_name == "path":
                            member.name = "../outside"
                    if member.name == "./bin/alias" and mutation_name == "hardlink":
                        member.linkname = "../outside"
                    return member, data
                self.make_archive(mutate)
                with self.assertRaises(ValueError):
                    archive_review.validate_archive(self.archive, self.expected())
                self.assertFalse(self.destination.exists())

    def test_manifest_cannot_traverse_guest_symlink_or_claim_another_commit(self):
        self.report["source_commit"] = "b" * 40
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "another source commit"):
            self.expected()
        self.report["source_commit"] = "a" * 40
        self.report["entries"].append({"path": "guest-link/child", "kind": "directory", "mode": 0o755})
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "traverses a missing directory or symlink"):
            self.expected()

    def test_existing_destination_symlink_is_never_followed(self):
        self.make_archive()
        expected = self.expected()
        layout, root = archive_review.validate_archive(self.archive, expected)
        outside = self.root / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel"
        sentinel.write_text("keep")
        self.destination.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            archive_review.extract_archive(self.archive, expected, layout, root, self.destination)
        self.assertEqual(sentinel.read_text(), "keep")
        self.assertEqual(sorted(path.name for path in outside.iterdir()), ["sentinel"])


if __name__ == "__main__":
    unittest.main()
