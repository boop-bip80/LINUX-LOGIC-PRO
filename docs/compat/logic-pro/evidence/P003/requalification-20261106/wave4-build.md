# Wave 4 independent build review — repair checkpoint

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

## Original-build review remains pending

The coordinator has identified new P003 run `42177445982` at `b6f4d9bf`. No original A/B archive from that run had been supplied at this checkpoint. I have not issued a fresh G1 or lifecycle acceptance verdict.

On receipt, the remaining bounded review must inspect original archive SHA-256/CRC and exact source/toolchain provenance; all 63 classifications; 160 child pins/161 repositories/44 LFS payloads; frozen Clang 14 code-generation proof; complete compile/install logs and compile commands, including the current objc4 header-derived debug mode; raw clean before/after source status; equal per-host first/reinstall inventories; and real uninstall removal with distinct lifecycle state. Package-byte difference and live runtime reviewers must complete their separate scopes. Historical `89c6c9d` acceptance and the failed `af3566ee` job logs do not satisfy these current-source gates.
