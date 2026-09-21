"""Genes of the brain world's people (design doc 4, generations): a genotype that is not the person, and a development
that turns it into one.

Genotype. Every person carries two copies of every locus, one from each parent. What tunes a mind or a body (each
temperament dimension, the two plasticities, strength) is the sum of several loci of small effect, mostly additive with
a little dominance, so continuous variation comes out of Mendelian inheritance by itself (Fisher 1918). Loci sit at
positions on a few chromosomes. A gamete takes one homolog of every chromosome at random and switches homolog at each
crossover, so loci close together travel together. Where each locus sits is drawn once; no package of traits is designed.
Every allele copied into a gamete mutates now and then.

Recessive harmful alleles (load loci) do nothing in one copy and weaken a body in two. Nobody forbids kin from mating;
when kin mate, two copies of the same rare harmful allele meet more often, and inbreeding depression follows from that
alone (Charlesworth & Willis 2009). Neutral marker loci change nothing, so how far their frequencies drift is the
yardstick a change in a trait allele has to beat before it is called selection.

Development. A trait's value is the lineage's mean (what the outer evolution carries) + the genotype + developmental
noise (identical genotypes still differ, as twins' fingerprints do) + what the mother's body went through while carrying
the child + what the child's own first days did. The last two are scaled by the person's plasticity loci, so how much an
environment shapes a child is itself inherited and selected (a reaction norm). Hardship early in life setting how
reactive a mind is has been shown in rats (maternal care, Weaver et al. 2004) and is associated in people born during a
famine (Heijmans et al. 2008). Whether such marks reach the next generation is doubtful in mammals (Heard & Martienssen
2014), so passing the mother's early mark on is a switch, off unless an experiment turns it on.

Twin studies put the heritability of personality near 40%, so founders' allele variance and the noise are set to make
about 40% of a trait's spread (temperament.SPREAD) genetic at the start. From then on selection and drift move it.

Neural genes. The brain's wiring is the species' and stays shared, but every person's brain runs it a little differently:
one locus per hidden unit sets how strongly that unit responds (a gain, the way per-neuron scaling adapts a shared
network, as IA3 does, Liu et al. 2022), and one locus per act nudges how readily it is chosen. Each number keeps the same
meaning in every body, so two copies, dominance, crossing over and mutation work on them as on any locus; a low-rank
adapter would not, because its factors can be rotated without changing what they do, and mixing two parents' factors
piece by piece breaks both. A little developmental noise is added, as wiring is never grown exactly to plan.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from . import temperament
from .choices import OPS

TRAITS = temperament.GENES + ("maternal_plasticity", "early_plasticity", "strength")
LOCI_PER_TRAIT = 4
LOAD_LOCI = 20
MARKERS = 10
CHROMOSOMES = 6
CHROMOSOME_LENGTH = 1.2        # Morgans: a little over one crossover per chromosome per gamete
HERITABILITY = 0.4
ALLELE_SD = math.sqrt(2 * HERITABILITY * temperament.SPREAD ** 2 / LOCI_PER_TRAIT)
NOISE_SD = temperament.SPREAD * math.sqrt(1 - HERITABILITY)
MUTATION = 0.005               # chance an allele changes on its way into a gamete
MUTATION_SD = ALLELE_SD * 0.5
LOAD_MUTATION = 0.001          # chance a working load allele turns harmful on its way into a gamete
LOAD_START = 0.05              # share of harmful alleles at each load locus among founders
LOAD_HARM = 0.15               # each load locus with two harmful copies takes this share of vigour
MARKER_ALLELES = 20
PLASTICITY = 0.5               # gene units a full hardship shifts a trait, for a person of average plasticity
EPIGENETIC_INHERITANCE = 0.0   # share of a mother's early mark a child is born with; 0 unless an experiment says so
NEURAL_WIDTH = 32              # hidden units of every brain candidate (brains.Brain d)
NEURAL_ALLELE_SD = 0.1         # founders' spread of a unit's log-gain or an act's nudge, per allele
NEURAL_NOISE_SD = 0.05

# How hardship shifts a developing mind, as a hypothesis in the direction of the findings above: more reactive to threat,
# slower to let a harmless threat go, less willing to wait. Scaled by plasticity; the brain still decides what to do.
HARDSHIP_SHIFT = {"fear_gain": 1.0, "habituation": -0.5, "patience": -0.5}


@dataclass(frozen=True)
class Locus:
    name: str
    kind: str              # "trait" | "load" | "marker"
    trait: str | None
    chromosome: int
    position: float
    dominance: float       # -1..1: 1 the larger allele dominates, -1 the smaller, 0 purely additive


def _layout() -> tuple[Locus, ...]:
    rng = random.Random("genome-layout-v1")
    loci = []
    for trait in TRAITS:
        for i in range(LOCI_PER_TRAIT):
            loci.append(Locus(f"{trait}.{i}", "trait", trait, rng.randrange(CHROMOSOMES), rng.uniform(0, CHROMOSOME_LENGTH),
                              max(-1.0, min(1.0, rng.gauss(0.0, 0.3)))))
    for i in range(LOAD_LOCI):
        loci.append(Locus(f"load.{i}", "load", None, rng.randrange(CHROMOSOMES), rng.uniform(0, CHROMOSOME_LENGTH), 0.0))
    for i in range(MARKERS):
        loci.append(Locus(f"marker.{i}", "marker", None, rng.randrange(CHROMOSOMES), rng.uniform(0, CHROMOSOME_LENGTH), 0.0))
    for target in [f"gain.{i}" for i in range(NEURAL_WIDTH)] + [f"act.{op}" for op in OPS]:
        loci.append(Locus(f"neural.{target}", "neural", target, rng.randrange(CHROMOSOMES), rng.uniform(0, CHROMOSOME_LENGTH),
                          max(-1.0, min(1.0, rng.gauss(0.0, 0.3)))))
    return tuple(loci)


LOCI = _layout()
BY_CHROMOSOME = {c: sorted((i for i, locus in enumerate(LOCI) if locus.chromosome == c), key=lambda i: LOCI[i].position)
                 for c in range(CHROMOSOMES)}


@dataclass
class Genome:
    haplotypes: tuple[list[float], list[float]]   # from the mother, from the father


def founder(rng: random.Random) -> Genome:
    def haplotype() -> list[float]:
        out = []
        for locus in LOCI:
            if locus.kind == "trait":
                out.append(rng.gauss(0.0, ALLELE_SD))
            elif locus.kind == "neural":
                out.append(rng.gauss(0.0, NEURAL_ALLELE_SD))
            elif locus.kind == "load":
                out.append(1.0 if rng.random() < LOAD_START else 0.0)
            else:
                out.append(float(rng.randrange(MARKER_ALLELES)))
        return out
    return Genome((haplotype(), haplotype()))


def _poisson(rng: random.Random, mean: float) -> int:
    limit, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _mutate(value: float, locus: Locus, rng: random.Random) -> float:
    if locus.kind == "trait":
        return value + rng.gauss(0.0, MUTATION_SD) if rng.random() < MUTATION else value
    if locus.kind == "neural":
        return value + rng.gauss(0.0, NEURAL_ALLELE_SD * 0.5) if rng.random() < MUTATION else value
    if locus.kind == "load":
        return 1.0 if rng.random() < LOAD_MUTATION else value
    return float(rng.randrange(MARKER_ALLELES)) if rng.random() < MUTATION else value


def gamete(genome: Genome, rng: random.Random) -> list[float]:
    """Meiosis: one homolog per chromosome, switching at crossovers, every copied allele open to mutation."""
    out = [0.0] * len(LOCI)
    for order in BY_CHROMOSOME.values():
        strand = rng.randrange(2)
        crossovers = sorted(rng.uniform(0, CHROMOSOME_LENGTH) for _ in range(_poisson(rng, CHROMOSOME_LENGTH)))
        k = 0
        for i in order:
            while k < len(crossovers) and crossovers[k] < LOCI[i].position:
                strand, k = 1 - strand, k + 1
            out[i] = _mutate(genome.haplotypes[strand][i], LOCI[i], rng)
    return out


def conceive(mother: Genome, father: Genome, rng: random.Random) -> Genome:
    return Genome((gamete(mother, rng), gamete(father, rng)))


def genotypic_values(genome: Genome) -> dict[str, float]:
    values = dict.fromkeys(TRAITS, 0.0)
    first, second = genome.haplotypes
    for i, locus in enumerate(LOCI):
        if locus.kind == "trait":
            a, b = first[i], second[i]
            values[locus.trait] += (a + b) / 2 + locus.dominance * abs(a - b) / 2
    return values


def neural_values(genome: Genome) -> dict[str, float]:
    first, second = genome.haplotypes
    return {locus.trait: (first[i] + second[i]) / 2 + locus.dominance * abs(first[i] - second[i]) / 2
            for i, locus in enumerate(LOCI) if locus.kind == "neural"}


def vigour(genome: Genome) -> float:
    """1 for a body carrying no harmful allele twice; lower with every load locus where both copies are harmful."""
    first, second = genome.haplotypes
    doubled = sum(1 for i, locus in enumerate(LOCI) if locus.kind == "load" and first[i] and second[i])
    return (1.0 - LOAD_HARM) ** doubled


def marker_homozygosity(genome: Genome) -> float:
    first, second = genome.haplotypes
    markers = [i for i, locus in enumerate(LOCI) if locus.kind == "marker"]
    return sum(first[i] == second[i] for i in markers) / len(markers)


def _plastic(z: float) -> float:
    return PLASTICITY * math.exp(max(-3.0, min(3.0, z)))


@dataclass
class Development:
    genotype: dict[str, float]
    noise: dict[str, float]
    maternal: dict[str, float] = field(default_factory=dict)
    early: dict[str, float] = field(default_factory=dict)
    settled: bool = False       # the early window has closed
    neural: dict[str, float] = field(default_factory=dict)   # gain.i and act.op, as grown

    def own(self, trait: str) -> float:
        """What genes and noise alone make of a trait, before any hardship."""
        return self.genotype[trait] + self.noise[trait]

    def traits(self, means: list[float] | None = None) -> dict[str, float]:
        lineage = dict(zip(temperament.GENES, means)) if means is not None else {}
        return {t: lineage.get(t, 0.0) + self.own(t) + self.maternal.get(t, 0.0) + self.early.get(t, 0.0) for t in TRAITS}


def _shift(amount: float) -> dict[str, float]:
    return {trait: weight * amount for trait, weight in HARDSHIP_SHIFT.items()}


def born(genome: Genome, rng: random.Random, mother_hardship: float = 0.0, mother_mark: dict[str, float] | None = None) -> Development:
    """A child's start: genes, noise, the hardship its mother lived while carrying it (0-1), and, only when the
    experiment switch is on, part of the mark the mother's own first days left."""
    genotype = genotypic_values(genome)
    noise = {t: rng.gauss(0.0, NOISE_SD) for t in TRAITS}
    development = Development(genotype, noise)
    development.neural = {k: v + rng.gauss(0.0, NEURAL_NOISE_SD) for k, v in neural_values(genome).items()}
    development.maternal =_shift(max(0.0, min(1.0, mother_hardship)) * _plastic(development.own("maternal_plasticity")))
    if mother_mark and EPIGENETIC_INHERITANCE:
        development.early = {t: EPIGENETIC_INHERITANCE * v for t, v in mother_mark.items()}
    return development


