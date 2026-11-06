# Wave 4 independent clone B and LFS review

**Verdict: APPROVE the scoped clone B/LFS and cross-host evidence review.**
Reviewer: `/root/wave4_clone_b_lfs`, 2026-11-06 UTC. The reviewer authored no
production changes. Tested implementation:
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.

No blocking defect remains in this scope. This is a technical Wave 4 approval,
not whole-phase acceptance. P002 still needs the P001 predecessor decision,
complementary clone A review, and final Wave 5 decision. P003/P004 are not
reaccepted by this report. No production source, test expectations, lock,
workflow, or phase status was changed by this reviewer.

## Original evidence and official identity

I independently fetched the public run, jobs, and artifact collection through
the GitHub read-only connector. The retained response bodies and request URLs
are in [official-identities.json](official-identities.json). The run completed
successfully at the exact tested source, with the following identities:

| Record | Clone A | Clone B |
| --- | --- | --- |
| Run | 42155822754 | 42155822754 |
| Job | 127689585878 | 127689585612 |
| Official job label | ubuntu-22.04 | ubuntu-24.04 |
| Official runner ID | 1000004197 | 1000004200 |
| Artifact | 13475330560 | 13474341831 |
| Original ZIP bytes | 53,657 | 54,174 |
| Image | ubuntu22 / 20261101.347.1 | ubuntu24 / 20261101.360.1 |
| Python | 3.10.12 | 3.12.3 |
| Git | 2.56.0 | 2.56.0 |
| Git LFS | 3.8.1 | 3.8.1 |

Official run: <https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822754>.
Clone B job:
<https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822754/job/127689585612>.

The independently calculated original ZIP SHA-256 values equal the official
artifact `digest` fields and the original downloaded metadata:

- A: `cca5a057713e7b5688cb1c2f03a7adfd12606b21a70b5bdac8c7def36171296d`.
- B: `5a9b117e720e2d1d93ce406ec971dc9e29dc2dfee565410c5647c954fe7af376`.

Both ZIP CRC checks pass. Each has exactly 18 unique members, each member equals
the extracted original byte for byte, and each member's independently calculated
size/hash matches the original member manifest. All 17 internal checksum lines
per artifact pass with complete coverage. The original metadata wrapper omits
the API's `node_id`; all fields it does retain equal the independently fetched
official response. These checks use the original ZIP bytes, not replacement
archives generated from summaries.

Full results, including every member hash and every command segment, are in
[evidence-audit.json](evidence-audit.json). The review-owned stdlib auditor is
[replay_review.py](replay_review.py). The separate durable original archive was
published at evidence commit
`44b20845cbbe9a4e1bb951c9fb1da4cbc68b309a`; root's anonymous 70-member remote
readback confirmation is published at
`f8af3e1c9e0f27cd36c13a9b8ce4684088063a57`. Those documentation commits do not
replace the tested implementation identity. Root owns that full-archive
publication/readback review; my checks above independently address the original
clone A/B artifacts supplied to this reviewer.

## Commands, actual fixtures, and acquisition independence

For each original artifact I independently rehashed all 13 command segments
using their recorded offsets and lengths, verified all exits are zero, and
required contiguous complete coverage of the referenced log bytes. This includes
the zero-length successful exact-commit presence probe. I also rehashed the
outputs of the three nested LFS commands and checked their zero exits.

Both transcripts contain **115 distinct test invocations and 115 successful
case completions**, followed by an unqualified `Ran 115 tests` / `OK` result.
No skipped, expected-failure, unexpected-success, failed, or errored case counts
as success. This audit counts actual case records independently of the campaign
summary. The recorded tests run from the newly acquired clone. The independent
local rerun also completed all 115 cases in 28.133 seconds, exit zero, with no
qualified success; see [local-fixture-tests.log](local-fixture-tests.log).

The workflow at d58 checks out the runner with pinned `actions/checkout`,
`submodules: false`, and `persist-credentials: false`. Its two matrix jobs have
different official runner IDs and different hosted OS images. The two campaign
records name different destinations, `p002-independent-clone-a` and
`p002-independent-clone-b`, outside the runner source checkout. Both runner
`source-head.sha` and fresh-clone `head.sha` are exactly d58.

The recorded acquisition is ordinary anonymous HTTPS Git: `git clone --no-local
--no-hardlinks --no-checkout --no-recurse-submodules --origin origin` from the
public project URL, detached checkout of the immutable SHA, then `git submodule
update --init --recursive --jobs 12`. No reference/shared-store clone option is
present. The reviewed runner refuses an existing destination or overlapping
source/clone/evidence directory, removes ambient Git selectors and credentials,
disables global/system Git configuration and interactive credential lookup,
disables hooks/fsmonitor, and restricts normal acquisition to HTTPS. The LFS and
strict-verifier checks reject private object-store alternates and attribute
overrides. Together, the official distinct hosts, workflow, exact source, and
recorded acquisition establish independent fresh object stores; different path
strings alone would not establish independence.

## Exact graph, current lock, and physical payloads

