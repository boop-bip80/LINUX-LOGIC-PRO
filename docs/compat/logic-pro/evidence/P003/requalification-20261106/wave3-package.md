# Wave 3 — independent original-package review method

**Preparation complete; historical method QA passed. Fresh candidate package
acceptance remains pending. Remain in P003.**

Reviewer: `/root/wave3_package`, 2026-11-06. Candidate implementation:
`af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`, full workflow `42169925661`.
This reviewer did not author the candidate's production build, install,
source-classification or runtime changes. This review authors only this report
and the evidence helper/results in `wave3-package-review/`. It does not issue
G1–G4 acceptance and does not borrow the historical `89c6c9d` verdict.

## Contract and completed work

The root `AGENTS.md`, README global gate contract and original P003 G1–G4
requirements were read before preparing the review. The package contribution to
G1 requires the actual original installed bytes, identical source/toolchain
inputs, complete enumeration of differences, and independent reproduction. G2's
live framework resolution, G3's actual probe results, and G4's runtime lifecycle
and separate archive-only host remain separate required evidence.

The [independent helper](wave3-package-review/compare_original_packages.py) uses
only Python's standard library and Git for exact pinned source-object reads. It
does not import or call a production verifier, extract archive paths to the
filesystem, follow an archived symbolic link, or execute an installed member.
The helper reads both compressed tar archives as data and checks:

1. Original ZIP SHA-256, all-member CRCs, duplicate ZIP members, and byte identity
   between the supplied tar/manifest/linker reports and their original ZIP
   members.
2. Every installed path, entry type, permission mode, regular-file size and
   SHA-256, and literal symbolic-link target against that host's
   `install-first.json`. The sole non-manifest archive root is checked as an
   actual directory. No manifest path is silently excluded. Hard links, special
   entries, duplicate paths, traversal paths, sparse members and excessive
   expansion fail review.
3. Both actual installed inventories against each other, and first versus second
   install manifests when supplied. Tar ownership, timestamps, type flags,
   device fields, link names and extended metadata are compared separately.
4. Every changed byte of every differing regular file. The JSON includes both
   raw file hashes/sizes, every changed offset interval and its exact A/B bytes,
   every recognized field, all unclassified bytes, and complete-file hashes after
   narrowly scoped normalization. A remaining unknown byte, parse failure,
   inventory mismatch, source-binding failure or normalized-file mismatch causes
   a nonzero exit.

The helper's status `INSTALLED_PACKAGE_BYTES_CLASSIFIED` describes this bounded
byte analysis. `phase_acceptance` is always false. It does not certify that a
build completed, that runtime probes passed, or that all build intermediates are
byte-reproducible.

## Exact normalization policy

Mach-O headers, fat-slice boundaries, load-command boundaries, section ranges,
symbol-table bounds and string-table references are parsed independently.
Different layout or unsupported content is a failure, not a reason to widen the
normalization.

- **N_OSO:** Only the `n_value` bytes of parsed `N_OSO` symbol records can be
  normalized. Their object names, locations, widths, section/descriptor metadata
  and every other byte must agree. Both changed values must be plausible bounded
  Unix timestamps. The exact old/new values and object path are recorded for
  every changed field.
- **Compile-time strings:** Only the four individually named installed images
  below are eligible. Matching occurs in the specific parsed `__TEXT` section,
  requires one unambiguous literal with valid date/time syntax at the same
  location, and is bound to an exact reviewed source-file SHA-256. The helper
  obtains that source file with `git show` at the submodule commit in the actual
  install manifest, then crosschecks the root source commit's gitlink. A generic
  date-looking byte sequence elsewhere is not an exemption.
- **LC_UUID:** A changed UUID is eligible only together with a source-bound time
  change in that image. Both actual UUIDs must be recomputed exactly using the
  pinned linker's content-hash policy before the 16 UUID bytes can be normalized.
  Zeroing UUIDs without verifying their derivation is insufficient. STABS-related
  ranges omitted from the UUID hash are still compared in the full-file byte
  analysis; only parsed N_OSO timestamp fields can differ there.

The reviewed source bindings are metadata causes in existing licensed repository
dependencies. No external implementation code is copied into this helper.

