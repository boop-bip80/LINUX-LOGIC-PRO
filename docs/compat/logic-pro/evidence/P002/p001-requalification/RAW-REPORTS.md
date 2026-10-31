# Complete P001 requalification raw reports

**Publication pending:** the complete archive has been built and independently
validated locally, but its large GitHub upload is still pending. This candidate
publishes the manifest, restoration reader and small logs first. The archive
must be committed before the commands below can succeed from a clean checkout
and before P002 may be marked PASSED.

`raw-reports.tar.xz` preserves every uncompressed member of both original P001
requalification artifacts from [workflow run 41246526024](https://github.com/boop-bip80/MAC-OS-EMULATION/actions/runs/41246526024),
at implementation commit `3043fdfe9ef4ce3c1a8485fcecbd42ebb355dde7`.
This is the historical source-evidence requalification associated with P002;
it is not a new run, a runtime-compatibility result, or a qualification of later
implementation changes.

The preservation includes **all 32 original members, totaling 398,117,923 raw
bytes**: original checksum files, summaries, commands, six command logs per
host, inventories, recovery reports, source-retrieval reports, classifications,
and initial/final tracked-file manifests. The complete mapping, original ZIP
provenance, byte counts, SHA-256 hashes, and CRC32 values are in
[`raw-reports.manifest.json`](raw-reports.manifest.json).

## Original downloaded artifacts

| Host | Runner OS | Artifact ID | Original ZIP bytes | Original ZIP SHA-256 |
| --- | --- | ---: | ---: | --- |
| a | Ubuntu 22.04 | 13059652667 | 22,159,243 | `0d74179fd13f3544bc6e1f150fe29a2d9f4fcfe895d6aca421d465595e393cbf` |
| b | Ubuntu 24.04 | 13059608360 | 22,159,502 | `e100f49d7cb30a65c315a2acdb007e47dfb9abe163cb550f7b98863327a64970` |

The builder verifies these original ZIP sizes and digests before reading any
members. The original checksum manifests and command-log hashes are then checked
against the exact extracted bytes. Nothing in a raw JSON or log was reformatted,
redacted, repaired, or regenerated.

## Lossless deduplication and archive format

The four initial/final tracked-file manifests are byte-identical, as are several
small reports/logs. Identical payloads are stored once as `objects/<sha256>`.
The 22 distinct payloads total 105,568,119 bytes before compression.

The archive is **9,667,936 bytes**, SHA-256
`5f431af649f7a261249000cf6cd727b9b13ad686e881ddcd22e4db2d29a38b0d`.
It is an XZ-compressed USTAR file (XZ preset 6, CRC64). Object names are ordered
lexicographically; entries are regular files with mode `0644`, UID/GID/mtime
zero, and empty user/group names. There are no symlinks, hardlinks, absolute
paths, external references, or network dependencies.

The manifest maps each `(host, original member name)` to its content-addressed
object, raw SHA-256, size, and CRC32. Shared objects are expanded into separate
files during restoration. The **original member bytes and filenames are fully
reconstructible**. The original ZIP container byte streams, ZIP metadata,
compression streams, and ZIP timestamps are not reconstructed; their exact
downloaded-container sizes and digests remain recorded above and in the
manifest.

Six original command logs and the original checksum manifest for each host are
also present as directly readable `*-a.*` / `*-b.*` files, alongside the already
published classifications, commands, and summaries. The five previously missing
small logs are `revision`, `inventory`, `recovery`, `classifications`, and
`final-source-verification`. The sixth is the full `fixture-tests` transcript.
Host suffixes distinguish copies; references inside each original JSON retain
their original filenames. Restore a host directory before using tools that
expect those original names.

## Verify or restore without GitHub access

Python 3.10 or newer with the standard-library `lzma` module is sufficient.
From the repository root:

```bash
evidence=docs/compat/logic-pro/evidence/P002/p001-requalification
python3 "$evidence/raw_evidence_bundle.py" verify
python3 "$evidence/raw_evidence_bundle.py" restore --host a --output /tmp/p001-host-a
python3 "$evidence/raw_evidence_bundle.py" restore --host b --output /tmp/p001-host-b
```

Each restore destination must not already exist. Restoration first verifies the
archive, all 22 payloads, all 32 member mappings, and all 20 directly published
copies. It also checks the 15 original checksum entries and six command-log
references per host, revision, summary, source-retrieval digest, and tracked-file
references. Restored files are opened exclusively and checked again while being
written. `verify` is read-only and does not require the original ZIP files.

The complete restored reports may be passed to
`tools/compat/logic-pro/run_baseline.py`'s `check_reports` function with the
historical P001 `remote-snapshot.json` oracle. This rechecks the archived reports;
it does not rerun the original source acquisition or fixture commands.

## Rebuild from the exact downloaded ZIPs

To reproduce the archive and mapping, use the two original downloads matching
the sizes/digests above. The artifact download endpoints are recorded in the
manifest; GitHub artifact availability/authentication may vary over time.

```bash
evidence=docs/compat/logic-pro/evidence/P002/p001-requalification
bundle_dir=$(mktemp -d /tmp/p001-bundle-rebuild-XXXXXX)
python3 "$evidence/raw_evidence_bundle.py" build \
  --zip-a /path/to/P001-green-a.zip \
  --zip-b /path/to/P001-green-b.zip \
  --directory "$bundle_dir" > "$bundle_dir/raw-reports.manifest.json"
cmp "$evidence/raw-reports.tar.xz" "$bundle_dir/raw-reports.tar.xz"
cmp "$evidence/raw-reports.manifest.json" "$bundle_dir/raw-reports.manifest.json"
python3 "$evidence/raw_evidence_bundle.py" verify --directory "$bundle_dir"
```

The builder uses a temporary content store and refuses to overwrite differing
existing files. Its output contains no acquisition timestamps or temporary
paths. Archive construction uses the Python standard library and liblzma;
byte-for-byte deterministic rebuilding was checked with the recorded producer
environment in `raw-reports-validation.json`. Raw SHA-256 member identity is
the preservation invariant even if a future compression-library release emits
a different valid XZ stream.
