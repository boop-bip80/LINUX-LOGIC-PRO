# P002 current-source requalification — 2026-11-05

## Scope and status

**ACTIVE; no new phase acceptance is claimed.** The user requested five waves
of analysis and coding, with incremental commits and pushes, until Phase 2 can
be judged against its original gates. The starting source is
`c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a` on `master`.

The current upstream merge advances 13 direct gitlinks without updating the
historical P002 lock. The actual 97-test P002 suite fails its lock regeneration
test at `src/external/bootstrap_cmds`. P001's current 151-test suite also fails
(six failures and one error), so ordered predecessor acceptance must be repaired
and verified before P002 can pass. Historical acceptances remain historical.

## Five-wave ownership

| Wave | Three parallel assignments | Integration gate |
| --- | --- | --- |
| 1 | Lock/physical verifier audit; LFS/campaign audit; predecessor/CI/evidence audit | Reproduce and record actual current-source defects |
| 2 | Dependency provenance/lock repair; acquisition/verification repair; prerequisite source-gate repair | Focused positive and negative tests, reviewed changes |
| 3 | Independent lock review; adversarial campaign review; predecessor regression review | Fix remaining findings and publish exact candidate |
| 4 | Independent clone A review; independent clone B/LFS review; P001 evidence review | Original exact-source campaign evidence and ordered review |
| 5 | Final source/diff review; independent evidence replay; acceptance/documentation consistency | Explicit non-author verdicts for every original gate |

`/root` owns integration, README status and publication. Agents use separate
worktrees for coding. Three subagents run at once, the session's concurrency
limit. Completed work is published incrementally on
`phase2/requalification-20261105`; the reviewed implementation will be advanced
to `master` without force to obtain exact-source hosted qualification.

## Invariants

- Preserve legitimate upstream source updates and all historical evidence.
- Every changed pin needs an explicit old/new identity, reachable public source,
  reviewed diff and provenance. Never silently bless a different dependency.
- Preserve physical-byte, Git index, URL, nested-child, LFS OID/size and negative
  checks. Missing objects, skipped cases and failed commands remain failures.
- Require fresh ordinary anonymous recursive acquisition with independent
  object stores, the complete locked LFS payloads, reproducible lock generation,
  exact implementation identity and independent review.
- This scope qualifies reproducible source acquisition. It does not qualify
  Logic Pro execution or reinstate P003/P004 acceptance.

## Evidence publication

Commands, outputs, exact commit identities, artifact hashes and review records
will be added here as observed. Scratch-only results are not acceptance evidence.
No reviewer has yet accepted this campaign.

Provenance: existing repository source, Git metadata, original acceptance
contract and public upstream commit history. No restricted implementation
material is used.

## Wave 1 observations

- The latest upstream merge changes **13 direct and one nested pin**. All 14
  old/new source diffs and commit/tree identities were inspected; the nested
  change is `src/external/metal/deps/indium`. See [the explicit source review](upstream-pin-review.json).
- The independent hosted P002 run [42150490608](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42150490608)
  failed on both Ubuntu hosts at the same lock fixture as the local reproduction.
  All 18 original raw artifact members are retained unchanged under
  [the failed-campaign history](history/c7ef7fe4/artifacts.json), with exact official ZIP and member hashes.
- Fresh source-inspection acquisition retrieved all **160 current recursive
  gitlinks** anonymously. This uses P001's raw-source inspection policy and
  therefore is not substituted for either ordinary P002 clone. The complete
  raw report is preserved in [XZ form](source-inspection-c7ef7fe4.json.xz), with
  [byte counts and hashes](source-inspection-c7ef7fe4.manifest.json).
- No lock or verifier repair has been accepted yet. The next wave implements
  explicit reviewed current-source provenance and repairs the prerequisite checks.

## Supplemental LFS availability check

A separate fresh anonymous clone of the unchanged pinned Swift repository
retrieved and materialized all **44 locked LFS payloads / 16,128,448 bytes**
with Git LFS 3.6.1. Every size, executable mode and SHA-256 passed the existing
physical verifier. [Original hydration report](diagnostic-lfs-availability.json),
[command transcript](diagnostic-lfs-availability.log) and
[scope/hash manifest](diagnostic-lfs-availability.manifest.json) preserve the
result. This isolates public payload availability; it does not replace either
complete P002 clone campaign or independent phase acceptance.

## Wave 2: reviewed dependency lock

The lock/provenance worker completed local commit `3288f796` and 110 passing
P002 tests. Integration preserves the immutable original evidence, requires
the explicitly reviewed current source archive, and updates exactly 14
commit/tree pairs among 160 recursive dependencies. All paths, parent
relationships, URLs and 44 LFS records are unchanged. Current lock SHA-256:
`2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`.
This is implementation progress; exact-commit campaigns and ordered independent
P001/P002 acceptance remain pending.

