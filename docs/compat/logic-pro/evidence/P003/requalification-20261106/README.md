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
