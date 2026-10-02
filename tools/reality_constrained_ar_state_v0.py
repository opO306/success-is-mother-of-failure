"""SURVEY_ONLY deterministic candidates; never a production A initializer.

Default reality-only path refuses missing data. Explicit conditional proxy mode
compares presealed algorithms, reports all results, and never repairs a state.
No RNG or binary floating-point, physics imports, force, integration, or network.
Fixed-context Decimal approximates coefficient representatives/diagnostics;
Fraction and integer root comparisons exactly define/project those representatives.
"""
import argparse
from collections import Counter
from decimal import Decimal as D, localcontext, ROUND_HALF_EVEN
from fractions import Fraction as F
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/proposals/reality_constrained_ar_state_v0"
SOURCE_SHA = "6015bbcd25d556ad2246b095b940fe51341d21ca0a02825bea8cc2c2a5c3094d"
PROTOCOL_SHA = "bca5c3f3505cfa71688909fff98e90e4b440dad6a6846abd1a3d3e14a2c83f35"
NS = (4, 8, 16, 32, 64)
Q_METHODS = ("Q1_GRID", "Q2_HALTON", "Q4_RANK1")
P_METHODS = ("P1_CARTESIAN_QUANTILES", "P2_RADIAL_SPHERE_ANTIPODAL")
# Copied source-versioned nominal constants for observation only; no A import.
KB_SI = F("1.380649e-23")  # SI exact definition
KB_AU = F("3.1668115634564e-6")  # CODATA2022 table, nominal Eh/K
A0_M = F("5.29177210903e-11")  # C1-A source-versioned CODATA2018
MASS_AU = F("39.9623831237") / F("5.485799090441e-4")  # C1-B1 nominal Ar40/me
PI = D("3.141592653589793238462643383279502884197169399375105820974944592307816406")
BINS = tuple(map(F, ("1/64", "1/16", "1/4", "9/16", "1", "2", "3")))


class Refused(ValueError):
    pass


