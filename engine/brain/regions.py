"""Brain D: a brain in areas instead of one meeting room (2026-09-16).

A (brains.TransformerBrain) mixes every sense in one pool; the probe found thirst drowned there (R² 0.36) while the
evolved genome chose no more drinking for a thirsty body. Animals have areas that each take their own few senses and
push the body toward what they are for: thirst neurons alone drive drinking (Oka et al. 2015) and foresee what drinking
will do (Zimmerman et al. 2016). D keeps the base brain's senses, lifetime learning, temper, neural genes and body
forecast, and replaces the pool with areas:

  hypothalamus   the body's own states, the time of day, what is in hand, food and water here      -> votes for acts
  amygdala       pain, danger, fear, others' pain, herds, people, faces seen                        -> votes for acts
  hippocampus    where one is and has been: places, water, food, herds, the time; carries a memory whose
                 connections change while living (B's Hebbian trace)                               -> votes for acts
  social         people here and what they were seen doing                                          -> votes for acts
  frontal        only the areas' states and the time of day; thinks as many steps as it decides (C's halting)
  basal ganglia  adds every area's votes, each by the area's gain in the genome, to the frontal cortex's act scores;
                 the same learning from the body's easing as every brain

Each area sees a small share of the senses and the areas talk only through their states, so most connections a
meeting room has do not exist here. Nothing in an area's wiring says what to do: votes start small and random, and
evolution and living decide what each area comes to push for.
"""
from __future__ import annotations

import random
from pathlib import Path

import torch
from torch import nn
from torch.nn.utils import parameters_to_vector, vector_to_parameters

from ..primal.config import SLOTS
from .brains import Brain
from .choices import OPS, Candidate, OpOption
from .senses import BODY_KINDS, BODY_SIZE, CATEGORIES, CONTEXT_SIZE, EXTRA_KINDS, Sense

AREA_SIZE = 16
MAX_STEPS = 8
# Positions in the situation vector: body (BODY_SIZE), then context (slot one-hot, rain, storm, temperature, fire, roof,
# crowd, corpses), then the felt extras.
_B = {k: i for i, k in enumerate(BODY_KINDS)}
_HEALTH = len(BODY_KINDS)
_CTX = BODY_SIZE
_SLOT = list(range(_CTX, _CTX + len(SLOTS)))
_RAIN, _STORM, _TEMP, _FIRE, _ROOF, _CROWD, _CORPSES = range(_CTX + len(SLOTS), _CTX + CONTEXT_SIZE)
_X = {k: BODY_SIZE + CONTEXT_SIZE + i for i, k in enumerate(EXTRA_KINDS)}
_C = CATEGORIES

AREAS = {   # name: (situation positions, token categories)
    "hypothalamus": (list(range(BODY_SIZE)) + _SLOT + [_TEMP, _X["light"], _X["arousal"], _X["sweet"], _X["bitter"]],
                     (_C["carried"], _C["gatherable"], _C["water"])),
    "amygdala": ([_B["pain"], _B["danger"], _HEALTH, _CROWD, _FIRE, _CORPSES, _X["fear"], _X["others_pain"],
                  _X["arousal"], _X["light"]], (_C["herd"], _C["person"], _C["seen"])),
    "hippocampus": (_SLOT + [_RAIN, _X["light"], _X["moon"], _B["thirst"], _B["hunger"], _X["novelty"]],
                    (_C["place"], _C["water"], _C["gatherable"], _C["herd"])),
    "social": ([_CROWD, _X["others_pain"], _X["novelty"]], (_C["person"], _C["seen"])),
}
PLASTIC = ("hippocampus",)
GRAFTED = ("encoder.", "op_embedding.", "genes.", "learning.")


class Area(nn.Module):
    def __init__(self, d: int, positions: list[int], categories: tuple[int, ...], n_ops: int, plastic: bool) -> None:
        super().__init__()
        self.positions = positions
        self.categories = categories
        self.query = nn.Parameter(torch.randn(d) * 0.1)
        self.situation = nn.Linear(len(positions), AREA_SIZE)
        self.cell = nn.GRUCell(d + AREA_SIZE, AREA_SIZE)
        self.vote = nn.Linear(AREA_SIZE, n_ops)
        with torch.no_grad():
            self.vote.weight.mul_(0.1)
            self.vote.bias.zero_()
        self.plastic = plastic
        if plastic:
            self.fixed = nn.Parameter(torch.randn(AREA_SIZE, AREA_SIZE) * 0.1)
            self.plasticity = nn.Parameter(torch.full((AREA_SIZE, AREA_SIZE), 0.01))
            self.modulator = nn.Linear(AREA_SIZE, 1)

    def step(self, values: torch.Tensor, tokens: torch.Tensor, categories: torch.Tensor,
             state: torch.Tensor, trace: torch.Tensor | None) -> tuple[torch.Tensor, torch.Tensor | None]:
        mine = torch.zeros(len(categories), dtype=torch.bool)
        for c in self.categories:
            mine |= categories == c
        if bool(mine.any()):
            seen = tokens[mine]
            pooled = (torch.softmax(seen @ self.query, 0)[:, None] * seen).sum(0)
        else:
            pooled = torch.zeros(tokens.shape[1])
        x = torch.cat([pooled, torch.tanh(self.situation(values[self.positions]))])
        h = self.cell(x[None], state[None])[0]
        if self.plastic:
            y = torch.tanh((self.fixed + self.plasticity * trace) @ h)
            trace = torch.clamp(trace + torch.tanh(self.modulator(y)) * torch.outer(y, h), -1.0, 1.0)
            h = y
        return h, trace


