import random
import statistics

from engine.brain import genetics, temperament


def _pair_on(same_chromosome: bool, close: float = 0.1):
    loci = list(enumerate(genetics.LOCI))
    for i, a in loci:
        for j, b in loci:
            if i < j and a.kind == b.kind == "trait":
                if same_chromosome and a.chromosome == b.chromosome and abs(a.position - b.position) < close:
                    return i, j
                if not same_chromosome and a.chromosome != b.chromosome:
                    return i, j
    raise AssertionError("no such pair in the layout")


def test_a_gamete_carries_one_parental_copy_of_every_locus_and_close_loci_travel_together(monkeypatch):
    monkeypatch.setattr(genetics, "MUTATION", 0.0)
    monkeypatch.setattr(genetics, "LOAD_MUTATION", 0.0)
    n = len(genetics.LOCI)
    parent = genetics.Genome(([1.0] * n, [2.0] * n))
    rng = random.Random(0)
    gametes = [genetics.gamete(parent, rng) for _ in range(3000)]
    assert all(set(g) <= {1.0, 2.0} for g in gametes[:50])

    def recombined(i, j):
        return sum(g[i] != g[j] for g in gametes) / len(gametes)

    assert recombined(*_pair_on(True)) < 0.2
    assert abs(recombined(*_pair_on(False)) - 0.5) < 0.05


def test_founders_spread_as_temperament_did_and_offspring_resemble_parents_by_about_the_heritability():
    rng = random.Random(1)
    founders = [genetics.founder(rng) for _ in range(1200)]
    starts = [genetics.born(g, rng) for g in founders]
    spread = statistics.pstdev(d.own("fear_gain") for d in starts)
    assert abs(spread - temperament.SPREAD) < 0.05
    slopes = []
    for trait in temperament.GENES:
        mid, child = [], []
        for k in range(0, 1200, 2):
            baby = genetics.born(genetics.conceive(founders[k], founders[k + 1], rng), rng)
            mid.append((starts[k].own(trait) + starts[k + 1].own(trait)) / 2)
            child.append(baby.own(trait))
        slopes.append(genetics.regression_slope(mid, child))
    assert 0.25 < statistics.mean(slopes) < 0.55


def test_harmful_recessives_hurt_only_in_two_copies_and_kin_matings_bring_them_together(monkeypatch):
    load = [i for i, locus in enumerate(genetics.LOCI) if locus.kind == "load"]
    n = len(genetics.LOCI)
    one, two = [0.0] * n, [0.0] * n
    one[load[0]] = two[load[0]] = 1.0
    assert genetics.vigour(genetics.Genome((one, [0.0] * n))) == 1.0
    assert genetics.vigour(genetics.Genome((one, two))) == 1.0 - genetics.LOAD_HARM
    monkeypatch.setattr(genetics, "LOAD_START", 0.1)
    rng = random.Random(2)
    kin, unrelated = [], []
    for _ in range(400):
        mother, father = genetics.founder(rng), genetics.founder(rng)
        sister, brother = genetics.conceive(mother, father, rng), genetics.conceive(mother, father, rng)
        kin.append(genetics.vigour(genetics.conceive(sister, brother, rng)))
        stranger = genetics.conceive(genetics.founder(rng), genetics.founder(rng), rng)
        unrelated.append(genetics.vigour(genetics.conceive(sister, stranger, rng)))
    assert statistics.mean(kin) < statistics.mean(unrelated)


def test_markers_change_nothing_a_body_is_made_of():
    rng = random.Random(3)
    genome = genetics.founder(rng)
    before = (genetics.genotypic_values(genome), genetics.vigour(genome))
    for i, locus in enumerate(genetics.LOCI):
        if locus.kind == "marker":
            genome.haplotypes[0][i] = (genome.haplotypes[0][i] + 1) % genetics.MARKER_ALLELES
    assert (genetics.genotypic_values(genome), genetics.vigour(genome)) == before


def test_the_same_genome_grows_differently_and_hardship_shapes_the_plastic_more(monkeypatch):
    rng = random.Random(4)
    genome = genetics.founder(rng)
    assert genetics.born(genome, random.Random(5)).noise != genetics.born(genome, random.Random(6)).noise
    plastic_loci = [i for i, locus in enumerate(genetics.LOCI) if locus.trait == "maternal_plasticity"]

    def shift_with(allele):
        g = genetics.Genome(([v for v in genome.haplotypes[0]], [v for v in genome.haplotypes[1]]))
        for i in plastic_loci:
            g.haplotypes[0][i] = g.haplotypes[1][i] = allele
        d = genetics.born(g, random.Random(7), mother_hardship=1.0)
        return d.maternal["fear_gain"] - (d.maternal["fear_gain"] * 0)

    assert shift_with(1.0) > shift_with(-1.0) > 0
    early = genetics.born(genome, random.Random(8))
    genetics.settle_early(early, 1.0)
    once = dict(early.early)
    genetics.settle_early(early, 1.0)
    assert early.early == once and once["fear_gain"] > 0 > once["patience"]


def test_a_mothers_early_mark_passes_on_only_when_the_experiment_switch_is_on(monkeypatch):
    genome = genetics.founder(random.Random(9))
    mark = {"fear_gain": 0.8}
    assert genetics.born(genome, random.Random(10), mother_mark=mark).early == {}
    monkeypatch.setattr(genetics, "EPIGENETIC_INHERITANCE", 0.25)
    assert genetics.born(genome, random.Random(10), mother_mark=mark).early == {"fear_gain": 0.2}


def test_neural_genes_give_every_unit_a_gain_and_every_act_a_nudge_and_are_inherited():
    neural = [locus for locus in genetics.LOCI if locus.kind == "neural"]
    assert len(neural) == genetics.NEURAL_WIDTH + len(genetics.OPS)
    rng = random.Random(12)
    founders = [genetics.founder(rng) for _ in range(600)]
    starts = [genetics.born(g, rng) for g in founders]
    gains, nudges = genetics.neural_of(starts[0])
    assert len(gains) == genetics.NEURAL_WIDTH and all(g > 0 for g in gains) and len(nudges) == len(genetics.OPS)
    mid, child = [], []
    for k in range(0, 600, 2):
        baby = genetics.born(genetics.conceive(founders[k], founders[k + 1], rng), rng)
        mid.append((starts[k].neural["gain.0"] + starts[k + 1].neural["gain.0"]) / 2)
        child.append(baby.neural["gain.0"])
    assert genetics.regression_slope(mid, child) > 0.5


def test_a_gene_pool_is_summarised_per_locus():
    rng = random.Random(11)
    pool = genetics.frequencies([genetics.founder(rng) for _ in range(50)])
    assert set(pool) == {locus.name for locus in genetics.LOCI}
    assert all(0.0 <= pool[locus.name] <= 1.0 for locus in genetics.LOCI if locus.kind in ("load", "marker"))
    development = genetics.born(genetics.founder(rng), rng)
    assert isinstance(genetics.temper_of(development), temperament.Temper) and 8.0 <= genetics.strength_of(development) <= 40.0
