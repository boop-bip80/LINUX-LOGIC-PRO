# Independent exact-candidate CI review

Reviewer: `/root/ci_requalification_review`. The implementation author and this
reviewer are different agents. The reviewer changed no production file, branch,
pull request, or remote evidence object.

The reviewed candidate is `da1000be001711f80d6880eed9eeca916f6d0a23` on draft
[PR #1](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/1). The workflows
actually checked out synthetic merge `b628085a19bae2d467fd9549ec0767636423a90a`.
Both commits have tree `37761104d97e824a2567f91dff2dea391bb635dd`.
The default `master` branch remained `f7bd711013d3c41c3eee4ec76926bfe3a152cb46`.

## Evidence and result

`hosted-review.json` records 213 successful checks over all 68 raw members of four
complete workflow ZIPs. Each ZIP was compared with the official GitHub artifact
size and SHA-256 obtained independently through the GitHub API. Each internal
checksum, command transcript or byte segment, exact source SHA, original pin,
dependency tree, and relevant outcome was checked without importing production
verification functions.

- [P001 run 41256694734](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41256694734): both Ubuntu jobs passed 120 fixtures, all 63 static citations,
  complete 160-pin / 161-repository inventory, and both isolated historical
  recovery snapshots. The current tracked inventory has 293305 entries.
- [P002 run 41256694572](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41256694572): both Ubuntu jobs passed 96 fixtures, inspected 293145 physical
  blobs, preserved all 160 pins, and verified all 44 LFS payloads totaling
  16128448 bytes. The regenerated lock is byte-identical to the committed lock.
- Both P002 runs first returned 128 from the optional `locate-exact-commit`
  probe, then successfully fetched and checked out the exact PR merge SHA.
  All required commands exited zero. The optional miss is retained as evidence.
- All four P001 initial/final manifests are byte-identical: 97533706 bytes,
  SHA-256 `3bf22490c31d3dbc11bb8328ce8b9bc8bb87c229c8a07fe8b1cf69a30e713d0e`.

`static-review.json` records 15 successful workflow/source checks before
publication. `candidate-api.json` binds the published changed blobs and Git
trees to that review. `artifacts-api.json` contains the official artifact
metadata plus local materialization paths; `run-metadata.json` records the
completed workflow statuses. API `head_sha` identifies the PR head; the artifact
names and raw summaries identify the actual checked-out merge SHA.

## Reproduce

Obtain the four original ZIPs using the artifact IDs in `artifacts-api.json`.
Change only each `local_path` to its downloaded ZIP location. Preserve the
official metadata fields. Keep the review script, `candidate-api.json`, and
`static-review.json` together. Use a checkout containing the unchanged
`docs/compat/logic-pro/submodules.lock.json` whose SHA-256 is recorded in the
static review, then run:

```sh
python3 review_hosted_candidate.py \
  --repo /absolute/path/to/source \
  --artifacts artifacts-api.json \
  --output reproduced-review.json
```

The verifier reads ZIP members in place, hashes the large manifests in chunks,
and never executes archived code. A mismatch exits nonzero. The review timestamp
will differ on reproduction; test and source facts must agree.

## Verdict limits

This is independent approval of the stated candidate's source/integrity
qualification. It does not merge PR #1 or mark either phase fully accepted on
`master`. Default-branch update approval, the historical archive-publication
hold, and durable publication of the new large raw manifests remain separate
requirements. The reviewer made no attempt to publish, re-encode, or bypass the
held historical archive. Finite-lived GitHub artifacts alone are not durable
evidence publication. No Darling build, Logic execution, audio/graphics, or ARM
compatibility is demonstrated by these phases.
