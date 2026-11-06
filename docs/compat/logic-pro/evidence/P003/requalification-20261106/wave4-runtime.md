# Wave 4: independent original-runtime evidence review

## Current checkpoint

- Reviewer: `/root/wave4_runtime`, a non-author of the production runtime drivers, probes and Wave 3 review.
- Checkpoint date: **2026-11-06 UTC**.
- Candidate: **`b6f4d9bf04dd4a15a1b349845f962295ff350b7d`**.
- Hosted campaign: **[run 42177445982](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42177445982)**.
- Verdict: **PENDING original evidence. No current runtime G3/G4 acceptance.**
- Independently reproduced implementation defects at this checkpoint: **none**.

This checkpoint records code and oracle preparation. It does not claim that this reviewer executed an installed Darling runtime locally, that any of the five new hosted runtime campaigns passed, or that an earlier reviewer's tests were rerun. The parent reviewer reports that exact frozen-input restoration and the 174/115/200 hosted regression suites have passed and both fresh build checkouts are active. Those parent-reported results are not substitutes for the original runtime evidence assigned to this reviewer.

The reviewer read `AGENTS.md`, the README global gate contract and P003 requirements, the three probe sources and framework image helper, the production runner, the independent runtime/archive drivers and the evidence comparator. No restricted source, Apple binary, proprietary application, or dependency implementation source was inspected. No production file, dependency pin, workflow or README was changed by this reviewer.

## Independently recomputed source binding

The following SHA-256 values were recomputed from the checked-out files while `git rev-parse HEAD` returned the candidate above. They match the runtime file identities recorded in the separately authored [Wave 3 review](wave3-runtime.md). Matching source bytes establish continuity of the reviewed runtime method; they do not establish a fresh runtime result.

| Path | SHA-256 |
| --- | --- |
| `tools/compat/logic-pro/run_build_probes.py` | `3e778e7fe42fb2897b2f7244490008361f964d02fe17816c1729d6d69d9df541` |
| `tools/compat/logic-pro/compare_p003.py` | `e60cb440b933d5b0e89d19f40bbb80285206791d9b6062c1aaada6685193c240` |
| `tools/compat/logic-pro/review_installed_runtime.py` | `d2cf2a5d4d50d7c3e8574dbb696a7f076c2d2cb4543972ccbe3f935968ad6edc` |
| `tools/compat/logic-pro/review_package_archive.py` | `cede93530d11d2611ef43e9acb848c2a71f463cf8c7d6b3b3af5051a51c76d52` |
| `tests/compat/logic-pro/build/macho.c` | `350d965c030b7fa33ca80ebd4132ca87cd6f348922cf9e5c72b3491d0b428fd2` |
| `tests/compat/logic-pro/build/foundation.m` | `c3d2fd926dfdf4944cb9a23b12ad3de7bd979aedc9a1d5d62c8f93d26bedd6b3` |
| `tests/compat/logic-pro/build/gui.m` | `54bc9ebae6f7cfb3e58521b0976b09ad99a7a7918357ed2836e66dc65794d875` |
| `tests/compat/logic-pro/build/images.h` | `bd894d1cb17f9287cb2c8e77277baa38d2477a980a9eb7223304d5726f7549b7` |

Relevant gitlinks read from the candidate tree, without opening their source:

| Dependency | Commit |
| --- | --- |
| `src/external/cocotron` | `d89d7aa029c1ca2d297372fc7f618e9b006112d0` |
| `src/external/corefoundation` | `3469fdf6904155e0efa84a6d6ca58a6986890c25` |
| `src/external/darlingserver` | `498f7c14265d58d0849e144ce18fd700e8c5c989` |
| `src/external/foundation` | `a8b5ab193a107712d0806b6f95bfa763be68e1f8` |
| `src/external/libxpc` | `394e033333d3c253a12f08a99090c113b0917d00` |
| `src/external/objc4` | `092352cab947b410a73b5123b190df03f90c1802` |

The independently hashed recursive submodule lock is `2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`; the toolchain lock is `aef0e952e8fe505191ce8dfaec146e7fd27036d10b52b8b4efdb76dfae319963`.

## Fixed review method and remaining evidence

All five campaigns require independent examination: first install and fresh reinstall on each of two build hosts, followed by a separate source/build-free host using the retained installed package. The expected total is **50 cases**, ten in each campaign.

