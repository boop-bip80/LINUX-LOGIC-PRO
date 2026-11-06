# Wave 4 independent original source/build review

## Final bounded verdict — 2026-11-06 08:01:43 UTC

**APPROVED for exact source, frozen toolchain identity, both fresh complete builds/installations, source cleanliness and both hosts' uninstall/reinstall lifecycle at `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, tree `9db3623bd2c81d18b17b29c921b1d6212ca1339d`, run `42180484781`. No blocking finding remains in this bounded scope.**

Reviewer **`/root/wave4_build`** is a distinct non-author of the production repairs, workflow and production tests. I independently inspected the original current-source evidence and wrote only this report and `wave4-build/` helpers/receipts. No production edits, README changes, commits or pushes were made. The [paired decision receipt](wave4-build/final-paired-builds.json) records the exact date, original metadata, both runner identities, evidence identities, reproduction helpers and limitations.

This supplies the source/build/install portion of G1 and the two build hosts' removal/reinstall portion of G4. **Full phase acceptance remains the coordinator's combined decision:** package-byte nondeterminism, live framework/runtime behavior and the source-free fifth campaign have separate independent reviewers. This report does not advance P004, qualify Logic Pro, audio performance or ARM execution, or claim byte-identical packages. Neither superseded `b6f4d9bf` output nor historical `89c6c9d` acceptance is used as current-source acceptance evidence.

### Original artifact identity and independent hosts

| Original | Job / runner | Artifact | ZIP bytes | ZIP SHA-256 |
| --- | --- | --- | ---: | --- |
| A | `127768936785` / `1000004332` | [`13485932962`](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42180484781/artifacts/13485932962) | 87,409,741 | `27b4a147ff1993bc6756172767cb4d60a8d4e437d5f9d85effe039571d5aa038` |
| B | `127768936725` / `1000004331` | [`13486009301`](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42180484781/artifacts/13486009301) | 87,410,244 | `a7c394d71cc4d83857c0dd2988291c0b9e4bf31cb1555785c2e71dfcd6387759` |

I independently streamed both complete original ZIPs, recomputed their SHA-256 values and **all 459 member CRCs per host**, hashed every member and compared its size/hash with the untouched extracted copy. The extracted file sets match exactly; duplicate, escaping or redirected members were not accepted. Each original identity matches the final official Actions metadata in name, size, digest, exact source and run. Both distinct build jobs record successful recursive checkout, LFS hydration, frozen input download, actual complete build/probe step and final artifact publication. Container identities differ: A **`9c5c302ffed2`**, B **`57121cab165e`**.

All required before/after source-status files are original regular ZIP members containing exactly zero bytes. Both final uploads succeeded with those files included, providing actual hosted corroboration of the earlier root-container/uploader permission repair; local mode-bit fixtures are no longer the only evidence for successful publication.

### Source and frozen toolchain

Both actual source reports identify exact `4622a939`. I compared **every one of the 160 child path/commit/tree/resolved-URL records** with the committed source lock and independently compared all 160 lines of raw recursive submodule status. Both report **161 repositories**, **293,755 physical blobs**, **44 LFS payloads totaling 16,128,448 bytes**, zero uninitialized/mismatched/conflicted/dirty repositories, and the same four explicitly recorded standard-CRLF paths. The accepted source lock remains SHA-256 **`2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`**. Its relevant unchanged children include:

| Component | Exact child commit |
| --- | --- |
| objc4 | `092352cab947b410a73b5123b190df03f90c1802` |
| libunwind | `a91da1a0e262e04eb601152a84228ff733e48422` |
| cctools-port / source-built linker | `d9456c221e1f462e17c0b3297748bc089d5a861e` |

Both original classification reports contain the complete **63 distinct citations across 41 source files**. I checked their historical identity fields and complete typed current-source provenance against the committed manifest: root versus nested commits, gitlink chains, reviewed source anchor, blob/excerpt hashes, line ranges and assertion counts. Both retain all required categories and six launch stages with no missing source/category/stage. The exact reviewed historical P004-labelled CMake re-audit remains historical provenance and does not authorize P004 work. The classification reports are byte-identical, SHA-256 **`8f0024ff45e65b739c9c60604a6061af58966252c7ea6cd81bf08dd8869a842f`**, and their raw logs agree with the 63-row audit.

