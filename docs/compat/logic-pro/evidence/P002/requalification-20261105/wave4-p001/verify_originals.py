#!/usr/bin/env python3
"""Independent P001 byte/object oracle; no imports from production gate code.

Arguments are the exact implementation checkout, original artifact directory,
read-only full child object checkout, and output path. Only hashes/metadata are
emitted: source contents and license text are never copied into this report.
"""
import collections
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zipfile

ROOT, RAW, CHILDREN, OUT = map(pathlib.Path, sys.argv[1:])
IMPL = 'd58cca513559cfef0ff9af59aa5dc3b6341bdf77'
TRACKED = 'c2995040954cc2f844994ac8854ee51607c15a9a3c0a552f4ae53fa1635cd0cd'
HERE = pathlib.Path(__file__).parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(repo, *args):
    return subprocess.check_output(['git', '--no-optional-locks', '-c',
        'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-C', str(repo), *args])

def repo_path(path):
    return ROOT if path == '.' else CHILDREN / path

def read(path):
    return json.loads(path.read_bytes())

def require(value, message):
    if not value:
        raise AssertionError(message)

def native_entries(repo, commit):
    result = {}
    for item in git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0'):
        if not item:
            continue
        metadata, name = item.split(b'\t', 1)
        mode, kind, obj = metadata.decode().split()
        result[name.decode('utf-8', 'surrogateescape')] = (mode, kind, obj)
    return result

def reconstruct(entries):
    root = {}
    for entry in entries:
        parts = entry['repository_path'].split('/')
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        require(parts[-1] not in node, 'duplicate manifest path')
        node[parts[-1]] = (entry['mode'], entry['object'])
    tree_count = 0
    def encode(node):
        nonlocal tree_count
        tree_count += 1
        records = []
        for name, value in node.items():
            rawname = name.encode('utf-8', 'surrogateescape')
            if isinstance(value, dict):
                mode, obj, key = '40000', encode(value), rawname + b'/'
            else:
                mode, obj = value
                key = rawname
            records.append((key, mode.encode() + b' ' + rawname + b'\0' + bytes.fromhex(obj)))
        body = b''.join(record for _, record in sorted(records))
        return hashlib.sha1(b'tree ' + str(len(body)).encode() + b'\0' + body).hexdigest()
    return encode(root), tree_count

run, artifacts, jobs = [read(HERE / name) for name in
    ('official-run.json', 'official-artifacts.json', 'official-jobs.json')]
require(run['id'] == 42155822562 and run['head_sha'] == IMPL
        and run['conclusion'] == 'success', 'official run identity')
require(jobs['total_count'] == 2 and all(j['head_sha'] == IMPL and
    j['conclusion'] == 'success' and all(s['conclusion'] == 'success' for s in j['steps'])
    for j in jobs['jobs']), 'official hosted jobs')
