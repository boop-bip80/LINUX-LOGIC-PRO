# P001 acceptance and failure history

The current P001 verdict is `../acceptance.json`, accepted at implementation
`4707a919ef304945f7685390a68429242657eb54`. This directory retains earlier
observations so resolved failures and the earlier false pass remain auditable.

- `parent-only-acceptance.json` is the exact earlier acceptance record. Its
  parent-only scope did not satisfy the original recursive requirement.
- `parent-only-evidence-index.json`, `parent-only-independent-clone-check.json`
  and `parent-only-inherited-ci-failure.json` preserve the earlier evidence.
- [All original parent-only reports and logs](https://github.com/boop-bip80/MAC-OS-EMULATION/tree/2f945a0356b5c719a0dbafc66fe7c028eaf4a4f6/docs/compat/logic-pro/evidence/P001)
  remain available at their immutable Git revision.
- `reopened-acceptance.json` records the withdrawal of the earlier full-phase
  claim before the strict recursive implementation was hosted.
- `resolved-findings.json` indexes the actual failed development retrievals,
  raw-byte checkout problem and verified libffi correction. Compressed reports
  contain the original bytes; they are failure history, not passing evidence.

The two older review files at `../reviews/inventory-and-source.json` and
`../reviews/recovery-and-campaign.json` describe the historical parent-only
campaign. Current complementary reviews are in the two `recursive-*` folders.
No original source pin, committed `.gitmodules` URL or committed `.gitattributes`
was changed to obtain the new P001 acceptance.
