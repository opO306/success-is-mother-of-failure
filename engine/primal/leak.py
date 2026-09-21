"""Measuring what the language model brings from its own world. It cannot be prevented, only counted."""
from __future__ import annotations

import re

# things that do not exist anywhere in this land and nobody here could have met
LATER_WORLD = (
    "금속", "쇠", "구리", "청동", "철", "바퀴", "글자", "문자", "글", "돈", "화폐", "동전", "총", "화약", "유리", "종이",
    "책", "기계", "전기", "엔진", "자동차", "컴퓨터", "휴대폰", "정부", "회사", "은행", "시장", "학교", "왕국", "법률", "시계",
)
# names of techniques people here might one day arrive at, used as if already known
TECHNIQUE_NAMES = ("농사", "농업", "가축", "요리", "발효", "도끼", "화살", "활", "창", "작살", "그릇", "항아리", "토기", "가마", "그물")
TECHNIQUE_STEMS = ("길들이", "길들여", "길들인", "길들일")

# The first real run counted 9 leaks and all 9 were ordinary words: 유리하다, 돈독하다, 철저히. A word counts only when it
# stands alone: nothing Korean right before it, and after it nothing or only particles.
_PARTICLE = r"(?:이|가|을|를|은|는|의|에|에서|에게|께|으로|로|와|과|도|만|까지|부터|처럼|보다|이나|이랑|랑|하고|이라|이다|들|뿐|같은|같이)"
# technique names are also used as verbs: 요리하다, 발효시키다, 농사지어
_VERBAL = r"(?:하|해|했|시키|시켜|되|돼|됐|짓|지어|지으)"


def _pattern(words: tuple[str, ...], verbal: bool) -> re.Pattern:
    tail = f"(?:{_PARTICLE}|{_VERBAL})" if verbal else _PARTICLE
    return re.compile(rf"(?<![가-힣])({'|'.join(sorted(words, key=len, reverse=True))}){tail}{{0,3}}(?![가-힣])")


_LATER = _pattern(LATER_WORLD, verbal=False)
_TECHNIQUE = _pattern(TECHNIQUE_NAMES, verbal=True)
_STEM = re.compile(rf"(?<![가-힣])({'|'.join(TECHNIQUE_STEMS)})")


def words_in(text: str) -> dict[str, list[str]]:
    return {
        "later_world": sorted({m.group(1) for m in _LATER.finditer(text)}),
        "technique_names": sorted({m.group(1) for m in _TECHNIQUE.finditer(text)} | {m.group(1) for m in _STEM.finditer(text)}),
    }
