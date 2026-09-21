"""Land made from the real ground (design doc 4, new land): the upper South Han River around Danyang and Jecheon, where
Paleolithic people lived at Geumgul, Jeommal cave, the Sangsi rock shelter and Suyanggae, as the Last Glacial Maximum
left it (about 21,000 years ago). This module only reads the ground and writes it down; scenario.py turns the result
into lands with what grows and walks on them.

From SRTM 1-arc-second elevation (data/terrain), the region is cut into places about a half-day's walk across. Each place
takes its kind from its own ground: gentle ground is open grassland (glacial pollen in central Korea shows conifers with
dry-land herbs, a cold and dry climate), middling slopes forest, steep slopes mountain foot, the steepest ground rocky
hills. Rivers come from where water gathers: flow accumulation over the elevation, so the South Han runs where the ground
sends it. A place a big river runs through is river; one a stream runs through keeps its kind and has water. The known
Paleolithic sites become places of their own, joined to the place they sit in: the caves as caves, the rock shelter half
roofed, Suyanggae as the riverside terrace it is.

Roads join neighbouring places. How long a walk takes follows Tobler's hiking function over the ground between them
(6·exp(-3.5·|slope + 0.05|) km/h), a big river in between costs a slot more to cross, and a slot is four hours.

Known simplifications, written down so they are not mistaken for findings:
- Chungju Lake is a 1985 reservoir. Its flat surface is read as the valley floor with the river in it.
- The site coordinates of Sangsi are known only to the arc-minute (37°04′N 128°07′E).
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "terrain"
REGION = (36.85, 37.25, 128.05, 128.55)          # south, north, west, east
CELL_KM = 6.0
SLOT_HOURS = 4.0
POOL = 5                                         # 30 m pixels pooled into 150 m for water flow
BIG_RIVER_KM2 = 300.0                            # catchment that makes a river rather than a stream
STREAM_KM2 = 8.0
SITE_WATER_KM = 1.0                              # how far from a site its people would walk for water without it being a trip
SITE_STREAM_KM2 = 2.0                            # a brook that runs through the year
# The Olduvai basin on the eastern Serengeti plain (2026-09-17): the woodland-and-grass mosaic where our own line lived
# and where the oldest stone tools come from. Sites are the gorge itself (Olduvai, FLK), the Laetoli footprint beds and
# the lake at Ndutu; the two DEM tiles are S03E035 and S04E035.
OLDUVAI = (-3.30, -2.80, 35.10, 35.70)
OLDUVAI_TILES = ("S03E035", "S04E035")
OLDUVAI_TOP, OLDUVAI_LEFT = -2.0, 35.0
OLDUVAI_SITES = {
    "올두바이 협곡": (-2.99390, 35.35190, "바위그늘", 0.4),
    "라에톨리": (-3.21670, 35.20000, "야영지", 0.0),
    "은두투 호숫가": (-3.05000, 35.05000, "야영지", 0.0),
}
OLDUVAI_CAMPS = ("올두바이 협곡", "라에톨리", "은두투 호숫가")
SITES = {   # name: (lat, lon, kind, roof); Korean Wikipedia / 한국민족문화대백과사전 coordinates
    "금굴": (36.99639, 128.35750, "동굴", 0.8),
    "점말동굴": (37.19611, 128.22028, "동굴", 0.8),
    "상시 바위그늘": (37.0667, 128.1167, "바위그늘", 0.5),
    "수양개": (36.95889, 128.33194, "야영지", 0.0),
}
CAMPS = ("수양개", "상시 바위그늘", "점말동굴")
KM_PER_DEG_LAT = 111.0


def load_dem(root: Path = ROOT, tiles: tuple[str, str] = ("N37E128", "N36E128"), top: float = 38.0,
             left: float = 128.0) -> tuple[np.ndarray, float, float, float]:
    """Two tiles stacked north over south as one array, with its top latitude, left longitude and degrees per pixel."""
    def tile(name: str) -> np.ndarray:
        raw = gzip.decompress((root / f"{name}.hgt.gz").read_bytes())
        size = int(round((len(raw) / 2) ** 0.5))
        return np.frombuffer(raw, dtype=">i2").reshape(size, size).astype(np.float32)

    upper, lower = tile(tiles[0]), tile(tiles[1])
    return np.vstack([upper[:-1], lower]), top, left, 1.0 / (upper.shape[0] - 1)


def crop(dem: np.ndarray, top: float, left: float, px: float, region=REGION) -> np.ndarray:
    south, north, west, east = region
    r0, r1 = int(round((top - north) / px)), int(round((top - south) / px))
    c0, c1 = int(round((west - left) / px)), int(round((east - left) / px))
    out = dem[r0:r1, c0:c1].copy()
    out[out < -1000] = np.nanmedian(out[out > -1000])
    return out


def pool(z: np.ndarray, k: int) -> np.ndarray:
    rows, cols = z.shape[0] // k, z.shape[1] // k
    return z[: rows * k, : cols * k].reshape(rows, k, cols, k).mean(axis=(1, 3))


def fill_depressions(z: np.ndarray, step: float = 1e-3) -> np.ndarray:
    """Priority-flood (Barnes et al. 2014): raise every pit and flat to the lowest rim it spills over, a hair higher each
    cell inward, so water that runs into a hollow or across a reservoir surface keeps running to the edge. Without it
    the South Han gathered almost nothing: flow stopped at every pit and at the flat of Chungju Lake."""
    import heapq

    rows, cols = z.shape
    filled = z.astype(np.float64).copy()
    seen = np.zeros(z.shape, dtype=bool)
    heap: list[tuple[float, int, int]] = []
    for r in range(rows):
        for c in range(cols):
            if r in (0, rows - 1) or c in (0, cols - 1):
                seen[r, c] = True
                heapq.heappush(heap, (filled[r, c], r, c))
    while heap:
        h, r, c = heapq.heappop(heap)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if (dr or dc) and 0 <= rr < rows and 0 <= cc < cols and not seen[rr, cc]:
                    seen[rr, cc] = True
                    filled[rr, cc] = max(filled[rr, cc], h + step)
                    heapq.heappush(heap, (filled[rr, cc], rr, cc))
    return filled


def flow_accumulation(z: np.ndarray) -> np.ndarray:
    """D8: every cell sends what it gathered to its steepest lower neighbour, highest cells first."""
    rows, cols = z.shape
    acc = np.ones(z.shape, dtype=np.float64)
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for flat in np.argsort(z, axis=None)[::-1]:
        r, c = divmod(int(flat), cols)
        best, target = 0.0, None
        for dr, dc in offsets:
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                drop = (z[r, c] - z[rr, cc]) / (1.4142 if dr and dc else 1.0)
                if drop > best:
                    best, target = drop, (rr, cc)
        if target is not None:
            acc[target] += acc[r, c]
    return acc


def tobler_kmh(slope: float) -> float:
    return 6.0 * math.exp(-3.5 * abs(slope + 0.05))


def walk_hours(z: np.ndarray, pixel_km: tuple[float, float], a: tuple[float, float], b: tuple[float, float], samples: int = 40) -> float:
    """Hours to walk the straight line between two pixel positions (row, col) over the ground."""
    ky, kx = pixel_km
    hours = 0.0
    prev = a
    prev_h = float(z[int(a[0]), int(a[1])])
    for i in range(1, samples + 1):
        t = i / samples
        cur = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        h = float(z[min(z.shape[0] - 1, int(cur[0])), min(z.shape[1] - 1, int(cur[1]))])
        km = math.hypot((cur[0] - prev[0]) * ky, (cur[1] - prev[1]) * kx)
        if km > 0:
            hours += km / tobler_kmh((h - prev_h) / (km * 1000.0))
        prev, prev_h = cur, h
    return hours


def kind_of(slope_deg: float) -> str:
    if slope_deg < 12.0:
        return "초원"
    if slope_deg < 22.0:
        return "숲"
    if slope_deg < 30.0:
        return "산기슭"
    return "언덕"


def build(z: np.ndarray, region=REGION, cell_km: float = CELL_KM, sites: dict = SITES, camps=CAMPS) -> dict:
    """Places, their ground and water, sites, camps and roads, as plain data."""
    south, north, west, east = region
    mid_lat = (south + north) / 2
    ky = (north - south) * KM_PER_DEG_LAT / z.shape[0]
    kx = (east - west) * KM_PER_DEG_LAT * math.cos(math.radians(mid_lat)) / z.shape[1]
    gy, gx = np.gradient(z, ky * 1000.0, kx * 1000.0)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    heights, counts = np.unique(np.round(z).astype(int), return_counts=True)
    lake_level = int(heights[np.argmax(counts)]) if counts.max() > 0.005 * z.size else None
    lake = np.abs(z - lake_level) <= 1.0 if lake_level is not None else np.zeros(z.shape, bool)
    pooled = fill_depressions(pool(z, POOL))
    acc_km2 = flow_accumulation(pooled) * (ky * POOL) * (kx * POOL)
    lake_pooled = pool(lake.astype(np.float32), POOL) > 0.5
    big = (acc_km2 >= BIG_RIVER_KM2) | lake_pooled
    rows = max(1, int(round(z.shape[0] * ky / cell_km)))
    cols = max(1, int(round(z.shape[1] * kx / cell_km)))
    ch, cw = z.shape[0] / rows, z.shape[1] / cols
    places, grid = [], {}
    for r in range(rows):
        for c in range(cols):
            r0, r1, c0, c1 = int(r * ch), int((r + 1) * ch), int(c * cw), int((c + 1) * cw)
            p0, p1, q0, q1 = r0 // POOL, max(r0 // POOL + 1, r1 // POOL), c0 // POOL, max(c0 // POOL + 1, c1 // POOL)
            catchment = float(acc_km2[p0:p1, q0:q1].max())
            river = bool(big[p0:p1, q0:q1].mean() > 0.02)
            mean_slope = float(slope[r0:r1, c0:c1].mean())
            kind = "강" if river else kind_of(mean_slope)
            name = f"{r}-{c} {kind}"
            grid[(r, c)] = name
            places.append({
                "name": name, "kind": kind, "row": r, "col": c,
                "lat": round(north - (r + 0.5) * (north - south) / rows, 5), "lon": round(west + (c + 0.5) * (east - west) / cols, 5),
                "elevation": round(float(z[r0:r1, c0:c1].mean()), 1), "slope": round(mean_slope, 1),
                "catchment_km2": round(catchment, 1),
                "water": "맑은 물" if river or catchment >= STREAM_KM2 else None,
                "center": [(r0 + r1) / 2, (c0 + c1) / 2], "site": None, "roof": 0.0,
            })
    by_name = {p["name"]: p for p in places}
    roads = []
    for (r, c), name in grid.items():
        for dr, dc in ((0, 1), (1, -1), (1, 0), (1, 1)):
            other = grid.get((r + dr, c + dc))
            if other is None:
                continue
            a, b = by_name[name]["center"], by_name[other]["center"]
            hours = walk_hours(z, (ky, kx), tuple(a), tuple(b))
            crosses = False
            if by_name[name]["kind"] != "강" and by_name[other]["kind"] != "강":
                for i in range(1, 20):
                    t = i / 20
                    pr = int((a[0] + (b[0] - a[0]) * t) // POOL)
                    pc = int((a[1] + (b[1] - a[1]) * t) // POOL)
                    if 0 <= pr < big.shape[0] and 0 <= pc < big.shape[1] and big[pr, pc]:
                        crosses = True
                        break
            roads.append([name, other, max(1, math.ceil(hours / SLOT_HOURS)) + (1 if crosses else 0)])
    for site, (lat, lon, kind, roof) in sites.items():
        r = min(rows - 1, max(0, int((north - lat) / (north - south) * rows)))
        c = min(cols - 1, max(0, int((lon - west) / (east - west) * cols)))
        host = by_name[grid[(r, c)]]
        # a site's water is what runs within a short walk of the site itself, not somewhere in its 6 km cell
        pr = int((north - lat) / (north - south) * acc_km2.shape[0])
        pc = int((lon - west) / (east - west) * acc_km2.shape[1])
        wr, wc = int(SITE_WATER_KM / (ky * POOL)) + 1, int(SITE_WATER_KM / (kx * POOL)) + 1
        near = float(acc_km2[max(0, pr - wr): pr + wr + 1, max(0, pc - wc): pc + wc + 1].max())
        places.append({"name": site, "kind": kind, "row": r, "col": c, "lat": lat, "lon": lon,
                       "elevation": host["elevation"], "slope": host["slope"], "catchment_km2": round(near, 1),
                       "water": "맑은 물" if near >= SITE_STREAM_KM2 else None, "center": host["center"], "site": site, "roof": roof})
        roads.append([site, host["name"], 1])
    for place in places:
        place.pop("center")
    return {"region": list(region), "cell_km": cell_km, "slot_hours": SLOT_HOURS, "lake_level": lake_level,
            "places": places, "roads": roads, "camps": [c for c in camps if c in sites]}


def save(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
