"""Build the Danyang/Jecheon land from the SRTM tiles in data/terrain and draw it (design doc 4, new land).

  python -m tools.build_land

Writes data/terrain/danyang_lgm.json (places, water, sites, camps, roads) and data/terrain/danyang_lgm.png.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

from engine.primal import terrain

COLORS = {"강": "#2b6cb0", "초원": "#c9b458", "숲": "#2f7d4a", "산기슭": "#8a6d4b", "언덕": "#7a7a7a",
          "동굴": "#111111", "바위그늘": "#553300", "야영지": "#d9480f"}


def main(argv: list[str] | None = None) -> Path:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(terrain.ROOT / "danyang_lgm.json"))
    args = parser.parse_args(argv)
    dem, top, left, px = terrain.load_dem()
    z = terrain.crop(dem, top, left, px)
    data = terrain.build(z)
    out = Path(args.out)
    terrain.save(data, out)
    kinds = Counter(p["kind"] for p in data["places"])
    watered = sum(1 for p in data["places"] if p["water"])
    slots = Counter(r[2] for r in data["roads"])
    print(f"places {len(data['places'])} kinds {dict(kinds)} with water {watered} roads {len(data['roads'])} slots {dict(slots)}"
          f" lake level {data['lake_level']}")
    south, north, west, east = data["region"]
    gy, gx = np.gradient(z)
    shade = np.clip(0.5 + 0.02 * (gx - gy), 0, 1)
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(shade, cmap="gray", extent=(west, east, south, north))
    where = {p["name"]: p for p in data["places"]}
    for a, b, s in data["roads"]:
        pa, pb = where[a], where[b]
        ax.plot([pa["lon"], pb["lon"]], [pa["lat"], pb["lat"]], color="#444444", lw=0.6 + 0.6 * (s - 1), alpha=0.6)
    for p in data["places"]:
        ax.scatter(p["lon"], p["lat"], s=160 if not p["site"] else 90, c=COLORS.get(p["kind"], "#ffffff"),
                   edgecolors="#1e90ff" if p["water"] else "white", linewidths=2.0, zorder=3, marker="o" if not p["site"] else "s")
        if p["site"]:
            ax.annotate(p["name"], (p["lon"], p["lat"]), xytext=(4, 4), textcoords="offset points", fontsize=8, color="#b00020",
                        fontfamily="Malgun Gothic")
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=k) for k, c in COLORS.items()]
    ax.legend(handles=handles, loc="lower left", fontsize=8, prop={"family": "Malgun Gothic"})
    ax.set_title("Danyang / Jecheon, LGM land (blue ring = water)")
    picture = out.with_suffix(".png")
    fig.savefig(picture, dpi=90, bbox_inches="tight")
    print("wrote", out, picture)
    return out


if __name__ == "__main__":
    main()
