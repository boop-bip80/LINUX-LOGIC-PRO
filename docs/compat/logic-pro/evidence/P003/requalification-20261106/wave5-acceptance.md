# P003 Wave 5 final independent acceptance

**Decision: ACCEPTED — G1, G2, G3 and G4 PASS for the exact implementation below.**

**Reviewer:** /root/wave5_acceptance, independent non-author of the production changes, workflow, guest probes, producer and installed-package reviewer.  
**Decision time:** 2026-11-06T08:33:06.074064Z.  
**Tested implementation:** 4622a9396c5c9fbe0014bdf6a2f695dcc491233c.  
**Implementation tree:** 9db3623bd2c81d18b17b29c921b1d6212ca1339d.  
**Original hosted campaign:** [run 42180484781](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42180484781), attempt 1.  
**Stable signed decision:** [acceptance.json](wave5-acceptance/acceptance.json).

This accepts the original P003 synthetic x86_64 build/install/runtime scope. **P004 remains NOT PASSED. Logic Pro compatibility and broader framework/API/audio completeness are not accepted.** The coordinator can now reconcile the live phase surfaces to this dated decision and publish the evidence. Later documentation commits do not create a new implementation verdict.

The [original PENDING preparation checkpoint](wave5-acceptance/preparation-20261106T074518Z.md) is preserved byte-for-byte, SHA-256 c47332cd5d413a462899848a9a7deb02c305c465ed4252f9e2f2ab7bd7e3c731. I wrote only this report and wave5-acceptance/, made no production/README/ledger/peer changes, and made no commit or push.

## Original gate decisions

| Original gate | Verdict | Decisive current evidence |
| --- | --- | --- |
| G1: two clean builds and installs with identical source/toolchain manifests; output nondeterminism enumerated | **PASS** | Both complete fresh builds, source/input continuity, 11,947-entry installations and exact reinstalls are independently approved. All 137 changed installed files and 4,418 changed bytes are classified, with zero unknown bytes; intermediate-linker limits are explicitly retained. |
| G2: intended installed framework implementations rather than competing developer stubs | **PASS** | Seven actual source/build owners, Mach-O IDs, public/current aliases, 70 direct edges per host, all 21 native wrapper bridges, actual packaged ELF bytes and five original live loaded-path sets agree. |
| G3: installed Mach-O computation, Foundation operation and GUI event round trip with asserted outputs | **PASS** | This reviewer independently recomputed all 50 cases, nonce/FNV/object/transaction outputs, typed negatives, external click/type/Return, and raw XWD/PNG pixels. A meaningful rehashed behavioral corruption fails both independent and committed validators. |
| G4: clean uninstall/reinstall without dependency on the prior installation | **PASS** | Both hosts remove all 11,947 entries and use fresh ownership/runtime state; complete inventories remain equal. A separate source/build-free host installs the exact archived package and passes all ten cases and process/namespace teardown. |

These conclusions follow after all five distinct final peer reviews completed. The [final evidence closure](wave5-acceptance/final-evidence-closure.json) rehashes **66 referenced files**, verifies exact candidate/run identities, binds the peer reports and their supporting receipts, and confirms no unclosed current package discrepancy. An automated comparison status alone grants no acceptance.

| Distinct non-author | Completed review |
| --- | --- |
| /root/wave4_build | [Exact source, frozen toolchain, two full builds and per-host lifecycle](wave4-build/final-paired-builds.json) |
| /root/wave4_package | [G1/G2 and package lifecycle, dated 08:24:50 UTC](wave4-package/final-4622a939/final-verdict.json) |
| /root/wave4_runtime | [Current G3/G4 raw runtime and lifecycle](wave4-runtime/final-462/summary.json) |
| /root/wave5_source | [Final source, critical repair and predecessor continuity](wave5-source/current-source-review.json) |
| /root/wave5_package | [Independent package and normalization challenge, dated 08:24:55 UTC](wave5-package/final-review-receipt.json) |

## Exact originals and independent method

I read AGENTS.md, the README global contract and original P003 gates, the critical producer/comparator/independent-reviewer code, the guest Foundation/GUI/image probes, and the package comparison method. I independently examined original hosted evidence; **I did not run another installed guest locally**. Superseded b6 and historical 89c6 runtime artifacts supply no current gate result.

