# Candidate b6f4d9bf: recovered frozen inputs and hosted preflight

Exact implementation: `b6f4d9bf04dd4a15a1b349845f962295ff350b7d`, tree
`202dbdc59c0bd9df10804b9e3a75674508eab75d`.
[Run 42177445982](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42177445982)
passes all **174 P001 / 115 P002 / 200 P003** hosted regressions, zero skips.
The unchanged original four-member fixture ZIP is retained here.

The actual hosted toolchain acquisition restores and verifies the exact retained
original frozen archive at 06:55:14 UTC, including all five members and CRCs, unchanged
recipe/environment, sealed image bytes and original checksums. Its [original
printed receipt](original-retained-origin.json) is extracted without alteration
from the complete decoded runner log; `gzip -dc toolchain-job.log.gz` reconstructs
that original log. [Preflight receipt](preflight.json) records all hashes and
identities and explicitly states the connector's local full-image download limit.

Both fresh recursive build checkouts are active. This prerequisite evidence
does not constitute G1–G4 acceptance. Full current build archives, all five actual
runtime campaigns and independent Wave 4/Wave 5 decisions remain required.
