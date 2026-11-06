# Wave 2: complete current source provenance

Date: 2026-11-06
Author: `/root/wave2_source`

## Finding and repair

The accepted P001 producer emits `current_source_anchor` and a separate
`checked[i].current_source` for all 63 citations. P003's aggregate expected only
the original citation and historical `current_reaudit` summary, so it rejected
the unchanged hosted report at `architecture-targets`.

The aggregate now requires the manifest's complete current re-audit and exact
reviewed anchor `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`. It reuses the producer's
anchor/ID structure validator without resolving Git objects, then independently
constructs the expected current report fields. Root citations bind the requested
build commit; nested citations retain their reviewed commits and gitlink chains.
Canonical JSON comparison binds every blob, excerpt, line range, assertion
count, preservation flag, and field type. The original assertions, reviewed URL
assertions, original citations, and strict historical P004 checks remain required.

No producer, manifest, accepted report, pin, or lock changed. This is a consumer
schema repair; it does not qualify a complete build or accept P004.

## Regression results

Command:

```sh
PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH python -m unittest discover -s tests/compat/logic-pro/build -p test_source_classifications.py -v
```

Result: **26 tests passed, zero skips**, including all 18 existing tests and eight
new tests. The new tests consume the actual committed P001 reports from both
Ubuntu 22.04 and 24.04 runners, verify their unchanged SHA-256, and reject missing
provenance for each of the 63 citations, changed anchors/pins/fields, omitted or
extra fields, incorrect JSON types, incomplete manifest IDs, and replacement
assertions with unchanged counts. Both original reports have SHA-256
`15b1d5e657e09215e4f070bad580d9ed9b4ac78a55d348026cb6c850163180b7`.

Both fresh `source-classifications.json` reports and their original logs from
hosted run `42165628353`, build-a and build-b, were also passed directly to
`validate_source_classifications`. Each passed with **63 citations / 41 sources**,
current commit `8a222c7d5e11fbd2c3ece79c53d60c1be545d0a0`, and the reviewed anchor.
Their identical report SHA-256 is
`6cf6a34398634cf5a51f5c2d15a364197941ac306687278daa473920949c52b5`;
the raw log SHA-256 is
`6087fa4239b4df9685950b7cb9ce32c7821986dd51d8556349dd4cc216f9cfd8`.

`git diff --check` passed. The coordinating agent runs the full build test suite
and fresh hosted campaigns after combining the Wave 2 changes.

## Provenance

This change uses only the repository's existing classification verifier,
manifest, and captured hosted reports. No restricted source or external code was
used. The frozen reports remain the original producer artifacts; synthetic
mutations are confined to parser regression tests.
