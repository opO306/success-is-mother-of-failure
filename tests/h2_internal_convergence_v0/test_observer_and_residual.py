"""Known dyadics, independent algebra, and deliberate observer corruptions."""
from fractions import Fraction
from pathlib import Path
import struct

import pytest

from electronic_pilot.h2_internal_convergence_v0.instrument import helper_bytes, instrument, low_itmax, strip_observer
from electronic_pilot.h2_internal_convergence_v0.observe import parse
from electronic_pilot.h2_internal_convergence_v0.residual import measure
from electronic_pilot.h2_internal_convergence_v0.snapshot import context, decode_word, read_hs, read_ev, HS_MAGIC, EV_MAGIC, ZERO_EXP


def words(value, bits=320):
    value = Fraction(value)
    if value == 0:
        return [bits, 1, ZERO_EXP] + [0] * 6
    numerator, denominator = abs(value.numerator), value.denominator
    assert denominator & (denominator - 1) == 0
    exponent = numerator.bit_length() - (denominator.bit_length() - 1)
    mantissa = numerator << (bits - numerator.bit_length())
    limbs = []
    for i in range(6):
        limb = (mantissa >> (64 * i)) & ((1 << 64) - 1)
        limbs.append(limb if limb < (1 << 63) else limb - (1 << 64))
    return [bits, 1 if value > 0 else 4294967295, exponent, *limbs]


def value_line(name, value):
    return "VALUE " + name + " " + " ".join(map(str, words(value))) + "\n"


def sidecar(exhausted=False, error=False):
    maxit = 1 if exhausted else 40
    text = f"SNAPSHOT 2 7 80 60 {maxit}\n"
    text += value_line("initial_EN", -1) + value_line("EPSKOR", 0)
    text += f"BEGIN 2 {maxit} 0\n" + value_line("errest", Fraction(1, 2) if not exhausted else Fraction(1, 16))
    text += "LEQ 1 0 0\n" + value_line("factor_negative_count", 1)
    text += "LEQ 2 1 0\nITER 1\n"
    text += value_line("previous", -1) + value_line("updated", Fraction(-3, 4))
    text += value_line("signed_delta", Fraction(1, 4)) + value_line("abs_delta", Fraction(1, 4))
    text += value_line("threshold", Fraction(3, 64) if exhausted else Fraction(3, 8))
    if exhausted:
        text += "EXHAUSTED 1\nNORMALIZED_EXHAUSTED 1 0\n"
    else:
        text += "NORMALIZED_CONVERGED 1 0\n"
    text += f"RETURN {65 if error else 0}\n" + value_line("final_EN", Fraction(-3, 4)) + value_line("wa1", 1)
    return text


@pytest.mark.parametrize("number", [0, -1, Fraction(-3, 2), Fraction(25, 8), 2**100, Fraction(1, 2**300), Fraction(2**100+1, 2**100)])
def test_exact_dyadic_reader(number):
    ctx = context()
    decoded, bits = decode_word(words(number), ctx)
    assert decoded == ctx.mpf(Fraction(number).numerator) / Fraction(number).denominator
    assert bits == 320


@pytest.mark.parametrize("position,replacement", [(0, 53), (0, 448), (1, 0), (2, ZERO_EXP+1), (7, 0), (8, 1)])
def test_corrupt_native_record_rejected(position, replacement):
    record = words(1)
    record[position] = replacement
    with pytest.raises(ValueError):
        decode_word(record, context())


def test_real_branch_converged(tmp_path):
    path = tmp_path / "audit.log"
    path.write_text(sidecar(), encoding="ascii")
    result = parse(path)
    assert result["inverse_iteration_supported"]
    assert result["termination_reason"] == "EIGENVALUE_TEST"
    assert not result["maxit_exhausted"]


def test_maxit_exhaustion_despite_normal_output(tmp_path):
    path = tmp_path / "audit.log"
    path.write_text(sidecar(exhausted=True), encoding="ascii")
    result = parse(path)
    assert result["termination_reason"] == "MAXIT_EXHAUSTED"
    assert result["maxit_exhausted"]
    assert not result["inverse_iteration_supported"]


def test_leq_error_never_pass(tmp_path):
    path = tmp_path / "audit.log"
    path.write_text(sidecar(error=True), encoding="ascii")
    assert not parse(path)["inverse_iteration_supported"]


