# Independent ORIGINAL GitHub Actions ZIP review (review-only)

This is an independent evidence verifier, originally branched from
source `ef6ac628ae532f48a24d6aab374832e1adae8d90` on
`review/p004-original-zips-ef6ac`. **The verifier does not hardcode that SHA**:
its input must be the final implementation A tested by an exact-commit push,
with run IDs for that same SHA. New audits default to
`boop-bip80/LINUX-LOGIC-PRO` on `main`. Historical evidence can be replayed only
with the explicit pair `--repo boop-bip80/MAC-OS-EMULATION --branch master`.
Other repository/branch pairs are rejected, including either canonical
repository paired with the other's branch. The verifier does **not** import
the producer's P001, P002, P003 or P004 gate/checksum code. Its inclusion in the
consolidated branch grants no acceptance and does not requalify historical runs.

**No phase is certified by this verifier.** The first stage emits
`audit_status=PREDECESSOR_ORIGINAL_BYTES_VERIFIED` for ten authenticated
P001–P003 ZIPs. Only a subsequent docs-only B canonical-branch push P004 run can produce
the full seventeen-ZIP `audit_status=ORIGINAL_BYTES_VERIFIED`. Both stages
always retain `phase_verdict=NOT_EVALUATED`. The independent reviewer still must inspect outputs, authenticate
their own separate signoff and create exact-documentation publication B.

## Scope and expected ORIGINAL uploaded artifacts

For exact tested source A, use the `main` push run IDs, **never PR or workflow
dispatch runs**, for P001, P002 and P003:

| Phase | Original artifact names (suffix is full source A) |
| --- | --- |
| P001 | `p001-ubuntu-22.04-A`, `p001-ubuntu-24.04-A` |
| P002 | `p002-clone-a-A`, `p002-clone-b-A` |
| P003 | `p003-fixtures-A`, `p003-toolchain-A`, `p003-build-a-A`, `p003-build-b-A`, `p003-independent-runtime-A`, `p003-comparison-A` |

After independently accepted P001/P002/P003 reviews are published in strict
documentation-only commit B, run P004 on B's **main push**. Historical replay
instead requires `master` pushes in the historical repository. The auditor then
requires seven original P004 artifacts: five producer stages (`source`,
`toolchain`, `build-a`, `build-b`, `runtime`) named with A, the original resolver
named with B, and the final `p004-gate-A` report archive.

The independent review deliberately has two stages to prevent a circular
dependency: first authenticate ten P001–P003 original ZIPs, let a genuinely
independent reviewer accept and publish the three predecessor records in B,
then authenticate the seven P004 B-run ZIPs. Across both stages the full
review covers **17 distinct immutable GitHub-hosted ZIPs**:
10 predecessor ZIPs, 5 P004 stage ZIPs, 1 resolver ZIP, and 1 gate ZIP.
Every original GitHub artifact ID, SHA-256 digest, compressed byte length,
creation/expiry timestamp, and full member SHA-256/CRC32/byte map is recorded.
GitHub's 90-day artifact expiration is anchored to the authenticated **workflow
run creation time**, not the later time an individual ZIP finished uploading.
The reviewer checks `expires_at >= run.created_at + 90 days`,
`artifact.created_at >= run.created_at`, and `expires_at > artifact.created_at`.
Real historical P003 uploads completed as much as 37 minutes after the run
started, so requiring 90 full days from the per-artifact upload would
incorrectly reject legitimately retained original evidence.

The auditor verifies GitHub's exact repository, workflow path, `push` event,
selected canonical branch, SHA, run conclusion/attempt and every named mandatory job. It
retrieves archives from GitHub's artifact-ID API, hashes the *actual downloaded
ZIP bytes* against GitHub's own published digest and size, and reads every
original member without extraction. It rejects unsafe/traversing paths
(including directory entries), duplicate members, symbolic links, special
files, malformed CRC, decompression-budget overruns and partial archives.

Additional independent cross-checks cover both P001 host summaries and their
self-checksums, both P002 host summaries and their self-checksums, all six P003
roles and runtime/package/toolchain anchors, the five P004 producer receipts,
every member of original P004 gate `inventory.json`, and literal equality
between original resolver source-equivalence proof and the source-stage copy.
It independently queries GitHub's A...B comparison to reject code changes in
the final publication.

## Current manual invocation

Use independently confirmed run IDs for the same full source SHA in the
current repository. The default repository and branch are shown explicitly:

```bash
python3 -B -m unittest discover -s review/original_zips -p 'test_*.py' -v

python3 -B review/original_zips/verify_original_zips.py \
  --repo boop-bip80/LINUX-LOGIC-PRO --branch main \
  --predecessors-only \
  --source-sha <FULL-TESTED-A-SHA> \
  --p001-run <A-MAIN-PUSH-P001-RUN-ID> \
  --p002-run <A-MAIN-PUSH-P002-RUN-ID> \
  --p003-run <A-MAIN-PUSH-P003-RUN-ID> \
  --output predecessor-original-zip-review.json
```

For the full seventeen-ZIP review, omit `--predecessors-only` and add
`--publication-sha <FULL-DOCS-ONLY-B-SHA>` and
`--p004-run <B-MAIN-PUSH-P004-RUN-ID>`. The publication must preserve the exact
tested implementation and satisfy the existing documentation-only delta check.
These placeholders must be replaced with actual verified commits and runs;
branch consolidation alone does not supply fresh qualification evidence.

## Historical source A2 and archived invocation

