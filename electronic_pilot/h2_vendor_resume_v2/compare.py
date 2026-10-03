"""Compare vendor output without importing its numerical implementation.

Printed energy/observable reproduction is distinct from unreported native
iteration termination, lowest-root qualification and recurrence correctness.
"""
import re
from decimal import Decimal, InvalidOperation, localcontext


NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?\Z")
ENERGY = re.compile(r"^\s*EN\s*=\s*(\S+)\s*$", re.MULTILINE)
FAILURE = re.compile(
    r"\b(?:nan|inf(?:inity)?|error|warning|failed|failure|stop)\b|"
    r"iteration.{0,40}(?:limit|maximum)|(?:limit|maximum).{0,40}iteration|"
    r"not\s+converg|no\s+converg", re.IGNORECASE)
FIELDS = {
    "basis_size": r"Basis size:\s*(\d+)",
    "integral_digits_label": r"Work\. prec\. for integr\.:\s*(\d+)",
    "linear_algebra_digits_label": r"Work\. prec\. for lin\. alg\.:\s*(\d+)",
    "restriction1": r"Type 1 of restriction:\s*(\d+)",
    "restriction2": r"Type 2 of restriction:\s*(\d+)",
    "omega": r"Rank \(OMEGA\):\s*(\d+)",
    "nmax": r"Length of Taylor series:\s*(\d+)",
    "nuclear_symmetry": r"A <-> B symmetry:\s*(\S+)",
    "electron_symmetry": r"r1 <-> r2 symmetry:\s*(\S+)",
    "basis_family": r"^\s*((?:James-Coolidge|H2 SYM|H-H\+ SYM|General KOLOS)[^\n]*)",
    "delta_r12": r"4\*Pi\*DELTA\(r12\)\s*=\s*(\S+)",
}


def decimal(token):
    value = Decimal(token.replace("D", "E").replace("d", "e"))
    if not value.is_finite():
        raise ValueError("nonfinite number")
    return value


def fields(text):
    text = re.sub(r"[ \t]+", " ", text)
    energies = ENERGY.findall(text)
    if len(energies) != 1:
        raise ValueError("missing or duplicated final energy")
    result = {"energy": str(decimal(energies[0]))}
    for name, pattern in FIELDS.items():
        matches = re.findall(pattern, text, re.MULTILINE)
        if not matches:
            raise ValueError("missing field: " + name)
        values = [" ".join(m.split()) for m in matches]
        if len(set(values)) != 1:
            raise ValueError("ambiguous field: " + name)
        result[name] = values[0]
    return result


def compare(reference, actual, stderr, solver_exit, example_exit, protocol):
    """Fail closed on observable failures; expose unavailable native telemetry."""
    issues = []
    if solver_exit != 0 or example_exit != 0:
        issues.append("PROCESS_EXIT")
    for channel, text in [("stdout", actual), ("stderr", stderr)]:
        match = FAILURE.search(text)
        if match:
            issues.append("FAILURE_INDICATION:" + channel + ":" + match.group(0))
    normalized_actual = re.sub(r"[ \t]+", " ", actual)
    for marker in ("integrals completed", "Hamitonian matrix completed",
                   "Resulting energy:", "Input OK", "4*Pi*DELTA(r12)"):
        if marker not in normalized_actual:
            issues.append("MISSING_COMPLETION:" + marker)
    measured = expected = None
    try:
        expected, measured = fields(reference), fields(actual)
    except (ValueError, InvalidOperation) as exc:
        issues.append("FIELDS:" + str(exc))
    exact_decimals = None
    differences = []
    with localcontext() as ctx:
        ctx.prec = 100
        if measured is not None and expected is not None:
            for key in FIELDS:
                if key != "delta_r12" and measured[key] != expected[key]:
                    issues.append("FIELD_MISMATCH:" + key)
            energy_difference = abs(decimal(measured["energy"]) - decimal(expected["energy"]))
            if energy_difference > Decimal(protocol["comparison"]["energy_absolute_Eh"]):
                issues.append("ENERGY_MISMATCH")
            exact_decimals = decimal(measured["energy"]) == decimal(expected["energy"])
        ref_tokens, out_tokens = reference.split(), actual.split()
        if len(ref_tokens) != len(out_tokens):
            issues.append("TOKEN_COUNT_MISMATCH")
        else:
            tolerance = Decimal(protocol["comparison"]["float_token_abs_relative"])
            for index, (a, b) in enumerate(zip(ref_tokens, out_tokens)):
                if NUMBER.fullmatch(a) and NUMBER.fullmatch(b):
                    va, vb = decimal(a), decimal(b)
                    integer = not any(ch in a + b for ch in ".eEdD")
                    permitted = Decimal(0) if integer else tolerance * max(Decimal(1), abs(va))
                    delta = abs(vb - va)
                    if delta:
                        differences.append({"token": index, "reference": a, "actual": b,
                                            "abs_difference": str(delta), "tolerance": str(permitted)})
                    if delta > permitted:
                        issues.append("NUMERIC_TOKEN_MISMATCH:" + str(index))
                elif a != b:
                    issues.append("TEXT_TOKEN_MISMATCH:" + str(index))
    return {
        "printed_output_match": not issues,
        "status": "VENDOR_PRINTED_OUTPUT_REPRODUCED" if not issues else "H2SOLV_VENDOR_EXAMPLE_MISMATCH",
        "issues": issues,
        "expected": expected, "measured": measured,
        "energy_exact_decimal_match": exact_decimals,
        "numeric_token_differences": differences,
        "solver_errors_or_nonfinite": bool(FAILURE.search(actual + "\n" + stderr)),
        "native_iteration_count": None,
        "native_iteration_limit_reached": None,
        "native_root_convergence": "UNAVAILABLE_NOT_REPORTED_BY_UNMODIFIED_VENDOR",
        "root_energy_output_check": "REFERENCE_PRINTED_ENERGY_REPRODUCTION_ONLY",
        "independent_root_convergence_pass": False,
        "lowest_root_certified": False,
    }