require(artifacts['total_count'] == 2, 'official artifact count')
host_reports = []
inventories = []
for host, artifact_id in [('ubuntu-22.04', 13474243274), ('ubuntu-24.04', 13474213466)]:
    directory = RAW / ('p001-' + host)
    archive = directory.with_suffix(directory.suffix + '.zip')
    metadata = next(a for a in artifacts['artifacts'] if a['id'] == artifact_id)
    zip_bytes = archive.read_bytes()
    require(len(zip_bytes) == metadata['size_in_bytes'], host + ' ZIP size')
    require('sha256:' + sha(zip_bytes) == metadata['digest'], host + ' official ZIP digest')
    require(metadata['workflow_run']['head_sha'] == IMPL, host + ' artifact head')
    checksums = read(directory / 'checksums.json')
    members = []
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, host + ' ZIP CRC')
        names = z.namelist()
        require(len(names) == len(set(names)) == 17, host + ' ZIP member count')
        require(set(names) == set(checksums) | {'checksums.json'}, host + ' nested member set')
        require(set(names) == {p.name for p in directory.iterdir()}, host + ' extracted set')
        for name in names:
            data = z.read(name)
            require(data == (directory / name).read_bytes(), host + ' original/extracted bytes ' + name)
            record = {'name': name, 'bytes': len(data), 'sha256': sha(data)}
            if name in checksums:
                require(checksums[name] == {k: record[k] for k in ('bytes', 'sha256')}, host + ' nested hash ' + name)
            if name in ('tracked-files.json', 'final-tracked-files.json'):
                require(len(data) == 97657320 and sha(data) == TRACKED, host + ' full manifest')
            members.append(record)
    require((directory / 'revision.log').read_text().strip() == IMPL, host + ' revision log')
    summary = read(directory / 'summary.json')
    require(summary['implementation_commit'] == IMPL and summary['result'] == 'PASS'
        and summary['failures'] == [] and summary['fixture_tests_executed'] == 174,
        host + ' summary identity')
    require(summary['checks']['runtime_executed'] is False and summary['checks']['logic_executed'] is False,
        host + ' static scope')
    log = (directory / 'fixture-tests.log').read_text()
    require(re.search(r'^Ran 174 tests in [0-9.]+s$', log, re.M) and log.rstrip().endswith('OK'), host + ' actual unittest summary')
    names = re.findall(r'^(test_\S+) \(([^)]+)\)', log, re.M)
    require(len(names) == len(set(names)) == 174, host + ' actual distinct test names')
    commands = read(directory / 'commands.json')
    require(len(commands) == 6 and all(c['exit_code'] == 0 for c in commands), host + ' command exits')
    for c in commands:
        require(sha((directory / c['log']).read_bytes()) == c['log_sha256'], host + ' command log hash')
    retrieval = read(directory / 'source-retrieval.json')
    require(retrieval['result'] == 'PASS' and not retrieval['failures'] and
        retrieval['recursive_content_complete'] and retrieval['recursive_submodules_observed'] == 160,
        host + ' retrieval completeness')
    require(all(c['exit_code'] == 0 for c in retrieval['commands']), host + ' retrieval exits')
    require(summary['source_retrieval_sha256'] == sha((directory / 'source-retrieval.json').read_bytes()), host + ' retrieval digest')
    for filename in ('inventory.json', 'final-inventory.json'):
        inv = read(directory / filename)
        require(inv['inventory_status'] == 'VALID' and not inv['issues'], host + ' inventory validity')
        require(inv['source']['commit'] == inv['source']['checkout_head'] == IMPL, host + ' inventory identity')
        require(len(inv['submodules']) == 160 and len(inv['repositories']) == 161, host + ' closure counts')
        for r in inv['repositories']:
            require(r['checkout_head'] == r['commit'] and r['worktree_clean'] and
                not r['working_tree_status'] and not r['staged_index_changes'], host + ' clean repository ' + r['path'])
            require(r['materialization']['status'] == 'PASS' and
                r['materialization']['expected_blobs'] == r['materialization']['verified_blobs'], host + ' physical content ' + r['path'])
        inventories.append(inv)
    host_reports.append({'host': host, 'artifact_id': artifact_id, 'zip_bytes': len(zip_bytes),
        'zip_sha256': sha(zip_bytes), 'members': members, 'nested_hashes_verified': len(checksums),
        'actual_distinct_tests': len(names), 'commands_zero': len(commands),
        'retrieval_commands_zero': len(retrieval['commands']), 'result': 'PASS'})

inv = inventories[0]
require(all(x['repositories'] == inv['repositories'] and x['submodules'] == inv['submodules']
    for x in inventories), 'all four inventories agree on complete repository state')
manifest = read(RAW / 'p001-ubuntu-22.04/tracked-files.json')
require(manifest['source_commit'] == IMPL and len(manifest['entries']) == 293660, 'tracked identity/count')
groups = collections.defaultdict(list)
for entry in manifest['entries']:
    groups[entry['repository']].append(entry)
repositories = {r['path']: r for r in inv['repositories']}
require(set(groups) == set(repositories) and len(groups) == 161, 'manifest repository coverage')
tree_reports = []
gitlinks = {}
licenses = []
for path, entries in sorted(groups.items()):
    r = repositories[path]
    repo = repo_path(path)
    native = native_entries(repo, r['commit'])
    observed = {e['repository_path']: (e['mode'], e['type'], e['object']) for e in entries}
    require(native == observed and len(native) == len(entries) == r['tracked_entries'], 'native tracked entries ' + path)
    tree, count = reconstruct(entries)
    actual_tree = git(repo, 'rev-parse', r['commit'] + '^{tree}').decode().strip()
    require(tree == actual_tree == r['tree'], 'reconstructed native Git tree ' + path)
    tree_reports.append({'repository': path, 'commit': r['commit'], 'tree': tree,
        'tracked_entries': len(entries), 'native_trees_reconstructed': count})
    for entry in entries:
        if entry['mode'] == '160000':
            require(entry['path'] not in gitlinks, 'duplicate gitlink')
            gitlinks[entry['path']] = entry
    for license in r['licenses']:
        require(native[license['path']][::2] == (license['mode'], license['git_blob']), 'license native identity')
        data = git(repo, 'cat-file', 'blob', license['git_blob'])
        require(len(data) == license['bytes'] and sha(data) == license['sha256'], 'license bytes ' + path + '/' + license['path'])
        require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == license['git_blob'], 'license physical blob')
        licenses.append({'repository': path, 'path': license['path'], 'git_blob': license['git_blob'], 'sha256': sha(data)})
