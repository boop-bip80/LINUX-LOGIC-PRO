# P003 Wave 4 package/framework review

## Superseded b6 diagnostic checkpoint — 2026-11-06 07:56 UTC

**This completed rehearsal does not accept the corrected candidate.** The campaign
coordinator superseded b6 with the corrected candidate under run `42180484781`.
Final original-package/G1/G2 review is still pending its paired originals and exact
source binding. The older dated checkpoint below is retained as history.

At the coordinator's request, the unchanged comparator was run on original run
`42177445982` A/B packages for source
`b6f4d9bf04dd4a15a1b349845f962295ff350b7d`, tree
`202dbdc59c0bd9df10804b9e3a75674508eab75d`, using
`--purpose historical-method-qa` and no repeated counterexamples. The separately
recorded purpose is `superseded-candidate-diagnostic`; current-candidate acceptance
is false throughout.

| Original b6 artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Build A ZIP | 87,412,935 | `741afe44814f42d9f01e3ea0e1efffa56240e0e66a5443dc3b27003f3d692c93` |
| Build B ZIP | 87,411,252 | `7c9fd88cae4f9562f24a411a394f990f73a24b3f7d83ccc6f66d9736e7c69766` |
| A installed-prefix archive | 85,637,759 | `342db8eed844a54d919f265b01992ee4b58f13dd9693507fdd207ef5ce38bf55` |
| B installed-prefix archive | 85,638,387 | `13a8c9a679e7ed3bf7dc033a9734f120c31c18e851ff81d96b7327457de1bfb5` |

Both original ZIP sizes/hashes and all 459 members' CRCs were independently verified.
Both install manifests were present, byte-identical within each host, and bound to
the originals. Actual inventories contain **11,947 entries** each: 9,460 regular
files, 1,366 symlinks, and 1,121 directories. There are no structural inventory,
tar metadata, archive/manifest, source-binding, or first/second-install differences.

The unchanged comparator exited zero: **9,322 identical regular files; 138 different
regular files; 4,410 changed installed bytes; zero unclassified bytes.** Every range
and normalization is enumerated in the complete result. The breakdown is 4,335
changed bytes in 3,539 `N_OSO` fields, 11 changed bytes in four source-bound time
strings, and 64 changed bytes in four independently source-derived UUID fields.
No additional normalization was introduced.

The source-built-linker hashes differ: A
`ba80f018ed86f43d354adbaaa1ba5c256a5f5b5d7595d26bfebb4cfba9b7bdc3`, B
`889bb20c69bc1cbb86fa87292773e101a754a802bd235dcc9baa847da5566839`.
Their version text differs only at source-bound `BUILD` times `07:03:19` and
`07:05:32 Nov 6 2026`. Both commands exited zero. **The executable bytes are absent
from both original ZIPs, so exhaustive intermediate-linker byte classification and
whole-build byte reproducibility remain unproved.**

### Actual framework and native metadata observations

The seven actual packaged Mach-O images on each host have the expected absolute
install IDs `/System/Library/Frameworks/<name>.framework/Versions/<version>/<name>`.
Their public aliases resolve through `Versions/Current` to the indicated version
and regular-file image. All **70 direct load dependencies per host** resolve through
the actual archive's alias chains to regular installed files. Parsed metadata
agrees with the original manifest. This bounded check does not claim a recursively
parsed transitive Mach-O graph.

| Framework | Version | Direct dependencies | Source owner | Compile commands per host |
| --- | --- | ---: | --- | ---: |
| AppKit | C | 19 | `src/external/cocotron/AppKit` | 331 |
| Foundation | C | 8 | `src/external/foundation` | 233 |
| CoreGraphics | A | 7 | `src/external/cocotron/CoreGraphics` | 40 |
| CoreText | A | 7 | `src/external/cocotron/CoreText` | 14 |
| ImageIO | A | 5 | `src/frameworks/ImageIO` | 3 |
| QuartzCore | A | 13 | `src/external/cocotron/QuartzCore` | 32 |
| AudioToolbox | A | 11 | `src/CoreAudio/AudioToolbox` | 18 |

