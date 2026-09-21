"""Live one world with a saved brain and write down every slot for the replay page (engine/brain/record.py).

  python -m tools.record_world --brain A --genome runs/evolve_20260916_A_readapt/best_gen172.pt --world 5001 --out runs/replay_A172_5001.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import torch
from torch.nn.utils import vector_to_parameters

from engine.brain import brains, evolve, record


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brain", default="A", choices=["A", "B", "C", "D", "random"])
    parser.add_argument("--genome", default=None)
    parser.add_argument("--no-learn", action="store_true")
    parser.add_argument("--world", type=int, default=5001)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--per-camp", type=int, default=5)
    parser.add_argument("--out", required=True)
    parser.add_argument("--html", default=None, help="also write the replay page with the record inside it")
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    brain = brains.make(args.brain, 0, learns=not args.no_learn)
    if args.genome:
        vector_to_parameters(evolve.load_genome(brain, Path(args.genome)), brain.parameters())
    data = record.run(brain, args.world, args.days, args.per_camp, energy=True, wildlife=True, puddles=True, plants=True,
                      sky=True, graded=True, animals=True, sleep_switch=True)
    data["meta"].update(brain=args.brain, genome=args.genome)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    Path(args.out).write_text(text, encoding="utf-8")
    if args.html:
        page = (Path(__file__).parent / "replay_viewer.html").read_text(encoding="utf-8")
        Path(args.html).write_text(page.replace("__REPLAY_DATA__", text.replace("</", "<\\/")), encoding="utf-8")
    print(f"days {data['meta']['days_lived']} lifespan {data['meta']['lifespan']} frames {len(data['frames'])} "
          f"size {len(text) / 1e6:.2f} MB deaths {dict(Counter(d['cause'] for d in data['deaths']))}")
    return data


if __name__ == "__main__":
    main()
