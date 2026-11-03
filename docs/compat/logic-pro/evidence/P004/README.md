# P004 evidence policy and handover

**Status: NOT STARTED / no P004 acceptance recorded.** This document specifies evidence controls; writing it, creating a CI workflow, or obtaining a green harness test does **not** pass P004. The project's README and four original P004 checkboxes remain authoritative. Actual Logic Pro execution is not established.

## Accepted predecessor is source-specific

P003's independent G1–G4 verdict is bound to source commit \`89c6c9d85aba6ed1662035e6366298c92ef9c970\`, tree \`1ce359808d725efd07ec2b51548760893a7cf5a5\` and original Action run \`41292343355\`. The later upstream merge \`5e08de551ae51ea8415bfad875ea95f0e44cda51\` modified root \`CMakeLists.txt\`. Old P003 reports must **not** be rebadged as current-HEAD evidence. Requalify ordered P001, P002 and P003 gates on the exact proposed P004 implementation source, or keep the current phase blocked/reopen the earliest affected phase.

## Public P004 artifact contract

Run the full, real P003-derivative source/build/install/runtime campaign on its actual GitHub Actions SHA. The P004 artifact inventory requires *all* five independently uploaded, unmerged stage directories:

| Role | Directory suffix | Primary anchors |
| --- | --- | --- |
| \`source\` | \`p004-source-\${SHA}\` | \`p004-job.json\`, \`source-summary.json\`, \`baseline.log\`, \`submodules.log\`, \`build.log\`, \`harness.log\`, \`fault-matrix.json\` |
| \`toolchain\` | \`p004-toolchain-\${SHA}\` | \`p004-job.json\`, \`toolchain.lock.json\`, \`toolchain-image.tar.gz\` |
| \`build-a\` | \`p004-build-a-\${SHA}\` | \`p004-job.json\`, \`build-summary.json\`, \`install-first.json\`, \`install-second.json\`, \`runtime-prefix.tar.gz\`, \`runtime-prefix.sha256\`, and first/second installed probe reports |
| \`build-b\` | \`p004-build-b-\${SHA}\` | Same anchors, separately built and verified |
| \`independent-runtime\` | \`p004-runtime-\${SHA}\` | \`p004-job.json\`, \`package-review.json\`, \`runtime/report.json\`, \`runtime-summary.json\` |

Every \`p004-job.json\` must record the exact full source commit, GitHub run ID/attempt, root source tree, role/name, phase, real exit status, timeout outcome, discovered/executed counts, and observed assertions. It is an observation, **not an independent reviewer verdict**. A skipped producer, omitted role, partial tar, mismatched source, missing assertion, empty suite, timeout, or intentionally injected failure is not a PASS.

Use the standard-library-only helper:

\`\`\`sh
python3 -B tools/compat/logic-pro/p004_evidence.py \
  --artifacts "$RUNNER_TEMP/p004-artifacts" \
  --commit "$GITHUB_SHA" --run-id "$GITHUB_RUN_ID" \
  --run-attempt "$GITHUB_RUN_ATTEMPT" \
  --output "$RUNNER_TEMP/p004-artifacts/inventory.json"
\`\`\`

The output is **only** \`darling.p004.evidence-inventory.v1\`, \`status=EVIDENCE_INVENTORY_VERIFIED\`, \`phase_verdict=NOT_EVALUATED\`, and a SHA-256/byte inventory of every original extracted file. It enforces canonical relative paths, no symlinks or hardlinks, no empty required anchors, exact source/run identity, original toolchain image and runtime-prefix hashes, and all ten independent installed-runtime cases. It does not grant PASS authority.

The separate \`check_gates.py\` validator must rehash this inventory, verify every mandatory stage, real behavioral reports, phase ordering, failure-injection matrix, and missing-runner/fixture failure behavior. Missing \`manifest.json\`, \`inventory.json\`, predecessor records, reports, or original artifact provenance blocks acceptance.

## Original hosted artifacts and independent review

Unpacked files and GitHub Actions environment variables **do not authenticate their own provenance**. Before final acceptance, a reviewer who did not author the implementation must independently retrieve the *original* GitHub Actions artifacts for the exact tested SHA and run. Record each GitHub artifact ID, original ZIP byte length, SHA-256 and CRC/member inventory, job conclusion, workflow/attempt, artifact retention timestamp, and immutable source/tree/submodule/toolchain identity. Download, validate and compare raw bytes against the inventory; do not accept producer-written hashes alone. Preserve the independent reviewer/date/reproduction details and a final explicit verdict on every P004 checkbox. If archives are expired or cannot be downloaded, acceptance remains BLOCKED until rerun.

GitHub Actions uploads should set \`retention-days: 90\` and \`if-no-files-found: error\`. A changed source SHA, submodule pin, toolchain or assertion invalidates dependent acceptance until retested. Non-byte-identical outputs must be exhaustively enumerated and independently classified; do not silently normalize them.

## Privacy and licensing

Public CI uses generated and redistributable synthetic fixtures only. No Logic Pro \`.app\`, purchased audio library, proprietary plug-in, commercial activation material, account token, keychain or customer data may enter public artifacts or Git history. Use separately authorized infrastructure for licensed Logic and native reference-Mac work, linking its results by stable nonsecret evidence IDs and hashes. If required private infrastructure is unavailable, the corresponding gate reports **BLOCKED**; it cannot inherit success from synthetic CI.

The P004 compatibility gate proves that the test system tells the truth; it is **not** a Logic Pro functionality certification. After independent P004 acceptance, P005 begins identifying actual eligible Intel Logic binaries and native-reference evidence.

## Evidence index (pending)

| Required item | State |
| --- | --- |
| Exact candidate implementation SHA/tree and 160 recursive pins | Not yet recorded |
| Fresh P001→P002→P003 accepted regression on candidate | Not yet recorded |
| P004 hosted run/job IDs and all original ZIP hashes | Not yet recorded |
| Mandatory fault matrix, no false-positive or skipped result | Not yet recorded |
| Independent reviewer and dated verdict for four P004 gates | Not yet recorded |
| Final P004 status | **NOT PASSED** |

**Handover:** do not mark P004 PASSED or begin P005 until the original roadmap's four pass gates and the global independent-review contract have reproducible, exact-source evidence. An unsuccessful run belongs in the attempt history with its authentic failure state, not in a synthetic success bundle.
