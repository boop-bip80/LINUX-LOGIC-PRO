# P003 Wave 5 final independent package and reproducibility review

**Reviewer:** `/root/wave5_package`  
**Reviewed at:** `2026-11-06T08:24:55.371418+00:00`  
**Verdict:** **APPROVED_PACKAGE_SCOPE — G1 installed-package reproducibility/classification and G2 framework/package fidelity pass for the exact source below.**

Source `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, tree `9db3623bd2c81d18b17b29c921b1d6212ca1339d`, run `42180484781`. The source tree was independently checked locally. Later documentation commits do not extend this verdict to other implementation bytes. This is a scoped nonauthor review; the final adjudicator owns whole-phase acceptance and the separate clean-build/runtime reviews.

## Final findings

All four original ZIP sizes and SHA-256 digests match the supplied official metadata. The six official jobs completed successfully at the exact source. Every original member was CRC-checked and matched byte-for-byte against its extracted sibling: **459 build A, 459 build B, 48 independent-runtime, and one comparison member**. Required-member presence, canonical paths, duplicate names, regular member types, and complete extracted inventories were checked independently of the inherited comparator. The comparison's complete two 459-member digest maps and the replay's original A archive/manifest identities agree.

Each actual tar contains **11,947 entries: 9,460 regular files, 1,366 symlinks, and 1,121 directories**. Every file size/hash, mode, type and literal symlink target agrees with its manifest. **Both complete first/reinstall manifests are present and equal within each host**, including the framework and source records; both CMake install inventories also agree. No structural archive difference or manifest mismatch remains.

The two builds have **9,323 identical regular files and 137 differing regular files**. The unchanged independent helper classifies all **4,418 changed installed bytes**:

| Classification | Fields | Changed bytes |
| --- | ---: | ---: |
| Mach-O `N_OSO` timestamp values | 3,485 | 4,343 |
| Four specifically source-bound build-time strings | 4 | 11 |
| Independently source-derived `LC_UUID` fields | 4 | 64 |
| Unclassified | 0 | 0 |

Every changed file has equal normalized bytes; every raw changed span remains recorded. No new normalization was added. The complete original comparison is [final-installed-byte-comparison.json](wave5-package/final-installed-byte-comparison.json).

Tar metadata is explicitly adjudicated: both archives have equal member order, modes, literal links, ownership, timestamps, device fields and PAX fields. UID/GID and device numbers are zero, owner/group names are empty, PAX maps are empty, and every member mtime is `1793949760`. A separate complete gzip read verified both CRCs and hashed **all decompressed bytes outside regular-file payloads**, including headers and padding; that hash is identical (`de48d846969235e890e4ff42f2ada69e11b53b119d33b3a89aefd6304ac50f17`). Thus the archive metadata result does not merely rely on the helper's narrower status. The gzip headers also agree; compressed stream byte identity is not claimed.

## Framework and native closure

An independently written Mach-O parser checked the actual archived bytes, exact install IDs, public and `Versions/Current` aliases, unique regular framework images, and all **70 direct dependency edges per build**. Exact owner CMake blobs, root/submodule commits, actual compile-command targets and implementation sentinels agree. No selected framework is supplied by a competing developer-stub target.

| Framework | Version | Exact owner | Direct dependencies | Actual compile commands |
| --- | --- | --- | ---: | ---: |
| AppKit | C | `src/external/cocotron/AppKit` | 19 | 331 |
| Foundation | C | `src/external/foundation` | 8 | 233 |
| CoreGraphics | A | `src/external/cocotron/CoreGraphics` | 7 | 40 |
| CoreText | A | `src/external/cocotron/CoreText` | 7 | 14 |
| ImageIO | A | `src/frameworks/ImageIO` | 5 | 3 |
| QuartzCore | A | `src/external/cocotron/QuartzCore` | 13 | 32 |
| AudioToolbox | A | `src/CoreAudio/AudioToolbox` | 11 | 18 |

The exact Cocotron pin is `d89d7aa029c1ca2d297372fc7f618e9b006112d0`; Foundation is `a8b5ab193a107712d0806b6f95bfa763be68e1f8`. Foundation's `Foundation_obj`/`Foundation_x86_64` distinction is preserved. All five original GUI logs report the seven canonical installed image paths, including the independently reproduced source-free runtime.

A separate ELF parser checked the four actual packaged native executables on both hosts. All **four native reports, 292 command records and 584 raw logs** were authenticated and reconstructed, including the **21 source-declared host-library resolutions per report**. Their native identities agree across both hosts and reinstalls and use the same frozen toolchain lock as the independent replay.

The concrete Wave 4 method correction was independently checked: `wrapgen` stores the resolved host `DT_SONAME` in **`__TEXT,__elfname`**. For all 21 actual wrappers on both hosts, section bounds, bytes, NUL termination, wrapper install ID, original host `readelf` SONAME, original versioned x86_64 loader-cache entry and default `dlopen` provenance agree. The CMake lookup name is retained separately. For example, the actual FreeType wrapper contains `libfreetype.so.6` at offset 24,374, with section size 17. No production change or relaxed requirement was needed.

## Independent normalization challenge

The reviewer independently decoded nano and recomputed both original UUIDs without the comparison helper's parser or UUID routine. Both match. A one-second `N_OSO` timestamp positive control is classified, and removing nano's exact source binding rejects the real A/B difference.

The meaningful negative changes **one non-timestamp STABS string byte at nano offset 227,680**. Its independently recomputed UUID remains valid because that string lies inside a linker UUID exclusion. The experiment reconstructs the **complete original A tar and all 459 original ZIP members**, updating nano's content hash in **both** complete install manifests and updating archive checksums. All ZIP CRCs, selected original-member bindings, tar/manifest contents, reinstall comparisons and source/structure checks pass. Nevertheless, the installed-byte comparator exits **1** for **exactly one unclassified byte**, with unequal normalized bytes and no parser error. This demonstrates rejection beyond stale-checksum detection and distinguishes UUID exclusions from permitted byte normalization. Original evidence was untouched; temporary derived archives were removed.

## Explicit limits and Wave 4 reconciliation

Both original linker-version commands exited zero. Their reported hashes differ; the version text differs only at the source-bound `BUILD` date/time (`07:31:45` versus `07:29:13 Nov 6 2026`). The exact pinned linker source explains that banner. **The intermediate linker executable bytes are absent from the original ZIPs: exhaustive linker-byte classification and whole-build byte identity remain NOT PROVED.** This review approves the installed-package classification and records that separate limitation.

External host-library bytes are outside the installed tar. Their original command results, paths, sizes, hashes, source declarations and pinned-toolchain provenance were authenticated; this is not an independent byte inspection of unarchived host libraries. Each framework retains a build-tree `LC_RPATH` string; all 70 audited direct names are absolute, resolve inside the package, and the five actual live campaigns include source-free replay. This review does not claim a separate recursively parsed transitive Mach-O graph or general framework/API completeness.

The final Wave 4 comparison and corrected metadata receipt were read and reconciled against actual Wave 5 results. All 137 detailed byte reviews, source bindings, archive/manifest records, metadata and linker classifications agree. All **14 framework observations, 84 wrapper/native bridge observations and five live path sets** agree. Wave 4's metadata report SHA-256 is `cc85f551f43f3267a83b45d2b15f7cab30af6513894e733f51a04f790ae3ae03`; its successful receipt records exit zero. The preserved failed `__cstring` assumption is a reviewer-method correction, not a product defect. There is **no remaining package-scope blocker or unexplained installed byte**.

## Bound evidence

- [Final review receipt](wave5-package/final-review-receipt.json): exact source/run, scoped G1/G2 verdict, cross-review results, commands and all evidence hashes.
- [Complete archive fidelity](wave5-package/final-archive-fidelity.json), reproduced by [audit_archive_fidelity.py](wave5-package/audit_archive_fidelity.py).
- [Framework/native findings](wave5-package/final-framework-native.json), reproduced by [audit_framework_native.py](wave5-package/audit_framework_native.py).
- [Independent UUID and rehashed challenge](wave5-package/final-normalization-challenge.json), [complete negative comparison](wave5-package/final-rehashed-corruption-comparison.json), and [reproduction script](wave5-package/challenge_normalization.py).

No production code, inherited helper, README, ledger or workflow was changed; no archive executable was run, and this reviewer made no commit or push. The earlier PENDING preparation checkpoint follows as historical context and is superseded by this exact-source final verdict.

---

## Preserved preparation checkpoint

**Reviewer:** `/root/wave5_package`  
**Checkpoint date:** 2026-11-06  
**Checkpoint status when written:** **PENDING — fresh original artifacts and independent cross-review are required.**

## Exact source and scope

Final package acceptance must be bound to source `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, tree `9db3623bd2c81d18b17b29c921b1d6212ca1339d`, and hosted run `42180484781`, as supplied by the parent. This reviewer has not yet independently checked that candidate's originals or issued an implementation verdict for it. The preceding accepted P001/P002 source is `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.

