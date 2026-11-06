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
