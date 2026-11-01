# P003 evidence index

Status: **ACTIVE; not accepted**. P001 and then P002 were independently reaccepted at `b2c0d4893cace4ddbacf9f7c29503990b07491cd`; the root README records the ordered verdict. P003 resumes with the reviewed static-unwind compiler repair and mandatory precompile source/compiler checks. No Logic Pro compatibility is established by this build phase.

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

## Resumed candidate after ordered predecessor acceptance

P001 and P002 passed again at `b2c0d489` in runs 41275067092 and 41275067090, with 130/97 tests per host and complementary independent acceptance. The next candidate applies `-fno-jump-tables` privately to static libunwind C++ compilation, preserving dyld's chained fixups and all pins. Exact frozen-Clang14 CMake builds reproduce 70 offending relative-data relocations in the control and none with the helper; both native versions preserve 51 independently expected register-name results. The exact source headers match pinned Git blobs `6ec649a460b89ea8120421af3889c1e1eb8b5e77` and `61be55b6162883a84f82bce7cefec0841f583737`.

Both hosted builds must reproduce this compiler regression and the complete 63-citation current-source audit before compiling Darling. The aggregate validates their exact identities, original/current source records and raw proof hashes. Original Actions artifacts will preserve these newly generated reports and compiled proof files. The complete build/install/runtime/reinstall and independent installed-package replay still must run successfully; no phase gate is passed by this local compiler proof alone.

Integrated local verification: **136 P003 fixtures pass** (including the two real CMake unwind tests and 14 new aggregate evidence tests); the source-audit suite passes 130 fixtures. Required hosted fixture floors are 130 P001 / 97 P002 / 136 P003. These verifier results do not qualify runtime behavior.

## Attempt 2409473: both entire builds and first installs succeed; real startup fails

[P003 workflow 41276794652](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652), exact source commit `2409473d37b951a0dd44346f128edb2112de6b25`, tree `24d9386e02abc6b29a5fd18f786833ea3986e34e`, passed all 130/97/136 verifier cases and froze the exact 511-package toolchain. Both independent hosts verified unchanged recursive pins, 63 current-source citations and the exact Clang 14 libunwind control/repaired codegen proof. Each then completed **all 16,590 real compiler/linker steps**, including previously failing dyld, and installed **11,941** entries. Both passed seven-framework owner/provenance and native runtime linkage checks (4 native ELF entries; 21 required wrapped SONAMEs).

Both stopped in the first installed-runtime case, `macho-known-vector`, before a Mach-O output could be observed. Original stderr on both hosts:

```text
Setting up a new Darling prefix at /p003/runtime-first
Error connecting to shellspawn in the container (/p003/runtime-first/var/run/shellspawn.sock): No such file or directory
```

The command exited 1 after roughly 15 seconds; no timeout or stub marker was substituted. Required shutdown succeeded, released the private mount namespace and terminated its holders. No remaining computation, Foundation, GUI, uninstall/reinstall or independent installed-archive case ran. Source-built GUI/audio components and first-install metadata do **not** satisfy those gates.

| Original Actions artifact | Size (bytes) | SHA-256 |
| --- | ---: | --- |
| [Build A 13072621775](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652/artifacts/13072621775) | 1,547,432 | `bfcd243e0c0d2ca451bedf85750578f0db028ad3892a498c22c46349d0aa3b05` |
| [Build B 13071818748](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652/artifacts/13071818748) | 1,547,174 | `a5cbd625601a49604eecbc4fe3eb65e8e55fca772a9b009b1fa7e57edc5820d7` |
| [Frozen toolchain 13071716180](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652/artifacts/13071716180) | 583,830,167 | `d05be12645dd4175de80c27c42237fc6d97eda54221afca413cd291c8718f828` |

Independent reviewer `/root/p003_independent_build_review` rehashed both original build ZIPs, validated all **235** members per host and the original raw stdout/stderr, reran the 51-input compiled codegen oracle and enumerated the first-install content differences. On 2026-11-01 at 06:02:13 UTC, its verdict was **FAILED_RUNTIME_STARTUP** (not P003 acceptance). Across the two initial installs, exactly 138 regular-file SHA identities differ, comprising 37,017,680 bytes; installed binary bytes and their classification are required for nondeterminism acceptance. The failed bundles omitted the package tar, so the differences cannot yet be explained from those artifacts.

The separate source/dependency requalification is accepted at this exact candidate, in order: [P001 41276794767](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794767) passed 130 fixtures, 63 citations and all 161 Git trees per host; independent P001 verdict **ACCEPTED** at 05:30:32 UTC. [P002 41276794763](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794763) passed 97 fixtures, all 160 unchanged pins, 44 LFS objects and the byte-identical lock; independent P002 verdict **PASSED_AFTER_P001** at 05:31:01 UTC, 1,009 checks. This is **2/96 phases accepted**, never an inferred P003 pass.

The initial installation also contained a stale binfmt handler configuration: it referred to `/libexec/darling/bin/mldr` but the real executable was in `/libexec/darling/usr/libexec/darling/mldr`. The next candidate repairs all three handler paths and tests them using real CMake File-API install targets. The pinned darlingserver initially invokes mldr by its already-correct direct path; the stale binfmt file alone does not explain the socket failure.

The next candidate must capture bounded native process-tree samples during the initial startup and retain the actual installed prefix on a failed probe, without altering exit codes or suppressing any case. Local observation tests verify preservation of failures. Those **five** new cases and the **two** loader-configuration cases raise the hosted P003 fixture floor to **143**. No rejected raw evidence bundle is being republished to Git; original official Actions artifacts remain the source. All four P003 acceptance boxes remain unchecked. P004 is not started.

