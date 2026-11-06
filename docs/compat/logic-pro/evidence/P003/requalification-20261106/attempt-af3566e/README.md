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
Both build jobs complete all 16,594 compile actions and print first/second runtime
PASS summaries, then fail artifact upload with EACCES on root-owned 0600 final
source status. No A/B archive is finalized; downstream replay and comparison
are skipped. These producer observations do not pass any current gate.

[Complete failed-publication receipt](failed-publication.json) records original
job status, finalized artifact inventory, selected exact log lines and raw/gzip
hashes. `gzip -dc build-a-job.log.gz` and `gzip -dc build-b-job.log.gz` reconstruct
the complete original decoded job logs. A fresh full run after the permission
repair must retain the archives and receive independent acceptance.
