"""Exports one seed's full simulation run + the two headline A/B experiments
to JSON for the dashboard artifact. Uses the real engine (engine/scenarios.py,
engine/batch.py) — no synthetic/placeholder numbers."""
import json

from engine.config import SimulationConfig
from engine.formulas import apply_legitimacy_event
from engine.personas import (
    ARCHETYPE_BLURB_KR,
    ARCHETYPE_LABEL_KR,
    DISPLAY_NAME,
    INDIVIDUAL_LABEL_KR,
    INDIVIDUAL_NAME,
    STATE_KR,
    VIGILANTE_LABEL_KR,
    VIGILANTE_NAME,
)
from engine.scenarios import build_emotionless_ab_pair, build_full_world, build_hive_mind_shock_pair

SEED = 0
TICKS = 40


def export_main_run() -> dict:
    world = build_full_world(seed=SEED)
    companies = {
        c.name: {
            "name": c.name,
            "display_name": DISPLAY_NAME[c.archetype],
            "archetype": c.archetype.name,
            "archetype_kr": ARCHETYPE_LABEL_KR[c.archetype],
            "blurb_kr": ARCHETYPE_BLURB_KR[c.archetype],
            "ticks": [],
        }
        for c in world.companies
    }
    individuals = {
        i.name: {
            "name": i.name, "display_name": INDIVIDUAL_NAME[i.archetype],
            "archetype_kr": INDIVIDUAL_LABEL_KR[i.archetype], "ticks": [],
        }
        for i in world.individuals
    }
    vigilantes = {
        v.name: {
            "name": v.name, "display_name": VIGILANTE_NAME[v.faction],
            "faction_kr": VIGILANTE_LABEL_KR[v.faction], "ticks": [],
        }
        for v in world.vigilantes
    }
    events = []

    for _ in range(TICKS):
        tick_record = world.tick()  # snapshot resources immediately after this tick, not after the whole run
        for c in world.companies:
            entry = companies.get(c.name)
            if entry is None:  # a self-replicator spawned mid-run
                entry = {
                    "name": c.name, "display_name": f"{DISPLAY_NAME[c.archetype]} (분사)",
                    "archetype": c.archetype.name, "archetype_kr": ARCHETYPE_LABEL_KR[c.archetype],
                    "blurb_kr": f"{c.spawned_from}에서 분사", "ticks": [],
                }
                companies[c.name] = entry
            r = c.resources
            entry["ticks"].append({
                "tick": tick_record.index,
                "capital": round(r.capital, 2),
                "tech": round(r.tech, 2),
                "legitimacy": round(r.legitimacy, 3),
                "coercion": round(r.coercion, 2),
                "currency_value": round(tick_record.currency_values.get(c.name, 0.0), 3),
                "state": STATE_KR[tick_record.company_states[c.name]],
            })
        for i in world.individuals:
            individuals[i.name]["ticks"].append({
                "tick": tick_record.index,
                "capital": round(i.resources.capital, 2),
                "tech": round(i.resources.tech, 2),
            })
        for v in world.vigilantes:
            vigilantes[v.name]["ticks"].append({
                "tick": tick_record.index, "capital": round(v.resources.capital, 2),
            })

        events.append({
            "tick": tick_record.index,
            "trades_proceeded": sum(1 for t in tick_record.trades if t.proceeded),
            "trades_refused": sum(1 for t in tick_record.trades if not t.proceeded),
            "espionage": [
                {"actor": e.actor, "target": e.target, "success": e.success, "detected": e.detected}
                for e in tick_record.espionage_events
            ],
            "wmd": [
                {"company": w.company, "leaked": w.leaked, "leak_probability": round(w.leak_probability, 2)}
                for w in tick_record.wmd_attempts
            ],
        })

    return {
        "seed": SEED, "ticks": TICKS,
        "companies": list(companies.values()),
        "individuals": list(individuals.values()),
        "vigilantes": list(vigilantes.values()),
        "events": events,
    }


def export_emotionless_experiment() -> dict:
    world = build_emotionless_ab_pair(seed=SEED, scripted_relationship=-1.0)
    treatment_cum, control_cum = [], []
    t_total = c_total = 0
    for tick_record in world.run(30):
        for trade in tick_record.trades:
            pair = {trade.actor, trade.counterpart}
            if pair == {"Treatment", "Counterpart"} and trade.proceeded:
                t_total += 1
            if pair == {"Control", "Counterpart"} and trade.proceeded:
                c_total += 1
        treatment_cum.append(t_total)
        control_cum.append(c_total)
    return {"ticks": 30, "relationship_value": -1.0, "treatment_cumulative": treatment_cum, "control_cumulative": control_cum}


def export_hive_mind_experiment() -> dict:
    config = SimulationConfig(espionage_attempt_probability=0.0)
    world = build_hive_mind_shock_pair(seed=SEED)
    world.config = config
    hive_series, ord_series = [], []
    by_name = {c.name: c for c in world.companies}
    for _ in range(5):
        world.tick()
        hive_series.append(round(by_name["HiveMind"].resources.legitimacy, 3))
        ord_series.append(round(by_name["Ordinary"].resources.legitimacy, 3))

    apply_legitimacy_event(by_name["HiveMind"], exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=config)
    apply_legitimacy_event(by_name["Ordinary"], exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=config)
    shock_tick = len(hive_series)
    hive_series.append(round(by_name["HiveMind"].resources.legitimacy, 3))
    ord_series.append(round(by_name["Ordinary"].resources.legitimacy, 3))

    for _ in range(20):
        world.tick()
        hive_series.append(round(by_name["HiveMind"].resources.legitimacy, 3))
        ord_series.append(round(by_name["Ordinary"].resources.legitimacy, 3))

    return {"shock_tick": shock_tick, "hive_legitimacy": hive_series, "ordinary_legitimacy": ord_series}


def main() -> None:
    data = {
        "meta": {"seed": SEED, "ticks": TICKS, "note": "engine/heuristics.py 기반 휴리스틱 엔진, LLM 미적용"},
        **export_main_run(),
        "experiments": {
            "emotionless_ab": export_emotionless_experiment(),
            "hive_mind_shock": export_hive_mind_experiment(),
        },
    }
    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))
    print("wrote dashboard_data.json")


if __name__ == "__main__":
    main()