The original per-host frozen lock bytes are identical, SHA-256 **`9438c463449752b1e84b45706bf0cbeec25f803eb1e46870f23908e53183421e`**, matching the independently reviewed actual retained-origin receipt. They identify image config **`sha256:eddd66602086a48927c87aff7b086c338f86fe6b67690b2f91f663e7646441de`** and the **583,513,814-byte** image archive with SHA-256 **`6d98365bd067b28c8e8b71e1b34a7200bca5aad0c790cbdd808fe2f14f67d4d5`**. Each actual host observation matches all **511 package pins and 13 tool identities**, recipe, snapshot, base and static environment fields. The preserved `dsymutil` Host CPU observations are A `icelake-client`, B `znver3`; only that already-reviewed host observation differs. Compiler bytes and static version fields remain exact.

The predecessor continuity checks and final **174/115/201** original preflight are recorded below. No changed source input invalidates the accepted ordered P001/P002 conditions, and the fresh source reports now corroborate the complete pinned graph on both actual build hosts.

### Actual compilation and frozen Clang 14 proof

Both configure logs reach actual generation completion with Clang **14.0.0**. Both full build logs contain every numbered Ninja step **1 through 16,594**, with the final completed step and no failed/stopped build marker. Their **15,399 actual compile commands** are byte-identical: **13,727** use `/usr/bin/clang-14`, **1,672** use `/usr/bin/clang++-14`. The shared compile-command SHA-256 is **`fb13552fe2abd5969033cbaeb3a85c934152089f306a35689cec65af0a5ab1ef`**. Actual caches specify Release, `cli,gui`, x86_64 enabled, i386 disabled, Metal/probes/debian packaging enabled, no ccache, and the isolated `/opt/darling-p003` prefix.

All **48 objc4 runtime compile commands** use the intended x86_64 Darwin target and `NDEBUG`, with **no injected `DEBUG` or `OBJC_IS_DEBUG_BUILD` macro**. This directly corroborates the currently pinned header-derived mode reviewed in Waves 3 and 5. The static unwind option occurs only on the **four intended static C++ compilation commands**; it does not spread to other targets.

The only raw CMake cache difference is the single `SITE:STRING` value naming each actual container. I checked each value against its independently recorded container identity; **every other cache byte matches**. The exact two hashes and 11-line unified diff are retained in the paired receipt. No compiler/configuration difference is hidden by that host-label observation. Raw parallel build logs remain preserved independently, rather than being represented as byte-identical logs.

I independently checked all **61 retained code-generation proof files per host** against their original member hashes and the bound proof receipt. Both proofs identify frozen compiler SHA-256 **`31925065812631303cf9af9a30b2f56427d2102667a87a9fb4ba03a306104589`**, the exact helper and two pinned libunwind source inputs. I parsed the generated public-source test objects' Mach-O headers, sections, relocation records and symbol table directly, without disassembly: the control contains **70 unsupported relative fixups** and `l_reltable.register_name`; the repaired object contains **zero** and no relative-table symbol. Both native variants' raw stdout exactly matches the **51 fixed register vectors**, including the default hole and integer boundaries; their common stdout SHA-256 is **`879cbb9be382326578400ec4862804628f97d01e5853ce6e82e6f1201071c8d0`**. The proof's own reported layout is corroborated by the actual object bytes, not accepted solely from its `PASS` label.

### Complete installations, removal and fresh lifecycle state

Each host's first and second inventories contain **11,947 entries: 9,460 files, 1,121 directories and 1,366 symlinks**. First versus reinstall entries match exactly within each host, including every byte hash, size, mode and link target. Their **10,486-line CMake install manifests** and **11,233-line actual install logs** also match within each host. The latter run through installation of the final GUI probe. Both hosts retain the same path/type/mode/link layout; cross-host package-byte differences are reserved for the package review.

Each original uninstall receipt binds exact `4622a939`, all **11,947 removed entries**, the isolated prefix and its verified absence. The reviewed producer checks snapshot/ownership identities before real recursive removal, checks prefix absence, removes the stopped first runtime prefix/HOME/workdir, and creates a newly marked installation. Both hosts' first and second ownership records have different nonces and recorded directory inodes. All **four installation nonces** and **four runtime challenges** are distinct across both hosts.

