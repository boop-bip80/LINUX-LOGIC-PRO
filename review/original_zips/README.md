# Independent ORIGINAL GitHub Actions ZIP review (review-only)

This is a deliberately separate evidence verifier, originally branched from
source `ef6ac628ae532f48a24d6aab374832e1adae8d90` on
`review/p004-original-zips-ef6ac`. **The verifier does not hardcode that SHA**:
its input must be the final exact master-tested implementation A (including
any later reviewed A2 patch), with new run IDs for the same exact SHA. It does **not** import the producer's P001,
P002, P003 or P004 gate/checksum code and must **not** be merged into or used to
modify frozen tested source A while its formal master-push qualification runs
are pending.

**No phase is certified by this verifier.** The first stage emits
`audit_status=PREDECESSOR_ORIGINAL_BYTES_VERIFIED` for ten authenticated
P001–P003 ZIPs. Only a subsequent docs-only B master-push P004 run can produce
the full seventeen-ZIP `audit_status=ORIGINAL_BYTES_VERIFIED`. Both stages
always retain `phase_verdict=NOT_EVALUATED`. The independent reviewer still must inspect outputs, authenticate
their own separate signoff and create exact-documentation publication B.

## Scope and expected ORIGINAL uploaded artifacts

For exact tested source A, use the master-push run IDs, **never PR or workflow
dispatch runs**, for P001, P002 and P003:

| Phase | Original artifact names (suffix is full source A) |
| --- | --- |
| P001 | `p001-ubuntu-22.04-A`, `p001-ubuntu-24.04-A` |
| P002 | `p002-clone-a-A`, `p002-clone-b-A` |
| P003 | `p003-fixtures-A`, `p003-toolchain-A`, `p003-build-a-A`, `p003-build-b-A`, `p003-independent-runtime-A`, `p003-comparison-A` |

After independently accepted P001/P002/P003 reviews are published in strict
documentation-only commit B, run P004 on B's **master push**. The auditor then
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

The auditor verifies GitHub's exact repository, workflow path, `push` event,
master branch, SHA, run conclusion/attempt and every named mandatory job. It
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

## Source A2 and two-stage manual invocation

The historic pre-hotfix tested commit was
`ef6ac628ae532f48a24d6aab374832e1adae8d90` with formal master-push
candidate runs P001 `41702268341`, P002 `41702268298`, P003
`41702268352` and P004 `41702268292`. These IDs are **not reusable** if
a subsequent accepted gate fix creates a new tested source A2. Do not
launder stale originals by pointing an A2 report at ef6ac runs.

Once the **new exact-master A2** P001/P002/P003 runs are completed and have
real original artifacts, independently review the first **ten ZIPs**:

```bash
python3 -m unittest discover -s review/original_zips -p 'test_*.py' -v

python3 -B review/original_zips/verify_original_zips.py \
  --repo boop-bip80/MAC-OS-EMULATION \
  --predecessors-only \
  --source-sha <FINAL-EXACT-MASTER-A2-SHA> \
  --p001-run <A2-P001-MASTER-PUSH-RUN> \
  --p002-run <A2-P002-MASTER-PUSH-RUN> \
  --p003-run <A2-P003-MASTER-PUSH-RUN> \
  --output predecessor-original-zip-review.json
```

That output verifies original ZIP provenance only. It is not an independent
P001/P002/P003 acceptance verdict. A reviewer must inspect all raw reports,
their original source/tree/lock bindings, and independently attest their
judgment before **documentation-only B** can be published.

After B's new exact-master P004 run completes successfully, verify all
**17 ZIPs** and B's exact documentation-only delta:

```bash
python3 -B review/original_zips/verify_original_zips.py \
  --repo boop-bip80/MAC-OS-EMULATION \
  --source-sha <FINAL-EXACT-MASTER-A2-SHA> \
  --publication-sha <FULL-DOCS-ONLY-B-SHA> \
  --p001-run <A2-P001-MASTER-PUSH-RUN> \
  --p002-run <A2-P002-MASTER-PUSH-RUN> \
  --p003-run <A2-P003-MASTER-PUSH-RUN> \
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

## Future isolated GitHub Actions workflow, not committed yet

When originals are available, add a **separate**, narrowly scoped workflow
only to this isolated review branch:

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

The review workflow is deliberately **not created now**: new A2 qualification
must replace the historic ef6ac runs, and original A2 ZIPs must exist first.
Only after that, add the branch-only workflow for the predecessor stage; after
independent B publication, update the same review branch's locked B/P004
arguments for the final stage. Adding the workflow would needlessly occupy
an already-congested runner and create a misleading failed review attempt.

## Review limitations and gaps found in frozen source A

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
