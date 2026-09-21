from engine.primal import animals, plants
from engine.primal.nature import SPECIES, Fire, Gatherable, Weather
from engine.primal.scenario import build_world


class Dice:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value

    def choice(self, options):
        return options[0]


def _world(**kw):
    return build_world(seed=0, band_size=5, animals=True, **kw)


def _herd(world, species):
    return next(h for h in world.herds if h.species == species)


def _full(herd):
    return animals.DIETS[herd.species].store


def test_a_thirsty_herd_walks_toward_water_and_drinks_when_it_gets_there():
    world = _world()
    deer = next(h for h in world.herds if h.species == "사슴" and h.place == "북쪽 숲")
    deer.hydration, deer.energy = 0.2, _full(deer)
    animals.slot(world, "낮")
    assert deer.place != "북쪽 숲"
    for _ in range(3):
        animals.slot(world, "낮")
    assert world.lands[deer.place].water and deer.hydration == 1.0


def test_a_hungry_grazer_eats_the_land_down_and_moves_on_when_it_is_bare():
    world = _world()
    horses = next(h for h in world.herds if h.species == "들소")
    land = world.lands[horses.place]
    land.gather["풀"] = Gatherable("풀", 1.0, 60.0, {})
    land.gather.pop("쑥", None)
    horses.energy, horses.hydration = 0.5, 1.0
    start = horses.place
    animals.slot(world, "낮")
    assert land.gather["풀"].stock < 3.0 and horses.energy > 0.5 and horses.place != start


def test_a_herd_out_of_food_loses_animals_to_carrion_and_one_in_condition_bears_in_spring():
    world = _world()
    deer = next(h for h in world.herds if h.species == "사슴")
    deer.energy, count = 0.0, deer.count
    animals.day(world)
    assert deer.count < count and world.lands[deer.place].carrion > 0
    rabbits = next(h for h in world.herds if h.species == "토끼")
    rabbits.energy, before = _full(rabbits), rabbits.count
    world.day = 1
    world.weather.season = "봄"
    animals.day(world)
    assert sum(h.count for h in world.herds if h.species == "토끼") > before
    thin = next(h for h in world.herds if h.species == "사슴" and h is not deer)
    thin.energy, thin_count = 0.2 * _full(thin), thin.count
    world.day = 1
    animals.day(world)
    assert thin.count <= thin_count                                    # a thin herd bears nothing


def test_a_hungry_predator_hunts_the_prey_where_it_is_and_eats():
    world = _world()
    wolves = _herd(world, "늑대")
    deer = next(h for h in world.herds if h.species == "사슴")
    deer.place = wolves.place
    deer.energy = _full(deer)                         # a full herd stays put instead of wandering off to graze
    wolves.energy, deer_count = 0.5, deer.count
    world.rng = Dice(0.0)
    animals.slot(world, "밤")
    assert deer.count == deer_count - 1 and wolves.energy > 0.5 and deer.fear == 1.0


def test_a_hungry_predator_eats_carrion_it_finds_before_it_hunts():
    world = _world()
    wolves = _herd(world, "늑대")
    for herd in world.herds:
        if herd is not wolves:
            herd.place = "동굴"
    land = world.lands[wolves.place]
    land.carrion, wolves.energy = 5.0, 0.5
    animals.slot(world, "밤")
    assert land.carrion < 5.0 and wolves.energy > 0.5


def test_carcass_food_is_explicit_and_not_combat_toughness():
    assert SPECIES["누"].edible_meat_kg == 108
    assert SPECIES["누"].edible_meat_kg != SPECIES["누"].toughness
    assert {"가젤", "임팔라", "혹멧돼지"} <= set(animals.DIETS["표범"].prey)
    assert animals.DIETS["점박이하이에나"].capture_scale > animals.DIETS["사자"].capture_scale


def test_a_full_tiger_walks_past_a_hungry_one_takes_the_lone_sleeper_and_a_crowd_by_a_fire_is_left_alone():
    world = _world()
    tiger = _herd(world, "호랑이")
    for herd in world.herds:
        if herd is not tiger:
            herd.place = "동굴"
    camp = world.lands["북쪽 야영지"]
    people = world.at("북쪽 야영지")
    tiger.place, tiger.boldness = "북쪽 야영지", 0.5
    camp.fire = Fire(heat=0.7, fuel_slots=8)
    world.rng = Dice(0.99)
    tiger.energy = 0.0
    animals.slot(world, "밤")
    assert not any(p.body.injuries for p in people)                   # five awake people and a fire
    loner = people[0]
    for other in people[1:]:
        other.location = "북쪽 숲"
    camp.fire = None
    world.asleep = {loner.name}
    tiger.place, tiger.energy = "북쪽 야영지", _full(tiger)
    animals.slot(world, "밤")
    assert not loner.body.injuries                                     # a full tiger
    tiger.place, tiger.energy = "북쪽 야영지", 0.0
    animals.slot(world, "밤")
    assert loner.body.injuries                                         # the same tiger, starving


