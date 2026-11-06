#!/usr/bin/env python3
"""Independent offline adjudication of P003 originals; executes no guest code.

Uses Python's standard library only. Does not import producer or peer checkers.
The scoped result is not a whole-phase acceptance decision.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tarfile
import zipfile
import zlib

CANDIDATE = '4622a9396c5c9fbe0014bdf6a2f695dcc491233c'
TREE = '9db3623bd2c81d18b17b29c921b1d6212ca1339d'
PREDECESSOR = 'd58cca513559cfef0ff9af59aa5dc3b6341bdf77'
RUN = 42180484781
INSTALL = '/opt/darling-p003'
FRAMEWORKS = {name: '/System/Library/Frameworks/' + name + '.framework/Versions/' + version + '/' + name
              for name, version in [('AppKit', 'C'), ('Foundation', 'C'), ('CoreGraphics', 'A'),
                                    ('CoreText', 'A'), ('ImageIO', 'A'), ('QuartzCore', 'A'),
                                    ('AudioToolbox', 'A')]}
EXPECTED_ARCHIVES = {
    'build-a': (87409741, '27b4a147ff1993bc6756172767cb4d60a8d4e437d5f9d85effe039571d5aa038', 459),
    'build-b': (87410244, 'a7c394d71cc4d83857c0dd2988291c0b9e4bf31cb1555785c2e71dfcd6387759', 459),
    'independent-runtime': (36170, 'c77fdb0085e892cd39ea30b36c2e5e352a87f3f17e0d05234b5395b8c32a46a9', 48),
    'comparison': (35804, '92fac49f42ffc2e03d267cef76f4bdc2841803b0a429c38b9f216475e8012915', 1),
}
CASE_NAMES = {'macho-known-vector', 'macho-nonce', 'macho-boundary-64', 'macho-reject-65',
              'macho-invalid-arguments', 'foundation-invalid-arguments', 'gui-invalid-arguments',
              'foundation-objects', 'gui-event-roundtrip', 'runtime-shutdown'}
EXITS = {name: 0 for name in ['macho-known-vector', 'macho-nonce', 'macho-boundary-64', 'foundation',
                            'gui', 'gui-focus', 'gui-move', 'gui-click', 'gui-type', 'gui-acknowledge', 'shutdown']}
EXITS.update({name: 64 for name in ['macho-reject-65', 'macho-invalid', 'foundation-invalid', 'gui-invalid']})


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def bound(root, ref):
    n = ref['file']
    check(n and PurePosixPath(n).name == n and n not in ['.', '..'], 'noncanonical evidence name')
    p = root / n
    check(p.is_file() and not p.is_symlink(), 'non-regular evidence: ' + str(p))
    b = p.read_bytes()
    check(sha(b) == ref['sha256'], 'evidence digest mismatch: ' + str(p))
    if 'bytes' in ref:
        check(len(b) == ref['bytes'], 'evidence length mismatch: ' + str(p))
    return b


def archives(root, metadata):
    result = {}
    for name, (size, digest, count) in EXPECTED_ARCHIVES.items():
        p = root / (name + '.zip')
        check(p.stat().st_size == size and file_sha(p) == digest, 'original ZIP identity: ' + name)
        matches = [a for a in metadata['artifacts']['artifacts'] if a['name'] == f'p003-{name}-{CANDIDATE}']
        check(len(matches) == 1, 'official artifact name: ' + name)
        meta = matches[0]
        check(meta['digest'] == 'sha256:' + digest and meta['size_in_bytes'] == size, 'official ZIP metadata')
        check(meta['workflow_run']['head_sha'] == CANDIDATE and meta['workflow_run']['id'] == RUN,
              'official artifact source/run')
        members = {}
        with zipfile.ZipFile(p) as z:
            check(len(z.infolist()) == count, 'ZIP member count')
            for item in z.infolist():
                n = item.filename
                rel = PurePosixPath(n)
                check(not rel.is_absolute() and '..' not in rel.parts and str(rel) == n.rstrip('/'), 'unsafe ZIP member')
                check(n not in members, 'duplicate ZIP member')
                if item.is_dir():
                    members[n] = {'directory': True}
                    continue
                target = root / name / n
                check(target.is_file() and not target.is_symlink(), 'missing extracted original member')
                h = hashlib.sha256()
                length = 0
                with z.open(item) as a, target.open('rb') as b:
                    for chunk in iter(lambda: a.read(1024 * 1024), b''):
                        check(chunk == b.read(len(chunk)), 'extraction differs: ' + n)
                        h.update(chunk)
                        length += len(chunk)
                    check(b.read(1) == b'', 'extra extracted bytes: ' + n)
                check(length == item.file_size, 'ZIP decoded length')
                members[n] = {'bytes': length, 'sha256': h.hexdigest(), 'crc32': f'{item.CRC:08x}'}
        check({str(p.relative_to(root / name)) for p in (root / name).rglob('*') if p.is_file()}
              == {n for n, value in members.items() if not value.get('directory')}, 'unbound extracted members')
        result[name] = {'bytes': size, 'sha256': digest, 'artifact_id': meta['id'], 'member_count': count,
                        'crc_and_extraction_fidelity': True, 'members': members}
    return result


def fnv(text):
    value = 2166136261
    for byte in text.encode('ascii'):
        value = ((value ^ byte) * 16777619) % (1 << 32)
    return f'{value:08x}'


def decode_xwd(data, expected_title):
    check(len(data) >= 100, 'short XWD')
    h = struct.unpack('>25I', data[:100])
    header, version, form, depth, width, height, xoffset, order = h[:8]
    check(version == 7 and form == 2 and depth == 24 and h[11] == 32 and h[13] == 4, 'unexpected actual XWD format')
    check(320 <= width <= 1024 and 200 <= height <= 768 and xoffset == 0 and order in [0, 1], 'XWD dimensions/order')
    check(h[14:17] == (0xff0000, 0xff00, 0xff) and h[12] == width * 4, 'XWD color masks/stride')
    check(100 < header < len(data) and h[19] <= 4096, 'XWD header/palette bounds')
    title = data[100:header]
    check(title == expected_title.encode('ascii') + b'\0', 'nonce/state not bound to original XWD title')
    offset = header + 12 * h[19]
    check(offset + h[12] * height == len(data), 'XWD payload boundaries')
    rgb = bytearray()
    for row in range(height):
        words = struct.unpack(('<' if order == 0 else '>') + str(width) + 'I',
                              data[offset + row*h[12]:offset + (row+1)*h[12]])
        for word in words:
            rgb.extend([(word >> 16) & 255, (word >> 8) & 255, word & 255])
    return width, height, bytes(rgb)


def decode_png(data):
    check(data[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
    at, payload, header, ended = 8, bytearray(), None, False
    while at < len(data):
        check(at + 12 <= len(data), 'short PNG chunk')
        size = int.from_bytes(data[at:at+4], 'big')
        kind = data[at+4:at+8]
        content = data[at+8:at+8+size]
        check(len(content) == size and at + 12 + size <= len(data), 'PNG chunk bounds')
        crc = int.from_bytes(data[at+8+size:at+12+size], 'big')
        check(zlib.crc32(kind + content) & 0xffffffff == crc, 'PNG CRC')
        if kind == b'IHDR':
            check(header is None and size == 13, 'PNG IHDR')
            header = struct.unpack('>2I5B', content)
        elif kind == b'IDAT':
            payload.extend(content)
        elif kind == b'IEND':
            check(size == 0 and at + 12 == len(data), 'PNG IEND')
            ended = True
        at += size + 12
    check(ended and header and header[2:] == (8, 2, 0, 0, 0), 'PNG RGB8 structure')
    width, height = header[:2]
    raw = zlib.decompress(payload)
    row_size = width * 3 + 1
    check(len(raw) == row_size * height, 'PNG raster length')
    check(all(raw[y * row_size] == 0 for y in range(height)), 'expected lossless filter-zero review PNG')
    return width, height, b''.join(raw[y*row_size+1:(y+1)*row_size] for y in range(height))


def runtime(root, independent=False):
    report = read_json(root / 'report.json')
    check(report.get('source_commit' if independent else 'source_revision') == CANDIDATE, 'runtime exact source')
    check(report['passed'] is True and not report['errors'], 'runtime reported failure')
    expected_cases = CASE_NAMES.copy()
    if independent:
        expected_cases -= {'macho-nonce', 'foundation-objects'}
        expected_cases |= {'macho-fresh-nonce', 'foundation-fresh-nonce'}
    check(len(report['cases']) == 10 and {x['name'] for x in report['cases']} == expected_cases,
          'runtime case completeness')
    check(all(c['status'] == ('PASS' if independent else 'PASSED') for c in report['cases']), 'runtime case failure')
    nonce = report['nonce']
    check(re.fullmatch('[0-9a-f]{16}', nonce) is not None, 'nonce format')
    commands = {c['label']: c for c in report['commands']}
    check(len(commands) == len(report['commands']) == 15 and set(commands) == set(EXITS), 'runtime command coverage')
    streams = {}
    for label, cmd in commands.items():
        check(cmd['exit_code'] == EXITS[label] and cmd.get('timed_out', False) is False,
              'runtime command result: ' + label)
        streams[label] = {kind: bound(root, cmd[kind]).decode('utf-8') for kind in ['stdout', 'stderr']}
    for label, token in [('macho-known-vector', 'foobar' if independent else 'hello'),
                         ('macho-nonce', nonce), ('macho-boundary-64', 'a'*64)]:
        check(commands[label]['argv'] == [INSTALL+'/bin/darling', 'exec', INSTALL+'/libexec/darling/usr/libexec/p003/p003_macho', token],
              'Mach-O command/input binding')
        check(streams[label]['stdout'] == f'P003_MACHO nonce={token} hash={fnv(token)}\n', 'raw FNV result mismatch')
    for label, component in [('macho-reject-65', 'MACHO'), ('macho-invalid', 'MACHO'),
                              ('foundation-invalid', 'FOUNDATION'), ('gui-invalid', 'GUI')]:
        error = f'P003_{component}_ERROR ' + ('invalid challenge' if component == 'GUI' else 'invalid arguments')
        lines = [x for x in streams[label]['stderr'].splitlines() if x.startswith('P003_')]
        check(lines == [error] and streams[label]['stdout'] == '', 'typed negative path mismatch')
    check(commands['macho-reject-65']['argv'][-1] == 'a'*65, '65-byte input binding')
    check(commands['foundation']['argv'][-1] == nonce, 'Foundation nonce command binding')
    expected = f'P003_FOUNDATION nonce={nonce} items=alpha|beta|gamma count=3 answer=42 bytes=007fff missing=nil\n'
    expected += f'P003_TRANSACTION nonce={nonce} deltas=1|2|1|0\n'
    check(streams['foundation']['stdout'] == expected, 'raw Foundation transaction/value mismatch')
    gui = streams['gui']['stdout'].splitlines()
    check([x for x in gui if x.startswith('P003_GUI ')] ==
          [f'P003_GUI nonce={nonce} clicks=1 keys=16 rendered=2 acknowledged=1'], 'raw external event result mismatch')
    loaded = [x.removeprefix('P003_IMAGE ') for x in gui if x.startswith('P003_IMAGE ')]
    check(len(loaded) == 7 and set(loaded) == set(FRAMEWORKS.values()), 'live image owner mismatch')
    check(commands['gui']['argv'][-1] == nonce, 'GUI challenge input binding')
    wid = commands['gui-focus']['argv'][-1]
    check(wid.isdecimal() and int(wid) > 0, 'window id')
    check(commands['gui-focus']['argv'] == ['xdotool','windowfocus','--sync',wid], 'external focus')
    check(commands['gui-move']['argv'] == ['xdotool','mousemove','--window',wid,'200','131'], 'external pointer target')
    check(commands['gui-click']['argv'] == ['xdotool','click','1'], 'external XTest click')
    check(commands['gui-type']['argv'] == ['xdotool','type','--clearmodifiers','--delay','45' if independent else '35',nonce], 'external nonce typing')
    check(commands['gui-acknowledge']['argv'] == ['xdotool','key','Return'], 'external Return')
    check(commands['shutdown']['argv'] == [INSTALL+'/bin/darling','shutdown'], 'installed runtime shutdown')
    positions = {c['label']: i for i,c in enumerate(report['commands'])}
    check(positions['gui-focus'] < positions['gui-move'] < positions['gui-click'] < positions['gui-type'] < positions['gui-acknowledge'] < positions['shutdown'], 'input ordering')
    photos = {}
    for state, title, targets in [('before', 'WAIT', [(255,0,0),(0,0,255)]),
                                  ('after', 'READY', [(0,255,0),(255,255,0)])]:
        ref = report['screenshots'][state]
        width, height, rgb = decode_xwd(bound(root, ref), f'P003_{title}_{nonce}')
        check(decode_png(bound(root, ref['png'])) == (width, height, rgb), 'PNG pixels differ from original XWD')
        checked, worst = 0, 0
        for center, target in zip([width//4, 3*width//4], targets):
            for dx in [-4,-2,0,2,4]:
                for dy in [-4,-2,0,2,4]:
                    at = ((height//2+dy)*width+center+dx)*3
                    errors = [abs(rgb[at+i]-target[i]) for i in range(3)]
                    worst = max(worst, *errors)
                    check(max(errors) <= 40, 'displayed color state mismatch')
                    checked += 1
        photos[state] = {'width': width, 'height': height, 'title': f'P003_{title}_{nonce}',
                         'rgb_bytes_compared': len(rgb), 'rgb_sha256': sha(rgb),
                         'patch_pixels_checked': checked, 'maximum_channel_error': worst}
    check(photos['before']['rgb_sha256'] != photos['after']['rgb_sha256'], 'no displayed state change')
    lifecycle = report['lifecycle']
    server = lifecycle['server_before']
    check(type(server['pid']) is int and server['pid'] > 1 and server['starttime'] > 0
          and server['state'] not in ['Z','X'] and re.fullmatch(r'mnt:\[[0-9]+\]',server['mount_namespace']), 'live server identity')
    check(lifecycle['server_exited'] is True and lifecycle['mount_namespace_released'] is True
          and lifecycle['namespace_holders_after'] == [], 'server/namespace teardown incomplete')
    check(report['controlled_home'] == report['prefix'] + '.home', 'controlled fresh home')
    detail = {}
    if independent:
        stat = bound(root, lifecycle['server_stat']).decode('ascii')
        fields = stat[stat.rfind(')')+2:].split()
        check(int(stat.split('(',1)[0]) == server['pid'] and fields[0] == server['state']
              and int(fields[19]) == server['starttime'], 'raw /proc identity mismatch')
        isolation = report['isolation']
        check(isolation['source_and_build_absent'] is True
              and isolation['caller_mount_namespace'] != server['mount_namespace'], 'source-free namespace isolation')
        check(isolation['environment']['HOME'] == report['controlled_home']
              and isolation['environment']['DPREFIX'] == report['prefix']
              and isolation['environment']['STUB_VERBOSE'] == '1', 'isolated runtime environment')
        mounts = []
        for line in bound(root, isolation['mountinfo']).decode('utf-8').splitlines():
            parts = line.split(); sep = parts.index('-')
            check(sep >= 6 and len(parts) == sep+4, 'malformed raw mountinfo')
            unescape = lambda s: re.sub(r'\\([0-7]{3})',lambda m:chr(int(m[1],8)),s)
            source, target = unescape(parts[3]), unescape(parts[4])
            check(not any(v == x or v.startswith(x+'/') for v in [source,target]
                          for x in ['/p003/source','/p003/build']), 'source/build tree mounted')
            if 'MAC-OS-EMULATION' in source:
                check(target in ['/p003/review_package_archive.py','/p003/review_installed_runtime.py']
                      and source.endswith('/tools/compat/logic-pro/'+PurePosixPath(target).name), 'repository tree mounted')
            mounts.append({'root':source,'mount':target})
        check(len(mounts) >= 10, 'incomplete mountinfo')
        host = report['host_commands']
        check(len(host) == 4 and len({c['label'] for c in host}) == 4, 'independent host command count')
        for c in host:
            check(c['exit_code'] == 0 and c['timed_out'] is False, 'host helper failed')
            for stream in ['stdout','stderr']: bound(root,c[stream])
            if c['label'].startswith('gui-search-'):
                suffix = 'WAIT' if c['label'].endswith('wait') else 'READY'
                check(c['argv'] == ['xdotool','search','--sync','--onlyvisible','--name',f'^P003_{suffix}_{nonce}$'], 'nonce search')
                check(bound(root,c['stdout']).decode('ascii').splitlines() == [wid], 'search/focus window mismatch')
            else:
                check(c['argv'][:4] == ['xwd','-silent','-id',wid], 'external XWD target')
        detail = {'raw_stat_recomputed': True, 'mounts': mounts, 'host_commands_checked': len(host)}
    else:
        startup = read_json(root / report['startup_processes']['file'])
        bound(root,report['startup_processes'])
        check(len(startup['samples']) == report['startup_processes']['sample_count'] >= 1, 'startup observation count')
        observations = [p for sample in startup['samples'] for p in sample['processes']
                        if p['pid'] == server['pid'] and p['exe'] == INSTALL+'/bin/darlingserver']
        check(observations and all(report['prefix'] in p['cmdline'] for p in observations), 'startup server/prefix binding')
        detail = {'startup_samples':len(startup['samples']), 'raw_server_observations':len(observations)}
    all_streams = [value for record in streams.values() for value in record.values()]
    pattern = r'\bSTUB(?:\s|:)|\blibxpc stub called:|\bunimplemented in\b|only defined for abstract class\. Define'
    check(not any(re.search(pattern, value) for value in all_streams), 'reached stub/unsupported operation')
    check(report['stub_diagnostics'] == {'enabled':True,'environment':{'STUB_VERBOSE':'1'},'hits':[]}, 'diagnostic evidence')
    return {'source_commit':CANDIDATE,'cases':10,'nonce':nonce,'known_vector':'foobar' if independent else 'hello',
            'fnv_nonce':fnv(nonce),'transaction_deltas':[1,2,1,0], 'commands':15,
            'loaded_frameworks':loaded,'screenshots':photos,'prefix':report['prefix'],
            'home':report['controlled_home'],'lifecycle':lifecycle,'lifecycle_raw_binding':detail,
            'report_sha256':file_sha(root/'report.json')}


def macho(data):
    wrapper = None
    if data[:4] == b'\xca\xfe\xba\xbe':
        check(len(data) >= 28, 'short universal Mach-O header')
        count = int.from_bytes(data[4:8], 'big')
        check(count == 1, 'expected one actual x86_64 universal slice')
        cpu, subtype, offset, size, alignment = struct.unpack('>5I', data[8:28])
        check(cpu == 0x01000007 and 28 <= offset and alignment <= 30
              and offset % (1 << alignment) == 0 and offset+size == len(data),
              'universal Mach-O slice bounds/alignment')
        wrapper = {'architectures':count,'cpu_type':cpu,'cpu_subtype':subtype,
                   'offset':offset,'bytes':size,'alignment_power':alignment}
        data = data[offset:offset+size]
    check(len(data) >= 32, 'short Mach-O')
    magic, cpu, subtype, filetype, count, length, flags, reserved = struct.unpack('<8I',data[:32])
    check(magic == 0xfeedfacf and cpu == 0x01000007 and 32+length <= len(data), 'actual Mach-O format')
    at, install_id, deps = 32, [], []
    for _ in range(count):
        cmd, size = struct.unpack('<2I',data[at:at+8])
        check(size >= 8 and at+size <= 32+length, 'Mach-O load-command bounds')
        if cmd in [12,13,0x80000018,0x8000001f,0x80000023]:
            check(size >= 24, 'short dylib load command')
            offset = int.from_bytes(data[at+8:at+12],'little')
            check(24 <= offset < size, 'dylib string offset')
            value = data[at+offset:at+size].split(b'\0',1)[0].decode('utf-8')
            (install_id if cmd == 13 else deps).append(value)
        at += size
    check(at == 32+length, 'Mach-O load-command extent')
    return {'filetype':filetype,'install_ids':install_id,'dependencies':deps,
            'universal_wrapper':wrapper,'slice_sha256':sha(data)}


def installed_binding(root):
    result = {}
    for side in ['a','b']:
        build = root / ('build-'+side)
        first, second = [read_json(build/('install-'+stage+'.json')) for stage in ['first','second']]
        check(first['source_commit'] == second['source_commit'] == CANDIDATE, 'installed exact candidate')
        check(first['entries'] == second['entries'] and len(first['entries']) == 11947, 'fresh reinstall byte inventory')
        inventory = {item['path']:item for item in first['entries']}
        check(len(inventory) == len(first['entries']), 'duplicate installed inventory')
        uninstalled = read_json(build/'uninstall.json')
        check(uninstalled['status'] == 'PASSED' and uninstalled['errors'] == []
              and uninstalled['manifest_source_commit'] == CANDIDATE and uninstalled['prefix_absent'] is True
              and uninstalled['removed_entries'] == len(inventory), 'uninstall binding')
        owner = [read_json(build/f) for f in ['install-owner.json','install-owner-second.json']]
        check(owner[0]['nonce'] != owner[1]['nonce'] and all(o['prefix'] == INSTALL for o in owner), 'fresh install owner')
        wanted = {'libexec/darling'+p for p in FRAMEWORKS.values()}
        wanted |= {'libexec/darling/usr/libexec/p003/'+n for n in ['p003_macho','p003_foundation','p003_gui']}
        observed = {}
        with tarfile.open(build/'runtime-prefix.tar.gz','r:gz') as tar:
            for member in tar:
                name = member.name.removeprefix('./')
                if name not in wanted: continue
                check(member.isfile() and name not in observed, 'selected package member type/uniqueness')
                data = tar.extractfile(member).read()
                entry = inventory[name]
                check(len(data) == entry['size'] and sha(data) == entry['sha256'] and member.mode == entry['mode'], 'actual installed bytes/mode')
                observed[name] = {'sha256':sha(data),'bytes':len(data),'macho':macho(data)}
        check(set(observed) == wanted, 'selected actual Mach-O package coverage')
        for framework in first['frameworks']:
            actual = observed[framework['installed_path']]['macho']
            check(actual['install_ids'] == [FRAMEWORKS[framework['name']]] and actual['filetype'] == 6, 'actual framework install ID')
            recorded = framework['macho']['architectures'][0]
            check(actual['dependencies'] == [d['path'] for d in recorded['dependencies']], 'actual framework dependencies')
        for stage in ['first','second']:
            probes = read_json(build/('probes-'+stage)/'report.json')
            for name, ref in probes['binaries'].items():
                item = observed['libexec/darling/usr/libexec/p003/'+name]
                check(item['macho']['filetype'] == 2 and item['sha256'] == ref['sha256'] and item['bytes'] == ref['bytes'], 'actual executed probe binding')
        result[side] = {'entries':len(inventory),'reinstall_equal':True,'owner_nonces':[o['nonce'] for o in owner],
                        'uninstall':uninstalled,'selected_actual_macho':observed,
                        'archive_sha256':file_sha(build/'runtime-prefix.tar.gz')}
    package = read_json(root/'independent-runtime/package-review.json')
    check(package['source_commit'] == CANDIDATE and package['archive_sha256'] == result['a']['archive_sha256']
          and package['archive_bytes'] == (root/'build-a/runtime-prefix.tar.gz').stat().st_size
          and package['manifest_sha256'] == file_sha(root/'build-a/install-first.json')
          and package['entry_count'] == 11947 and package['errors'] == [] and package['installed_readback'] == 'PASS',
          'source-free package binding')
    runtime_report = read_json(root/'independent-runtime/runtime/report.json')
    for name,ref in runtime_report['binaries'].items():
        actual = result['a']['selected_actual_macho']['libexec/darling/usr/libexec/p003/'+name]
        check(actual['sha256'] == ref['sha256'] and actual['bytes'] == ref['bytes'], 'source-free executable bytes')
    result['independent_package'] = package
    check(len({n for side in ['a','b'] for n in result[side]['owner_nonces']}) == 4, 'paired owner nonce freshness')
    return result


def source_binding(repo, root):
    check(git(repo,'rev-parse',CANDIDATE+'^{tree}').decode().strip() == TREE, 'candidate tree')
    prior = Path('docs/compat/logic-pro/evidence/P002/requalification-20261105')
    order = read_json(repo/prior/'ordered-acceptance.json')
    check(order['status'] == 'PASSED' and order['implementation_commit'] == PREDECESSOR, 'predecessor acceptance')
    decisions = []
    for phase in ['P001','P002']:
        record = next(d for d in order['decisions'] if d['phase'] == phase)
        actual = repo/prior/record['record']
        check(file_sha(actual) == record['record_sha256'] and record['decision'] == 'ACCEPTED'
              and set(record['gates'].values()) == {'PASS'} and record['reviewer_authored_production_changes'] is False,
              'prerequisite original decision binding')
        decisions.append(record)
    check(decisions[0]['accepted_at_utc'] < decisions[1]['accepted_at_utc'], 'phase acceptance order')
    locks = {}
    for name in ['.gitmodules','AGENTS.md','ci/logic-pro/Dockerfile.p003','docs/compat/logic-pro/submodules.lock.json',
                 'docs/compat/logic-pro/toolchain.lock.json','tools/compat/logic-pro/classifications.json']:
        current = git(repo,'show',CANDIDATE+':'+name)
        check(current == git(repo,'show',PREDECESSOR+':'+name), 'changed accepted input: '+name)
        locks[name] = sha(current)
    def root_pins(revision):
        return {row.split(b'\t',1)[1].decode():row.split()[2].decode()
                for row in git(repo,'ls-tree','-r','-z',revision).split(b'\0') if row.startswith(b'160000 ')}
    pins = root_pins(CANDIDATE)
    check(len(pins) == 149 and pins == root_pins(PREDECESSOR), 'direct gitlink continuity')
    runtime_sources = ['tests/compat/logic-pro/build/foundation.m','tests/compat/logic-pro/build/gui.m',
                       'tests/compat/logic-pro/build/macho.c','tests/compat/logic-pro/build/images.h',
                       'tests/compat/logic-pro/build/CMakeLists.txt','ci/logic-pro/build-p003.sh',
                       '.github/workflows/phase3-build.yml','tools/compat/logic-pro/run_build_probes.py',
                       'tools/compat/logic-pro/review_installed_runtime.py','tools/compat/logic-pro/review_package_archive.py']
    sources = {name:sha(git(repo,'show',CANDIDATE+':'+name)) for name in runtime_sources}
    driver = root/'independent-runtime/runtime/reviewer-driver.py'
    check(file_sha(driver) == sources['tools/compat/logic-pro/review_installed_runtime.py'], 'retained independent driver source')
    package = read_json(root/'independent-runtime/package-review.json')
    check(package['driver_sha256'] == sources['tools/compat/logic-pro/review_package_archive.py'], 'retained package verifier source')
    root_citations = []
    for side in ['a','b']:
        build = root/('build-'+side)
        check((build/'source-status-before.txt').read_bytes() == (build/'source-status-after.txt').read_bytes() == b'', 'raw source cleanliness')
        summary = read_json(build/'build-summary.json')
        check(summary['source_commit'] == CANDIDATE and summary['source_lock_sha256'] == locks['docs/compat/logic-pro/submodules.lock.json']
              and summary['last_stage'] == 'complete' and summary['exit_code'] == 0, 'fresh complete build binding')
        original = read_json(build/'source-lock-verification.json')
        check(original['root_commit'] == CANDIDATE and original['verified_gitlinks'] == 160
              and original['verified_repositories'] == 161 and original['verified_lfs_payloads'] == 44
              and all(original[k] == 0 for k in ['conflicted','dirty_repositories','mismatched','uninitialized']), 'original source checkout closure')
        citations = read_json(build/'source-classifications.json')
        check(citations['current_commit'] == CANDIDATE and citations['checked_count'] == len(citations['checked']) == 63, 'original current classifications')
        for row in citations['checked']:
            current = row['current_source']
            if current['repository'] != '.': continue
            data = git(repo,'show',CANDIDATE+':'+current['path'])
            blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            excerpt = b''.join(data.splitlines(keepends=True)[current['line_start']-1:current['line_end']])
            check(blob == current['blob_sha1'] and sha(excerpt) == current['excerpt_sha256'], 'current root citation bytes: '+row['id'])
            if side == 'a': root_citations.append(row['id'])
    head = git(repo,'rev-parse','HEAD').decode().strip()
    later = git(repo,'diff','--name-only',CANDIDATE,head).decode().splitlines()
    allowed = lambda p: p == 'README.md' or p.startswith('docs/compat/logic-pro/evidence/')
    check(all(allowed(p) for p in later), 'post-test execution file changed')
    worktree = git(repo,'diff','--name-only','HEAD').decode().splitlines()
    check(all(allowed(p) for p in worktree), 'uncommitted execution file changed')
    return {'candidate':CANDIDATE,'tree':TREE,'predecessor_decisions':decisions,'protected_input_sha256':locks,
            'direct_gitlinks_unchanged':len(pins),'root_citations_recomputed':root_citations,
            'critical_source_sha256':sources,'documentation_head':head,'post_test_paths_only_documentation':True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--originals',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    metadata = read_json(args.originals/'metadata-final.json')
    jobs = metadata['jobs']['jobs']
    check(len(jobs) == 6 and all(j['run_id'] == RUN and j['head_sha'] == CANDIDATE and j['conclusion'] == 'success' for j in jobs), 'six successful exact-source jobs')
    result = {'schema':'darling.p003.wave5-independent-original-audit.v1', 'reviewer':'/root/wave5_acceptance',
              'non_author':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_commit':CANDIDATE,'tree':TREE,'run_id':RUN,'phase_acceptance':False,
              'review_mode':'offline original-evidence recomputation; no local guest execution',
              'helper_sha256':file_sha(Path(__file__)),
              'metadata_sha256':file_sha(args.originals/'metadata-final.json'),
              'jobs':[{k:j[k] for k in ['id','name','runner_id','head_sha','conclusion']} for j in jobs]}
    result['archives'] = archives(args.originals,metadata)
    result['campaigns'] = {}
    for side in ['a','b']:
        for stage in ['first','second']:
            result['campaigns'][f'{side}-{stage}'] = runtime(args.originals/f'build-{side}'/f'probes-{stage}')
    result['campaigns']['independent'] = runtime(args.originals/'independent-runtime/runtime',True)
    check(len({c['nonce'] for c in result['campaigns'].values()}) == 5, 'five independent runtime nonces')
    result['installed_binding'] = installed_binding(args.originals)
    result['source_binding'] = source_binding(args.repo,args.originals)
    result['cases_checked'] = sum(c['cases'] for c in result['campaigns'].values())
    result['raw_rgb_bytes_compared'] = sum(p['rgb_bytes_compared'] for c in result['campaigns'].values() for p in c['screenshots'].values())
    result['patch_pixels_checked'] = sum(p['patch_pixels_checked'] for c in result['campaigns'].values() for p in c['screenshots'].values())
    result['status'] = 'PASS_SCOPED_ORIGINAL_RUNTIME_AND_BINDING_RECOMPUTATION'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f: json.dump(result,f,indent=2,sort_keys=True); f.write('\n')
    print(json.dumps({k:result[k] for k in ['status','cases_checked','raw_rgb_bytes_compared','patch_pixels_checked','phase_acceptance']}))


if __name__ == '__main__':
    main()
