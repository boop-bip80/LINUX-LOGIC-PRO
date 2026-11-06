# P003 Wave 5 independent package and reproducibility review

**Reviewer:** `/root/wave5_package`  
**Checkpoint date:** 2026-11-06  
**Status:** **PENDING — fresh original artifacts and independent cross-review are required.**

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
