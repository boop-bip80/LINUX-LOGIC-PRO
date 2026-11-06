#!/usr/bin/env python3
"""Verify final review references; this helper does not grant acceptance."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

CANDIDATE = '4622a9396c5c9fbe0014bdf6a2f695dcc491233c'
TREE = '9db3623bd2c81d18b17b29c921b1d6212ca1339d'
PEERS = [
    ('wave4-build/final-paired-builds.json','70cf0ce101611124394ed1caecd5590aac70beb775ec4c649c0f3fd1d7dda6dc','wave4-build.md','913b7fd2e5f59fae03c1017e3e09754b98f1c071d8b043c9cf266df8f9f3c9bd','/root/wave4_build'),
    ('wave4-package/final-4622a939/final-verdict.json','724fdba9ad9cf2128a357c6c0a279d4a58d61a392b6d0d14e944ecce422d7ffc','wave4-package.md','aed015691dc1fc2d5db1023683c69d146d80090d1fad396455c1e1e5ef8fcc4e','/root/wave4_package'),
    ('wave4-runtime/final-462/summary.json','d5ef7cc10b1519ee99f39f495b97bbf73b54dddc39db6e41b740e37ceb6a80bb','wave4-runtime.md','c9116e1d9a28d5cbc121f840560cb6d21db6c9511e4308a01e08f3cf3ab1b2ae','/root/wave4_runtime'),
    ('wave5-source/current-source-review.json','9a097b4f6f332e7604da850872ec5b633ad6708aeed614865f4ed4a543e0c51d','wave5-source.md','2024a142629576e8f34225a90e419d9545eda8f29876ab6c8ba53f6bb4add0bb','/root/wave5_source'),
    ('wave5-package/final-review-receipt.json','a022ee10cb9a2a316ac684c346e5743441ece132c904088a3cb80245e67017a9','wave5-package.md','e48aa173668904da276ba4d3d428a807b6b53e2b7575f5a65f21907b60ecb10b','/root/wave5_package'),
]


def require(value, message):
    if not value:
        raise ValueError(message)


def record(path):
    data = path.read_bytes()
    return {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--originals',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    campaign = args.repo/'docs/compat/logic-pro/evidence/P003/requalification-20261106'
    result = {'schema':'darling.p003.wave5-final-evidence-closure.v1',
              'reviewer':'/root/wave5_acceptance','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_commit':CANDIDATE,'tree':TREE,'run_id':42180484781,'phase_acceptance':False,
              'helper':record(Path(__file__)),'peers':[],'verified_references':{}}
    def verify(path, expected):
        actual = record(path)
        require(actual['sha256'] == expected['sha256'], 'changed referenced evidence: '+str(path))
        if 'bytes' in expected:
            require(actual['bytes'] == expected['bytes'], 'changed referenced evidence length')
        result['verified_references'][str(path.relative_to(campaign))] = actual
    reports = {}
    for path, digest, report_path, report_digest, reviewer in PEERS:
        verify(campaign/path, {'sha256':digest})
        verify(campaign/report_path, {'sha256':report_digest})
        report = json.loads((campaign/path).read_bytes())
        source = report.get('source_commit',report.get('implementation',report.get('source')))
        run = report.get('run_id',report.get('hosted_run',report.get('run')))
        require(source == CANDIDATE and run == 42180484781 and report['reviewer'] == reviewer,
                'peer candidate/run/reviewer binding')
        require(report.get('tree',report.get('source_tree',TREE)) == TREE, 'peer tree binding')
        reports[reviewer] = report
        result['peers'].append({'reviewer':reviewer,'receipt':path,'receipt_sha256':digest,
                                'report':report_path,'report_sha256':report_digest})
    build = reports['/root/wave4_build']
    require(build['non_author'] is True and build['verdict'] == 'APPROVED_SOURCE_FROZEN_TOOLCHAIN_TWO_FRESH_BUILDS_AND_PER_HOST_LIFECYCLE', 'build approval')
    for side in ['a','b']:
        verify(campaign/f'wave4-build/final-{side}-archive.json', {'sha256':build['archive_receipts_sha256'][side]})
        verify(campaign/f'wave4-build/final-{side}-build.json', {'sha256':build['build_receipts_sha256'][side]})
    for name,digest in build['review_helpers_sha256'].items():
        verify(campaign/'wave4-build'/name,{'sha256':digest})
    package4 = reports['/root/wave4_package']
    require(package4['non_author_of_production_and_unchanged_byte_comparator'] is True
            and package4['gates']['G1']['verdict'] == package4['gates']['G2']['verdict'] == 'PASS'
            and package4['unexplained_package_discrepancies'] == [], 'Wave 4 package approval')
    for name,ref in package4['evidence'].items():
        verify(campaign/'wave4-package/final-4622a939'/name,ref)
    runtime = reports['/root/wave4_runtime']
    require(runtime['reviewer_non_author'] is True and runtime['gate_verdicts'] == {'G3':'PASS','G4':'PASS'}
            and runtime['actual_cases_checked'] == 50 and runtime['new_production_defects'] == [], 'runtime approval')
    for name,ref in runtime['receipt_files'].items():
        verify(campaign/'wave4-runtime/final-462'/name,ref)
    verify(campaign/'wave4-runtime/audit_runtime.py',{'sha256':runtime['independent_auditor_unchanged_sha256']})
    source = reports['/root/wave5_source']
    require(source['source_scope_verdict'] == 'APPROVED' and source['paired_source_toolchain_and_configuration_identity'] is True, 'source approval')
    git = lambda *argv: subprocess.check_output(['git','-C',str(args.repo),*argv])
    for name,digest in source['production_validator_file_hashes'].items():
        require(hashlib.sha256(git('show',CANDIDATE+':'+name)).hexdigest() == digest, 'exact source validator hash')
        require(record(args.repo/name)['sha256'] == digest, 'working production validator changed')
    for name in ['corrected-commit-binding.json','interruption-before.json','interruption-after-4622a939.json','abort-regressions.log','corrected-preflight-review.json']:
        result['verified_references']['wave5-source/'+name] = record(campaign/'wave5-source'/name)
    package5 = reports['/root/wave5_package']
    require(package5['status'] == 'APPROVED_PACKAGE_SCOPE' and set(package5['gates'].values()) == {'APPROVED'}
            and package5['results']['unclassified_bytes'] == 0 and package5['wave4_reconciliation']['status'] == 'AGREED', 'Wave 5 package approval')
    for name,ref in package5['outputs'].items():
        verify(campaign/'wave5-package'/name,ref)
    for name,ref in package5['wave4_reconciliation']['inputs'].items():
        verify(campaign/name,ref)
    original_audit = json.loads((campaign/'wave5-acceptance/original-runtime-audit.json').read_bytes())
    for name, details in package5['originals'].items():
        own = original_audit['archives'][name]
        require(own['sha256'] == details['sha256'] and own['bytes'] == details['bytes']
                and own['member_count'] == details['member_count'], 'peer original archive differs')
    for filename,status in [('original-runtime-audit.json','PASS_SCOPED_ORIGINAL_RUNTIME_AND_BINDING_RECOMPUTATION'),
                             ('rehashed-transaction-challenge.json','PASS_BOTH_SEMANTIC_REJECTIONS'),
                             ('package-table-reconciliation.json','PASS_TABLE_RECONCILIATION')]:
        path = campaign/'wave5-acceptance'/filename
        data = json.loads(path.read_bytes())
        require(data['status'] == status and data['source_commit'] == CANDIDATE and data['phase_acceptance'] is False,
                'own scoped review prerequisite')
        result['verified_references']['wave5-acceptance/'+filename] = record(path)
    fixture = args.originals/'fixtures.zip'
    require(record(fixture) == {'bytes':11686,'sha256':'155fcbc2432969eca8248a4f8166c1d55c2e584a95dce3650f8793bd77cf00ed'}, 'exact corrected fixture ZIP')
    require(record(fixture) == record(campaign/'attempt-4622a93/fixtures.zip'), 'published fixture ZIP differs')
    fixture_rows = []
    with zipfile.ZipFile(fixture) as z:
        require(len(z.infolist()) == 4 and z.testzip() is None, 'fixture members/CRC')
        for info in z.infolist():
            text = z.read(info).decode('utf-8')
            counts = re.findall(r'^Ran ([0-9]+) tests? in ',text,re.M)
            if counts:
                require(len(counts) == 1 and text.rstrip().endswith('OK') and not re.search(r'^OK \(',text,re.M), 'nonplain or substituted fixture outcome')
                fixture_rows.append({'member':info.filename,'tests':int(counts[0]),'sha256':hashlib.sha256(z.read(info)).hexdigest()})
    require(sorted(row['tests'] for row in fixture_rows) == [115,174,201], 'corrected mandatory suite counts')
    result['fixture_original'] = {**record(fixture),'members':4,'suites':fixture_rows}
    diagnostic_rows = []
    messages = ['Validation layer requested but not available. Ignoring...',
                '_CFGetHostUUIDString: unable to determine UUID for host. Error: 78']
    for relative in ['build-a/probes-first','build-a/probes-second','build-b/probes-first','build-b/probes-second','independent-runtime/runtime']:
        raw = args.originals/relative/'gui.stderr.log'
        text = raw.read_text()
        require(all(message in text for message in messages), 'raw diagnostic account differs')
        diagnostic_rows.append({'path':relative+'/gui.stderr.log',**record(raw)})
    result['retained_gui_diagnostics'] = {'exact_messages':messages,'original_files':diagnostic_rows,
        'interpretation':'The validation-layer notice and host-UUID error are retained, not suppressed. P003 asserts the selected installed owners, actual computation/Foundation object/transaction results, externally driven GUI events/pixels, and clean lifecycle. Those assertions independently pass; neither a working validation layer nor host UUID operation is claimed. Broader framework/API completeness remains unqualified. The guest rendered=2 receipt denotes its enforced minimum draws >= 2, not exact draw-count instrumentation.'}
    head = git('rev-parse','HEAD').decode().strip()
    changed = git('diff','--name-only',CANDIDATE,head).decode().splitlines()
    allowed = lambda name: name == 'README.md' or name.startswith('docs/compat/logic-pro/evidence/')
    require(all(allowed(name) for name in changed), 'post-tested execution changes')
    require(all(allowed(name) for name in git('diff','--name-only','HEAD').decode().splitlines()), 'uncommitted execution changes')
    require(git('rev-parse',CANDIDATE+'^{tree}').decode().strip() == TREE,'tested implementation tree')
    result['documentation_continuity'] = {'head':head,'post_test_changed_paths':len(changed),'all_readme_or_evidence':True}
    result['status'] = 'ALL_REQUIRED_FINAL_REVIEW_RECORDS_BOUND'
    result['bound_reference_count'] = len(result['verified_references'])
    with args.output.open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:result[k] for k in ['status','bound_reference_count','phase_acceptance']}))


if __name__ == '__main__':
    main()
