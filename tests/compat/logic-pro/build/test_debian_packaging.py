#!/usr/bin/env python3
"""Exercise the daily package scripts against Debian's actual source builder."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[4]
UPSTREAM = "0.1.20261107"
VERSION = UPSTREAM + "-1~jammy"
ARTIFACTS = (
    f"darling_{UPSTREAM}.orig.tar.xz",
    f"darling_{VERSION}.debian.tar.xz",
    f"darling_{VERSION}.dsc",
    f"darling_{VERSION}_source.changes",
    f"darling_{VERSION}_source.buildinfo",
)


class DebianPackagingTests(unittest.TestCase):
    def setUp(self):
        for tool in ("dpkg-buildpackage", "dpkg-source", "dpkg-parsechangelog", "tar"):
            self.assertIsNotNone(shutil.which(tool), f"Required Debian test tool missing: {tool}")
        temporary = tempfile.TemporaryDirectory(prefix="darling-debian-test-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base / f"darling-{UPSTREAM}"
        self.source.mkdir()
        scripts = self.source / "tools/debian"
        scripts.mkdir(parents=True)
        for name in ("make-deb", "ppa-build-source", "package-common.sh", "collect-source-artifacts"):
            shutil.copy2(ROOT / "tools/debian" / name, scripts / name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.log = self.base / "debuild.args"
        admindir = self.base / "dpkg"
        admindir.mkdir()
        (admindir / "status").write_text("")
        self.environment = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                                DEB_DISTRO="jammy", DEBUILD_TEST_LOG=str(self.log),
                                DPKG_TEST_ADMINDIR=str(admindir),
                                DPKG_TEST_ROOT=str(self.base),
                                LC_ALL="C", DEBEMAIL="packaging-test@example.invalid")
        self.container_name = "darling-package-test-" + uuid.uuid4().hex
        self.environment["DPKG_TEST_CONTAINER_NAME"] = self.container_name
        self.container_image = os.environ.get("DARLING_PACKAGE_TEST_IMAGE")
        if self.container_image:
            self.assertRegex(self.container_image, r"\Asha256:[0-9a-f]{64}\Z")
            self.assertIsNotNone(shutil.which("docker"), "Required package fixture container runner missing")
            self.addCleanup(self.cleanup_source_container)
        self.write("README", "Synthetic source packaging fixture.\n")
        self.write("module/source.txt", "Nested upstream fixture.\n")
        self.write(".git/config", "synthetic git metadata\n")
        self.write("module/.git", "gitdir: ../.git/modules/module\n")
        self.write("debian/source/format", "3.0 (quilt)\n")
        self.write("debian/control", """Source: darling
Section: devel
Priority: optional
Maintainer: Packaging Test <packaging-test@example.invalid>
Standards-Version: 4.6.2
Rules-Requires-Root: no

Package: darling
Architecture: any
Description: synthetic packaging test
 Tests the actual Debian source package format.
""")
        self.write("debian/copyright", "Synthetic fixture for packaging tests.\n")
        self.write("debian/rules", "#!/usr/bin/make -f\n%:\n\t@true\n", executable=True)
        # Only the devscripts wrappers and clock are substitutes. The source
        # build, source-format validation, and extraction use dpkg unchanged.
        self.shim("date", """#!/bin/sh
if [ "$#" = 1 ] && [ "$1" = +%Y%m%d ]; then
    echo 20261107
else
    exec /usr/bin/date "$@"
fi
""")
        self.shim("dch", """#!/usr/bin/python3
import os, pathlib, sys
args = sys.argv[1:]
version = args[args.index('-v') + 1]
distro = args[args.index('--distribution') + 1]
package = args[args.index('--package') + 1]
pathlib.Path('debian/changelog').write_text(
    f'{package} ({version}) {distro}; urgency=low\\n\\n'
    '  * Daily build\\n\\n'
    f' -- {os.environ["NAME"]} <{os.environ["EMAIL"]}>  Sat, 07 Nov 2026 00:00:00 +0000\\n')
