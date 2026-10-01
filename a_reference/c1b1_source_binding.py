"""Narrow source transport for the 2026-10-01 exception-classification audit.

Old mathematical foundations retain their hashes. A changed source is accepted
only if the entire AST is exactly the old AST plus the audited edits below.
This is not a general semantic-equivalence checker or an A-EV proof.
"""
import ast
import re
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'docs/history/c1b1_source_binding_pre_classification_v1'
BASELINES = {
    'a_reference/c1b1_two_atom.py': 'e5889e8af2901eaa594b9b593a2c47048c61a4b4811bb0af04fb6c5d25c32c0e',
    'a_reference/c1b1_axis_decision_bounds.py': '3ff1590322cd9dbb7c34b345a56cac35ad649a5c3881661fb3a1ec8bebd7c68c',
    'a_reference/c1b1_family_checker.py': 'bb6a39be7f58eb4fc317bd0f74c94f47534f1dd21528f995b12320dcac7ed9d0',
    'a_reference/c1b1_half_ulp_boundaries.py': 'c71886bb6de0c69aad829f3d3c817c567e1981308ac7f0d2a2d9718d0fd8f4ed',
    'a_reference/c1b1_fractional_phase_survey.py': 'b6eab332e14238a0f8ee91eb9ab14c2062c04ef42e38e93e964049ab843fb7e1',
    'a_reference/c1b1_modular_distance_survey.py': '3b31d8bbc270a52dbb4e51d09bed5960c9536c69dfd1342fa1662758dc57b50e',
    'a_reference/c1b1_residue_class_survey.py': '2b76285a45b37b58a2320b650643b551f617b73e47f35c114cd47f6fd52ddb7f',
    'a_reference/c1b1_quotient_gap_survey.py': 'f90bf0e1bc1ecec5197e62e9a66ffee6c4d67e1ec8118d6f0f56ad0f1a8d350d',
    'a_reference/c1b1_same_input_checker.py': '02586d548bce8fe25b2b8d1083ab0435d9cf490feab8e263fcde9c6f8f9340bf',
}
EXECUTOR_HASH = 'c09c080775768c27ae77deeabb7a55ddc136095138d06bddb7efaf8ac8b21591'
CURRENT_VARIANTS = {'a_reference/c1b1_two_atom.py': 'c09c080775768c27ae77deeabb7a55ddc136095138d06bddb7efaf8ac8b21591', 'a_reference/c1b1_axis_decision_bounds.py': '2dd5b104b4b361a7f849de0b0a1d73d385ac48fb41d812ec7e012586fdc2a5e5', 'a_reference/c1b1_family_checker.py': '4860a0281ec5dfa1685002acb9ef6a3be1fdc34755c5b4d62ac320b9ee743332', 'a_reference/c1b1_half_ulp_boundaries.py': '1c1029572abed4c4086160d5bd823ebf23c8bf5684425d385ffa14051b70c271', 'a_reference/c1b1_fractional_phase_survey.py': 'db610775d47907aad4a78de15510edf322a1a582d3fe9bc2f3bee1f600918c4e', 'a_reference/c1b1_modular_distance_survey.py': 'b81d7a1c5e6c0e975e55a3f3c0099c9166e0171840a3195b14561cf31639dc3d', 'a_reference/c1b1_residue_class_survey.py': '17a8910d42f67563e999dcc7c5edd490b60cd4011dcabd96d242cccc4053d8ce', 'a_reference/c1b1_quotient_gap_survey.py': '3dd08c0103caec70d80529311af8c3cfe166df4604b4ea21d5f317588ee15370', 'a_reference/c1b1_same_input_checker.py': '85bfb00f644a638e8632139d7c192cd7cda125b89863900cb46e2bc61bf2c0c2'}
# Only provenance SOURCE checks are transported. Artifact/inventory hash checks
# remain exact. These are the transitive readers of the original group proofs.
METADATA_EDITS = {
    'a_reference/c1b1_half_ulp_boundaries.py': (
        ("sha256((root/path).read_bytes().replace(b'\\r\\n', b'\\n')).hexdigest() != expected", 'not SA.source_matches(root/path, expected)', 1),),
    'a_reference/c1b1_fractional_phase_survey.py': (
        ("sha256((ROOT/path).read_bytes().replace(b'\\r\\n', b'\\n')).hexdigest() != expected", 'not SA.source_matches(ROOT/path, expected)', 1),),
    'a_reference/c1b1_modular_distance_survey.py': (
        ("sha256((ROOT/source).read_bytes().replace(b'\\r\\n', b'\\n')).hexdigest() != digest", 'not SA.source_matches(ROOT/source, digest)', 1),),
    'a_reference/c1b1_residue_class_survey.py': (
        ("sha256((ROOT/name).read_bytes().replace(b'\\r\\n', b'\\n')).hexdigest() != digest", 'not SA.source_matches(ROOT/name, digest)', 1),
        ("sha256((ROOT/source).read_bytes().replace(b'\\r\\n', b'\\n')).hexdigest() != expected", 'not SA.source_matches(ROOT/source, expected)', 1)),
    'a_reference/c1b1_quotient_gap_survey.py': (
        ("_require(sha256(actual).hexdigest() == digest, 'prior source changed')", "_require(SA.source_matches(ROOT/name, digest), 'prior source changed')", 1),),
    'a_reference/c1b1_same_input_checker.py': (
        ("require(_hash(path) == digest, 'same-input prior source changed')", "require(SA.source_matches(ROOT/path, digest), 'same-input prior source changed')", 2),),
}