The following records describe the former `MAC-OS-EMULATION/master` workflow.
Their statuses are archived observations, not the current phase dashboard or
current run status. Original URLs, commits and run IDs remain unchanged.
The historical implementation source A2 on `master` was
`44a6353528624c862a0cf7d95fa2411d28129cb1` (reviewed semantic-fault and ZIP/redirect hardening, PR #11).
The exact **master-push** qualification runs were recorded as follows:

| Phase | Historical A2 run | Archived GitHub status at the time |
| --- | --- | --- |
| P001 | [41708486168](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41708486168) | QUEUED; no verdict |
| P002 | [41708485572](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41708485572) | QUEUED; no verdict |
| P003 | [41708485536](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41708485536) | QUEUED; no verdict |
| P004 source candidate | [41708485625](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41708485625) | QUEUED; **not** the final B publication run |

The historic pre-hotfix source `ef6ac628ae532f48a24d6aab374832e1adae8d90`
used P001 `41702268341`, P002 `41702268298`, P003 `41702268352`,
and candidate P004 `41702268292`. **Never substitute those run IDs or
ZIPs for A2 evidence.** Replay still requires successful runs and their own originals.

To replay the historical A2 P001/P002/P003 review, use the explicit historical
pair below. The verifier checks current availability and completion before
reading the first **ten ZIPs**:

```bash
python3 -m unittest discover -s review/original_zips -p 'test_*.py' -v

python3 -B review/original_zips/verify_original_zips.py \
  --repo boop-bip80/MAC-OS-EMULATION \
  --branch master \
  --predecessors-only \
  --source-sha 44a6353528624c862a0cf7d95fa2411d28129cb1 \
  --p001-run 41708486168 \
  --p002-run 41708485572 \
  --p003-run 41708485536 \
  --output predecessor-original-zip-review.json
```

That output verifies original ZIP provenance only. It is not an independent
P001/P002/P003 acceptance verdict. A reviewer must inspect all raw reports,
their original source/tree/lock bindings, and independently attest their
judgment before **documentation-only B** can be published.

For a historical B exact-master P004 run that completed successfully, verify all
**17 ZIPs** and B's exact documentation-only delta:

```bash
python3 -B review/original_zips/verify_original_zips.py \
  --repo boop-bip80/MAC-OS-EMULATION \
  --branch master \
  --source-sha 44a6353528624c862a0cf7d95fa2411d28129cb1 \
  --publication-sha <FULL-DOCS-ONLY-B-SHA> \
  --p001-run 41708486168 \
  --p002-run 41708485572 \
  --p003-run 41708485536 \
  --p004-run <FINAL-B-MASTER-PUSH-P004-RUN-ID> \
  --output final-original-artifact-review.json
```

Set `GITHUB_TOKEN` through a read-only Actions environment or a preconfigured
scoped GitHub CLI token. Never paste real tokens into a command or repository.
The placeholders are illustrative, **not executable** until corresponding
original ZIPs and commits genuinely exist.

Original ZIP verification can take significant runner disk, bandwidth and CPU
for compiled package and toolchain archives. The verifier handles only one ZIP
at a time and retains only compact independent JSON evidence. The default
archive size limit is 12 GiB; the per-ZIP expanded-member budget is 60 GiB.
Independent reviewers may lower these limits but must document a justified
increase. Preserve every original ZIP digest and the review result for 90 days,
without copying proprietary binaries, credentials or licensed Logic Pro
content into any public artifact.

## Archived proposal for an isolated GitHub Actions workflow

The following proposal belonged to the historical review branch. That branch
has been consolidated into `main`; this section does not instruct creation of
a replacement branch or describe an active workflow. The original proposal was:

- `on.push.branches: [review/p004-original-zips-ef6ac]` and path restriction
  to the review files; **no** PR trigger, no master trigger, no reusable workflow
  accepting untrusted user-supplied run IDs.
- `permissions: {contents: read, actions: read}` and
  `persist-credentials: false`; no write permission, no user secrets.
- Check out this review branch at the exact reviewed commit, run the offline
  adversarial suite, then invoke the applicable predecessor-only or full-B
  verifier mode with **hard-coded, independently confirmed run IDs** and
  read-only `github.token`.
- Upload only the independent JSON report and test transcript with 90-day
  retention, `if: always()`; a failing/blocked report must fail the audit job.
- Do not merge this review branch, use its result as a phase status, or publish
  B from it. B must descend directly from source A with documentation-only
  changes, as separately proven by the production P004 gate.

At the time of this proposal, exact A2 master-push runs were queued and their
original ZIPs had not been published. This archived observation is not a
present-day availability claim. Neither the proposed workflow nor the example
commands establish passing tests or phase acceptance.

## Historical review limitations and gaps found in frozen source A

The observations and line references below apply to the historical frozen
source reviewed here; they are not a fresh audit of the consolidated branch.

- P004's production gate already authenticates five original P004 stage ZIPs
  in `tools/compat/logic-pro/check_gates.py:604-696`, but it does not inspect
  the resolver's original ZIP (`:692` skips it). It does not reject a malicious
  ZIP directory entry before skipping directories (`:627-629`), nor check ZIP
  symlink file types (`:632-643`).
- The original P001/P002 workflows upload only; P003 compare consumes
  extracted artifacts. The P004 predecessor gate at
  `tools/compat/logic-pro/check_gates.py:921-955` authenticates run/job
  conclusions and reviewed B blobs but **not** original P001/P002/P003 ZIP
  bytes. Their in-artifact checksums are useful consistency checks, not an
  independent hosted provenance oracle.
- The P004 gate checks original artifacts are unexpired but does not validate
  their `expires_at-created_at` against the 90-day retention requirement.
- The reviewer/author inequality check is a **string** comparison. The future
  accepting reviewer must provide a real independently attributable signoff,
  not a fictional different display name or a self-written PASS claim.

The source-level verifier above closes these archive-provenance gaps as
supporting evidence. It does **not** prove original Logic Pro execution or
replace final independent human/agent review of actual raw logs.
