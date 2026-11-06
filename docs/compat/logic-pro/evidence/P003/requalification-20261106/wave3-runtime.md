# Wave 3: independent runtime and evidence review

## Identity, scope and verdict

- Reviewer: `/root/wave3_runtime`, a non-author of the Wave 2 runtime correction and the reviewed production drivers.
- Review completed: **2026-11-06T05:58:38Z**.
- Tested implementation: **`af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`**.
- Implementation tree: `84fc6c85fc4d2a9c3611dc0dd757a34a0dff4c71`.
- Documentation-only checkout at review start: `b815ab202207b1ce43dfc713b3c4c35c0f1983ed`.
- Pre-correction comparison: `d0f33422fba168ca83b7052ba06b624f8892af1f`, the parent of the tested implementation.
- Verdict: **PASS for the bounded initialization correction and preservation of the runtime/evidence contract. Current installed-runtime acceptance remains PENDING.** No new blocking defect was demonstrated in this review.

This is Wave 3 of five. The reviewer read `AGENTS.md`, the README global gate contract and current P003 entry, the actual runtime/reporting diff, the installed probes, the comparison gates and the two independent archive/runtime drivers. No production file, workflow, README or dependency pin was changed by this reviewer. The only authored deliverable is this review record. No restricted source, proprietary application or Apple binary was inspected.

The review does **not** accept G1, G2, G3 or G4 for this candidate. Fresh original artifacts from run `42169925661`, two successful builds, four first/reinstall runtime campaigns, a fifth source-free archive replay and final non-author evidence acceptance are still required. Historical `89c6c9d` execution is used below only to check the review method.

## Exact file and dependency binding

The nine implementation/probe files in the first table were compared byte-for-byte with `git show af3566ee:<path>`; all matched. There was no current diff in those drivers or the build-test directory. The first three SHA-256 values also match `wave2-integration.json` exactly. That integration record itself hashes to `152386a8c4ec3a6fde0f97bf772302cc42ea70d10c2b341b4d1515d08f3edf79`.

| Reviewed path | SHA-256 |
| --- | --- |
| `tools/compat/logic-pro/run_build_probes.py` | `3e778e7fe42fb2897b2f7244490008361f964d02fe17816c1729d6d69d9df541` |
| `tests/compat/logic-pro/build/test_probes.py` | `5c2c45b5c03a3fff923d97009c6743c2f3fa52b22aa2b89cc2b5ceefab6f6247` |
| `tools/compat/logic-pro/compare_p003.py` | `e60cb440b933d5b0e89d19f40bbb80285206791d9b6062c1aaada6685193c240` |
| `tools/compat/logic-pro/review_installed_runtime.py` | `d2cf2a5d4d50d7c3e8574dbb696a7f076c2d2cb4543972ccbe3f935968ad6edc` |
| `tools/compat/logic-pro/review_package_archive.py` | `cede93530d11d2611ef43e9acb848c2a71f463cf8c7d6b3b3af5051a51c76d52` |
| `tests/compat/logic-pro/build/macho.c` | `350d965c030b7fa33ca80ebd4132ca87cd6f348922cf9e5c72b3491d0b428fd2` |
| `tests/compat/logic-pro/build/foundation.m` | `c3d2fd926dfdf4944cb9a23b12ad3de7bd979aedc9a1d5d62c8f93d26bedd6b3` |
| `tests/compat/logic-pro/build/gui.m` | `54bc9ebae6f7cfb3e58521b0976b09ad99a7a7918357ed2836e66dc65794d875` |
| `tests/compat/logic-pro/build/images.h` | `bd894d1cb17f9287cb2c8e77277baa38d2477a980a9eb7223304d5726f7549b7` |

Additional inspected orchestration and exercised regression files:

| Path | SHA-256 |
| --- | --- |
| `ci/logic-pro/build-p003.sh` | `b73c2b49a22914e339d9db87d2d813fcc6823801fc960cbcb6010640c48d52f5` |
| `.github/workflows/phase3-build.yml` | `5061eb70814017e8eaeb89562ae42c3e75da30842e86ae579d163c0d4b979cac` |
| `tests/compat/logic-pro/build/test_runtime_review.py` | `bf499dd78fb6d15c4af13f4384d7a0d22f2e357637cf3658d04142e9498e6b0f` |
| `tests/compat/logic-pro/build/test_independent_review.py` | `079c22bd169d71b217c4fa8b1dd881d7684dad032726368d4414adedc70cb145` |
| `tests/compat/logic-pro/build/test_comparison.py` | `8eb69d881cf502a9e1c96e27c9a9a019461d30c251396471aad4ee0c19b1b0d8` |