def settle_early(development: Development, hardship: float) -> None:
    """The early window closes: how hard the first days were (0-1) leaves its mark, as far as this person is plastic."""
    if development.settled:
        return
    mark = _shift(max(0.0, min(1.0, hardship)) * _plastic(development.own("early_plasticity")))
    for trait, value in mark.items():
        development.early[trait] = development.early.get(trait, 0.0) + value
    development.settled = True


def temper_of(development: Development, means: list[float] | None = None) -> temperament.Temper:
    z = development.traits(means)
    return temperament.from_values([z[g] for g in temperament.GENES])


def neural_of(development: Development) -> tuple[list[float], list[float]]:
    """How this person's brain runs the species' wiring: a gain per hidden unit and a nudge per act."""
    gains = [math.exp(max(-3.0, min(3.0, development.neural.get(f"gain.{i}", 0.0)))) for i in range(NEURAL_WIDTH)]
    nudges = [development.neural.get(f"act.{op}", 0.0) for op in OPS]
    return gains, nudges


def strength_of(development: Development) -> float:
    """Founders' strength spread about as it did before genes (12-28, sd about 4.6)."""
    return max(8.0, min(40.0, 20.0 * math.exp(0.65 * development.traits()["strength"])))


def frequencies(genomes: list[Genome]) -> dict[str, float]:
    """Per locus: the mean allele of a trait locus, the share of harmful copies at a load locus, and the share of the
    commonest allele at a marker. What a generation's gene pool looks like, for the log."""
    out: dict[str, float] = {}
    if not genomes:
        return out
    for i, locus in enumerate(LOCI):
        copies = [g.haplotypes[0][i] for g in genomes] + [g.haplotypes[1][i] for g in genomes]
        if locus.kind == "marker":
            counts: dict[float, int] = {}
            for c in copies:
                counts[c] = counts.get(c, 0) + 1
            out[locus.name] = max(counts.values()) / len(copies)
        else:
            out[locus.name] = sum(copies) / len(copies)
    return out


def regression_slope(xs: list[float], ys: list[float]) -> float | None:
    """Offspring on mid-parent: the slope estimates narrow-sense heritability."""
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    return None if sxx == 0 else sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
