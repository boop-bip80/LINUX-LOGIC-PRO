# Wave 3 independent object-integrity and campaign review

**Date:** 2026-11-06

**Reviewer:** `/root/wave3_integrity_review` (non-author review)

**Reviewed source:** `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`

**Decision:** **Implementation approved in the scope below.** This is not P001 or P002 phase acceptance.

## Scope and contract

This review covers canonical Git blob verification in `tools/compat/logic-pro/inventory.py`, the physical checkout and restricted CRLF exception in `tools/compat/logic-pro/check_submodules.py`, and the current-provenance CLI and complete anonymous workflow in `tools/compat/logic-pro/run_submodule_campaign.py` and `.github/workflows/phase2-submodules.yml`. The repository `AGENTS.md` and root README P001/P002 acceptance requirements were reviewed. Separate reviewers own the provenance lock and baseline implementation.

The acceptance obligation remains all **160 gitlinks (149 direct and 11 nested)** and **44 LFS objects with actual payload bytes**, acquired in isolated anonymous checkouts without an existing object cache or authentication. The historical P001 evidence and recovery obligation are unchanged. Hosted artifact acceptance is reviewed separately in the subsequent ordered review waves.

## Independent reproduction

The retained [object-integrity reproducer](object-integrity/reproduce.py) was run against both the repaired worktree and a fresh temporary extraction of `tools/compat/logic-pro` from old commit `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`. The extraction and reproduction repositories were temporary and were not reused as qualification checkouts.

The fixture replaces a real loose Git blob with different bytes under the expected object's path and makes the physical `.vcxproj` checkout match those forged bytes with CRLF endings. The requested object ID is `4b48deed3a433909bfd6b6ab3d4b91348b6af464`.

| Source | Observed result |
| --- | --- |
| Old `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a` | `read_blobs trusts forged bytes: True`; `verify_checkout` returned `verified_blobs: 2` and `standard_crlf_paths: ['project.vcxproj']`. |
| Repaired `d58cca513559cfef0ff9af59aa5dc3b6341bdf77` | Both `read_blobs` and `verify_checkout` raised `InventoryError: committed blob content does not match its object ID`. |
| Independent Git integrity check in both fixtures | `git fsck` exited 3, reporting the missing expected blob and a hash-path mismatch for the forged object. |

This independently confirms the old false pass and the repaired rejection before the CRLF exception can authorize forged content. The original before/after evidence remains in the [object-integrity evidence directory](object-integrity/README.md).

## Implementation findings

### Blob identity and physical checkout

The batch blob reader now recomputes the canonical Git object digest over `blob <byte-length>\0` followed by the payload. It selects SHA-1 for 40-character object IDs and SHA-256 for 64-character IDs, and rejects a mismatch before returning the bytes. Batch response framing and a repeated requested object ID therefore cannot substitute for content integrity.

The physical reader uses directory-relative opens with `O_NOFOLLOW`, requires a regular leaf file, checks executable mode, and checks file metadata after reading. The checkout verifier compares the committed tree and index, rejects checkout overrides and remaining changes, and checks untracked content including ignored paths.

The CRLF exception remains confined to committed attributes declaring `text` and `eol=crlf`, without filter, ident, or working-tree encoding transformations. Its committed source must be a verified blob containing LF and no CR or NUL; the physical bytes must equal the exact LF-to-CRLF conversion. Valid committed CRLF checkouts remain supported.

### Campaign and hosted workflow

Lock regeneration explicitly passes `--evidence-mode reviewed-current` and retains the byte-for-byte comparison with the committed lock, including SHA-256 diagnostics. A semantic JSON match alone cannot pass this gate.

The campaign requires an immutable expected source SHA, verifies source and cloned HEAD, creates a fresh destination, rejects existing destinations and unsafe/overlapping evidence paths, and retains command output, exits, and checksums on failure. Its production CLI permits HTTPS acquisition; the local-protocol fixture option is not exposed there. Authentication-related environment settings are removed, Git credentials and prompts are disabled, and a pre-existing netrc file is refused.

Successful completion requires the full fixture suite, strict LFS hydration, independent native recursive submodule status, strict physical inventory, and byte-identical lock regeneration. The workflow runs that complete campaign on separate Ubuntu 22.04 and Ubuntu 24.04 matrix jobs, binds the expected source to `github.sha`, uses checkout without persisted credentials or preloaded submodules, and uploads evidence even after a failed campaign. No shortened second-host path or object-cache reuse was identified.

## Independent validation

The following commands ran in the reviewed worktree and completed successfully:

```sh
python -B -m unittest discover -s tests/compat/logic-pro/submodules -p test_object_integrity.py -v
python -B -m unittest discover -s tests/compat/logic-pro/submodules -p test_campaign.py -v
```

| Suite | Result | Relevant coverage |
| --- | --- | --- |
| Object integrity | **4 tests passed** | Real corrupt loose blobs in SHA-1 and SHA-256 repositories; forged CRLF rejection; valid CRLF checkout; valid empty, binary, and duplicate blob reads in both object formats. |
| Campaign | **18 tests passed** | Explicit current provenance regeneration and byte equality; failure/timeout evidence; immutable/exact source acquisition including advanced branches and PR-only commits; native status; full physical/LFS inventory; stale, overlapping, existing, and symlink destinations; sanitized environment and netrc refusal. |

The old/new reproductions above were also rerun independently. The broader integrated suite counts are author validation and are not substituted for these independent checks or for hosted qualification.

## Approval and remaining acceptance work

No concrete implementation defect was found in this bounded review, and no code change is requested. **The reviewed object-integrity, physical-checkout, and campaign implementation is approved at `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.**

At review completion, the coordinating reviewer reported successful P001 and P002 hosted campaigns at the exact reviewed source, with original artifact digests, internal checksums, and command segments verified. This implementation reviewer did not independently accept those hosted artifacts; full clone B and LFS artifact acceptance belongs to the next review wave.

This decision does not itself certify current public availability of every dependency, completed payload acquisition, a successful hosted campaign, or phase acceptance. P001/P002 remain pending ordered wave 4/5 acceptance review. The 160-gitlink/44-payload contract must not be reduced, and P003/P004 are not reaccepted by this review.