The orchestration hashes also match `wave2-integration.json`; workflow content was read solely to confirm the existing source-free replay boundary.

Relevant gitlinks obtained from the exact candidate tree, without opening dependency implementation source:

| Dependency | Commit |
| --- | --- |
| `src/external/cocotron` | `d89d7aa029c1ca2d297372fc7f618e9b006112d0` |
| `src/external/corefoundation` | `3469fdf6904155e0efa84a6d6ca58a6986890c25` |
| `src/external/darlingserver` | `498f7c14265d58d0849e144ce18fd700e8c5c989` |
| `src/external/foundation` | `a8b5ab193a107712d0806b6f95bfa763be68e1f8` |
| `src/external/libxpc` | `394e033333d3c253a12f08a99090c113b0917d00` |
| `src/external/objc4` | `092352cab947b410a73b5123b190df03f90c1802` |

The complete recursive dependency lock remains the integration record's `docs/compat/logic-pro/submodules.lock.json`, SHA-256 `2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`. The frozen toolchain lock remains SHA-256 `aef0e952e8fe505191ce8dfaec146e7fd27036d10b52b8b4efdb76dfae319963`.

## Initialization-failure reproduction and review

The reviewed change initializes `campaign` to `None`, validates the runtime prefix before constructing `Campaign`, and constructs it inside the existing reporting `try` block. Known constructor failures populate `errors`; an unexpected `Exception` records its type and text and is re-raised with its traceback. The finalizer only calls shutdown if a campaign was constructed and a runtime launch was attempted. Absent initialization produces empty command/case arrays and null lifecycle/HOME fields. This does not manufacture a shutdown or runtime result.

The output directory is claimed with exclusive creation before setup. Existing output directories, files and symlinks are rejected. The report is also opened with mode `x`, so a report appearing during initialization is preserved rather than overwritten. The actual fix changes reporting and ordering, with no successful probe assertion removed.

I independently executed the parent and current versions of `run()` from their exact source bytes in temporary directories. Each case had an existing `prefix.home` containing a sentinel and no runtime installation or prefix. Loading the old source used `git show af3566ee^:tools/compat/logic-pro/run_build_probes.py`; current source came from the hash-bound path above. Both calls used the same arguments and filesystem setup.

| Observation | Parent `d0f33422` | Candidate `af3566ee` |
| --- | --- | --- |
| Result | Raised `ProbeFailure: controlled runtime HOME must be absent` | Returned `1` |
| `report.json` created | No | Yes |
| Report status / passed | No report | `FAILED` / `false` |
| Report errors | No report | `["controlled runtime HOME must be absent"]` |
| Cases / commands | No report | `[]` / `[]` |
| Lifecycle / controlled HOME | No report | `null` / `null` |
| Existing HOME sentinel | Intact | Intact |
| Runtime prefix | Absent | Absent |

The focused regression run also reproduced constructor `OSError`, unexpected `KeyError` identity and original traceback preservation, existing HOME/output directory/file/symlink/dangling-symlink collisions, dirty-prefix preservation, and a concurrent report collision. Unexpected exceptions still propagate; collisions still fail without replacing the existing evidence.

## Runtime and replay requirements preserved

