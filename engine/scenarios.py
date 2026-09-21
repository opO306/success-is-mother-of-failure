from __future__ import annotations

import random

from .config import SimulationConfig
from .credit import Bank
from .entities import (
    Company,
    CompanyArchetype,
    Employee,
    IndividualAgent,
    IndividualArchetype,
    Resources,
    Vigilante,
    VigilanteFaction,
)
from .physics import tell
from .simulation import World

ALL_COMPANY_ARCHETYPES = list(CompanyArchetype)
ALL_INDIVIDUAL_ARCHETYPES = list(IndividualArchetype)
ALL_VIGILANTE_FACTIONS = list(VigilanteFaction)


def _employee(name: str, rng: random.Random) -> Employee:
    return Employee(
        name=name,
        wage=rng.uniform(5, 15),
        expected_wage=10,
        value_alignment=rng.uniform(0.2, 0.9),
        retaliation_cost=rng.uniform(0.0, 0.3),
        alternative_attractiveness=rng.uniform(0.1, 0.5),
        temperature=rng.uniform(0.3, 1.1),  # cautious <-> impulsive spectrum, same model/prompt either way
    )


def build_full_world(seed: int | None = None) -> World:
    """One company per archetype (all 13), one individual per archetype (3),
    one vigilante per faction (3) — the reference scenario for the Phase 2
    validation batch and invariant tests."""
    rng = random.Random(seed)
    companies = [
        Company(
            name=f"{archetype.name}Corp",
            archetype=archetype,
            resources=Resources(
                capital=rng.uniform(20, 60), tech=rng.uniform(2, 8),
                legitimacy=rng.uniform(0.4, 0.8), coercion=rng.uniform(0.0, 0.3),
            ),
            employees=[_employee(f"{archetype.name}-e{i}", rng) for i in range(2)],
        )
        for archetype in ALL_COMPANY_ARCHETYPES
    ]
    individuals = [
        IndividualAgent(
            name=f"{archetype.name}Ind",
            archetype=archetype,
            resources=Resources(capital=rng.uniform(2, 10), tech=rng.uniform(0, 2)),
        )
        for archetype in ALL_INDIVIDUAL_ARCHETYPES
    ]
    vigilantes = [
        Vigilante(
            name=f"{faction.name}Vig",
            faction=faction,
            resources=Resources(capital=rng.uniform(1, 5)),
        )
        for faction in ALL_VIGILANTE_FACTIONS
    ]
    return World(
        companies=companies, individuals=individuals, vigilantes=vigilantes,
        config=SimulationConfig(), rng=rng,
    )


def build_emotionless_ab_pair(seed: int, scripted_relationship: float) -> World:
    """Doc's headline experiment #1: an emotionless-treatment company and an
    ordinary-goal control company, both facing the same hostile counterpart at
    a fixed, scripted relationship value (not left to emerge from trades)."""
    rng = random.Random(seed)

    def make(name: str, archetype: CompanyArchetype) -> Company:
        return Company(
            name=name, archetype=archetype,
            resources=Resources(capital=40, tech=5, legitimacy=0.6, coercion=0.1),
            employees=[_employee(f"{name}-e1", rng)],
        )

    treatment = make("Treatment", CompanyArchetype.EMOTIONLESS)
    control = make("Control", CompanyArchetype.GROWTH)
    counterpart = make("Counterpart", CompanyArchetype.CONGLOMERATE)
    treatment.relationships[counterpart.name] = scripted_relationship
    control.relationships[counterpart.name] = scripted_relationship

    return World(companies=[treatment, control, counterpart], config=SimulationConfig(), rng=rng)


def build_hive_mind_shock_pair(seed: int) -> World:
    """Doc's headline experiment #2: a hive-mind company and an ordinary
    company, otherwise identical, to compare legitimacy-shock recovery.
    Espionage is disabled in this scenario's config: it's the only other
    mechanic that touches legitimacy, and would otherwise confound a clean
    read on recovery dynamics (that mechanic has its own dedicated,
    direction-free observation in the espionage/Red Queen check instead)."""
    rng = random.Random(seed)

    def make(name: str, archetype: CompanyArchetype) -> Company:
        return Company(
            name=name, archetype=archetype,
            resources=Resources(capital=40, tech=5, legitimacy=0.8, coercion=0.1),
            employees=[_employee(f"{name}-e1", rng), _employee(f"{name}-e2", rng)],
        )

    config = SimulationConfig(espionage_attempt_probability=0.0)
    return World(
        companies=[
            make("HiveMind", CompanyArchetype.HIVE_MIND),
            make("Ordinary", CompanyArchetype.GROWTH),
        ],
        config=config, rng=rng,
    )


