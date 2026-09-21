"""Brain candidates for v0, compared on the same world before any is chosen (design doc 4).

  A  a small transformer over what is perceived this moment: no state between moments
  B  a recurrent core that carries its state from moment to moment, with connections that change while living
     (Hebbian traces gated by a signal the network computes itself, as in Backpropamine)
  C  B that decides how many steps to think before acting (adaptive computation time); the steps are reported so
     thinking can later cost the body

Learning within a life (stage 3) is the same for all three, so they are compared fairly. Each person is born with an
empty lifetime layer: a bias on which act to pick given what is perceived, and a bias on which thing to pick it with.
After an act, how much the body's distress eased (life.drive) is the only signal: a three-factor rule strengthens the
perceived-state to chosen-act link when the body got better and weakens it when the body got worse. How fast a person
learns is one number in the genome, so evolution can change it. Nobody is told what was good.

Stage 4 tunes the same weights per person with a temper (temperament.py): choices spread by the person's action noise,
company-seeking acts draw or repel by their people pull, and how far back an outcome reaches over earlier choices is their
patience. The lineage's means of the temper sit in the genome. A genome from an earlier stage grows into the current
shapes by name (grow): what the old brain had is copied, a new sense column starts at zero so it changes nothing until
evolution or learning makes use of it, tasting starts unlikely, and mating and nursing start as likely as an average act
(both are driven by innate pleasures in mammals; a start near never would leave no one to be selected).

Foresight (2026-09-16): every brain also forecasts how each act would change its own body, and learns that forecast
while living from what its body then did (Foresight). A forecast of feeling worse holds an act back by the genome's
trust in it, zero in a genome grown from before, so nothing changes until evolution uses it.
"""
from __future__ import annotations

import math
import random

import torch
from torch import nn
from torch.nn.utils import parameters_to_vector, vector_to_parameters

from . import temperament
from .choices import OPS, Candidate, OpOption
from .senses import (BODY_KINDS, BODY_SIZE, CATEGORIES, CONTEXT_SIZE, EXTRA_KINDS, EXTRA_SIZE, KIND_BUCKETS,
                     LOOKS, PROPS, Sense, Token)

LEGACY_OPS = OPS.index("taste")        # ops a genome from before stage 4 knows
STAGE4_OPS = OPS.index("mate")         # ops a stage 4 genome knows
NEW_OP_BIAS = -4.0                     # tasting starts about 50 times less likely than an average act
SOCIAL = ("give", "follow")            # acts that seek another person out
PRE_SEEN_CATEGORIES = CATEGORIES["seen"]   # token categories before others' acts could be seen
PRE_SKY_EXTRA = 7                          # feelings before light, moon and arousal were felt
PRE_CLOCK_GENES = 11                       # temperament genes before the body clock
_OLD = {"n_extra": PRE_SKY_EXTRA, "n_genes": PRE_CLOCK_GENES, "foresight": False, "drives": False}
SHAPES = (   # older genome shapes grow() recognises
    {"legacy": True, "n_categories": PRE_SEEN_CATEGORIES, "foresight": False, "drives": False},
    {"n_ops": STAGE4_OPS, "n_categories": PRE_SEEN_CATEGORIES, **_OLD},
    {"n_ops": len(OPS), "n_categories": PRE_SEEN_CATEGORIES, **_OLD},
    {"n_ops": len(OPS), "n_categories": len(CATEGORIES), **_OLD},
    {"foresight": False, "drives": False},    # every sense and gene of today, before the body forecast
    {"drives": False},                        # before the inborn drives
)
SEEN_KEEP = 16


def _sample(probs: torch.Tensor, rng: random.Random) -> int:
    r, total = rng.random(), 0.0
    values = probs.tolist()
    for i, p in enumerate(values):
        total += p
        if r < total:
            return i
    return len(values) - 1


