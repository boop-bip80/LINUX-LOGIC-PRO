#!/usr/bin/env python3
"""Read recursive Git objects independently of the P001 producer modules."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--tracked', type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='')

    def git(folder, *argv, input_bytes=None):
        return subprocess.check_output(['git', '--no-optional-locks', '--literal-pathspecs',
                                        '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null',
                                        '-C', str(folder), *argv], env=env,
                                       input=input_bytes, stderr=subprocess.PIPE)

    root_pin = git(root, 'rev-parse', 'HEAD').decode().strip()
    pending = [('.', root_pin)]
    repositories, links, tracked = [], [], []
    visited = set()
    while pending:
        owner, pin = pending.pop()
        assert owner not in visited, ('duplicate repository', owner)
        visited.add(owner)
        folder = root if owner == '.' else root / owner
        assert not folder.is_symlink() and (folder / '.git').exists(), ('missing checkout', owner)
        assert git(folder, 'rev-parse', 'HEAD').decode().strip() == pin, ('wrong pin', owner)
        tree = git(folder, 'rev-parse', pin + '^{tree}').decode().strip()
        raw = git(folder, 'ls-tree', '-r', '--full-tree', '-z', pin)
        entries = []
        for row in raw.split(b'\0'):
            if not row:
                continue
            meta, raw_name = row.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = os.fsdecode(raw_name)
            full = name if owner == '.' else owner + '/' + name
            entry = {'path': full, 'repository': owner, 'repository_path': name,
                     'mode': mode, 'type': kind, 'object': oid}
            tracked.append(entry)
            entries.append(entry)
            if mode == '160000':
                links.append({'path': full, 'repository': owner, 'repository_path': name, 'commit': oid})
                pending.append((full, oid))
        # Prove that the complete referenced blob set is locally available,
        # without executing source, loading filters, or allowing a lazy fetch.
        blob_ids = sorted({e['object'] for e in entries if e['type'] == 'blob'})
        if blob_ids:
            response = git(folder, 'cat-file', '--batch-check', input_bytes=('\n'.join(blob_ids) + '\n').encode())
            observed = [row.decode().split() for row in response.splitlines()]
            assert len(observed) == len(blob_ids), owner
            assert all(len(row) == 3 and row[0] == oid and row[1] == 'blob'
                       for row, oid in zip(observed, blob_ids)), ('missing blob', owner)
        repositories.append({'path': owner, 'commit': pin, 'tree': tree,
                             'entries': len(entries), 'gitlinks': sum(e['mode'] == '160000' for e in entries),
                             'unique_blobs_available': len(blob_ids),
                             '.gitmodules': next((e['object'] for e in entries if e['repository_path'] == '.gitmodules'), None),
                             'tree_listing_sha256': hashlib.sha256(raw).hexdigest()})
    repositories.sort(key=lambda e: e['path'])
    links.sort(key=lambda e: e['path'])
    tracked.sort(key=lambda e: e['path'])
    payload = {'schema_version': 1, 'source_commit': root_pin, 'entries': tracked}
    payload_bytes = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + '\n').encode()
    checks = []
    licenses_verified = 0
    if args.inventory:
        inventory = json.loads(args.inventory.read_text())
        assert inventory['source']['commit'] == root_pin
        expected = sorted((e['path'], e['repository'], e['repository_path'], e['commit']) for e in inventory['submodules'])
        actual = sorted((e['path'], e['repository'], e['repository_path'], e['commit']) for e in links)
        assert actual == expected, 'recursive graph mismatch'
        expected = sorted((e['path'], e['commit'], e['tree'], e['tracked_entries']) for e in inventory['repositories'])
        actual = sorted((e['path'], e['commit'], e['tree'], e['entries']) for e in repositories)
        assert actual == expected, 'repository tree mismatch'
        checks.append('recursive graph and every repository commit/tree/count match inventory')
        tracked_by_path = {entry['path']: entry for entry in tracked}
        for repository in inventory['repositories']:
            owner = repository['path']
            folder = root if owner == '.' else root / owner
            licenses = repository['licenses']
            ids = sorted({entry['git_blob'] for entry in licenses})
            objects = {}
            if ids:
                raw = git(folder, 'cat-file', '--batch', input_bytes=('\n'.join(ids) + '\n').encode())
                offset = 0
                for oid in ids:
                    end = raw.index(b'\n', offset)
                    header = raw[offset:end].decode().split()
                    assert header[0] == oid and header[1] == 'blob'
                    size = int(header[2])
                    data = raw[end + 1:end + 1 + size]
                    assert len(data) == size and raw[end + 1 + size:end + 2 + size] == b'\n'
                    objects[oid] = data
                    offset = end + 2 + size
                assert offset == len(raw)
            for candidate in licenses:
                full = candidate['path'] if owner == '.' else owner + '/' + candidate['path']
                source = tracked_by_path[full]
                assert source['repository'] == owner and source['object'] == candidate['git_blob']
                assert source['mode'] == candidate['mode']
                data = objects[candidate['git_blob']]
                assert candidate['bytes'] == len(data)
                assert candidate['sha256'] == hashlib.sha256(data).hexdigest()
                if source['mode'] == '120000':
                    assert candidate['content_kind'] == 'symlink_target_text'
                    assert candidate['target_dereferenced'] is False
                    assert candidate['symlink_target'] == os.fsdecode(data)
                licenses_verified += 1
        checks.append('every license candidate byte count and SHA-256 matches its committed Git blob; symlink target text is not followed')
    if args.tracked:
        raw = args.tracked.read_bytes()
        if args.tracked.suffix == '.gz':
            raw = gzip.decompress(raw)
        assert json.loads(raw) == payload, 'tracked entry mismatch'
        assert raw == payload_bytes, 'tracked serialization bytes mismatch'
        checks.append('all tracked path/owner/mode/type/object records and serialized bytes match')
    report = {'result': 'PASS', 'oracle': 'Independent native Git plumbing; no producer module imports',
              'root_commit': root_pin, 'repository_count': len(repositories), 'gitlink_count': len(links),
              'tracked_entry_count': len(tracked), 'tracked_json_sha256': hashlib.sha256(payload_bytes).hexdigest(),
              'license_records_verified': licenses_verified,
              'checks': checks, 'repositories': repositories, 'submodules': links}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('repositories', 'submodules')}, indent=2))


if __name__ == '__main__':
    main()
