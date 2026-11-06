# Independent nano UUID crosscheck — historical method QA

- Reviewer: `/root/wave3_package/uuid_crosscheck`.
- Review and input rehash date: `2026-11-06T06:07:40.770216+00:00`.
- Historical implementation: `89c6c9d85aba6ed1662035e6366298c92ef9c970`.
- Original workflow: `41292343355`.
- Reviewed helper: [compare_original_packages.py](compare_original_packages.py),
  specifically its Mach-O metadata, UUID and byte-normalization paths.
- Helper SHA-256 at the final recorded replay:
  `0115737614c47266678af87da2bb9c681af4c009c061b538299eacaef4104d62`.
- Authorship boundary: this reviewer did not author or edit the helper or any
  production implementation. The only authored file is this evidence record.

**Result: the independent calculation reproduces both original nano UUIDs
exactly. Two concrete counterexamples are rejected. This is historical method
QA only; it does not accept `af3566ee` or any current P003 gate.**

## Original input identities

Both original packages were opened as data. No archive member was extracted to
an executable or symlink path, and no member was executed. All six SHA-256 values
below were independently recomputed from the local original bytes.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Build A original ZIP | 87,382,711 | `14f9e0c507efeff85652008e160f2f4fb1e68d7e0f4cb5dd46c941b1918b9849` |
| Build B original ZIP | 87,371,725 | `e33778793ce009ff7eb01b8257f58098545c760d496d5fc37775f4ee26d82530` |
| Build A `runtime-prefix.tar.gz` | 85,606,210 | `110a80dda4c0126271f7948e6c2fa1796809258881ee22717a3c615412095e12` |
| Build B `runtime-prefix.tar.gz` | 85,603,171 | `333707dd485b4be84d3ec25379e8cd954516dc40e759fcacab741e249a8349a0` |
| Build A nano member | 236,780 | `543a4b87d080cd2be159650861e88a3cd23043b88567169fc8a29633944f5ff9` |
| Build B nano member | 236,780 | `dc2534436547819be746ca78ddac9e5711c4d28343b42a6d562fc3852133a810` |

The tar member is `./libexec/darling/usr/bin/nano`. The original ZIPs are the
siblings `build-a.zip` and `build-b.zip` of the two artifact directories shown in
the reproduction command below. The immutable hashes identify the inputs if
those temporary directory names change.

## Exact-source basis

The metadata calculation was checked against the already-pinned, publicly
licensed `cctools-port` source at
`d9456c221e1f462e17c0b3297748bc089d5a861e`. The relevant locations are
`cctools/ld64/src/ld/OutputFile.cpp::computeContentUUID`, STABS layout and string
pool construction in `LinkEditClassic.hpp`, and command offsets/sizes in
`HeaderAndLoadCommands.hpp`. The nano time-string source is `src/nano.c` at
`7514f5f1115fffedd8fc2095107ca86ff82c54d6`.

| Pinned file | SHA-256 |
|---|---|
| `cctools/ld64/src/ld/OutputFile.cpp` | `052e1e7411c88dc8391a30f489c924d6e244734c067f72698eeac5284ce2a4e4` |
| `cctools/ld64/src/ld/LinkEditClassic.hpp` | `f407611ea2ec16577b36bd510fd169bd572da4509b677b4d42d9d83115a7cd54` |
| `cctools/ld64/src/ld/HeaderAndLoadCommands.hpp` | `e862083250232792991eecbc9b672f5ae8e1583d84509e2db1e743eddb3dfce3` |
| nano `src/nano.c` | `612842cb483fc8560bbfb2d035407e3645cc5b7f0ab066f99956521eb8ea07c5` |

This investigation used the repository's own built nano bytes and selected
license-declared build metadata source. No proprietary Apple binary,
disassembly, CoreCrypto source or restricted source was used. No external
implementation was copied into the helper by this reviewer.

## Independently reproduced formula

For both original members, zero the 16 UUID bytes at half-open offsets
`[1544, 1560)`. Prefix the MD5 input with the five bytes `/nano`, hexadecimal
`2f6e616e6f`. Hash the remaining file in original order, excluding only these
regions from the **UUID calculation**:

| Half-open file range | Parsed meaning |
|---|---|
| `[1280, 1352)` | `__LINKEDIT` segment command |
| `[1400, 1424)` | `LC_SYMTAB` command |
| `[183312, 208928)` | 1,601 contiguous STABS nlist records |
| `[227679, 235889)` | STABS string region |

Thus the digest input, after zeroing the UUID field, is:

```python
payload = (
    b"/nano"
    + data[:1280]
    + data[1352:1400]
    + data[1424:183312]
    + data[208928:227679]
    + data[235889:236780]
)
```

Set digest byte 6 to `(byte & 0x0f) | 0x30` and digest byte 8 to
`(byte & 0x3f) | 0x80`. The independently parsed exclusions and digest agree
with the helper for each original member.

| Build | Observed UUID | Independently computed UUID |
|---|---|---|
| A | `d04d74f362cf301f8fc4cc08928c11d7` | `d04d74f362cf301f8fc4cc08928c11d7` |
| B | `1dbe6136f96934868a3c9f60ef79a5ce` | `1dbe6136f96934868a3c9f60ef79a5ce` |

The exploratory mismatch preceding this review came from a temporary diagnostic
loop that reused `end` for relative and absolute range endpoints. The helper
constructs its exclusions before its digest loop and does not contain that
diagnostic defect.

## Actual negative results

The two mutations were made only to in-memory copies or a copied binding map;
the original artifacts were untouched.

1. **A changed STABS byte remains an unknown package byte.** Changing original
   A's byte at offset `227700` from `0x72` to `0x73` leaves its UUID calculation
   valid, because the byte lies inside a UUID-excluded string region. The helper
   nevertheless reports exactly one `UNCLASSIFIED` byte in `[227700, 227701)`,
   preserves both byte values, and returns `normalized_equal: false`. This
   confirms that UUID exclusions do not become package-normalization permission.
2. **Missing exact source binding fails.** Comparing the original A/B nano
   members after removing only the `nano` entry from the verified binding map
   reports `missing exact source binding: nano`, 19 unclassified bytes and
   `normalized_equal: false`.

No concrete false pass was found in this bounded source-binding and byte-
normalization review. This statement does not extend to unreviewed helper
branches or to a phase acceptance verdict.

## Reproduction command

Run from the repository root after retrieving the two original artifact ZIPs
and their regular evidence files. This command uses Python standard-library
modules; Git is used by the evidence helper only to retrieve immutable source
bindings from the local root/submodule object stores. It imports no production
verifier. The independent UUID reconstruction below does not call the helper's
Mach-O parser or UUID implementation to obtain its expected digest.

