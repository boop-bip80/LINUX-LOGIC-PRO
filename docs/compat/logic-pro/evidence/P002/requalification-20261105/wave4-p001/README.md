# Wave 4 independent P001 original-evidence review

**Decision: P001 ACCEPTED.** All four original P001 gates pass at implementation
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`, tree
`957b20a38292ae2bd70c5cc90deef5ab274c73ba`.

**Acceptance time:** 2026-11-06 04:06:14 UTC.  
**Reviewer:** `/root/wave4_p001_evidence`, independent of the production authors.

This is the ordered P001 prerequisite acceptance. P002 may now complete its
independent evidence review and final acceptance. This report does not accept
P002 or reaccept P003/P004, and contains no runtime or Logic Pro execution claim.
The mandatory `AGENTS.md`, README global acceptance contract and original P001
G1–G4 requirements were read. No gate, recovery anchor, historical assertion or
production file was changed for this review.

## Original gate decisions

| Gate | Verdict | Independently established evidence |
| --- | --- | --- |
| G1 — every tracked gitlink and committed SHA appears once; missing/unreachable sources identified | **PASS** | All 160 unique current gitlink paths match native owning trees, inventory records, child commits and frozen provenance; 161 repository trees and 293,660 tracked entries match native Git objects. Both hosted retrievals report complete source acquisition, with every retained retrieval command exiting zero and no unavailable gitlink. |
| G2 — clean baseline checkout resolves the recorded tree without unrecorded changes | **PASS** | Both pre/post inventories on both hosts identify exact d58, clean working trees/indexes and complete physical blob verification. Independent recovery reproduced both original trees in clean isolated checkouts; all 27,125 blobs per snapshot and modes/symlink target bytes were verified. |
| G3 — concrete source citations for runtime, architecture and stub classifications; static and executed evidence distinguished | **PASS** | All 63 historical and 63 current citation blobs, exact line excerpts, required assertions and parent chains were checked directly against Git objects. Required category and launch-stage coverage is complete. Runtime and Logic Pro execution remain explicitly false. |
| G4 — recovery restores baseline and previous README in an isolated checkout | **PASS** | The original recovery manifest is byte unchanged from c7ef7fe4. A fresh local recovery restored 3447ff5a and b25035fc with exact trees and README hashes, separate object stores, clean destinations and unchanged source. Both original hosted recoveries agree. |

The machine-readable decision is [acceptance.json](acceptance.json). The
complete independent results are in
[independent-original-verification.json](independent-original-verification.json).

## Official hosted provenance and original ZIP bytes

Fresh official GitHub API reads of the run, jobs and artifacts are retained as
[official-run.json](official-run.json), [official-jobs.json](official-jobs.json)
and [official-artifacts.json](official-artifacts.json). Run
[42155822562](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822562)
completed successfully at exact d58. Both source recovery jobs and every job
step succeeded; the reported workflow is `.github/workflows/phase1-baseline.yml`.

| Host | Artifact ID | Original ZIP bytes | Original ZIP SHA-256 |
| --- | ---: | ---: | --- |
| Ubuntu 22.04 | 13474243274 | 22,224,353 | `a7b6025493d107f51e90bdf94f52be6247a462f1b86d630011d0351de0b75447` |
| Ubuntu 24.04 | 13474213466 | 22,227,464 | `cb6316201b0db5e769cd20a88738b32e9b7c42ef7945c32e73fe99a38d2614cf` |

For each original ZIP I recomputed the whole-file SHA-256 against the official
artifact digest and checked ZIP CRCs. Exactly 17 unique members were present.
Every member equals its extracted raw file byte for byte, and all 16 nested
checksums and lengths match. The result retains every member's size and digest.
Both actual verbose fixture transcripts contain 174 distinct test names, a
`Ran 174 tests` line and final plain `OK`; each of the six gate commands exited
zero and its retained log hash matches. Every source retrieval command exited
zero, and each source retrieval digest matches the aggregate. These checks used
the original ZIP bytes and raw records rather than trusting a PASS summary.

## Complete tree and graph reproduction

All four full tracked manifests — initial and final on both hosts — contain
**97,657,320 bytes** and share SHA-256
`c2995040954cc2f844994ac8854ee51607c15a9a3c0a552f4ae53fa1635cd0cd`.
They preserve all **293,660 entries**. All four inventories agree on the complete
repository and submodule state.

The independent [verify_originals.py](verify_originals.py) imports no production
gate module. It groups entries by owning repository, constructs the native Git
tree encoding with Git's directory ordering, hashes each constructed tree, and
compares the root tree with the recorded and actual commit tree. It also compares
every mode/type/object/path tuple with native `git ls-tree -r -z` output.
**All 161 repositories and 37,764 reconstructed native tree objects passed.**

Root objects were read from the exact d58 worktree's Git database. Child objects
were read without modifying `/workspace/scratch/5826e6462159/source-audit`.
That checkout's root is 6cb6cada; it is used solely as the available child object
store. Each child is selected by its recorded immutable commit, while d58 root
objects are read from the exact implementation database. All 160 current pins
and all 160 historical pins were separately resolved through their actual
parent trees and compared with each child's actual tree.

All **755 license candidate** records were checked against the native tracked
mode and blob ID, the canonical physical Git blob hash, byte length and SHA-256.
This confirms candidate discovery and byte provenance; candidate filenames are
not a legal conclusion. The review retained metadata and hashes, and did not
copy restricted implementation source or license text into its evidence.

## Historical and current citation reproduction

The original 63-entry `evidence` array and original `inspected_commit` are
unchanged from committed c7ef7fe4. The historical inspection anchor remains
`b25035fce2cd1c038c567d34ea0797371947d95d`; the historical recursive source graph
remains anchored at `4707a919ef304945f7685390a68429242657eb54`. The current graph
and separate current citation supplement remain anchored at
`c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`.

For all 63 records in each era I independently resolved the recorded path in
its owning commit, read the Git blob, recomputed the canonical blob SHA-1 and
exact inclusive line-excerpt SHA-256, and checked every declared assertion.
Every child citation's complete gitlink chain was resolved through native parent
objects. Current root citations were resolved at exact d58. The two hosted
classification reports are byte identical. This directly reproduces the critical
citation checks, including the changed current child pins, without substituting
current source for the historical oracle.

The source evidence distinguishes native Linux host code, Mach-O components,
implemented but unqualified bodies, partial frameworks, developer link stubs,
stub generation and generated placeholder bodies. The launch stages cover host
launch, mldr mapping and dyld handoff, dyld dependency loading, system library
initialization, server check-in/RPC dispatch and framework initialization. These
are static source classifications, not execution proof or framework-completeness
claims. Architecture constraints remain tied to their concrete source citations.

## Independent recovery and regression execution

The full baseline fixture command was independently run in the exact d58 worktree:

```sh
python3 -m unittest discover -s tests/compat/logic-pro/baseline -p 'test_*.py' -v
```

Observed result: **174 tests passed in 23.430 seconds**, exit zero, with no skipped
or weakened assertion. The full transcript is
[fixture-reproduction.log](fixture-reproduction.log). It includes the existing
positive and negative inventory, source preparation, citation, aggregate,
source-equivalence and recovery tests. No additional test was introduced for
this evidence-only review.

The exact implementation's `recover_baseline.py` was independently executed
against the original manifest. [recovery-reproduction.json](recovery-reproduction.json)
and its [raw log](recovery-reproduction.log) record the successful result.

| Restored snapshot | Original commit | Native tree | Verified blobs / tracked entries |
| --- | --- | --- | ---: |
| Baseline | `3447ff5ab8e837ea54a13a506c60d34d77e2bd15` | `cfa2352b7296ef5667a8f8c5a11a5718bb3453a0` | 27,125 / 27,274 |
| Previous integration | `b25035fce2cd1c038c567d34ea0797371947d95d` | `43461175ff5cfc470f1c1dbf1e4e202aa93a2123` | 27,125 / 27,274 |

The original baseline README SHA-256 is
`c4caa8d1815a58a763e91bd98cf5c3b40c6247d7c63ad5bfc61aa8291f5a14af`;
the previous integration README SHA-256 is
`9d2df6cb94822cf1335324fb5d77bb1c57773c4c20598c88baca4f06d6c5221d`.
Both were independently recomputed from the original commit blobs and matched
both hosted and local recovered results. Both local restored worktrees are clean
and have disjoint object stores. Their complete materialized-entry digests equal
those in both hosted recoveries. The review worktree contained only the newly
saved official metadata files when recovery began; recovery recorded and
preserved them and did not import them into either isolated destination.

[reproduction-commands.json](reproduction-commands.json) records the three
independently executed commands and observed exits. Run `verify_originals.py`
with the exact implementation checkout, the original artifact directory, the
read-only child object checkout and a report output path to reproduce this
independent object/byte verification.

## Durable evidence and implementation review prerequisites

Before this acceptance, the complete lossless original archive was published at
`44b20845cbbe9a4e1bb951c9fb1da4cbc68b309a`, with tree
`7769b8ecc47a7d2f70f320f2759543979982bb45`. The coordinating reviewer anonymously
fetched that commit into a fresh bare Git object store and reconstructed all
70 members across the four P001/P002 artifacts, comparing each with the original
artifact member hashes. The published confirmation and final integrity review
are at `f8af3e1c9e0f27cd36c13a9b8ce4684088063a57`.

I read that exact published confirmation and all three published Wave 3
implementation reviews. I also directly verified the expected archive tree in
the fresh bare object store and the absence of an alternates file. The confirmation
is retained as [published-archive-readback.json](published-archive-readback.json),
and the exact published prerequisite paths and hashes are recorded in
`acceptance.json`. All three scoped implementation reviews approve, including
the independently reproduced corrupt-blob rejection. Publication and final
integrity review prerequisites were satisfied before the acceptance timestamp.

## Handover

P001 G1–G4 are accepted at exact d58 as of the timestamp above. The original
recovery obligations and historical citation evidence remain intact. The next
permitted phase decision is P002, using the separate independent ordinary-clone
and LFS evidence reviews and the user's required final review wave. No production
changes were made by this reviewer; this commit contains only review evidence
and the README handover.