require(len(gitlinks) == 160 and len(licenses) == 755, 'complete gitlink/license counts')
modules = {m['path']: m for m in inv['submodules']}
require(set(modules) == set(gitlinks) and len(modules) == len(inv['submodules']), 'exact gitlink set')
provenance = read(RAW / 'p001-ubuntu-22.04/source-provenance.json')
for path, entry in gitlinks.items():
    m, r, p = modules[path], repositories[path], provenance['current_records'][path]
    require(entry['object'] == m['commit'] == r['commit'] == p['commit'], 'gitlink commit ' + path)
    require(entry['repository'] == m['repository'] == p['parent_path'], 'gitlink parent ' + path)
    require(p['tree'] == r['tree'], 'provenance tree ' + path)
    require(m['content_status'] == 'available_at_pin' and m['recursive_inventory'] == 'inspected', 'available recursive gitlink')
    require(m['resolved_url'].removesuffix('.git') == p['resolved_url'].removesuffix('.git'), 'gitlink URL ' + path)
for era in ('historical', 'current'):
    records = provenance[era + '_records']
    require(len(records) == 160, era + ' provenance count')
    for path, record in records.items():
        parent = record['parent_path']
        parent_commit = provenance[era + '_source_anchor'] if parent == '.' else records[parent]['commit']
        relative = path if parent == '.' else str(pathlib.PurePosixPath(path).relative_to(parent))
        native_pin = git(repo_path(parent), 'rev-parse', parent_commit + ':' + relative).decode().strip()
        native_tree = git(repo_path(path), 'rev-parse', record['commit'] + '^{tree}').decode().strip()
        require(native_pin == record['commit'] and native_tree == record['tree'], era + ' anchored graph ' + path)

source_manifest = json.loads(git(ROOT, 'show', IMPL + ':tools/compat/logic-pro/classifications.json'))
require(source_manifest['runtime_executed'] is False, 'static classification contract')
prior_manifest = json.loads(git(ROOT, 'show', 'c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a:tools/compat/logic-pro/classifications.json'))
require(source_manifest['evidence'] == prior_manifest['evidence'] and
    source_manifest['inspected_commit'] == prior_manifest['inspected_commit'], 'original historical citation contract unchanged')
historical = {e['id']: e for e in source_manifest['evidence']}
current = {e['id']: e for e in source_manifest['current_source_reaudit']['evidence']}
citations = read(RAW / 'p001-ubuntu-22.04/classifications.json')
require(set(historical) == set(current) and len(historical) == 63, 'citation manifest coverage')
citation_reports = []
for record in citations['checked']:
    ident = record['id']
    row = {'id': ident, 'historical': None, 'current': None}
    for era, citation, expected in [('historical', record, historical[ident]),
            ('current', record['current_source'], current[ident])]:
        path, commit = citation['repository'], citation['repository_commit']
        repo = repo_path(path)
        blob = git(repo, 'rev-parse', commit + ':' + citation['path']).decode().strip()
        data = git(repo, 'cat-file', 'blob', blob)
        require(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob, 'citation physical blob ' + ident)
        require(blob == citation['blob_sha1'] == expected['blob_sha1'], era + ' citation blob ' + ident)
        excerpt = b''.join(data.splitlines(keepends=True)[citation['line_start']-1:citation['line_end']])
        require(sha(excerpt) == citation['excerpt_sha256'] == expected['excerpt_sha256'], era + ' citation excerpt ' + ident)
        require(all(s.encode() in excerpt for s in expected['contains']), era + ' citation assertions ' + ident)
        if path == '.':
            require(commit == (IMPL if era == 'current' else source_manifest['inspected_commit']), era + ' root anchor ' + ident)
        else:
            parent, parent_commit = '.', provenance[era + '_source_anchor']
            for edge in citation['gitlink_chain']:
                relative = edge['path'] if parent == '.' else str(pathlib.PurePosixPath(edge['path']).relative_to(parent))
                actual = git(repo_path(parent), 'rev-parse', parent_commit + ':' + relative).decode().strip()
                require(actual == edge['commit'], era + ' citation gitlink chain ' + ident)
                parent, parent_commit = edge['path'], edge['commit']
            require(parent == path and parent_commit == commit, era + ' citation chain terminal ' + ident)
        row[era] = {'repository': path, 'commit': commit, 'blob': blob, 'excerpt_sha256': sha(excerpt), 'assertions': len(expected['contains'])}
    citation_reports.append(row)
