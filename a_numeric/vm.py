"""A-Numeric VM, stage 0 (docs/current/A_NUMERIC_EXECUTION_STACK_V1.md, section 3).

A small, slow, executable definition of what A's arithmetic means. It runs
straight-line programs over named registers under one number profile.

What is deliberately ABSENT (section 2: forbid by absence, not by detection):
no instruction reads a label or identity, draws a random number, reads a clock
or a thread index, or switches overflow checking off. Register names are only
addresses; no instruction can observe them.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from fractions import Fraction

from .profiles import VMHalt

OPCODES = frozenset({"CONST", "ADD", "SUB", "MUL", "DIV", "NEG", "ABS", "SQRT", "CMP", "SUM", "DOT"})
_BINARY = {"ADD": "add", "SUB": "sub", "MUL": "mul", "DIV": "div"}
_UNARY = {"NEG": "neg", "ABS": "abs", "SQRT": "sqrt"}
# capability each opcode needs from the profile (SUM and DOT are built from ADD/MUL)
_NEEDS = {"CONST": set(), "SUM": {"ADD"}, "DOT": {"ADD", "MUL"}}


class VMUnsupported(Exception):
    """Rejected before execution: the program needs an operation the profile lacks."""


@dataclass(frozen=True)
class Instr:
    op: str
    dst: str | None
    args: tuple


@dataclass(frozen=True)
class Branch:
    """A comparison whose outcome could steer causality later: the exact margin
    |a - b| is kept so the branch audit can ask whether rounding decided it."""
    pc: int
    result: int
    margin: Fraction


@dataclass
class RunResult:
    profile: str
    registers: dict
    branches: list = field(default_factory=list)
    halt: tuple | None = None            # (pc, reason) -- a halt is a canonical result
    op_count: dict = field(default_factory=dict)

    def canonical(self) -> dict:
        return {"profile": self.profile, "registers": dict(sorted(self.registers.items())),
                "branches": [[b.pc, b.result, f"{b.margin.numerator}/{b.margin.denominator}"] for b in self.branches],
                "halt": list(self.halt) if self.halt else None}

    def digest(self) -> str:
        text = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode()).hexdigest()


def validate(program, profile) -> None:
    for pc, ins in enumerate(program):
        if not isinstance(ins, Instr) or ins.op not in OPCODES:
            raise VMUnsupported(f"pc {pc}: unknown instruction {ins!r}")
        need = _NEEDS.get(ins.op, {ins.op})
        missing = need - profile.capabilities
        if missing:
            raise VMUnsupported(f"pc {pc}: {ins.op} needs {sorted(missing)}, {profile.name} lacks it")


def canonical_sum(profile, values):
    """Leaves sorted by value (never by name or position), then a fixed pairwise
    tree: (0+1), (2+3), ...; an odd last element moves up unchanged."""
    if not values:
        return profile.from_exact(0)
    level = sorted(values, key=profile.sort_key)
    while len(level) > 1:
        nxt = [profile.add(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def dot(profile, xs, ys):
    """Fixed left fold over the axis index (axes are coordinates, not labels)."""
    if len(xs) != len(ys) or not xs:
        raise VMUnsupported("DOT needs two equal, non-empty vectors")
    acc = profile.mul(xs[0], ys[0])
    for x, y in zip(xs[1:], ys[1:]):
        acc = profile.add(acc, profile.mul(x, y))
    return acc


def run(program, profile, inputs=None) -> RunResult:
    validate(program, profile)
    regs = dict(inputs or {})
    result = RunResult(profile.name, {})
    counts: dict = {}
    for pc, ins in enumerate(program):
        counts[ins.op] = counts.get(ins.op, 0) + 1
        try:
            if ins.op == "CONST":
                regs[ins.dst] = profile.from_exact(ins.args[0])
            elif ins.op in _BINARY:
                regs[ins.dst] = getattr(profile, _BINARY[ins.op])(regs[ins.args[0]], regs[ins.args[1]])
            elif ins.op in _UNARY:
                regs[ins.dst] = getattr(profile, _UNARY[ins.op])(regs[ins.args[0]])
            elif ins.op == "SUM":
                regs[ins.dst] = canonical_sum(profile, [regs[a] for a in ins.args])
            elif ins.op == "DOT":
                xs, ys = ins.args
                regs[ins.dst] = dot(profile, [regs[a] for a in xs], [regs[a] for a in ys])
            elif ins.op == "CMP":
                a, b = regs[ins.args[0]], regs[ins.args[1]]
                margin = abs(profile.to_exact(a) - profile.to_exact(b))
                result.branches.append(Branch(pc, profile.cmp(a, b), margin))
        except VMHalt as halt:
            result.halt = (pc, halt.reason)
            break
    result.registers = {k: profile.encode(v) for k, v in regs.items()}
    result.op_count = counts
    return result
