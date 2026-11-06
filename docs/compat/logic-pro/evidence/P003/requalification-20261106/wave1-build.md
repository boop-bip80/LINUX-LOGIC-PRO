# Wave 1 — P003 build and installation audit

Date: 2026-11-06 UTC. Starting source: `3be66e2b3`. Reviewer: `/root/wave1_build`, independent build/install sub-agent. This wave reviewed production code without changing it. This note does not grant P003 acceptance.

## Scope and evidence

Reviewed the repository instructions and P003 contract, the full-build workflow, container/toolchain preparation, build/install script, isolated uninstall guard, installed-framework verifier, and P003 comparison and independent-runtime acceptance paths. The review used repository source, public-contract reasoning, existing tests, and the parent agent's identified hosted evidence. No restricted Apple or CoreCrypto implementation material was accessed.

The local build-fixture invocation completed 153 tests but could not pass because the environment lacked the required clang compiler (`test_mldr_thread_entry.setUpClass`). That is an environment limitation, not evidence of a product defect. The parent independently reproduced the actual hosted source-classification failures and subsequently reported the repaired 155-fixture job passing in run `42165628353` at `8a222c7d5e11fbd2c3ece79c53d60c1be545d0a0`.

## Verified findings and repair review

1. **Source-evidence producer and consumer disagree.** The initial comparison consumer did not understand the already-reviewed `P004`-labelled root-CMake re-audit. The parent reproduced the resulting failure in run `42163489140`. I reviewed the published repair in `8a222c7d5`: it confines this form to root `CMakeLists.txt`, requires the existing exact upstream merge and prior P003 blob constants, preserves original assertions, and checks the combined reviewed-addition count. The added negative cases cover altered historical identities, missing report bindings, unauthorized paths, and incorrect counts/boolean flags. I found no blocker in this narrow repair.

   A further producer/consumer mismatch remains at this checkpoint: the actual producer includes per-record `current_source` and a top-level `current_source_anchor`, whereas the consumer and synthetic fixture omit them. The parent reproduced rejection of the frozen real producer report at `docs/compat/logic-pro/evidence/P002/requalification-20261105/hosted-d58cca51/p001-ubuntu-22.04/classifications.json`, at the `architecture-targets` record. Wave 2 must bind the complete current manifest and replay this real producer output, with adversarial mutations. Passing synthetic fixtures alone is insufficient evidence that the full campaign's final comparison can consume its own reports.

2. **End-of-build source cleanliness is recorded but not enforced.** `ci/logic-pro/build-p003.sh` requires an empty `source-status-before.txt`, then writes `source-status-after.txt` and immediately reaches the complete stage without checking that it is empty. `compare_p003.campaign` likewise checks only the before file. Thus a source tree mutation during configure/build/install/probes can coexist with a successful summary; the after file's presence in the evidence hash inventory does not reject that mutation. This is a verified acceptance gap, not a demonstrated build mutation. A later scoped repair should reject a missing or dirty after-status record and enforce cleanliness before declaring the build complete, with fixture coverage for a clean before/dirty after campaign. Any legitimate generator output should be identified explicitly rather than silently accepting arbitrary source changes.

No other concrete build or installation defect was established in this timeboxed wave. Possible additional hardening was not promoted to a defect without a reproduction.

## What the hosted qualification must establish

- Both clean builds use the same pinned source/submodule/LFS manifest and measured compiler/container environment, pass the actual source-audit producer output through the comparison consumer, and leave the qualified source unchanged.
- Both builds install all seven required real frameworks with the expected source ownership, Mach-O identities, public aliases, dependency resolution, and installed bytes matching build outputs.
- Both first and second installations execute the ten behavioral probes, including fresh challenges, Foundation/XPC behavior, visible GUI input and captured pixel checks, without stubs or leaked runtime namespaces.
- Guarded uninstall removes the whole owned installation; a second installation and fresh runtime directories reproduce the behavior without relying on the first installation.
- The independently downloaded runtime archive is checked and executed on a host without source/build mounts using fresh challenges and the independently recorded reviewer drivers.
- The final comparison binds both builds and independent review to the exact implementation commit, accepts the actual producer schema, enumerates every allowed output difference, and retains raw logs and artifact hashes. Any unexplained difference or failing job keeps P003 open.

The historical accepted P003 implementation `89c6c9d85aba6ed1662035e6366298c92ef9c970` does not qualify the changed current implementation. P004 remains blocked until the new P003 campaign and independent review pass.
