# P001 independent audit procedure

Reviewer: `/root/phase1_audit`. No production code was authored or changed by
this reviewer. The reviewed implementation is `78dff3235e95d90e43faa4af7de34d5f926c9d28`;
`f7bd711013d3c41c3eee4ec76926bfe3a152cb46` adds only README/evidence-index text.
The source/test blob identities in `source-blobs.json` were checked before testing.

Run the complete isolated Git fixture suite from the exact implementation:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/compat/logic-pro/baseline -v
```

Observed: 113 tests, all successful, zero skipped tests and zero expected failures.

Run actual original-source recovery from a parent clone containing full history:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 tools/compat/logic-pro/recover_baseline.py \
  --repo . --manifest docs/compat/logic-pro/baseline.json --output /tmp/p001-recovery.json
```

Observed: both original source and initial roadmap recovered in new separate
object stores; 27,125 physical blobs checked per snapshot, with exact recorded
commit/tree/README identities, 528 executables and 2,890 symlinks per snapshot.

`verify_p001_evidence.py` independently checks all 103 historical evidence index
entries, the ordered 11-part archived manifest, both 15-entry original checksum
tables, and all 160 unchanged pins against both current hosted inventories and
the current P002 lock:

```sh
python3 verify_p001_evidence.py --repo /path/to/repo \
  --hosted-exports hosted --output retained-evidence-reproduction.json
```

The `hosted/` JSON files were independently decoded from the seven
`P001_EVIDENCE` records in each job's log. Each export's SHA-256 was checked
before writing it. The six ordinary reports also match the seventh exported
checksum table. The actual source run is 41253918642; jobs 124692950136 and
124692950242 both completed successfully at exact implementation 78dff323.

Full recursive source acquisition was observed in those two isolated hosted
campaigns. The available local cached checkout has no initialized dependencies;
strict inventory and classification invocations correctly rejected it (149
uninitialized gitlinks and 28 unavailable child citations). This local negative
case is not substituted for a complete local recursive source acquisition.

During review, the separate tooling auditor identified a summary-parser
false-pass involving unittest expected failures. Actual reviewed logs contain
only successful tests, so their measured results remain valid. The upcoming
fix and any later implementation commit are expressly outside this approval;
they require their own independent review and hosted qualification.
