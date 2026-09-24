"""A-Numeric VM: the reference meaning of A's arithmetic.

docs/current/A_NUMERIC_EXECUTION_STACK_V1.md. Not an executor of worlds --
executors (C++, CUDA, ...) are judged against it.
"""
from .profiles import Exact, FixedPoint, IEEE64Strict, VMHalt
from .vm import OPCODES, Branch, Instr, RunResult, VMUnsupported, canonical_sum, dot, run, validate

__all__ = ["Exact", "FixedPoint", "IEEE64Strict", "VMHalt", "OPCODES", "Branch", "Instr", "RunResult",
           "VMUnsupported", "canonical_sum", "dot", "run", "validate"]
