# Reproduce the P001 source-baseline milestone

P001 verifies the recoverability and description of the source. It does not build
Darling, initialize its dependencies, run Logic, or claim that any later phase
has passed. Every uninitialized child is recorded as unavailable for inspection;
its remote availability and any nested dependencies remain unknown until P002.

## Clean source and one-command campaign

Use an x86_64 Linux host with Git and Python 3.10 or newer. The workflow exercises
Ubuntu 22.04 and 24.04. Do not initialize the submodules for this P001 procedure.
Use the tested implementation commit recorded in the evidence summary and review.

```sh
git clone --no-recurse-submodules https://github.com/boop-bip80/MAC-OS-EMULATION.git
cd MAC-OS-EMULATION
git checkout --detach <tested-implementation-commit>
PYTHONDONTWRITEBYTECODE=1 python3 tools/compat/logic-pro/run_baseline.py \
  --repo . --output-dir ../p001-evidence
```

The output directory must be absent or empty and outside the checkout. Reusing an
old report directory is rejected. The workflow also exports compressed small JSON
reports to its log so the connected GitHub tool can retrieve evidence when the
interactive environment has no Git network transport. The export retains exact
SHA-256 digests; it does not change the evidence files.

Expected result is exit zero with `summary.json` reporting `PASS`, nonzero
executed fixture tests, all 149 recorded parent gitlinks matched, two verified
isolated source recoveries, and all source citations verified. This is a P001
candidate result. A separate review is required before the README phase can pass.

## What is actually checked

`inventory.py` reads the committed Git tree and `.gitmodules`, inventories tracked
paths, modes, object IDs and license-like files, and distinguishes exact child
checkouts from missing or mismatched ones. It records dirty state and staged index
changes separately from historical committed objects. It resolves relative URLs
against the actual fork remote without fetching or repairing them. Available
children are inspected recursively; missing children have explicit unknown
recursive scope.

`recover_baseline.py` creates two new clones with independent object stores from
the fetched parent repository. One restores the original audited source and prior
README; the other restores the initial roadmap integration. It verifies every
ordinary tracked file, executable bit, and symlink target against its Git blob
ID, checks exact commit/tree IDs and README SHA-256 hashes, and proves clean
checkouts. Gitlinks remain explicit uninitialized entries. Local recovery is not
proof that the current fork-relative dependency URLs are obtainable.

`verify_classifications.py` verifies immutable source blobs, inclusive line
ranges, exact excerpt hashes and required text. The current implementation must
still contain those audited source blobs. A source change requires re-auditing
the affected classification instead of keeping a stale success result.

`run_baseline.py` runs the fixture tests and all three tools, retains command logs,
compares the dependency pins and restored trees with the independently retrieved
GitHub snapshot, and checks that the source checkout remains clean. Missing
reports, empty/skipped tests, bad hashes, mismatched pins and failed commands
prevent success. This small phase-local campaign is not P004 runtime CI.

## Complete tracked-file manifest

The full 8,797,722-byte tracked-file JSON is committed in `tracked-files.json.gz`.
It is the exact output emitted by both hosted jobs and a separate clean clone.
Its uncompressed SHA-256 is
`ac07d77474ed75518643e4efe4d007c9550b80a39a58a8c13cb25a56905c1ca2`.
Both inventories reference the original filename `tracked-files.json`; preserve
those emitted reports and expand the shared archive when inspecting that file:

```sh
gzip -dc docs/compat/logic-pro/evidence/P001/tracked-files.json.gz > /tmp/p001-tracked-files.json
sha256sum /tmp/p001-tracked-files.json
```

The archive avoids duplicating almost nine megabytes of JSON for every host.
The raw command logs, per-host reports and reviewer records are committed here,
so the accepted milestone does not depend on GitHub artifact retention. The ZIP
artifact hashes and all retained file hashes are listed in `evidence-index.json`.

## Independent review and retained evidence

The committed `inventory.json`, recovery/citation reports, summary, review and
checksums name the exact tested revision. GitHub workflow artifacts also retain
the full tracked-file list and raw command output for 90 days. Their SHA-256
digests and rerun command remain recorded after artifact expiry. Do not equate
an expired artifact with a successful new run; regenerate and review if needed.

Reviewers must reproduce the critical positive and deliberate-failure cases,
inspect the dependency crosscheck and recovery results, and record their identity,
tested implementation commit, source/submodule pins, verdict and remaining scope.
The original `baseline.json` snapshots are immutable recovery targets. Updating
the current source inventory does not authorize changing those historical targets.

## Next work after P001 acceptance

P002 owns `.gitmodules` URL repair, a recursive dependency lock/verifier, proof of
anonymous pinned-object availability, and two independent recursive clones. Keep
all 149 parent gitlink SHAs unchanged unless a separately reviewed source change
is unavoidable. The inventory is a starting map, not proof that those dependencies
or Logic already work.