The coordinator initialized the unchanged Cocotron pin
`d89d7aa029c1ca2d297372fc7f618e9b006112d0` and Foundation pin
`a8b5ab193a107712d0806b6f95bfa763be68e1f8`. Their exact owner CMake blobs were then
read and hash-bound, together with the root-owned ImageIO/AudioToolbox CMake blobs
at b6. The observed source targets, framework versions, and actual compile-command
owner paths agree. The complete record preserves hashes, source locations and
relevant target/version lines.

Each framework retains one build-tree `LC_RPATH` string. All 70 inspected direct
load dependencies are absolute installed paths and resolve in the package without
that search path. The original RPATH strings are preserved in the observation
record; this is not a claim about every possible dynamic load at runtime.

GNU `readelf -W -h -l -d` was run on the actual archived bytes of `darling`,
`darling-coredump`, `darlingserver`, and `mldr`, using anonymous in-memory files.
Their hashes, ELF type, interpreter, direct NEEDED entries, and empty RPATH/RUNPATH
lists agree with the original reports on both hosts. No packaged executable was
run. Eight raw readelf outputs are retained. All 292 original native stdout/stderr
logs per host were hash-verified; each recorded command exited zero without a
timeout and no raw ldd output contained a not-found error. The first/second native
identities agree, and both native-wrapper source inputs match their exact b6 blobs.
The 21 wrapped host-library identities are retained in the original reports;
independent full reconstruction of their external host resolution is reserved for
the final review, because those host-library bytes are not packaged here.

### Publishable superseded evidence

- [Complete byte comparison](wave4-package/superseded-b6/original-package-comparison.json)
  — SHA-256 `6205bd79d5f3286296ec469a105dc5318012853105cb235cf52ff163e05f387b`.
- [Unchanged-comparator replay receipt](wave4-package/superseded-b6/replay-receipt.json)
  — SHA-256 `f5b37c614ee9f843a692c93a656a19a499372f2bf44e67f745e540b060eb0ec7`.
- [Framework/native observations](wave4-package/superseded-b6/framework-native-observations.json)
  — SHA-256 `caf7d9f2e10d378d9dbc31efe855a2b0aeab8e94925ea5d6849e3581a04144d2`.
- Comparator stdout/stderr and the eight raw readelf outputs are retained in the
  same directory. The exact comparator command and original identities are in the
  replay receipt and complete report.

**Superseded diagnostic verdict:** no unexplained installed-byte, tar-metadata,
framework-ID/alias, direct dependency, or inspected source-owner discrepancy was
found in the b6 originals. This evidence cannot accept the corrected candidate;
its paired original artifacts must be reviewed separately. No production, helper,
README, or workflow changes, commits, pushes, or additional counterexample tests
were made for this rehearsal.

## Bounded method checkpoint — 2026-11-06 06:58 UTC

Reviewer: `/root/wave4_package`, an independent nonauthor of the inherited
comparator, its UUID crosscheck, and the production implementation. This checkpoint
records completed method review and historical method QA. **Fresh installed-package,
G1, and G2 verdicts remain PENDING.**

The current candidate supplied by the campaign coordinator is
`b6f4d9bf04dd4a15a1b349845f962295ff350b7d`, hosted run `42177445982`.
The local repository HEAD matched that candidate at this checkpoint. The coordinator
reports successful retained frozen-toolchain acquisition and hosted fixture checks;
those reports are context, not original-package acceptance evidence. Fresh original
A/B ZIPs, their hashes, and their installed-prefix archives have not yet been
supplied to this reviewer. No current-candidate artifact hash or successful package
verdict is asserted here.

AGENTS.md and the README global and P003 gates were read. This review is limited to
package fidelity, installed-byte nondeterminism, framework ownership and dependency
resolution, and native dependency/provenance evidence. Other reviewers own the full
build-input and runtime-case reviews. No restricted source, disassembly, or
decompilation was used. No production, workflow, README, or inherited helper edits
were made, and this reviewer made no commit or push.

## Inherited method reviewed