def lf(data):
    return data.replace(b'\r\n', b'\n')


def digest(data):
    return sha256(lf(data)).hexdigest()


def variant_hash(name, data):
    data = lf(data)
    if name == 'a_reference/c1b1_axis_decision_bounds.py':
        # Break the guard/auditor hash cycle only at this literal. The exact
        # literal value is independently checked by the AST transport and by
        # proof_guard itself. All other bytes, including comments, are pinned.
        data = re.sub(rb"SOURCE_BINDING_AUDITOR_SHA256 = '[a-f0-9]{64}'",
                      b"SOURCE_BINDING_AUDITOR_SHA256 = '<AUDITOR_HASH>'", data)
    return digest(data)


def _nodes(text):
    return ast.parse(text).body


def _function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _dump(tree):
    # Docstrings do not affect the audited numerical behavior. All executable
    # statements, imports, constants, defaults and decorators remain compared.
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                n.body = n.body[1:]
    return ast.dump(tree, include_attributes=False)


def _executor_edits(tree):
    index = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.ClassDef) and n.name == 'ReferenceUndecided')
    tree.body[index+1:index+1] = _nodes('''
class ContractViolation(ValueError):
    reason = "contract_violation"
''')
    decide = _function(tree, '_decide')
    loop = next(n for n in decide.body if isinstance(n, ast.While))
    loop.body[1:1] = _nodes('''
if lo > hi:
    raise ContractViolation("reversed evaluator enclosure")
''')
    for block in (n for n in loop.body if isinstance(n, ast.Try)):
        block.handlers[0].body[0:0] = _nodes('''
if h.reason != "overflow":
    raise
''')
    limit = _function(tree, '_limit')
    block = next(n for n in limit.body if isinstance(n, ast.Try))
    block.handlers[0].body[0:0] = _nodes('''
if h.reason != "overflow":
    raise
''')
    step = _function(tree, 'step')
    index = next(i for i, n in enumerate(step.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'J' for t in n.targets))
    step.body[index:index] = _nodes('''
values = [(pos, a.r) for a in atoms] + [(mom, a.p) for a in atoms]
if run.J_cache is not None:
    values.append((mom, run.J_cache))
for profile, raws in values:
    valid = getattr(profile, "valid_raw", None)
    if valid is not None and not all(valid(v) for v in raws):
        raise ContractViolation("invalid stored raw for profile")
''')


