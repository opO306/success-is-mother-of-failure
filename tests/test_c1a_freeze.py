"""C1-A freeze (designer 10th ed.): the Ar-Ar physical and numerical meaning contract.

docs/current/C1A_AR2_FREEZE_V1.md. Frozen: the Lang 2024 model with its exact published decimals, V_BO + V_rel +
V_QED, retardation ON in the A world, r_min = 1.2 A (below: physics_domain_exceeded), the source-versioned CODATA
2018 a0, bohr / hartree / hartree per bohr, V and F each rounded once, refusal instead of guessing, and the
fixture's result bits. NOT frozen: executor limits, precision caps, threads, limbs, CUDA layout, timings.
A failure here means the frozen contract changed -- that needs a new contract version and a designer verdict.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from fractions import Fraction as Q

import pytest

import a_reference.ar2_lang2024 as L
import a_reference.ar2_lang2024_fixture as X

FROZEN_CONTRACT = "c1a-ar2-lang2024-v1"
FROZEN_PARAMETER_FINGERPRINT = "ada6153be05af3e582139fdc81b5697fffaf18d12f9f2de6e8d5ac2fdfe0839e"
FROZEN_FIXTURE_SHA256 = "9038bb1551110e6c6a3fc99e085c433a15eb1220eab0b2d005a7ed7aa85fe76b"   # LF-normalised
FROZEN_LANG_SHA256 = {
    "S2_ar2_pot.f90": "a598057183121b9c928b3a9804c8e2e99afa553bad570a471aa4130f20e6b049",
    "S1_abinitio.txt": "b29c002ad7004214d2e7e93c5e4217ba603e5804cca4a4f5fab78a3450a02371",
    "lang2024_v2.pdf": "893c6db03e5f92a6b983a97a7719604a24e4abd376f7b5e58312b25e1d1d85bf",
}


def test_frozen_physics_contract() -> None:
    assert L.CONTRACT_VERSION == FROZEN_CONTRACT
    assert L.parameter_fingerprint() == FROZEN_PARAMETER_FINGERPRINT
    assert set(L.COMPONENTS) == {"BO", "REL", "QED"}                       # V_real = V_BO + V_rel + V_QED
    assert L.WORLD_RETARDATION is True                                     # A world: retardation ON
    assert L.R_MIN_ANGSTROM == Q("1.2") and L.BOHR_ANGSTROM == Q("0.529177210903")
    assert "source-versioned" in L.BOHR_ANGSTROM_SOURCE
    assert L.R_MIN_BOHR == Q("1.2") / Q("0.529177210903")
    with pytest.raises(L.PhysicsDomainExceeded):
        L.check_domain(L.R_MIN_BOHR - Q(1, 10 ** 30))
    assert issubclass(L.ReferenceUndecided, Exception)                     # refuse, never guess


def test_frozen_fixture_bits_and_its_contract() -> None:
    raw = X.FIXTURE.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == FROZEN_FIXTURE_SHA256
    fix = X.load()
    assert fix["contract"]["version"] == FROZEN_CONTRACT
    assert fix["contract"]["parameter_fingerprint"] == FROZEN_PARAMETER_FINGERPRINT
    assert fix["contract"]["units"] == "R bohr, V and sigma hartree, F hartree/bohr"
    assert fix["provenance"]["lang2024_files_sha256"] == FROZEN_LANG_SHA256


def test_provenance_names_the_exact_code_that_generated_the_fixture() -> None:
    """Every recorded code hash equals the current file, and the recorded commit holds exactly those files."""
    p = X.load()["provenance"]
    assert p["code_files_committed_at_head"] is True
    assert p["reference_code_sha256"] == X.code_sha256(X.ROOT / "a_reference/ar2_lang2024.py")
    assert p["generator_code_sha256"] == X.code_sha256(X.ROOT / X.GENERATOR_FILE)
    for group in ("reference_dependencies_sha256", "audit_code_sha256"):
        for f, h in p[group].items():
            assert h == X.code_sha256(X.ROOT / f), f
    if shutil.which("git") is None:
        pytest.skip("git not available")
    head = p["git_head_at_generation"]
    for f in X.code_files():
        blob = subprocess.run(["git", "show", f"{head}:{f}"], capture_output=True, cwd=X.ROOT)
        if blob.returncode != 0:
            pytest.skip(f"commit {head} not in this clone")
        assert hashlib.sha256(blob.stdout).hexdigest() == X.code_sha256(X.ROOT / f), f