| Original artifact | Artifact ID | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| Build A ZIP | 13485932962 | 87,409,741 | 27b4a147ff1993bc6756172767cb4d60a8d4e437d5f9d85effe039571d5aa038 |
| Build B ZIP | 13486009301 | 87,410,244 | a7c394d71cc4d83857c0dd2988291c0b9e4bf31cb1555785c2e71dfcd6387759 |
| Independent runtime ZIP | 13486318290 | 36,170 | c77fdb0085e892cd39ea30b36c2e5e352a87f3f17e0d05234b5395b8c32a46a9 |
| Comparison ZIP | 13486224676 | 35,804 | 92fac49f42ffc2e03d267cef76f4bdc2841803b0a429c38b9f216475e8012915 |

My [separate stdlib-only auditor](wave5-acceptance/audit_originals.py) imports no producer or peer checker. Its [complete result](wave5-acceptance/original-runtime-audit.json) records all four full ZIP hashes/sizes, **967 member CRCs and exact extracted byte comparisons**, and the source/run binding against supplied original API metadata. That metadata hashes to d04738e9f5a6b0eaddcae8ebab30d88b2c8cec89fa67b41a7cb9a4484fd7b147 and identifies all six successful jobs. The separately verified corrected fixture ZIP has four CRC-valid members and **174/115/201 plain-OK tests**; its digest is 155fcbc2432969eca8248a4f8166c1d55c2e584a95dce3650f8793bd77cf00ed. No skipped/substituted outcome supports this decision.

## Independent runtime recomputation

All **five actual campaigns, ten required cases each**, pass the separate auditor. It checks 75 main command records plus four independent replay search/capture records and bound raw streams. No-argument Mach-O/Foundation/GUI cases and the 65-byte Mach-O challenge reject with exit 64 and their typed error; the 64-byte boundary computes correctly.

| Campaign | Fresh challenge | Independently calculated FNV-1a/32 |
| --- | --- | --- |
| A initial install | e8c97e3cfebf2908 | 5e3ab9f6 |
| A fresh reinstall | 7b8a7639a7762a62 | 15d50d12 |
| B initial install | b04fa23a2b787356 | a8f50958 |
| B fresh reinstall | fec34391e9d92379 | 770ea7cf |
| Independent archive install | 19449b3bb9e3e094 | 46799d1c |

The fixed known results independently calculate to 4f9f2cab for hello, bf9cf968 for foobar, and d96f0f85 for 64 a bytes. Each original Foundation output has sorted alpha|beta|gamma, count 3, answer 42, bytes 007fff, missing-key nil and live transaction deltas **1|2|1|0**. The inspected actual guest source calls xpc and vproc begin/end functions, observes the live transaction counter around those calls, and prints success only after those counter transitions and object assertions hold.

Each GUI execution has the actual window/focus target, external pointer movement, one XTest click, all 16 challenge characters, external Return and the exact nonce-bound guest acknowledgement. All seven canonical framework image paths occur once in each raw log. The guest source requires progressive challenge receipt, readiness, redraw and acknowledgement. Its rendered=2 receipt represents the enforced **minimum of two draws**; it is not exact draw-count instrumentation.

I independently decoded all ten raw XWD headers and complete rasters. Every original title binds its campaign nonce to the WAIT or READY state. Each image is 400 × 262. All **3,144,000 RGB bytes** equal the separately decoded PNG rasters, with PNG CRC checks; **500 patch pixels** show red/blue before input and green/yellow after input, with maximum observed channel error zero.

### Rehashed behavioral rejection

The [separate challenge helper](wave5-acceptance/challenge_transaction.py) first confirms both unchanged controls pass. It then changes the independent runtime's final transaction delta from **0 to 1**, representing an unreleased transaction, while retaining PASS labels and all ten cases. Both raw-file hash/length references, including the evidence inventory, are recomputed.

Byte binding passes, but both the independent auditor and exact committed comparator reject the incorrect transaction behavior. The [receipt](wave5-acceptance/rehashed-transaction-challenge.json) retains exact code/evidence hashes and the semantic failure reasons. Altered stdout/report are under wave5-acceptance/transaction-corruption/. Temporary complete copies were removed; all 48 original replay files and all four original ZIPs were rehashed unchanged.

## Build, package, framework and lifecycle findings

Both original hosts retain all 16,594 build steps, 15,399 compile commands and identical frozen source/toolchain/configuration identities, apart from the explicitly documented host observation fields. Both original source scans bind 160 recursive pins, 161 repositories, 44 LFS payloads and 293,755 physical blobs with no dirty/conflicted/uninitialized/mismatched repository. The independent source/build reviews authenticate these original measurements; I independently confirm the exact candidate, clean before/after status and critical bindings.