The actual lifecycle records additionally show different server PID/starttime pairs for the two campaigns on each host, separate first/second runtime and HOME paths, exited servers, released mount namespaces and empty remaining-holder sets. A uses server **48781 / starttime 157832**, then **49939 / 159181**; B uses **48794 / 191123**, then **49952 / 192972**. The kernel reuses the mount-namespace number after teardown; that is retained honestly and is not mistaken for shared live state. Freshness is established by the complete ownership, challenge, path and process identities together with observed shutdown, rather than by demanding globally unique recycled namespace numbers. The separate runtime review verifies the real asserted execution outputs and source-free replay.

### Limits and scope of this decision

The large original/republished frozen image ZIPs exceed the connector download ceiling, so this reviewer did not perform a local full-image rehash or local CRC replay. I independently reviewed the exact restoration verifier and complete original hosted restoration receipt, and now both original per-host environment observations plus frozen-compiler object/behavior evidence corroborate its actual use. No source-build or runtime output was reused from the retained-input run.

The source-built linker is not archived. Its original version/hash observations are retained separately: A hash **`9a123cb216f640e3cb85410d60233dede7d621f9fb0ce5ad74a37c9fe8aa8994`**, B **`c2adc09b1f85f2da5bc77b01a9f3773c733943149feebae856fb7d66923ef475`**, with their distinct recorded build timestamps. I cannot independently rehash those missing linker binaries or prove their byte-level difference from the version strings alone. This limitation remains explicit and is not converted into a byte-identical-tool claim; all prebuilt frozen tool identities are exact, and the linker source pin is unchanged.

The two original source/build/install/lifecycle observations are sufficient for this bounded approval. Package nondeterminism and G2/G3/replay acceptance are separate required decisions. No optional test expansion or historical acceptance was used to replace current evidence.

### Final receipts and reproduction

| Independent final evidence | SHA-256 |
| --- | --- |
| [A: all original archive members](wave4-build/final-a-archive.json) | `b1d928792bee8f04e998c96abfaccb96167ee1348102bc879e947208b4bbd336` |
| [B: all original archive members](wave4-build/final-b-archive.json) | `de8c674f0da9b3ae4a238d9fe162906a439cf1aec038bdb6fac3917244e1584f` |
| [A: source/build/lifecycle audit](wave4-build/final-a-build.json) | `5294c932c38d1334a3c19420051a55a48e14ab7afc0cbcfb58c1a420be6ac6e2` |
| [B: source/build/lifecycle audit](wave4-build/final-b-build.json) | `ee85bdf7058e3f7a49c938470288f3d169db57c431a0f2234862d5069d56dfbe` |
| [Paired official-metadata binding and bounded verdict](wave4-build/final-paired-builds.json) | `70cf0ce101611124394ed1caecd5590aac70beb775ec4c649c0f3fd1d7dda6dc` |

The three reviewer-owned helpers are [verify_original_archive.py](wave4-build/verify_original_archive.py), [audit_original_build.py](wave4-build/audit_original_build.py) and [compare_original_builds.py](wave4-build/compare_original_builds.py). Their exact hashes are bound in the paired receipt. They read original files without modifying/extracting them or calling the aggregate P003 PASS verifier. After retaining each original ZIP/extracted directory at `RUN`, reproduce archive checks using the artifact ID/bytes/SHA-256 table above and the exact commit/run/job identifiers. Then run the source/build audit for each host and the paired check, for example:

```sh
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave4-build/audit_original_build.py --root RUN/build-a --commit 4622a9396c5c9fbe0014bdf6a2f695dcc491233c --archive-receipt RECEIPTS/final-a-archive.json --output RECEIPTS/final-a-build.json
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave4-build/audit_original_build.py --root RUN/build-b --commit 4622a9396c5c9fbe0014bdf6a2f695dcc491233c --archive-receipt RECEIPTS/final-b-archive.json --output RECEIPTS/final-b-build.json
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave4-build/compare_original_builds.py --run RUN --receipts RECEIPTS --output RECEIPTS/final-paired-builds.json
```

## Earlier final-source preflight checkpoint: `4622a939`

**At this earlier checkpoint original-build acceptance was pending; the final bounded decision above supersedes that pending state for this reviewer's scope.** The exact source is `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, tree `9db3623bd2c81d18b17b29c921b1d6212ca1339d`, run `42180484781`. I independently verified that documentation/evidence HEAD `6879d82c75bb13cf6b5488b5b117630a64f4b8d2` changes no implementation from this exact candidate. The earlier `b6f4d9bf` build outputs are superseded and cannot qualify `4622a939`.