| Requirement | Source and evidence checks inspected |
| --- | --- |
| Real nonce computation | `macho.c` executes the FNV-1a recurrence over the supplied input using a volatile accumulator. The host checks its own fixed vector, then a fresh 16-hex-character nonce and the 64-character boundary. Empty/missing arguments and 65-character input must explicitly reject with exit `64`. The independent driver uses a different fixed vector (`foobar`) and a separately implemented recurrence. |
| Foundation objects and live transactions | `foundation.m` creates and sorts an array, joins it, stores array/number objects in a mutable dictionary, verifies count/value/missing-key behavior and binary `NSData`, and round-trips the nonce through `NSString`. It then observes `_vproc_transaction_count()` around `xpc_transaction_begin`, `_vproc_transaction_begin`, `xpc_transaction_end`, `_vproc_transaction_end`. The expected live deltas are **+1,+2,+1,0**. Both Foundation and transaction records are required by both drivers and both aggregate review paths. A Foundation-only record cannot pass. |
| Seven actual framework owners | `images.h` opens AppKit C, Foundation C, CoreGraphics A, CoreText A, ImageIO A, QuartzCore A and AudioToolbox A; it enumerates dyld images, rejects competing paths and requires exactly one canonical image for each. Handles remain open through GUI execution. Install reports and live loaded-image records are both required. This preserves the P003 load/owner gate and does not claim comprehensive behavior of every framework API. |
| External GUI events and pixels | Both drivers select a nonce-titled visible X11 window, capture its initial red/blue pixels, focus it, move the pointer, inject a click and the nonce through `xdotool`, observe the same window after its title changes, capture green/yellow pixels, then inject Return. The AppKit probe uses actual event dispatch and requires one click, the full challenge, at least two draws, visibility and acknowledgement. No driver calls the view's event handlers directly. |
| Independent pixel oracle | Original XWD bytes remain authoritative; encoded PNG bytes must reproduce them. The independently authored driver decodes the XWD format separately and checks 25 pixels in each half in each state. Blank/wrong-state/malformed images and corruption away from the central sample are covered by tests. |
| Shutdown lifecycle | Both drivers obtain the runtime server PID and start time from the kernel, require its private mount namespace to differ from the caller's, issue actual shutdown, and require both the original server identity to disappear and all namespace holders to exit. The independent driver retains original server stat bytes and caller mount information. A mere empty caller mount table is insufficient. |
| Fresh reinstall | The build script removes the verified installation, confirms its absence, removes the first stopped runtime prefix plus HOME/workdir after mount checks, installs again and uses distinct second-run paths. Each run creates a controlled HOME and filters inherited environment. The comparator requires equal first/second inventories and four distinct campaign nonces. |
| Independent installed-archive replay | The workflow uses a separate network-disabled privileged container, the frozen toolchain, the original installed archive/manifest and only the two reviewer files. It does not mount the source or build trees. The independent runtime preflight inspects actual mount information, rejects source/build checkout mounts, verifies fresh prefix/HOME/workdir paths, records its exact driver and hashes installed executables. The fifth nonce must differ from all four producer campaigns. |
| Archive fidelity | `review_package_archive.py` imports no producer package verifier. It rejects duplicate/unsafe paths, changed bytes/modes/links and missing/extra members, checks hardlink content, creates a new destination and uses directory-relative no-follow extraction. It then rechecks the extracted installation. The aggregate binds archive, manifest, destination, entry count, driver and toolchain identities. |
| Truthful failure evidence | Raw command exit codes and the complete required command set are checked independently of reported case success. Reached stub/unimplemented diagnostics in original stdout/stderr remain errors with `STUB_VERBOSE=1`. Missing records, omitted negative cases, changed probe identities and failed namespace release remain disqualifying. |

## Focused adversarial regression result

Command, executed from the repository root:

```sh
PYTHONPATH=tests/compat/logic-pro/build \
PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH \
python3 -m unittest test_probes test_runtime_review test_comparison test_independent_review -v
```

**76 tests passed, zero skips, 9.093 seconds, process exit `0`.** The original captured stdout/stderr transcript has SHA-256 `f85ba5eabca06205457add0583d7184d6319fbd66e7a245c1810ac57d5bd27cd` and is embedded verbatim at the end of this document. These are parser, lifecycle-driver, failure and extraction regressions; they are not installed-runtime executions.

In addition to initialization cases, the run exercises rehashed missing transaction results, wrong FNV/Foundation/GUI results, omitted XTest commands and negative cases, forged exits, changed binaries, stub diagnostics concealed by an empty summary, retained mount namespaces, stale HOME, daemon descriptor timeouts, noncentral pixel corruption, unsafe archive entries, source/build mounts and reuse of prior nonces.

## Historical original-artifact method QA

