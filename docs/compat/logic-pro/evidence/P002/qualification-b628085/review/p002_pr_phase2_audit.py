#!/usr/bin/env python3
"""Independent P002 artifact and immutable-source audit (no network/writes to source)."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--source',type=Path,required=True)
parser.add_argument('--zip-a',type=Path,required=True)
parser.add_argument('--zip-b',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
SOURCE = args.source.resolve(strict=True)
SHA = 'b628085a19bae2d467fd9549ec0767636423a90a'
SOURCE_SHA = 'da1000be001711f80d6880eed9eeca916f6d0a23'
TREE_SHA = '37761104d97e824a2567f91dff2dea391bb635dd'
ARTIFACTS = {
    'a': (13063572615, 52899, '2615667b47864b103147b705ce192f1d0551c884579f75947c5cc48e21e9a219'),
    'b': (13062978587, 53339, 'a1b200168b0a6003c29967d0b73331d3b27cfc5c562c37aa16b5898c67057d8a'),
}
checks = []
def check(name, ok, detail=None):
    checks.append({'case': name, 'result': 'PASS' if ok else 'FAIL', 'detail': detail})
    if not ok:
        raise AssertionError(name)
def digest(data):
    return hashlib.sha256(data).hexdigest()
def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args])

check('Exact independently checked-out source SHA', git('rev-parse', 'HEAD').decode().strip() == SOURCE_SHA)
check('Source tree equals independently confirmed official PR merge tree', git('rev-parse','HEAD^{tree}').decode().strip() == TREE_SHA)
check('Production P002 source is unchanged from independently accepted technical candidate', not git('diff','--name-only','78dff3235e95d90e43faa4af7de34d5f926c9d28',SOURCE_SHA,'--','tools/compat/logic-pro/check_submodules.py','tools/compat/logic-pro/lfs_manifest.py','tools/compat/logic-pro/make_submodule_lock.py','tools/compat/logic-pro/run_submodule_campaign.py','docs/compat/logic-pro/submodules.lock.json','docs/compat/logic-pro/lfs-provenance.json','tests/compat/logic-pro/submodules').strip())
old_root_blobs=sum(b' blob ' in line for line in git('ls-tree','-r','78dff3235e95d90e43faa4af7de34d5f926c9d28').splitlines())
new_root_blobs=sum(b' blob ' in line for line in git('ls-tree','-r',SOURCE_SHA).splitlines())
expected_physical_blobs=293128+new_root_blobs-old_root_blobs
lock_bytes = (SOURCE/'docs/compat/logic-pro/submodules.lock.json').read_bytes()
lock = json.loads(lock_bytes)
provenance = json.loads((SOURCE/'docs/compat/logic-pro/evidence/P001/source-retrieval.json').read_bytes())
original = {e['path']: e for e in provenance['submodules']}
current = {e['path']: e for e in lock['submodules']}
check('Full original P001 recursive graph retained', len(current) == 160 and set(current) == set(original))
check('149 direct entries and 11 descendants', sum(e['parent_path'] == '.' for e in current.values()) == 149)
check('All 160 exact commit/tree/owner identities preserved', all(
    (e['commit'], e['tree'], e['parent_path']) == (original[p]['commit'], original[p]['tree'], original[p]['parent_path'])
    for p, e in current.items()))
check('No child pin changes in source integration', not git('diff', '--raw', '4707a919ef304945f7685390a68429242657eb54', SOURCE_SHA, '--', 'src').strip())
check('Exactly 44 LFS payloads and required byte count', len(lock['lfs_objects']) == 44 and sum(e['size'] for e in lock['lfs_objects']) == 16128448)
hosts = []
for host, (artifact_id, size, expected_digest) in ARTIFACTS.items():
    archive = getattr(args,'zip_'+host)
    data = archive.read_bytes()
    check(f'{host}: ZIP matches independently fetched official GitHub digest and size', len(data) == size and digest(data) == expected_digest)
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        check(f'{host}: 18 unique simple regular evidence files', len(entries) == 18 and len({e.filename for e in entries}) == 18 and all('/' not in e.filename and not e.is_dir() for e in entries))
        files = {e.filename: z.read(e) for e in entries}
    checksums = {}
    for line in files['checksums.sha256'].decode().splitlines():
        d, name = line.split('  ', 1)
        check(f'{host}: checksum {name}', digest(files[name]) == d)
        checksums[name] = d
    check(f'{host}: checksum coverage is complete', set(checksums) == set(files)-{'checksums.sha256'})
    summary = json.loads(files['summary.json'])
    check(f'{host}: real campaign and exact implementation passed', summary['result'] == 'PASS' and summary['implementation_commit'] == SHA and not summary['failures'] and summary['ordinary_git_acquisition'] is True and summary['credential_or_reference_cache_used'] is False)
    check(f'{host}: exact source and clone SHA', files['head.sha'].decode().strip() == files['source-head.sha'].decode().strip() == SHA)
    commands = json.loads(files['commands.json'])
    required_labels = ['git-version', 'source-head', 'clone-root', 'locate-exact-commit', 'checkout-exact-commit', 'verify-exact-head', 'ordinary-recursive-submodules', 'fixture-tests', 'git-lfs-version', 'hydrate-locked-lfs', 'native-recursive-status', 'strict-lock-verifier', 'regenerate-lock']
    locate=next(c for c in commands if c['label']=='locate-exact-commit')
    if locate['exit_code'] != 0:
        required_labels.insert(required_labels.index('checkout-exact-commit'),'fetch-exact-commit')
    check(f'{host}: required stages run in order without masked errors', [c['label'] for c in commands] == required_labels and all(c['exit_code'] == 0 or (c['label']=='locate-exact-commit' and c['exit_code']==128) for c in commands))
    if locate['exit_code']:
        fetch=next(c for c in commands if c['label']=='fetch-exact-commit')
        check(f'{host}: failed availability probe is repaired by successful immutable fetch', fetch['exit_code']==0 and fetch['command'][-1]==SHA)
    spans = {}
    for c in commands:
        raw = files[c['log']]
        start, length = c['log_offset'], c['log_bytes']
        check(f'{host}: command segment {c["label"]}', digest(raw[start:start+length]) == c['output_sha256'])
        spans.setdefault(c['log'], []).append((start, start+length))
    for name, ranges in spans.items():
        end = 0
        for start, stop in ranges:
            check(f'{host}: contiguous command transcript {name}', start == end)
            end = stop
        check(f'{host}: complete command transcript {name}', end == len(files[name]))
    fixture = files['fixture-tests.log'].decode()
    check(f'{host}: 96 actual tests passed without skips or expected failures', len(re.findall(r'^test_.* \.\.\. ', fixture, re.M)) == 96 and re.search(r'Ran 96 tests in ', fixture) and fixture.rstrip().endswith('\nOK') and 'skipped' not in fixture and 'expected failure' not in fixture)
    verify = json.loads(files[f'verification-{host}.json'])
    check(f'{host}: physical Git and LFS check complete', verify['result'] == 'PASS' and verify['root_commit'] == SHA and verify['verified_gitlinks'] == 160 and verify['verified_repositories'] == 161 and verify['verified_physical_blobs'] == expected_physical_blobs and verify['verified_lfs_payloads'] == 44 and verify['verified_lfs_bytes'] == 16128448 and all(verify[k] == 0 for k in ['uninitialized', 'mismatched', 'conflicted', 'dirty_repositories']))
    observed = {e['path']: e for e in verify['submodules']}
    check(f'{host}: verifier reports every original immutable pin/tree', set(observed) == set(current) and all((observed[p]['commit'], observed[p]['tree'], observed[p]['resolved_url']) == (e['commit'], e['tree'], e['resolved_url']) for p, e in current.items()))
    native = files['native-git-status.txt'].decode().splitlines()
    parsed = {}
    for line in native:
        m = re.fullmatch(r' ([a-f0-9]{40}) (\S+)(?: \(.*\))?', line)
        check(f'{host}: native initialized status line', bool(m))
        parsed[m[2]] = m[1]
    check(f'{host}: native Git independently matches lock pins', len(native) == 160 and parsed == {p:e['commit'] for p,e in current.items()})
    hydration = json.loads(files['lfs-hydration.json'])
    check(f'{host}: LFS raw acquisition contains all exact objects', hydration['result'] == 'PASS' and hydration['verified_lfs_objects'] == 44 and hydration['verified_payload_bytes'] == 16128448 and not hydration['errors'] and hydration['objects'] == [{k:e[k] for k in ('path','oid_sha256','size','mode')} | {'status':'PASS'} for e in lock['lfs_objects']])
    check(f'{host}: lock regeneration matches independently checked out bytes', files['regenerated-lock.json'] == lock_bytes)
    hosts.append({'host':host,'artifact_id':artifact_id,'archive_sha256':expected_digest,'raw_member_hashes':{n:digest(b) for n,b in files.items()},'environment':json.loads(files['environment.txt'])})
report = {'schema_version':1,'phase':'P002','reviewer':'/root/phase2_audit','tested_commit':SHA,'source_commit':SOURCE_SHA,'tested_tree':TREE_SHA,'workflow_run_id':41256694572,'expected_physical_blobs':expected_physical_blobs,'scope':'Original P002 source closure, independently verified official artifacts and all raw member integrity, commands, payload provenance and failure tests','result':'PASS_WITHIN_REVIEWED_SCOPE','whole_phase_verdict':'NOT_ACCEPTED_PENDING_DURABLE_EVIDENCE_PUBLICATION','production_authorship':False,'lock_sha256':digest(lock_bytes),'hosts':hosts,'checks':checks,'limits':['No held historical archive was modified, uploaded, reconstructed or re-encoded.','This artifact audit verifies official hosted executions; the local source clone is only for independent fixtures, not an additional anonymous source-acquisition proof.','Raw artifact preservation in a public commit and required complete P001 evidence remain integration gates.']}
out = args.output
out.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
print(json.dumps({'result':report['result'],'checks':len(checks),'report':str(out)}))
