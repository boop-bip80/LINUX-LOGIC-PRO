# Wave 2: final source cleanliness

Date: 2026-11-06
Author: `/root/wave2_build`

## Verified gap and bounded change

The P003 producer previously recorded `source-status-after.txt` only on its
successful path without requiring that it be empty. The aggregate checked only
the initial checkout status. A build could therefore change tracked or untracked
source and still satisfy this part of the aggregate gate.

`ci/logic-pro/build-p003.sh` now captures final raw Git porcelain status in its
actual EXIT handler, including when an earlier build stage fails. It creates the
record exclusively without following a symlink, checks the captured file's type
and identity, and requires both successful Git execution and empty status. The
Git invocation explicitly includes submodule changes even when local ignore
configuration would hide them. There are no exclusions for generated tracked
files. A source-cleanliness failure changes an otherwise successful exit to 1
and records `source-cleanliness` as the failing stage; an existing nonzero exit
and its original stage remain authoritative. Dirty status bytes are retained.

The narrow `campaign()` change in `tools/compat/logic-pro/compare_p003.py`
requires both initial and final status evidence to exist as regular files,
rejects symlinks, and requires exactly empty contents. Missing final evidence
can no longer pass this gate.

## Focused verification

All commands below ran from the repository root with
`PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH` on 2026-11-06.

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s tests/compat/logic-pro/build -p test_source_cleanliness.py -v` | 15 tests passed |
| `python3 -m unittest discover -s tests/compat/logic-pro/build -p test_comparison.py -v` | 19 tests passed |
| `bash -n ci/logic-pro/build-p003.sh` | Passed |
| `git diff --check -- ci/logic-pro/build-p003.sh tools/compat/logic-pro/compare_p003.py tests/compat/logic-pro/build/test_source_cleanliness.py docs/compat/logic-pro/evidence/P003/requalification-20261106/wave2-build.md` | Passed |

The new producer tests execute the script's real EXIT function against tiny
temporary Git repositories. They cover clean success, tracked generated-file
mutation, untracked output, dirty submodules hidden by Git ignore configuration,
preservation of exit code 42 and the original stage on clean and dirty failures,
preexisting status, symlinks, directories, FIFOs, and Git status failure. The
aggregate tests exercise real status-file reads and evidence hashing, with only
unrelated validators mocked; they cover acceptance of clean status and rejection
of missing, dirty, symlinked, or directory status at both boundaries.

These are producer and evidence-validation regressions. Their temporary fixtures
are not Darling runtime evidence and do not qualify P003. The combined full suite
and fresh hosted qualification remain the integration owner's responsibility.
