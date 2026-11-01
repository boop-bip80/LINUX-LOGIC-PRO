#!/usr/bin/env python3
"""Independently inspect prepared current CI archive; never extract or upload."""
import argparse, datetime, hashlib, io, json, lzma, re, tarfile, zipfile
from pathlib import Path

EXPECTED = {
    13063666566: ('p001-b628085-ubuntu-22.04.zip', 22167948, 'af9a315592bf6f203e125f06d20729e15500944ec289954231800c260364c1d8', 16),
    13062918782: ('p001-b628085-ubuntu-24.04.zip', 22167665, '5f2cc6c620d250147b5e537f4fbaeb1c61618fa2475f9f99a75efc2995d96694', 16),
    13063572615: ('p002-b628085-host-a.zip', 52899, '2615667b47864b103147b705ce192f1d0551c884579f75947c5cc48e21e9a219', 18),
    13062978587: ('p002-b628085-host-b.zip', 53339, 'a1b200168b0a6003c29967d0b73331d3b27cfc5c562c37aa16b5898c67057d8a', 18),
}
PATTERNS = {
    'private_key_pem': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    'github_classic_token': rb'gh[pousr]_[A-Za-z0-9]{25,}',
    'github_fine_grained_pat': rb'github_pat_[A-Za-z0-9_]{20,}',
    'aws_access_key': rb'(?:AKIA|ASIA)[0-9A-Z]{16}',
    'google_api_key': rb'AIza[0-9A-Za-z_-]{35}',
    'slack_token': rb'xox[baprs]-[A-Za-z0-9-]{20,}',
    'stripe_secret_key': rb'sk_live_[A-Za-z0-9]{20,}',
    'openai_secret_key': rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',
    'authorization_header': rb'(?i)Authorization\s*:\s*(?:bearer|token|basic)\s+[A-Za-z0-9+/=._-]{12,}',
    'credential_in_url': rb'https?://[^\s/\"]+:[^\s/@\"]+@',
}

def digest(data): return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True,type=Path);p.add_argument('--manifest',required=True,type=Path);p.add_argument('--artifacts',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());compressed=a.archive.read_bytes()
    assert len(compressed)==manifest['archive']['bytes'];assert digest(compressed)==manifest['archive']['sha256']
    dec=lzma.LZMADecompressor(format=lzma.FORMAT_XZ);raw=dec.decompress(compressed)
    assert dec.eof and not dec.unused_data and dec.check==lzma.CHECK_CRC64
    mapped={};named_patterns={name:0 for name in PATTERNS};object_json_count=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tf:
        infos=tf.getmembers();assert len(infos)==manifest['unique_objects']
        assert [i.name for i in infos]==sorted(i.name for i in infos)
        cursor=0
        for info in infos:
            assert re.fullmatch('objects/[0-9a-f]{64}',info.name) and info.isfile() and not info.pax_headers
            assert info.offset==cursor and info.offset_data==cursor+512
            assert info.mode==0o644 and info.uid==info.gid==info.mtime==0 and info.uname==info.gname=='' and info.linkname==''
            expected_header=tarfile.TarInfo(info.name);expected_header.size=info.size;expected_header.mode=0o644
            assert raw[cursor:cursor+512]==expected_header.tobuf(format=tarfile.USTAR_FORMAT)
            data=raw[info.offset_data:info.offset_data+info.size];assert digest(data)==info.name.split('/')[1]
            data.decode('utf-8','strict');assert info.name not in mapped;mapped[info.name]=data
            end=info.offset_data+info.size;cursor=end+(-info.size)%512
            assert not any(raw[end:cursor])
            for name,pattern in PATTERNS.items():named_patterns[name]+=len(re.findall(pattern,data))
        trailer=raw[cursor:];assert len(trailer)>=1024 and len(raw)%10240==0 and not any(trailer)
    source_ids={s['artifact_id'] for s in manifest['sources']};assert source_ids==set(EXPECTED)
    occurrences=[];used=set();json_objects=set()
    for source in manifest['sources']:
        filename,size,sha,count=EXPECTED[source['artifact_id']]
        original=(a.artifacts/filename).read_bytes();assert len(original)==size and digest(original)==sha
        assert (source['zip_file'],source['zip_bytes'],source['zip_sha256'])==(filename,size,sha)
        with zipfile.ZipFile(io.BytesIO(original)) as z:
            members=z.infolist();assert len(members)==count==len({i.filename for i in members})
            mapping={m['path']:m for m in source['members']};assert len(mapping)==count and set(mapping)==set(z.namelist())
            for name,record in mapping.items():
                b=z.read(name);assert b==mapped[record['object']]
                assert len(b)==record['bytes'] and digest(b)==record['sha256']
                if name.endswith('.json') and record['object'] not in json_objects:
                    json.loads(b);json_objects.add(record['object'])
                used.add(record['object']);occurrences.append({'artifact_id':source['artifact_id'],'host':source['host'],'path':name,'bytes':len(b),'sha256':digest(b)})
    assert used==set(mapped) and len(occurrences)==68==manifest['member_count']
    assert sum(o['bytes'] for o in occurrences)==manifest['member_bytes']
    assert sum(len(x) for x in mapped.values())==manifest['unique_bytes']
    assert not any(named_patterns.values()),named_patterns
    out={'schema_version':1,'reviewer':'/root/final_acceptance_audit','reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verdict':'PASS_PREPARED_CURRENT_BUNDLE_INTEGRITY_REVIEW; NO_PUBLICATION_AUTHORIZATION',
        'tested_implementation_commit':manifest['tested_implementation_commit'],'archive':{'bytes':len(compressed),'sha256':digest(compressed)},'manifest_sha256':digest(a.manifest.read_bytes()),
        'decompressed_bytes':len(raw),'objects':len(mapped),'json_objects_parsed':len(json_objects),'original_members_verified':len(occurrences),'exact_original_member_bytes':sum(o['bytes'] for o in occurrences),
        'all_unique_objects_used_by_original_member_mapping':True,'canonical_headers_content_padding_and_trailer_account_for_every_byte':True,'single_complete_crc64_xz_stream_without_trailing_data':True,'named_credential_patterns':named_patterns,
        'sources':[{ 'artifact_id':aid,'zip_bytes':vals[1],'zip_sha256':vals[2]} for aid,vals in EXPECTED.items()],
        'limits':['Named credential-pattern checks are bounded, not a universal absence-of-secrets claim.','The separately held historical archive was not read, reconstructed, encoded, or published.','This script reads local ZIP/archive files only and never uploads data.','Correct prepared bytes do not establish durable publication or override either approval boundary.']}
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2))

if __name__=='__main__':main()
