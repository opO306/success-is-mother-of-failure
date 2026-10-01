"""Portable deployment, with original bytes and location-only changes bound separately."""
import ast
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile

REFERENCE = 'reference/ar2_lang2024/S2_ar2_pot.f90'
PARENT = 'docs/active/C1B1_DT40_INTEGRATOR_BENCHMARK_SEAL_V1.json'
EXECUTION = 'docs/active/C1B1_DT40_DEPLOYMENT_SEAL_V2.json'
MANIFEST = 'manifest.json'
TRANSFORMS = {'c1b1_o1/model.py': 'SOURCE', 'tools/c1b1_o1_study.py': 'SOURCE',
              'c1b1_integrator_benchmark/study.py': 'SEAL'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def portable_name(name):
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '\\' in name or ':' in name or '..' in p.parts or str(p) != name:
        raise ValueError('nonportable package name: ' + name)
    return name


def check_transform(old, new, location):
    def without_location(text):
        tree = ast.parse(text)
        nodes = [n for n in tree.body if isinstance(n, ast.Assign) and
                 any(isinstance(t, ast.Name) and t.id == location for t in n.targets)]
        if len(nodes) != 1:
            raise ValueError('location assignment missing or ambiguous')
        tree.body.remove(nodes[0])
        return ast.dump(tree, include_attributes=False)
    if without_location(old) != without_location(new):
        raise ValueError('nonlocation AST mutation')


def relocate(name, text):
    location = TRANSFORMS[name]
    if location == 'SOURCE':
        line = "SOURCE = Path(__file__).resolve().parents[1].parent / 'reference/ar2_lang2024/S2_ar2_pot.f90'"
    else:
        line = "SEAL=ROOT/'docs/active/C1B1_DT40_DEPLOYMENT_SEAL_V2.json'"
    new, count = re.subn(r'^' + location + r'\s*=.*$', line, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError('location assignment missing or ambiguous')
    check_transform(text, new, location)
    return new


def build(root, original_bundle, destination):
    root = Path(root)
    contents, originals, transformed = {}, {}, {}
    with tarfile.open(original_bundle) as archive:
        old_manifest = json.loads(archive.extractfile('bundle_manifest.json').read())
        if len(old_manifest) != 272:
            raise ValueError('unexpected original inventory')
        parent = json.loads(archive.extractfile(PARENT).read())
        payload = parent['payload']
        if sha(encoded(payload)) != parent['payload_sha256']:
            raise ValueError('original seal hash')
        for group in ('sources', 'protected_sources'):
            for name, expected in payload[group].items():
                if sha((root/name).read_bytes()) != expected:
                    raise ValueError('local original source changed: ' + name)
        for name, row in old_manifest.items():
            archived = name[3:] if name.startswith('D:/') else name
            member = archive.getmember(archived)
            if not member.isfile():
                raise ValueError('original entry is not a regular file')
            data = archive.extractfile(member).read()
            if sha(data) != row['sha256']:
                raise ValueError('original archive hash: ' + name)
            runtime = name in payload['sources'] or name in {
                'tests/test_c1b1_o1.py', 'tests/test_c1b1_o1_diagnostic.py', 'tools/c1b1_o1_study.py'}
            target = REFERENCE if name.startswith('D:/') else (
                'evidence/protected/' + name if name in payload['protected_sources'] and not runtime else 'code/' + name)
            portable_name(target)
            contents[target] = data
            original_target = target
            if name in TRANSFORMS:
                original_target = 'evidence/original_code/' + name
                contents[original_target] = data
                contents[target] = relocate(name, data.decode('utf-8')).encode('utf-8')
                transformed[name] = {'original': original_target, 'runtime': target,
                                     'original_sha256': sha(data), 'runtime_sha256': sha(contents[target]),
                                     'location': TRANSFORMS[name]}
            originals[name] = {'package_path': original_target, 'sha256': row['sha256']}
    execution_payload = copy.deepcopy(payload)
    for name in execution_payload['sources']:
        execution_payload['sources'][name] = sha(contents['code/' + name])
    execution_seal = {'payload': execution_payload, 'payload_sha256': sha(encoded(execution_payload)),
                      'parent_seal_sha256': sha(contents['code/' + PARENT]),
                      'parent_payload_sha256': parent['payload_sha256'],
                      'change_scope': 'resource and seal locations only; no numerical AST changes'}
    contents['code/' + EXECUTION] = encoded(execution_seal)
    # This checker is also used remotely, byte-for-byte, before any numerical imports.
    contents['package_check.py'] = (root/'tools/c1b1_dt40_package.py').read_bytes()
    # Historical provenance tests inspect the preserved original files. The
    # benchmark runs in a separate process against the independently bound
    # runtime snapshot; this fixture never changes its numerical implementation.
    contents['code/tests/conftest.py'] = HISTORICAL_VIEW.encode('utf-8')
    manifest = {'schema': 'c1b1-dt40-portable-package-v1', 'originals': originals,
                'transforms': transformed, 'parent': 'code/' + PARENT, 'execution': 'code/' + EXECUTION,
                'reference': REFERENCE, 'objects': {n: {'sha256': sha(b), 'bytes': len(b)} for n, b in contents.items()}}
    contents[MANIFEST] = encoded(manifest)
    with Path(destination).open('xb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode='w') as archive:
            for name in sorted(contents):
                portable_name(name)
                info = tarfile.TarInfo(name);info.size = len(contents[name]);info.mode = 0o644
                archive.addfile(info, io.BytesIO(contents[name]))
    return {'originals': len(originals), 'objects': len(manifest['objects']),
            'bundle_sha256': sha(Path(destination).read_bytes())}


def extract(bundle, destination):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('extract destination must be new')
    with tarfile.open(bundle) as archive:
        names = set()
        for member in archive.getmembers():
            portable_name(member.name)
            if not member.isfile() or member.name.casefold() in names:
                raise ValueError('nonregular or duplicate archive entry')
            names.add(member.name.casefold())
        destination.mkdir(parents=True)
        archive.extractall(destination, filter='data')


def verify(root):
    root = Path(root)
    manifest = json.loads((root/MANIFEST).read_bytes())
    for name, row in manifest['objects'].items():
        portable_name(name)
        data = (root/name).read_bytes()
        if sha(data) != row['sha256'] or len(data) != row['bytes']:
            raise ValueError('package hash: ' + name)
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != set(manifest['objects']) | {MANIFEST}:
        raise ValueError('package inventory mismatch')
    for row in manifest['originals'].values():
        portable_name(row['package_path'])
        if sha((root/row['package_path']).read_bytes()) != row['sha256']:
            raise ValueError('original byte hash')
    parent = json.loads((root/manifest['parent']).read_bytes())
    execution = json.loads((root/manifest['execution']).read_bytes())
    if sha(encoded(parent['payload'])) != parent['payload_sha256'] or sha(encoded(execution['payload'])) != execution['payload_sha256']:
        raise ValueError('seal payload hash')
    if execution['parent_seal_sha256'] != sha((root/manifest['parent']).read_bytes()) or execution['parent_payload_sha256'] != parent['payload_sha256']:
        raise ValueError('parent binding hash')
    original_payload = copy.deepcopy(parent['payload'])
    runtime_payload = copy.deepcopy(execution['payload'])
    runtime_sources = runtime_payload.pop('sources');original_payload.pop('sources')
    if original_payload != runtime_payload:
        raise ValueError('numerical protocol or input changed')
    for name, want in runtime_sources.items():
        if sha((root/'code'/name).read_bytes()) != want:
            raise ValueError('runtime source hash')
    for name, row in manifest['transforms'].items():
        old = (root/row['original']).read_text(encoding='utf-8')
        new = (root/row['runtime']).read_text(encoding='utf-8')
        check_transform(old, new, row['location'])
        if relocate(name, old) != new:
            raise ValueError('unexpected location transform')
    for path in (root/'code').rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        compile(text, str(path), 'exec')
        if re.search(r'[A-Za-z]:[/\\]', text):
            raise ValueError('Windows drive requirement in active code: ' + str(path))
    reference_hash = sha((root/manifest['reference']).read_bytes())
    if reference_hash != parent['payload']['public_source_sha256']:
        raise ValueError('public reference hash')
    return {'originals_verified': len(manifest['originals']), 'objects_verified': len(manifest['objects']),
            'reference_sha256': reference_hash, 'location_only_transforms': sorted(manifest['transforms']),
            'parent_payload_sha256': parent['payload_sha256'], 'execution_payload_sha256': execution['payload_sha256']}


HISTORICAL_VIEW = '''"""Read historical bytes for historical provenance tests; no benchmark patching."""
import json
import os
from pathlib import Path
import shutil
import pytest

@pytest.fixture(scope='session',autouse=True)
def historical_files(tmp_path_factory):
    package=Path(__file__).resolve().parents[2]
    manifest=json.loads((package/'manifest.json').read_bytes())
    original=tmp_path_factory.mktemp('original_files')
    for name,row in manifest['originals'].items():
        if row['package_path']==manifest['reference']:
            continue
        target=original/name
        target.parent.mkdir(parents=True,exist_ok=True)
        try:
            os.link(package/row['package_path'],target)
        except OSError:
            shutil.copyfile(package/row['package_path'],target)
    import c1b1_o1_diagnostic.study as diagnostic
    import tools.c1b1_o1_study as driver
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(diagnostic,'ROOT',original)
        patch.setattr(driver,'ROOT',original)
        patch.setattr(driver,'INPUT',original/'docs/active/C1B1_O1_INPUTS_V1.json')
        yield
'''
