"""The source campaign rejects incomplete recursive source and forged summaries."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[4] / "tools/compat/logic-pro/run_baseline.py"
SPEC = importlib.util.spec_from_file_location("baseline_campaign", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FixtureOutcomeTests(unittest.TestCase):
    """Use real unittest outcomes as the oracle for the campaign transcript."""

    def run_cases(self, *methods):
        case_type = type("AcceptanceFixture", (unittest.TestCase,),
                         {f"test_{index}": method for index, method in enumerate(methods)})
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(case_type))
        return result, stream.getvalue()

    def test_plain_success_counts_executed_tests(self):
        result, transcript = self.run_cases(lambda case: None, lambda case: None)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(MODULE.verify_fixture_transcript(transcript), 2)

    def test_expected_failure_cannot_hide_a_failed_acceptance_assertion(self):
        failed_assertion = unittest.expectedFailure(lambda case: case.fail("required behavior is broken"))
        result, transcript = self.run_cases(failed_assertion)
        self.assertTrue(result.wasSuccessful())  # unittest's exit status would be zero.
        self.assertEqual(len(result.expectedFailures), 1)
        with self.assertRaisesRegex(ValueError, "expected-failure"):
            MODULE.verify_fixture_transcript(transcript)

    def test_successes_do_not_waive_skipped_or_expected_failure_cases(self):
        masked_cases = [unittest.skip("required oracle unavailable")(lambda case: None),
                        unittest.expectedFailure(lambda case: case.fail("broken"))]
        for masked in masked_cases:
            with self.subTest(outcome=masked):
                result, transcript = self.run_cases(lambda case: None, masked)
                self.assertTrue(result.wasSuccessful())
                self.assertEqual(result.testsRun, 2)
                with self.assertRaises(ValueError):
                    MODULE.verify_fixture_transcript(transcript)

    def test_empty_suite_is_not_successful_evidence(self):
        result, transcript = self.run_cases()
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(result.testsRun, 0)
        with self.assertRaises(ValueError):
            MODULE.verify_fixture_transcript(transcript)

    def test_failure_error_and_unexpected_success_are_rejected(self):
        cases = [lambda case: case.fail("broken"), lambda case: 1 / 0,
                 unittest.expectedFailure(lambda case: None)]
        for method in cases:
            with self.subTest(outcome=method):
                result, transcript = self.run_cases(method)
                self.assertFalse(result.wasSuccessful())
                with self.assertRaises(ValueError):
                    MODULE.verify_fixture_transcript(transcript)

    def test_incomplete_output_cannot_prove_success(self):
        _, transcript = self.run_cases(lambda case: None)
        with self.assertRaises(ValueError):
            MODULE.verify_fixture_transcript(transcript.removesuffix("OK\n"))

    def test_multiple_unittest_summaries_are_rejected_even_with_terminal_ok(self):
        _, transcript = self.run_cases(lambda case: None)
        diagnostic = "fixture diagnostic: previous log follows\nRan 999 tests in 0.1s\n\nOK\n"
        for forged in (diagnostic + transcript, transcript + diagnostic):
            with self.subTest(forged=forged), self.assertRaisesRegex(ValueError, "exactly one"):
                MODULE.verify_fixture_transcript(forged)

    def test_claimed_count_must_match_distinct_verbose_test_announcements(self):
        _, transcript = self.run_cases(lambda case: None, lambda case: None)
        self.assertEqual(MODULE.verify_fixture_transcript(transcript), 2)
        for forged in (transcript.replace("Ran 2 tests", "Ran 3 tests"),
                       transcript.replace("test_1", "test_0"),
                       transcript.replace("test_1", "other_1")):
            with self.subTest(forged=forged), self.assertRaisesRegex(ValueError, "verbose"):
                MODULE.verify_fixture_transcript(forged)

    def test_campaign_rejects_a_green_suite_with_shrunk_fixture_coverage(self):
        def verbose_report(count):
            cases = "".join(f"test_{i} (fixtures.Acceptance) ... ok\n" for i in range(count))
            return cases + f"\n----------------------------------------------------------------------\nRan {count} tests in 0.1s\n\nOK\n"

        self.assertEqual(MODULE.verify_campaign_fixture_suite(verbose_report(130)), 130)
        self.assertEqual(MODULE.verify_campaign_fixture_suite(verbose_report(131)), 131)
        for transcript in (verbose_report(1), verbose_report(120), verbose_report(129)):
            with self.subTest(transcript=transcript), self.assertRaisesRegex(ValueError, "coverage shrank"):
                MODULE.verify_campaign_fixture_suite(transcript)


class CampaignEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.snapshot = {"external_tree": {"gitlinks": [{"path": "dep", "sha": "pin"}]},
                         "baseline_commit": "original", "baseline_tree": "original-tree",
                         "integration_commit": "plan", "integration_tree": "plan-tree"}
        root = self.repository(".", "implementation", "https://fork.test/runtime.git", 1)
        root["index_gitlinks"] = [self.index_link("dep", "pin")]
        root["materialization"].update(expected_blobs=0, verified_blobs=0)
        child = self.repository("dep", "pin", "https://upstream.test/dep.git", 1)
        module = self.module(".", "dep", "pin", root["configured_origin"], child["configured_origin"])
        self.write("inventory.json", {
            "source": {"commit": "implementation", "tree": "implementation-tree", "checkout_head": "implementation"},
            "inventory_status": "VALID", "requirements": {"clean_checkout": True, "recursive_source": True},
            "issues": [], "submodules": [module], "repositories": [root, child],
            "summary": {"error_count": 0, "warning_count": 0, "tracked_entries": 2, "gitlinks": 1,
                        "available_gitlinks": 1, "unavailable_gitlinks": 0, "inspected_repositories": 2,
                        "recursive_content_complete": True}, "tracked_files": {"entries": 2},
        })
        self.set_tracked([self.entry(".", "dep", "pin", True), self.entry("dep", "source.c", "source-blob")])
        self.write("source-retrieval.json", {
            "result": "PASS", "failures": [],
            "source": {"commit": "implementation", "tree": "implementation-tree", "parent_source_unchanged": True},
            "recursive_content_complete": True, "recursive_submodules_observed": 1,
            "submodules": [self.retrieved(module)],
        })
        self.write("recovery.json", {"result": "PASS", "snapshots": [
            {"label": label, "commit": self.snapshot[label + "_commit"], "tree": self.snapshot[label + "_tree"],
             "working_tree_clean": True, "independent_object_store": True, "verified_blobs": 2,
             "gitlinks": [{"path": "dep", "commit": "pin"}]} for label in ("baseline", "integration")]})
        categories = ["native_linux_host", "macho_runtime_component", "implemented_body_unqualified", "partial_framework",
                      "developer_link_stub", "generated_stub_tooling", "generated_style_stub_body", "architecture_constraint"]
        stages = ["host_launch", "mldr_mapping_and_dyld_handoff", "dyld_dependency_loading", "system_library_initialization",
                  "server_checkin_and_rpc_dispatch", "framework_initialization"]
        self.write("classifications.json", {
            "status": "PASS", "checked_count": len(categories), "current_commit": "implementation",
            "coverage": {"required": True, "status": "PASS", "categories": categories, "launch_stages": stages,
                         "required_categories": categories, "required_stages": stages,
                         "missing_categories": [], "missing_stages": [], "missing_stage_sources": {}},
            "checked": [{"id": category, "repository": "dep", "repository_commit": "pin", "category": category,
                         "launch_stages": stages if n == 0 else [], "path": "source.c", "blob_sha1": "source-blob"}
                        for n, category in enumerate(categories)],
        })

    def repository(self, path, commit, origin, count):
        return {"path": path, "commit": commit, "tree": commit + "-tree", "checkout_head": commit,
                "worktree_clean": True, "checkout_matches_ref": True, "working_tree_status": [],
                "staged_index_changes": [], "tracked_entries": count, "index_gitlinks": [], "licenses": [],
                "materialization": {"status": "PASS", "reference_commit": commit, "expected_blobs": count, "verified_blobs": count},
                "configured_origin": origin, "effective_remote_url": origin, "effective_remote_provenance": "configured_origin"}

    def entry(self, repo, local, oid, gitlink=False):
        return {"repository": repo, "repository_path": local, "path": local if repo == "." else repo + "/" + local,
                "mode": "160000" if gitlink else "100644", "type": "commit" if gitlink else "blob", "object": oid}

    def index_link(self, path, pin):
        return {"path": path, "object": pin, "mode": "160000", "stage": 0}

    def module(self, owner, local, pin, parent_origin, child_origin):
        resolved = parent_origin.rsplit("/", 1)[0] + "/" + local + ".git"
        return {"path": local if owner == "." else owner + "/" + local, "repository": owner,
                "repository_path": local, "commit": pin, "checkout_head": pin,
                "declared_url": "../" + local + ".git", "resolved_url": resolved,
                "effective_resolved_url": resolved, "content_status": "available_at_pin", "recursive_inventory": "inspected",
                "source_origin": child_origin, "source_origin_provenance": "child_remote_origin_configuration",
                "resolution_base_url": parent_origin, "resolution_base_provenance": "configured_origin"}

    def retrieved(self, module):
        return {"path": module["path"], "parent_path": module["repository"], "status": "PASS",
                "commit": module["commit"], "tree": module["commit"] + "-tree",
                "configured_origin": module["source_origin"], "fetch_url": module["source_origin"],
                "declared_url": module["declared_url"], "resolved_url": module["effective_resolved_url"]}

    def read(self, name):
        return json.loads((self.out / name).read_text())

    def write(self, name, value):
        (self.out / name).write_text(json.dumps(value))

    def mutate(self, name, callback):
        value = self.read(name)
        callback(value)
        self.write(name, value)

    def set_tracked(self, entries):
        self.write("tracked-files.json", {"source_commit": "implementation", "entries": entries})
        digest = hashlib.sha256((self.out / "tracked-files.json").read_bytes()).hexdigest()
        self.mutate("inventory.json", lambda value: value["tracked_files"].update(sha256=digest, entries=len(entries)))

    def add_license(self, owner=".", path="APPLE_LICENSE", data=b"Candidate fixture.\n", mode="100644", reasons=None):
        oid = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        entry = self.entry(owner, path, oid)
        entry["mode"] = mode
        self.set_tracked(self.read("tracked-files.json")["entries"] + [entry])
        value = self.read("inventory.json")
        repository = next(record for record in value["repositories"] if record["path"] == owner)
        repository["tracked_entries"] += 1
        repository["materialization"]["expected_blobs"] += 1
        repository["materialization"]["verified_blobs"] += 1
        value["summary"]["tracked_entries"] += 1
        record = {"path": path, "git_blob": oid, "mode": mode, "bytes": len(data),
                  "sha256": hashlib.sha256(data).hexdigest(),
                  "content_kind": "symlink_target_text" if mode == "120000" else "regular_file",
                  "discovery_reasons": reasons if reasons is not None else ["basename_license_notice_keyword"],
                  "classification": "filename/path candidate; not a legal determination"}
        if mode == "120000":
            record.update(symlink_target=data.decode(), target_dereferenced=False)
        repository["licenses"].append(record)
        self.write("inventory.json", value)

    def add_nested(self):
        module = self.module("dep", "child", "child-pin", "https://upstream.test/dep.git", "https://upstream.test/child.git")
        value = self.read("inventory.json")
        value["submodules"].append(module)
        value["repositories"][1]["tracked_entries"] = 2
        value["repositories"][1]["index_gitlinks"] = [self.index_link("child", "child-pin")]
        value["repositories"].append(self.repository("dep/child", "child-pin", module["source_origin"], 1))
        value["summary"].update(gitlinks=2, available_gitlinks=2, inspected_repositories=3, tracked_entries=4)
        self.write("inventory.json", value)
        self.mutate("source-retrieval.json", lambda value: value["submodules"].append(self.retrieved(module)))
        self.mutate("source-retrieval.json", lambda value: value.update(recursive_submodules_observed=2))
        self.set_tracked(self.read("tracked-files.json")["entries"] + [self.entry("dep", "child", "child-pin", True),
                         self.entry("dep/child", "leaf.c", "leaf-blob")])

    def rejected(self):
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_complete_reports_pass_without_claiming_runtime(self):
        result = MODULE.check_reports(self.out, self.snapshot)
        self.assertEqual(result["known_gitlinks_verified"], 1)
        self.assertEqual(result["recursive_gitlinks_verified"], 1)
        self.assertEqual(result["unavailable_submodule_contents"], 0)
        self.assertEqual(result["recursive_dependency_closure"], "COMPLETE_AT_RECORDED_PINS")
        self.assertFalse(result["runtime_executed"])
        self.assertIn("REQUIRED", result["independent_review"])

    def add_reaudited_gitmodules(self):
        """Historical .gitmodules citation and its exact P002 current blob coexist."""
        self.set_tracked(self.read("tracked-files.json")["entries"] + [
            self.entry(".", ".gitmodules", "1" * 40),
        ])

        def add_root_blob(manifest):
            root = manifest["repositories"][0]
            root["tracked_entries"] += 1
            root["materialization"].update(expected_blobs=1, verified_blobs=1)
            manifest["summary"]["tracked_entries"] += 1
        self.mutate("inventory.json", add_root_blob)

        def add_historical_citation(manifest):
            manifest["checked"].append({
                "id": "submodule-declarations", "repository": ".", "repository_commit": "historical",
                "category": "macho_runtime_component", "launch_stages": [], "path": ".gitmodules",
                "blob_sha1": "0" * 40,
                "current_reaudit": {
                    "phase": "P002", "url_rewrites_verified": 149, "blob_sha1": "1" * 40,
                    "excerpt_sha256": "2" * 64,
                },
            })
            manifest["checked_count"] += 1
        self.mutate("classifications.json", add_historical_citation)

    def test_p002_current_gitmodules_reaudit_binds_current_inventory_without_erasing_history(self):
        self.add_reaudited_gitmodules()
        result = MODULE.check_reports(self.out, self.snapshot)
        self.assertEqual(result["source_citations_verified"], 9)
        self.assertEqual(result["tracked_entries"], 3)
        self.assertFalse(result["runtime_executed"])

    def test_p002_reaudit_cannot_bypass_unrelated_or_forged_source_citations(self):
        self.add_reaudited_gitmodules()
        original = self.read("classifications.json")
        for edit in (
            lambda c: c.pop("current_reaudit"),
            lambda c: c["current_reaudit"].update(phase="P003"),
            lambda c: c["current_reaudit"].update(url_rewrites_verified=148),
            lambda c: c["current_reaudit"].update(url_rewrites_verified=True),
            lambda c: c["current_reaudit"].update(blob_sha1="9" * 40),
            lambda c: c["current_reaudit"].update(blob_sha1="invalid"),
            lambda c: c["current_reaudit"].update(excerpt_sha256="invalid"),
            lambda c: c["current_reaudit"].update(unexpected="waiver"),
            lambda c: c.update(path="README.md"),
            lambda c: c.update(repository="dep"),
        ):
            with self.subTest(edit=edit):
                self.write("classifications.json", original)
                self.mutate("classifications.json", lambda v: edit(v["checked"][-1]))
                self.rejected()
        self.write("classifications.json", original)
        self.mutate("classifications.json", lambda v: v["checked"][0].update(
            current_reaudit=original["checked"][-1]["current_reaudit"]))
        self.rejected()
        self.write("classifications.json", original)
        changed_entries = self.read("tracked-files.json")["entries"]
        changed_entries[-1]["object"] = "0" * 40
        self.set_tracked(changed_entries)
        self.rejected()

    def add_reaudited_cmake(self, path="src/CMakeLists.txt", identity="core-runtime-owners",
                            category="build_ownership", additions=4):
        self.set_tracked(self.read("tracked-files.json")["entries"] + [self.entry(".", path, "1" * 40)])

        def add_current_source(manifest):
            root = manifest["repositories"][0]
            root["tracked_entries"] += 1
            root["materialization"].update(expected_blobs=1, verified_blobs=1)
            manifest["summary"]["tracked_entries"] += 1
        self.mutate("inventory.json", add_current_source)

        def add_historical_citation(manifest):
            manifest["checked"].append({
                "id": identity, "repository": ".", "repository_commit": "historical",
                "category": category, "launch_stages": [], "path": path, "blob_sha1": "0" * 40,
                "current_reaudit": {
                    "phase": "P003", "kind": "additive-build-integration", "blob_sha1": "1" * 40,
                    "excerpt_sha256": "2" * 64, "additions_verified": additions,
                    "original_assertions_preserved": True,
                },
            })
            manifest["checked_count"] += 1
            manifest["coverage"]["categories"] = sorted(set(manifest["coverage"]["categories"]) | {category})
        self.mutate("classifications.json", add_historical_citation)

    def test_p003_src_cmake_reaudit_binds_current_inventory_and_preserves_history(self):
        self.add_reaudited_cmake()
        result = MODULE.check_reports(self.out, self.snapshot)
        self.assertEqual(result["source_citations_verified"], 9)
        self.assertEqual(result["tracked_entries"], 3)
        self.assertFalse(result["runtime_executed"])
        historical = self.read("classifications.json")["checked"][-1]
        self.assertEqual(historical["blob_sha1"], "0" * 40)
        self.assertEqual(historical["current_reaudit"]["blob_sha1"], "1" * 40)

    def test_p003_root_cmake_reaudit_binds_current_inventory(self):
        self.add_reaudited_cmake("CMakeLists.txt", "host-build-restrictions", "architecture_constraint", 1)
        self.assertEqual(MODULE.check_reports(self.out, self.snapshot)["source_citations_verified"], 9)

    def add_p004_upstream_reaudit(self):
        self.add_reaudited_cmake("CMakeLists.txt", "host-build-restrictions", "architecture_constraint", 1)
        self.mutate("classifications.json", lambda value: value["checked"][-1]["current_reaudit"].update({
            "phase": "P004", "kind": "p003-plus-reviewed-upstream-merge",
            "upstream_merge_commit": "5e08de551ae51ea8415bfad875ea95f0e44cda51",
            "prior_p003_blob_sha1": "6e5320117349ab0edead8ef0ee84ef41fd487e82",
            "additions_verified": 2,
        }))

    def test_p004_exact_upstream_source_reaudit_preserves_current_inventory(self):
        self.add_p004_upstream_reaudit()
        checked = MODULE.check_reports(self.out, self.snapshot)
        self.assertEqual(checked["source_citations_verified"], 9)
        self.assertEqual(checked["tracked_entries"], 3)
        self.assertFalse(checked["runtime_executed"])
        original = self.read("classifications.json")["checked"][-1]
        self.assertEqual(original["blob_sha1"], "0" * 40)
        self.assertEqual(original["current_reaudit"]["blob_sha1"], "1" * 40)

    def test_p004_reaudit_forgery_and_missing_tracking_cannot_pass(self):
        self.add_p004_upstream_reaudit()
        original = self.read("classifications.json")
        for edit in (
            lambda c: c["current_reaudit"].update(phase="P003"),
            lambda c: c["current_reaudit"].update(kind="arbitrary-source-changes"),
            lambda c: c["current_reaudit"].update(upstream_merge_commit="0" * 40),
            lambda c: c["current_reaudit"].update(prior_p003_blob_sha1="0" * 40),
            lambda c: c["current_reaudit"].update(additions_verified=1),
            lambda c: c["current_reaudit"].update(additions_verified=True),
            lambda c: c["current_reaudit"].update(original_assertions_preserved=False),
            lambda c: c["current_reaudit"].update(extra_waiver=True),
        ):
            with self.subTest(edit=edit):
                self.write("classifications.json", original)
                self.mutate("classifications.json", lambda value: edit(value["checked"][-1]))
                self.rejected()
        self.write("classifications.json", original)
        entries = self.read("tracked-files.json")["entries"]
        entries[-1]["object"] = "0" * 40
        self.set_tracked(entries)
        self.rejected()
    def test_p003_reaudit_cannot_bypass_unrelated_or_forged_current_inventory(self):
        self.add_reaudited_cmake()
        original = self.read("classifications.json")
        for edit in (
            lambda citation: citation.pop("current_reaudit"),
            lambda citation: citation.update(id="unreviewed-citation"),
            lambda citation: citation.update(path="README.md"),
            lambda citation: citation.update(repository="dep"),
            lambda citation: citation["current_reaudit"].update(phase="P002"),
            lambda citation: citation["current_reaudit"].update(kind="arbitrary-source-changes"),
            lambda citation: citation["current_reaudit"].update(additions_verified=1),
            lambda citation: citation["current_reaudit"].update(additions_verified=2),
            lambda citation: citation["current_reaudit"].update(additions_verified=True),
            lambda citation: citation["current_reaudit"].update(original_assertions_preserved=False),
            lambda citation: citation["current_reaudit"].update(blob_sha1="9" * 40),
            lambda citation: citation["current_reaudit"].update(blob_sha1="invalid"),
            lambda citation: citation["current_reaudit"].update(excerpt_sha256="invalid"),
            lambda citation: citation["current_reaudit"].update(unexpected="waiver"),
        ):
            with self.subTest(edit=edit):
                self.write("classifications.json", original)
                self.mutate("classifications.json", lambda manifest: edit(manifest["checked"][-1]))
                self.rejected()
        self.write("classifications.json", original)
        entries = self.read("tracked-files.json")["entries"]
        entries[-1]["object"] = "0" * 40
        self.set_tracked(entries)
        self.rejected()

    def test_missing_report_is_not_success(self):
        (self.out / "source-retrieval.json").unlink()
        with self.assertRaises(OSError):
            MODULE.check_reports(self.out, self.snapshot)

    def test_missing_license_arrays_are_rejected_even_without_candidates(self):
        self.mutate("inventory.json", lambda v: [r.pop("licenses") for r in v["repositories"]])
        self.rejected()

    def test_license_candidate_arrays_cannot_be_replaced_with_other_types(self):
        original = self.read("inventory.json")
        for wrong in (None, {}, "[]"):
            with self.subTest(value=wrong):
                self.mutate("inventory.json", lambda v: v["repositories"][0].update(licenses=wrong))
                self.rejected()
                self.write("inventory.json", original)

    def test_omitted_parent_or_child_license_candidate_is_rejected(self):
        self.add_license()
        self.add_license("dep", "LEGAL", reasons=["conventional_legal_notice_basename"])
        self.assertEqual(MODULE.check_reports(self.out, self.snapshot)["license_candidates_verified"], 2)
        original = self.read("inventory.json")
        for index in (0, 1):
            with self.subTest(repository=index):
                self.mutate("inventory.json", lambda v: v["repositories"][index].update(licenses=[]))
                self.rejected()
                self.write("inventory.json", original)

    def test_duplicate_or_untracked_license_candidates_are_rejected(self):
        self.add_license()
        original = self.read("inventory.json")
        for path in ("APPLE_LICENSE", "invented/COPYING"):
            with self.subTest(path=path):
                def mutation(value):
                    records = value["repositories"][0]["licenses"]
                    records.append({**records[0], "path": path})
                self.mutate("inventory.json", mutation)
                self.rejected()
                self.write("inventory.json", original)

    def test_license_candidate_metadata_tampering_is_rejected(self):
        self.add_license()
        original = self.read("inventory.json")
        mutations = (
            {"git_blob": "0" * 40}, {"mode": "100755"}, {"content_kind": "symlink_target_text"},
            {"discovery_reasons": []}, {"classification": "declared to be legally MIT licensed"},
            {"bytes": -1}, {"bytes": True}, {"bytes": "19"}, {"sha256": "z" * 64},
            {"sha256": "0" * 63}, {"sha256": None}, {"target_dereferenced": False},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.mutate("inventory.json", lambda v: v["repositories"][0]["licenses"][0].update(mutation))
                self.rejected()
                self.write("inventory.json", original)

    def test_repeated_license_blob_must_have_consistent_size_and_hash(self):
        self.add_license()
        self.add_license("dep", "COPYING")
        self.assertEqual(MODULE.check_reports(self.out, self.snapshot)["license_candidates_verified"], 2)
        original = self.read("inventory.json")
        for mutation in ({"bytes": 999}, {"sha256": "0" * 64}):
            with self.subTest(mutation=mutation):
                self.mutate("inventory.json", lambda v: v["repositories"][1]["licenses"][0].update(mutation))
                self.rejected()
                self.write("inventory.json", original)

    def test_license_symlink_target_and_digests_are_crosschecked(self):
        self.add_license(path="License", data=b"../../outside/private-file", mode="120000")
        self.assertEqual(MODULE.check_reports(self.out, self.snapshot)["license_candidates_verified"], 1)
        original = self.read("inventory.json")
        for mutation in ({"target_dereferenced": True}, {"symlink_target": "../different"},
                         {"bytes": 999}, {"sha256": "0" * 64}):
            with self.subTest(mutation=mutation):
                self.mutate("inventory.json", lambda v: v["repositories"][0]["licenses"][0].update(mutation))
                self.rejected()
                self.write("inventory.json", original)
        # Even a coordinated record/tracked-object forgery must match the raw target's Git blob hash.
        entries = self.read("tracked-files.json")["entries"]
        next(entry for entry in entries if entry["path"] == "License")["object"] = "0" * 40
        self.set_tracked(entries)
        self.mutate("inventory.json", lambda v: v["repositories"][0]["licenses"][0].update(git_blob="0" * 40))
        self.rejected()

    def test_unavailable_direct_content_cannot_pass_with_true_summary(self):
        self.mutate("inventory.json", lambda v: v["submodules"][0].update(content_status="not_checked_out", recursive_inventory="unavailable"))
        self.rejected()

    def test_missing_nested_content_cannot_pass_with_true_summary(self):
        self.add_nested()
        self.mutate("inventory.json", lambda v: v["submodules"][1].update(content_status="not_checked_out"))
        self.rejected()

    def test_missing_child_repository_cannot_be_faked_by_available_status(self):
        self.mutate("inventory.json", lambda v: v["repositories"].pop())
        self.rejected()

    def test_omitted_nested_record_is_detected_in_tracked_gitlinks(self):
        self.add_nested()
        def mutation(v):
            v["submodules"].pop()
            v["repositories"].pop()
            v["summary"].update(gitlinks=1, available_gitlinks=1, inspected_repositories=2)
        self.mutate("inventory.json", mutation)
        self.rejected()

    def test_invented_recursive_dependency_without_tracked_gitlink_fails(self):
        self.add_nested()
        self.set_tracked([e for e in self.read("tracked-files.json")["entries"] if e["path"] != "dep/child"])
        self.mutate("inventory.json", lambda v: v["summary"].update(tracked_entries=3))
        self.rejected()

    def test_false_summary_counts_and_completeness_fail(self):
        for key, wrong in (("gitlinks", 149), ("available_gitlinks", 0), ("unavailable_gitlinks", 1),
                           ("inspected_repositories", 1), ("recursive_content_complete", False), ("error_count", False)):
            with self.subTest(key=key):
                original = self.read("inventory.json")
                self.mutate("inventory.json", lambda v: v["summary"].update({key: wrong}))
                self.rejected()
                self.write("inventory.json", original)

    def test_changed_dependency_pin_is_rejected(self):
        self.mutate("inventory.json", lambda v: v["submodules"][0].update(commit="wrong"))
        self.rejected()

    def test_wrong_nested_pin_is_rejected_without_changing_root_oracle(self):
        self.add_nested()
        self.mutate("inventory.json", lambda v: v["submodules"][1].update(commit="wrong", checkout_head="wrong"))
        self.rejected()

    def test_wrong_tracked_nested_pin_is_rejected(self):
        self.add_nested()
        entries = self.read("tracked-files.json")["entries"]
        next(e for e in entries if e["path"] == "dep/child")["object"] = "wrong"
        self.set_tracked(entries)
        self.rejected()

    def test_wrong_repository_ownership_is_rejected(self):
        self.add_nested()
        self.mutate("inventory.json", lambda v: v["submodules"][1].update(repository=".", repository_path="dep/child"))
        self.rejected()

    def test_staged_index_pin_cannot_hide_behind_clean_boolean(self):
        self.mutate("inventory.json", lambda v: v["repositories"][0]["index_gitlinks"][0].update(object="wrong"))
        self.rejected()

    def test_physical_blob_count_cannot_hide_behind_clean_boolean(self):
        self.mutate("inventory.json", lambda v: v["repositories"][1]["materialization"].update(verified_blobs=0))
        self.rejected()

    def test_source_retrieval_failure_is_rejected(self):
        self.mutate("source-retrieval.json", lambda v: v.update(result="FAIL", failures=["fetch failed"]))
        self.rejected()

    def test_stale_retrieval_revision_is_rejected(self):
        self.mutate("source-retrieval.json", lambda v: v["source"].update(commit="stale"))
        self.rejected()

    def test_forged_retrieval_origin_is_rejected(self):
        self.mutate("source-retrieval.json", lambda v: v["submodules"][0].update(fetch_url="https://wrong.test/repo.git"))
        self.rejected()

    def test_forged_nested_effective_url_is_rejected(self):
        self.add_nested()
        self.mutate("inventory.json", lambda v: v["submodules"][1].update(effective_resolved_url="https://fork.test/child.git"))
        self.rejected()

    def test_forged_recovered_revision_is_rejected(self):
        self.mutate("recovery.json", lambda v: v["snapshots"][0].update(commit="wrong"))
        self.rejected()

    def test_shared_object_store_is_rejected(self):
        self.mutate("recovery.json", lambda v: v["snapshots"][1].update(independent_object_store=False))
        self.rejected()

    def test_truncated_tracked_manifest_is_rejected(self):
        self.write("tracked-files.json", {"entries": []})
        self.rejected()

    def test_stale_citation_revision_is_rejected(self):
        self.mutate("classifications.json", lambda v: v.update(current_commit="stale"))
        self.rejected()

    def test_unrequired_phase_coverage_is_rejected(self):
        self.mutate("classifications.json", lambda v: v["coverage"].update(required=False))
        self.rejected()

    def test_phase_coverage_summary_cannot_conceal_missing_source_class(self):
        self.mutate("classifications.json", lambda v: v["checked"][-1].update(category="native_linux_host"))
        self.rejected()

    def test_phase_coverage_summary_cannot_conceal_missing_launch_stage(self):
        self.mutate("classifications.json", lambda v: v["checked"][0]["launch_stages"].pop())
        self.rejected()

    def test_child_citation_blob_must_exist_in_tracked_source(self):
        self.mutate("classifications.json", lambda v: v["checked"][0].update(blob_sha1="wrong"))
        self.rejected()

    def test_child_source_citation_must_match_recursive_pin(self):
        self.mutate("classifications.json", lambda v: v["checked"][0].update(repository="dep", repository_commit="wrong"))
        self.rejected()

    def test_complete_nested_gitlinks_leave_parent_oracle_unchanged(self):
        self.add_nested()
        result = MODULE.check_reports(self.out, self.snapshot)
        self.assertEqual(result["known_gitlinks_verified"], 1)
        self.assertEqual(result["recursive_gitlinks_verified"], 2)
        self.assertEqual(result["source_repositories_verified"], 3)

    def test_duplicate_recursive_gitlink_is_rejected(self):
        self.mutate("inventory.json", lambda v: v["submodules"].append(dict(v["submodules"][0])))
        self.rejected()



class ReviewedCurrentSourceTests(unittest.TestCase):
    """Historical recovery and reviewed current sources are separate oracles."""

    def setUp(self):
        self.fixture = CampaignEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def prepare(self, nested=False):
        case = self.fixture
        if nested:
            case.add_nested()
        before = case.read("inventory.json")
        old_records = {
            module["path"]: {"path": module["path"], "parent_path": module["repository"],
                             "commit": module["commit"], "tree": module["commit"] + "-tree",
                             "resolved_url": module["source_origin"]}
            for module in before["submodules"]
        }
        pin, blob, anchor = "a" * 40, "b" * 40, "d" * 40
        before["submodules"][0].update(commit=pin, checkout_head=pin)
        before["repositories"][0]["index_gitlinks"][0]["object"] = pin
        child = before["repositories"][1]
        child.update(commit=pin, checkout_head=pin, tree=pin + "-tree")
        child["materialization"]["reference_commit"] = pin
        case.write("inventory.json", before)
        entries = case.read("tracked-files.json")["entries"]
        for entry in entries:
            if entry["path"] == "dep":
                entry["object"] = pin
            elif entry["path"] == "dep/source.c":
                entry["object"] = blob
        case.set_tracked(entries)
        case.mutate("source-retrieval.json", lambda value: value["submodules"][0].update(
            commit=pin, tree=pin + "-tree"))
        current_records = {path: dict(record) for path, record in old_records.items()}
        current_records["dep"].update(commit=pin, tree=pin + "-tree")
        self.provenance = {"historical_records": old_records, "current_records": current_records,
                           "current_source_anchor": anchor}
        report = case.read("classifications.json")
        originals, current = [], []
        for record in report["checked"]:
            record.update(gitlink_chain=[{"path": "dep", "commit": "pin"}],
                          line_start=1, line_end=1, excerpt_sha256="e" * 64)
            originals.append(dict(record, contains=["documented assertion"]))
            meta = {"id": record["id"], "repository": "dep", "path": "source.c",
                    "repository_commit": pin, "gitlink_chain": [{"path": "dep", "commit": pin}],
                    "blob_sha1": blob, "line_start": 1, "line_end": 2, "excerpt_sha256": "c" * 64,
                    "contains": ["documented assertion"]}
            current.append(meta)
            result = {key: value for key, value in meta.items() if key not in ("id", "contains")}
            result.update(source_anchor=anchor, assertions_verified=1, original_assertions_preserved=True)
            record["current_source"] = result
        case.write("classifications.json", report)
        self.manifest = {"inspected_commit": "original", "evidence": originals,
                         "current_source_reaudit": {"schema_version": 1, "source_anchor": anchor,
                                                     "evidence": current}}
        return self.check()

    def check(self):
        return MODULE.check_reports(self.fixture.out, self.fixture.snapshot,
                                    reviewed_source=self.provenance, citation_manifest=self.manifest)

    def test_current_graph_and_historical_recovery_are_both_required(self):
        result = self.prepare()
        self.assertEqual(result["reviewed_dependency_updates"], 1)
        self.assertFalse(result["runtime_executed"])
        self.assertEqual(self.fixture.read("recovery.json")["snapshots"][0]["gitlinks"][0]["commit"], "pin")
        with self.assertRaises(ValueError):
            MODULE.check_reports(self.fixture.out, self.fixture.snapshot)

    def test_current_pins_cannot_replace_original_recovery_oracle(self):
        self.prepare()
        self.fixture.mutate("recovery.json", lambda value: value["snapshots"][0]["gitlinks"][0].update(commit="a" * 40))
        with self.assertRaisesRegex(ValueError, "recovered baseline"):
            self.check()

    def test_historical_graph_cannot_be_rewritten_to_match_current(self):
        self.prepare()
        self.provenance["historical_records"]["dep"]["commit"] = "a" * 40
        with self.assertRaisesRegex(ValueError, "immutable baseline"):
            self.check()

    def test_unknown_current_pin_tree_parent_or_origin_is_rejected(self):
        self.prepare()
        for field, value in (("commit", "unknown"), ("tree", "unknown"),
                             ("parent_path", "unknown"), ("resolved_url", "https://wrong.test/source")):
            with self.subTest(field=field):
                old = self.provenance["current_records"]["dep"][field]
                self.provenance["current_records"]["dep"][field] = value
                with self.assertRaises(ValueError):
                    self.check()
                self.provenance["current_records"]["dep"][field] = old

    def test_missing_nested_current_provenance_is_rejected(self):
        self.prepare(nested=True)
        del self.provenance["current_records"]["dep/child"]
        with self.assertRaisesRegex(ValueError, "graphs are incomplete"):
            self.check()

    def test_forged_current_citation_identity_and_bytes_are_rejected(self):
        self.prepare()
        original = self.fixture.read("classifications.json")
        for key, value in (("repository_commit", "f" * 40), ("blob_sha1", "f" * 40),
                           ("source_anchor", "f" * 40), ("excerpt_sha256", "f" * 64),
                           ("repository", "."), ("line_end", 99), ("assertions_verified", True),
                           ("assertions_verified", 0), ("original_assertions_preserved", False)):
            with self.subTest(key=key, value=value):
                report = json.loads(json.dumps(original))
                report["checked"][0]["current_source"][key] = value
                self.fixture.write("classifications.json", report)
                with self.assertRaises(ValueError):
                    self.check()
        self.fixture.write("classifications.json", original)

    def test_current_chain_must_match_reviewed_graph_even_if_report_and_metadata_agree(self):
        self.prepare()
        self.manifest["current_source_reaudit"]["evidence"][0]["gitlink_chain"] = []
        self.fixture.mutate("classifications.json", lambda value: value["checked"][0]["current_source"].update(gitlink_chain=[]))
        with self.assertRaisesRegex(ValueError, "owner chains"):
            self.check()

    def test_historical_citation_bytes_remain_immutable(self):
        self.prepare()
        self.fixture.mutate("classifications.json", lambda value: value["checked"][0].update(blob_sha1="f" * 40))
        with self.assertRaisesRegex(ValueError, "immutable historical"):
            self.check()

    def test_duplicate_or_missing_current_citation_cannot_pass(self):
        self.prepare()
        self.fixture.mutate("classifications.json", lambda value: value["checked"][1].update(id=value["checked"][0]["id"]))
        with self.assertRaisesRegex(ValueError, "duplicated or unreviewed"):
            self.check()

    def test_absent_current_result_and_missing_assertions_fail(self):
        self.prepare()
        report = self.fixture.read("classifications.json")
        report["checked"][0].pop("current_source")
        self.fixture.write("classifications.json", report)
        with self.assertRaisesRegex(ValueError, "every historical citation"):
            self.check()
        report["checked"][0]["current_source"] = dict(
            self.fixture.read("classifications.json")["checked"][1]["current_source"])
        self.fixture.write("classifications.json", report)
        self.manifest["current_source_reaudit"]["evidence"][0]["contains"] = []
        with self.assertRaises(ValueError):
            self.check()




if __name__ == "__main__":
    unittest.main()