def test_hunting_near_a_boar_startles_it_until_it_charges():
    world = _world()
    boar = _herd(world, "멧돼지")
    hunter = next(iter(world.people.values()))
    hunter.location = boar.place
    world.slot_done = {hunter.name: [{"op": "hunt", "ok": True}]}
    boar.energy, boar.fear = _full(boar), 0.5
    animals.slot(world, "낮")
    assert hunter.body.injuries and boar.fear < 0.7


def test_a_herd_grown_too_big_splits_and_the_new_group_goes_next_door():
    world = _world()
    deer = next(h for h in world.herds if h.species == "사슴")
    deer.count, deer.energy = 30, _full(deer)
    world.day = 2                                     # not the turn of spring, so nobody is born today
    herds_before = len(world.herds)
    animals.day(world)
    young = world.herds[-1]
    assert len(world.herds) == herds_before + 1 and young.species == "사슴"
    assert deer.count + young.count == 30 and young.place != deer.place


def test_grazers_and_bears_burn_less_in_the_short_days_and_hunters_do_not():
    world = _world(land="danyang")
    deer, wolves, bear = animals.DIETS["사슴"], animals.DIETS["늑대"], animals.DIETS["큰곰"]
    uses = []
    for day in range(1, 4 * world.config.days_per_season + 1):
        world.day = day
        uses.append((animals.food_use(world, deer), animals.food_use(world, wolves), animals.food_use(world, bear)))
    assert min(u[0] for u in uses) < 0.45 and max(u[0] for u in uses) > 0.95
    assert all(u[1] == 1.0 for u in uses) and min(u[2] for u in uses) < 0.3


def test_carrion_keeps_in_the_frost_and_rots_in_the_warmth():
    assert animals.rot_share(-5.0) < 0.05 < animals.rot_share(20.0)


def test_grass_stands_dry_through_a_frozen_month():
    world = _world(land="danyang", plants=True)
    land = next(l for l in world.lands.values() if "풀" in l.gather)
    stand = land.gather["풀"]
    stand.stock = stand.cap
    for day in range(30):
        plants.plants_day(land, Weather(300 + day, "겨울", -10.0, False, False), world.config)
    assert stand.stock > 0.6 * stand.cap


def test_a_place_of_the_real_land_carries_pasture_by_its_area_and_grazers_eat_it_before_the_stands():
    world = _world(land="danyang", plants=True)
    meadow = next(l for l in world.lands.values() if l.kind == "초원")
    assert meadow.pasture_cap == animals_pasture_per_ha("초원") * 36 * 100
    horses = next(h for h in world.herds if h.species == "말")
    land = world.lands[horses.place]
    stands = {k: s.stock for k, s in land.gather.items()}
    pasture, horses.energy, horses.hydration = land.pasture, 0.0, 1.0
    animals.slot(world, "낮")
    assert land.pasture < pasture and horses.energy > 0 and {k: s.stock for k, s in land.gather.items()} == stands
    land.pasture = 0.2 * land.pasture_cap
    plants.plants_day(land, Weather(150, "여름", 18.0, False, False), world.config)
    assert land.pasture > 0.2 * land.pasture_cap


def test_a_predator_goes_hunting_once_its_store_is_half_gone():
    world = _world()
    wolves = _herd(world, "늑대")
    deer = next(h for h in world.herds if h.species == "사슴")
    deer.place, deer.energy = wolves.place, _full(deer)
    world.rng = Dice(0.0)
    wolves.energy, count = 0.8 * _full(wolves), deer.count
    animals.slot(world, "밤")
    assert deer.count == count                        # well fed: no hunt
    wolves.place, deer.place = deer.place, deer.place
    wolves.energy = 0.4 * _full(wolves)
    animals.slot(world, "밤")
    assert deer.count == count - 1
    wolves.fed_today, wolves.energy = 1.0, 0.4 * _full(wolves)
    animals.slot(world, "밤")
    assert deer.count == count - 1                    # fed a day's worth today: no second kill


def animals_pasture_per_ha(kind):
    from engine.primal import scenario
    return scenario.PASTURE_PER_HA[kind]


def test_worlds_with_animal_minds_do_not_use_the_old_odds():
    world = _world()
    assert world.config.animal_minds and {"호랑이", "표범"} <= {h.species for h in world.herds}
    assert all(-1.0 <= h.boldness <= 1.0 for h in world.herds)
    assert all(h.energy == animals.DIETS[h.species].store * animals.START_STORE for h in world.herds)
