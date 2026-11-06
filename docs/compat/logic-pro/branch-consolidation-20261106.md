# Branch consolidation — November 6, 2026

## Result and preserved history

The repository's canonical branch is `main`. The former default was the older
`audit/p001-p002-qualification` snapshot. Pull requests #1–#9 consolidate the newer
accepted implementation, original development histories, and independent ZIP
review tools. Every one of the 16 pre-existing branch heads was proved to be an
ancestor of `main` before its branch reference was deleted.

The cleanup verification revision is
`eaa72179a2774e16fb6a5281ed83dec99de321d0`, tracked tree
`772d832254f119af19e561bf74750235d889adbe`. This tree equals the prior `master`
implementation at `984cbcf46a83dc794bc99deea9bfa837a9682043` plus only the three
`review/original_zips` files. The subsequent maintenance changes adapt active CI
and tools to the current repository and branch; they do not rewrite historical
acceptance evidence or remove original commits.

| Previous branch | Original head preserved in history | Integration PR |
| --- | --- | --- |
| `audit/p001-p002-qualification` | `c64792c9b4bc856827e8f424e3247872c811422a` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `fix/p004-fixture-diagnostics-20261104` | `44a6353528624c862a0cf7d95fa2411d28129cb1` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `master` | `984cbcf46a83dc794bc99deea9bfa837a9682043` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `p003-five-wave-requalification-20261106` | `67530b7ea1a5fea36b3c33bf1f414599404c07ea` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `p004-ci-workflow` | `7aad971c9624c2cdec87a4b3d725c5206718298e` | [#5](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/5) |
| `p004-compatibility-integration-20261103` | `d8a812bf86d7d0ff512028bf80f1c813b0ac0fb4` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `p004-evidence-provenance` | `51d692d8e7244c0d8e0a70f9a6d7ba50766f10db` | [#2](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/2) |
| `p004-fault-harness` | `a29418004539ea64b91d38e20479468cd9f5464f` | [#6](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/6) |
| `p004-legacy-concurrency-guard` | `929b36e3939f013964f374fae0f1e6f2666e9e66` | [#3](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/3) |
| `p004-strict-gate-engine` | `18dc05f9e9acde1093a709b05cf7c0b3b0fc3ebf` | [#7](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/7) |
| `p004/exact-qualifier-trigger-hardening-20261103` | `ef6ac628ae532f48a24d6aab374832e1adae8d90` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `p004/predecessor-cmake-reaudit` | `5c5a119d89a7014a582791734337b030fa7c3d28` | [#8](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/8) |
| `p004/semantic-fault-oracle-20261103` | `44a6353528624c862a0cf7d95fa2411d28129cb1` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `p004/source-equivalence-proof` | `965aa0bfdbf8d4ff6843056f8758abc00e7c8f50` | [#9](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/9) |
| `phase2/requalification-20261105` | `3be66e2b343b77c34d023c20bd7822dc055c657f` | [#1](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/1) |
| `review/p004-original-zips-ef6ac` | `fbc291d9a53a774dfc483f119dd19fe9b7a0cf3a` | [#4](https://github.com/boop-bip80/LINUX-LOGIC-PRO/pull/4) |

The original changes from the five conflicting P004 branches had already been
integrated at `d8a812bf86d7d0ff512028bf80f1c813b0ac0fb4` and subsequently hardened.
The CI receipt's earlier incorrect return annotation was already corrected.
Conflict resolution retained the newer current versions. For each resolution,
`git diff --cached --exit-code HEAD` and tracked-tree identity proved that it
introduced no content rollback. Both the current main parent and the original
branch parent were retained in each resolution commit.

## Phase status

| Phase | Recorded result | Qualified revision / evidence |
| --- | --- | --- |
| P001 | PASSED | `d58cca51`; [ordered independent acceptance](evidence/P002/requalification-20261105/wave4-p001/acceptance.json) |
| P002 | PASSED | `d58cca51`; [final independent acceptance](evidence/P002/requalification-20261105/wave5-replay/acceptance.json) |
| P003 | PASSED | `78454aa22fac577295b66342ac2c8a766358bc02`; [five-wave acceptance](evidence/P003/five-wave-hardening-20261106.md) |
| P004 | NOT PASSED | Fresh exact-source hosted qualification and independent acceptance remain required. |

These are retained scoped acceptance decisions at the recorded revisions.
The consolidation is not a new full build/runtime qualification and does not
establish working Logic Pro, broad macOS compatibility, or production audio use.
Original `MAC-OS-EMULATION` run URLs, hashes, and dated failure reports remain
unchanged because they identify where the evidence was produced.

## Integration validation

- Git ancestry checks proved all 16 old branch tips are retained before deletion.
- PRs #2, #3 and #5–#9 preserve the current tracked tree exactly.
- The newly integrated independent ZIP verifier passed all 43 existing tests.
- The existing P004 harness reproduced one failure out of 86 tests: the empty-test
  negative case expected obsolete error wording. The validator itself rejected
  the input with `missing/insufficient actual discovered or executed assertions`.
  After updating that exact expectation, all 86 tests passed. No production
  rejection condition was loosened.
- Eight workflow push filters move from `master` to `main`; the P003 workflow's
  build-fixture minimum is restored to the recorded 224-test acceptance floor.

## Final maintenance and validation

The final maintenance PR updates the canonical repository in current source
inventory, fresh-clone campaigns, the P004 contract, and original-ZIP auditing.
Only the current lock's `root_origin` changes: all 160 dependency entries, 44 LFS
objects, pins, URLs, hashes and provenance remain identical. Explicit historical
lock generation and original-ZIP replay preserve the old repository scope.

P004 and ZIP run validators still require the exact repository, full source SHA,
workflow, push event, expected branch, jobs and original artifact bytes. New
current runs require `main`; historical replay is explicit. Source-free runtime
review rejects checkout mounts under either repository name. Diagnostic workflows
fetch their pinned historical run IDs from the original artifact repository while
binding the diagnostic checkout to this repository.

| Check actually executed | Result |
| --- | --- |
| P001 baseline suite after origin migration | 174 passed, no skips |
| P002 dependency suite after origin migration | 116 passed, no skips |
| Integrated P004 harness and branch-identity tests | 94 passed |
| Original-ZIP verifier and migration tests | 51 passed |
| Focused P003 independent comparison tests | 25 passed |
| Focused P003 runtime-boundary tests | 18 passed |
| Modified Python syntax and workflow YAML/main filters | Passed |
| Dependency lock comparison and unchanged `src` / gitlinks | Passed |
| Full local P003 suite on the accepted pre-migration implementation | 222 passed; one class setup error because Clang is unavailable; two compiler-dependent tests did not execute |
| Diagnostic suite | 14 passed; 10 native tracer tests failed before attachment because this environment denies `ptrace` with `EPERM` |

The native tracer implementation and its tests were not modified. The Clang and
ptrace limitations are retained as incomplete local validation, not converted to
skips or passes. No full Docker build, installed Darling runtime campaign, or new
hosted exact-main phase acceptance is claimed by this maintenance work.

Reproduction commands use `python3 -B -m unittest discover -s <suite> -p
'test_*.py' -v`, with suites under `tests/compat/logic-pro/{baseline,submodules,
harness,diagnostics}` and `review/original_zips`. The two focused P003 commands
select `test_independent_review.py` and `test_runtime_review.py` in the `build`
suite. The original negative test was reproduced failing before its stale text
expectation was corrected; production rejection logic was unchanged.

Three separate agents reviewed phase acceptance, branch integration, and live
repository references. The final root diff received an independent bounded
review with no concrete blocker. These reviews concern this consolidation and
are not substitutes for the plan's later hosted P004 acceptance.

## Follow-up: historic P003 diagnostic CI after the repository migration

The automatic P003 GUI/X11 replay at main commit `4cb86d39` failed on
[run 42286672164](https://github.com/boop-bip80/LINUX-LOGIC-PRO/actions/runs/42286672164)
before executing a probe: `actions/download-artifact` could not find the pinned
original build from historic run `41286874621`. The original
`boop-bip80/MAC-OS-EMULATION` repository API returns 404, and querying that
historic run through `LINUX-LOGIC-PRO` also returns 404. The retained original
package and frozen toolchain cannot currently be re-downloaded from either path.

The startup diagnostic replay likewise depends on original run `41281586902`.
Both workflows now execute their available, meaningful source-level diagnostic
fixtures on pull requests and pushes. Installed-package and frozen-toolchain
replays require explicit `workflow_dispatch`, retaining their original run IDs,
artifact names, SHA-256 checks and fail-closed behavior. A green fixture run
does **not** mean the inaccessible historical binary replay was performed,
and neither replay is used as P003 phase acceptance. Restoring the original
immutable artifacts is required before claiming those replays were executed.
