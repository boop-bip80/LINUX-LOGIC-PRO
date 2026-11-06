# Wave 3 independent P001 prerequisite implementation review

- **Reviewer:** `/root/wave3_baseline_review`, independent of the scoped implementation authors.
- **Date:** 2026-11-06 UTC.
- **Verdict:** **APPROVED FOR IMPLEMENTATION INTEGRATION**. No additional reproducible defect was found in the reviewed changes. This review does not accept P001 or P002, or reaccept P003/P004.
- **Reviewed implementation:** `6cb6cada6fb48da501a255e69c049fcde1798a79`, compared with `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`.
- **Integrated candidate:** `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`. An independent `git diff --exit-code` confirmed that all five scoped production files below are identical between the reviewed implementation and this candidate.

## Scope and preserved anchors

The review covered `run_baseline.py`, `verify_classifications.py`,
`prepare_sources.py`, `classifications.json`, the supporting
`source_provenance.py`, and their relevant fixture tests. The mandatory
`AGENTS.md` rules and README phase contract were read before review. The
physical Git blob hashing repair in `inventory.read_blobs` belongs to the
separate integrity review; this report does not approve that implementation.

The distinct historical identities remain explicit:

| Identity | Exact commit |
| --- | --- |
| Original citation inspection | `b25035fce2cd1c038c567d34ea0797371947d95d` |
| Historical source retrieval anchor | `4707a919ef304945f7685390a68429242657eb54` |
| Historical accepted phase anchor | `89c6c9d85aba6ed1662035e6366298c92ef9c970` |
| Reviewed current source anchor | `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a` |

The reviewer directly compared the original `evidence` array and
`inspected_commit` with the manifest committed at the current source anchor:
both are unchanged. The current supplement contains exactly the same 63 unique
citation IDs. Loading the frozen source provenance independently succeeded with
160 historical and 160 current recursive records, including the 14 reviewed
changes. These are metadata and frozen-evidence checks; this review did not
independently repeat the complete 63-citation source-object campaign.

## Findings and reasoning

### Historical and current source chains remain independent

`verify_classifications.verify` first resolves each original citation through
the original parent commits and checks its original object, excerpt and
assertions. `verify_current_source` separately resolves the current chain
against the fixed reviewed anchor, then against the requested current root and
actual child HEADs. The current object must match both the anchor and the
current audit record. Historical-only verification can succeed without current
anchor objects; current verification still requires that anchor.

The aggregate also checks both chains against separately frozen historical and
current graphs. Refreshing a citation result and its accompanying metadata
together cannot authorize an unreviewed parent, child pin, or ownership chain.
The historical recovery oracle remains separate from the current graph.

### Complete coverage is bound to the immutable original manifest

The current supplement and emitted checked records must have the complete,
unique original ID set. The aggregate compares each original receipt with its
original manifest entry and verifies source categories and required launch
stages from the records themselves. Missing records, duplicate IDs, shortened
coverage, or rewritten historical blobs cannot be concealed by a PASS summary.
The runner additionally compares the original manifest data with committed
anchor data before aggregating the current audit.

### Current citations are bound to the physical source inventory

The aggregate checks the complete current recursive graph against frozen pins,
trees, parents and origins. It crosschecks tracked gitlinks, repository owners,
index pins, physical materialization counts and current checkout identities.
Each current citation's expected blob must occur at its exact owned path in the
tracked inventory. The runner performs a second inventory after all evidence
commands and requires stable source, repositories, submodules, tracked digest,
issues and summary. The separate canonical blob hashing repair remains a
required dependency of the integrated physical verification.

### The current CMake allowance is limited to the reviewed bytes

For root CMake citations, the current guard reverses exactly the approved staged
install replacement before invoking the existing P003/P004 byte reconstruction
checks. Those checks retain the exact P003 predecessor object and require the
entire reconstructed byte sequence, not just matching excerpts or refreshed
digests. Existing negative tests modify the guard environment variable, install
target, version restriction and unrelated trailing bytes while refreshing the
audit metadata; all fail. The `.gitmodules` allowance remains the exact set of
149 URL rewrites.

### Frozen child history is explicitly fetched in shallow checkouts

`fetch_historical_citations` verifies every historical gitlink hop in its parent
tree, fetches the exact child commit from the already verified acquisition URL,
resolves the returned commit, and confirms that current HEAD did not move. It
performs the child fetch even when the object is already cached. The focused
fixture proves that both old child and nested commits are absent before their
initial fetch, and proves that a second run still issues both explicit fetches.
Missing historical objects, altered chains, owners or blobs fail without moving
the current child checkouts.

## Independently executed checks

| Check | Observed result |
| --- | --- |
| `python3 -m unittest discover -s tests/compat/logic-pro/baseline -p 'test_*.py' -v` | **174 tests, OK**, 20.425 seconds |
| `python3 -m unittest discover -s tests/compat/logic-pro/submodules -p test_source_provenance.py -v` | **12 tests, OK**, 1.665 seconds |
| `verify_campaign_fixture_suite` on the retained raw baseline transcript | Exactly **174**, with a complete unique verbose record and plain final OK |
| Compare historical manifest data with committed `c7ef7fe4` data | Unchanged original evidence and inspection commit |
| Compare original/current citation ID sets | Exactly **63 unique IDs** in each, identical sets |
| `load_reviewed_source` on committed frozen evidence | Verified evidence digests and both 160-record graphs; **14** changed records |
| Diff scoped production files from `6cb6cada` to `d58cca51` | Empty; exit **0** |

The baseline transcript is retained as
[`wave3-baseline-review-tests.log`](wave3-baseline-review-tests.log): **30,833
bytes**, SHA-256
`dfa95cc18a59ef0f3548c362e1e3cc4bacbcf6e138681162b6b71e8f4c13985f`.
No tests were weakened or removed, and no production change was needed for this
review. The existing test-count floor was left unchanged; the complete current
174-test suite was actually executed and its transcript validated.

## Exact scoped file digests

| File under `tools/compat/logic-pro/` | SHA-256 |
| --- | --- |
| `run_baseline.py` | `7caf98372482001ab9a59748cd9512dd0a66f4a7f1f0d766c62adc2ea130f256` |
| `verify_classifications.py` | `9be2c655c419ab8d44d6b2e59f45b86ac7f0dd5c87a321ac3b5c0bcb87eb9a79` |
| `prepare_sources.py` | `b22dab2469f7af402f609aaba2e23f6bb7d4b4c1b1be3b947fb340a19ad99547` |
| `classifications.json` | `177bc2daa9cd7c8f6e4bd3f97ae396e28283efb32f77fc6ae9918499545bea11` |
| `source_provenance.py` | `3d9bb043c51e994c027843fafee489c902b18d8595081bd779ed7ed1943d2214` |

## Limits and handover

This bounded implementation review used repository tooling, synthetic Git
fixtures and committed provenance evidence. It did not inspect restricted Apple
or corecrypto implementation source, use a native macOS oracle, execute Logic
Pro, or make a runtime compatibility claim.

Root-reported hosted successes and the complete local source rehearsal are not
substitutes for this review's independently executed checks and are not accepted
here as phase evidence. The next reviewer must assess the exact-SHA hosted
artifacts, isolated clone results, original archived bytes and checksums, and
ordered P001/P002 acceptance under the phase contract. The separate integrity
repair review must also be integrated. P003/P004 remain outside this verdict.
