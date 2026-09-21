"""Independent audit tools.

This package MUST NOT import from `engine`. It exists to check the engine's
own records by a separate route, so a bug shared between a writer and its
verifier cannot hide. See `audit/independent_trace/README.md`.
"""
