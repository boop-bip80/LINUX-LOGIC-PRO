# MAC-OS-EMULATION: Logic Pro on x86_64 Linux

## Project goal and present status

**This README is the implementation plan, acceptance contract, progress ledger, and handover document for making Logic Pro work on x86_64 Linux. It replaces the previous general Darling introduction. It does not announce working Logic Pro support.**

There are two consecutive delivery targets:

1. **Short-term target — Intel:** run the newest **verified x86_64-compatible** macOS Logic Pro release on an **x86_64 Linux host**, with the complete set of first-party workflows that the same build supports on a reference Intel Mac, and an explicitly qualified catalog of third-party plug-ins and devices.
2. **Long-term target — Apple silicon:** run the latest qualifying **ARM64/Apple silicon Logic Pro release on that same x86_64 Linux architecture**, including its Apple silicon features. This requires an ARM-to-x86 execution engine as well as compatible Darwin services and frameworks. Running Darling on an ARM Linux computer is useful research, but does not meet this target.

The practical meaning of “fully working” is specified below. A window appearing, a missing symbol being added, a demo producing sound, or a package compiling is an intermediate result. None is sufficient for either release claim.

| Project field | Current value |
| --- | --- |
| Plan publication date | 2026-10-31 |
| Source baseline inspected | [`3447ff5ab8e837ea54a13a506c60d34d77e2bd15`](https://github.com/boop-bip80/MAC-OS-EMULATION/tree/3447ff5ab8e837ea54a13a506c60d34d77e2bd15) |
| Implementation phases | 96, numbered P001–P096 |
| Phases passed | **2 / 96 accepted at current implementation `d58cca51`: P001 and P002.** P001 was independently accepted at 04:06:14 UTC and P002 at 04:29:24 UTC on 2026-11-06. [Ordered acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/ordered-acceptance.json). Historical P001/P002/P003 acceptance at `89c6c9d` remains preserved. |
| Current phase | **P003 ACTIVE: current-source build/install/runtime requalification in five waves.** P001 and P002 remain accepted at `d58cca51`; P003 has no current acceptance. [P003 campaign](docs/compat/logic-pro/evidence/P003/requalification-20261106/README.md). P004 remains NOT PASSED. |
| Latest Intel-compatible Logic build | **Unverified; resolve in P005 using actual binaries and native execution** |
| Latest ARM Logic build to qualify | **Preliminary release research in P005; complete binary manifest and native reference required in P069** |
| Actual Logic execution on this fork | **Not demonstrated by this audit** |
| Intel release qualification | NOT STARTED; release gate P068 |
| ARM-on-x86 release qualification | NOT STARTED; release gate P096 |
| Latest verified implementation | P001/P002 remain independently accepted at [`d58cca51`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/d58cca513559cfef0ff9af59aa5dc3b6341bdf77). P003 `8a222c7d5` passed hosted 174/115/155 preflight tests but failed actual configuration. The combined candidate [`af3566e`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2) passes local and hosted **174/115/187**, including the current Objective-C adapter repair; [full run 42169925661](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42169925661) completed both builds and producer runtime probes but **failed artifact publication**. The final source-status file permission is repaired for a fresh full rerun. [Exact local code hashes and transcripts](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave2-integration.json). |
| Last accepted P001/P002 verification | **Current, exact `d58cca51`:** P001 G1–G4 accepted **2026-11-06 04:06:14 UTC** by `/root/wave4_p001_evidence`; P002 G1–G4 accepted **04:29:24 UTC** by `/root/wave5_final_replay`, after public final source approval. [P001](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-p001/acceptance.json), [P002](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json). |
| Current build blocker | Both `af3566e` build jobs failed when the uploader could not read root-owned `source-status-after.txt`. The new file now receives exact mode 0644 through its exclusively created descriptor, with restrictive-umask and failure-preservation regression coverage. Original runner logs are retained; fresh archives and all current G1–G4 acceptance remain required. |
| Historical regressions | `5e08de5` failed P001 source citations and blocked P003. Starting source `c7ef7fe4` additionally advanced 14 recursive pins beyond the accepted lock; both [P002 jobs in run 42150490608](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42150490608) failed. [Original failed artifacts and explicit pin review](docs/compat/logic-pro/evidence/P002/requalification-20261105/README.md) remain preserved. |
| Current implementation owner | P003 `/root`, with three distinct subagent assignments per wave across five planned waves. [Current wave ledger](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave-ledger.json). The completed P002 campaign remains separately preserved. |
| Next required action | Run the combined candidate through both frozen-toolchain builds, live probes, uninstall/reinstall and the independent installed-archive replay. Wave 3 code/method review is complete; Waves 4–5 must independently reproduce and accept all fresh G1–G4 evidence. **Remain in P003.** |

**All source findings in this initial document are static findings at the recorded revision. No Logic binary, sound library, reference Mac result, Linux audio measurement, or end-to-end execution result was supplied for the audit.** Therefore the first actual failure encountered by a particular Logic installation remains unknown. The plan deliberately starts by making that failure reproducible.

### What this repository actually is

This is a fork of [Darling](https://github.com/darlinghq/darling): a macOS application compatibility runtime for Linux. Its existing design combines a Mach-O loader, `dyld`, Darwin/Mach services, and reimplemented frameworks. It does not currently provide a complete bootable macOS machine. This plan interprets the requested result as **loading and running the Logic application and its supporting processes on Linux**, rather than booting a macOS desktop. The application route fits the repository's existing design. See Darling's [system-call architecture](https://docs.darlinghq.org/internals/basics/system-call-emulation.html).

The ARM delivery path adds two distinct requirements: execute ARM instructions on x86 hardware, and satisfy the Apple ARM ABI and Darwin application environment. A CPU translator alone does not supply AppKit, CoreAudio, Audio Units, Mach IPC, or Logic's other dependencies. Likewise, adding ARM compilation targets to Darling alone does not execute ARM instructions on an x86 CPU. The architectural separation must remain explicit throughout the work.

## Research findings that determine the plan

### “Latest” must be verified, not guessed

On the research date, Apple's [Logic release notes](https://support.apple.com/en-us/109503) identify **12.4** as the current release. However, the [Logic product page](https://www.apple.com/logic-pro/), [one-time-purchase Mac App Store listing](https://apps.apple.com/us/app/logic-pro/id634148309?mt=12), and [Creator Studio listing](https://apps.apple.com/us/app/logic-pro-make-music/id1615087040?platform=mac) do not present identical platform requirements. Product marketing and a minimum macOS version do not prove which architecture slices are in a particular downloadable app and all of its helpers.

**This plan does not invent a “last Intel version,” and does not assume that 12.4 is ARM-only.** P005 must inspect the actual release/channel, `CFBundleShortVersionString`, `CFBundleVersion`, Mach-O CPU types/subtypes, minimum OS load commands, nested executables, bundled frameworks, extensions, helpers, content compatibility, and successful reference execution. If the newest current build contains a usable Intel slice and supports the reference Intel environment, it is the short-term target. If it does not, record the newest evidenced compatible build and the evidence for why newer candidates do not qualify. An inaccessible build is “unverified,” not proof that it lacks Intel support.

Apple identifies features such as Stem Splitter, ChromaGlow, and particular Mastering Assistant processing options as requiring Apple silicon; see [the official feature restrictions](https://support.apple.com/en-us/120406). A feature absent on the reference Intel configuration is not an Intel-runtime failure. It remains part of the ARM target when present in that target's native feature inventory. Every claim must identify the exact build, distribution channel, native comparison environment, and verification date.

### Confirmed gaps and why they matter

The table below records concrete starting points. It is an implementation map, not an assertion that every listed function is necessarily reached by every Logic project. P007 and P008 establish actual dependency and execution reachability.

| Area | Evidence at the baseline | Consequence and required work |
| --- | --- | --- |
| Reproducible source checkout | [`.gitmodules`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/.gitmodules) contains 149 relative submodule URLs. Checks of representative fork-relative destinations for Darling's server, Cocotron, and Metal returned unavailable repositories. | Verify every URL and pinned commit from a fresh clone. Use explicit accessible upstream URLs for unmodified dependencies and real owned forks for modified dependencies. Do not replace pinned commits with floating branch tips. |
| Architecture support | [`cmake/architecture.cmake`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/cmake/architecture.cmake) selects x86_64/i386; [`mldr.c`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/startup/mldr/mldr.c) contains an ARM `#error TODO: arm` path. | Finish the Intel environment first; the ARM route needs loader, ABI, runtime, and ARM-to-x86 execution work. |
| Host time and audio clock | [`HostTime.mm`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/CoreAudio/HostTime.mm) returns zero from `AudioGetCurrentHostTime`; hardware time functions contain placeholder behavior. | Transport, MIDI timestamps, full-duplex alignment, latency reporting, and scheduling need one coherent clock model. |
| Audio data layout | [`AudioHardwareImpl.cpp`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp) multiplies bytes per frame by sample rate; it also contains hardcoded 44.1 kHz properties and unimplemented listeners. | Stereo interleaved float32 should have 8 bytes per frame, not 352,800 at 44.1 kHz. Correct units, format negotiation, property sizes, notifications, and device state before interpreting playback results. |
| Audio callback safety and timing | [`AUHAL.cpp`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/CoreAudioComponent/AUHAL.cpp) has callback waits/allocations, unfinished planar handling, and frame-count problems; [Pulse output](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/CoreAudio/pulse/AudioHardwareStreamPAOutput.cpp) uses placeholder timestamps and fixed channel assumptions. | Rework the host bridge and buffer ownership. A functioning desktop audio output is not proof of stable DAW recording or monitoring. |
| Audio Unit lifecycle | [`AudioComponent.mm`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/AudioToolbox/AudioComponent.mm) does not complete asynchronous instantiation and reports validation passed without actual validation. | Implement callback completion and meaningful validation. Passing a registration or validation stub cannot qualify a plug-in. Existing component loading/factory code is useful and should be preserved. |
| MIDI and graph execution | [`CoreMIDI.m`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/frameworks/CoreMIDI/src/CoreMIDI.m) has generic null-returning API stubs; [`MusicDevice.cpp`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/AudioToolbox/MusicDevice.cpp) returns unimplemented errors; [`AUGraph.cpp`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/AudioToolbox/AUGraph.cpp) contains only an include. | Implement typed ABI-correct MIDI services, scheduled instrument events, and the graph APIs actually reached by the target. |
| DSP correctness | [`vDSP.c`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/frameworks/Accelerate/vecLib/vDSP/src/vDSP.c) contains hundreds of active stub bodies; BLAS, vMisc, and BNNS also have extensive placeholders. | Audio math must return correct samples, not merely export symbols. Add numerical oracle tests for reachable vector, FFT, filtering, matrix, and model operations. Preserve already real implementations. |
| Audio files and queues | [`ExtendedAudioFile.cpp`](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/CoreAudio/AudioToolbox/ExtendedAudioFile.cpp) is largely unimplemented; queue execution has unimplemented paths. | Recording, sample streaming, conversion, seeking, and offline bounce require explicit functional and failure-path coverage. Existing FFmpeg converter scaffolding is a starting point. |
| GUI/compositing | Cocotron's pinned [`CALayer.m`](https://github.com/darlinghq/darling-cocotron/blob/c8d38d16a9f613d300157bebbab2b9501bc0c274/QuartzCore/CALayer.m) and [`CATransaction.m`](https://github.com/darlinghq/darling-cocotron/blob/c8d38d16a9f613d300157bebbab2b9501bc0c274/QuartzCore/CATransaction.m) have unfinished display/transaction behavior; [`IOSurface` XPC support](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/src/frameworks/IOSurface/src/api.m) is incomplete. | Complete actual AppKit, layer, text, input, sharing, and graphics behavior used by Logic and plug-in editors. There is useful GUI code already; the problem is incomplete behavior. |
| Graphics and modern compute | The pinned [Metal build](https://github.com/darlinghq/darling-metal/blob/ae20248dc144beab899e38752f5a530f28a0ea56/CMakeLists.txt) has an initial Vulkan-backed implementation and a dummy MetalPerformanceShaders target. Private compute frameworks also contain many stubs. | Measure required Metal/shader/model paths. Do not assume that a framework's presence implies working rendering or Apple silicon features. |
| Evidence and CI | Existing [workflow definitions](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/.github/workflows/actions.yaml) primarily build/package; no supplied end-to-end Logic qualification results establish this goal. | Add reproducible compatibility probes, native comparisons, actual Logic workloads, deadline measurements, and independently reviewed evidence. |

Historical [Darling Logic issue #935](https://github.com/darlinghq/darling/issues/935) is useful for regression ideas, including missing-framework failures. Its older Logic versions and reports do not establish the first failure of the present target. Similarly, [Darling ARM work](https://github.com/darlinghq/darling/pull/1753) and [VibeDarling](https://github.com/VibeDarling/darling) are research candidates, not evidence that this fork already supports modern Logic or ARM execution on x86.

## Acceptance contract: what “fully working” means

### Scope that cannot silently shrink

P005 and P006 must freeze a complete native feature/workflow inventory for the Intel target, derived from the selected version's application, manual, release notes, available content, and reference runs. P069 must do the same for the then-current ARM target, including its Apple silicon features. Every applicable first-party function must map to one or more tests: project creation and exchange; track/channel-strip types; recording; playback; editing; MIDI; stock instruments/effects; automation; routing; tempo; sound-library workflows; plug-in hosting; save/recovery; export; video/scoring; surround/spatial functions; and version-specific features. Early ARM research is useful, but unavailable ARM binaries or reference hardware must not block a fully evidenced Intel phase whose scope does not require them.

Do not trim this inventory to match what happens to work. The phase structure groups implementation work; it does not excuse an unlisted capability. A newly discovered native capability is added to the inventory and assigned to a phase before that phase or release can pass. A genuinely native-unavailable feature can be marked `NATIVE_NOT_APPLICABLE` only with build-specific reference evidence and reviewer approval. “Not implemented,” “no test hardware,” “no licensed plug-in,” “service unreachable,” and “not tested” are **BLOCKED**, not not-applicable.

Third-party software and physical devices form explicitly named, versioned qualification catalogs. A full first-party release claim may identify a finite supported plug-in/device catalog; it must never imply every existing or future product is supported. The catalog must include representative complex AUv2/AUv3 plug-ins, instruments, effects, protected legitimate installations where selected, and relevant interface classes. Any advertised product must pass all of its required workflows. Architecture support and service availability are recorded separately.

### Proposed minimum qualification profile

These are **future pass requirements**, not measurements of the current repository. P006 records the exact hardware and project fixtures needed to make them reproducible; later phases may tighten them with evidence. A weaker profile requires an explicit scope-change entry and cannot retain an unchanged “fully working” claim.

| Dimension | Required proof |
| --- | --- |
| Host | Named x86_64 CPU, RAM, kernel, distribution, filesystem/storage, display stack, GPU/driver, host audio service, interface firmware, and runtime/submodule versions. No undocumented host tuning. |
| Format matrix | At least 44.1, 48, and 96 kHz where the reference device supports them; integer and float file paths; stereo and applicable multichannel layouts; all required interleaved/planar boundaries. |
| Live profile | Defined small live-monitoring project at 48 kHz with 64- and 128-frame buffers on the qualified reference interface; record actual round-trip latency and callback deadlines. Device/profile inability is a documented blocker until resolved or a scope change is explicitly approved. |
| Mixing profile | Defined medium and large projects, fixed stock and catalog plug-in versions, sample libraries, automation, routing, and real-time/offline exports; qualify the specified buffers and concurrency. Project sizes are frozen in P006 before tuning. |
| Numerical result | Bit-exact output when deterministic operation permits it; otherwise predeclared justified tolerances against the native reference, including alignment, channel order, clipping, NaN/Inf, phase, duration, and audible artifact checks. No tolerance widened after seeing a failure without review and rerunning the affected baseline. |
| Reliability | Repeated clean starts, full save/reopen and recovery tests, an eight-hour integrated workload, and separate stress/fault campaigns. Zero observed unexplained dropouts, crashes, corruption, or missed deadlines in the declared acceptance run. This is a bounded test result, not a proof about all possible future workloads. |
| Graphics/input | Every cataloged workflow usable with correct focus, dialogs, text, menus, plug-in windows, resizing, scaling, and project editing while audio runs. |
| Update/reinstall | A clean Linux installation can recreate the qualified environment from pinned open-source artifacts plus legitimately obtained user assets. Upgrades preserve projects and permit a tested rollback. |

At 48 kHz, 64, 128, and 256 frames correspond to approximately **1.333, 2.667, and 5.333 milliseconds per buffer**. Those are scheduling periods, **not** measured input-to-output latency. Track callback start delay, execution duration, device buffering, transport buffering, conversion, plug-in delay, and full round-trip measurements separately. Apple's [audio performance guidance](https://developer.apple.com/documentation/audiotoolbox/analyzing-audio-performance-with-instruments) and [audio workgroups](https://developer.apple.com/documentation/audiotoolbox/understanding-audio-workgroups) inform the design; they do not provide a ready-made Linux scheduler implementation.

## Mandatory instructions for every agent and contributor

**READ THIS SECTION BEFORE WORK. AFTER EVERY WORK SESSION, UPDATE THIS README. A CODE CHANGE WITHOUT ITS README PROGRESS UPDATE IS INCOMPLETE.**

### Strict phase order

1. Read the dashboard, phase index, most recent handover, and full current-phase entry. Confirm the repository head and all relevant submodule heads before editing.
2. The only implementation phase that may be active is the earliest phase without a valid `PASSED` result. Work through **P001 → P002 → … → P096**. Do not start or merge a separately scheduled later phase, or claim its completion, until **every condition in the previous phase and the global gate contract is met and independently verified**.
3. Several agents may work in parallel **inside the current phase**, with explicit ownership of files/tests. Research may document future risks, but it must not be used to claim later-phase progress or bypass a blocked predecessor. The roadmap's initial authoring is documentation, not implementation of its phases.
4. All earlier passing tests remain mandatory regression checks when touched. If a regression invalidates a passed condition, mark the phase `REOPENED`, mark dependent claims invalid, and return to the earliest affected phase. A later success cannot compensate for an earlier failure.
5. A phase can be split into substeps, but all original requirements remain binding. Reordering, removing, or relaxing a gate requires an explicit dated rationale, scope impact, and project-owner approval recorded here before it can affect acceptance. Routine implementation choices within the gate do not require extra approval.

**Dependency repair stays inside the active phase.** The real application may require an audio, graphics, language-runtime, or service contract earlier than the roadmap's comprehensive subsystem phase. For example, P027 startup may require genuine Audio Unit enumeration/validation before P036 formally qualifies the complete Audio Unit lifecycle. When a minimal reproducer proves such a dependency, implement the minimum correct prerequisite in its actual source owner **as work for the current phase**, with tests and evidence. Keep the later phase `NOT STARTED`; link the prerequisite work there as prior evidence to revalidate when its turn arrives. This does not authorize skipping a phase, marking a later gate passed, faking an API, disabling required initialization, or doing unrelated future work. If the prerequisite cannot be implemented, the current phase remains BLOCKED. This rule prevents a numbering-based deadlock while preserving the requirement that no phase advances before all its conditions pass.

### Allowed status values

| Status | Meaning |
| --- | --- |
| NOT STARTED | No implementation or verified completion is claimed. |
| ACTIVE | The current phase has an assigned owner and concrete work in progress. |
| BLOCKED | A required dependency, asset, observation, behavior, or test is unavailable/failing. Record exactly how to unblock it. |
| READY FOR REVIEW | Implementation and all evidence are present; an independent reviewer has not yet accepted every gate. |
| PASSED | Every checkbox and global requirement passed, evidence is reproducible, and a different agent/person independently verified it. |
| REOPENED | Previously accepted evidence has been invalidated by regression, changed prerequisites, or a proven false pass. |

An agent must never mark its own unreviewed work `PASSED`. An independent reviewer is required for every phase; a native reference is additionally required whenever that phase's behavioral gate calls for one. Source-inventory, clone, build-infrastructure, and harness checks may use their specified independent non-Mac oracles. If a required reviewer or required oracle is unavailable, retain `READY FOR REVIEW` or `BLOCKED`; do not advance. A screenshot is supplementary evidence. A process exit code, exported symbol, non-null pointer, green package build, or nonempty waveform alone is not a behavioral acceptance test.

### Global gate contract — applies to all 96 phases

Every phase must satisfy all of the following in addition to its own checkboxes:

- Its predecessor is validly passed, and its implementation matches the exact pinned source/target manifest and defined scope available at that stage. P001–P004 establish source, build, and synthetic-probe evidence before the Intel application manifest is frozen in P005; P005–P068 require the Intel evidence relevant to their gates; P069 onward requires the refreshed ARM manifest and native ARM reference. P001 has no predecessor.
- The stated positive, negative, lifecycle, failure, and boundary cases are implemented and exercised where applicable. Errors must remain errors; returning invented success is a failure.
- Any API reached by an acceptance scenario has a real typed implementation or a deliberately supported, tested native-equivalent result. Generic null/success stubs, silent feature disablement, bypassed validation, fabricated receipts, ignored callbacks, and skipped assertions cannot pass.
- Expected results come from specifications and/or the recorded native reference, with the comparison method and tolerance fixed before acceptance. P001–P004 use independent source/build assertions and purpose-built probe expectations; P005 establishes actual native application eligibility and P006 freezes its full oracle corpus. Do not use the implementation's own output as its only oracle or demand a future-phase artifact before its planned creation.
- Commands, fixtures, exact versions, raw logs, relevant traces, outputs, and environment details are recorded. Tests can be rerun from a clean checkout/prefix. Required unavailable evidence means blocked.
- Relevant previous tests pass; new code has focused tests that exercise the discovered failure and observable behavior. Test volume is not a completion metric.
- An independent reviewer records identity, date, tested implementation commit, relevant submodule commits, cases reviewed, and verdict. They reproduce critical cases rather than approving a prose claim.
- This README contains the updated phase status, completed work, evidence pointers, remaining failures, exact next action, and the permitted next phase. The dashboard and phase index agree.

### Required progress update after every session

Update **all** of the following before handing work to another agent or ending a work session, including sessions that only investigate or fail:

1. **Dashboard:** active phase, owner, latest verified implementation revision, passed count, blocking issue, and exact next action.
2. **Current phase entry:** check only verified conditions; append an implementation record describing files/functions changed, observable behavior gained, remaining limitations, and test results. Never replace the original gate with an easier one.
3. **Evidence index:** add relative paths or durable URLs, content hashes, commands, reference results, and reviewer information. Local temporary paths alone are insufficient handover evidence.
4. **Handover log at the end of this README:** date, author, phase, implementation/submodule commits, what changed, what was verified, what failed or remains, and exactly which phase/substep the next agent must work on.
5. **Phase index:** keep its status synchronized with the detailed section. If incomplete, explicitly state “remain in P0XX.” If passed, state “next permitted phase: P0YY.”

Use this implementation-record template inside the affected phase; preserve previous records rather than rewriting their history:

```text
Date / agent:
Phase and status:
Implementation commit(s) and submodule commit(s):
Files / functions changed:
Behavior implemented:
Commands and fixture IDs:
Expected result / actual result:
Evidence paths or URLs and hashes:
Native reference build / environment:
Gate checkboxes verified / still failing:
Independent reviewer / reproduction / verdict:
Known limitations and exact blocker:
Next action (file, function, test, expected result):
Next permitted phase (or remain in current phase):
README update included in commit:
```

Record the tested **implementation revision** in the evidence. The documentation commit containing that record will necessarily be newer; do not create a self-referential requirement that the README contain the hash of its own commit. Every behavior-changing commit must include a README progress update in the same integration change. For submodule changes, push the submodule commit first, then update the parent gitlink and README together. Do not claim a submodule fix that another clean checkout cannot fetch.

### Evidence layout and ownership

The paths below are **proposed new project infrastructure**, not commands or files that already exist at the baseline. Create them in the relevant phase. This README remains the complete plan; supporting files hold machine-readable inventories, implementation decisions, test fixtures, and raw evidence.

| Proposed path | Purpose |
| --- | --- |
| `docs/compat/logic-pro/targets/` | Exact Intel and ARM manifests, release/channel research, checksums, native feature inventory. |
| `docs/compat/logic-pro/decisions/` | Numbered architecture decisions with alternatives, experiments, and rejected approaches. |
| `docs/compat/logic-pro/evidence/P0XX/` | Versioned evidence manifests, small logs, native comparisons, reviewer verdicts, and hashes/URLs for large artifacts. |
| `docs/compat/logic-pro/hardware/` | Host, interface, GPU, firmware, and scheduling qualification profiles. |
| `tests/compat/logic-pro/` | Minimal API probes and integrated deterministic fixtures by phase. |
| `tests/compat/logic-pro/projects/` | Reproducible project recipes and redistributable test assets; hashes and local acquisition instructions for user-owned assets. |
| `tools/compat/logic-pro/` | Inventory, trace normalization, oracle comparison, manifest validation, and gate-check tooling. |
| `ci/logic-pro/` | Clean build, privileged/native-lab orchestration, artifact retention, and release qualification configuration. |

Never commit user credentials, signing secrets, authorization tokens, commercial application binaries, purchased sample libraries, or plug-ins merely to make a test self-contained. Record legitimate acquisition prerequisites and hashes; keep required private evidence available to authorized reviewers. Lack of public redistribution rights does not mean tests may be skipped. Live-account operations must use the project owner's actual authorized test arrangements.

When agents work concurrently in the current phase, reserve ownership in the handover entry, use separate branches/worktrees, and merge only after checking the live head. Resolve README changes by combining factual records rather than dropping another agent's work. Never force-update a shared branch to publish a stale plan or overwrite implementation progress.

## Source ownership and implementation map

Use these real repository areas before inventing parallel implementations. Some components are submodules; edits inside them require their own published commits and a parent gitlink update. A phase's proposed child file does not imply that file already exists.

| Concern | Existing location / ownership boundary |
| --- | --- |
| Build and architecture | `CMakeLists.txt`, `cmake/architecture.cmake`, `cmake/darling_parse_components.cmake`, `.gitmodules`, `.github/workflows/actions.yaml` |
| Process startup and Mach-O loading | `src/startup/mldr/`, `src/libelfloader/`, `src/external/dyld/` |
| Darwin services and process environment | `src/external/darlingserver/`, `src/external/xnu/`, `src/launchd/`, `src/vchroot/`, `src/xtrace/`, relevant libSystem/libpthread/libdispatch submodules identified in P001 |
| Objective-C, Swift, Foundation | `src/external/objc4/`, `src/external/swift/`, `src/external/foundation/`, associated CoreFoundation and runtime submodules |
| AppKit and core drawing/compositing | `src/external/cocotron/AppKit/`, `src/external/cocotron/CoreGraphics/`, `src/external/cocotron/QuartzCore/`, `src/frameworks/IOSurface/` |
| Metal and graphics translation | `src/external/metal/`, its Vulkan backend and framework targets; `src/frameworks/` and `src/private-frameworks/` for other reached dependencies |
| Audio hardware and host service | `src/CoreAudio/CoreAudio/`, especially `AudioHardwareImpl.cpp`, `HostTime.mm`, and `pulse/` |
| Output/IO Audio Units | `src/CoreAudio/CoreAudioComponent/`, especially `AUHAL.cpp` and output-unit classes |
| Audio Toolbox, components, graphs, files | `src/CoreAudio/AudioToolbox/` |
| MIDI | `src/frameworks/CoreMIDI/`, `src/CoreAudio/AudioToolbox/MusicDevice.cpp` |
| DSP/Accelerate | `src/frameworks/Accelerate/vecLib/`, including `vDSP`, `BLAS`, `vMisc`, and `BNNS` |
| Audio framework wrappers/editor views | `src/frameworks/AVFAudio/`, `src/frameworks/CoreAudioKit/` |
| Store/service/model dependencies | `src/frameworks/StoreKit/`, relevant Security submodules, `src/private-frameworks/Espresso/`, and other reached frameworks found by the target inventory |
| Existing tests and packages | `tests/`, `ci/`, `debian/`, `rpm/` |
| New ARM-on-x86 execution integration | **Proposed:** `src/translation/`; backend choice and exact ownership are decided in P070 before implementation |

## Phase index

Each row links to the complete implementation and pass criteria below. Initial statuses intentionally make no execution claims. The index must be kept synchronized after every work session.

| Phase | Work and required milestone | Status |
| --- | --- | --- |
| [P001](#p001) | Preserve and inventory the actual source baseline | **PASSED at `d58cca51`**, independently accepted 2026-11-06 04:06:14 UTC; G1–G4 pass. [Acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-p001/acceptance.json). P002 has subsequently passed; current next permitted phase: P003. |
| [P002](#p002) | Make every submodule reproducibly obtainable | **PASSED at `d58cca51`**, independently accepted 2026-11-06 04:29:24 UTC after P001; all four original gates and five waves complete. [Acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json). Next permitted phase: P003. |
| [P003](#p003) | Pin a complete GUI-capable build and installation | **ACTIVE; remain in P003.** Waves 1–3 complete; local and hosted 174/115/187 pass. Wave 4 repairs the observed artifact-permission defect and independently reviews fresh full build, package and runtime evidence; no current gate is accepted. Historical G1–G4 PASS at `89c6c9d` remains preserved. |
| [P004](#p004) | Establish CI that cannot manufacture compatibility success | IN DEVELOPMENT — NOT PASSED |
| [P005](#p005) | Identify and lock the newest eligible Logic targets | NOT STARTED |
| [P006](#p006) | Build reference-Mac evidence and canonical workloads | NOT STARTED |
| [P007](#p007) | Map the complete reachable application dependency closure | NOT STARTED |
| [P008](#p008) | Make crashes, hangs, and false-success stubs observable | NOT STARTED |
| [P009](#p009) | Establish differential compatibility testing against macOS | NOT STARTED |
| [P010](#p010) | Correct x86_64 Mach-O loading and process startup | NOT STARTED |
| [P011](#p011) | Resolve dyld images, imports, fixups, and runtime loading | NOT STARTED |
| [P012](#p012) | Verify Objective-C, blocks, ownership, and unwinding | NOT STARTED |
| [P013](#p013) | Supply the Swift runtime and ABI actually required | NOT STARTED |
| [P014](#p014) | Correct Mach IPC, ports, memory, and exception semantics | NOT STARTED |
| [P015](#p015) | Establish correct threads, workqueues, clocks, and synchronization | NOT STARTED |
| [P016](#p016) | Implement launchd, XPC, and helper-process lifecycle | NOT STARTED |
| [P017](#p017) | Preserve filesystem semantics and project-package integrity | NOT STARTED |
| [P018](#p018) | Implement legitimate security, keychain, and receipt flows | NOT STARTED |
| [P019](#p019) | Resolve bundles, resources, Launch Services, and content types | NOT STARTED |
| [P020](#p020) | Complete the Foundation and CoreFoundation contracts in use | NOT STARTED |
| [P021](#p021) | Construct AppKit startup and nib object graphs correctly | NOT STARTED |
| [P022](#p022) | Implement window, menu, focus, and input behavior | NOT STARTED |
| [P023](#p023) | Make layout, text, scaling, and accessibility usable | NOT STARTED |
| [P024](#p024) | Render CoreGraphics, CoreText, and ImageIO correctly | NOT STARTED |
| [P025](#p025) | Implement Core Animation transactions and IOSurface sharing | NOT STARTED |
| [P026](#p026) | Support the graphics API path needed for baseline GUI operation | NOT STARTED |
| [P027](#p027) | Reach a usable empty Logic project through the first-failure ladder | NOT STARTED |
| [P028](#p028) | Accept baseline GUI workflows and the first save/reopen round trip | NOT STARTED |
| [P029](#p029) | Correct audio format, frame, packet, and buffer contracts | NOT STARTED |
| [P030](#p030) | Implement one coherent host clock and audio sample timeline | NOT STARTED |
| [P031](#p031) | Implement truthful audio hardware properties and notifications | NOT STARTED |
| [P032](#p032) | Define and implement a production host audio backend lifecycle | NOT STARTED |
| [P033](#p033) | Complete full-duplex buffer transport and channel layout handling | NOT STARTED |
| [P034](#p034) | Measure and correct latency, alignment, drift, and reconfiguration | NOT STARTED |
| [P035](#p035) | Remove unbounded work from the real-time audio path | NOT STARTED |
| [P036](#p036) | Implement honest Audio Unit creation, lifetime, and validation | NOT STARTED |
| [P037](#p037) | Complete Audio Unit parameters, state, and sample-offset automation | NOT STARTED |
| [P038](#p038) | Deliver MIDI and note events to MusicDevice components | NOT STARTED |
| [P039](#p039) | Implement Audio Unit graph construction, routing, and mixing | NOT STARTED |
| [P040](#p040) | Replace CoreMIDI entry-point stubs with a real object model | NOT STARTED |
| [P041](#p041) | Qualify MIDI scheduling, protocols, hotplug, and transport control | NOT STARTED |
| [P042](#p042) | Establish a DSP ABI inventory and numerical reference harness | NOT STARTED |
| [P043](#p043) | Implement required vDSP vector arithmetic and reductions | NOT STARTED |
| [P044](#p044) | Implement FFT, convolution, correlation, and filter semantics | NOT STARTED |
| [P045](#p045) | Complete reachable BLAS, vector math, and BNNS numerical paths | NOT STARTED |
| [P046](#p046) | Implement reliable AudioFile and ExtAudioFile storage semantics | NOT STARTED |
| [P047](#p047) | Complete AudioConverter and AudioQueue streaming/offline behavior | NOT STARTED |
| [P048](#p048) | Demonstrate integrated Logic audio recording, playback, and bounce | NOT STARTED |
| [P049](#p049) | Qualify every bundled x86_64 instrument | NOT STARTED |
| [P050](#p050) | Complete sampler streaming and sound-library access | NOT STARTED |
| [P051](#p051) | Qualify stock effects, automation, and delay compensation | NOT STARTED |
| [P052](#p052) | Complete MIDI composition, recording, and controller workflows | NOT STARTED |
| [P053](#p053) | Complete audio editing, Flex, and tempo analysis | NOT STARTED |
| [P054](#p054) | Complete loops, arrangement, and native-supported session features | NOT STARTED |
| [P055](#p055) | Verify project persistence, autosave, and recovery behavior | NOT STARTED |
| [P056](#p056) | Finish the complete GUI workflow and rendering matrix | NOT STARTED |
| [P057](#p057) | Qualify third-party AUv2 plug-ins and their user interfaces | NOT STARTED |
| [P058](#p058) | Implement AUv3 extension discovery, hosting, and isolation | NOT STARTED |
| [P059](#p059) | Qualify ARA and advanced plug-in integrations | NOT STARTED |
| [P060](#p060) | Complete video scoring and frame-accurate synchronization | NOT STARTED |
| [P061](#p061) | Complete multichannel, surround, and spatial production | NOT STARTED |
| [P062](#p062) | Complete content installation, updates, and legitimate services | NOT STARTED |
| [P063](#p063) | Qualify physical audio/MIDI interfaces and device recovery | NOT STARTED |
| [P064](#p064) | Meet fixed-hardware production performance budgets | NOT STARTED |
| [P065](#p065) | Pass long-duration operation and fault-recovery qualification | NOT STARTED |
| [P066](#p066) | Close the complete x86_64 feature matrix and verify version selection | NOT STARTED |
| [P067](#p067) | Produce a reproducible x86_64 release and clean-install qualification | NOT STARTED |
| [P068](#p068) | Independently accept and maintain the x86_64 milestone | NOT STARTED |
| [P069](#p069) | Freeze the current ARM release and its complete native feature inventory | NOT STARTED |
| [P070](#p070) | Choose an ARM-to-x86 execution architecture through measured feasibility work | NOT STARTED |
| [P071](#p071) | Add translator integration, guest address space, and build isolation | NOT STARTED |
| [P072](#p072) | Implement and verify ARM scalar instructions and control flow | NOT STARTED |
| [P073](#p073) | Implement NEON, floating point, and per-thread numerical state | NOT STARTED |
| [P074](#p074) | Preserve ARM atomics, exclusives, and memory ordering | NOT STARTED |
| [P075](#p075) | Reconcile guest virtual memory, page sizes, protections, and mappings | NOT STARTED |
| [P076](#p076) | Implement the Apple ARM ABI, TLS, commpage, and syscall boundary | NOT STARTED |
| [P077](#p077) | Support ARM dyld fixups, authenticated pointers, and branch requirements | NOT STARTED |
| [P078](#p078) | Build typed guest/host bridges and callback round trips | NOT STARTED |
| [P079](#p079) | Make translated threads, workqueues, and multicore execution correct | NOT STARTED |
| [P080](#p080) | Preserve signals, exceptions, unwinding, and debuggable guest faults | NOT STARTED |
| [P081](#p081) | Support generated code, code-cache invalidation, and executable-memory transitions | NOT STARTED |
| [P082](#p082) | Run ARM helper processes, launch services, and cross-process IPC | NOT STARTED |
| [P083](#p083) | Complete ARM Objective-C, Swift, Foundation, and application runtime behavior | NOT STARTED |
| [P084](#p084) | Render ARM application and plug-in graphics through the host backend | NOT STARTED |
| [P085](#p085) | Connect translated ARM audio, MIDI, and Audio Unit callbacks | NOT STARTED |
| [P086](#p086) | Qualify ARM Accelerate and DSP with safe native acceleration | NOT STARTED |
| [P087](#p087) | Execute required Core ML, BNNS, MPS, and private model paths | NOT STARTED |
| [P088](#p088) | Launch latest ARM Logic and complete the first real project | NOT STARTED |
| [P089](#p089) | Complete all Apple silicon and current-version first-party features | NOT STARTED |
| [P090](#p090) | Qualify ARM plug-ins and explicit cross-architecture Audio Unit hosting | NOT STARTED |
| [P091](#p091) | Requalify complete production workflows and cross-platform project exchange | NOT STARTED |
| [P092](#p092) | Optimize translation using measured Logic bottlenecks | NOT STARTED |
| [P093](#p093) | Meet the ARM-on-x86 real-time audio and monitoring contract | NOT STARTED |
| [P094](#p094) | Pass ARM long-duration, fault, recovery, and resource tests | NOT STARTED |
| [P095](#p095) | Independently audit the complete latest-ARM qualification claim | NOT STARTED |
| [P096](#p096) | Publish the qualified ARM release and establish continuous requalification | NOT STARTED |

## Intel delivery: reproducibility, runtime, GUI, audio, and production qualification

## Foundation, target selection, runtime, and application startup

The paths labeled **Existing** below refer to the audited source tree. Paths labeled **Proposed** are work to create; their names do not imply that a harness or result already exists. A directory inside an existing submodule must be changed in a maintained fork of that submodule, committed there, and integrated by updating the parent repository's gitlink. Every checklist item is mandatory unless that item explicitly defines an evidence-based not-applicable outcome. Every phase also follows the global README update and evidence rules.

<a name="p001"></a>

### P001 — Preserve and inventory the actual source baseline

**Status:** **PASSED at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.** Independent reviewer `/root/wave4_p001_evidence` accepted all four original gates at **2026-11-06 04:06:14 UTC**. Both exact-source hosted jobs passed 174 tests; the reviewer independently checked all original artifacts, reconstructed native inventory trees and reproduced all 174 tests plus both original recovery snapshots. [Formal acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-p001/acceptance.json), [review and reproduction evidence](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-p001/README.md). All earlier accepted and failed revisions below remain historical evidence. P002 was the permitted successor at this acceptance and has now also passed; the current next permitted phase is P003.

**Depends on:** None.

**Objective:** Establish a recoverable, accurately described baseline before changing the Darling fork. The application-compatibility runtime is the implementation being planned; a simulated macOS version or a framework directory is not evidence that Logic runs.

**Where:** **Existing:** `.gitmodules`, `CMakeLists.txt`, `cmake/architecture.cmake`, `src/CMakeLists.txt`, `src/startup/mldr/`, `src/frameworks/`, `src/private-frameworks/`, `src/external/`, `tests/`, `.github/workflows/`. **Proposed:** `tools/compat/logic-pro/inventory.py`, `docs/compat/logic-pro/baseline.json`, `docs/compat/logic-pro/evidence/P001/`.

**Implementation:**

1. Record the audited commit `3447ff5ab8e837ea54a13a506c60d34d77e2bd15`, current integration commit, branch topology, upstream relationship, working-tree status, tracked files, license files, and every recursive submodule path, URL, and gitlink SHA. Preserve the previous README through Git history and record its immutable source link.
2. Generate an inventory distinguishing native Linux code, Mach-O runtime components, implemented frameworks, partial implementations, developer link stubs, generated stubs, and unavailable submodule contents. Record classification evidence, not just names.
3. Map launch flow from `mldr` through dyld, system libraries, darlingserver, and framework initialization. Record which statements are static findings and which have been executed. Capture actual host architecture and build limitations without claiming ARM support from headers alone.

**Verification and pass gate:**

- [x] Every tracked gitlink and its committed SHA appears once in the inventory; missing or unreachable content is identified.
- [x] A clean checkout of the baseline resolves to the recorded tree, with no unrecorded local modifications.
- [x] Runtime architecture and stub classifications cite concrete source locations and distinguish inspection from execution.
- [x] The recovery procedure restores the baseline and prior README in an isolated checkout.

**Required evidence:** `docs/compat/logic-pro/evidence/P001/inventory.json`, command transcript, baseline/tree hashes, source map, and recovery check.

**On failure/next action:** Fix incomplete inventory or preserve inaccessible-object evidence; do not start P002 until the baseline is recoverable.

**README handover:** Update P001, the dashboard, source baseline, inventory link, and the exact P002 submodule-repair entry point.

#### P001 implementation record — 2026-10-31 (before hosted acceptance)

- **Owner and scope:** `/root` integrates work on `master`; `/root/inventory_tool` owns the committed-source inventory, `/root/recovery_tool` owns isolated recovery, and `/root/source_map` owns the static audit. Reviews cross those ownership boundaries. No runtime source or dependency pin is changed by this milestone.
- **Starting revision:** `b25035fce2cd1c038c567d34ea0797371947d95d`; audited source `3447ff5ab8e837ea54a13a506c60d34d77e2bd15`. Exact original tree/README hashes are retained in [baseline.json](docs/compat/logic-pro/baseline.json).
- **Implemented behavior:** `inventory.py` reads committed trees, matches gitlinks/declarations, resolves fork-relative URLs and records unavailable recursive contents; `recover_baseline.py` restores two independent object stores and verifies all materialized blobs/modes/symlinks; `verify_classifications.py` checks 32 hashed source citations; `run_baseline.py` crosschecks evidence and refuses empty, missing, stale or failed results.
- **Actual local verification:** 45 focused tests passed using real synthetic Git histories and deliberate damage. Independent agents reproduced inventory/recovery/citation cases and checked the 32 source excerpts across 23 distinct cited files. This does not substitute for the pending full-repository campaign.
- **Source finding:** all 149 `.gitmodules` declarations use relative URLs. Parent gitlinks are captured independently through GitHub's Git tree API. Uninitialized children and unknown nested dependencies remain explicitly uninspected; remote fetchability is not claimed.
- **Evidence/reproduction:** [source map](docs/compat/logic-pro/source-map.md), [classification register](tools/compat/logic-pro/classifications.json), [remote snapshot](docs/compat/logic-pro/evidence/P001/remote-snapshot.json), and [reproduction procedure](docs/compat/logic-pro/evidence/P001/REPRODUCE.md). The phase-local [workflow](.github/workflows/phase1-baseline.yml) runs the campaign on Ubuntu 22.04 and 24.04 and retains raw reports.
- **Remaining gate:** full repository inventory and baseline restoration must execute on clean hosted checkouts, with logs and independent acceptance recorded. Local direct Git network transport is unavailable, so this integration uses the selected GitHub connection and the hosted campaign. There is no Darling or Logic execution result.
- **Next action:** inspect the campaign's `summary.json`, `inventory.json`, recovery and citation reports, fix any failing case, record the tested implementation revision and reviewer verdict, and update this ledger. **Remain in P001; P002 has not started.**

#### P001 historical acceptance record — 2026-10-31 (superseded; recursive requirement was incomplete)

**Historical record, superseded:** the source baseline was recoverable and inventoried at the parent-tree boundary, but that narrower boundary did not fulfill the original recursive requirement. The raw results below remain valid evidence of what was actually checked; they are not current phase acceptance. [Current machine-readable acceptance](docs/compat/logic-pro/evidence/P001/acceptance.json) records the reopened state and subsequent final verdict.

| Verification | Observed result |
| --- | --- |
| Tested implementation | `dc787de7d0aba7582981c8bf106fa0ff5fb1ef37` on `master` |
| Hosted campaign | [Run 41237082207](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41237082207), both Ubuntu 22.04 and 24.04 jobs successful |
| Focused positive/negative tests | **45 executed and passed on each host**; no skipped or empty test success |
| Committed-tree inventory | **27,288 tracked entries**; **149 unique parent gitlinks** match the independent GitHub snapshot; zero inventory errors or warnings |
| Exact historical recovery | Both original-source and initial-plan snapshots restored with separate object stores; **27,125 blobs verified per snapshot**, including **528 executables** and **2,890 symlinks** |
| Original README preservation | Exact original and plan README SHA-256 values match [baseline.json](docs/compat/logic-pro/baseline.json); historical Git links remain available |
| Static source evidence | **32 exact hashed citations** verified against original and tested source; architecture and stub classes remain separate from runtime behavior |
| Independent clone | A separately fetched clean clone regenerated the **same complete tracked-file bytes** as both hosted jobs: SHA-256 `ac07d77474ed75518643e4efe4d007c9550b80a39a58a8c13cb25a56905c1ca2` |
| Independent reviewers | `/root/recovery_tool` accepted inventory/source classifications; `/root/source_map` accepted recovery/campaign/workflow. Each reproduced critical cases and retrieved actual hosted evidence; neither approved their own component. |

**Evidence index:** [inventory](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/inventory.json), [complete tracked-file archive](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/tracked-files.json.gz), [recovery](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/recovery.json), [source-citation results](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/classifications.json), [primary summary](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/summary.json), [second-host summary](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/ubuntu-22.04/summary.json), [command transcript](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/commands.json), [independent reviews](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/reviews/), [evidence hashes and artifact links](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/evidence-index.json), and [reproduction instructions](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/REPRODUCE.md).

**Reason this historical acceptance was invalid:** all 149 child contents were uninitialized. Deferring their recursive inventory to P002 contradicted the original P001 requirement; the complete recursive evidence below closes that gap. The unchanged inherited Darling packaging workflow actually failed while resolving fork-relative dependency URLs; its [captured failure evidence](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001/inherited-ci-failure.json) is a P002 entry point. No runtime compilation, Mach-O application, Logic, audio or ARM qualification is claimed.

**Superseded advancement instruction:** this earlier record proposed P002 prematurely. That instruction was withdrawn when P001 reopened. Only the final full-scope acceptance below now authorizes P002, which remains NOT STARTED.

#### P001 recursive completion implementation — 2026-10-31 (implementation history; accepted below)

- **Starting revision:** `2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6`; all original source and child gitlink pins remain unchanged. The identical audited root commit/tree and `.gitmodules` blob were independently confirmed in Darling upstream.
- **Source retrieval:** `prepare_sources.py` obtains exact pinned child commits from recorded public upstream origins and discovers every descendant. It preserves declared/fork-relative URLs separately from acquisition URLs and never changes committed URLs or pins. Fresh checkouts use a recorded local attributes override to preserve raw committed bytes; the actual libffi regression verified all **409 blobs** after fixing four CRLF-transformed files. The actual acquisition found **160 gitlinks: 149 direct plus 11 nested**. An independent Git walk confirmed **161 repositories**, with no missing child object. An initial local run recorded a final-state failure from recreated task-owned staging residue; that failed attempt remains preserved, and a clean hosted acquisition is mandatory before acceptance.
- **Strict source checks:** `inventory.py --require-recursive` and `run_baseline.py` now reject unavailable descendants and inconsistent graph/count/provenance records. They verify physical bytes, executable bits and symlink targets against Git objects, including changes hidden by index flags, and repeat the complete physical inventory after the campaign. The earlier parent-only false pass is covered by deliberate failures.
- **Complete static launch map:** the classification register now has **63 hashed citations across 41 files**, including **28 child citations** bound to exact gitlink chains. The verifier requires eight source categories and six launch stages. The source map follows mldr into dyld dependency loading, libSystem, dispatch, Objective-C callbacks, CoreFoundation initialization and the server's check-in implementation. It also records actual compiler/host/component configuration limits. All observations remain static source inspection.
- **Executed verification before publication:** **109 focused tests passed** in the integrated worktree and an independently assembled campaign. That campaign exercised actual tool interoperability, recursive acquisition, both historical recoveries, required citation coverage and final physical verification. Cross-component reviewers reproduced missing-child, wrong-pin, corrupted-evidence, hidden-dirty, executable-mode, filter-side-effect and checkout-transformation failures. License/notice candidate records cover all 174 independently observed formerly omitted paths and are now mandatory, crosschecked evidence.
- **Independent review ownership:** `/root/source_map` reviews retrieval, strict campaign integration and the recursive graph; `/root/recovery_tool` reviews inventory/campaign/workflow; `/root/inventory_tool` reviews the extended static source map and verifier. Final reviews must name the published implementation commit and actual hosted results before any `PASSED` claim.
- **Hosted outcome:** the published implementation passed the strict campaign on both clean hosts and received final complementary independent acceptance, as recorded below. P002 remains NOT STARTED.

#### P001 historical first full-scope acceptance — 2026-10-31 (original `4707a919` scope)

**All four original P001 gates and the independent-review contract were satisfied at this historical revision.** The accepted implementation was [`4707a919ef304945f7685390a68429242657eb54`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/4707a919ef304945f7685390a68429242657eb54). The following documentation/evidence publication records that tested revision without claiming a new runtime result. [Machine-readable original acceptance](docs/compat/logic-pro/evidence/P001/acceptance.json) is the historical verdict; the [current candidate acceptance](docs/compat/logic-pro/evidence/P001/qualification-b628085/acceptance-status.json) records the new `PASSED` result.

| Verification | Actual result |
| --- | --- |
| Clean hosted campaigns | [Run 41240503365](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41240503365); Ubuntu 22.04 and Ubuntu 24.04 both successful; **109 tests passed on each host** |
| Complete source graph | **161 repositories; 160 exact pinned gitlinks: 149 direct and 11 nested; zero unavailable contents** |
| Committed and physical inventory | **293,127 tracked entries; 292,967 physical blobs**, with actual bytes, modes and symlink targets checked; final rescan unchanged; zero errors or warnings |
| Source origins and notices | Declared/fork-relative URLs and actual acquisition URLs recorded separately; **754 license/notice filename/path candidates** with committed bytes/hashes, including raw symlink target text |
| Static architecture and launch map | **63 exact citations across 41 files, including 28 child citations**; all eight required categories and six launch stages verified against original/current pin chains |
| Historical recovery | Original source and initial plan restored in independent object stores on both hosts; **27,125 blobs per snapshot**, including 528 executables and 2,890 symlinks; exact README/tree hashes preserved |
| Independent source oracle | Native Git reconstruction fixed before hosted acceptance, eight upstream trees for nested pins, and a separate physical checkout all agree with the complete hosted manifests |
| Artifact integrity | Both downloaded ZIP hashes match GitHub metadata; all 15 checksum entries per host pass; all four full initial/final manifests are byte-identical |
| Complementary independent approval | [Recursive source/campaign reviewer](docs/compat/logic-pro/evidence/P001/reviews/recursive-source-and-campaign/final-independent-review.json) and [retrieval/static-source reviewer](docs/compat/logic-pro/evidence/P001/reviews/recursive-retrieval-and-source/final-independent-review.json); each excludes their authored production components |

The complete tracked-file payload is **97,472,302 bytes**, SHA-256 `047d659a94420c97f42d08cc4deea40fdc2912a69ff4c77057562835705404cd`. It is preserved once as an exact gzip archive in [11 ordered binary parts](docs/compat/logic-pro/evidence/P001/tracked-files/manifest.json), with an explicit mapping to both hosts' initial/final filenames. Concatenating the parts reproduces the verified gzip byte-for-byte; this avoids a stalled single large-blob upload. [The evidence index](docs/compat/logic-pro/evidence/P001/evidence-index.json) hashes all retained reports, raw logs, review assets and resolved-failure history; [reproduction instructions](docs/compat/logic-pro/evidence/P001/REPRODUCE.md) explain how to regenerate and verify them. The successful producer reports remain unchanged, including their requirement for the independent reviews now recorded in acceptance.json.

**What the reopened work corrected:** missing recursive contents can no longer pass; counts, pins and acquisition provenance are crosschecked; physical verification catches damage hidden by Git index flags or disabled mode checks; fresh source-inspection checkouts preserve raw bytes despite CRLF/identifier/encoding attributes; license/notice metadata is mandatory; and a partial or wrongly owned launch map fails fixed coverage checks. The actual libffi transformation and early failed retrieval attempts remain in [resolved-failure history](docs/compat/logic-pro/evidence/P001/history/resolved-findings.json).

**P001 scope is complete.** This is source-baseline and static-evidence acceptance. Darling runtime execution, Logic functionality and later audio/graphics/ARM qualification have not been demonstrated. The [unchanged inherited packaging workflow](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41240503294) failed at ordinary recursive checkout on the original fork-relative URLs; [its actual failure log](docs/compat/logic-pro/evidence/P001/inherited-ci-failure.json) remains visible.

**Next permitted phase: P002; status NOT STARTED.** Begin at `.gitmodules`, repair the recorded URL/provenance problem without silently advancing pins, add `tools/compat/logic-pro/check_submodules.py` and `docs/compat/logic-pro/submodules.lock.json`, and qualify two independent ordinary recursive clones. No P002 implementation or pass is claimed by this delivery.

#### P001 fixture-result correction — 2026-10-31

- **Reproduced failure:** `run_baseline.py` accepted a real failing `unittest.expectedFailure` assertion because unittest exits zero and prints `OK (expected failures=1)`. The old gate checked nonempty test counts and skips, but not this masked failure. Earlier inspected hosted transcripts contain actual plain `OK` successes; the finding does not fabricate a failure in those historical results.
- **Correction and ownership:** `/root/gate_tooling_audit` added `verify_fixture_transcript()` in `tools/compat/logic-pro/run_baseline.py`. It requires a positive count bound to the terminal, unqualified `OK` summary. Expected failures, skips, empty suites, failures, errors, unexpected successes and truncated output cannot pass. The existing nonzero-process check remains mandatory.
- **Executed local checks:** seven new tests in `test_baseline_gate.py` use real unittest results, including mixed passing/masked outcomes and earlier diagnostic summaries. All **120 P001 fixtures** pass; the unchanged P002 suite has **96 passing fixtures**. These local results do not substitute for fresh hosted source acquisition.
- **CI integration:** both push and pull-request paths in `.github/workflows/phase2-submodules.yml` now include the P001 runner and baseline tests so changes to this predecessor gate requalify both phases at the same source revision. Both workflows retain separate Ubuntu 22.04/24.04 hosts and their existing source, payload and evidence checks.
- **Independent review and next action:** `/root/negative_case_review` independently approved the correction after 16 transcript cases, 11 main-path cases and a mutation that restores the observed false pass. The [review, original subprocess transcripts and reproduction script](docs/compat/logic-pro/evidence/P001/fixture-outcome-gate/review.json) are retained. `/root/ci_requalification_review` reviews both workflows and the resulting hosted runs. Record the published implementation SHA and actual results in a subsequent evidence-only update. **P001 REOPENED; remain in P001 until these checks pass.** No original criterion is removed or relaxed.

#### P001 current candidate qualification — 2026-10-31

The published correction is fully qualified for its technical scope. A separate [whole-campaign review](docs/compat/logic-pro/evidence/P002/qualification-b628085/ci-review/hosted-review.json) verified all **68 raw artifact members** across both phases, actual test outcomes, command exits, complete file inventories, recovery and unchanged dependency pins. Its reviewer did not author the correction. The tested revision is `b628085a19bae2d467fd9549ec0767636423a90a`, whose tree exactly equals source head `da1000be001711f80d6880eed9eeca916f6d0a23`.

| Original `b628085` P001 measurement | Verified result on each host |
| --- | --- |
| Fixture outcomes | 120 tests, plain `OK`, no skips or expected failures |
| Complete source inventory | 293,305 tracked entries; 160 exact gitlinks; 161 repositories; no unavailable contents |
| Static source evidence | 63 citations and 755 license/notice candidates |
| Historical restoration | Original source and roadmap restored in isolated object stores; 27,125 physical blobs per snapshot |
| Initial/final complete manifests | All four are byte-identical: 97,533,706 bytes, SHA-256 `3bf22490c31d3dbc11bb8328ce8b9bc8bb87c229c8a07fe8b1cf69a30e713d0e` |
| Retained current raw outputs | 14 unchanged small members per host in [qualification-b628085](docs/compat/logic-pro/evidence/P001/qualification-b628085/); the two large manifest names per host map to the same verified payload |

The four large manifest members are preserved in the independently verified **9,594,676-byte current raw-report bundle** described below. This original `b628085` measurement is retained as the dated technical qualification; **the whole archive was subsequently published, read back from a public GitHub runner on two Ubuntu hosts, and accepted together with the P001 predecessor gates**. The fresh post-publication P001 run measured 293,462 tracked entries because new evidence files had been added. No original evidence requirement was waived.

#### P001 hardened-source requalification and fresh independent acceptance — 2026-11-01

- **Exact tested source:** [`5c3c77ee2dfff7330e335be4117f8d6269bf228b`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/5c3c77ee2dfff7330e335be4117f8d6269bf228b), tree `bb9cc99f312406ce986473e77f833db7fe448456`. The hardened parser requires one genuine terminal result, uniquely named real verbose tests and a floor of 120 fixtures; adversarial tests reject forged summaries and suite shrinkage. Neither original source pins nor runtime code changed.
- **Fresh clean hosts:** [P001 run 41263623123](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41263623123), Ubuntu 22.04 job `124721738816` and Ubuntu 24.04 job `124721738961`, each **SUCCESS, 122 distinct fixture tests, terminal plain `OK`, `result=PASS`, `failures=[]`**. Both inventory the **149 direct + 11 nested immutable gitlinks**, **161 repositories**, **293,468 tracked entries**, **755 license/notice candidates** and **63 original/current source citations**, with zero unavailable children or source errors. Both independently restore each historical snapshot's **27,125 blobs**.
- **Actual artifact integrity:** ZIP `13067040829` (Ubuntu 22.04), SHA-256 `71208a144eb51de0e03bf61e56b6f0f8ab5979f11757227339f56319f9e6167c`; ZIP `13067002518` (Ubuntu 24.04), SHA-256 `942722cb6d5e47ca0cb72cfa32f098706473f525d17dd1a14080c1b535a5af0e`. Independently downloaded; all **16/16 CRC members and 15/15 nested SHA-256 checks** passed per host, including the complete 97-MB tracked manifests. [Per-host small raw reports and indexed ZIP content hashes](docs/compat/logic-pro/evidence/P001/qualification-5c3c77e/requalification.json) retain the exact test/recovery/citation evidence. Large new tracked manifests remain available in the checksum-bound CI ZIPs through their recorded expiration; historical complete source archives are separately durable and unmodified.
- **Independent gate verdict:** reviewer `/root/phase1` did not author the new parser/source changes; reproduced false-pass regressions, validated fresh full source/recovery evidence and explicitly accepted **P001 gates G1–G4 PASS** at this SHA. Independent `/root/validation` approved parser implementation; `/root/ci` and `/root/security_runtime` separately approved hosted provenance and source identity. [Machine-readable P001 verdict](docs/compat/logic-pro/evidence/P001/qualification-5c3c77e/requalification.json) and [ordered final acceptance](docs/compat/logic-pro/evidence/P002/qualification-5c3c77e/final-ordered-acceptance.json) bind the evidence and reviewer scopes. **P001 PASSED before P002; P001 acceptance is source preservation, not runtime qualification.**

#### P001 source-citation continuity reopened during P003 — 2026-11-01

[Run 41271772655](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41271772655) failed at exact candidate `d89920b447658cfa01e9645864f2315cad4e386a` on Ubuntu 22.04 and 24.04. Both hosts passed 122 fixtures, complete recursive inventory and historical recovery, but only **58 of 63 citations** verified. The five failures cite root or `src/CMakeLists.txt`; P003 changed those files while the current-source verifier supported only the earlier P002 `.gitmodules` URL re-audit. This invalidates the current P001 citation gate and blocks dependent acceptance. Original accepted reports remain preserved.

The correction keeps all original citations and assertions, explicitly audits only the reviewed additions to those two CMake files, pins their current blobs and excerpts, and independently binds the result to the complete tracked inventory. Other changed source bytes still fail. [Official failure evidence, original job hashes and requalification index](docs/compat/logic-pro/evidence/P001/p003-source-reaudit/README.md) preserve the exact evidence. Local regression suites pass **130 P001 tests and 97 P002 tests**, with authentic terminal results and no skips; transcript hashes and commands are recorded in the requalification index. The source-audit author is `/root/p003_independent_package_review`; `/root/p003_independent_build_review` [independently approved the narrow implementation](docs/compat/logic-pro/evidence/P001/p003-source-reaudit/README.md), reproducing the focused tests and five real source hashes; full hosted acceptance is pending. Required next action: publish this correction, pass fresh clean P001 campaigns and obtain independent acceptance before reaccepting P002 and resuming P003. **Remain in P001.**

#### P001 current-source continuity reaccepted — 2026-11-01

Exact implementation `b2c0d4893cace4ddbacf9f7c29503990b07491cd`, tree `d717988463e25d8e5828f77d2eb17411561188ab`, passed [P001 run 41275067092](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067092) on Ubuntu 22.04 and 24.04. Each host passed **130 real fixture tests, 63 source citations, 755 license candidates, 293,577 tracked entries, 160 gitlinks and 161 repositories**, with zero missing/dirty source. Both historical snapshots restored 27,125 blobs each. All four complete tracked manifests are identical: 97,629,682 bytes, SHA-256 `dc8e9ba09cad0563604cbb37bebee5631309c12dd4ca0d7ffd1e18093f48603d`.

Independent reviewer `/root/p003_independent_build_review` accepted **P001 G1–G4 on 2026-11-01 at 05:08:55.615852 UTC**. The reviewer did not author the correction; independently replayed all 130 tests, verified both original artifact ZIPs and all 15 internal hashes per host, reconstructed all 161 Git tree hashes from the complete manifests, checked all 63 historical/current citations, and physically rehashed **54,250 restored blobs/symlinks** in separate historical object stores. No findings remain. Formal local review SHA-256: `6548bf8a4baac5eaa699639cf1fc74cd0b74586e03481991af3ce74621f18784`; this paragraph records its essential dated verdict and scope. [Official artifacts, hashes and reproduction commands](docs/compat/logic-pro/evidence/P001/p003-source-reaudit/README.md) remain available under recorded Actions retention. P001 acceptance precedes P002 and makes no runtime compatibility claim.

<a name="p002"></a>

### P002 — Make every submodule reproducibly obtainable

**Status:** **PASSED at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.** Independent reviewer `/root/wave5_final_replay` accepted all four original gates at **2026-11-06 04:29:24 UTC**, after P001 acceptance at 04:06:14 UTC and published independent final source approval. Both fresh hosted clones, all original artifact bytes, strict corruption/failure cases, changed-pin provenance and byte-identical lock regeneration passed review. [Formal P002 acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json), [final replay report](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/README.md), [five-wave ledger](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave-ledger.json). Later documentation/evidence commits preserve the tested implementation. Next permitted phase: P003. Historical records below remain unchanged.

**Depends on:** P001 (**reaccepted first at the same exact source revision**).

**Objective:** Make a clean recursive clone buildable without relying on an earlier developer's cached objects. Relative sibling URLs in a fork can resolve to repositories that do not exist under the fork owner.

**Where:** **Existing:** `.gitmodules`; gitlinks under `src/external/`, particularly `darlingserver`, `cocotron`, `metal`, `dyld`, `objc4`, `foundation`, and `xnu`. **Proposed:** `tools/compat/logic-pro/check_submodules.py`, `docs/compat/logic-pro/submodules.lock.json`, `docs/compat/logic-pro/evidence/P002/`.

**Implementation:**

1. Resolve each of the 149 audited submodule entries against the actual remote, then check recursive dependencies and object availability. Replace inappropriate relative sibling URLs with explicit, verified upstream or maintained-fork URLs; do not silently advance pinned commits.
2. For unavailable commits, locate the authoritative upstream object or create a documented maintained fork from a verifiable source. Record any unavoidable source change separately from URL repair, with diff, provenance, license, and rationale.
3. Add a lock verifier comparing `.gitmodules`, the Git index, recursive checkout status, and the lock manifest. Require a published submodule commit before accepting its parent gitlink. Specify a clean-clone procedure that clears only task-owned caches.
4. Run that procedure in two isolated workspaces with independent object stores. Ensure anonymous readers can obtain public dependencies; personal credentials must not be a hidden build requirement.

**Verification and pass gate:**

- [x] Both recursive clones retrieve all pinned objects and have no uninitialized, mismatched, or conflicted gitlinks — both independent hosted clones passed at exact `d58cca51`; original commands, complete 160-pin graphs and distinct hosts were independently verified. [G1](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json).
- [x] URLs, submodule SHAs, and recursive dependencies match the committed lock manifest — both complete native/verifier graphs and byte-identical regenerated locks match all 160 dependencies and 44 LFS objects. [G2](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json).
- [x] Every changed gitlink is reviewed as a source change, with a reachable commit and explanatory diff — all 14 already-merged upstream changes have explicit old/new source, diff and provenance review; no dependency pin was advanced by this repair. [G3](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json).
- [x] The verifier fails when a test gitlink or URL is deliberately corrupted — both hosted 115-test suites and independent real corruption/recovery cases pass; deliberately wrong committed gitlinks and URLs are rejected. [G4](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json).

**Required evidence:** `docs/compat/logic-pro/evidence/P002/clone-a.log`, `clone-b.log`, lock-verification output, and dependency provenance.

**On failure/next action:** Repair the failing object or URL first; cached partial clones cannot pass P002. Proceed to P003 only after reproducible retrieval.

**README handover:** Record repaired URLs, any changed pins, clean-clone commands, and the P003 toolchain selection.


#### P002 current-source final acceptance — 2026-11-06

**All four original P002 gates and the ordered independent-review contract pass
at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.** P001 was accepted first
at 04:06:14 UTC. The final source approval was published at
`f2cbf424b7a5433b20ecfcb1900e69de0adfbad5`, then the independent final evidence
reviewer accepted P002 at 04:29:24 UTC. [Ordered machine-readable record](docs/compat/logic-pro/evidence/P002/requalification-20261105/ordered-acceptance.json).

| Required proof | Accepted result |
| --- | --- |
| Independent acquisitions | Fresh anonymous recursive clones on separate Ubuntu 22.04/24.04 hosted machines and object stores |
| Dependency identity | 160 recursive gitlinks, 149 direct gitlinks, 161 repositories; complete native and locked path/commit/tree/URL agreement |
| Physical source and LFS | 293,500 physical blob paths per clone; all 44 LFS payloads, 16,128,448 bytes, correct hashes/sizes/modes |
| Mandatory regression execution | 174 P001 and 115 P002 tests on each host, all completed successfully without skipped or expected-failure substitutes |
| Original evidence | Four original hosted artifacts, all 70 raw members reconstructed and compared with original ZIP/extraction bytes; public archive/readback retained |
| Source changes | All 14 preexisting upstream pin changes reviewed; frozen original/current source provenance enforced; no new pin or native-source change |
| Independent failure reproduction | Actual wrong gitlinks/URLs, forged Git objects, CRLF bypass, dirty bytes, modes, symlinks and LFS failure/recovery remain strict failures |
| Final source continuity | 27,812 protected paths plus nine consumed frozen inputs unchanged after tested implementation; no weakened original gate |
| Five requested waves | 15 distinct subagent assignments; final source, evidence and ledger reviews complete |

The repair updates the stale current-source lock/provenance, restores strict P001
historical/current citation and recovery qualification, and closes a real corrupt
loose-blob false pass before CRLF conversion checks. Original raw failure evidence,
accepted historical records and exact upstream dependency pins remain preserved.
[Final replay](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/README.md),
[final source review](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-source/review.md),
[ledger consistency review](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-ledger/README.md).

**No P002 blocker remains. Next permitted phase: P003.** P003 must obtain new
current-source build/install/runtime acceptance; P004 remains unpassed. This
source-reproducibility verdict does not establish Logic Pro or macOS runtime
compatibility.

#### P002 current-source requalification started — 2026-11-05

At the start of this campaign on 2026-11-05, the
`c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a` upstream merge had changed
13 direct and one nested dependency pins relative to the historical lock. The executed 97-test P002
suite failed lock regeneration; P001's 151-test suite had six failures and one
error. Historical accepted evidence could not establish a pass for those new
source gates. Five waves of independent analysis, implementation
and verification are recorded in [the current evidence index](docs/compat/logic-pro/evidence/P002/requalification-20261105/README.md).
All original gates remained binding; the status at that starting point was
**ACTIVE, NOT ACCEPTED**. The live status above and subsequent dated records
report the completed repairs and acceptance decisions.

#### P002 historical implementation record — 2026-10-31 (superseded pre-acceptance design)

**Historical description of the original Git-only candidate. Its status, clone recipe and verification claims are superseded by the independent rejection and corrective implementation below; it is retained without erasing the failed design history.**

- **Scope and ownership:** `/root` owns direct-URL repair, the recursive lock, validator, corruption tests and hosted clone workflow on `master`. The accepted P001 source baseline remains immutable. No changes were made to any gitlink SHA or child source tree; therefore the changed-gitlink review gate has no applicable diff, but the equality of all 160 pins must still be independently confirmed.
- **Direct URL repair:** Replaced the 149 root `.gitmodules` fork-relative sibling URLs with the exact `https://github.com/darlinghq/…` sources recorded as successfully retrieved in [P001 source-retrieval evidence](docs/compat/logic-pro/evidence/P001/source-retrieval.json). The 11 deeper declarations are inside unchanged pinned child repositories; they resolve relative to each now-explicit upstream child origin (or already use absolute public URLs). No auth, mirrors or uncommitted `.git/config` override is required by the intended clone procedure.
- **Lock and regeneration:** [submodules.lock.json](docs/compat/logic-pro/submodules.lock.json) records all 149 direct and 11 nested paths, immediate owner, exact commit/tree, declared URL, resolved acquisition URL and P001 provenance. [make_submodule_lock.py](tools/compat/logic-pro/make_submodule_lock.py) rejects altered pins, different source origins, incomplete provenance and missing descendants before generating the same lock. Future pin changes must have separately audited provenance; a URL repair is not permission to change source.
- **Fail-closed verifier:** [check_submodules.py](tools/compat/logic-pro/check_submodules.py) checks the committed `.gitmodules` in **every** repository against its Git tree, exact lock, effective remote, child HEAD/tree, initialized Git worktree, tracked status, safe paths and recursive ownership. It rejects missing, mismatched and unexpectedly added descendants; it never fetches or repairs missing objects itself. A `PASS` result requires the complete graph, not a root-only smoke test.
- **Deliberate failure coverage:** [Real Git regression fixtures](tests/compat/logic-pro/submodules/test_lock.py) exercise nested relative resolution, uninitialized direct/nested checkouts, wrong pins/origins/URLs, edited committed/worktree metadata, missing lock records and unsafe URL/path input. The local fixture suite must pass again on the exact integrated commit before hosted acceptance.
- **Independent hosted qualification:** [P002 GitHub Actions](.github/workflows/phase2-submodules.yml) runs two separate anonymous `git clone --recurse-submodules` campaigns on Ubuntu 22.04 (clone A) and Ubuntu 24.04 (clone B), with isolated runners/object stores, no cached P001 retrieval, no credentials, an exact workflow-head assertion, native `git submodule status --recursive` and the strict lock verifier. Each job retains `clone-a.log` or `clone-b.log`, environment, native status, verdict and hashes as a workflow artifact even on failure.
- **Verification/acceptance state:** Local static lock reproduction and negative fixtures are implemented. Hosted verification and the separate independent reviewer must be examined **after this implementation is pushed**. Until actual results and source-owning reviewer evidence are committed under `docs/compat/logic-pro/evidence/P002/`, no checkbox above is checked, the phase remains ACTIVE, and **P003 is prohibited**. The P001 hosted success is not borrowed as proof of ordinary recursive clones.
- **Next action:** Verify that both independent anonymous clones retrieve all 160 exact pins, confirm artifact hashes and fail-closed test results, preserve the raw logs and reviewer verdict, then synchronize this section, dashboard and phase index. If an exact object is unavailable, document the URL/pin and repair only through verified upstream/fork provenance; do not skip it.

#### P002 historical Git-only qualification — 2026-10-31 (superseded as completion evidence)

**This record describes what the original campaign actually checked. Independent review subsequently found missing LFS payloads and verifier false passes. Its green results do not establish P002 completion; preserve them as historical Git-object acquisition evidence.**

- **Tested implementation:** [`1bc6d20aa6d59c109475d44822946d3471d638cf`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/1bc6d20aa6d59c109475d44822946d3471d638cf), published to `master`. This changes only 149 direct root URLs, verifier/lock/tests/workflow and documentation; no child source or gitlink pointer is changed. The prior P001 exact pin and provenance register is the independent source oracle for every lock entry.
- **Actual independent clone results:** [Hosted run 41244857162](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41244857162) succeeded on Ubuntu 22.04 (clone A, job 124666053533) and Ubuntu 24.04 (clone B, job 124666053805). Each performed an ordinary public anonymous `git clone --recurse-submodules --jobs 12` without cached objects or P001's acquisition rewrite, asserted the exact root SHA, and passed Git's native recursive status plus the strict lock verifier.
- **Counts on each host:** **160 initialized matching gitlinks; 149 direct + 11 nested; 161 repositories; zero missing, mismatched, conflicted or dirty checkouts.** The host-independent verification JSON and native Git status are byte-identical across hosts. Each runner also passed all **14** real-Git positive/negative tests.
- **Durable evidence:** Both workflow ZIPs were downloaded separately and SHA-256 matched against GitHub's artifact digests (`f1445e8c…` for A and `2e3db9ee…` for B). All six internal checksums per archive passed. The exact raw [clone A](docs/compat/logic-pro/evidence/P002/clone-a.log) and [clone B](docs/compat/logic-pro/evidence/P002/clone-b.log) logs, [verification A](docs/compat/logic-pro/evidence/P002/verification-a.json), [verification B](docs/compat/logic-pro/evidence/P002/verification-b.json), native statuses, environment, exact head and checksums are recorded in the [P002 evidence index](docs/compat/logic-pro/evidence/P002/evidence-index.json). Reproduction instructions remain in [REPRODUCE.md](docs/compat/logic-pro/evidence/P002/REPRODUCE.md).
- **P001 continuity confirmed:** The first P001 rerun at the P002 commit [correctly failed](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41244857142) one historical source citation because the current `.gitmodules` blob had intentionally changed. The original audited citation and accepted P001 evidence remain untouched. The versioned `current_reaudit` checks exact new blob/excerpt hashes and permits **only** 149 `../repo` → `https://github.com/darlinghq/repo` substitutions, rejecting other target/source modifications. The [second P001 campaign](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41245842957) proved **all 63 citations passed on both hosts**, but its *separate* inventory cross-check still demanded the original `.gitmodules` blob in the current tracked tree. That campaign cross-check now accepts the exact P002 re-audited current blob **only** for root `.gitmodules`, with the same 149-rewrite guard; positive and adversarial fixtures bring the P001 suite to **113 passing tests**. The [final hosted campaign 41246526024](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41246526024) is **green on both Ubuntu versions**, with 113/113 tests, 63/63 citations, 160 Gitlinks, 161 source repositories and zero failures on each. Both artifact ZIP SHA-256 hashes and the exact raw [per-host summaries, citation reports, commands and fixture transcripts](docs/compat/logic-pro/evidence/P002/p001-requalification/) are recorded in the [P002 index](docs/compat/logic-pro/evidence/P002/evidence-index.json). This closes the hosted regression; no new P001 independent acceptance is being invented.
- **Independent review still required:** No separate agent/person has approved this P002 work. The two GitHub runners and self-checks do not satisfy the README independence contract. **P002 remains READY FOR REVIEW, not PASSED; P003 is blocked.** The next reviewer must inspect exact code and logs, confirm no changed pins and the P001 re-audit, then commit their verdict and update this dashboard/index before proceeding.

#### P002 independent rejection and corrective implementation — 2026-10-31

- **Reviewed baseline:** `beb991101c944e4b0af3731633399a8b0e47c7ea`. Independent reviewers `/root/p002_acceptance` and `/root/p002_adversarial` reproduced the gaps rather than accepting the prior prose claim. A separate ordinary recursive clone materialized all 161 Git repositories, but all **44 Swift `.dylib` paths were LFS pointer text**, representing **16,128,448 payload bytes** still to retrieve. Four libffi Windows project files had legitimate committed `text eol=crlf` conversions; every other physical Git blob matched.
- **Rejected false passes:** changed root/nested files hidden by assume-unchanged or skip-worktree; executable changes hidden by `core.filemode=false`; untracked runtime inputs; a wrong raw origin masked by `insteadOf`; and a configured clean filter that both concealed a changed file and executed during purported read-only verification. Committed `update=none` could also leave a fresh clone incomplete even when an already initialized clone passed. These are failures of the existing gate, not new or relaxed acceptance criteria.
- **Corrective ownership and behavior:** `/root` replaces Git-status trust with complete tree/index equality and no-filter physical bytes/modes/symlink verification, rejects private checkout attributes/shared object stores/untracked inputs, checks raw and effective origins, pins the complete root `.gitmodules` blob, and validates acquisition metadata. Exact committed bytes or the exact committed built-in CRLF equivalent are accepted; arbitrary transforms cannot waive damage. `/root/p002_lfs_fix` inventories all committed small blobs, locks each LFS pointer/OID/size/mode and its owner's committed `.lfsconfig`, and explicitly hydrates and hashes the actual libraries. `/root/p002_campaign_fix` acquires an immutable root SHA before normal recursive Git initialization, avoiding mutable-master/PR races, and records fixture, acquisition, hydration and verification transcripts plus command exits/checksums.
- **Independent oracles and unchanged source:** original P001 provenance still fixes all **149 direct + 11 nested** commit/tree pairs. The new [LFS provenance](docs/compat/logic-pro/lfs-provenance.json) comes from the pinned Swift commit `471514f4b4985a604b192e1facac9bbc53dedad3` and public endpoint `https://git-lfs.darlinghq.org/lubos/darling-swift`; payload hashes are requirements, not inferred from downloaded bytes. No gitlink, dependency source or P001 historical citation has changed. P001 is source-object inventory, not a claim that pointer files are usable runtime libraries.
- **Observed local checks at integration:** all **95 P002 fixtures** (37 lock/verifier, 42 LFS, 16 campaign) and all **113 P001 regression fixtures** pass. Two independent draft reviewers reproduced the attacks; a separate full-graph check passed physical verification of all 161 repositories and 44 hydrated payloads. The public pinned LFS endpoint supplied all 16,128,448 bytes anonymously; actual Git LFS checkout and repeated hydration were verified. These draft/local observations do not replace exact published-candidate two-host campaigns and final independent acceptance. Initial [rejected reviews and native-object evidence](docs/compat/logic-pro/evidence/P002/history/independent-rejection/) remain preserved. Previously ZIP-only P001 outputs have been prepared in a [lossless content-addressed archive](docs/compat/logic-pro/evidence/P002/p001-requalification/RAW-REPORTS.md) and independently compared byte-for-byte with every original ZIP member. **The large archive's GitHub upload is pending; its manifest, reader and small raw logs are published first. Durable archive publication remains a completion gate.**
- **P003 toolchain selection for handover only:** start qualification with **Ubuntu 22.04 x86_64, LLVM/Clang 14 (`clang-14`/`clang++-14`), CMake and Ninja**, retaining the real GUI/audio components and the dependencies declared by `debian/control`. This is a selected starting recipe, **not** a supported build claim or a P003 implementation. `CMakeLists.txt` explicitly searches Clang 14 and recommends at least Clang 11. P003 must freeze the actual distribution image digest, compiler/linker/CMake/Ninja and package versions, resolve component/install conflicts, and execute all its required probes before calling this recipe supported.
- **Next action and status:** run [the corrected reproduction procedure](docs/compat/logic-pro/evidence/P002/REPRODUCE.md) twice from the published exact SHA, retain all payload/verifier/fixture evidence, rerun P001 continuity, and obtain independent exact-commit verdicts. **Remain in P002.** This implementation record accompanies the behavior change; the later evidence publication must name its resulting commit without a self-referential hash requirement.

#### P002 hosted-client correction and durable multipart evidence — 2026-10-31

- **Published candidate and actual failure:** [`82c9ef60c492852cd89c3327c1885469e57993e8`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/82c9ef60c492852cd89c3327c1885469e57993e8) preserved the independent rejection history and passed 95 local fixtures. In [P002 run 41251291839](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41251291839), both independent Ubuntu runners retrieved all 160 Gitlink checkouts but then failed exactly one of 95 tests: the real Git LFS checkout fixture left pointer text under Git LFS 3.8.1. The strict payload-size check correctly rejected it; the real payload-hydration and final-verifier stages were not reached. Both complete raw artifacts and their verified ZIP/member hashes are preserved in [the hosted-failure history](docs/compat/logic-pro/evidence/P002/history/82c9-hosted-failure/index.json). Local success with Git LFS 3.4.1 does not override this failure.
- **Narrow correction:** Git LFS 3.8.1 internally uses the magic attribute selector `:(top,attr:filter=lfs)` with modern Git. The helper's inherited global `--literal-pathspecs` turned that selector into a nonexistent literal filename. `_lfs_command` now omits that flag only for explicit, preflighted Git LFS acquisition; read-only Git inspection retains its literal-path safeguards. Checkout targets are still locked, validated and separated from options by `--`; no payload assertion or native-client fixture was removed. A new native-Git selector regression reproduces the defect and guards the correction.
- **Executed correction checks:** all **96 P002 fixtures** passed with the official checksum-verified Git LFS 3.8.1 client; all **43 LFS-specific fixtures** also passed with 3.4.1. An independent reviewer reproduced failure before the one-flag correction and **20/20 successful adversarial cases** afterward, plus **six argument-safety cases** using option-like, shell-looking and magic-selector-looking filenames without execution or unintended writes. The lock, provenance and all 160 source pins remain unchanged.
- **P001 continuity:** [run 41251291888](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41251291888) passed on both Ubuntu versions at `82c9ef6`. A separate reviewer reran 113 P001 fixtures and 23 independent positive/rejection cases, confirmed all 63 historical citations and all 160 recursive pin/tree records, and explicitly excluded the evidence reader they authored from their own approval. The replacement candidate must retain these regressions.
- **Evidence preparation, not completed publication:** the large historical P001 archive transfer stalled, so its exact **9,667,936 bytes** were prepared as 50 ordered small parts. Their local manifest binds every piece and the original complete SHA-256 `5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d`. The reader verifies every part and the assembled archive, reconstructing only in a temporary directory outside the checkout. All 32 original report members remain byte-identical; no evidence is dropped or regenerated. Missing, corrupted, extra, reordered, misnamed or symlinked parts fail, even when a valid whole-file copy also exists. Reader authorship and independent review remain separate. **The binary parts and their multipart manifest are withheld from this source-only commit pending explicit archive-publication approval.**
- **Remaining gate:** publish this correction and all exact evidence pieces, run both fresh Git+LFS campaigns against its resulting SHA, record successful complete payload/physical verification and P001 regressions, and obtain final exact-commit independent verdicts. **Remain in P002; P003 is not permitted.** The earlier records above remain historical, not alternate passing claims.

#### P002 evidence-publication authorization hold — 2026-10-31

- **Exact blocked payload:** the historical P001 verification archive, 9,667,936 compressed bytes, SHA-256 `5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d`, containing all 32 original CI JSON/text reports from public-repository run `41246526024`. Publishing it would make those raw reports durable in this public repository.
- **Checks completed without bypassing the hold:** official GitHub repository visibility, run identity and both original ZIP digests were independently verified. Every archive byte was accounted for as canonical headers, the 22 exact deduplicated report objects, or zero padding; no hidden member, special file or trailing payload existed. All objects were parsed as UTF-8 JSON or command/test text. Twelve named credential/private-key/token patterns had zero matches. This is a bounded disclosure check, not a universal secret-free guarantee or a substitute for user authorization.
- **Approval boundary:** a same-API, exact-byte retry was allowed after those checks, but a later safety review explicitly required the user's approval of the exact archive. All new binary requests then stopped; only already-started requests were settled. No alternative route, encoding or indirect publication is permitted. The partial uploaded Git objects are not a complete or branch-published evidence bundle.
- **Unaffected work:** publish the two-file native Git LFS correction, its 96-test suite, the independently tested reader and small diagnostic records, then run the required two-host P002 and P001 campaigns. Their success alone cannot pass the phase while durable evidence and independent final acceptance are missing. The independent provisional verdict is **NOT_ACCEPTED_PUBLICATION_AUTHORIZATION_REQUIRED**; [hold review](docs/compat/logic-pro/evidence/P002/history/evidence-publication-hold/review.json) and disclosure checks are retained.
- **Exact next action:** obtain explicit approval to publish the identified archive to this public repository; only then resume the same reviewed publication process, verify the complete published bytes, preserve new qualification outputs and obtain final acceptance. **P002 BLOCKED; P003 NOT STARTED.** No acceptance criterion has been waived.

#### P002 current candidate qualification — 2026-10-31

- **Source and hosts:** [P002 run 41256694572](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41256694572) qualifies exact PR merge `b628085a` on separate Ubuntu 22.04 and 24.04 machines. Both clone independent object stores, retrieve all 160 original pins and hydrate all 44 locked payloads without credentials. No gitlink, dependency source, URL repair, lock or LFS provenance changed in the latest correction.
- **Independent acceptance of technical gates:** [the source/artifact reviewer](docs/compat/logic-pro/evidence/P002/qualification-b628085/review/independent-review.json) passed 464 checks and independently reran all 96 fixtures. A separate [whole-campaign reviewer](docs/compat/logic-pro/evidence/P002/qualification-b628085/ci-review/hosted-review.json) passed 213 checks over all four current artifacts. Both bind their observations to the exact merge/head/tree identities and exclude publication authorization from their approval.
- **Real PR acquisition exercised:** the optional local commit-presence probe returned 128 because the synthetic PR merge was not in normal branch history; fetching that exact immutable SHA then succeeded. Every required command succeeded. The raw command records retain both results; no required failure is ignored.
- **Raw evidence:** all 36 current P002 members are retained unchanged as plain UTF-8 in [clone A](docs/compat/logic-pro/evidence/P002/qualification-b628085/clone-a/) and [clone B](docs/compat/logic-pro/evidence/P002/qualification-b628085/clone-b/). Official ZIP hashes, every member hash and transcript byte range are verified. The preceding 78dff323 campaign and its independent review are also retained in [qualification-78dff](docs/compat/logic-pro/evidence/P002/qualification-78dff/).
- **Final acceptance, 2026-11-01:** all original technical checkboxes and original raw P002 files remain valid. [Fresh P002 run 41260649124](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649124) passed **96 real fixtures per Ubuntu host**, 160 original pins, all 44 hydrated LFS objects (16,128,448 bytes), physical blob verification and lock regeneration. The [independent P002 continuity review](docs/compat/logic-pro/evidence/P002/qualification-b628085/independent-p002-technical-confirmation.json) and [final ordered evidence acceptance](docs/compat/logic-pro/evidence/P002/qualification-b628085/final-publication-acceptance.json) approved P002 after P001 passed. Both complete archives passed [two-host public-checkout readback](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649315). **P002 PASSED; P003 NOT STARTED.**

<a name="p001-p002-approval"></a>

#### Approved publication and ordered P001/P002 acceptance — 2026-11-01

The earlier automatic review rejected both a direct default-branch update and publication of the historical raw archive and a supplemental inventory. Its decisions and original preapproval reports remain immutable historical evidence. **The user subsequently explicitly approved publishing the two exact archives and all five historical reports to this public repository, then merging [PR #1](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/1) after full readback and independent acceptance.** The reviewed source and evidence branch is `audit/p001-p002-qualification`, with preapproval `master` at `f7bd711`.

Both complete archives were published unchanged in Git as individual files at branch head [`4339085`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/4339085c0a11ef2e33acc3259761ea2f8c8f1214). No original raw report was omitted, reformatted or replaced:

| Publicly published archive | Exact bytes | SHA-256 | Mapping and review |
| --- | ---: | --- | --- |
| Historical [`p001-requalification/raw-reports.tar.xz`](docs/compat/logic-pro/evidence/P002/p001-requalification/raw-reports.tar.xz) | 9,667,936 | `5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d` | All **32 original reports** mapped by the [original reader](docs/compat/logic-pro/evidence/P002/p001-requalification/RAW-REPORTS.md); public Git blob `d7743e5d60c9075aafd12859bd61436b70fd9262` |
| Current [`p001-p002-b628085-raw-reports.tar.xz`](docs/compat/logic-pro/evidence/P002/qualification-b628085/p001-p002-b628085-raw-reports.tar.xz) | 9,594,676 | `8a614792dc1558ecc9584d9e00013f8a6c02cdc2dd7f00e570117e3b8e74e7a5` | [Exact manifest](docs/compat/logic-pro/evidence/P002/qualification-b628085/raw-bundle.manifest.json), [independent review](docs/compat/logic-pro/evidence/P002/qualification-b628085/raw-bundle-independent-review.json), **68 members / 46 deduplicated objects**; public Git blob `8b5ffd70237895540e0ea263545d323916f3eab2` |

All **five supplemental historical P001 reports** totaling **6,531,593 bytes** are published under [the original provenance directory](docs/compat/logic-pro/evidence/P001/reviews/phase1-phase2-audit-20261031/). [Independent supplemental object review](docs/compat/logic-pro/evidence/P002/qualification-b628085/supplemental-published-object-review.json) verified exact public Git object IDs for all five; three smaller reports additionally passed complete remote-byte comparisons, while the two larger reports were bound by exact Git object identity and independently computed local SHA-256 and size. The [original hold report](docs/compat/logic-pro/evidence/P001/reviews/phase1-phase2-audit-20261031/publication-hold.json) records the rejection before explicit approval; it is preserved unchanged.

The [new public Git checkout readback workflow](.github/workflows/p001-p002-archive-readback.yml) ran independently on Ubuntu 22.04 and 24.04 at PR merge `5da6086` (tree `1aeefbf454c4169063742487579199f467a0900c`). [Run 41260649315](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649315) succeeded on **both hosts**. Both unmodified [raw host reports](docs/compat/logic-pro/evidence/P002/qualification-b628085/archive-readback-ubuntu-22.04.json) and [the second host](docs/compat/logic-pro/evidence/P002/qualification-b628085/archive-readback-ubuntu-24.04.json) confirm the two complete archive SHA-256 identities, all original member mappings and the strict current archive container; they are separately bound to official GitHub Actions artifact ZIP digests in the [final independent audit](docs/compat/logic-pro/evidence/P002/qualification-b628085/final-publication-acceptance.json).

The latest [P001 workflow](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649320) and [P002 workflow](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649124) also finished **SUCCESS on both hosts**, running 120 and 96 fixtures per host respectively. Separate reviewers confirmed no source, lock, pinned submodule, LFS provenance, tooling or existing gate changes between the original qualified correction and this evidence publication. The [independent final report](docs/compat/logic-pro/evidence/P002/qualification-b628085/final-publication-acceptance.json) accepted **P001 first, then P002**, preserving the original rejected and preapproval reviews in their dated historical scope. **Both phases PASSED; [PR #1 has since merged into `master`](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/1), whose tree exactly equals the accepted final PR tree. P003 remains NOT STARTED.**

#### P002 hardened-source requalification and subsequent independent acceptance — 2026-11-01

- **Predecessor first:** the fresh [`P001 hardened verdict`](docs/compat/logic-pro/evidence/P001/qualification-5c3c77e/requalification.json) at source `5c3c77ee` was independently approved **before** P002's new verdict. The unchanged P001/P002 historical acceptances remain preserved, not substituted for new tests.
- **Fresh independent acquisition:** [P002 run 41263623117](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41263623117) succeeded on Ubuntu 22.04 job `124721948271` and Ubuntu 24.04 job `124721948363` from the exact same source SHA. Every host ran **97 distinct real fixtures** with an authentic terminal `OK`, retrieved all **160 original gitlinks** and **161 repositories** anonymously with no cached credentials, hydrated and SHA-checked all **44 LFS payloads totaling 16,128,448 bytes**, physically verified **293,308 Git blobs** and regenerated the **byte-identical committed dependency lock**. Source-pin changes: **zero**.
- **Artifact provenance:** ZIP A `13066642379`, SHA-256 `074ef88a65c059ba2e5d6a92041007d7fdcd43aba121351b93e8a1f27dc9c5ac`; ZIP B `13066613073`, SHA-256 `653ab9d7a7716066570913a0a990d7dd0e9b26a7b3e6f3cd757fb079c6ed37ee`. Independently rehashed exact downloaded ZIP bytes, **18/18 CRC members and 17/17 internal checksums** per host. [Unmodified per-host raw clone/lock/LFS/test reports](docs/compat/logic-pro/evidence/P002/qualification-5c3c77e/requalification.json) are published with provenance.
- **Original gates and review:** **G1 PASS** (two anonymous complete clones); **G2 PASS** (160 immutable commits, lock/recursive source/LFS equality); **G3 PASS with no new pin change to review**; **G4 PASS** (wrong pin/URL, corruption, forged summaries and shrunk suites fail closed). Independent `/root/phase2` accepted the scope after `/root/phase1` approved P001; `/root/validation`, `/root/ci` and `/root/docs_evidence` supplied separate source/CI/evidence checks. [Fresh final ordered acceptance](docs/compat/logic-pro/evidence/P002/qualification-5c3c77e/final-ordered-acceptance.json) records roles, evidence and limitations. **P002 PASSED; P003 NOT STARTED.**

#### P002 accepted after current-source continuity restoration — 2026-11-01

At exact `b2c0d4893cace4ddbacf9f7c29503990b07491cd`, [run 41275067090](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067090) passed both fresh anonymous clone campaigns. Each host passed **97 tests**, retrieved all **149 direct + 11 nested pins / 161 repositories**, physically checked **293,417 blobs**, hydrated and verified **44 LFS objects totaling 16,128,448 bytes**, and regenerated the identical dependency lock, SHA-256 `1540d2552f36bd5ed29a640dbe12dfe0e37c618c02ed7fd1d59d4264a8ba5f1b`.

| Official original artifact | Bytes | ZIP SHA-256 |
| --- | ---: | --- |
| [Ubuntu 22.04 / 13071102388](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067090/artifacts/13071102388) | 52692 | `7070f9a6b4fd8a654a86c52dabd4a464158f9bcf265e375c80eafc225d28ee4b` |
| [Ubuntu 24.04 / 13071446003](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41275067090/artifacts/13071446003) | 53124 | `8baa47ea1967384b872ba300c0f86e7afc30d4a7503b461a4cadffe56fd12265` |

Independent `/root/p003_independent_package_review` accepted **P002 G1–G4 at 05:11:26.854450 UTC**, after binding the confirmed P001 verdict at 05:08:55.615852 UTC. The reviewer independently executed 97 fixtures, checked all 18 ZIP members and 17 internal hashes per host, reconstructed complete command-log segments, compared every original pin/tree/owner/URL and LFS identity, and crosschecked both physical inventories. All **1,009 enumerated checks passed**, with no findings. The reviewer did not author the P002 clone/lock/LFS tools; its separate P001 source-audit work was accepted by the other reviewer. Formal local review SHA-256 `08bc83ef5f8db707423226650a0bc3739437764639e423606e26932d3957c52a`; this record preserves the essential acceptance and authorship scope. Raw artifacts remain in their original Actions storage, expiring 2027-01-30; they were not republished after the automatic approval rejection. **P003 may resume; P004 remains NOT STARTED.**

<a name="p003"></a>

### P003 — Pin a complete GUI-capable build and installation

**Status:** **ACTIVE for current source, 2026-11-06.** Waves 1–3 are complete, and all **174 P001 / 115 P002 / 187 P003** local and hosted regression cases pass with zero skips. Latest full run `42169925661` completes compilation and producer runtime probes on both hosts but fails artifact publication because the new final source-status file is unreadable by the uploader. A scoped permission repair and eight restrictive-umask/failure-preservation subcases raise the P003 suite to 188; a fresh full campaign remains required. Wave 3 source/build and runtime code reviews approve the bounded repairs, and the independent package comparison method passes complete historical original-artifact QA. Wave 4 independently reviews the fresh full campaign after exact toolchain acquisition. All original current G1–G4 gates remain pending.

Historically **PASSED** for exact implementation [`89c6c9d`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/89c6c9d85aba6ed1662035e6366298c92ef9c970), independently accepted 2026-11-01 at **10:13:57 UTC**. Those original artifacts and failed attempts remain preserved. P004 remains **NOT PASSED**; no advancement beyond P003 is claimed.

**Depends on:** P002 (**PASSED after P001 at `d58cca51`, accepted 2026-11-06**). [Ordered predecessor acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/ordered-acceptance.json).

**Objective:** Produce an installable x86_64 runtime containing the real GUI and audio framework components needed for subsequent work. A command-line-only package or a developer stub package does not satisfy this phase.

**Where:** **Existing:** `CMakeLists.txt`, `cmake/architecture.cmake`, `cmake/darling_parse_components.cmake`, `src/CMakeLists.txt`, `src/frameworks/CMakeLists.txt`, `src/CoreAudio/CMakeLists.txt`, `debian/`, `rpm/`, `ci/`. **Proposed:** `ci/logic-pro/`, `docs/compat/logic-pro/toolchain.lock.json`, `tests/compat/logic-pro/build/`, `docs/compat/logic-pro/evidence/P003/`.

**Implementation:**

1. Pin compiler/linker, CMake, Ninja or selected build tool, Linux distribution image digest, package versions, and source-built dependencies. Document host kernel and required runtime privileges separately from compiler requirements.
2. Inspect component selection and install collisions, particularly `COMPONENT_gui`, GUI-common components, and `dev-stubs`. Ensure installed AppKit, CoreGraphics, CoreText, ImageIO, QuartzCore, and AudioToolbox resolve to the intended implementations. Do not mistake GUI-stub inclusion for implementation.
3. Repair build failures at their actual owners and pin submodule fixes. Capture compile configuration, install manifest, runtime search paths, missing dependencies, and package contents. Establish a supported baseline first; reproducible historical toolchains do not establish current Logic compatibility.
4. Install into a clean, isolated runtime prefix and execute minimal Mach-O, Foundation, and visible GUI probes. Record limitations exposed by those probes for later phases.

**Verification and pass gate:**

The unchecked boxes apply to the current source. The detailed successful observations and links in these rows describe the preserved historical `89c6c9d` acceptance; each must be reproduced and independently accepted for this campaign.

- [ ] Two clean builds and installs succeed with identical source and toolchain manifests; any output nondeterminism is enumerated. [Original artifacts, complete 138-path difference table and G1 acceptance](docs/compat/logic-pro/evidence/P003/README.md).
- [ ] Installed framework resolution selects the intended implementation rather than a competing developer stub. Seven actual framework Mach-O install names, aliases, owners, dependencies and live loaded paths independently verified.
- [ ] The installed runtime executes a Mach-O computation, a Foundation object operation, and a GUI event round trip with asserted outputs. Five independent real executions additionally passed nonce-bound XPC transaction counts and pixel/XTest evidence.
- [ ] Uninstall/reinstall in an isolated prefix leaves no required dependency supplied only by the previous installation. Both hosts removed 11,941 entries and reran all ten cases after fresh reinstall; a separate source-free host reproduced them from the installed archive.

**Historical P003 acceptance record:** [machine-readable G1–G4 verdict, dated independent review files, six original artifact hashes and complete 138-path cross-build difference table](docs/compat/logic-pro/evidence/P003/README.md). Final source SHA: `89c6c9d85aba6ed1662035e6366298c92ef9c970`; independently accepted 2026-11-01T10:13:57.779150Z. The exact test report and original build/runtime archives, not fixture tests alone, support the four historical gates. Fresh current-source evidence is still required. The installed packages are not byte-identical; the all-byte nondeterminism inventory and unarchived-linker limitation are explicit.

**Required evidence:** `docs/compat/logic-pro/evidence/P003/` build logs, package/install manifests, toolchain lock, and probe outputs.

**On failure/next action:** Correct packaging or component selection before P004; do not weaken probes to accept null implementations.

**README handover:** Record the supported build recipe, real probe results, changed pins, and P004 CI work.

#### P003 Wave 2 integration — 2026-11-06

The combined candidate includes the root-owned current-objc4 configuration repair
at `d0f33422f` and three agent-owned corrections. The aggregate now binds all 63
actual current-source records and their exact reviewed anchor, root commit and
nested pins. The real build EXIT handler records and enforces empty final source
status while preserving earlier failure codes and raw dirty status. Runtime
initialization failures retain truthful FAILED reports without replacing existing
HOME, prefix or evidence state; unexpected exceptions retain their traceback.

Local **174/115/187** regression cases pass with no skips. The original hosted
P001 reports and both unchanged source reports from `42165628353` pass the repaired
consumer. Fifteen new cleanliness tests execute the real EXIT handler and reject
tracked, untracked and submodule mutations, failed Git status and redirected or
missing evidence. All original acceptance assertions remain mandatory. The
[Wave 2 integration record](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave2-integration.json)
binds exact code/input hashes and complete test transcripts; the per-agent notes
record their changes and focused reproduction. No frozen source manifest,
classification producer, dependency pin or toolchain changed.

The workflow floor is now **174/115/187**. Three different Wave 3 reviewers are
challenging this code and preparing independent original-artifact analysis. Fresh
full two-host compilation, installation, all five real runtime campaigns, complete
output-difference classification and non-author acceptance remain required.
**Remain in P003; no current G1–G4 or Logic Pro compatibility pass is claimed.**

#### P003 exact hosted preflight checkpoint — 2026-11-06

Candidate `af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2` passes all **174/115/187**
hosted fixtures with zero skips in run `42169925661`. The [unchanged original
artifact and receipt](docs/compat/logic-pro/evidence/P003/requalification-20261106/attempt-af3566e/README.md)
are preserved with their API SHA-256 and all four ZIP members verified. Full
source/toolchain/build/install/runtime evidence is still pending. Three Wave 3
non-author reviews are active. **Remain in P003.**

#### P003 Wave 3 non-author code reviews — 2026-11-06

[Source/build integration](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave3-source.md)
and [runtime/evidence behavior](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave3-runtime.md)
receive bounded non-author approval at exact `af3566ee`. Reviewers reproduce the
original failure and repaired behavior, real CMake/compiler cases, all 63 original
producer citations, 822 independently mutated provenance cases, real Git EXIT
checks and runtime-oracle corruptions. Protected predecessor inputs, 149 direct
pins and 24 root citation blobs remain unchanged. The reports retain identities,
exact code hashes, original transcripts and current-versus-historical boundaries.

The exact frozen-toolchain acquisition succeeds in run `42169925661`; its raw
job log is retained losslessly. Fresh P001 and P002 workflows also succeed. Both
P003 build containers remain active. Package comparison preparation and all
current original-artifact G1–G4 verdicts remain pending. **Remain in P003.**

#### P003 Wave 3 complete; original-artifact review begins — 2026-11-06

The [independent package method](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave3-package.md)
now reproduces the historical original archives' complete 138-file / 6,447-byte
difference inventory, with zero unknown installed bytes or inventory/metadata
mismatches. Parsed N_OSO timestamps, four exact source-bound build-time strings
and four recomputed UUIDs account for every historical change. A separate
reviewer independently reconstructs nano UUIDs and proves a changed byte inside
an excluded STABS region still fails the full-byte comparison. An unknown byte
and a missing source binding also fail. This validates the review method only;
none of these historical observations is a current-candidate gate result.

All three primary Wave 3 assignments and the supporting UUID review are complete.
Three new Wave 4 reviewers own the original current build, package/framework and
runtime evidence. The tested implementation `af3566ee` finishes both build jobs
with an artifact-publication failure; the original logs and scoped repair are
recorded below. The helper states that intermediate linker bytes
were not archived and enumerates their recorded hashes/banners separately; it
claims exhaustive installed-byte classification only. Fresh original artifacts
and final Wave 5 acceptance remain required. **Remain in P003.**

#### P003 Wave 4 artifact-publication repair — 2026-11-06

Both original `af3566ee` hosts reach all 16,594 compilation actions, first-install
probes, uninstall/reinstall and second-install probes. Their upload steps fail
with `EACCES` on root-owned `source-status-after.txt`; no build archive is
finalized and the independent replay/comparator are skipped. [Original decoded
job logs, exact hashes and failure receipt](docs/compat/logic-pro/evidence/P003/requalification-20261106/attempt-af3566e/failed-publication.json)
preserve this unsuccessful campaign without treating producer summaries as
independent behavioral acceptance.

The EXIT handler now makes only its newly and exclusively created status file
readable with mode 0644, using `fchmod` on the owned descriptor so umask 077 cannot
remove uploader access. Exclusive/no-follow creation, inode identity, dirty-source
rejection and the original nonzero exit code remain enforced. One new test runs
eight combinations of umask 022/077, clean/dirty source and prior success/failure
against the real shell handler. The complete local P003 suite passes all 188 tests with zero skips in 31.111 seconds;
[exact code and transcript hashes](docs/compat/logic-pro/evidence/P003/requalification-20261106/wave4-permission-repair.json)
record the repair. The hosted regression floor is 174/115/188. Fresh original build archives and five complete runtime campaigns still require
independent Wave 4 and Wave 5 review. **Remain in P003.**

#### P003 implementation record — 2026-11-01

- **Starting revision:** `03e2880ba319d4b2b165c162cef4bffedb89d586`; all 160 original submodule pins and the accepted P002 source lock remain unchanged.
- **Implemented:** `ci/logic-pro/` freezes an observed Ubuntu 22.04 image digest, authenticated snapshot packages and compiler/tool hashes, then performs two clean builds with `cli,gui`, x86_64, Clang 14 and a dedicated `/opt/darling-p003` install. `.github/workflows/phase3-build.yml` runs the campaigns on independent disposable hosts with the same image archive.
- **Behavior under test:** the installed Mach-O probe computes independently checked FNV-1a values; Foundation sorts and preserves object/data values; AppKit renders a visible window and handles externally injected X11 click/nonce input, changes its pixels, and acknowledges completion. Missing/invalid arguments and incorrect/duplicate outputs fail. Seven intended framework image paths and their real build owners are checked.
- **Lifecycle:** ownership-checked removal proves the dedicated installation absent; the stopped first Darwin prefix is removed; a second fresh prefix repeats every runtime case after reinstall. The generic global uninstall script is not used for this isolated qualification.
- **Local result:** 122 P001 and 97 P002 regression fixtures pass. The first P003 implementation passed 50 focused fixtures; independent review added aggregate, lifecycle and native-dependency cases and repaired missing-HOME, persistent-descriptor and private-namespace shutdown defects. The final candidate fixture count and raw hosted logs are recorded by the workflow; these verifier tests do not establish runtime acceptance.
- **Evidence:** [P003 evidence index](docs/compat/logic-pro/evidence/P003/README.md). Raw hosted logs, observed lock, install manifests, captured X11 pixels and exact-SHA reviewer verdicts are pending. Existing successful legacy Debian builds do not satisfy these runtime gates.
- **Known limitations:** the first snapshot/toolchain acquisition and real build/probes have not yet completed. The local editor environment has no Docker/Clang and insufficient build disk; actual qualification uses the hosted workflow. All original checkboxes stay unchecked until observed evidence supports them.
- **Independent review:** `/root/p003_independent_build_review`, `/root/p003_independent_runtime_review`, `/root/p003_independent_package_review` are reproducing critical verifier cases and will review the actual hosted results.
- **Next permitted phase:** remain in **P003**. P004 is not started.

#### P003 hosted attempt and bootstrap repair — 2026-11-01

Candidate `0f69cb5a3bce971150279a9dfe9a888387eeb603` ran [qualification 41269126730](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41269126730). The hosted regression job passed **122 P001, 97 P002 and 82 P003 fixtures**. Toolchain setup failed because the minimal Ubuntu image had no CA trust bundle for snapshot HTTPS; the two build/runtime jobs were correctly skipped, and no phase checkbox passed. [Original failure evidence](docs/compat/logic-pro/evidence/P003/attempt-0f69cb5/result.json) is preserved.

The repair mounts the runner's public CA trust bundle ephemerally during Docker package bootstrap, retains TLS verification and signed APT metadata, makes APT index failures fatal, and pins the observed Ubuntu image digest. Toolchain capture runs with the caller UID so the host can seal its observed lock. No acceptance condition is relaxed. **Remain in P003:** rerun the full pinned build/install/runtime campaign and fix any observed failure before independent acceptance.

#### P003 observed toolchain lock and host identity correction — 2026-11-01

Candidate `354f7687a7ba809ffdbfc38ca7fea12ad86ba08f` successfully froze the authenticated Ubuntu snapshot in [run 41269315882](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41269315882), with **511 exact package versions**, Clang/LLVM **14.0.0**, CMake **3.22.1** and Ninja **1.10.1**. The observed [toolchain lock](docs/compat/logic-pro/toolchain.lock.json) is now committed; subsequent acquisition must reproduce its package versions, tool bytes, base image and recipe. The toolchain freeze received an [independent exact-lock review](docs/compat/logic-pro/evidence/P003/attempt-354f768/independent-freeze-review.json).

Both independent build hosts then rejected the tool identity before compilation. Their original logs reported only `tools` as different; the frozen dsymutil banner contains the dynamically detected `Host CPU: (unknown)` value. The next verifier preserves the complete per-host raw observation and dotted differences, and separates **only that explicit host CPU value** from installed tool identity. All binary hashes, package pins, tool paths, static version strings and target fields remain exact. Raw host observations must confirm the diagnosis in the next run; the previous failure is not retroactively counted as passed. [Both failed reports and hashes](docs/compat/logic-pro/evidence/P003/attempt-354f768/result.json) are preserved. Local qualification fixtures now pass **84 tests**. **Remain in P003**; no compile, install or runtime checkbox is checked.

#### P003 actual Release failure and independent installed-package replay — 2026-11-01

Candidate `00a8df32452757765296378ba5e6ea0b7b94de7f` ran [qualification 41270430492](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41270430492). Hosted fixtures passed **122 P001, 97 P002 and 84 P003 tests**. The reconstructed toolchain matched all **511 package versions and static tool identities**. Both hosts verified **160 gitlinks, 161 repositories, 44 LFS payloads and zero dirty repositories**. Actual raw observations now confirm the CPU-only distinction: the image was captured on `znver3`; host A reported `icelake-client`, with only `tools.dsymutil.version_output` differing; host B matched the capture exactly. [Independent host review and complete original build artifacts](docs/compat/logic-pro/evidence/P003/attempt-00a8df3/result.json) are retained with SHA-256 and per-member hashes.

Both hosts reached real compilation and failed the same `objc-runtime.mm` consistency assertion: the pinned `darling-objc4` CMake directory unconditionally defined `OBJC_IS_DEBUG_BUILD=1`, while Release supplied `NDEBUG`. The integration now replaces that one child-directory definition with the value appropriate for Release, RelWithDebInfo, MinSizeRel, Debug or the default configuration. It preserves the runtime assertion and all child pins. Real local CMake/compiler regressions reproduce the original failure and compile/execute all five repaired configurations without opposing definitions; the independent build reviewer reproduced this independently.

The runtime campaign now explicitly enables `STUB_VERBOSE`, retains known placeholder diagnostics from finalized stdout/stderr, and fails on any detected generic stub or unimplemented-operation marker. The aggregate rechecks the raw logs and binds each host's observed toolchain to the frozen lock. A separately authored archive verifier and runtime driver add a third disposable-host replay of the installed package, with no source/build tree mounted. That replay repeats computation, Foundation, actual GUI input/pixels and namespace shutdown using independent byte/pixel oracles. The two original clean-build and reinstall campaigns remain mandatory; this additional check addresses possible dependence on build-tree files.

Cross-review reproduced archive extraction with real GNU tar, hardlinks, guest absolute symlinks and setuid modes; independent runtime decoder/descriptor/timeout checks; and rejection of forged computation, hidden stub diagnostics, altered driver copies, incomplete shutdown and retained source mounts. The current fixture suite is required to contain at least **120 P003 tests**. These are verifier/configuration tests, not a successful Darling execution. **P003 stays ACTIVE, 2/96 phases accepted, and P004 remains NOT STARTED.** Next action: run the repaired exact candidate through both clean builds, both install/reinstall campaigns and the independent installed-package replay; inspect and repair every actual failure before acceptance.

#### P003 dyld linkage failure and predecessor regression — 2026-11-01

Candidate `d89920b447658cfa01e9645864f2315cad4e386a` passed all **122/97/120 fixtures**, exact toolchain identity and all 160 immutable child pins. Both full clean builds compiled objc4 with the correct Release definition and reached dyld linkage. Both then failed on a 32-bit relative register-name lookup table in static libunwind: the pinned ld64 cannot encode this compiler-generated representation under the chained fixups required by dyld startup. [Original hosted artifacts, hashes and independent review](docs/compat/logic-pro/evidence/P003/README.md) record the failure. The raw bundle is retained in Actions; automatic review rejected its republication into public Git history. No installation or runtime case executed.

The separate source-baseline workflow exposed five stale CMake citations, so **P001 is REOPENED and P003 is BLOCKED**. Proposed compiler adaptation remains unmerged while the exact source-audit correction and ordered P001/P002 requalification run. No gate is waived and no dependency pin is changed.

#### P003 static-unwind compatibility repair and early source validation — 2026-11-01

After P001 and P002 were independently accepted in order at `b2c0d489`, P003 resumes with a private C++ compiler option on `unwind_static`: `-fno-jump-tables` for Clang/AppleClang. `cmake/darling_unwind_configuration.cmake` verifies that the expected static target exists; the parent calls it immediately after the libunwind subdirectory. The shared unwind target and consumers receive no such option. Dyld retains its required chained fixups, and all dependency pins remain unchanged.

The exact frozen Ubuntu Clang 14 executable, SHA-256 `31925065812631303cf9af9a30b2f56427d2102667a87a9fb4ba03a306104589`, reproduced the failure using the pinned register-name function. Real CMake Mach-O builds emit **35 relative table entries / 70 paired four-byte relocations** in the control and **zero** with the adapter. Both optimized native variants return the independently expected result for **51 inputs**, including every valid register, the hole at 16, out-of-range values and integer limits; identical output SHA-256 `879cbb9be382326578400ec4862804628f97d01e5853ce6e82e6f1201071c8d0`. `/root/p003_independent_runtime_review` authored the reproducer; `/root/p003_independent_build_review` independently parsed the actual objects, reran both executables against its own oracle, verified all 61 proof files and matched both headers to their original Git blobs. This proves the targeted representation change, not a successful full Darling link or runtime.

Both hosted builds now run the actual 63-citation current-source verifier before compilation, with full root history available, and require the exact Clang 14 before/after regression. The aggregate binds the source rows and their re-audits to the checked-out manifest and verifies the compiler proof's identity and retained files. A third exact additive CMake re-audit preserves every historical source assertion, and the accepted P001 fixture floor advances to 130. The integrated local suites pass **130 P001 and 136 P003 fixtures** with no skips; the required hosted floors are now 130/97/136. The 14 new aggregate rejection cases were independently reproduced. Raw regression logs, compiled objects and Ninja metadata are retained by the existing Actions evidence workflow. **Remain in P003:** run the integrated candidate, fix each actual failure, then independently inspect the completed build/install/probe/reinstall and archive-only replay evidence. No P003 checkbox is checked yet.

#### P003 first complete GUI builds and real runtime-startup failure — 2026-11-01

Exact candidate `2409473d37b951a0dd44346f128edb2112de6b25`, tree `24d9386e02abc6b29a5fd18f786833ea3986e34e`, passed [P003 run 41276794652](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652)'s **130 P001 / 97 P002 / 136 P003** verifier fixtures and frozen 511-package toolchain capture. The current-source 63-citation audit, all 160 recursive pins and 44 LFS objects, and exact Clang 14 codegen regression passed on both fresh hosts. The corrected static libunwind compiled, dyld linked with its required chained fixups, and **both entire 16,590-step GUI builds completed**. Both real first installations succeeded with identical sets of **11,941 installed entries**; intended framework provenance and native ELF resolution checks (**4 native entries and 21 wrapped SONAMEs**) passed. These are first successful complete-build and first-install observations, not P003 acceptance.

The first real Mach-O computation failed identically in both fresh installations after approximately 15 seconds: `darling exec` returned 1 because `/p003/runtime-first/var/run/shellspawn.sock` did not exist. It printed no computation record. The mandatory shutdown did exit and release its private mount namespace; none of the subsequent Foundation, visible-GUI, uninstall/reinstall or independent archive-only checks executed. A separate installed `lib/binfmt.d/darling.conf` pointed to obsolete `libexec/darling/bin/mldr` paths despite the actual `libexec/darling/usr/libexec/darling/mldr` installation; the next candidate fixes all three loader references. The pinned darlingserver directly executes the correct loader for initial launchd, so this configuration mismatch alone is **not** established as the socket failure's cause. The original failed run is **P003 FAILED RUNTIME STARTUP**.

Original unmodified hosted build artifacts: [A 13072621775](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652/artifacts/13072621775), **1,547,432 bytes**, ZIP SHA-256 `bfcd243e0c0d2ca451bedf85750578f0db028ad3892a498c22c46349d0aa3b05`; [B 13071818748](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652/artifacts/13071818748), **1,547,174 bytes**, SHA-256 `a5cbd625601a49604eecbc4fe3eb65e8e55fca772a9b009b1fa7e57edc5820d7`. The independent build reviewer verified all 235 ZIP members per host and original stdout/stderr and qualified the compiler fix, but explicitly rejected P003 runtime acceptance at 06:02:13 UTC. Independently accepted current-source and dependency continuities: [P001 41276794767](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794767), 05:30:32 UTC; [P002 41276794763](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794763), 05:31:01 UTC. All 160 pins remain unchanged.

The next exact candidate preserves every assertion and requires the original complete campaign. It records bounded observed launchd/server process trees during the first real Mach-O start and, on failure after installation, preserves the actual first installed package for independent diagnosis before disposable-host teardown. Neither record can satisfy a behavioral gate or change a nonzero outcome. The loader-path regression is covered by real CMake File-API prefix and handler checks. Five new startup-observation tests plus two binfmt tests raise the P003 hosted fixture floor to **143** (prior-phase floors remain 130 and 97). **2/96 accepted; P003 ACTIVE, all four checkboxes unchecked; P004 NOT STARTED.**

<a name="p004"></a>

### P004 — Establish CI that cannot manufacture compatibility success

**Status:** IN DEVELOPMENT — NOT PASSED; no live gate approval on an exact integrated source SHA yet.

**Depends on:** P003 (historically PASSED at `89c6c9d`; **REOPENED for current master** until new exact-source G1–G4 acceptance).

**Objective:** Turn build success into a reliable prerequisite while keeping execution, behavioral correctness, and application acceptance distinct. Existing package automation is not Logic certification.

**Where:** **Existing:** `.github/workflows/actions.yaml`, `ci/`, `tests/`, root and test CMake integration. **Proposed:** `.github/workflows/compat.yml`, `tools/compat/logic-pro/check_gates.py`, `tests/compat/logic-pro/harness/`, `docs/compat/logic-pro/gates.json`, `docs/compat/logic-pro/evidence/P004/`.

**Implementation:**

1. Add separate clean-source, build/install, runtime-probe, and evidence-validation jobs. Run privileged/runtime tests only on deliberately provisioned runners; an unavailable runner must report BLOCKED rather than PASS.
2. Define machine-readable PASS, FAIL, BLOCKED, and permitted NOT-APPLICABLE results. Missing artifacts, empty test discovery, timeout, skipped prerequisite, and infrastructure failure must all prevent phase advancement.
3. Test the harness itself using deliberate faults: wrong computed result, crash, hang, missing callback, missing executable, and a stub that returns success without changing output. Require meaningful assertions, process exit capture, wall-clock deadlines, and artifact hashes.
4. Separate public synthetic fixtures from licensed Logic/reference-Mac jobs. Store only approved logs and reproducible metadata in public CI. Link private application results by stable evidence ID without pretending their absence is success.

**Verification and pass gate:**

- [ ] A clean supported build and all P003 behavioral probes execute on CI, with discovered/executed counts recorded.
- [ ] Every intentional fault is detected and prevents the appropriate gate from passing.
- [ ] Missing runners, missing licensed fixtures, and skipped jobs yield BLOCKED or FAIL, never green compatibility claims.
- [ ] Gate validation rejects a phase marked complete without predecessor and required evidence records.

**Required evidence:** `docs/compat/logic-pro/evidence/P004/` workflow run IDs, harness fault matrix, machine-readable results, and artifact-retention policy.

**On failure/next action:** Fix the harness before trusting additional phase results. Start P005 only with trustworthy status reporting.

**README handover:** Record working CI jobs, blocked infrastructure, fault-injection results, and P005 target-selection requirements.

<a name="p005"></a>

### P005 — Identify and lock the newest eligible Logic targets

**Status:** NOT STARTED.

**Depends on:** P004 (PASSED).

**Objective:** Define exact, legally obtained test artifacts for the newest verified x86_64-compatible Logic release, and record preliminary research for the latest ARM release. Product marketing, OS requirements, and application CPU slices are different evidence. Complete ARM binary/reference qualification is required in P069 and must not block the short-term Intel track here.

**Where:** **Existing:** loader/build architecture configuration for comparison, without changing it to spoof eligibility. **Proposed:** `tools/compat/logic-pro/inspect_logic_bundle.py`, `docs/compat/logic-pro/targets.json`, `docs/compat/logic-pro/target-selection.md`, `docs/compat/logic-pro/evidence/P005/`.

**Implementation:**

1. Record current official release candidates, distribution channel, version, build number, release/inspection dates, acquisition provenance, bundle identifier, minimum OS declarations, and executable hashes. Research observed Logic 12.4 does not by itself establish whether its purchased bundle contains x86_64, ARM, or both.
2. Inspect every nested executable, framework, XPC service, plug-in, and helper using Mach-O metadata: slices, CPU subtypes, `LC_BUILD_VERSION` or equivalent minimum OS command, linkage, signing metadata, and entitlements. Record arm64e requirements separately from ordinary arm64.
3. Test the highest candidate with an x86_64 slice on a supported Intel reference Mac. If it fails eligibility, investigate the next candidate and document evidence. An unavailable newer candidate makes “latest verified” provisional; an older convenient bundle cannot silently become “latest compatible.”
4. Freeze Intel target hashes and define upgrade review triggers. Maintain the verified x86 baseline and a clearly provisional ARM research manifest/feature delta. Inspect ARM binaries if available, but record unavailable ARM assets or reference hardware as pending P069, without claiming their verification or blocking otherwise complete Intel acceptance.

**Verification and pass gate:**

- [ ] The Intel target manifest contains inspected binary metadata and reproducible hashes; preliminary ARM information is clearly labeled and every unverified ARM requirement is assigned to P069.
- [ ] Evidence establishes the newest eligible x86 candidate among the current release candidates reviewed; unresolved acquisition or eligibility blocks the claim.
- [ ] The x86 target completes a reference-Intel-Mac launch and project-open test; no ARM execution success is claimed without separate evidence.
- [ ] Distribution-channel, OS, architecture, and feature differences are explicitly reconciled.

**Required evidence:** `docs/compat/logic-pro/evidence/P005/` metadata reports, candidate comparison, reference launch results, and official source links; no proprietary bundles committed.

**On failure/next action:** Resolve access or eligibility; never substitute a guessed version. Then begin P006.

**README handover:** Publish exact selected versions/builds and confidence, outstanding blockers, and the P006 reference matrix.

<a name="p006"></a>

### P006 — Build reference-Mac evidence and canonical workloads

**Status:** NOT STARTED.

**Depends on:** P005 (PASSED).

**Objective:** Define observable Intel success before implementing compatibility. A reference Intel Mac provides the required behavioral oracle here; the complete Apple silicon reference is established in P069. Reference Macs are test infrastructure, not substitutes for the requested Linux host.

**Where:** **Proposed:** `tests/compat/logic-pro/workloads/`, `tests/compat/logic-pro/reference/`, `tools/compat/logic-pro/capture_reference.py`, `docs/compat/logic-pro/lab.json`, `docs/compat/logic-pro/evidence/P006/`. **Existing:** `tests/` supplies integration points for synthetic probes.

**Implementation:**

1. Record Intel reference hardware, OS build, Logic build, user locale, display scale, audio/MIDI interfaces, sample rates, buffer sizes, content packs, and plug-in versions. Keep any provisional ARM observations separate; document known native feature differences and leave unverified ARM reference work explicitly for P069.
2. Create versioned projects and deterministic interactions covering empty launch, dialogs, save/reopen, recorded audio, MIDI instruments, editing, automation, bounce, plug-in scanning, content loading, and long sessions. Use redistributable generated signals and original MIDI fixtures; keep licensed content locally with hash manifests.
3. Define expected results per workload: visible controls, project structure, callback sequence, numerical/audio comparison tolerance, timing envelope, and resource budgets. Record nondeterminism explicitly; screenshots alone cannot certify a DAW.
4. Capture cold and warm runs, offline and authorized-online behavior where relevant, and repeated measurements. Predeclare sample sizes and tolerance rationale before Linux results are observed.

**Verification and pass gate:**

- [ ] Every workload has fixed inputs, exact steps, expected outputs, target feature applicability, and reproducible reset instructions.
- [ ] The selected Intel baseline completes three repeat runs with matching semantic results; variable metrics have measured ranges.
- [ ] All mandatory Intel feature categories map to at least one workload, including project integrity and real-time operation; known ARM-only categories are recorded as P069 obligations without an early ARM pass claim.
- [ ] A second operator or clean lab session reproduces the baseline using the written procedure.

**Required evidence:** `docs/compat/logic-pro/evidence/P006/` lab manifest, workload hashes, reference outputs, tolerance justifications, and reproducibility report.

**On failure/next action:** Repair ambiguous workloads or unstable baselines before P007. Do not set Linux acceptance thresholds after seeing failures.

**README handover:** Link the canonical matrix, record lab availability, and identify the P007 closure-capture workload sequence.

<a name="p007"></a>

### P007 — Map the complete reachable application dependency closure

**Status:** NOT STARTED.

**Depends on:** P006 (PASSED).

**Objective:** Discover the actual APIs and services the selected Intel Logic build uses, including delayed paths that a successful initial load would miss. Any preliminary ARM findings remain separate; the complete ARM closure is required in P069.

**Where:** **Existing:** `src/external/dyld/`, `src/frameworks/`, `src/private-frameworks/`, `src/softlinking/`, `src/xtrace/`. **Proposed:** `tools/compat/logic-pro/dependency_closure.py`, `docs/compat/logic-pro/dependency-closure.json`, `tests/compat/logic-pro/fixtures/macho/`, `docs/compat/logic-pro/evidence/P007/`.

**Implementation:**

1. Recursively scan all target executables and bundled libraries for load commands, reexports, weak imports, lazy bindings, Objective-C classes/selectors, Swift dependencies, bundle-relative paths, and private frameworks. Associate each requirement with architecture, image, and feature.
2. Exercise P006 workflows on the Intel reference system and collect permitted dyld, bundle loading, XPC/service, file/resource, and API observations. Record `dlopen`, `NSBundle`, soft-linking, plug-in discovery, and feature-triggered helpers that static imports omit.
3. Join requirements to current exported symbols and source implementations. Classify implemented-and-tested, partial, stub, absent, unknown, and not reached in the declared corpus. A symbol-name match does not count as implementation.
4. Build a ranked blocker list by first use, dependency fan-out, and user-visible impact. Preserve unknown runtime-discovered edges; explicitly scope third-party plug-ins rather than claiming all possible software is covered.

**Verification and pass gate:**

- [ ] Every bundled Mach-O image and declared workflow in the frozen Intel target has an architecture-specific inventory and capture result; incomplete ARM inventory is explicitly assigned to P069.
- [ ] Every observed dependency edge maps to an owner/path and implementation classification, including weak and late-loaded edges.
- [ ] Deliberate test fixtures containing `dlopen`, weak imports, and helper launches are discovered correctly.
- [ ] Unknown or inaccessible mandatory paths are listed as blockers, with no coverage claim inferred from an initial launch.

**Required evidence:** `docs/compat/logic-pro/evidence/P007/` static reports, workload-tagged runtime traces, classification provenance, and prioritized blocker graph.

**On failure/next action:** Expand the captures or repair scanner gaps before P008; revisit this closure whenever a later workload adds a dependency.

**README handover:** Record coverage boundaries, leading blockers, actual source owners, and the P008 instrumentation priorities.

<a name="p008"></a>

### P008 — Make crashes, hangs, and false-success stubs observable

**Status:** NOT STARTED.

**Depends on:** P007 (PASSED).

**Objective:** Identify the first incorrect observable behavior without allowing stubbed APIs to hide it behind nominal success.

**Where:** **Existing:** `src/crash/`, `src/libcrashhandler/`, `src/xtrace/`, `src/startup/mldr/`, `src/CoreAudio/AudioToolbox/stub.h`, `src/CoreAudio/CoreAudio/stub.h`, and reached framework stub implementations. **Proposed:** `tools/compat/logic-pro/collect_failure.py`, `tests/compat/logic-pro/telemetry/`, `docs/compat/logic-pro/stub-policy.json`, `docs/compat/logic-pro/evidence/P008/`.

**Implementation:**

1. Add correlated process/thread IDs, monotonic timestamps, image UUIDs or build IDs, module-relative addresses, loaded-image maps, and symbolication manifests. Preserve Linux host and guest exception contexts rather than losing the Mach-O frame when crossing the boundary.
2. Classify stubs by contract: unsupported error, absent object, inert success, missing callback, or uninitialized output. Provide an instrumented test mode that traps or records the first reached unsupported required operation. Production behavior must return meaningful supported errors without inventing completion.
3. Add bounded watchdogs and stack capture for UI deadlocks, helper timeouts, and callback starvation. Buffer diagnostics off real-time threads; instrumentation must not become the timing failure under investigation.
4. Sanitize paths, receipts, and project/private data while retaining enough identifiers to reproduce. Establish a deterministic bug report bundle and failure signature for deduplication.

**Verification and pass gate:**

- [ ] Injected crash, hang, swallowed exception, and false-success stub each produce distinct, actionable evidence.
- [ ] Stack frames resolve to exact parent/submodule revisions and the first relevant unsupported call is identified.
- [ ] A success-returning stub with unchanged output fails its behavioral assertion.
- [ ] Logging overhead is measured and bounded; disabling diagnostic capture does not change semantic test results.

**Required evidence:** `docs/compat/logic-pro/evidence/P008/` injected-failure bundles, symbolication checks, stub classification, and overhead measurements.

**On failure/next action:** Repair observability before P009; lack of crash output is not proof of correctness.

**README handover:** Record instrumentation entry points, unresolved blind spots, and P009 oracle integration.

<a name="p009"></a>

### P009 — Establish differential compatibility testing against macOS

**Status:** NOT STARTED.

**Depends on:** P008 (PASSED).

**Objective:** Compare behavior using identical synthetic workloads on the reference Mac and Linux runtime, with explicit allowances only for documented nondeterminism.

**Where:** **Existing:** `tests/` and its build integration. **Proposed:** `tests/compat/logic-pro/runner/`, `tests/compat/logic-pro/contracts/`, `tools/compat/logic-pro/compare_results.py`, `docs/compat/logic-pro/normalization.json`, `docs/compat/logic-pro/evidence/P009/`.

**Implementation:**

1. Define a portable result schema containing call arguments, returned values, initialized outputs, side effects, errors, callbacks, ordering, ownership/lifetime observations, and elapsed monotonic times. Each probe must assert the contract that matters to its consumer.
2. Build the same probe source with recorded reference and target toolchains. Separate API/ABI differences from accidental compiler or SDK differences. Exercise success, invalid argument, resource exhaustion, cancellation, and teardown paths.
3. Normalize only declared variable fields such as absolute temporary directory names or generated IDs. Never normalize away error codes, missing callbacks, truncated data, out-of-order execution, or numerical discrepancies.
4. Add seedable repetitions and structured artifacts. Require a reference rerun or documented authoritative contract when behavior is ambiguous; do not promote one accidental observation into a universal requirement.

**Verification and pass gate:**

- [ ] A representative set of process, Foundation, IPC, file, and UI probes produces comparable records on both platforms.
- [ ] Injected wrong return values, output bytes, callback order, and missing side effects are all detected.
- [ ] Every normalization rule is narrowly justified and tested against a deliberately corrupted fixture.
- [ ] Results retain exact source, binary, environment, seed, and reference identifiers for independent reproduction.

**Required evidence:** `docs/compat/logic-pro/evidence/P009/` schema version, paired probe outputs, negative-control results, and comparison report.

**On failure/next action:** Fix the comparator or uncertain contract before P010; never edit expected outputs merely to match the current implementation.

**README handover:** Link reusable runner commands and oracle availability; identify P010 loader fixtures and remaining comparison limitations.

<a name="p010"></a>

### P010 — Correct x86_64 Mach-O loading and process startup

**Status:** NOT STARTED.

**Depends on:** P009 (PASSED).

**Objective:** Execute the selected x86_64 application and helper image formats with correct memory and initial-process semantics before debugging higher frameworks.

**Where:** **Existing:** `src/startup/mldr/loader.c`, `src/startup/mldr/mldr.c`, `src/startup/mldr/commpage.c`, `src/startup/mldr/stack.c`, `src/libelfloader/`, `src/duct/`. **Proposed:** `tests/compat/logic-pro/macho_loader/`, `docs/compat/logic-pro/evidence/P010/`.

**Implementation:**

1. Compare loader support with P007 image metadata. Implement or repair actually required load commands, segment alignment, zero-fill, entrypoint selection, page protections, image slide handling, executable-stack policy, and fat-binary slice selection. Validate file bounds and reject malformed or unsupported images clearly.
2. Verify initial stack alignment, `argc`/`argv`/environment/apple vectors, thread-local initialization, commpage data, CPU capability reporting, and host-to-guest entry transitions. Report only instruction capabilities the host/runtime can execute correctly.
3. Exercise image mapping, remapping, signal delivery, exception/unwind visibility, and cleanup under failed loads. Keep Mach-O address space assumptions consistent with Linux mappings and darlingserver bookkeeping.
4. Build minimal fixtures mirroring the selected target's load-command combinations and helper entry styles; use them to isolate issues without repeatedly launching the full DAW.

**Verification and pass gate:**

- [ ] All target-relevant loader fixtures compute expected results and expose correct initialized and zero-filled data.
- [ ] Memory protection, alignment, thread-local storage, and initial-stack assertions match the reference contract.
- [ ] Malformed fixtures fail deterministically without host memory corruption or leaked mappings.
- [ ] The selected target and mandatory helpers reach dyld initialization with symbolicated evidence, without claiming application startup complete.

**Required evidence:** `docs/compat/logic-pro/evidence/P010/` image metadata, memory-map comparisons, fixture outputs, rejected-image tests, and startup traces.

**On failure/next action:** Fix the smallest failing image fixture, then rerun the matrix. P011 starts only after loader correctness passes.

**README handover:** Record supported commands and remaining exclusions, changed startup paths, and the first dyld blocker for P011.

<a name="p011"></a>

### P011 — Resolve dyld images, imports, fixups, and runtime loading

**Status:** NOT STARTED.

**Depends on:** P010 (PASSED).

**Objective:** Bind the selected target's complete image graph correctly, including runtime-loaded bundles, without arbitrary import suppression.

**Where:** **Existing:** `src/external/dyld/`, `src/startup/mldr/`, `src/softlinking/`, framework install configuration in `src/frameworks/CMakeLists.txt`. **Proposed:** `tests/compat/logic-pro/dyld/`, `tools/compat/logic-pro/trace_images.py`, `docs/compat/logic-pro/evidence/P011/`.

**Implementation:**

1. Audit the pinned dyld against required load-command and fixup formats. Implement target-used rebase/bind streams, chained fixups where present, export tries, reexports, weak/coalesced definitions, interposition, and two-level namespace behavior. Do not assume a modern format is supported because older binaries load.
2. Correct `@rpath`, `@loader_path`, `@executable_path`, framework version links, nested bundles, shared-cache assumptions, and library search precedence. Capture the resolved image/hash for every dependency to catch accidental host or developer-stub substitution.
3. Verify initialization/destruction order, Objective-C registration timing, thread-local initialization, `dlopen`/`dlsym`/`dlclose`, error reporting, and concurrent loads. Preserve valid weak-link behavior; absent mandatory functionality must remain a visible blocker.
4. Commit fixes in the dyld fork, pin the parent gitlink, and rerun both synthetic image graphs and the full P007 workload closure captures.

**Verification and pass gate:**

- [ ] Required fixup/import fixtures resolve to the correct symbol addresses and produce correct computed outputs.
- [ ] Search-path, weak-import, reexport, initialization-order, and concurrent-load tests match reference behavior.
- [ ] Every observed target image resolves to an explicitly approved installed file/hash, with no unexplained missing mandatory import.
- [ ] Failed loads unwind state safely and provide useful errors; repeated load/unload tests leave no growing stale registry.

**Required evidence:** `docs/compat/logic-pro/evidence/P011/` paired dyld probe results, resolved-image manifest, application traces, and submodule revision diff.

**On failure/next action:** Reduce unresolved behavior to a fixture and repair the owner; start P012 only when binding semantics pass.

**README handover:** Record supported target formats, exact dyld pin, remaining closure edges, and P012 runtime work.

<a name="p012"></a>

### P012 — Verify Objective-C, blocks, ownership, and unwinding

**Status:** NOT STARTED.

**Depends on:** P011 (PASSED).

**Objective:** Make object dispatch and lifetime behavior reliable enough for Logic's Cocoa object graph and callbacks.

**Where:** **Existing:** `src/external/objc4/runtime/`, `src/external/libclosure/`, `src/external/libunwind/`, `src/external/libcxxabi/`, `src/external/foundation/`. **Proposed:** `tests/compat/logic-pro/objc_runtime/`, `docs/compat/logic-pro/evidence/P012/`.

**Implementation:**

1. Validate x86_64 calling conventions, structure/vector return variants, `objc_msgSend` families, superclass dispatch, class/category registration, forwarding, dynamic method resolution, associated objects, and selector identity against target-relevant fixtures.
2. Exercise ARC and non-ARC boundaries, retain/release, weak zeroing, autorelease pools, tagged-pointer behavior where used, and teardown on worker threads. A leak-free toy class does not cover object graphs that cross framework and callback boundaries.
3. Validate copied and escaping blocks, captured object ownership, nested blocks, cross-thread invocation, and callback cancellation. Test both block layout and semantic lifetime.
4. Verify Objective-C and C++ exceptions, cleanup handlers, mixed-language stack unwinding, and crash diagnostics. Repair only runtime defects demonstrated by probes, preserving upstream ABI compatibility through pinned submodule changes.

**Verification and pass gate:**

- [ ] Dispatch/forwarding fixtures return correct scalars, structures, objects, and vector-relevant values across supported call paths.
- [ ] Ownership and escaping-block fixtures produce expected deallocation/callback sequences, without use-after-free or growing retained-object counts.
- [ ] Mixed Objective-C/C++ exceptions unwind through framework boundaries and execute every required cleanup exactly once.
- [ ] Target-observed class registration and selector failures are resolved or explicitly reassigned to unimplemented framework behavior.

**Required evidence:** `docs/compat/logic-pro/evidence/P012/` paired contract outputs, allocation/lifetime traces, unwind logs, and exact runtime gitlinks.

**On failure/next action:** Fix the runtime contract before extending AppKit behavior. Advance to P013 only after all runtime assertions pass.

**README handover:** Record runtime fixes, ABI coverage, remaining framework-level defects, and the measured Swift requirement for P013.

<a name="p013"></a>

### P013 — Supply the Swift runtime and ABI actually required

**Status:** NOT STARTED.

**Depends on:** P012 (PASSED).

**Objective:** Support Swift dependencies reached by the selected target or its helpers, without guessing that the bundled Swift source is sufficiently current.

**Where:** **Existing:** `src/external/swift/`, `src/external/libdispatch/`, `src/external/objc4/`, `src/external/foundation/`, their integration in `src/CMakeLists.txt`. **Proposed:** `tests/compat/logic-pro/swift_runtime/`, `docs/compat/logic-pro/swift-requirements.json`, `docs/compat/logic-pro/evidence/P013/`.

**Implementation:**

1. Use P007 imports and runtime traces to enumerate Swift runtime versions, metadata formats, compatibility libraries, standard-library dependencies, Objective-C bridges, and concurrency symbols. Include dynamically loaded helpers and plug-ins in the declared target scope.
2. Where required, align the runtime/compiler-rt interfaces and implement metadata access, generic instantiation, protocol witness lookup, strings/collections, bridging, error propagation, and reference counting used by the target. Add async task/executor, cancellation, actor, and task-local behavior only where the dependency closure requires them, but fully test those paths.
3. Check calling conventions, stack unwinding, thread-local state, and interaction with dispatch and autorelease pools. Avoid replacing missing Swift entries with no-op functions that allow initialization to continue incorrectly.
4. A NOT-APPLICABLE conclusion is allowed only for the exact selected target/workload set after both binary inspection and dynamic coverage show no reachable Swift dependency. Preserve the report and reopen this phase when target or plug-ins change.

**Verification and pass gate:**

- [ ] Every required Swift dependency maps to a supported runtime artifact and measured semantic contract, or a complete evidence-based N/A report exists.
- [ ] Required metadata, bridging, ownership, and concurrency fixtures match reference results under repeat execution.
- [ ] No required unresolved Swift import, fabricated-success entry, or swallowed runtime trap remains.
- [ ] Application/helper traces cover all declared Swift-bearing paths, including teardown.

**Required evidence:** `docs/compat/logic-pro/evidence/P013/` dependency map, paired probes, runtime/toolchain versions, and any narrowly scoped N/A justification.

**On failure/next action:** Repair the pinned runtime or keep P013 blocked; a target upgrade invalidates unsupported N/A assumptions. Then begin P014.

**README handover:** Record actual Swift requirement, supported contracts or proven N/A, pins, and P014 IPC work.

<a name="p014"></a>

### P014 — Correct Mach IPC, ports, memory, and exception semantics

**Status:** NOT STARTED.

**Depends on:** P013 (PASSED).

**Objective:** Provide the process and IPC contracts that Cocoa services and later audio helpers rely on, including error and cleanup behavior.

**Where:** **Existing:** `src/external/darlingserver/`, `src/external/xnu/darling/src/libsystem_kernel/`, `src/duct/`, `src/startup/mldr/`, `tests/src/` Mach probes. **Proposed:** `tests/compat/logic-pro/mach/`, `docs/compat/logic-pro/evidence/P014/`.

**Implementation:**

1. Map P007-reached Mach calls to the server and client implementation. Test port allocation/deallocation, send/receive/send-once rights, name transfer, dead-name notifications, message sizes, descriptors, out-of-line memory, and timeout/interruption behavior.
2. Correct task/thread identity and lifetime, exception delivery, memory allocation/protection, shared mappings, and cleanup after helper crashes. Validate interactions between Linux signals, guest exceptions, and Mach bookkeeping.
3. Add multiprocess request/reply and failure fixtures that deliberately close peers, exhaust bounded resources, send invalid descriptors, and cancel waits. Compare exact results and ownership, not only successful round trips.
4. Keep protocol versioning and parent/submodule pin changes coordinated. Instrument outstanding ports and mappings to detect leaks that only become obvious during repeated project/plugin lifecycle operations.

**Verification and pass gate:**

- [ ] Port-right transfers and message fixtures match reference results, ownership, and callback/notification order.
- [ ] Timeout, invalid-message, peer-crash, and interrupted-wait behavior completes without deadlock or leaked rights.
- [ ] Shared-memory/protection probes observe correct contents and access faults across processes.
- [ ] A repeatable 10,000-operation IPC/lifecycle stress run has no unexplained growth in live rights or mappings after quiescence.

**Required evidence:** `docs/compat/logic-pro/evidence/P014/` paired Mach results, stress counters, failure traces, and server/client revision manifest.

**On failure/next action:** Fix the failing semantic contract and rerun its multiprocess reproducer; P015 remains blocked until IPC is reliable.

**README handover:** Record corrected Mach contracts, bounded resource results, exact server/kernel pins, and P015 scheduling primitives.

<a name="p015"></a>

### P015 — Establish correct threads, workqueues, clocks, and synchronization

**Status:** NOT STARTED.

**Depends on:** P014 (PASSED).

**Objective:** Provide reliable scheduling primitives and time conversion before higher layers attempt UI concurrency or real-time audio.

**Where:** **Existing:** `src/external/libpthread/`, `src/external/libdispatch/`, `src/external/libplatform/`, `src/external/darlingserver/`, `src/external/xnu/darling/src/libsystem_kernel/`, `src/startup/mldr/commpage.c`, `src/CoreAudio/CoreAudio/HostTime.mm`. **Proposed:** `tests/compat/logic-pro/concurrency/`, `tests/compat/logic-pro/clocks/`, `docs/compat/logic-pro/evidence/P015/`.

**Implementation:**

1. Verify thread creation, TLS destructors, joins, cancellation behavior, recursive/error-check mutexes, condition variables, semaphores, once initialization, and priority inheritance where the declared contract requires it. Test ownership and wakeup races, not just uncontended calls.
2. Implement target-required dispatch queues, workqueue servicing, barriers, groups, sources, timers, suspend/resume, and main-queue interaction. Detect synchronous-dispatch deadlocks and lost wakeups with deterministic stress seeds.
3. Establish a monotonic host-time basis with correct frequency, conversion, overflow handling, and suspend semantics. The audited zero-returning CoreAudio host-time path must become correct before any audio timing claim; compare it with Mach and dispatch clocks.
4. Define Linux priority/QoS mapping and report unsupported guarantees accurately. Measure scheduling latency under load without elevating every thread indiscriminately or promising hard real-time behavior from average measurements.

**Verification and pass gate:**

- [ ] Synchronization and dispatch ordering tests pass repeated seeded stress runs without lost work, deadlock, or lifetime errors.
- [ ] Host time is nonconstant and monotonic, conversions round-trip within declared resolution, and cross-clock drift stays within measured bounds.
- [ ] Timer cancellation and deadline tests match documented/reference behavior under idle and loaded conditions.
- [ ] Priority/QoS behavior and tail scheduling latency are recorded on the declared Linux baseline, with no false capability claim.

**Required evidence:** `docs/compat/logic-pro/evidence/P015/` seed logs, clock calibration, latency distributions, and thread/lifetime traces.

**On failure/next action:** Repair primitives before P016; average throughput cannot excuse lost callbacks or broken clocks.

**README handover:** Record clock source, scheduler limits, fixed races, and P016 service-lifecycle work.

<a name="p016"></a>

### P016 — Implement launchd, XPC, and helper-process lifecycle

**Status:** NOT STARTED.

**Depends on:** P015 (PASSED).

**Objective:** Make required services discoverable, launchable, connected, and recoverable with valid message semantics.

**Where:** **Existing:** `src/launchd/`, `src/external/libxpc/`, `src/external/darlingserver/`, `src/shellspawn/`, `src/frameworks/ServiceManagement/`. **Proposed:** `tests/compat/logic-pro/xpc/`, `docs/compat/logic-pro/services.json`, `docs/compat/logic-pro/evidence/P016/`.

**Implementation:**

1. Inventory bootstrap names, application XPC services, launch configurations, helper binaries, expected environment, and lifecycle ownership from P007. Separate essential local services from optional network integrations.
2. Implement actual registration/lookup, activation, endpoint transfer, message serialization, replies, connection invalidation, cancellation, and connection error delivery. Preserve type fidelity for arrays, dictionaries, shared memory, file descriptors, and Mach rights used by the target.
3. Match subprocess arguments, working directory, bundle identity, exit status, signal forwarding, and inherited handles. Support clean shutdown/restart and avoid leaked orphan processes after Logic closes or a helper crashes.
4. Verify trusted caller/identity behavior for reached service contracts. An arbitrary always-authorized response is not a substitute for correct identity handling; unavailable capabilities need explicit failure paths.

**Verification and pass gate:**

- [ ] Each mandatory service activates from a clean prefix and returns correct request/reply results.
- [ ] Peer crash, timeout, cancellation, malformed message, and reconnect tests produce expected errors and complete without hangs.
- [ ] Repeated application/helper startup and shutdown leaves no growing process, endpoint, descriptor, or port count.
- [ ] Identity-sensitive service probes reject mismatched callers according to the established contract.

**Required evidence:** `docs/compat/logic-pro/evidence/P016/` service manifest, paired XPC tests, lifecycle process trees, and resource counts.

**On failure/next action:** Fix the concrete activation or transport contract; do not add dummy services that simply acknowledge messages. Start P017 after lifecycle acceptance.

**README handover:** Record implemented service names, remaining optional exclusions, revisions, and P017 filesystem contracts.

<a name="p017"></a>

### P017 — Preserve filesystem semantics and project-package integrity

**Status:** NOT STARTED.

**Depends on:** P016 (PASSED).

**Objective:** Ensure Logic's projects, media, settings, and temporary data survive normal operations and interruption on the declared Linux filesystem.

**Where:** **Existing:** `src/vchroot/`, `src/external/libc/`, `src/external/copyfile/`, `src/external/removefile/`, `src/external/foundation/`, `src/quarantine/`, `src/ditto/`. **Proposed:** `tests/compat/logic-pro/filesystem/`, `docs/compat/logic-pro/filesystem-profile.json`, `docs/compat/logic-pro/evidence/P017/`.

**Implementation:**

1. Specify supported filesystems and the namespace mapping between guest and host paths. Verify case sensitivity, Unicode normalization, symlinks, permissions, extended attributes, resource forks where used, file IDs, file URLs, bookmarks/aliases, and package-directory traversal against required workflows.
2. Implement safe temporary-file creation, rename/replacement, atomic saves, directory synchronization, locking, and cross-volume copy behavior. Preserve user data when a save fails; success must mean the written package is readable and complete.
3. Test large/sparse media files, long paths, non-ASCII names, removable/missing volumes, full disks, permission denial, and simultaneous readers. Avoid global case-folding hacks that merge two distinct Linux files silently.
4. Add controlled interruption tests at save/replacement boundaries. Recovery must yield the previous valid project or the new valid project, plus explainable recovery data, rather than an apparently successful truncated package.

**Verification and pass gate:**

- [ ] Path, Unicode, metadata, and package probes produce the declared compatible semantics on every supported filesystem profile.
- [ ] Interrupted replacement and ENOSPC/permission failures preserve a valid recoverable original and report failure accurately.
- [ ] Large-file and cross-volume fixtures retain expected content hashes and references.
- [ ] Repeated package creation/copy/reopen produces no unexplained metadata or data loss.

**Required evidence:** `docs/compat/logic-pro/evidence/P017/` filesystem matrix, before/after manifests, fault-injection logs, and recovery outputs.

**On failure/next action:** Repair data integrity first and restrict unsupported filesystem profiles explicitly; P018 cannot waive corrupt saves.

**README handover:** Record supported storage profiles, integrity results, outstanding restrictions, and P018 legitimate application-flow work.

<a name="p018"></a>

### P018 — Implement legitimate security, keychain, and receipt flows

**Status:** NOT STARTED.

**Depends on:** P017 (PASSED).

**Objective:** Support the selected legitimately acquired application's required security and account-related behavior without fabricating authorization, ownership, or validation success.

**Where:** **Existing:** `src/external/security/`, `src/external/corecrypto/`, `src/external/commoncrypto/`, `src/frameworks/SecurityFoundation/`, `src/frameworks/StoreKit/src/SKReceiptRefreshRequest.m`, `src/frameworks/StoreKit/src/SKPaymentQueue.m`, `src/sandbox/`, `src/libsandbox/`. **Proposed:** `tests/compat/logic-pro/security/`, `docs/compat/logic-pro/authorized-flows.md`, `docs/compat/logic-pro/evidence/P018/`.

**Implementation:**

1. Trace actual startup, receipt, keychain, signing, entitlement, sandbox, and account requirements for each chosen distribution channel. Distinguish local API compatibility from remote services that require legitimate supported authentication.
2. Implement reached cryptographic, certificate, keychain, permission, and callback contracts with meaningful errors. Protect stored secrets with the selected host credential/storage design and test lock/unlock, persistence, denial, and process-identity checks.
3. Replace logging-only StoreKit forwarding with correct reachable behavior or an explicit unsupported outcome. Preserve receipt validation and legitimate ownership; do not patch Logic, forge receipts, bypass checks, or pretend an unfinished request completed successfully.
4. Exercise the traced authorized offline/online operations and failure paths through a minimal harness using real services and user-provided entitlements. Repeat the complete application flow at P027 once AppKit is ready. Keep receipts, credentials, and proprietary identifiers out of committed evidence. If a necessary service cannot be implemented legitimately, record the target as blocked.

**Verification and pass gate:**

- [ ] Required valid security operations succeed with verified results, while invalid signatures, denied access, and incorrect secrets fail correctly.
- [ ] Keychain persistence and isolation tests pass without exposing secrets in logs or files outside the declared protected store.
- [ ] A minimal harness for the selected owned Logic build's traced validation/account operations completes the real required flow; no fabricated-success shim is involved, and P027 retains full application verification.
- [ ] Missing network, canceled requests, and expired/invalid inputs deliver documented terminal callbacks or errors.

**Required evidence:** `docs/compat/logic-pro/evidence/P018/` sanitized contract results, authorized-flow matrix, storage design, and blocker report.

**On failure/next action:** Repair the contract or keep this gate BLOCKED; disabling authorization is not a workaround. Then begin P019.

**README handover:** Record supported distribution/ownership flows, remaining legitimate blockers, and P019 bundle discovery.

<a name="p019"></a>

### P019 — Resolve bundles, resources, Launch Services, and content types

**Status:** NOT STARTED.

**Depends on:** P018 (PASSED).

**Objective:** Let Logic locate its own resources and required components, open the correct documents, and dispatch supported URLs predictably.

**Where:** **Existing:** `src/frameworks/CoreServices/`, `src/frameworks/UniformTypeIdentifiers/`, `src/external/foundation/`, `src/external/corefoundation/`, `src/external/cocotron/AppKit/`. **Proposed:** `tests/compat/logic-pro/bundles/`, `tests/compat/logic-pro/launchservices/`, `docs/compat/logic-pro/evidence/P019/`.

**Implementation:**

1. Implement target-required bundle identity, version lookup, localized resources, nested framework resources, executable discovery, and resource search ordering. Record why a resource path was selected to expose incorrect fallback behavior.
2. Support reached Launch Services registration, application/document association, UTI declaration/conformance, file-type detection, URL dispatch, and open-document events. Keep host URL launching and guest application activation explicit and validated.
3. Handle case/Unicode paths, locale fallback, package projects, moved application bundles, missing resources, and resource-cache invalidation. Test registration refresh after updates without leaving stale executable paths.
4. Trace Logic's template, icon, localization, component, and settings lookup from clean and populated prefixes. Preserve actual bundles and metadata; copying arbitrary system libraries into paths to silence lookup errors does not establish their compatibility.

**Verification and pass gate:**

- [ ] Resource fixtures select the reference-equivalent file for locale, bundle, nested path, and fallback cases.
- [ ] Open-document and supported URL events reach the correct running application with intact arguments exactly once.
- [ ] UTI conformance and document associations behave correctly for declared Logic project/media fixtures.
- [ ] Moved/updated bundles refresh registration and missing resources produce useful failures rather than stale cache success.

**Required evidence:** `docs/compat/logic-pro/evidence/P019/` paired lookup results, registration database snapshots, event traces, and application resource manifest.

**On failure/next action:** Repair lookup or dispatch semantics before debugging missing UI assets in P020–P023. Begin P020 only after discovery is reliable.

**README handover:** Record resolved resource paths, association coverage, cache behavior, and the Foundation contracts required next.

<a name="p020"></a>

### P020 — Complete the Foundation and CoreFoundation contracts in use

**Status:** NOT STARTED.

**Depends on:** P019 (PASSED).

**Objective:** Provide dependable object, collection, serialization, notification, and run-loop behavior beneath Logic's UI and services.

**Where:** **Existing:** `src/external/foundation/`, `src/external/corefoundation/`, `src/external/icu/`, `src/external/libdispatch/`. **Proposed:** `tests/compat/logic-pro/foundation/`, `docs/compat/logic-pro/foundation-contracts.json`, `docs/compat/logic-pro/evidence/P020/`.

**Implementation:**

1. Rank missing and partial contracts from P007 and first-failure traces. Cover collection equality/hash/mutation, strings and encoding, data ownership, numbers/dates, property lists, keyed archiving, errors, URLs, preferences, notifications, and bundle-related objects actually used by the target.
2. Test toll-free bridging, object ownership, observer lifetime, KVC/KVO, autorelease behavior, and exceptions across framework boundaries. Implement real returned objects and state changes; a correctly typed placeholder can still violate its consumer's contract.
3. Correct run-loop modes, sources, timers, event delivery, thread affinity, and interaction with the main dispatch queue. Exercise nested modal loops and delayed callbacks, since initialization success alone does not reveal starvation.
4. Compare persisted preferences and archives across Mac/Linux round trips. Maintain versioned fixtures and handle unsupported secure-coding classes with explicit errors rather than silently discarding state.

**Verification and pass gate:**

- [ ] Every Foundation/CoreFoundation contract reached by this phase's declared startup/GUI baseline has a passing behavioral probe. Only contracts proven outside that frozen baseline may be assigned to a later feature owner; an unresolved baseline contract blocks P020.
- [ ] Collections, encoding, plist/archive, and bridging fixtures match expected values and lifetime behavior.
- [ ] Observer/run-loop fixtures deliver callbacks on the required thread and mode without duplicate delivery, starvation, or teardown crashes.
- [ ] Cross-platform preferences/archive fixtures preserve declared semantic fields and reject unsupported data clearly.

**Required evidence:** `docs/compat/logic-pro/evidence/P020/` contract matrix, paired outputs, persistence round-trip manifests, and allocation/observer traces.

**On failure/next action:** Reduce failures to framework probes and repair the pinned source; do not compensate with Logic-specific hardcoded values. Then begin P021.

**README handover:** Record completed contracts, remaining later-feature dependencies, submodule pins, and P021 startup objects.

<a name="p021"></a>

### P021 — Construct AppKit startup and nib object graphs correctly

**Status:** NOT STARTED.

**Depends on:** P020 (PASSED).

**Objective:** Instantiate the application's real Cocoa object graph, actions, delegates, and resources with reliable initialization order.

**Where:** **Existing:** `src/external/cocotron/AppKit/`, particularly `nib.subproj/NSNib.m` and `NSView.m`; `src/external/foundation/`. **Proposed:** `tests/compat/logic-pro/appkit/startup/`, `tests/compat/logic-pro/appkit/nibs/`, `docs/compat/logic-pro/evidence/P021/`.

**Implementation:**

1. Trace application startup through principal class creation, nib/storyboard or archive loading where used, delegate callbacks, window-controller initialization, and run-loop entry. Distinguish unimplemented methods from corrupt decoding and missing resources.
2. Implement reached coder formats, object substitution, class-version handling, outlets, target/action wiring, bindings, top-level object ownership, and `awakeFromNib` ordering. Validate cross-object references rather than merely accepting the archive.
3. Correct initialization/teardown lifetimes and repeated document/window construction. Missing classes/selectors must produce actionable diagnostics; do not create generic objects that allow decoding to “succeed” while discarding behavior.
4. Build minimal open fixture archives exercising the exact failing patterns. Use sanitized structural metadata for proprietary nibs and retain original application resources only in the authorized local test environment.

**Verification and pass gate:**

- [ ] Fixture object graphs match reference classes, connections, ownership, and initialization callback order.
- [ ] Every required startup archive in the selected Logic target decodes without unresolved mandatory class, outlet, or action.
- [ ] Opening and closing the same fixture window 100 times produces valid action delivery and no growing retained top-level object graph.
- [ ] A real user action on a decoded control reaches its intended target and changes asserted application state.

**Required evidence:** `docs/compat/logic-pro/evidence/P021/` object-graph reports, paired archive probes, callback traces, and Logic startup milestone log.

**On failure/next action:** Repair decoding or AppKit ownership before adding cosmetic work. Advance to P022 only after actual actions work.

**README handover:** Record archive formats/classes covered, corrected Cocotron pin, and P022 interaction failures.

<a name="p022"></a>

### P022 — Implement window, menu, focus, and input behavior

**Status:** NOT STARTED.

**Depends on:** P021 (PASSED).

**Objective:** Make the DAW controllable through mouse, keyboard, menus, dialogs, and application/window focus on the declared Linux display environment.

**Where:** **Existing:** `src/external/cocotron/AppKit/`, `src/external/cocotron/CoreGraphics/X11.backend/CGSWindowX11.m`, `src/pboard/`, `src/private-frameworks/SkyLight/`. **Proposed:** `tests/compat/logic-pro/appkit/events/`, `docs/compat/logic-pro/display-profile.json`, `docs/compat/logic-pro/evidence/P022/`.

**Implementation:**

1. Implement required window creation/destruction, ordering, modal/sheet ownership, activation, focus transfer, coordinate conversion, cursor state, drag tracking, and resize behavior. Declare X11/XWayland/native Wayland coverage according to actual implementation and test each supported configuration.
2. Correct responder-chain routing, key equivalents, modifier mapping, key repeat, keyboard layouts, text versus command events, mouse buttons, scroll deltas, and drag/drop. Preserve event timestamps and ordering instead of synthesizing arbitrary values.
3. Support menus, enabled/checked states, contextual menus, file dialogs, clipboard types, and document activation. A click on the wrong control must fail the UI test even if some action occurred.
4. Test multiwindow transitions, focus loss, modal cancellation, clipboard ownership loss, and closing while an event is queued. Connect failures to AppKit or backend ownership rather than patching recorded input coordinates.

**Verification and pass gate:**

- [ ] Keyboard/menu/mouse fixtures invoke the correct action exactly once and preserve intended focus/responder state.
- [ ] Modal dialogs and sheets block/restore the correct windows without deadlock or lost input.
- [ ] Clipboard and supported drag/drop fixtures retain exact payload and type metadata through round trips.
- [ ] Declared display configurations pass repeated activation, resize, close, and focus-loss scenarios.

**Required evidence:** `docs/compat/logic-pro/evidence/P022/` event traces, display manifest, deterministic interaction results, and annotated screen recordings.

**On failure/next action:** Fix event semantics or restrict unsupported display configurations explicitly; P023 requires reliable interaction.

**README handover:** Record supported display/input matrix, known backend limits, and P023 layout/text work.

<a name="p023"></a>

### P023 — Make layout, text, scaling, and accessibility usable

**Status:** NOT STARTED.

**Depends on:** P022 (PASSED).

**Objective:** Ensure controls remain correctly positioned, readable, editable, and discoverable across the supported window sizes, locales, and display scales.

**Where:** **Existing:** `src/external/cocotron/AppKit/`, especially `NSView.m`; `src/external/cocotron/CoreText/`, `src/libaccessibility/`. **Proposed:** `tests/compat/logic-pro/appkit/layout/`, `tests/compat/logic-pro/appkit/text/`, `tests/compat/logic-pro/accessibility/`, `docs/compat/logic-pro/evidence/P023/`.

**Implementation:**

1. Implement target-used constraints, autoresizing, intrinsic sizes, invalidation, layout passes, coordinate transforms, clipping, scrolling, and view hierarchy updates. Trace actual unimplemented paths in `NSView` and fix their semantics instead of forcing a single screenshot size.
2. Correct font selection/fallback, shaping, baseline metrics, text measurement, selection, editing, composition/IME behavior, Unicode cursor movement, and clipboard insertion. Use reference fixtures for ligatures, combining marks, right-to-left text where required, and non-ASCII project names.
3. Handle backing scale, logical/device coordinates, mixed-DPI moves where supported, and resize propagation. Check hit testing at each scale; sharp drawing with incorrect input coordinates still fails.
4. Expose reached accessibility roles, names, values, actions, focus, and hierarchy with the selected Linux bridge or documented test interface. Verify meaningful actions rather than claiming accessibility from exported symbols.

**Verification and pass gate:**

- [ ] Canonical layouts remain operable without clipped mandatory controls at the declared minimum/maximum sizes and scales.
- [ ] Text/editing fixtures preserve Unicode data, caret/selection semantics, and reference-compatible metrics within predeclared tolerances.
- [ ] Hit testing and focus remain correct after resize, scroll, and supported scale changes.
- [ ] Every required accessible control exposes valid state and performs its advertised action; an unresolved required accessibility defect keeps P023 BLOCKED.

**Required evidence:** `docs/compat/logic-pro/evidence/P023/` layout metrics, image comparisons, text outputs, accessibility tree/action traces, and display matrix.

**On failure/next action:** Correct layout/text contracts before P024 acceptance; do not hide broken controls with screenshot exclusions.

**README handover:** Record tested scales/locales, fixed view methods, accessibility coverage, and P024 drawing gaps.

<a name="p024"></a>

### P024 — Render CoreGraphics, CoreText, and ImageIO correctly

**Status:** NOT STARTED.

**Depends on:** P023 (PASSED).

**Objective:** Produce correct 2D drawing, text rasterization, and image decoding for the selected Logic interface and its required assets.

**Where:** **Existing:** `src/external/cocotron/CoreGraphics/`, `src/external/cocotron/CoreText/`, `src/frameworks/ImageIO/`, `src/frameworks/ColorSync/`, `src/frameworks/ApplicationServices/`. **Proposed:** `tests/compat/logic-pro/graphics2d/`, `tests/compat/logic-pro/imageio/`, `docs/compat/logic-pro/evidence/P024/`.

**Implementation:**

1. Implement required context creation, pixel formats, row strides, alpha premultiplication, transforms, clipping, paths, gradients, blend modes, masks, and state save/restore. Add readback checks so a drawing call that silently does nothing fails immediately.
2. Verify font loading, glyph mapping, advances, kerning/shaping, text matrices, and rasterization paths used by Logic. Distinguish acceptable font-renderer pixel variation from incorrect glyph selection or geometry.
3. Decode reached image formats and metadata with correct orientation, color conversion, alpha, and ownership. Handle malformed/truncated assets with explicit errors and bounded resource use.
4. Test offscreen and onscreen composition at supported scale factors, color profiles, and resize states. Predeclare exact comparisons for deterministic generated shapes and perceptual/geometry tolerances for renderer-dependent text.

**Verification and pass gate:**

- [ ] Deterministic shape/compositing fixtures match expected pixels or predeclared numeric tolerances, including nontrivial blend and clip cases.
- [ ] Text fixtures match glyph identity, layout, and metrics; documented rasterization variance stays within the reference envelope.
- [ ] Required image formats decode to correct dimensions, orientation, color, alpha, and content; invalid inputs fail safely.
- [ ] Logic's canonical static UI views render all mandatory assets without blank, stale, or incorrectly transformed regions.

**Required evidence:** `docs/compat/logic-pro/evidence/P024/` pixel/geometry reports, image hashes, paired screenshots, and decoder/error-path results.

**On failure/next action:** Fix the primitive that produces the incorrect readback; P025 must not conceal broken 2D rendering beneath a layer cache.

**README handover:** Record supported drawing/image contracts, tolerances, unresolved assets, and P025 composition work.

<a name="p025"></a>

### P025 — Implement Core Animation transactions and IOSurface sharing

**Status:** NOT STARTED.

**Depends on:** P024 (PASSED).

**Objective:** Make layer-backed UI updates, synchronization, and shared surfaces behave correctly across threads and processes.

**Where:** **Existing:** `src/external/cocotron/QuartzCore/CALayer.m`, `CATransaction.m`, `CAContext.m`; `src/frameworks/IOSurface/src/api.m`, `IOSurfaceObjC.m`; `src/private-frameworks/SkyLight/`. **Proposed:** `tests/compat/logic-pro/coreanimation/`, `tests/compat/logic-pro/iosurface/`, `docs/compat/logic-pro/evidence/P025/`.

**Implementation:**

1. Replace reached empty layer/transaction behavior with real invalidation, display/layout scheduling, model/presentation state, transaction nesting, commit/flush, completion callbacks, and lock/thread-affinity semantics. Audited empty `displayIfNeeded` and transaction methods are concrete investigation points, not working implementations.
2. Implement required hierarchy transforms, clipping, opacity, ordering, dirty-region propagation, resize, and animation timing. Ensure updates occur at actual presentation boundaries rather than marking content clean before it is visible.
3. Provide correct IOSurface allocation, stride/plane metadata, mapping, locks, lifetime, and cross-process transport. The audited null-returning XPC surface creation path needs an actual transferable resource where reached.
4. Integrate fences/synchronization with the chosen graphics backend and IPC. Exercise producer/consumer crashes, delayed consumers, resize while drawing, and rapid teardown to expose stale or prematurely freed surfaces.

**Verification and pass gate:**

- [ ] Layer updates and transaction completion callbacks reflect actual presented content and match reference ordering.
- [ ] Transform, clipping, opacity, and nested-layer fixtures render correct output across resize and animation.
- [ ] A cross-process surface producer/consumer round trip preserves pixel data and synchronization with no stale frame or lifetime fault.
- [ ] Repeated surface/layer creation and destruction reaches stable resource counts after quiescence.

**Required evidence:** `docs/compat/logic-pro/evidence/P025/` transaction traces, frame comparisons, IOSurface descriptors/readbacks, and resource-stress logs.

**On failure/next action:** Repair synchronization/lifetime first; P026 requires real surfaces and visible updates.

**README handover:** Record implemented transaction/surface contracts, changed Cocotron pin, and P026 reachable GPU requirements.

<a name="p026"></a>

### P026 — Support the graphics API path needed for baseline GUI operation

**Status:** NOT STARTED.

**Depends on:** P025 (PASSED).

**Objective:** Execute the actual OpenGL and/or Metal operations reached by baseline Logic GUI workloads on x86_64 Linux. This phase does not certify later GPU compute or ARM-only features.

**Where:** **Existing:** `src/frameworks/OpenGL/`, `src/external/metal/`, including `src/external/metal/src/Metal/MTLDevice.mm`, `src/external/metal/src/Metal/MTLCommandBuffer.mm`, `src/external/metal/src/Metal/MTLTextureDescriptor.mm`, and `src/external/metal/src/Metal/MTLLibrary.mm`; `src/frameworks/IOSurface/`, Cocotron composition backend. **Proposed:** `tests/compat/logic-pro/gpu_gui/`, `docs/compat/logic-pro/gpu-baseline.json`, `docs/compat/logic-pro/evidence/P026/`.

**Implementation:**

1. Trace API calls, shaders/libraries, texture formats, capabilities, synchronization, presentation, and readback for P006 baseline GUI views. Do not assume a Vulkan-backed Metal scaffold implements the required Metal feature set.
2. Choose and document the viable backend per reached path. Implement actual shader/pipeline creation, resource binding, buffer/texture operations, command submission, fences, errors, and presentation needed by that trace. Advertise only capabilities backed by execution tests.
3. Verify lifetime and shared-surface interoperation with P025. Handle device loss, unsupported formats, pipeline compilation failures, and queue shutdown explicitly. Software rendering may establish correctness if measured and clearly labeled; it cannot prove later real-time performance.
4. A graphics API proven unreachable in the full baseline corpus can be marked not required for this phase only. Preserve the trace evidence and assign later compute/feature requirements to their subsequent phases.

**Verification and pass gate:**

- [ ] Every graphics operation reached by baseline GUI workloads executes correctly with verified framebuffer or resource readback.
- [ ] Capability queries agree with tested support; unsupported paths fail meaningfully instead of returning inert objects.
- [ ] Baseline views redraw, resize, and present without blank/stale frames or synchronization faults on the declared GPU/driver matrix.
- [ ] Resource stress and negative cases pass; measured frame-time distributions and backend limitations are recorded.

**Required evidence:** `docs/compat/logic-pro/evidence/P026/` API traces, shader/resource fixtures, readback comparisons, GPU/driver manifests, and timing results.

**On failure/next action:** Implement the missing backend contract or keep GUI acceptance blocked; do not declare Metal complete. Then begin P027.

**README handover:** Record tested graphics subset, backend/hardware coverage, deferred compute requirements, and P027 first-launch blockers.

<a name="p027"></a>

### P027 — Reach a usable empty Logic project through the first-failure ladder

**Status:** NOT STARTED.

**Depends on:** P026 (PASSED).

**Objective:** Make the exact selected x86_64 Logic build initialize, complete legitimate startup, and present an interactive empty project on the declared x86_64 Linux runtime.

**Where:** **Existing:** All runtime/framework owners identified by P007–P026; no speculative bulk edits. **Proposed:** `tools/compat/logic-pro/launch_logic.py`, `tests/compat/logic-pro/workloads/empty-project.json`, `docs/compat/logic-pro/first-failure-ladder.json`, `docs/compat/logic-pro/evidence/P027/`.

**Implementation:**

1. Launch from a clean prefix using the locked bundle and runtime hashes. Capture milestones: process entry, dyld completion, runtime initialization, services ready, application object graph, startup dialogs, project chooser, and empty project ready.
2. At each stop, classify crash, hang, missing object, incorrect result, or visible UI defect. Reduce the first causative failure to a minimal differential probe, fix its actual framework/submodule owner, and add the regression before moving down the ladder.
3. Exercise startup with fresh preferences, existing preferences, required content unavailable, permitted offline operation, and canceled optional dialogs. Complete required account/receipt flows using P018 behavior.
4. If genuine audio/device/AU initialization is required before the window opens, follow the global dependency-repair rule: implement and test that minimal prerequisite within P027, link it for later comprehensive P029–P047 review, and leave those phases NOT STARTED. Never bypass the dependency to obtain a screenshot.
5. Verify the window's controls, menus, selection, scrolling, and closing against the reference workload. A static window, patched-out initialization, muted errors, or fake plug-in validation cannot count as a usable project.

**Verification and pass gate:**

- [ ] Ten clean-start runs reach the correct empty-project state without crash, hang, required stub hit, or unresolved mandatory initialization error.
- [ ] Declared empty-project interactions update real application state and remain responsive for a 30-minute UI session.
- [ ] Every resolved ladder failure has a minimal regression, owner, revision, and evidence link; no unexplained bypass remains.
- [ ] Application close terminates owned helpers cleanly and preserves expected preferences without resource accumulation.

**Required evidence:** `docs/compat/logic-pro/evidence/P027/` launch matrix, complete ladder, traces, regression links, and annotated interactive recording.

**On failure/next action:** Return to the owning earlier contract and revalidate affected gates. Begin P028 only after repeatable interactive startup.

**README handover:** Record the exact achieved launch milestone, residual non-GUI blockers, and P028 save/reopen acceptance. Explicitly state audio is not yet certified.

<a name="p028"></a>

### P028 — Accept baseline GUI workflows and the first save/reopen round trip

**Status:** NOT STARTED.

**Depends on:** P027 (PASSED).

**Objective:** Demonstrate that the usable project window supports meaningful editing and durable project state, while keeping all audio, MIDI, DSP, and performance claims pending their own later gates.

**Where:** **Existing:** AppKit/Foundation/CoreServices/filesystem owners established in earlier phases. **Proposed:** `tests/compat/logic-pro/workloads/gui-project.json`, `tools/compat/logic-pro/compare_project_state.py`, `docs/compat/logic-pro/evidence/P028/`.

**Implementation:**

1. Define a canonical no-audio-certification project with named tracks/regions where creation does not require an unimplemented audio contract, edited parameters, markers, window state, and supported metadata. If a declared GUI operation requires an audio prerequisite, implement the minimal real contract within this active phase under the global dependency-repair rule. A reference-created fixture may isolate and diagnose the UI contract, but cannot replace an unpassed mandatory create/edit operation or justify a reduced gate.
2. Exercise create/open, rename, select, arrange, copy/paste, undo/redo, inspectors, menus, dialogs, zoom/scroll, save/save-as, close, and reopen according to the target's actual supported paths. Compare semantic state, not volatile serialized bytes alone.
3. Reopen Linux-saved projects on the reference Mac and reference-saved projects on Linux. Verify missing-media/error dialogs preserve references and user choices; repeat non-ASCII and moved-directory cases from P017.
4. Collect UI latency, memory, descriptors, surfaces, and helper lifetime over repeated cycles. Keep measured acceptance thresholds from P006 and flag architecture-specific feature controls separately.

**Verification and pass gate:**

- [ ] All declared baseline GUI operations perform their intended state change and undo/redo restores the expected state.
- [ ] Twenty save/close/reopen cycles retain every declared semantic field without corruption, lost references, or unexplained growth.
- [ ] Cross-platform project reopen preserves the declared fixture state and reports unsupported dependencies honestly.
- [ ] Cancellation, missing media, permission denial, and failed save leave a recoverable project and usable UI.
- [ ] Evidence and README explicitly limit this milestone to GUI/project-state acceptance; no playback, recording, instrument, or real-time guarantee is inferred.

**Required evidence:** `docs/compat/logic-pro/evidence/P028/` state manifests, paired project-round-trip results, interaction recordings, latency/resource traces, and failure recovery logs.

**On failure/next action:** Reopen the owning GUI/storage gate and repair the reproducer. P029 may begin only after the full declared GUI acceptance scope passes.

**README handover:** Record achieved GUI workflows, exact project-fixture hashes, unsupported feature dependencies, and the first audio-runtime task in P029.

<a name="p029"></a>

### P029 — Correct audio format, frame, packet, and buffer contracts

**Status:** NOT STARTED.

**Depends on:** P028.

**Objective:** Establish correct byte and frame accounting before connecting any professional audio workload to a host device.

**Where:** Existing `src/CoreAudio/CoreAudio/AudioHardwareImpl.cpp`, `AudioHardwareStream.cpp`, `src/CoreAudio/CoreAudioComponent/AUHAL.cpp`, and their headers. Proposed `tests/compat/logic-pro/P029/` and `docs/compat/logic-pro/audio-format-contract.md`.

**Implementation:**

1. Replace the constructor and format-setter calculation that multiplies channels, **sample rate**, and sample width to obtain `mBytesPerFrame`. For packed interleaved stereo Float32 the value is 8 bytes, regardless of sample rate; for noninterleaved Float32 each channel buffer advances by 4 bytes per frame. Derive packet size separately and validate format flags, padding, and integer overflow.
2. Centralize format validation and frame/byte conversion. Validate every `AudioBufferList`, advertised channel count, data pointer, capacity, and returned length. Preserve the distinction between allocated capacity and valid data.
3. Correct `AUHAL::doPlayback` frame counting; dividing bytes per frame by the buffer's channel count currently double-counts frames for ordinary stereo interleaved audio. Correct the `GetProperty` writes to `&outData` instead of caller storage. Audit buffer ownership, including array allocation/deallocation pairs.

**Verification and pass gate:**

- [ ] Mono, stereo, and multichannel Float32 plus required integer PCM formats pass interleaved/noninterleaved golden cases at every reference sample rate.
- [ ] Zero frames, undersized buffers, malformed flags, excessive channel counts, and overflow attempts return documented errors without memory corruption.
- [ ] Guarded buffers and sanitizer runs show no out-of-bounds access, use-after-free, or mismatched allocation on the tested paths.
- [ ] The same fixture produces identical frame counts before and after format changes.

**Required evidence:** Table of ASBD inputs and expected sizes, macOS comparison outputs, sanitizer logs, and changed-symbol inventory.

**On failure/next action:** Remain in P029 and fix the smallest failing format case. Update this README with implementation, evidence, and exact remaining failure; P030 starts only after approval of every gate.

<a name="p030"></a>

### P030 — Implement one coherent host clock and audio sample timeline

**Status:** NOT STARTED.

**Depends on:** P029.

**Objective:** Give audio, MIDI, scheduling, and timestamp conversion a coherent monotonic time domain with explicit validity and discontinuity rules.

**Where:** Existing `src/CoreAudio/CoreAudio/HostTime.mm`, `AudioHardwareImpl.cpp`, and `pulse/AudioHardwareStreamPAInput.cpp` / `AudioHardwareStreamPAOutput.cpp`. Proposed `tests/compat/logic-pro/P030/` and a clock contract under `docs/compat/logic-pro/`.

**Implementation:**

1. Replace `AudioGetCurrentHostTime` returning zero with the same underlying host-time domain used by the implemented Darwin timing APIs. Implement frequency, conversion, and overflow behavior from the declared macOS contract; do not assume host ticks are nanoseconds without proving that choice consistently.
2. Replace zero-filled callback timestamps and the zero-success/copy-only implementations of current time, nearest start time, and time translation. Track stream sample positions, host-time anchors, rate changes, and restart generations.
3. Obtain timestamps from the host backend when available. Distinguish capture time, playback presentation time, and callback invocation time. Set only validity flags supported by actual information; do not fabricate precision.
4. Define restart, suspend/resume, wraparound, and discontinuity handling so downstream MIDI and compensation code can recognize a broken timeline.

**Verification and pass gate:**

- [ ] Host time is nonzero, monotonic within the documented domain, and conversion round trips stay within the predeclared rounding tolerance.
- [ ] A synthetic device advancing a known number of frames produces the exact expected sample-time progression and correct timestamp flags.
- [ ] Start/stop, rate changes, and simulated discontinuities cannot silently reuse obsolete clock mappings.
- [ ] A one-hour clock comparison on the reference device reports drift and stays within the frozen P006 tolerance.

**Required evidence:** Timestamp traces, conversion boundary tests, backend timestamp provenance, and reference-clock comparison.

**On failure/next action:** Keep P030 active until clock errors are explained and repaired. Record the failing conversion or stream transition in this README; then advance to P031.

<a name="p031"></a>

### P031 — Implement truthful audio hardware properties and notifications

**Status:** NOT STARTED.

**Depends on:** P030.

**Objective:** Let Logic discover, select, and monitor the real capabilities and state of audio devices through Core Audio properties.

**Where:** Existing `src/CoreAudio/CoreAudio/AudioHardware.cpp`, `AudioHardwareImpl.cpp`, `AudioHardwareImpl.h`, and the `pulse/AudioHardwareImplPA*` implementations. Proposed `tests/compat/logic-pro/P031/` and an audio property coverage matrix.

**Implementation:**

1. Replace hardcoded 44.1 kHz rates, always-alive/running responses, and success without state changes with backend-derived values or accurate unsupported-property errors. Enumerate selectors actually requested by Logic and the baseline AU host.
2. Implement property size, data, settable, scope, and element semantics consistently, including stream configuration, buffer-frame ranges, sample-rate ranges, device UIDs, default-device changes, latency, and safety offsets when supported.
3. Implement listener registration, removal, and notification. Specify callback lifetime, concurrency, duplicate registration behavior, and removal during callback dispatch. Deliver notifications after state becomes observable, without holding the audio render lock.
4. Correctly propagate device disappearance and permission failures. Persist stable identities without treating enumeration order as identity. Do not advertise unsupported multichannel or sample-rate combinations.

**Verification and pass gate:**

- [ ] The complete baseline property query/set sequence agrees with a native reference or a documented backend capability difference.
- [ ] Size-query and short-buffer tests return correct sizes/status and never overrun caller memory.
- [ ] Every tested state change emits the required notifications; removed listeners receive no later callback after their documented lifetime ends.
- [ ] Selecting devices and changing supported rates in Logic updates its audio preferences consistently with the host state.

**Required evidence:** Property matrix, notification traces, device identity records, and UI-to-backend state comparisons.

**On failure/next action:** Remain in P031; fix the first inconsistent property contract and document it here. P032 begins only with truthful enumeration and notification evidence.

<a name="p032"></a>

### P032 — Define and implement a production host audio backend lifecycle

**Status:** NOT STARTED.

**Depends on:** P031.

**Objective:** Make host audio start, stop, negotiation, and recovery deterministic, with an explicit backend contract suitable for the later low-latency qualification.

**Where:** Existing `src/CoreAudio/CoreAudio/AudioHardwareStream*`, `pulse/`, `src/CoreAudio/CoreAudioComponent/AUHAL.cpp`, and Core Audio CMake files. Proposed backend interface and selected backend directory within `src/CoreAudio/CoreAudio/`; proposed `tests/compat/logic-pro/P032/`.

**Implementation:**

1. Compare the existing PulseAudio path with a native PipeWire, JACK, or ALSA integration using the frozen hardware matrix. Select and document one primary production backend, its version range, timestamp facilities, latency reporting, and device ownership model. Keep alternatives explicitly unqualified until tested.
2. Introduce a backend abstraction for enumeration, negotiated formats, buffers, clocks, transport state, and errors. Keep Darwin-facing property behavior outside backend-specific code.
3. Implement a state machine for created, configured, running, stopping, stopped, disconnected, and failed states. Correct AUHAL startup error propagation and rollback; fix stale `m_running` and IOProc identifiers during stop/disposal.
4. Make partial initialization reversible. Tear down callbacks before freeing their user data; reconnect only through explicit state transitions. Avoid requiring administrator privileges merely to run ordinary playback.

**Verification and pass gate:**

- [ ] One hundred create/start/stop/dispose cycles complete without leaked streams, callbacks after destruction, or stale running state.
- [ ] Every injected backend startup failure reaches Logic as an actionable error and releases all partially acquired resources.
- [ ] Unsupported rate/buffer requests are rejected or negotiated with truthful readback.
- [ ] Backend disconnect/reconnect tests terminate or recover deterministically without a process hang.

**Required evidence:** Backend decision record, lifecycle diagram, resource counts, injected-failure traces, and selected version matrix.

**On failure/next action:** Fix lifecycle failures within P032. Update this README with the selected backend and unresolved transition; proceed to P033 only after every gate passes.

<a name="p033"></a>

### P033 — Complete full-duplex buffer transport and channel layout handling

**Status:** NOT STARTED.

**Depends on:** P032.

**Objective:** Transport simultaneous input and output correctly across supported layouts, without losing channel identity or confusing buffer size with frame count.

**Where:** Existing `src/CoreAudio/CoreAudioComponent/AUHAL.cpp` / `.h`, `src/CoreAudio/CoreAudio/AudioHardwareStream*`, and backend stream implementations. Proposed `tests/compat/logic-pro/P033/` and channel-map fixtures.

**Implementation:**

1. Replace the single-buffer, hardcoded stereo assumptions in the existing input/output callbacks with descriptions derived from the negotiated stream. Implement the AUHAL noninterleaved TODO paths and multiple-buffer ownership correctly.
2. Provide explicit interleave/deinterleave and supported sample-type conversion at a single audited boundary. Preallocate working storage for the maximum negotiated frame and channel counts; reject out-of-contract buffers instead of reallocating inside callbacks.
3. Separate capture and playback queues while maintaining the shared timeline from P030. Handle input-only, output-only, and simultaneous duplex configurations, including a temporarily missing input block.
4. Preserve silence flags, timestamps, per-buffer valid lengths, bus numbering, and channel labels. Treat backend buffer-quantum changes as reconfiguration events, not permission to overwrite old-sized buffers.

**Verification and pass gate:**

- [ ] Channel-coded impulses and distinct tones return on the correct channels for every qualified mono, stereo, and multichannel configuration.
- [ ] Interleaved-to-planar round trips preserve exact Float32 sample values when no numerical conversion is requested.
- [ ] Thirty-minute duplex runs at the required 44.1/48/96 kHz configurations produce no unexplained dropped, repeated, or reordered frames.
- [ ] Missing input and oversized callback injections produce bounded, documented behavior without a deadlock or memory violation.

**Required evidence:** Channel-map recordings, frame-sequence logs, configuration matrix, and buffer-boundary test outputs.

**On failure/next action:** Keep P033 open and isolate the failing layout or direction. Update the README handover with the reproduction; P034 requires all transport gates to pass.

<a name="p034"></a>

### P034 — Measure and correct latency, alignment, drift, and reconfiguration

**Status:** NOT STARTED.

**Depends on:** P033.

**Objective:** Make recorded material land at the correct project position and maintain synchronization across supported device and rate configurations.

**Where:** Existing Core Audio hardware/stream code, `AUHAL.cpp`, and the primary backend introduced in P032. Proposed `tests/compat/logic-pro/P034/` and latency-calibration records under `docs/compat/logic-pro/`.

**Implementation:**

1. Report hardware latency, backend buffering, safety offsets, and input/output presentation times using clearly defined units. Avoid double-counting a delay already represented in timestamps.
2. Build digital and physical loopback measurements using impulses and pseudorandom test sequences. Separate fixed latency, time-varying scheduling jitter, converter delay, and host/guest clock error.
3. Define duplex synchronization for shared-clock devices. For independent input/output clocks, either implement measured drift compensation and required resampling or expose an explicit unsupported configuration; the supported-device matrix cannot claim unimplemented aggregate behavior.
4. Handle rate, buffer size, and device changes by draining or resetting affected state, updating properties/listeners, and restoring a valid time mapping. Preserve project sample-rate semantics even when hardware runs at another rate.

**Verification and pass gate:**

- [ ] Reported and measured round-trip latency agree within the predeclared reference-device tolerance.
- [ ] A recorded loopback impulse lands within the frozen recording-alignment tolerance after applying the advertised compensation.
- [ ] A one-hour supported duplex run stays within the frozen drift bound; no discontinuity is hidden by relabeling timestamps.
- [ ] Reconfiguration tests produce no stale-format buffers or unreported timeline jumps, and recover to valid operation.

**Required evidence:** Raw loopback audio, impulse/correlation analysis, latency component table, and rate-change traces.

**On failure/next action:** Retain P034 until alignment and drift discrepancies are resolved. Record the exact device/rate combination in this README, then proceed to P035.

<a name="p035"></a>

### P035 — Remove unbounded work from the real-time audio path

**Status:** NOT STARTED.

**Depends on:** P034.

**Objective:** Ensure audio callback work has bounded cost and does not depend on a GUI thread, disk operation, or blocking synchronization.

**Where:** Existing `src/CoreAudio/CoreAudioComponent/AUHAL.cpp`, hardware/backend callback paths, and reachable audio dispatch code. Proposed `tests/compat/logic-pro/P035/`, callback instrumentation, and scheduler qualification records.

**Implementation:**

1. Replace AUHAL's condition-variable wait in `Render`, mutex-dependent recording handoff, and callback-time buffer growth with preallocated queues and a defined bounded underrun policy. Reclaim retired state outside the callback.
2. Trace the complete runtime-owned callback call graph. Remove allocation, synchronous logging, file access, GUI calls, unbounded retries, and other potentially blocking work; audit hidden allocations in helper libraries.
3. Map required thread priority and audio workgroup behavior onto Linux scheduling facilities supported by the deployment profile. Document permissions, fallback behavior, CPU affinity decisions, and priority-inversion protections without silently degrading a claimed configuration.
4. Instrument callback duration, deadline misses, queue occupancy, and backend xruns. At 48 kHz, 64/128/256 frames provide approximately 1.333/2.667/5.333 ms per buffer; these are processing intervals, not total round-trip latency.

**Verification and pass gate:**

- [ ] Instrumentation observes zero runtime-owned forbidden operations during steady-state callbacks in the baseline workload.
- [ ] Thirty-minute runs at each required buffer size show zero observed xruns and remain inside the frozen callback budget/headroom.
- [ ] Simulated starvation exits through the defined bounded policy instead of blocking indefinitely.
- [ ] Profiling instrumentation is shown not to hide or materially distort the measured behavior.

**Required evidence:** Callback call graph, allocator/lock traces, duration distribution including maximum, xrun counters, and scheduler configuration.

**On failure/next action:** Stay in P035, identify the blocking edge or budget overrun, and update this README. P036 requires measured callback safety.

<a name="p036"></a>

### P036 — Implement honest Audio Unit creation, lifetime, and validation

**Status:** NOT STARTED.

**Depends on:** P035.

**Objective:** Make baseline in-process Audio Unit discovery, creation, initialization, destruction, and validation report actual behavior.

**Where:** Existing `src/CoreAudio/AudioToolbox/AudioComponent.mm`, `AudioComponentManager.mm`, `AUComponent.cpp`, `ComponentDispatch.h`, and component registration code. Proposed `tests/compat/logic-pro/P036/` with deliberately valid and invalid test units.

**Implementation:**

1. Preserve the real component manager and dispatch mechanisms already present. Repair missing semantics around factory selection, descriptions, resource ownership, initialization order, and cleanup rather than replacing working code with stubs.
2. Implement `AudioComponentInstantiate`, whose current body never calls the completion handler. Specify handler ownership, execution context, error delivery, and exactly-once completion under supported creation options. Explicitly reject unsupported options; later AUv3 isolation remains a separate qualification phase.
3. Replace `AudioComponentValidate` unconditionally returning `Passed` with real validation and truthful statuses. Populate configuration metadata from actual capabilities instead of returning an empty dictionary as successful discovery.
4. Exercise failed factories, missing resources, repeated initialize/uninitialize, invalid instances, disposal during pending creation, and process shutdown. Ensure scanner failures are distinguishable from plugin incompatibility.

**Verification and pass gate:**

- [ ] Valid baseline units instantiate and render; invalid units fail validation with the expected reason instead of receiving a pass.
- [ ] Every accepted asynchronous request completes exactly once, with no leaked retained blocks or instances.
- [ ] One thousand lifecycle cycles show stable resource counts and no stale instance references.
- [ ] Logic's baseline component scan finishes and its result matches the independent test-host result for the fixture set.

**Required evidence:** Validation result matrix, completion traces, lifecycle resource counts, and Logic scan logs.

**On failure/next action:** Keep P036 open and record the exact component/option failure in this README. Advance to P037 only after truthful lifecycle and validation gates pass.

<a name="p037"></a>

### P037 — Complete Audio Unit parameters, state, and sample-offset automation

**Status:** NOT STARTED.

**Depends on:** P036.

**Objective:** Preserve a unit's musical state and apply parameter changes at their intended processing positions.

**Where:** Existing `src/CoreAudio/AudioToolbox/AUComponent.cpp`, component dispatch, and the Audio Unit support code selected by the current build. Proposed `tests/compat/logic-pro/P037/` and a parameter/state compatibility matrix.

**Implementation:**

1. Inventory the parameter, property, listener, preset, class-info, render-notification, reset, latency, and tail-time APIs used by baseline units. Implement exact types, scopes, elements, ownership, and error semantics; do not substitute one generic call signature.
2. Implement scheduled parameter events and ramps with correct sample offsets, order, and block-boundary behavior. Transfer control-thread updates through the bounded mechanism established in P035.
3. Serialize and restore state with round-trip coverage for presets, nondefault settings, opaque component data, and versioned property lists. Distinguish state restoration from rendering initialization.
4. Ensure parameter notifications and GUI bindings reflect changes without recursive notification storms or UI-thread access in callbacks. Preserve render flags and reset behavior across stop/start and offline rendering.

**Verification and pass gate:**

- [ ] A deterministic gain-ramp test produces the expected sample values and transition positions across several buffer sizes.
- [ ] Save/dispose/recreate/restore produces matching parameter values and baseline render output within the approved numerical tolerance.
- [ ] Invalid scope, element, type, and property-size cases match reference statuses without modifying unrelated state.
- [ ] Concurrent UI parameter movement and playback complete a thirty-minute run without races, deadlocks, or missed baseline automation events.

**Required evidence:** Parameter event traces, reference renders, serialized-state hashes, and concurrency diagnostics.

**On failure/next action:** Remain in P037 and record the failing state or event sequence in this README. P038 starts only after the baseline parameter/state contract is verified.

<a name="p038"></a>

### P038 — Deliver MIDI and note events to MusicDevice components

**Status:** NOT STARTED.

**Depends on:** P037.

**Objective:** Turn scheduled musical events into correctly timed instrument calls rather than returning an unimplemented error.

**Where:** Existing `src/CoreAudio/AudioToolbox/MusicDevice.cpp`, `ComponentDispatch.h`, `AUComponent.cpp`, and associated headers/support classes. Proposed `tests/compat/logic-pro/P038/` with a deterministic instrument fixture.

**Implementation:**

1. Replace the `unimpErr` bodies of `MusicDeviceMIDIEvent`, `MusicDeviceSysEx`, `MusicDeviceStartNote`, and `MusicDeviceStopNote` with correctly typed dispatch into the selected component interface. Preserve errors from the component.
2. Implement note-instance identifiers, instrument/group arguments, sample-offset handling, variable-size note parameters, and ownership of asynchronous payloads. Validate sizes before copying MIDI or SysEx data.
3. Preserve event order for equal timestamps, sustain, all-notes-off, pitch bend, program changes, and overlapping notes. Define behavior when an event arrives late or a transport discontinuity invalidates pending events.
4. Keep delivery bounded on the render path. Test component support detection explicitly; successful dispatch must not be reported for a selector the component does not implement.

**Verification and pass gate:**

- [ ] The fixture records the exact expected event order and sample offset for notes at the start, middle, and end of a render block.
- [ ] Start/stop-note identifiers and overlapping-note lifetimes agree with the native reference fixture.
- [ ] Long/fragmented SysEx and malformed payload tests produce correct bounded behavior without memory errors.
- [ ] Repeated stop, seek, and loop operations leave no hanging notes in the baseline instrument test.

**Required evidence:** Event logs, deterministic instrument output, reference status comparisons, and payload-boundary tests.

**On failure/next action:** Keep P038 active and identify the precise dispatch or scheduling failure in this README. Proceed to P039 after all event delivery gates pass.

<a name="p039"></a>

### P039 — Implement Audio Unit graph construction, routing, and mixing

**Status:** NOT STARTED.

**Depends on:** P038.

**Objective:** Support the Audio Unit graph operations required by the target and baseline component hosts, with correct bus topology and render order.

**Where:** Existing `src/CoreAudio/AudioToolbox/AUGraph.cpp`—currently only an include—plus `AUComponent.cpp` and component support code. Proposed graph implementation files and `tests/compat/logic-pro/P039/`.

**Implementation:**

1. Use the dependency/call inventory to define required graph functions and their ABI. Implement node creation/removal, connections, interaction queries, opening, initialization, start/stop, update, and disposal as a consistent graph state machine.
2. Validate bus formats and channel layouts before committing a topology change. Reject unsupported cycles and incompatible connections with accurate errors; do not silently drop an edge.
3. Determine render order and scratch storage outside real-time callbacks. Publish topology updates at a safe boundary without freeing nodes still used by a render operation.
4. Implement baseline mixing, fan-out, mute/bypass, silence propagation, and error propagation through the applicable component interfaces. Trace whether Logic itself uses AUGraph or another host path; this phase must not claim that AUGraph is its internal engine without evidence.

**Verification and pass gate:**

- [ ] Source → gain → mixer → output and multibus fixtures produce the expected channel-correct samples.
- [ ] Invalid graphs fail atomically, leaving the previous runnable graph intact.
- [ ] One hundred supported live topology changes complete without callback races, leaked nodes, or wrong render ordering.
- [ ] Required graph functions match the native reference's observable lifecycle and error behavior.

**Required evidence:** Graph fixtures, render comparisons, topology transition traces, and the actual Logic call-coverage record.

**On failure/next action:** Remain in P039 and document the failing graph transition here. P040 requires all required graph behavior and baseline fixtures to pass.

<a name="p040"></a>

### P040 — Replace CoreMIDI entry-point stubs with a real object model

**Status:** NOT STARTED.

**Depends on:** P039.

**Objective:** Provide functioning CoreMIDI clients, devices, entities, endpoints, ports, connections, and property access.

**Where:** Existing `src/frameworks/CoreMIDI/src/CoreMIDI.m`, `MIDIServices.m`, framework headers, and `CMakeLists.txt`. Proposed backend/object-model files in that framework and `tests/compat/logic-pro/P040/`.

**Implementation:**

1. Replace the generic `void *(void)` bodies in the audited CoreMIDI stub set with exact public ABI signatures and typed implementations. A symbol merely linking is not functional coverage; the audited file contains approximately 100 such stub definitions.
2. Implement object identifiers, stable unique IDs, property types, ownership, creation/disposal, and connection state. Replace placeholder property-key behavior where required by the reference API.
3. Introduce a Linux MIDI transport adapter selected through the same explicit backend decision discipline as audio. Support virtual sources/destinations and a loopback endpoint before depending on physical hardware.
4. Implement input callbacks, send/receive packet processing, client notifications, and teardown. Separate object bookkeeping from scheduling, which is qualified in P041. Inventory modern protocol/event-list APIs required by the exact Logic build; mark remaining required work explicitly rather than treating MIDI 1.0 alone as complete.

**Verification and pass gate:**

- [ ] A native CoreMIDI probe running through Darling creates, discovers, connects, uses, and disposes virtual endpoints successfully.
- [ ] Typed properties and object lifetime behavior match the reference fixture, including invalid IDs and removed objects.
- [ ] Virtual loopback preserves packet payloads and connection routing without cross-client leakage.
- [ ] Logic enumerates and selects the baseline virtual MIDI ports, and teardown leaves no stale selectable endpoint.

**Required evidence:** API inventory, endpoint/property snapshots, packet captures, and Logic enumeration results.

**On failure/next action:** Stay in P040 and record the failing object or ABI contract in this README. Advance to P041 only after all object-model gates pass.

<a name="p041"></a>

### P041 — Qualify MIDI scheduling, protocols, hotplug, and transport control

**Status:** NOT STARTED.

**Depends on:** P040.

**Objective:** Deliver MIDI at the correct musical time and recover predictably from endpoint or transport changes.

**Where:** Existing CoreMIDI framework and the implementation introduced in P040; shared clock code from P030. Proposed `tests/compat/logic-pro/P041/` and MIDI timing/transport fixtures.

**Implementation:**

1. Map `MIDITimeStamp` into the same host-time domain as audio. Implement future scheduling, immediate events, late-event policy, cancellation, and ordering across packets without using wall-clock time as a substitute.
2. Exercise the protocols actually required by the target: MIDI 1.0 messages and SysEx, plus MIDI 2.0/Universal MIDI Packet paths if present in the captured feature inventory. Do not claim an unsupported protocol through a successful no-op.
3. Implement endpoint arrival/removal, reconnection, unique-ID persistence, and notification ordering. Drain or invalidate pending events safely when devices disappear.
4. Test MIDI clock, start/continue/stop, timecode, control surfaces, and external synchronization according to the frozen baseline feature set. Keep internal virtual scheduling precision separate from physical USB/device jitter.

**Verification and pass gate:**

- [ ] Deterministic virtual scheduling delivers events at the expected sample positions and preserves equal-time order across buffer boundaries.
- [ ] Physical loopback latency and jitter meet the predeclared hardware-specific bounds, with complete distributions and maxima reported.
- [ ] Disconnect/reconnect during playback leaves no hanging notes, dangling callback, or unusable duplicate endpoint.
- [ ] Thirty-minute transport and dense-event tests show no lost, duplicated, or reordered messages beyond explicitly documented protocol semantics.

**Required evidence:** Timestamped packet traces, audio/MIDI alignment captures, hotplug logs, and protocol coverage results.

**On failure/next action:** Retain P041 and record the first lost or mistimed event sequence in this README. P042 requires the entire declared MIDI baseline to pass.

<a name="p042"></a>

### P042 — Establish a DSP ABI inventory and numerical reference harness

**Status:** NOT STARTED.

**Depends on:** P041.

**Objective:** Identify the numerical routines that must work and define how correctness will be measured before optimizing them.

**Where:** Existing `src/frameworks/Accelerate/vecLib/` and its `vDSP`, `BLAS`, `vMisc`, and `BNNS` subdirectories. Proposed `tests/compat/logic-pro/P042/`, a DSP symbol manifest, and a macOS reference-data generator.

**Implementation:**

1. Combine static imports, dynamic lookup tracing, helper-process coverage, and actual instrument/effect workflows into a required-symbol list. The audited `vDSP.c` has 454 active stub logging sites after comments are excluded; that count describes source incompleteness, not a compatibility percentage.
2. Recover exact function prototypes, integer widths, pointer ownership, setup-object lifetimes, vector/complex layouts, and calling conventions from appropriate headers and reference behavior. Remove generic signatures only with ABI-correct replacements.
3. Establish deterministic reference fixtures and tolerances per operation. Cover random seeds, extremes, NaN/Inf, denormals, rounding modes, aliasing, strides, zero-length input, and overflow/error behavior where defined.
4. Audit build wiring: `vDSP/CMakeLists.txt` currently compiles `vDSP.c` and `extrema.c`, so implementation in another file such as `basic.c` does not become active merely because it exists.

**Verification and pass gate:**

- [ ] Every required symbol has an exact signature, owner, implementation status, reference fixture, and acceptance tolerance.
- [ ] Fixtures fail against representative current stubs and catch deliberately corrupted arithmetic.
- [ ] Built/exported symbols map to intended implementations with no duplicate or accidentally unlinked replacements.
- [ ] All numerical tolerances are approved before production results are examined.

**Required evidence:** Reachability manifest, ABI checks, reference fixture hashes, negative-control results, and link-map audit.

**On failure/next action:** Stay in P042 until ambiguous signatures or tolerances are resolved. Update this README; P043 begins with a reproducible numerical oracle.

<a name="p043"></a>

### P043 — Implement required vDSP vector arithmetic and reductions

**Status:** NOT STARTED.

**Depends on:** P042.

**Objective:** Make the required vector operations produce correct numerical results across the layouts used by Logic and its components.

**Where:** Existing `src/frameworks/Accelerate/vecLib/vDSP/src/vDSP.c`, `basic.c`, `extrema.c`, and `CMakeLists.txt`. Proposed typed implementation units and `tests/compat/logic-pro/P043/`.

**Implementation:**

1. Implement the required arithmetic, multiply-add, clipping, scaling, conversion, windowing, reduction, ramp, interleave, and complex-vector families from the P042 manifest. Prioritize complete observable semantics over the number of exported names.
2. Establish a straightforward scalar reference implementation for each operation, then add host SIMD dispatch where justified. Ensure unsupported CPU instruction sets are never selected merely because the build machine supported them.
3. Respect strides, negative strides where specified, in-place operations, permitted aliasing, float/double variants, and defined empty-vector behavior. Do not globally enable floating-point transformations that violate the frozen numerical contract.
4. Wire the implementations into the actual shared library and eliminate only the corresponding stub definitions. Keep unimplemented symbols visible in the coverage ledger instead of returning plausible-looking zeroes.

**Verification and pass gate:**

- [ ] Every required vector/reduction fixture passes the native reference comparison and its edge-case suite.
- [ ] Scalar and enabled SIMD implementations agree within the predefined tolerance on all supported CPU profiles.
- [ ] Stride and aliasing tests pass with guarded memory; no unsupported instruction executes on the minimum CPU profile.
- [ ] A representative DSP chain consumes the functions through the exported Mach-O ABI and produces the expected non-silent output.

**Required evidence:** Per-symbol numerical report, CPU dispatch matrix, performance measurements, and exported-call integration results.

**On failure/next action:** Keep P043 active and name the exact operation/layout mismatch in this README. P044 requires all required vector operations to pass.

<a name="p044"></a>

### P044 — Implement FFT, convolution, correlation, and filter semantics

**Status:** NOT STARTED.

**Depends on:** P043.

**Objective:** Complete the required transform and stateful filtering primitives without normalization, layout, or history errors that corrupt musical output.

**Where:** Existing `src/frameworks/Accelerate/vecLib/vDSP/` and related Accelerate build definitions. Proposed transform/filter implementation files and `tests/compat/logic-pro/P044/`.

**Implementation:**

1. Implement required FFT/DFT setup creation, reuse, destruction, forward/inverse execution, and supported size handling. Preserve Apple's defined real/split-complex packing, DC/Nyquist representation, direction conventions, and scaling.
2. Select a maintained numerical backend or implement the kernels, but put compatibility adaptation at an explicit boundary. A backend function with a similar name is insufficient evidence of equivalent semantics.
3. Implement required convolution, correlation, FIR/IIR/biquad, decimation, and interpolation routines with exact coefficient order, state layout, stride, and history behavior.
4. Preallocate setups and working memory outside callbacks. Validate setup handles and supported dimensions; make reset and disposal safe across lifecycle transitions. Preserve deterministic state when rendering the same signal with different block partitions.

**Verification and pass gate:**

- [ ] Impulse, sinusoid, random, and extreme-value transform cases match reference packing and normalization at all required sizes.
- [ ] Forward/inverse round trips meet the approved error bound without an unexplained gain factor.
- [ ] Stateful filters and convolutions produce equivalent output across different block partitions and after defined resets.
- [ ] Repeated setup/use/dispose tests show no memory growth or callback-time setup allocation on qualified paths.

**Required evidence:** Frequency-domain comparisons, impulse responses, block-partition tests, allocation traces, and backend/version record.

**On failure/next action:** Remain in P044 and record the failing transform convention or filter state transition in this README. Proceed to P045 only after complete required-kernel verification.

<a name="p045"></a>

### P045 — Complete reachable BLAS, vector math, and BNNS numerical paths

**Status:** NOT STARTED.

**Depends on:** P044.

**Objective:** Close the remaining numerical API dependencies of the verified x86_64 target without pretending all Accelerate exports are implemented.

**Where:** Existing `src/frameworks/Accelerate/vecLib/BLAS/src/BLAS.c`, `vMisc/src/libvMisc.c`, `BNNS/src/BNNS.c`, and their build definitions. Proposed `tests/compat/logic-pro/P045/` and adapters for selected host numerical libraries.

**Implementation:**

1. Map each required symbol to its correct family and ABI. Audit BLAS integer widths, column/row conventions, transpose flags, complex representation, leading dimensions, and symbol naming before binding a host implementation.
2. Implement required vector transcendental functions with frozen special-value and numerical tolerances. Audit rounding and floating-point environment interactions rather than assuming the host math library is identical.
3. Implement BNNS descriptors, filter/object lifetimes, tensor layouts, supported operations, and execution behavior only as required by the target inventory; retain a clear unsupported ledger for the remainder. Apple-silicon-only modern model completion remains a later ARM milestone.
4. Control nested threading and allocation in numerical backends so they do not oversubscribe or block an audio render thread. Provide a deterministic bounded execution profile where the audio path requires one.

**Verification and pass gate:**

- [ ] Every required x86_64 symbol in these families passes its ABI and native numerical fixtures.
- [ ] Invalid descriptors/dimensions fail safely, and setup lifetimes pass repeated create/use/destroy tests.
- [ ] Backend thread and allocation behavior stays inside the declared real-time contract when called from audio workloads.
- [ ] No required workflow reaches a remaining no-op numerical stub.

**Required evidence:** Required-symbol closure report, tensor/matrix fixtures, backend threading configuration, and runtime stub-trap results.

**On failure/next action:** Keep P045 blocked on the named missing routine or numerical mismatch and update this README. P046 begins only after required numerical closure is verified.

<a name="p046"></a>

### P046 — Implement reliable AudioFile and ExtAudioFile storage semantics

**Status:** NOT STARTED.

**Depends on:** P045.

**Objective:** Read, write, seek, and describe the audio formats required for the baseline Logic project without corruption or metadata loss.

**Where:** Existing `src/CoreAudio/AudioToolbox/AudioFile.cpp`, `AudioFileComponent.cpp`, `AudioFileFormatManager.cpp`, `ExtendedAudioFile.cpp`, and associated headers. Proposed `tests/compat/logic-pro/P046/` and format/metadata fixtures.

**Implementation:**

1. Inventory actual project import, recording, and export calls. Implement the current `ExtendedAudioFile.cpp` open/read/write/seek/property routines that return `unimpErr`, reusing the existing audio file architecture where appropriate.
2. Separate storage format from client PCM format; preserve frame and packet distinctions for variable-packet compressed formats. Support required WAV, AIFF, CAF, and compressed formats from the frozen native-target feature list. An unavailable codec implementation is a blocker, not permission to omit a native-supported required format. Implement the minimal real converter primitives needed for these file contracts within P046 under the global prerequisite-repair rule; P047 still independently qualifies the complete converter/queue scope.
3. Implement large-file offsets, seeking, frame counts, channel layouts, metadata, packet tables, and asynchronous-write behavior where required. Use precise error reporting for truncated files, unsupported codecs, disk-full conditions, and invalid paths.
4. Ensure finalization flushes data and headers correctly. Preserve filesystem atomicity and recovery rules from P017; do not make a file appear successfully recorded before buffered failures are known.

**Verification and pass gate:**

- [ ] Required format round trips preserve expected samples and required metadata, with independently decoded verification.
- [ ] Random seek/read comparisons return the correct frames at the beginning, middle, end, and beyond the valid extent.
- [ ] Large-file and variable-packet fixtures retain correct lengths without truncation or integer overflow.
- [ ] Disk-full, interrupted-write, and damaged-file tests return truthful errors and leave documented recoverable results.

**Required evidence:** Format matrix, fixture hashes, independent decode reports, seek comparisons, and storage-failure traces.

**On failure/next action:** Remain in P046 and document the failing format or persistence condition in this README. P047 requires all baseline file contracts to pass.

<a name="p047"></a>

### P047 — Complete AudioConverter and AudioQueue streaming/offline behavior

**Status:** NOT STARTED.

**Depends on:** P046.

**Objective:** Support conversion, queued audio, and offline processing with correct timing, buffering, and end-of-stream semantics.

**Where:** Existing `src/CoreAudio/AudioToolbox/AudioConverter.cpp`, `AudioConverterImpl.*`, `AudioQueue.cpp`, `AudioQueueBase.*`, `AudioQueueOutput.*`, and the concrete converter implementations selected by CMake. Proposed `tests/compat/logic-pro/P047/`.

**Implementation:**

1. Preserve existing converter scaffolding and working codec integrations. Close required format/property/fill-callback behavior, sample-rate conversion, channel conversion, codec priming, trailing frames, reset, and drain semantics.
2. Implement the currently missing required AudioQueue input, start, prime, pause, stop, flush, reset, timeline, and offline-render operations. Use a documented state machine and explicit buffer ownership rather than issuing callbacks from arbitrary states.
3. Handle partial packets, short reads, zero-length buffers, cancellation, device errors, and end-of-stream without dropping final samples or looping indefinitely. Keep callback scheduling and disposal consistent with the API contract.
4. Separate offline throughput from real-time pacing. Offline conversion must run without a physical device and must not use fabricated audio timestamps to mask missing synchronization.

**Verification and pass gate:**

- [ ] Required conversions match reference sample counts, priming/trailing behavior, and approved numerical or codec tolerances.
- [ ] Queue lifecycle fixtures return each buffer exactly as specified, including pause/reset/dispose and injected failure cases.
- [ ] Real-time and offline paths produce equivalent deterministic baseline content after explicitly accounting for documented codec behavior.
- [ ] Long streams, short final packets, and repeated resets finish without leaked buffers, missing tails, or hangs.

**Required evidence:** Converter/queue coverage matrix, sample-count reports, lifecycle callback traces, and reference decoded output.

**On failure/next action:** Keep P047 active and record the exact conversion or queue transition failure in this README. P048 begins only after all baseline streaming/offline gates pass.

<a name="p048"></a>

### P048 — Demonstrate integrated Logic audio recording, playback, and bounce

**Status:** NOT STARTED.

**Depends on:** P047.

**Objective:** Prove the first meaningful end-to-end DAW milestone using the actual selected Logic build, while reserving comprehensive instruments, effects, plugins, and production qualification for later phases.

**Where:** Existing runtime layers completed through P047; fixes belong in the first incorrect layer identified by tracing. Proposed `tests/compat/logic-pro/P048/`, a baseline project, scripted/manual workflow instructions, and evidence manifests.

**Implementation:**

1. From a clean qualified prefix, launch the exact hashed x86_64 Logic build, select the reference interface, create a project, and import a known PCM fixture. Confirm meters, transport, channel routing, and audible/measured output.
2. Record a reference input through the qualified duplex path, stop, edit a simple region, save, close, and reopen. Verify timeline placement and that audio files persist with correct lengths and metadata.
3. Bounce the baseline project in real time and offline, independently decode both outputs, and compare them to the reference Mac with the predeclared numerical and alignment criteria.
4. Run stub traps, timing instrumentation, and resource observation throughout. A launch screenshot, moving meters, or a nonempty output file does not establish correct audio. Keep feature exclusions explicit without weakening later full-workflow gates.

**Verification and pass gate:**

- [ ] The complete create/import/play/record/save/reopen/bounce sequence succeeds on three clean runs.
- [ ] Captured and bounced audio meets the frozen sample-count, channel, alignment, clipping, and numerical criteria.
- [ ] A thirty-minute baseline session has zero observed xruns at the qualified buffer size and no required stub invocation.
- [ ] Saved projects reopen on the reference Mac and on the same qualified Linux build with matching baseline content.

**Required evidence:** Exact project/target hashes, raw recordings, reference/bounce comparisons, runtime logs, and a workflow recording.

**On failure/next action:** Remain in P048 and reopen any earlier failed dependency gate. Update this README with evidence and the exact remaining integration failure; P049 begins only after every baseline DAW criterion passes.

<a name="p049"></a>

### P049 — Qualify every bundled x86_64 instrument

**Status:** NOT STARTED.

**Depends on:** P048.

**Objective:** Run the instrument implementations shipped with the selected Logic build and establish musical correctness across the complete native x86_64 instrument inventory.

**Where:** Existing: `src/CoreAudio/AudioToolbox/MusicDevice.cpp`, `src/CoreAudio/AudioToolbox/AUComponent.cpp`, `src/frameworks/Accelerate/`, and the relevant runtime/submodule owners identified by traces. Proposed: `tests/compat/logic-pro/P049/`, `docs/compat/logic-pro/instrument-matrix.json`.

**Implementation:**

1. Enumerate installed stock instruments, versions, architectures, presets, required assets, outputs, MIDI behavior, and native platform restrictions. Distinguish an instrument's bundled executable from its supporting frameworks; compatibility work belongs in the latter unless a reproducible application defect exists.
2. Construct repeatable MIDI passages covering pitch range, velocity layers, sustain, release tails, pitch bend, program changes where supported, tempo changes, dense polyphony, and repeated transport starts. Fix seeds where the native instrument provides that facility.
3. Trace failing presets to exact missing APIs, ABI errors, DSP primitives, file operations, or state restoration failures. Add minimized reproductions before implementation changes; do not substitute a different synthesizer for the stock instrument.
4. Compare rendering, interactive performance, preset browsing, automation, and saved state with the same instrument and assets on the reference Mac. Use bounded statistical comparisons for intentionally randomized output, with the reason and metric recorded.

**Verification and pass gate:**

- [ ] Every instrument in the frozen x86_64 inventory has an executed case covering load, playback, editing, save, reopen, and bounce.
- [ ] Deterministic output meets the P042 numerical contract; randomized output satisfies predeclared musical and statistical checks.
- [ ] Dense MIDI and transport interruption produce no stuck voices, missing releases, invalid samples, or unexpected silence.
- [ ] Preset/state restoration survives a clean application restart without hidden dependency on a warm cache.

**Required evidence:** Inventory, preset/test identifiers, MIDI fixtures, audio comparisons, API traces, and reviewer-approved failures resolved.

**On failure/next action:** Block P050; repair the identified runtime dependency and rerun affected P036–P048 gates before requesting review.

<a name="p050"></a>

### P050 — Complete sampler streaming and sound-library access

**Status:** NOT STARTED.

**Depends on:** P049.

**Objective:** Make sample-based instruments reliable with cold caches, large libraries, relocated content, and sustained polyphony.

**Where:** Existing: `src/CoreAudio/AudioToolbox/AudioFile.cpp`, `src/CoreAudio/AudioToolbox/ExtendedAudioFile.cpp`, `src/CoreAudio/AudioToolbox/AudioConverter.cpp`, `src/vchroot/`, and traced filesystem/runtime owners. Proposed: `tests/compat/logic-pro/P050/`, `docs/compat/logic-pro/library-layout.md`.

**Implementation:**

1. Inventory the selected build's sampler instruments and required factory content separately from optional downloadable packs. Record file formats, paths, case and Unicode behavior, aliases, bookmarks, compression, memory mapping, and concurrent-read patterns observed on the reference Mac.
2. Build instrument fixtures for long release tails, velocity switching, round-robin selection, reverse playback, loop boundaries, tuning, multi-output routing, and simultaneous patches. Cover every supported sampler workflow in the native feature inventory.
3. Correct streaming and filesystem semantics where measurements show missed reads or incorrect mapping. Move allocation, decoding, prefetch, and page-fault preparation away from time-critical callbacks; expose underflow counters instead of hiding missing samples with silence.
4. Test valid library relocation, offline external storage, reconnect, permission failure, truncated content, and interrupted copying. Preserve useful missing-content messages and recovery behavior.

**Verification and pass gate:**

- [ ] All required factory sampler content loads and resolves paths after a cold application start and an authorized relocation.
- [ ] The frozen maximum-polyphony fixture completes with zero observed streaming underflows at the qualification buffer setting.
- [ ] Loop boundaries, release tails, pitch, velocity, and channel routing match the native reference within declared tolerances.
- [ ] Missing or corrupted files yield recoverable errors without project damage, hangs, or an incorrectly reported successful load.

**Required evidence:** Content manifests and hashes, cold/warm storage traces, underflow counters, memory traces, relocation cases, and audio comparisons.

**On failure/next action:** Keep P051 blocked; isolate file, converter, scheduler, or sampler dependency failures and repeat the relevant earlier gate.

<a name="p051"></a>

### P051 — Qualify stock effects, automation, and delay compensation

**Status:** NOT STARTED.

**Depends on:** P050.

**Objective:** Make every stock effect available on the x86_64 reference behave correctly in live playback, automation, and offline rendering.

**Where:** Existing: `src/CoreAudio/AudioToolbox/AUComponent.cpp`, `src/CoreAudio/AudioToolbox/AUGraph.cpp`, `src/frameworks/Accelerate/`, and GUI owners for plug-in views. Proposed: `tests/compat/logic-pro/P051/`, `docs/compat/logic-pro/effect-matrix.json`.

**Implementation:**

1. Enumerate effects by exact component identity and native architecture availability. Include instruments' embedded effects, MIDI effects, convolution assets, sidechains, channel configurations, bypass, presets, and reported latency/tail behavior.
2. Feed impulses, sweeps, multitone signals, silence, near-zero samples, and representative music through each effect. Separate expected nonlinear or randomized behavior from framework defects; define tolerances before evaluating Linux output.
3. Exercise sample-positioned automation, parameter ramps, tempo synchronization, preset changes, external sidechains, sends, buses, and low-latency monitoring. Correct property notifications and processing order through the runtime interfaces that carry these operations.
4. Measure plug-in delay compensation with parallel paths containing different lookahead and processing delays. Verify compensation after insert/remove, bypass, latency changes, track freeze, and real-time/offline mode changes.

**Verification and pass gate:**

- [ ] Every native-supported stock effect passes parameter editing, state restoration, processing, and applicable channel-layout cases.
- [ ] Impulse arrival and parallel-path alignment meet the P006/P042 predeclared sample-domain tolerance.
- [ ] Automation occurs at the required event positions without stepping, missed events, or buffer-boundary artifacts beyond native behavior.
- [ ] Real-time playback, freeze, and offline bounce preserve the intended processing and tails; intentional mode differences are documented against the native reference.
- [ ] Apple-silicon-only effects remain explicitly assigned to the ARM track, with no x86 implementation claim.

**Required evidence:** Effect matrix, latency reports, impulse captures, automation fixtures, null/error measurements, and native applicability evidence.

**On failure/next action:** Block P052 and repair the smallest failing DSP, parameter, routing, or state contract.

<a name="p052"></a>

### P052 — Complete MIDI composition, recording, and controller workflows

**Status:** NOT STARTED.

**Depends on:** P051.

**Objective:** Turn working MIDI transport into dependable end-user composition and performance workflows.

**Where:** Existing: `src/frameworks/CoreMIDI/`, `src/CoreAudio/AudioToolbox/MusicDevice.cpp`, the Cocotron AppKit implementation, and traced timing/runtime owners. Proposed: `tests/compat/logic-pro/P052/`, `docs/compat/logic-pro/midi-workflows.json`.

**Implementation:**

1. Build a native capability inventory for MIDI regions, piano-roll and event editing, score editing, step sequencing, transforms, articulation handling, controller assignments, and expressive MIDI features present in the chosen build. Confirm actual feature and device support before including a test variant.
2. Record a timestamped hardware/virtual MIDI fixture while audio runs. Compare captured event positions, ordering, quantization, cycle recording, punch recording, sustain state, and tempo-map transitions against the source events and reference project.
3. Exercise GUI editing through normal user actions: copy, split, merge, transpose, undo/redo, region aliases where supported, and project reopen. Validate resulting event data, rather than accepting screenshots as proof of MIDI correctness.
4. Test transport stop, loop wrap, device disconnect, bank/program changes where supported, and panic/reset behavior. Preserve legitimate controller configuration and reconnect associations across restarts.

**Verification and pass gate:**

- [ ] Every native-supported MIDI workflow category has a successful end-to-end case with inspected saved event data.
- [ ] Recording timing, ordering, and controller continuity meet the P041 timing contract under the qualified audio workload.
- [ ] Editing and undo/redo reproduce the expected notes, expressions, articulations, and durations after save/reopen.
- [ ] Stop, disconnect, and loop transitions leave no stuck notes or permanently latched controllers.
- [ ] Qualified physical controllers retain mappings and resume usable operation after reconnect.

**Required evidence:** Timestamped MIDI logs, edited project fixtures, event diffs, controller manifests, and interaction recordings.

**On failure/next action:** Keep P053 blocked; distinguish transport defects from AppKit editing defects and retest their owning gates.

<a name="p053"></a>

### P053 — Complete audio editing, Flex, and tempo analysis

**Status:** NOT STARTED.

**Depends on:** P052.

**Objective:** Support nondestructive audio editing and the selected x86_64 build's analysis and time/pitch workflows without damaged source media or timing drift.

**Where:** Existing: `src/CoreAudio/AudioToolbox/`, `src/frameworks/Accelerate/`, filesystem/runtime owners, and Cocotron drawing/event code. Proposed: `tests/compat/logic-pro/P053/`, `docs/compat/logic-pro/audio-editing-matrix.json`.

**Implementation:**

1. Cover region trims, fades, crossfades, comping, take folders, destructive operations explicitly requested by the test, sample-editor actions, reverse, normalization, and supported time/pitch modes. Hash original media before each nondestructive case.
2. Create native reference fixtures with known transients, tempo changes, pickups, silence, sustained tones, polyphonic material, unusual meter, and changing sample rates. Record analysis results, region anchors, markers, and rendered output.
3. Trace missing computation or private-framework behavior reached by Flex and Smart Tempo. Implement required semantics or compatible backend mappings while preserving the application's own analysis/state model; returning a fabricated analysis result is a failing outcome.
4. Stress background analysis while editing, recording, canceling work, saving, and closing a project. Verify task cancellation and object lifetime rather than serializing all analysis onto the audio thread.

**Verification and pass gate:**

- [ ] Every native-supported editing and analysis category completes and survives undo/redo plus save/reopen.
- [ ] Nondestructive operations leave source-media hashes unchanged and retain intended region references.
- [ ] Tempo, transient, and time/pitch results meet predeclared reference-based timing and audio-quality checks.
- [ ] Canceled or failed analysis leaves a recoverable project with no dangling tasks, partial metadata, or corrupted media.
- [ ] Concurrent analysis stays within the qualified real-time performance envelope.

**Required evidence:** Original/rendered media hashes, marker diffs, edit scripts, analysis traces, and interruption cases.

**On failure/next action:** Block P054; reduce the failing analysis or editing operation to a framework regression fixture.

<a name="p054"></a>

### P054 — Complete loops, arrangement, and native-supported session features

**Status:** NOT STARTED.

**Depends on:** P053.

**Objective:** Cover creative workflows that combine library discovery, analysis, instruments, arrangement state, and synchronized playback.

**Where:** Existing: traced framework/runtime owners under `src/frameworks/`, `src/private-frameworks/`, `src/CoreAudio/`, and `src/external/cocotron/`. Proposed: `tests/compat/logic-pro/P054/`, `docs/compat/logic-pro/session-feature-matrix.json`.

**Implementation:**

1. Inventory Apple Loops browsing/indexing, arrangement and global tracks, Live Loops, Drummer, Session Players, and other session features actually provided to the frozen native x86_64 target. Separate inaccessible ARM-only variants with evidence; never infer support from a menu label alone.
2. Test library search, tags, preview, drag/drop, tempo/key adaptation, arrangement changes, section duplication, and conversion between supported region or session representations. Verify actual rendered music and saved state.
3. For generative or adaptive parts, capture controls, seeds where exposed, model/content versions, arrangement context, and native output expectations. Define repeatability or statistical acceptance explicitly rather than demanding bit identity from nondeterministic generation.
4. Trace required analysis, database, model, and graphics dependencies. Implement only identified reachable contracts, then extend coverage to every native-supported feature row; the inventory cannot be reduced to make a failing build appear complete.

**Verification and pass gate:**

- [ ] All x86_64-native feature rows complete create/edit/play/save/reopen/bounce workflows.
- [ ] Loop preview and imported regions follow the correct tempo, key, synchronization, and asset reference behavior.
- [ ] Generative/adaptive output meets the frozen control-response and musical acceptance criteria.
- [ ] Offline or missing optional content produces actionable recovery without breaking unrelated workflows.
- [ ] Each ARM-only row points to a later ARM qualification obligation instead of receiving a Linux support checkmark.

**Required evidence:** Feature applicability table, content/model versions, arrangement fixtures, rendering comparisons, and dependency traces.

**On failure/next action:** Keep P055 blocked; identify whether the defect belongs to content indexing, analysis, DSP, transport, or UI state.

<a name="p055"></a>

### P055 — Verify project persistence, autosave, and recovery behavior

**Status:** NOT STARTED.

**Depends on:** P054.

**Objective:** Preserve users' complete projects through normal saves, concurrent background work, application failures, and recoverable storage errors.

**Where:** Existing: `src/vchroot/`, traced Darwin filesystem/syscall owners, Foundation submodule code, and LaunchServices-related framework code. Proposed: `tests/compat/logic-pro/P055/`, `docs/compat/logic-pro/project-integrity-contract.md`.

**Implementation:**

1. Define a semantic project comparison: tracks, regions, events, tempo maps, automation, plug-in state, routing, markers, assets, library references, and application metadata. Do not require package-byte identity when native Logic rewrites harmless timestamps or identifiers.
2. Exercise package and folder project forms supported by the target, Save As, copies with assets, templates, project alternatives/backups, autosave/recovery, and interchange with the same Logic build on the reference Mac.
3. Inject controlled failures at create/write/flush/rename boundaries, exhausted space, read-only destinations, revoked permissions, and process termination. Use disposable fixtures and explicit failure injection; never run destructive tests against a user's originals.
4. Correct atomic replacement, durability, extended attributes, file locking, alias/bookmark resolution, and notification behavior required by observed save/recovery flows. Ensure errors reach the application instead of silently acknowledging an incomplete save.

**Verification and pass gate:**

- [ ] All normal save variants reopen with semantically equivalent content on Linux and the reference Mac.
- [ ] Every injected failure preserves a previously valid project or a verified recoverable version with an accurate error indication.
- [ ] Referenced and copied assets remain locatable after moving the project to the qualification test location.
- [ ] Autosave/recovery retains the documented interval of edits and does not overwrite the last valid copy with incomplete state.
- [ ] Repeated save/reopen cycles show no accumulating state loss or unexplained media changes.

**Required evidence:** Project manifests, semantic diffs, crash points, storage traces, and recovery transcripts.

**On failure/next action:** Block P056 and treat silent corruption as a release-stopping defect; reopen the owning filesystem/runtime gate.

<a name="p056"></a>

### P056 — Finish the complete GUI workflow and rendering matrix

**Status:** NOT STARTED.

**Depends on:** P055.

**Objective:** Establish that every qualified Logic workflow remains usable across supported display configurations and concurrent audio activity.

**Where:** Existing: `src/external/cocotron/` AppKit/QuartzCore/CoreGraphics implementations, `src/frameworks/IOSurface/`, `src/frameworks/OpenGL/`, and the Metal submodule where reached. Proposed: `tests/compat/logic-pro/P056/`, `docs/compat/logic-pro/display-matrix.json`.

**Implementation:**

1. Inventory all primary editors, mixer variants, plug-in windows, browsers, preferences, modal sheets, file dialogs, context menus, tooltips, help flows, and accessibility interactions used by the complete feature matrix.
2. Test normal and high-DPI scaling, fractional host scaling where supported, multiple monitors, window moves, resize, minimize/restore, focus changes, keyboard layouts, input methods, drag/drop, clipboard, and display reconnection.
3. Instrument frame scheduling, redraw invalidation, layer contents, resource lifetime, and GPU/CPU usage. Fix missing Core Animation transactions, rendering synchronization, or event delivery at their ownership boundary; screenshots alone cannot prove event behavior.
4. Repeat representative heavy UI operations during playback, recording, analysis, and plug-in loading. Record missed input, stale meters, corrupt surfaces, stalled menus, and deadline misses separately.

**Verification and pass gate:**

- [ ] Every matrix workflow is operable through normal input without hidden command-line workarounds.
- [ ] Text, controls, waveforms, automation, meters, and plug-in views render correctly against approved native references.
- [ ] Focus, keyboard shortcuts, drag/drop, clipboard, and accessibility checks pass across declared display profiles.
- [ ] Repeated window/monitor lifecycle operations show no stale surfaces, crashes, or unbounded resource growth.
- [ ] GUI stress meets the interaction-response contract while audio remains within its deadline contract.

**Required evidence:** Display/driver manifest, interaction recordings, image diffs with reviewed tolerances, frame traces, and audio counters.

**On failure/next action:** Block P057; repair the specific rendering/event contract and rerun affected P021–P028 gates.

<a name="p057"></a>

### P057 — Qualify third-party AUv2 plug-ins and their user interfaces

**Status:** NOT STARTED.

**Depends on:** P056.

**Objective:** Establish a named, reproducible AUv2 compatibility set while keeping unsupported plug-ins visibly separate from verified support.

**Where:** Existing: `src/CoreAudio/AudioToolbox/AudioComponentManager.mm`, `AudioComponent.mm`, and `AUComponent.cpp` in that directory; `src/frameworks/CoreAudioKit/`; loader, Security, and Cocotron owners reached by plug-ins. Proposed: `tests/compat/logic-pro/P057/`, `docs/compat/logic-pro/plugin-matrix.json`.

**Implementation:**

1. Select legitimate plug-in fixtures spanning instruments, effects, MIDI processors, custom Cocoa views, generic views, multiple outputs, sidechains, presets, and documented authorization mechanisms. Record exact versions, architectures, vendors, and native validation results.
2. Exercise discovery, installation paths, rescan, failed validation, enable/disable, duplicate versions, and cache invalidation. Preserve genuine errors; an unconditional validation pass must never qualify a plug-in.
3. Test instance isolation, multiple projects, automation, presets, state save/restore, transport, latency, tails, offline rendering, and GUI lifetime. Use purpose-built diagnostic plug-ins to distinguish host ABI defects from vendor bugs.
4. Support normal authorization and network/helper behavior where required. Document unavailable vendor services as blockers for that plug-in, without fabricating credentials, entitlements, receipts, or success responses.

**Verification and pass gate:**

- [ ] Every named qualification plug-in passes genuine validation and its complete workflow case on Linux and the native reference.
- [ ] Deliberately invalid fixtures fail cleanly without becoming enabled or damaging the plug-in cache.
- [ ] State, latency, automation, rendering, and UI behavior meet the shared contracts across repeated instance creation/destruction.
- [ ] Compatibility claims identify exact tested versions; they do not imply every existing third-party plug-in works.
- [ ] Missing dependencies and authorization failures remain diagnosable and recoverable.

**Required evidence:** Plug-in matrix, native/Linux validation logs, instance stress logs, state hashes, and audio comparisons.

**On failure/next action:** Block P058; resolve host defects or explicitly fail the declared qualification row before review.

<a name="p058"></a>

### P058 — Implement AUv3 extension discovery, hosting, and isolation

**Status:** NOT STARTED.

**Depends on:** P057.

**Objective:** Support the selected x86_64 target's AUv3 workflows through real extension registration and lifecycle semantics.

**Where:** Existing: `src/CoreAudio/AudioToolbox/AudioComponent.mm`, `src/CoreAudio/AudioToolbox/AUComponent.cpp`, `src/frameworks/CoreAudioKit/`, `src/launchd/`, and traced XPC/LaunchServices/framework owners. Proposed: `tests/compat/logic-pro/P058/`, new extension-host implementation files under the owning subsystem after the P007 mapping is updated.

**Implementation:**

1. Use [Apple's AU workflow documentation](https://support.apple.com/en-by/guide/logicpro/lgcp22a0dab0/12.3/mac/15.6) and native traces to distinguish application-contained AUv3 extensions from AUv2 component bundles. Inventory registration metadata, helper executables, entitlements, service lookup, and asynchronous completion paths.
2. Implement the reachable extension-management and Audio Unit hosting contracts, including invalidation, cancellation, asynchronous instantiation, remote views, shared buffers, parameter communication, and state restoration. Do not replace asynchronous behavior with a permanent blocking wait.
3. Validate architecture selection and helpers independently from the main application. A compatible main binary does not establish that its extension or service can execute.
4. Test crash, timeout, malformed response, extension update/removal, and stale registration. Preserve the isolation behavior observed in the exact native target; do not promise a newer architecture's containment features without implementation evidence.

**Verification and pass gate:**

- [ ] Every declared AUv3 fixture is discovered, genuinely validated, instantiated, rendered, edited, saved, and restored.
- [ ] Every asynchronous request reaches exactly one valid completion or documented cancellation/error path.
- [ ] Helper and view lifecycles terminate without leaked processes, Mach rights, shared memory, or deadlocked callers.
- [ ] Failure/restart cases preserve the native target's documented recovery and project-integrity behavior.
- [ ] Audio communication and view activity remain inside qualified timing/resource limits.

**Required evidence:** Extension manifests, process/XPC traces, completion counts, shared-memory ownership checks, and fault-injection results.

**On failure/next action:** Keep P059 blocked; repair extension infrastructure rather than labeling AUv3 an optional omission.

<a name="p059"></a>

### P059 — Qualify ARA and advanced plug-in integrations

**Status:** NOT STARTED.

**Depends on:** P058.

**Objective:** Cover advanced integrations supported by the exact native x86_64 target, including ARA when present in that target's qualified plug-in ecosystem.

**Where:** Existing: `src/CoreAudio/AudioToolbox/`, filesystem and XPC/runtime owners, and the GUI implementations reached by the chosen integration. Proposed: `tests/compat/logic-pro/P059/`, `docs/compat/logic-pro/advanced-plugin-contracts.md`.

**Implementation:**

1. Freeze a target-specific applicability matrix from vendor documentation and native execution. [Apple documents ARA 2 sharing of region/audio information and analysis](https://support.apple.com/en-ae/guide/logicpro/lgcp58ce340b/10.7/mac/11.0); this is a distinct contract beyond ordinary buffer processing.
2. For each supported integration, enumerate host callbacks, object lifetimes, region-to-file mappings, analysis access, background tasks, state serialization, and timing relationships. Use a diagnostic integration fixture where licensing and SDK availability permit.
3. Exercise insertion in valid positions, initial information transfer, region moves/copies, edits, undo/redo, project copy, reopen, and supported rendering/freeze behavior. Respect native documented limitations instead of inventing broader guarantees.
4. Trace threading, memory ownership, ABI, and file-access failures to the compatibility layer. Ensure sharing project structure does not leave borrowed pointers alive after the host removes a region or closes the document.

**Verification and pass gate:**

- [ ] Every integration supported by the frozen native qualification set passes its full lifecycle and editing cases.
- [ ] Region and analysis data remain consistent after move/copy/edit/undo and project save/reopen.
- [ ] Background analysis and document teardown cause no stale-object access, deadlocks, or project corruption.
- [ ] Native limitations and architecture requirements are documented with evidence; untested host behavior is not marked passed.
- [ ] Advanced integrations preserve the established audio and project-integrity contracts.

**Required evidence:** Applicability decisions, vendor/reference versions, callback traces, semantic project comparisons, and teardown tests.

**On failure/next action:** Block P060; reduce the failing callback or lifecycle sequence to a host regression case.

<a name="p060"></a>

### P060 — Complete video scoring and frame-accurate synchronization

**Status:** NOT STARTED.

**Depends on:** P059.

**Objective:** Support the target's movie and scoring workflows with correct decode, transport, timecode, and audio/video alignment.

**Where:** Existing: framework targets listed in `src/frameworks/CMakeLists.txt`, especially AVFoundation, CoreMedia, CoreVideo, VideoToolbox, and reachable rendering/audio code. Proposed: `tests/compat/logic-pro/P060/`, `docs/compat/logic-pro/video-format-matrix.json`.

**Implementation:**

1. Inventory the exact target's supported import/export containers, codecs, frame rates, timecode modes, movie offsets, audio extraction, and scoring operations. Implement a legitimate decode/encode path for every required native-supported format; a missing viable backend is BLOCKED, not permission to omit that format from the matrix.
2. Implement required framework contracts around demuxing, decode, pixel buffers, color metadata, presentation timestamps, cancellation, and seek. A video backend must preserve API semantics rather than merely display the first frame.
3. Construct synthetic movies containing numbered frames, flash markers, and aligned audio impulses. Test fractional frame rates, long durations, tempo changes, locate, scrub, loop, pause/resume, and seeks near file boundaries.
4. Exercise movie windows on qualified displays while recording or playing demanding audio. Separate decoder failures, frame-presentation latency, clock drift, and audio callback misses in diagnostics.

**Verification and pass gate:**

- [ ] Every native-supported format in the declared qualification matrix completes import, seek, playback, and applicable export cases.
- [ ] Frame selection and timecode calculations match the native reference at all test markers, including fractional-rate cases.
- [ ] Measured audio/video offset and long-run drift remain within the frozen scoring tolerance.
- [ ] Missing codecs and malformed files produce accurate recoverable errors without damaging the project.
- [ ] Video playback and window interaction preserve the real-time audio contract on the qualification hardware.

**Required evidence:** Generated marker-media specifications, decoder/backend versions, timestamp traces, captured synchronization measurements, and output metadata.

**On failure/next action:** Block P061; fix the failing media, timing, or rendering contract and rerun affected clock tests.

<a name="p061"></a>

### P061 — Complete multichannel, surround, and spatial production

**Status:** NOT STARTED.

**Depends on:** P060.

**Objective:** Qualify all surround and spatial workflows exposed by the selected native x86_64 build, with explicit treatment of hardware-dependent features.

**Where:** Existing: `src/CoreAudio/`, `src/frameworks/AVFAudio/`, Accelerate and traced audio-rendering/private-framework owners. Proposed: `tests/compat/logic-pro/P061/`, `docs/compat/logic-pro/spatial-matrix.json`.

**Implementation:**

1. Inventory native channel layouts, ordering, surround buses, panners, object/bed routing, monitoring renderers, binaural modes, export formats, and device-specific functions. A feature's need for particular hardware remains a qualification dependency, not evidence that Linux implements it.
2. Test isolated channel impulses and object-position trajectories through import, mixing, sends, plug-ins, monitoring, and bounce. Verify channel labels, interleaving, gain, automation, and layout changes independently.
3. Where the target supports Dolby Atmos export, preserve audio and object metadata together; [Apple's documentation explains the ADM BWF structure](https://support.apple.com/en-euro/guide/logicpro/lgcp449359b0/12.3/mac/15.6). Validate generated files with an independent parser/player permitted for the format and compare the native output.
4. Cover physical multichannel interfaces, headphone monitoring, render changes, and save/reopen. Record any native requirement for personalized profiles, head-tracking devices, or platform-specific renderers and assign unresolved implementation to a blocking feature row.

**Verification and pass gate:**

- [ ] Every native-supported layout routes channel-identity fixtures correctly with no reordering, truncation, or stereo fallback.
- [ ] Spatial/object automation and supported monitoring modes match reference behavior and timing tolerances.
- [ ] Exported media and metadata validate and reopen or play correctly in the qualified independent consumer.
- [ ] All claimed hardware-dependent functions have actual device evidence; missing equipment produces BLOCKED status.
- [ ] Qualified channel counts and processing loads satisfy audio deadlines and persistence requirements.

**Required evidence:** Channel maps, object trajectories, device manifests, export validation reports, and reference renders.

**On failure/next action:** Block P062; resolve routing, renderer, metadata, or device support without narrowing the stated full-feature goal.

<a name="p062"></a>

### P062 — Complete content installation, updates, and legitimate services

**Status:** NOT STARTED.

**Depends on:** P061.

**Objective:** Make the application's legitimate acquisition-dependent workflows usable and recoverable with the required accounts, entitlements, and service access.

**Where:** Existing: `src/frameworks/StoreKit/`, traced Security/Foundation/networking implementations, `src/launchd/`, and filesystem owners. Proposed: `tests/compat/logic-pro/P062/`, `docs/compat/logic-pro/service-dependency-matrix.json`.

**Implementation:**

1. Inventory sound-library download/install/relocation, update checks, account/receipt verification, optional online features, help links, and service-dependent content in the exact target. Record which operations occur in Logic, a helper, or an external distribution application.
2. Reproduce legitimate flows using authorized software and accounts. Implement observed networking, TLS/trust, keychain, receipt-reading, service discovery, progress, cancellation, and helper contracts; never fake an entitlement or mark a rejected transaction successful.
3. Test paused/interrupted downloads, partial extraction, insufficient space, permission errors, clock skew, unavailable services, expired sessions, and content-version mismatches. Make retries idempotent and preserve previously working content.
4. Freeze executable and content manifests for a qualification run. An update must create a new candidate and rerun affected gates instead of silently changing the software under a passing result.

**Verification and pass gate:**

- [ ] Required content and service workflows complete through legitimate authorization and produce verified installed assets.
- [ ] All interruption cases recover without corrupting existing content or falsely reporting completion.
- [ ] Offline behavior matches the native target's documented behavior for previously authorized, installed functionality.
- [ ] Credentials and account secrets are excluded from logs, artifacts, fixtures, and source control.
- [ ] Any unavailable essential service remains an explicit release blocker with a reproducible error and owner.

**Required evidence:** Redacted transaction/service traces, asset hashes, install manifests, recovery cases, and target-update records.

**On failure/next action:** Block P063; repair the observed compatibility failure or leave the gate blocked if an external prerequisite cannot be satisfied.

<a name="p063"></a>

### P063 — Qualify physical audio/MIDI interfaces and device recovery

**Status:** NOT STARTED.

**Depends on:** P062.

**Objective:** Prove reliable operation on named real hardware rather than inferring interface support from virtual-device tests.

**Where:** Existing: `src/CoreAudio/CoreAudio/`, `src/CoreAudio/CoreAudioComponent/AUHAL.cpp`, `src/frameworks/CoreMIDI/`, and the host backend established in P032. Proposed: `tests/compat/logic-pro/P063/`, `docs/compat/logic-pro/hardware-matrix.json`.

**Implementation:**

1. Freeze devices spanning the declared deployment needs: onboard output, class-compliant USB interfaces, qualified multichannel interfaces, and MIDI controllers. Record model, firmware, host driver, supported sample rates/channel counts, clock sources, and control facilities.
2. Distinguish Linux host-driver support from emulating a vendor's macOS driver. Implement host-backed property and control mappings where available; a hardware model requiring an unavailable essential driver remains unsupported and cannot enter the qualified set.
3. Measure physical loopback latency, recording offset, drift, sample-rate transitions, buffer changes, channel labels, device selection, and input/output synchronization. Exercise independently clocked inputs/outputs only if aggregate-device behavior is part of the declared target scope.
4. Disconnect/reconnect during playback, recording, idle, and project load; restart the host audio service; test sleep/resume when the deployment profile supports it. Verify recovery and error messages without silently redirecting a live recording to an unintended source.

**Verification and pass gate:**

- [ ] Every qualified hardware/profile combination passes recording, playback, MIDI, and channel-identity tests.
- [ ] Measured round-trip latency and capture alignment meet device-specific frozen limits.
- [ ] Hotplug, service restart, and supported power transitions recover without deadlock, corruption, or stuck notes.
- [ ] Unsupported devices receive accurate capability/error reporting rather than false discovery success.
- [ ] Hardware manifests and qualification scope are visible in the README release claims.

**Required evidence:** Physical loopback captures, device/firmware manifests, driver logs, drift plots, and recovery timelines.

**On failure/next action:** Block P064 and repair the owning backend, clock, notification, or MIDI contract.

<a name="p064"></a>

### P064 — Meet fixed-hardware production performance budgets

**Status:** NOT STARTED.

**Depends on:** P063.

**Objective:** Demonstrate usable production capacity and real-time headroom on a published x86_64 Linux hardware profile.

**Where:** Existing: instrumented runtime, DSP, graphics, storage, and host-audio owners identified by profiling. Proposed: `tests/compat/logic-pro/P064/`, `docs/compat/logic-pro/performance-contract.json`.

**Implementation:**

1. Use the P006 reference projects and freeze CPU, memory, storage, GPU/driver, kernel, audio backend, scheduler configuration, interface, sample rate, buffer size, plug-in versions, and power state before measurement. Publish multiple tiers if needed; do not replace a failed profile silently.
2. Include recording, editing, large sample streaming, synthesis, heavily routed mixing, analysis, GUI stress, and offline bounce. Set minimum useful track/voice counts and acceptable load/save/bounce times in advance based on the declared production workload.
3. Capture callback deadlines and execution distributions, host xruns, scheduling stalls, page faults, I/O queues, memory growth, GPU stalls, and critical-path flame graphs. Optimize measured bottlenecks and preserve numerical/behavioral gates.
4. At 48 kHz, treat 64/128/256-frame periods as approximately 1.333/2.667/5.333 ms of processing time; these values are not physical round-trip latency. Report separately measured converter, buffering, and transport delay.

**Verification and pass gate:**

- [ ] Every frozen production workload meets its predeclared capacity, responsiveness, and render-time limits.
- [ ] One uninterrupted hour per required real-time profile has zero observed underruns, overruns, missed render deadlines, and unexpected engine resets.
- [ ] Worst-case observed callback execution fits the documented headroom budget, with raw maximum and percentile distributions retained.
- [ ] Performance improvements preserve DSP, project-integrity, GUI, and device regressions at the same commit.
- [ ] Reports distinguish measured results from projections and explain hardware differences in native comparisons.

**Required evidence:** Immutable workload/hardware manifests, raw timing traces, profiler captures, exact commands, and before/after comparisons.

**On failure/next action:** Keep P065 blocked; optimize the measured bottleneck or explicitly revise the proposed deployment contract before repeating qualification.

<a name="p065"></a>

### P065 — Pass long-duration operation and fault-recovery qualification

**Status:** NOT STARTED.

**Depends on:** P064.

**Objective:** Establish sustained reliability across real work and controlled failures after the shorter performance gates pass.

**Where:** Existing: all exercised runtime/framework/audio owners. Proposed: `tests/compat/logic-pro/P065/`, `docs/compat/logic-pro/soak-protocol.md`.

**Implementation:**

1. Run an eight-hour minimum uninterrupted qualification session on each required deployment profile, alternating playback, recording, instrument use, editing, autosave, plug-in views, and legitimate background analysis. Keep expected failures out of this baseline run.
2. Track process and helper memory, file descriptors, threads, Mach ports, shared-memory objects, GPU allocations, clock drift, audio counters, and project integrity. Define steady-state resource-growth thresholds before the run and retain time-series evidence.
3. Perform a separate fault campaign: host audio service restart, device disconnect, plug-in/helper crash, project-storage exhaustion, canceled analysis/download, and controlled application termination. Each scenario starts with a known valid disposable project and a specified expected recovery path.
4. Repeat suspicious cases until their cause is understood; a single unexplained crash or silent corruption is a failed gate. Distinguish external service outages from compatibility defects while preserving the overall blocked state when required workflows remain unavailable.

**Verification and pass gate:**

- [ ] Each baseline soak completes at least eight hours with zero observed crashes, deadlocks, xruns, corrupted saves, or unexplained engine resets.
- [ ] Resource usage stays within frozen bounds and shows no unexplained sustained leak after warm-up.
- [ ] Clock alignment and recorded media remain within the established long-run timing contract.
- [ ] Every injected fault follows its verified recovery path without losing the last valid project or leaving orphaned processes.
- [ ] Soak projects reopen on Linux and the reference Mac with expected semantic state.

**Required evidence:** Full run logs, resource time series, audio captures, project manifests, fault timelines, and independent reviewer observations.

**On failure/next action:** Block P066, identify the first causal failure, and rerun the complete affected duration after its fix.

<a name="p066"></a>

### P066 — Close the complete x86_64 feature matrix and verify version selection

**Status:** NOT STARTED.

**Depends on:** P065.

**Objective:** Decide from evidence whether the short-term goal has been met for the newest verified x86_64-compatible Logic release available at qualification time.

**Where:** Existing: `README.md` and all implementation owners with unresolved rows. Proposed: `docs/compat/logic-pro/x86-feature-matrix.json`, `tests/compat/logic-pro/P066/`.

**Implementation:**

1. Reconcile every native first-party feature against P005's exact binary inventory and the P006 reference. Include workflows not individually named earlier: preferences, customization, project interchange, score/print output, control surfaces, export variants, accessibility, and any new features in the selected release.
2. Require a case and evidence for each supported-native row. A Linux failure is FAILED or BLOCKED, not NOT APPLICABLE. Native nonavailability requires official documentation or reproducible native evidence and, where relevant, a linked ARM-track obligation.
3. Recheck release metadata and obtainable legitimate bundles. Inspect executable/helper/plug-in slices and deployment requirements to determine whether a newer x86_64-compatible candidate exists. Marketing pages alone cannot establish the final Intel-compatible version.
4. If a newer qualifying candidate exists, freeze its manifest, compute dependency/API/feature deltas, and reopen affected gates. Preserve the prior build's results as historical evidence, without relabeling them as tests of the new release.

**Verification and pass gate:**

- [ ] Every first-party native-supported feature has executed passing evidence; no untested or blocked row is hidden in a total.
- [ ] Third-party and physical-device support claims match named tested qualification sets.
- [ ] The selected release is the newest x86_64-compatible build verified from the available candidate inventory, with an explicit verification date.
- [ ] All source/submodule hashes and binary/content manifests match the tested configuration.
- [ ] An independent reviewer accepts applicability decisions and confirms that “fully working” has not been weakened to basic launch/audio playback.

**Required evidence:** Signed-off feature matrix, release/slice comparison, open-issue disposition, and complete gate index.

**On failure/next action:** Block P067; reopen the responsible implementation phase or target-selection gate with an exact missing capability.

<a name="p067"></a>

### P067 — Produce a reproducible x86_64 release and clean-install qualification

**Status:** NOT STARTED.

**Depends on:** P066.

**Objective:** Make the qualified runtime reproducibly installable outside the development machine without redistributing user-owned proprietary application assets.

**Where:** Existing: `CMakeLists.txt`, `cmake/`, `debian/`, `rpm/`, `.github/workflows/actions.yaml`, and `README.md`. Proposed: `tests/compat/logic-pro/P067/`, `docs/compat/logic-pro/release-manifest.json`, additional packaging/CI files where needed.

**Implementation:**

1. Build from the qualified root commit and pinned submodules in a clean environment. Record compiler/linker, SDK inputs, dependencies, feature switches, generated files, and artifact hashes. Explain any non-bit-reproducible inputs and make functional reproduction independently verifiable.
2. Package all required runtime/framework components and host dependencies. Detect incompatible or missing drivers/backend services at setup time, expose actionable diagnostics, and avoid accidental dependence on a developer's home directory or cache.
3. Document installation, legitimate application/content provisioning, initial configuration, updates, rollback, diagnostic collection, and removal. Test account and receipt paths using authorized fixtures with secrets excluded from artifacts.
4. Extend CI with always-available synthetic ABI/audio/MIDI/GUI regressions and an authorized integration runner for proprietary Logic tests. Keep private assets on permitted infrastructure; clearly distinguish an unavailable integration runner from a passing test.

**Verification and pass gate:**

- [ ] A second operator reproduces the release build from documented source and dependency pins.
- [ ] Clean installs on every declared distribution/profile complete the full release smoke suite and required representative workloads.
- [ ] Upgrade, rollback, and uninstall behave as documented without damaging user projects or unrelated host configuration.
- [ ] Public artifacts contain required notices and runtime components, with no application binaries, credentials, or unauthorized content accidentally included.
- [ ] CI genuinely fails on injected regressions and reports unavailable proprietary integration tests as blocked/skipped with an explicit reason.

**Required evidence:** Build logs, package manifests/hashes, clean-machine transcripts, release smoke results, and CI failure-demonstration logs.

**On failure/next action:** Keep P068 blocked; correct packaging or reproducibility before release acceptance.

<a name="p068"></a>

### P068 — Independently accept and maintain the x86_64 milestone

**Status:** NOT STARTED.

**Depends on:** P067.

**Objective:** Accept the short-term milestone only after independent reproduction, then preserve its validity while opening the ARM translation track.

**Where:** Existing: `README.md`, release/CI configuration, and all affected source owners. Proposed: `docs/compat/logic-pro/x86-acceptance.md`, `tests/compat/logic-pro/P068/`.

**Implementation:**

1. Assign a reviewer who did not implement the critical failing/fixed paths. Provide the immutable source, binary/content, host, hardware, workload, and artifact manifests; require them to reproduce installation and a risk-based cross-section of the full feature matrix.
2. Audit all P001–P067 checkboxes, runtime assertions, stub-detection output, unresolved issues, applicability decisions, soak results, and failure/recovery evidence. A satisfied-looking interface or successful build never substitutes for executed behavior.
3. Publish a scoped release statement: exact Logic build and architecture, verification date, qualified Linux/hardware profiles, tested third-party ecosystem, measured latency/capacity, and remaining native platform restrictions. State that latest ARM Logic remains a separate unmet goal until its later gates pass.
4. Establish change triggers: upstream merge, submodule update, compiler/backend/driver change, new Logic release, new plug-in version, and new hardware profile. Each triggers impact analysis and reopens relevant gates; old evidence stays attributable to its original configuration.

**Verification and pass gate:**

- [ ] Independent review accepts every required x86_64 gate and reproduces the selected end-to-end cases without undocumented assistance.
- [ ] No unresolved defect contradicts the full native first-party feature claim on the declared profile.
- [ ] Release documentation exposes the actual measured scope and newest-verified-build date without claiming universal plug-in/hardware compatibility.
- [ ] Regression owners, rerun triggers, evidence retention, and rollback procedure are assigned and exercised once.
- [ ] README records the accepted milestone, evidence links, implementation commits, next owner, and P069 as the next eligible phase.

**Required evidence:** Independent acceptance record, reproduced cases, release statement, and a sample change-impact/requalification exercise.

**On failure/next action:** Leave the milestone unaccepted and P069 blocked; reopen the earliest invalid gate and name the exact remediation.

## ARM delivery: latest Apple silicon Logic on an x86_64 Linux host

**P069 cannot begin implementation until P068 passes.** This track must retain the working Intel profile while adding ARM execution. The guest application architecture is ARM64; the physical Linux host remains x86_64. Every phase below inherits the global evidence, independent-review, and README-update requirements.

<a name="p069"></a>

### P069 — Freeze the current ARM release and its complete native feature inventory

**Status:** NOT STARTED.

**Depends on:** P068.

**Objective:** Replace preliminary ARM assumptions with an exact, current, legally obtained application manifest and Apple silicon reference behavior. Recheck the newest release at this point; the version identified when this README was written may have changed.

**Where:** Existing: loader/framework/build locations in the implementation map. Proposed: `docs/compat/logic-pro/targets/arm64.json`, `arm64-features.md`, `arm64-dependencies.json`, and `tests/compat/logic-pro/P069/`.

**Implementation:**

1. Enumerate all Mach-O slices, CPU subtypes, minimum OS versions, UUIDs, imports, fixup formats, embedded frameworks, XPC services, extensions, executable content, models, and shader libraries. Include nested assets; do not inspect only the main executable.
2. Run the selected build natively on a supported Apple silicon Mac. Record the hardware, OS, app channel/build, library versions, and results for every first-party feature, including newly added features absent from the Intel baseline.
3. Separate actual ARM64/arm64e and instruction requirements from marketing requirements. Identify dependencies on graphics/compute services, model execution, platform checks, and auxiliary processes with trace evidence.
4. Define the architecture of each plug-in/helper supported in the ARM release. Keep the verified Intel release and its artifacts available for regression comparison.

**Verification and pass gate:**

- [ ] A reviewer independently reproduces the complete ARM bundle inventory and checks its hashes.
- [ ] Every advertised native feature has a reference scenario and expected result; no unexplained entry is omitted.
- [ ] The newest-release search and selected exact build/channel are dated and evidenced.
- [ ] Native reference runs succeed, and required model/content/helper assets are identified and available to authorized tests.

**Required evidence:** Release search record, signed-off target manifest, architecture/dependency graphs, native feature results, and asset hashes.

**On failure/next action:** Remain in P069 until unavailable binaries, native failures, or unknown dependencies are resolved. After acceptance, evaluate the execution architecture in P070.

<a name="p070"></a>

### P070 — Choose an ARM-to-x86 execution architecture through measured feasibility work

**Status:** NOT STARTED.

**Depends on:** P069.

**Objective:** Select a technically defensible instruction-translation architecture before building a large integration around it. An ARM Linux port alone is not an acceptable decision.

**Where:** Existing: `src/startup/mldr/`, `src/external/darlingserver/`, `src/external/dyld/`, and architecture CMake files. Proposed: `docs/compat/logic-pro/decisions/arm-execution.md` and a disposable feasibility benchmark under `tests/compat/logic-pro/P070/`.

**Implementation:**

1. Compare a Darwin-aware in-process dynamic translator with an adapted mature CPU engine and other concretely viable architectures. Evaluate source availability, maintenance, licensing compatibility, Mach-O integration, memory ownership, syscall interception, exceptions, and multithreading. QEMU TCG is a research candidate; its current [user-mode documentation](https://www.qemu.org/docs/master/user/main.html) does not make stock Linux-user execution a complete Darwin application environment.
2. Use isolated candidate experiments to measure representative scalar/vector DSP, indirect calls, thread synchronization, and host-boundary calls on the intended x86 host. Distinguish existing backend capability from work this fork would still need.
3. Decide which code stays in the translated Darwin ABI and which typed boundaries may call native Linux/x86 implementations. Prefer preserving one guest object/runtime domain until a bridge is proven.
4. Record architecture risks and numerical performance budgets derived from the frozen audio workloads. Select a pinned backend or formally block the goal if no candidate is viable.

**Verification and pass gate:**

- [ ] The chosen design actually executes ARM instructions on an x86_64 host and accounts for Darwin services separately.
- [ ] Candidate measurements, missing capabilities, integration ownership, and maintenance costs are reviewable.
- [ ] There is a concrete ABI/memory/thread/exception boundary design and a justified path to the declared deadlines.
- [ ] No ARM-native Linux result or full-system VM is substituted for the required application-on-x86 goal.

**Required evidence:** Architecture decision, benchmark sources/results, backend revision/license inventory, boundary diagram, and risk register.

**On failure/next action:** Remain BLOCKED in P070 if feasibility is not demonstrated. Do not promise real-time viability from instruction correctness alone. Proceed to P071 only after independent acceptance.

<a name="p071"></a>

### P071 — Add translator integration, guest address space, and build isolation

**Status:** NOT STARTED.

**Depends on:** P070.

**Objective:** Establish a maintainable translation subsystem and loader integration without destabilizing the qualified Intel runtime.

**Where:** Existing: `CMakeLists.txt`, `cmake/architecture.cmake`, `src/startup/mldr/loader.c`, `src/startup/mldr/mldr.c`, and relevant `src/CMakeLists.txt` entries. Proposed: `src/translation/` with backend, guest-state, memory, dispatch, and tracing interfaces; `tests/compat/logic-pro/P071/`.

**Implementation:**

1. Separate host architecture from guest architecture throughout configuration. Build x86 host support code and ARM guest runtime libraries with unambiguous targets, output directories, dependency graphs, and package names.
2. Define the guest register/state structure, address-space ownership, mapped-image records, dispatch entry/exit contract, code-cache ownership, and structured unsupported-operation faults.
3. Add explicit ARM Mach-O selection/loading while retaining Intel selection. Validate segments, alignments, protections, bounds, entry metadata, and mapping collisions before any guest instruction executes.
4. Integrate the pinned backend behind a narrow interface. At this phase, loader/state tests may deliberately stop at the first unsupported instruction; do not mislabel a loader-only test as ARM execution. Instruction acceptance follows in P072.

**Verification and pass gate:**

- [ ] Clean builds produce distinct host/guest artifacts with no architecture contamination.
- [ ] Valid ARM fixtures map deterministically; malformed/truncated/overlapping fixtures fail safely with actionable errors.
- [ ] Guest state can enter/leave the dispatch interface without corrupting host state or leaking mappings.
- [ ] The P068 Intel qualification smoke subset still passes, and ARM-disabled packages retain their previous behavior.

**Required evidence:** Build graphs, artifact architecture reports, mapping traces, negative fixtures, and Intel regression results.

**On failure/next action:** Keep P071 active until integration and isolation are sound; then implement scalar execution in P072.

<a name="p072"></a>

### P072 — Implement and verify ARM scalar instructions and control flow

**Status:** NOT STARTED.

**Depends on:** P071.

**Objective:** Execute the scalar ARM instruction families required by the target accurately on x86_64.

**Where:** Proposed selected-backend integration under `src/translation/`, instruction decoding/lowering components chosen in P070, and `tests/compat/logic-pro/P072/`.

**Implementation:**

1. Build an instruction-coverage inventory from the target's binaries and dynamically discovered code, retaining a structured trap for every unsupported instruction. Cover integer arithmetic, flags, shifts, extensions, loads/stores, addressing modes, branches, calls, returns, and indirect dispatch required by the inventory.
2. Test both 32-bit and 64-bit register behavior, zero/sign extension, carry/overflow flags, unaligned accesses, endianness, stack alignment, and precise faulting addresses. Do not infer semantics from mnemonic similarity to x86.
3. Compare generated and edge-case instruction sequences against native ARM execution and an independently validated reference engine. Use minimized reproducible cases for every discrepancy.
4. Add block linking and indirect dispatch only after the unoptimized execution path is correct; keep a differential slow path to diagnose optimizations.

**Verification and pass gate:**

- [ ] All required scalar families pass deterministic boundary and randomized differential tests with reproducible seeds.
- [ ] Branch/call/return chains preserve guest state and report faults at the correct guest instruction.
- [ ] Unsupported instructions fail explicitly without silently becoming no-ops or successful operations.
- [ ] Multiblock ARM test programs produce the native reference results on the x86 host, and Intel regressions pass.

**Required evidence:** Coverage manifest, reference inputs/outputs, seeds, fault traces, backend revision, and minimized failures fixed.

**On failure/next action:** Remain in P072 until scalar execution is correct; next add vector/floating-point behavior in P073.

<a name="p073"></a>

### P073 — Implement NEON, floating point, and per-thread numerical state

**Status:** NOT STARTED.

**Depends on:** P072.

**Objective:** Preserve the numerical behavior required by ARM audio and graphics code when lowering it to x86 instructions.

**Where:** Proposed `src/translation/` vector/FP lowering and state handling; `tests/compat/logic-pro/P073/`; existing Accelerate fixtures supply higher-level checks later.

**Implementation:**

1. Inventory required NEON/scalar FP and any additional observed ISA extensions. Implement vector lane access, widening/narrowing, saturating operations, conversions, shuffles, reductions, and fused operations with correct lane widths and signedness.
2. Preserve ARM FP control/status behavior, rounding modes, exceptions where observable, NaNs, infinities, subnormals, signed zero, and fused-versus-unfused results. Map to host SSE/AVX only when semantics match; use a tested fallback otherwise.
3. Save/restore guest vector and FP state across dispatch, host calls, and context switches. Use host-driven synthetic guest contexts to verify isolation here; complete Darwin thread lifecycle is qualified in P079 and full signal delivery in P080. Do not let one eventual audio worker inherit another thread's rounding or flush behavior.
4. Differentially test DSP-shaped kernels and adversarial values. Keep performance numbers separate from correctness acceptance.

**Verification and pass gate:**

- [ ] Every required vector/FP family has native comparison cases covering ordinary and exceptional inputs.
- [ ] Results and status are bit-exact wherever the Arm ISA requires them; only architecturally permitted alternatives or documented estimate bounds are accepted. Application-level DSP tolerances do not excuse incorrect instruction semantics.
- [ ] Host-driven tests alternating guest contexts and dispatch entry/exit preserve registers, FP flags, and control state; complete bridge/thread/signal integrations repeat these checks in P078–P080.
- [ ] Unsupported extensions are accurately reported and cannot be exposed as available CPU features.

**Required evidence:** ISA matrix, native/transformed output comparisons, state-transition traces, tolerance rationale, and regression results.

**On failure/next action:** Fix discrepancies in P073; do not hide them with output clamping or silence substitution. Then address concurrency semantics in P074.

<a name="p074"></a>

### P074 — Preserve ARM atomics, exclusives, and memory ordering

**Status:** NOT STARTED.

**Depends on:** P073.

**Objective:** Make multithreaded ARM code correct under translated execution, including its interaction with native host services.

**Where:** Proposed translator memory/atomic lowering, dispatch synchronization, guest-memory helpers, and `tests/compat/logic-pro/P074/`.

**Implementation:**

1. Implement required acquire/release operations, barriers, read-modify-write instructions, and exclusive load/store sequences. Preserve permitted failure/retry behavior without creating lost updates or impossible successes.
2. Define ordering at guest-to-host boundaries and shared-memory IPC. An x86 host's relatively strong memory behavior does not by itself make compiler transformations, helper calls, code generation, or exclusive-monitor emulation correct.
3. Add litmus tests, contended queues, reference-counting, lock-free ring buffers, and cancellation tests with randomized scheduling. Include mixed translated/native access only for explicitly supported shared layouts. Race instrumentation must observe guest memory operations and translated/native sharing; a host-only sanitizer cannot certify uninstrumented generated guest accesses.
4. Use conservative correct paths first; optimize barriers and atomic lowering only after independent comparison. Consult Arm's [memory-ordering guidance](https://support.arm.com/documentation/102336/0100/Memory-ordering) and the selected backend's actual concurrency contracts.

**Verification and pass gate:**

- [ ] Required atomic widths, alignments, barriers, and exclusive sequences pass reference and stress tests.
- [ ] No forbidden result, lost update, corrupted queue, or unbounded retry appears in the defined stress campaign.
- [ ] Host/guest shared-memory boundaries have explicit reviewed ordering and ownership rules.
- [ ] Instrumented race analysis and translated/native comparisons identify no unresolved correctness defect.

**Required evidence:** Memory model decision, litmus outcomes, stress parameters/seeds, ordering annotations, and reviewer reproduction.

**On failure/next action:** Remain in P074 until the concurrency model is correct. Next implement complete guest virtual-memory behavior in P075.

<a name="p075"></a>

### P075 — Reconcile guest virtual memory, page sizes, protections, and mappings

**Status:** NOT STARTED.

**Depends on:** P074.

**Objective:** Present the target's Darwin memory contract without assuming Linux host page geometry or address layout is identical.

**Where:** Existing: `src/startup/mldr/`, `src/external/darlingserver/`, `src/external/xnu/`, relevant memory syscall wrappers. Proposed translator memory manager and `tests/compat/logic-pro/P075/`.

**Implementation:**

1. Record the target's page-size expectations and implement guest-granularity allocation, protection, mapping, deallocation, and queries over the host's actual page size. Exercise 16 KiB guest expectations on a 4 KiB host where applicable; do not globally replace one constant and assume correctness.
2. Preserve fixed-address requests, aliases, copy-on-write, shared files, zero-fill, guard pages, stack growth, and address-space reservations. Translate errors consistently and prevent guest mappings from overwriting translator/native runtime state.
3. Coordinate mappings with code-cache invalidation and guest fault reporting; P081 later completes dynamic-code workloads. Account for shared memory used by audio, IPC, and surfaces.
4. Bound address-space fragmentation and allocation metadata. Test large sample-map workloads without loading the full application yet.

**Verification and pass gate:**

- [ ] Mapping/protection/query behavior matches the native reference for required page geometries and boundary cases.
- [ ] Host-driven multi-context and isolated-process fixtures preserve shared/aliased/COW contents and protections; complete Darwin guest-thread/helper integration repeats these checks in P079/P082.
- [ ] Invalid accesses fault at correct guest addresses without host corruption.
- [ ] Large repeated map/unmap and fragmentation tests show no unexplained resource growth or stale executable mappings.

**Required evidence:** Page-size contract, mapping traces, fault comparisons, memory-pressure results, and leak accounting.

**On failure/next action:** Remain in P075 for mapping or protection failures; next establish the Apple ARM ABI and syscall boundary in P076.

<a name="p076"></a>

### P076 — Implement the Apple ARM ABI, TLS, commpage, and syscall boundary

**Status:** NOT STARTED.

**Depends on:** P075.

**Objective:** Connect ARM execution to Darwin services using Apple's actual ABI rather than assuming generic Linux AArch64 conventions suffice.

**Where:** Existing: `src/startup/mldr/commpage.c`, startup code, `src/external/darlingserver/`, XNU/libSystem/libpthread submodules identified in P001. Proposed ARM-specific translation bridges and `tests/compat/logic-pro/P076/`.

**Implementation:**

1. Implement register/stack arguments, aggregate returns, variadic calls, alignment, thread-local storage, process startup vectors, and ABI-specific data layouts. Include differences in C++ and floating types at boundaries. Use Apple's [ARM64 ABI documentation](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms) and compile native fixtures as the oracle.
2. Supply correct thread-pointer/TLS access, errno isolation, commpage time/capability functions, and guest CPU feature reporting. Advertise only instructions and behaviors the engine can execute.
3. Intercept the target's Darwin syscalls/Mach traps and marshal arguments/results into the existing service layer. Implement cancellation, interrupted calls, timeouts, and error conventions; do not route them as Linux AArch64 syscalls.
4. Verify minimal statically linked C fixtures and host-driven synthetic guest-thread contexts before Objective-C and Logic integration. Establish TLS/errno isolation without requiring the full Darwin pthread/workqueue lifecycle implemented in P079; complete dynamic linking is qualified in P077.

**Verification and pass gate:**

- [ ] ABI fixtures cover scalar/vector/aggregate/variadic calls and required data layouts with native-equivalent results.
- [ ] TLS, errno, clocks, and capability queries are correct and isolated across threads.
- [ ] Required syscall/Mach-trap probes preserve errors, timeouts, and interruption semantics.
- [ ] Minimal static ARM command-line/ABI fixtures execute through this fork on x86_64 Linux with reproducible traces; full dynamic-library and thread-lifecycle claims remain assigned to P077/P079.

**Required evidence:** ABI layout tables, compiler versions, native fixtures, syscall traces, and guest capability manifest.

**On failure/next action:** Remain in P076; adding API names or changing architecture strings is not acceptance. Continue to dynamic linking in P077 after review.

<a name="p077"></a>

### P077 — Support ARM dyld fixups, authenticated pointers, and branch requirements

**Status:** NOT STARTED.

**Depends on:** P076.

**Objective:** Load the selected ARM executable and library formats correctly, including arm64e behavior when the actual target requires it.

**Where:** Existing: `src/external/dyld/`, Mach-O startup/loader code, Objective-C runtime interfaces. Proposed translator pointer/control-flow handling and `tests/compat/logic-pro/P077/`.

**Implementation:**

1. Extend image loading and binding for the exact chained-fixup formats, symbol binding, weak imports, initializers, TLS images, and library metadata observed in P069. Compare with [Apple's fixup definitions](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/fixup-chains.h).
2. Determine whether each image is arm64, arm64e, or another relevant subtype. Implement required pointer authentication/signing/discriminator behavior and branch-target semantics in the execution model, including correct failure behavior. Do not blindly strip every high pointer bit or turn all authentication instructions into successful no-ops.
3. Audit function pointers, C++ virtual tables, Objective-C metadata, block invoke pointers, and loader-produced authenticated pointers at their actual ABI boundaries. [Clang's pointer-authentication ABI documentation](https://clang.llvm.org/docs/PointerAuthentication.html) is a design reference.
4. Test `dlopen`/`dlclose`, duplicate images, malformed chains, missing required imports, and dynamic initializers with small fixtures before the app bundle.

**Verification and pass gate:**

- [ ] Every required fixup/image format binds to the correct address and preserves pointer semantics.
- [ ] Valid authenticated-pointer paths work; deliberately invalid paths fail as defined instead of executing arbitrary targets.
- [ ] Dynamic loading/unloading and initializer ordering match the native reference.
- [ ] A documented absence of arm64e requirements is evidenced by the complete target graph, not assumed from the main executable alone.

**Required evidence:** Image/fixup coverage, pointer tests, loader traces, negative fixtures, and signed-off subtype inventory.

**On failure/next action:** Remain in P077 for unresolved loaders or pointer semantics. Then prove typed cross-architecture calls in P078.

<a name="p078"></a>

### P078 — Build typed guest/host bridges and callback round trips

**Status:** NOT STARTED.

**Depends on:** P077.

**Objective:** Allow translated ARM code to call selected native host services and receive callbacks without corrupting the ABI or object ownership.

**Where:** Proposed `src/translation/bridges/`, bridge generators/schema if justified, selected existing framework/Linux boundary implementations, and `tests/compat/logic-pro/P078/`.

**Implementation:**

1. Define supported bridge signatures and ownership rules for scalars, vectors, structures, unions, pointers, buffers, variadics, and callback contexts. Generate typed adapters only from reviewed signatures; a generic `void *(void)` trampoline is not a safe universal bridge.
2. Keep Objective-C objects, Swift metadata, C++ objects, and block layouts within one agreed guest domain unless an explicit marshaller is proven. Equal pointer width does not imply equal class layout, vtables, calling convention, or exception ABI.
3. Implement nested guest→host→guest calls, callbacks on foreign host threads, reentrancy, thread attachment, lifetime/disposal, and cancellation using controlled guest-context fixtures. Complete guest-created thread/workqueue lifecycle remains P079. Exception crossing is intentionally completed in P080; until then it must fail in a controlled documented manner.
4. Minimize per-buffer transitions by bridging operations in useful batches, without altering observable timing or ownership.

**Verification and pass gate:**

- [ ] All selected signature classes and ownership transfers pass native differential tests and sanitizers where applicable.
- [ ] Nested callbacks, concurrent callbacks, and callbacks after teardown are handled correctly with no use-after-free.
- [ ] Host and guest register, stack, TLS, and FP state remain intact across repeated transitions.
- [ ] Unsupported bridge signatures are rejected explicitly and listed, not silently coerced.

**Required evidence:** Bridge catalog, generated/manual adapter review, callback traces, lifetime tests, and transition-cost measurements.

**On failure/next action:** Remain in P078 until boundaries are trustworthy. Proceed to complete translated thread/process scheduling in P079.

<a name="p079"></a>

### P079 — Make translated threads, workqueues, and multicore execution correct

**Status:** NOT STARTED.

**Depends on:** P078.

**Objective:** Support Logic's concurrent processing without serializing all meaningful work or breaking thread lifecycle semantics.

**Where:** Existing: Darwin threading/workqueue service layers and libdispatch/libpthread submodules. Proposed translator per-thread state, code-cache synchronization, and `tests/compat/logic-pro/P079/`.

**Implementation:**

1. Implement thread creation, startup, join, detach, cancellation, thread-local destructors, and guest context ownership. Map guest workqueue/QoS requests to a documented Linux scheduling policy with correct fallback errors.
2. Allow multiple guest threads to execute on multiple host cores while synchronizing translation metadata and shared guest state correctly. Keep global code-generation/lookup locks out of steady-state audio execution where the selected architecture permits it.
3. Test dispatch queues, semaphores, groups, timers, barriers, recursive callbacks, and bounded worker pools. Preserve priority relationships without claiming that a Linux label exactly duplicates every Darwin QoS behavior.
4. Measure scaling and contention separately from correctness. Use the selected backend's requirements, including [QEMU's multithreaded translation design](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html) if that backend is adopted.

**Verification and pass gate:**

- [ ] Thread/workqueue lifecycle and synchronization fixtures match native results under repeated stress.
- [ ] Multiple translated workers execute concurrently with correct shared-state results and no unresolved race.
- [ ] Cancellation/shutdown leaves no orphan threads, stale callbacks, or guest-state leaks.
- [ ] Scheduling limitations and critical contention sites are measured and documented for later deadline work.

**Required evidence:** Thread traces, stress seeds, race reports, multicore profiles, and scheduler mapping decision.

**On failure/next action:** Remain in P079 for correctness or lifecycle failures. Next complete exceptions and debugging in P080.

<a name="p080"></a>

### P080 — Preserve signals, exceptions, unwinding, and debuggable guest faults

**Status:** NOT STARTED.

**Depends on:** P079.

**Objective:** Make failures and language exceptions behave correctly across translated code and supported host boundaries.

**Where:** Existing: Mach exception/service layers, loader unwind registration, Objective-C/C++ runtimes. Proposed translator PC maps, signal adapters, unwind metadata, and `tests/compat/logic-pro/P080/`.

**Implementation:**

1. Maintain reversible mappings between host generated-code locations and guest instructions/register state. Distinguish guest faults from translator bugs and host-service failures.
2. Implement guest signal delivery, masks, alternate stacks, synchronous faults, asynchronous interruption, and return-to-guest semantics. Preserve precise faulting addresses and resumable state where required.
3. Implement unwind registration, bridge cleanup, and selected exception mechanisms using controlled fixtures and the minimal runtime subset available in this phase. Define supported exception crossings and cleanup/destructor behavior. P083 must repeat the suite using the complete target-required C++/Objective-C/Swift runtimes and actual language-generated paths; unavailable higher-level runtime behavior is not silently declared complete here.
4. Produce useful guest backtraces, symbolication using recorded image UUIDs, core/crash metadata, and minimized repros without relying on raw host JIT addresses alone.

**Verification and pass gate:**

- [ ] Signals and faults arrive with correct guest context, masks, and continuation behavior.
- [ ] Nested unwind, cleanup, and supported bridge-crossing fixtures match their native counterparts using the declared minimal runtime subset; complete language-runtime integration remains mandatory in P083.
- [ ] A deliberate crash can be traced to the original guest image/function/instruction with reproducible artifacts.
- [ ] Repeated signal/exception stress causes no stale frame, leaked resource, or corrupted translation state.

**Required evidence:** Native exception fixtures, crash bundles, host/guest PC-map checks, unwinder tests, and reviewer reproductions.

**On failure/next action:** Keep P080 active until diagnostics and semantics are reliable; then handle dynamically generated code in P081.

<a name="p081"></a>

### P081 — Support generated code, code-cache invalidation, and executable-memory transitions

**Status:** NOT STARTED.

**Depends on:** P080.

**Objective:** Correctly execute required runtime-generated or modified guest code while keeping translation caches coherent across threads.

**Where:** Proposed translator code-cache and memory-protection integration; existing memory service wrappers and reached JIT/runtime interfaces; `tests/compat/logic-pro/P081/`.

**Implementation:**

1. Identify actual generated-code paths from runtimes, plug-ins, DSP, models, and loaders. Implement required instruction-cache synchronization and writable/executable transitions using the agreed guest memory contract.
2. Invalidate affected translations, direct links, lookup entries, and metadata when guest code changes, unloads, remaps, or loses executable permission. Coordinate with executing threads without stale-code execution or deadlock.
3. Keep guest-code permissions distinct from host-generated-code permissions and cache allocation. Handle memory exhaustion and cache eviction predictably.
4. Test self-modifying fixtures, frequent load/unload, cross-thread patch visibility, and changed indirect targets. Preserve a traceable relationship between code hash, translation generation, and faults.

**Verification and pass gate:**

- [ ] Required generated-code paths execute the new instructions after valid synchronization, never stale cached versions.
- [ ] Protection changes and invalid executable accesses produce correct guest behavior.
- [ ] Concurrent invalidation/eviction tests show no use-after-free, deadlock, or unbounded cache growth.
- [ ] Cache miss/flush events are measurable and can be correlated with future audio deadline failures.

**Required evidence:** Dynamic-code fixtures, cache-generation traces, protection results, stress logs, and memory accounting.

**On failure/next action:** Remain in P081 for cache-coherence defects. Proceed to translated helper processes and IPC in P082.

<a name="p082"></a>

### P082 — Run ARM helper processes, launch services, and cross-process IPC

**Status:** NOT STARTED.

**Depends on:** P081.

**Objective:** Extend ARM support beyond a single process so Logic's required helpers and services operate with correct architecture selection and lifecycle.

**Where:** Existing: `src/launchd/`, `src/external/darlingserver/`, XPC implementations/submodules discovered in P001, loader/spawn paths. Proposed `tests/compat/logic-pro/P082/` and helper fixtures.

**Implementation:**

1. Route ARM helper launch/spawn/exec through the translator with inherited environment, credentials, descriptors, working directory, cancellation, and exit status. Select slices per process rather than assuming a universal bundle uses one architecture everywhere.
2. Implement required Mach messages, ports/rights, XPC serialization, shared memory, endpoint transfer, and synchronous/asynchronous replies for translated participants. Use typed serialization; never transfer a raw cross-process function pointer as if it were callable.
3. Test translated-to-translated and explicitly supported translated-to-native service boundaries. Verify helper crashes, restarts, timeouts, disconnections, and orphan cleanup.
4. Build a process topology from the ARM manifest and map every required spawn/IPC mechanism to a minimal representative helper fixture. Full Foundation/Swift/GUI/model-dependent Logic helpers are mapped to P083–P088 prerequisites and must all run for the actual application gate in P088.

**Verification and pass gate:**

- [ ] Minimal helper fixtures covering every required process-launch/registration mechanism run with the correct architecture; actual Logic helper closure remains a mandatory P088 gate.
- [ ] IPC payloads, ownership, rights, ordering, cancellation, and error paths match native fixtures.
- [ ] Helper termination/restart does not hang the parent or leak ports, mappings, descriptors, or processes.
- [ ] Process-tree traces identify all participating binaries and their actual execution architecture.

**Required evidence:** Process topology, architecture reports, IPC traces, restart/fault tests, and resource counts.

**On failure/next action:** Keep P082 blocked for unresolved service boundaries. Next complete the ARM language/framework runtime in P083.

<a name="p083"></a>

### P083 — Complete ARM Objective-C, Swift, Foundation, and application runtime behavior

**Status:** NOT STARTED.

**Depends on:** P082.

**Objective:** Make the target's higher-level language and foundation runtime behave correctly under translation, preserving the object domain decided in P070.

**Where:** Existing: `src/external/objc4/`, `src/external/swift/`, `src/external/foundation/`, CoreFoundation and related submodules, runtime framework implementations. Proposed `tests/compat/logic-pro/P083/`.

**Implementation:**

1. Build and validate the necessary ARM guest runtime libraries. Implement Objective-C message dispatch, categories, protocols, associated objects, weak references, autorelease behavior, blocks, and metadata formats actually used by the target.
2. Complete required Swift ABI/runtime behavior: metadata, generics, protocol witnesses, reference counting, bridging, dynamic casts, reflection, concurrency/task paths, and runtime version compatibility where reached. Do not replace the needed Darwin Swift runtime with an unrelated Linux build merely because both are called Swift.
3. Re-run Foundation/CoreFoundation data, collection, file, serialization, notification, run-loop, and bundle tests under translated ARM execution. Repeat P080 unwind/cleanup/exception tests with complete target language runtimes, including actual language-generated paths, callbacks, and helper interactions.
4. Resolve all ARM-specific regressions while keeping Intel results intact. Record actual reachability for optional language features rather than implementing unrelated APIs blindly.

**Verification and pass gate:**

- [ ] Required language/metadata fixtures pass on native ARM and translated ARM with matching observable behavior.
- [ ] Object lifetime and callback stress show no unresolved leaks, premature frees, or dispatch corruption.
- [ ] Required concurrency and foundation workflows operate across helpers and threads.
- [ ] Unsupported runtime-version paths fail clearly, and the target has no unresolved required runtime dependency.

**Required evidence:** Runtime versions, ABI tests, lifetime results, dependency closure, and Intel/ARM regression comparison.

**On failure/next action:** Remain in P083 until the runtime closure is complete; then qualify graphics boundaries in P084.

<a name="p084"></a>

### P084 — Render ARM application and plug-in graphics through the host backend

**Status:** NOT STARTED.

**Depends on:** P083.

**Objective:** Reuse the completed GUI stack while correctly handling ARM ABI boundaries and the target's current graphics/shader formats.

**Where:** Existing: Cocotron AppKit/CoreGraphics/QuartzCore, `src/frameworks/IOSurface/`, `src/external/metal/`, relevant OpenGL/graphics services. Proposed ARM graphics bridges and `tests/compat/logic-pro/P084/`.

**Implementation:**

1. Re-run the Intel GUI conformance suite under ARM translation, including window lifecycle, events, text, layers, transactions, scaling, and surface sharing. Resolve architecture-sensitive structure/callback layouts.
2. Inventory actual Metal/OpenGL calls, shader libraries, texture formats, synchronization, and command-buffer behavior used by the ARM target and cataloged editors. Implement missing paths in the selected Linux backend with real execution and errors.
3. Prove support for the target's compiled shader/library formats or an available legitimate equivalent pipeline. A Vulkan-capable GPU does not automatically make arbitrary Apple shader libraries usable.
4. Verify cross-process surfaces, completion callbacks, resource lifetime, GPU/CPU synchronization, and recovery from device errors. Keep graphics/translation work from introducing unbounded stalls on audio threads.

**Verification and pass gate:**

- [ ] Required ARM GUI fixtures match native behavior and render correctly on the declared GPU/driver profile.
- [ ] Every reached shader/library format and graphics operation has an implementation and regression case.
- [ ] Surface sharing, callbacks, resizing, and device-error scenarios preserve resources and application responsiveness.
- [ ] Graphics stress is instrumented for interference with audio; no unsupported GPU feature is advertised as working.

**Required evidence:** GPU/driver manifest, shader/API coverage, image comparisons, event traces, resource profiles, and fault results.

**On failure/next action:** Remain in P084 for missing rendering or shader support. Next connect ARM audio and MIDI paths in P085.

<a name="p085"></a>

### P085 — Connect translated ARM audio, MIDI, and Audio Unit callbacks

**Status:** NOT STARTED.

**Depends on:** P084.

**Objective:** Carry the proven Intel audio contract across ARM execution boundaries without adding incorrect timestamps, data layouts, or callback lifetimes.

**Where:** Existing: `src/CoreAudio/`, `src/frameworks/CoreMIDI/`, `src/frameworks/CoreAudioKit/`; proposed typed audio bridges in `src/translation/bridges/` and `tests/compat/logic-pro/P085/`.

**Implementation:**

1. Marshal AudioStreamBasicDescription, AudioBufferList, timestamps, property data, parameter events, MIDI packets/events, and callbacks according to the guest ABI. Keep sample buffers in explicitly owned shared/mapped storage where safe; avoid copies only after correctness is proven.
2. Re-run duplex, planar/interleaved, multichannel, sample-rate, device-change, Audio Unit lifecycle, async completion, and MIDI timing suites under ARM translation.
3. Attach callback threads to the guest runtime safely. Preallocate bridge contexts, stabilize callback code, and expose transition/cache events in real-time traces. Do not perform translation compilation, blocking logging, or avoidable allocation in steady-state callbacks.
4. Verify property listeners and teardown ordering while audio, MIDI, plug-in editors, and helpers are active.

**Verification and pass gate:**

- [ ] ARM audio/MIDI conformance fixtures match the qualified Intel and native ARM contracts.
- [ ] Frame counts, channel ordering, clock conversions, and latency properties remain correct across every bridge.
- [ ] Callback lifetime/reentrancy/teardown tests show no stale calls, deadlocks, or resource corruption.
- [ ] Transition costs and deadline distributions are recorded on the fixed host; unmet later performance targets remain explicit risks.

**Required evidence:** ABI layout checks, loopback captures, MIDI timestamp comparisons, callback traces, and lifecycle stress results.

**On failure/next action:** Remain in P085 until audio boundaries are correct. Next complete ARM DSP behavior and acceleration in P086.

<a name="p086"></a>

### P086 — Qualify ARM Accelerate and DSP with safe native acceleration

**Status:** NOT STARTED.

**Depends on:** P085.

**Objective:** Obtain correct ARM DSP output and remove unnecessary translation overhead at carefully validated numerical boundaries.

**Where:** Existing: `src/frameworks/Accelerate/vecLib/`, audio converter/processing implementations. Proposed typed numerical bridges and `tests/compat/logic-pro/P086/`.

**Implementation:**

1. Re-run all reachable vDSP, FFT, convolution, filtering, vector math, matrix, and related numerical tests with ARM callers. Verify structure layout, scalar types, complex packing, strides, aliasing, alignment, and setup-object ownership across boundaries.
2. Compare a pure translated path with selected host-native implementations. Use native x86 vector/FFT/BLAS libraries only behind reviewed adapters that preserve results, scaling, error behavior, and floating-point state.
3. Benchmark short real-time blocks as well as large offline workloads. Large-array throughput does not establish low overhead for 64-frame calls.
4. Separate model-oriented BNNS/Core ML operations for P087 while retaining their numerical primitives and ABI probes here. Never substitute silence, approximate identity transforms, or constant successful outputs for missing math.

**Verification and pass gate:**

- [ ] Every required ARM DSP operation meets its predeclared native-reference tolerance over boundary and realistic signals.
- [ ] Accelerated and translated paths agree within the justified numerical contract and preserve thread FP state.
- [ ] Setup/disposal, concurrent use, aliasing, stride, and failure cases pass without resource defects.
- [ ] Per-block cost and worst observed latency are measured; optimizations do not regress existing Intel DSP behavior.

**Required evidence:** Numerical corpus, spectra/error metrics, backend versions, bridge review, and small-block/offline benchmarks.

**On failure/next action:** Remain in P086 for output differences or unsafe acceleration. Then implement model/compute services in P087.

<a name="p087"></a>

### P087 — Execute required Core ML, BNNS, MPS, and private model paths

**Status:** NOT STARTED.

**Depends on:** P086.

**Objective:** Supply real model/compute execution for the exact Apple silicon features in the target, using an evidenced CPU/GPU path where viable.

**Where:** Existing: reached frameworks under `src/frameworks/`, `src/frameworks/Accelerate/vecLib/BNNS/`, `src/external/metal/` including MetalPerformanceShaders targets, and `src/private-frameworks/Espresso/` where actually used. Proposed model fixtures/adapters under `tests/compat/logic-pro/P087/` and decisions/evidence directories.

**Implementation:**

1. Trace each feature's actual model format, operator set, data types, preprocessing/postprocessing, scheduling, caches, and framework calls. Do not assume every modern feature uses the same public Core ML entry point.
2. Determine whether the exact model can execute through a compatible CPU or GPU implementation. Apple's [compute-unit API](https://developer.apple.com/documentation/coreml/mlcomputeunits) permits different execution choices, but does not prove every private model has an available portable path.
3. Implement required operators, layouts, quantization, graph compilation/execution, resource lifetime, cancellation, and errors. If a compatible model conversion is selected, validate the complete result and record transformation/version provenance.
4. Treat dedicated Apple Neural Engine emulation as an evidence-driven architectural question, not an automatic prerequisite and not something that may be claimed away. A hardware-bound required operation with no working substitute is a real blocker.

**Verification and pass gate:**

- [ ] Every required model/compute path has a complete operator/dependency inventory and real execution result.
- [ ] Outputs match native references under justified feature-specific tolerances and quality checks.
- [ ] CPU/GPU selection, cancellation, cache reuse, memory pressure, and repeated execution pass.
- [ ] No mandatory Apple silicon feature remains hidden behind a successful stub or an unverified hardware assumption.

**Required evidence:** Model hashes, operator coverage, backend/driver versions, quality comparisons, resource/time measurements, and unresolved hardware findings.

**On failure/next action:** Remain BLOCKED in P087 for any required unsupported model path. After acceptance, launch the complete ARM application in P088.

<a name="p088"></a>

### P088 — Launch latest ARM Logic and complete the first real project

**Functional-test scope for P088–P091:** These phases establish native-equivalent behavior under declared diagnostic execution profiles, including larger buffers where needed. Record those settings and all measured deadline deficits. They cannot replace or weaken P093's required 64/128-frame live qualification. Unsupported functionality still blocks the current phase; final live-performance acceptance belongs to P092/P093.

**Status:** NOT STARTED.

**Depends on:** P087.

**Objective:** Demonstrate the first complete ARM Logic application flow on physical x86_64 Linux, with all required helpers and real audio behavior.

**Where:** Existing runtime/framework/translator components implicated by traces. Proposed `tests/compat/logic-pro/P088/` integration recipes and ARM smoke project.

**Implementation:**

1. Install the exact manifested target and legitimate content into a clean isolated prefix using the qualified installation path. Launch with architecture tracing enabled and verify that the selected Logic executable is actually ARM.
2. Complete required first-run/account/content interactions, open an empty project, create audio and instrument tracks, record input/MIDI, play a stock instrument/effect, edit, save, close, reopen, and export a short reference project.
3. Trace helper/service startup and all unexpected stubs or errors. Fix missing semantics in the owning layer rather than patching the application's success checks.
4. Repeat from clean and warm states while comparing project and output results to the native ARM reference.

**Verification and pass gate:**

- [ ] Process/binary evidence proves ARM Logic executes through the selected engine on an x86_64 Linux host.
- [ ] The complete first-project scenario succeeds with actual non-placeholder audio/MIDI and reusable saved data.
- [ ] Required helpers, services, and legitimate authorization paths operate without unresolved blocking failures.
- [ ] Multiple cold/warm repetitions reproduce the result with no unhandled required stub or hidden manual repair.

**Required evidence:** Host/guest architecture reports, full process traces, project recipe/hash, recordings/exports, native comparison, and reproduction commands.

**On failure/next action:** Remain in P088 for any incomplete step. This milestone does not yet qualify all features or real-time production performance; next complete feature-specific workflows in P089.

<a name="p089"></a>

### P089 — Complete all Apple silicon and current-version first-party features

**Status:** NOT STARTED.

**Depends on:** P088.

**Objective:** Close the full ARM feature inventory rather than releasing a translated Intel-like subset of the latest application.

**Where:** Existing framework/audio/graphics/model implementations reached by each feature. Proposed `tests/compat/logic-pro/P089/` feature projects and `docs/compat/logic-pro/targets/arm64-feature-results.md`.

**Implementation:**

1. Execute each native ARM feature scenario from P069, including applicable Stem Splitter, ChromaGlow, Mastering Assistant modes, session-player/assistance functions, and every additional feature introduced by the selected build. This list is illustrative; the complete native inventory is authoritative.
2. Validate not just button availability but processing quality, parameter behavior, preview/playback, undo/redo, automation where supported, cancellation, project persistence, and final export.
3. Measure model initialization, GPU/CPU work, memory, output alignment, and UI responsiveness. Compare results against the same content and settings on the native reference.
4. Add a minimized regression fixture for every fixed feature failure. Keep any unmet mandatory feature visible as BLOCKED with a concrete owning dependency.

**Verification and pass gate:**

- [ ] Every applicable first-party ARM feature has a passing native-comparison workflow and recorded artifact.
- [ ] No Apple silicon feature is removed, renamed, silently downgraded, or replaced with a constant-output approximation to achieve a pass.
- [ ] Feature state survives save/reopen and produces native-equivalent streaming/offline results under the recorded functional-test profile; final live deadline acceptance remains mandatory in P093.
- [ ] Cancellation, invalid input, unavailable resources, and repeated-use tests behave correctly without corrupting the project.

**Required evidence:** Complete feature matrix, per-feature inputs/settings/outputs, quality/timing comparisons, persistence cases, and reviewer results.

**On failure/next action:** Remain in P089 for any mandatory feature gap. Next qualify third-party architecture combinations in P090.

<a name="p090"></a>

### P090 — Qualify ARM plug-ins and explicit cross-architecture Audio Unit hosting

**Status:** NOT STARTED.

**Depends on:** P089.

**Objective:** Support the declared plug-in catalog with explicit architecture-aware hosting and isolation.

**Where:** Existing AudioComponent/Audio Unit hosting, CoreAudioKit, XPC/helper lifecycle, AppKit/graphics. Proposed architecture broker/adapter only if required by the approved design, and `tests/compat/logic-pro/P090/`.

**Implementation:**

1. Inventory each catalog plug-in's exact executable/helper slices, AU version, resources, UI, authorization path, state format, and supported native hosting mode. Test ARM-native plug-ins first.
2. For Intel-only plug-ins required by the catalog, design a supported separate process/bridge where necessary. Do not directly load an x86 function pointer into an ARM caller or assume Apple Rosetta is available on Linux. Apple's [Audio Unit compatibility guidance](https://support.apple.com/en-ca/102082) provides native behavior to compare, not a Linux bridge implementation.
3. Validate sample transport, parameter timestamps, latency reporting, state save/restore, automation, sidechains, multi-output routing, editors, helper crashes, and reconnect behavior across the architecture boundary.
4. Preserve the exact catalog and clearly label genuinely unsupported architecture combinations. A required advertised combination blocks qualification until it works.

**Verification and pass gate:**

- [ ] Every cataloged plug-in and supported architecture combination passes validation, rendering, UI, state, and automation tests.
- [ ] Cross-architecture hosting has explicit typed IPC/buffer ownership and correct timing/latency behavior.
- [ ] Plug-in/helper failures are isolated and recover without data loss, hung audio, or orphan processes.
- [ ] No untested plug-in or architecture is represented as supported by inference from another product.

**Required evidence:** Catalog versions/hashes, architecture topology, plug-in projects, bridge latency results, crash/recovery cases, and independent review.

**On failure/next action:** Remain in P090 for required catalog gaps. Then repeat full production workflows in P091.

<a name="p091"></a>

### P091 — Requalify complete production workflows and cross-platform project exchange

**Status:** NOT STARTED.

**Depends on:** P090.

**Objective:** Demonstrate that the ARM application can perform complete production sessions, including exchange with native Logic environments.

**Where:** Existing components as traced by failures. Proposed ARM variants of P049–P063 project fixtures and `tests/compat/logic-pro/P091/`.

**Implementation:**

1. Re-run the full first-party and catalog workflow matrix under ARM translation: editing, comping, timing, automation, routing, libraries, plug-ins, scoring/video, multichannel/spatial outputs, project management, and recovery. Include both new projects and existing supported-format projects.
2. Move projects between Linux/ARM execution and native Apple silicon Logic with the same exact app build. Where Intel/ARM versions differ, test only documented supported interchange paths and record version limitations; do not require impossible backward compatibility.
3. Verify audio, MIDI, region positions, fades, automation curves, mixer state, plug-in presets, sample references, metadata, and exports rather than merely checking that a project opens.
4. Exercise both host display configurations and named interfaces in the qualified profile while collecting translation, audio, graphics, and storage traces.

**Verification and pass gate:**

- [ ] Every applicable production workflow passes with no missing state, silent content substitution, or unsupported required operation.
- [ ] Same-version native↔Linux project exchange preserves the defined project semantics and output quality.
- [ ] Version-limited interchange is explicitly documented and correctly rejected or handled where unsupported.
- [ ] All workflow failures have reproducible regression cases; no mandatory case remains untested.

**Required evidence:** Full matrix, project semantic comparisons, input/output hashes, audio/MIDI/video artifacts, and cross-platform review.

**On failure/next action:** Remain in P091 for any functional mismatch. Only then optimize full-workload translation performance in P092.

<a name="p092"></a>

### P092 — Optimize translation using measured Logic bottlenecks

**Status:** NOT STARTED.

**Depends on:** P091.

**Objective:** Reduce translation overhead while preserving the already qualified behavior and numerical contracts.

**Where:** Selected translator/backend, native bridges, framework hot paths, code-cache policy, and proposed `tests/compat/logic-pro/P092/` benchmarks.

**Implementation:**

1. Profile representative Logic projects and classify time in guest DSP, translated control flow, indirect dispatch, runtime calls, bridge marshalling, synchronization, code generation, graphics, storage, and host audio. Do not optimize a synthetic score unrelated to the failing workload.
2. Improve hot block linking, register allocation, vector lowering, callback batching, cache sizing, and typed native acceleration where measurements justify them. Keep a correct reference path and version each optimization separately.
3. Pretranslate or warm required code outside real-time callbacks where possible, while still measuring cold paths and legitimate runtime changes. Prewarming cannot excuse an unbounded callback stall when a user invokes a supported live operation.
4. Re-run numerical, concurrency, exception, code-invalidation, and workflow regressions after each optimization. Measure p95/p99 and worst observed latency as well as throughput and memory.

**Verification and pass gate:**

- [ ] Profiles identify and quantify the dominant costs on the frozen host/projects.
- [ ] Chosen optimizations produce reproducible improvements without changing any required output or behavior.
- [ ] Cold/warm/cache-pressure behavior and memory use remain bounded and observable.
- [ ] Translated-block, bridge, cache, and scheduling costs meet the component budgets fixed before optimization on the declared fixtures, with raw maxima and distributions retained; a budget deficit blocks progression to P093.

**Required evidence:** Before/after profiles, patch-level benchmark comparisons, regression results, cache metrics, and budget accounting.

**On failure/next action:** Remain in P092 if performance cannot plausibly meet the profile; do not weaken functionality to manufacture speed. Proceed to actual deadline qualification in P093.

<a name="p093"></a>

### P093 — Meet the ARM-on-x86 real-time audio and monitoring contract

**Status:** NOT STARTED.

**Depends on:** P092.

**Objective:** Prove production-relevant real-time behavior on the declared x86 hardware, including translation overhead and realistic user interaction.

**Where:** Existing host audio backend, scheduling/workgroup mappings, translator critical paths, and proposed `tests/compat/logic-pro/P093/` workload runner and measurement recipes.

**Implementation:**

1. Run the frozen live and mixing profiles at the required sample rates, buffers, channel counts, and interface settings. Include simultaneous recording, monitoring, instruments, automation, editing, plug-in windows, and supported live feature changes.
2. Measure hardware loopback round-trip latency, callback start jitter, execution time, queue depth, device/bridge/converter delay, translation-cache events, CPU/core usage, thermal steady state, and storage pressure.
3. Resolve deadline misses at their actual cause. Use bounded scheduling and preallocation; avoid global busy loops or a configuration that starves normal UI/storage services.
4. Repeat on the declared qualification host(s) with documented settings and no hidden interventions. Separate unsupported hardware profiles from supported-profile failures.

**Verification and pass gate:**

- [ ] The fixed 48 kHz live profiles at 64/128 frames and declared mixing profiles meet all predeclared limits on the qualified hardware.
- [ ] Acceptance runs show zero observed unexplained dropouts, overruns, underruns, or missed callback deadlines.
- [ ] Measured round-trip latency and compensation agree with the device/plug-in model; buffer period is not reported as round-trip latency.
- [ ] Concurrent UI, MIDI, content access, and supported feature operations remain usable without violating the audio contract.

**Required evidence:** Raw loopback captures, deadline distributions/maxima, complete environment settings, workload manifests, xrun counters, and independent reruns.

**On failure/next action:** Remain BLOCKED in P093 until the actual profile passes. Then perform long-duration reliability qualification in P094.

<a name="p094"></a>

### P094 — Pass ARM long-duration, fault, recovery, and resource tests

**Status:** NOT STARTED.

**Depends on:** P093.

**Objective:** Demonstrate stable sessions beyond short demonstrations and recover from expected failures without project or audio-state corruption.

**Where:** All affected runtime/audio/graphics/translation/service layers; proposed `tests/compat/logic-pro/P094/` soak and fault scripts, and evidence manifests.

**Implementation:**

1. Run at least eight continuous hours of the frozen representative session with recording/playback, automation, periodic editing/saving, content streaming, and declared plug-in/model activity. Record hardware thermal state and background load.
2. Run separate controlled campaigns for device unplug/replug, sample-rate changes, plug-in/helper crash, display loss, audio-server restart, disk full, missing samples, permission errors, network loss where relevant, and process termination/recovery. Fault injection is separate from the uninterrupted no-dropout acceptance run.
3. Track RSS, virtual mappings, guest and code caches, GPU memory, descriptors, ports, threads, disk growth, and allocator summaries. Define settling windows and explain intentional caches rather than labeling every increase a leak.
4. Verify autosave recovery and final project/output integrity natively. Confirm errors are visible and recoverable instead of silently losing tracks or taking the entire session down.

**Verification and pass gate:**

- [ ] The uninterrupted eight-hour profile finishes with no unexplained crash, dropout, deadline miss, or corruption.
- [ ] Every declared fault case produces the expected visible error and recovery behavior without unauthorized data loss.
- [ ] Resource usage stabilizes within predeclared bounds, with no unresolved leak or unbounded cache growth.
- [ ] Recovered and final projects reopen natively with correct state and outputs.

**Required evidence:** Time-series metrics, uninterrupted audio traces, fault timelines, recovery artifacts, native comparisons, and reviewer reproduction of critical cases.

**On failure/next action:** Remain in P094, reopen earlier faulty phases where necessary, and repeat the affected campaign after repair. Next conduct independent full-scope qualification in P095.

<a name="p095"></a>

### P095 — Independently audit the complete latest-ARM qualification claim

**Status:** NOT STARTED.

**Depends on:** P094.

**Objective:** Verify that the final claim matches actual evidence and that no feature, architecture, or performance gap was concealed by the development process.

**Where:** This README, all target/feature/catalog manifests, evidence directories, release candidate artifacts, and proposed `docs/compat/logic-pro/evidence/P095/qualification-audit.md`.

**Implementation:**

1. A reviewer who did not implement the relevant subsystem reconciles every native feature, required dependency, catalog entry, hardware profile, and phase checkbox against actual evidence and reruns high-risk cases.
2. Recheck the newest available ARM Logic release/channel. If a newer release exists, the current candidate may only claim qualification for its recorded build; completing the requested latest-release goal requires inventory and affected-gate requalification for the newer build.
3. Inspect stub-hit/error traces, skipped tests, native-not-applicable decisions, numerical tolerances, authorization/service dependencies, unavailable private artifacts, and manual workarounds. No ambiguous result is promoted to pass.
4. Confirm that the physical host is x86_64, the actual Logic process uses the ARM slice, and all helpers/plug-ins use documented supported execution paths. Check Intel release regressions as well.

**Verification and pass gate:**

- [ ] Every applicable first-party feature and advertised catalog/profile requirement has valid reproducible evidence.
- [ ] All 94 preceding phase results remain valid; regressions or scope mismatches are reopened and resolved.
- [ ] The exact latest-release claim is correct as of the dated review, with no unverified newer candidate hidden.
- [ ] Independent review finds no required skipped case, fabricated success, undocumented workaround, or misleading architecture claim.

**Required evidence:** Signed audit checklist, rerun logs, latest-version check, coverage reconciliation, exception disposition, and reviewed candidate hashes.

**On failure/next action:** Block P095 and return to the earliest invalid phase until corrected. After a clean audit, package and release through P096.

<a name="p096"></a>

### P096 — Publish the qualified ARM release and establish continuous requalification

**Status:** NOT STARTED.

**Depends on:** P095.

**Objective:** Deliver a reproducible, installable, supportable ARM-on-x86 Logic compatibility environment and maintain truthful current-version claims.

**Where:** Existing `ci/`, `.github/workflows/`, `debian/`, `rpm/`, build files, submodule pins, and this README. Proposed `ci/logic-pro/` release/qualification jobs, release manifests, migration/rollback recipes, and maintenance schedule.

**Implementation:**

1. Build clean release artifacts from reviewed pinned source and all submodule commits. Publish checksums, dependency/runtime versions, supported host profiles, legitimate user-asset prerequisites, installation steps, and the complete known-limitations/certified-catalog record.
2. Test clean install, upgrade from the prior qualified runtime, project preservation, uninstall where supported, and rollback. Reproduce at least one full representative session from released artifacts rather than a developer build tree.
3. Maintain separate Intel and ARM qualification lanes. Track new Logic releases, OS/framework changes, Linux/kernel/audio/GPU updates, translator changes, and catalog plug-in updates. An update invalidates affected evidence until the required gates are rerun.
4. Keep this README's dashboard, current phase/requalification work, tested build/date, evidence links, and handover current after every agent session. Upstream reusable fixes where appropriate without claiming acceptance before upstream review.

**Verification and pass gate:**

- [ ] A fresh x86_64 Linux machine installs the release and reproduces the reviewed ARM Logic workflows with the declared prerequisites.
- [ ] Released artifacts match reviewed source/submodule manifests and pass clean-install, upgrade, project-preservation, and rollback tests.
- [ ] The README accurately states exact qualified Intel/ARM versions, hardware/catalog scope, evidence, remaining limitations, and the date of the latest-version check.
- [ ] Continuous public probe CI and authorized full-application qualification jobs exist, have accountable owners, and fail visibly on regressions.
- [ ] An independent reviewer accepts the release artifact results; the maintenance handover names the next concrete verification action.

**Required evidence:** Release artifact hashes, reproducible build record, clean-machine session results, migration/rollback logs, final reviewer verdict, and maintenance ownership.

**On failure/next action:** Remain in P096 until released artifacts reproduce the qualification. After passing, the next work is explicit version/hardware/catalog requalification under the same gates—not an unsupported promise that all future Logic releases automatically work.

## Risk register and rules for interpreting progress

| Risk / uncertainty | Earliest controlling gate | Required response |
| --- | --- | --- |
| The newest Intel-compatible app build is not established by current marketing pages | P005, rechecked P066 | Inspect actual binaries and helpers, run the reference build, preserve release/channel evidence, and date the claim. Never guess the last Intel version. |
| A clean fork checkout cannot fetch an upstream submodule pin | P001–P002 | Repair source provenance and fetchability before implementation; preserve missing-object evidence. |
| Logic reaches an undocumented/private dependency absent from the original inventory | P007–P008 and every integration phase | Add it to the graph, reduce the failure, implement its actual observable contract in its owner, and extend the oracle corpus. |
| A framework exists but returns a successful placeholder | P004, P008–P009, then every functional gate | Treat the stub as missing behavior. Assert output/state/callback/error semantics; fail the gate on a reached required placeholder. |
| Native GUI/audio initialization requires a subsystem whose full formal phase is later | Current active phase | Implement the minimum real prerequisite under the dependency-repair rule. Do not advance, fake success, or mark the later phase passed. |
| Live audio cannot meet deadlines on the declared host | P035, P064–P065, P092–P094 | Measure the actual cause, fix the implementation or remain blocked. Report physical round-trip latency separately from buffer duration. |
| ARM translation is correct but too slow for production | P070, P092–P094 | Keep measured feasibility/performance gates binding. Do not substitute an ARM host or a reduced feature set for the requested ARM-on-x86 result. |
| A required shader, model, service, or hardware-dependent operation has no working compatible path | P026/P062 or P084/P087 | Record a concrete blocker and its dependency. Do not advertise the capability or treat a framework stub as an implementation. |
| An integration test depends on unavailable commercial assets, devices, or services | Its owning feature phase | Arrange authorized test access; keep the case blocked until evidence exists. A public synthetic test does not automatically prove proprietary application behavior. |
| A new release changes requirements during development | P005/P066 or P069/P095 | Keep the current campaign immutable, open a new target manifest, compute the delta, and rerun affected gates. A previously qualified build stays historically qualified; it does not inherit “latest” forever. |
| A fix in one submodule or architecture breaks another | Every changed dependency and release gate | Reopen the earliest invalid gate, invalidate affected downstream claims, preserve regression evidence, and repair before further advancement. |

There is no evidence-based calendar estimate for “perfect Logic compatibility” at this starting point. This is a substantial operating-system compatibility, graphics, audio, and binary-translation program. P001–P009 produce the information needed to estimate the Intel work; P069–P070 produce the information needed to assess the ARM-on-x86 architecture. Unknowns must become experiments, measured blockers, or implemented contracts—not confident schedules invented before the binary and workload inventories exist.

Progress is measured by **reproducible behavior and completed gates**, not lines of code, exported-symbol counts, number of generated framework directories, elapsed time, or an agent's confidence. Keep user-visible claims tied to the exact evidence.

## Initial handover and ongoing work log

Append new dated entries here after every work session, and update the affected phase and dashboard at the same time. Keep this section chronological. If it becomes large, archive older evidence in the proposed evidence directory while retaining a concise historical entry and link here. The current handover must always remain directly readable in this README.

### 2026-10-31 — Initial research and roadmap publication

| Field | Record |
| --- | --- |
| Author / work type | Documentation research and roadmap authoring |
| Source inspected | Parent repository commit `3447ff5ab8e837ea54a13a506c60d34d77e2bd15` and pinned source snapshots cited above |
| Implementation changed | None; this publication replaces `README.md` with the complete plan |
| What was done | Inspected source/build/submodule structure, audio/MIDI/DSP/GUI gaps, and current official Logic requirements; created 96 gated phases, source ownership map, qualification contracts, evidence policy, and mandatory per-agent progress/handover instructions |
| Documentation review | Independent review of phase sequencing, architecture claims, source locations, acceptance loopholes, and x86-versus-ARM scope; fixes incorporated before publication |
| Documentation checks | Sequential P001–P096 numbering, predecessor relationships, required section fields, unchecked gate state, index anchors, consistent proposed evidence paths, and publication content integrity checked |
| Actual Logic/runtime tests | Not performed; no application execution or phase completion is claimed |
| Passed phases | **0 / 96** |
| Current phase | **P001 — NOT STARTED** |
| Immediate next action | Create the P001 source inventory at the live repository head, record all gitlinks/URLs/pins and the audited baseline, and prove recovery in an isolated checkout |
| Next permitted phase | Remain in P001 until every P001 gate and independent review pass; only then start P002 |
| Key unresolved items | Exact newest Intel bundle, reference Intel workload evidence, clean recursive clone, build/runtime execution; ARM bundle/reference and translator feasibility are later mandatory gates |
| Branch publication context | The live API inspection for P001 confirms `master` as the default and only observed branch; the roadmap commit is `b25035fce2cd1c038c567d34ea0797371947d95d` on `master`. The previous statement about a `main` mirror was not supported by the observed branch topology and is corrected here. |

### 2026-10-31 — P001 implementation and verification campaign

| Field | Record |
| --- | --- |
| Owner / status | `/root` with inventory, recovery and source-map agents; **P001 ACTIVE** |
| Starting integration / branch | `b25035fce2cd1c038c567d34ea0797371947d95d`; `master` as explicitly requested |
| What changed | Added executable inventory/recovery/citation tools, 45 focused source-evidence tests, baseline and remote manifests, a documented runtime source map, and a phase-local hosted verification campaign |
| Actual local tests | All 45 focused tests passed; separate agents reproduced critical positive and negative cases; all 32 pinned citations matched exact source bytes |
| Current evidence limitation | Full parent-repository materialization and campaign results are pending; direct Git transport from the interactive environment is unavailable |
| Source/dependency changes | None; original code and all 149 dependency pins are preserved |
| Independent review | Cross-component tool reviews passed; full P001 verdict remains pending actual clean-checkout evidence |
| Next action | Run and inspect both hosted jobs, preserve reports and hashes, obtain independent phase acceptance, update all four P001 gate checkboxes from actual evidence |
| Next permitted phase | **Remain in P001** until complete acceptance; then P002 starts at `.gitmodules` URL/provenance repair and recursive dependency verification |

### 2026-10-31 — Historical parent-only acceptance (superseded by reopening below)

| Field | Record |
| --- | --- |
| Phase / state | **P001 PASSED; 1 / 96 phases complete** |
| Tested implementation / branch | `dc787de7d0aba7582981c8bf106fa0ff5fb1ef37`; `master` |
| What was completed | Source inventory/recovery tools, 32-citation runtime map, 45 focused tests, clean hosted verification on two distributions, complete compressed tracked-file archive, raw command logs, hashes and independent reviewer records |
| Actual results | Both [hosted jobs](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41237082207) passed. All 149 parent pins match; 27,288 current entries inventoried; 27,125 blobs per historical snapshot restored exactly; same tracked-file checksum reproduced from a separate network clone. |
| Independent acceptance | [Inventory/source reviewer](docs/compat/logic-pro/evidence/P001/reviews/inventory-and-source.json) and [recovery/campaign reviewer](docs/compat/logic-pro/evidence/P001/reviews/recovery-and-campaign.json); cross-component ownership prevents self-approval |
| Preserved failure | Inherited packaging CI fails before build because relative dependency URLs resolve under the fork account; actual logs are recorded. This is the next source-provenance task, not a concealed successful build. |
| Environment follow-up | Initial command-sandbox Git transport was unavailable; GitHub tools delivered the implementation and hosted results. An independently retrieved clean network clone then verified the full tracked-file artifact, and both hosted ZIPs were downloaded and hash-checked. |
| Remaining limitations | Child source contents/nested dependencies not retrieved; runtime and Logic execution not attempted; all later gates remain unqualified |
| Exact next action | **P002:** repair and verify `.gitmodules` URL/provenance, write the recursive dependency lock/verifier, retain existing pins, and demonstrate two independent recursive clones before P003 build work |
| Ledger consistency | Dashboard, P001 gates/detail, phase index, acceptance/evidence index and this handover agree; P002 remains NOT STARTED |

### 2026-10-31 — P001 reopened to complete the original recursive requirement

| Field | Record |
| --- | --- |
| Phase / state | **P001 REOPENED; 0 / 96 phases validly complete** |
| Starting revision / branch | `2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6`; integration remains on `master` |
| Proven false pass | The prior campaign recorded 149 parent gitlinks but inspected no child contents, leaving every nested dependency unknown. The original P001 implementation requirement explicitly includes every recursive submodule. The prior narrower acceptance is superseded. |
| Ownership | `/root` owns README, evidence and integration; `/root/recovery_tool` owns `prepare_sources.py` and its tests in a separate `p001-recursive-tool` worktree; `/root/inventory_tool` owns strict inventory/campaign checks, their tests and the P001 workflow in a separate `p001-strict-gate` worktree; `/root/source_map` independently audits completion and reproduces critical cases. |
| Work in progress | Obtain the exact pinned recursive sources using recorded upstream origins without changing source pins; make recursive incompleteness fail the P001 campaign; rerun preservation and classification checks and record independent review. |
| Exact next action | Complete source retrieval and inspect every descendant's committed tree and declarations; preserve full recursive tracked-file/license evidence and crosscheck it against the original gitlinks. |
| Next permitted phase | **Remain in P001.** P002 stays NOT STARTED until the full original P001 scope is accepted. |

### 2026-10-31 — P001 fully accepted after recursive completion

| Field | Record |
| --- | --- |
| Phase / state | **P001 PASSED; 1 / 96 phases complete; P002 NOT STARTED** |
| Tested implementation / branch | `4707a919ef304945f7685390a68429242657eb54`, tree `8fb4a8c4b7855d2dec827a9e4d6499cb113b3776`; `master` |
| What changed | Added exact-pin recursive acquisition and raw-byte checkout policy; strict physical inventory and mandatory notice/graph evidence; full pinned launch map and fixed citation coverage; final physical rescan and 109-test campaign |
| Actual verification | Both Ubuntu hosts in [run 41240503365](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41240503365) passed; 161 repositories, all160 gitlinks available, 293127 tracked entries, 292967 physical blobs, 754 notice candidates, 63 citations and two exact historical recoveries |
| Independent acceptance | `/root/source_map` approved recursive source/inventory/recovery/campaign and new launch-map additions; `/root/inventory_tool` approved retrieval and the full static source map/verifier. Explicit authorship exclusions and raw evidence hashes are retained in [acceptance.json](docs/compat/logic-pro/evidence/P001/acceptance.json). |
| Evidence durability | Raw per-host reports and logs, complete compressed tracked manifest, independent oracle/review assets, historical false acceptance and resolved local failures committed; [evidence-index.json](docs/compat/logic-pro/evidence/P001/evidence-index.json) records exact hashes |
| Remaining limitation | No P001 condition remains open. Ordinary fork-relative recursive checkout/packaging CI still fails and belongs to P002; no runtime or Logic execution is claimed. |
| Exact next action | **P002:** start at `.gitmodules` URL/provenance repair, retain original pins, implement recursive lock/verifier, then prove two independent ordinary recursive clones. P002 has not been started. |
| Ledger synchronization | Dashboard, phase index, all four P001 gates, final acceptance/evidence index and this handover agree. The tested implementation is frozen; this publication adds evidence and documentation only. |

### 2026-10-31 — Historical P002 Git-only qualification (superseded by independent rejection)

| Field | Record |
| --- | --- |
| Phase / state | **P002 READY FOR REVIEW; 1 / 96 phases formally PASSED. Remain in P002; P003 is not permitted.** |
| Author / tested implementation | `/root`; P002 exact clone candidate [`1bc6d20aa6d59c109475d44822946d3471d638cf`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/1bc6d20aa6d59c109475d44822946d3471d638cf), raw evidence and current-source citation re-audit [`8c061245bf7f0c545afac23937cd5a194175f884`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/8c061245bf7f0c545afac23937cd5a194175f884), and P001 independent campaign cross-check fix [`3043fdfe9ef4ce3c1a8485fcecbd42ebb355dde7`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/3043fdfe9ef4ce3c1a8485fcecbd42ebb355dde7), all on `master` |
| Source and exact submodule revisions | All **149 direct + 11 nested** Gitlink SHAs and Git trees are unchanged from the accepted P001 exact-pin provenance; [160-entry lock](docs/compat/logic-pro/submodules.lock.json) gives each full SHA, tree, owner and URL. No dependency source was modified. |
| Files / behavior changed | Repaired all 149 root `.gitmodules` URLs to independently retrieved public upstreams; added [strict recursive verifier](tools/compat/logic-pro/check_submodules.py), [fail-closed lock generator](tools/compat/logic-pro/make_submodule_lock.py), [real-Git fixtures](tests/compat/logic-pro/submodules/test_lock.py), [two-runner CI](.github/workflows/phase2-submodules.yml), [reproduction procedure](docs/compat/logic-pro/evidence/P002/REPRODUCE.md), raw evidence and a narrowly constrained historical P001 `.gitmodules` citation re-audit. |
| Commands and cases | On **separate** Ubuntu 22.04/24.04 VMs: anonymous `git -c credential.helper= clone --recurse-submodules --jobs 12 --branch master https://github.com/boop-bip80/MAC-OS-EMULATION.git`, `git submodule status --recursive`, `python3 -B tools/compat/logic-pro/check_submodules.py --repo … --lock … --output …`, and 14 focused real-Git fixtures on each host. Local P001 classification/campaign fixtures: **113 cases**; lock regeneration from P001 report checked for byte-identical output. See exact workflow and evidence files for flags and environments. |
| Expected / actual | **PASS / PASS** for both independent ordinary clones: 160 initialized matching pins, 161 repositories, 0 missing/mismatched/conflicted/dirty; both JSON verification reports and 160-line native statuses byte-identical. All 14 positive/negative tests passed on each host; wrong URL/HEAD/gitlink and absent nested children fail as expected. Lock regeneration also matches byte for byte. |
| Durable evidence and SHA-256 | [Successful CI run 41244857162](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41244857162); [P002 evidence index](docs/compat/logic-pro/evidence/P002/evidence-index.json) lists every raw log, source state and SHA-256. Full GitHub artifact ZIP digests: clone A `f1445e8cebbae37fc67e311d6f210de59c3462609de5f890b7976f3c375a3c32`, clone B `2e3db9ee17f0d15fb9b4bf354fdc632eaab25571513c3b123d24be6e7dc6ab2d`; all internal hashes validated; exact extracted text committed. |
| Continuity / open checks | The historical citation and separate current-tree cross-check each initially rejected the expected URL relocation. Both are now narrowly re-audited without changing any original P001 source record. [Final two-host hosted P001 run 41246526024](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41246526024) is **PASS/PASS**: 113 local/hosted fixture cases, 63 static citations, 160 recursive pins and 161 repositories per host; the archive hashes and raw small reports are in the [evidence index](docs/compat/logic-pro/evidence/P002/evidence-index.json). No Darling GUI build, Logic run or audio functionality is claimed at this phase. |
| Independent reviewer / verdict | **PENDING.** No agent/person other than the implementer has independently inspected and reproduced this P002 gate. Hosted machines provide independent clone evidence, not the separate source-and-evidence reviewer mandated by the README. |
| Exact next action | A distinct reviewer must verify the 160 immutable pins, compare both committed raw clone logs/native statuses/checksums, re-run lock generation and corruption cases, confirm the hosted P001 re-audit, and publish a dated identity/commit/tested-pin/verdict record in `docs/compat/logic-pro/evidence/P002/acceptance.json`. Only after a positive verdict update the four gates, dashboard, index, and handover to P002 **PASSED**, then open P003. |
| README ledger | Dashboard, P002 four technical checkboxes, evidence index and phase index are synchronized to **READY FOR REVIEW**; this entry satisfies the required end-of-session handover. |

### 2026-10-31 — Independent P002 rejection and stricter qualification in progress

| Field | Record |
| --- | --- |
| Phase / state | **P002 ACTIVE; 1 / 96 phases PASSED; remain in P002** |
| Starting revision / authors | `beb991101c944e4b0af3731633399a8b0e47c7ea`; `/root` integrates verifier/lock/tests, `/root/p002_lfs_fix` owns LFS tooling/provenance, `/root/p002_campaign_fix` owns campaign/workflow |
| Independent findings | `/root/p002_acceptance` found 44 unhydrated LFS library pointers and evidence durability gaps; `/root/p002_adversarial` reproduced hidden-dirty/filter/origin false passes and acquisition-policy failures. Prior green Git-only evidence is preserved but not accepted as completion. |
| Changed behavior / exact source | Complete physical/index verification without filter execution, explicit LFS SHA-256/size/mode and endpoint lock, immutable-SHA anonymous acquisition, complete fixture/transcript retention. All 160 original submodule commits/trees remain unchanged. |
| Checks actually completed | All 95 P002 fixtures and 113 P001 regression fixtures pass locally; independent draft attacks reject the false passes. Actual anonymous LFS retrieval and preliminary full-graph physical verification passed; final exact-SHA hosted qualification and acceptance remain mandatory. |
| Evidence / continuity | Original results and P001 acceptance remain historical records. Initial rejected reviews are preserved; all 32 original P001 continuity ZIP members have been losslessly archived locally and independently matched by hash/bytes, but the large archive upload is pending. It, corrected campaigns and final reviewer verdicts must be published and linked before acceptance. |
| Exact next action | Publish this candidate, run both independent Git+LFS campaigns and the P001 regression campaign, inspect every raw output/hash, then get separate reviewers' exact-commit verdicts. No author may self-approve. |
| P003 handover choice | Ubuntu 22.04 x86_64 + LLVM/Clang 14, CMake, Ninja, real GUI/audio and declared development dependencies; only a starting recipe. Freeze exact image/packages and qualify builds/probes in P003, after P002 passes. |
| Ledger synchronization | Dashboard, P002 checkboxes/detail, phase index and this handover record P002 ACTIVE. P003 remains NOT STARTED and prohibited pending acceptance. |

### 2026-10-31 — Correct the hosted Git LFS client behavior and complete evidence delivery

| Field | Record |
| --- | --- |
| Phase / state | **P002 ACTIVE; remain in P002; P003 NOT STARTED** |
| Starting implementation | `82c9ef60c492852cd89c3327c1885469e57993e8`; both hosted P002 jobs failed the one real Git LFS 3.8.1 checkout fixture; raw artifacts are retained |
| Corrected behavior | Remove inherited literal-pathspec mode only from trusted LFS acquisition so the client's own attribute selector works; retain every byte/hash/mode assertion and read-only safeguard |
| Actual tests | Official Git LFS 3.8.1: 96/96 P002 fixtures; 3.4.1: 43/43 LFS cases; independent 20-case red/green and six filename-safety cases. P001 at the prior candidate passed both hosted jobs plus independent 113+23 cases. |
| Evidence delivery | Store the exact previously verified archive as 50 hashed pieces; verify and assemble outside the checkout. Preserve original ZIP/member digests, all 32 raw reports, and the failed hosted campaign. |
| Ownership / independence | `/root/p002_lfs_fix` owns the LFS correction; `/root/p001_continuity_review` owns the multipart reader but does not approve it; `/root/p002_acceptance` reviews that reader and full gate; `/root/p002_adversarial` independently reproduces client/version and corruption cases; `/root` integrates on master |
| Exact next action | Publish this implementation with README and multipart evidence, inspect both new hosted campaigns, preserve all outputs, and obtain independent exact-SHA acceptance before updating the dashboard/gates/index to PASSED |

### 2026-10-31 — Publish the source correction while respecting the evidence authorization hold

| Field | Record |
| --- | --- |
| Phase / state | **P002 BLOCKED; 1 / 96 phases PASSED; remain in P002** |
| Published source revision | `78dff3235e95d90e43faa4af7de34d5f926c9d28`, tree `cd24ef64fd9f3ab73a3afbd90e33673ba0d161d8`, parent `82c9ef60c492852cd89c3327c1885469e57993e8`; exact API and local Git tree equality confirmed, no binary archive paths included |
| Source correction | Git LFS 3.8.1 internal selector works without weakening actual payload checks; all original 160 pins, schema-2 lock and LFS provenance are unchanged |
| Completed local checks | 96 P002 tests with official Git LFS 3.8.1, 113 P001 regressions and 33 reader tests; separate reviewers reproduced the native-client red/green behavior and archive lifecycle/content checks |
| Withheld publication | Exact 9,667,936-byte historical CI-report archive and all binary parts; explicit user authorization is required after a renewed safety-review rejection |
| Preserved evidence | Small source/test/failure records and the independent hold/disclosure reports are committed; incomplete uploaded blobs are not claimed as a published archive |
| Hosted work started, not yet passed | P002 run `41253918669` and P001 run `41253918642` both target exact `78dff323`; independent source/code review has started. Inspect completed raw results rather than assuming queued/running jobs succeeded |
| Next action | Complete review of the running source-only candidate's hosted P002/P001 gates, obtain explicit archive approval, and preserve complete final evidence before independent acceptance. No author may self-approve or bypass the hold |
| Permitted next phase | **Remain in P002; P003 prohibited until every gate and the evidence-publication requirement pass** |

### Required next-agent handover format

```text
YYYY-MM-DD — agent / phase / status
Starting root revision and relevant submodule revisions:
Files/functions changed and resulting behavior:
Tests actually run, exact commands, and fixture IDs:
Expected versus observed results:
Evidence paths/URLs and artifact hashes:
Independent reviewer and reproduced cases:
Gate conditions passed / still blocked:
Regressions reopened, if any:
Exact next file/function/test to work on:
Remain in phase P___ / next permitted phase P___:
Dashboard, phase entry, phase index, and README record updated:
```

## Research and implementation references

The source links in the findings table are immutable baseline permalinks. Documentation and product links below are living sources; record their access date and the applicable version whenever they inform a target manifest or gate. A linked project, issue, pull request, or API page is a research reference, not a certification that the required behavior already works here.

### Repository and upstream architecture

- [Audited repository revision](https://github.com/boop-bip80/MAC-OS-EMULATION/tree/3447ff5ab8e837ea54a13a506c60d34d77e2bd15) and [previous README preserved in history](https://github.com/boop-bip80/MAC-OS-EMULATION/blob/3447ff5ab8e837ea54a13a506c60d34d77e2bd15/README.md).
- [Darling upstream](https://github.com/darlinghq/darling), [build instructions](https://docs.darlinghq.org/build-instructions.html), [system-call emulation](https://docs.darlinghq.org/internals/basics/system-call-emulation.html), and [priority implementation areas](https://docs.darlinghq.org/contributing/high-priority-stuff.html).
- [Darling testsuite](https://github.com/darlinghq/darling-testsuite) for native-versus-Darling probe methodology.
- [Historical Logic issue](https://github.com/darlinghq/darling/issues/935), [ARM work PR 1753](https://github.com/darlinghq/darling/pull/1753), and [earlier ARM work PR 1450](https://github.com/darlinghq/darling/pull/1450). Verify each current status and actual code before selecting reusable patches.
- [VibeDarling](https://github.com/VibeDarling/darling) and its [framework dependency notes](https://github.com/VibeDarling/darling/blob/master/docs/framework-gap-tiering.md) as comparison material; independently test any adopted code.
- [Git submodule URL semantics](https://git-scm.com/docs/gitmodules). Relative submodule URLs are resolved relative to the parent repository's origin; a fork must verify its own resolved destinations.

### Logic versions, features, and native workflow contracts

- [Official Logic release notes](https://support.apple.com/en-us/109503), [product requirements](https://www.apple.com/logic-pro/), [one-time-purchase listing](https://apps.apple.com/us/app/logic-pro/id634148309?mt=12), and [Creator Studio listing](https://apps.apple.com/us/app/logic-pro-make-music/id1615087040?platform=mac).
- [Apple silicon feature restrictions](https://support.apple.com/en-us/120406) and [Audio Unit architecture compatibility](https://support.apple.com/en-ca/102082).
- [Audio Units in the Logic user guide](https://support.apple.com/en-by/guide/logicpro/lgcp22a0dab0/12.3/mac/15.6), [ARA integration](https://support.apple.com/en-ae/guide/logicpro/lgcp58ce340b/10.7/mac/11.0), and [spatial-audio overview](https://support.apple.com/en-euro/guide/logicpro/lgcp449359b0/12.3/mac/15.6). These versioned manual pages illustrate contracts; select the correct native-target manual during inventory rather than assuming an older page defines every current feature.

### Audio, timing, ABI, and execution-engine references

- [AudioStreamBasicDescription bytes per frame](https://developer.apple.com/documentation/coreaudiotypes/audiostreambasicdescription/mbytesperframe), [MIDI timestamp contract](https://developer.apple.com/documentation/coremidi/miditimestamp), [audio workgroups](https://developer.apple.com/documentation/audiotoolbox/understanding-audio-workgroups), and [audio performance analysis](https://developer.apple.com/documentation/audiotoolbox/analyzing-audio-performance-with-instruments).
- [Apple ARM64 ABI](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms), [Apple Intel ABI](https://developer.apple.com/documentation/xcode/writing-64-bit-intel-code-for-apple-platforms), and [architectural differences](https://developer.apple.com/documentation/apple-silicon/addressing-architectural-differences-in-your-macos-code).
- [Apple dyld fixup definitions](https://github.com/apple-oss-distributions/dyld/blob/main/include/mach-o/fixup-chains.h), [Clang pointer authentication](https://clang.llvm.org/docs/PointerAuthentication.html), and [Arm memory ordering](https://support.arm.com/documentation/102336/0100/Memory-ordering).
- [QEMU user-mode scope](https://www.qemu.org/docs/master/user/main.html), [multithreaded TCG design](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html), and [atomic operations](https://www.qemu.org/docs/master/devel/atomics.html) when evaluating a reusable engine. Pin the actual selected version; documentation for a development branch is not a dependency lock.
- [Core ML compute-unit options](https://developer.apple.com/documentation/coreml/mlcomputeunits), to investigate the actual model execution route without assuming either mandatory Neural Engine emulation or automatic CPU compatibility.

## Upstream attribution and licensing

This repository derives from Darling. Preserve upstream authorship, copyright notices, [LICENSE](LICENSE), [CONTRIBUTORS](CONTRIBUTORS.md), and the individual licenses of submodules and dependencies. The main project's existing license is GNU GPL version 3; individual components may use different licenses. This roadmap changes the project's README and implementation priorities, not the ownership or license of existing source. Consult the license files at the exact selected revisions when adding or redistributing components.


### 2026-10-31 — P001 fixture-result correction and six-task audit

| Field | Recorded result |
| --- | --- |
| Starting branch/head | `master` at `f7bd711013d3c41c3eee4ec76926bfe3a152cb46`; tested existing implementation `78dff3235e95d90e43faa4af7de34d5f926c9d28` |
| Preserved source | All 160 original gitlink commits/trees, `.gitmodules`, lock and LFS provenance remain unchanged |
| Defect repaired | P001 could accept a real failing expected-failure assertion; terminal plain-success validation now rejects masked outcomes and keeps nonzero exits fatal |
| Local verification | All 120 P001 fixtures pass. Independent reviewer reproduced 16 transcript cases, 11 campaign-verdict cases and killed the historical-predicate mutation; 45 focused tests pass |
| CI selection | P002 push/PR filters now also cover P001 runner/baseline-test changes; both phase workflows requalify this exact new source |
| Existing hosted results | Both P001 run 41253918642 and P002 run 41253918669 completed successfully at `78dff323`; actual raw results independently reviewed |
| Outstanding verification | Inspect both hosts for both new exact-commit campaigns and record scoped independent acceptance; current source is not yet claimed qualified |
| Retained approval boundary | Historical 9,667,936-byte raw report archive remains withheld, SHA-256 `5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d`; no replacement route or encoding is attempted |
| Next action | Publish this correction with its README record, inspect fresh raw results, and retain current scoped independent review/evidence |
| Permitted phase | **Remain in P001 until requalification passes; P002 remains blocked; P003 NOT STARTED** |


### 2026-10-31 — Exact-candidate technical qualification completed; final approvals pending

| Field | Recorded result |
| --- | --- |
| Published review work | Draft PR #1, `audit/p001-p002-qualification`; source correction `da1000be001711f80d6880eed9eeca916f6d0a23` |
| Actually tested implementation | PR merge `b628085a19bae2d467fd9549ec0767636423a90a`, tree `37761104d97e824a2567f91dff2dea391bb635dd`; identical to the source correction tree |
| Hosted verification | P001 run 41256694734: 120 tests per host, both PASS. P002 run 41256694572: 96 tests per host, both PASS |
| Independent review | Six dedicated tasks: original P001 audit, P002 audit, gate-tooling implementation, adversarial verdict review, exact-candidate CI/artifact review, and final acceptance/archive audit. Authors do not approve their own components |
| Source/payload result | All 160 original pins/trees unchanged; 161 repositories; 44 LFS payloads, 16,128,448 bytes; all required acquisition and corruption cases passed |
| Retained evidence | All 36 fresh P002 raw members, 28 fresh small P001 members, prior scoped reviews and current independent checks are in the PR. Full current manifests are losslessly mapped into the independently verified prepared archive |
| Actual blockers | Approval to update the default branch; explicit publication approval for the historical 9,667,936-byte archive, current 9,594,676-byte archive, and five supplemental historical reports listed in the publication hold; final durable readback and acceptance depend on those actions |
| Exact next action | Obtain the concrete approval above, publish/verify the reviewed bytes, then accept P001 followed by P002 and integrate the PR |
| Permitted phase | **Remain in P001 for its global evidence requirement; P002 technical gates verified but globally BLOCKED; P003 NOT STARTED** |

### 2026-11-01 — Approved complete evidence publication; P001 and P002 independently PASSED

The dated work logs above preserve the state when each campaign was evaluated; their earlier `BLOCKED`, incomplete publication and `0 / 96` statements are historical snapshots. The live dashboard, phase index, current P001/P002 entries and accepted evidence indexes record the latest status.

| Field | Final evidence and handover |
| --- | --- |
| Phase / state | **P001 PASSED, then P002 PASSED — 2 / 96 phases complete; P003 NOT STARTED** |
| Exact source qualification | Original reviewed source correction `da1000be001711f80d6880eed9eeca916f6d0a23`, original tested merge `b628085a19bae2d467fd9549ec0767636423a90a`, tree `37761104d97e824a2567f91dff2dea391bb635dd`. Post-publication source head `4339085c0a11ef2e33acc3259761ea2f8c8f1214`, tested merge `5da6086fde2cdf0dad36da1cf8d9f66909222e7a`, tree `1aeefbf454c4169063742487579199f467a0900c`; original implementation/dependency objects unchanged. |
| Authorized exact public evidence | Historical archive 9,667,936 B / SHA-256 `5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d` (32 original reports); current bundle 9,594,676 B / SHA-256 `8a614792dc1558ecc9584d9e00013f8a6c02cdc2dd7f00e570117e3b8e74e7a5` (68 original members); five supplemental historical reports 6,531,593 B. All original bytes published after explicit user approval. |
| Live two-host checks | [P001 41260649320](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649320) **120 PASS** per host, [P002 41260649124](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649124) **96 PASS** per host, [public archive readback 41260649315](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41260649315) **PASS** on both hosts. |
| Independent acceptance | [P001 continuity](docs/compat/logic-pro/evidence/P001/qualification-b628085/independent-p001-technical-confirmation.json), [P002 continuity](docs/compat/logic-pro/evidence/P002/qualification-b628085/independent-p002-technical-confirmation.json), [published objects](docs/compat/logic-pro/evidence/P002/qualification-b628085/supplemental-published-object-review.json), two [raw](docs/compat/logic-pro/evidence/P002/qualification-b628085/archive-readback-ubuntu-22.04.json) [readbacks](docs/compat/logic-pro/evidence/P002/qualification-b628085/archive-readback-ubuntu-24.04.json) and [independent final acceptance](docs/compat/logic-pro/evidence/P002/qualification-b628085/final-publication-acceptance.json). Prior independent rejections and prepublication audit preserved. |
| Verified integration | Explicit user approval covered final evidence publication and [PR #1](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/1). GitHub merged PR #1 on 2026-11-01 as `7a0f2e43dc58b35c63401656d6f38c6b0e1696ff` with parents `f7bd711` and `c64792c9`; the public `master` ref and merge tree `633186bf14854a37d2ddaa5a652af5df43b06229` were independently read back and exactly match the approved PR final tree. |
| Next implementation task | **P003:** freeze Ubuntu 22.04 x86_64, Clang 14, CMake/Ninja and package versions as an independently checked starting toolchain; build/install the real GUI/audio components, verify resolution and run Mach-O, Foundation and GUI probes. No Logic or GUI execution is claimed by P001/P002. |

### 2026-11-01 — P001/P002 additional adversarial guard hardening; requalification pending

This entry supersedes the previous section **only for the current new candidate's gate state**. The 120/96-test accepted campaigns and the original complete publication acceptance remain genuine, immutable historical evidence, not successful runs of the changed verifier. P001 must be independently accepted again **before** P002; P003 is blocked throughout.

| Field | Current candidate and required next evidence |
| --- | --- |
| Starting `master` revision | `e2799209ecb3e5e2a8e4c3652df53bb458fbfe74`; the earlier accepted PR #1 merge and evidence objects are preserved. |
| Proven failure reproduced | P002 `run_submodule_campaign.py` previously selected the first `Ran N tests` occurrence anywhere and only checked the last `OK`. A forged earlier positive count followed by the actual zero-test result could pass. An EOF-only fix could still accept a forged second final summary after a real zero-test result. P001 also permitted shrinking the genuine suite to one green test without a coverage floor. |
| Source/test repair | Use a shared fail-closed unittest transcript parser requiring exactly one final plain-OK summary and an equal number of **distinct verbose test announcements**. Require at least **120 P001** and **96 P002** tests, preserve nonzero exit handling, and add adversarial cases for both forged-summary orders, missing/duplicated announcements, reduced test coverage, skip/expected-failure, failure and truncation. |
| Local verification | **PASS on the prepublication candidate:** `python3 -B -m unittest discover -s tests/compat/logic-pro/baseline -p 'test_*.py' -v` ran **122 tests, plain OK, exit 0**; the analogous `-s tests/compat/logic-pro/submodules` command ran **97 tests, plain OK, exit 0**. Independent agents also replayed the stricter parser against four original raw hosted logs (120/120 P001, 96/96 P002). This is local fixture verification, not a substitute for fresh two-host exact-SHA campaigns. |
| Dependency continuity | No original 160 gitlink pins, 149 direct URLs, LFS records, Darling runtime source or historical evidence artifacts are intentionally changed by this hardening. Recheck complete physical clone/lock and raw reports on both hosts. |
| Fresh acceptance still required | Push the exact source/test/README candidate; run P001 Ubuntu 22.04/24.04 then P002 independent anonymous Git+LFS clones on both; inspect complete logs, counters, hashes, physical verification, and lock regeneration; preserve dated independent reviewers' exact-SHA verdict and update README/indexes. The old 120/96 runs cannot qualify a new SHA. |
| Current gate | **P001 REOPENED; P002 REOPENED/BLOCKED ON P001; P003 NOT STARTED. Current candidate: 0 / 96 accepted.** Preserve the historical passed verdict and do not silently claim current success. |

### 2026-11-01 — Hardened requalification accepted in order; handover to P003

This is the current implementation handover and supersedes the preceding *pending* candidate gate state. Prior historical rows remain accurate for the dates and exact commits they describe; none has been overwritten or retroactively altered.

| Field | Final evidence and next action |
| --- | --- |
| Current accepted count/state | **2 / 96; P001 PASSED first, then P002 PASSED. P003 NOT STARTED.** No Intel/ARM Logic compatibility or real GUI/audio execution milestone has passed. |
| Tested implementation | `5c3c77ee2dfff7330e335be4117f8d6269bf228b`, tree `bb9cc99f312406ce986473e77f833db7fe448456` on `master`; new publication is documentary evidence only. Five hardened-code commit paths: README, two gate scripts and their two tests. |
| Source/pin identity | 149 direct plus 11 nested original pinned gitlinks, 161 repositories, 44 independently verified LFS objects, 16,128,448 hydrated bytes; **zero** source pin, `.gitmodules`, lock, provenance or runtime code changes. Committed lock SHA-256 `1540d2552f36bd5ed29a640dbe12dfe0e37c618c02ed7fd1d59d4264a8ba5f1b`. |
| Fresh hosted source gates | [P001 41263623123](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41263623123) Ubuntu 22.04/24.04 both **SUCCESS / 122 tests per host / 160 recursive gitlinks / 63 citations / two 27,125-blob recoveries**, zero errors. |
| Fresh hosted dependency gates | [P002 41263623117](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41263623117) Ubuntu 22.04/24.04 both **SUCCESS / 97 tests per host / all 44 LFS payloads / 293,308 physical blobs / identical regenerated lock**, zero errors. |
| Artifact and report integrity | All four GitHub-hosted ZIP SHA-256 digests independently match downloaded bytes; ZIP CRC and individual internal SHA checks all pass. Raw small reports, reproducibility data, per-host report hashes and dated reviewer verdicts: [P001](docs/compat/logic-pro/evidence/P001/qualification-5c3c77e/requalification.json), [P002](docs/compat/logic-pro/evidence/P002/qualification-5c3c77e/requalification.json), [ordered acceptance](docs/compat/logic-pro/evidence/P002/qualification-5c3c77e/final-ordered-acceptance.json). The new large P001 tracked manifests are hash-bound to CI artifacts and must be regenerated or preserved separately before Actions retention expires; previously authorized full historical archives are unchanged and durable. |
| Independent acceptance | `/root/phase1` independently **PASSED P001 G1–G4 first**; `/root/phase2` independently **PASSED P002 G1–G4 after P001**; `/root/validation` reviewed the hardened parser and false-pass tests, `/root/ci` verified actual GitHub steps/commit/artifacts, `/root/security_runtime` checked deployment and raw host logs (not self-reviewing its parser work), `/root/docs_evidence` verified evidence/disclosure scope. Exact review identity and judgments are recorded in the machine-readable acceptance. |
| Remaining limitation and next action | **Begin P003** with Ubuntu 22.04 x86_64/Clang 14/CMake/Ninja package and image pinning, followed by a real GUI/audio build, installation, binary execution and required runtime probes. A green source/clone test alone does **not** demonstrate a working Logic Pro emulator. |

### 2026-11-01 — P003 implementation and qualification campaign started

| Field | Current implementation and next action |
| --- | --- |
| State | **P003 ACTIVE; 2 / 96 phases accepted.** P001/P002 accepted source and dependency qualification remains intact. |
| Starting source | `03e2880ba319d4b2b165c162cef4bffedb89d586`, unchanged recursive gitlinks and P002 lock. The next commit contains the P003 implementation and this progress record. |
| Six delegated owners | Toolchain `/root/p003_toolchain`; probes `/root/p003_probes`; packaging `/root/p003_packaging`; separate independent build, runtime and package reviewers. Root integrates/publishes and resolves findings. |
| Changed behavior | Optional installed Mach-O/Foundation/AppKit probes; frozen build recipe and two-host workflow; real-framework provenance and full install-tree verification; guarded isolated removal/reinstall; raw-evidence cross-build comparison. |
| Verified locally | 122 P001 and 97 P002 regression fixtures pass. The initial 50 P003 fixtures were expanded during independent review; fixed explicit rejection, raw-log identity, fresh HOME, daemon output and namespace lifecycle checks are included. Hosted exact-SHA fixture logs must pass before either full build. These checks do not establish runtime success. |
| Still required | Successful observed toolchain acquisition; two clean source builds/installs; all required real runtime and lifecycle cases on each; source/toolchain equality, enumerated output nondeterminism, durable raw evidence and exact-revision independent acceptance. |
| Exact next action | Run `.github/workflows/phase3-build.yml`, inspect the first actual failure, repair it without relaxing the probe, and repeat the affected qualification. |
| Permitted phase | **Remain in P003. P004 NOT STARTED.** |

### 2026-11-01 — P003 toolchain bootstrap failure repaired

The first published candidate `0f69cb5a` passed all hosted fixture suites (122/97/82) but failed HTTPS trust bootstrap before compilation in run [41269126730](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41269126730). Raw log/hash and the failure reason are retained in `docs/compat/logic-pro/evidence/P003/attempt-0f69cb5/`. The next candidate supplies ephemeral CA trust, pins the observed base digest and preserves writable lock ownership. No runtime result is claimed; **P003 ACTIVE, 2/96 accepted, P004 NOT STARTED**. Next action: rerun acquisition, then both clean build/install/reinstall and real probe campaigns.

### 2026-11-01 — P003 exact toolchain frozen; host-observation comparison repaired

The toolchain and hosted verifier fixtures succeeded at `354f7687`, but both independent builds stopped before compilation on an undifferentiated tool identity mismatch. The 511-package observed lock is committed, full failed reports retained, and independent freeze review recorded. The new comparison preserves raw observations while separating only dsymutil's runtime `Host CPU` value; compiler bytes, package versions and all static identity remain strict. **84 local P003 fixtures pass. P003 ACTIVE; 2/96 accepted; P004 NOT STARTED.** Next action: reproduce the fixed lock, inspect actual host differences, then complete both clean GUI builds and all install/runtime/lifecycle gates.

### 2026-11-01 — P003 reaches compilation; Objective-C build configuration repaired

Both clean hosts at `00a8df3` passed the exact source/toolchain checks and failed at the same real objc4 Release assertion. Full original build artifacts and independent CPU-observation review are preserved in `docs/compat/logic-pro/evidence/P003/attempt-00a8df3/`. The next candidate corrects only the Objective-C child directory's build-type definition, keeps all 160 pins unchanged, enables runtime placeholder diagnostics, and adds an independently authored installed-archive replay without source/build mounts. The independent reviewers reproduced the CMake failure/repair, archive handling, runtime oracles and aggregate rejection cases. The fixture coverage floor is now 120. **P003 ACTIVE; 2/96 accepted; P004 NOT STARTED.** Required next action: full hosted qualification of the repaired candidate, followed by exact-SHA artifact review; no installation, GUI, audio or Logic compatibility success is claimed yet.

### 2026-11-01 — Current source-baseline citation regression reopened before further build work

| Field | Current evidence and handover |
| --- | --- |
| State | **P001 REOPENED; P002 BLOCKED; P003 BLOCKED; 0/96 accepted for this changed candidate.** Historical accepted revisions remain valid in their recorded scope. |
| Tested source | `d89920b447658cfa01e9645864f2315cad4e386a`; all 160 dependency pins unchanged. |
| Actual prior-phase failure | P001 run `41271772655`: both hosts passed 122 fixtures, recursive inventory and recovery, but five current CMake citations failed; 58/63 verified. Official hosted artifacts/job links and exact hashes are indexed in `docs/compat/logic-pro/evidence/P001/p003-source-reaudit/README.md`. Automatic review rejected raw-bundle republication into public Git history; that bundle is not included in this correction. |
| Correction | Explicit source re-audit preserves original assertions and permits only the reviewed CMake additions, with exact current blob/excerpt and independent inventory binding. No broad changed-source waiver. |
| P003 observation retained | Run `41271772667` cleared the objc4 Release assertion and reached dyld linkage on both independent builds. Both then failed `chained binds not implemented yet` for a relative lookup table emitted into static libunwind. The unmerged build repair is held until predecessor acceptance is restored. |
| Ownership and review | `/root/p003_independent_package_review` authors the P001 correction; `/root/p003_independent_build_review` independently reviews it; `/root` integrates evidence and ledger. |
| Exact next action | Run and independently accept the corrected P001 source campaign, then P002 clone/lock regressions; resume P003 only after ordered acceptance. P004 remains NOT STARTED. |

### 2026-11-01 — Ordered predecessor acceptance restored; P003 unwind repair integrated

| Field | Current evidence and handover |
| --- | --- |
| Accepted source | `b2c0d4893cace4ddbacf9f7c29503990b07491cd`, tree `d717988463e25d8e5828f77d2eb17411561188ab`; all 160 pins and the dependency lock unchanged. |
| Ordered verdict | P001 accepted by `/root/p003_independent_build_review` at 05:08:55.615852 UTC; P002 accepted afterward by `/root/p003_independent_package_review` at 05:11:26.854450 UTC. **2/96 accepted; P003 ACTIVE; P004 NOT STARTED.** |
| Actual predecessor results | P001 run `41275067092`: both hosts 130 tests, 63 citations, full recursive inventory and historical recovery. P002 run `41275067090`: both hosts 97 tests, anonymous acquisition, 44 verified LFS objects and identical lock regeneration. Original artifact URLs/hashes and essential reviewer records are preserved above. |
| P003 implementation | Scoped static-unwind compiler representation repair; exact Clang 14 control/repaired object and 51-input native regression; full-history real current-source audit before compile; strict aggregate evidence binding. Original dyld chained fixups and all child pins remain intact. |
| Independent code review | Helper/proof and precompile wiring reviewed across authorship boundaries. The full installed-runtime campaign is still unaccepted and must execute on the new exact candidate. |
| Publication scope | Source, tests and concise progress/evidence references only. Automatic review rejected republishing new raw bundles to public Git history; original Actions artifacts remain available under recorded retention. No rejected payload is included indirectly. |
| Exact next action | Reproduce the complete two-host P003 workflow, inspect actual failures or successful artifacts, and require independent acceptance of all four gates. Remain in P003. |

### 2026-11-01 — Both complete P003 builds/installations qualify; real launchd startup blocks runtime

| Field | Current evidence and exact handover |
| --- | --- |
| State | **2/96 accepted, P001 PASSED, then P002 PASSED at exact `2409473d`; P003 ACTIVE with zero of four gates fully accepted; P004 NOT STARTED.** |
| Ordered predecessor acceptance | [P001 41276794767](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794767): 130 real fixtures, all 63 citations, all 161 source trees; independent reviewer4 **ACCEPTED** at 05:30:32 UTC. [P002 41276794763](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794763): 97 fixtures, identical lock, 160 pins, 44 hydrated LFS objects; reviewer6 **PASSED_AFTER_P001** at 05:31:01 UTC after 1,009 checks. |
| Tested P003 source | [`2409473d37b951a0dd44346f128edb2112de6b25`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/2409473d37b951a0dd44346f128edb2112de6b25), tree `24d9386e02abc6b29a5fd18f786833ea3986e34e`; all 160 original gitlinks and Clang 14 / Ubuntu toolchain lock unchanged. |
| Actual hosted result | [Run 41276794652](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41276794652): 130/97/136 hosted verifier suites, required precompile proofs, two complete **16,590-step** compilations/links, both 11,941-entry first installs, seven-framework provenance and native ELF checks passed. First Mach-O guest operation failed on both hosts after 15 seconds because `shellspawn.sock` was absent. Shutdown passed; no further real probes, reinstall or independent package-only replay ran. Reviewer4 verdict **FAILED_RUNTIME_STARTUP**, 06:02:13 UTC. |
| Original evidence | [P003 evidence index](docs/compat/logic-pro/evidence/P003/README.md), original Actions artifact IDs 13072621775 (A), 13071818748 (B) and 13071716180 (frozen toolchain), each with byte count, SHA-256 and provenance. No rejected raw ZIP/log bundle republished into Git. |
| Newly corrected independent package defect | `src/startup/mldr/darling.conf.in` now specifies the actual `usr/libexec/darling/mldr` install path for all handlers; real CMake File-API checks confirm the mapped target, preserving the original Mach-O magic and handler flags. This binfmt mismatch is distinct from the not-yet-diagnosed initial launchd startup failure. |
| Next candidate's diagnostic hardening | `run_build_probes.py` observes the actual startup process tree at bounded intervals and preserves hashed raw samples. The failure trap in `build-p003.sh` preserves the actual first installed package on failure. Both additions preserve the failing exit and all original assertions; five new startup tests and two package tests raise P003 fixture floor to **143**. Hosted acceptance of these new changes is pending. |
| Exact next action | Publish source/tests/status, run the new exact-SHA full CI campaign, diagnose retained live process/package bytes, repair the actual launchd/shellspawn cause, repeat both full builds and both install/reinstall runtime campaigns plus archive-only fresh-host replay, explain all output nondeterminism and obtain non-author independent acceptance. **Do not advance to P004.** |

### 2026-11-01 — P003 native thread-entry SIGSEGV independently localized; guarded source repair pending full qualification

This handover supersedes the earlier *unknown startup cause*, not the immutable historic failure results. The accepted count remains **2 / 96**, P003 **ACTIVE**, and P004 **NOT STARTED**.

| Field | Verified evidence and pending next gate |
| --- | --- |
| Exact original candidate | [`0f7f34f`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/0f7f34f32de7a2b403df3d38a656b979a1a3ee7c), [P003 run 41281586902](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41281586902): **130 / 97 / 143** suites, identical 511-package frozen toolchain, two 16,590-step GUI builds, both 11,941-entry first installs and static framework/native-owner checks passed. Both actual Mach-O starts failed; Foundation, GUI, reinstall and package-only runtime cases were skipped. Independent G1 PASS; G2 live loading NOT VERIFIED; G3 FAIL; G4 NOT EXECUTED. |
| Predecessor continuity | [P001 exact `0f7f34f`, run 41281586753](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41281586753) independently accepted on two hosts. Latest independently accepted P002 is the earlier `2409473d` candidate; fresh P001 **then** P002 must qualify the forthcoming repaired SHA. P002 workflow trigger coverage now includes production CMake, source, toolchain, build scripts and tests so this requalification runs at the new exact SHA. |
| Frozen failure and replay | [Diagnostic `bc57e881`, run 41284477835](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41284477835) confirmed guest launchd Linux SIGSEGV 11/wait 139. [Diagnostic `6f2b272e`, run 41285728755](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41285728755) passed all **24** real-kernel/synthetic diagnostic tests and preserved actual first SIGSEGV register/maps/stack evidence, but its later fault storm exceeded safe capture limits; **COLLECTION_ERROR is not acceptance**. Exact artifact sizes/SHA-256 and independent analysis are in [P003 evidence](docs/compat/logic-pro/evidence/P003/README.md). |
| Independently confirmed cause | Exact failed native `mldr` binary SHA-256 `e1c37512cdd756609f00c14885ee5c807a78808abd228a1ae679f0a54bfa60d2` loads entry-point into RBP, then executes `xor rbp,rbp` and `jmp rbp`. Two observed launchd workers instead reach address zero despite valid callbacks. Separate reviewers independently disassembled the archived ELF and resolved the first and secondary fault locations. |
| Proposed production correction | In root-owned `src/startup/mldr/elfcalls/threads.c`, copy entry-point into explicitly clobbered R11 **before** changing RBP/RSP, then branch via R11. Preserve six ABI argument registers, 16-byte stack alignment and synthetic zero return address. The new real-source native compiler regression replays normal/workqueue paths, including forced RBP operand allocation, and reproduces the historical SIGSEGV as a negative control. Both test methods pass under byte-identical frozen Clang 14 and GCC, bringing the **P003 fixture floor to 145**; this does not prove installed runtime success. |
| Publication and acceptance still required | Independently approve exact changed source/workflow/test/docs, publish to `master`, pass both fresh predecessor campaigns in order and **both** complete clean P003 build/install/probe/reinstall campaigns. Require all seven live intended framework image resolutions, Mach-O/Foundation/visible-GUI asserted results, full lifecycle teardown, independent package-only fresh-host runtime, enumerated nondeterminism, original raw evidence and explicit non-author G1–G4 acceptance before checking any P003 completion box. |

### 2026-11-01 — P003 real GUI authorization failure and reached libxpc stubs; repaired candidate pending

**P003 is still ACTIVE and NOT ACCEPTED. P001 and then P002 independently passed the exact earlier `bdff28ac` source, but the new source candidate must requalify them. P004 is NOT STARTED.**

| Evidence | Actual result |
| --- | --- |
| [Full P003 run 41286874621](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41286874621), exact `bdff28ac` | **130 / 97 / 145** verifier suites passed, then both fresh hosts completed **16,590/16,590** real builds and first installations. All eight pre-window cases (Mach-O, Foundation and invalid-GUI arguments) passed, seven intended frameworks were loaded, and shutdown released each namespace. Both GUI processes exited **1** on X11 authorization before showing a visible window. Both jobs failed; uninstall/reinstall and independent archive-only runtime were skipped. Original A/B artifact IDs **13076458249 / 13076323975** and exact SHA-256 hashes are indexed under [P003 evidence](docs/compat/logic-pro/evidence/P003/README.md). |
| Independent original-archive review | Actual installed native `mldr` instructions confirm the prior thread-entry crash is fixed. Exhaustive raw-log inspection found exactly two *reached* `libxpc stub called:` transaction placeholders that the original scanner mistakenly reported as zero. This invalidates G3 even if the GUI works. G4 was not executed. |
| [Installed-package-only X11 differential replay 41290683823](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41290683823), diagnostic commit [`2ac8d813`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/2ac8d813ed7e3e605fd7944d5d6a5a89c7290819) | The exact retained `bdff28ac` package reproduced the authenticated-X11 failure. In a disposable **network-disabled, no-TCP** Xvfb server with private `-ac`, all ten real Mach-O/Foundation/visible-GUI/XTest/pixel/shutdown cases passed, including distinct nonce-bound before/after XWD+PNG images and the seven loaded framework paths. Two independent readers verified the raw pixels and inputs. The same two libxpc stubs remained present; this is **not Phase 3 acceptance**. |
| Next production candidate (pending hosted gates) | A root-owned CMake source replacement preserves the frozen pinned `libxpc` gitlink and every unrelated API, while forwarding `xpc_transaction_begin/end` to liblaunch's actual serialized transaction lifecycle. The installed Foundation probe now requires live mixed `xpc`/`vproc` counter changes **+1, +2, +1, 0**, with exact nonce output. Both producer and independent scanner reject the previously missed lowercase stubs. The private GUI display change preserves all real external input, screenshot, exit and teardown tests. Native/CMake/adversarial regressions raise the local P003 fixture floor to **151**; no hosted passing claim is made. |

**Next gate:** publish the independently reviewed candidate, rerun P001 then P002 on its exact SHA, complete *both* P003 clean build/install/runtime/uninstall/reinstall campaigns, pass fresh package-only independent runtime and nondeterminism comparison, inspect original raw artifacts and require explicit non-author acceptance of G1–G4. Do not mark any P003 box or begin P004 before that result.

### 2026-11-01 — P003 ACCEPTED after two complete builds, five installed runtime campaigns and non-author G1–G4 review

This is the **current status**, superseding the earlier candidate's pending next gate above without altering any historical failed result. **3 / 96 phases independently PASSED; P004 NOT STARTED.** Exact tested source [`89c6c9d85aba6ed1662035e6366298c92ef9c970`](https://github.com/boop-bip80/MAC-OS-EMULATION/commit/89c6c9d85aba6ed1662035e6366298c92ef9c970), tree `1ce359808d725efd07ec2b51548760893a7cf5a5`. The [P003 workflow 41292343355](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41292343355) finished **SUCCESS** with all jobs green; the original uploaded ZIPs, member hashes, source review and final gate verdicts are indexed in [accepted P003 evidence](docs/compat/logic-pro/evidence/P003/README.md).

| Original gate / review | Verified accepted result |
| --- | --- |
| Required predecessors | [P001 run 41292343282](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41292343282) independently accepted **09:23:58 UTC**: 130 fixtures, 63 citations, 293,593 recursive entries. [P002 run 41292343322](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41292343322) independently accepted **after P001 at 09:25:39 UTC**: 97 fixtures, all 160 pins and 44 LFS objects, 1,009 original-evidence checks. |
| **G1 PASS** | Both independent hosts used the same Ubuntu 22.04/Clang 14 frozen image and 511-package lock, completed **all 16,590 build steps**, and installed **11,941 entries** per cycle. Cross-host outputs were **not byte-identical**: all 138 differing installed files/**6,447 bytes** have exact A/B hashes and a separately reproduced zero-unclassified-byte explanation. The unarchived intermediate linker's differing hashes/build banners are explicitly enumerated, not asserted binary-normalized. |
| **G2 PASS** | Real installed Mach-O headers, owners, aliases, framework install names and dependencies verified for all seven required frameworks; all five actual runtimes loaded them. Four native ELF entries, 21 wrapped library resolutions and the 48-node startup dependency closure were independently reviewed; no developer-stub substitution. |
| **G3 PASS** | **Five real installed executions, 10 cases each, 50 total**, with 75 expected primary command exits: independently calculated Mach-O results, Foundation objects/data, exact nonce-bound mixed XPC/liblaunch counter deltas **1,2,1,0**, **zero reached stubs**, visible GUI/XTest input and 400×262 before/after screenshot/color assertions. Independent review matched all **1,048,000 PNG pixels** to their original XWD files. |
| **G4 PASS** | Both original hosts removed **11,941** entries, confirmed isolated install prefixes absent, reinstalled to fresh ownership and separate runtime state, reran every case and cleaned their server mount namespaces. A fifth, separate host ran the verified installed package without source/build mounts; all ten cases and cleanup passed. |
| Final non-author sign-off | Package G1/G2/G4 accepted **10:06:15 UTC**; runtime G3/G4 accepted **10:09:31 UTC**; combined source/build/runtime independent G1–G4 **PASSED at 10:13:57 UTC**. The [dated JSON review records](docs/compat/logic-pro/evidence/P003/acceptance-89c6c9d.json) and 138-path table preserve exact identities, original artifact SHA-256 and reviewer authorship boundaries. |

**P004 handover:** Retain the exact source/toolchain lock, real GUI/audio install recipe, previous native mldr and libxpc repairs, no-TCP private X11 fixture, all 151 P003 verifier regressions and original five-campaign acceptance artifacts. P004 may implement stronger CI gates in its own scope. **No claim is made here about running Logic Pro or completing any later phase.**


### 2026-11-03 — Reopen exact-source predecessor and prepare P004 without claiming acceptance

The newest upstream merge `5e08de551ae51ea8415bfad875ea95f0e44cda51` added a new CMake compiler-flag block after P003 was independently accepted at `89c6c9d`. Actual hosted P001 run [41559900736](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41559900736) failed three current-source citations on both supported Ubuntu hosts; P003 run [41559900724](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41559900724) likewise failed source qualification and skipped remaining runtime gates. P002 run [41559900733](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41559900733) passed its dependency jobs, but this cannot substitute for the required P001→P002→P003 independent source-bound acceptance sequence.

Draft [PR #3](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/3) scopes the exact upstream CMake bytes while preserving historical immutable P001/P003 source identities and tamper rejection. Independent source-level review is conditional; hosted P001/P002 jobs [41684499371](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41684499371) and [41684499386](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41684499386) were queued at this handover, and new P003 installed runtime requalification remains mandatory.

P004 implementation components are intentionally isolated in draft branches: [fault harness PR #2](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/2), [evidence PR #4](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/4), [source-equivalence PR #5](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/5), [CI PR #6](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/6) and [strict gate-engine PR #7](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/7). The separate [legacy CI safeguard PR #8](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/8) retains full PR/master/release-tag packaging while preventing duplicate feature-branch pushes and canceling only superseded PR runs; the existing old CI queue still needs to drain. These artifacts are implementation candidates, not finished phase evidence. Final P004 acceptance still requires complete live hosted source/build/install/runtime/evidence jobs, wrong-result/crash/hang/callback/executable/fake-success rejection, missing-runner/fixture blocking, original artifact hashes and separate non-author G1–G4 equivalent review of all four P004 checkboxes. Logic Pro has not been run on Linux.

**Next permitted activity:** repair and independently accept P001, then P002 then P003 on exact new source; only then activate P004 acceptance work, publish original evidence and request independent review. No later phase may be marked PASSED from suite counts, a successful package build, or a self-authored receipt.


### 2026-11-03 — Exact master qualification started; first hosted P001 defect corrected

The six-agent Phase 4 qualification candidate was atomically integrated in [PR #9](https://github.com/boop-bip80/MAC-OS-EMULATION/pull/9) and non-force fast-forwarded to `master` at reviewed source `d8a812bf86d7d0ff512028bf80f1c813b0ac0fb4`; no native emulator implementation or submodule pin was changed in this integration. Its 21-file source/test/CI/documentation commit remains an **implementation candidate, not P004 acceptance**. GitHub created exact-master-push P001 [41690944782](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41690944782), P002 [41690944787](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41690944787), P003 [41690944848](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41690944848), and P004 [41690944846](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41690944846). These were queued at the handover; prior PR runs using GitHub's synthetic merge revision are **diagnostics only** and cannot substitute for independently reviewed master-push predecessor evidence.

A genuine hosted P001 regression signal surfaced in upstream re-audit [PR #3 run 41684499371](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41684499371), Ubuntu 24.04 job `126086551395`: all **63 current-source citations were verified**, but 1 of 135 unit tests errored while locating the repository root. `test_p004_actual_root_cmake_is_only_approved_upstream_delta` incorrectly derived the project directory as `SCRIPT.parents[4]` from `<repo>/tools/compat/logic-pro/verify_classifications.py`, which instead selects the parent of the checkout. This subsequent source-fix commit changes only that test lookup to `SCRIPT.parents[3]` and retains the real CMake byte-equality/tamper assertions. The independent reviewer checked this exact path fix. **The master revision carrying this correction is a new implementation SHA; all required P001→P002→P003→P004 proof must be rerun against it.** Old A or PR-merge runs cannot be relabeled as passing new A'.

GitHub Actions' queue has been busy with six obsolete feature-branch Darling packaging runs from the unchanged previous baseline. The legacy workflow now keeps the three packaging jobs for every PR, master push and tag, while suppressing duplicate feature-branch pushes and canceling only superseded PR attempts. No existing running jobs were forcibly canceled. P004 remains **IN DEVELOPMENT / NOT PASSED** until hosted native install/runtime probes, fault-injection negatives, original ZIP/hash provenance, documentation-only evidence publication and separate non-author sign-off all succeed.


### 2026-11-03 — Prevent skipped P003 and superseded exact-SHA acceptance jobs

The one-line P001 root-path repair was published at implementation `7774ad2511372c19602cd0bb4355deb4c14a19da`, but its corresponding master-push run did not start P003: the legacy P003 workflow restricted `push.paths` to a fixed set of files, accidentally omitting baseline test files whose behavior P003 itself executes. Thus this revision could **not** satisfy the P004 predecessor gate regardless of P001/P002 results; old revision evidence remains historical.

The immediately succeeding CI-hardening revision removes source-path allowlists from P001, P002 and P003 qualification workflows so that every `master` implementation revision receives exact-source predecessor runs (all original testing steps remain intact). P004 was already unfiltered. All four workflows also assign a unique concurrency group to **each master-push run**, preventing GitHub from silently displacing pending acceptance runs when a later commit arrives; superseded PR diagnostics alone may be canceled by PR number. This intentionally increases CI work on documentation-only master pushes but prioritizes qualification integrity. A reviewer independently compared the modified workflow job bodies byte-for-byte with their originals.

**Acceptance reset:** the latest master revision containing this trigger/concurrency correction is the only current P004 implementation candidate; P001→P002→P003 and the P004 source/build/runtime/evidence chain require new hosted results for that exact full SHA, original artifact verification and separate independent sign-off. Neither the older `d8a812b` candidate nor the `7774ad2` path-fix candidate can be used as an accepted current revision. **P004 remains NOT PASSED.**

### 2026-11-05 — P002 five-wave current-source requalification started

`/root` inspected exact master `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`.
The latest upstream source advances 13 direct gitlinks while the P002 lock
still describes the original graph. Actual local baseline tests fail: P002
97 tests / one error; P001 151 tests / six failures and one error. Independent
wave-one audits cover the dependency verifier, LFS/campaign and prerequisite
acceptance. [Work, ownership and evidence](docs/compat/logic-pro/evidence/P002/requalification-20261105/README.md)
are published incrementally. No pin is reverted and no gate is relaxed.
**Next:** explicitly review and record the upstream source changes, repair the
current lock/provenance and prerequisite gates, rerun independent exact-source
campaigns, then obtain non-author P001 followed by P002 acceptance. Remain in
P002; P003/P004 are not reaccepted by this work.

#### 2026-11-05 P002 wave-one evidence checkpoint

The source audit identifies **14 recursive pin changes (13 direct plus nested
indium)**. Both original hosted P002 jobs at `c7ef7fe4` failed lock regeneration;
all 18 original raw members and verified artifact hashes are preserved. A
separate P001-style anonymous source inspection retrieved every current pinned
object (160 recursive gitlinks); its complete original raw report is archived.
[Wave-one evidence and upstream diff review](docs/compat/logic-pro/evidence/P002/requalification-20261105/README.md)
record these observations without claiming P002 acceptance. Continue the
current-source provenance and prerequisite repairs; remain in P002.

#### 2026-11-05 P002 prerequisite fixture repair

The predecessor suite's source-publication negatives now use a real Git commit
as an invalid dependency change instead of the all-zero object ID that Git
correctly rejects before the verifier runs. Five rejection checks now identify
the actual offending history path. A separate never-created tested-source
pointer case preserves direct missing-pointer coverage in addition to deletion
rejection. The focused source-equivalence suite passes **17 tests**, with no
production gate changed and no assertions skipped. [Raw focused results](docs/compat/logic-pro/evidence/P002/requalification-20261105/source-equivalence-repair-tests.log)
are retained. Remaining failures are the actual current-source provenance and
citation changes. This is prerequisite repair inside the requested P002 work;
P004 remains unaccepted. Independent review and exact-source P001/P002
campaigns are still required.

#### 2026-11-05 P002 payload availability and current gate status

A fresh anonymous Swift-only clone retrieved and physically verified all
**44 locked LFS objects / 16,128,448 bytes**, with no payload cache or credentials.
[Original reports and scope](docs/compat/logic-pro/evidence/P002/requalification-20261105/diagnostic-lfs-availability.manifest.json)
are retained as a supplemental check, not a replacement for the two complete
P002 campaigns. The phase index, current P002 status and four acceptance
checkboxes now explicitly show that current-source acceptance is pending.
Historical passes remain in their original dated records. Current work remains
reviewed provenance, prerequisite repair and independent exact-source qualification.

#### 2026-11-06 P002 wave-two reviewed-source lock implementation

`/root/wave2_lock_repair` added the shared
[source-provenance loader](tools/compat/logic-pro/source_provenance.py) and updated
[lock regeneration](tools/compat/logic-pro/make_submodule_lock.py) to consume the
archived `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a` inspection. Frozen SHA-256
digests bind the original P001 report, current compressed/raw report, archive
manifest and reviewed update list. The original retrieval anchor `4707a919`
and historical accepted-lock anchor `89c6c9d` remain distinct and immutable.
The review must cover exactly all 14 old/new recursive pin and tree changes,
including each immediate parent and public URL; missing, extra, duplicate,
stale or altered evidence fails. Supplying original P001 evidence against
current pins continues to fail. The current lock retains all 160 paths,
149 direct/11 nested relationships, acquisition URLs and all 44 LFS records;
its provenance explicitly describes source review, not phase acceptance.

**Author verification:** `python3 -B -m unittest discover -s
tests/compat/logic-pro/submodules -v` passed **110 tests** (27.801 seconds),
including the existing physical/index/URL/LFS corruption fixtures, current
lock byte equality, historical-evidence rejection and new provenance
negatives. The CLI also regenerates the same bytes from an unrelated working
directory. No dependency source or gitlink was edited. **Next:** integrate
the prerequisite and campaign repairs, run both independent ordinary-clone
campaigns, and obtain ordered non-author P001 then P002 review. P002 remains
**ACTIVE, NOT ACCEPTED**; no later phase is reaccepted by this change.


### 2026-11-06 P002 wave 2: historical and current citation chains

The P001 verifier now retains all 63 original citation objects and validates a
separate complete current-source audit at reviewed source anchor
`c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`. Historical and current gitlink chains
are checked independently; current child HEADs, source blobs, inclusive excerpts,
and every original assertion (or the previously reviewed URL rewrite) must agree.
The staged-install root CMake guard is allowed only as its exact reviewed bytes,
while the original P003/P004 predecessor checks remain mandatory. Current evidence
includes each owner commit and chain for comparison with the current inventory.

Source preparation explicitly fetches each frozen historical citation hop even
when it is already cached, verifies the original chain and blob, and leaves the
current checkout HEAD unchanged. Fresh shallow retrieval therefore does not
silently depend on objects from an earlier checkout. Local verification passed
33 classifier tests and 23 retrieval tests, including altered pins, chains,
source bytes, excerpt hashes, assertions, missing historical objects, and exact
CMake predecessor checks. Independent source-object checks verified all 63
historical and all 63 current citations. This is prerequisite repair evidence;
it does not accept P001/P002 or advance P003/P004 qualification.


### 2026-11-06 P002 wave 2: independently reproducible historical audit

Historical-only citation verification does not require current-anchor objects in
the checkout. The explicit current audit still resolves and checks the exact
reviewed anchor before accepting any current citation. A focused regression
covers an unavailable current anchor: historical verification passes from its
frozen objects, while current verification fails. The classifier suite now has
34 passing tests; this remains local prerequisite evidence only.

#### 2026-11-06 P001 wave-two aggregate prerequisite integration

The integrated prerequisite preserves the original recovery oracle and original
63 citation objects while separately checking the reviewed current graph. The
aggregate binds all 160 current pins, trees, parents and origins to frozen source
provenance, every historical/current citation to its own complete parent chain,
and current cited blobs to the actual physical inventory. Missing or duplicate
citations, rewritten historical evidence and jointly forged report/metadata
chains fail. The runner also compares the original manifest against committed
`c7ef7fe4` bytes before accepting any current-source supplement.

**Author validation:** the complete integrated P001 suite passed **174 tests**,
including 62 aggregate-gate tests. The raw local test transcript is retained in
the [five-wave evidence directory](docs/compat/logic-pro/evidence/P002/requalification-20261105/README.md).
Worker commits `c2db2b24` and `550af5d1` supplied the separately reviewed source
chains and explicit shallow historical-object acquisition; `/root` implemented
the aggregate crosscheck. This is prerequisite implementation, not current phase
acceptance. P001/P002 remain pending exact-source hosted campaigns and ordered
non-author review; P003/P004 are not reaccepted.

#### 2026-11-06 P002 wave-two object integrity repair

A real corrupt loose Git object reproduced a false pass through the restricted
CRLF checkout waiver. Blob reads now verify the canonical Git object hash before
trusting bytes. Four integrity fixtures and all 18 campaign fixtures pass; the
campaign explicitly requests the parallel lock repair's `reviewed-current`
provenance mode and still requires byte-identical regeneration.
The full 102-test suite has one existing stale-provenance error before that
parallel repair is integrated; the original failure transcript is retained.
[Reproducer and original before/after evidence](docs/compat/logic-pro/evidence/P002/requalification-20261105/object-integrity/README.md)
are retained. Integrate the lock repair, run exact-source hosted campaigns, and
obtain independent review. This handover does not accept P001 or P002.

#### 2026-11-06 P002 complete repair candidate published for qualification

All wave-two code is published at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`
and advanced to `master` without force. Combined author suites passed **174 P001
and 115 P002 tests**, with the unchanged full negative-case requirements.
[The exact raw local transcripts and tested-code hashes](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave2-complete-tests.json)
are retained. Three independent reviewers are examining the lock/provenance,
P001 historical/current continuity and corruption/campaign changes. Hosted
P001 and P002 workflows now qualify this exact push. **P002 remains ACTIVE,
NOT ACCEPTED; P001 predecessor reacceptance and two complete ordinary clones
are still required.** Evidence-only publication may follow the tested source;
any further production fix requires fresh campaigns at its own exact SHA.

#### 2026-11-06 current-versus-historical dashboard synchronization

The live dashboard, phase index, P001 and P002 entries consistently retain pending
current acceptance rather than inheriting checked boxes or the historical 3/96
count. Historical full-scope P001/P002/P003 verdicts remain unmodified in their
dated records. Current implementation `d58cca51` is on `master`; current P001 and
P002 hosted runs are 42155822562 and 42155822754. Next: inspect original artifacts,
finish the remaining independent waves, and accept P001 before P002 only if every
original gate passes. No later phase is accepted by these repairs.

#### 2026-11-06 P002 wave-three independent provenance review

`/root/wave3_provenance_review`, a non-author reviewer, approved the scoped
provenance loader, lock generator, current lock and new provenance tests at
`9612e4b7a5931a15e892881173a643008af032ea`; those four files are independently
confirmed unchanged at integration `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
The [independent review](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave3-provenance-review.md)
records 110 passing P002 tests, both immutable 160-record Git graphs, all 320
original/current declared URL records, all 160 current lock records, frozen
evidence hashes, and 44 preserved LFS pointer records. No concrete defect was
reproduced, so no production or test change was needed. This is implementation
approval only; hosted artifact review and ordered current-source P001 then P002
acceptance remain separate requirements.

#### 2026-11-06 P001 wave 3: independent prerequisite implementation review

Reviewer `/root/wave3_baseline_review` approved the scoped prerequisite
implementation at `6cb6cada6fb48da501a255e69c049fcde1798a79` for integration with
no additional reproducible defect. The five reviewed production files are
unchanged at integrated candidate `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
The independent review checked the separate historical/current source chains,
complete 63-citation ID coverage, frozen 160-record graph binding, physical
inventory crosschecks, exact current CMake allowance, and explicit historical
fetches in fresh shallow checkouts. Independently executed checks passed all
**174 P001 fixtures** and **12 source-provenance fixtures**.

The [review report](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave3-baseline-review.md)
records exact anchors, file and transcript hashes, reasoning and limitations.
The canonical Git blob hashing repair remains covered by the separate integrity
review. This verdict approves implementation integration only. The next step is
the independent exact-SHA hosted artifact and ordered phase-acceptance review;
this handover does not accept P001/P002 or reaccept P003/P004.

#### 2026-11-06 hosted evidence preserved; independent artifact waves beginning

P001 run **42155822562** and P002 run **42155822754** both succeeded on Ubuntu
22.04 and 24.04 at exact `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. All four
original ZIP digests matched GitHub metadata, every member passed CRC, all 66
internal checksum entries and 38 command-log segments passed, and all recorded
commands exited zero. [The complete archived raw evidence and replay reader](docs/compat/logic-pro/evidence/P002/requalification-20261105/hosted-d58cca51/README.md)
retain all 70 members, including every byte of the four complete tracked-file
manifests. Each P002 clone verified all 160 gitlinks, 44 LFS payloads /
16,128,448 bytes and 293,500 physical files; both regenerated the exact current
lock. Provenance and baseline implementation reviews are independently approved.
Next: complete the third integrity review, then the fourth/fifth artifact and
acceptance waves. **Current P001/P002 phase acceptance remains pending.**


#### 2026-11-06 P002 wave-three independent integrity and campaign review

A non-author review approves the object-integrity, physical-checkout, and complete
anonymous campaign implementation at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
The retained corrupt loose-object case independently reproduced the false pass
on `c7ef7fe4` and failed closed on the repaired source. All **4 object-integrity
tests and 18 campaign tests** passed, including real SHA-1/SHA-256 corrupt-object
negatives, valid CRLF/empty/binary blobs, explicit `reviewed-current` lock
regeneration, and byte-identical lock enforcement. No concrete implementation
defect was found in this bounded review.

The [wave-three integrity review](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave3-integrity-review.md)
records the scope, independent results, and approval. This is implementation
approval only: hosted artifacts are reviewed separately, and P001/P002 remain
pending ordered wave 4/5 acceptance review. All **160 gitlinks and 44 actual LFS payloads**
remain required; P003/P004 are not reaccepted.

#### 2026-11-06 complete published-archive readback and third-wave completion

The complete raw-evidence archive was published in `44b20845`. A fresh anonymous
Git object store fetched that exact public commit, verified its tree, reconstructed
all 70 original artifact members, and matched every raw size/SHA-256 against the
original downloaded artifact metadata. [Remote readback record](docs/compat/logic-pro/evidence/P002/requalification-20261105/hosted-d58cca51/archive-remote-readback.json).
All three independent third-wave implementation reviewers approve the exact
production bytes tested at `d58cca51`; none required a further production fix.
The fourth wave owns P001 original-evidence review, clone A review, and clone B/LFS
review. Next: complete those checks, then the fifth-wave final replay and ordered
acceptance. P001/P002 current acceptance remains pending; later phases remain
unaccepted at this source.

#### 2026-11-06 bounded tree-object follow-up during artifact review

The integrator checked whether the proven blob corruption gap also applied to
Git tree metadata. A real temporary repository with a corrupted tree and matching
index/worktree is rejected by native `ls-tree` and `status` (hash mismatch), and
by independent `fsck`. [Reproducer and original result](docs/compat/logic-pro/evidence/P002/requalification-20261105/tree-integrity-probe.json)
are retained. No further production repair is indicated. Current implementation
remains the exactly hosted-tested `d58cca51`; complete original artifact review
and ordered acceptance remain the fourth/fifth-wave work.


#### 2026-11-06 04:06:14 UTC — independent current-source P001 acceptance

Independent reviewer `/root/wave4_p001_evidence` accepts **P001 G1–G4** at
implementation `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. The original P001
recovery and historical citation contract is unchanged. Both successful hosted
P001 jobs in run `42155822562` were checked from their original ZIP bytes and
fresh official metadata: all members/checksums, 174 actual tests per host, exact
source identity and command exits pass. Independent native-object verification
matches 293,660 entries, 161 repositories, 160 current and 160 historical graph
pins, all 63 historical and 63 current citations, and 755 license candidate
hashes. The local 174-test rerun and both clean isolated original recoveries pass.

The complete archive was durably published at `44b20845` and read back from a
fresh anonymous Git object store; confirmation and the final integrity review
were published at `f8af3e1c` before this decision. All three Wave 3 implementation
reviews approve. [Independent report, exact UTC acceptance and reproduction evidence](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-p001/README.md)
record the complete gate decision. **P001 is accepted before P002.** Proceed only
to the independent current-source P002 evidence review and ordered final
acceptance. This decision does not accept P002 or later phases and makes no
runtime or Logic Pro execution claim.

#### 2026-11-06 P002 wave-four independent clone A review

Independent reviewer `/root/wave4_clone_a`, who authored no production repair,
records a scoped **TECHNICAL PASS** for clone A at tested implementation
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. The original 53,657-byte artifact
passes all 18 member identities, 17 internal checksums and 13 command/log segment
checks. All 160 checkout records/native pins agree with the locked commits,
trees and URLs; 115 fixtures actually complete successfully. The hosted reports
agree on 161 repositories, 293,500 physical blob paths and 44 LFS payloads
totaling 16,128,448 bytes, and the regenerated lock is byte-identical to tested
source. Fifteen independent synthetic integrity cases pass, including corrupt
blob/CRLF, hidden dirty bytes, modes, symlinks, committed URL/gitlink changes,
existing-clone refusal and a corrupt loose tree with a matching index/worktree.
No production change is indicated. [Complete scoped review, executable audit,
and reproduction results](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-clone-a/README.md)
record the evidence limits. This is not whole P002 acceptance: the final wave
must establish ordered P001 acceptance and incorporate the complementary clone B
review before changing the phase status. P003 and later phases remain blocked.

#### 2026-11-06 P002 Wave 4 clone B and LFS independent approval

Independent reviewer `/root/wave4_clone_b_lfs` approves the scoped clone B/LFS
and cross-host original-evidence review at tested implementation
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. Independently fetched official metadata
confirms separate hosted runners. Original ZIP/CRC/member/internal hashes,
all 13 command segments per clone, 115 actual successful cases per clone,
the complete 160-gitlink graph, and byte-identical regenerated locks pass.
All 44 supplemental physical LFS payloads independently match committed
OID/size/mode identities, totaling 16,128,448 bytes. Ten corruption/restoration
probes, actual Git LFS cached checkout, and false-success/network-failure
rejections pass; the independent local full suite passes all 115 tests.
[Scoped report, replay tools, official metadata, and raw local results](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave4-clone-b/README.md)
are retained. This reviewer changed only documentation and review evidence.
Whole P002 acceptance remains contingent on P001, complementary Wave 4 review,
and final Wave 5 approval; P003/P004 are not reaccepted.

### 2026-11-06 — Wave 4 complete; P001 independently accepted before P002

Root integrated the three independent Wave 4 records without changing tested
production code. P001 G1–G4 were accepted at 04:06:14 UTC by
`/root/wave4_p001_evidence`, after both original hosted archives, complete native
inventory, 63 historical/current citations and isolated recovery were checked.
The clone A reviewer passed 15 independent integrity cases; the clone B/LFS
reviewer passed 115 local fixtures, 13 LFS/failure/recovery cases and independent
physical hashes for all 44 payloads. Original raw transcripts and reviewer-owned
reproducers are retained in the five-wave evidence directory.

The live dashboard, phase index and P001 checkboxes now record that explicit
predecessor acceptance at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. P002 remains
READY FOR REVIEW while the final three agents check source equivalence, archive
replay and acceptance-ledger consistency. No technical blocker remains from
Wave 4; final P002 acceptance and its publication are the next required action.
P003/P004 and runtime/application claims are outside this acceptance.

### 2026-11-06 — Final-wave ledger consistency corrections

The independent fifth-wave ledger reviewer confirmed all eight original P001
and P002 gate cores are unchanged. Root corrected the starting-source narrative
to state its historical date explicitly, updated the machine-readable wave
ledger with all 15 assigned agents and completed first-four-wave evidence, and
corrected the evidence index's obsolete future-tense master-publication note.
P001 remains independently accepted; P002 remains READY FOR REVIEW pending
the final source/evidence verdict and final dashboard consistency check.

### 2026-11-06 — Final-wave independent source approval

The independent source reviewer `/root/wave5_final_source` approved the
production and regression integrity of public publication
`9b2ce08d9012091e23173b8ac1a37b5c0e98359c` against tested production
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. All 27,812 protected paths and all
nine explicitly checked frozen contract/provenance inputs are identical. All
137 subsequent changed paths are review evidence or README updates; none of
the added evidence helpers is referenced by production, tests or CI.

The original 63 citations, 149 root gitlinks, native/build/workflow sources and
original negative gate semantics remain intact. Both 160-dependency provenance
graphs passed the unchanged production loader. The report and full path/hash
comparison are under
`docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-source/`.
No source blocker remains. This is technical source approval; the independent
final evidence reviewer still owns P002 acceptance. No later phase or runtime
claim is made.

### 2026-11-06 — Fifth-wave final independent P002 evidence acceptance

Reviewer: `/root/wave5_final_replay` (no production changes authored). At
`2026-11-06T04:29:24Z`, accepted **P002 G1–G4** for tested production
`d58cca513559cfef0ff9af59aa5dc3b6341bdf77`, after published same-source P001
acceptance at `2026-11-06T04:06:14Z` and final source approval published at
`f2cbf424b7a5433b20ecfcb1900e69de0adfbad5`.

Final replay reconstructed all 70 original hosted artifact members and compared
each against the original ZIP and extracted bytes. The unchanged independent
artifact auditors passed both original hosts, 26 successful command segments,
230 completed P002 cases, complete 160-gitlink graphs and byte-identical locks.
All 44 supplemental physical LFS payloads matched; that partial checkout did
not replace either original hosted clone. Five focused positive/corruption
fixtures passed, including actually committed URL/gitlink damage and real
canonical-object/forged-CRLF rejection. The unchanged source approval and P001
record were read back from their public commits before signing.

See [the final review](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/README.md),
[formal acceptance](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/acceptance.json),
and [raw replay results](docs/compat/logic-pro/evidence/P002/requalification-20261105/wave5-replay/replay-results.json).
Only evidence/documentation and the bounded replay wrapper changed. No dependency
pin or production code changed, and no P003/P004 or runtime acceptance is made.
The coordinator retains responsibility for synchronizing the live dashboard and
ordered ledger with this signed decision.

### 2026-11-06 — P002 accepted after five waves; final handover

Root integrated the final non-author source and evidence reviews and synchronized
the dashboard, phase index, original P001/P002 gate checkboxes, evidence index and
machine-readable wave ledger. P001 G1–G4 were accepted at 04:06:14 UTC, then P002
G1–G4 at 04:29:24 UTC, both at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
The fifth-wave ledger reviewer checked this concrete final status draft and its
evidence links; that review binds the exact reviewed bytes without claiming a
new implementation test. All five waves contain three distinct assignments.

Both exact-source hosted campaigns passed on both hosts. Independent archive
replay reconstructed all 70 original members and matched their original bytes;
independent critical cases retain strict error behavior. All later changes are
documentation and review evidence, with protected production/test/workflow/lock
and frozen provenance bytes unchanged. Work is published incrementally on the
requalification branch and this final evidence is advanced to `master` without
force after checking the remote head.

**P002 is complete. No P002 failure or unresolved review blocker remains.** The
next permitted phase is P003, which must repeat its original current-source
qualification. P004 and application/runtime acceptance remain unclaimed.
[Complete evidence and decisions](docs/compat/logic-pro/evidence/P002/requalification-20261105/README.md).

### 2026-11-06 — P003 five-wave requalification started

Owner `/root` started from `3be66e2b343b77c34d023c20bd7822dc055c657f`, after the
accepted ordered P001/P002 campaign. Three independent first-wave assignments
audit the acceptance contract, build/install path and runtime/evidence checks.
The latest original P003 run `42163489140` fails before full build because the
aggregate does not recognize the current reviewed CMake re-audit format. Local
reproduction of its 14 source-classification tests gives the same 20 failing
subtests and one error. All 174 P001 and 115 P002 local regression tests pass.

This initial change records the current state and clears only the live P003
checkboxes; historical acceptance and its evidence remain intact. No production
source, dependency pin, frozen toolchain or acceptance requirement changed.
The exact next action is to repair the scoped aggregation mismatch, rerun its
adversarial tests, and qualify all four original gates with fresh hosted evidence.
**Remain in P003; no current runtime or Logic Pro compatibility pass is claimed.**
[Campaign evidence](docs/compat/logic-pro/evidence/P003/requalification-20261106/README.md).

### 2026-11-06 — P003 current-source aggregation repaired

Root repaired `compare_p003.validate_source_classifications` to consume the exact
already-reviewed root-CMake upstream re-audit emitted by the accepted P001
verifier. It binds the reviewed upstream commit and prior P003 blob, preserves
all original assertion and citation checks, and confines this case to the
reviewed root `CMakeLists.txt` delta. This does not accept P004. No source
manifest, producer audit, dependency pin, toolchain lock or runtime source changed.

The original 14 focused cases reproduced 20 failing subtests and one error.
After the repair, **18 focused and all 155 P003 verifier tests pass**, including
real Clang 19/GCC 14 local native boundary cases and four new adversarial tests
for forged/omitted identities, unrelated paths and changed assertion/count data.
The full hosted campaign still uses its frozen Clang 14 toolchain. The workflow
now enforces the current regression floors of **174 P001 / 115 P002 / 155 P003**.
The preceding 174/115 suites pass unchanged locally. Local fixture success is
not installed-runtime acceptance. The original failing hosted fixture ZIP is
preserved unchanged with its API SHA-256.

Provenance: existing repository contracts, accepted source-audit implementation,
and original GitHub Actions failure logs. No restricted material or new external
dependency entered the repository. Fresh two-host build/install/reinstall and
independent archive-only execution are the next required actions. **Remain in P003.**

### 2026-11-06 — P003 Wave 1 closed; actual producer replay drives Wave 2

Three independent audits completed and are retained in the current P003 evidence
campaign. The first repair `8a222c7d5` passes hosted 174/115/155 fixtures in
`42165628353`, and its two full builds have started. Root replayed the preserved
real P001 producer report and found a further missing aggregate binding for all
63 current-source records. The source auditor and accepted manifest remain
unchanged; Wave 2 fixes their consumer and adds a real-report regression.

The build reviewer separately verified that final source status was captured but
not enforced, and the runtime reviewer reproduced a constructor failure that
left an empty evidence directory. Dedicated Wave 2 agents are implementing
those scoped corrections and rejection tests. No observed source mutation or
false runtime success is claimed. P001/P002's ordered accepted scope is retained;
all current P003 gates remain unaccepted. **Remain in P003.**

### 2026-11-06 — P003 current Objective-C pin configuration repaired

Both original build artifacts for `8a222c7d5` are preserved unchanged in
[the failed-attempt record](docs/compat/logic-pro/evidence/P003/requalification-20261106/attempt-8a222c7/README.md).
They pass the frozen toolchain, 160 pins/44 payloads, 63 source citations and
Clang 14 unwind regression, then fail at the root-owned Objective-C adapter.
The accepted current objc4 dependency already derives its debug flag from its
header; the old adapter incorrectly demanded the earlier hard-coded definition.

Root updated `cmake/darling_objc_configuration.cmake` to retain the legacy
repair for its recognized old layout and preserve the current header-derived
layout without injecting a conflicting build-type guess. Unknown definitions
and missing/changed/duplicate header derivations remain fatal. Six real CMake
and C++ regressions pass, including normal and customized release flags, with
raw results retained. No pin, frozen toolchain, runtime implementation, accepted
P001 source verifier or classification manifest changed. This bounded checkpoint
is pushed immediately; the combined Wave 2 candidate will run full CI after the
remaining provenance and failure-evidence repairs. **Remain in P003.**

### 2026-11-06 — P003 Wave 2 complete; integrated candidate starts full qualification

Root integrated the source, build and runtime agents' bounded repairs after review.
The complete local run passes **174 P001 / 115 P002 / 187 P003**, zero skips; raw
transcripts and code hashes are retained in the current campaign. The expected
negative toolchain-drift diagnostic in the unittest transcript remains a passing
rejection test. The current Objective-C header-derived and legacy configurations
are covered by six real CMake/compiler tests. Both original fresh source reports
now satisfy all 63 current and historical provenance bindings.

The protected predecessor manifests, source producer, gitlinks and frozen toolchain
remain unchanged. Provenance is the existing repository contracts, public upstream
build configuration and original hosted reports; no restricted source, proprietary
binary or new dependency was used. Three new Wave 3 agents independently review
source/build integration, package nondeterminism and runtime/evidence behavior.
The exact next action is fresh two-host full qualification and original-artifact
review in Waves 3–5. The five-wave ledger and dashboard are synchronized.
**P003 ACTIVE; remain in P003; P004 NOT PASSED.**

### 2026-11-06 — P003 repaired candidate passes hosted preflight

Published candidate `af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2` passes the exact
174/115/187 hosted fixture gate in `42169925661`. Root preserved the original
11,383-byte artifact and verified its API SHA-256, all four CRC members and
all transcript counts without skipped tests. This evidence-only checkpoint leaves
qualified code and frozen inputs unchanged. Full builds and runtime qualification
remain in progress; Waves 3–5 must independently establish all four original gates.
**Remain in P003; no runtime acceptance yet.**

### 2026-11-06 — Independent source/runtime review checkpoint

Two Wave 3 non-author reviews approve the scoped `af3566ee` repairs with critical
reproduction and exact file hashes; their original reports, JSON and transcripts
are published unchanged. The independent package comparison remains active.
Root also preserves the successful frozen-toolchain job's decoded log losslessly,
plus the original image artifact identity. Both fresh P003 build containers remain
in progress; no runtime or phase pass is inferred. This checkpoint changes only
documentation/evidence and keeps the tested implementation fixed. **Remain in P003.**

### 2026-11-06 — Third wave complete; fourth-wave original-artifact reviewers assigned

The source, runtime and package-method reviewers complete their bounded Wave 3
assignments, plus a separate UUID crosscheck. The independent 504-line stdlib
package helper, complete historical QA JSON and exact source/UUID counterexamples
are published with hashes. Its reproduced 138-file inventory is historical
method validation, not borrowed current acceptance. Three new Wave 4 agents
review actual current build inputs/outputs, package/framework provenance and
runtime/lifecycle evidence. All implementation and frozen input bytes remain
unchanged from tested `af3566ee` at that checkpoint. Subsequent log inspection
finds both artifact uploads failed; the next handover records the repair. All
current G1–G4 checkboxes remain pending. **Remain in P003.**

### 2026-11-06 — Repair the observed artifact upload failure

Root preserves the complete original runner logs from both failed `af3566ee`
uploads and repairs the newly created final-status file permission at its owner.
The explicit descriptor mode supports the root-container/unprivileged-uploader
boundary under a restrictive umask; the actual-handler regression verifies eight
success/failure combinations. The fixture floor is 174/115/188. Independent Wave 4
reviewers remain assigned to build, package/framework and runtime evidence. A
fresh full frozen-toolchain campaign is mandatory because no prior A/B archive
was finalized. No current G1–G4 gate is accepted. **Remain in P003.**