def _guard_edits(tree, auditor_hash):
    index = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.ImportFrom) and any(a.name == 'c1b1_outer_bootstrap' for a in n.names))
    tree.body[index+1:index+1] = _nodes('from a_reference import c1b1_source_binding as S')
    index = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name == 'proof_guard')
    tree.body[index:index] = _nodes(f"SOURCE_BINDING_AUDITOR_SHA256 = {auditor_hash!r}\n_AUDIT_STATE_FUNCTION = S.binding_state\n_AUDIT_BINDING = S.binding_state()")
    guard = _function(tree, 'proof_guard')
    guard.body[1:1] = _nodes('''
if S.binding_state is not _AUDIT_STATE_FUNCTION or S.binding_state() != _AUDIT_BINDING or sha256(Path(S.__file__).read_bytes().replace(b'\\r\\n', b'\\n')).hexdigest() != SOURCE_BINDING_AUDITOR_SHA256:
    raise O.NotCertified('source-binding auditor changed')
''')
    loop = next(n for n in guard.body if isinstance(n, ast.For))
    loop.body[0].test = ast.parse('not S.source_matches(Path(module.__file__), expected)', mode='eval').body


def _family_edits(tree):
    index = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.ImportFrom) and any(a.name == 'c1b1_rounding_regions' for a in n.names))
    tree.body[index+1:index+1] = _nodes('from a_reference import c1b1_source_binding as S')
    guard = _function(tree, 'foundation_guard')
    loop = next(n for n in guard.body if isinstance(n, ast.For))
    loop.body[0].value.args[0] = ast.parse('S.source_matches(ROOT/path, expected)', mode='eval').body


def provenance_source(old, name):
    """Apply exactly the listed source-check replacements; never artifact checks."""
    text = old.decode('utf-8')
    for before, after, count in METADATA_EDITS[name]:
        if text.count(before) != count:
            raise ValueError('unrecognized historical provenance check')
        text = text.replace(before, after)
    tree = ast.parse(text)
    index = max(i for i, n in enumerate(tree.body) if isinstance(n, ast.ImportFrom) and n.module == 'a_reference')
    tree.body[index+1:index+1] = _nodes('from a_reference import c1b1_source_binding as SA')
    return tree


@lru_cache(maxsize=16)
def equivalent_source(name, old, new, auditor_hash):
    """Check exact audited syntax transport; reject every other executable edit."""
    if name not in BASELINES or digest(old) != BASELINES[name]:
        return False
    if variant_hash(name, new) != CURRENT_VARIANTS.get(name):
        return False
    if name == 'a_reference/c1b1_two_atom.py' and digest(new) != EXECUTOR_HASH:
        return False
    before, after = ast.parse(old), ast.parse(new)
    if name.endswith('c1b1_two_atom.py'):
        _executor_edits(before)
    elif name.endswith('c1b1_axis_decision_bounds.py'):
        _guard_edits(before, auditor_hash)
    elif name.endswith('c1b1_family_checker.py'):
        _family_edits(before)
    else:
        before = provenance_source(old, name)
    return _dump(before) == _dump(after)


def source_matches(path, expected):
    """Exact original hash OR the explicitly audited transport of that original.

    Read bytes on every call. The cache key contains the bytes, so editing a
    source or its historical original cannot reuse an earlier acceptance.
    """
    path = Path(path)
    if not path.is_absolute():
        path = ROOT/path
    current = lf(path.read_bytes())
    if digest(current) == expected:
        return True
    try:
        name = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    if BASELINES.get(name) != expected:
        return False
    original = lf((HISTORY/name).read_bytes())
    return equivalent_source(name, original, current, digest(Path(__file__).read_bytes()))


def binding_state():
    """Runtime identities/constants pinned by the endpoint proof guard."""
    return (source_matches, equivalent_source, _executor_edits, _guard_edits,
            _family_edits, provenance_source, _dump, _nodes, _function, digest, lf, variant_hash,
            tuple(sorted(BASELINES.items())), tuple(sorted(METADATA_EDITS.items())),
            tuple(sorted(CURRENT_VARIANTS.items())), EXECUTOR_HASH, ROOT, HISTORY)