The bounded method inspection below initially used README source `b6f4d9bf04dd4a15a1b349845f962295ff350b7d`, whose tree `202dbdc59c0bd9df10804b9e3a75674508eab75d` was checked locally. The parent superseded that candidate after a concrete unexpected-abort receipt defect and reports the corrected candidate adds `BaseException` handling with original-exception re-raise, regression coverage, and a fixture floor of 201. Although the parent reports that b6 run `42177445982` reached `READY_FOR_INDEPENDENT_REVIEW`, its originals under `/workspace/scratch/430a9939323d/p003-work/run-42177445982` are diagnostic/method evidence only and have not been inspected by this reviewer. Final-source originals remain unavailable at this checkpoint.

This checkpoint covers the independent review method and its acceptance boundaries. The parent will supply centrally downloaded original build A, build B, replay, and comparison ZIPs. This reviewer has not polled or downloaded GitHub artifacts, and has not inspected fresh originals or accepted their package results at this checkpoint. The parent-reported fixture and restoration results do not substitute for the original-package checks below.

## Bounded method review completed

Read the repository `AGENTS.md`, the README global acceptance contract and complete P003 section at b6, the Wave 3 comparison implementation and report, its independent UUID cross-check note, and the Wave 4 package review. The complete implementation of `wave3-package-review/compare_original_packages.py` was inspected without importing the production verifier or executing archive content. This reviewer has not yet executed a package comparison. Historical execution findings below remain attributed to the earlier reviewers.