""")
        self.shim("debuild", """#!/usr/bin/python3
import os, pathlib, re, sys
pathlib.Path(os.environ['DEBUILD_TEST_LOG']).write_text('\\n'.join(sys.argv[1:]) + '\\n')
if '-S' in sys.argv[1:]:
    command = ['/usr/bin/dpkg-buildpackage', '--admindir=' + os.environ['DPKG_TEST_ADMINDIR'],
               '-S', '-d', '-us', '-uc']
    image = os.environ.get('DARLING_PACKAGE_TEST_IMAGE')
    if image:
        if re.fullmatch(r'sha256:[0-9a-f]{64}', image) is None:
            raise SystemExit('Package fixture requires an immutable container image ID')
        root = os.environ['DPKG_TEST_ROOT']
        command = ['docker', 'run', '--rm', '--pull', 'never', '--platform', 'linux/amd64',
                   '--name', os.environ['DPKG_TEST_CONTAINER_NAME'],
                   '--user', f'{os.getuid()}:{os.getgid()}', '--network', 'none',
                   '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                   '--tmpfs', '/tmp:rw,nosuid,nodev',
                   '--mount', f'type=bind,src={root},dst={root}',
                   '--workdir', os.getcwd(), '--env', 'HOME=/tmp', '--env', 'TMPDIR=/tmp',
                   '--env', 'LC_ALL=C', '--env', 'PATH=/usr/sbin:/usr/bin:/sbin:/bin',
                   image, *command]
    elif os.environ.get('DARLING_PACKAGE_TEST_REQUIRE_CONTAINER') == '1':
        raise SystemExit('Required package fixture container image is missing')
    os.execvp(command[0], command)
