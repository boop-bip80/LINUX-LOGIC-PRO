#!/usr/bin/env python3
"""Bind the two completed installed-byte tables to the original inventories.

This checks table identity, complete path coverage, span arithmetic, and original
manifest hashes; the distinct package reviews perform actual all-byte parsing.
It does not replace those reviews or make a phase acceptance decision.
"""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def record(path):
    data = path.read_bytes()
    return {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--campaign', type=Path, required=True)
    p.add_argument('--originals', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    paths = [args.campaign/'wave4-package/final-4622a939/original-package-comparison.json',
             args.campaign/'wave5-package/final-installed-byte-comparison.json']
    left, right = [json.loads(path.read_bytes()) for path in paths]
    require(left['byte_reviews'] == right['byte_reviews'], 'peer tables differ')
    require(not left['structural_inventory_differences'] and not left['tar_metadata_differences']
            and not left['source_binding_errors'], 'unclosed package difference')
    manifest_paths = [args.originals/f'build-{side}/install-first.json' for side in ['a','b']]
    manifests = [json.loads(path.read_bytes()) for path in manifest_paths]
    source = '4622a9396c5c9fbe0014bdf6a2f695dcc491233c'
    require(left['expected_source'] == right['expected_source'] == source
            and all(m['source_commit'] == source for m in manifests), 'candidate binding')
    inventories = [{x['path']:x for x in m['entries']} for m in manifests]
    require(inventories[0].keys() == inventories[1].keys(), 'installed path sets differ')
    changed = {n for n,x in inventories[0].items() if x != inventories[1][n]}
    rows = {row['path']:row for row in left['byte_reviews']}
    require(changed == set(rows) and len(rows) == len(left['byte_reviews']) == 137, 'changed path coverage')
    fields, byte_counts = collections.Counter(), collections.Counter()
    for name, row in rows.items():
        require(row['sha256_a'] == inventories[0][name]['sha256']
                and row['sha256_b'] == inventories[1][name]['sha256'], 'original installed digest binding')
        require(row['normalized_equal'] and row['normalized_sha256_a'] == row['normalized_sha256_b']
                and not row['errors'] and row['unclassified_bytes'] == 0, 'unclosed row')
        spans = row['all_changed_byte_spans']
        require(sum(s['end']-s['offset'] for s in spans) == row['changed_bytes'], 'row changed-byte count')
        for index, span in enumerate(spans):
            require(span['offset'] < span['end'] and (index == 0 or spans[index-1]['end'] <= span['offset']), 'span ordering/overlap')
            a, b = bytes.fromhex(span['a_hex']), bytes.fromhex(span['b_hex'])
            require(len(a) == len(b) == span['end']-span['offset'] and all(x != y for x,y in zip(a,b)), 'actual differing span length')
            byte_counts[span['classification']] += len(a)
        fields.update(f['kind'] for f in row['fields'])
    require(dict(fields) == left['field_counts'] and sum(byte_counts.values()) == left['changed_bytes'] == 4418,
            'total changed fields/bytes')
    result = {'schema':'darling.p003.wave5-package-table-reconciliation.v1',
              'reviewer':'/root/wave5_acceptance', 'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_commit':source, 'run_id':42180484781, 'status':'PASS_TABLE_RECONCILIATION',
              'phase_acceptance':False, 'helper':record(Path(__file__)),
              'tables':[{**record(path), 'path':str(path.relative_to(args.campaign))} for path in paths],
              'original_manifests':[{**record(path), 'path':str(path.relative_to(args.originals))} for path in manifest_paths],
              'changed_paths_exactly_covered':len(changed), 'changed_bytes_by_field':dict(byte_counts),
              'changed_bytes':sum(byte_counts.values()), 'field_counts':dict(fields),
              'unclassified_bytes':0, 'normalized_digests_equal_all_rows':True}
    with args.output.open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    print(json.dumps({k:result[k] for k in ['status','changed_paths_exactly_covered','changed_bytes','unclassified_bytes']}))


if __name__ == '__main__':
    main()