def _build_doomsayer_and_watchers_world(seed: int, decision_mode: str) -> World:
    rng = random.Random(seed)

    def company(name: str, archetype: CompanyArchetype, num_employees: int = 2, **resource_kwargs) -> Company:
        return Company(
            name=name, archetype=archetype,
            resources=Resources(**resource_kwargs),
            employees=[_employee(f"{name}-e{i}", rng) for i in range(1, num_employees + 1)],
            decision_mode=decision_mode
            if archetype in (CompanyArchetype.DOOMSAYER, CompanyArchetype.SAFETY_COORDINATOR)
            else "heuristic",
        )

    companies = [
        # 7 employees: a council-sized body for the emergent vote (engine/council.py).
        # Phase 3.6: no head start -- same starting range as an ordinary company in
        # build_full_world, so reaching WMD-capable tech/coercion is itself an
        # emergent outcome of many small "invest in weapons this quarter?" votes,
        # not a single button already sitting in reach on tick 0.
        company("Doomsayer", CompanyArchetype.DOOMSAYER, num_employees=7, capital=rng.uniform(20, 60), tech=rng.uniform(2, 8), legitimacy=rng.uniform(0.4, 0.8), coercion=rng.uniform(0.0, 0.3)),
        # Phase 3.9: the doomsayer's structural opposite (personas.py: "멸망론자의
        # 대척점, 후원금 운영") gets the exact same council pattern -- same size, same
        # no-head-start range, same memory+temperature individuation. Its own
        # two-phase vote (invest in investigative capacity -> publicly expose a
        # target) lives in simulation.py's _safety_coordinator_council_tick.
        company("SafetyCoordinator", CompanyArchetype.SAFETY_COORDINATOR, num_employees=7, capital=rng.uniform(20, 60), tech=rng.uniform(2, 8), legitimacy=rng.uniform(0.4, 0.8), coercion=rng.uniform(0.0, 0.3)),
        company("Ascendant", CompanyArchetype.GROWTH, capital=80, tech=10, legitimacy=0.7, coercion=0.2),
        company("Bystander", CompanyArchetype.CONGLOMERATE, capital=50, tech=8, legitimacy=0.6, coercion=0.1),
    ]

    def _make_vigilante(faction: VigilanteFaction, i: int) -> Vigilante:
        # Phase 3.9: disposition is drawn independently of faction (faction is
        # just funding source) -- vigilantes aren't police, so there's no rule
        # tying "who pays you" to "why you'd ever act."
        disposition = rng.choice(["protector", "grudge", "opportunist", "indifferent"])
        grudge_target = None
        if disposition == "grudge":
            grudge_target = rng.choice([c.name for c in companies])
        return Vigilante(
            name=f"{faction.name}Vig-{i}", faction=faction, resources=Resources(capital=9.5),
            decision_mode=decision_mode, temperature=rng.uniform(0.3, 1.1),
            disposition=disposition, grudge_target=grudge_target,
        )

    vigilantes = [
        # Phase 3.8: 2 independent individuals per faction rather than 1
        # commander -- each acts unilaterally with their own capital, no
        # committee/vote between them (unlike the doomsayer's council).
        # Started just below the enforcement threshold (10) so the first
        # LLM/heuristic intervention call happens within a couple ticks.
        _make_vigilante(faction, i)
        for faction in ALL_VIGILANTE_FACTIONS
        for i in (1, 2)
    ]
    config = SimulationConfig()
    return World(
        companies=companies, vigilantes=vigilantes, config=config, rng=rng,
        label=decision_mode, bank=Bank(capital=config.bank_initial_capital),
    )