""")

    def cleanup_source_container(self):
        if not self.container_image:
            return
        # Killing a timed-out Docker client alone does not stop its container.
        # Remove only this test's uniquely named container, before temp cleanup.
        result = subprocess.run(["docker", "rm", "--force", self.container_name],
                                text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=15)
        if result.returncode and "No such container" not in result.stdout:
            self.fail("Cannot clean up owned package fixture container: " + result.stdout)

    def write(self, relative, content, executable=False):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)

    def shim(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self, name, *arguments, success=True):
        try:
            result = subprocess.run([str(self.source / "tools/debian" / name), *arguments],
                                    cwd=self.source, env=self.environment, text=True,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=60)
        except subprocess.TimeoutExpired as error:
            observed = error.stdout or b""
            if isinstance(observed, bytes):
                observed = observed.decode("utf-8", "replace")
            self.fail(f"{name} exceeded the unchanged {error.timeout}s deadline; "
                      f"captured source-build output:\n{observed}")
        if success:
            self.assertEqual(result.returncode, 0, result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def assert_source_package(self):
        for name in ARTIFACTS:
            self.assertTrue((self.base / name).is_file(), name)
        with tarfile.open(self.base / ARTIFACTS[0]) as archive:
            members = archive.getnames()
        self.assertIn("./README", members)
        self.assertIn("./module/source.txt", members)
        self.assertFalse(any(".git" in Path(name).parts for name in members), members)
        self.assertFalse(any(Path(name).parts[:1] == ("debian",) for name in members), members)
        destination = self.base / "extracted"
        result = subprocess.run(["dpkg-source", "-x", str(self.base / ARTIFACTS[2]), str(destination)],
                                cwd=self.base, env=self.environment, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual((destination / "README").read_text(), "Synthetic source packaging fixture.\n")
        self.assertIn(f"darling ({VERSION}) jammy;", (destination / "debian/changelog").read_text())

    def test_source_build_produces_extractable_quilt_package(self):
        self.run_script("make-deb", "--dsc")
        self.assert_source_package()
        self.assertIn("-S\n-d\n", self.log.read_text())

    def test_ppa_source_build_produces_extractable_quilt_package(self):
        self.run_script("ppa-build-source")
        self.assert_source_package()
        self.assertIn("-S\n", self.log.read_text())

    def test_binary_mode_preserves_binary_build_and_does_not_make_orig(self):
        self.run_script("make-deb")
        self.assertIn(f"darling ({VERSION}) jammy;", (self.source / "debian/changelog").read_text())
        self.assertEqual(self.log.read_text().splitlines(),
                         ["--preserve-envvar", "CCACHE_*", "--no-lintian", "-us", "-uc", "-b"])
        self.assertFalse((self.base / ARTIFACTS[0]).exists())

    def test_container_launch_failure_cannot_fall_back_to_host_builder(self):
        self.environment["DARLING_PACKAGE_TEST_IMAGE"] = "sha256:" + "1" * 64
        self.shim("docker", "#!/bin/sh\necho 'deliberate container launch failure' >&2\nexit 73\n")
        result = self.run_script("make-deb", "--dsc", success=False)
        self.assertEqual(result.returncode, 73, result.stdout)
        self.assertIn("deliberate container launch failure", result.stdout)
        self.assertTrue((self.base / ARTIFACTS[0]).is_file())
        self.assertFalse((self.base / ARTIFACTS[2]).exists())

    def test_required_container_missing_cannot_use_host_builder(self):
        self.environment.pop("DARLING_PACKAGE_TEST_IMAGE", None)
        self.environment["DARLING_PACKAGE_TEST_REQUIRE_CONTAINER"] = "1"
        result = self.run_script("make-deb", "--dsc", success=False)
        self.assertIn("Required package fixture container image is missing", result.stdout)
        self.assertFalse((self.base / ARTIFACTS[2]).exists())

    def test_cli_help_and_invalid_arguments_do_not_mutate_changelog(self):
        for script in ("make-deb", "ppa-build-source"):
            for arguments in (("--help",), ("-h",), ("--invalid",), ("--dsc", "extra")):
                with self.subTest(script=script, arguments=arguments):
                    self.write("debian/changelog", "Do not replace this changelog.\n")
                    self.run_script(script, *arguments, success=arguments[0] in ("--help", "-h"))
                    self.assertEqual((self.source / "debian/changelog").read_text(),
                                     "Do not replace this changelog.\n")
                    self.assertFalse(self.log.exists())

    def test_collector_moves_complete_source_set_including_upstream_orig(self):
        self.run_script("make-deb", "--dsc")
        unrelated = self.base / "unrelated.orig.tar.xz"
        unrelated.write_text("not this package")
        self.run_script("collect-source-artifacts", "source artifacts")
        destination = self.source / "source artifacts"
        self.assertEqual(sorted(path.name for path in destination.iterdir()), sorted(ARTIFACTS))
        self.assertTrue(unrelated.exists())
        self.assertTrue(all(not (self.base / name).exists() for name in ARTIFACTS))

    def test_collector_missing_artifact_fails_before_any_move(self):
        self.run_script("make-deb", "--dsc")
        (self.base / ARTIFACTS[-1]).unlink()
        result = self.run_script("collect-source-artifacts", "source", success=False)
        self.assertIn("Missing source artifact:", result.stdout)
        self.assertFalse((self.source / "source").exists())
        self.assertTrue(all((self.base / name).exists() for name in ARTIFACTS[:-1]))

    def test_collector_rejects_revisionless_version(self):
        self.write("debian/changelog", """darling (0.1.20261107~jammy) jammy; urgency=low

  * Invalid non-native version.

 -- Packaging Test <packaging-test@example.invalid>  Sat, 07 Nov 2026 00:00:00 +0000
