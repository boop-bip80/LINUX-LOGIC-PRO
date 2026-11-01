"""Mutation tests ensure a citation check cannot turn absent evidence into success."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/verify_classifications.py"
SPEC = importlib.util.spec_from_file_location("classification_verifier", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.content = b"// example\nint result() { return 0; }\n"
        (self.repo / "source.c").write_bytes(self.content)
        self.git("add", "source.c")
        self.git("commit", "-qm", "fixture")
        self.commit = self.git("rev-parse", "HEAD")
        self.manifest = {"schema_version": 1, "inspected_commit": self.commit,
            "evidence": [{"id": "result", "category": "partial_implementation",
                "observation": "STATIC_SOURCE_INSPECTION", "path": "source.c",
                "line_start": 2, "line_end": 2, "blob_sha1": self.git("rev-parse", "HEAD:source.c"),
                "excerpt_sha256": hashlib.sha256(self.content.splitlines(keepends=True)[1]).hexdigest(),
                "contains": ["return 0;"]}]}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], stderr=subprocess.PIPE).decode().strip()

    def test_exact_pinned_citation_passes(self):
        result = MODULE.verify(self.repo, self.manifest, "HEAD")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked_count"], 1)

    def test_corrupted_hashes_range_assertion_and_path_fail(self):
        for key, value in (("blob_sha1", "0" * 40), ("excerpt_sha256", "0" * 64),
                           ("line_end", 99), ("contains", ["returns real audio"]),
                           ("contains", []), ("path", "../outside"),
                           ("observation", "EXECUTED")):
            with self.subTest(key=key, value=value):
                modified = copy.deepcopy(self.manifest)
                modified["evidence"][0][key] = value
                self.assertEqual(MODULE.verify(self.repo, modified)["status"], "FAIL")

    def test_empty_evidence_rejected(self):
        self.manifest["evidence"] = []
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.verify(self.repo, self.manifest)

    def test_nonobject_manifest_rejected(self):
        with self.assertRaises(MODULE.EvidenceError):
            MODULE.verify(self.repo, [])

    def test_inherited_git_directory_cannot_redirect_inspection(self):
        with patch.dict("os.environ", {"GIT_DIR": "/not/the/source/git",
                                       "GIT_WORK_TREE": "/not/the/source"}):
            self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")

    def test_duplicate_evidence_rejected(self):
        self.manifest["evidence"] *= 2
        self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "FAIL")

    def test_uncommitted_file_cannot_replace_pinned_source(self):
        (self.repo / "source.c").write_text("uncommitted changed source\n")
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "PASS")

    def test_current_source_drift_requires_new_audit(self):
        (self.repo / "source.c").write_text("int result() { return 1; }\n")
        self.git("commit", "-qam", "changed source")
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "FAIL")
        self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")

    def url_reaudit_fixture(self):
        old = b'[submodule "dependency"]\n\tpath = dependency\n\turl = ../dependency.git\n'
        path = self.repo / ".gitmodules"
        path.write_bytes(old)
        self.git("add", ".gitmodules")
        self.git("commit", "-qm", "original source URL")
        self.manifest["inspected_commit"] = self.git("rev-parse", "HEAD")
        record = self.manifest["evidence"][0]
        record.update({"path": ".gitmodules", "line_start": 1, "line_end": 3,
                       "blob_sha1": self.git("rev-parse", "HEAD:.gitmodules"),
                       "excerpt_sha256": hashlib.sha256(old).hexdigest(),
                       "contains": ["../dependency.git"]})
        new = old.replace(b"../dependency.git", b"https://github.com/darlinghq/dependency.git")
        path.write_bytes(new)
        self.git("commit", "-qam", "explicit verified upstream URL")
        record["current_reaudit"] = {"phase": "P002", "expected_url_rewrites": 1,
                                     "blob_sha1": self.git("rev-parse", "HEAD:.gitmodules"),
                                     "line_start": 1, "line_end": 3,
                                     "excerpt_sha256": hashlib.sha256(new).hexdigest(),
                                     "contains": ["https://github.com/darlinghq/dependency.git"]}
        return path

    def test_url_only_reaudit_preserves_original_source_evidence(self):
        self.url_reaudit_fixture()
        result = MODULE.verify(self.repo, self.manifest, "HEAD")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["checked"][0]["current_reaudit"]["url_rewrites_verified"], 1)
        self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")
        self.assertEqual(MODULE.verify(self.repo, self.manifest, self.manifest["inspected_commit"])["status"], "PASS")

    def test_url_reaudit_cannot_hide_other_source_or_target_changes(self):
        path = self.url_reaudit_fixture()
        for corruption in (b"https://github.com/darlinghq/another.git", b"../new-dependency.git"):
            with self.subTest(corruption=corruption):
                new = path.read_bytes().replace(b"https://github.com/darlinghq/dependency.git", corruption)
                path.write_bytes(new)
                self.git("commit", "-qam", "tamper after re-audit")
                forged = copy.deepcopy(self.manifest)
                forged_audit = forged["evidence"][0]["current_reaudit"]
                forged_audit["blob_sha1"] = self.git("rev-parse", "HEAD:.gitmodules")
                forged_audit["excerpt_sha256"] = hashlib.sha256(new).hexdigest()
                forged_audit["contains"] = [corruption.decode()]
                self.assertEqual(MODULE.verify(self.repo, forged, "HEAD")["status"], "FAIL")
                # Restore the valid version as a new committed revision.
                path.write_bytes(b'[submodule "dependency"]\n\tpath = dependency\n\turl = https://github.com/darlinghq/dependency.git\n')
                self.git("commit", "-qam", "restore URL")

    def build_reaudit_fixture(self, path="src/CMakeLists.txt"):
        if path == "src/CMakeLists.txt":
            old = (b"add_subdirectory(external/libsystem)\n"
                   b"add_subdirectory(external/objc4/runtime)\n"
                   b"add_subdirectory(external/corefoundation)\n"
                   b"#add_subdirectory(external/WebCore)\n")
            new = old.replace(b"add_subdirectory(external/objc4/runtime)\n",
                              b"add_subdirectory(external/objc4/runtime)\n"
                              b"include(darling_objc_configuration)\n"
                              b'darling_configure_objc_runtime("${CMAKE_CURRENT_SOURCE_DIR}/external/objc4/runtime")\n')
            new += (b"\nif (DARLING_P003_PROBES)\n"
                    b'\tadd_subdirectory("${CMAKE_SOURCE_DIR}/tests/compat/logic-pro/build"\n'
                    b'\t\t"${CMAKE_BINARY_DIR}/p003-probe-build")\n'
                    b"endif()\n")
            identity, category = "core-runtime-owners", "build_ownership"
            assertions = ["external/libsystem", "external/objc4/runtime", "external/corefoundation"]
        else:
            old = (b"set(CLANG_RECOMMENDED_MINIMUM_VERSION 11)\n"
                   b"MACRO_ENSURE_OUT_OF_SOURCE_BUILD()\n"
                   b'option(ENABLE_TESTS "Install in-prefix unit tests" OFF)\n')
            new = old + b'option(DARLING_P003_PROBES "Build installed-runtime P003 qualification probes" OFF)\n'
            identity, category = "host-build-restrictions", "architecture_constraint"
            assertions = ["CLANG_RECOMMENDED_MINIMUM_VERSION 11", "MACRO_ENSURE_OUT_OF_SOURCE_BUILD"]
        source = self.repo / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(old)
        self.git("add", path)
        self.git("commit", "-qm", "original CMake source")
        self.manifest["inspected_commit"] = self.git("rev-parse", "HEAD")
        record = self.manifest["evidence"][0]
        record.update(id=identity, category=category, path=path, line_start=1,
                      line_end=len(old.splitlines()), blob_sha1=self.git("rev-parse", "HEAD:" + path),
                      excerpt_sha256=hashlib.sha256(old).hexdigest(), contains=assertions)
        source.write_bytes(new)
        self.git("commit", "-qam", "reviewed P003 build integration")
        record["current_reaudit"] = {
            "phase": "P003", "kind": "additive-build-integration", "line_start": 1,
            "line_end": len(new.splitlines()), "blob_sha1": self.git("rev-parse", "HEAD:" + path),
            "excerpt_sha256": hashlib.sha256(new).hexdigest(), "contains": assertions.copy(),
        }
        return source

    def test_exact_p003_build_reaudit_preserves_historical_citations(self):
        for path, additions in (("src/CMakeLists.txt", 2), ("CMakeLists.txt", 1)):
            with self.subTest(path=path):
                self.build_reaudit_fixture(path)
                result = MODULE.verify(self.repo, self.manifest, "HEAD")
                self.assertEqual(result["status"], "PASS", result["failures"])
                audit = result["checked"][0]["current_reaudit"]
                self.assertEqual(audit["additions_verified"], additions)
                self.assertTrue(audit["original_assertions_preserved"])
                self.assertEqual(result["checked"][0]["blob_sha1"], self.manifest["evidence"][0]["blob_sha1"])
                self.assertNotEqual(audit["blob_sha1"], result["checked"][0]["blob_sha1"])
                self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")
                historical = MODULE.verify(self.repo, self.manifest, self.manifest["inspected_commit"])
                self.assertEqual(historical["status"], "PASS")
                self.assertIsNone(historical["checked"][0]["current_reaudit"])

    def test_p003_reaudit_cannot_approve_unrelated_edits_by_refreshing_hashes(self):
        path = self.build_reaudit_fixture()
        reviewed = path.read_bytes()
        for changed in (reviewed + b"# unreviewed source change\n",
                        reviewed.replace(b"add_subdirectory(external/corefoundation)",
                                         b"#add_subdirectory(external/corefoundation)"),
                        reviewed.replace(b"if (DARLING_P003_PROBES)", b"if (TRUE)"),
                        reviewed.replace(b"include(darling_objc_configuration)",
                                         b"include(unreviewed_configuration)")):
            with self.subTest(change=changed):
                path.write_bytes(changed)
                self.git("commit", "-qam", "unreviewed CMake mutation")
                forged = copy.deepcopy(self.manifest)
                audit = forged["evidence"][0]["current_reaudit"]
                audit.update(blob_sha1=self.git("rev-parse", "HEAD:src/CMakeLists.txt"),
                             excerpt_sha256=hashlib.sha256(changed).hexdigest(), line_end=len(changed.splitlines()))
                result = MODULE.verify(self.repo, forged, "HEAD")
                self.assertEqual(result["status"], "FAIL")
                self.assertIn("beyond the reviewed", result["failures"][0]["error"])

    def test_p003_reaudit_metadata_cannot_waive_source_identity_or_scope(self):
        self.build_reaudit_fixture()
        for edit in (
            lambda record: record.pop("current_reaudit"),
            lambda record: record.update(id="unreviewed-citation"),
            lambda record: record.update(category="implemented_body_unqualified"),
            lambda record: record["current_reaudit"].update(phase="P002"),
            lambda record: record["current_reaudit"].update(kind="arbitrary-source-changes"),
            lambda record: record["current_reaudit"].update(blob_sha1="0" * 40),
            lambda record: record["current_reaudit"].update(excerpt_sha256="0" * 64),
            lambda record: record["current_reaudit"].update(line_end=999),
            lambda record: record["current_reaudit"].update(contains=["external/libsystem"]),
        ):
            with self.subTest(edit=edit):
                forged = copy.deepcopy(self.manifest)
                edit(forged["evidence"][0])
                self.assertEqual(MODULE.verify(self.repo, forged, "HEAD")["status"], "FAIL")

    def test_p003_current_excerpt_must_still_contain_all_original_assertions(self):
        path = self.build_reaudit_fixture()
        record = self.manifest["evidence"][0]
        record["current_reaudit"].update(line_end=1,
            excerpt_sha256=hashlib.sha256(path.read_bytes().splitlines(keepends=True)[0]).hexdigest())
        result = MODULE.verify(self.repo, self.manifest, "HEAD")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("original citation assertions", result["failures"][0]["error"])

    def test_p003_build_reaudit_cannot_authorize_a_different_source_file(self):
        (self.repo / "source.c").write_text("int result() { return 1; }\n")
        self.git("commit", "-qam", "changed non-CMake implementation")
        record = self.manifest["evidence"][0]
        record["current_reaudit"] = {
            "phase": "P003", "kind": "additive-build-integration",
            "blob_sha1": self.git("rev-parse", "HEAD:source.c"),
        }
        result = MODULE.verify(self.repo, self.manifest, "HEAD")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("not allowed for this citation", result["failures"][0]["error"])

    def test_nonempty_subset_cannot_pass_phase_scope(self):
        self.manifest["runtime_executed"] = False
        result = MODULE.verify(self.repo, self.manifest, "HEAD", require_phase_coverage=True)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(result["coverage"]["required"])
        self.assertIn("native_linux_host", result["coverage"]["missing_categories"])
        self.assertIn("framework_initialization", result["coverage"]["missing_stages"])

    def test_stage_label_on_wrong_source_owner_is_insufficient(self):
        self.manifest["evidence"][0]["launch_stages"] = ["dyld_dependency_loading", "framework_initialization"]
        result = MODULE.verify(self.repo, self.manifest, "HEAD", require_phase_coverage=True)
        self.assertEqual(result["checked_count"], 1)
        self.assertIn("dyld_dependency_loading", result["coverage"]["missing_stages"])
        self.assertIn("framework_initialization", result["coverage"]["missing_stages"])

    def child_fixture(self, nested=False):
        def run(folder, *args):
            return subprocess.check_output(["git", "-C", str(folder), *args], stderr=subprocess.PIPE).decode().strip()

        child = self.repo / "dependency"
        child.mkdir()
        for folder in [child] + ([child / "nested"] if nested else []):
            folder.mkdir(exist_ok=True)
            run(folder, "init", "-q")
            run(folder, "config", "user.name", "Fixture")
            run(folder, "config", "user.email", "fixture@example.invalid")
            (folder / "source.c").write_bytes(self.content)
            run(folder, "add", "source.c")
            run(folder, "commit", "-qm", "child source")
        leaf = child / "nested" if nested else child
        leaf_commit = run(leaf, "rev-parse", "HEAD")
        if nested:
            run(child, "update-index", "--add", "--cacheinfo", f"160000,{leaf_commit},nested")
            run(child, "commit", "-qm", "pin nested child")
        child_commit = run(child, "rev-parse", "HEAD")
        self.git("update-index", "--add", "--cacheinfo", f"160000,{child_commit},dependency")
        self.git("commit", "-qm", "pin child")
        self.manifest["inspected_commit"] = self.git("rev-parse", "HEAD")
        record = self.manifest["evidence"][0]
        record.update({"repository": "dependency/nested" if nested else "dependency",
                       "repository_commit": leaf_commit,
                       "gitlink_chain": [{"path": "dependency", "commit": child_commit}],
                       "blob_sha1": run(leaf, "rev-parse", "HEAD:source.c")})
        if nested:
            record["gitlink_chain"].append({"path": "nested", "commit": leaf_commit})
        return child, leaf, run

    def test_exact_nested_child_citation_binds_every_hop(self):
        self.child_fixture(nested=True)
        result = MODULE.verify(self.repo, self.manifest, "HEAD")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["checked"][0]["gitlink_chain"]), 2)

    def test_nested_child_wrong_pin_missing_chain_and_owner_fail(self):
        self.child_fixture(nested=True)
        for mutate in (
            lambda r: r["gitlink_chain"][0].update(commit="0" * 40),
            lambda r: r["gitlink_chain"][1].update(commit="0" * 40),
            lambda r: r.update(gitlink_chain=[]),
            lambda r: r.update(repository="dependency"),
            lambda r: r.update(repository_commit="0" * 40),
        ):
            modified = copy.deepcopy(self.manifest)
            mutate(modified["evidence"][0])
            self.assertEqual(MODULE.verify(self.repo, modified, "HEAD")["status"], "FAIL")

    def test_child_checkout_at_other_commit_fails(self):
        child, leaf, run = self.child_fixture()
        (leaf / "source.c").write_text("int result() { return 1; }\n")
        run(leaf, "commit", "-qam", "other child revision")
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "FAIL")

    def test_current_parent_pin_drift_fails_even_with_audited_child(self):
        child, leaf, run = self.child_fixture()
        original = run(leaf, "rev-parse", "HEAD")
        (leaf / "source.c").write_text("int result() { return 1; }\n")
        run(leaf, "commit", "-qam", "other child revision")
        changed = run(leaf, "rev-parse", "HEAD")
        self.git("update-index", "--cacheinfo", f"160000,{changed},dependency")
        self.git("commit", "-qm", "change child pin")
        run(leaf, "checkout", "--detach", original)
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "FAIL")
        self.assertEqual(MODULE.verify(self.repo, self.manifest)["status"], "PASS")

    def test_symlink_cannot_substitute_child_source(self):
        child, leaf, run = self.child_fixture()
        target = self.repo / "elsewhere"
        child.rename(target)
        child.symlink_to(target, target_is_directory=True)
        self.assertEqual(MODULE.verify(self.repo, self.manifest, "HEAD")["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
