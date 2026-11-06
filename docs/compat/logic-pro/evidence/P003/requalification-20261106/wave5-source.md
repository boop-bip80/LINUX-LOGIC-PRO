# P003 Wave 5 independent source review — bounded checkpoint

**Verdict: source continuity and bounded critical checks verified; the newly discovered interruption-receipt defect is repaired and independently approved by exact code hash. Full current-source P003 G1–G4 acceptance remains PENDING.**

Reviewer: `/root/wave5_source`, a distinct non-author of the production changes. Review date: **2026-11-06 UTC**. The original audited implementation is `b6f4d9bf04dd4a15a1b349845f962295ff350b7d`, tree `202dbdc59c0bd9df10804b9e3a75674508eab75d`, associated with run `42177445982`. The correction is now published at **`4622a9396c5c9fbe0014bdf6a2f695dcc491233c`**, tree **`9db3623bd2c81d18b17b29c921b1d6212ca1339d`**. I independently verified its three reviewed file hashes and complete scoped patch match the published Git objects, then repeated the interruption control at that exact commit. Fresh complete qualification remains required.

I read `AGENTS.md`, the global phase contract, the P003 objectives and original gates, the ordered predecessor decisions, and the actual scoped production/workflow/test diffs. I did not author or modify production, workflow, tests, locks, dependencies, README, or another reviewer's report. Only this report and `wave5-source/` were written. No commit or push was made. Sources were the repository's exact Git objects, its supplied original artifact bytes and public pinned build-configuration metadata. No restricted Apple material or proprietary binary internals were used.

## Exact source and predecessor continuity

The independent [source audit](wave5-source/source-audit.json) compares accepted `d58cca513559cfef0ff9af59aa5dc3b6341bdf77` with exact `b6f4d9bf`. It verifies **27,350 existing superproject tree entries** outside README, evidence directories, and the 13 explicit P003 change paths remain identical by Git mode/type/object identity. Those 13 changes are confined to the P003 workflow, build/Objective-C configuration, evidence/probe consumers, retained toolchain input recovery, their tests and the retained-input manifest. The complete allowed change and code-hash map is in the receipt. The [corrected commit binding](wave5-source/corrected-commit-binding.json) extends that continuity through `4622a939`: its only additional non-documentation changes are the already-scoped runner, runner tests and workflow floor; every direct gitlink remains identical. I also read the intervening README diff: it records status and evidence without changing the original phase contract.

All **149 direct gitlinks** are unchanged. The unchanged source lock continues to bind **160 recursive dependency pins and 44 LFS payloads**. All **24 root-owned cited blobs**, `.gitmodules`, classification producer/manifest, toolchain lock, Docker recipe and `AGENTS.md` preserve their predecessor identities. This is a superproject/pin-continuity check; it is not a new physical fetch/rehash of every recursive source repository. The fresh hosted source-verification records must supply that observation.

I checked both linked independent predecessor decision files against their recorded SHA-256 hashes, exact `d58cca51` implementation identity and four positive gates. P001 was accepted at **04:06:14 UTC**, then P002 at **04:29:24 UTC**, on 2026-11-06. No scoped P003 change invalidates those frozen prior-phase inputs. Their acceptance is not replaced by this review.

The source-classification consumer preserves every historical citation, root/current distinction and nested gitlink chain. Its P004-labelled historical re-audit handling is limited to the already-reviewed root CMake upstream delta and fixed identities; it does not authorize P004 advancement. Canonical JSON comparison prevents integer/boolean/float substitutions from passing through Python's loose equality.

## Independently exercised evidence and critical controls

I independently rehashed the original supplied `b6f4d9bf` fixture ZIP, checked all four member CRCs, and counted distinct named cases directly from each raw transcript. Its **11,674 bytes** have SHA-256 `c3e9124012f7b9a4ea8249022bfe8ffbd6d8e8740c381b940aca69aea0f6b085`, matching supplied artifact `13483523427`. The transcripts contain **174 / 115 / 200** unique cases and terminal plain `OK`, without skipped, expected-failure or unexpected-success substitutions. This establishes those fixture executions at `b6f4d9bf`; it cannot qualify the later abort correction.

I read both original `8a222c7d5` build ZIPs, checked their full SHA-256 values and CRCs, and used their unchanged source reports and logs as older producer/parser controls. Both actual reports retain 63 citations and 41 distinct source files and are accepted by the current consumer. I then constructed **28 independent counterexamples**, 14 for each original. Every one was rejected: missing or extra provenance, wrong root versus child commit, missing gitlink chain, booleans replaced by integers, line/count integers replaced by floats, changed historical binding, duplicate citation with unchanged total, forged top-level anchor and contradictory raw log. The original archives and extracted files were not modified. These are parser controls; neither older build is treated as current runtime acceptance.

I independently executed the following focused tests against the then-exact `b6f4d9bf` working files:

| Critical scope | Methods | Observation |
| --- | ---: | --- |
| Legacy/current Objective-C build configuration | 6 | Real CMake/C++ configure, compile and execution; mismatch and unreviewed layouts reject. |
| Complete source classifications and bound codegen proof | 26 | Exact identities, types, coverage, original/raw evidence and proof file binding remain enforced. |
| Producer/aggregate final source cleanliness | 16 | Actual shell handler rejects dirty or redirected status evidence and preserves earlier failures. |
| Retained frozen input recovery | 12 | Actual ZIP/CLI/shell controls reject corruption, changed frozen inputs, unsafe members and improper fallback. |
| Early probe failure and existing-state preservation | 7 | Expected failures remain failures; prior files/state and unexpected exception propagation are preserved. |
| **Total** | **67** | **Plain OK, zero skips, 18.319 seconds.** |

