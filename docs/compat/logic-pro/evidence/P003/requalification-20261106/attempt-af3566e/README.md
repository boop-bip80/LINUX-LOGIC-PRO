# Candidate af3566e: original hosted preflight

Exact source: `af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`.
[P003 run 42169925661](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42169925661)
passes its original mandatory preflight job: **174 / 115 / 187**, zero skips.

`fixtures.zip` is the unchanged official artifact `13480895155`, 11,383 bytes,
SHA-256 `8df781803f0253e5843d4167b7e4c45eb95808683734fd4d2bcc6fefd3947792`.
All four CRC members and each original transcript's result/count were checked.
[Receipt](preflight.json) records exact identities and the qualification boundary.

The frozen-toolchain acquisition and exact environment comparison succeeded at
05:45:35 UTC. [Original job log and artifact identities](toolchain-acquisition.json)
are retained; `gzip -dc toolchain-job.log.gz` reconstructs the decoded raw log.
Both full build containers are running. These prerequisite results do not pass
any current P003 runtime gate. Wave 3 performs independent code and original-evidence review.
