# P003 five-wave hardening — exact-master acceptance

**Date:** 2026-11-06T11:31:25Z  
**Independent adjudicator:** /root/w1_provenance (not an author of the implementation)  
**Scope:** P003's frozen x86_64 GUI-capable build, installation, synthetic runtime and evidence checks. **P003 G1–G4: PASS.** This is not proof of Logic Pro execution or general macOS compatibility.

## Exact source and review trail

- Implementation PR: [#12](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/12), 23 incrementally pushed commits, ten changed source/test paths, five waves of analysis, coding, and adversarial review with six reused subagent streams.
- Qualified PR head: `67530b7ea1a5fea36b3c33bf1f414599404c07ea`.
- Merged default branch: [`78454aa22fac577295b66342ac2c8a766358bc02`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/78454aa22fac577295b66342ac2c8a766358bc02); the PR head and merge have identical tracked trees.
- Premerge full six-job pass: [run 42200493978](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42200493978), independently accepted with 138 differing regular files / 6,140 differing actual bytes.
- **Exact-merged-master full six-job pass:** [run 42206518968](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42206518968). Independent original-artifact adjudication at 2026-11-06T11:31:25Z: **G1, G2, G3 and G4 all PASS**. CI's automated comparison intentionally says `READY_FOR_INDEPENDENT_REVIEW`; that is a request for this separate adjudication, not an automatic independent verdict.

## Exact-master qualification

| Gate | Independent verdict | Original evidence |
| --- | --- | --- |
| G1 — Two pinned builds and enumerated nondeterminism | **PASS** | Same exact source and locked Ubuntu 22.04/Clang 14 toolchain; two clean 16,594/16,594-step builds, 11,947 installed paths each, identical path/kind/mode/size inventories. Exactly **138 differing regular files and 4,366 differing actual bytes** across the two installed tar payloads; all 138 files were independently rehashed against both install manifests and exactly match the comparator's inventory. |
| G2 — Real framework ownership | **PASS** | Seven intended framework owners and 70 direct dependency edges per install; 21 native wrappers per install; no developer-stub substitution. Competing DYLD-loaded basename detection is now adversarially tested. |
| G3 — Real installed runtime and GUI | **PASS** | Five separate campaigns, **50 asserted cases** (two per Build A/B, one source/build-free replay); real Mach-O, Foundation, xpc lifecycle and external GUI event round-trip; ten raw XWD screenshots with nonce/state-bound window titles, complete original PNG fidelity and **100% expected RGB panel coverage**. No positive contradictory P003 errors or stub hits in original logs. |
| G4 — Isolated uninstall/reinstall and source-free replay | **PASS** | Both builds removed 11,947 entries and proved prefix absence; fresh reinstall owner nonce and inode, inventories match; a separate runner executed the exact A package without source/build mounts and proved server/namespace shutdown and seven loaded framework paths. |

All **174 P001, 115 P002 and 224 P003** named regression tests passed on the exact-master runner, with zero skips/failures. All six P003 jobs succeeded: frozen toolchain `127854439329`, fixtures `127854439586`, Build B `127854784703`, Build A `127854784764`, independent replay `127867896789`, final comparison `127868249875`.

## Original GitHub Actions artifacts

These are the **exact-master** artifacts from run `42206518968`, not the previous accepted baseline. Five ZIPs were independently downloaded, their SHA-256 recomputed and CRCs checked; individual original member/file hashes and nested installed tar byte contents were also independently checked. The large toolchain ZIP was verified by hosted acquisition and the shared recorded toolchain hash, but was **not** separately downloaded by the reviewer.

| Original artifact | GitHub artifact ID | ZIP SHA-256 |
| --- | ---: | --- |
| P001/P002/P003 fixtures (174/115/224) | 13497385639 | `013c3ffde7ee05e72064c6c72e083072b1682f720a0cff16b31bf74bb780c308` |
| Build A (459 members) | 13498707978 | `43e1e16bef074f2c2b7b6a64ede755dfd3c8896bf75a4eb486db742eab2693cf` |
| Build B (459 members) | 13498283279 | `edbd53fcd66c28911b789d4707c208cd8b14b4e2557f3c7d4be85673e51323d9` |
| Independent installed-archive runtime (48 members) | 13497449485 | `0077945d67e8a5b1e3499c903b2afbc405486df46ef21dfabd299913785bfb39` |
| Complete comparison (1 member) | 13497959285 | `7b5fe4cb8e4be2f3ef8196e1c4ae6e22919b204859475e4528b01914f8870715` |
| Frozen toolchain (hosted validated, not separately rehashed) | 13496369119 | `d41f0aa8781a960c995f07e20c2bf7e5988961e2cccec8c04c7a5ec3a3a67fa4` |

Build A nested installed tar SHA-256: `eec2cbffa501a937f0f70ca2f03008012f54f577fac6c77b7025e2d8a462e6d0`; Build B nested installed tar SHA-256: `835c8c2cba559e287db98222f2982338a421fcd5b0c74a39f98b155b3b5ba041`. Toolchain lock SHA-256: `9438c463449752b1e84b45706bf0cbeec25f803eb1e46870f23908e53183421e`. Artifact links and raw original logs remain on GitHub Actions subject to its retention settings.

## Improvements independently exercised across five waves

1. Isolated evidence outputs cannot be symlink-redirected into the installation prefix.
2. Uninstall pins parent and quarantine directory descriptors, validates inode/device after atomic rename and refuses cross-mount directory/file traversal (including same-device bind mounts); supports Ubuntu 22.04's Python 3.10 using fd-relative removal.
3. Framework image selection rejects a competing dyld-loaded basename even if the competitor is outside a conventional `.framework` path.
4. Build probes and independent comparison reject contradictory P003 error markers, screenshot recoloring/metadata forgery, invalid pixel masks and XWD window titles not bound to the correct `WAIT`/`READY` nonce.
5. Adversarial tests cover races, forged manifests/images, corrupt raw runtime output, unexpected mounts and unavailable Linux procfs, with no weakening of the original test transcript or pass criteria.

## Explicit limits and handover

- The output is **not** bit-for-bit reproducible: all 138 differing installed paths and 4,366 changed bytes are enumerated and verified; precise root causes for every byte in this particular re-run are not proven.
- P003 assumes a controlled stopped-server, no-network teardown runner. A separate hostile same-UID process retaining an open quarantined-directory descriptor could modify its contents during deletion. This does not demonstrate outside-quarantine deletion but is outside the controlled acceptance threat model.
- These probes do **not** establish unmodified Logic Pro functionality, broad macOS API parity, professional audio usability, or Xcode/iOS Simulator support.
- P004 remains **NOT PASSED**. Its separate workflow has a pre-existing test-message mismatch in the baseline (old `zero/missing` assertion versus `missing/insufficient actual` implementation); that is not a P003 failure and must be addressed as P004 work.
- Preserve the prior [formal P003 acceptance](requalification-20261106/wave5-acceptance/acceptance.json) at `4622a939` and all historical failures. This record is a later scoped hardening and fresh exact-master requalification, not a retroactive overwrite of those original artifacts.
