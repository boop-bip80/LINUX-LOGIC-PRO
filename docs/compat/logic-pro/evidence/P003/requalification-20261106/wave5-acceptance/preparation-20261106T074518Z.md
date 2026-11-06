# P003 Wave 5 independent acceptance — PENDING preparation checkpoint

**Status: PENDING. All current G1–G4 gates remain pending. P003 is ACTIVE / NOT PASSED; P004 remains NOT PASSED.**

- Reviewer: `/root/wave5_acceptance`, independent non-author final acceptance adjudicator.
- Checkpoint: 2026-11-06 07:45:18 UTC.
- Exact candidate: `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`.
- Candidate tree: `9db3623bd2c81d18b17b29c921b1d6212ca1339d`.
- Current campaign: GitHub Actions run `42180484781`.
- Scope of this checkpoint: preparation and source inspection, not acceptance of runtime or build results.

## Evidence boundary

The reviewer independently confirmed the local candidate commit and tree with `git rev-parse HEAD HEAD^{tree}`. The root reports successful acquisition and mandatory fixture jobs with both fresh full builds still active. Current original build/package/runtime archives have not been supplied to this reviewer. Reported hosted progress does not establish any gate below.

Preceding run `42177445982` at `b6f4d9bf04dd4a15a1b349845f962295ff350b7d`, and historical run `41292343355`, are diagnostic or method evidence only. Neither can qualify this corrected candidate. No original runtime data from either run was replayed by this reviewer during preparation. The current evidence must cover five real campaigns of ten cases each: both initial installs, both fresh reinstalls, and the independent archived-package installation.

## Preparation completed and concrete findings

Read `AGENTS.md`, the README global acceptance contract and full P003 section, this campaign's evidence account, the current producer and independent runtime reviewer, the comparator's source/runtime/package binding, and the focused abort-receipt tests. The distinct source review in `wave5-source.md` was also examined. No production, README, ledger, or peer-review files were changed; no tests were run by this reviewer for this checkpoint.

The earlier producer exception path could propagate a constructor `KeyboardInterrupt` while its `finally` block wrote a zero-case `PASSED` receipt. This is a receipt truthfulness defect even though the overall comparator requires the exact ten cases and rejects that receipt. The corrected producer catches `BaseException` to record the error, then uses a bare re-raise to preserve the original exception. Its focused test covers `KeyboardInterrupt`, `SystemExit(0)`, `SystemExit(42)`, and `GeneratorExit`, including identity, traceback, failed status, empty case/command evidence, and absent fabricated lifecycle/home/startup observations. The distinct Wave 5 source reviewer independently approved the exact committed repair. Fresh evidence from the corrected candidate is still required; prior runtime success cannot close this change.

The independent installed-package reviewer has its own FNV calculation, command execution, raw XWD parsing and RGB extraction, image production, GUI interaction, and process/namespace lifecycle checks, without importing the producer verifier. The automated comparator does use producer helper functions for several runtime checks. Accordingly, a comparator PASS or producer PASS label will not substitute for this reviewer's critical recomputation from original raw evidence. Its successful completion label is only `READY_FOR_INDEPENDENT_REVIEW`.

The inspected source-binding path checks the exact candidate, the current classification records and anchors, the complete 63-citation set, root/submodule relationships, and supported re-audit scopes. Preparation did not independently reproduce the complete current artifact source closure. The independently accepted P001/P002 prerequisite at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77` and unchanged locks/pins must be reconciled with the final originals and the current distinct source verdict before acceptance.

## Final decision checklist

| Gate | Current verdict | Required original evidence and independent checks |
| --- | --- | --- |
| G1 — reproducible complete build/install | PENDING | Two fresh complete builds and installs at the exact candidate; identical frozen inputs and toolchain; original archive/member integrity; clean source before/after; source/dependency/LFS/classification closure; every installed-byte difference enumerated and justified, including relevant Mach-O/debug/UUID details. |
| G2 — actual framework ownership and loading | PENDING | Actual owners, aliases, Mach-O IDs and dependencies, installed files, and live loaded paths for AppKit, Foundation, CoreGraphics, CoreText, ImageIO, QuartzCore, and AudioToolbox. Reconcile the package review against both fresh inventories and runtime observations. |
| G3 — real runtime behavior | PENDING | Five campaigns × ten exact cases, with actual Mach-O FNV and Foundation behavior, live XPC/vproc transaction sequence `+1,+2,+1,0`, typed negative results, an external XTest click and 16-character nonce followed by Return, and original before/after XWD pixels. Independently recompute critical raw values and image evidence. |
| G4 — clean lifecycle and archived-package replay | PENDING | Both uninstall/reinstall sequences with genuinely fresh state, unchanged reinstall inventories, and a separate source/build-free archived-package runtime. Verify shutdown, process identity, released mount namespaces, isolation, and the independent archive's binding to the reviewed install. |

For the final adjudication, obtain the exact current original archive paths and provenance, the completed Wave 4 original-evidence reviews, and the other Wave 5 source/package verdicts. Preserve the original bytes and operate on separate review outputs. Independently recompute critical FNV/transaction/event/pixel/lifecycle results rather than relying on reported PASS labels. Challenge at least one behavioral corruption whose file hashes have been recomputed, so rejection demonstrates semantic validation beyond checksum integrity. Record reproduction commands, results, reviewer identity, UTC date, exact implementation SHA, and remaining limits.

Acceptance also requires agreement among README, phase state, evidence, failure account, and review conclusions; the exact prerequisite and source bindings; and closure of the abort-receipt defect on the new candidate. Missing evidence or an unresolved gate prevents P003 acceptance. This reviewer is not authorizing P004.

## Limits to preserve in the final decision

- Historically unarchived intermediate source-built linker binaries prevent a whole-build byte-identity claim. Scope any comparison to the actual retained evidence.
- The full frozen toolchain ZIP exceeds the local retrieval limit. Exact hosted restoration verification, original metadata/raw receipt, and A/B observations may be reviewed, but do not claim local inspection of the entire ZIP or image.
- Snapshot acquisitions failed with HTTP 500/502/503. The reviewed recovery permits only strict exact-original input-archive reuse. No build, installed-package, or runtime-output reuse can count as a fresh campaign. Preserve the distinct build review of that repair.
- The bounded runtime/source repairs and their independent reviews must stay within the clean-room contract; no application-specific bypass or restricted Apple input can establish acceptance.

**Next action:** resume only after the fresh `4622a9396c5c9fbe0014bdf6a2f695dcc491233c` original evidence and peer reviews are available. This is a pending preparation checkpoint, not a formal G1–G4 acceptance verdict.
