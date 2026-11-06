# Wave 2: runtime initialization failure evidence

Date: 2026-11-06
Author: `/root/wave2_runtime`
Scope: bounded P003 probe reporting correction.

## Reproduced defect and correction

An existing controlled runtime HOME caused `Campaign` construction to raise
`ProbeFailure` before `run()` entered its failure-reporting block. The probe failed
but left its newly created evidence directory without a report.

`Campaign` construction now occurs inside that block, after prefix validation.
Known initialization failures return exit code 1 and write `status: FAILED`,
`passed: false`, and the failure reason. Unexpected exceptions also record a
FAILED report, then propagate with their original traceback. The constructor
`KeyError` regression verifies that the original exception object and failing
constructor frame survive.

When initialization does not complete, the report contains empty `cases` and
`commands`, null `lifecycle` and `controlled_home`, and no `startup_processes`.
It makes no claim that a runtime case, startup, or shutdown executed. Prefix
validation runs before controlled HOME creation, so a rejected dirty prefix does
not create that HOME.

The output directory is still claimed exclusively before initialization. Existing
output paths are preserved and fail before any runtime setup. Report creation
also uses exclusive mode, preserving a report that appears after the output
directory was claimed. In that collision, the operation fails without replacing
the existing report. Existing HOME paths, symlink targets, and dirty prefix
contents remain intact.

## Verification

Commands run from the repository root:

```sh
python3 -m unittest discover -s tests/compat/logic-pro/build -p 'test_probes.py' -v
PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH python3 -m unittest discover -s tests/compat/logic-pro/build -v
```

- Focused probe tests: **20 passed**, 0.087 seconds, exit code 0.
- Intermediate build/runtime suite snapshot: **164 passed**, 38.568 seconds,
  exit code 0. This predates the source/build agents' new tests; root records the
  final integrated count and raw transcript.
- Focused coverage includes controlled HOME and output collisions for directories,
  files, symlinks, and dangling symlinks; constructor `OSError` and `KeyError`;
  dirty-prefix preservation; and a report created during initialization.
- The full suite's `P003 toolchain verify: FAIL: Toolchain changed:
  tools.clang.sha256` diagnostic is the expected toolchain-drift negative fixture;
  the unittest result was `OK`.

## Qualification boundary and provenance

This change corrects evidence reporting inside P003. It does not establish runtime
acceptance. No installed-runtime, X11, or privileged-shutdown campaign was replayed
for this correction; P003 acceptance remains pending and G1–G4 remain pending.

The change uses repository tests and public Python filesystem/exception interfaces.
No proprietary inputs or new dependencies were introduced.
