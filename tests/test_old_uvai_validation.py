from tools import validate_olduvai


def test_old_uvai_is_connected_deterministic_and_has_reachable_water():
    report = validate_olduvai.static_validation(seed=7)
    assert report["places"] == 102
    assert report["water_places"] > 0
    assert all(distance is not None for distance in report["nearest_water_slots"].values())
    assert not report["failures"]
    assert report["state_hash"] == validate_olduvai.static_validation(seed=7)["state_hash"]


def test_old_uvai_fruiting_plants_can_complete_more_than_one_cycle_without_a_cold_winter():
    report = validate_olduvai.plant_validation(seed=7, years=2)
    assert not report["failures"]
    assert not report["missing_repeated_fruiting"]
    assert all(cycles >= 2 for cycles in report["max_cycles_per_stand"].values())


def test_old_uvai_ecology_never_breaks_physical_resource_invariants():
    report = validate_olduvai.ecology_validation(seed=7, days=30)
    assert not report["failures"]
    assert report["start"] and report["snapshots"]["30"]
    assert set(report["predator_diagnostics"]) == {"사자", "점박이하이에나", "표범"}


def test_reflex_probe_uses_body_needs_not_a_fitness_score():
    world = validate_olduvai._world(7, people_per_camp=2)
    population = validate_olduvai.lifecycle.found(world, None)
    policy = validate_olduvai.ReflexProbe(world, population)
    assert not hasattr(policy, "fitness")
    assert not hasattr(policy, "score")


def test_manifest_hashes_the_world_rules_that_were_validated():
    report = validate_olduvai.validate([7], days=30, plant_years=1)
    # A one-year plant probe is intentionally too short for the normal gate; the manifest itself is pure bookkeeping.
    manifest = validate_olduvai.build_manifest(report, [7], 30, 1)
    assert manifest["lineage"] == "E"
    assert "engine/primal/animals.py" in manifest["files"]
    assert manifest["validation"]["initial_state_sha256"] == report["static"]["state_hash"]
