"""Did the physics follow the rules the world declared?

Conservation says nothing moved that should not have existed. This says
nothing moved by a route the rules forbid. Nothing here imports from
`engine`. See `README.md`.
"""
from .checker import (
    ComplianceFinding,
    ComplianceReport,
    check_stage,
    check_trace_compliance,
)
from .field import FieldError, FieldView, changed_points, read_field
from .rules import RuleError, WorldRules, read_rules

__all__ = [
    "ComplianceFinding",
    "ComplianceReport",
    "FieldError",
    "FieldView",
    "RuleError",
    "WorldRules",
    "changed_points",
    "check_stage",
    "check_trace_compliance",
    "read_field",
    "read_rules",
]
