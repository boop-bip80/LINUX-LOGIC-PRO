# Wave 4: independent original-runtime evidence review

**Final verdict, 2026-11-06T08:02:49 UTC: G3 PASS; G4 PASS**, for exact source **`4622a9396c5c9fbe0014bdf6a2f695dcc491233c`**, tree **`9db3623bd2c81d18b17b29c921b1d6212ca1339d`**, run **42180484781**. The [final exact-source review](#final-exact-source-runtime-review) and [machine-readable verdict](wave4-runtime/final-462/summary.json) below record the acceptance, original hashes and limits. This is the runtime reviewer's G3/G4 verdict; the whole-phase decision remains separate. Earlier preparation checkpoints and the b6 rehearsal are preserved as dated work records, including their then-pending status statements.

## Initial preparation checkpoint (preserved)

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

## Next action at the initial checkpoint (preserved)

The parent reviewer will supply finalized original archives for the candidate above. This reviewer will then verify all five campaigns, retain exact report/archive/stream hashes and independently calculated values, reproduce meaningful rehashed corruptions, and replace this PENDING checkpoint with the bounded findings and verdict. **Remain in P003.**

## Pre-correction b6 method rehearsal

This section records an offline review of original hosted executions for **`b6f4d9bf04dd4a15a1b349845f962295ff350b7d`**, [run 42177445982](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42177445982). The five-campaign auditor run completed at **2026-11-06T07:38:17 UTC**; the final eight-copy corruption reproduction completed at **07:43:47 UTC**. This work is expressly a **pre-correction method rehearsal**. It does not accept the later `4622a939` implementation or mark current P003 G3/G4 passed.

**Rehearsal result: all five original b6 campaigns pass the unchanged independent auditor; all eight rehashed corruptions reject. No new runtime-evidence defect was demonstrated.** This reviewer did not launch an installed runtime locally. The original build, runtime and comparison archives were supplied by the parent reviewer, and the actual evidence was independently recalculated below rather than inferred from the producer's PASS or the aggregate READY status.

The complete [machine-readable summary](wave4-runtime/b6-method/summary.json) links and hashes all results. The [campaign invocation receipt](wave4-runtime/b6-method/campaign-receipt.json), [original archive/extraction binding](wave4-runtime/b6-method/original-binding.json), [package and reinstall cross-binding](wave4-runtime/b6-method/runtime-cross-binding.json), and [rehashed counterexamples](wave4-runtime/b6-method/rehashed-counterexamples.json) retain the detailed checks. The independent auditor remains byte-for-byte unchanged at SHA-256 `452e3fb75333f2e15b67770cea81066a4b46d3cd80fa3d8d80a89e72ac0eb046`.

### Original archives and extraction

All four complete archive SHA-256 values and byte counts were independently recomputed. Every ZIP member was read through CRC validation and compared by size and SHA-256 with its extracted counterpart: **967 members total**. The original binding receipt records every member's name, byte count, CRC and content hash.

| Original archive | Bytes | Members | SHA-256 |
| --- | ---: | ---: | --- |
| `build-a.zip` | 87,412,935 | 459 | `741afe44814f42d9f01e3ea0e1efffa56240e0e66a5443dc3b27003f3d692c93` |
| `build-b.zip` | 87,411,252 | 459 | `7c9fd88cae4f9562f24a411a394f990f73a24b3f7d83ccc6f66d9736e7c69766` |
| `independent-runtime.zip` | 36,173 | 48 | `b74d5066943485954433cdce400725346aacf26a5c109c69e8a315bf3418678c` |
| `comparison.zip` | 35,905 | 1 | `cd6cbae21d884f3aef4a78b0bb3c0c3b2ec6944cf787e7b3251cf152be1a411a` |

### All five campaigns and fifty cases

The unchanged auditor passed all **50 required cases**, checking **79 actual command records and 158 stdout/stderr streams**. The four producer campaigns each contain fifteen commands; the independent campaign contains fifteen required commands plus four original window-search/capture commands. All referenced streams were hash-checked before their contents were used.

| Original campaign and detailed result | Nonce | Independently calculated nonce FNV-1a/32 | Server PID | Start time | Cases |
| --- | --- | --- | ---: | ---: | ---: |
| [Build A, first install](wave4-runtime/b6-method/build-a-first.json) | `a280c146948537ce` | `3ed78874` | 48840 | 264778 | 10/10 |
| [Build A, reinstall](wave4-runtime/b6-method/build-a-second.json) | `8ca76d29dc7352be` | `b734a99a` | 49998 | 266542 | 10/10 |
| [Build B, first install](wave4-runtime/b6-method/build-b-first.json) | `d858d48d7da08917` | `660f21e1` | 48801 | 158502 | 10/10 |
| [Build B, reinstall](wave4-runtime/b6-method/build-b-second.json) | `98eeb6dda60b1e43` | `1a8e6698` | 49959 | 160049 | 10/10 |
| [Independent package replay](wave4-runtime/b6-method/independent-runtime.json) | `a22d8ff4df66d543` | `5b011abc` | 25 | 12870 | 10/10 |

Every producer's fixed `hello` vector independently evaluates to `4f9f2cab`; the separate replay's `foobar` evaluates to `bf9cf968`. The 64-byte `a` boundary independently evaluates to `d96f0f85` in every campaign. The actual argument vectors, expected exits and raw records also confirm all twenty required invalid-input rejections: 65-byte Mach-O input and missing arguments for each of Mach-O, Foundation and GUI, all with exit 64 and the explicit matching probe error.

Each campaign's raw Foundation stdout contains the exact nonce-bound object result (`alpha|beta|gamma`, count 3, answer 42, bytes `007fff`, absent key `nil`) and the separate xpc/vproc transaction record `1|2|1|0`. Each GUI stdout contains exactly the seven canonical framework image paths and `clicks=1 keys=16 rendered=2 acknowledged=1` for that campaign's nonce. Actual external commands establish window focus, pointer movement, one click, all sixteen nonce characters, and Return in the required sequence. Placeholder logging is explicitly enabled, and the independently scanned raw streams contain no matching stub/unimplemented-operation diagnostic.

All five nonces and all five PID/start-time identities are distinct. Each original campaign records the required successful `darling shutdown`, a live pre-shutdown server identity, server exit, namespace release and an empty post-shutdown holder list. Producer startup snapshots bind the initial server PID to the shutdown identity. The fifth campaign additionally supplies the hash-bound original `/proc` stat, whose PID and start time independently match the lifecycle record. Mount namespace strings repeat in the artifacts; they were not treated as globally unique identities or used alone to distinguish campaigns.

### Original displayed pixels and separate replay

All ten XWD images decode to **400 × 262 RGB rasters**. Before input, the left sample is `(255, 0, 0)` and the right `(0, 0, 255)`; after input, the samples are `(0, 255, 0)` and `(255, 255, 0)`. Two 5 × 5 patches in every image satisfy the fixed channel thresholds: **500 displayed pixels checked in total**. Independently decoding the corresponding PNG chunks and filtered scanlines gives exactly the same **314,400 RGB bytes per image**, or **3,144,000 bytes across all ten image comparisons**.

The original XWD window-name header in every image was separately read and checked against `P003_WAIT_<actual nonce>` or `P003_READY_<actual nonce>`. All ten titles match their campaign and state. The simple displayed color fields produce identical RGB/PNG results across campaigns; the original XWD titles and hashes bind those displays to the different challenges. No screenshot was regenerated or substituted during this review.

The previously unexercised independent-runtime branch passed unchanged. Its two raw external window searches select the same window, the two original `xwd` capture command records name the retained screenshots, its raw mount table contains no source/build tree, and the archived independent driver matches the reviewed hash `d2cf2a5d4d50d7c3e8574dbb696a7f076c2d2cb4543972ccbe3f935968ad6edc`. The allowed repository-backed mounts are the two individual reviewer files. The runtime's private namespace differs from the caller namespace.

The exact b6 workflow defines the archive replay as a separate hosted job after the builds. Its mount table identifies review container `7fdcd717b0cb4c7aa36dc3d733fbd5e53e7f976e1cc1ef9550dc929f5057e28b`, distinct from build container hostnames `095d13c6ad05` and `31c73c343141`. These are the observed container identities; this offline review does not infer physical hardware identity from them.

### Reinstall and exact package/probe bytes

Both hosts' first and second manifests contain **11,947 entries**, with identical full inventories and identical manifest bytes within each host. Each original removal receipt records 11,947 removed entries, no error and an absent installation prefix. Both second campaigns use their separate `/p003/runtime-second` prefix and `/p003/runtime-second.home`, and raw startup stderr records creation of a new Darling prefix. The independent replay uses its own `/p003/runtime-review` and controlled HOME.

The original package hashes are:

| Package | SHA-256 |
| --- | --- |
| Build A `runtime-prefix.tar.gz` | `342db8eed844a54d919f265b01992ee4b58f13dd9693507fdd207ef5ce38bf55` |
| Build B `runtime-prefix.tar.gz` | `13a8c9a679e7ed3bf7dc033a9734f120c31c18e851ff81d96b7327457de1bfb5` |

The fifth campaign's package review binds **85,637,759 bytes** of the exact Build A package to the exact first-install manifest (`f0e7b5a78e0ae92605ae8af391546716b187d91bc50de5496dee55d6cdbad30c`), with 11,947 entries and successful installed readback. Build B's first/second manifest hash is `d15d044017daa71bbbbf625e625d7e279057ad1c86927e0654c8f2e495c4ab30`.

This reviewer read all three probe executables directly from **each** original tar package, recomputed their hashes and sizes, checked their executable modes and x86_64 Mach-O executable headers, and matched them with both manifests and every runtime report. The probe bytes are identical across both packages and all five reported executions:

| Installed probe | Bytes | SHA-256 |
| --- | ---: | --- |
| `p003_macho` | 12,768 | `3d66cf7afa0d80063b788ab91f003fd0a63d3ac7ed2c19dad709714822941e08` |
| `p003_foundation` | 18,340 | `3c3dcadac262cf3df5e50e602dc0c5d36fda3c2b336ee51e4cc13e36aa8ba040` |
| `p003_gui` | 24,804 | `89a8bac8f4be431304fb17888287def9f4662071174d786924a9694c2e94309a` |

This is runtime/package binding for the rehearsal, not an independent G1 verdict about all cross-build package differences.

### Rehashed behavioral counterexamples

Four corruptions were applied independently to temporary copies of **both** the original Build A first campaign and the original separate replay. Changed stream SHA-256 and byte-count references were updated everywhere, including the separate replay's evidence inventory. Every remaining referenced file was rehashed successfully before either checker ran, and modified report hashes were recorded. The producer PASS summaries and empty error arrays remained intact.

| Corruption | Independent auditor | Exact-b6 production validator |
| --- | --- | --- |
| Replace nonce FNV output with `00000000` | Rejects independently calculated FNV mismatch | Rejects incorrect nonce computation record |
| Remove only the transaction record, retaining valid Foundation objects | Rejects missing live transaction deltas | Rejects missing `P003_TRANSACTION` record |
| Remove the `xdotool key Return` command record | Rejects missing required command evidence | Rejects missing required command evidence |
| Retain a namespace holder and set release false | Rejects retained server/mount namespace | Rejects incomplete namespace shutdown |

All **eight corrupted copies produced sixteen behavioral rejections** across the two checkers. These failures occur with valid updated file hashes, not because the checksum layer notices stale metadata. The two unmodified production-validator baselines first passed.

The comparison code was pinned to b6 for this reproduction. A preflight identity check correctly refused to use the now-changed current runner; the b6 runner was then loaded from `git show b6f4d9bf:tools/compat/logic-pro/run_build_probes.py`, without changing a production file. The inline reproduction harness initially caught only `ProbeFailure`; the required-command check correctly raises `ValueError`. Catching both intended rejection types completed the final eight-case run. This harness correction did not change the independent auditor or any production behavior, and the detailed receipt preserves it.

After the temporary copies were removed, **all 190 original runtime evidence files were rehashed and remained unchanged**. The earlier historical checkpoint and method receipts also retain their original hashes.

### Acceptance boundary at the b6 rehearsal (preserved)

The review method has now been exercised end to end on the original b6 evidence, including its independent-runtime branch and meaningful behavioral corruption. **Current runtime G3/G4 remain PENDING for `4622a9396c5c9fbe0014bdf6a2f695dcc491233c`, run 42180484781.** The parent reviewer will supply those final originals. The next review must bind and recalculate all five final campaigns and repeat critical corruption checks against those exact files. No current phase acceptance, commit, push, production edit or local installed-runtime execution is claimed here. **Remain in P003.**

## Final exact-source runtime review

### Identity, exact revision and verdict

- Reviewer: **`/root/wave4_runtime`**, a non-author of the production runtime drivers, probes and abort-receipt correction.
- Review completed: **2026-11-06T08:02:49 UTC**.
- Tested implementation: **`4622a9396c5c9fbe0014bdf6a2f695dcc491233c`**.
- Exact implementation tree: **`9db3623bd2c81d18b17b29c921b1d6212ca1339d`**.
- Original hosted execution: **[run 42180484781](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42180484781)**, attempt 1.
- Verdict: **G3 PASS and G4 PASS for this exact source, tree and run. No new runtime-evidence defect demonstrated.**

| Gate | Independent verdict | Basis |
| --- | --- | --- |
| G3: installed Mach-O computation, Foundation operation and GUI event round trip | **PASS** | All five original campaigns satisfy all ten required cases; raw computation, object, transaction, framework-image, external-input, pixel and shutdown evidence was independently checked. |
| G4: uninstall/reinstall without dependency on the previous installation | **PASS** | Both hosts remove all 11,947 inventoried entries and record an absent prefix; fresh reinstall produces the same complete inventory and repeats all ten cases. A third hosted runner executes all ten cases from the exact installed archive without source/build trees. |

This is **offline independent verification of original hosted executions**. This reviewer did not claim or perform another local installed-runtime execution. The conclusion follows from the original byte-bound streams, independent calculations, package reads, official job provenance and adversarial reproductions described below; it does not rely solely on the producer PASS summaries or the automated comparison status.

The [final machine-readable verdict](wave4-runtime/final-462/summary.json) records the scope and hashes all component receipts. The complete five auditor invocations and their exit statuses are in the [campaign receipt](wave4-runtime/final-462/campaign-receipt.json). Each returned zero with empty stderr.

### Final source binding and preserved method

The [source-binding receipt](wave4-runtime/final-462/source-binding.json) compares the actual reviewed files byte-for-byte with `git show 4622a939:<path>`, verifies the exact tree, records all relevant gitlinks, and retains the inspected runtime delta. The independent auditor remains unchanged from before these final artifacts existed, at SHA-256 **`452e3fb75333f2e15b67770cea81066a4b46d3cd80fa3d8d80a89e72ac0eb046`**. It imports no production runner, comparator, probe or image decoder.

| Final runtime source | SHA-256 |
| --- | --- |
| `tools/compat/logic-pro/run_build_probes.py` | `de3be619acc733a92190c0f7e6454e1768da864feabe5d846eadf1720f0bd508` |
| `tools/compat/logic-pro/compare_p003.py` | `e60cb440b933d5b0e89d19f40bbb80285206791d9b6062c1aaada6685193c240` |
| `tools/compat/logic-pro/review_installed_runtime.py` | `d2cf2a5d4d50d7c3e8574dbb696a7f076c2d2cb4543972ccbe3f935968ad6edc` |
| `tools/compat/logic-pro/review_package_archive.py` | `cede93530d11d2611ef43e9acb848c2a71f463cf8c7d6b3b3af5051a51c76d52` |
| `tests/compat/logic-pro/build/macho.c` | `350d965c030b7fa33ca80ebd4132ca87cd6f348922cf9e5c72b3491d0b428fd2` |
| `tests/compat/logic-pro/build/foundation.m` | `c3d2fd926dfdf4944cb9a23b12ad3de7bd979aedc9a1d5d62c8f93d26bedd6b3` |
| `tests/compat/logic-pro/build/gui.m` | `54bc9ebae6f7cfb3e58521b0976b09ad99a7a7918357ed2836e66dc65794d875` |
| `tests/compat/logic-pro/build/images.h` | `bd894d1cb17f9287cb2c8e77277baa38d2477a980a9eb7223304d5726f7549b7` |

The final runner changes its outer unexpected-error catch from `Exception` to `BaseException`, records the exception type/text and re-raises. Inspection confirms that this delta changes no successful probe expectation, transaction, GUI command, pixel or shutdown assertion. The original successful execution evidence reviewed here does not itself exercise an abort; no additional abort-path regression run is claimed by this reviewer.

The exact final gitlinks remain `cocotron` **`d89d7aa029c1ca2d297372fc7f618e9b006112d0`**, `corefoundation` **`3469fdf6904155e0efa84a6d6ca58a6986890c25`**, `darlingserver` **`498f7c14265d58d0849e144ce18fd700e8c5c989`**, `foundation` **`a8b5ab193a107712d0806b6f95bfa763be68e1f8`**, `libxpc` **`394e033333d3c253a12f08a99090c113b0917d00`** and `objc4` **`092352cab947b410a73b5123b190df03f90c1802`**. Their implementation source was not opened. The recursive submodule lock hashes to `2612d5f32262276fd1eaa8961c38f56e748c49bbbcc95c5997bf7f1f1cee206f`; the committed toolchain lock hashes to `aef0e952e8fe505191ce8dfaec146e7fd27036d10b52b8b4efdb76dfae319963`.

### Original artifacts and separate hosted runners

The [original-binding receipt](wave4-runtime/final-462/original-binding.json) records independently recomputed archive SHA-256/size, every member CRC and extracted content hash. All **967 ZIP members** were read and matched. The preserved [official metadata](wave4-runtime/final-462/metadata-final.json), SHA-256 **`d04738e9f5a6b0eaddcae8ebab30d88b2c8cec89fa67b41a7cb9a4484fd7b147`**, binds the original artifact IDs, bytes, digests and all six successful jobs to the exact final source and run.

| Original archive | Artifact ID | Bytes | Members | SHA-256 |
| --- | ---: | ---: | ---: | --- |
| `build-a.zip` | 13485932962 | 87,409,741 | 459 | `27b4a147ff1993bc6756172767cb4d60a8d4e437d5f9d85effe039571d5aa038` |
| `build-b.zip` | 13486009301 | 87,410,244 | 459 | `a7c394d71cc4d83857c0dd2988291c0b9e4bf31cb1555785c2e71dfcd6387759` |
| `independent-runtime.zip` | 13486318290 | 36,170 | 48 | `c77fdb0085e892cd39ea30b36c2e5e352a87f3f17e0d05234b5395b8c32a46a9` |
| `comparison.zip` | 13486224676 | 35,804 | 1 | `92fac49f42ffc2e03d267cef76f4bdc2841803b0a429c38b9f216475e8012915` |

The actual build and replay jobs have **three distinct official runner IDs**, all labeled `ubuntu-22.04`. The observed container identities independently differ as well:

| Execution | Official job ID | Official runner ID | Observed container hostname/ID |
| --- | ---: | ---: | --- |
| Build A, first and reinstall | 127768936785 | 1000004332 | `9c5c302ffed2` |
| Build B, first and reinstall | 127768936725 | 1000004331 | `57121cab165e` |
| Independent archive replay | 127779824418 | 1000004339 | `7012e31fd3b9a452f4c057bd6e40c4d89af8a6e6ff1c0d89cc4aa5881184b2df` |

The exact workflow and the raw replay mount table agree on the separate review job. The table shows the installed archive, first manifest, frozen toolchain lock, empty review/evidence locations and the two individual reviewer files; no source or build directory is retained. The hash-bound archived independent driver, controlled environment and original process stat all pass the independent audit. This establishes the recorded separate hosted execution without inferring physical machine identity from container names.

### Independently calculated final runtime results

All **50 cases** were checked against **79 command records and 158 original stdout/stderr streams**. Each case below is an actual final hosted execution, not a historical rehearsal or parser fixture.

| Campaign and full audit result | Actual nonce | Independently calculated FNV-1a/32 | Server PID | Start time | Cases |
| --- | --- | --- | ---: | ---: | ---: |
| [Build A first](wave4-runtime/final-462/build-a-first.json) | `e8c97e3cfebf2908` | `5e3ab9f6` | 48781 | 157832 | 10/10 |
| [Build A reinstall](wave4-runtime/final-462/build-a-second.json) | `7b8a7639a7762a62` | `15d50d12` | 49939 | 159181 | 10/10 |
| [Build B first](wave4-runtime/final-462/build-b-first.json) | `b04fa23a2b787356` | `a8f50958` | 48794 | 191123 | 10/10 |
| [Build B reinstall](wave4-runtime/final-462/build-b-second.json) | `fec34391e9d92379` | `770ea7cf` | 49952 | 192972 | 10/10 |
| [Independent archive replay](wave4-runtime/final-462/independent-runtime.json) | `19449b3bb9e3e094` | `46799d1c` | 25 | 22883 | 10/10 |

The fixed computation vectors independently evaluate to **`4f9f2cab` for `hello`** and **`bf9cf968` for `foobar`**. The 64-byte `a` boundary is **`d96f0f85`** in all five campaigns. All fifteen computation outputs match those independent calculations and the exact actual inputs. All twenty invalid-input cases use their required argument vectors, return **64**, emit their explicit probe error and emit no success record.

Every Foundation stream contains the exact sorted object/dictionary/data result and the same campaign's separate **`deltas=1|2|1|0`** transaction record. Each GUI stream contains exactly the seven canonical AppKit, Foundation, CoreGraphics, CoreText, ImageIO, QuartzCore and AudioToolbox paths, followed by the exact nonce-bound acknowledgement. AppKit and Foundation resolve to version `C`; the other five to version `A`, under `/System/Library/Frameworks`.

The actual external `xdotool` commands establish the XTest input path: focus and pointer movement, one click, all **sixteen actual nonce characters**, and Return. Their argument vectors, order and exit codes were checked, along with the final `clicks=1 keys=16 rendered=2 acknowledged=1` record. The independent replay's additional window-search and capture streams identify the same window before and after input. Stub diagnostics are explicitly enabled, and independent inspection of the raw streams finds no required stub/unimplemented-operation diagnostic.

All five nonces and all five server PID/start-time identities are distinct. Every actual shutdown exits successfully, records the prior live server identity, confirms server exit and an empty namespace-holder list, and records namespace release. Producer startup process traces match the respective shutdown PID; the separate replay's original `/proc` stat independently matches PID 25 and start time 22883. Namespace strings alone were not treated as unique identity: the producer records reuse `mnt:[4026532320]`, while the distinct PID/start-time and host context establish the separate servers.

### Original displayed pixels

The independent decoder checks all ten original XWD files and separately decodes the original PNG chunks and scanlines. Every raster is **400 × 262**, with **314,400 identical RGB bytes** between XWD and PNG. That is **3,144,000 compared RGB bytes** across the five before/after pairs.

Before input, the displayed left/right samples are exactly **red `(255, 0, 0)` / blue `(0, 0, 255)`**. After input they are exactly **green `(0, 255, 0)` / yellow `(255, 255, 0)`**. Two 5 × 5 patches per image satisfy the fixed color thresholds, giving **500 displayed pixels** independently checked. Every original XWD window-name header equals `P003_WAIT_<actual nonce>` or `P003_READY_<actual nonce>` for its actual campaign. The ten title bindings and original XWD hashes are retained in the [cross-binding receipt](wave4-runtime/final-462/runtime-cross-binding.json).

These are original recorded X11 captures, not regenerated screenshots. The verifier compared the entire RGB rasters in addition to the asserted color regions, and the image decoder did not import or call the production PNG encoder.

### Fresh reinstall and exact package/probe binding

On both build hosts, first and second inventories contain **11,947 entries** and are identical in every entry; the manifest bytes are also identical within each host. Each original removal receipt records 11,947 removed entries, an absent installation prefix and no error. The second campaigns use fresh `/p003/runtime-second` and `/p003/runtime-second.home`, with raw startup output recording creation of a new Darling prefix. The separate replay uses `/p003/runtime-review` and its own controlled HOME, on the third runner described above.

| Original package | Bytes | SHA-256 |
| --- | ---: | --- |
| Build A `runtime-prefix.tar.gz` | 85,637,318 | `a909db932897b151255388949273f3e5bc41e4e55fc8c48ae4f5e73bc89e2ad3` |
| Build B `runtime-prefix.tar.gz` | 85,635,689 | `106d4fe3504e5887e5f5f358144b1186031f3dff4ae1d7a1dee21dd364af436c` |

Build A's first/reinstall manifest hash is **`4cbbdf89bcf138ea006fb5ce9fadabfb3f0425220f2d60126c1972a8314ebf5f`**. Build B's is **`670345603110da9eef1fab28977ef147d831ed6bda0f1580e64f2e10f0dd9ec8`**. The independent package receipt binds the exact 85,637,318-byte Build A archive to that exact manifest, 11,947 entries, destination `/opt/darling-p003` and successful installed readback. The three retained runtime toolchain locks are identical.

All three probe executables were independently read directly from **each** original package. Their hashes, sizes, executable modes and x86_64 Mach-O executable headers match both install manifests and every runtime report:

| Probe | Bytes | SHA-256 |
| --- | ---: | --- |
| `p003_macho` | 12,768 | `3d66cf7afa0d80063b788ab91f003fd0a63d3ac7ed2c19dad709714822941e08` |
| `p003_foundation` | 18,340 | `3c3dcadac262cf3df5e50e602dc0c5d36fda3c2b336ee51e4cc13e36aa8ba040` |
| `p003_gui` | 24,804 | `89a8bac8f4be431304fb17888287def9f4662071174d786924a9694c2e94309a` |

The package archives are not byte-identical across hosts. This review binds the runtime tests and replay to their actual package contents; it does not substitute for the separate G1 nondeterminism review.

### Critical behavioral rejection on final originals

The [final counterexample receipt](wave4-runtime/final-462/rehashed-counterexamples.json) records the bounded repetition of the four previously defined corruptions on temporary copies of final Build A first-install evidence and final independent replay evidence. All changed stream hash/size references were updated, including duplicate references in the replay's evidence inventory; all remaining referenced files verified before the behavioral checks. Modified report hashes are retained, and the original PASS summaries were deliberately left intact.

| Final corruption, applied to both evidence families | Independent auditor result | Exact-462 production validator result |
| --- | --- | --- |
| Replace actual nonce FNV with `00000000` | Rejects wrong independently calculated result | Rejects incorrect computation record |
| Delete only the live transaction record | Rejects missing transaction deltas | Rejects missing `P003_TRANSACTION` record |
| Delete the external Return command record | Rejects incomplete command evidence | Rejects incomplete command evidence |
| Record a retained namespace holder and release false | Rejects retained namespace | Rejects incomplete shutdown |

All **eight corrupted copies caused sixteen semantic rejections**. Both unmodified production-validator baselines first passed, and all production modules used for the negative replay were byte-bound to **4622a939**, including the final runner hash. These are behavioral failures with correct updated file hashes, not stale-checksum failures. The unchanged independent auditor also performed each rejection independently of the production validators.

After temporary-copy cleanup, all **190 original runtime evidence files** were independently rehashed and remained unchanged. Earlier historical and b6 method artifacts retain their original hashes; the b6 summary remains `35a4514b507572aa975e57cf8e3a5d9c02f06b49f4b1e2fff7f8f3c0525d4c39`.

### Limits and handoff

**G3 and G4 are accepted for the exact final source, tree and original run stated above.** The accepted scope is the P003 purpose-built x86_64 runtime computation, Foundation/transaction operation, visible GUI event round trip and clean installation/replay boundary on the recorded privileged Linux/X11 environments. It makes no claim about running Logic, later-phase APIs, audio hardware, native macOS behavior, or another source revision.

This reviewer does not independently decide G1's complete package nondeterminism inventory, G2's complete component ownership audit, or the whole P003 phase. Those remain the separate reviewers' and final whole-phase reviewer's decisions. The successful artifacts also do not separately exercise the abort-receipt failure path; its small source delta was inspected here, without claiming another regression run.

No restricted source or proprietary Apple binary was inspected. No original artifact was modified, no production/README/workflow file was edited, and no commit or push was made by this reviewer. The parent can publish this report and `wave4-runtime/final-462/` immediately for the final whole-phase review. No further runtime work is required for this bounded G3/G4 verdict unless that review identifies a concrete discrepancy.
