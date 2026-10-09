"""Read-only, stdlib ZIP dependency analysis; never extracts or imports a project.

Pins must be provisioned OUTSIDE the ZIP by the reviewer. Success covers only
the explicit dependency contract, and always grants zero execution authority.
"""
import argparse
import hashlib
import json
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath


def sha(data):
    return hashlib.sha256(data).hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('DUPLICATE_JSON_KEY:' + k)
            result[k] = v
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def safe_name(name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name or '\x00' in name
            or name.startswith('/') or name.endswith('/') or any(p in ('', '.', '..') for p in name.split('/'))
            or str(PurePosixPath(name)) != name):
        raise ValueError('UNSAFE_PATH:' + repr(name))
    return name


def hash_map(obj):
    if not isinstance(obj, dict) or not obj:
        raise ValueError('NONEMPTY_FILE_MAP_REQUIRED')
    lowered = set()
    for name, wanted in obj.items():
        safe_name(name)
        if not digest(wanted) or name.casefold() in lowered:
            raise ValueError('HASH_OR_CASE_ALIAS:' + name)
        lowered.add(name.casefold())
    return obj


def pinned_json(path, expected):
    data = Path(path).read_bytes()
    if not digest(expected) or sha(data) != expected:
        raise ValueError('EXTERNAL_PIN_MISMATCH:' + str(path))
    return strict_json(data)


def inspect_package(archive, original_inventory, contract, contract_sha256, *,
                    candidate_inventory=None, candidate_inventory_sha256=None):
    result = dict(status='INTEGRITY_REFUSED', errors=[], missing=[], execution_authorized=False,
                  project_imports=0, dynamic_tests=0, extracted_files=0,
                  scope='EXPLICIT_RUNTIME_DEPENDENCIES_ONLY; DYNAMIC_COMPLETENESS_NOT_PROVEN')
    try:
        spec = pinned_json(contract, contract_sha256)
        if spec['schema'] != 'BOUNDED_ADMIN_PACKAGE_DEPENDENCIES_V0':
            raise ValueError('DEPENDENCY_CONTRACT_SCHEMA')
        original = pinned_json(original_inventory, spec['original_inventory_sha256'])
        first_files = hash_map(original['files'])
        if original['zip_sha256'] != spec['original_zip_sha256'] or not digest(original['zip_sha256']):
            raise ValueError('ORIGINAL_ZIP_BINDING')
        required = dict(hash_map(spec['required_files']))
        manifests = hash_map(spec['runtime_manifests'])
        for name, wanted in manifests.items():
            if name in required and required[name] != wanted:
                raise ValueError('REQUIREMENT_CONFLICT:' + name)
            required[name] = wanted
        for name, wanted in required.items():
            if name in first_files and first_files[name] != wanted:
                raise ValueError('ORIGINAL_REQUIREMENT_CONFLICT:' + name)
        is_candidate = candidate_inventory is not None
        if is_candidate:
            expected = pinned_json(candidate_inventory, candidate_inventory_sha256)
            files = hash_map(expected['files'])
            if any(files.get(k) != v for k, v in first_files.items()):
                raise ValueError('ORIGINAL_MEMBER_REMOVED_OR_CHANGED')
            additions = set(files) - set(first_files)
            if additions != set(required) - set(first_files):
                raise ValueError('EXACT_DECLARED_MISSING_ADDITIONS_REQUIRED')
            if any(files[k] != required[k] for k in additions):
                raise ValueError('ADDITION_HASH_MISMATCH')
        else:
            if candidate_inventory_sha256 is not None:
                raise ValueError('AMBIGUOUS_INVENTORY_ARGUMENTS')
            expected, files = original, first_files
        if Path(archive).stat().st_size > 64 * 1024**2:
            raise ValueError('ZIP_SIZE_CAP')
        data = Path(archive).read_bytes()
        if len(data) > 64 * 1024**2 or not digest(expected['zip_sha256']) or sha(data) != expected['zip_sha256']:
            raise ValueError('ZIP_HASH_OR_SIZE')
        result.update(zip_sha256=sha(data), original_zip_sha256=original['zip_sha256'], candidate=is_candidate)
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            names = [safe_name(i.filename) for i in infos]
            if (len(names) != len(set(names)) or len(names) != len(set(n.casefold() for n in names))
                    or set(names) != set(files)):
                raise ValueError('ZIP_MEMBER_SET_OR_ALIAS')
            if sum(i.file_size for i in infos) > 128 * 1024**2:
                raise ValueError('UNCOMPRESSED_SIZE_CAP')
            for info in infos:
                mode = info.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if (info.flag_bits & 1 or info.is_dir() or kind not in (0, stat.S_IFREG)
                        or info.file_size > 64 * 1024**2):
                    raise ValueError('ZIP_SPECIAL_MEMBER:' + info.filename)
            raw_files = {}
            for name in names:
                body = z.read(name)  # zipfile verifies CRC; no extraction.
                if sha(body) != files[name]:
                    raise ValueError('MEMBER_HASH:' + name)
                raw_files[name] = body
            for name, wanted in required.items():
                if name not in raw_files:
                    result['missing'].append(name)
                elif sha(raw_files[name]) != wanted:
                    raise ValueError('REQUIRED_HASH:' + name)
            references = 0
            for name in manifests:
                if name not in raw_files:
                    continue
                bindings = hash_map(strict_json(raw_files[name])['files'])
                for relative, wanted in bindings.items():
                    references += 1
                    if relative in required and required[relative] != wanted:
                        raise ValueError('MANIFEST_REQUIREMENT_CONFLICT:' + relative)
                    if relative in files and files[relative] != wanted:
                        raise ValueError('MANIFEST_MEMBER_HASH_CONFLICT:' + relative)
                    if relative not in raw_files:
                        result['missing'].append(relative)
            result.update(entries=len(names), verified_member_hashes=len(names), manifest_references=references)
        result['missing'] = sorted(set(result['missing']))
        result['status'] = 'INCOMPLETE' if result['missing'] else 'COMPLETE_DECLARED_ONLY'
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, RuntimeError) as error:
        result['errors'].append(str(error))
        result['status'] = 'INTEGRITY_REFUSED'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', required=True, type=Path)
    p.add_argument('--original-inventory', required=True, type=Path)
    p.add_argument('--contract', required=True, type=Path)
    p.add_argument('--contract-sha256', required=True)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    result = inspect_package(args.archive, args.original_inventory, args.contract, args.contract_sha256)
    with args.out.open('xb') as f:
        f.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True).encode() + b'\n')
    return 0 if result['status'] == 'COMPLETE_DECLARED_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
