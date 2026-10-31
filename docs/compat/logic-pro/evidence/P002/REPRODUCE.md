# P002: reproduce the independent ordinary recursive-clone gate

This phase proves that **anonymous users can retrieve the committed dependency
graph** using ordinary Git, without the P001 source-inspection acquisition
override, local URL rewriting, credentials or cached child objects. A successful
checkout alone does not qualify the Darling build or Logic functionality.

The initial source inventory and published pins are preserved by
[`submodules.lock.json`](../../submodules.lock.json). Its 160 records are
derived from the independently accepted P001 retrieval report. The 149 direct
URLs point to verified Darling upstream repositories; the 11 nested declarations
are controlled by their unchanged pinned child source commits.

## Clean qualification, twice

Use two **different** Linux hosts or isolated workspaces with separate Git
object stores and no alternates/reference/cache. Git 2.39+ and Python 3.10+
are sufficient for the retrieval and verification gate. The hosted P002 workflow
uses Ubuntu 22.04 for A and Ubuntu 24.04 for B. The checkout must be from the
published `master` branch, and the resulting HEAD must equal the exact tested
implementation SHA recorded in the reviewer evidence.

On each fresh runner, start in a task-owned empty directory:

```bash
export GIT_TERMINAL_PROMPT=0
export GIT_ALLOW_PROTOCOL=https
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
git -c credential.helper= clone --recurse-submodules --jobs 12 \
  --branch master https://github.com/boop-bip80/MAC-OS-EMULATION.git clone-a
git -C clone-a rev-parse HEAD
git -C clone-a submodule status --recursive
python3 -B clone-a/tools/compat/logic-pro/check_submodules.py \
  --repo clone-a --lock clone-a/docs/compat/logic-pro/submodules.lock.json \
  --output clone-a-verification.json
python3 -B -m unittest discover \
  -s clone-a/tests/compat/logic-pro/submodules -v
```

For the second run, substitute `clone-b` and use a **different host/object store**.
Never run both against the same source checkout, a `--reference` clone, or a
previously initialized Git module cache. Preserve the full stdout/stderr of
both clone commands in `clone-a.log` and `clone-b.log`, together with exact
tool versions, environment, native status, verifier JSON, fixture transcript
and SHA-256 checksums. The workflow collects these in separate artifacts.

The pinned URL repair must not be masked by configuring `url.*.insteadOf`,
`git submodule set-url`, a private Git credential helper or an out-of-band
network mirror. P001's `prepare_sources.py --upstream-url` is **not** the P002
clone procedure. If the checkout cannot fetch a published pinned commit, fail
this gate and record the missing URL/object rather than silently advancing it.

## Acceptance review

1. Both separate clones have Git exit code zero and exactly 160 initialized
   descendants. There must be no leading `-`, `+` or `U` in native recursive
   `git submodule status`, and no dirty worktree/index in the locked graph.
2. `check_submodules.py` must report `PASS`, 160 exact commits/trees and 161
   inspected Git repositories. It must detect deliberate URL and pin damage,
   including missing nested children in the real Git fixtures.
3. Re-run `make_submodule_lock.py` in an isolated checkout and require a
   byte-identical lock; compare all 149 root gitlinks to the P001 source
   evidence. There are no changed gitlinks in this URL-only repair.
4. Obtain a **different agent/person's** source and evidence review, covering
   the concrete implementation revision and raw hosted artifacts. The author
   cannot approve their own P002 work. Commit the verdict and both clone logs
   under this evidence directory before checking the README gates or advancing
   to P003.

Workflow run and artifact URLs, tested SHA, archive hashes and independent
reviewer identity belong in a dated `acceptance.json` after successful review.
Any missing evidence means ACTIVE/READY FOR REVIEW/BLOCKED, never PASSED.
