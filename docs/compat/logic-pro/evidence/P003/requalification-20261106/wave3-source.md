# Wave 3 independent source and build-integration review

**Verdict: APPROVED within the bounded source/build-integration scope below. No verified blocker remains in these three repairs. This is not P003 G1–G4 acceptance; remain in P003.**

## Identity, source and independence

- Reviewer: `/root/wave3_source`, a distinct non-author review agent. I authored none of the reviewed production changes or their tests. This review adds evidence only.
- Review completed: 05:59:22 UTC, 2026-11-06.
- Tested implementation: `af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`; tree `84fc6c85fc4d2a9c3611dc0dd757a34a0dff4c71`.
- Evidence-only HEAD at review: `b815ab202207b1ce43dfc713b3c4c35c0f1983ed`. Each reviewed working file was compared byte-for-byte with its blob at the tested implementation.
- Campaign production baseline: `3be66e2b343b77c34d023c20bd7822dc055c657f`. P001/P002 accepted predecessor: `d58cca513559cfef0ff9af59aa5dc3b6341bdf77`.
- Relevant child: `src/external/objc4` at `092352cab947b410a73b5123b190df03f90c1802`; the actual local child HEAD and candidate gitlink agree. The unchanged submodule lock binds all other dependencies.

I read `AGENTS.md`, the README dashboard/global gate contract and current P003 entry. The bounded review covers `darling_configure_objc_runtime`, `validate_source_classifications`, the actual `build-p003.sh` EXIT handler, the aggregate before/after status gate and their focused tests. Runtime initialization and whole-artifact/runtime acceptance have separate reviewers. No restricted CoreCrypto source, Apple binary internals or external implementation material was consulted. No production, workflow, README, dependency-pin or toolchain edit was made by this reviewer.

## Exact reviewed files

| File | SHA-256 at tested implementation and review workspace |
| --- | --- |
| `cmake/darling_objc_configuration.cmake` | `cc2b9a481ad75abec9224b2eef49f4c4d753c50c9394c298c6dba3212dc7bfb0` |
| `ci/logic-pro/build-p003.sh` | `b73c2b49a22914e339d9db87d2d813fcc6823801fc960cbcb6010640c48d52f5` |
| `tools/compat/logic-pro/compare_p003.py` | `e60cb440b933d5b0e89d19f40bbb80285206791d9b6062c1aaada6685193c240` |
| `tests/compat/logic-pro/build/test_objc_configuration.py` | `f7103c0e583a01937e5fe408f7c0118b78110698dd3ba821bb31f9270c65a2bd` |
| `tests/compat/logic-pro/build/test_source_classifications.py` | `0607e22f16a3c07a3491531592778cbc2fad63ee0a34c1fd9b54cc9bf8cc7a71` |
| `tests/compat/logic-pro/build/test_source_cleanliness.py` | `3be561db4bd0c37799134d02ae8bb675d5d85f84d303e89ae72488e11ed014f5` |

The full machine-readable source hashes, protected inputs, root citation blob identities and transcript checks are retained in [wave3-source-tests.json](wave3-source-tests.json).

## Reproduced cases and findings

### Objective-C configuration

Both original configure logs in run `42165628353` fail at the old helper's `Pinned objc4 debug definition changed` check. The current pin has no directory-level `OBJC_IS_DEBUG_BUILD` definition and defines it from `DEBUG` in `runtime/objc-config.h`. That header derives `DEBUG` from `NDEBUG`; these are actual pinned source observations, not assumptions from fixture output. The header SHA-256 is `28104a987e265db55fc6aaaf2d751a74655c77dde216d7e15a73076a55f17169`; its runtime CMake file is `f6de466b4996f8cf550993ca4f21b4af10a1fa8619b65df32117e5573957385e`.

The repair recognizes exactly one expected header derivation and leaves that case to the header. It preserves the existing legacy adapter only when the exact old directory definition is present. Other explicit values, an absent derivation or multiple matching definitions remain configuration errors. It neither suppresses the runtime consistency check nor changes the child pin.

I executed the six focused tests through real CMake, a real C++ compiler and the resulting executables. They reproduced the old Release mismatch as a failing control; passed legacy and current contracts in empty/Debug/Release/RelWithDebInfo/MinSizeRel configurations; passed all three release-like configurations with custom flags omitting `NDEBUG`; and rejected unknown definitions and missing/changed/duplicated derivations. Compile commands are inspected by the tests to ensure the header-derived case receives no injected macro and legacy cases receive a consistent value. Result: **6 tests, terminal plain `OK`, no skips**.