@pytest.mark.parametrize("old,new", [
    ("NORMALIZED_CONVERGED 1 0", "EXHAUSTED 40\nNORMALIZED_EXHAUSTED 1 0"),
    ("NORMALIZED_CONVERGED 1 0", "NORMALIZED_CONVERGED 2 0"),
    ("LEQ 1 0 0", "LEQ 1 0 129"),
    (value_line("wa1", 1), value_line("wa1", 0)),
    (value_line("threshold", Fraction(3, 8)), value_line("threshold", Fraction(1, 2))),
    (value_line("signed_delta", Fraction(1, 4)), value_line("signed_delta", Fraction(1, 8))),
    (value_line("previous", -1), value_line("previous", -2)),
    ("ITER 1", "ITER 2"),
    ("RETURN 0", ""),
    (value_line("final_EN", Fraction(-3, 4)), ""),
])
def test_sidecar_fault_injections_fail_closed(tmp_path, old, new):
    path = tmp_path / "audit.log"
    path.write_text(sidecar().replace(old, new), encoding="ascii")
    try:
        result = parse(path)
    except ValueError:
        return
    assert not result["inverse_iteration_supported"]


def test_wrong_energy_and_normalization_are_measured(tmp_path):
    ctx = context()
    # H=[[2,1],[1,3]], S=I, v=(2,0), E=2: r=(0,2), vTSv=4, RQ=2.
    result = measure(list(map(ctx.mpf, [2, 1, 3])), list(map(ctx.mpf, [1, 0, 1])),
                     ctx.mpf(2), list(map(ctx.mpf, [2, 0])), ctx)
    assert ctx.mpf(result["residual_l2"]) == 2
    assert ctx.mpf(result["residual_linf"]) == 2
    assert ctx.mpf(result["vTSv"]) == 4
    assert ctx.mpf(result["normalization_abs_error"]) == 3
    assert ctx.mpf(result["E_RQ_minus_E_invsg"]) == 0
    assert "PASS" not in result
    wrong_energy = measure(list(map(ctx.mpf, [2, 1, 3])), list(map(ctx.mpf, [1, 0, 1])),
                           ctx.mpf(4), list(map(ctx.mpf, [2, 0])), ctx)
    assert ctx.mpf(wrong_energy["residual_linf"]) == 4
    assert ctx.mpf(wrong_energy["E_RQ_minus_E_invsg"]) == -2


def test_indefinite_metric_refused():
    ctx = context()
    with pytest.raises(ValueError, match="nonpositive"):
        measure([ctx.mpf(2)], [ctx.mpf(-1)], ctx.mpf(2), [ctx.mpf(1)], ctx)


def test_packed_snapshot_length_and_order(tmp_path):
    ctx = context()
    path = tmp_path / "HS.bin"
    data = struct.pack("<9q", HS_MAGIC, 1, 2, 3, 6, 60, 80, 7, 40)
    data += b"".join(struct.pack("<9q", *words(v)) for v in [2, 1, 3, 1, 0, 1])
    path.write_bytes(data)
    h, s, metadata = read_hs(path, ctx)
    assert h == [2, 1, 3] and s == [1, 0, 1]
    assert metadata["precision_bits_counts"] == {320: 6}
    path.write_bytes(data[:-1])
    with pytest.raises(ValueError, match="length"):
        read_hs(path, ctx)


def test_vector_snapshot_length(tmp_path):
    ctx = context()
    path = tmp_path / "EV.bin"
    data = struct.pack("<4q", EV_MAGIC, 1, 2, 6)
    data += b"".join(struct.pack("<9q", *words(v)) for v in [2, 1, 0])
    path.write_bytes(data)
    energy, vector, _ = read_ev(path, ctx)
    assert energy == 2 and vector == [1, 0]
    path.write_bytes(data + b"unexpected")
    with pytest.raises(ValueError, match="length"):
        read_ev(path, ctx)


def test_original_calculation_lines_retained():
    root = Path(__file__).resolve().parents[2]
    source = (root / "runs/h2_representation_pilot1/resume_v1_20261003/vendor_original/h2solv/f/h2solv.f").read_bytes()
    observed = instrument(source, helper_bytes())
    assert observed != source
    assert strip_observer(observed) == source
    mutant = low_itmax(observed)
    assert mutant != observed
    assert b"itmax = 1 !" in mutant
    assert b"itmax = 40 !" in observed