class Encoder(nn.Module):
    def __init__(self, d: int, props: int = PROPS, situation: int = BODY_SIZE + CONTEXT_SIZE + EXTRA_SIZE,
                 categories: int = len(CATEGORIES)) -> None:
        super().__init__()
        self.d = d
        self.category = nn.Embedding(categories, d)
        self.kind = nn.Embedding(KIND_BUCKETS, d)
        self.props = nn.Linear(props, d)
        self.situation = nn.Linear(situation, d)

    def tokens(self, tokens: list[Token]) -> torch.Tensor:
        if not tokens:
            return torch.zeros(1, self.d)
        category = torch.tensor([t.category for t in tokens])
        kind = torch.tensor([t.kind for t in tokens])
        props = torch.tensor([t.props for t in tokens], dtype=torch.float32)[:, : self.props.in_features]
        return self.category(category) + self.kind(kind) + self.props(props)

    def whole(self, sense: Sense) -> torch.Tensor:
        values = (tuple(sense.body) + tuple(sense.context) + tuple(sense.extra))[: self.situation.in_features]
        return torch.tanh(self.situation(torch.tensor(values, dtype=torch.float32)))


class LearningRate(nn.Module):
    """A module of its own because torch lays a module's own parameters out before its submodules': registered as the
    last submodule, this number comes last in the genome vector, after every weight a genome without learning has."""

    def __init__(self, rate: float) -> None:
        super().__init__()
        self.log = nn.Parameter(torch.tensor(math.log(rate)))


class Genes(nn.Module):
    """The lineage's mean of every temperament dimension in gene units; evolution moves them like any weight."""

    def __init__(self, n: int = len(temperament.GENES)) -> None:
        super().__init__()
        self.mean = nn.Parameter(torch.zeros(n))


# Probed 2026-09-16 (gen147, 4 worlds): at 0.5 each person's forecast chased noise and missed worse than knowing each
# act's average (MSE 0.059 against 0.030); at 0.05 it beat that average (0.017) and ordered acts right more often.
FORESIGHT_RATE = 0.05
# How much a change in each felt state matters, the same weights life.drive sums distress with: every felt distress
# counts once, health (a hundredth per point in the body vector) twice, the mind's needs not at all.
EASE = torch.tensor([1.0] * len(BODY_KINDS) + [-2.0] + [0.0] * (BODY_SIZE - len(BODY_KINDS) - 1))


class Foresight(nn.Module):
    """A body forecast (interoceptive prediction, 2026-09-16): before acting, how each act would change what the body
    feels by the next time the person is asked. The brain predicts its own body, a dozen numbers, rather than the world
    (the allostatic principle of Candia-Rivera 2026; emotion as predicted body state, Barrett). The inborn forecast is
    weight @ (the moment + the act); a person's own corrections are learned while living, by the error between the
    forecast and what the body then did (a normalised delta rule). How far a forecast of feeling worse holds a person
    back from an act is trust, in the genome; it starts at zero, so a brain grown from one without foresight chooses
    exactly as before until evolution finds a use for it. The inborn weights are held at zero in evolution
    (evolve.FROZEN): while trust stayed near zero they only gathered mutations."""

    def __init__(self, d: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.zeros(BODY_SIZE, d))   # zeros draw no random numbers, so older brains init as before
        self.bias = nn.Parameter(torch.zeros(BODY_SIZE))
        self.trust = nn.Parameter(torch.zeros(()))
        self.log_rate = nn.Parameter(torch.tensor(math.log(FORESIGHT_RATE)))