Each package contains **11,947 entries: 9,460 regular files, 1,366 symlinks and 1,121 directories**. Of the regular files, 9,323 match exactly and 137 differ. I inspected the bounded normalization method and [independently reconciled both current tables](wave5-acceptance/package-table-reconciliation.json) against the complete original changed-path inventories and hashes:

| Classified field | Changed fields | Changed bytes |
| --- | ---: | ---: |
| Mach-O N_OSO timestamp values | 3,485 | 4,343 |
| Exact source-bound build-time strings | 4 | 11 |
| Recomputed content-derived UUIDs | 4 | 64 |
| Unclassified | 0 | 0 |
| **Total changed bytes** | | **4,418** |

Every row has nonoverlapping exact changed spans and equal normalized digests. The distinct package reviews also inspect every actual tar entry and all non-payload tar bytes, including metadata/padding, and find no tar metadata difference. Their current negative fixture changes a non-timestamp nano STABS string byte at offset 227,680 inside a UUID-excluded region, recomputes both manifests and the complete tar/459-member ZIP, and preserves the independently calculated UUID. Integrity checks pass while the comparator rejects exactly one unclassified byte. UUID exclusions therefore do not silently excuse arbitrary installed-byte changes.

I independently read all three probe executables and seven framework binaries from both actual tar packages, checked bytes/modes against the inventories, and parsed their Mach-O headers, IDs and direct dependency records. Foundation's legitimate one-slice universal wrapper is explicitly bounded and parsed; my initial thin-file-only inspection assumption was corrected without changing the candidate. The actual three probe hashes/sizes match all corresponding initial-install, reinstall and separate-runtime reports.

The distinct final package reviews check exact owners, public/current aliases and **70 direct dependency edges per host**. AppKit/Foundation use version C; CoreGraphics/CoreText/ImageIO/QuartzCore/AudioToolbox use version A. The respective owners are Cocotron AppKit, external Foundation, Cocotron CoreGraphics/CoreText, framework ImageIO, Cocotron QuartzCore and CoreAudio AudioToolbox. The competing developer-stub target is not the selected implementation.

All four native reports, **292 commands and 584 raw logs**, agree with actual packaged ELF parsing and all 21 native wrappers. The initially failed supplemental collection assumed __cstring; exact wrapper source instead emits the host DT_SONAME in **__TEXT,__elfname**. The failed method result and source-specific correction remain preserved. Both package reviewers then independently match all actual generated names to raw host DT_SONAME, versioned x86_64 loader-cache and dlopen provenance. This is an inspection-method correction, with no product repair or waived original gate.

Both complete initial/reinstall inventories are equal within each host; all 11,947 entries are removed, the prefix is absent and four distinct ownership nonces bind fresh installs. The inspected script requires initially absent paths, checks for surviving mounts before removing the stopped first runtime's prefix/HOME/workdir, and uses a separate second runtime prefix/HOME.

I check original startup records against server identity and prefix, and independently parse the separate replay's raw /proc stat. Every campaign records successful shutdown, ended server identity, no private-namespace holders and namespace release. Namespace numbers can be reused; freshness follows owner nonce, challenge, prefix/HOME and PID/start time. This offline review does not re-query historical processes.

The fifth campaign installs the exact A package: **85,637,318 bytes**, SHA-256 a909db932897b151255388949273f3e5bc41e4e55fc8c48ae4f5e73bc89e2ad3, and manifest SHA-256 4cbbdf89bcf138ea006fb5ce9fadabfb3f0425220f2d60126c1972a8314ebf5f. Its raw mount table has no source/build tree; only two individual reviewer files are mounted from the repository. The retained runtime driver equals exact tested source, its private namespace differs from its caller's, and official metadata identifies a separate hosted job/runner.

## Ordered prerequisites, failure closure and truthfulness

I verify both previously signed decision files by hash, exact implementation and original positive gates: P001 was accepted at **04:06:14 UTC**, followed by P002 at **04:29:24 UTC**, on 2026-11-06, at d58cca513559cfef0ff9af59aa5dc3b6341bdf77. The current candidate preserves predecessor locks, recipe, classification manifest and all 149 direct gitlinks. I recompute **35 root-owned current citation records** from exact Git blobs/excerpts; the distinct final source reviewer verifies all 63 current citations across 41 files and the complete original recursive pin/tree records.

