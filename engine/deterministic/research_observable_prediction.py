"""G6c-3: the one generic prediction kind a synthetic world's adapter can evaluate.

`ObservablePrediction` names a tick and a public observable's expected
boolean value -- nothing about bonds, energy, or momentum. Physical A's five
existing prediction kinds (`StateDigestPrediction` etc., in
`causal_hypothesis.py`) are untouched; this is a sixth, separate kind a
caller can seal alongside or instead of them, evaluated only by an adapter
that declares support for it (`SyntheticResearchAdapter`, not
`PhysicalCausalResearchAdapter` -- see `physical_research_adapter.py`'s
`_SUPPORTED_PREDICTION_KINDS`, which this kind is deliberately absent from).
"""
from __future__ import annotations

from dataclasses import dataclass

FORMAT = "observable-prediction-v1"


def _text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be non-empty text")
    return value


@dataclass(frozen=True)
class ObservablePrediction:
    tick: int
    observable_id: str
    expected_value: bool

    def __post_init__(self) -> None:
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValueError("tick must be a nonnegative integer")
        _text(self.observable_id, "observable_id")
        if not isinstance(self.expected_value, bool):
            raise ValueError("expected_value must be a boolean")

    def canonical(self) -> dict[str, object]:
        return {"expected_value": self.expected_value, "kind": "observable_value",
                "observable_id": self.observable_id, "tick": self.tick}
