"""Reshapes dashboard_data.json (already produced by export_dashboard_data.py)
into flat CSV files — the point is a format anyone (a person in a spreadsheet,
or another AI reading plain text) can open without knowing the JSON schema."""
import csv
import json

with open("dashboard_data.json", encoding="utf-8") as f:
    DATA = json.load(f)


def write_csv(path: str, header: list[str], rows: list[list]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def export_companies() -> None:
    rows = []
    for c in DATA["companies"]:
        for row in c["ticks"]:
            rows.append([
                row["tick"], c["name"], c["display_name"], c["archetype"], c["archetype_kr"],
                row["capital"], row["tech"], row["legitimacy"], row["coercion"],
                row["currency_value"], row["state"],
            ])
    write_csv(
        "companies_timeseries.csv",
        ["tick", "name", "display_name", "archetype", "archetype_kr",
         "capital", "tech", "legitimacy", "coercion", "currency_value", "state"],
        rows,
    )


def export_individuals() -> None:
    rows = []
    for i in DATA["individuals"]:
        for row in i["ticks"]:
            rows.append([row["tick"], i["name"], i["display_name"], i["archetype_kr"], row["capital"], row["tech"]])
    write_csv("individuals_timeseries.csv", ["tick", "name", "display_name", "archetype_kr", "capital", "tech"], rows)


def export_vigilantes() -> None:
    rows = []
    for v in DATA["vigilantes"]:
        for row in v["ticks"]:
            rows.append([row["tick"], v["name"], v["display_name"], v["faction_kr"], row["capital"]])
    write_csv("vigilantes_timeseries.csv", ["tick", "name", "display_name", "faction_kr", "capital"], rows)


def export_events() -> None:
    summary_rows, espionage_rows, wmd_rows = [], [], []
    for e in DATA["events"]:
        summary_rows.append([e["tick"], e["trades_proceeded"], e["trades_refused"], len(e["espionage"]), len(e["wmd"])])
        for ev in e["espionage"]:
            espionage_rows.append([e["tick"], ev["actor"], ev["target"], ev["success"], ev["detected"]])
        for w in e["wmd"]:
            wmd_rows.append([e["tick"], w["company"], w["leaked"], w["leak_probability"]])

    write_csv("events_summary.csv", ["tick", "trades_proceeded", "trades_refused", "espionage_count", "wmd_attempt_count"], summary_rows)
    write_csv("espionage_events.csv", ["tick", "actor", "target", "success", "detected"], espionage_rows)
    write_csv("wmd_attempts.csv", ["tick", "company", "leaked", "leak_probability"], wmd_rows)


def export_experiments() -> None:
    emo = DATA["experiments"]["emotionless_ab"]
    rows = [[t, emo["treatment_cumulative"][t], emo["control_cumulative"][t]] for t in range(emo["ticks"])]
    write_csv("experiment_emotionless_ab.csv", ["tick", "treatment_cumulative_trades", "control_cumulative_trades"], rows)

    hive = DATA["experiments"]["hive_mind_shock"]
    rows = [
        [t, hive["hive_legitimacy"][t], hive["ordinary_legitimacy"][t], t == hive["shock_tick"]]
        for t in range(len(hive["hive_legitimacy"]))
    ]
    write_csv("experiment_hive_mind_shock.csv", ["tick", "hive_mind_legitimacy", "ordinary_legitimacy", "is_shock_tick"], rows)


if __name__ == "__main__":
    export_companies()
    export_individuals()
    export_vigilantes()
    export_events()
    export_experiments()
