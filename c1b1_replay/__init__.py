"""Independent C1-B1 replay verification; no executor implementation dependencies."""
from .types import Limits, Result, Verdict
from .verify import verify

__all__ = ["Limits", "Result", "Verdict", "verify"]
