"""A band whose people each carry their own brain (2026-09-17).

Until now one genome was the whole band's: fifteen people shared one set of 154,212 weights, as if a village copied a
single instruction manual, and only their tempers and what each learned differed. Evolution then happened outside the
world — worlds were scored, the best manual was copied into the next round. Here nobody is scored. A child is born with
a brain mixed from its mother's and father's and a little mutation, lives, and either leaves children or does not.

What a child inherits can be set:
  all       every weight of both parents mixed: the manual, the way it has been
  learning  only what the genome could really hold — the drives, the temper means, how fast one learns, how far one
            trusts a forecast, and (brain D) how loud each area is. The rest starts untuned, to be filled by living.
            This is the genomic bottleneck: a genome cannot store a finished brain (Zador 2019), so what is inherited
            is the machinery for learning, not the knowledge.
"""
from __future__ import annotations

import random

import torch
from torch.nn.utils import parameters_to_vector, vector_to_parameters

from . import brains, temperament

LEARNING_PARTS = ("drives.", "genes.", "learning.", "foresight.trust", "foresight.log_rate", "gains")
# What two brains of different make still share: the senses, the acts' names, the inborn drives, the temper means and
# how fast one learns. Their cores have no common ground - A's pool and D's areas put different meanings in the same
# place - so a child of parents of different make takes its mother's build and only these from its father.
SHARED_PARTS = ("encoder.", "op_embedding.", "arg_query.", "genes.", "learning.", "drives.", "foresight.")
MUTATION = 0.02        # how far a child's weights drift from the mix of its parents
FOUNDER_SPREAD = 0.02  # founders are not clones: each starts a little off the seed


def learning_mask(brain) -> torch.Tensor:
    return torch.cat([torch.full((p.numel(),), name.startswith(LEARNING_PARTS), dtype=torch.bool)
                      for name, p in brain.named_parameters()])


class Band:
    """Stands in for one brain in life.live_day, and hands every call to the brain of the person it is about."""

    def __init__(self, brain_name: str, seed_genome: torch.Tensor, learns: bool = True, inherit: str = "all",
                 rng: random.Random | None = None, others: dict[str, torch.Tensor] | None = None) -> None:
        """others: seeds of other makes of brain living in the same world (brain name -> genome)."""
        self.brain_name, self.learns, self.inherit = brain_name, learns, inherit
        self.seed = seed_genome.detach().clone()
        self.seeds = {brain_name: self.seed, **{k: v.detach().clone() for k, v in (others or {}).items()}}
        self.kind_of: dict[str, str] = {}
        self.rng = rng or random.Random(0)
        self.generator = torch.Generator().manual_seed(self.rng.randrange(1 << 30))
        self.brains: dict[str, brains.Brain] = {}
        self.gone: set[str] = set()          # the buried, so a call about them raises no one
        self.genomes: dict[str, torch.Tensor] = {}
        self.neural: dict[str, tuple] = {}
        self.temper: dict[str, temperament.Temper] = {}
        self._fresh = brains.make(brain_name, 0, learns=learns)
        self._mask = learning_mask(self._fresh)
        self._blank = parameters_to_vector(self._fresh.parameters()).detach().clone()

    # ---- making people
    def _put(self, person: str, genome: torch.Tensor, kind: str | None = None) -> brains.Brain:
        kind = kind or self.kind_of.get(person, self.brain_name)
        brain = brains.make(kind, self.rng.randrange(1 << 30), learns=self.learns)
        vector_to_parameters(genome, brain.parameters())
        self.brains[person], self.genomes[person], self.kind_of[person] = brain, genome, kind
        return brain

    def found(self, people: list[str], kinds: dict[str, str] | None = None) -> None:
        for name in people:
            kind = (kinds or {}).get(name, self.brain_name)
            seed = self.seeds[kind]
            self._put(name, seed + FOUNDER_SPREAD * torch.randn(seed.shape, generator=self.generator), kind)

    def born(self, child: str, mother: str | None, father: str | None) -> None:
        """A child's brain from its parents'. What is missing (an unknown father, a dead parent's brain) is the seed.
        Parents of different makes: the child is built as its mother is, and takes the senses, drives, temper and
        learning of both."""
        kind = self.kind_of.get(mother, self.brain_name)
        a = self.genomes.get(mother, self.seeds[kind])
        other = self.kind_of.get(father, kind)
        share = float(torch.rand((), generator=self.generator))
        if other != kind and father in self.brains:
            mixed = a.clone()
            self._put(child, mixed, kind)
            mine, theirs = dict(self.brains[child].named_parameters()), dict(self.brains[father].named_parameters())
            with torch.no_grad():
                for name, p in mine.items():
                    q = theirs.get(name)
                    if q is not None and q.shape == p.shape and name.startswith(SHARED_PARTS):
                        p.mul_(share).add_((1 - share) * q)
                        p.add_(MUTATION * torch.randn(p.shape, generator=self.generator))
            self.genomes[child] = parameters_to_vector(self.brains[child].parameters()).detach().clone()
            return
        b = self.genomes.get(father, a)
        mixed = share * a + (1 - share) * b + MUTATION * torch.randn(a.shape, generator=self.generator)
        if self.inherit == "learning":
            fresh = brains.make(kind, self.rng.randrange(1 << 30), learns=self.learns)
            genome = parameters_to_vector(fresh.parameters()).detach().clone()
            genome[self._mask if kind == self.brain_name else learning_mask(fresh)] = mixed[self._mask if kind == self.brain_name else learning_mask(fresh)]
            mixed = genome
        self._put(child, mixed, kind)

    def buried(self, person: str) -> None:
        self.brains.pop(person, None)
        self.genomes.pop(person, None)
        self.gone.add(person)

    def of(self, person: str) -> brains.Brain:
        brain = self.brains.get(person)
        if brain is None:
            if person in self.gone:
                return self._fresh          # life still tidies up after the dead; it brings nobody back
            brain = self._put(person, self.seed.clone())
        return brain

    # ---- what life.live_day asks of a brain
    def genes_values(self):
        return self._fresh.genes_values() if not self.genomes else \
            [float(v) for v in torch.stack([b.genes.mean for b in self.brains.values()]).mean(0)]

    def set_temper(self, person, temper):
        self.temper[person] = temper
        self.of(person).set_temper(person, temper)

    def set_plasticity(self, person, factor):
        self.of(person).set_plasticity(person, factor)

    def set_neural(self, person, gains, nudges):
        self.neural[person] = (gains, nudges)
        self.of(person).set_neural(person, gains, nudges)

    def observe(self, person, events):
        self.of(person).observe(person, events)

    def decide(self, person, sense, options, rng):
        return self.of(person).decide(person, sense, options, rng)

    def op_probs(self, person, sense, options):
        return self.of(person).op_probs(person, sense, options)

    def learn(self, person, trace, reward):
        self.of(person).learn(person, trace, reward)

    def learn_body(self, person, trace, then, now):
        self.of(person).learn_body(person, trace, then, now)

    def dislike(self, person, token, strength):
        self.of(person).dislike(person, token, strength)

    def reset_people(self):
        for brain in self.brains.values():
            brain.reset_people()

    def drift(self) -> float:
        """How far the living brains have wandered from the seed, on average."""
        if not self.genomes:
            return 0.0
        drifts = [float((g - self.seeds[self.kind_of.get(name, self.brain_name)]).norm()) for name, g in self.genomes.items()]
        return sum(drifts) / len(drifts)
