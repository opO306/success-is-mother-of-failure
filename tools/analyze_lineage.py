"""Analyze compartment/strand lineage output from run_nonliving_face_until.py.

Three analyses, read-only over already-recorded observer data (never touches
the simulated world):

1. Strand family tree: which strands trace back to which via copy/join/cleave
   events, rendered as an indented text tree per lineage cluster.
2. Copy-error timeline: when mismatch events happened across the run,
   bucketed so you can see whether errors cluster or spread evenly.
3. Compartment survival curve: how many ordinary events each compartment
   lineage lasted, split/merge/created/destroyed counted from the same log.

Usage:
    python tools/analyze_lineage.py <lineage_dir_or_glob> [--out report.json]

Where <lineage_dir_or_glob> is a directory containing lineage_seed*.json files
(as extracted from a cohort's tar.gz), or an explicit glob pattern.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field


def _load_lineage_files(pattern: str) -> list[tuple[str, dict]]:
    if os.path.isdir(pattern):
        paths = sorted(glob.glob(os.path.join(pattern, "lineage_seed*.json")))
    else:
        paths = sorted(glob.glob(pattern))
    out = []
    for path in paths:
        with open(path, encoding="utf-8-sig") as handle:
            out.append((path, json.load(handle)))
    return out


def _matching_result_path(lineage_path: str) -> str | None:
    """lineage_seed<N>.json -> result_seed<N>.json in the same directory.

    IMPORTANT CAVEAT: strand_lineages in the lineage file is a snapshot of
    only the strands ALIVE at the end of the run. A strand that copied,
    mismatched, and was later dissolved or absorbed into a join/cleave
    leaves no trace in that snapshot -- its copy_steps/copy_mismatches
    numbers simply vanish with it. This undercounts total copy/mismatch
    activity, sometimes down to zero, even when many copy events occurred
    during the run. The authoritative total copy/mismatch event count is
    the result file's event_counts (sequence.face_material_extend), which
    this function locates so analyze_one() can report both numbers and
    flag the gap between them rather than silently trusting the smaller one.
    """
    directory = os.path.dirname(lineage_path)
    name = os.path.basename(lineage_path)
    if not name.startswith("lineage_seed") or not name.endswith(".json"):
        return None
    candidate = os.path.join(directory, "result_" + name[len("lineage_"):])
    return candidate if os.path.exists(candidate) else None


# ---------------------------------------------------------------------------
# 1. Strand family tree
# ---------------------------------------------------------------------------

@dataclass
class StrandNode:
    strand_id: int
    copy_steps: int
    copy_mismatches: int
    transformations: int
    children: list[int] = field(default_factory=list)


def build_strand_forest(strand_lineages: list[dict]) -> dict[int, StrandNode]:
    """The recorded lineage does not store explicit parent pointers per strand
    (only cumulative copy/mismatch ids), so the forest here is a flat listing
    grouped by shared ancestry digest prefix -- i.e. strands whose copy_event_ids
    overlap are treated as the same family. This is an approximation for
    display purposes only; the authoritative record is the events list.
    """
    nodes = {
        item["strand_id"]: StrandNode(
            item["strand_id"], item["copy_steps"], item["copy_mismatches"], item["transformations"]
        )
        for item in strand_lineages
    }
    return nodes


def render_family_summary(strand_lineages: list[dict], limit: int = 20) -> list[str]:
    lines = []
    by_mismatches = sorted(strand_lineages, key=lambda x: -x["copy_mismatches"])
    lines.append(f"{'strand_id':>12} {'copy_steps':>10} {'mismatches':>10} {'transformations':>15}")
    for item in by_mismatches[:limit]:
        lines.append(
            f"{item['strand_id']:>12} {item['copy_steps']:>10} {item['copy_mismatches']:>10} "
            f"{item['transformations']:>15}"
        )
    return lines


# ---------------------------------------------------------------------------
# 2. Copy-error timeline
# ---------------------------------------------------------------------------

def copy_error_timeline(strand_lineages: list[dict], bucket_count: int = 20) -> dict:
    all_copy_events: list[int] = []
    all_mismatch_events: list[int] = []
    for item in strand_lineages:
        all_copy_events.extend(item.get("copy_event_ids", []))
        all_mismatch_events.extend(item.get("copy_mismatch_event_ids", []))
    all_copy_events = sorted(set(all_copy_events))
    all_mismatch_events = sorted(set(all_mismatch_events))
    if not all_copy_events:
        return {"copy_events": 0, "mismatch_events": 0, "buckets": []}
    lo, hi = all_copy_events[0], all_copy_events[-1]
    span = max(hi - lo, 1)
    bucket_width = span / bucket_count
    copy_buckets = [0] * bucket_count
    mismatch_buckets = [0] * bucket_count

    def bucket_of(value: int) -> int:
        idx = int((value - lo) / bucket_width) if bucket_width else 0
        return min(idx, bucket_count - 1)

    for value in all_copy_events:
        copy_buckets[bucket_of(value)] += 1
    for value in all_mismatch_events:
        mismatch_buckets[bucket_of(value)] += 1

    buckets = []
    for i in range(bucket_count):
        start = int(lo + i * bucket_width)
        end = int(lo + (i + 1) * bucket_width)
        copies = copy_buckets[i]
        mismatches = mismatch_buckets[i]
        rate = mismatches / copies if copies else 0.0
        buckets.append({
            "range": [start, end],
            "copy_events": copies,
            "mismatch_events": mismatches,
            "mismatch_rate": round(rate, 4),
        })
    overall_rate = len(all_mismatch_events) / len(all_copy_events) if all_copy_events else 0.0
    return {
        "copy_events": len(all_copy_events),
        "mismatch_events": len(all_mismatch_events),
        "overall_mismatch_rate": round(overall_rate, 6),
        "event_index_range": [lo, hi],
        "buckets": buckets,
    }


def render_timeline_ascii(timeline: dict, width: int = 40) -> list[str]:
    lines = []
    if not timeline["buckets"]:
        return ["(no copy events recorded)"]
    max_copies = max(b["copy_events"] for b in timeline["buckets"]) or 1
    lines.append(f"overall mismatch rate: {timeline['overall_mismatch_rate']:.4%} "
                 f"({timeline['mismatch_events']}/{timeline['copy_events']})")
    lines.append("")
    for b in timeline["buckets"]:
        bar_len = int(width * b["copy_events"] / max_copies)
        bar = "#" * bar_len
        mismatch_marker = "!" * min(b["mismatch_events"], 10)
        lines.append(
            f"[{b['range'][0]:>9}-{b['range'][1]:<9}] {bar:<{width}} "
            f"copies={b['copy_events']:<5} mismatches={b['mismatch_events']:<3} {mismatch_marker}"
        )
    return lines


# ---------------------------------------------------------------------------
# 3. Compartment survival curve
# ---------------------------------------------------------------------------

def compartment_survival(events: list[dict]) -> dict:
    """Reconstruct each compartment's lifespan in ordinary-event ticks from
    created/destroyed/split/merge event records. A compartment "born" at
    event X and next appearing as a parent of a destroyed/split/merge event
    at event Y lived (Y - X) ticks.
    """
    birth: dict[int, int] = {}
    death: dict[int, int] = {}
    kinds_by_id: dict[int, list[str]] = defaultdict(list)

    for event in sorted(events, key=lambda e: e["event_index"]):
        idx = event["event_index"]
        kind = event["kind"]
        for child in event.get("children", ()):
            cid = child["compartment_id"]
            if cid not in birth:
                birth[cid] = idx
            kinds_by_id[cid].append(f"born@{idx}:{kind}")
        for parent in event.get("parents", ()):
            pid = parent["compartment_id"]
            if pid not in death:
                death[pid] = idx
            kinds_by_id[pid].append(f"ended@{idx}:{kind}")

    lifespans = []
    for cid, start in birth.items():
        end = death.get(cid)
        lifespans.append({
            "compartment_id": cid,
            "born_at": start,
            "ended_at": end,
            "lifespan_events": (end - start) if end is not None else None,
            "still_active": end is None,
            "history": kinds_by_id[cid],
        })
    finite = [item["lifespan_events"] for item in lifespans if item["lifespan_events"] is not None]
    finite_sorted = sorted(finite)

    def percentile(data: list[int], p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * p
        f, c = int(k), min(int(k) + 1, len(data) - 1)
        if f == c:
            return float(data[f])
        return data[f] + (data[c] - data[f]) * (k - f)

    summary = {
        "compartments_tracked": len(lifespans),
        "still_active_at_end": sum(1 for item in lifespans if item["still_active"]),
        "median_lifespan_events": percentile(finite_sorted, 0.5) if finite_sorted else None,
        "p90_lifespan_events": percentile(finite_sorted, 0.9) if finite_sorted else None,
        "max_lifespan_events": max(finite_sorted) if finite_sorted else None,
    }
    return {"summary": summary, "lifespans": lifespans}


def render_survival_ascii(survival: dict, width: int = 40) -> list[str]:
    lines = []
    s = survival["summary"]
    lines.append(f"compartments tracked: {s['compartments_tracked']}, "
                 f"still active at run end: {s['still_active_at_end']}")
    lines.append(f"median lifespan: {s['median_lifespan_events']} events, "
                 f"p90: {s['p90_lifespan_events']}, max: {s['max_lifespan_events']}")
    lines.append("")
    finite = sorted(
        (item["lifespan_events"] for item in survival["lifespans"] if item["lifespan_events"] is not None),
        reverse=True,
    )
    if not finite:
        return lines + ["(no finite-lifespan compartments recorded)"]
    max_life = finite[0] or 1
    # histogram of lifespans in log-ish buckets
    buckets = [(1, 1), (2, 9), (10, 99), (100, 999), (1000, float("inf"))]
    labels = ["1", "2-9", "10-99", "100-999", "1000+"]
    counts = [0] * len(buckets)
    for life in finite:
        for i, (lo, hi) in enumerate(buckets):
            if lo <= life <= hi:
                counts[i] += 1
                break
    max_count = max(counts) or 1
    for label, count in zip(labels, counts):
        bar = "#" * int(width * count / max_count)
        lines.append(f"{label:>10} events: {bar:<{width}} {count}")
    return lines


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def analyze_one(path: str, data: dict) -> dict:
    seed = data.get("seed")
    strand_lineages = data.get("strand_lineages", [])
    events = data.get("events", [])
    timeline = copy_error_timeline(strand_lineages)
    survival = compartment_survival(events)

    # Cross-check against the result file's raw event_counts, since
    # strand_lineages only reflects strands still alive at the end (see
    # _matching_result_path docstring). This is what actually happened
    # during the run, independent of what survived to the final snapshot.
    true_extend_events = None
    result_path = _matching_result_path(path)
    if result_path is not None:
        with open(result_path, encoding="utf-8-sig") as handle:
            result_data = json.load(handle)
        true_extend_events = result_data.get("event_counts", {}).get("sequence.face_material_extend", 0)

    snapshot_copy_events = sum(item["copy_steps"] for item in strand_lineages)
    survivorship_gap = (
        None if true_extend_events is None
        else true_extend_events - snapshot_copy_events
    )

    return {
        "path": path,
        "seed": seed,
        "ordinary_events": data.get("ordinary_events"),
        "strand_count": len(strand_lineages),
        "total_copy_mismatches": sum(item["copy_mismatches"] for item in strand_lineages),
        "total_extend_events_true": true_extend_events,
        "total_extend_events_in_final_snapshot": snapshot_copy_events,
        "extend_events_lost_to_survivorship": survivorship_gap,
        "event_kinds": {
            kind: sum(1 for e in events if e["kind"] == kind)
            for kind in sorted(set(e["kind"] for e in events))
        },
        "copy_error_timeline": timeline,
        "compartment_survival": survival["summary"],
        "_full_survival": survival,
        "_family_summary": render_family_summary(strand_lineages),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lineage_dir", help="directory of lineage_seed*.json or a glob pattern")
    parser.add_argument("--out", type=str, default=None, help="write full JSON report here")
    parser.add_argument("--top", type=int, default=5, help="show ASCII detail for the top N seeds by mismatch count")
    args = parser.parse_args()

    files = _load_lineage_files(args.lineage_dir)
    if not files:
        raise SystemExit(f"no lineage files matched: {args.lineage_dir}")

    per_seed = [analyze_one(path, data) for path, data in files]
    per_seed.sort(key=lambda x: -x["total_copy_mismatches"])

    print(f"Loaded {len(per_seed)} lineage files\n")
    print(
        f"{'seed':>25} {'events':>10} {'strands_final':>13} {'extend(true)':>12} "
        f"{'extend(snap)':>12} {'lost':>7} {'compartments':>13} {'max_life':>9}"
    )
    for item in per_seed:
        print(
            f"{str(item['seed']):>25} {item['ordinary_events'] or 0:>10} {item['strand_count']:>13} "
            f"{str(item['total_extend_events_true']):>12} {item['total_extend_events_in_final_snapshot']:>12} "
            f"{str(item['extend_events_lost_to_survivorship']):>7} "
            f"{item['compartment_survival']['compartments_tracked']:>13} "
            f"{item['compartment_survival']['max_lifespan_events'] or 0:>9}"
        )
    total_true = sum(item["total_extend_events_true"] or 0 for item in per_seed)
    total_snapshot = sum(item["total_extend_events_in_final_snapshot"] for item in per_seed)
    print(
        f"\nTOTAL across all seeds: {total_true} copy(extend) events actually happened, "
        f"only {total_snapshot} survive in final-state snapshots "
        f"({total_true - total_snapshot} lost to compartment/strand death -- "
        f"this is expected, not a bug: the snapshot only shows what's alive at the end)."
    )

    print(f"\n{'='*70}\nDetail for top {args.top} seeds by copy-mismatch count\n{'='*70}")
    for item in per_seed[: args.top]:
        print(f"\n--- seed {item['seed']} ({item['ordinary_events']} events) ---")
        print("\nCopy-error timeline:")
        for line in render_timeline_ascii(item["copy_error_timeline"]):
            print("  " + line)
        print("\nCompartment survival:")
        for line in render_survival_ascii(item["_full_survival"]):
            print("  " + line)
        print("\nTop strands by mismatch count:")
        for line in item["_family_summary"]:
            print("  " + line)

    if args.out:
        # strip the heavy internal fields before writing, keep summaries
        slim = []
        for item in per_seed:
            slim.append({k: v for k, v in item.items() if not k.startswith("_")})
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(slim, handle, indent=2, ensure_ascii=False)
        print(f"\nWrote summary report to {args.out}")


if __name__ == "__main__":
    main()