class RegionBrain(Brain):
    name = "D"

    def __init__(self, d: int = 32, max_steps: int = MAX_STEPS, seed: int = 0, **shape) -> None:
        super().__init__(d, seed, **shape)
        n_ops = self.op_head.out_features
        self.areas = nn.ModuleDict({name: Area(d, positions, categories, n_ops, name in PLASTIC)
                                    for name, (positions, categories) in AREAS.items()})
        self.frontal = nn.GRUCell(AREA_SIZE * len(AREAS) + len(SLOTS), d)
        self.halt = nn.Linear(d, 1)
        self.gains = nn.Parameter(torch.ones(len(AREAS)))
        self.max_steps = max_steps
        self.state: dict[str, dict] = {}
        self.votes: dict[str, torch.Tensor] = {}   # person -> (areas, ops) votes of the latest moment
        self.eval()

    def think(self, person: str, sense: Sense) -> tuple[torch.Tensor, int]:
        before = self.state.get(person)
        values = torch.tensor(tuple(sense.body) + tuple(sense.context) + tuple(sense.extra), dtype=torch.float32)
        if values.numel() < BODY_SIZE + CONTEXT_SIZE + len(EXTRA_KINDS):
            values = torch.cat([values, torch.zeros(BODY_SIZE + CONTEXT_SIZE + len(EXTRA_KINDS) - values.numel())])
        tokens = self.encoder.tokens(sense.tokens)
        categories = torch.tensor([t.category for t in sense.tokens]) if sense.tokens else torch.zeros(1, dtype=torch.long) - 1
        after, states, votes = {}, [], []
        for name, area in self.areas.items():
            state = before[name] if before else torch.zeros(AREA_SIZE)
            trace = (before.get(name + ".trace") if before else None)
            if area.plastic and trace is None:
                trace = torch.zeros(AREA_SIZE, AREA_SIZE)
            h, trace = area.step(values, tokens, categories, state, trace)
            after[name] = h
            if area.plastic:
                after[name + ".trace"] = trace
            states.append(h)
            votes.append(area.vote(h))
        x = torch.cat(states + [values[_SLOT]])
        y = before["frontal"] if before else torch.zeros(self.d)
        halted, steps = 0.0, 0
        while True:
            y = self.frontal(x[None], y[None])[0]
            steps += 1
            halted += float(torch.sigmoid(self.halt(y)))
            if halted >= 1.0 or steps >= self.max_steps:
                break
        after["frontal"] = y
        self.state[person] = after
        self.votes[person] = torch.stack(votes) * self.gains[:, None]
        return y, steps

    def _op_scores(self, person, h, options, temper, sense=None):
        index, chosen = super()._op_scores(person, h, options, temper, sense)
        votes = self.votes.get(person)
        if votes is not None:
            chosen = chosen + votes[:, index].sum(0)
        return index, chosen

    @torch.no_grad()
    def op_probs(self, person, sense, options):
        saved = self.votes.get(person)
        probs, h = super().op_probs(person, sense, options)
        if saved is None:
            self.votes.pop(person, None)
        else:
            self.votes[person] = saved
        return probs, h

    @torch.no_grad()
    def decide(self, person: str, sense: Sense, options: list[OpOption], rng: random.Random) -> tuple[OpOption, list[Candidate], dict]:
        option, picks, info = super().decide(person, sense, options, rng)
        votes = self.votes.get(person)
        if votes is not None:
            op = OPS.index(option.op)
            info["areas"] = {name: round(float(votes[i, op]), 3) for i, name in enumerate(AREAS)}
        return option, picks, info

    def reset_people(self) -> None:
        super().reset_people()
        self.votes.clear()


def graft(brain: RegionBrain, donor_path: Path, donor_name: str = "A") -> torch.Tensor:
    """Give D what another brain's lineage learned about the world's things: the senses' token embeddings (what a stone,
    water, a deer are), the acts' embeddings, the temper gene means and the learning rate. The rest of D starts its own,
    since no other brain has areas to copy from. Returns D's genome with the graft loaded."""
    from . import brains, evolve
    donor = brains.make(donor_name, 0, learns=brain.learns)
    vector_to_parameters(evolve.load_genome(donor, donor_path), donor.parameters())
    given = dict(donor.named_parameters())
    with torch.no_grad():
        for name, p in brain.named_parameters():
            q = given.get(name)
            if q is not None and q.shape == p.shape and name.startswith(GRAFTED):
                p.copy_(q)
    return parameters_to_vector(brain.parameters()).detach().clone()