| Area | Independent check to apply to original evidence |
| --- | --- |
| Computation | Recompute FNV-1a/32 over `hello` (producer) or `foobar` (separate reviewer), each actual 16-character nonce and 64 `a` bytes. Require exact nonce-bound records from hash-checked raw stdout. |
| Invalid input | Check the actual no-argument Mach-O/Foundation/GUI invocations and the 65-byte Mach-O input, explicit probe error records, exit 64, and absence of a success record. |
| Foundation and transactions | Require the exact sorted array/dictionary/data/absent-key record and live xpc/vproc deltas `1|2|1|0`, bound to that campaign's nonce. |
| Framework ownership | Require exactly the seven canonical AppKit, Foundation, CoreGraphics, CoreText, ImageIO, QuartzCore and AudioToolbox image paths in raw GUI stdout. |
| External GUI input | Check actual X11 window identity, focus, pointer movement, one click, all 16 nonce characters, and external Return command; require the exact final acknowledgement record. |
| Pixels | Independently decode original XWD pixels and PNG chunks/scanlines; compare the full RGB rasters and check red/blue before input and green/yellow after input with the existing channel tolerances. |
| Lifecycle | Check the actual shutdown command and process identity, startup/process evidence where retained, server exit and empty namespace-holder result; require separate campaign nonces and server identities. |
| Reinstall and replay | Bind first/second installation manifests, explicit removal and fresh paths, package/probe bytes, separate host identity, mount table and archived independent driver to the exact candidate. |
| Behavioral rejection | On temporary copies of new originals, update affected hashes after corrupting runtime behavior (for example FNV, transaction/Return evidence, or namespace release), and verify rejection beyond checksum mismatch. Preserve original artifacts unchanged. |

The earlier `af3566ee` hosted run did not finalize its build artifacts because upload failed on `source-status-after.txt`; its PASS summaries do not satisfy this review. The three `cc268442` toolchain acquisition failures also supply no fresh runtime acceptance. Historical `89c6c9d` files may be used solely to rehearse the independent decoder, with that use explicitly identified separately from current acceptance.

## Completed bounded method check

At **2026-11-06T07:03:21 UTC**, this reviewer ran the new [independent evidence auditor](wave4-runtime/audit_runtime.py) once against the retained original `build-a/probes-first` campaign from historical run `41292343355`, exact implementation `89c6c9d85aba6ed1662035e6366298c92ef9c970`. The invocation, exit status and content hashes are retained in [the method receipt](wave4-runtime/historical-method-receipt.json), with [the complete calculation result](wave4-runtime/historical-method-qa.json) and [stderr](wave4-runtime/historical-method-qa.stderr.txt). Exit status was `0`; stderr was empty. This is a method rehearsal, **not current-candidate runtime evidence**.

The helper imports no production runner, comparator, probe, or image decoder. It independently hashes each referenced stream, checks the actual argument vectors and required exits, calculates FNV, parses the runtime records, compares the three probe identities against the installation manifest, checks retained lifecycle/startup observations, and decodes XWD and PNG through separate routines. Its independent-replay branch also checks the original host search/capture commands, mount table, archived driver and pre-shutdown process stat; that branch awaits the new fifth campaign and is not claimed as exercised by this one producer-campaign rehearsal.

| Historical rehearsal observation | Independently calculated result |
| --- | --- |
| Cases checked | 10 required cases; 15 command records and all their original stdout/stderr hashes |
| Known vector `hello` | `4f9f2cab` |
| Actual historical nonce `5a92669296f99425` | `e0573625` |
| Boundary of 64 `a` bytes | `d96f0f85` |
| Before-input pixels | 400 × 262; left `(255, 0, 0)`, right `(0, 0, 255)` |
| After-input pixels | 400 × 262; left `(0, 255, 0)`, right `(255, 255, 0)` |
| Full image comparison | All 314,400 RGB bytes match between original XWD and independently decoded PNG in each state |
| Color regions | Fifty pixels per state, in two 5 × 5 patches, satisfy the fixed channel tolerances |

The helper SHA-256 at this rehearsal is `452e3fb75333f2e15b67770cea81066a4b46d3cd80fa3d8d80a89e72ac0eb046`; the full calculation output hashes to `065abbb4fd65cd1c7adab6dbe9456f13588c064dfe49f90b47eddd20a4e10ed1`. No installed runtime was launched by this offline check. Original historical files were only read. Rehashed behavioral corruption of the **fresh** evidence remains pending with the five actual campaign reviews.

## Next action

The parent reviewer will supply finalized original archives for the candidate above. This reviewer will then verify all five campaigns, retain exact report/archive/stream hashes and independently calculated values, reproduce meaningful rehashed corruptions, and replace this PENDING checkpoint with the bounded findings and verdict. **Remain in P003.**
