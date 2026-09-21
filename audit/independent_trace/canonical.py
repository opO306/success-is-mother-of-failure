"""Independent canonical serialisation and hashing.

The engine derives its digests with `json.dumps(..., sort_keys=True,
separators=(",", ":"))`. If that call ever produced something other than the
intended canonical form, the engine's own verifier would reproduce the same
mistake and still report a match.

This module therefore does NOT call `json.dumps` for hashing. It walks the
value and emits canonical bytes from explicit rules, so a disagreement between
the two routes is visible instead of silently cancelling out.

Canonical form (stated, not inherited):

- object   : `{` key `:` value (`,` ...) `}` with keys sorted by UTF-16 code
             unit order, which is what Python's `sorted()` on `str` gives and
             what `json.dumps(sort_keys=True)` uses.
- array    : `[` value (`,` ...) `]`, order preserved
- string   : double quoted, with `"` `\\` and C0 controls escaped; all other
             characters, including non-ASCII, emitted literally (UTF-8)
- integer  : shortest decimal form; `bool` is NOT an integer here
- bool/null: `true` / `false` / `null`
- float    : rejected. The world is integer-only, so a float in a trace is
             itself a finding, not something to hash over.
"""
from __future__ import annotations

import hashlib
from typing import Any

_ESCAPES = {
    0x22: '\\"',
    0x5C: "\\\\",
    0x08: "\\b",
    0x0C: "\\f",
    0x0A: "\\n",
    0x0D: "\\r",
    0x09: "\\t",
}


class CanonicalError(ValueError):
    """A value cannot be represented in the canonical form."""


def _string(value: str, path: str) -> str:
    out = ['"']
    for char in value:
        point = ord(char)
        escape = _ESCAPES.get(point)
        if escape is not None:
            out.append(escape)
        elif point < 0x20:
            out.append(f"\\u{point:04x}")
        else:
            out.append(char)
    out.append('"')
    return "".join(out)


def canonical_text(value: Any, path: str = "$") -> str:
    """Render `value` in this module's own canonical form."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        raise CanonicalError(f"float is not allowed in an integer world at {path}")
    if isinstance(value, str):
        return _string(value, path)
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            if not isinstance(key, str):
                raise CanonicalError(f"object key must be a string at {path}")
            parts.append(f"{_string(key, path)}:{canonical_text(value[key], f'{path}.{key}')}")
        return "{" + ",".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(
            canonical_text(item, f"{path}[{index}]") for index, item in enumerate(value)
        ) + "]"
    raise CanonicalError(f"unsupported type {type(value).__name__} at {path}")


def canonical_bytes(value: Any) -> bytes:
    return canonical_text(value).encode("utf-8")


def digest(value: Any) -> str:
    """SHA-256 over this module's canonical bytes."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