## Wave 2: P001 prerequisite integration

Worker commits `c2db2b24` and `550af5d1` plus the integrator's strict aggregate
crosscheck passed the complete **174-test P001 suite**. All 63 immutable citation
objects are preserved; all 63 separately reviewed current citations also passed
against the independent source inspection checkout. Explicit shallow historical
fetch tests prove old objects are obtained without moving current child HEADs.
The aggregate binds every citation to independent old/current owner chains and
requires the full frozen dependency graph. [Raw test output](wave2-integrated-p001-tests.log)
and [tested-file hashes](wave2-integrated-p001-tests.json) record local author
validation, not hosted qualification or phase acceptance.

## Wave 2: real Git object corruption repair

The integrity worker reproduced a false pass: a forged loose blob stored under
the expected Git object name could authorize forged CRLF worktree bytes.
Independent `git fsck --full` rejected that repository with exit 3. The reader
now verifies the canonical Git blob hash before trusting returned bytes.
Four real-object integrity tests pass for SHA-1/SHA-256, including valid CRLF
and forged-byte rejection. The campaign now regenerates from explicitly
reviewed current provenance and still requires byte-identical lock output;
all 18 focused campaign tests pass. [Original red/green evidence and reproducer](object-integrity/README.md)
retain the defect, repair and the isolated branch's known stale-lock failure.
Worker commit `cab5f8ed` is integrated with the lock and baseline repairs.
Combined complete suites and the independent third-wave review are in progress.

## Integrated candidate and third-wave review

All wave-two changes are published at
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`, now advanced to `master` without
force after verifying the previous remote head. The combined local suites
passed **174 P001 tests and 115 P002 tests**, with no skips or expected failures.
[Original transcripts and tested-code hashes](wave2-complete-tests.json)
bind these author results to the published code bytes. Three independent
third-wave reviewers are challenging provenance, predecessor continuity and
physical/campaign integrity. Fresh hosted P001/P002 workflows are requested by
the same exact push; local results and this publication do not accept either
phase. Any further production repair will require new exact-source campaigns.

Current hosted runs at the exact implementation are
[P001 42155822562](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822562)
and [P002 42155822754](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822754).
The live dashboard and unchecked P001/P002 gates distinguish these pending
current results from the preserved historical three-phase acceptance.

## Original hosted outcomes and archive

Both P001 jobs and both P002 jobs **succeeded** at exact implementation
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. The complete
[70-member original evidence archive](hosted-d58cca51/README.md) includes all
raw reports/logs and the four identical 97,657,320-byte tracked manifests,
with part-level and whole-file hashes. All four official ZIP digests match;
all 66 internal checksums and 38 command-log segments pass. Every command
exit is zero, with 174 P001 / 115 P002 distinct tests on each host.
The committed archive reader reconstructed all 70 exact raw members locally.
These producer results await independent phase acceptance.

## Wave 3 independent implementation reviews

- [Provenance/lock review](wave3-provenance-review.md): approved after native
  reconstruction of both 160-record graphs, all 320 declared URLs, every current
  lock record, all 44 LFS pointers and 110 independently executed tests.
- [P001 prerequisite review](wave3-baseline-review.md): approved after 174 P001
  and 12 provenance tests, immutable original citation comparison, exact
  63-citation identity sets and current/historical graph crosschecks.
- [Physical-integrity/campaign review](wave3-integrity-review.md): approved after independent old/new corruption reproduction, four real-object tests and all 18 campaign tests. No further production change was needed.

The first two reviewers found no additional defect and authored no production
changes. Their reviewed production bytes remain identical in the hosted
`d58cca51` candidate. Waves four and five independently inspect the original
artifacts, replay critical cases and record ordered P001 then P002 acceptance.

## Published archive readback

Evidence commit `44b20845cbbe9a4e1bb951c9fb1da4cbc68b309a` contains the complete
raw artifact archive. A brand-new anonymous Git object store fetched that exact
commit from the public repository, without object alternates or an existing
reference cache. Its tree matched `7769b8ecc47a7d2f70f320f2759543979982bb45`.
The reader reconstructed every raw member from those fetched bytes, then a
separate comparison matched all 70 members against the original downloaded
artifact metadata. [Readback result](hosted-d58cca51/archive-remote-readback.json).
All three third-wave implementation reviews are approved. The fourth-wave
P001, clone A and clone B/LFS reviewers are completing independent artifact
and critical-case review before the fifth-wave final acceptance checks.