| Method | SHA-256 | Review result |
| --- | --- | --- |
| [Wave 3 original-package comparator](wave3-package-review/compare_original_packages.py) | `0115737614c47266678af87da2bb9c681af4c009c061b538299eacaef4104d62` | Reviewed unchanged; adequate for its explicitly bounded installed-byte classification claim when the additional gate checks below are applied. |
| [Independent UUID crosscheck](wave3-package-review/uuid-independent-crosscheck.md) | `8551d190d753c1f724addcf4c79e4a7abc70bbed613ad7f92712dab0703f4197` | Reviewed and replayed unchanged; separately reconstructs the historical UUID inputs and checks excluded-byte and missing-source-binding counterexamples. |

The comparator independently reads the original ZIP and installed-prefix tar data,
checks CRCs and selected local-input fidelity, builds an actual path/type/mode/size/
hash/link inventory, and compares the manifest and first/second installations. It
rejects duplicate or unsafe archive paths and unsupported tar members. It parses
Mach-O metadata without executing the packaged binaries and enumerates every
changed installed byte, including explicit unclassified ranges and normalized
hashes.

The allowed normalizations are narrowly tied to parsed `N_OSO` timestamp values,
specific build-time strings in source-bound sections, and the content-derived
`LC_UUID` algorithm. Source binding uses the expected superproject commit, its exact
gitlinks, and pinned source blobs. UUID exclusions do not themselves authorize
arbitrary changes to the excluded bytes. The separate UUID replay verifies that a
changed excluded byte is still rejected by the full byte classifier, and that a
missing required source binding prevents acceptance.

The helper's existing `/root/wave3_package` reviewer field is retained as inherited
authorship. The Wave 4 replay receipts identify the independent replayer. These
receipts do not convert historical evidence into fresh acceptance.

## Completed historical method QA

Both replays used the original run `41292343355` packages for historical source
`89c6c9d85aba6ed1662035e6366298c92ef9c970`. They did not use fresh candidate output.
The replay receipts were created while `cc268442e9711beeb117f59850dcc6526dd03c46`
and run `42175768705` were the then-pending campaign. Their recorded candidate/run
fields are preserved as historical context; both explicitly set
`current_candidate_acceptance: false`. The current pending binding is the
`b6f4d9bf...` candidate and run `42177445982` stated above.

| Historical input | Original ZIP SHA-256 | Installed-prefix archive SHA-256 |
| --- | --- | --- |
| A | `14f9e0c507efeff85652008e160f2f4fb1e68d7e0f4cb5dd46c941b1918b9849` | `110a80dda4c0126271f7948e6c2fa1796809258881ee22717a3c615412095e12` |
| B | `e33778793ce009ff7eb01b8257f58098545c760d496d5fc37775f4ee26d82530` | `333707dd485b4be84d3ec25379e8cd954516dc40e759fcacab741e249a8349a0` |

The unchanged comparator replay exited zero and reported
`INSTALLED_PACKAGE_BYTES_CLASSIFIED`: 9,320 identical regular files and 138 different
regular files, covering 6,447 changed installed bytes with zero unclassified bytes.
It recorded 3,539 `N_OSO_n_value` fields, four source-bound build-time fields, and four
content-derived UUID fields. Actual inventories, tar metadata, archive/manifest
fidelity, and first/second install comparisons had no differences requiring an
exception in this historical pair. Each ZIP's 459 members passed CRC checks. The
ordinary-byte mutation counterexample was rejected with one unclassified byte and
unequal normalized output; the originals were untouched.

The unchanged UUID crosscheck replay also exited zero. Its independently computed
historical nano UUIDs matched the originals:

| Historical host | Original and independently computed UUID |
| --- | --- |
| A | `d04d74f362cf301f8fc4cc08928c11d7` |
| B | `1dbe6136f96934868a3c9f60ef79a5ce` |

It confirmed rejection of both an otherwise UUID-excluded byte mutation and a
missing exact source binding. These are method checks, not current-candidate G1,
G2, or phase acceptance.

### Retained replay evidence

