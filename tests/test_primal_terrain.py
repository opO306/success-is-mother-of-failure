import math

import numpy as np
import pytest

from engine.primal import terrain


def _valley(rows=240, cols=240):
    """A valley running north to south: high on both sides, the floor sloping gently south."""
    y, x = np.mgrid[0:rows, 0:cols]
    return (400.0 + np.abs(x - cols / 2) * 3.0 + (rows - y) * 0.5).astype(np.float32)


def test_water_gathers_along_the_valley_floor_and_grows_downstream():
    z = terrain.pool(_valley(), 5)
    acc = terrain.flow_accumulation(z)
    floor = z.shape[1] // 2
    assert acc[-1, floor] > acc[z.shape[0] // 2, floor] > acc[2, floor]
    assert acc[-1, floor] > 10 * acc[-1, 2]


def test_water_running_into_a_hollow_or_across_a_flat_still_reaches_the_edge_once_hollows_are_filled():
    z = terrain.pool(_valley(), 5)
    rows, cols = z.shape
    z[rows // 2, cols // 2 - 2: cols // 2 + 3] -= 40.0          # a pit across the valley floor
    z[rows // 2 + 5: rows // 2 + 9, cols // 2 - 3: cols // 2 + 4] = z[rows // 2 + 5, cols // 2]   # a dead-flat stretch
    floor = cols // 2
    raw = terrain.flow_accumulation(z)
    filled = terrain.flow_accumulation(terrain.fill_depressions(z))
    assert filled[-1, floor] > 1.5 * raw[-1, floor]
    assert filled[-1, floor] > 0.5 * rows


def test_walking_is_fastest_just_downhill_and_slow_up_a_steep_slope():
    assert terrain.tobler_kmh(-0.05) == pytest.approx(6.0)
    assert terrain.tobler_kmh(0.0) == pytest.approx(5.036, abs=0.01)
    assert terrain.tobler_kmh(0.4) < 1.5
    flat = np.full((100, 100), 300.0, dtype=np.float32)
    assert terrain.walk_hours(flat, (0.06, 0.06), (0, 0), (0, 99)) == pytest.approx(99 * 0.06 / 5.036, rel=0.02)


def test_the_danyang_land_builds_a_connected_world_with_glacial_seasons_and_cave_fauna():
    if not (terrain.ROOT / "danyang_lgm.json").exists():
        pytest.skip("run tools/build_land.py first")
    from engine.primal.scenario import CAMPS, LGM_SEASON_TEMP, build_world
    world = build_world(seed=0, band_size=2, energy=True, wildlife=True, puddles=True, land="danyang")
    assert world.config.season_temp == LGM_SEASON_TEMP
    camps = {p.camp for p in world.people.values()}
    assert camps == {"수양개", "상시 바위그늘", "점말동굴"} and not camps & set(CAMPS)
    assert all(world.map.route("수양개", place) is not None for place in world.lands)
    assert all(l.water for l in world.lands.values() if l.kind == "강")
    assert world.lands["금굴"].natural_roof == 0.8
    species = {h.species for h in world.herds}
    assert {"큰사슴", "말", "원시소", "호랑이"} <= species
    tame = build_world(seed=0, band_size=2, land="danyang")
    assert "호랑이" not in {h.species for h in tame.herds}


def test_a_built_land_has_a_river_down_the_valley_slopes_beside_it_sites_and_roads_both_ways():
    z = _valley()
    region = (37.0, 37.0 + 240 * 30 / 111000, 128.0, 128.0 + 240 * 30 / (111000 * math.cos(math.radians(37))))
    sites = {"굴": (region[0] + 0.01, region[2] + 0.01, "동굴", 0.8), "터": (region[0] + 0.03, (region[2] + region[3]) / 2, "야영지", 0.0)}
    old_big, terrain.BIG_RIVER_KM2 = terrain.BIG_RIVER_KM2, 20.0
    try:
        data = terrain.build(z, region=region, cell_km=1.5, sites=sites, camps=("터",))
    finally:
        terrain.BIG_RIVER_KM2 = old_big
    places = {p["name"]: p for p in data["places"]}
    grid = [p for p in data["places"] if not p["site"]]
    middle = max(p["col"] for p in grid) // 2
    assert any(p["kind"] == "강" and p["col"] in (middle, middle + 1) for p in grid)
    assert all(p["kind"] != "강" for p in grid if p["col"] == 0)
    assert places["굴"]["kind"] == "동굴" and places["굴"]["roof"] == 0.8 and data["camps"] == ["터"]
    assert all(s >= 1 for _, _, s in data["roads"]) and {a for a, _, _ in data["roads"]} | {b for _, b, _ in data["roads"]} == set(places)
