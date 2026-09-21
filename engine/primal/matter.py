"""Matter: what things are made of. Property names are for the engine only and never reach a person."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# 0..1 unless noted. weight and nutrition may exceed 1.
PROPS = (
    "hardness", "brittleness", "sharpness", "weight", "flexibility", "plasticity", "porosity", "concavity",
    "flammability", "nutrition", "toxicity", "sweetness", "ferment", "insulation", "fiber", "moisture",
    "fired", "cooked", "spoil", "germination", "roughness", "scraped", "water", "reach", "evenness",
    "bones", "parasites", "bone_lodge",
)


@dataclass(frozen=True)
class Template:
    kind: str
    props: dict[str, float]
    varies: float = 0.15
    drawn: tuple[str, ...] = ()   # props every individual gets anew from 0 to 1 (how its parts happen to lie)


def _t(kind: str, varies: float = 0.15, drawn: tuple[str, ...] = (), **props: float) -> Template:
    return Template(kind, dict(props), varies, drawn)


# Natural things only: what is lying around, growing or walking in the land. Nothing made is listed here.
TEMPLATES: dict[str, Template] = {t.kind: t for t in [
    _t("부싯돌", hardness=0.8, brittleness=0.8, weight=0.5),
    _t("강돌", hardness=0.9, brittleness=0.2, weight=0.7),
    _t("사암", hardness=0.5, brittleness=0.5, weight=0.6, roughness=0.8),
    _t("점토", plasticity=0.3, moisture=0.3, porosity=0.7, hardness=0.1, weight=0.5),
    _t("나뭇가지", hardness=0.3, flexibility=0.5, flammability=0.7, moisture=0.25, weight=0.2, reach=0.6),
    _t("통나무", hardness=0.5, flammability=0.6, moisture=0.4, weight=1.0, reach=0.8),
    _t("나무껍질", fiber=0.4, flexibility=0.6, flammability=0.6, moisture=0.2, weight=0.1, insulation=0.2),
    _t("풀", fiber=0.5, flexibility=0.9, flammability=0.8, moisture=0.35, weight=0.05, insulation=0.15),
    _t("산딸기", nutrition=0.25, sweetness=0.8, moisture=0.8, weight=0.05),
    _t("들사과", nutrition=0.35, sweetness=0.5, moisture=0.7, weight=0.15),
    # glacial central Korea (Hanam pollen and macrofossils): Korean pine dominant on the plateau, Artemisia common
    _t("잣", nutrition=0.35, hardness=0.5, moisture=0.1, weight=0.05, germination=0.3),
    # the Olduvai basin (2026-09-17): what foragers on this plain live on - tubers dug from the ground, baobab pods,
    # Grewia berries, wild honey and grass seed
    _t("덩이줄기", nutrition=0.5, moisture=0.6, hardness=0.3, weight=0.3, germination=0.2),
    _t("바오바브 열매", nutrition=0.45, sweetness=0.5, moisture=0.2, hardness=0.4, weight=0.2, germination=0.25),
    _t("들열매", nutrition=0.2, sweetness=0.7, moisture=0.7, weight=0.03),
    _t("벌꿀", nutrition=0.9, sweetness=1.0, moisture=0.3, weight=0.1),
    _t("아카시아 씨", nutrition=0.3, hardness=0.6, moisture=0.1, weight=0.03, germination=0.3),
    _t("쑥", nutrition=0.1, fiber=0.3, moisture=0.6, weight=0.05),
    _t("도토리", nutrition=0.5, toxicity=0.6, hardness=0.3, moisture=0.2, weight=0.05, germination=0.3),
    _t("버섯", nutrition=0.3, moisture=0.8, weight=0.05),
    _t("붉은 버섯", nutrition=0.2, toxicity=0.9, moisture=0.8, weight=0.05),
    _t("칡뿌리", nutrition=0.6, toxicity=0.1, hardness=0.3, fiber=0.3, moisture=0.5, weight=0.3),
    _t("토란", nutrition=0.6, toxicity=0.5, moisture=0.6, weight=0.3),
    _t("들풀 씨앗", nutrition=0.2, germination=0.8, moisture=0.1, weight=0.02),
    _t("새알", nutrition=0.4, moisture=0.7, weight=0.05),
    # river fish have fine bones, and raw freshwater fish carry fluke cysts (Clonorchis, long common in Korea)
    # bone_lodge: how this fish's fine bones happen to lie, set when the fish is made, so whether a bite sticks follows
    # from the fish and the eater (body.eat), not from a roll at the moment of eating
    _t("물고기", nutrition=0.6, moisture=0.8, weight=0.3, bones=0.6, parasites=0.5, drawn=("bone_lodge",)),
    _t("고기", nutrition=0.8, moisture=0.7, weight=0.4),
    _t("지방", nutrition=0.9, flammability=0.6, moisture=0.3, weight=0.2),
    _t("가죽", fiber=0.6, flexibility=0.4, insulation=0.3, moisture=0.6, weight=0.4),
    _t("뼈", hardness=0.6, brittleness=0.4, sharpness=0.05, weight=0.2),
    _t("뿔", hardness=0.7, brittleness=0.3, sharpness=0.2, weight=0.2),
    _t("힘줄", fiber=0.9, flexibility=0.8, moisture=0.5, weight=0.05),
    _t("물", water=1.0, moisture=1.0, weight=0.2, varies=0.0),
    _t("재", weight=0.05, varies=0.0),
    _t("숯", flammability=0.95, hardness=0.2, weight=0.1),
]}

FOOD_KINDS = frozenset({"산딸기", "들사과", "도토리", "버섯", "붉은 버섯", "칡뿌리", "토란", "들풀 씨앗", "새알", "물고기", "고기", "지방",
                        "잣", "쑥"})
CLAY_KINDS = frozenset({"점토"})
STONE_KINDS = frozenset({"부싯돌", "강돌", "사암"})


@dataclass
class Thing:
    id: int
    kind: str
    props: dict[str, float]
    shape: str = ""
    parts: list[Thing] = field(default_factory=list)
    contents: list[Thing] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)   # person -> what they call it
    history: list[str] = field(default_factory=list)       # the truth of what was done to it, for the records
    handled_by: set[str] = field(default_factory=set)      # people who have held it: they know how it feels in the hand
    tested: dict[str, set[str]] = field(default_factory=dict)  # person -> what they found out by trying it

    def p(self, name: str) -> float:
        return self.props.get(name, 0.0)

    def set(self, name: str, value: float, cap: float | None = 1.0) -> None:
        self.props[name] = max(0.0, value if cap is None else min(cap, value))

    @property
    def is_food(self) -> bool:
        return self.p("nutrition") > 0 and self.p("hardness") < 0.6


class Maker:
    def __init__(self, rng: random.Random, start: int = 1) -> None:
        self.rng = rng
        self.next_id = start

    def new_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1

    def make(self, kind: str) -> Thing:
        template = TEMPLATES[kind]
        props = {}
        for name, value in template.props.items():
            spread = 1.0 + self.rng.uniform(-template.varies, template.varies)
            props[name] = value * spread if name in ("weight", "nutrition") else min(1.0, max(0.0, value * spread))
        for name in template.drawn:
            props[name] = self.rng.random()
        return Thing(id=self.new_id(), kind=kind, props=props)

    def derive(self, kind: str, props: dict[str, float], shape: str = "") -> Thing:
        return Thing(id=self.new_id(), kind=kind, props=dict(props), shape=shape)