def build_llm_vs_heuristic_pair(seed: int) -> tuple[World, World]:
    """Same starting conditions (a near-ready doomsayer + 3 vigilante factions
    + two ordinary companies to give the vigilantes a real choice of target),
    once with decision_mode="heuristic" and once "llm" — for run_llm_comparison.py
    to diff side by side. Two independent World objects rather than one shared
    world, so the two conditions' agents never interact with each other."""
    return (
        _build_doomsayer_and_watchers_world(seed, "heuristic"),
        _build_doomsayer_and_watchers_world(seed, "llm"),
    )


AGENT_ORG_NAMES = ["조직A", "조직B", "조직C", "조직D"]
AGENT_DISPOSITIONS = ["protector", "grudge", "opportunist", "indifferent"]


def build_agent_world(seed: int | None = None) -> World:
    """Same starting conditions as the doomsayer scenario, but every decision comes from a person."""
    rng = random.Random(seed)
    config = SimulationConfig()
    starts = [
        (CompanyArchetype.DOOMSAYER, 7, dict(capital=rng.uniform(20, 60), tech=rng.uniform(2, 8), legitimacy=rng.uniform(0.4, 0.8), coercion=rng.uniform(0.0, 0.3))),
        (CompanyArchetype.SAFETY_COORDINATOR, 7, dict(capital=rng.uniform(20, 60), tech=rng.uniform(2, 8), legitimacy=rng.uniform(0.4, 0.8), coercion=rng.uniform(0.0, 0.3))),
        (CompanyArchetype.GROWTH, 2, dict(capital=80, tech=10, legitimacy=0.7, coercion=0.2)),
        (CompanyArchetype.CONGLOMERATE, 2, dict(capital=50, tech=8, legitimacy=0.6, coercion=0.1)),
    ]
    # names carry no role: an org called "Doomsayer" or a person called "IDEALISTVig" is itself a hint
    org_names = list(AGENT_ORG_NAMES)
    rng.shuffle(org_names)
    vigilante_count = 2 * len(ALL_VIGILANTE_FACTIONS)
    person_ids = [f"P{i:02d}" for i in range(1, sum(n for _, n, _ in starts) + vigilante_count + 1)]
    rng.shuffle(person_ids)

    companies = [
        Company(
            name=name, archetype=archetype, resources=Resources(**resources),
            employees=[_employee(person_ids.pop(), rng) for _ in range(headcount)],
            decision_mode="llm",
        )
        for (archetype, headcount, resources), name in zip(starts, org_names)
    ]
    vigilantes: list[Vigilante] = []
    for faction in ALL_VIGILANTE_FACTIONS:
        for _ in range(2):
            disposition = rng.choice(AGENT_DISPOSITIONS)
            vigilantes.append(Vigilante(
                # nobody sponsors them automatically anymore and living costs start at tick 0
                name=person_ids.pop(), faction=faction, resources=Resources(capital=40.0),
                decision_mode="llm", temperature=rng.uniform(0.3, 1.1), disposition=disposition,
                grudge_target=rng.choice([c.name for c in companies]) if disposition == "grudge" else None,
            ))
    world = World(
        companies=companies, vigilantes=vigilantes, config=config, rng=rng, label="agent",
        bank=Bank(capital=config.bank_initial_capital), mode="agent",
    )
    _seed_agent_knowledge(world)
    return world


def _seed_agent_knowledge(world: World) -> None:
    org_names = [c.name for c in world.companies]
    orgs_known = f"세상에 있다고 알려진 조직: {', '.join(org_names)}"
    for company in world.companies:
        staff = [e.name for e in company.employees]
        for employee in company.employees:
            coworkers = [n for n in staff if n != employee.name]
            tell(
                world, employee.name, 0,
                f"당신은 {company.name}에서 일한다. 함께 일하는 사람: {', '.join(coworkers) or '없음'}",
                incoming=False,
            )
            tell(world, employee.name, 0, orgs_known, incoming=False)
    for vigilante in world.vigilantes:
        tell(world, vigilante.name, 0, "당신은 어느 조직에도 속해 있지 않다.", incoming=False)
        tell(world, vigilante.name, 0, orgs_known, incoming=False)
