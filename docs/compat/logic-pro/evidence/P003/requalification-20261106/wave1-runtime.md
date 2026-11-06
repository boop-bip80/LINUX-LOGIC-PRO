# Wave 1: runtime and independent replay audit

Date: 2026-11-06 UTC. Reviewer: `/root/wave1_runtime`. Initial source reviewed: `3be66e2b3`.

Scope: `AGENTS.md`, the P003 contract in `README.md`, the Mach-O,
Foundation and GUI probes, `run_build_probes.py`,
`review_installed_runtime.py`, `review_package_archive.py`, and relevant
runtime/package tests. Production code was not edited by this reviewer.
CoreCrypto source was not inspected.

## Findings

No new verified false-success defect was found in the inspected runtime or
package replay paths. This is a bounded source and fixture audit, not a real
installed Darling runtime pass.

One minor evidence-reporting defect was reproduced: in
`tools/compat/logic-pro/run_build_probes.py`, `run()` constructs `Campaign`
before entering its failure-reporting `try` block. If the controlled HOME
already exists, the constructor raises `ProbeFailure`; the output directory
is created but remains empty instead of receiving a structured FAILED report.
The reproduction used an isolated temporary directory, created
`runtime.home`, and called `run()` with absolute installation/output/prefix
paths. Result: `ProbeFailure: controlled runtime HOME must be absent`, with an existing
empty output directory. This fails closed and cannot establish a false P003
pass. A later patch can move campaign setup under failure reporting while
preserving the rejection of reused HOME state.

## Positive evidence and limits

- Mach-O computation checks exact nonce-bound FNV values and rejects invalid
  argument counts and oversized input. The host oracle also checks a known
  fixed vector.
- Foundation verifies object values, byte contents, missing-key behavior and
  interoperation of XPC/vproc transaction counts.
- GUI acceptance combines exact input/acknowledgement records with visible
  X11 window discovery, externally injected input and before/after pixels.
  Runtime framework reports require the seven canonical image paths.
- Both runtime drivers check server identity and surviving holders of the
  private mount namespace during shutdown, rather than accepting only a
  successful shutdown command.
- The independent driver has its own process execution and image decoding,
  uses a controlled environment and rejects source/build mounts. The archive
  reviewer validates manifest membership, hashes, metadata and link handling
  before extraction and checks the installed tree afterward.

The local command
`python3 -m unittest discover -s tests/compat/logic-pro/build -p 'test_*.py'`
ran 153 tests in 24.563 seconds and exited 1 with one setup error:
`Required clang compiler unavailable; cannot skip` in
`test_mldr_thread_entry.MldrThreadEntryTests.setUpClass`. No assertion failures
were reported. This invocation did not include the compiler wrapper later
prepared by the parent agent; it is not evidence of a product defect or a
complete passing suite. The toolchain-negative-test message
`Toolchain changed: tools.clang.sha256` appeared in that run and was not a
test failure.

No complete build/install, source-free privileged replay, X11 interaction or
installed-runtime shutdown was executed by this reviewer. G1–G4 therefore
remain subject to the parent campaign's actual build and runtime evidence.