def pinned_json(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise Refused("INPUT_BYTES_CHANGED")
    return json.loads(raw)


def inputs(source=DATA / "source_manifest.json", protocol=DATA / "protocol_v0.json"):
    return pinned_json(source, SOURCE_SHA), pinned_json(protocol, PROTOCOL_SHA)


def decimal(value):
    value = F(value)
    return D(value.numerator) / D(value.denominator)


def erf(value):
    # Fixed series, range used only by the declared bounded quantile search.
    term = value
    total = term
    for k in range(1, 240):
        term *= -value * value / k
        total += term / (2 * k + 1)
    return 2 * total / PI.sqrt()


def cdf(value, kind):
    if kind == "normal":
        return (1 + erf(value / D(2).sqrt())) / 2
    if kind == "maxwell":
        if value <= 0:
            return D(0)
        return erf(value / D(2).sqrt()) - (D(2) / PI).sqrt() * value * (-value * value / 2).exp()
    raise Refused("UNKNOWN_DISTRIBUTION")


@lru_cache(maxsize=512)
def quantile(probability, kind):
    with localcontext() as ctx:
        ctx.prec = 70
        ctx.rounding = ROUND_HALF_EVEN
        target = decimal(probability)
        supported = {F(1, 2) + F(2 * j + 1, 2 * n) if kind == "normal"
                     else F(2 * j + 1, n)
                     for n in NS for j in range(n // 2)}
        if probability not in supported or not 0 < target < 1:
            raise Refused("UNSUPPORTED_QUANTILE")
        low, high = D(0), D(8)
        if kind == "normal" and target <= D("0.5"):
            raise Refused("POSITIVE_NORMAL_QUANTILE_ONLY")
        for _ in range(128):
            middle = (low + high) / 2
            if cdf(middle, kind) < target:
                low = middle
            else:
                high = middle
        return F(((low + high) / 2).quantize(D("1e-30")))


def radical_inverse(index, base):
    result, denominator = F(0), 1
    while index:
        index, digit = divmod(index, base)
        denominator *= base
        result += F(digit, denominator)
    return result


def positions(n, method):
    if type(n) is not int or n not in NS:
        raise Refused("UNSUPPORTED_N")
    if method == "Q1_GRID":
        side = next(k for k in range(1, 5) if k ** 3 >= n)
        points = [tuple(F(2 * x + 1, 2 * side) for x in v)
                  for v in itertools.product(range(side), repeat=3)][:n]
    elif method == "Q2_HALTON":
        points = [tuple(radical_inverse(i, base) for base in (2, 3, 5)) for i in range(1, n + 1)]
    elif method == "Q4_RANK1":
        points = [tuple(F(2 * ((multiplier * k) % n) + 1, 2 * n)
                        for multiplier in (1, 3, 5)) for k in range(n)]
    elif method == "Q3_EXPERIMENTAL_RECONSTRUCTION":
        raise Refused("STRUCTURE_STATISTICS_UNAVAILABLE")
    else:
        raise Refused("UNKNOWN_POSITION_METHOD")
    if len(set(points)) != n:
        raise Refused("POSITION_TIE_UNSUPPORTED")
    return sorted(tuple(x - F(1, 2) for x in v) for v in points)


def trig(phi):
    phi = phi % (2 * PI)
    if phi > PI:
        phi -= 2 * PI
    cos_term, sin_term = D(1), phi
    cosine, sine = cos_term, sin_term
    for k in range(1, 120):
        cos_term *= -phi * phi / ((2 * k - 1) * (2 * k))
        sin_term *= -phi * phi / ((2 * k) * (2 * k + 1))
        cosine += cos_term
        sine += sin_term
    return cosine, sine


def rational_sphere_direction(j, half):
    with localcontext() as ctx:
        ctx.prec = 70
        ctx.rounding = ROUND_HALF_EVEN
        z = decimal(F(2 * j + 1, 2 * half))
        cosine, sine = trig(D(j) * PI * (3 - D(5).sqrt()))
        radius = (1 - z * z).sqrt()
        u = F((radius * cosine / (1 + z)).quantize(D("1e-30")))
        v = F((radius * sine / (1 + z)).quantize(D("1e-30")))
    denom = 1 + u * u + v * v
    return (2 * u / denom, 2 * v / denom, (1 - u * u - v * v) / denom)


@lru_cache(maxsize=16)
def momenta_coefficients(n, method):
    half = n // 2
    if n not in NS:
        raise Refused("UNSUPPORTED_N")
    if method == "P1_CARTESIAN_QUANTILES":
        values = [quantile(F(1, 2) + F(2 * j + 1, 2 * n), "normal") for j in range(half)]
        positive = [tuple(values[(mult * j + shift) % half]
                          for mult, shift in ((1, 0), (3, 1), (5, 1))) for j in range(half)]
    elif method == "P2_RADIAL_SPHERE_ANTIPODAL":
        positive = [tuple(quantile(F(2 * j + 1, 2 * half), "maxwell") * v
                          for v in rational_sphere_direction(j, half)) for j in range(half)]
    else:
        raise Refused("UNKNOWN_MOMENTUM_METHOD")
    return tuple(v for point in positive for v in (point, tuple(-x for x in point)))


def squared(v):
    return sum(x * x for x in v)


def distance2(a, b):
    return squared(tuple(x - y for x, y in zip(a, b)))


@lru_cache(maxsize=2)
def uniform_cube_proxy():
    # Independent pair difference density: 8 product(1-|d_k|), d_k>=0.
    # A fixed quadrature diagnostic, not measured g(r) or minimum-image distances.
    weights = [F(63 - 2 * j, 1024) for j in range(32)]
    counters = [F(0)] * len(BINS)
    for indices in itertools.product(range(32), repeat=3):
        r2 = sum(F(2 * j + 1, 64) ** 2 for j in indices)
        weight = weights[indices[0]] * weights[indices[1]] * weights[indices[2]]
        for k, bound in enumerate(BINS):
            if r2 <= bound:
                counters[k] += weight
    return tuple(counters)


def nth_floor_integer(value, degree):
    if value < 0 or degree not in (2, 3):
        raise Refused("UNSUPPORTED_ROOT")
    low, high = 0, 1 << ((value.bit_length() + degree - 1) // degree)
    while low < high:
        middle = (low + high + 1) // 2
        if middle ** degree <= value:
            low = middle
        else:
            high = middle - 1
    return low


def root_floor_raw(value, degree, frac_bits):
    scaled = F(value) * (1 << (degree * frac_bits))
    return nth_floor_integer(scaled.numerator // scaled.denominator, degree)


def round_algebraic(coefficient, radicand, degree, frac_bits, width=96):
    coefficient, radicand = F(coefficient), F(radicand)
    if radicand < 0:
        raise Refused("NEGATIVE_RADICAND")
    target = abs(coefficient) ** degree * radicand
    lower = root_floor_raw(target, degree, frac_bits)
    half = F(2 * lower + 1, 2 * (1 << frac_bits)) ** degree
    raw = lower + (target > half or (target == half and lower % 2 == 1))
    raw = int(raw) * (-1 if coefficient < 0 else 1)
    if not -(1 << (width - 1)) <= raw < (1 << (width - 1)):
        raise Refused("FX_OVERFLOW")
    return raw


def root_interval(value, degree, bits=160):
    raw = root_floor_raw(value, degree, bits)
    lo = F(raw, 1 << bits)
    return lo, lo if lo ** degree == value else F(raw + 1, 1 << bits)


def max_round_error(coeffs, radicand, degree, grid, raw_points):
    lo, hi = root_interval(radicand, degree)
    error = F(0)
    for point, raw in zip(coeffs, raw_points):
        for coefficient, value in zip(point, raw):
            ends = (coefficient * lo, coefficient * hi)
            error = max(error, *(abs(v - F(value, 1 << grid)) for v in ends))
    return error


def cdf_discrepancy(values, kind):
    with localcontext() as ctx:
        ctx.prec = 70
        ctx.rounding = ROUND_HALF_EVEN
        result = D(0)
        count = len(values)
        for i, value in enumerate(sorted(values)):
            point = cdf(value, kind)
            result = max(result, abs(point - D(i) / count), abs(D(i + 1) / count - point))
        return F(result.quantize(D("1e-25")))


def statistics(q, p, temperature):
    n = len(q)
    pair_r2 = [distance2(q[i], q[j]) for i in range(n) for j in range(i)]
    nearest = [min(distance2(a, b) for j, b in enumerate(q) if j != i) for i, a in enumerate(q)]
    pair_cdf = [F(sum(v <= bound for v in pair_r2), len(pair_r2)) for bound in BINS]
    energy_norm = sum(squared(v) for v in p)
    kinetic = energy_norm * KB_AU * temperature / 2
    tensor = [[sum(v[a] * v[b] for v in p) / energy_norm for b in range(3)] for a in range(3)]
    directional = [[sum(v[a] * v[b] / squared(v) for v in p) / n for b in range(3)] for a in range(3)]
    covariance = [[sum((q[i][a] - sum(x[a] for x in q) / n) * p[i][b] for i in range(n)) / n
                   for b in range(3)] for a in range(3)]
    q_cross = [[sum((v[a] - sum(x[a] for x in q) / n) *
                        (v[b] - sum(x[b] for x in q) / n) for v in q) / n
                for b in range(3)] for a in range(3)]
    octants = {}
    conditional_octants = {"x_negative": {}, "x_nonnegative": {}}
    for v in p:
        key = "".join("+" if x > 0 else "-" if x < 0 else "0" for x in v)
        octants[key] = octants.get(key, 0) + 1
    for point, v in zip(q, p):
        group = conditional_octants["x_negative" if point[0] < 0 else "x_nonnegative"]
        key = "".join("+" if x > 0 else "-" if x < 0 else "0" for x in v)
        group[key] = group.get(key, 0) + 1
    multiplicities = Counter(p)
    antipodal = sum(min(count, multiplicities[tuple(-x for x in point)])
                    for point, count in multiplicities.items() if point < tuple(-x for x in point))
    with localcontext() as ctx:
        ctx.prec = 70
        ctx.rounding = ROUND_HALF_EVEN
        speed_ks = cdf_discrepancy([decimal(squared(v)).sqrt() for v in p], "maxwell")
        component_ks = [cdf_discrepancy([decimal(v[a]) for v in p], "normal") for a in range(3)]
    return {
        "pair_count": len(pair_r2), "pair_distance_squared_cdf_fractional": pair_cdf,
        "pair_cdf_uniform_cube_proxy_max_difference": max(abs(x - y) for x, y in zip(pair_cdf, uniform_cube_proxy())),
        "unique_pair_squared_distances": len(set(pair_r2)),
        "nearest_squared_fractional_min": min(nearest), "nearest_squared_fractional_max": max(nearest),
        "position_covariance_fractional": q_cross,
        "total_momentum_coefficient_exact": [sum(v[a] for v in p) for a in range(3)],
        "K_hartree_exact": kinetic, "K_over_kBT": energy_norm / 2,
        "Tkin_over_targetT_COM_removed": energy_norm / (3 * (n - 1)),
        "Tkin_K_COM_removed": energy_norm * temperature / (3 * (n - 1)),
        "speed_CDF_maxwell_proxy_discrepancy": speed_ks,
        "component_CDF_normal_proxy_discrepancy": component_ks,
        "speed_fourth_moment_normalized": sum(squared(v) ** 2 for v in p) / n,
        "MB_proxy_target_speed_fourth_moment": 15,
        "kinetic_direction_tensor": [[diagnostic_fraction(x) for x in row] for row in tensor],
        "unweighted_direction_tensor": [[diagnostic_fraction(x) for x in row] for row in directional],
        "kinetic_direction_max_deviation_from_isotropic": diagnostic_fraction(max(
            abs(tensor[a][b] - (F(1, 3) if a == b else 0)) for a in range(3) for b in range(3))),
        "octant_counts": octants, "distinct_speed_squared_count": len({squared(v) for v in p}),
        "position_conditioned_octants": conditional_octants,
        "exact_antipodal_pairs": antipodal,
        "q_p_covariance_dimensionless": [[diagnostic_fraction(x) for x in row] for row in covariance],
        "nonenergy_momentum_diagnostics_rounding": "25 decimal digits; not a formal distribution certificate",
        "empirical_structure_fit": "UNAVAILABLE",
        "statistics_reference_grade": "ASSUMED_IDEAL_GAS_AND_MB_PROXIES_NOT_EXPERIMENTAL",
    }


def diagnostic_fraction(value):
    with localcontext() as ctx:
        ctx.prec = 70
        ctx.rounding = ROUND_HALF_EVEN
        return F(decimal(value).quantize(D("1e-25")))


def fx_diagnostics(q, p, box_cubed, momentum_scale_squared, kinetic):
    qr = [tuple(round_algebraic(c, box_cubed, 3, 48) for c in v) for v in q]
    pr = [tuple(round_algebraic(c, momentum_scale_squared, 2, 80) for c in v) for v in p]
    quant_p = [tuple(F(x, 1 << 80) for x in v) for v in pr]
    after_k = sum(squared(v) for v in quant_p) / (2 * MASS_AU)
    q_error = max_round_error(q, box_cubed, 3, 48, qr)
    p_error = max_round_error(p, momentum_scale_squared, 2, 80, pr)
    L2_lo, L2_hi = root_interval(box_cubed * box_cubed, 3)
    max_pair_delta = F(0)
    for i in range(len(q)):
        for j in range(i):
            r2_coeff = distance2(q[i], q[j])
            raw_r2 = distance2(qr[i], qr[j]) / (1 << 96)
            max_pair_delta = max(max_pair_delta, abs(raw_r2 - r2_coeff * L2_lo), abs(raw_r2 - r2_coeff * L2_hi))
    return {
        "scope": "OBSERVATION_ONLY_NOT_A_INPUT_OR_BOUNDARY",
        "q_profile": "FX(96,48) bohr", "p_profile": "FX(96,80) atomic momentum",
        "q_raw": qr, "p_raw": pr,
        "max_abs_q_change_upper_bohr": q_error,
        "max_abs_p_change_upper_atomic": p_error,
        "K_before_exact_hartree": kinetic, "K_after_exact_hartree": after_k,
        "K_change_exact_hartree": after_k - kinetic,
        "K_relative_change_exact": (after_k - kinetic) / kinetic,
        "total_P_after_exact_atomic": [sum(v[a] for v in quant_p) for a in range(3)],
        "max_pair_R2_change_upper_bohr2": max_pair_delta,
        "initial_state_changed_to_help_quantization": False,
    }


def canonical_physical_records(records):
    return sorted((tuple(row["q_coefficient"]), tuple(row["p_coefficient"])) for row in records)


def check_minimum_separation(q, volume_bohr3, minimum_bohr):
    if volume_bohr3 <= 0 or minimum_bohr < 0:
        raise Refused("UNSUPPORTED_DENSITY_OR_MINIMUM")
    min_r2 = min(distance2(q[i], q[j]) for i in range(len(q)) for j in range(i))
    if min_r2 ** 3 * volume_bohr3 ** 2 < minimum_bohr ** 6:
        raise Refused("MINIMUM_SEPARATION_FAILED; state not repaired")


def generate(n, q_method, p_method, source=DATA / "source_manifest.json",
             protocol=DATA / "protocol_v0.json", conditional_proxy=False,
             minimum_separation_angstrom=F("1.2")):
    manifest, _ = inputs(source, protocol)
    if not conditional_proxy:
        raise Refused("REALITY_DATA_INSUFFICIENT: n/EOS, structure statistics, isotope mapping")
    if manifest["temperature_K"]["value"] != "273.16" or manifest["pressure_Pa"]["value"] != "80900":
        raise Refused("UNSUPPORTED_T_OR_DENSITY")
    temperature = F(manifest["temperature_K"]["value"])
    density_proxy = F(manifest["pressure_Pa"]["value"]) / (KB_SI * temperature)
    q, p = positions(n, q_method), momenta_coefficients(n, p_method)
    volume_bohr3 = F(n) / density_proxy / A0_M ** 3
    minimum = F(minimum_separation_angstrom)
    if minimum != F("1.2"):
        raise Refused("UNSUPPORTED_MINIMUM_SEPARATION")
    minimum_bohr = minimum * F("1e-10") / A0_M
    check_minimum_separation(q, volume_bohr3, minimum_bohr)
    stats = statistics(q, p, temperature)
    records = [{"storage_index": i, "species_proxy": "Ar40_ASSUMED",
                "q_coefficient": point, "p_coefficient": momentum}
               for i, (point, momentum) in enumerate(zip(q, p))]
    return {
        "classification": "REALITY_CONSTRAINED_GENERATED_STATE",
        "qualification": "CONDITIONAL_ASSUMED_PROXY_ONLY; NOT AN OBSERVED MICROSTATE",
        "reality_only_eligible": False, "production_A_input": False,
        "N_survey_only": n, "Q_method": q_method, "P_method": p_method,
        "source_sha256": SOURCE_SHA, "protocol_sha256": PROTOCOL_SHA,
        "field_status": {
            "temperature": "DERIVED_FROM_MEASUREMENT", "pressure": "DERIVED_FROM_MEASUREMENT",
            "q": "REALITY_CONSTRAINED_GENERATED", "p": "REALITY_CONSTRAINED_GENERATED",
            "number_density": "ASSUMED", "species_isotope_mapping": "ASSUMED",
            "momentum_distribution": "ASSUMED", "placement_cube": "ASSUMED",
            "experimental_g_r_and_S_q": "UNAVAILABLE", "physical_boundary": "UNAVAILABLE",
            "N": "ASSUMED", "units_constants": "DERIVED_FROM_MEASUREMENT",
            "storage_index": "REALITY_CONSTRAINED_GENERATED"},
        "number_density_proxy_m3_exact": density_proxy,
        "box_cube_volume_bohr3_exact": volume_bohr3,
        "q_exact_representation": "q_coefficient * positive_cuberoot(box_cube_volume_bohr3_exact), bohr",
        "p_exact_representation": "p_coefficient * positive_sqrt(momentum_scale_squared_exact), atomic momentum",
        "momentum_scale_squared_exact": MASS_AU * KB_AU * temperature,
        "mass_proxy_electron_masses_exact": MASS_AU,
        "minimum_separation_angstrom_diagnostic": minimum,
        "records": records, "statistics": stats,
        "FX_observation": fx_diagnostics(q, p, volume_bohr3, MASS_AU * KB_AU * temperature, stats["K_hartree_exact"]),
        "C1C_D5": "PENDING", "forward_steps": 0,
    }


def serializable(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    return value


def serialize(value):
    return json.dumps(serializable(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def campaign():
    inputs()
    examples = []
    for n in NS:
        for q in Q_METHODS:
            for p in P_METHODS:
                try:
                    examples.append(generate(n, q, p, conditional_proxy=True))
                except Refused as exc:
                    examples.append({"N_survey_only": n, "Q_method": q, "P_method": p,
                                     "status": "REFUSED", "reason": str(exc), "state_repaired": False})
    return {
        "verdict": "E_REALITY_DATA_INSUFFICIENT", "source_sha256": SOURCE_SHA,
        "protocol_sha256": PROTOCOL_SHA,
        "strict_reality_path": "REFUSED_REALITY_DATA_INSUFFICIENT",
        "scope": "CONDITIONAL_PROXY_SURVEY_ONLY; NOT AN OBSERVED MICROSTATE",
        "uniform_cube_CDF_reference": uniform_cube_proxy(),
        "examples": examples,
        "winner": None, "forward_steps": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--conditional-proxy-survey", action="store_true")
    args = parser.parse_args()
    if not args.conditional_proxy_survey:
        raise Refused("REALITY_DATA_INSUFFICIENT; no default assumption mode")
    if args.output.exists():
        raise Refused("OUTPUT_ALREADY_EXISTS")
    output = serialize(campaign())
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(output)
    print("30 presealed conditional examples; E / forward_steps=0 / no winner")
