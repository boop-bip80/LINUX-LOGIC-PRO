# P003 evidence index

Status: **ACTIVE; not accepted**. The binding gate is the P003 section of the root README. P001/P002 passed first; no Logic Pro compatibility is established by this build phase.

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
