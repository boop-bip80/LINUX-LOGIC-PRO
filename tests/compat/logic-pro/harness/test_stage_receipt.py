"""Adversarial physical-fixture tests for the real P004 stage receipt producer.

The receipt is *not* a phase acceptance certificate. These tests exercise the
production module itself and prove that each deliberately corrupted on-disk
input rejects instead of creating a passing receipt. Test-only mocks replace
git's remote checkout identity in the CLI tests; role validation uses actual
files, bytes, and hashes under a private temporary directory.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import struct
import zlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[4]
SCRIPT = REPO / "ci" / "logic-pro" / "p004-stage-receipt.py"
SOURCE_SHA = "a" * 40
TREE_SHA = "b" * 40
PUBLICATION_SHA = "c" * 40
SUITE_COUNTS = {"baseline": 143, "submodules": 97, "build": 151,
                "harness": 86, "evidence": 39}
BUILD_CASES = (
    "macho-known-vector", "macho-nonce", "macho-boundary-64",
    "macho-reject-65", "macho-invalid-arguments",
    "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-objects", "gui-event-roundtrip", "runtime-shutdown",
)
RUNTIME_CASES = (
    "macho-known-vector", "macho-fresh-nonce", "macho-boundary-64",
    "macho-reject-65", "macho-invalid-arguments",
    "foundation-invalid-arguments", "gui-invalid-arguments",
    "foundation-fresh-nonce", "gui-event-roundtrip", "runtime-shutdown",
)


def load_receipt_module():
    if not SCRIPT.is_file():
        raise RuntimeError(f"Production stage receipt unavailable: {SCRIPT}")
    spec = importlib.util.spec_from_file_location("p004_stage_receipt_under_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import production stage receipt: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


receipt = load_receipt_module()


def digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def harness_case_names() -> list[str]:
    """Use the exact discoverable test names, not invented green test labels."""
    statements = []
    for filename in ("test_fault_matrix.py", "test_gate_validator.py",
                     "test_stage_receipt.py"):
        path = REPO / "tests" / "compat" / "logic-pro" / "harness" / filename
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and method.name.startswith("test_"):
                    statements.append(
                        f"{method.name} ({path.stem}.{node.name}.{method.name}) ... ok")
    if len(statements) != 86 or len(set(statements)) != 86:
        raise AssertionError(
            f"Source fixture requires all 86 distinct actual test names; found {len(statements)}")
    return statements


def make_xwd_png(ready: bool) -> tuple[bytes, bytes, dict]:
    """Make a real self-consistent XWD/PNG pixel pair with observable state."""
    width, height = 320, 200
    left, right = ((0, 255, 0), (255, 255, 0)) if ready else (
        (255, 0, 0), (0, 0, 255))
    pixel = lambda rgb: bytes((rgb[2], rgb[1], rgb[0], 0))
    one_row = pixel(left) * (width // 2) + pixel(right) * (width // 2)
    header = [104, 7, 2, 24, width, height, 0, 0, 32, 0, 32, 32,
              width * 4, 4, 0x00ff0000, 0x0000ff00, 0x000000ff,
              8, 256, 0, 0, 0, 0, 0, 0]
    xwd = struct.pack(">25I", *header) + b"P003" + one_row * height
    rgb_row = bytes(left) * (width // 2) + bytes(right) * (width // 2)
    raw_png = (b"\0" + rgb_row) * height

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (len(data).to_bytes(4, "big") + kind + data +
                (zlib.crc32(kind + data) & 0xffffffff).to_bytes(4, "big"))

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(raw_png, 9)) +
           chunk(b"IEND", b""))
    samples = {"width": width, "height": height, "depth": 24,
               "left_rgb": list(left), "right_rgb": list(right)}
    return xwd, png, samples


FRAMEWORK_IMAGES = (
    ("AppKit", "C"), ("Foundation", "C"), ("CoreGraphics", "A"),
    ("CoreText", "A"), ("ImageIO", "A"), ("QuartzCore", "A"), ("AudioToolbox", "A"),
)


def make_p003_observations(directory: Path, nonce: str, *, independent: bool) -> dict:
    """Write physically hashed raw Foundation/XPC transcripts and GUI pixels."""
    directory.mkdir(parents=True, exist_ok=True)
    foundation_output = (
        f"P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 "
        f"answer=42 bytes=007fff missing=nil\n"
        f"P003_TRANSACTION nonce={nonce} deltas=1|2|1|0\n"
    ).encode()
    images = "\n".join(
        f"P003_IMAGE /System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
        for name, version in FRAMEWORK_IMAGES
    )
    gui_output = (f"P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1\n"
                  + images + "\n").encode()
    for label, data in (("foundation", foundation_output), ("gui", gui_output)):
        (directory / f"{label}.stdout.log").write_bytes(data)
        (directory / f"{label}.stderr.log").write_bytes(b"")
    commands = []
    for label in ("foundation", "gui"):
        commands.append({
            "label": label, "exit_code": 0, "expected_exit_code": 0,
            "timed_out": False,
            "stdout": {"file": f"{label}.stdout.log",
                       "sha256": digest((directory / f"{label}.stdout.log").read_bytes())},
            "stderr": {"file": f"{label}.stderr.log",
                       "sha256": digest(b"")},
        })
    shots = {}
    for label, ready in (("before", False), ("after", True)):
        xwd, png, samples = make_xwd_png(ready)
        xwd_name, png_name = f"gui-{label}.xwd", f"gui-{label}.png"
        (directory / xwd_name).write_bytes(xwd)
        (directory / png_name).write_bytes(png)
        shot = {
            "file": xwd_name, "sha256": digest(xwd),
            "pixels": samples,
            "png": {"file": png_name, "sha256": digest(png)},
            "asserted_state": "green/yellow after input" if ready else "red/blue before input",
            "patches": {"pixels_per_half": 25, "maximum_channel_error": [0, 0],
                        "maximum_allowed_error": 40,
                        "expected_rgb": [list((0, 255, 0) if ready else (255, 0, 0)),
                                         list((255, 255, 0) if ready else (0, 0, 255))]},
        }
        if independent:
            shot["bytes"] = len(xwd)
            shot["png"]["bytes"] = len(png)
            shot["capture_attempts"] = 1
        shots[label] = shot
    return {"screenshots": shots, "commands": commands,
            "window_id": 4207,
            "loaded_framework_paths": [
                f"/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
                for name, version in FRAMEWORK_IMAGES
            ]}



def json_file(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ReceiptAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="p004-receipt-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def stage(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def make_source(self) -> Path:
        directory = self.stage("source")
        suites = []
        for name, count in SUITE_COUNTS.items():
            transcript = (
                "\n".join(harness_case_names()) + "\n" if name == "harness"
                else "".join(
                    f"test_{name}_case_{i:04d} (compat.{name}) ... ok\n"
                    for i in range(count)
                )
            )
            contents = (transcript +
                        f"\nRan {count} tests in 0.1s\n\nOK\n").encode()
            (directory / f"{name}.log").write_bytes(contents)
            suites.append({"suite": name, "count": count,
                           "discovered": count, "passed": count,
                           "skipped": 0, "exit_code": 0,
                           "sha256": digest(contents)})
        json_file(directory / "source-summary.json", {
            "schema": "darling.p004.source-suites.v1",
            "phase": "P004", "source_commit": SOURCE_SHA,
            "publication_commit": PUBLICATION_SHA,
            "status": "PASS", "suites": suites,
        })
        json_file(directory / "fault-matrix.json", {
            "schema": "darling.p004.fault-matrix.v1",
            "status": "PASS", "control": {"status": "PASS"},
            "fault_matrix": [{"id": "wrong-result", "status": "DETECTED"}],
        })
        return directory

    def make_toolchain(self) -> Path:
        directory = self.stage("toolchain")
        archive = b"p004 synthetic frozen image fixture\n"
        (directory / "toolchain-image.tar.gz").write_bytes(archive)
        json_file(directory / "toolchain.lock.json", {
            "schema": "darling.p004.toolchain-lock.v1",
            "image_archive": {"sha256": digest(archive)},
        })
        return directory

    def make_build(self, role: str = "build-a") -> Path:
        directory = self.stage(role)
        json_file(directory / "build-summary.json", {
            "schema": "darling.p004.build-summary.v1",
            "source_commit": SOURCE_SHA,
            "status": "PASS", "exit_code": 0,
            "last_stage": "complete", "build_id": role[-1],
        })
        for cycle in ("first", "second"):
            probe = directory / f"probes-{cycle}"
            observed = make_p003_observations(probe, "0123456789abcdef",
                                              independent=False)
            json_file(probe / "report.json", {
                "schema": "logic-pro-p003-probes-v1",
                "source_revision": SOURCE_SHA,
                "status": "PASSED", "passed": True,
                "nonce": "0123456789abcdef",
                "oracle": "independent P003 computation, Foundation XPC and visible X11 GUI",
                **observed,
                "binaries": {
                    "p003_macho": {"sha256": "4" * 64},
                    "p003_foundation": {"sha256": "5" * 64},
                    "p003_gui": {"sha256": "6" * 64},
                },
                "stub_diagnostics": {"enabled": True, "environment": {"STUB_VERBOSE": "1"}, "hits": []},
                "lifecycle": {"server_before": {"pid": 4321,
                                                "mount_namespace": "mnt:[12345]"},
                              "server_exited": True,
                              "mount_namespace_released": True,
                              "namespace_holders_after": []},
                "errors": [], "cases": [
                    {"name": case, "status": "PASSED"} for case in BUILD_CASES
                ],
            })
        archive = b"p004 independently-installed runtime package fixture\n"
        (directory / "runtime-prefix.tar.gz").write_bytes(archive)
        (directory / "runtime-prefix.sha256").write_text(
            digest(archive) + "  runtime-prefix.tar.gz\n", encoding="utf-8")
        for name in ("install-first.json", "install-second.json", "uninstall.json"):
            json_file(directory / name, {"status": "PASS", "source_commit": SOURCE_SHA})
        return directory

    def make_runtime(self) -> Path:
        directory = self.stage("independent-runtime")
        json_file(directory / "package-review.json", {
            "schema": "darling.p003.package-review.v1",
            "source_commit": SOURCE_SHA, "status": "PASS",
            "installed_readback": "PASS",
        })
        observed = make_p003_observations(directory / "runtime",
                                          "abcdef0123456789", independent=True)
        json_file(directory / "runtime" / "report.json", {
            "schema": "darling.p003.independent-runtime.v1",
            "source_commit": SOURCE_SHA, "status": "PASS", "passed": True,
            "nonce": "abcdef0123456789",
            "oracle": "source-free independent installed-runtime oracle",
            **observed,
            "isolation": {"source_and_build_absent": True},
            "stub_diagnostics": {"enabled": True, "environment": {"STUB_VERBOSE": "1"}, "hits": []},
            "lifecycle": {"server_before": {"pid": 4321,
                                            "mount_namespace": "mnt:[12345]"},
                          "server_exited": True,
                          "mount_namespace_released": True,
                          "namespace_holders_after": []},
            "errors": [],
            "cases": [{"name": case, "status": "PASS"} for case in RUNTIME_CASES],
        })
        return directory

    def assert_valid(self, role: str, directory: Path) -> None:
        if role == "source":
            count, statements = receipt.source_receipt(directory, SOURCE_SHA)
            expected = sum(SUITE_COUNTS.values())
        elif role == "toolchain":
            count, statements = receipt.toolchain_receipt(directory)
            expected = 1
        elif role.startswith("build"):
            count, statements = receipt.build_receipt(directory, SOURCE_SHA, role)
            expected = 20
        else:
            count, statements = receipt.runtime_receipt(directory, SOURCE_SHA)
            expected = 10
            self.assertEqual(read_json(directory / "runtime-summary.json")["status"], "PASS")
        self.assertEqual(count, expected)
        self.assertTrue(statements)
        self.assertTrue(all(row["actual"] == row["expected"] for row in statements))

    def assert_rejected(self, role: str, directory: Path, pattern: str) -> None:
        with self.assertRaisesRegex(receipt.ReceiptFailure, pattern):
            if role == "source":
                receipt.source_receipt(directory, SOURCE_SHA)
            elif role == "toolchain":
                receipt.toolchain_receipt(directory)
            elif role.startswith("build"):
                receipt.build_receipt(directory, SOURCE_SHA, role)
            else:
                receipt.runtime_receipt(directory, SOURCE_SHA)

    def test_source_honest_physical_fixture_passes_receipt(self):
        self.assert_valid("source", self.make_source())

    def test_source_wrong_commit_sha_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        report = read_json(directory / "source-summary.json")
        report["source_commit"] = "f" * 40
        json_file(directory / "source-summary.json", report)
        self.assert_rejected("source", directory, "source-sha")

    def test_source_wrong_log_sha_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        (directory / "build.log").write_bytes(b"tampered fixture content\n")
        self.assert_rejected("source", directory, "build-log-sha")

    def test_source_suite_skipped_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        report = read_json(directory / "source-summary.json")
        report["suites"][0]["skipped"] = 1
        json_file(directory / "source-summary.json", report)
        self.assert_rejected("source", directory, "baseline-skipped")

    def test_source_suite_missing_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        report = read_json(directory / "source-summary.json")
        report["suites"] = report["suites"][:-1]
        json_file(directory / "source-summary.json", report)
        self.assert_rejected("source", directory, "source fixture suites")

    def test_source_suite_empty_test_run_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        report = read_json(directory / "source-summary.json")
        report["suites"][0]["count"] = 0
        report["suites"][0]["discovered"] = 0
        report["suites"][0]["passed"] = 0
        json_file(directory / "source-summary.json", report)
        self.assert_rejected("source", directory, "baseline fixture floor")

    def test_source_missing_original_output_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        (directory / "evidence.log").unlink()
        self.assert_rejected("source", directory, "Missing evidence original test output")

    def test_source_missing_fault_matrix_rejected(self):
        directory = self.make_source()
        self.assert_valid("source", directory)
        (directory / "fault-matrix.json").unlink()
        self.assert_rejected("source", directory, "Missing regular report")

    def test_toolchain_honest_physical_fixture_passes_receipt(self):
        self.assert_valid("toolchain", self.make_toolchain())

    def test_toolchain_corrupted_archive_rejected(self):
        directory = self.make_toolchain()
        self.assert_valid("toolchain", directory)
        with (directory / "toolchain-image.tar.gz").open("ab") as handle:
            handle.write(b"unexpected image mutation")
        self.assert_rejected("toolchain", directory, "frozen-lock-verified")

    def test_toolchain_missing_image_rejected(self):
        directory = self.make_toolchain()
        self.assert_valid("toolchain", directory)
        (directory / "toolchain-image.tar.gz").unlink()
        self.assert_rejected("toolchain", directory, "Actual frozen toolchain archive is missing")

    def test_build_a_honest_installed_runtime_fixture_passes_receipt(self):
        self.assert_valid("build-a", self.make_build("build-a"))

    def test_build_b_honest_installed_runtime_fixture_passes_receipt(self):
        self.assert_valid("build-b", self.make_build("build-b"))

    def test_build_wrong_revision_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        report = read_json(directory / "probes-first" / "report.json")
        report["source_revision"] = "e" * 40
        json_file(directory / "probes-first" / "report.json", report)
        self.assert_rejected("build-a", directory, "first-runtime-source")

    def test_build_false_positive_subcase_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        report = read_json(directory / "probes-second" / "report.json")
        report["cases"][3]["status"] = "FAILED"
        json_file(directory / "probes-second" / "report.json", report)
        self.assert_rejected("build-a", directory, "case identity/status")

    def test_build_original_xpc_transaction_marker_mutation_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        log = directory / "probes-first" / "foundation.stdout.log"
        original = log.read_text(encoding="utf-8")
        log.write_text(original.replace("deltas=1|2|1|0", "deltas=0|0|0|0"),
                       encoding="utf-8")
        self.assert_rejected("build-a", directory, "P003_TRANSACTION")

    def test_build_missing_one_of_seven_framework_images_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        log = directory / "probes-second" / "gui.stdout.log"
        lines = log.read_text(encoding="utf-8").splitlines()
        log.write_text("\n".join(line for line in lines
                                  if "AudioToolbox.framework" not in line) + "\n",
                       encoding="utf-8")
        self.assert_rejected("build-a", directory, "seven genuine GUI framework owners")

    def test_build_fake_gui_color_even_when_sha_and_pixels_agree_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        stage = directory / "probes-second"
        wrong_xwd, wrong_png, wrong_samples = make_xwd_png(False)
        (stage / "gui-after.xwd").write_bytes(wrong_xwd)
        (stage / "gui-after.png").write_bytes(wrong_png)
        report = read_json(stage / "report.json")
        report["screenshots"]["after"]["sha256"] = digest(wrong_xwd)
        report["screenshots"]["after"]["pixels"] = wrong_samples
        report["screenshots"]["after"]["png"]["sha256"] = digest(wrong_png)
        json_file(stage / "report.json", report)
        self.assert_rejected("build-a", directory, "GUI after does not show required visible")

    def test_build_wrong_case_names_cannot_fake_ten_passing_probes(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        report = read_json(directory / "probes-first" / "report.json")
        report["cases"] = [{"name": f"fake-success-{i}", "status": "PASSED"}
                           for i in range(10)]
        json_file(directory / "probes-first" / "report.json", report)
        self.assert_rejected("build-a", directory, "case")

    def test_build_duplicate_macho_case_does_not_cover_gui(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        report = read_json(directory / "probes-first" / "report.json")
        report["cases"][8] = {"name": "macho-known-vector", "status": "PASSED"}
        json_file(directory / "probes-first" / "report.json", report)
        self.assert_rejected("build-a", directory, "case")

    def test_build_missing_xpc_foundation_case_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        report = read_json(directory / "probes-first" / "report.json")
        report["cases"][7] = {"name": "macho-nonce", "status": "PASSED"}
        json_file(directory / "probes-first" / "report.json", report)
        self.assert_rejected("build-a", directory, "case")

    def test_build_missing_shutdown_case_rejected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        report = read_json(directory / "probes-second" / "report.json")
        report["cases"][-1] = {"name": "fake-server-still-running", "status": "PASSED"}
        json_file(directory / "probes-second" / "report.json", report)
        self.assert_rejected("build-a", directory, "case")

    def test_build_archive_repackaging_detected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        (directory / "runtime-prefix.tar.gz").write_bytes(b"repacked different runtime")
        self.assert_rejected("build-a", directory, "installed-package-sha")

    def test_build_missing_real_probe_report_detected(self):
        directory = self.make_build()
        self.assert_valid("build-a", directory)
        (directory / "probes-second" / "report.json").unlink()
        self.assert_rejected("build-a", directory, "Missing regular report")

    def test_runtime_honest_source_free_replay_fixture_passes_receipt(self):
        self.assert_valid("independent-runtime", self.make_runtime())

    def test_runtime_source_isolation_absent_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        report = read_json(directory / "runtime" / "report.json")
        report["isolation"]["source_and_build_absent"] = False
        json_file(directory / "runtime" / "report.json", report)
        self.assert_rejected("independent-runtime", directory, "runtime-source-isolation")

    def test_runtime_false_positive_case_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        report = read_json(directory / "runtime" / "report.json")
        report["cases"][4]["status"] = "SKIP"
        json_file(directory / "runtime" / "report.json", report)
        self.assert_rejected("independent-runtime", directory, "case identity/status")

    def test_runtime_fake_ten_successful_case_names_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        report = read_json(directory / "runtime" / "report.json")
        report["cases"] = [{"name": "fake-success", "status": "PASS"} for _ in range(10)]
        json_file(directory / "runtime" / "report.json", report)
        self.assert_rejected("independent-runtime", directory, "case")

    def test_runtime_missing_gui_roundtrip_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        report = read_json(directory / "runtime" / "report.json")
        report["cases"][8] = {"name": "fictitious-gui", "status": "PASS"}
        json_file(directory / "runtime" / "report.json", report)
        self.assert_rejected("independent-runtime", directory, "case")

    def test_runtime_missing_foundation_xpc_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        report = read_json(directory / "runtime" / "report.json")
        report["cases"][7] = {"name": "placeholder-foundation", "status": "PASS"}
        json_file(directory / "runtime" / "report.json", report)
        self.assert_rejected("independent-runtime", directory, "case")

    def test_runtime_source_free_xpc_log_wrong_nonce_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        path = directory / "runtime" / "foundation.stdout.log"
        path.write_text(path.read_text().replace("abcdef0123456789", "0000000000000000"),
                        encoding="utf-8")
        self.assert_rejected("independent-runtime", directory, "P003_FOUNDATION")

    def test_runtime_independent_gui_patch_oracle_missing_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        path = directory / "runtime" / "report.json"
        report = read_json(path)
        del report["screenshots"]["after"]["patches"]["expected_rgb"]
        json_file(path, report)
        self.assert_rejected("independent-runtime", directory, "50-pixel patch oracle")

    def test_runtime_missing_actual_report_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        (directory / "runtime" / "report.json").unlink()
        self.assert_rejected("independent-runtime", directory, "Missing regular report")

    def test_runtime_active_mount_namespace_rejected(self):
        directory = self.make_runtime()
        self.assert_valid("independent-runtime", directory)
        report = read_json(directory / "runtime" / "report.json")
        report["lifecycle"]["mount_namespace_released"] = False
        json_file(directory / "runtime" / "report.json", report)
        self.assert_rejected("independent-runtime", directory, "runtime-lifecycle")

    def invoke_cli(self, role: str, directory: Path,
                   *, actual_commit: str = SOURCE_SHA,
                   actual_tree: str = TREE_SHA) -> int:
        arguments = [
            str(SCRIPT), "--role", role, "--directory", str(directory),
            "--commit", SOURCE_SHA, "--publication", PUBLICATION_SHA,
            "--runner", "ubuntu-22.04", "--run-id", "12345",
            "--run-attempt", "1",
        ]
        # The checkout, not the artifact contents, supplies the Git identity.
        # No production acceptance check is bypassed for any on-disk stage data.
        status_output = " " + ("d" * 40) + " path\n"
        mock_submodules = types.SimpleNamespace(stdout=status_output * 160)
        previous = Path.cwd()
        try:
            os.chdir(REPO)
            with mock.patch.object(sys, "argv", arguments), \
                 mock.patch.object(receipt.subprocess, "check_output",
                                   side_effect=[actual_commit + "\n", actual_tree + "\n"]), \
                 mock.patch.object(receipt.subprocess, "run",
                                   return_value=mock_submodules):
                return receipt.main()
        finally:
            os.chdir(previous)

    def test_real_cli_emits_pass_receipt_only_for_verified_stage(self):
        directory = self.make_source()
        self.assertEqual(self.invoke_cli("source", directory), 0)
        result = read_json(directory / "p004-job.json")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["source_commit"], SOURCE_SHA)
        self.assertEqual(result["source_tree"], TREE_SHA)
        self.assertEqual(result["publication_commit"], PUBLICATION_SHA)
        self.assertEqual(result["submodule_pin_count"], 160)
        self.assertEqual(result["discovered"], sum(SUITE_COUNTS.values()))
        self.assertEqual(result["passed"], result["executed"])
        self.assertEqual(result["github_run_attempt"], 1)
        self.assertTrue(result["source_lock_sha256"])
        self.assertEqual(result["source_lock_sha256"],
                         receipt.sha256(REPO / "docs/compat/logic-pro/submodules.lock.json"))

    def test_real_cli_wrong_checked_out_commit_never_emits_pass_receipt(self):
        directory = self.make_source()
        self.assertNotEqual(self.invoke_cli("source", directory,
                                            actual_commit="e" * 40), 0)
        self.assertFalse((directory / "p004-job.json").exists())

    def test_real_cli_invalid_source_tree_never_emits_pass_receipt(self):
        directory = self.make_source()
        self.assertNotEqual(self.invoke_cli("source", directory,
                                            actual_tree="not-a-git-tree"), 0)
        self.assertFalse((directory / "p004-job.json").exists())

    def test_real_cli_corrupt_input_never_emits_pass_receipt(self):
        directory = self.make_source()
        (directory / "source-summary.json").unlink()
        self.assertNotEqual(self.invoke_cli("source", directory), 0)
        self.assertFalse((directory / "p004-job.json").exists())

    def test_real_cli_refuses_existing_success_receipt_overwrite(self):
        directory = self.make_source()
        self.assertEqual(self.invoke_cli("source", directory), 0)
        original_bytes = (directory / "p004-job.json").read_bytes()
        self.assertNotEqual(self.invoke_cli("source", directory), 0)
        self.assertEqual((directory / "p004-job.json").read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
