# P002 wave-two committed object integrity repair

The original implementation at `aa9e047c7b700a9dd003844012425dcbbc9a43b3`
accepted a corrupt loose Git blob stored under the expected object ID. Git's
`cat-file --batch` returned that requested ID with the replacement bytes, so
valid batch framing did not prove the blob's identity. A matching forged CRLF
worktree then passed `verify_checkout` through its restricted conversion waiver.
The independent `git fsck --full` oracle rejected the repository with a hash-path
mismatch (exit 3).

`inventory.read_blobs` now hashes the canonical Git blob header and bytes using
the object ID's SHA-1 or SHA-256 format before returning any trusted content.
The same fixture now raises `InventoryError` in both `read_blobs` and
`verify_checkout`. The restricted valid CRLF case remains accepted.

## Reproduction and retained output

Run the included script against either source checkout. It creates and removes
only its own temporary repository; it does not modify the supplied source.

```sh
python -B docs/compat/logic-pro/evidence/P002/requalification-20261105/object-integrity/reproduce.py /path/to/source
```

- [before.txt](before.txt): actual output against the unchanged original code.
- [after.txt](after.txt): actual output after the hash check in this revision.
- [tests-before.txt](tests-before.txt): four new tests before repair; three
  failures across the corruption cases, with valid blobs and valid CRLF passing.
- [tests-after.txt](tests-after.txt): the same four tests after repair; all pass.

The new fixtures exercise real loose objects in both SHA-1 and SHA-256
repositories, valid empty/binary/duplicate batch reads, and the CRLF false-pass
path. The campaign also explicitly requests `--evidence-mode reviewed-current`
instead of the historical P001 report; its regression checks the command and
retains the byte-exact lock comparison. All 18 campaign tests pass locally.

The complete submodule suite ran 102 tests on this branch, with 101 passing and
one existing stale-provenance error in
`test_actual_lock_is_reproducible_from_p001`: `pin changed without new source
evidence: src/external/bootstrap_cmds`. The parallel lock repair has not been
merged into this isolated branch. The complete original output is retained in
[suite-before-integration.txt](suite-before-integration.txt); the failed check
was not bypassed or weakened.

This is a local regression repair and handover, not P001 or P002 acceptance.
The reviewed-current generator belongs to the parallel lock repair; integrate
both changes before the exact-source hosted campaigns and independent review.
