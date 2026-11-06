# P003 current-source requalification — 2026-11-06

Status: ACTIVE, all original current-source G1–G4 gates pending. Starting
commit: `3be66e2b343b77c34d023c20bd7822dc055c657f`. The ordered P001/P002
acceptance at `d58cca51` remains the predecessor record.

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
