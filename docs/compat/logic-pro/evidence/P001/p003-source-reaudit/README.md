# P001 current-source continuity after P003 CMake integration

Status: **REOPENED; exact-commit requalification pending**. P002 and P003 acceptance are blocked until the corrected P001 gate passes and receives independent review.

The original 63 citations, historical blobs/excerpts and source assertions remain binding. Five explicit re-audits now cover root and src CMakeLists.txt after the reviewed P003 additions. The verifier reconstructs the exact additions and binds the resulting blobs to the current recursive inventory; arbitrary edits still fail, even with refreshed claimed hashes.

## Observed failure and official raw evidence

Candidate `d89920b447658cfa01e9645864f2315cad4e386a` failed [P001 run 41271772655](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772655) on both hosts. The original job logs and uploaded evidence remain with that run:

| Host | Original job | Decoded job-log SHA-256 |
| --- | --- | --- |
| Ubuntu 22.04 | [124745831128](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772655/job/124745831128) | `111867de05a92a962407307a38c3302cfb962762ec4ea40db3bb08e337c02b91` |
| Ubuntu 24.04 | [124745830971](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772655/job/124745830971) | `338d0ed2fd559266fa2e549ee9f81e15c197e477005175b078812b657ab1b513` |

Both hosts passed 122 fixtures, complete recursive inventory and recovery, then failed five citations: core-runtime-owners, gui-source-owners, host-build-restrictions, python-bytecode-is-conditional, and metal-and-setcap-build-prerequisites. Their complete classifications.json bytes are identical: 38,182 bytes, SHA-256 `d8e7e5a183695f701e919c9da0888e21a2c652add81268fcac7a26f8031b13ec`; 58/63 citations verified. It is recoverable directly from each uploaded artifact or the hash-bound P001_EVIDENCE record in its job log.

Automatic approval review rejected republishing the raw CI evidence bundle into public Git history. This correction publishes code and original evidence references only; it does not claim that the raw bundle is committed here. The Actions artifacts use their recorded 90-day retention policy.

## Implementation review and requalification

On 2026-11-01, `/root/p003_independent_build_review` independently approved `/root/p003_independent_package_review`'s narrow source correction after reproducing 22 classification and 50 aggregate cases, recomputing all five real Git blob/excerpt identities, and comparing all 63 historical records unchanged. The reviewed current root/src CMake blobs are `6e5320117349ab0edead8ef0ee84ef41fd487e82` and `47269412c9a4b80a9fa212ae4a1effa74e64c558`. This is implementation review, not hosted phase acceptance.

Local complete suites pass **130 P001 and 97 P002 tests** with authentic terminal results and no skips. Their raw transcript SHA-256 values are `661c5c52ff7d42712e59c79579c291deb56764564af6094f32cb492c91161740` and `e4fd0ec4ad7af54310a883a315308ea4be418f5c097dff61a534cbb3f5949394`.

Run `.github/workflows/phase1-baseline.yml` and `.github/workflows/phase2-submodules.yml` at the correction's exact commit. Independently inspect all raw source/recovery/citation and Git/LFS/lock results. Accept P001 before P002; only then resume P003 implementation. The author cannot independently approve their own correction.