Reviewer `/root/wave4_build`, a non-author, independently checked the final original preflight on **2026-11-06 UTC**. The [final preflight receipt](wave4-build/final-preflight.json), SHA-256 **`89006ce8261e79679f2f1f856c4199006895c604b7de4e5cfd0420f3fbf8e089`**, records exact metadata and the following observations:

- Original fixture artifact **`13485460372`**, **11,686 bytes**, ZIP SHA-256 **`155fcbc2432969eca8248a4f8166c1d55c2e584a95dce3650f8793bd77cf00ed`** matches official metadata at exact `4622a939`. All four member CRCs and all extracted file bytes match. Direct raw-transcript counts are **174 / 115 / 201 distinct named tests**, each with its matching single `Ran` count and terminal plain `OK`, without skipped/expected-failure substitutions. The new abort regression appears once in the actual build transcript.
- Complete actual toolchain job **`127768690555`** log is **19,791 bytes**, **243 lines**, SHA-256 **`a75ed922fa945e31cf7bdd9ff5905b6ee52a2b0914c6d2db2b12d52343ff0ab3`**. It identifies the exact current checkout, restoration command, complete origin/five-file hash receipt, successful publication and runner cleanup. The complete restoration receipt is field-for-field identical to the previously reviewed retained-input receipt below, including original source/artifact, frozen image ID and all five original file hashes.
- The current toolchain publication is artifact **`13485057920`**, **583,810,387 bytes**, outer ZIP SHA-256 **`c945f5350c9166becd7bb2251ed067e872d680e93de0c52883a5a54380d8711d`**. The raw upload log and official metadata agree on identity, size, digest and exact source. The large-ZIP local access limitation below still applies.
- The only non-documentation delta from `b6f4d9bf` is the unexpected-abort handler, its focused regression and the workflow test floor. I read that three-file diff and the [published independent exact-source repair review](wave5-source.md). It records typed failure for `BaseException` and re-raises the original abort; it does not alter normal build inputs or successful runtime behavior. The separately reviewed permission producer, acquisition shell/verifier/manifest and their tests remain byte-identical to the approved repair checkpoint below.
- Rechecking the final source preserves all six protected inputs, all **149 direct gitlinks**, all **24 root-owned cited blobs**, and the unchanged source lock binding **160 recursive pins and 44 LFS payloads**. Official fresh metadata additionally records success for P001 **`42180484697`**, P002 **`42180484739`** and predecessor archive readback **`42180484773`**, each at exact `4622a939`. This supports scoped predecessor continuity; it is not an independent new acceptance of their full artifact inventories.

The original final A/B archives had not yet been supplied at this preflight checkpoint. They were subsequently reviewed in the final bounded decision above. No earlier fixture, source-build or runtime output was substituted for them.

## Earlier bounded repair checkpoint: `b6f4d9bf`

**Scoped verdict: APPROVED for the uploader-permission repair and verified retained-toolchain acquisition mechanism. Fresh original-build acceptance is PENDING. This checkpoint does not pass P003 G1–G4 or advance P004.**

## Identity and exact scope

- Reviewer: `/root/wave4_build`, a distinct non-author review agent. The coordinator `/root` authored the reviewed repairs and their production tests. I added only this report and its `wave4-build/` evidence/helpers.
- Review date: **2026-11-06 UTC**. Individual observations carry exact timestamps in the linked receipts.
- Reviewed recovered-input implementation: **`b6f4d9bf04dd4a15a1b349845f962295ff350b7d`**, tree **`202dbdc59c0bd9df10804b9e3a75674508eab75d`**. All reviewed working files were independently compared byte-for-byte with this commit.
- Permission repair was introduced by **`cc268442e9711beeb117f59850dcc6526dd03c46`**. The failing control is the actual producer at **`af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`**.
- Accepted predecessor: **`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`**. Relevant unchanged child: `src/external/objc4` at **`092352cab947b410a73b5123b190df03f90c1802`**, as reviewed in [Wave 3 source review](wave3-source.md).