## Attempt 0f7f34f: full two-host installation and retained runtime crash

The [original P003 qualification run 41281586902](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41281586902) passed **130 P001 / 97 P002 / 143 P003** fixtures, froze the same 511-package Ubuntu 22.04/Clang 14 image, reproduced all 63 current-source citations and the 160 child pins/44 LFS objects, and completed **16,590/16,590** real build steps on **both** fresh hosts. Both first installations and native dependency/owner inspections passed, with identical installed path inventories of **11,941 entries**. First real Mach-O execution failed identically on both because shellspawn never created its socket. Each installed shutdown released its mount namespace. Foundation, visible GUI, reinstall and independent archive-only runtime probes were not executed.

| Frozen original Actions evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| [Build A 13074088205](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41281586902/artifacts/13074088205) | 86,691,566 | `4300110a890551c14212f38445799654938baa405082d32b06820b646640dec4` |
| [Build B 13073784053](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41281586902/artifacts/13073784053) | 86,696,687 | `599cb0376d84d219d624aa2b9ec50c25aa2e23e2b3be73fa93fa27615506b72e` |

Both archives retain the actual first installed prefix on failure. Independent review reconciled every one of its 11,941 archive entries against its complete install manifest. Exactly **138 regular files** differed between first installs; each difference was independently accounted for by debug-symbol `N_OSO` timestamps, four derived Mach-O UUIDs and four embedded build-time strings. No unclassified byte difference remains. The independent original-gate verdict is **G1 PASS, G2 static owner/dependency provenance PASS but live framework loading NOT VERIFIED, G3 FAIL, G4 NOT EXECUTED**. G1 alone does not advance P003.

[P001 at the exact `0f7f34f` source](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41281586753) passed its two fresh-host campaigns and independent review. The latest separately accepted P002 campaign precedes this source SHA; the next repair must trigger P002 on its **exact** SHA before P003 can be accepted.

## Artifact-only diagnosis: original launchd crash and exact instruction defect

The [first diagnostic replay, `bc57e881`, run 41284477835](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41284477835) restored Build A's *unchanged*, hash-bound package inside the original frozen Docker image with no source/build mount. Its [475,598-byte diagnostic artifact 13074424283](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41284477835/artifacts/13074424283), SHA-256 `cdc994391361b63a36a1f83f9c20cf5901307f5ef22529d808e56305df3d5bbd`, established that guest `launchd` PID 1 died by real Linux **SIGSEGV (11)** with wait status **139** and core bit set, while its leader had been blocked in `recvmsg`. No crash log was present and no instruction pointer was yet known. The installed shutdown remained successful; this replay was intentionally **not** acceptance.

The [second artifact-only replay, `6f2b272e`, run 41285728755](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41285728755) independently **passed all 24 diagnostic tests** on the hosted Ubuntu runner (11 real ptrace, seven synthetic state-transition, six existing file/process tests), then traced the exact unchanged package. Its [543,664-byte original diagnostic artifact 13075480656](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41285728755/artifacts/13075480656), SHA-256 `e382675ba6e060d333dea613d5c16b040a3df1ba1fb8dd228c1e2243ae5394ac`, retains the first eight fault records with raw register and memory-map evidence. The collector itself reported **COLLECTION_ERROR** after a later recurrent-fault storm exceeded its bounded fault/event limits and cleanup met transient `ESRCH`; the original installed launcher still exited 1. This error is explicitly retained, never treated as a successful observation or a P003 pass.

Critically, the **first two actual faults** occur in different guest launchd worker threads at 162–164 ms, each with `RIP=0`, `RBP=0`, a zero fake return address at `RSP`, and a valid launchd callback in `RDX` (`_kqueue_demand_loop` or `_update_thread`). Both match the exact x86_64 stack-switch sequence in the archived native `mldr` executable (SHA-256 `e1c37512cdd756609f00c14885ee5c807a78808abd228a1ae679f0a54bfa60d2`): at offset `0x4e77`, Clang has loaded the thread entry pointer into `RBP`; at `0x4e84`, it executes `xor rbp,rbp`; at `0x4e8c`, it executes `jmp rbp`, thus deterministically jumping to zero. Two distinct non-author reviewers independently verified the original binary's bytes/disassembly and signal registers. The later repeated fault lies in an error-formatting path of `libsystem_kernel.dylib`, not the primary thread-start jump.

The owner is **`src/startup/mldr/elfcalls/threads.c`**, whose unrestricted inline-assembly entry operand was clobbered before its indirect jump. The proposed narrow repair preserves the entry pointer in an explicitly clobbered scratch register before clearing `RBP`. A **new actual-source-bound native regression** compiles and executes the extracted production stack-switch assembly with the exact byte-verified frozen Clang 14 and independently with GCC, for both normal and workqueue calls, optimized and debug configurations, and deliberately forced RBP inputs. Its **16 real success executions** preserve the six argument registers, switched/aligned stack, zero frame pointer and fake return; the two original-order negative controls fail by SIGSEGV. Both discovered regression tests pass locally and increase the full P003 verifier floor to **145**. This compiler evidence is not installed-runtime acceptance.

The repair is **not accepted until full two-host clean builds, actual Mach-O/Foundation/GUI behaviors, framework loading, uninstall/reinstall, independent archive-only runtime replay, exact-source P001/P002 requalification and independent G1–G4 acceptance all pass**. P004 remains NOT STARTED; raw diagnostic archives remain in their original official Actions artifact retention rather than public Git history.