The inspected comparison helper has SHA-256 `0115737614c47266678af87da2bb9c681af4c009c061b538299eacaef4104d62`. It performs bounded ZIP CRC and duplicate-name checks, exact-source manifest checks, streaming tar member checks, full regular-file content hashes, and an independent Mach-O parser. Its normalization is limited to source-bound N_OSO timestamp fields, four specifically identified compile-time string locations, and LC_UUID values independently recomputed from both actual files using the pinned linker algorithm. It labels every changed installed regular-file byte and requires equality after that bounded normalization. A changed byte in a UUID-excluded region is not automatically permitted as an installed-file difference.

No concrete defect requiring a production or comparison-helper change was found in this bounded source inspection. This is not a fresh-artifact verdict.

## Acceptance obligations beyond the helper's status

The helper's `INSTALLED_PACKAGE_BYTES_CLASSIFIED` result has a narrower meaning than complete P003 package acceptance. Source inspection independently confirms the limits recorded by Wave 4:

| Obligation | Helper behavior and required Wave 5 adjudication |
| --- | --- |
| Both reinstall manifests | An absent second manifest can be recorded as `SECOND_MANIFEST_NOT_PROVIDED` without failing the installed-byte status. Both actual first and second manifests must be present, authenticated to the original ZIPs, and compared independently for each build. |
| Complete original ZIP fidelity | The helper compares selected ZIP members only when corresponding local files exist. A positive selected-input flag does not prove that every required artifact member was provided. Enumerate the fresh ZIP inventory, check canonical names and duplicates, and establish required-member presence before accepting any comparison. |
| Full tar fidelity | The helper verifies all tar members against manifest entries and reports metadata differences separately. Independently adjudicate every tar path, type, mode, literal link target, file size/hash, ownership field, timestamp, device field, and PAX field relevant to the fresh archives. An enumerated metadata difference is not automatically an accepted difference. |
| Linker metadata | The helper reports linker metadata separately; a changed or unclassified linker banner does not necessarily fail its installed-byte result. Inspect both original reports, their exit status and hashes, and the exact pinned source that explains a proposed banner difference. |
| Intermediate linker binaries | A report of a linker hash or a source explanation of its banner does not classify every byte of an unarchived linker binary. If the actual intermediate binaries are absent, whole-build byte identity remains **NOT PROVED**. |
| Seven framework resolutions | An installed-file comparison is not proof of framework resolution or ownership. Independently check exact owners, collisions, aliases, install names, dependencies, loaded paths, and native provenance for AppKit, Foundation, CoreGraphics, CoreText, ImageIO, QuartzCore, and AudioToolbox. |
| Replay provenance | Replay/comparison output must be bound to these fresh original artifacts and exact source. A green producer summary or matching object count alone is insufficient. |

