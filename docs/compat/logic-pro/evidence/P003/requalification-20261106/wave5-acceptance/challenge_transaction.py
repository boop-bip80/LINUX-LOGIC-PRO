#!/usr/bin/env python3
"""Rehash a leaked-transaction result and challenge two separate validators.

The independent raw-evidence auditor has no producer imports. This script also
invokes the exact committed comparator as a separate, explicitly identified
control. Originals are read only; temporary copies stay under the output folder.
"""
import argparse
import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import audit_originals as independent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--originals', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checker_path = args.repo / 'tools/compat/logic-pro/compare_p003.py'
    exact = subprocess.check_output(['git', '-C', str(args.repo), 'show',
                                    independent.CANDIDATE + ':tools/compat/logic-pro/compare_p003.py'])
    independent.check(checker_path.read_bytes() == exact, 'comparator is not the exact tested source')
    sys.path.insert(0, str(checker_path.parent))
    spec = importlib.util.spec_from_file_location('committed_comparator', checker_path)
    comparator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(comparator)
    original = args.originals / 'independent-runtime'
    original_files = {str(p.relative_to(original)): independent.file_sha(p)
                      for p in original.rglob('*') if p.is_file()}
    baseline = independent.runtime(original / 'runtime', True)
    producer_baseline = comparator.validate_independent_review(
        original, args.originals/'build-a', args.originals/'build-b', independent.CANDIDATE)
    independent.check(producer_baseline['status'] == 'PASS', 'unmodified comparator control failed')
    with tempfile.TemporaryDirectory(prefix='rehashed-transaction-', dir=args.output.parent) as temp:
        copy = Path(temp) / 'independent-runtime'
        shutil.copytree(original, copy)
        raw_path = copy / 'runtime/foundation.stdout.log'
        before = raw_path.read_bytes()
        independent.check(before.count(b'deltas=1|2|1|0\n') == 1, 'unexpected original transaction trace')
        after = before.replace(b'deltas=1|2|1|0\n', b'deltas=1|2|1|1\n')
        raw_path.write_bytes(after)
        report_path = copy / 'runtime/report.json'
        report = independent.read_json(report_path)
        refs = [c['stdout'] for c in report['commands'] if c['label'] == 'foundation']
        refs += [r for r in report['evidence'] if r['file'] == 'foundation.stdout.log']
        independent.check(len(refs) == 2, 'not all raw-file digest references located')
        for ref in refs:
            ref['sha256'] = independent.sha(after)
            ref['bytes'] = len(after)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        independent.check(all(independent.bound(copy/'runtime', ref) == after for ref in refs),
                          'rehash did not satisfy byte-binding checks')
        evidence = args.output.parent / 'transaction-corruption'
        evidence.mkdir(exist_ok=False)
        (evidence/'foundation.stdout.log').write_bytes(after)
        (evidence/'report.json').write_bytes(report_path.read_bytes())
        results = {}
        checkers = {
            'independent_raw_auditor': lambda: independent.runtime(copy/'runtime', True),
            'committed_comparator': lambda: comparator.validate_independent_review(
                copy, args.originals/'build-a', args.originals/'build-b', independent.CANDIDATE),
        }
        for name, callback in checkers.items():
            try:
                callback()
            except Exception as error:
                text = str(error)
                independent.check(('Foundation transaction/value mismatch' in text if name == 'independent_raw_auditor'
                                   else 'P003_TRANSACTION' in text), 'rejected before behavioral check: ' + text)
                results[name] = {'verdict':'REJECTED_BEHAVIORAL_CORRUPTION',
                                 'exception':type(error).__name__, 'reason':text}
            else:
                raise ValueError(name + ' accepted a leaked transaction')
        receipt = {
            'schema':'darling.p003.wave5-rehashed-transaction-challenge.v1',
            'reviewer':'/root/wave5_acceptance', 'non_author':True,
            'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_commit':independent.CANDIDATE, 'run_id':independent.RUN,
            'helper_sha256':independent.file_sha(Path(__file__)),
            'independent_auditor_sha256':independent.file_sha(Path(independent.__file__)),
            'committed_comparator_sha256':independent.sha(exact),
            'unmodified_controls':{'independent_raw_auditor_cases':baseline['cases'],
                                   'committed_comparator_status':producer_baseline['status']},
            'mutation':'Replace final transaction delta 0 with 1, representing an unreleased live transaction; preserve PASS labels and all case counts.',
            'rehash':{'raw_file':'foundation.stdout.log', 'before_sha256':independent.sha(before),
                      'after_sha256':independent.sha(after), 'bytes':len(after),
                      'all_references_updated':len(refs), 'byte_binding_checks_pass':True,
                      'mutated_report_sha256':independent.file_sha(report_path)},
            'checker_results':results, 'phase_acceptance':False,
        }
    for name, digest in original_files.items():
        independent.check(independent.file_sha(original/name) == digest, 'original evidence modified')
    receipt['original_files_rehashed_unchanged'] = len(original_files)
    receipt['original_archives_unchanged'] = {}
    for name, (_, digest, _) in independent.EXPECTED_ARCHIVES.items():
        actual = independent.file_sha(args.originals/(name+'.zip'))
        independent.check(actual == digest, 'original archive modified')
        receipt['original_archives_unchanged'][name] = actual
    receipt['status'] = 'PASS_BOTH_SEMANTIC_REJECTIONS'
    with args.output.open('x') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'status':receipt['status'], 'semantic_rejections':len(results),
                      'original_files_unchanged':len(original_files)}))


if __name__ == '__main__':
    main()
