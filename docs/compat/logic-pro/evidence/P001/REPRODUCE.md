# Reproduce the P001 source-baseline milestone

P001 verifies the recoverability and description of the complete pinned source.
Its original scope requires every recursive dependency to be inventoried. The
earlier parent-only acceptance was reopened because unknown descendants did not
satisfy that scope. The current procedure obtains and inspects all exact pinned
children, then runs an offline acceptance campaign. It does not build or execute
Darling or Logic, or claim that a later phase has passed.

## Clean source acquisition and offline acceptance

Use an x86_64 Linux host with Git and Python 3.10 or newer. The workflow exercises
Ubuntu 22.04 and 24.04. Public HTTPS access to the recorded source origins is
required during acquisition. The acceptance tools themselves disable Git network
transport and lazy fetching.
Use the tested implementation commit recorded in the evidence summary and review.

```sh
git clone --no-recurse-submodules https://github.com/boop-bip80/MAC-OS-EMULATION.git
cd MAC-OS-EMULATION
git checkout --detach 4707a919ef304945f7685390a68429242657eb54
PYTHONDONTWRITEBYTECODE=1 python3 tools/compat/logic-pro/prepare_sources.py \
  --repo . --upstream-url https://github.com/darlinghq/darling.git \
  --output ../p001-source-retrieval.json --jobs 8
PYTHONDONTWRITEBYTECODE=1 python3 tools/compat/logic-pro/run_baseline.py \
  --repo . --retrieval-report ../p001-source-retrieval.json \
  --output-dir ../p001-evidence
```

The output directory must be absent or empty and outside the checkout. Reusing an
old report directory is rejected. The workflow also exports compressed small JSON
reports to its log so the connected GitHub tool can retrieve evidence when the
interactive environment has no Git network transport. The export retains exact
SHA-256 digests; it does not change the evidence files.

Expected result is exit zero with `summary.json` reporting `PASS`,
**109 executed and passing fixture tests**, all 149 original parent gitlinks unchanged, all 160
recursive gitlinks and 161 repositories accounted for, zero unavailable child
contents, two verified isolated historical recoveries, and all 63 source citations
verified with complete category/stage coverage. This is a P001 candidate result;
a separate review is required before the README phase can pass.

## What is actually checked

`prepare_sources.py` reads committed gitlinks and `.gitmodules`, resolves root
relative URLs against the explicitly recorded Darling upstream, and resolves
nested relatives against each actually fetched parent origin. It fetches only
the original exact commits, with anonymous public transport and no source hooks
or filters. It preserves committed URLs and gitlink pins, records every command,
and rejects unsafe paths, dirty/mismatched checkouts and incomplete retrieval.
Fresh source-inspection checkouts use a recorded local `.git/info/attributes`
policy, `* -text -eol -ident -filter -working-tree-encoding`, so committed CRLF,
identifier and encoding attributes cannot transform the bytes being inventoried.
Committed `.gitattributes` files remain unchanged; an existing transformed
checkout is refused rather than rewritten. The libffi regression demonstrates
why `core.autocrlf=false` alone was insufficient.
The original fork-relative URL and the effective acquisition URL remain separate
evidence fields. See `upstream-provenance.json` for the identical original root
commit/tree in Darling upstream.

`inventory.py` reads the committed Git tree and `.gitmodules`, inventories tracked
paths, modes, object IDs and license-like files, and distinguishes exact child
checkouts from missing or mismatched ones. It records dirty state and staged index
changes separately from historical committed objects. It verifies actual file
bytes, executable bits and symlink text against Git blob identities, so index
flags such as `assume-unchanged` cannot conceal damage. It checks every child and
leaf tree recursively. Diagnostic mode can describe unavailable contents, but
the P001 campaign always uses `--require-clean --require-recursive`: any unknown
descendant makes acceptance fail.

`recover_baseline.py` creates two new clones with independent object stores from
the fetched parent repository. One restores the original audited source and prior
README; the other restores the initial roadmap integration. It verifies every
ordinary tracked file, executable bit, and symlink target against its Git blob
ID, checks exact commit/tree IDs and README SHA-256 hashes, and proves clean
checkouts. Gitlinks remain explicit uninitialized entries. Local recovery is not
proof that the current fork-relative dependency URLs are obtainable.

`verify_classifications.py` verifies immutable source blobs, inclusive line
ranges, exact excerpt hashes and required text. Child citations must match every
original and current gitlink hop. The current implementation must still contain
those audited blobs. `--require-phase-coverage` additionally requires eight
categories and six launch stages from the correct concrete source owners. A
nonempty subset, parent-only map or mislabeled source cannot satisfy that scope.

