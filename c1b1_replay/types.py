"""Public verdict/resource types. Computational VALID is not designer approval."""
from dataclasses import dataclass
from enum import Enum

class Verdict(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    REFUSED = "REFUSED"

class Invalid(Exception):
    pass

class Refused(Exception):
    pass

@dataclass(frozen=True)
class Limits:
    max_steps: int = 2_000_000
    max_bytes: int = 128_000_000
    max_evaluations: int = 4_000_010
    start_bits: int = 128
    max_bits: int = 16384
    seconds: float = 3600.0

    def __post_init__(self):
        for name in ("max_steps", "max_bytes", "max_evaluations", "start_bits", "max_bits"):
            v = getattr(self, name)
            if type(v) is not int or v < 1:
                raise ValueError(name)
        if not 16 <= self.start_bits <= self.max_bits <= 16384:
            raise ValueError("precision must fit the unchanged contract cap")
        import math
        if type(self.seconds) not in (int, float) or not math.isfinite(self.seconds) or self.seconds <= 0:
            raise ValueError("seconds")

@dataclass(frozen=True)
class Result:
    verdict: Verdict
    reason: str
    verified_steps: int
    last_state: tuple | None
    evaluations: int
    max_precision: int
    cpu_seconds: float
    wall_seconds: float
    witness_bytes: int
    witness_sha256: str
    spec_fingerprint: str
    implementation_fingerprint: str
    dependency_fingerprint: str
    trust: tuple = ("mpmath-1.3.0 interval encloses real values", "Python integer/Fraction semantics")