Only for method QA, I read the unchanged original runtime reports from run `41292343355`, source **`89c6c9d85aba6ed1662035e6366298c92ef9c970`**, under the coordinator's verified `build-a` and `build-b` artifact extracts. This did not launch an old installed runtime or transfer its acceptance to the new candidate.

For each of the four real historical reports, I ran the current `compare_p003.validate_probes` against the matching original install manifest. I separately decoded both original XWD images with `review_installed_runtime.decode_xwd` and checked 25 pixels per half through `inspect_color_patches`. I also read the original command arguments and required `xdotool click 1`, typing the actual campaign nonce, and `xdotool key Return`.

| Historical campaign | Nonce | Original report SHA-256 |
| --- | --- | --- |
| Build A first | `5a92669296f99425` | `3ecac3d1ad54bdaf3cd60b6c384b6c1b695f7fb1a07a317c12cc30129b9dd6e8` |
| Build A second | `80d3a52251322512` | `f21f61c8d4e0683777ac2915e5d92781e3bb20469cd8d643d2d0cd604783680f` |
| Build B first | `f873b135c55c0f3a` | `c613e0f538f247f4a2321b40be735c699fcd915a959dfff31612fa0b80b2c4ce` |
| Build B second | `067b5b2d75eac859` | `16861510226454dc512671988e40c8bf17550da4783f57601c57cf5620357fea` |

All four historical reports supplied ten accepted cases to the parser. All eight independent image decodes found the expected red/blue or green/yellow patches with **zero maximum channel error**. These observations qualify the method against existing real evidence only.

I then copied the first historical probe evidence into separate temporary directories and changed each copy independently. The original artifacts were untouched. Deliberately wrong raw stdout was rehashed in the report so rejection could not be attributed only to a digest mismatch:

| Deliberate corruption | Actual rejection |
| --- | --- |
| Delete `P003_TRANSACTION`, retaining the real Foundation object record, and update its raw-log SHA-256 | Missing `P003_TRANSACTION ... deltas=1|2|1|0` |
| Replace the nonce computation result with `00000000` and update its raw-log SHA-256 | Expected FNV `e0573625`; actual `00000000` |
| Remove the `gui-acknowledge` Return command | `Required runtime command evidence missing` |
| Set `namespace_holders_after` to a surviving PID | `Runtime namespace shutdown was not proved` |

## Required fresh-artifact review for Waves 4–5

The following are the concrete remaining evidence requirements, not additional phase scope:

1. Verify original uploaded artifact identities, ZIP CRC/member hashes and the actual source revision of every report. It must be `af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`; old `89c6c9d` reports and documentation-only HEAD labels cannot supply current implementation evidence.
2. Inspect all four new first/second probe campaigns against their own install manifests. Recompute expected nonce results, inspect Foundation **and** transaction lines, the seven canonical loaded images, negative exits and rejection text, original command arguments, original XWD/PNG correspondence, stub diagnostics and exact probe identities.
3. Independently decode the real before/after screenshots with the separate decoder and inspect the images. Bind shutdown to the actual runtime server identity/private namespace and verify all holders exited. Confirm fresh HOME/prefix state and distinct nonces across reinstall and across hosts.
4. Verify uninstall evidence and matching first/second package inventories. The source-free replay must use the exact verified installed archive, frozen toolchain and hash-bound reviewer drivers, with raw mount information excluding source/build trees. Require its ten actual cases, fresh fifth nonce, independent X11 evidence and successful shutdown.
5. Preserve complete original artifacts and obtain separate dated non-author G1–G4 verdicts, including the package/output-nondeterminism review owned by other reviewers. Fixture counts and this code review alone cannot supply those verdicts.

**Exact remaining blocker:** current-candidate installed-runtime artifacts and final original-evidence review are not yet available to this reviewer. **Remain in P003.**

## Original focused test transcript

The following block preserves the captured test output without alterations.

