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
from .particles import (
    BondRule,
    ParticleRuleError,
    ParticleRules,
    ParticleView,
    check_particle_transition,
    read_particle_rules,
    read_particles,
)
from .rules import RuleError, WorldRules, read_rules

__all__ = [
    "BondRule",
    "ComplianceFinding",
    "ComplianceReport",
    "FieldError",
    "FieldView",
    "ParticleRuleError",
    "ParticleRules",
    "ParticleView",
    "RuleError",
    "WorldRules",
    "changed_points",
    "check_particle_transition",
    "check_stage",
    "check_trace_compliance",
    "read_field",
    "read_particle_rules",
    "read_particles",
    "read_rules",
]
