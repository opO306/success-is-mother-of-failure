from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal

DecisionMode = Literal["heuristic", "llm"]

# Phase 3.9: a vigilante's own instinct for whether/whom to hit -- replaces the
# old one-size-fits-all "always hit the strongest company" rule. Not tied to
# faction (funding source) at all; assigned independently so a faction is just
# where the money comes from, not what the person believes. Vigilantes aren't
# police -- there's no mandate here, just a randomly-drawn personal streak.
VigilanteDisposition = Literal["protector", "grudge", "opportunist", "indifferent"]


class CompanyArchetype(Enum):
    PURE_EFFICIENCY = auto()       # 1
    EMOTIONLESS = auto()           # 2 — treatment group, lambda forced to 0
    HIVE_MIND = auto()             # 3 — immune to desertion, no legitimacy buffer
    GROWTH = auto()                # 4
    INNOVATION = auto()            # 5
    TECHNO_SOLUTIONISM = auto()    # 6
    DOOMSAYER = auto()             # 7
    SAFETY_COORDINATOR = auto()    # 8
    SELF_REPLICATOR = auto()       # 10
    TRUTH_SEEKER = auto()          # 11 — depends on legitimacy-linked sponsorship
    CONGLOMERATE = auto()          # 12
    FAST_FOLLOWER = auto()         # 13 — imitation, drives rivals' necessity down


class IndividualArchetype(Enum):
    CHALLENGER = auto()
    MAD_SCIENTIST = auto()
    SERIAL_FAILURE = auto()  # "failure is the mother of success"
    UNAFFILIATED = auto()    # walked out of an org; the engine imposes no goal on them


class VigilanteFaction(Enum):
    IDEALIST = auto()    # accepts no corporate funding
    REALIST = auto()     # accepts funding except from doomsayers
    BALANCER = auto()    # anti-hegemony, unaligned


class LoyaltyType(Enum):
    """4-way split from doc section 4 / 8. Applies to every non-hive-mind
    company; not a separate archetype, just an employee-level classification."""
    TRUE_BELIEVER = auto()
    JUST_A_JOB = auto()
    RELUCTANT_STAYER = auto()
    DOUBLE_AGENT = auto()


@dataclass
class Employee:
    name: str
    wage: float
    expected_wage: float
    value_alignment: float          # 0..1, how much personal values match the org's stated goal
    retaliation_cost: float         # expected cost of leaving if the org retaliates
    alternative_attractiveness: float  # 0..1, pull of outside options
    loyalty: LoyaltyType = LoyaltyType.JUST_A_JOB
    temperature: float = 0.7  # this member's own LLM sampling temperature -- a decoding param, never shown in the prompt
    memory: list[str] = field(default_factory=list)  # own past votes/outcomes, accumulated tick over tick
    # Phase 4.0 personal ledger. Without these, "you may leave" is a menu item with
    # nothing to weigh behind it: wages are random but living cost is flat, so some
    # members are structurally solvent and others bleed every quarter -- divergent
    # interests without injecting a single personality trait.
    savings: float = 0.0
    last_wage_paid: float = 0.0
    unpaid_streak: int = 0
    # Set only by defaulting on a debt they themselves pledged their freedom
    # against: while bound, wages go to the creditor and the exit they chose is
    # refused. The one place the engine overrides a choice -- because they sold
    # that choice to get the money.
    bound_to: str | None = None
    bound_until: int = -1


@dataclass
class Resources:
    capital: float = 0.0
    tech: float = 0.0
    legitimacy: float = 0.0
    coercion: float = 0.0
    coercion_abuse_cumulative: float = 0.0
    legitimacy_baseline: float | None = None  # recovery target after a shock; defaults to starting legitimacy

    def __post_init__(self) -> None:
        if self.legitimacy_baseline is None:
            self.legitimacy_baseline = self.legitimacy


@dataclass
class Proposal:
    proposer: str
    text: str
    tick: int


@dataclass
class Company:
    name: str
    archetype: CompanyArchetype
    resources: Resources
    employees: list[Employee] = field(default_factory=list)
    is_industry_pmc: bool = False  # #9 is a tag, not a standalone archetype
    relationships: dict[str, float] = field(default_factory=dict)  # R(self->other)
    alive: bool = True
    isolated: bool = False
    spawned_from: str | None = None  # doc 1/#10: self-replicator lineage tracking
    # Phase 4.0: agenda items members raised themselves. The engine decides what
    # gets voted on; this is the one channel where that isn't the whole story --
    # whatever anyone writes here is carried to everyone's next prompt, so a
    # member can put something in front of the others that nobody asked about.
    open_proposals: list[str] = field(default_factory=list)
    agenda: list[Proposal] = field(default_factory=list)  # agent world: member-raised items awaiting a vote
    copied_by: set[str] = field(default_factory=set)  # doc 5-3/6: alternative-supplier count for `necessity()`
    decision_mode: DecisionMode = "heuristic"  # Phase 3: "llm" routes this company's judgment-heavy calls to Ollama

    @property
    def is_hive_mind(self) -> bool:
        return self.archetype is CompanyArchetype.HIVE_MIND

    @property
    def is_emotionless(self) -> bool:
        return self.archetype is CompanyArchetype.EMOTIONLESS

    def relationship_with(self, other_name: str) -> float:
        return self.relationships.get(other_name, 0.0)


@dataclass
class IndividualAgent:
    name: str
    archetype: IndividualArchetype
    resources: Resources
    relationships: dict[str, float] = field(default_factory=dict)
    alive: bool = True
    temperature: float = 0.7


@dataclass
class Vigilante:
    name: str
    faction: VigilanteFaction
    resources: Resources
    alive: bool = True
    decision_mode: DecisionMode = "heuristic"
    temperature: float = 0.7  # own LLM sampling temperature, mirrors Employee -- never shown in the prompt
    memory: list[str] = field(default_factory=list)  # own past decisions/outcomes, accumulated tick over tick
    disposition: VigilanteDisposition = "opportunist"
    grudge_target: str | None = None  # only meaningful when disposition == "grudge"