| Installed image | Exact source binding used for historical method QA | Section / allowed string |
| --- | --- | --- |
| CoreFoundation | `corefoundation@a3640a77410cf1825f7855172b1551ae7917c461`, `CFVersion.c:28` | `__const`; fixed version prefix, then `__DATE__` and `__TIME__` |
| IOKit | `IOKitUser@534684e6748dffbd875c6cd1942477a52b66a077`, `kext.subproj/OSKext.c:376` | `__cstring`; `OSKEXT_BUILD_DATE`, then time and date |
| nano | `nano@7514f5f1115fffedd8fc2095107ca86ff82c54d6`, `src/nano.c:843` | `__cstring`; the separate time/date literals used by its version output |
| vim | `vim@7f8da1dd66fc8f0654ebfa597b6013c8cf15185a`, `src/version.c:62` | `__cstring`; combined date/time literal |

The current CoreFoundation gitlink is
`3469fdf6904155e0efa84a6d6ca58a6986890c25`. Its `CFVersion.c` is byte-identical
to the historical binding (SHA-256
`14748415cdbf66e4f65b1d039ac7c0d190eb877a7feeca079ec34c1e5ff7e366`), but the
helper still resolves each campaign's own exact gitlink. The other four relevant
source gitlinks, including cctools-port, are unchanged between those campaigns.
This equality does not make their installed outputs accepted in advance.

The UUID policy is bound to `cctools-port@d9456c221e1f462e17c0b3297748bc089d5a861e`,
with complete-file SHA-256 bindings for `OutputFile.cpp`, `LinkEditClassic.hpp`
and `HeaderAndLoadCommands.hpp`. With no STABS exclusions, UUID derivation hashes
the complete Mach-O slice with its UUID bytes zeroed. With the observed STABS
layout, the hash omits the parsed STABS records/string interval, `LC_SYMTAB` and
the `__LINKEDIT` segment command and includes the output leaf-name suffix.
Version/variant bits are then applied. The helper preserves the exact omitted
ranges, hash prefix, computed value and actual UUID for both builds.

## Historical original-artifact method QA — not current acceptance

The [complete byte report](wave3-package-review/historical-method-qa.json) was
computed from the original two build artifacts of workflow `41292343355`, source
`89c6c9d85aba6ed1662035e6366298c92ef9c970`. Root downloaded the original archives;
this reviewer independently rehashed them, checked all 459 CRC members in each,
and bound the selected input bytes to their ZIP members.

| Original artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Build A, artifact `13078431359` | 87,382,711 | `14f9e0c507efeff85652008e160f2f4fb1e68d7e0f4cb5dd46c941b1918b9849` |
| Build B, artifact `13078653955` | 87,371,725 | `e33778793ce009ff7eb01b8257f58098545c760d496d5fc37775f4ee26d82530` |

| Independently observed result | Value |
| --- | ---: |
| Installed entries in each archive and manifest | 11,941 |
| Regular files / symbolic links / directories | 9,458 / 1,364 / 1,119 |
| Archive-versus-own-manifest mismatches | 0 |
| Cross-build path/type/mode/link/size differences | 0 |
| Tar member metadata differences | 0 |
| First-versus-second install manifest differences, each host | 0 |
| Byte-identical regular files | 9,320 |
| Differing regular files | 138 |
| Changed installed bytes | 6,447 |
| Parsed changed N_OSO fields / changed bytes | 3,539 / 6,371 |
| Source-bound changed time-string fields / changed bytes | 4 / 12 |
| Exactly recomputed changed UUID fields / changed bytes | 4 / 64 |
| Unclassified installed bytes | 0 |

All 138 independently computed path/hash-pair/changed-byte-count rows also match
the published historical difference table, as recorded in the
[separate reference crosscheck](wave3-package-review/historical-reference-crosscheck.json).
The historical table was used as a crosscheck after computing the actual-byte
report, not as the helper's oracle or an assumed current count.

The required negative reproduction changes one otherwise unexplained byte in an
in-memory copy of the real Build A `nano` member: offset 4,096, `00` to `01`.
The same classifier reports exactly one `UNCLASSIFIED` byte and unequal
normalized hashes. The original archives remain untouched. Its full input/output
hashes and rejected byte span are retained in the byte report's `counterexample`
record.

### Independent challenge of the UUID and unknown-byte method

