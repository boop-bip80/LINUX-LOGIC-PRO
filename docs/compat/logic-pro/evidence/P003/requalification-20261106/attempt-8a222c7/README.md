# First repaired candidate: actual configure failure

Source: `8a222c7d5e11fbd2c3ece79c53d60c1be545d0a0`. Original
[run 42165628353](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42165628353).
The original fixture and both build ZIPs are preserved here unchanged; all
three SHA-256 values match the GitHub artifact metadata in `artifacts.json`.

The hosted 174/115/155 verifier suites passed. Both clean build hosts verified
the frozen toolchain, all 160 recursive pins, 44 LFS objects, 63 source citations
and the actual Clang 14 static-unwind code-generation regression. Both then
failed CMake configuration at `darling_objc_configuration.cmake`: the legacy
adapter required a directory definition removed by the current objc4 pin.
Neither installation nor installed runtime execution occurred.

The current dependency is `092352cab947b410a73b5123b190df03f90c1802`. Its
[public upstream change](https://github.com/darlinghq/darling-objc4/commit/092352cab947b410a73b5123b190df03f90c1802)
derives the debug macro from the runtime's own `DEBUG` definition. Root read
the exact pinned CMake/header change and repaired only the root-owned adapter.
The current header SHA-256 is
`28104a987e265db55fc6aaaf2d751a74655c77dde216d7e15a73076a55f17169`.
No dependency commit or source file changed.

Six real CMake/compiler regressions pass: reproduce the original legacy failure,
retain legacy standard configurations, accept the current header-derived layout
without injected definitions, respect customized release flags without NDEBUG,
and reject unrecognized compiler definitions or missing/changed/duplicate header
derivations. Raw transcript: `../objc-current-pin.log`. This is local adapter
verification, not an installed-runtime pass. The combined Wave 2 implementation
will rerun the full hosted campaign after the remaining consumer/reporting fixes.

Provenance: repository build contract, original hosted logs, and the existing
publicly licensed Darling objc4 CMake/configuration change. No restricted source
or proprietary Apple binary was used; no third-party implementation was copied.
