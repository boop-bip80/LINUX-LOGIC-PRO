#!/usr/bin/env python3
"""Independent review of hosted retrieval and citations, excluding authored gates."""
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

BASE = Path(__file__).resolve().parent
SOURCE = Path('/workspace/scratch/42c72cef8fac/verified-master')
COMMIT = '4707a919ef304945f7685390a68429242657eb54'
TREE = '8fb4a8c4b7855d2dec827a9e4d6499cb113b3776'
CATEGORIES = {'native_linux_host', 'macho_runtime_component', 'implemented_body_unqualified',
              'partial_framework', 'developer_link_stub', 'generated_stub_tooling',
              'generated_style_stub_body', 'architecture_constraint'}
STAGES = {'host_launch', 'mldr_mapping_and_dyld_handoff', 'dyld_dependency_loading',
          'system_library_initialization', 'server_checkin_and_rpc_dispatch', 'framework_initialization'}
ENV = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
ENV.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_NO_REPLACE_OBJECTS='1',
           GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_OPTIONAL_LOCKS='0')


def git(repo, *args):
    return subprocess.check_output(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                                    '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args], env=ENV)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def review(label):
    folder = BASE / label
    summary = read(folder / 'summary.json')
    retrieval = read(folder / 'source-retrieval.json')
    citations = read(folder / 'classifications.json')
    commands = read(folder / 'commands.json')
    checksums = read(folder / 'checksums.json')
    native = read(BASE / 'native-pin-manifest.json')
    manifest = read(SOURCE / 'tools/compat/logic-pro/classifications.json')
    artifact = read(folder / 'artifact-metadata.json')
    assert artifact['workflow_run']['head_sha'] == COMMIT
    assert artifact['workflow_run']['head_branch'] == 'master'
    assert artifact['workflow_run']['id'] == 41240503365
    assert summary['result'] == 'PASS' and not summary['failures']
    assert summary['implementation_commit'] == COMMIT and summary['fixture_tests_executed'] == 109
    assert summary['checks']['runtime_executed'] is False and summary['checks']['logic_executed'] is False
    assert sha(folder / 'source-retrieval.json') == summary['source_retrieval_sha256']
    assert retrieval['result'] == 'PASS' and not retrieval['failures']
    assert retrieval['source']['commit'] == COMMIT and retrieval['source']['tree'] == TREE
    assert retrieval['source']['parent_source_unchanged'] is True
    assert retrieval['source']['upstream_url'] == 'https://github.com/darlinghq/darling.git'
    assert retrieval['source']['original_origin'].rstrip('/').removesuffix('.git') == 'https://github.com/boop-bip80/MAC-OS-EMULATION'
    assert retrieval['recursive_content_complete'] is True and retrieval['recursive_submodules_observed'] == 160
    native_repos = {entry['path']: entry for entry in native['repositories']}
    native_links = {entry['path']: entry for entry in native['gitlinks']}
    hosted_links = {entry['path']: entry for entry in retrieval['submodules']}
    assert len(hosted_links) == len(retrieval['submodules']) == 160
    assert set(hosted_links) == set(native_links)
    attributes = b'* -text -eol -ident -filter -working-tree-encoding\n'
    policy = retrieval['fresh_checkout_policy']
    assert policy['attributes'].encode() == attributes
    assert policy['attributes_sha256'] == hashlib.sha256(attributes).hexdigest()
    assert policy['committed_attributes_modified'] is False
    for path, record in hosted_links.items():
        assert record['commit'] == native_links[path]['commit'], path
        assert record['parent_path'] == native_links[path]['parent_path'], path
        assert record['tree'] == native_repos[path]['tree'], path
        assert record['fetch_url'] == record['configured_origin'] == native_repos[path]['public_origin'], path
        assert record['status'] == 'PASS' and record['retrieval'] == 'FETCHED_EXACT_PIN', path
        assert record['checkout_policy']['applied_to_fresh_checkout'] is True, path
        assert record['checkout_policy']['attributes_path'] == '.git/info/attributes', path
        assert record['checkout_policy']['attributes_sha256'] == policy['attributes_sha256'], path
    # Read declarations independently from the exact parent Git blobs, without
    # importing either the retrieval implementation or the authored inventory.
    declaration_sets = {}
    for parent in {record['parent_path'] for record in hosted_links.values()}:
        local = SOURCE if parent == '.' else SOURCE / parent
        config = git(local, 'config', '--no-includes', '--blob', native_repos[parent]['commit'] + ':.gitmodules', '--null', '--list')
        sections = {}
        for raw in config.split(b'\0'):
            if not raw:
                continue
            key, _, value = raw.partition(b'\n')
            key = key.decode()
            if key.startswith('submodule.'):
                name, field = key[len('submodule.'):].rsplit('.', 1)
                if field in ('path', 'url'):
                    assert field not in sections.setdefault(name, {})
                    sections[name][field] = value.decode()
        declaration_sets[parent] = {entry['path']: {'name': name, **entry} for name, entry in sections.items()}
    def resolve(base, declared):
        return urljoin(base.rstrip('/') + '/', declared) if declared.startswith(('../', './')) else declared
    def https_source(url):
        if url.startswith('git@github.com:'):
            return 'https://github.com/' + url.split(':', 1)[1]
        parts = urlsplit(url)
        if parts.hostname == 'github.com' and parts.scheme in ('git', 'ssh'):
            return urlunsplit(('https', 'github.com', parts.path, '', ''))
        return url
    for path, record in hosted_links.items():
        parent = record['parent_path']
        declaration = declaration_sets[parent][native_links[path]['repository_path']]
        assert declaration['name'] == record['name'] and declaration['url'] == record['declared_url'], path
        declared_base = retrieval['source']['original_origin'] if parent == '.' else native_repos[parent]['public_origin']
        acquisition_base = retrieval['source']['upstream_url'] if parent == '.' else native_repos[parent]['public_origin']
        assert record['resolved_url'] == resolve(declared_base, declaration['url']), path
        assert record['acquisition_resolved_url'] == resolve(acquisition_base, declaration['url']), path
        assert record['fetch_url'] == https_source(record['acquisition_resolved_url']), path
    fetches = [entry for entry in retrieval['commands'] if 'fetch' in entry['command']]
    checkouts = [entry for entry in retrieval['commands'] if 'checkout' in entry['command']]
    remotes = [entry for entry in retrieval['commands'] if 'remote' in entry['command'] and 'add' in entry['command']]
    pins = collections.Counter(entry['commit'] for entry in hosted_links.values())
    assert len(fetches) == len(checkouts) == len(remotes) == 160
    assert collections.Counter(entry['command'][-1] for entry in fetches) == pins
    assert collections.Counter(entry['command'][-1] for entry in checkouts) == pins
    assert collections.Counter(entry['command'][-1] for entry in remotes) == collections.Counter(entry['fetch_url'] for entry in hosted_links.values())
    for entry in fetches:
        assert entry['exit_code'] == 0
        assert '--depth=1' in entry['command'] and '--no-tags' in entry['command'] and '--no-recurse-submodules' in entry['command']
    for entry in checkouts:
        assert entry['exit_code'] == 0 and '--detach' in entry['command']
    assert citations['status'] == 'PASS' and not citations['failures']
    assert citations['current_commit'] == COMMIT and citations['inspected_commit'] == manifest['inspected_commit']
    assert citations['checked_count'] == len(citations['checked']) == 63
    assert citations['source_file_count'] == len({(c['repository'], c['path']) for c in citations['checked']}) == 41
    assert citations['coverage']['required'] is True and citations['coverage']['status'] == 'PASS'
    assert set(citations['coverage']['required_categories']) == CATEGORIES
    assert set(citations['coverage']['required_stages']) == STAGES
    assert set(citations['coverage']['launch_stages']) == STAGES
    assert not citations['coverage']['missing_categories'] and not citations['coverage']['missing_stages']
    assert not citations['coverage']['missing_stage_sources']
    declared = {entry['id']: entry for entry in manifest['evidence']}
    assert len(declared) == len(manifest['evidence']) == 63
    assert {entry['id'] for entry in citations['checked']} == set(declared)
    assert manifest['runtime_executed'] is False
    cache = {}
    verified = []
    for record in citations['checked']:
        definition = declared[record['id']]
        for field in ('category', 'path', 'line_start', 'line_end', 'blob_sha1', 'excerpt_sha256'):
            assert record[field] == definition[field], (record['id'], field)
        assert record['launch_stages'] == definition.get('launch_stages', [])
        owner = definition.get('repository', '.')
        assert record['repository'] == owner
        assert record['gitlink_chain'] == definition.get('gitlink_chain', [])
        source = SOURCE if owner == '.' else SOURCE / owner
        pin = manifest['inspected_commit'] if owner == '.' else native_links[owner]['commit']
        assert record['repository_commit'] == pin
        chain_source, chain_pin, chain_now = SOURCE, manifest['inspected_commit'], COMMIT
        chain_owner = []
        for hop in record['gitlink_chain']:
            expected = ('160000 commit ' + hop['commit'] + '\t' + hop['path'] + '\0').encode()
            for revision in {chain_pin, chain_now}:
                assert git(chain_source, '--literal-pathspecs', 'ls-tree', '-z', revision, '--', hop['path']) == expected
            chain_source = chain_source / hop['path']
            chain_pin = chain_now = hop['commit']
            chain_owner.append(hop['path'])
            assert git(chain_source, 'rev-parse', 'HEAD').decode().strip() == chain_pin
        if owner != '.':
            assert '/'.join(chain_owner) == owner and chain_pin == pin
        key = owner, record['path']
        if key not in cache:
            blob = git(source, 'rev-parse', pin + ':' + record['path']).decode().strip()
            data = git(source, 'cat-file', 'blob', blob)
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == blob
            current = COMMIT if owner == '.' else pin
            assert git(source, 'rev-parse', current + ':' + record['path']).decode().strip() == blob
            cache[key] = blob, data
        blob, data = cache[key]
        assert blob == record['blob_sha1']
        excerpt = b''.join(data.splitlines(keepends=True)[record['line_start'] - 1:record['line_end']])
        assert hashlib.sha256(excerpt).hexdigest() == record['excerpt_sha256'], record['id']
        assert all(token.encode() in excerpt for token in definition['contains'])
        verified.append({'id': record['id'], 'repository': owner, 'repository_commit': pin,
                         'path': record['path'], 'blob_sha1': blob, 'excerpt_sha256': record['excerpt_sha256']})
    command_by_label = {entry['label']: entry for entry in commands}
    assert len(command_by_label) == len(commands)
    assert all(entry['exit_code'] == 0 for entry in commands)
    for entry in commands:
        assert entry['log_sha256'] == checksums[entry['log']]['sha256']
    assert command_by_label['classifications']['command'][-1] == '--require-phase-coverage'
    log = (folder / 'job.log').read_text(encoding='utf-8-sig')
    assert len(re.findall(r'Ran 109 tests in ', log)) == 1
    assert re.search(r'Ran 109 tests in [^\n]+\n[^\n]*\n[^\n]*OK', log)
    pairs = [{'path': name, 'commit': record['commit']} for name, record in sorted(hosted_links.items())]
    pin_digest = hashlib.sha256(json.dumps(pairs, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert pin_digest == native['canonical_pin_pairs_sha256']
    result = {
        'reviewer': '/root/inventory_tool', 'review_date': '2026-10-31', 'implementation_commit': COMMIT,
        'implementation_tree': TREE, 'environment': label, 'workflow_run': 41240503365,
        'artifact': {'id': artifact['id'], 'name': artifact['name'], 'github_digest': artifact['digest']},
        'scope': 'Independent hosted retrieval/provenance and static-source citation review; excludes authored inventory/runner implementations.',
        'report_sha256': {name: sha(folder / name) for name in ('source-retrieval.json', 'classifications.json', 'summary.json', 'checksums.json', 'commands.json')},
        'recursive_gitlinks_compared_to_native_git': 160, 'direct_gitlinks': 149,
        'fresh_exact_pin_fetches': len(fetches), 'recorded_origins_and_trees_match_native_git': True,
        'declared_urls_checked_against_native_gitmodules': 160,
        'fork_and_upstream_resolution_independently_recomputed': True,
        'canonical_pin_pairs_sha256': pin_digest, 'submodule_pins': pairs,
        'static_citations_recomputed_from_native_git': len(verified), 'unique_source_files': len(cache),
        'child_citations': sum(entry['repository'] != '.' for entry in verified),
        'required_categories': sorted(CATEGORIES), 'required_launch_stages': sorted(STAGES),
        'fixture_tests_reported_and_observed_in_hosted_logs': 109,
        'verified_citations': verified, 'runtime_executed': False,
        'verdict': 'PASS_FOR_RETRIEVAL_AND_STATIC_SOURCE_MAP_SCOPE',
        'whole_phase_acceptance': 'Requires complementary independent review of inventory/runner and complete raw artifacts.'
    }
    (folder / 'independent-review.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('submodule_pins', 'verified_citations')}, indent=2))


if __name__ == '__main__':
    for target in sys.argv[1:]:
        review(target)