I read `AGENTS.md`, the README global gate contract and P003 implementation/pass gates, the actual producer and acquisition code, the focused tests, original failed job logs, small original ZIPs, official retained-artifact metadata and prior published source review. No restricted Apple material, proprietary binary internals or external implementation source was used. I did not modify production code, workflow, README, locks or dependencies, and did not commit or push.

Package nondeterminism and installed-runtime evidence have separate reviewers. This checkpoint covers the narrow repair mechanisms and continuity of the accepted inputs; it does not substitute fixture success for full builds.

## Permission repair: independently reproduced

Run `42169925661` at `af3566ee` reached both real build completions before both artifact uploads failed. The original decoded A/B logs contain the exact uploader error opening `source-status-after.txt`, following the final `16594/16594` compile step. Both logs extend through runner cleanup. I independently recomputed their complete decoded identities:

| Original job log | Decoded bytes | SHA-256 |
| --- | ---: | --- |
| A, job `127736351114` | 7,362,553 | `69b01bb9a89cd9f482b3f55c381ebb365655a5e78b978cfb5f144f8649e38989` |
| B, job `127736351115` | 7,363,195 | `c2682c12d486c9b8dfdcb812f01f5f4a3291e7c34890dbcbde2221932ff21097` |

The producer requires container UID 0; the artifact uploader runs outside that container. The prior handler created the final status file with mode `0600`. The repair creates it with `0644` and sets `0644` on the exclusively created descriptor with `fchmod`, preserving readability even with a `077` umask. It does not grant write permission to group or others.

I executed [an independent reproducer](wave4-build/reproduce_permissions.py) against the actual handlers extracted from both exact commits. Its **24 cases** comprise three implementations × two umasks (`022`, `077`) × clean/dirty source × original exit `0`/`42`. The third implementation is a controlled copy of the repair with only `fchmod` removed.

| Actual handler/control | Umask `022` | Umask `077` | Status and original failure behavior |
| --- | --- | --- | --- |
| Original `af3566ee` | `0600` | `0600` | Correct raw bytes and exit/stage retained |
| Repair `cc268442` | `0644` | `0644` | Correct raw bytes and exit/stage retained |
| Repair without `fchmod` control | `0644` | `0600` | Correct raw bytes and exit/stage retained |

All assertions passed. Dirty source still changes an otherwise successful build to failure at `source-cleanliness`; an existing exit 42 at `compile` remains exit 42 at `compile`. The exact porcelain bytes remain recorded. The control establishes why the explicit descriptor permission change is necessary.

I also independently ran the **16 focused source-cleanliness tests**, terminal plain `OK`, no skips. These exercise the actual EXIT handler, including dirty submodules hidden by Git ignore configuration, failed Git status, existing files, symlinks, directories, FIFOs, and the independent aggregate cleanliness checks. Source review confirms `O_EXCL`, `O_NOFOLLOW`, regular-file/inode checks and explicit `--ignore-submodules=none` are unchanged. `fchmod` operates on the new owned descriptor, never a pathname supplied by a preexisting symlink.

This local evidence verifies file permissions and the producer contract. It is not an actual cross-UID hosted uploader execution. Successful publication of the new original A/B archives remains necessary.

## Retained frozen input: contract and code review

README P003 G1 requires two clean builds/installs with identical source and toolchain manifests. It does not require repeated network acquisition of identical frozen inputs. Restoring a verified immutable compiler environment is compatible with that contract when both source checkouts, full builds, installations and replay remain fresh.

The original retained input is precisely identified:

| Field | Identity |
| --- | --- |
| Original run/source | `42169925661` / `af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2` |
| Official artifact | `13480314988`, `p003-toolchain-af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2` |
| Original ZIP bytes | `583808684` |
| Original ZIP SHA-256 | `08a023bcc09f0c50de36953530cd812728a55470c82e22614d072feeb93a4cfc` |
| Committed toolchain-lock SHA-256 | `aef0e952e8fe505191ce8dfaec146e7fd27036d10b52b8b4efdb76dfae319963` |
| Docker recipe SHA-256 | `9e4e70f77beb6e772c2236f23342822b242fed807d3fe9afbbd6f43ccd692f06` |

I compared those fields with the saved official Actions artifact metadata, including original run, source revision, artifact name, size, digest and unexpired status at retrieval. I independently decoded and hashed the original acquisition job log: **315,090 bytes**, SHA-256 **`1e159427f09c9cf89756724d6a04684b03e1d1503d13fa756159f634cc9108a8`**. It contains the completed frozen-environment comparison and subsequent upload/runner cleanup.

