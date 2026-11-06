#!/usr/bin/env python3
"""Independent data-only seven-framework and native-provenance audit of final originals."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shlex
import struct
import subprocess
import tarfile

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[6]
BASE = Path('/workspace/scratch/430a9939323d/p003-work/run-42180484781')
SOURCE = '4622a9396c5c9fbe0014bdf6a2f695dcc491233c'
EXPECTED = {
    'AppKit': ('C', 'src/external/cocotron/AppKit', 'NSApplication.m'),
    'Foundation': ('C', 'src/external/foundation', 'src/NSString.m'),
    'CoreGraphics': ('A', 'src/external/cocotron/CoreGraphics', 'CGContext.m'),
    'CoreText': ('A', 'src/external/cocotron/CoreText', 'CTFont.m'),
    'ImageIO': ('A', 'src/frameworks/ImageIO', 'src/CGImageSource.m'),
    'QuartzCore': ('A', 'src/external/cocotron/QuartzCore', 'CALayer.m'),
    'AudioToolbox': ('A', 'src/CoreAudio/AudioToolbox', 'AudioConverter.cpp'),
}
NATIVE = ('bin/darling', 'bin/darling-coredump', 'bin/darlingserver', 'libexec/darling/usr/libexec/darling/mldr')

def check(value, message):
    if not value:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load(path):
    return json.loads(path.read_text())

def bound(data, start, length):
    check(0 <= start <= len(data) and 0 <= length <= len(data) - start, 'binary bounds')
    return data[start:start+length]

def cstring(data, start, end):
    return data[start:data.index(b'\0', start, end)].decode()

def macho(data):
    # Separate parser from both the production verifier and the installed-byte helper.
    slices = [(0, len(data))]
    if data[:4] == b'\xca\xfe\xba\xbe':
        n, = struct.unpack_from('>I', data, 4)
        check(0 < n < 16, 'fat slice count')
        slices = [struct.unpack_from('>II', data, 8+i*20+8) for i in range(n)]
    answer = []
    for base, size in slices:
        view = bound(data, base, size)
        check(view[:4] == b'\xcf\xfa\xed\xfe', 'expected little-endian Mach-O 64')
        cpu, subtype, filetype, count, commands = struct.unpack_from('<5I', view, 4)
        check(filetype == 6 and cpu == 0x01000007 and count < 1000, 'framework architecture/type')
        ids, deps, rpaths, uuids, cursor = [], [], [], [], 32
        for _ in range(count):
            command, length = struct.unpack('<II', bound(view, cursor, 8))
            check(length >= 8 and length % 4 == 0 and cursor+length <= 32+commands, 'Mach-O load command bounds')
            if command in (0xd, 0xc, 0x80000018, 0x8000001f, 0x20, 0x80000023):
                offset, = struct.unpack_from('<I', view, cursor+8)
                check(24 <= offset < length, 'dylib string bounds')
                text = cstring(view, cursor+offset, cursor+length)
                if command == 0xd:
                    ids.append(text)
                else:
                    deps.append({'path': text, 'weak': command == 0x80000018})
            elif command == 0x8000001c:
                offset, = struct.unpack_from('<I', view, cursor+8)
                check(12 <= offset < length, 'rpath bounds')
                rpaths.append(cstring(view, cursor+offset, cursor+length))
            elif command == 0x1b:
                check(length == 24, 'UUID command bounds')
                uuids.append(view[cursor+8:cursor+24].hex())
            cursor += length
        check(cursor == 32+commands and len(ids) == 1, 'install ID/count')
        answer.append({'bits':64, 'cpu_type':cpu, 'cpu_subtype':subtype, 'install_name':ids[0],
                       'dependencies':deps, 'rpaths':rpaths, 'uuids':uuids, 'slice_sha256':sha(view)})
    check(len(answer) == 1, 'exactly one x86_64 framework slice required')
    return answer

def resolve(entries, guest_path):
    check(guest_path.startswith('/'), 'nonabsolute guest dependency')
    remaining, resolved, hops = list(PurePosixPath(guest_path).parts[1:]), [], []
    while remaining:
        part = remaining.pop(0)
        if part == '..':
            check(resolved, 'guest root escape')
            resolved.pop()
            continue
        if part in ('', '.'):
            continue
        candidate = 'libexec/darling/' + '/'.join(resolved+[part])
        check(candidate in entries, 'guest path absent: '+candidate)
        row = entries[candidate]
        if row['kind'] == 'symlink':
            check(len(hops) < 64 and candidate not in hops, 'symlink loop')
            hops.append(candidate)
            target = row['target']
            if target.startswith('/'):
                resolved = []
            remaining = list(PurePosixPath(target).parts[1:] if target.startswith('/') else PurePosixPath(target).parts)+remaining
        else:
            check(not remaining or row['kind'] == 'directory', 'nondirectory path ancestor')
            resolved.append(part)
    final = 'libexec/darling/'+'/'.join(resolved)
    check(entries[final]['kind'] == 'file', 'dependency is not regular')
    return final, [{'path':p, 'target':entries[p]['target']} for p in hops]

def actual_elfname(data):
    slices = [(0,len(data))]
    if data[:4] == b'\xca\xfe\xba\xbe':
        count, = struct.unpack_from('>I',data,4)
        check(0 < count < 16,'wrapper fat slice bound')
        slices = [struct.unpack_from('>II',data,8+i*20+8) for i in range(count)]
    names=[]
    for base,size in slices:
        view=bound(data,base,size)
        check(view[:4] == b'\xcf\xfa\xed\xfe','wrapper Mach-O64')
        count,command_bytes=struct.unpack_from('<II',view,16)
        cursor=32
        for _ in range(count):
            command,length=struct.unpack_from('<II',view,cursor)
            check(length >= 8 and cursor+length <= 32+command_bytes,'wrapper command bound')
            if command == 0x19:
                section_count,=struct.unpack_from('<I',view,cursor+64)
                check(length == 72+80*section_count,'wrapper section table bound')
                for i in range(section_count):
                    at=cursor+72+80*i
                    name=view[at:at+16].rstrip(b'\0')
                    segment=view[at+16:at+32].rstrip(b'\0')
                    if name == b'__elfname' and segment == b'__TEXT':
                        length_string,offset=struct.unpack_from('<QI',view,at+40)
                        check(0 < length_string <= 100,'wrapper elf name length')
                        content=bound(view,offset,length_string)
                        check(content.endswith(b'\0') and b'\0' not in content[:-1],'wrapper elf name terminator')
                        names.append({'section':'__TEXT,__elfname','offset':base+offset,'size':length_string,'DT_SONAME':content[:-1].decode()})
            cursor+=length
        check(cursor == 32+command_bytes,'wrapper command consumption')
    check(len(names) == 1,'one actual wrapper elf name')
    return names[0]

def elf(data):
    check(data[:6] == b'\x7fELF\x02\x01', 'native ELF class/endian')
    typ, machine = struct.unpack_from('<HH', data, 16)
    check(machine == 62 and typ in (2,3), 'native ELF machine/type')
    phoff, = struct.unpack_from('<Q', data, 32)
    width, count = struct.unpack_from('<HH', data, 54)
    check(width == 56 and count < 1000, 'ELF program headers')
    ph = [struct.unpack('<IIQQQQQQ', bound(data, phoff+i*width, width)) for i in range(count)]
    interp = [bound(data,p[2],p[5]).rstrip(b'\0').decode() for p in ph if p[0] == 3]
    check(len(interp) <= 1, 'ELF interpreter count')
    dynamic = []
    for p in ph:
        if p[0] == 2:
            block = bound(data,p[2],p[5])
            for at in range(0,len(block),16):
                key,val = struct.unpack_from('<qQ',block,at)
                if key == 0:
                    break
                dynamic.append((key,val))
    strings = [v for k,v in dynamic if k == 5]
    def string(offset):
        check(len(strings) == 1, 'ELF string table')
        address = strings[0]+offset
        candidates = [p[2]+address-p[3] for p in ph if p[0] == 1 and p[3] <= address < p[3]+p[5]]
        check(len(candidates) == 1, 'ELF string address')
        return cstring(data,candidates[0],len(data))
    return {'type':'DYN' if typ == 3 else 'EXEC', 'interpreter':interp[0] if interp else None,
            'needed':[string(v) for k,v in dynamic if k == 1],
            'rpath':[s for k,v in dynamic if k == 15 for s in string(v).split(':')],
            'runpath':[s for k,v in dynamic if k == 29 for s in string(v).split(':')]}

def readelf_text(text):
    typ = re.search(r'^\s*Type:\s+(\S+)',text,re.M)
    interp = re.findall(r'\[Requesting program interpreter: ([^\]]+)\]',text)
    return {'type':typ.group(1), 'interpreter':interp[0] if interp else None,
            'needed':re.findall(r'\(NEEDED\).*?\[([^\]]+)\]',text),
            **{tag.lower():[part for value in re.findall(r'\('+tag+r'\).*?\[([^\]]*)\]',text) for part in value.split(':')] for tag in ('RPATH','RUNPATH')}}

def source_blob(module, pin, path):
    if module:
        gitdir = Path(subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=REPO,text=True).strip())/'modules'/module
        check(subprocess.check_output(['git','ls-tree',SOURCE,module],cwd=REPO,text=True).split()[:3] == ['160000','commit',pin], 'owner gitlink')
        return subprocess.check_output(['git','--git-dir='+str(gitdir),'show',pin+':'+path])
    return subprocess.check_output(['git','show',SOURCE+':'+path],cwd=REPO)

def main():
    wrappers, wrapper_sources, wrapper_specs = set(), [], {}
    for path in ('src/native/CMakeLists.txt','src/CoreAudio/CMakeLists.txt'):
        data = source_blob(None,SOURCE,path)
        wrapper_sources.append({'path':path,'sha256':sha(data)})
        wrappers.update(re.findall(r'^\s*wrap_elf\(\S+\s+(\S+?)(?:\s|\))',data.decode(),re.M))
        for name,soname,destination in re.findall(r'^\s*wrap_elf\((\S+)\s+([^\s)]+)(?:\s+"([^"]+)")?\)',data.decode(),re.M):
            check(soname not in wrapper_specs,'duplicate wrapper declaration')
            wrapper_specs[soname]={'target':name,'guest_path':'/'+(destination or 'usr/lib/native')+'/lib'+name+'.dylib'}
    check(len(wrappers) == 21, 'exact native wrapper declaration set')
    check(set(wrapper_specs) == wrappers,'all wrapper destinations parsed')
    wrapper_contract=[]
    for path in ('cmake/wrap_elf.cmake','src/libelfloader/wrapgen/wrapgen.cpp','src/libelfloader/wrapgen/print_wrapped_elf.cpp'):
        data=source_blob(None,SOURCE,path)
        wrapper_contract.append({'path':path,'source_commit':SOURCE,'sha256':sha(data)})
        if path.endswith('/wrapgen.cpp'):
            check(b'case DT_SONAME:' in data and b'.section __TEXT,__elfname' in data and b'dlopen_fatal(__elfname)' in data,'exact wrapper generator contract')
    hosts, native_reports, stable_native, live = {}, {}, [], {}
    for build in ('build-a','build-b'):
        directory = BASE/build
        manifest = load(directory/'install-first.json')
        check(manifest['source_commit'] == SOURCE and manifest['status'] == 'PASSED' and not manifest['errors'], 'framework manifest status')
        entries = {e['path']:e for e in manifest['entries']}
        frames = {f['name']:f for f in manifest['frameworks']}
        check(set(frames) == set(EXPECTED), 'seven framework set')
        wanted = {f['installed_path'] for f in frames.values()} | set(NATIVE) | {'libexec/darling'+s['guest_path'] for s in wrapper_specs.values()}
        images = {}
        with tarfile.open(directory/'runtime-prefix.tar.gz','r|gz') as t:
            for member in t:
                path = member.name.removeprefix('./')
                if path in wanted:
                    check(member.isfile(), 'required binary not regular')
                    images[path] = t.extractfile(member).read()
        check(set(images) == wanted, 'required archived images absent')
        bridges={}
        for soname,spec in wrapper_specs.items():
            path='libexec/darling'+spec['guest_path']; data=images[path]
            check(sha(data) == entries[path]['sha256'],'actual wrapper/manifest hash')
            parsed=macho(data)
            check(parsed[0]['install_name'] == spec['guest_path'],'actual wrapper install ID')
            bridges[soname]={**spec,'actual_wrapper_sha256':sha(data),**actual_elfname(data)}
        commands = load(directory/'compile_commands.json')
        install_lines = (directory/'cmake-install-manifest-first.txt').read_text().splitlines()
        pins = {m['path']:m['sha'] for m in manifest['submodules']}
        observations = []
        for name,(version,owner,sentinel) in EXPECTED.items():
            row = frames[name]
            target = 'Foundation_obj' if name == 'Foundation' else name
            check(row['source_owner'] == owner and row['cmake_source_target'] == target and row['cmake_target'] == ('Foundation_x86_64' if name == 'Foundation' else name), 'exact source/target owner')
            check(row['build_artifact'] == owner+'/'+name, 'exact build artifact owner')
            image = f'/System/Library/Frameworks/{name}.framework/Versions/{version}/{name}'
            installed = 'libexec/darling'+image
            check(row['installed_path'] == installed and sha(images[installed]) == row['sha256'] == entries[installed]['sha256'], 'framework actual bytes')
            collisions = [p for p,e in entries.items() if e['kind'] == 'file' and p.endswith('/'+name) and '.framework/' in p]
            check(collisions == [installed] and install_lines.count('/opt/darling-p003/'+installed) == 1, 'competing installed image/collision')
            alias = f'/System/Library/Frameworks/{name}.framework/{name}'
            current = f'/System/Library/Frameworks/{name}.framework/Versions/Current/{name}'
            resolutions = {path:resolve(entries,path) for path in (image,alias,current)}
            check(all(result[0] == installed for result in resolutions.values()), 'version/public/Current alias selection')
            actual = macho(images[installed])
            dep_results = []
            for arch in actual:
                check(arch['install_name'] == image, 'actual framework install ID')
                for dep in arch['dependencies']:
                    check(dep['path'].startswith('/'), 'unexpected relative direct dependency')
                    resolved, chain = resolve(entries,dep['path'])
                    dep['installed'] = True
                    dep_results.append({'path':dep['path'],'resolved':resolved,'sha256':entries[resolved]['sha256'],'aliases':chain})
            check(actual == row['macho']['architectures'], 'independent Mach-O parse differs from producer')
            matches = [c for c in commands if f'CMakeFiles/{target}.dir/' in c['command']]
            check(matches and any(c['file'] == '/p003/source/'+owner+'/'+sentinel for c in matches), 'actual owner sentinel compile absent')
            check(all('/dev-stubs/' not in c['file'] and c['directory'] == '/p003/build' for c in matches), 'dev stub or foreign build directory')
            objects = []
            for c in matches:
                argv=shlex.split(c['command']); obj=argv[argv.index('-o')+1]
                check(obj.startswith(owner+'/CMakeFiles/'+target+'.dir/'), 'compile target owner mismatch')
                objects.append(obj)
            module = 'src/external/cocotron' if owner.startswith('src/external/cocotron/') else owner if name == 'Foundation' else None
            pin = pins[module] if module else SOURCE
            cmake_path = owner[len(module)+1:]+'/CMakeLists.txt' if module and owner != module else 'CMakeLists.txt' if module else owner+'/CMakeLists.txt'
            blob = source_blob(module,pin,cmake_path)
            check(re.search(r'add_(?:separated_)?framework\(\s*'+name+r'\b',blob.decode()), 'pinned source target declaration')
            if name != 'AudioToolbox':
                check(re.search(r'set\(FRAMEWORK_VERSION\s+"'+version+r'"\)',blob.decode()), 'pinned source framework version')
            else:
                check(b'set(FRAMEWORK_AUDIOTOOLBOX_VERSION "A")' in source_blob(None,SOURCE,'src/CoreAudio/CMakeLists.txt'), 'AudioToolbox parent version')
            observations.append({'name':name,'version':version,'owner':owner,'source_commit':pin,'cmake_source_path':cmake_path,'cmake_source_sha256':sha(blob),
                                 'actual_binary_sha256':sha(images[installed]),'aliases':resolutions,'install_name':image,'dependencies':dep_results,
                                 'rpaths':actual[0]['rpaths'],'UUIDs':actual[0]['uuids'],'compile_command_count':len(matches),
                                 'compile_object_paths_sha256':sha(json.dumps(objects).encode()),'sentinel':owner+'/'+sentinel,
                                 'outside_owner_sources':sorted({c['file'] for c in matches if not c['file'].startswith('/p003/source/'+owner+'/')})})
        hosts[build] = observations
        for stage in ('first','second'):
            n = load(directory/f'native-{stage}.json')
            check(n['source_commit'] == SOURCE and n['status'] == 'PASSED' and n['errors'] == [] and n['installation_prefix'] == '/opt/darling-p003', 'native provenance source/status')
            check(n['wrapper_source_inputs'] == wrapper_sources and {w['soname'] for w in n['wrapped_libraries']} == wrappers and len(n['wrapped_libraries']) == 21, 'native wrapper exact source set')
            check(len(n['commands']) == 73 and {e['installed_path'] for e in n['entries']} == set(NATIVE), 'native command/entry coverage')
            logs = {}
            for i,c in enumerate(n['commands']):
                check(c['exit_code'] == 0 and c['timed_out'] is False, 'native command failed')
                logs[i] = {}
                for stream in ('stdout','stderr'):
                    file = directory/c[stream]['file']; data = file.read_bytes()
                    check(sha(data) == c[stream]['sha256'], 'native raw log hash')
                    logs[i][stream] = data.decode()
            check(n['commands'][0]['argv'] == ['git','-C','/p003/source','rev-parse','HEAD'] and logs[0]['stdout'].strip() == SOURCE, 'native recorded source command')
            check(n['commands'][1]['argv'] == ['ldconfig','-p'], 'native loader inventory command')
            for entry in n['entries']+n['wrapped_libraries']:
                ri,li=entry['command_indices']; path=entry['path']
                check(n['commands'][ri]['argv'] == ['readelf','-W','-h','-l','-d',path] and n['commands'][li]['argv'] == ['ldd',path], 'native exact command paths')
                check(readelf_text(logs[ri]['stdout']) == entry['elf'], 'native raw readelf metadata')
                raw_deps = {}
                for line in logs[li]['stdout'].splitlines():
                    check('not found' not in line, 'unresolved native dependency')
                    match = re.match(r'\s*(\S+) => (/\S+) \(',line)
                    direct = re.match(r'\s*(/\S+) \(',line)
                    if match: raw_deps[match.group(1)] = match.group(2)
                    elif direct: raw_deps[PurePosixPath(direct.group(1)).name] = direct.group(1)
                check(raw_deps == {d['name']:d['path'] for d in entry['dependencies']}, 'native raw ldd identities')
                check(set(entry['elf']['needed']) <= set(raw_deps), 'native needed dependency coverage')
                for identity in entry['dependencies'] + ([entry['interpreter']] if entry['interpreter'] else []):
                    check(identity['bytes'] > 0 and re.fullmatch('[a-f0-9]{64}',identity['sha256']) and identity['realpath'].startswith('/usr/lib/') and not any(x in identity['path'] for x in ('/p003/','dev-stubs')), 'native external dependency identity')
                if 'installed_path' in entry:
                    check(entry['sha256'] == sha(images[entry['installed_path']]) and elf(images[entry['installed_path']]) == entry['elf'], 'actual packaged ELF metadata/hash')
                else:
                    identity=entry['resolved_identity']; soname=entry['soname']
                    check(identity['sha256'] == entry['sha256'] and identity['realpath'] == path and identity['name'] == soname and identity['bytes'] > 0, 'wrapped native identity')
                    indices=[i for i,c in enumerate(n['commands']) if c['argv'][:2] == ['/usr/bin/python3','-c'] and c['argv'][-1] == soname]
                    check(len(indices) == 1, 'native dlopen coverage')
                    c=n['commands'][indices[0]]
                    check('ctypes.CDLL(sys.argv[1], mode=os.RTLD_NOW | os.RTLD_LOCAL)' in c['argv'][2] and 'dlinfo' in c['argv'][2], 'native resolver mechanism')
                    check(json.loads(logs[indices[0]]['stdout']) == {'soname':soname,'resolved':identity['path']}, 'native actual dlopen result')
                    declared_sonames=re.findall(r'\(SONAME\).*?\[([^\]]+)\]',logs[ri]['stdout'])
                    check(declared_sonames == [bridges[soname]['DT_SONAME']],'actual wrapper __elfname differs from resolved host DT_SONAME')
                    cache=[{'abi':abi,'path':path} for name,abi,path in re.findall(r'^\s*(\S+)\s+\(([^)]+)\)\s+=>\s+(\S+)\s*$',logs[1]['stdout'],re.M)
                           if name == declared_sonames[0] and 'x86-64' in abi]
                    check(cache and all(row['path'].startswith(('/lib/x86_64-linux-gnu/','/usr/lib/x86_64-linux-gnu/')) for row in cache),'versioned native name absent from original x86_64 loader cache')
                    bridges[soname]['versioned_loader_cache']=cache
                    bridges[soname]['host_identity']=identity
            stable = {'entries':n['entries'],'wrapped_libraries':n['wrapped_libraries'],'wrapper_source_inputs':n['wrapper_source_inputs']}
            stable_native.append(stable)
            native_reports[build+'/'+stage]={'native_report_sha256':sha((directory/f'native-{stage}.json').read_bytes()),'commands':73,'raw_log_hashes_verified':146,
                                           'packaged_ELF_count':4,'wrapped_host_libraries':21,'actual_wrapper_elfname_to_host_DT_SONAME':bridges,
                                           'stable_provenance_sha256':sha(json.dumps(stable,sort_keys=True).encode())}
        for stage in ('probes-first','probes-second'):
            report=load(directory/stage/'report.json'); check(report['source_revision'] == SOURCE and report['status'] == 'PASSED' and report['errors'] == [], 'producer live report source/status')
            commands=[c for c in report['commands'] if c['stdout']['file'] == 'gui.stdout.log']; check(len(commands) == 1, 'GUI command coverage')
            data=(directory/stage/'gui.stdout.log').read_bytes(); check(sha(data) == commands[0]['stdout']['sha256'], 'GUI live log hash')
            paths=re.findall(r'^P003_IMAGE (\S+)$',data.decode(),re.M)
            check(len(paths) == 7 and set(paths) == {x['install_name'] for x in observations}, 'seven actual live image paths')
            live[build+'/'+stage]={'raw_log_sha256':sha(data),'paths':paths}
    check(all(n == stable_native[0] for n in stable_native[1:]), 'native provenance differs across hosts/reinstalls')
    runtime=BASE/'independent-runtime/runtime'; replay=load(runtime/'report.json')
    check(replay['source_commit'] == SOURCE and replay['status'] == 'PASS' and not replay['errors'], 'independent replay source/status')
    log=(runtime/'gui.stdout.log').read_bytes(); paths=re.findall(r'^P003_IMAGE (\S+)$',log.decode(),re.M)
    gui=[c for c in replay['commands'] if c['stdout']['file'] == 'gui.stdout.log']; check(len(gui) == 1 and sha(log) == gui[0]['stdout']['sha256'], 'independent GUI log hash')
    check(paths == replay['loaded_framework_paths'] and set(paths) == {x['install_name'] for x in hosts['build-a']} and len(paths) == 7, 'independent live paths')
    live['independent-runtime']={'raw_log_sha256':sha(log),'paths':paths,'isolation':replay['isolation']}
    locks=[(BASE/n/'toolchain.lock.json').read_bytes() for n in ('build-a','build-b','independent-runtime')]
    check(locks[0] == locks[1] == locks[2], 'native host/replay toolchain locks differ')
    report={'reviewer':'/root/wave5_package','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':SOURCE,'run':42180484781,
            'status':'PASSED','phase_acceptance':False,'script_sha256':sha(Path(__file__).read_bytes()),'frameworks':hosts,'native_reports':native_reports,
            'identical_native_provenance_across_four_reports':True,'native_wrapper_sources':wrapper_sources,'declared_native_sonames':sorted(wrappers),
            'exact_wrapper_generation_contract':wrapper_contract,
            'native_stable_provenance':stable_native[0],'live_framework_paths':live,'toolchain_lock_sha256':sha(locks[0]),
            'limits':['All 70 direct framework dependency edges are resolved; this is not a separate transitive Mach-O graph audit.',
                      'Each framework retains a build-tree LC_RPATH string. All audited direct dependency names are absolute, all resolve in the package, and five live campaigns confirm canonical paths including source-free replay.',
                      'External host-library bytes are not in the installed tar. This audit authenticates all recorded native commands, raw results, identities, actual packaged ELF bytes and shared pinned toolchain provenance; it does not claim independent byte inspection of unarchived host libraries.']}
    (OUT/'final-framework-native.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASSED','frameworks_per_build':7,'direct_dependencies_per_build':sum(len(f['dependencies']) for f in hosts['build-a']),
                      'compile_counts':{f['name']:f['compile_command_count'] for f in hosts['build-a']},'native_reports':4,'native_commands':292,
                      'native_raw_logs':584,'native_wrappers_per_report':21,'live_campaigns':5,
                      'outside_owner_sources':{f['name']:f['outside_owner_sources'] for f in hosts['build-a'] if f['outside_owner_sources']}},indent=2))

if __name__ == '__main__':
    main()