The [raw 67-test transcript](wave5-source/critical-regressions.log) is SHA-256 `609352877427e4b7de5eb283288a16c4b17efc0c1eb2f8e850924da2af4a5712`. Local Python was 3.12.14, CMake 4.4.4 and the compiled C++ contract used GCC 14.2.0. The exact frozen Clang 14 full builds remain a separate requirement.

I also inspected the actual pinned Objective-C build contract at `src/external/objc4` commit `092352cab947b410a73b5123b190df03f90c1802`. Its runtime CMake has no explicit `OBJC_IS_DEBUG_BUILD` definition; the pinned header derives that macro from its `DEBUG` mode, which depends on `NDEBUG`. [Exact file/blob hashes and observations](wave5-source/objc-current-contract.json) bind this check. The adapter preserves that header behavior and still rejects unsupported definitions; it does not weaken the runtime assertion or impose a Release guess when custom flags omit `NDEBUG`.

## Discovered reporting defect and independently reviewed repair

The independent controller-only control at exact `b6f4d9bf` injects `KeyboardInterrupt` during `Campaign` construction. The original interruption propagates, but the finalizer writes `status=PASSED`, `passed=true`, no errors, and empty cases/commands. [The retained before result](wave5-source/interruption-before.json) binds runner SHA-256 `3e778e7fe42fb2897b2f7244490008361f964d02fe17816c1729d6d69d9df541`.

**This is a misleading interrupted-initialization receipt, not a reproduced overall false P003 pass.** The interruption and absent mandatory cases/evidence prevent phase acceptance. I reported the concrete edge to the coordinator before any production change; the coordinator chose to close it in this campaign.

Root changes the unexpected-abort handler from `Exception` to `BaseException`, records the typed error, and re-raises the same abort. I read the [complete three-file diff](wave5-source/abort-fix.diff). The change neither swallows interruption/exit nor changes the successful behavior path. The new regression covers `KeyboardInterrupt`, `SystemExit(0)`, `SystemExit(42)` and `GeneratorExit`, checking exception identity and trace frame, FAILED/false evidence, empty command/case lists, null lifecycle/HOME and untouched prefix/HOME paths. The fixture floor becomes 201.

My **same independent control** now yields FAILED/false with the typed error, empty case/command records and null lifecycle/HOME while preserving the original interruption. I also independently ran the new abort method and the seven existing early-failure/collision methods: **8 methods, plain OK, zero skips**. The exact [working-tree after result](wave5-source/interruption-after-working-tree.json) and [raw 8-test transcript](wave5-source/abort-regressions.log) are retained. After publication I independently repeated the same controller at exact `4622a939`; its [committed-source result](wave5-source/interruption-after-4622a939.json) again preserves the original interruption and records FAILED/false with the same typed error and empty execution state.

| Reviewed correction | SHA-256 |
| --- | --- |
| `run_build_probes.py` | `de3be619acc733a92190c0f7e6454e1768da864feabe5d846eadf1720f0bd508` |
| `test_probes.py` | `5ba0125ccf388e9ea1e337d285a0e5272fb1cdff5411f709f91fcbba881df706` |
| `phase3-build.yml` | `d68c6f8a193d5ef3ea637f565359ad8b1b84518d2d612c38032b92154b957e47` |

**Scoped repair verdict: APPROVED at exact published `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, with all three file hashes and the complete patch matching the independently reviewed bytes.** No remaining defect was reproduced in this bounded source review. All current full-build/package/runtime gates must be completed and independently reviewed at that corrected source.

## Acceptance boundary and remaining evidence

The [machine-readable checkpoint](wave5-source/checkpoint.json), SHA-256 `2625a80dea7da48bdf2dda3ddcf0000850aeb054f25fefaf69d95679d107e981`, contains the complete evidence/hash map and explicit limitations. The initial `b6f4d9bf` build results may remain diagnostic or method evidence, but they cannot become final acceptance for changed code.

For the corrected candidate, this source review still requires both original A/B artifacts with exact ZIP identity and member fidelity; actual matching source revisions and complete recursive-pin/LFS/classification observations; clean before/after status; frozen toolchain observations and Clang 14 proof; and full configure/compile/install evidence. Package, framework, runtime and lifecycle reviewers must finish their separate original-evidence checks, including the source-free fifth campaign. The retained full image ZIP was not locally downloaded because it exceeds the connector's limit; this review makes no local full-image CRC/byte verification claim.

**All current G1–G4 phase verdicts remain pending. Remain in P003.**

## Reproduction

For the initial source audit, use a separate clean `b6f4d9bf` checkout as `--repo` and the latest documentation checkout as `--evidence-repo`; the latter supplies the later-published original ZIPs. The helper verifies the execution-file identities before importing the classification consumer. It can optionally check supplied extracted copies with `--producer-root`.

```sh
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-source/audit_source.py --repo /path/to/b6f4d9bf-checkout --evidence-repo /path/to/current-documentation-checkout --output /path/to/source-audit.json
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-source/reproduce_interruption.py --repo /path/to/repository --commit b6f4d9bf04dd4a15a1b349845f962295ff350b7d --expected-status PASSED --output /path/to/before.json
```

The first interruption command intentionally demonstrates the old incorrect receipt. The corrected-source reproduction is:

```sh
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-source/reproduce_interruption.py --repo /path/to/repository --commit 4622a9396c5c9fbe0014bdf6a2f695dcc491233c --expected-status FAILED --output /path/to/after.json
```

The retained earlier `--working-tree` control records its exact tested bytes without claiming a commit identity. None of these controller controls starts Darling or substitutes for the real runtime campaign.
