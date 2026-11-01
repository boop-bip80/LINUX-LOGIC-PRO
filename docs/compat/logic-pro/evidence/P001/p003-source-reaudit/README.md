# P001 current-source continuity after P003 CMake integration

Status: **PASSED at `b2c0d4893cace4ddbacf9f7c29503990b07491cd`**, independently accepted before P002 on 2026-11-01. The failed candidate and original evidence references below remain historical records.

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

## Exact-commit hosted and independent acceptance

[P001 run 41275067092](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067092) passed both Ubuntu hosts: 130 tests, all 63 citations, 755 license candidates, 293,577 tracked entries, 160 gitlinks and 161 repositories. Current classifications SHA-256: `0d6b44d4e6ca0db596ec34acda355bffe5b08661fc112e08a8ad0f1a5e399b31`. All four full tracked manifests match: `dc8e9ba09cad0563604cbb37bebee5631309c12dd4ca0d7ffd1e18093f48603d`, 97,629,682 bytes.

| Original artifact | Bytes | ZIP SHA-256 |
| --- | ---: | --- |
| [Ubuntu 22.04 / 13070977660](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067092/artifacts/13070977660) | 22183912 | `6b5f49df54d2967e4c9a013c4c071fffed2edfc65b451f47750d4a772d3eff22` |
| [Ubuntu 24.04 / 13070442627](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067092/artifacts/13070442627) | 22185200 | `088d468b54ec31a55897fff3300d72d13b3cbdde03b446e972b7194a6f09ec3e` |

Reviewer `/root/p003_independent_build_review` accepted P001 G1–G4 at **05:08:55.615852 UTC**, after replaying 130 fixtures, validating all original ZIP/member hashes, independently reconstructing every repository's Git tree from the complete manifests, checking all historical/current citations and rehashing 54,250 actual restored file/symlink blobs in separate historical object stores. No findings remain. Review SHA-256 `6548bf8a4baac5eaa699639cf1fc74cd0b74586e03481991af3ce74621f18784`; the source-audit author and accepting reviewer are distinct. P002's separate reviewer accepted that successor at 05:11:26.854450 UTC. See the root README for the ordered successor record.

To reproduce, use a clean full-history recursive checkout of the exact SHA, run the baseline unittest suite, and run `run_baseline.py` with the documented recursive acquisition report. The two original Actions archives retain complete manifests, six command records, raw fixture/recovery/citation logs and all 15 checksummed report members. They use 90-day retention; this acceptance does not claim permanent republication of the raw bundles.
