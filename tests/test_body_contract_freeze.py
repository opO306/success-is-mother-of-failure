"""Human-Realizable Body Contract v1, frozen (designer decision Q4/Q6, 2026-09-24).

The body is fixed BEFORE any world is designed against it: a world accepts
the body, the body is never adjusted to a world (RULES, constitution art. 26).
So the contract text -- sections 1 to 8 of
docs/current/HUMAN_REALIZABLE_BODY_CONTRACT_V1.md -- is pinned by content.
Section 9 (open items the implementer found) stays editable.

If this fails, do NOT update the digest to make it pass. A change to the body
is a new contract version (v2) in a new file, decided by the designer.
Line endings are normalised so a checkout setting cannot break or fake it.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "current" / "HUMAN_REALIZABLE_BODY_CONTRACT_V1.md"
FROZEN_SECTIONS_1_TO_8 = "50517c6aed969dd9f9661b987678d5dc62e890cfd35262eaf985a8a6ff0bd750"


def _contract_text() -> bytes:
    text = DOC.read_bytes().replace(b"\r\n", b"\n")
    return text.split("\n## 9.".encode("utf-8"), 1)[0]


def test_body_contract_is_unchanged() -> None:
    assert hashlib.sha256(_contract_text()).hexdigest() == FROZEN_SECTIONS_1_TO_8, (
        "the body contract is frozen -- make a v2 instead of editing sections 1-8")


def test_the_frozen_part_holds_the_decisions() -> None:
    text = _contract_text().decode("utf-8")
    for decided in ("두 손", "독립 표본 공급원", "state clone", "제17조", "특정 세계를 보기 전에"):
        assert decided in text


def test_constitution_has_article_26_scoped_to_researcher_b() -> None:
    constitution = (DOC.parents[2] / "PROJECT_CONSTITUTION.md").read_text(encoding="utf-8")
    article = constitution.split("## 제26조", 1)[1]
    assert "연구자 B에게만 적용" in article and "제17조" in article and "되감기지 않는다" in article
