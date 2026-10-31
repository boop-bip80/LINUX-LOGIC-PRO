# P002: reproduce the independent ordinary recursive-checkout gate

This phase proves that **anonymous users can retrieve the committed dependency
graph and the exact large-file payloads it consumes**, without P001's
source-inspection acquisition override, local URL rewriting, credentials or
cached child objects. A successful checkout does not qualify the Darling build
or Logic functionality; those are later phases.

[`submodules.lock.json`](../../submodules.lock.json) preserves all 160 recursive
pins derived from the independently accepted P001 retrieval report: 149 direct
repositories and 11 nested children. Root URL repairs must not change any pin.
The lock also records the 44 Git LFS payloads in the pinned Swift repository,
their pointer blobs, exact SHA-256 OIDs and sizes, and the public endpoint from
the committed `.lfsconfig`. A tiny pointer file is not a retrieved library.

## Clean qualification, twice

Use two **different** Linux hosts or isolated workspaces with independent Git
object stores and no alternates, references or object caches. Required tools are
Git 2.39+, Python 3.10+ and Git LFS. The hosted workflow uses Ubuntu 22.04 for A
and Ubuntu 24.04 for B and records the actual versions. Do not run both against
one previously initialized repository or module cache.

Choose the full 40-character SHA of the published implementation under review.
For a push or manual run this is the exact tested commit on `master`; a pull
request run qualifies its exact public merge commit. Never substitute the
current branch tip for the recorded SHA after a queued run starts.

Obtain the runner from that exact revision in a separate source checkout. From
that checkout, run the following with **new, nonexistent** clone and evidence
paths outside the source directory, replacing the example SHA and paths:

```bash
python3 -B tools/compat/logic-pro/run_submodule_campaign.py \
  --source "$PWD" \
  --destination /absolute/task-owned/p002-clone-a \
  --output /absolute/task-owned/p002-evidence-a \
  --commit FULL_40_CHARACTER_LOWERCASE_IMPLEMENTATION_SHA \
  --host-id a
```

On the second host, use that same SHA, `--host-id b`, and separate clone/evidence
paths. The runner refuses pre-existing destinations, evidence directories,
symlinks and overlapping paths; it never deletes or reuses old evidence.
Use the hosted workflow's two matrix artifacts for the independent-host gate.

The runner performs standard Git acquisition:

1. `git clone --no-local --no-hardlinks --no-checkout
   --no-recurse-submodules --origin origin` from the public repository URL.
2. Locate the requested commit; if not already present, `git fetch --no-tags
   --no-recurse-submodules origin FULL_SHA`. This also handles public PR-only
   commits without following a moving ref.
3. `git checkout --detach FULL_SHA`, prove exact `HEAD`, and run
   `git submodule update --init --recursive --jobs 12`.
4. Execute the complete positive/negative fixture suite **from that independent
   exact-SHA clone** and retain its stdout/stderr. Empty or skipped suites fail.
5. Explicitly fetch and check out Git LFS payloads using `lfs_manifest.py hydrate`
   and the trusted `git-lfs` executable. The exact endpoint
   `https://git-lfs.darlinghq.org/lubos/darling-swift` is pinned by the source's
   immutable `.lfsconfig`; this is not a replacement Git origin or URL rewrite.
   Every retrieved payload must match its locked OID and size.
6. Compare native recursive Git status against every locked path and pin, run
   the strict physical verifier, regenerate the lock and require byte equality.

Ambient `GIT_*` selectors, config injection, alternates and Git tokens are
removed. System/global Git configuration, credential helpers, hooks and
fsmonitor are disabled; noninteractive HTTPS is the only acquisition transport.
An ambient netrc credential file is refused without reading its contents.
Required proxy and CA trust variables are retained. Committed Git attributes
are honored, including ordinary Git CRLF checkout conversion; P001's raw-source
inspection overrides are not used. Arbitrary configured clean/smudge filters
are not installed or executed to hydrate LFS.

Do not mask source availability with `url.*.insteadOf`, `git submodule set-url`,
private credentials, a reference clone or an out-of-band mirror. In particular,
`prepare_sources.py --upstream-url` is **not** the P002 acquisition procedure.
If any pinned Git object or LFS payload is unavailable anonymously, record the
failure; do not advance a pin, accept an unhydrated pointer or waive the gate.

## Preserved evidence

Each host's output directory contains the following on success; on failure it
retains every completed or failed stage and a `FAIL` summary:

| File | Evidence |
| --- | --- |
| `environment.txt`, `git-version.txt`, `git-lfs-version.txt` | UTC, OS/kernel/runner image and actual Python/Git/Git LFS versions; no environment secrets |
| `source-head.sha`, `head.sha` | Runner checkout and independent checkout match the requested full SHA |
| `clone-a.log` or `clone-b.log` | Complete root clone, exact-SHA fetch/checkout and native recursive submodule acquisition transcript |
| `fixture-tests.log` | Complete positive and negative fixture transcript, including immutable-SHA/ref-race/PR-only acquisition cases |
| `lfs-hydration.log`, `lfs-hydration.json` | Explicit anonymous LFS acquisition, endpoint provenance, exact object verification and failures |
| `native-git-status.txt` | Native status for all 160 initialized descendants at their locked commits |
| `verifier-a.log` / `verifier-b.log`, `verification-a.json` / `verification-b.json` | Strict lock and physical-worktree verification, including LFS payload bytes |
| `lock-regeneration.log`, `regenerated-lock.json`, `lock-regeneration.json` | Regeneration output and byte-identical comparison against the committed lock |
| `commands.json` | Every executed stage's argv, exit code, duration, transcript offset/length and output SHA-256 |
| `summary.json`, `checksums.sha256` | Overall result and portable SHA-256 checksums of every artifact file |

The workflow uploads each directory even when a gate fails. The fixtures also
exercise command errors/timeouts, preserved failure evidence, stale directories
and symlink rejection. Passing only the helper's fixtures is not the real-world
two-host retrieval gate.

## Acceptance review

1. Both separate checkouts have successful ordinary Git acquisition and exactly
   160 initialized descendants at the locked commits. Native recursive status
   must have no missing, mismatched or conflicted entries. No worktree/index
   damage may be hidden by flags, filters, URL rewrites or altered metadata.
2. All 44 locked LFS payloads are retrieved anonymously and match their exact
   SHA-256 OIDs and sizes; the committed pointer blobs alone cannot pass.
3. `check_submodules.py` must report `PASS`, 160 exact gitlinks and 161 inspected
   repositories. Its positive and deliberate-corruption fixtures must all pass
   without skips, including missing nested children and physical-file damage.
4. Regeneration must produce a byte-identical lock. Compare all 149 root gitlinks
   to the accepted P001 source evidence; the URL-only repair changes no pins.
5. Obtain a **different agent/person's** source and evidence review for the exact
   implementation revision and both raw hosted artifacts. Authors cannot approve
   their own work. Commit the verdict and both raw campaigns under this evidence
   directory before marking P002 passed or advancing to P003.

The dated acceptance record must identify workflow/artifact URLs, the tested SHA,
archive hashes and independent reviewers. Missing or failing evidence means
ACTIVE, READY FOR REVIEW or BLOCKED, never PASSED.
