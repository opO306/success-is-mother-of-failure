"""Evolvable control without named instincts, goals, or correct actions.

The body supplies graded physical signals.  An inherited recurrent network lets
anonymous physical action patterns compete.  Persistence can keep a previous
choice despite a stronger immediate impulse, while a sufficiently better rival
can still replace it.  Learning uses only change in bodily distress; no observer
label or world-law answer is exposed to the organism.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from .body import BodyIntent, BodyTickResult, MatterPool, body_tick, internal_signals
from .foundation import ControllerGene, LivingState, PhysicalCue, Sensation, perceive


@dataclass(frozen=True)
class Decision:
    action_index: int
    inputs: tuple[float, ...]
    activations: tuple[float, ...]
    scores: tuple[float, ...]
    retained_previous: bool
    intent: BodyIntent


@dataclass(frozen=True)
class ControlCostResult:
    spent: tuple[float, ...]
    shortfall: tuple[float, ...]
    damage_added: float


@dataclass(frozen=True)
class ControlledTickResult:
    sensations: tuple[Sensation, ...]
    decision: Decision
    control_cost: ControlCostResult
    body: BodyTickResult
    distress_change: float


def _receptor_summary(state: LivingState, sensations: tuple[Sensation, ...]) -> tuple[float, ...]:
    """Keep the strongest signed activity per inherited receptor."""
    values = []
    for index in range(len(state.genome.receptors)):
        candidates = [sensation.receptor_activity[index] for sensation in sensations]
        values.append(max(candidates, key=abs) if candidates else 0.0)
    return tuple(values)


def _source_features(state: LivingState, sensations: tuple[Sensation, ...]) -> tuple[float, float, float]:
    """Association, familiarity, and novelty for the currently strongest source."""
    if not sensations:
        return 0.0, 0.0, 0.0
    strongest = max(
        sensations,
        key=lambda sensation: (sum(abs(value) for value in sensation.receptor_activity), -sensation.distance),
    )
    association, familiarity = state.memory.get(strongest.source_key, (0.0, 0.0))[:2]
    novelty = 1.0 / (1.0 + max(0.0, familiarity))
    return association, familiarity, novelty


def control_inputs(state: LivingState, sensations: tuple[Sensation, ...]) -> tuple[float, ...]:
    return internal_signals(state) + _receptor_summary(state, sensations) + _source_features(state, sensations)


def _validate_interface(state: LivingState, gene: ControllerGene, inputs: tuple[float, ...]) -> None:
    if state.controller is None:
        raise ValueError("living state has no developed controller")
    if len(gene.input_weights[0]) != len(inputs):
        raise ValueError("controller input width must match body signals and inherited receptors")
    dimensions = len(state.position)
    processes = len(state.genome.catalysts)
    width = len(state.reserves)
    if gene.control_cost and len(gene.control_cost) != width:
        raise ValueError("control cost must use the body's material channels")
    for action in gene.actions:
        if len(action.exchange) != width:
            raise ValueError("action exchange must use the body's material channels")
        if len(action.displacement) != dimensions:
            raise ValueError("action displacement must use the body's spatial dimensions")
        if action.process_rates and len(action.process_rates) != processes:
            raise ValueError("action process rates must match inherited catalysts")


def decide(state: LivingState, sensations: Iterable[Sensation]) -> Decision:
    """Let inherited and acquired physical connections select one possible act."""
    gene = state.genome.controller
    if gene is None or state.controller is None:
        raise ValueError("decide requires an inherited and developed controller")
    sensed = tuple(sensations)
    inputs = control_inputs(state, sensed)
    _validate_interface(state, gene, inputs)
    control = state.controller
    previous_nodes = tuple(control.activations)
    activations = []
    for node, (input_row, recurrent_row, bias, retention) in enumerate(
        zip(gene.input_weights, gene.recurrent_weights, gene.node_bias, gene.node_retention)
    ):
        incoming = bias
        incoming += sum(weight * value for weight, value in zip(input_row, inputs))
        incoming += sum(weight * value for weight, value in zip(recurrent_row, previous_nodes))
        mixed = retention * previous_nodes[node] + (1.0 - retention) * math.tanh(incoming)
        activations.append(max(-1.0, min(1.0, mixed)))

    control.commitment *= gene.commitment_decay
    scores = [sum(weight * value for weight, value in zip(row, activations)) for row in control.action_weights]
    retained = False
    best = max(range(len(scores)), key=lambda index: (scores[index], -index))
    if control.chosen_action is not None:
        current = control.chosen_action
        current_score = scores[current] + gene.persistence * control.commitment
        if best == current or scores[best] <= current_score + gene.switch_margin:
            best = current
            retained = True
    if best != control.chosen_action:
        control.commitment = 1.0
    control.chosen_action = best
    control.activations[:] = activations
    control.last_inputs = inputs
    pattern = gene.actions[best]
    return Decision(
        best,
        inputs,
        tuple(activations),
        tuple(scores),
        retained,
        BodyIntent(pattern.exchange, pattern.displacement, pattern.process_rates),
    )


def _pay_control_cost(state: LivingState, ambient: MatterPool, gene: ControllerGene) -> ControlCostResult:
    required = gene.control_cost or (0.0,) * len(state.reserves)
    spent = []
    shortfall = []
    for index, cost in enumerate(required):
        paid = min(cost, state.reserves[index])
        state.reserves[index] -= paid
        ambient.amounts[index] += paid
        spent.append(paid)
        shortfall.append(cost - paid)
    total = sum(required)
    missing_share = sum(shortfall) / total if total else 0.0
    damage = missing_share * state.boundary.damage_from_total_shortfall
    state.damage += damage
    return ControlCostResult(tuple(spent), tuple(shortfall), damage)


def _distress(signals: tuple[float, ...]) -> float:
    return sum(max(0.0, value) for value in signals)


def learn_from_result(
    state: LivingState,
    before_signals: tuple[float, ...],
    after_signals: tuple[float, ...],
    sensations: tuple[Sensation, ...] = (),
) -> float:
    """Change only the selected connections from experienced bodily consequence."""
    gene = state.genome.controller
    control = state.controller
    if gene is None or control is None or control.chosen_action is None:
        return 0.0
    improvement = _distress(before_signals) - _distress(after_signals)
    for action_index, row in enumerate(control.action_weights):
        inherited = gene.action_weights[action_index]
        for node in range(len(row)):
            row[node] = inherited[node] + gene.learning_decay * (row[node] - inherited[node])
    chosen = control.action_weights[control.chosen_action]
    for node, activity in enumerate(control.activations):
        changed = chosen[node] + gene.learning_rate * improvement * activity
        chosen[node] = max(-16.0, min(16.0, changed))
    seen = {sensation.source_key: sensation for sensation in sensations}
    for source_key in tuple(state.memory):
        if source_key not in seen:
            association, familiarity = state.memory[source_key][:2]
            association *= gene.memory_decay
            familiarity *= gene.memory_decay
            if abs(association) < 1e-12 and familiarity < 1e-12:
                del state.memory[source_key]
            else:
                state.memory[source_key] = (association, familiarity)
    for source_key, sensation in seen.items():
        salience = min(1.0, sum(abs(value) for value in sensation.receptor_activity))
        association, familiarity = state.memory.get(source_key, (0.0, 0.0))[:2]
        association = gene.memory_decay * association + gene.association_learning * improvement * salience
        familiarity = gene.memory_decay * familiarity + salience
        state.memory[source_key] = (
            max(-1.0, min(1.0, association)),
            max(0.0, familiarity),
        )
    return improvement


def controlled_body_tick(
    state: LivingState,
    ambient: MatterPool,
    cues: Iterable[PhysicalCue] = (),
    chemistry=None,
) -> ControlledTickResult:
    """Sense, choose, pay for control, suffer consequences, and learn once."""
    sensations = perceive(state.genome, cues)
    before = internal_signals(state)
    decision = decide(state, sensations)
    gene = state.genome.controller
    assert gene is not None
    cost = _pay_control_cost(state, ambient, gene)
    body = body_tick(state, ambient, decision.intent, chemistry)
    after = internal_signals(state)
    change = learn_from_result(state, before, after, sensations)
    return ControlledTickResult(sensations, decision, cost, body, change)
