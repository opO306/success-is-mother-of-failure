"""Independent delta checking — by application, not by regeneration.

The engine verifies a recorded delta by calling the same `_delta()` that
produced it and comparing the two results. A bug inside `_delta()` is
therefore invisible: it is applied to both sides of the comparison.

This module never regenerates a delta. It takes the recorded delta as given
and *applies* it to the before-snapshot, then checks the result equals the
after-snapshot. A delta that was computed wrongly will not reconstruct the
recorded successor, so the error surfaces instead of cancelling out.

Path grammar accepted here (matching what the recorder emits):

    $                  the document root
    $.key              a member of an object
    $.key.other        nested members

Array indexing is deliberately NOT supported: the recorder replaces a list
wholesale rather than indexing into it. A path that indexes an array is
reported as unsupported rather than guessed at.
"""
from __future__ import annotations

import copy
from typing import Any

_OPERATIONS = ("add", "remove", "replace")


class DeltaError(ValueError):
    """A delta cannot be parsed or applied."""


def parse_path(path: str) -> tuple[str, ...]:
    """Split `$.a.b` into `("a", "b")`. The root `$` yields an empty tuple."""
    if not isinstance(path, str) or not path.startswith("$"):
        raise DeltaError(f"path must start with '$': {path!r}")
    if path == "$":
        return ()
    if not path.startswith("$."):
        raise DeltaError(f"unsupported path syntax: {path!r}")
    steps = path[2:].split(".")
    if any(step == "" for step in steps):
        raise DeltaError(f"path has an empty step: {path!r}")
    if any("[" in step or "]" in step for step in steps):
        raise DeltaError(f"array indexing is not supported in a recorded path: {path!r}")
    return tuple(steps)


def _descend(document: Any, steps: tuple[str, ...], path: str) -> Any:
    cursor = document
    for step in steps:
        if not isinstance(cursor, dict):
            raise DeltaError(f"path {path!r} descends into a non-object")
        if step not in cursor:
            raise DeltaError(f"path {path!r} refers to a missing member {step!r}")
        cursor = cursor[step]
    return cursor


def apply_delta(before: Any, changes: list[dict[str, Any]]) -> Any:
    """Return a new document with `changes` applied to `before`.

    Each change is checked against the document it claims to modify: a
    `replace` whose `before` does not match what is actually there is an
    error, not something to overwrite silently.
    """
    if not isinstance(changes, list):
        raise DeltaError("delta must be a list")
    document = copy.deepcopy(before)
    for index, change in enumerate(changes):
        if not isinstance(change, dict):
            raise DeltaError(f"delta entry {index} is not an object")
        operation = change.get("op")
        if operation not in _OPERATIONS:
            raise DeltaError(f"delta entry {index} has unknown op {operation!r}")
        raw_path = change.get("path")
        steps = parse_path(raw_path)

        if steps == ():
            if operation != "replace":
                raise DeltaError(f"delta entry {index} cannot {operation} the root")
            if document != change.get("before"):
                raise DeltaError(f"delta entry {index} root before-value does not match")
            document = copy.deepcopy(change.get("after"))
            continue

        parent = _descend(document, steps[:-1], raw_path)
        leaf = steps[-1]
        if not isinstance(parent, dict):
            raise DeltaError(f"path {raw_path!r} has a non-object parent")

        if operation == "add":
            if leaf in parent:
                raise DeltaError(f"delta entry {index} adds an existing member {raw_path!r}")
            parent[leaf] = copy.deepcopy(change.get("after"))
        elif operation == "remove":
            if leaf not in parent:
                raise DeltaError(f"delta entry {index} removes a missing member {raw_path!r}")
            if parent[leaf] != change.get("before"):
                raise DeltaError(f"delta entry {index} before-value does not match at {raw_path!r}")
            del parent[leaf]
        else:
            if leaf not in parent:
                raise DeltaError(f"delta entry {index} replaces a missing member {raw_path!r}")
            if parent[leaf] != change.get("before"):
                raise DeltaError(f"delta entry {index} before-value does not match at {raw_path!r}")
            parent[leaf] = copy.deepcopy(change.get("after"))
    return document
