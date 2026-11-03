"""Adversarial Git-tree tests for P004 source-equivalence across evidence publication."""

import json
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/p004_source_equivalence.py"
SPEC = importlib.util.spec_from_file_location("p004_source_equivalence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceEquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "P004 Fixture")
        self.git("config", "user.email", "p004@example.invalid")
        (self.repo / "src").mkdir()
        (self.repo / "src/main.c").write_text("int main(void) { return 0; }\n")
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/compat.yml").write_text("name: qualification\n")
        (self.repo / "README.md").write_text("# P004 proof fixture\n")
        (self.repo / "docs/compat/logic-pro/evidence/P003").mkdir(parents=True)
        (self.repo / "docs/compat/logic-pro/evidence/P003/acceptance.json").write_text("{}\n")
        self.git("add", ".")
        self.git("commit", "-qm", "tested implementation A")
        self.tested = self.git("rev-parse", "HEAD")
        (self.repo / "README.md").write_text("# P004 proof fixture\n\nVerified source A.\n")
        self.evidence = self.repo / MODULE.P004_EVIDENCE_PREFIX
        self.evidence.mkdir(parents=True)
        (self.evidence / "tested-source.json").write_text(json.dumps({
            "schema_version": 1, "phase": "P004", "tested_sha": self.tested,
        }) + "\n")
        (self.evidence / "predecessors.json").write_text(json.dumps({
            "schema_version": 1, "evidence": [],
        }) + "\n")
        self.git("add", ".")
        self.git("commit", "-qm", "reviewed documentation publication B")
        self.publication = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.repo), *args], stderr=subprocess.STDOUT,
        ).decode().strip()

    def assert_rejected(self, tested=None, publication=None, message=None):
        result = MODULE.prove(self.repo, tested or self.tested, publication or self.git("rev-parse", "HEAD"))
        self.assertEqual(result["status"], "FAIL", result)
        if message:
            self.assertIn(message, " ".join(result["failures"]))
        return result

    def test_docs_only_descendant_proves_exact_code_and_hashes(self):
        result = MODULE.prove(self.repo, self.tested, self.publication)
        self.assertEqual(result["status"], "PASS", result["failures"])
        self.assertTrue(result["ancestor_verified"])
        self.assertTrue(result["code_tree_identical"])
        self.assertEqual(result["change_count"], 3)
        self.assertEqual(len(result["allowed_documentation_changes"]), 3)
        self.assertEqual(len(result["code_tree_manifest_sha256"]), 64)
        self.assertEqual(
            {record["path"] for record in result["allowed_documentation_changes"]},
            {"README.md", MODULE.TESTED_SOURCE_PATH, MODULE.P004_EVIDENCE_PREFIX + "predecessors.json"},
        )
        self.assertTrue(all(r["mode"] == "100644" and len(r["sha256"]) == 64
                            for r in result["allowed_documentation_changes"]))

    def test_cli_writes_machine_proof_and_propagates_exit(self):
        output = self.repo / "proof.json"
        self.assertEqual(MODULE.main([
            "--repo", str(self.repo), "--tested", self.tested,
            "--publication", self.publication, "--output", str(output),
        ]), 0)
        report = json.loads(output.read_text())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["publication_commit"], self.publication)

    def test_changed_source_cannot_be_declared_documentation(self):
        (self.repo / "src/main.c").write_text("int main(void) { return 1; }\n")
        self.git("commit", "-qam", "malicious code delta")
        result = self.assert_rejected(message="code/source")
        self.assertFalse(result["code_tree_identical"])

    def test_changed_workflow_and_predecessor_evidence_are_protected(self):
        (self.repo / ".github/workflows/compat.yml").write_text("name: skip-tests\n")
        (self.repo / "docs/compat/logic-pro/evidence/P003/acceptance.json").write_text('{"pass":false}\n')
        self.git("commit", "-qam", "tamper previous test and evidence")
        result = self.assert_rejected(message="unapproved changed path")
        self.assertFalse(result["code_tree_identical"])

    def test_submodule_gitlink_change_is_not_source_equivalent(self):
        self.git("update-index", "--add", "--cacheinfo",
                 "160000," + "0" * 40 + ",src/external/foreign")
        self.git("commit", "-qm", "sneak in new unreviewed gitlink")
        result = self.assert_rejected(message="code/source")
        self.assertFalse(result["code_tree_identical"])

    def test_nested_or_wrong_phase_evidence_is_not_allowed(self):
        nested = self.evidence / "nested"
        nested.mkdir()
        (nested / "review.json").write_text("{}\n")
        (self.repo / "docs/compat/logic-pro/evidence/P003/second.json").write_text("{}\n")
        self.git("add", ".")
        self.git("commit", "-qm", "unreviewed docs locations")
        self.assert_rejected(message="unapproved changed path")

    def test_symlink_and_executable_evidence_are_rejected(self):
        (self.evidence / "unsafe.json").symlink_to("tested-source.json")
        self.git("add", ".")
        self.git("commit", "-qm", "symlink evidence")
        self.assert_rejected(message="ordinary nonexecutable")
        (self.evidence / "unsafe.json").unlink()
        (self.evidence / "unsafe.json").write_text("{}\n")
        self.git("add", ".")
        self.git("update-index", "--chmod=+x", MODULE.P004_EVIDENCE_PREFIX + "unsafe.json")
        self.git("commit", "-qm", "executable evidence")
        self.assert_rejected(message="ordinary nonexecutable")

    def test_deletion_of_readme_is_not_allowed(self):
        self.git("rm", "README.md")
        self.git("commit", "-qm", "delete accepted roadmap")
        self.assert_rejected(message="document deletion")

    def test_tested_source_pointer_must_match_exact_A(self):
        (self.evidence / "tested-source.json").write_text(json.dumps({
            "schema_version": 1, "phase": "P004", "tested_sha": "0" * 40,
        }) + "\n")
        self.git("commit", "-qam", "forged tested implementation")
        self.assert_rejected(message="does not bind")

    def test_tested_source_pointer_schema_is_closed(self):
        (self.evidence / "tested-source.json").write_text(json.dumps({
            "schema_version": 1, "phase": "P004", "tested_sha": self.tested,
            "allow_any_file": True,
        }) + "\n")
        self.git("commit", "-qam", "forged schema")
        self.assert_rejected(message="does not bind")

    def test_invalid_or_duplicate_json_cannot_be_published(self):
        (self.evidence / "secondary.json").write_text('{"phase":"P004","phase":"PASS"}\n')
        self.git("add", ".")
        self.git("commit", "-qm", "duplicate key evidence")
        self.assert_rejected(message="duplicate JSON key")

    def test_neither_nonancestor_nor_same_commit_passes(self):
        self.assert_rejected(self.tested, self.tested, "distinct descendant")
        self.git("checkout", "--orphan", "unrelated")
        (self.repo / "README.md").write_text("# unrelated\n")
        self.git("add", ".")
        self.git("commit", "-qm", "unrelated history")
        self.assert_rejected(self.tested, self.git("rev-parse", "HEAD"), "not an ancestor")

    def test_non_sha_input_and_missing_evidence_fail_closed(self):
        self.assert_rejected("master", self.publication, "exact lowercase")
        (self.evidence / "tested-source.json").unlink()
        self.git("add", ".")
        self.git("commit", "-qm", "remove tested pointer")
        self.assert_rejected(message="missing P004/tested-source.json")


if __name__ == "__main__":
    unittest.main()