require(len(citation_reports) == 63 and citations['status'] == 'PASS' and not citations['failures'], 'citation result')
require((RAW / 'p001-ubuntu-22.04/classifications.json').read_bytes() ==
    (RAW / 'p001-ubuntu-24.04/classifications.json').read_bytes(), 'host citation identity')

baseline = json.loads(git(ROOT, 'show', IMPL + ':docs/compat/logic-pro/baseline.json'))
require(git(ROOT, 'show', IMPL + ':docs/compat/logic-pro/baseline.json') ==
    git(ROOT, 'show', 'c7ef7fe4dc7801fd083b12a22bdbe43d13a8ab0a:docs/compat/logic-pro/baseline.json'), 'unchanged recovery manifest bytes')
require(baseline['baseline']['commit'] == '3447ff5ab8e837ea54a13a506c60d34d77e2bd15' and
    baseline['baseline']['tree'] == 'cfa2352b7296ef5667a8f8c5a11a5718bb3453a0' and
    baseline['baseline']['readme']['sha256'] == 'c4caa8d1815a58a763e91bd98cf5c3b40c6247d7c63ad5bfc61aa8291f5a14af' and
    baseline['integration']['commit'] == 'b25035fce2cd1c038c567d34ea0797371947d95d' and
    baseline['integration']['tree'] == '43461175ff5cfc470f1c1dbf1e4e202aa93a2123' and
    baseline['integration']['readme']['sha256'] == '9d2df6cb94822cf1335324fb5d77bb1c57773c4c20598c88baca4f06d6c5221d', 'original README acceptance anchors')
recovery_reports = []
for host in ('ubuntu-22.04', 'ubuntu-24.04'):
    recovery = read(RAW / ('p001-' + host) / 'recovery.json')
    require(recovery['result'] == 'PASS' and recovery['source']['head'] == IMPL
        and recovery['source']['unchanged_after_recovery'], host + ' recovery source unchanged')
    require(all(c['exit_code'] == 0 for c in recovery['commands']), host + ' recovery command exits')
    for snapshot in recovery['snapshots']:
        expected = baseline[snapshot['label']]
        require(snapshot['commit'] == expected['commit'] and snapshot['tree'] == expected['tree'], host + ' unchanged original recovery')
        require(git(ROOT, 'rev-parse', expected['commit'] + '^{tree}').decode().strip() == expected['tree'], 'original native tree')
        require(sha(git(ROOT, 'show', expected['commit'] + ':README.md')) == expected['readme']['sha256'] == snapshot['readme']['verified_sha256'], 'original README bytes')
        require(snapshot['independent_object_store'] and snapshot['working_tree_clean'] and snapshot['result'] == 'PASS', 'recovery isolation')
        recovery_reports.append({k: snapshot[k] for k in ('label', 'commit', 'tree', 'tracked_entries', 'verified_blobs', 'materialized_entries_sha256')})

report = {'result': 'PASS', 'completed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'implementation_commit': IMPL, 'reviewer': '/root/wave4_p001_evidence',
    'production_imports': False, 'source_checkout_root_commit': git(CHILDREN, 'rev-parse', 'HEAD').decode().strip(),
    'hosts': host_reports, 'tracked_manifest_bytes': 97657320, 'tracked_manifest_sha256': TRACKED,
    'tracked_entries_verified': len(manifest['entries']), 'repositories_verified': len(tree_reports),
    'native_tree_objects_reconstructed': sum(r['native_trees_reconstructed'] for r in tree_reports),
    'gitlinks_verified': len(gitlinks), 'historical_graph_pins_verified': 160,
    'current_graph_pins_verified': 160, 'licenses_verified': len(licenses),
    'license_scope': 'candidate discovery/byte provenance only; no legal approval',
    'historical_citations_verified': 63, 'current_citations_verified': 63,
    'trees': tree_reports, 'citations': citation_reports, 'license_candidates': licenses,
    'hosted_recovery': recovery_reports, 'runtime_or_later_phase_acceptance': False}
OUT.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('hosts','trees','citations','license_candidates','hosted_recovery')}, indent=2))
