#!/usr/bin/env python3
"""Independent retained-evidence checks for the reviewed P001 implementation."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--hosted-exports', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.repo / 'docs/compat/logic-pro/evidence/P001'
index = json.loads((root / 'evidence-index.json').read_text())
for record in index['files']:
    data = (root / record['path']).read_bytes()
    assert len(data) == record['bytes'], record['path']
    assert hashlib.sha256(data).hexdigest() == record['sha256'], record['path']
storage = json.loads((root / 'tracked-files/manifest.json').read_text())
parts = []
for record in storage['parts']:
    data = (root / 'tracked-files' / record['path']).read_bytes()
    assert len(data) == record['bytes'], record['path']
    assert hashlib.sha256(data).hexdigest() == record['sha256'], record['path']
    parts.append(data)
compressed = b''.join(parts)
assert len(compressed) == 10943098
assert hashlib.sha256(compressed).hexdigest() == 'ce373fd1818fd6f8f59d1f0e9cd39abf726ea789895e9383a44aef2e819f7799'
tracked = gzip.decompress(compressed)
assert len(tracked) == 97472302
assert hashlib.sha256(tracked).hexdigest() == '047d659a94420c97f42d08cc4deea40fdc2912a69ff4c77057562835705404cd'
tables = []
for folder in (root, root / 'ubuntu-22.04'):
    checksums = json.loads((folder / 'checksums.json').read_text())
    for name, expected in checksums.items():
        data = tracked if name in ('tracked-files.json', 'final-tracked-files.json') else (folder / name).read_bytes()
        assert len(data) == expected['bytes'], (folder, name)
        assert hashlib.sha256(data).hexdigest() == expected['sha256'], (folder, name)
    tables.append({'host': folder.name, 'entries': len(checksums)})
files = json.loads(tracked)
links = [row for row in files['entries'] if row['mode'] == '160000']
assert len(links) == len({row['path'] for row in links}) == 160
pins = {row['path']: row['object'] for row in links}
original = json.loads((root / 'inventory.json').read_text())
assert pins == {row['path']: row['commit'] for row in original['submodules']}
lock = json.loads((args.repo / 'docs/compat/logic-pro/submodules.lock.json').read_text())
assert pins == {row['path']: row['commit'] for row in lock['submodules']}
hosts = []
for host in ('ubuntu-22.04', 'ubuntu-24.04'):
    folder = args.hosted_exports / host
    checksums = json.loads((folder / 'checksums.json').read_text())
    verified = []
    for path in folder.iterdir():
        if path.name in checksums:
            data = path.read_bytes()
            assert len(data) == checksums[path.name]['bytes'], path
            assert hashlib.sha256(data).hexdigest() == checksums[path.name]['sha256'], path
            verified.append(path.name)
    assert len(verified) == 6
    fresh = json.loads((folder / 'inventory.json').read_text())
    assert pins == {row['path']: row['commit'] for row in fresh['submodules']}
    summary = json.loads((folder / 'summary.json').read_text())
    assert summary['result'] == 'PASS' and not summary['failures']
    assert summary['implementation_commit'] == '78dff3235e95d90e43faa4af7de34d5f926c9d28'
    assert summary['fixture_tests_executed'] == 113
    assert summary['checks']['source_repositories_verified'] == 161
    assert summary['checks']['source_citations_verified'] == 63
    hosts.append({'host': host, 'checksummed_exported_entries': verified, 'summary': summary})
result = {'result': 'PASS', 'original_index_entries': len(index['files']),
          'original_artifact_tables': tables, 'parts_verified': len(parts),
          'original_tracked_entries': len(files['entries']), 'unchanged_recursive_pins': len(pins),
          'fresh_hosted_evidence': hosts}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print('PASS:', len(index['files']), 'original files, 30 hosted checksums,', len(pins), 'unchanged pins, two current hosted exports')