Both original strict-verifier reports contain the same complete 160-row
`path`/`commit`/`tree`/`resolved_url` graph as the tested lock. Graph comparison is
by path because report traversal order differs from lock order. The 160 native
recursive status lines in each artifact are all clean and independently match
the locked path/commit map. Both reports record 149 direct gitlinks, 160 recursive
gitlinks, 161 repositories, and **293,500 physically checked blobs** with zero
conflicted, dirty, mismatched, or uninitialized repositories. Both report the
physical bytes/modes/symlinks/LFS verification method, rather than a status-only
method.

Both regenerated locks equal the current tested lock byte for byte, independently
of their regeneration receipts. Its SHA-256 is:
`2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`.
The local lock itself equals `git show d58cca51:docs/compat/logic-pro/submodules.lock.json`.

Every one of the 44 hosted LFS records exactly matches the lock's path, SHA-256
OID, byte size, and executable mode, with no extra or missing record. Both hosted
reports verify **16,128,448 actual payload bytes**. Repository metadata matches
the locked Swift owner commit
`471514f4b4985a604b192e1facac9bbc53dedad3`, origin
`https://github.com/darlinghq/darling-swift.git`, and committed endpoint
`https://git-lfs.darlinghq.org/lubos/darling-swift`. Each hosted command fetches
that immutable owner commit and checks out the explicit 44 paths. The LFS
implementation SHA-256 matches the reviewed d58 source file.

As a separate physical crosscheck, I read all 44 files in the supplied read-only
Swift-only checkout. For every file, an independent stdlib SHA-256 calculation,
regular-file check, byte count, and executable mode match the lock and both
hosted reports. I checked each committed pointer's canonical bytes and Git tree
mode/blob ID, as well as the owner HEAD/origin and the committed `.lfsconfig`
SHA-1/SHA-256 identities. The per-file results are retained in the audit JSON.
This crosscheck confirms the payload identities and availability. It is not a
third complete hosted clone and does not replace either original full campaign.
The 293,500 count is a verified claim in the original complete hosted verifier
output, not a claim that this local Swift-only checkout contains all those files.

## Critical failures and recoveries

[reproduce_lfs.py](reproduce_lfs.py) constructs disposable synthetic repositories
using the tested fixture's repository builder, then applies review-owned
mutations with explicit failure/recovery assertions. It never mutates the
supplemental real payload checkout. Full observations, commands, and tool
versions are in [lfs-reproductions.json](lfs-reproductions.json).

| Case | Observed result |
| --- | --- |
| Unhydrated pointer text | Rejected; restored actual payload passes |
| Same-size payload corruption | SHA-256 rejection; restored bytes pass |
| Truncated or missing payload | Size/open rejection; restored bytes pass |
| Executable bit removed | Mode rejection; restored mode passes |
| Corruption under assume-unchanged | Rejected; restored bytes pass |
| Corruption under skip-worktree | Rejected; restored bytes pass |
| Leaf symlink, parent symlink, FIFO | Rejected; regular restored path passes |
| Actual Git LFS cached checkout | Installed Git LFS materializes the synthetic payload; physical hash/mode/size pass |
| All mocked command exits succeed but pointer remains | Hydration rejects, remains FAIL, zero verified payloads |
| Mocked endpoint failure | Hydration rejects after two commands, remains FAIL, no checkout fallback |

The ten physical mutations each pass an initial valid-payload check, fail after
mutation, and pass after restoration. The real cached checkout uses an isolated
synthetic cache and actual Git LFS 3.6.1; it makes no additional network
acquisition claim. The hosted successful network acquisitions used Git LFS
3.8.1. The two failure-outcome probes mock only command results and exercise the
real hydration decision and physical verifier. The independent full local
115-case suite additionally covers endpoint/provenance drift, staged pointer
changes, malicious local configuration, dirty/private attributes, object-store
overrides, filters/fsmonitor execution prevention, pointer discovery, and
corrupted Git-object rejection. No new production test or exception was needed.

## Replay and limits

From the repository root, with the original ZIPs and extracted folders under
`/path/to/raw-evidence` and the supplemental checkout under
`/path/to/lfs-availability`, run:

```sh
python3 -B docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-clone-b/replay_review.py --repo . --raw /path/to/raw-evidence --physical-root /path/to/lfs-availability --output /tmp/p002-wave4-evidence-audit.json
python3 -B docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-clone-b/reproduce_lfs.py --repo . --output /tmp/p002-wave4-lfs-reproductions.json
python3 -B -m unittest discover -s tests/compat/logic-pro/submodules -v
```

The replay auditor checks a retained independently fetched official snapshot;
re-fetch its listed public endpoints when a new live metadata check is required.
Fixture runs use temporary repositories and do not require network fetches.
The scope is repository reproducibility, payload integrity, and evidence
qualification. It does not establish macOS/Logic behavior or accept later
phases. I used public repository metadata, committed pointer/configuration
metadata, byte hashing, synthetic tests, and original hosted logs. I did not
inspect restricted Apple/corecrypto source, disassemble binaries, or infer
private implementation details.

**Handover:** approve this Wave 4 scope, publish this documentation-only review
commit, and proceed to the ordered predecessor/complementary/final reviews.