This local run used CMake 4.4.4 and GCC 14.2.0, with Python 3.12.14. It exercises the minimal build contracts, not the full objc4 runtime. Frozen Clang 14 compilation of the full pinned runtime remains a hosted-build requirement.

### Complete source-classification consumer

The repaired consumer preserves the original citation fields and historical re-audit metadata while adding exact current provenance for every citation: reviewed anchor, owner/path, actual root commit or nested pinned commit, complete gitlink chain, full-blob/excerpt identities, line range, assertion count and preservation flag. Canonical JSON comparison distinguishes boolean/integer/float substitutions and rejects missing or extra checked-record fields. The existing exact source anchor, complete 63-ID set and reviewed assertions remain required.

The existing `P004`-labelled historical CMake re-audit is accepted only for its already-reviewed root-file identity, fixed upstream commit and prior blob. Consuming that P001 report format does not authorize new P004 implementation or relax P003 gates.

I ran all **26 focused source-classification/unwind-parser tests**, terminal plain `OK`, no skips. In addition to synthetic corruptions, these include the unchanged original P001 producer reports from both accepted `d58cca51` hosted runners; the real reports are independently hash-bound by the test.

I separately passed both untouched actual producer reports from `run-42165628353/build-a` and `build-b` through the candidate consumer using producer SHA `8a222c7d5e11fbd2c3ece79c53d60c1be545d0a0`. Both validate **63 citations across 41 files**, with exact anchor `c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a`. For both hosts, report SHA-256 is `6cf6a34398634cf5a51f5c2d15a364197941ac306687278daa473920949c52b5`; raw source-log SHA-256 is `6087fa4239b4df9685950b7cb9ce32c7821986dd51d8556349dd4cc216f9cfd8`.

An independent mutation loop over an untouched producer report rejected **822 negative cases**: remove each citation's complete current provenance; remove each of its eleven current-provenance fields; substitute wrong top-level anchor/current/original commits; and replace every actual root commit with the historical anchor or every nested commit with the producer root commit. Every rejection and both successful original validations are recorded in [wave3-source-producer-replay.json](wave3-source-producer-replay.json). Original input files were not modified.

The underlying run failed configuration later. Its valid source-audit outputs establish producer/consumer compatibility, not successful build or installed-runtime behavior.

### Actual EXIT handler and aggregate cleanliness

The producer now captures final status from the real source checkout on both success and failure. Exclusive, no-follow creation rejects preexisting/redirected evidence, failed Git status remains an error, and an explicit `--ignore-submodules=none` prevents local ignore configuration from hiding child changes. An otherwise successful build becomes `FAIL` at `source-cleanliness` when the source is dirty; an earlier nonzero code and its original stage remain authoritative. Raw dirty status is retained.

The aggregate separately requires both before and after status files to be regular, non-symlink files containing exactly zero bytes, and hashes those files into its evidence result. This makes post-build status a required input rather than merely retained output.

I executed **15 focused tests**, terminal plain `OK`, no skips. The producer tests extract and execute the actual checked-in shell EXIT handler against temporary real Git repositories. Cases cover clean source, tracked and untracked mutation, a dirty submodule hidden from ordinary status by ignore configuration, failed Git status, preexisting regular evidence, symlink/directory/FIFO evidence, and original exit 42 at `compile` with both clean and dirty source. The aggregate cases exercise its real status-file reads, failures and evidence hashing while mocking unrelated build/runtime validators. No full installation or runtime result is inferred from these fixtures.

## P001/P002 predecessor continuity and hosted corroboration

I compared accepted `d58cca51` with candidate `af3566ee` and verified byte identity for the classification producer and manifest, submodule lock, toolchain lock, `.gitmodules` and Docker recipe. All **149 direct gitlinks** are unchanged; immutable unchanged direct pins also preserve their nested graph, and the unchanged accepted lock binds **160 total dependencies**. All **24 root-owned source files** cited by the complete current-source re-audit retain exactly the same Git blob IDs. No P001/P002 tool, fixture or workflow changed; the non-evidence diff is confined to the P003 implementation/tests and its workflow floor. The consumer repair does not edit the accepted classification producer or its source assertions.

These checks found no source-input regression invalidating the accepted P001/P002 conditions. Fresh hosted runs provide corroboration: the coordinator reports P001 `42169925654`, P002 `42169925596` and archive readback `42169925649` completed successfully at the candidate. This Wave 3 report does not independently accept those runs' complete raw artifact inventories; that belongs to the subsequent artifact-review waves.

