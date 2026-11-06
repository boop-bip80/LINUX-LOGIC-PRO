"""Reject stale or incomplete source-audit evidence at the P003 aggregate gate.

The original hosted P001 reports pin the producer/consumer contract. Synthetic
parser inputs cover additional corruptions; neither replaces a fresh Git-backed
source audit or compiler execution.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools/compat/logic-pro"))
import compare_p003 as gate


def classification_report(manifest, commit):
    # Materialize the verifier's documented report schema. Coverage comes from
    # the producing verifier; the aggregate computes it independently.
    checked = []
    anchor = manifest["current_source_reaudit"]["source_anchor"]
    current_sources = {row["id"]: row for row in manifest["current_source_reaudit"]["evidence"]}
    for source in manifest["evidence"]:
        audit = source.get("current_reaudit")
        current = None
        if audit:
            current = {key: audit[key] for key in ("phase", "blob_sha1", "excerpt_sha256")}
            if audit["phase"] == "P002":
                current["url_rewrites_verified"] = audit["expected_url_rewrites"]
            elif audit["phase"] == "P003":
                current.update(kind="additive-build-integration", original_assertions_preserved=True,
                               additions_verified=len(gate.source_audit.P003_BUILD_ADDITIONS[source["path"]]))
            elif audit["phase"] == "P004":
                current.update(kind="p003-plus-reviewed-upstream-merge", original_assertions_preserved=True,
                               additions_verified=len(gate.source_audit.P003_BUILD_ADDITIONS[source["path"]])
                               + len(gate.source_audit.P004_UPSTREAM_CMAKE_ADDITIONS),
                               upstream_merge_commit=audit["upstream_merge_commit"],
                               prior_p003_blob_sha1=audit["prior_p003_blob_sha1"])
            else:
                raise AssertionError("Unsupported fixture source re-audit")
        source_now = current_sources[source["id"]]
        current_source = {key: copy.deepcopy(source_now[key]) for key in (
            "repository", "path", "repository_commit", "gitlink_chain", "blob_sha1",
            "line_start", "line_end", "excerpt_sha256")}
        if source_now["repository"] == ".":
            current_source["repository_commit"] = commit
        current_source.update(source_anchor=anchor, assertions_verified=len(source_now["contains"]),
                              original_assertions_preserved=True)
        checked.append({
            "id": source["id"], "category": source["category"], "path": source["path"],
            "repository": source.get("repository", "."),
            "repository_commit": source.get("repository_commit", manifest["inspected_commit"]),
            "gitlink_chain": copy.deepcopy(source.get("gitlink_chain", [])),
            "launch_stages": list(source.get("launch_stages", [])),
            "line_start": source["line_start"], "line_end": source["line_end"],
            "blob_sha1": source["blob_sha1"], "excerpt_sha256": source["excerpt_sha256"],
            "current_reaudit": current, "current_source": current_source,
        })
    return {"schema_version": 1, "status": "PASS", "failures": [],
            "inspected_commit": manifest["inspected_commit"], "current_commit": commit,
            "current_source_anchor": anchor,
            "checked_count": len(checked),
            "source_file_count": len({(row["repository"], row["path"]) for row in checked}),
            "checked": checked, "coverage": gate.source_audit.phase_coverage(checked, True)}


class SourceClassificationAggregateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.commit = "1" * 40
        self.manifest = json.loads(gate.CLASSIFICATION_MANIFEST.read_text())
        self.manifest_path = self.root / "current-manifest.json"
        patch = mock.patch.object(gate, "CLASSIFICATION_MANIFEST", self.manifest_path)
        patch.start()
        self.addCleanup(patch.stop)
        self.report = classification_report(self.manifest, self.commit)
        self.save()
        (self.root / "source-classifications.log").write_text("source classifications: PASS; 63 citations verified\n")

    def save(self):
        self.manifest_path.write_text(json.dumps(self.manifest))
        (self.root / "source-classifications.json").write_text(json.dumps(self.report))

    def check(self):
        return gate.validate_source_classifications(self.root, self.commit)

    def test_full_current_manifest_binding_is_accepted_for_parser_testing(self):
        result = self.check()
        self.assertEqual(result["checked_count"], 63)
        self.assertEqual(result["source_file_count"], 41)
        self.assertEqual(result["current_commit"], self.commit)
        self.assertEqual(result["manifest_sha256"], hashlib.sha256(self.manifest_path.read_bytes()).hexdigest())

    def test_reviewed_upstream_identity_is_required_even_when_reports_agree(self):
        original_manifest, original_report = copy.deepcopy(self.manifest), copy.deepcopy(self.report)
        index = next(i for i, row in enumerate(self.manifest["evidence"])
                     if row.get("current_reaudit", {}).get("phase") == "P004")
        mutations = {"kind": "arbitrary-build-change", "upstream_merge_commit": "a" * 40,
                     "prior_p003_blob_sha1": "b" * 40}
        for key, value in mutations.items():
            with self.subTest(field=key):
                self.manifest, self.report = copy.deepcopy(original_manifest), copy.deepcopy(original_report)
                self.manifest["evidence"][index]["current_reaudit"][key] = value
                self.report["checked"][index]["current_reaudit"][key] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "Unreviewed current upstream"):
                    self.check()

    def test_upstream_report_cannot_omit_or_forge_its_source_binding(self):
        original = copy.deepcopy(self.report)
        index = next(i for i, row in enumerate(self.report["checked"])
                     if (row.get("current_reaudit") or {}).get("phase") == "P004")
        for key in ("upstream_merge_commit", "prior_p003_blob_sha1"):
            for missing in (False, True):
                with self.subTest(field=key, missing=missing):
                    self.report = copy.deepcopy(original)
                    audit = self.report["checked"][index]["current_reaudit"]
                    if missing:
                        del audit[key]
                    else:
                        audit[key] = "f" * 40
                    self.save()
                    with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                        self.check()

    def test_upstream_reaudit_is_confined_to_the_reviewed_root_cmake(self):
        source = next(row for row in self.manifest["evidence"]
                      if row.get("current_reaudit", {}).get("phase") == "P003"
                      and row["path"] != "CMakeLists.txt")
        source["current_reaudit"].update(phase="P004", kind="p003-plus-reviewed-upstream-merge",
                                        upstream_merge_commit=gate.source_audit.P004_UPSTREAM_COMMIT,
                                        prior_p003_blob_sha1=gate.source_audit.P004_P003_ROOT_CMAKE_BLOB)
        self.report = classification_report(self.manifest, self.commit)
        self.save()
        with self.assertRaisesRegex(ValueError, "Unreviewed current upstream"):
            self.check()

    def test_upstream_report_requires_exact_addition_count_and_preserved_assertions(self):
        original = copy.deepcopy(self.report)
        index = next(i for i, row in enumerate(self.report["checked"])
                     if (row.get("current_reaudit") or {}).get("phase") == "P004")
        for key, value in (("additions_verified", 0), ("additions_verified", True),
                           ("original_assertions_preserved", False),
                           ("original_assertions_preserved", 1)):
            with self.subTest(field=key, value=value):
                self.report = copy.deepcopy(original)
                self.report["checked"][index]["current_reaudit"][key] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()

    def test_success_count_cannot_replace_missing_duplicate_or_unknown_ids(self):
        original = copy.deepcopy(self.report)
        mutations = (
            lambda rows: rows.pop(),
            lambda rows: rows.__setitem__(-1, copy.deepcopy(rows[0])),
            lambda rows: rows[0].__setitem__("id", "fabricated-citation"),
            lambda rows: rows.append(copy.deepcopy(rows[0])),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                self.report = copy.deepcopy(original)
                mutate(self.report["checked"])
                self.save()
                with self.assertRaises(ValueError):
                    self.check()

    def test_wrong_schema_failure_or_current_and_original_commit_are_rejected(self):
        original = copy.deepcopy(self.report)
        mutations = {"schema_version": True, "status": "FAIL", "failures": [{"id": "stale"}],
                     "current_commit": "2" * 40, "inspected_commit": "3" * 40,
                     "checked_count": 62, "source_file_count": 42}
        for key, value in mutations.items():
            with self.subTest(field=key):
                self.report = copy.deepcopy(original)
                self.report[key] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.check()

    def test_every_original_citation_field_remains_bound(self):
        original = copy.deepcopy(self.report)
        mutations = {"repository": "unrelated/owner", "path": "unrelated.c", "category": "invented",
                     "repository_commit": "a" * 40,
                     "gitlink_chain": [{"path": "unexpected", "commit": "b" * 40}],
                     "line_start": 2, "line_end": 39, "blob_sha1": "c" * 40,
                     "excerpt_sha256": "d" * 64, "launch_stages": ["host_launch"]}
        for key, value in mutations.items():
            with self.subTest(field=key):
                self.report = copy.deepcopy(original)
                self.report["checked"][0][key] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()
        for key in ("blob_sha1", "excerpt_sha256", "gitlink_chain"):
            with self.subTest(missing=key):
                self.report = copy.deepcopy(original)
                del self.report["checked"][0][key]
                self.save()
                with self.assertRaises(ValueError):
                    self.check()
        self.report = copy.deepcopy(original)
        self.report["checked"][0]["line_start"] = True  # Python considers True == 1.
        self.save()
        with self.assertRaises(ValueError):
            self.check()

    def test_current_cmake_and_url_reaudit_summaries_are_exact(self):
        original = copy.deepcopy(self.report)
        for identity, mutations in (
            ("core-runtime-owners", {"blob_sha1": "a" * 40, "excerpt_sha256": "b" * 64,
                                     "additions_verified": 999, "kind": "arbitrary-change",
                                     "original_assertions_preserved": False}),
            ("submodule-declarations", {"url_rewrites_verified": 148, "phase": "P003"}),
            ("host-build-restrictions", {"additions_verified": True}),
        ):
            for key, value in mutations.items():
                with self.subTest(id=identity, field=key):
                    self.report = copy.deepcopy(original)
                    row = next(row for row in self.report["checked"] if row["id"] == identity)
                    row["current_reaudit"][key] = value
                    self.save()
                    with self.assertRaises(ValueError):
                        self.check()
        for identity in ("core-runtime-owners", "submodule-declarations"):
            with self.subTest(missing_audit=identity):
                self.report = copy.deepcopy(original)
                next(row for row in self.report["checked"] if row["id"] == identity)["current_reaudit"] = None
                self.save()
                with self.assertRaises(ValueError):
                    self.check()

    def test_earlier_success_cannot_survive_current_manifest_audit_drift(self):
        original = copy.deepcopy(self.manifest)
        for field, value in (("blob_sha1", "9" * 40), ("excerpt_sha256", "8" * 64)):
            with self.subTest(field=field):
                self.manifest = copy.deepcopy(original)
                record = next(row for row in self.manifest["evidence"] if row["id"] == "core-runtime-owners")
                record["current_reaudit"][field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()

    def test_coverage_summary_is_derived_from_checked_fields(self):
        original = copy.deepcopy(self.report)
        for key, value in (("required", False), ("required_categories", []), ("required_stages", []),
                           ("launch_stages", []), ("categories", []), ("missing_stages", ["host_launch"])):
            with self.subTest(field=key):
                self.report = copy.deepcopy(original)
                self.report["coverage"][key] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "coverage differs"):
                    self.check()

    def test_matching_rows_and_manifest_cannot_fake_missing_required_coverage(self):
        original_manifest, original_report = copy.deepcopy(self.manifest), copy.deepcopy(self.report)
        for removed in ("host_launch", "native_linux_host"):
            with self.subTest(removed=removed):
                self.manifest, self.report = copy.deepcopy(original_manifest), copy.deepcopy(original_report)
                for table in (self.manifest["evidence"], self.report["checked"]):
                    for row in table:
                        if removed == "host_launch":
                            row["launch_stages"] = [stage for stage in row.get("launch_stages", []) if stage != removed]
                        elif row["category"] == removed:
                            row["category"] = "build_ownership"
                self.save()  # Keep the earlier fabricated PASS coverage summary.
                with self.assertRaisesRegex(ValueError, "Actual checked citations do not cover"):
                    self.check()

    def test_raw_source_audit_log_is_required_and_cannot_contradict_the_report(self):
        log = self.root / "source-classifications.log"
        for value in ("", "source classifications: FAIL; 58 citations verified\n",
                      "source classifications: PASS; 62 citations verified\n"):
            with self.subTest(log=value):
                log.write_text(value)
                with self.assertRaises(ValueError):
                    self.check()
        log.unlink()
        with self.assertRaises(ValueError):
            self.check()


    def test_complete_reviewed_current_manifest_is_required(self):
        original = copy.deepcopy(self.manifest)
        mutations = (
            lambda manifest: manifest.pop("current_source_reaudit"),
            lambda manifest: manifest["current_source_reaudit"].__setitem__("schema_version", True),
            lambda manifest: manifest["current_source_reaudit"].__setitem__("source_anchor", "0" * 40),
            lambda manifest: manifest["current_source_reaudit"]["evidence"].pop(),
            lambda manifest: manifest["current_source_reaudit"]["evidence"].append(
                copy.deepcopy(manifest["current_source_reaudit"]["evidence"][0])),
            lambda manifest: manifest["current_source_reaudit"]["evidence"][0].__setitem__("id", "unknown"),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                self.manifest = copy.deepcopy(original)
                mutate(self.manifest)
                self.save()
                with self.assertRaises(ValueError):
                    self.check()

    def test_current_assertions_cannot_be_replaced_by_a_matching_count(self):
        original = copy.deepcopy(self.manifest)
        for identity in ("architecture-targets", "submodule-declarations"):
            with self.subTest(id=identity):
                self.manifest = copy.deepcopy(original)
                source = next(row for row in self.manifest["current_source_reaudit"]["evidence"]
                              if row["id"] == identity)
                source["contains"][0] = "fabricated assertion with the same total count"
                self.save()
                with self.assertRaisesRegex(ValueError, "preserve original or reviewed URL assertions"):
                    self.check()


class HostedSourceClassificationAggregateTests(unittest.TestCase):
    """Consume the unchanged producer output, independently of the synthetic helper."""

    evidence = ROOT / "docs/compat/logic-pro/evidence/P002/requalification-20261105/hosted-d58cca51"
    original_sha256 = "15b1d5e657e09215e4f070bad580d9ed9b4ac78a55d348026cb6c850163180b7"

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.report = json.loads((self.evidence / "p001-ubuntu-22.04/classifications.json").read_text())
        self.commit = self.report["current_commit"]
        self.save()
        (self.root / "source-classifications.log").write_text("source classifications: PASS; 63 citations verified\n")

    def save(self):
        (self.root / "source-classifications.json").write_text(json.dumps(self.report))

    def check(self):
        return gate.validate_source_classifications(self.root, self.commit)

    def test_original_producer_reports_from_both_hosted_runners_are_accepted(self):
        for runner in ("22.04", "24.04"):
            with self.subTest(runner=runner):
                raw = (self.evidence / f"p001-ubuntu-{runner}/classifications.json").read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), self.original_sha256)
                (self.root / "source-classifications.json").write_bytes(raw)
                result = self.check()
                self.assertEqual(result["checked_count"], 63)
                self.assertEqual(result["source_file_count"], 41)
                self.assertEqual(result["current_source_anchor"], gate.source_audit.CURRENT_SOURCE_ANCHOR)
                self.assertEqual(result["report_sha256"], self.original_sha256)

    def test_original_report_requires_exact_top_level_anchor(self):
        for value in (None, "0" * 40, True):
            with self.subTest(value=value):
                self.report["current_source_anchor"] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "different current source anchor"):
                    self.check()
        del self.report["current_source_anchor"]
        self.save()
        with self.assertRaisesRegex(ValueError, "different current source anchor"):
            self.check()

    def test_original_report_requires_current_provenance_for_all_63_citations(self):
        original = copy.deepcopy(self.report)
        for index, row in enumerate(original["checked"]):
            with self.subTest(id=row["id"]):
                self.report = copy.deepcopy(original)
                del self.report["checked"][index]["current_source"]
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()

    def test_original_report_binds_every_current_source_field_and_type(self):
        original = copy.deepcopy(self.report)
        mutations = (("source_anchor", "0" * 40), ("repository", "other"), ("path", "other.c"),
                     ("repository_commit", "1" * 40), ("gitlink_chain", None),
                     ("blob_sha1", "2" * 40), ("line_start", 2), ("line_start", True),
                     ("line_end", 39), ("line_end", 38.0), ("excerpt_sha256", "3" * 64),
                     ("assertions_verified", 0), ("assertions_verified", True),
                     ("assertions_verified", 4.0), ("original_assertions_preserved", False),
                     ("original_assertions_preserved", 1), ("unexpected", "extra"))
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                self.report = copy.deepcopy(original)
                self.report["checked"][0]["current_source"][field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()
        for field in original["checked"][0]["current_source"]:
            with self.subTest(missing=field):
                self.report = copy.deepcopy(original)
                del self.report["checked"][0]["current_source"][field]
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()

    def test_original_report_distinguishes_root_commit_from_nested_pins(self):
        original = copy.deepcopy(self.report)
        root_index = next(i for i, row in enumerate(original["checked"]) if row["repository"] == ".")
        nested_index = next(i for i, row in enumerate(original["checked"]) if row["repository"] != ".")
        cases = ((root_index, "repository_commit", original["current_source_anchor"]),
                 (nested_index, "repository_commit", self.commit),
                 (nested_index, "repository_commit", original["checked"][nested_index]["repository_commit"]),
                 (nested_index, "gitlink_chain", []),
                 (nested_index, "gitlink_chain", original["checked"][nested_index]["gitlink_chain"]))
        for index, field, value in cases:
            with self.subTest(id=original["checked"][index]["id"], field=field, value=value):
                self.report = copy.deepcopy(original)
                self.report["checked"][index]["current_source"][field] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()

    def test_original_report_cannot_trade_original_or_historical_evidence_for_current_source(self):
        original = copy.deepcopy(self.report)
        for field in ("blob_sha1", "excerpt_sha256", "repository_commit", "current_reaudit"):
            with self.subTest(field=field):
                self.report = copy.deepcopy(original)
                if field == "current_reaudit":
                    row = next(row for row in self.report["checked"] if row["current_reaudit"])
                else:
                    row = self.report["checked"][0]
                row[field] = None
                self.save()
                with self.assertRaisesRegex(ValueError, "differs from the current manifest"):
                    self.check()


class UnwindRegressionAggregateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.proof_root = self.root / "unwind-codegen"
        self.proof_root.mkdir()
        self.lock = {"environment": {"tools": {"clang": {"sha256": "c" * 64}}}}
        self.toolchain_hash = "d" * 64
        files = ("compiler-version.stdout.log", "control-behavior.stdout.log", "repaired-behavior.stdout.log",
                 "macho/build/compile_commands.json",
                 "macho/build/CMakeFiles/control_static.dir/register_names.cpp.o",
                 "macho/build/CMakeFiles/unwind_static.dir/register_names.cpp.o")
        evidence = {}
        for name in files:
            path = self.proof_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("Synthetic hash-binding fixture: " + name + "\n").encode())
            evidence[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.report = {"schema": "darling.p003.unwind-codegen.v1", "status": "PASS", "errors": [],
                       "compiler": {"sha256": "c" * 64}, "toolchain_sha256": self.toolchain_hash,
                       "helper_sha256": gate.digest(ROOT / "cmake/darling_unwind_configuration.cmake"),
                       "source_inputs": dict(gate.UNWIND_SOURCE_HASHES), "evidence": evidence}
        (self.root / "unwind-codegen.log").write_text("Synthetic compiler-gate parser fixture, not execution evidence\n")
        self.save()

    def save(self):
        (self.proof_root / "report.json").write_text(json.dumps(self.report))

    def check(self):
        return gate.validate_unwind_codegen(self.root, self.lock, self.toolchain_hash)

    def test_required_proof_hash_binding_accepts_complete_parser_fixture(self):
        self.assertEqual(self.check()["evidence_files"], 6)

    def test_compiler_toolchain_helper_and_pinned_source_identity_cannot_drift(self):
        original = copy.deepcopy(self.report)
        for field in ("compiler", "toolchain_sha256", "helper_sha256", "source_inputs"):
            with self.subTest(field=field):
                self.report = copy.deepcopy(original)
                if field == "compiler":
                    self.report[field]["sha256"] = "0" * 64
                elif field == "source_inputs":
                    self.report[field][next(iter(self.report[field]))] = "0" * 64
                else:
                    self.report[field] = "0" * 64
                self.save()
                with self.assertRaises(ValueError):
                    self.check()

    def test_missing_raw_gate_and_changed_artifact_are_rejected(self):
        log = self.root / "unwind-codegen.log"
        original = log.read_bytes()
        log.unlink()
        with self.assertRaises(ValueError):
            self.check()
        log.write_bytes(original)
        artifact = self.proof_root / "control-behavior.stdout.log"
        artifact.write_text("Changed output\n")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.check()

    def test_critical_object_cannot_be_omitted_or_replaced_with_escaping_path(self):
        name = "macho/build/CMakeFiles/unwind_static.dir/register_names.cpp.o"
        del self.report["evidence"][name]
        self.save()
        with self.assertRaises(ValueError):
            self.check()
        self.report["evidence"][name] = gate.digest(self.proof_root / name)
        self.report["evidence"]["../outside.log"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.check()

    def test_entire_proof_directory_cannot_redirect_outside_the_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            borrowed = Path(directory) / "borrowed-proof"
            self.proof_root.rename(borrowed)
            self.proof_root.symlink_to(borrowed, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "directory is missing or redirected"):
                self.check()


if __name__ == "__main__":
    unittest.main()
