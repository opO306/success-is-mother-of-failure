"""What a person in the primal land is shown: their senses, their memories, nothing else."""
from __future__ import annotations

from pydantic import BaseModel, Field

from . import body as physiology
from . import mind as minds
from .config import SLOTS
from .nature import SPECIES, air_temp, shelter_at
from .senses import describe
from .world import World


# The schema sent to the server names every field as required. With defaults alone the fields were optional, and a
# server that enforces the schema let a model leave "plan" out: Gemma 4 31B did on 5 of 5 mornings, Qwen3.8-27B on
# 2 of 135, and such an answer became a person with no plan. Required means the key is written, not that it says
# anything: an empty plan or response is still theirs to give.
class DayDeclaration(BaseModel):
    model_config = {"json_schema_extra": {"required": ["plan", "reasoning", "same_as_yesterday"]}}
    plan: str = Field(default="", max_length=1200)
    reasoning: str = Field(default="", max_length=600)
    same_as_yesterday: bool = False


class Reaction(BaseModel):
    model_config = {"json_schema_extra": {"required": ["response", "reasoning"]}}
    response: str = Field(default="", max_length=600)
    reasoning: str = Field(default="", max_length=400)


def weather_words(world: World, slot: str) -> str:
    t = air_temp(world.weather, slot, world.config)
    feel = "덥다" if t >= 25 else "따뜻하다" if t >= 15 else "선선하다" if t >= 5 else "춥다" if t >= -2 else "몹시 춥다"
    sky = ""
    if world.weather.storm:
        sky = ", 폭풍이 몰아친다"
    elif world.weather.raining:
        sky = ", 눈이 내린다" if t < 0 else ", 비가 온다"
    return feel + sky


def carried_lines(world: World, name: str) -> list[str]:
    person = world.people[name]
    return [describe(t, name) for t in person.carried]


def surroundings(world: World, name: str) -> list[str]:
    person = world.people[name]
    land = world.lands[person.location]
    lines = []
    if land.fire:
        lines.append("불이 타고 있다")
    done = [s for s in land.structures if s.complete]
    if done:
        lines.append(f"누군가 지어 놓은 것 {len(done)}채")
    if any(not s.complete for s in land.structures):
        lines.append("짓다 만 것이 있다")
    for herd in world.herds:
        if herd.place == land.name and herd.count > 0:
            lines.append(f"{herd.species} {'무리' if herd.count > 2 else ''}가 보인다".replace("  ", " "))
    visible = sorted({g.kind for g in land.gather.values() if g.stock >= 1})
    if land.water:
        visible.append(land.water)
    if visible:
        lines.append("구할 수 있어 보이는 것: " + ", ".join(visible))
    if land.lying:
        lines.append("바닥에 놓인 것: " + ", ".join(describe(t, name) for t in land.lying[:8]))
    if any(p.grown for p in land.plantings):
        lines.append("땅에 묻었던 곳에서 싹이 자라 있다")
    if land.corpses:
        lines.append(f"시신 {len(land.corpses)}구")
    return lines


def feelings(world: World, name: str) -> list[str]:
    """Body and mind in one stream, strongest first: a parched throat does not hide a restless mind, nor the other way."""
    person = world.people[name]
    lines = physiology.signals(person.body, world.config) + minds.signals(person.mind)
    return [text for _, text in sorted(lines, key=lambda s: -s[0])] or ["몸도 마음도 별다른 것이 없다"]


def facts(world: World, name: str, slot: str = "새벽") -> list[str]:
    person = world.people[name]
    others = [p.name for p in world.at(person.location) if p.name != name]
    known = world.acquaintances.get(name, set())
    who = [n if n in known else f"처음 보는 사람 {n}" for n in others]
    return [
        f"지금 있는 곳: {person.location}",
        f"날씨: {weather_words(world, slot)}",
        "지금 몸과 마음에 오는 것: " + " / ".join(feelings(world, name)),
        "몸에 걸친 것: " + (", ".join(describe(t, name) for t in person.worn) or "없음"),
        "이곳에 있는 사람: " + (", ".join(who) or "없음"),
    ]


def known_places(world: World, name: str) -> list[str]:
    person = world.people[name]
    lines = []
    for place in sorted(person.known_places):
        if place == person.location:
            continue
        route = world.map.route(person.location, place)
        if route is not None:
            lines.append(f"{place}: {route[1]}칸")
    return lines


def known_lines(world: World, name: str) -> list[str]:
    knowledge = world.knowledge.get(name)
    return [e.text for e in knowledge.recent(world.config.knowledge_prompt_window)] if knowledge else []


def _section(title: str, lines: list[str], numbered: bool = False) -> str:
    if not lines:
        return ""
    body = "\n".join((f"{i}. {line}" if numbered else f"- {line}") for i, line in enumerate(lines, 1))
    return f"{title}\n{body}\n\n"


def plan_prompt(world: World, name: str) -> str:
    return (
        f"당신은 {name}입니다. 오늘은 {world.day}번째 날입니다. 하루는 {'·'.join(SLOTS)}으로 흘러갑니다.\n\n"
        f"{_section('당신에 대한 사실:', facts(world, name))}"
        f"{_section('지니고 있는 것:', carried_lines(world, name), numbered=True) or '지니고 있는 것: 없음' + chr(10) + chr(10)}"
        f"{_section('주위에 보이는 것:', surroundings(world, name))}"
        f"{_section('당신이 아는 곳과 지금 있는 곳에서 가는 데 걸리는 시간(칸):', known_places(world, name))}"
        f"{_section('당신이 겪었거나 전해 들은 것 (오래된 것부터):', known_lines(world, name))}"
        "오늘 하루를 어떻게 보낼지 자유롭게 말하라. 무엇을 하든, 누구와 함께하든, 쉬든 모두 당신이 정한다. "
        "지니고 있는 물건은 번호나 생김새로, 사람이나 장소는 이름 그대로 말하라. 어제와 똑같이 보내려면 same_as_yesterday를 true로 하라.\n"
        "plan에 오늘 할 일을, reasoning에는 그러고 싶은 속마음을 한두 마디로 적으라. JSON으로만 답하라."
    )


def reaction_prompt(world: World, name: str, slot: str, situation: str) -> str:
    person = world.people[name]
    return (
        f"당신은 {name}입니다. 지금은 {world.day}번째 날 {slot}, 당신은 {person.location}에 있습니다.\n\n"
        f"{_section('당신에 대한 사실:', facts(world, name, slot))}"
        f"{_section('지니고 있는 것:', carried_lines(world, name), numbered=True)}"
        f"{_section('당신이 겪었거나 전해 들은 것 (최근):', known_lines(world, name)[-8:])}"
        f"지금 이 순간 일어나고 있는 일: {situation}\n\n"
        "이 순간 어떻게 하겠는가? 무엇이든 괜찮고 아무것도 하지 않아도 된다. "
        "response에 할 행동이나 할 말을, reasoning에 이유를 적으라. JSON으로만 답하라."
    )


__all__ = ["DayDeclaration", "Reaction", "plan_prompt", "reaction_prompt", "facts", "carried_lines", "known_lines", "SPECIES", "shelter_at"]