I did independently inspect the original preflight ZIP for exact-candidate P003 run `42169925661`: SHA-256 `8df781803f0253e5843d4167b7e4c45eb95808683734fd4d2bcc6fefd3947792`, all **4 CRC members** valid. The raw baseline/submodule/build transcripts each contain exactly **174/115/187 distinct named tests**, matching their single `Ran ...` summaries and terminal plain `OK`; there are no skipped, expected-failure or unexpected-success substitutions. Per-transcript hashes are in the machine-readable review. This is regression evidence, not P003 installation acceptance.

## Reproduction commands

From the candidate repository root, with the local Clang wrapper supplied for the broader local harness:

```sh
PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/compat/logic-pro/build -p test_objc_configuration.py -v
PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/compat/logic-pro/build -p test_source_classifications.py -v
PATH=/workspace/scratch/430a9939323d/p003-work/bin:$PATH PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/compat/logic-pro/build -p test_source_cleanliness.py -v
```

Replay the original producer reports and independently reconstruct the 822 negative cases with their unchanged artifact directories available:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYCODE'
from pathlib import Path
import copy, json, shutil, sys, tempfile
sys.path.insert(0, str(Path.cwd() / 'tools/compat/logic-pro'))
import compare_p003 as gate
base = Path('/workspace/scratch/430a9939323d/p003-work/run-42165628353')
commit = '8a222c7d5e11fbd2c3ece79c53d60c1be545d0a0'
for host in ('build-a', 'build-b'):
    print(host, gate.validate_source_classifications(base / host, commit))
original = json.loads((base / 'build-a/source-classifications.json').read_text())
with tempfile.TemporaryDirectory() as temporary:
    output = Path(temporary)
    shutil.copyfile(base / 'build-a/source-classifications.log', output / 'source-classifications.log')
    cases = []
    for index, row in enumerate(original['checked']):
        for key in (None, *row['current_source']):
            changed = copy.deepcopy(original)
            if key is None:
                del changed['checked'][index]['current_source']
            else:
                del changed['checked'][index]['current_source'][key]
            cases.append(changed)
    for key in ('current_source_anchor', 'current_commit', 'inspected_commit'):
        changed = copy.deepcopy(original)
        changed[key] = '0' * 40
        cases.append(changed)
    for index, row in enumerate(original['checked']):
        changed = copy.deepcopy(original)
        changed['checked'][index]['current_source']['repository_commit'] = (
            original['current_source_anchor'] if row['repository'] == '.' else commit)
        cases.append(changed)
    for changed in cases:
        (output / 'source-classifications.json').write_text(json.dumps(changed))
        try:
            gate.validate_source_classifications(output, commit)
        except ValueError:
            pass
        else:
            raise AssertionError('Corrupted producer report was accepted')
    assert len(cases) == 822
    print('822 negative provenance cases rejected')
PYCODE
```

Source/pin continuity commands used `git diff --name-status d58cca513559cfef0ff9af59aa5dc3b6341bdf77 af3566ee387ed05f0b28c4ea02ebe7ecf59aa3f2`, `git ls-tree -r` on both revisions, `git rev-parse COMMIT:PATH` for each root citation, and `git show COMMIT:PATH` byte comparisons for each protected/scoped file. The retained JSON records the resulting identities and complete relevant path set; none of these checks requires restricted source inspection.

## Evidence integrity and remaining acceptance work

| Review artifact | SHA-256 |
| --- | --- |
| [wave3-source-tests.json](wave3-source-tests.json) | `237992c240c3fea017c16e528a316b5bb5fe7816fdc6e7831764deb4d232bd3b` |
| [wave3-source-producer-replay.json](wave3-source-producer-replay.json) | `cdb25622e45af58b231a43329d52cdac949c1c036648b7a5085e1967742acaed` |
| [wave3-source-objc_configuration.log](wave3-source-objc_configuration.log) | `bf35620dc9bb12177de4863056d8d34650dc35cb43a52165209055028752bb64` |
| [wave3-source-source_classifications.log](wave3-source-source_classifications.log) | `23db4174e271ad4c749e28e10b937ab2b477a4ad6b0eaf666eeaaa62cd424f7c` |
| [wave3-source-source_cleanliness.log](wave3-source-source_cleanliness.log) | `4102556dcf84add8120b0ffb5fbdd0d2fe32a3dc21937d2eaf63bc9f25cde1eb` |

No verified blocker was found in this bounded review. Approval covers the three repair mechanisms and focused regression behavior at the exact candidate. Full frozen-Clang14 compilation, two clean builds/installations, installed-framework resolution, all real runtime campaigns, complete nondeterminism accounting, uninstall/reinstall and source-free installed-archive replay still require the fresh current-source artifacts and independent Waves 4–5 review. No P003 checkbox, P004 status, Logic Pro functionality, audio qualification or ARM qualification is advanced by this report.
