# Original hosted evidence at d58cca51

Implementation: `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
This archive preserves all **70 original raw members** from the four successful
P001/P002 hosted artifacts. It records producer outcomes; independent phase
acceptance is recorded separately after review.

## Observed campaigns

| Campaign | Hosts | Original result |
| --- | --- | --- |
| [P001 run 42155822562](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822562) | Ubuntu 22.04 / 24.04 | 174 distinct tests each; 160 gitlinks, 161 repositories, 293,660 tracked entries, 755 license/notice candidates, 63 old/current citations; both original snapshots restore 27,125 physical blobs each |
| [P002 run 42155822754](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/42155822754) | Independent clone A / B on Ubuntu 22.04 / 24.04 | 115 distinct tests each; 160 native/locked gitlinks, 161 repositories, 293,500 physical files, all 44 LFS payloads / 16,128,448 bytes; byte-identical lock regeneration |

The downloaded ZIP sizes and SHA-256 values matched the original GitHub
artifact metadata. Every ZIP member passed CRC. All 66 internal checksum
entries and all 38 command-log segments passed; every recorded command exited
zero. Both phases identify the exact implementation above, and all four jobs
concluded successfully. Original GitHub run/job responses are retained here.

## Complete byte retention

[artifact-manifest.json](artifact-manifest.json) maps every original member to
its exact raw size, SHA-256 and stored path or compressed payload. Original
GitHub artifact IDs, ZIP digests, source identities and expiration dates are
retained independently of the data representation. The two P002 ZIP containers
are also retained byte-for-byte under `original-zips/`. For P001, every raw ZIP
member is retained; the large ZIP containers are represented by their original
hashes and complete member mappings. No summary replaces a raw member.

The four initial/final complete tracked manifests are byte-identical:
**97,657,320 bytes**, SHA-256
`c2995040954cc2f844994ac8854ee51607c15a9a3c0a552f4ae53fa1635cd0cd`.
They share one losslessly compressed XZ payload (9,342,836 bytes) in 18 ordered
binary parts. The manifest binds each part and both the compressed and raw
whole-file digests. Large inventory/retrieval JSON members are also retained
losslessly; small reports and logs remain directly readable.

## Verify and reconstruct

From any working directory, run the committed reader by its path:

```sh
python3 -B docs/compat/logic-pro/evidence/P002/requalification-20261105/hosted-d58cca51/verify_archive.py
```

Add `--destination /tmp/p002-d58-replayed-evidence` to reconstruct the exact
original directory/file names. The destination must be new. The reader verifies
all part, payload, member and retained-ZIP hashes before writing any output.
Its result concerns archive bytes and does not declare phase acceptance.

For a new acquisition campaign, check out the exact implementation and use
`tools/compat/logic-pro/run_submodule_campaign.py` with a new destination, new
output directory, `--commit d58cca513559cfef0ff9af59aa5dc3b6341bdf77` and host ID
`a` or `b`. Git LFS must be installed. The recorded commands in each artifact
contain the complete actual invocation, versions, output boundaries and exits.

Provenance: original GitHub Actions artifacts, public Git metadata, the existing
repository acceptance contract and source-verification tools. No restricted
implementation material was used.