The reviewed restoration code validates the committed manifest, exact lock bytes and Docker recipe before downloading. It then requires the pinned outer ZIP size/SHA-256, exactly five regular members with no duplicates or unexpected paths, complete reads that check ZIP CRCs, a valid sealed lock, exact base/snapshot/recipe and static environment identities, exact image size/hash, and the original checksum receipt. It preserves all five original files and emits a separate origin receipt. The only existing environment normalization is the explicitly documented `dsymutil` Host CPU banner value; tool bytes, package pins and other version fields remain exact.

`acquire-toolchain.sh` downloads from the original Actions artifact endpoint with read-only access. An unavailable transfer may invoke the unchanged pinned recipe. Successful transfer followed by any integrity failure is fatal; it cannot fall back to another input. The workflow still uses two fresh hosted VMs, recursive source checkout/LFS hydration, new isolated build/runtime paths, and separate installed-archive replay. Neither build nor installed-runtime output is reused.

I independently executed the **12 focused retained-toolchain tests**, terminal plain `OK`, no skips. They perform actual ZIP/CLI/shell operations covering exact-byte restoration and receipt, permitted host observation differences, outer size/hash tampering, sealed-image tampering, compiler/package/base/snapshot/recipe changes, missing/duplicate/extra/traversing members, symlink/directory members, existing destinations, altered checksums, stale committed inputs, inner CRC corruption, transport fallback and fatal integrity errors.

### Actual hosted restoration observed

Before publishing this checkpoint, the original complete toolchain log from new run **`42177445982`**, job **`127759056901`**, became available. I independently read its exact checkout identity, executed acquisition command, full origin/file-hash receipt, artifact finalization and runner cleanup. The decoded log is **19,151 bytes**, **233 lines**, SHA-256 **`bc5570f3aa571d90b82b4f44f7c0d63f6bcd003ce511342285646fd2becb4a32`**. It records successful actual restoration at **2026-11-06T06:55:14.6590700Z** and contains no runner error record.

The full receipt's origin equals the committed manifest field-for-field. Its image config ID, **`sha256:eddd66602086a48927c87aff7b086c338f86fe6b67690b2f91f663e7646441de`**, also appears in the original `af3566ee` Docker acquisition log. It records original frozen-lock SHA-256 **`9438c463449752b1e84b45706bf0cbeec25f803eb1e46870f23908e53183421e`** and original image-archive SHA-256 **`6d98365bd067b28c8e8b71e1b34a7200bca5aad0c790cbdd808fe2f14f67d4d5`**, together with hashes of both original acquisition logs and `SHA256SUMS`.

The new publication contains the original five files plus the two acquisition receipts/logs. Both original job log and official metadata identify new artifact **`13482839624`**, **583,810,387 bytes**, ZIP SHA-256 **`19741feab50478efc961e4900dc0f3626313f866fd82996e6ee6be852d547c2c`**, bound to `b6f4d9bf` and run `42177445982`. The new outer ZIP identity is distinct because the publication adds acquisition evidence; the original image and lock identities remain explicitly bound in the restoration receipt.

**Practical evidence limit:** the original and republished frozen-toolchain ZIPs exceed the connector's 512 MiB download limit and were not locally available to this reviewer. I have not independently run CRC/image verification against those real large ZIPs locally. I reviewed the exact verifier that consumed the original ZIP on the fresh hosted runner and independently checked its complete raw receipt/provenance. The new original A/B locks and actual per-host observations must still corroborate its use. This is observed frozen-input restoration, not fresh source-build or installed-runtime acceptance.

## Failed acquisition attempts and predecessor continuity

At `cc268442`, the three unchanged acquisition attempts in run `42175768705` failed against the pinned Ubuntu snapshot, with HTTP 500/502 and then 503 responses. I independently read and hashed all three complete decoded job logs and CRC-checked their two-member original failure ZIPs. The retained failures do not show a lock or pin change. Their original metadata and hashes are in [the failure record](attempt-cc26844/preflight-and-outage.json) and the independent checkpoint receipt.

I also CRC-checked both earlier original fixture ZIPs and independently counted their distinct named cases and terminal results: **174/115/187** for `af3566ee`, **174/115/188** for `cc268442`, all terminal plain `OK`, without skipped/expected-failure substitutions. These establish focused regression execution at those revisions, not qualification at the recovered-input candidate.