""")
        result = self.run_script("collect-source-artifacts", "source", success=False)
        self.assertIn("must include a Debian revision", result.stdout)
        self.assertFalse((self.source / "source").exists())

    def test_collector_requires_one_destination(self):
        for arguments in ((), ("one", "two")):
            with self.subTest(arguments=arguments):
                result = self.run_script("collect-source-artifacts", *arguments, success=False)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Usage:", result.stdout)


class DebianStripTests(unittest.TestCase):
    def setUp(self):
        for tool in ("dh_strip", "file", "cc", "readelf", "make"):
            self.assertIsNotNone(shutil.which(tool), f"Required Debian test tool missing: {tool}")
        temporary = tempfile.TemporaryDirectory(prefix="darling-strip-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        debian = self.root / "debian"
        debian.mkdir()
        (debian / "control").write_text(
            "Source: darling\nSection: devel\nPriority: optional\n"
            "Maintainer: Packaging Test <packaging-test@example.invalid>\n\n"
            "Package: darling-cli\nArchitecture: any\nDescription: strip regression fixture\n"
            " Tests data preservation and native ELF stripping.\n")
        (debian / "changelog").write_text(
            "darling (0.1-1) unstable; urgency=low\n\n  * Test.\n\n"
            " -- Packaging Test <packaging-test@example.invalid>  Sat, 07 Nov 2026 00:00:00 +0000\n")
        shutil.copy2(ROOT / "debian/compat", debian / "compat")
        shutil.copy2(ROOT / "debian/rules", debian / "rules")
        self.magic = debian / "darling-cli/usr/libexec/darling/usr/share/file/magic/elf"
        self.magic.parent.mkdir(parents=True)
        # New file(1) releases include the ELF/executable words from this text
        # in the description. Retain that observed classification on older
        # CI hosts as well, while running real dh_strip and strip unchanged.
        self.magic.write_text(
            "\n#------------------------------------------------------------------------------\n"
            "# synthetic fixture\n# file(1) magic for ELF executables\n"
            "0 string \\177ELF ELF binary\n")
        self.magic.chmod(0o755)
        scripts = self.root / "fixture-bin"
        scripts.mkdir()
        classifier = scripts / "file"
        classifier.write_text(
            "#!/usr/bin/python3\nimport os, sys\n"
            "if sys.argv[-1].endswith('/usr/share/file/magic/elf'):\n"
            "    print('magic text fragment for file(1) cmd, ELF executables')\n"
            "else:\n"
            f"    os.execv({json.dumps(shutil.which('file'))}, ['file', *sys.argv[1:]])\n")
        classifier.chmod(0o755)
        self.native = debian / "darling-cli/usr/bin/native-fixture"
        self.native.parent.mkdir(parents=True)
        source = self.root / "native.c"
        source.write_text("int main(void) { return 0; }\n")
        compiled = subprocess.run(["cc", "-g", "-Wl,--build-id", str(source), "-o", str(self.native)],
                                  capture_output=True, text=True, timeout=30)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        self.environment = dict(os.environ, LC_ALL="C", DEB_BUILD_OPTIONS="",
                                PATH=f"{scripts}:{os.environ['PATH']}",
                                DH_OPTIONS="--no-automatic-dbgsym")

    def run_strip(self, command):
        return subprocess.run(command, cwd=self.root, env=self.environment, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)

    def test_observed_magic_description_reproduces_real_strip_failure(self):
        original = self.magic.read_bytes()
        result = self.run_strip(["dh_strip"])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("magic/elf", result.stdout)
        self.assertIn("file format not recognized", result.stdout)
        self.assertEqual(self.magic.read_bytes(), original)

    def test_packaging_preserves_magic_data_and_still_strips_native_elf(self):
        original = self.magic.read_bytes()
        before = self.run_strip(["readelf", "-S", str(self.native)])
        self.assertIn(".debug_info", before.stdout)
        result = self.run_strip(["make", "-f", "debian/rules", "override_dh_strip"])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.magic.read_bytes(), original)
        after = self.run_strip(["readelf", "-S", str(self.native)])
        self.assertEqual(after.returncode, 0, after.stdout)
        self.assertNotIn(".debug_info", after.stdout)
        self.assertEqual(self.run_strip([str(self.native)]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
