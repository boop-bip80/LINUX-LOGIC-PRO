# P003 current-source requalification — 2026-11-06

Status: **PASSED — all original G1–G4 gates accepted 2026-11-06 08:33:06 UTC** by
independent non-author `/root/wave5_acceptance`. Exact tested implementation:
`4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, tree `9db3623bd2c81d18b17b29c921b1d6212ca1339d`,
[run 42180484781](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42180484781).
[Formal decision](wave5-acceptance/acceptance.json), SHA-256 `c145f4059e97f6939abb4a57968320017c48dc54778c5a6eda2ab0c16167f101`;
[final report](wave5-acceptance.md). **All five waves are complete; P004 is next and NOT PASSED.**

The ordered P001/P002 acceptance at `d58cca51` remains valid with independently
verified source/pin continuity. The campaign started at
`3be66e2b343b77c34d023c20bd7822dc055c657f`. Earlier ACTIVE/PENDING statements below
are preserved dated checkpoints, not the current verdict.

## Current accepted result

| Gate | Independent final result |
| --- | --- |
| G1 | Two fresh 16,594-step builds; identical frozen inputs; 11,947 entries per install; all 137 differing installed files / 4,418 changed bytes classified, zero unexplained. |
| G2 | Seven real framework owners/aliases/IDs and 70 direct edges per host; 21 native wrapper names and original host provenance; all five live path sets. |
| G3 | Five campaigns / 50 actual cases; computation, Foundation objects and live transactions, external click/nonce/Return and original displayed pixels. |
| G4 | Both complete removals and matching fresh reinstalls; separate third-runner execution from the exact installed archive without source/build mounts. |

[Complete original artifact identities](attempt-4622a93/completed-run.json),
[137-path byte-difference table](wave4-package/final-4622a939/installed-differences.csv),
[final package challenge](wave5-package/final-normalization-challenge.json),
[final raw-runtime audit](wave5-acceptance/original-runtime-audit.json),
[final transaction challenge](wave5-acceptance/rehashed-transaction-challenge.json),
and [completed wave ledger](wave-ledger.json) retain the full record.
Hosted fixtures are **174/115/201**, zero skips. All six workflow jobs succeed.

Installed packages are not byte-identical, and whole-build byte identity remains
unproved because intermediate linker bytes are unarchived. Complete image-byte
verification ran on the hosted runner; external host-library bytes remain bound
host observations and framework review covers direct edges. Raw validation-layer
and host-UUID diagnostics remain visible and do not establish those additional
operations. The [formal scope and material limits](wave5-acceptance/acceptance.json)
exclude broader framework/audio and Logic Pro compatibility.

The previously published [technical-closure progress index](independent-closure.json)
remains unchanged at its original review-time hash; its pending status is historical
and is superseded by the final decision above.

## Initial observations

- Original [P003 run 42163489140](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42163489140) failed the 151-test build suite: 20 failing subtests and one error, all caused by unsupported current-source re-audit aggregation. Both full builds were skipped.
- The original fixture artifact is `13478520059`, 11,253 bytes, SHA-256 `2f2cdf2c84fa7b1155043e8e636e979239a30f9cd4dd8bc104a41981e0a83df6`.
- Local source-classification regression reproduces the same failure across 14 discovered tests.
- Local original P001 and P002 suites pass 174 and 115 tests respectively, with no skipped tests. Their complete transcripts are retained beside this note.

## Contract

Two clean builds with identical frozen inputs; complete framework owner and
live-resolution validation; asserted real Mach-O, Foundation, visible GUI and
XPC behaviors; complete uninstall/reinstall plus an independent installed-archive
execution. All output differences must be enumerated. Independent reviewers
must inspect original evidence and record a dated exact-source verdict.
Historical results cannot replace these current-source gates.

## Five-wave ownership

[Machine-readable ledger](wave-ledger.json) records each actual assignment and
its evidence. Wave 1 audits requirements, builds and runtime; Wave 2 implements
observed repairs; Wave 3 challenges the integrated candidate; Wave 4 reviews
hosted evidence and closes defects; Wave 5 independently decides acceptance.
No reviewer accepts implementation they authored.

## Provenance

The investigation uses this repository, its public GitHub Actions logs and its
existing independently accepted source manifests. No proprietary Apple binaries
or restricted source were used. No production behavior changed in the initial
documentation checkpoint.

## First implementation checkpoint

The scoped source-re-audit aggregation repair preserves exact upstream/prior-blob
identities and all historical citation checks. Four new adversarial cases reject
forged/omitted identities, unreviewed paths and changed assertion/count data.
All 18 focused source tests and the complete 155-case P003 suite pass locally
with Clang 19/GCC 14. The exact frozen Clang 14 build/runtime campaign remains
mandatory. Hosted floor: 174/115/155. No runtime acceptance is inferred.

The original failing hosted fixture archive is preserved byte-for-byte as
`initial-hosted-fixtures.zip`; its SHA-256 and original run are listed above.
Raw local before/after outputs: `initial-build.log`, `source-repair-focused.log`
and `source-repair-build.log`. The printed toolchain failure at the end of the
passing suite is the expected negative test for changed compiler bytes.

## Wave 1 completed; Wave 2 active

Three non-author reviews are retained in [contract](wave1-contract.md),
[build/install](wave1-build.md), and [runtime](wave1-runtime.md). The first
repair at `8a222c7d5` passed all 174/115/155 hosted fixtures in run `42165628353`.
Both full build jobs started after the frozen-toolchain job succeeded.

A replay of the actual already-published P001 producer report reveals a second
schema gap: complete per-citation `current_source` and the top-level
`current_source_anchor` are absent from the aggregate's expected records.
The unchanged original report SHA-256 is
`15b1d5e657e09215e4f070bad580d9ed9b4ac78a55d348026cb6c850163180b7`.
Wave 2 repairs this consumer and adds a real-report regression. Separate agents
address the verified missing post-build source-cleanliness rejection and the
reproduced early runtime initialization failure-reporting defect. The latter
already fails closed; the repair improves retained evidence without permitting
reused runtime state. All four original P003 gates remain pending.

## Wave 2 complete; integrated candidate

The three bounded repairs and current-objc4 adapter now pass the combined local
**174 P001 / 115 P002 / 187 P003** suites, with no skips. [Exact inputs, code hashes
and transcript hashes](wave2-integration.json) bind this integration. Raw logs are
`wave2-baseline.log`, `wave2-submodules.log` and `wave2-build.log`; the preceding
172-case snapshot is explicitly retained as `wave2-build-172-intermediate.log`.
The printed negative toolchain-drift diagnostic is expected by a passing test.

[Source repair](wave2-source.md), [cleanliness repair](wave2-build.md) and
[runtime failure repair](wave2-runtime.md) describe the changes and focused
reproductions. The source adapter accepts both unchanged fresh hosted reports and
both preserved P001 reports, while preserving all 18 original focused tests and
adding eight adversarial cases. The cleanliness tests execute the actual producer
EXIT handler against real temporary Git repositories. Runtime tests preserve
existing state and the original traceback of unexpected constructor failures.

The current classification producer/manifest, source lock, all dependency pins and
toolchain lock remain unchanged. Three non-author Wave 3 reviewers are active.
Fresh complete hosted qualification and independent G1–G4 review are pending;
this local integration is not runtime acceptance.

## Exact hosted preflight at af3566e

The [original candidate artifact and receipt](attempt-af3566e/README.md) preserve
all **174/115/187** hosted fixture passes, zero skips, from run `42169925661`.
The subsequent full run fails artifact publication; this is not current G1–G4 acceptance.

## Wave 3 code review checkpoint

The [source/build reviewer](wave3-source.md) and [runtime reviewer](wave3-runtime.md)
approve their bounded `af3566ee` scopes after independent critical reproduction.
Their reports explicitly leave current G1–G4 acceptance pending. The package
reviewer is still preparing and checking the complete byte comparison method.
The [successful frozen-toolchain acquisition](attempt-af3566e/toolchain-acquisition.json)
retains its original decoded job log and official image artifact identity.
Both full build containers remain in progress at this checkpoint.

## Wave 3 complete; Wave 4 active

The [package method report](wave3-package.md) completes Wave 3 alongside the
source and runtime code reviews. Its complete historical original-archive QA
reproduces all 138 path/hash pairs and 6,447 changed bytes, with zero unexplained
installed bytes. The separate UUID reviewer and byte/source-binding mutations
challenge the method. These historical results establish method behavior only.

Wave 4 assigns new non-author reviewers to current build inputs/outputs,
package/framework provenance and all five runtime campaigns. Current run
`42169925661` fails artifact publication after successful producer build/runtime summaries.
The scoped permission repair and fresh full rerun are now required.
The ledger records all actual assignments, including the supporting UUID review.

## Wave 4 observed upload failure and repair

Both full jobs reached 16,594/16,594 compilation actions and both producer runtime
PASS summaries, then failed with `EACCES` reading root-owned 0600 final source status.
No A/B archive was finalized; independent replay and aggregate comparison were
skipped. [Lossless original runner logs and receipt](attempt-af3566e/failed-publication.json)
retain the unsuccessful outcome.

The root-owned repair sets 0644 only on the exclusively created status descriptor,
including under umask 077, and preserves dirty-source and earlier-failure semantics.
The new actual-handler test covers eight combinations and raises the hosted P003
floor to 188. Three non-author Wave 4 reviewers require a fresh complete campaign;
all current G1–G4 verdicts remain pending.

The [local repair record](wave4-permission-repair.json) binds all changed code and
the complete passing 188-test transcript, with zero skips. Its printed toolchain
drift failure is the expected assertion in the negative test.

## Candidate cc268442 hosted preflight and acquisition outage

The [current original receipt](attempt-cc26844/README.md) preserves hosted
174/115/188 passes, zero skips, and two failed Ubuntu snapshot acquisitions.
Root requests another identical acquisition in run 42175768705; source and frozen
inputs remain unchanged. This external 500/502 failure occurs before current
builds and cannot establish any G1–G4 gate.

## Wave 4 exact frozen-input recovery

After the third snapshot-service 503 failure, the [bounded recovery record](wave4-retained-recovery.json)
binds unchanged recipe/source/toolchain locks, the original successful toolchain
artifact, the new restoration code and 200 passing local cases. The restore path
checks exact outer ZIP identity, all original members/CRCs, same environment,
sealed image and original checksums; corrupt inputs fail. Only transport
unavailability permits the unchanged fresh recipe. Two new source checkouts,
builds and all five runtime campaigns remain mandatory. No current gate is passed.

## Actual b6f4d9bf recovery and independent checkpoints

[Original hosted evidence](attempt-b6f4d9b/README.md) records 174/115/200 fixtures
and successful exact retained-input restoration. The [non-author build reviewer](wave4-build.md)
approves the permission/recovery mechanisms after independent critical cases and
raw provenance inspection. The [non-author package reviewer](wave4-package.md)
approves the bounded method and explicitly identifies the additional manifest,
metadata, source-built-linker and framework checks required for a fresh verdict.
Both current full builds remain active; original G1–G4 acceptance is pending.

## Runtime method preparation and final-wave assignments

The [runtime checkpoint](wave4-runtime.md) records independent source binding and
a separate raw-stream/XWD/PNG decoder, rehearsed only on identified historical
evidence. All five fresh campaigns remain pending. Three final-wave reviewers
prepare source, package and runtime/whole-phase audits during the long full builds;
the [ledger](wave-ledger.json) records all assignments. Final decisions await
complete current originals and Wave 4 fresh reviews.

## Final source review finding and abort-receipt repair

[The independent observation and root repair record](wave5-abort-repair.json)
preserve the reproduced KeyboardInterrupt receipt defect and 201 passing local
cases after correction. Original interruption semantics remain intact; the
receipt now records failure. This is not an overall false gate-pass finding.
A new full exact-source campaign and independent closure review are mandatory;
ongoing b6f4d9bf originals cannot accept the corrected source.

## Corrected-source preflight and final-wave checkpoints

[The exact 4622a939 preflight](attempt-4622a93/README.md) preserves the original
174/115/201 hosted tests, zero skips, and verified frozen-input acquisition. Both
fresh source builds are running in `42180484781`. [Wave 5 source review](wave5-source.md)
independently approves the committed abort repair, while [package preparation](wave5-package.md)
records the still-required original-byte/metadata/framework checks. The prior b6
run completed all six automated jobs; [its completion receipt](attempt-b6f4d9b/superseded-completion.json)
retains those results explicitly as superseded method/diagnostic evidence.
All current G1–G4 gates and final independent acceptance remain pending.

## Complete runtime-audit method rehearsal on superseded originals

[The Wave 4 runtime reviewer](wave4-runtime.md) independently verifies all five
b6 original campaigns and 50 cases with the unchanged separate auditor. The
[method summary](wave4-runtime/b6-method/summary.json) binds all 967 ZIP members,
79 command records, 158 streams, actual XWD/PNG pixels, complete reinstall/probe
bindings and eight rehashed corrupted copies rejected by both independent and
production checks. All original files remain unchanged. These are superseded
b6 method results; final462 G3/G4 and whole-phase acceptance remain pending.

## Final build A complete; original-evidence reviews active

[The corrected original A archive](attempt-4622a93/original-progress.json) contains
459 CRC-verified members from a complete successful build/install/runtime/reinstall
job. Build B remains active. Both [Wave 4 build](wave4-build.md) and
[Wave 5 source](wave5-source.md) independently verify the corrected 174/115/201
preflight and unchanged frozen/source inputs. Fresh paired outputs, source-free
replay and final independent G1–G4 acceptance remain pending.

## Complete corrected-source workflow; final independent closure

[All six jobs succeed at exact462](attempt-4622a93/completed-run.json). Both original
build ZIPs, the independent installed-runtime ZIP and the aggregate comparison
are downloaded and hash/CRC-checked. Automated status is READY_FOR_INDEPENDENT_REVIEW,
with five campaigns and 50 asserted cases. Original A/B outputs are not byte-identical.
The [superseded package rehearsal](wave4-package.md) is complete, but every final
acceptance check uses the new462 originals. Final non-author original-evidence
reviews and dated G1–G4 acceptance remain pending.

## Final source/build/runtime approvals published

[The independent closure index](independent-closure.json) binds completed
non-author exact-source reviews: Wave 4 full build/source/toolchain/per-host
lifecycle, Wave 4 G3/G4 real runtime and separate replay, and Wave 5 source and
ordered predecessor continuity. Full original byte/stream/image evidence and
bounded rehashed corruptions support these verdicts. Package/framework/native
G1/G2 and the final Wave 5 whole-phase decision remain pending; P003 stays ACTIVE.

## Final package/native reviews complete; Wave 4 closed

[Wave 4 package verdict](wave4-package/final-4622a939/final-verdict.json) and
[Wave 5 package verdict](wave5-package/final-review-receipt.json) independently
approve their exact-source scopes. Both classify 137 files / 4,418 changed bytes /
zero unknown bytes; all seven frameworks, 21 actual native wrapper names and
raw host provenance close. The [complete 137-path difference table](wave4-package/final-4622a939/installed-differences.csv)
and rehashed corruption evidence are retained. Wave 4 is complete, and the
[closure index](independent-closure.json) now contains all five technical approvals.
Only the final independent whole-phase adjudication remains pending.
