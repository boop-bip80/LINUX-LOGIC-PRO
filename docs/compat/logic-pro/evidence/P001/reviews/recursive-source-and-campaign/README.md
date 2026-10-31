# Independent P001 review evidence

This directory belongs to reviewer `/root/source_map`. The acceptance scope and
original-author exclusions are in `final-independent-review.json`. Every asset
has a byte count and SHA-256 in that record. Hosted logs were independently
retrieved through the GitHub connector, not copied from the implementation
agent's local assertions.

## Reproduce the independent comparisons

Use a checkout of implementation `4707a919ef304945f7685390a68429242657eb54`.
The production P001 reproduction procedure obtains its exact recursive sources.
All source Git commands in the native oracle disable ambient Git selectors,
replacement objects, optional locks and network transports.

```sh
python3 native-source-oracle.py --repo /path/to/full-pinned-checkout --inventory /path/to/inventory.json --tracked /path/to/tracked-files.json --output /tmp/independent-oracle.json
python3 synthetic-campaign-reproduction.py --implementation-root /path/to/implementation-checkout --output /tmp/new-empty-independent-campaign
```

The synthetic reproduction builds fresh local Git histories, including a nested
source dependency and all mandatory source-owner paths, then runs the actual
production tools. Its tiny source functions are fixture data, not runtime proof.
The supplied implementation must retain the published code hashes documented
in `published-code-review.json` to reproduce this reviewed version.

The two `*-job.log.gz` files contain the complete independently fetched job logs.
Each `P001_EVIDENCE` record contains a filename, raw SHA-256 and base64-encoded
zlib stream; verify the decompressed bytes against that digest. The per-host
review JSON records all seven export hashes. `primary-git-tree-responses.json.gz`
contains the exact saved response texts and hashes for the eight upstream GitHub
trees used to independently verify all eleven nested gitlinks. No source or
symlink target is executed by those comparisons.