Following the published [Wave 3 source review](wave3-source.md), I independently compared `b6f4d9bf` against accepted `d58cca51`: all **149 direct gitlinks**, the unchanged lock binding **160 recursive dependencies and 44 LFS payloads**, all **24 root-owned cited blobs**, `.gitmodules`, the classification producer/manifest, toolchain lock and Docker recipe retain their accepted identities. None of the additional Wave 4 production changes edits those accepted inputs. The change scope therefore does not invalidate predecessor acceptance; fresh candidate hosted evidence remains required for this campaign. No broad unrelated test expansion was used to infer acceptance.

## Evidence and exact reviewed bytes

The full path/hash map is recorded in [checkpoint.json](wave4-build/checkpoint.json). Principal repair identities are:

| Reviewed file | SHA-256 |
| --- | --- |
| `ci/logic-pro/build-p003.sh` | `9399b66268621619ad9766e2f93fa4166c67916090a106e8cd820dc8fa46dda2` |
| `ci/logic-pro/acquire-toolchain.sh` | `bf1b82540fd0938009f45279b038d3bbc441b6e270712f9db8dd9e90312b693a` |
| `tools/compat/logic-pro/restore_toolchain.py` | `27952ddaa70008bdf7527c1ef7ce9ef8450bdcaa818463f054a6746f4f2c3c9f` |
| `docs/compat/logic-pro/retained-toolchain.json` | `c4ba2b7b9cb8e4dad5774aacc9837788c40b35997a15a2e1c4a05c091c2b5761` |
| `.github/workflows/phase3-build.yml` | `356c8e3d9aa3e5e614312504ae42f289d2a29cce7f37a33bc31b6c528031859d` |

| Independent evidence | SHA-256 |
| --- | --- |
| [Checkpoint receipt](wave4-build/checkpoint.json) | `2c695bd97a3fdd0a11e42f03f04a3a6e6901aced46b757c7e92ebe27f77674af` |
| [24-case permission reproduction](wave4-build/permission-reproduction.json) | `388fdeb1ca6b64d58e6b64ffdfb6ea0d9057b2bc29d3b5d18b7d41c1b7fe8a0e` |
| [16 source-cleanliness tests](wave4-build/permission-focused.log) | `aa573a3eb4508b108be6546e69380bb7766385c9c85b357d8348d2446b8d84b3` |
| [12 retained-input tests](wave4-build/retained-focused.log) | `203c890602b7c9173f1a4da07439ac3aed0d083c5f705b927022fe5cad51f2fa` |
| [Actual hosted restoration observation](wave4-build/retained-toolchain-observation.json) | `fc369d98cccf7680febf3f52ad24fc9925c1de355832b5989ff03aef9e674de4` |
| [Complete original restoration job log, gzip](wave4-build/retained-toolchain-job.log.gz) | `4a1967204de4c2e5fc6de66b90e61da209a81b7433439d6f96de852d7a11cdfc` |

From the repository root, reproduce the bounded executable checks with:

```sh
python3 -B docs/compat/logic-pro/evidence/P003/requalification-20261106/wave4-build/reproduce_permissions.py
python3 -B -m unittest discover -s tests/compat/logic-pro/build -p test_source_cleanliness.py -v
python3 -B -m unittest discover -s tests/compat/logic-pro/build -p test_retained_toolchain.py -v
```

## Original-build work outstanding at the earlier `b6f4d9bf` checkpoint

The coordinator has identified new P003 run `42177445982` at `b6f4d9bf`. No original A/B archive from that run had been supplied at this checkpoint. I have not issued a fresh G1 or lifecycle acceptance verdict.

On receipt, the remaining bounded review must inspect original archive SHA-256/CRC and exact source/toolchain provenance; all 63 classifications; 160 child pins/161 repositories/44 LFS payloads; frozen Clang 14 code-generation proof; complete compile/install logs and compile commands, including the current objc4 header-derived debug mode; raw clean before/after source status; equal per-host first/reinstall inventories; and real uninstall removal with distinct lifecycle state. Package-byte difference and live runtime reviewers must complete their separate scopes. Historical `89c6c9d` acceptance and the failed `af3566ee` job logs do not satisfy these current-source gates.