The constructor-interruption receipt defect remains explicitly recorded. The earlier runner could rethrow KeyboardInterrupt while writing a zero-case PASSED receipt, although the aggregate already rejected missing cases. The current handler records a typed failure then rethrows the same abort. The distinct source reviewer reproduced before/after at exact committed source; the new four-abort regression covers KeyboardInterrupt, SystemExit(0), SystemExit(42), GeneratorExit, exception identity/traceback and absent fabricated execution evidence. Its exact source is exercised by the corrected 201-case hosted suite; the fresh corrected runtime originals supply successful-path evidence. Superseded b6 results are not substituted.

The five-wave ledger records 15 primary assignments and the supporting UUID review. Final acceptance follows all required current original reviews, not their preparation checkpoints. The initial closure verifies tested-tree continuity through documentation HEAD 9eafc4cc8754e00008c29a56a5d373cb7d978ea2. The subsequent [published closure binding](wave5-acceptance/published-closure-binding.json) independently verifies all five published technical approvals and continuity through **7328461734c14afcdc69b95a88623452355da76f**, where all 151 changed paths are README or evidence. No production change is accepted through a documentation update. Live phase surfaces were correctly held pending this decision and are to be synchronized by the coordinator with this exact acceptance record.

### Retained raw GUI diagnostics

The five current GUI stderr streams retain these exact diagnostic messages:

- Validation layer requested but not available. Ignoring...
- _CFGetHostUUIDString: unable to determine UUID for host. Error: 78

They are neither suppressed nor described as zero stderr/warnings. The first reports an unavailable validation layer, while actual displayed pixels and external events still satisfy the required GUI assertions. The second reports a host UUID operation failure; P003's tested Foundation contract is the specified object/transaction operation, which independently passes, and this review makes no successful host-UUID claim. Neither diagnostic demonstrates failure of an original P003 gate. They remain relevant limitations for broader API work and cannot support a general framework-completeness claim. The closure binds every original stderr file and its digest.

## Material acceptance limits

- **Installed packages are not byte-identical. Whole-build byte identity is NOT PROVED.** All installed differences are classified, but intermediate source-built linker binaries were not archived. Their differing hashes and source-bound date/time banners are retained; they do not establish exhaustive intermediate-binary classification.
- The complete frozen toolchain ZIP exceeds the local retrieval limit. Exact hosted restoration, committed verifier/input binding and both original environment observations support the frozen-input conclusion. No local full-image ZIP rehash is claimed.
- External host-library bytes are not in the installed tar. Original dlopen/readelf/ldd results, identities, pinned toolchain provenance and actual packaged ELF bytes are checked; unarchived external-library bytes were not independently inspected locally.
- Framework review covers all seven selected owners, aliases and 70 direct edges, with five actual live path sets. It does not claim a separately parsed complete transitive Mach-O graph. Build-tree LC_RPATH strings are retained; all audited direct dependency names are absolute installed paths and the independent replay has no source/build mounts.
- Full physical source and process observations are original hosted measurements. Independent offline recomputation is not a new full local dependency scan or installed-runtime execution.
- This is the exact privileged disposable Linux/x86_64 synthetic baseline using the recorded frozen toolchain and private X11 display. It does not establish P004, general Logic Pro operation, complete APIs, audio behavior or other host configurations.

## Reproduction

The four review helpers operate on the supplied originals and repository Git objects. Use new output paths; do not modify original archives.

    python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-acceptance/audit_originals.py \
      --repo /path/to/MAC-OS-EMULATION --originals /path/to/run-42180484781 \
      --output /new/review/original-runtime-audit.json

    python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-acceptance/challenge_transaction.py \
      --repo /path/to/MAC-OS-EMULATION --originals /path/to/run-42180484781 \
      --output /new/review/rehashed-transaction-challenge.json

    python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-acceptance/reconcile_package_tables.py \
      --campaign /path/to/MAC-OS-EMULATION/docs/compat/logic-pro/evidence/P003/requalification-20261106 \
      --originals /path/to/run-42180484781 --output /new/review/package-table-reconciliation.json

    python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave5-acceptance/verify_closure.py \
      --repo /path/to/MAC-OS-EMULATION --originals /path/to/run-42180484781 \
      --output /new/review/final-evidence-closure.json

All four completed successfully. Their scoped machine results and reproduction inputs are bound by the final decision. The **dated independent adjudication in acceptance.json**, supported by those results and the five completed peer reviews, accepts G1–G4.
