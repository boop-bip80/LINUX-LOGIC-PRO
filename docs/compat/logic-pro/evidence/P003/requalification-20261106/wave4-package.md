# P003 Wave 4 package/framework review

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