| Evidence | SHA-256 |
| --- | --- |
| [Comparator replay receipt](wave4-package/historical-method-replay-receipt.json) | `943db17865be9f2b95c821a9a45d8511ca2325bb6b2aef0e83dcd8aea1ee0a69` |
| [Complete comparator result](wave4-package/historical-method-qa.json) | `a1355bf55960bdc1d5da9cf434941c492c86ea240ccf46491270fa78b7b64f63` |
| [UUID replay receipt](wave4-package/historical-uuid-crosscheck-replay-receipt.json) | `eefd0304cb6abb250080cc2a731305f78f897b2de14c702f4ead3d05cc40b57f` |
| [UUID replay output](wave4-package/historical-uuid-crosscheck.stdout.json) | `538aad9d7ccdb901d6d7f477662c958c6f598d62121e3de0c41aa7e6f47736c2` |

The corresponding comparator stdout/stderr and UUID stderr are retained beside
these files. The receipts preserve replay times, exact command or unchanged shell
block hash, method identity, and exit status.

## Acceptance boundaries requiring explicit fresh review

The comparator's success status is intentionally narrower than full P003 gate
acceptance. Its result must be read with the underlying records:

1. A missing `install-second.json` yields `SECOND_MANIFEST_NOT_PROVIDED`; only an
   actual nonempty difference list contributes to the failure expression. The
   fresh review must require both install manifests for each host and compare
   them. A missing second manifest cannot satisfy reinstall evidence.
2. Selected local-input ZIP comparisons run only for inputs that exist locally.
   Consequently, `selected_inputs_match_zip: true` does not independently prove
   all required evidence was supplied. The fresh review must require every input
   it relies on and match those bytes to the original ZIP members.
3. Tar metadata differences are enumerated but do not contribute to the helper's
   failure expression. The fresh review must inspect and explain any such
   differences independently. The original gzip archives remain hash-bound;
   compressed-stream differences are not interpreted as installed executable
   differences.
4. Source-built-linker report differences, including an unclassified banner
   difference, do not themselves change the installed-byte status. The fresh
   review must inspect both raw linker reports and their exact-source binding.
   Historical A/B reports had different linker hashes and build-time banner
   values. Their linker executable bytes were absent from both original ZIPs.
   The method therefore correctly retains
   `NOT_PROVED; differing intermediate linker bytes unavailable` for whole-build
   byte reproducibility. A source-bound banner explanation is not exhaustive
   classification of the unavailable linker binaries.
5. The helper does not replace the seven-framework or native dependency reviews.
   Producer summaries and aggregate workflow status are not sufficient evidence
   for those claims.

No helper or production-code change is requested by this bounded review. The
existing method can support the fresh installed-byte review provided these
independent checks remain explicit. Any unexplained fresh installed-byte change,
unsupported normalization, unresolved dependency, or missing required evidence
prevents the corresponding positive verdict. The unarchived-linker limitation
must remain visible in any later assessment; it cannot be described as proof of
whole-build byte equality or exhaustive intermediate-linker classification.

## Fresh package/G2 work awaiting original artifacts

Once the coordinator supplies both original A/B artifacts, the fresh dated review
will bind the exact candidate, run, artifact identities, original ZIP hashes and
sizes, and installed-prefix archive hashes. It will apply the unchanged comparator
with the current exact source commit, require complete original inputs, inspect
every differing byte and metadata record, and retain the linker-byte limitation
where the original evidence lacks the executable bytes.

G2 review will inspect actual packaged Mach-O load-command metadata for AppKit,
Foundation, CoreGraphics, CoreText, ImageIO, QuartzCore, and AudioToolbox, including
each install name, public/version alias chain, recursive dependency resolution,
and exact pinned source/build owner. Native ELF dependencies and provenance will
be checked against actual package bytes and the original raw dependency evidence.
These findings will be recorded independently of producer pass labels. The
runtime and fullbuild reviewers retain ownership of their respective gates.

**Checkpoint verdict:** bounded method review and historical QA complete and
publishable; fresh installed-package/G1/G2 acceptance pending original artifacts.