Compressed ZIP/tar hashes bind the actual evidence inputs. Differences in compressed streams, tar metadata, installed executable contents, and unarchived intermediate outputs must be reported with their separate scopes. No conclusion about one scope will be silently expanded to another.

## Historical evidence boundary

The original packages under `/workspace/scratch/430a9939323d/p003-work/run-41292343355` belong to source `89c6c9d85aba6ed1662035e6366298c92ef9c970` and are method-QA inputs only. Wave 3 and Wave 4 report exhaustive classification of that historical pair, ordinary byte-mutation rejection, and a separately reproduced nano UUID calculation. The Wave 3 cross-check also reports rejection of a changed byte inside a UUID-excluded STABS string interval and rejection after removing nano's exact source binding. These findings are useful challenges to the method but are not fresh-source acceptance evidence and were not rerun by this reviewer at this checkpoint. Their historical file counts and byte totals will not be presumed for final run `42180484781`.

## Required fresh-artifact continuation

1. Record the original A/B/replay/comparison ZIP paths, sizes, digests, complete member inventories, and source/run attribution supplied by the parent for source `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, run `42180484781`. Check every original ZIP and verify each locally examined member against its original bytes.
2. Require both install and reinstall manifests for A and B. Independently reconcile complete actual tar inventories with those manifests, including file contents, modes, types, aliases, literal link targets, and metadata. Explicitly adjudicate tar and linker metadata outside the helper's pass/fail scope.
3. Run the independent installed-byte comparator on the exact-source fresh pair and independently reproduce critical normalization cases. Exercise meaningful rehashed corruption so rejection is not merely the result of a stale checksum. In particular, challenge the distinction between a UUID-excluded region and a legitimately classified N_OSO/time-string difference.
4. Inspect all seven frameworks' exact ownership/resolution chains, install names and dependencies, including the native evidence provenance that supports the fresh result. Cross-check fresh replay and comparison outputs against the originals.
5. Read the fresh Wave 4 reports and reconcile any disagreements using actual inputs. Only then issue this reviewer's exact-source verdict, distinguishing installed-package classification from unproved intermediate or whole-build properties.

## Current disposition

**G1 package reproducibility: PENDING. G2 package/framework fidelity: PENDING. Final independent package verdict: PENDING.** No P003 acceptance gate is advanced by this checkpoint. No production/helper files, README, or ledger were changed, and this reviewer has not committed or pushed anything.

### Sources reviewed

- Repository `AGENTS.md`.
- README global contract and complete P003 section at `b6f4d9bf04dd4a15a1b349845f962295ff350b7d`.
- `wave3-package-review/compare_original_packages.py` (SHA-256 above).
- `wave3-package-review/uuid-independent-crosscheck.md` (SHA-256 `8551d190d753c1f724addcf4c79e4a7abc70bbed613ad7f92712dab0703f4197`).
- `wave3-package.md`.
- `wave4-package.md`.
- Parent candidate updates supplying the final 462 source/tree/run and superseding b6; these updates are provenance supplied to this checkpoint, not an independent fresh-artifact verdict.