```text
test_bad_xwd_metadata_rejected (test_probes.EvidenceTests.test_bad_xwd_metadata_rejected) ... ok
test_blank_window_does_not_pass (test_probes.EvidenceTests.test_blank_window_does_not_pass) ... ok
test_command_failure_and_timeout_recorded (test_probes.EvidenceTests.test_command_failure_and_timeout_recorded) ... ok
test_controlled_home_collision_writes_failure_and_preserves_paths (test_probes.EvidenceTests.test_controlled_home_collision_writes_failure_and_preserves_paths) ... ok
test_dirty_prefix_rejected (test_probes.EvidenceTests.test_dirty_prefix_rejected) ... ok
test_duplicate_success_not_accepted (test_probes.EvidenceTests.test_duplicate_success_not_accepted) ... ok
test_elf_or_foreign_macho_not_accepted (test_probes.EvidenceTests.test_elf_or_foreign_macho_not_accepted) ... ok
test_exact_output_required (test_probes.EvidenceTests.test_exact_output_required) ... ok
test_fnv_reference_vectors (test_probes.EvidenceTests.test_fnv_reference_vectors) ... ok
test_framework_image_paths (test_probes.EvidenceTests.test_framework_image_paths) ... ok
test_initialization_oserror_writes_failure_without_execution (test_probes.EvidenceTests.test_initialization_oserror_writes_failure_without_execution) ... ok
test_late_report_collision_preserves_existing_report (test_probes.EvidenceTests.test_late_report_collision_preserves_existing_report) ... ok
test_missing_display_writes_failure_not_success (test_probes.EvidenceTests.test_missing_display_writes_failure_not_success) ... ok
test_missing_framework_image (test_probes.EvidenceTests.test_missing_framework_image) ... ok
test_output_collision_preserves_existing_evidence (test_probes.EvidenceTests.test_output_collision_preserves_existing_evidence) ... ok
test_png_copy_signature (test_probes.EvidenceTests.test_png_copy_signature) ... ok
test_truncated_and_trailing_xwd_rejected (test_probes.EvidenceTests.test_truncated_and_trailing_xwd_rejected) ... ok
test_unexpected_initialization_error_records_failure_and_preserves_traceback (test_probes.EvidenceTests.test_unexpected_initialization_error_records_failure_and_preserves_traceback) ... ok
test_wrong_state_does_not_pass_pixels (test_probes.EvidenceTests.test_wrong_state_does_not_pass_pixels) ... ok
test_xwd_little_and_big_endian_pixels (test_probes.EvidenceTests.test_xwd_little_and_big_endian_pixels) ... ok
test_independent_capture_handles_daemon_descriptors_and_kills_timeout (test_runtime_review.IndependentRuntimeDriverReview.test_independent_capture_handles_daemon_descriptors_and_kills_timeout) ... ok
test_pixel_layouts_png_bytes_and_noncentral_patch_corruption (test_runtime_review.IndependentRuntimeDriverReview.test_pixel_layouts_png_bytes_and_noncentral_patch_corruption) ... ok
test_malformed_process_identity_is_an_error (test_runtime_review.RuntimeBoundaryReview.test_malformed_process_identity_is_an_error) ... ok
test_namespace_holders_are_checked_outside_caller_mountinfo (test_runtime_review.RuntimeBoundaryReview.test_namespace_holders_are_checked_outside_caller_mountinfo) ... ok
test_old_controlled_home_cannot_supply_reinstall_dependencies (test_runtime_review.RuntimeBoundaryReview.test_old_controlled_home_cannot_supply_reinstall_dependencies) ... ok
test_persistent_daemon_descriptors_do_not_timeout_completed_command (test_runtime_review.RuntimeBoundaryReview.test_persistent_daemon_descriptors_do_not_timeout_completed_command) ... ok
test_process_identity_parses_kernel_comm_with_spaces_and_parentheses (test_runtime_review.RuntimeBoundaryReview.test_process_identity_parses_kernel_comm_with_spaces_and_parentheses) ... ok
test_real_framework_placeholder_diagnostics_preserve_original_lines (test_runtime_review.RuntimeBoundaryReview.test_real_framework_placeholder_diagnostics_preserve_original_lines) ... ok
test_shutdown_rejects_surviving_private_namespace_holder (test_runtime_review.RuntimeBoundaryReview.test_shutdown_rejects_surviving_private_namespace_holder) ... ok
test_shutdown_requires_server_exit_and_no_namespace_holders (test_runtime_review.RuntimeBoundaryReview.test_shutdown_requires_server_exit_and_no_namespace_holders) ... ok
test_startup_receives_fresh_explicit_home_without_private_environment (test_runtime_review.RuntimeBoundaryReview.test_startup_receives_fresh_explicit_home_without_private_environment) ... ok
test_stub_logging_cannot_be_disabled_by_inherited_environment (test_runtime_review.RuntimeBoundaryReview.test_stub_logging_cannot_be_disabled_by_inherited_environment) ... ok
test_success_records_and_environment_metadata_are_not_stub_calls (test_runtime_review.RuntimeBoundaryReview.test_success_records_and_environment_metadata_are_not_stub_calls) ... ok
test_changed_toolchain_cannot_count_as_reproducible (test_comparison.CrossBuildGateTests.test_changed_toolchain_cannot_count_as_reproducible) ... ok
test_copied_runtime_campaigns_cannot_count_as_two_builds (test_comparison.CrossBuildGateTests.test_copied_runtime_campaigns_cannot_count_as_two_builds) ... ok
test_output_nondeterminism_is_enumerated_without_claiming_phase_pass (test_comparison.CrossBuildGateTests.test_output_nondeterminism_is_enumerated_without_claiming_phase_pass) ... ok
test_changed_archive_content_permissions_and_traversal_fail_before_extraction (test_comparison.IndependentArchiveTests.test_changed_archive_content_permissions_and_traversal_fail_before_extraction) ... ok
test_existing_destination_symlink_is_never_followed (test_comparison.IndependentArchiveTests.test_existing_destination_symlink_is_never_followed) ... ok
test_faithful_extraction_preserves_guest_absolute_symlink_and_forward_hardlink (test_comparison.IndependentArchiveTests.test_faithful_extraction_preserves_guest_absolute_symlink_and_forward_hardlink) ... ok
test_manifest_cannot_traverse_guest_symlink_or_claim_another_commit (test_comparison.IndependentArchiveTests.test_manifest_cannot_traverse_guest_symlink_or_claim_another_commit) ... ok
test_claimed_negative_case_without_raw_command_is_rejected (test_comparison.ProbeEvidenceGateTests.test_claimed_negative_case_without_raw_command_is_rejected) ... ok
test_claimed_shutdown_without_raw_command_is_rejected (test_comparison.ProbeEvidenceGateTests.test_claimed_shutdown_without_raw_command_is_rejected) ... ok
test_complete_synthetic_report_is_accepted_for_parser_testing (test_comparison.ProbeEvidenceGateTests.test_complete_synthetic_report_is_accepted_for_parser_testing) ... ok
test_empty_summary_cannot_hide_hashed_raw_placeholder_execution (test_comparison.ProbeEvidenceGateTests.test_empty_summary_cannot_hide_hashed_raw_placeholder_execution) ... ok
test_modified_raw_log_is_rejected (test_comparison.ProbeEvidenceGateTests.test_modified_raw_log_is_rejected) ... ok
test_placeholder_diagnostics_must_be_enabled_and_empty (test_comparison.ProbeEvidenceGateTests.test_placeholder_diagnostics_must_be_enabled_and_empty) ... ok
test_rehashed_foundation_without_live_transaction_interop_is_rejected (test_comparison.ProbeEvidenceGateTests.test_rehashed_foundation_without_live_transaction_interop_is_rejected) ... ok
test_report_cannot_redefine_a_failed_positive_exit_as_expected (test_comparison.ProbeEvidenceGateTests.test_report_cannot_redefine_a_failed_positive_exit_as_expected) ... ok
test_report_cannot_redefine_a_negative_success_as_expected (test_comparison.ProbeEvidenceGateTests.test_report_cannot_redefine_a_negative_success_as_expected) ... ok
test_required_external_input_command_cannot_be_omitted (test_comparison.ProbeEvidenceGateTests.test_required_external_input_command_cannot_be_omitted) ... ok
test_same_size_wrong_probe_binary_is_rejected (test_comparison.ProbeEvidenceGateTests.test_same_size_wrong_probe_binary_is_rejected) ... ok
test_screenshot_cannot_borrow_another_file_through_symlink (test_comparison.ProbeEvidenceGateTests.test_screenshot_cannot_borrow_another_file_through_symlink) ... ok
test_all_required_cases_must_be_present_once_and_pass (test_independent_review.IndependentReviewGateTests.test_all_required_cases_must_be_present_once_and_pass) ... ok
test_archive_manifest_size_destination_and_count_are_exact (test_independent_review.IndependentReviewGateTests.test_archive_manifest_size_destination_and_count_are_exact) ... ok
test_changed_archive_and_manifest_bytes_are_rejected (test_independent_review.IndependentReviewGateTests.test_changed_archive_and_manifest_bytes_are_rejected) ... ok
test_complete_synthetic_parser_fixture_is_accepted (test_independent_review.IndependentReviewGateTests.test_complete_synthetic_parser_fixture_is_accepted) ... ok
test_different_frozen_toolchain_is_rejected (test_independent_review.IndependentReviewGateTests.test_different_frozen_toolchain_is_rejected) ... ok
test_different_installed_executable_is_rejected (test_independent_review.IndependentReviewGateTests.test_different_installed_executable_is_rejected) ... ok
test_duplicate_command_and_redefined_expected_exit_are_rejected (test_independent_review.IndependentReviewGateTests.test_duplicate_command_and_redefined_expected_exit_are_rejected) ... ok
test_each_external_window_and_capture_command_is_required (test_independent_review.IndependentReviewGateTests.test_each_external_window_and_capture_command_is_required) ... ok
test_empty_placeholder_summary_cannot_hide_raw_stub_diagnostics (test_independent_review.IndependentReviewGateTests.test_empty_placeholder_summary_cannot_hide_raw_stub_diagnostics) ... ok
test_escaped_source_path_and_alternate_checkout_mount_are_rejected (test_independent_review.IndependentReviewGateTests.test_escaped_source_path_and_alternate_checkout_mount_are_rejected) ... ok
test_exact_reviewer_script_mounts_do_not_look_like_retained_checkout (test_independent_review.IndependentReviewGateTests.test_exact_reviewer_script_mounts_do_not_look_like_retained_checkout) ... ok
test_forged_unhashed_raw_output_is_rejected (test_independent_review.IndependentReviewGateTests.test_forged_unhashed_raw_output_is_rejected) ... ok
test_independent_runtime_cannot_reuse_any_prior_nonce (test_independent_review.IndependentReviewGateTests.test_independent_runtime_cannot_reuse_any_prior_nonce) ... ok
test_malformed_raw_mountinfo_is_rejected (test_independent_review.IndependentReviewGateTests.test_malformed_raw_mountinfo_is_rejected) ... ok
test_missing_shutdown_or_retained_namespace_is_rejected (test_independent_review.IndependentReviewGateTests.test_missing_shutdown_or_retained_namespace_is_rejected) ... ok
test_modified_archived_driver_cannot_claim_current_driver_identity (test_independent_review.IndependentReviewGateTests.test_modified_archived_driver_cannot_claim_current_driver_identity) ... ok
test_no_required_runtime_command_can_be_omitted (test_independent_review.IndependentReviewGateTests.test_no_required_runtime_command_can_be_omitted) ... ok
test_placeholder_detection_must_be_enabled (test_independent_review.IndependentReviewGateTests.test_placeholder_detection_must_be_enabled) ... ok
test_rehashed_foundation_with_real_objects_but_no_transaction_interop_is_rejected (test_independent_review.IndependentReviewGateTests.test_rehashed_foundation_with_real_objects_but_no_transaction_interop_is_rejected) ... ok
test_rehashed_wrong_runtime_results_are_rejected (test_independent_review.IndependentReviewGateTests.test_rehashed_wrong_runtime_results_are_rejected) ... ok
test_retained_source_or_build_mount_is_rejected_in_all_locations (test_independent_review.IndependentReviewGateTests.test_retained_source_or_build_mount_is_rejected_in_all_locations) ... ok
test_review_must_use_exact_source_commit_and_drivers (test_independent_review.IndependentReviewGateTests.test_review_must_use_exact_source_commit_and_drivers) ... ok
test_source_and_build_absence_cannot_be_skipped (test_independent_review.IndependentReviewGateTests.test_source_and_build_absence_cannot_be_skipped) ... ok
test_successful_exit_without_required_operation_record_is_rejected (test_independent_review.IndependentReviewGateTests.test_successful_exit_without_required_operation_record_is_rejected) ... ok

----------------------------------------------------------------------
Ran 76 tests in 9.093s

OK
```
