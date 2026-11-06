# Wave 1 — P003 acceptance-contract audit

Date: 2026-11-06. Reviewer: `/root/wave1_contract`.

This inspection began at `3be66e2b3`. It covers `AGENTS.md`, the README's
global gates and P003 section, the current ordered P002 acceptance, the
historical P003 acceptance, and the P003 workflow/build/comparison drivers.
This reviewer did not run tests, change implementation, inspect CoreCrypto
source, or independently reproduce a hosted run. Hosted and local test updates
below are explicitly attributed to the coordinating agent.

## Acceptance contract

The README's existing global gates G1–G8 remain controlling. In particular,
passing fixtures alone cannot establish P003 acceptance; unavailable build or
runtime evidence is blocked evidence, and an independent reviewer must replay
critical cases before the phase becomes `PASSED`.

| Gate | Existing required evidence | Principal implementation/evidence paths |
| --- | --- | --- |
| P003-G1 | Two clean builds and installations from the same source and toolchain manifests; enumerate all nondeterministic outputs. | `.github/workflows/phase3-build.yml`, `ci/logic-pro/build-p003.sh`, `tools/compat/logic-pro/compare_p003.py` |
| P003-G2 | Intended real framework resolution, including the seven required Mach-O names, aliases, owners, dependencies, and installed live paths; no accidental devstub selection. | Build/install verification and native dependency reports collected by `build-p003.sh` |
| P003-G3 | Installed Mach-O computation, Foundation, and visible GUI assertions, including independent archive-only replay. | Installed probes, `tools/compat/logic-pro/review_package_archive.py`, `tools/compat/logic-pro/review_installed_runtime.py` |
| P003-G4 | Uninstall/reinstall in clean prefixes without stale files, with the installed assertions repeated. | Both build campaigns' first/second manifests, uninstall report, and runtime reports |

The four gates also retain the README's requirements for pinned toolchain,
Linux image and package inputs, separate kernel/privilege assumptions, intended
GUI/audio component selection, install collisions/search paths, raw logs,
reproducible fixtures, and explicit limitations. P003 does not establish P004
or native Logic Pro compatibility.

## Preserve the accepted predecessor scope

`docs/compat/logic-pro/evidence/P002/requalification-20261105/ordered-acceptance.json`
records ordered P001 then P002 acceptance for implementation
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`, tree
`957b20a38292ae2bd70c5cc90deef5ab274c73ba`:

- P001: accepted at `2026-11-06T04:06:14Z` by `/root/wave4_p001_evidence`.
- P002: accepted at `2026-11-06T04:29:24Z` by `/root/wave5_final_replay`.
- The associated source approval records 27,812 protected paths, nine frozen
  inputs, and 149 root gitlinks unchanged, with no blockers.

Those accepted records should remain intact. A change confined to P003
aggregation and its regression fixtures does not by itself invalidate the
previously accepted P001/P002 implementation. Preserve that ordered record,
document the changed paths and their scope, and retain focused predecessor
regression results. Do not alter the accepted P001 verifier, source
classification manifest, or P002 pinning merely to accommodate a P003 consumer.
If an actual predecessor requirement or protected implementation changes,
reassess the affected acceptance scope using the existing global gates.

The coordinator reports that current-master P001 and P002 hosted runs
`42163489160` and `42163489196` succeeded. These are regression evidence;
their success alone is not a replacement for the independent ordered
acceptance record.

## Verified pipeline strengths and unresolved evidence

Inspection confirms that the existing workflow already provides two separate
build jobs, a frozen toolchain image, clean build/install prefixes, repeated
runtime probes, and a separate archive-only runtime job without source/build
mounts. The build container runs with networking disabled. The comparator
checks exact source identity, toolchain/lock agreement, complete submodule
state, first/second installation manifests, uninstall success, and runtime
reports. Its successful automated result is deliberately
`READY_FOR_INDEPENDENT_REVIEW`; manual independent approval and classification
of differing outputs remain required.

The historical acceptance in
`docs/compat/logic-pro/evidence/P003/acceptance-89c6c9d.json` is scoped to
`89c6c9d85aba6ed1662035e6366298c92ef9c970`, not the current implementation.
It records five installed runtime campaigns, six original Actions ZIPs, and
138 differing installed files whose differences were classified. It explicitly
does not claim byte-identical output. Preserve this history without using its
old source identity, logs, or independent signoffs as current acceptance.

At this review's baseline, the remaining current acceptance evidence was:

1. A complete fresh P003 campaign at the implementation revision being judged,
   including both builds, both install/reinstall cycles, and archive-only replay.
2. Review and classification of every differing output from those fresh builds.
3. Retention and an index of the original current-run archives and their hashes,
   sufficient for an independent reviewer to retrieve and replay them.
4. A current independent review identifying the implementation revision,
   submodule pins, exercised cases, results, and verdict.

These are existing acceptance obligations, not new gates introduced by this
audit. The workflow's 90-day Actions retention makes prompt preservation of
original archives useful; the historical archive metadata is not a substitute
for the fresh archives.

## Immediate repair and next-wave handoff

The coordinator reports that exact-master P003 run `42163489140` failed in
fixtures with 20 failures and one error among 151 cases, including rejection of
the current `host-build-restrictions` source-audit form. The coordinator then
published repair `8a222c7d5e11fbd2c3ece79c53d60c1be545d0a0` and reported local
P001/P002/P003 suites passing at 174/115/155 cases. That repair addressed the
older P004 classification form; the coordinator subsequently identified that
the real producer also supplies per-row `current_source` and top-level
`current_source_anchor`, which the aggregate and its synthetic fixture omit.
This reviewer has not independently verified those execution results or the
newly identified producer fields.

Wave 2 should independently compare the real current P001 producer output
with the P003 aggregate, repair the P003 consumer and representative fixtures,
and retain meaningful negative cases for malformed or mismatched provenance.
Keep the accepted predecessor producer and manifest unchanged. The existing
focused suites live under `tests/compat/logic-pro/baseline`,
`tests/compat/logic-pro/submodules`, and `tests/compat/logic-pro/build`; use the
workflow's transcript validator and applicable test floors when recording
results. Then advance through the existing full hosted P003 campaign and
independent review requirements.

The coordinator also reports that README checkpoint `e0ba71a` now marks P003
active, clears current acceptance checkboxes, and labels preserved historical
acceptance. This addresses the initial documentation ambiguity identified in
this inspection. No additional implementation defect was verified by this
contract audit, and no phase-passing verdict is made here.
