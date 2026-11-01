"""Adversarial P003 packaging fixtures; these do not claim a Darling build."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro"
sys.path.insert(0, str(TOOLS))
import verify_build_install as install
import isolated_install as isolation


def image(install_name, dependencies=(), cpu=0x01000007, duplicate_id=False):
    commands = []
    for command, value in [(0xD, install_name)] * (2 if duplicate_id else 1) + [(0xC, name) for name in dependencies]:
        string = value.encode() + b"\0"
        length = (24 + len(string) + 7) // 8 * 8
        commands.append(struct.pack("<IIIIII", command, length, 24, 0, 0, 0) + string.ljust(length - 24, b"\0"))
    body = b"".join(commands)
    return struct.pack("<IIIIIIII", 0xFEEDFACF, cpu, 3, 6, len(commands), len(body), 0, 0) + body


class MachOTests(unittest.TestCase):
    def test_real_header_and_dependency_names(self):
        parsed = install.macho(image("/Framework", ["/usr/lib/example.dylib"]))
        self.assertEqual(parsed["architectures"][0]["dependencies"], [{"path": "/usr/lib/example.dylib", "weak": False}])

    def test_non_macho_and_truncated_header_rejected(self):
        for data in (b"\x7fELF" + bytes(64), b"", b"\xcf\xfa\xed\xfe"):
            with self.subTest(data=data), self.assertRaises(install.VerificationError):
                install.macho(data)

    def test_non_x86_64_rejected(self):
        with self.assertRaisesRegex(install.VerificationError, "x86_64"):
            install.macho(image("/Framework", cpu=0x0100000C))

    def test_duplicate_install_id_rejected(self):
        with self.assertRaisesRegex(install.VerificationError, "exactly one LC_ID_DYLIB"):
            install.macho(image("/Framework", duplicate_id=True))

    def test_load_command_outside_slice_rejected(self):
        data = bytearray(image("/Framework"))
        struct.pack_into("<I", data, 36, 0xFFFFFFF0)
        with self.assertRaises(install.VerificationError):
            install.macho(data)

    def test_unterminated_install_id_rejected(self):
        data = bytearray(image("/Framework"))
        data[56:] = b"x" * (len(data) - 56)
        with self.assertRaisesRegex(install.VerificationError, "unterminated"):
            install.macho(data)

    def test_fat_overlap_rejected(self):
        thin = image("/Framework")
        header = struct.pack(">II", 0xCAFEBABE, 2)
        records = struct.pack(">IIIII", 0x01000007, 3, 48, len(thin), 0) * 2
        with self.assertRaisesRegex(install.VerificationError, "overlapping"):
            install.macho(header + records + thin)


class GuestPathTests(unittest.TestCase):
    def test_absolute_guest_symlink_does_not_select_host_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "System").mkdir()
            (root / "System/library").write_text("guest bytes")
            (root / "alias").symlink_to("/System/library")
            self.assertEqual(install.guest_resolve(root, "/alias"), root / "System/library")

    def test_escape_loop_missing_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "loop").symlink_to("loop")
            for candidate in ("/../etc/passwd", "/loop", "/missing"):
                with self.subTest(candidate=candidate), self.assertRaises(install.VerificationError):
                    install.guest_resolve(root, candidate)

    def test_snapshot_records_dangling_external_link_without_following(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "external").symlink_to("/Volumes/SystemRoot/not-present")
            self.assertEqual(install.snapshot(root)[0]["target"], "/Volumes/SystemRoot/not-present")


class InstallFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.build = self.root / "build"
        self.prefix = self.root / "darling-p003-install"
        self.reply = self.build / ".cmake/api/v1/reply"
        self.reply.mkdir(parents=True)
        self.prefix.mkdir()
        self.source.mkdir()
        (self.build / "CMakeCache.txt").write_text(f"CMAKE_INSTALL_PREFIX:PATH={self.prefix}\nTARGET_x86_64:BOOL=ON\nCOMPONENTS:STRING=cli,gui\n")
        targets = []
        for name, (version, owner, sentinel) in install.FRAMEWORKS.items():
            (self.source / owner).mkdir(parents=True, exist_ok=True)
            source_file = f"{owner}/{sentinel or 'NSObject.m'}"
            (self.source / source_file).parent.mkdir(parents=True, exist_ok=True)
            (self.source / source_file).write_text("synthetic unit-test source fixture\n")
            artifact = f"{owner}/{name}"
            (self.build / artifact).parent.mkdir(parents=True, exist_ok=True)
            virtual_path = f"/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}"
            data = image(virtual_path)
            (self.build / artifact).write_bytes(data)
            framework = self.prefix / f"libexec/darling/System/Library/Frameworks/{name}.framework"
            (framework / "Versions" / version).mkdir(parents=True)
            (framework / "Versions" / version / name).write_bytes(data)
            (framework / "Versions/Current").symlink_to(version)
            (framework / name).symlink_to(f"Versions/Current/{name}")
            target = {"name": name, "paths": {"source": owner}, "sources": [{"path": source_file}], "artifacts": [{"path": artifact}]}
            (self.reply / f"{name}.json").write_text(json.dumps(target))
            if name == "Foundation":
                (self.build / f"{artifact}_x86_64").write_bytes(data)
                target["artifacts"] = [{"path": f"{artifact}_x86_64"}]
                (self.reply / "Foundation_x86_64.json").write_text(json.dumps(target))
                (self.reply / "Foundation_obj.json").write_text(json.dumps(target))
                targets.extend([{"name": "Foundation_x86_64", "jsonFile": "Foundation_x86_64.json"}, {"name": "Foundation_obj", "jsonFile": "Foundation_obj.json"}])
            else:
                targets.append({"name": name, "jsonFile": f"{name}.json"})
        model = {"paths": {"source": str(self.source), "build": str(self.build)}, "configurations": [{"targets": targets}]}
        (self.reply / "model.json").write_text(json.dumps(model))
        (self.reply / "index-test.json").write_text(json.dumps({"objects": [{"kind": "codemodel", "version": {"major": 2}, "jsonFile": "model.json"}]}))
        self.git_mock = patch.object(install, "git", side_effect=lambda _source, *args: "a" * 40 if args[0] == "rev-parse" else "160000 commit " + "b" * 40 + "\tsrc/external/cocotron")
        self.git_mock.start()
        self.addCleanup(self.git_mock.stop)

    def verify(self):
        return install.verify(self.source, self.build, self.prefix)

    def test_all_seven_owners_and_installed_bytes_are_bound(self):
        report = self.verify()
        self.assertEqual(report["status"], "PASSED", report["errors"])
        self.assertEqual(len(report["frameworks"]), 7)
        self.assertGreater(len(report["entries"]), 30)

    def test_cli_stub_owner_rejected(self):
        target = self.reply / "AppKit.json"
        payload = json.loads(target.read_text())
        payload["paths"]["source"] = "src/frameworks/dev-stubs/AppKit"
        target.write_text(json.dumps(payload))
        report = self.verify()
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(any("source owner" in error for error in report["errors"]))

    def test_substituted_installed_binary_rejected(self):
        path = self.prefix / "libexec/darling/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit"
        path.write_bytes(path.read_bytes() + b"substitution")
        report = self.verify()
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(any("bytes differ" in error for error in report["errors"]))

    def test_wrong_public_alias_rejected(self):
        framework = self.prefix / "libexec/darling/System/Library/Frameworks/AppKit.framework"
        (framework / "AppKit").unlink()
        (framework / "AppKit").symlink_to("/System/Library/Frameworks/Foundation.framework/Foundation")
        report = self.verify()
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(any("competing implementation" in error for error in report["errors"]))

    def test_matching_bytes_with_missing_strong_dependency_rejected(self):
        name = "AppKit"
        data = image("/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit", ["/usr/lib/missing.dylib"])
        (self.build / "src/external/cocotron/AppKit/AppKit").write_bytes(data)
        (self.prefix / "libexec/darling/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit").write_bytes(data)
        report = self.verify()
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(any("missing installed guest path" in error for error in report["errors"]))

    def test_missing_codemodel_cannot_pass(self):
        (self.reply / "index-test.json").unlink()
        with self.assertRaisesRegex(install.VerificationError, "missing CMake"):
            self.verify()

    def test_foundation_lipo_output_cannot_substitute_another_link_target(self):
        path = self.build / "src/external/foundation/Foundation_x86_64"
        path.write_bytes(path.read_bytes() + b"a different linked slice")
        report = self.verify()
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(any("slice differs" in error for error in report["errors"]))

    def test_wrong_macho_install_name_rejected_even_when_bytes_match(self):
        data = image("/unexpected/stub/AppKit")
        (self.build / "src/external/cocotron/AppKit/AppKit").write_bytes(data)
        (self.prefix / "libexec/darling/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit").write_bytes(data)
        report = self.verify()
        self.assertEqual(report["status"], "FAILED")
        self.assertTrue(any("LC_ID_DYLIB" in error for error in report["errors"]))


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / "darling-p003-owned"
        self.marker = self.root / "marker.json"
        self.manifest = self.root / "install.json"

    def prepare(self):
        isolation.mark(self.prefix, self.marker)
        (self.prefix / "binary").write_bytes(b"fixture")
        self.manifest.write_text(json.dumps({"schema_version": 1, "gate": "installed-framework-provenance", "status": "PASSED", "configuration": {"install_prefix": str(self.prefix)}, "entries": install.snapshot(self.prefix)}))

    def test_owned_pristine_prefix_removed_and_absence_proven(self):
        self.prepare()
        result = isolation.remove(self.prefix, self.marker, self.manifest)
        self.assertTrue(result["prefix_absent"])
        self.assertFalse(self.prefix.exists())
        self.assertTrue(self.marker.exists())

    def test_changed_or_added_file_blocks_uninstall(self):
        self.prepare()
        (self.prefix / "user-file").write_text("preserve me")
        with self.assertRaisesRegex(install.VerificationError, "contents changed"):
            isolation.remove(self.prefix, self.marker, self.manifest)
        self.assertTrue((self.prefix / "user-file").exists())

    def test_symlink_never_deletes_external_target(self):
        isolation.mark(self.prefix, self.marker)
        survivor = self.root / "survivor"
        survivor.mkdir()
        (survivor / "keep").write_text("keep")
        (self.prefix / "link").symlink_to(survivor)
        self.manifest.write_text(json.dumps({"schema_version": 1, "gate": "installed-framework-provenance", "status": "PASSED", "configuration": {"install_prefix": str(self.prefix)}, "entries": install.snapshot(self.prefix)}))
        isolation.remove(self.prefix, self.marker, self.manifest)
        self.assertEqual((survivor / "keep").read_text(), "keep")

    def test_system_or_unmarked_prefix_cannot_be_deleted(self):
        for prefix in (Path("/usr"), Path("/opt"), Path("/"), Path("relative"), self.root / "unrelated"):
            with self.subTest(prefix=prefix), self.assertRaises(install.VerificationError):
                isolation.checked_prefix(prefix)

    def test_initial_nonempty_prefix_not_adopted(self):
        self.prefix.mkdir()
        (self.prefix / "user-file").write_text("keep")
        with self.assertRaisesRegex(install.VerificationError, "not empty"):
            isolation.mark(self.prefix, self.marker)

    def test_mismatched_owner_or_failed_manifest_refused(self):
        self.prepare()
        original = self.marker.read_text()
        self.marker.write_text("{}")
        with self.assertRaisesRegex(install.VerificationError, "marker mismatch"):
            isolation.remove(self.prefix, self.marker, self.manifest)
        self.marker.write_text(original)
        payload = json.loads(self.manifest.read_text())
        payload["status"] = "FAILED"
        self.manifest.write_text(json.dumps(payload))
        with self.assertRaisesRegex(install.VerificationError, "passed installation"):
            isolation.remove(self.prefix, self.marker, self.manifest)


if __name__ == "__main__":
    unittest.main()