```sh
python - \
  /workspace/scratch/430a9939323d/p003-work/run-41292343355/build-a \
  /workspace/scratch/430a9939323d/p003-work/run-41292343355/build-b <<'PY'
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tarfile

sys.dont_write_bytecode = True
repo = Path.cwd()
helper = repo / "docs/compat/logic-pro/evidence/P003/requalification-20261106/wave3-package-review/compare_original_packages.py"
spec = importlib.util.spec_from_file_location("review_helper", helper)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
directories = [Path(value) for value in sys.argv[1:]]
assert len(directories) == 2
member = "libexec/darling/usr/bin/nano"
expected_uuids = ["d04d74f362cf301f8fc4cc08928c11d7",
                  "1dbe6136f96934868a3c9f60ef79a5ce"]

def identity(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": path.stat().st_size, "sha256": digest.hexdigest()}

members = []
proofs = []
for number, directory in enumerate(directories):
    with tarfile.open(directory / "runtime-prefix.tar.gz") as archive:
        data = archive.extractfile("./" + member).read()
    members.append(data)
    assert len(data) == 236780 and data[:4] == b"\xcf\xfa\xed\xfe"
    view = bytearray(data)
    position = 32
    exclusions = []
    for _ in range(struct.unpack_from("<I", view, 16)[0]):
        command, length = struct.unpack_from("<II", view, position)
        assert length >= 8 and position + length <= len(view)
        if command == 27:
            uuid_offset = position + 8
        if command == 2:
            symbols = struct.unpack_from("<IIII", view, position + 8)
            exclusions.append((position, position + length))
        if command == 25 and view[position + 8:position + 24].split(b"\0")[0] == b"__LINKEDIT":
            exclusions.append((position, position + 72))
        position += length
    symbol_offset, symbol_count, string_offset, string_size = symbols
    stabs = []
    strings = []
    for index in range(symbol_count):
        at = symbol_offset + 16 * index
        string_index = struct.unpack_from("<I", view, at)[0]
        if view[at + 4] & 0xe0:
            stabs.append(at)
            if string_index > 1:
                end = view.index(0, string_offset + string_index) + 1 - string_offset
                strings.append((string_index, end))
    assert stabs == list(range(stabs[0], stabs[-1] + 16, 16))
    start = min(value[0] for value in strings)
    end = max(value[1] for value in strings)
    if string_size - end < 8:
        end = string_size
    exclusions.extend([(stabs[0], stabs[-1] + 16),
                       (string_offset + start, string_offset + end)])
    assert sorted(exclusions) == [(1280, 1352), (1400, 1424),
                                  (183312, 208928), (227679, 235889)]
    assert uuid_offset == 1544
    actual = view[uuid_offset:uuid_offset + 16].hex()
    view[uuid_offset:uuid_offset + 16] = bytes(16)
    digest = hashlib.md5(b"/nano")
    cursor = 0
    for start, end in sorted(exclusions):
        digest.update(view[cursor:start])
        cursor = end
    digest.update(view[cursor:])
    calculated = bytearray(digest.digest())
    calculated[6] = (calculated[6] & 15) | 48
    calculated[8] = (calculated[8] & 63) | 128
    assert actual == calculated.hex() == expected_uuids[number]
    helper_proof = review.uuid_proof(data, review.macho(data)[0], "nano")
    assert helper_proof["matches"] and helper_proof["computed"] == calculated.hex()
    proofs.append({"build": "AB"[number], "zip": identity(directory.with_suffix(".zip")),
                   "tar": identity(directory / "runtime-prefix.tar.gz"),
                   "member_sha256": hashlib.sha256(data).hexdigest(),
                   "actual_uuid": actual, "computed_uuid": calculated.hex(),
                   "exclusions": sorted(exclusions), "helper_matches": True})

manifest = review.read_json(directories[0] / "install-first.json")
bindings, errors = review.source_bindings(
    repo, manifest, "89c6c9d85aba6ed1662035e6366298c92ef9c970")
assert not errors
modified = bytearray(members[0])
assert modified[227700] == 0x72
modified[227700] ^= 1
negative = review.compare_bytes(member, members[0], bytes(modified), bindings)
assert review.uuid_proof(bytes(modified), review.macho(bytes(modified))[0], "nano")["matches"]
assert negative["unclassified_bytes"] == 1 and not negative["normalized_equal"]
assert negative["unclassified_byte_spans"] == [{
    "offset": 227700, "end": 227701, "a_hex": "72", "b_hex": "73",
    "classification": "UNCLASSIFIED"}]
missing = dict(bindings)
del missing["nano"]
unbound = review.compare_bytes(member, members[0], members[1], missing)
assert unbound["errors"] == ["missing exact source binding: nano"]
assert unbound["unclassified_bytes"] == 19 and not unbound["normalized_equal"]
print(json.dumps({"purpose": "historical-method-qa", "proofs": proofs,
                  "uuid_excluded_byte_rejected": True,
                  "missing_source_binding_rejected": True,
                  "current_candidate_acceptance": False}, indent=2))
PY
```

Expected outcome: exit 0, both exact UUIDs printed, both rejection assertions
true, and `current_candidate_acceptance: false`. Fresh original archives and
independent current-source review remain required. Remain in P003.

The exact fenced Python command above was extracted from this Markdown and
executed against the recorded helper on 2026-11-06. Actual result: exit 0, both
exact UUIDs and all six input hashes matched the tables, both rejection
assertions were true, and current-candidate acceptance remained false.