`run_baseline.py` runs the fixture tests and acceptance tools, retains command
logs, compares parent pins and restored trees with the independent GitHub
snapshot, and crosschecks every recursive gitlink against the tracked-file
manifest, exact child repository, acquisition record and source citations. It
recomputes completeness rather than trusting summary counters, then repeats the
physical inventory to detect changes during the campaign. Missing or stale
reports, empty/skipped tests, bad hashes, incomplete source graphs, mismatched
pins and failed commands prevent success.

## Complete tracked-file manifest

The complete recursive tracked-file JSON is committed as an exact gzip archive
split into 11 ordered binary parts under `tracked-files/`. The order, individual
part hashes and reconstructed archive hashes are recorded in
`tracked-files/manifest.json`. Concatenate the raw part bytes before decompression;
the parts are not separate gzip members. This publication layout avoids the
single large-blob request that stalled, while preserving the original archive
byte-for-byte.
Its byte count and SHA-256 are recorded in `evidence-index.json` and the actual
inventory reports. Each record identifies its owning repository, local/full
path, mode and exact Git object. Per-repository inventories include all
license/notice candidate paths and hashes, including prefixed names, legal
directories and raw symlink target text. These are deliberately inclusive
filename/path candidates, with discovery reasons and no legal interpretation.
Preserve emitted reports unchanged and expand the
archive when inspecting its original `tracked-files.json` payload:

```sh
cat docs/compat/logic-pro/evidence/P001/tracked-files/part-*.bin > /tmp/p001-tracked-files.json.gz
sha256sum /tmp/p001-tracked-files.json.gz
gzip -dc /tmp/p001-tracked-files.json.gz > /tmp/p001-tracked-files.json
sha256sum /tmp/p001-tracked-files.json
```

The concatenated gzip is 10,943,098 bytes with SHA-256 `ce373fd1818fd6f8f59d1f0e9cd39abf726ea789895e9383a44aef2e819f7799`. The archive avoids duplicating the complete recursive JSON for every host. Its decompressed payload is exactly 97,472,302 bytes with SHA-256 `047d659a94420c97f42d08cc4deea40fdc2912a69ff4c77057562835705404cd`. It reconstructs both `tracked-files.json` and `final-tracked-files.json` in each host directory. Their original names and hashes remain unchanged in each raw checksum table.
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

P002 owns committed `.gitmodules` URL repair, a recursive dependency lock/verifier
and qualification of the normal recursive-clone procedure in two independent
workspaces. Its anonymous availability checks can revalidate P001's acquisition
evidence. Keep
all 149 parent gitlink SHAs unchanged unless a separately reviewed source change
is unavoidable. The inventory is a starting map, not proof that those dependencies
or Logic already work.

## Verify the durable artifact copies

Run this from the repository root containing the accepted evidence. It validates
all fifteen entries in each original hosted checksum table, reconstructing the
identical large manifests from their single compressed archive:

```sh
python3 - <<'PY'
import gzip, hashlib, json
from pathlib import Path
root = Path('docs/compat/logic-pro/evidence/P001')
parts_root = root / 'tracked-files'
storage = json.loads((parts_root / 'manifest.json').read_text())
parts = []
for part in storage['parts']:
    data = (parts_root / part['path']).read_bytes()
    assert len(data) == part['bytes']
    assert hashlib.sha256(data).hexdigest() == part['sha256']
    parts.append(data)
compressed = b''.join(parts)
assert len(compressed) == 10943098
assert hashlib.sha256(compressed).hexdigest() == 'ce373fd1818fd6f8f59d1f0e9cd39abf726ea789895e9383a44aef2e819f7799'
manifest = gzip.decompress(compressed)
for folder in (root, root / 'ubuntu-22.04'):
    checksums = json.loads((folder / 'checksums.json').read_text())
    for name, expected in checksums.items():
        data = manifest if name in ('tracked-files.json', 'final-tracked-files.json') else (folder / name).read_bytes()
        assert len(data) == expected['bytes'], (folder, name, 'size')
        assert hashlib.sha256(data).hexdigest() == expected['sha256'], (folder, name, 'hash')
    print(folder, 'PASS', len(checksums), 'original artifact entries')
PY
```

The current acceptance is in `acceptance.json`; complementary independent reviews
are in `reviews/recursive-source-and-campaign/final-independent-review.json` and
`reviews/recursive-retrieval-and-source/final-independent-review.json`. Their
authorship exclusions prevent self-approval. The source/campaign review bundle
also contains `native-source-oracle.py`, a separate Git-plumbing reconstruction
that accepts `--repo`, `--output`, `--inventory` and `--tracked` arguments. Run it
against the tested implementation checkout, with the saved inventory and full
tracked manifest, to repeat the independent object/notice comparison.

The acceptance publication adds only documentation and evidence after the tested
implementation. Source counts/hashes describe that exact tested commit, not a
self-referential inventory of a later evidence commit. P002 remains NOT STARTED.
Historical parent-only evidence is retained through immutable links described in
`history/README.md`; it must not be substituted for the current recursive reports.
