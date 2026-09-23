"""Model-neutral evidence types shared by B's hypothesis records.

Moved out of `hypotheses.py` (which still re-exports them): that module also
imports the environment world's spec, so any B-side module that needed only
`EvidenceReference` was pulling A's physics-spec code into its import
closure -- a path constitution art. 25 forbids. Found by G11's boundary test,
which (unlike the earlier ones) also forbids environment modules. This
module imports nothing from any world.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RationalWeight:
    numerator: int
    denominator: int
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.numerator, bool) or not isinstance(self.numerator, int) or self.numerator < 0:
            raise ValueError("weight numerator must be a nonnegative integer")
        if isinstance(self.denominator, bool) or not isinstance(self.denominator, int) or self.denominator <= 0:
            raise ValueError("weight denominator must be a positive integer")
        if self.numerator > self.denominator: raise ValueError("weight cannot exceed one")
        if not self.evidence_ids: raise ValueError("a numerical weight needs evidence provenance")

    def canonical(self) -> dict[str, object]:
        return {"denominator": self.denominator, "evidence_ids": list(self.evidence_ids),
                "numerator": self.numerator}


@dataclass(frozen=True)
class EvidenceReference:
    evidence_id: str
    relation: str
    source_digest: str
    description: str

    def __post_init__(self) -> None:
        if self.relation not in ("supports", "refutes", "leaves_open"):
            raise ValueError("unsupported evidence relation")
        if not all(isinstance(value, str) and value for value in
                   (self.evidence_id, self.source_digest, self.description)):
            raise ValueError("evidence fields must be non-empty text")

    def canonical(self) -> dict[str, str]:
        return {"description": self.description, "evidence_id": self.evidence_id,
                "relation": self.relation, "source_digest": self.source_digest}
