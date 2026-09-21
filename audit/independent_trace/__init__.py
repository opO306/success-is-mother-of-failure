"""A second, independent reader of the engine's provenance traces.

Nothing here imports from `engine`. See `README.md` for why that matters and
`tests/test_audit_independence.py` for the check that keeps it true.
"""
from .canonical import CanonicalError, canonical_bytes, canonical_text, digest
from .delta import DeltaError, apply_delta, parse_path
from .external_hash import ExternalHashResult, sha256_via_external_tool
from .verifier import (
    FORMAT,
    GENESIS_HASH,
    Finding,
    IndependentVerification,
    verify_trace_independently,
)

__all__ = [
    "CanonicalError",
    "DeltaError",
    "ExternalHashResult",
    "FORMAT",
    "Finding",
    "GENESIS_HASH",
    "IndependentVerification",
    "apply_delta",
    "canonical_bytes",
    "canonical_text",
    "digest",
    "parse_path",
    "sha256_via_external_tool",
    "verify_trace_independently",
]
