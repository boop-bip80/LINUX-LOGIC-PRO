# Candidate cc268442: hosted preflight and acquisition outage

Exact implementation: `cc268442e9711beeb117f59850dcc6526dd03c46`.
[Run 42175768705](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42175768705)
passes all **174 P001 / 115 P002 / 188 P003** hosted regression cases, zero skips.
The unchanged original fixture archive is retained here.

Toolchain attempts 1, 2 and 3 fail closed when the fixed Ubuntu snapshot returns
HTTP 500/502/503 for its signed InRelease metadata. No current build is started and
no runtime acceptance is inferred. All three identical attempts fail. The next candidate restores the exact
hash-pinned retained toolchain inputs and verifies them against the unchanged
recipe, base digest, snapshot, packages and tool identities.

[Receipt](preflight-and-outage.json) binds all original archive byte counts,
SHA256 hashes, CRC-verified member counts, job IDs and raw runner-log hashes.
The three failed acquisition ZIPs are retained unchanged. `gzip -dc` reconstructs
each complete original decoded runner log. Independent Wave 4 and Wave 5 review
still requires the fresh full build archives and five runtime campaigns.
