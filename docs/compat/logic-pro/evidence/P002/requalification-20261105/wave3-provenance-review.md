# P002 wave three: independent provenance and lock implementation review

Date: 2026-11-06 UTC

Reviewer: `/root/wave3_provenance_review` (non-author of the reviewed implementation)

Reviewed implementation: `9612e4b7a5931a15e892881173a643008af032ea`

Integration comparison: `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`

## Decision

**APPROVED for the scoped provenance and lock implementation.** No concrete
implementation defect or acceptance bypass was reproduced. This is an
independent implementation review, not P001 or P002 phase acceptance. Hosted
campaign artifact review and the ordered final acceptance decisions belong to
later review waves.

The four scoped implementation artifacts are byte unchanged between the
reviewed commit and integration commit `d58cca51`, as independently checked
with `git diff --name-only`:

- `tools/compat/logic-pro/source_provenance.py`
- `tools/compat/logic-pro/make_submodule_lock.py`
- `docs/compat/logic-pro/submodules.lock.json`
- `tests/compat/logic-pro/submodules/test_source_provenance.py`

No production change or additional regression fixture is included with this
review because no new defect was reproduced. Existing strict tests and
historical evidence remain intact.

## Contract and scope

Read the repository `AGENTS.md` and the README P001/P002 acceptance contracts,
including the historical and current-source distinctions. Reviewed the complete
new provenance loader, lock generator, new provenance tests, and the related
physical checkout and LFS validation paths. The source identity loader must not
turn source review or a local test result into ordinary-clone or phase acceptance.
P001 must be reaccepted before current-source P002 is accepted.

This review used Git object metadata, committed `.gitmodules` configuration,
archived evidence, and the 44 known Git LFS pointer blobs. It did not inspect
restricted Apple or corecrypto source, application payloads, disassembly, or
private credentials. The review made no dependency-source or gitlink changes.

## Independent immutable-object checks

The original retrieval, historical acceptance, and current source are distinct
immutable commits. Direct `git rev-parse <commit>^{tree}` checks produced:

| Role | Commit | Tree |
| --- | --- | --- |
| Original retrieval | `4707a919ef304945f7685390a68429242657eb54` | `8fb4a8c4b7855d2dec827a9e4d6499cb113b3776` |
| Historical acceptance | `89c6c9d85aba6ed1662035e6366298c92ef9c970` | `1ce359808d725efd07ec2b51548760893a7cf5a5` |
| Current source | `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a` | `8f3700d4cf59d47449ab7d8243d0d3599a32a6ac` |

Read the historical accepted lock directly with
`git show 89c6c9d85aba6ed1662035e6366298c92ef9c970:docs/compat/logic-pro/submodules.lock.json`.
Its SHA-256 is
`1540d2552f36bd5ed29a640dbe12dfe0e37c618c02ed7fd1d59d4264a8ba5f1b`,
matching the separately frozen historical lock identity.

Independently traversed the original and current pinned graphs using the
available object stores under `source-audit`. For each graph, inspected
`git ls-tree -rz <pinned-commit>` in the root and every recorded child repository,
compared all gitlink paths, immediate parents and commits, and checked every
recorded commit's tree with `git rev-parse`. Both reconstructed graphs matched
the archived records exactly: **160 records each, 320 records compared**, with
149 direct and 11 nested records per graph. No discrepancy was found.

Independently read committed `.gitmodules` at the owning pinned commit for
every graph parent with `git config --blob <commit>:.gitmodules --null --list`.
All **320 declared URL records** matched the corresponding original/current
archive. Compared the complete current lock mapping of path, immediate parent,
commit, tree, and canonical public acquisition URL with the frozen current
mapping: **all 160 records matched**.

## Frozen evidence and semantic validation

Recomputed SHA-256 for the historical retrieval JSON, compressed current
retrieval archive, current archive manifest, and pin-review JSON. Independently
decompressed the current archive and checked its raw SHA-256. All five matched
the frozen implementation constants; loader validation also checks archive/raw
byte lengths and the manifest's source, count, and PASS result.

The reviewed loader binds the original and current root commits and trees,
requires a completed PASS retrieval with no failures and exactly 160 unique,
canonical paths, and reconstructs immediate parents from the complete path set.
It rejects cached-only retrieval labels. The review requires exactly the complete
14-record graph delta, including 13 direct changes and the nested
`src/external/metal/deps/indium` change. Each record binds both old/new commits
and trees, the unchanged immediate parent, and the canonical acquisition URL.
The pin-review status explicitly remains
`SOURCE_REVIEW_ONLY_NOT_PHASE_ACCEPTANCE`.

The normal generator calls the digest-verifying loader before selecting evidence.
A caller-supplied report must equal the verified original or current report;
arbitrary modified evidence cannot establish a new trusted graph. Original
retrieval evidence against current root pins still fails. Current generation
binds the committed root declarations and root gitlinks to the reviewed records,
then validates nested resolution and the complete lock. Physical materialization
and payload validation remain responsibilities of the existing checkout and LFS
verifiers and hosted campaigns.

The semantic helper accepts fixtures for adversarial tests. It is not the trust
entry point: production generation uses `load_reviewed_source`. Its diff digest
fields are validated structurally and are themselves covered by the frozen
pin-review file digest. This bounded implementation review did not repeat the
author's full dependency-source diff review or independently establish network
reachability from cached object availability.

## LFS preservation

Compared both `lfs_objects` and `lfs_repositories` in the current lock with the
LFS provenance manifest and the immutable historical accepted lock. Both lists
match exactly. The lock contains **44 objects in one owning repository**.

For every one of the 44 records, used its owning pinned repository commit and
repository-relative path to check the committed mode and pointer blob identity.
Read only those known pointer blobs and checked the pointer version, SHA-256
object identifier and declared payload size against the lock. **All 44 matched.**
This establishes the preserved pointer inventory; it does not substitute for
ordinary-clone payload retrieval or the hosted payload checks.

## Tests and negative coverage

Independently ran at the reviewed implementation commit:

```sh
python3 -m unittest discover -s tests/compat/logic-pro/submodules -p 'test_*.py' -v
```

Result: **110 tests passed in 26.746 seconds**. No skipped or weakened assertion
was introduced for this review. Existing physical/index/origin/URL/LFS corruption
checks were included.

Reviewed the new negative cases for omitted, extra, duplicate, stale, reparented,
and altered source-review records; wrong roots, trees, counts, status and
digests; an unreviewed fifteenth change; changed historical evidence; missing or
duplicate current retrieval records; cached-only retrieval; tampered frozen
files; and caller-supplied altered evidence. The CLI cases prove byte-identical
regeneration from an unrelated working directory and rejection of historical
evidence against current pins without writing an output lock.

The integration coordinator reports that the complete integration suites and
four hosted jobs pass at `d58cca51`. This reviewer did not count that report as
independently reviewed campaign evidence. The independent local result above
and the verified unchanged scoped files are the implementation-review evidence.

## Remaining acceptance boundaries

The later artifact-review wave must evaluate the original hosted archives,
ordinary-clone isolation and credentials policy, source equivalence, command
and payload results, and exact tested revision. Current-source P001 then P002
acceptance must follow their README contracts. No local suite, frozen source
inspection, cached Git metadata, or this scoped approval establishes phase
acceptance by itself.