# Innate drives (2026-09-17). A newborn mammal is not blank: hunger drives it toward food (AgRP neurons make a fed
# mouse eat, Betley 2015), thirst toward water (Oka 2015), a hurt or exhausted body toward lying still. Those paths are
# inborn, not learned, so a brain here is born with a weak pull from each felt state toward the acts that have ever
# answered it. Nothing is forced: a pull is added to the act's score and any choice can still win, and each drive's
# strength is a number in the genome that evolution can raise, lower or switch off. Weights are starting values.
DRIVE_PULLS = {
    "thirst": {"drink": 1.0, "fill": 0.3, "go": 0.2},
    "hunger": {"eat": 1.0, "gather": 0.8, "fish": 0.5, "hunt": 0.4, "pick": 0.3, "taste": 0.2, "go": 0.2},
    "sleepy": {"sleep": 1.0, "rest": 0.4},
    "cold": {"fire": 0.8, "heat": 0.3, "build": 0.2},
    "pain": {"rest": 0.8, "sleep": 0.3},
    "danger": {"flee": 0.8, "rest": 0.2},
}
# Two more pulls that are not about one's own body (2026-09-17). A grown animal with food in its hands and a hungry
# young one beside it is drawn to hand it over: among people this provisioning is the rule, not the exception - a
# forager's child lives on what adults bring for years after weaning. And a hungry animal that cannot feed itself where
# it stands follows the others, which is how a patch one has never seen is ever found.
CARE_PULLS = {"give": 1.0, "nurse": 0.6}
DRIVE_STATES = tuple(DRIVE_PULLS) + ("care",)
DRIVE_SCALE = 2.0   # how many points of an act's score a fully felt drive with gain 1 adds
# What the mouth knows without being taught: a hungry animal reaches for what is soft and sweet and turns from what is
# stone-hard or bitter (newborns' faces already say so, Steiner). These are the token's own felt props - hardness and
# weight from the hand, sweetness and toxicity from a tongue that has tried it - so nothing here names a food.
MOUTH_PULLS = {"hardness": -1.0, "weight": -0.5, "sweetness": 1.0, "toxicity": -1.0, "moisture": 0.5, "spoil": -0.5}
# Area-restricted search, the oldest foraging rule there is: while there is something growing here to pick, a hungry
# animal picks; when the patch is bare it moves on. Both pulls are hunger times the same gene, so evolution can undo them.
HERE_PULLS = {"gather": 1.0, "pick": 0.5}
ELSEWHERE_PULLS = {"go": 0.8, "follow": 0.4}
MOUTH_PROPS = {"hardness": LOOKS, "weight": LOOKS + 1, "sweetness": LOOKS + 6, "toxicity": LOOKS + 7,
               "moisture": 5, "spoil": 1}   # these two are seen rather than felt, so a standing patch shows them too
FORAGING = ("eat", "taste", "gather", "pick")


class Drives(nn.Module):
    """The inborn pulls from what the body feels toward what has ever answered it. The table is fixed (it is what the
    body is wired to); the gains are the genome's."""

    def __init__(self, n_ops: int) -> None:
        super().__init__()
        table = torch.zeros(len(DRIVE_STATES), n_ops)
        for row, state in enumerate(DRIVE_STATES):
            for op, weight in (CARE_PULLS if state == "care" else DRIVE_PULLS[state]).items():
                if op in OPS[:n_ops]:
                    table[row, OPS.index(op)] = weight
        self.register_buffer("table", table)
        self.gain = nn.Parameter(torch.ones(len(DRIVE_STATES)))

    def mouth(self, body: tuple[float, ...], props: torch.Tensor) -> torch.Tensor:
        """How much hunger draws the hand toward each thing it could put in the mouth."""
        hunger = body[BODY_KINDS.index("hunger")] if len(body) > BODY_KINDS.index("hunger") else 0.0
        gain = float(self.gain[DRIVE_STATES.index("hunger")]) * hunger
        if gain <= 0:
            return torch.zeros(props.shape[0])
        felt = sum(weight * props[:, MOUTH_PROPS[name]] for name, weight in MOUTH_PULLS.items())
        return DRIVE_SCALE * gain * felt

    def pull(self, body: tuple[float, ...], index: torch.Tensor, food_here: bool = False,
             care: float = 0.0) -> torch.Tensor:
        felt = torch.tensor([care if state == "care" else
                             (body[BODY_KINDS.index(state)] if BODY_KINDS.index(state) < len(body) else 0.0)
                             for state in DRIVE_STATES], dtype=torch.float32)
        pulls = DRIVE_SCALE * ((self.gain * felt)[:, None] * self.table[:, index]).sum(0)
        hunger = float(self.gain[DRIVE_STATES.index("hunger")]) * float(felt[DRIVE_STATES.index("hunger")])
        if hunger > 0:
            table = HERE_PULLS if food_here else ELSEWHERE_PULLS
            here = torch.zeros(self.table.shape[1])
            for op, weight in table.items():
                if op in OPS:
                    here[OPS.index(op)] = weight
            pulls = pulls + DRIVE_SCALE * hunger * here[index]
        return pulls


