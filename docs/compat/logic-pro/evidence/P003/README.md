# P003 evidence index

Status: **BLOCKED on current P001/P002 requalification; not accepted**. The binding gate is the P003 section of the root README. Historical P001/P002 acceptance is preserved; the current CMake source-citation regression must be requalified first. No Logic Pro compatibility is established by this build phase.

The campaign starts from `03e2880ba319d4b2b165c162cef4bffedb89d586` with unchanged recursive dependency pins. The workflow records the exact implementation it actually tests; this starting revision is not a claim that new code was tested there.

## Reproduce

Run `.github/workflows/phase3-build.yml` on the exact candidate commit. It freezes one Ubuntu 22.04/Clang 14 toolchain and passes the same hash-verified image archive to two independent clean hosted builds. The observed toolchain lock must be committed after review. Rebuilding from that lock enforces the fixed base digest, snapshot, exact package versions and tool bytes.

The container recipe and `ci/logic-pro/build-p003.sh` record all compiler/build commands. Runtime privileges allow Darling to create its mount/PID/IPC/UTS namespaces only within a disposable hosted container. Each campaign installs to `/opt/darling-p003`, probes a fresh Darwin prefix, removes the verified installation and old prefix, then reinstalls and probes a second fresh prefix.

## Required artifacts

- Frozen `toolchain.lock.json`, acquisition logs and hash-bound image archive.
- `build-summary.json`, verified P002 source lock, recursive heads and clean initial source status.
- `configure.log`, `build.log`, CMake cache/compile commands and source-built Mach-O linker identity.
- First/second install logs and manifests, seven real-framework provenance records and full install-tree hashes.
- Ownership-checked `uninstall.json` proving the isolated installation absent.
- Four complete runtime campaigns across both clean builds: exact command outputs and exits, binary hashes, unpredictable challenges, before/after XWD and PNG captures, pixel assertions, all ten required cases and shutdown evidence.
- Cross-build comparison with identical inputs and every output difference enumerated.
- Dated independent review identifying the actual tested commit and submodule pins, reproduced critical cases and explicit verdict for all four original gates.

No artifact has yet been accepted. A green verifier fixture suite or legacy package build does not qualify this phase. Full evidence and review records will be linked here as they become available; failures must remain recorded.

## Attempt history

- [0f69cb5a / run 41269126730](attempt-0f69cb5/result.json): hosted 122/97/82 fixture checks passed; image acquisition failed on missing bootstrap CA trust. Builds/runtime were skipped, not passed. Original raw job log and SHA-256 retained.

- [354f7687 / run 41269315882](attempt-354f768/result.json): authenticated toolchain freeze and 122/97/82 fixtures passed; both hosts rejected tool identity before compilation. Actual 511-package lock, full partial build reports, hashes and independent freeze review preserved. Next verifier captures actual host fields and keeps all static tool identity strict.

## Attempt 00a8df3: real Release compilation failure

[Run 41270430492](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41270430492) passed fixtures (122/97/84), rebuilt the exact frozen environment, and passed all source/toolchain checks on both hosts. Both then failed the same objc4 debug-definition consistency assertion during actual Release compilation. No install/runtime gate passed.

[attempt-00a8df3/result.json](attempt-00a8df3/result.json) records the exact failure, artifact identities and every original ZIP member hash. The complete unmodified [build A ZIP](attempt-00a8df3/build-a.zip) and [build B ZIP](attempt-00a8df3/build-b.zip) preserve configuration, compile commands, full partial build logs, observed toolchain and recursive-source verification. The [independent host comparison](attempt-00a8df3/independent-host-observation-review.json) confirms the only cross-host variation is dsymutil's CPU banner. [toolchain-job.txt.gz](attempt-00a8df3/toolchain-job.txt.gz) losslessly preserves the successful acquisition log; its decoded hash is in the result.

Reproduce inspection with `unzip build-a.zip -d a`, `unzip build-b.zip -d b`, and `gzip -dc toolchain-job.txt.gz`. Do not count these failed builds as installed-runtime evidence. The next candidate preserves the objc runtime assertion, corrects its CMake definition, enables placeholder diagnostics and requires independent execution of the installed package without source/build mounts.

## Attempt d89920b: objc compilation repaired; dyld linkage fails

[Run 41271772667](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772667) passed 122/97/120 fixtures and the exact frozen environment/source checks. Both independent builds compiled the previously failing Objective-C runtime with the correct Release definition, then failed linking dyld on a Clang-generated 32-bit relative libunwind lookup table unsupported by the pinned ld64 in its required chained-fixup image. No installation or runtime scenario executed.

| Original hosted artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [Build A, artifact 13069334278](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772667/artifacts/13069334278) | 736393 | `3ae6eb3c39ee3449bcf75e27c1509809e28439409113cad871a643f142773440` |
| [Build B, artifact 13070510118](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772667/artifacts/13070510118) | 736146 | `2d239a85022884b2ebb3d9a4eacc4a09aa8118b7a9143b326174a4fd1ae0f12d` |

The independent build reviewer downloaded both exact ZIPs, verified API SHA-256 and all 13 CRC members per host, and inspected the actual generated compile commands, full build logs and raw frozen-environment observations without importing production verification code. All 511 package and 13 tool observations match the shared lock, SHA-256 `ebacf5c3f85446fedd44191590a361bc5b3bdfd18dd642b7e858ce9367f3eb83`. Every Objective-C runtime command contains exactly `OBJC_IS_DEBUG_BUILD=0` with `NDEBUG`; the failure moved to the real dyld link.

Reviewed unchanged pins: libunwind `a91da1a0e262e04eb601152a84228ff733e48422`, dyld `63f667cf06d7ed59553adebb0c8d70a117135ac9`, cctools-port `d9456c221e1f462e17c0b3297748bc089d5a861e`. Reviewer `/root/p003_independent_build_review`, 2026-11-01, verdict **P003 FAILED COMPILE**. Automatic review rejected adding the new raw bundle to public Git history; the original uploaded Actions artifacts remain the evidence source under their 90-day retention policy.

The separate P001 run rejected five stale current-source CMake identities. See [the reopened predecessor audit](../P001/p003-source-reaudit/README.md). Restore P001/P002 acceptance first, then resume the actual linker repair; P004 is not started.