Reviewer `/root/wave3_package/uuid_crosscheck` independently parsed both actual
nano members and recomputed their UUIDs without using this helper's parser or
UUID function as the oracle. Both digests matched. The reviewer then changed a
byte at offset 227,700 inside the STABS string interval omitted from the UUID
hash. Although that modified file still has a correctly derived UUID, the
package classifier rejected its one unknown byte. Removing nano's exact source
binding likewise rejected the real A/B pair, leaving 19 bytes unclassified.
The [authored independent record](wave3-package-review/uuid-independent-crosscheck.md)
preserves original input hashes, precise ranges, results and a command that the
reviewer extracted from the Markdown and successfully replayed. No concrete
false pass was found in that bounded review; fresh candidate acceptance remains
pending.

### Intermediate linker limitation

Both original `source-built-linker.json` records are preserved verbatim and
hash-bound in the new report. Their linker hashes differ:

| Build | Recorded linker SHA-256 | Recorded BUILD value |
| --- | --- | --- |
| A | `e9b4903cbb50aeb2a231d926716daefd15f6b73e2356191218993336fc8e803c` | `09:25:35 Nov  1 2026` |
| B | `37a753e4a697cf4b70de4eeb39898ca81acef0295aa5d0b4f2b201f8d8512600` | `09:26:06 Nov  1 2026` |

The banner difference is bound to pinned `Options.cpp:4208`; all other banner
text agrees and both version commands returned zero. The intermediate linker
executable is absent from the original ZIPs. Therefore its differing binary
bytes cannot be exhaustively classified or counted. **Zero unknown bytes above
applies only to installed regular-file contents.** Whole-build byte
reproducibility is explicitly unproved. Raw compressed archives are hash-bound;
compressed-stream byte changes are not treated as installed executable changes.

## Reproduction

From the repository root, with the original ZIPs placed next to their respective
artifact directories as `build-a.zip` and `build-b.zip`, and the five selected
submodule object stores available:

```bash
python docs/compat/logic-pro/evidence/P003/requalification-20261106/wave3-package-review/compare_original_packages.py \
  --a /workspace/scratch/430a9939323d/p003-work/run-41292343355/build-a \
  --b /workspace/scratch/430a9939323d/p003-work/run-41292343355/build-b \
  --repo . \
  --expected-source 89c6c9d85aba6ed1662035e6366298c92ef9c970 \
  --purpose historical-method-qa \
  --counterexample \
  --output /tmp/p003-historical-method-qa.json
```

Observed exit: **0**. Expected observed totals: 138 files, 6,447 changed bytes,
zero unknown installed bytes, and a rejected one-byte counterexample. The JSON
timestamp and absolute-path provenance vary on replay; the actual byte analysis
must reproduce.

For fresh candidate originals, use their own two artifact directories,
`--expected-source af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2` and
`--purpose candidate-package-review`. Do not pass the historical source SHA or
assume the historical file counts. Unsupported changes remain failures requiring
new source-bound explanation and independent review.

## Evidence identities and remaining work

| File | SHA-256 |
| --- | --- |
| `wave3-package-review/compare_original_packages.py` | `0115737614c47266678af87da2bb9c681af4c009c061b538299eacaef4104d62` |
| `wave3-package-review/historical-method-qa.json` | `06c29d18748aeeb2134ec12083eb6eda60a8d8d576664e8920287525566ad0e3` |
| `wave3-package-review/historical-reference-crosscheck.json` | `68a25fa50f4ce759097b139aaeacdd4071ba4c0497e3b8143eea34c79472e034` |
| `wave3-package-review/uuid-independent-crosscheck.md` | `8551d190d753c1f724addcf4c79e4a7abc70bbed613ad7f92712dab0703f4197` |

Fresh original `af3566ee` package bytes were not yet available when this method
record was prepared. Waves 4–5 must independently review this helper and run it
against both actual new packages, examine every new difference and unknown byte,
bind both packages to their complete build/source/toolchain and runtime evidence,
and preserve the independent source-free installed-archive replay. The separate
unarchived-linker limitation must remain explicit if the new originals likewise
omit its executable. No current P003 gate is checked by this report.

Provenance: repository requirements, original open-source project build artifacts,
the listed exact dependency source objects and their public license notices.
No CoreCrypto source, proprietary Apple binary, restricted Apple source,
disassembly or decompilation was used. No production file, dependency pin,
workflow, root README or test suite was modified by this review. No commit or
push was performed by this reviewer.