class Brain(nn.Module):
    name = "brain"

    def __init__(self, d: int = 32, seed: int = 0, legacy: bool = False, n_ops: int | None = None,
                 n_categories: int | None = None, n_extra: int | None = None, n_genes: int | None = None,
                 foresight: bool = True, drives: bool = True) -> None:
        torch.manual_seed(seed)
        super().__init__()
        self.d = d
        self.legacy = legacy
        n_ops = n_ops if n_ops is not None else LEGACY_OPS if legacy else len(OPS)
        categories = n_categories if n_categories is not None else len(CATEGORIES)
        extra = n_extra if n_extra is not None else EXTRA_SIZE
        self.encoder = (Encoder(d, LOOKS, BODY_SIZE + CONTEXT_SIZE, categories) if legacy
                        else Encoder(d, situation=BODY_SIZE + CONTEXT_SIZE + extra, categories=categories))
        self.op_head = nn.Linear(d, n_ops)
        self.op_embedding = nn.Embedding(n_ops, d)
        self.arg_query = nn.Linear(d, d)
        if not legacy:
            self.genes = Genes(n_genes if n_genes is not None else len(temperament.GENES))
        self.foresight = Foresight(d) if foresight else None
        self.drives = Drives(n_ops) if drives else None
        self.learns = False
        self.rule = "rpe"
        self.lifetime: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}   # person -> (act bias, thing bias)
        self.expected: dict[str, float] = {}                               # person -> how much the body usually eases
        self.recent: dict[str, list[tuple]] = {}                           # person -> latest choices, newest first
        self.temper: dict[str, temperament.Temper] = {}                    # person -> what they were born with
        self.neural: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}     # person -> (unit gains, act nudges) from genes
        self.seen: dict[str, list[tuple[str, Token, float]]] = {}          # person -> others' acts seen since their last choice
        self.expecting: dict[str, torch.Tensor] = {}                       # person -> own corrections to the body forecast
        self.eagerness: dict[str, float] = {}                              # person -> how fast they are learning now (youth)

    # Stage 3 v2. With the plain rule nearly every choice was punished (mean reward -0.12 to -0.19), because a body left
    # alone slowly gets thirstier whatever is chosen. Dopamine reports how much better or worse things went than
    # expected (Schultz, Dayan & Montague 1997), so each person keeps a running expectation and learns from the
    # difference. A walk to water is rewarded only when the drinking comes later, so the difference is also shared
    # with the two choices before, fading each time by the person's patience (an eligibility trace; half by default).
    EXPECTATION_STEP = 0.1
    TRACE_DECAY = temperament.DEFAULT.patience
    TRACE_LENGTH = 6

    def enable_learning(self, rate: float = 0.1, rule: str = "rpe") -> None:
        """Registered last, so a genome that learns is the same vector as one that does not, plus this one number."""
        self.learns = True
        self.rule = rule
        self.learning = LearningRate(rate)

    def learning_rate(self) -> float | None:
        return float(torch.exp(self.learning.log)) if self.learns else None

    def genes_values(self) -> list[float] | None:
        return None if self.legacy else [float(v) for v in self.genes.mean]

    def set_temper(self, person: str, temper: temperament.Temper) -> None:
        self.temper[person] = temper

    def set_plasticity(self, person: str, factor: float) -> None:
        """How fast this person learns at this point in life: young animals learn faster than old ones."""
        self.eagerness[person] = factor

    def set_neural(self, person: str, gains: list[float], nudges: list[float]) -> None:
        """A person's neural genes (genetics.neural_of): each hidden unit scaled, each act nudged. Shapes that do not fit
        this brain (an older genome's) are ignored."""
        if len(gains) == self.d and len(nudges) == self.op_head.out_features:
            self.neural[person] = (torch.tensor(gains, dtype=torch.float32), torch.tensor(nudges, dtype=torch.float32))

    def observe(self, person: str, events: list[tuple[str, Token, float]]) -> None:
        """Others' acts this person saw: (the act, what it was done to as a token, how it seemed to go for them)."""
        if events:
            self.seen[person] = (self.seen.get(person, []) + list(events))[-SEEN_KEEP:]

    def _learn_seen(self, person: str, h: torch.Tensor, events: list[tuple[str, Token, float]]) -> None:
        """Observational learning (stage 5): the same three-factor rule as one's own outcomes, with the onlooker's
        present state as context and what showed on the other's face as the signal. A pleased eater pulls the onlooker
        toward that act and that kind of thing; a hurt or frightened one pushes away. No act is copied by the engine."""
        acts, things = self.lifetime.setdefault(person, (torch.zeros(len(OPS), self.d), torch.zeros(self.d)))
        rate = float(torch.exp(self.learning.log)) * self.eagerness.get(person, 1.0)
        for op, token, signal in events:
            if signal == 0.0 or op not in OPS:
                continue
            acts[OPS.index(op)] += rate * signal * h
            things.add_(rate * signal * self.encoder.tokens([token])[0])
        acts.clamp_(-5.0, 5.0)
        things.clamp_(-5.0, 5.0)

    def reset_people(self) -> None:
        self.lifetime.clear()
        self.expected.clear()
        self.recent.clear()
        self.temper.clear()
        self.neural.clear()
        self.seen.clear()
        self.expecting.clear()
        self.eagerness.clear()
        state = getattr(self, "state", None)
        if state is not None:
            state.clear()

    def think(self, person: str, sense: Sense) -> tuple[torch.Tensor, int]:
        raise NotImplementedError

    def parameters_count(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def expect(self, person: str, x: torch.Tensor) -> torch.Tensor:
        """The body forecast for moments-with-acts x (..., d): the change in the body vector by the next choice."""
        weight = self.foresight.weight
        own = self.expecting.get(person) if self.learns else None
        if own is not None:
            weight = weight + own
        return x @ weight.T + self.foresight.bias

    def _worsening(self, person: str, x: torch.Tensor) -> torch.Tensor:
        if self.foresight is None or float(self.foresight.trust) == 0.0:
            return torch.zeros(x.shape[:-1])
        return self.foresight.trust * (self.expect(person, x) @ EASE)

    def _op_scores(self, person: str, h: torch.Tensor, options: list[OpOption],
                   temper: temperament.Temper, sense: Sense | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        neural = self.neural.get(person)
        learned = self.lifetime.get(person) if self.learns else None
        logits = self.op_head(h)
        if neural is not None:
            logits = logits + neural[1]
        if learned is not None:
            logits = logits + learned[0] @ h
        index = torch.tensor([OPS.index(o.op) for o in options])
        chosen = logits[index]
        if temper.people_pull:
            chosen = chosen + torch.tensor([temper.people_pull if o.op in SOCIAL else 0.0 for o in options])
        if self.drives is not None and sense is not None:
            care = sense.extra[EXTRA_KINDS.index("others_pain")] if len(sense.extra) > EXTRA_KINDS.index("others_pain") else 0.0
            chosen = chosen + self.drives.pull(sense.body, index, self._worth_picking(person, sense), care)
        return index, chosen - self._worsening(person, h + self.op_embedding(index))

    def _worth_picking(self, person: str, sense: Sense) -> bool:
        """Whether anything growing here is worth staying for: what this person has learned to like, and whatever they
        have never tried. A stone spat out once stops counting, so a riverbank of stones no longer reads as a patch of
        food and hunger pushes them on."""
        growing = [t for t in sense.tokens if t.category == CATEGORIES["gatherable"]]
        if not growing:
            return False
        learned = self.lifetime.get(person) if self.learns else None
        if learned is None:
            return True
        return bool((self.encoder.tokens(growing) @ learned[1] >= 0).any())

    @torch.no_grad()
    def op_probs(self, person: str, sense: Sense, options: list[OpOption]) -> tuple[torch.Tensor, torch.Tensor]:
        """How likely each act would be, and the inner state, with nothing changed: no memory carried on, nothing
        learned, nothing seen used up. For asking the same brain what it would do in a changed world (probe.py)."""
        state = getattr(self, "state", None)
        saved = state.get(person) if state is not None else None
        h, _ = self.think(person, sense)
        if state is not None:
            if saved is None:
                state.pop(person, None)
            else:
                state[person] = saved
        neural = self.neural.get(person)
        if neural is not None:
            h = h * neural[0]
        temper = self.temper.get(person, temperament.DEFAULT)
        _, chosen = self._op_scores(person, h, options, temper, sense)
        return torch.softmax(chosen / temper.action_noise, 0), h

    @torch.no_grad()
    def decide(self, person: str, sense: Sense, options: list[OpOption], rng: random.Random) -> tuple[OpOption, list[Candidate], dict]:
        temper = self.temper.get(person, temperament.DEFAULT)
        h, steps = self.think(person, sense)
        neural = self.neural.get(person)
        if neural is not None:
            h = h * neural[0]
        watched = self.seen.pop(person, None)
        if self.learns and watched:
            self._learn_seen(person, h, watched)
        learned = self.lifetime.get(person) if self.learns else None
        index, chosen = self._op_scores(person, h, options, temper, sense)
        probs = torch.softmax(chosen / temper.action_noise, 0)
        k = _sample(probs, rng)
        option = options[k]
        base = h + self.op_embedding(torch.tensor(OPS.index(option.op)))
        query = self.arg_query(base)
        if learned is not None:
            query = query + learned[1]
        picks, remembered = [], []
        for candidates in option.args:
            embedded = self.encoder.tokens([c.token for c in candidates])
            scores = embedded @ query - self._worsening(person, base + embedded)
            if self.drives is not None and option.op in FORAGING:
                props = torch.tensor([c.token.props for c in candidates], dtype=torch.float32)
                scores = scores + self.drives.mouth(sense.body, props)
            p = torch.softmax(scores / temper.action_noise, 0)
            j = _sample(p, rng)
            picks.append(candidates[j])
            remembered.append((embedded, p, j))
        info = {"think_steps": steps, "hidden": h}
        if self.learns:
            info["trace"] = (h.clone(), index, probs, k, remembered)
        return option, picks, info

    @torch.no_grad()
    def dislike(self, person: str, token: Token, strength: float) -> None:
        """One bad meal, remembered for life (taste aversion, Garcia): the pull toward things like this one drops, for
        this person alone; a negative strength is the other way about, the kind that fed one being looked for again."""
        if not self.learns or strength == 0:
            return
        _, things = self.lifetime.setdefault(person, (torch.zeros(len(OPS), self.d), torch.zeros(self.d)))
        embedded = self.encoder.tokens([token])[0]
        things.add_(-strength * embedded / (embedded.norm() + 1e-6))
        things.clamp_(-5.0, 5.0)

    @torch.no_grad()
    def learn_body(self, person: str, trace: tuple, then: tuple[float, ...], now: tuple[float, ...]) -> None:
        """What the body did after a choice, against what was forecast for it: the act alone and the act with the
        thing it was done to both learn from the miss."""
        if not self.learns or self.foresight is None:
            return
        h, index, _, k, remembered = trace
        actual = torch.tensor(now, dtype=torch.float32) - torch.tensor(then, dtype=torch.float32)
        base = h + self.op_embedding(index[k])
        own = self.expecting.setdefault(person, torch.zeros(BODY_SIZE, self.d))
        rate = float(torch.exp(self.foresight.log_rate))
        for x in [base] + [base + embedded[j] for embedded, _, j in remembered[:1]]:
            miss = actual - self.expect(person, x)
            own.add_(rate * torch.outer(miss, x) / (float(x @ x) + 1.0))
        own.clamp_(-5.0, 5.0)

    @torch.no_grad()
    def learn(self, person: str, trace: tuple, reward: float) -> None:
        """What was perceived, what was chosen against what was likely, and how much the body eased after."""
        if not self.learns:
            return
        if self.rule == "plain":
            self._strengthen(person, trace, reward)
            return
        expected = self.expected.get(person, 0.0)
        surprise = reward - expected
        self.expected[person] = expected + self.EXPECTATION_STEP * surprise
        recent = [trace] + self.recent.get(person, [])[: self.TRACE_LENGTH - 1]
        self.recent[person] = recent
        decay = self.temper.get(person, temperament.DEFAULT).patience
        for i, past in enumerate(recent):
            self._strengthen(person, past, surprise * decay ** i)

    def _strengthen(self, person: str, trace: tuple, signal: float) -> None:
        if signal == 0.0:
            return
        h, index, probs, k, remembered = trace
        acts, things = self.lifetime.setdefault(person, (torch.zeros(len(OPS), self.d), torch.zeros(self.d)))
        rate = float(torch.exp(self.learning.log)) * self.eagerness.get(person, 1.0)
        push = -probs
        push[k] += 1.0
        acts.index_add_(0, index, rate * signal * torch.outer(push, h))
        acts.clamp_(-5.0, 5.0)
        for embedded, p, j in remembered:
            things.add_(rate * signal * (embedded[j] - (p[:, None] * embedded).sum(0)))
        things.clamp_(-5.0, 5.0)


class TransformerBrain(Brain):
    name = "A"

    def __init__(self, d: int = 32, layers: int = 2, heads: int = 4, seed: int = 0, **shape) -> None:
        super().__init__(d, seed, **shape)
        layer = nn.TransformerEncoderLayer(d, heads, dim_feedforward=2 * d, batch_first=True, dropout=0.0)
        self.core = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.eval()

    def think(self, person: str, sense: Sense) -> tuple[torch.Tensor, int]:
        sequence = torch.cat([self.encoder.whole(sense)[None], self.encoder.tokens(sense.tokens)], 0)[None]
        return self.core(sequence)[0, 0], 1


class RecurrentPlasticBrain(Brain):
    name = "B"

    def __init__(self, d: int = 32, seed: int = 0, **shape) -> None:
        super().__init__(d, seed, **shape)
        self.cell = nn.GRUCell(2 * d, d)
        self.fixed = nn.Parameter(torch.randn(d, d) * 0.1)
        self.plasticity = nn.Parameter(torch.full((d, d), 0.01))
        self.modulator = nn.Linear(d, 1)
        self.state: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}   # person -> (activity, Hebbian trace)
        self.eval()

    def _situation(self, sense: Sense) -> torch.Tensor:
        return torch.cat([self.encoder.whole(sense), self.encoder.tokens(sense.tokens).mean(0)])

    def _step(self, person: str, x: torch.Tensor) -> torch.Tensor:
        h, trace = self.state.get(person, (torch.zeros(self.d), torch.zeros(self.d, self.d)))
        h = self.cell(x[None], h[None])[0]
        y = torch.tanh((self.fixed + self.plasticity * trace) @ h)
        modulation = torch.tanh(self.modulator(y))
        trace = torch.clamp(trace + modulation * torch.outer(y, h), -1.0, 1.0)
        self.state[person] = (y, trace)
        return y

    def think(self, person: str, sense: Sense) -> tuple[torch.Tensor, int]:
        return self._step(person, self._situation(sense)), 1


class PonderingBrain(RecurrentPlasticBrain):
    name = "C"

    def __init__(self, d: int = 32, max_steps: int = 8, seed: int = 0, **shape) -> None:
        super().__init__(d, seed, **shape)
        self.max_steps = max_steps
        self.halt = nn.Linear(d, 1)
        self.eval()

    def think(self, person: str, sense: Sense) -> tuple[torch.Tensor, int]:
        x = self._situation(sense)
        halted, steps = 0.0, 0
        while True:
            y = self._step(person, x)
            steps += 1
            halted += float(torch.sigmoid(self.halt(y)))
            if halted >= 1.0 or steps >= self.max_steps:
                return y, steps


class RandomPolicy:
    """No brain at all: a uniform pick among what the body could try. The floor every brain is measured against."""
    name = "random"
    learns = False

    def parameters_count(self) -> int:
        return 0

    def reset_people(self) -> None:
        pass

    def learning_rate(self) -> None:
        return None

    def genes_values(self) -> None:
        return None

    def set_temper(self, person: str, temper: temperament.Temper) -> None:
        pass

    def set_neural(self, person: str, gains: list[float], nudges: list[float]) -> None:
        pass

    def set_plasticity(self, person: str, factor: float) -> None:
        pass

    def observe(self, person: str, events: list) -> None:
        pass

    def learn(self, person: str, trace: tuple, reward: float) -> None:
        pass

    def learn_body(self, person: str, trace: tuple, then: tuple, now: tuple) -> None:
        pass

    def dislike(self, person: str, token, strength: float) -> None:
        pass

    def op_probs(self, person: str, sense: Sense, options: list[OpOption]) -> tuple[torch.Tensor, None]:
        return torch.full((len(options),), 1.0 / len(options)), None

    def decide(self, person: str, sense: Sense, options: list[OpOption], rng: random.Random) -> tuple[OpOption, list[Candidate], dict]:
        option = rng.choice(options)
        return option, [rng.choice(candidates) for candidates in option.args], {"think_steps": 0}


def make(name: str, seed: int = 0, learns: bool = False, rule: str = "rpe", **shape):
    """shape: legacy, n_ops, n_categories, n_extra, n_genes, for building a brain of an older genome's shape."""
    if name == "random":
        return RandomPolicy()
    if name == "D":
        from .regions import RegionBrain
        brain = RegionBrain(seed=seed, **shape)
    else:
        brain = {"A": TransformerBrain, "B": RecurrentPlasticBrain, "C": PonderingBrain}[name](seed=seed, **shape)
    if learns:
        brain.enable_learning(rule=rule)
    return brain


def grow(vector: torch.Tensor, brain: Brain) -> torch.Tensor:
    """A genome of an earlier shape, moved into this brain by name. Returns the grown genome (and leaves it loaded)."""
    for shape in SHAPES:
        old = make(brain.name, **shape)
        size = parameters_to_vector(old.parameters()).numel()
        if vector.numel() == size + 1:
            old.enable_learning()
        if vector.numel() in (size, size + 1):
            break
    else:
        raise ValueError(f"a genome of {vector.numel()} numbers fits neither this brain nor any earlier shape")
    vector_to_parameters(vector, old.parameters())
    before = dict(old.named_parameters())
    with torch.no_grad():
        for name, p in brain.named_parameters():
            q = before.get(name)
            if q is None:
                if name == "genes.mean":
                    p.zero_()
                elif name == "learning.log":
                    p.fill_(math.log(0.1))
                elif name == "drives.gain":
                    p.fill_(1.0)
                elif name == "foresight.log_rate":
                    p.fill_(math.log(FORESIGHT_RATE))
                elif name.startswith("foresight."):
                    p.zero_()
                continue
            if q.shape == p.shape:
                p.copy_(q)
                continue
            if name == "drives.gain":
                p.fill_(1.0)
                p[: q.shape[0]] = q
                continue
            p.zero_()
            p[tuple(slice(0, s) for s in q.shape)] = q
            if name == "op_head.bias":
                for i in range(q.shape[0], p.shape[0]):
                    p[i] = NEW_OP_BIAS if OPS[i] == "taste" else float(q.mean())
    return parameters_to_vector(brain.parameters()).detach().clone()
