"""v0.1: pure-code engine sanity run — no LLM in the loop yet.

Confirms the formulas from agent_world_design_v1.md section 5 don't diverge
or crash over a run, per the agreed phase-1 step before wiring in Ollama/Qwen3.
"""
import random

from engine.config import SimulationConfig
from engine.entities import Company, CompanyArchetype, Employee, Resources
from engine.simulation import World


def build_world() -> World:
    def employee(name, wage=10, value_alignment=0.6):
        return Employee(
            name=name, wage=wage, expected_wage=10, value_alignment=value_alignment,
            retaliation_cost=0.2, alternative_attractiveness=0.3,
        )

    companies = [
        Company(
            name="EfficiencyCorp", archetype=CompanyArchetype.PURE_EFFICIENCY,
            resources=Resources(capital=50, tech=5, legitimacy=0.6, coercion=0.1),
            employees=[employee("e1"), employee("e2")],
        ),
        Company(
            name="EmotionlessCorp", archetype=CompanyArchetype.EMOTIONLESS,
            resources=Resources(capital=50, tech=5, legitimacy=0.6, coercion=0.1),
            employees=[employee("e3"), employee("e4")],
        ),
        Company(
            name="HiveMindCorp", archetype=CompanyArchetype.HIVE_MIND,
            resources=Resources(capital=50, tech=5, legitimacy=0.6, coercion=0.1),
            employees=[employee("e5"), employee("e6")],
        ),
        Company(
            name="DoomCorp", archetype=CompanyArchetype.DOOMSAYER,
            resources=Resources(capital=30, tech=8, legitimacy=0.2, coercion=0.6),
            employees=[employee("e7", value_alignment=0.9), employee("e8", value_alignment=0.1)],
        ),
        Company(
            name="CoordinatorCorp", archetype=CompanyArchetype.SAFETY_COORDINATOR,
            resources=Resources(capital=10, tech=3, legitimacy=0.9, coercion=0.0),
            employees=[employee("e9", value_alignment=0.95)],
        ),
    ]
    return World(companies=companies, config=SimulationConfig(), rng=random.Random(7))


def main(ticks: int = 30) -> None:
    world = build_world()
    for tick in world.run(ticks):
        pass  # history accumulates in world.history

    print(f"{'tick':>4} " + " ".join(f"{c.name:>16}" for c in world.companies))
    for tick in world.history:
        row = [f"{tick.index:>4}"]
        for c in world.companies:
            state = tick.company_states[c.name].name
            value = tick.currency_values[c.name]
            row.append(f"{state:>8}/{value:6.2f}")
        print(" ".join(row))

    print("\nfinal resources:")
    for c in world.companies:
        r = c.resources
        print(
            f"  {c.name:<16} alive={c.alive!s:<5} isolated={c.isolated!s:<5} "
            f"capital={r.capital:7.2f} tech={r.tech:6.2f} legitimacy={r.legitimacy:5.2f}"
        )


if __name__ == "__main__":
    main()
