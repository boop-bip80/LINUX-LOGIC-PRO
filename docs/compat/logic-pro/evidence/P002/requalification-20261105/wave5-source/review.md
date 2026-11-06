# Fifth-wave independent source and regression-integrity review

- Reviewer: `/root/wave5_final_source`, not an author of the production changes.
- Review time: `2026-11-06T04:26:18Z`.
- **Verdict: SOURCE APPROVED. No blocking source or regression-integrity finding.**
- Tested production: `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
- Reviewed public publication: `9b2ce08d9012091e23173b8ac1a37b5c0e98359c` (including Wave 4 acceptance records and the final-wave ledger corrections).
- Original starting source: `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`.
- Machine-readable results: [summary.json](summary.json) and [tree-identity.json](tree-identity.json).

This is a technical source approval. It does not set P002 to PASSED, reaccept a later phase, or establish runtime/application compatibility. The independent final evidence reviewer owns the P002 acceptance decision.

## Exact source identity

The review compared recursive Git trees using `git ls-tree -r -z`, retaining path, mode, object type and blob/gitlink object identity. The tested tree contains 27,850 tracked entries. Across all 137 paths changed after the tested commit, every change is in the root README or the exact P002 requalification evidence subtree. All 27,812 paths outside that review scope have identical tree entries. This covers production tools, native sources, tests, workflows, build files, the baseline and lock, and older evidence outside that subtree.

The evidence subtree was not treated as harmless merely because it is under `docs/`. Nine consumed contract/provenance inputs were checked explicitly for identical tested/publication tree identity and SHA-256 bytes: baseline JSON, dependency lock, classification manifest, LFS provenance, the historical P001 source report and remote snapshot, and the current source-inspection XZ, its manifest, and upstream pin review. All are unchanged. The current frozen data inside the permitted documentation subtree therefore remains protected by an explicit comparison.

The production `source_provenance.load_reviewed_source` loader was also executed locally with bytecode writes disabled. Its frozen-digest and semantic checks passed both complete 160-record graphs, exact source anchors, current archive/manifest bytes and the reviewed 14-change provenance. The historical 63 citation records and inspected commit are structurally identical to the original starting manifest; the separate current-source audit retains all 63 records. No broad acquisition or already-satisfied test matrix was rerun.

All newly added Python files after the tested commit are review reproducers or archive auditors in the evidence subtree. A literal-reference scan of production tools, tests and CI found no references to those helper filenames. They do not alter the qualified execution path. The full changed-path list and all explicitly checked input hashes are preserved in `tree-identity.json`.

## Original-to-tested production review

The original-to-tested comparison changes no native source, build file, workflow or root gitlink. All 149 root gitlinks retain their original mode and object identity. The source repair is confined to compatibility qualification tooling, its regression cases, source-contract data and documentation/evidence. The 13 direct and one nested dependency differences relative to the historical P001 graph predate this repair and are explicitly reviewed against the current starting anchor; this review found no silent new dependency update.

The production changes preserve and extend the original requirements:

1. The current-source loader verifies fixed byte digests before interpreting historical/current evidence, validates the complete path sets, anchors, parents, pins, trees and public URLs, and requires the exact reviewed 14-change coverage. Arbitrary refreshed reports cannot authorize new dependencies.
2. Lock generation accepts only the frozen historical or reviewed-current report. Its conservative Git pin, URL, graph and LFS validation remains. The campaign invokes the tool from its acquired checkout and compares regenerated lock bytes exactly.
3. Historical citation acquisition explicitly fetches each old exact pin and validates its chain/blob without moving any current checkout HEAD. Classification verification retains the frozen historical blob, excerpt and assertion checks, then independently checks the current anchor, owner chain, actual HEAD, exact blob/excerpt and unchanged assertions.
4. Baseline reporting still binds the immutable historical direct-gitlink oracle and recovery checks. Current-source reporting additionally requires the full reviewed 160-node graph and all historical/current citation identities. Missing, duplicated, mismatched or unreviewed records fail closed.
5. Inventory now recomputes each raw Git blob's canonical object hash, including the Git object header, before checkout-conversion comparisons. Existing batch framing/type/size checks remain. This addresses the independently reproduced forged loose-blob defect without relaxing normal CRLF handling. Real SHA-1/SHA-256 corruption and native tree-object rejection evidence already exists in the prior waves and was not redundantly rerun.

The approved CMake source predates the reviewed repair. Its citation adaptation reverses exactly one known staged-install guard before checking the earlier immutable predecessor hash. That operation does not authorize unrelated source changes or replace the previous P003/P004 source-delta constraints.

## Regression integrity

The AST method inventory across `tests/compat/logic-pro/` records 545 original methods and 586 current methods. The inventory is a source comparison, not an assertion that this review executed 586 cases. Exactly one original method name is absent: the historical-report-positive lock test. It is replaced by the reviewed-current lock positive, which retains semantic equality and the 160-dependency check, adds exact serialized-byte equality and the 44-LFS count, and is paired with an explicit rejection of using the historical P001 report to authorize current pins.

Seven retained methods have modified bodies. Six source-equivalence negatives preserve rejection and source-identity assertions while updating the expected rejection reason or using a valid nonzero gitlink fixture. A separate missing-pointer case now reaches the pointer gate without being stopped first by the documentation-deletion gate. The remaining method preserves the approved CMake delta predecessor hash after reversing the one exact already-reviewed staged-install guard. Its associated new negatives reject altered guards, unrelated source and refreshed forged metadata. No original negative requirement is turned into a success expectation or skipped.

The original eight P001/P002 gate cores were independently checked as unchanged by the final ledger reviewer. This source review independently inspected the affected production and test diffs and found no weakened gate semantics. Existing hosted 174-case P001 and 115-case P002 evidence, the implementation reviews, and the independent real corruption reproductions remain bound to the unchanged tested implementation. Their full artifact replay and final acceptance are the parallel final evidence reviewer's responsibility.

## Debugging, provenance and limits

AGENTS.md's clean-room, provenance and test-preservation requirements were applied. No native runtime or build path was modified. The added compatibility-tool code contains no debugger hook, ad hoc print probe, diagnostic environment switch or skipped-test path. Ordinary qualification outputs and failure evidence remain part of the documented tooling contract; temporary corruption/replay helpers are confined to the evidence directory and are not consumed by production/tests/CI.

The source-review module identifies public dependency URLs and immutable historical/current sources rather than claiming new third-party runtime implementation. No third-party native code was introduced by this repair. Original history and attribution remain retained. This review offers no legal/license determination for unrelated existing dependencies and no later-phase acceptance.

**Final source decision:** the reviewed publication is source-equivalent to tested production for all protected execution and frozen-provenance inputs. The original requirements and regression semantics remain intact. There is no source blocker to the separate final P002 evidence decision.
