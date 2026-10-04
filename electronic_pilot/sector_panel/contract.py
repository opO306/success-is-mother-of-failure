"""Authoritative Z/positions/Ne/sector; charge is derived, labels refused."""
import math


def validate(case):
    if set(case) != {"nuclei", "ghost_centers_bohr", "electrons", "sector", "basis", "law"}:
        raise ValueError("REFUSED: unknown/missing authority or chemical label")
    if case["basis"] != "cc-pVTZ" or case["law"] != "isolated_clamped_nonrelativistic_coulomb":
        raise ValueError("REFUSED: unsupported Hamiltonian/basis")
    if type(case["electrons"]) is not int or (case["electrons"], case["sector"]) not in {
            (1, "doublet"), (2, "singlet"), (2, "triplet")}:
        raise ValueError("REFUSED: unsupported electron/spin sector")
    nuclei = case["nuclei"]
    if not isinstance(nuclei, list) or len(nuclei) not in (1, 2):
        raise ValueError("REFUSED: unsupported nuclear panel")
    for n in nuclei:
        if set(n) != {"Z", "position_bohr"} or type(n["Z"]) is not int or n["Z"] != 1:
            raise ValueError("REFUSED: this pilot supports Z=1 only")
    ghosts = case["ghost_centers_bohr"]
    if not isinstance(ghosts, list) or len(ghosts) > 1 or (ghosts and len(nuclei) != 1):
        raise ValueError("REFUSED: invalid fragment ghost control")
    positions = [n["position_bohr"] for n in nuclei] + ghosts
    if len(positions) > 2:
        raise ValueError("REFUSED: too many basis centers")
    for p in positions:
        if not isinstance(p, list) or len(p) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in p):
            raise ValueError("REFUSED: nonfinite/invalid position")
    if len(positions) == 2 and positions[0] == positions[1]:
        raise ValueError("REFUSED: coincident centers")
    return sum(n["Z"] for n in nuclei) - case["electrons"]


def validate_charge_assertion(case, asserted_charge):
    """Import diagnostic only: assertion is never a solver authority."""
    derived = validate(case)
    if type(asserted_charge) is not int or asserted_charge != derived:
        raise ValueError("REFUSED: charge assertion conflicts with sum(Z)-Ne")
    return derived


def dimension(m, electrons, sector):
    if (electrons, sector) == (1, "doublet"):
        return m
    if (electrons, sector) == (2, "singlet"):
        return m*(m+1)//2
    if (electrons, sector) == (2, "triplet"):
        return m*(m-1)//2
    raise ValueError("REFUSED: unsupported electron/spin sector")
