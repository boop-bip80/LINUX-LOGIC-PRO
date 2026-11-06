# Wave 5 final independent P002 archive replay

Reviewer: `/root/wave5_final_replay`, 2026-11-06 UTC. This reviewer authored no
production changes. The reviewed implementation is
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`, tree
`957b20a38292ae2bd70c5cc90deef5ab274c73ba`.

**Final verdict: P002 ACCEPTED, all G1–G4 PASS, at 2026-11-06T04:29:24Z.**
The signed [acceptance.json](acceptance.json) binds the completed bounded replay,
five focused gate reproductions, published P001 predecessor, and published
independent final source approval. No unresolved blocker remains in P002 scope.

## Original evidence replay

I read the applicable `AGENTS.md`, global README acceptance rules, and P001/P002
gate definitions. I ran the committed
[`verify_archive.py`](../hosted-d58cca51/verify_archive.py) into a new destination.
It exited zero after reconstructing and hashing **all 70 original members in
four original hosted artifacts**, including seven unique compressed payloads.
The exact invocation and output are in [archive-replay.log](archive-replay.log).

I then compared each reconstructed member, byte for byte, with both its original
ZIP member and the original extracted member. All four original ZIP sizes,
SHA-256 digests, CRCs, exact member sets, and original acquisition receipts match
the committed archive manifest. The official artifact metadata in those
receipts binds each ZIP to the exact tested revision and original hosted run.
This is a fresh replay of retained evidence, not a new network acquisition.

| Original artifact | Run | Artifact ID | ZIP bytes | Original members | Hosted tests |
| --- | --- | --- | --- | --- | --- |
| P001 Ubuntu 22.04 | 42155822562 | 13474243274 | 22,224,353 | 17 | 174 |
| P001 Ubuntu 24.04 | 42155822562 | 13474213466 | 22,227,464 | 17 | 174 |
| P002 clone A / Ubuntu 22.04 | 42155822754 | 13475330560 | 53,657 | 18 | 115 |
| P002 clone B / Ubuntu 24.04 | 42155822754 | 13474341831 | 54,174 | 18 | 115 |

The original successful runs are [P001 42155822562](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822562)
and [P002 42155822754](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822754).
Archive publication is bound to `44b20845cbbe9a4e1bb951c9fb1da4cbc68b309a`;
the preexisting fresh remote readback record is published at
`f8af3e1c9e0f27cd36c13a9b8ce4684088063a57`.

[replay_checks.py](replay_checks.py), [replay-checks.log](replay-checks.log), and
[replay-results.json](replay-results.json) retain this final comparison. The
first invocation incorrectly treated the original acquisition receipt wrapper
as the embedded official metadata object. Inspection showed the documented
`metadata` member; correcting that field selection made the complete comparison
pass without changing any original evidence or acceptance condition. The
initial failed invocation is preserved in
[replay-initial-schema-error.log](replay-initial-schema-error.log).

## Actual commands, source graph, isolation, and payload identity

I fetched public review commit `ef6e43b6862cba0a8642d38c8e103421e7142369`
from the project remote and reran the two independent published Wave 4 artifact
auditors without altering their bytes. Their exact source hashes and commands
are recorded in `replay-results.json`; their results are
[clone-a-replay.json](clone-a-replay.json) and
[cross-host-replay.json](cross-host-replay.json). The latter retains the
original auditor's reviewer field; the invoking final reviewer and execution
record are explicitly identified in `replay-results.json`.

Both auditors passed. Together they check the two original ZIPs, their 36
members and 34 internal member hashes, all 26 recorded command segments, output
offsets and lengths, zero exit codes, and **230 actually completed P002 test
cases**. Unqualified `OK` endings are present; skips and qualified successes do
not count as a passing campaign. The final wrapper also checks all original
P001 command-log hashes and zero exits, exact implementation identities, and
the two 174-test transcript endings.

The original P002 jobs have distinct official runner IDs and Ubuntu 22.04/24.04
labels. Their source and acquired-clone HEADs equal the tested revision. Their
commands show public HTTPS acquisition with `--no-local --no-hardlinks`,
separate absent clone destinations, immutable detached checkout, and ordinary
recursive submodule initialization. The reviewed implementation rejects
existing destinations and alternate object stores and disables ambient
credentials and configuration. The original workflow, recorded commands,
distinct hosted machines, and strict source review jointly establish independent
object stores; different local path strings alone would be insufficient.

Each host's complete native status and verifier graph match all **160 locked
recursive gitlinks**, including **149 direct gitlinks**, with zero uninitialized,
mismatched, conflicted, or dirty entries. Clone A's acquisition transcript also
contains all 160 actual checkout records. The detailed verifier records and
summaries agree on 161 repositories and 293,500 physically verified blob paths.
Both regenerated locks are byte identical to the 94,944-byte committed lock at
the tested revision, SHA-256
`2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`.

All 44 hosted LFS path/OID/size/mode records match that lock and total 16,128,448
bytes. As a supplemental check, the rerun cross-host auditor independently read
and hashed all 44 actual files in the provided read-only Swift checkout and
verified their committed pointer and endpoint provenance. This partial checkout
does not replace either original complete hosted clone. The 293,500-blob count
is an original hosted measurement corroborated by its exact verifier, logs, and
independent adversarial reviews; I did not repeat a full local network clone.

## Strict failures and changed-pin provenance

I independently invoked five bounded existing tests against unchanged tested
production code. The valid recursive checkout passed. Actually committed wrong
gitlink and `.gitmodules` URL fixtures were rejected. Real corrupt loose blobs
were rejected in SHA-1 and SHA-256 repositories. Corrupt canonical blob bytes
could not authorize a matching forged CRLF checkout. All five tests completed
successfully in 1.773 seconds, exit zero, with no skips. Exact command,
environment override, and transcript are in
[critical-gates.json](critical-gates.json) and
[critical-gates.log](critical-gates.log).

I also read the published scoped Wave 4 reviews and their reproduction
summaries: clone A's 15 positive/negative cases and clone B's 13 LFS/recovery
cases, plus clone B's 115-test local rerun. Those reviews cover physical bytes,
executable mode, symlink confinement, hidden index flags, real Git object
corruption, native tree corruption, unhydrated/missing/corrupt payloads,
successful commands leaving pointers behind, and explicit endpoint failure.
The normal CRLF allowance remains limited to declared attributes and exact
conversion bytes, after canonical object integrity verification.

The published Wave 3 provenance review independently bound both original and
current native graphs, all 320 declared URL records, frozen source identities,
and the exact 14-record delta. I read that review and all 14 pin-review records:
13 direct changes and nested `metal/deps/indium`, with old/new commits, trees,
public upstream URLs, diff hashes, scope summaries, and no recorded license-file
changes. These changes were already merged by the owner before this campaign;
this review neither advances nor rewrites a dependency pin. Original historical
recovery and citation identities remain binding. The hosted native graphs and
byte-identical locks supply the current acquisition proof missing from a cached
source inspection alone. [reviewed-inputs.json](reviewed-inputs.json) binds the
published reports read in this final review.

## Ordered prerequisite and scope

Public commit `ef6e43b6862cba0a8642d38c8e103421e7142369` contains P001's formal
G1–G4 acceptance at **2026-11-06T04:06:14Z**, reviewer
`/root/wave4_p001_evidence`, for the same exact tested revision. I verified every
file listed in its published review-checksum manifest and the acceptance JSON
itself. Its acceptance SHA-256 is
`f17b1207c8b37c416c0c986d5916c3a34b96fa11c9bb14ace52b91cea2411b90`.
This predecessor must remain valid and temporally precede the separate final
P002 decision. The final source approval and its publication identity are bound
by `acceptance.json` before that decision is signed.

This review qualifies repository acquisition, source identity, dependency
provenance, and evidence integrity for P002. It does not accept P003, P004,
macOS/Logic Pro runtime behavior, or later phases. No dependency code was
executed, no binary was disassembled, and no restricted Apple/corecrypto
implementation was inspected. All changes made here are review documentation,
evidence logs, and the bounded replay wrapper.

## Final source approval and decision

The source approval was published at `f2cbf424b7a5433b20ecfcb1900e69de0adfbad5` and fetched from
the project remote before this signature. Its three report files equal the
reviewed local approval bytes exactly. The identity report SHA-256 is
`cdf21bef42056e2d93bc1962795f62c6c74016efbe6948d13ffe52b960f6f731`.
The independent reviewer approved all 27,812 protected paths, nine explicitly
protected consumed frozen inputs, the original regression semantics, and 149
unchanged root gitlinks. [source-approval-readback.json](source-approval-readback.json)
records the public commit/tree and exact report hashes.

At **2026-11-06T04:29:24Z**, after P001 acceptance at 04:06:14Z and that
published source approval, this independent reviewer accepts **P002 G1, G2, G3,
and G4**. The root coordinator owns the final dashboard and ordered ledger
update. No later phase is accepted by this decision.
