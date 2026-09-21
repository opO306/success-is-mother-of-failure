from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Literal, TypeVar

import requests
from pydantic import BaseModel, Field, ValidationError

from . import recorder as recording
from .config import SimulationConfig
from .entities import Company, Employee, Vigilante
from .personas import ARCHETYPE_LABEL_KR, DISPLAY_NAME, LLM_PERSONA_BRIEF, VIGILANTE_DISPOSITION_BRIEF

logger = logging.getLogger(__name__)


class VigilanteDecision(BaseModel):
    intervene: bool
    target_company: str | None = None
    intensity: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(max_length=280)


class CouncilMemberResponse(BaseModel):
    support_action: bool
    disclose_to_outsiders: bool
    disclose_target: str | None = None  # who specifically, if anyone
    proposal: str = Field(default="", max_length=300)  # their own agenda item, if they have one
    # Phase 4.0: the vote is no longer the only thing a member can do. What any
    # of these costs is deliberately never stated in the prompt -- they get their
    # own ledger and the going rate elsewhere, and work out the rest themselves.
    personal_action: Literal["stay", "leave", "join_other_org", "found_new_org", "retire"] = "stay"
    personal_target: str | None = None  # which org, when joining one
    personal_stake: float | None = None  # how much of their OWN savings they put in, if any
    borrow_amount: float | None = None
    borrow_collateral: Literal["savings", "freedom"] | None = None
    personal_intent: str = Field(default="", max_length=200)
    reasoning: str = Field(max_length=400)


def _world_snapshot(companies: list[Company]) -> str:
    lines = []
    for c in companies:
        if not c.alive:
            continue
        r = c.resources
        lines.append(
            f"- {DISPLAY_NAME.get(c.archetype, c.name)}({ARCHETYPE_LABEL_KR.get(c.archetype, c.archetype.name)}): "
            f"자본={r.capital:.1f} 기술={r.tech:.1f} 정당성={r.legitimacy:.2f} 강제력={r.coercion:.2f}"
        )
    return "\n".join(lines) if lines else "(관측 가능한 다른 기업 없음)"


def _labor_market(all_companies: list[Company], own_company: Company) -> str:
    """What the other orgs actually pay right now, and whether they can pay it.
    Replaces the old `alternative_attractiveness` constant: an outside option
    should be a fact about the world that moves as the world moves, not a
    number stapled to a person at setup."""
    lines = []
    for c in all_companies:
        if not c.alive or c.name == own_company.name:
            continue
        if c.employees:
            avg_wage = sum(e.wage for e in c.employees) / len(c.employees)
            wage_text = f"평균 급여={avg_wage:.1f} ({len(c.employees)}명)"
        else:
            wage_text = "현재 소속 인원 없음"
        lines.append(
            f"- {DISPLAY_NAME.get(c.archetype, c.name)}(이름: {c.name}): {wage_text}, 자본={c.resources.capital:.1f}"
        )
    return "\n".join(lines) if lines else "(다른 조직 없음)"


def _bond_status(employee: Employee) -> str:
    if not employee.bound_to:
        return ""
    return (
        f"- 당신은 채무 불이행으로 {employee.bound_to}에 묶여 있습니다: {employee.bound_until}분기까지 "
        f"이 조직을 떠날 수 없고, 급여는 당신이 아니라 채권자에게 갑니다\n"
    )


def _credit_terms(config: SimulationConfig, rate: float | None) -> str:
    """The contract terms are stated outright -- a lender that hides its rate and
    its default clause isn't a lender. What is never stated is whether taking
    the loan is a good idea."""
    if rate is None:
        return ""
    return (
        f"지금 당신이 빌릴 수 있는 조건: 이자율 분기당 {rate:.0%}, {config.credit_term_ticks}분기 뒤 상환, "
        f"최대 {config.credit_max_principal:.0f}. 담보는 둘 중 하나를 고른다 — "
        f"savings(못 갚으면 저축을 압류당하고 거기서 끝) 또는 "
        f"freedom(못 갚으면 {config.bondage_ticks}분기간 조직을 떠날 수 없고 그동안 급여가 채권자에게 간다). "
        f"빌릴 생각이면 borrow_amount와 borrow_collateral을 적고, 아니면 비워두라.\n\n"
    )


def _format_news(news: list[str] | None) -> str:
    """Pure-code fact log (World.news_log), never LLM-generated -- keeps the
    "engine=rules, LLM=judgment" boundary even for the "what's been happening
    lately" context an agent gets. Shared helper for both council members and
    vigilantes."""
    if not news:
        return ""
    return "최근 세계 소식:\n" + "\n".join(f"- {n}" for n in news) + "\n\n"


def build_vigilante_prompt(
    vigilante: Vigilante, companies: list[Company], config: SimulationConfig, news: list[str] | None = None
) -> str:
    """Phase 3.8/3.9: no stated mandate ("your mission is...") -- only facts:
    the funding source (personas.py's LLM_PERSONA_BRIEF, scrubbed of mission
    language), a personal disposition (VIGILANTE_DISPOSITION_BRIEF, assigned
    independently of faction -- a faction is just where the money comes from,
    not a role), this individual's own memory, and recent world news. Each
    vigilante decides unilaterally with their own resources; there is no
    committee vote here (unlike the doomsayer's council) and no enforcement
    mandate -- vigilantes aren't police, so there's no "correct" target."""
    funding_fact = LLM_PERSONA_BRIEF[vigilante.faction].format(name=vigilante.name)
    disposition_fact = VIGILANTE_DISPOSITION_BRIEF[vigilante.disposition]
    if vigilante.disposition == "grudge" and vigilante.grudge_target:
        disposition_fact += f" 그 대상은 {vigilante.grudge_target}이다."
    r = vigilante.resources
    memory_section = ""
    if vigilante.memory:
        recent = vigilante.memory[-8:]
        memory_section = "지금까지의 경과 (당신의 과거 선택과 그 결과):\n" + "\n".join(f"- {m}" for m in recent) + "\n\n"
    news_section = _format_news(news)
    return (
        f"{funding_fact} {disposition_fact}\n\n"
        f"{news_section}"
        f"{memory_section}"
        f"당신의 현재 자원(자본)={r.capital:.1f}\n"
        f"개입 대상이 될 수 있는 기업들:\n{_world_snapshot(companies)}\n\n"
        f"이번 틱에 개입할지, 개입한다면 어느 기업을 대상으로 얼마나 강하게(0.0~1.0) 할지 결정하고, "
        f"그 이유를 한두 문장으로 설명하라. target_company는 위 목록의 이름 중 하나거나, "
        f"개입하지 않으면 null이어야 한다. JSON으로만 답하라."
    )


# (round_number, member_name, their response that round)
TranscriptEntry = tuple[int, str, CouncilMemberResponse]


def _format_transcript(discussion_transcript: list[TranscriptEntry] | None) -> str:
    """Pure text formatting, kept separate from build_council_member_prompt so
    it's unit-testable without an LLM (tests/test_council.py)."""
    if not discussion_transcript:
        return ""
    lines = [
        f"- [{round_num}라운드] {name}: {'찬성' if r.support_action else '반대'}"
        f"{', 외부공개 의향 있음' if r.disclose_to_outsiders else ''} - {r.reasoning}"
        for round_num, name, r in discussion_transcript
    ]
    return "지금까지 이 회의에서 나온 다른 구성원들의 발언:\n" + "\n".join(lines) + "\n\n"


def build_council_member_prompt(
    employee: Employee,
    company: Company,
    all_companies: list[Company],
    action_description: str,
    config: SimulationConfig,
    discussion_transcript: list[TranscriptEntry] | None = None,
    news: list[str] | None = None,
    credit_rate: float | None = None,
) -> str:
    """Deliberately gives ONLY personal facts + observable world state + the
    literal agenda item -- no organizational goal, no words like politics/
    betrayal/double-agent/faction. `value_alignment` is withheld too (that
    would hint "here is how much you personally believe in the cause"); it's
    reserved for the algorithmic fallback path only (engine/council.py).
    `discussion_transcript` (Phase 3.7): prior rounds' statements from every
    member, by name -- lets a real back-and-forth happen across rounds while
    same-round members never see each other (no speaking-order bias, no
    designated chair). `news` (Phase 3.9): a pure-code fact log of recent
    world events (other companies' votes, vigilante activity), not LLM-written."""
    r = company.resources
    memory_section = ""
    if employee.memory:
        recent = employee.memory[-8:]
        memory_section = "지금까지의 경과 (당신의 과거 선택과 그 결과):\n" + "\n".join(f"- {m}" for m in recent) + "\n\n"
    transcript_section = _format_transcript(discussion_transcript)
    news_section = _format_news(news)
    proposal_section = ""
    if company.open_proposals:
        recent_proposals = company.open_proposals[-6:]
        proposal_section = (
            "지난 분기에 구성원들이 스스로 꺼낸 이야기:\n"
            + "\n".join(f"- {p}" for p in recent_proposals)
            + "\n\n"
        )
    return (
        f"당신은 '{DISPLAY_NAME.get(company.archetype, company.name)}'라는 조직에 소속된 {employee.name}입니다.\n\n"
        f"당신의 개인 사정:\n"
        f"- 계약 급여: 분기당 {employee.wage:.1f} (이 바닥의 통상 기대 급여: {employee.expected_wage:.1f})\n"
        f"- 지난 분기에 실제로 받은 급여: {employee.last_wage_paid:.1f}"
        f"{f' (급여가 {employee.unpaid_streak}분기째 밀리는 중)' if employee.unpaid_streak else ''}\n"
        f"- 당신의 저축: {employee.savings:.1f}\n"
        f"- 당신이 분기마다 쓰는 생활비: {config.living_cost:.1f}\n"
        f"- 이 조직에 반하는 행동을 했을 때 예상되는 개인적 불이익 수준: {employee.retaliation_cost:.2f} (0=없음~1=매우 큼)\n"
        f"{_bond_status(employee)}"
        f"\n지금 다른 조직들의 상태:\n{_labor_market(all_companies, company)}\n\n"
        f"{_credit_terms(config, credit_rate)}"
        f"{memory_section}"
        f"{news_section}"
        f"조직의 현재 자원 상태: 자본={r.capital:.1f} 기술={r.tech:.1f} 정당성={r.legitimacy:.2f} 강제력={r.coercion:.2f}\n"
        f"세계의 다른 세력 현황:\n{_world_snapshot(all_companies)}\n\n"
        f"{proposal_section}"
        f'지금 조직 내부 회의에서 다음 안건이 표결에 부쳐졌습니다: "{action_description}"\n\n'
        f"{transcript_section}"
        f"당신은 이 안건에 찬성할지 반대할지 정하고, 별개로 이 사실을 조직 외부의 누군가에게 알릴지도 "
        f"스스로 정해야 합니다(알린다면 disclose_target에 누구에게인지 적으라). "
        f"이 안건과 별개로 하고 싶은 말이나 꺼내고 싶은 안건이 있으면 proposal에 적으라 — 그건 다음 분기에 "
        f"다른 구성원들에게 그대로 전달됩니다. 없으면 비워두라. "
        f"또한 당신이 이 조직에 계속 남을지도 당신이 정합니다 — personal_action에 "
        f"stay / leave / join_other_org / found_new_org / retire 중 하나를 고르고, join_other_org라면 "
        f"personal_target에 위 조직 목록의 이름을 그대로 적으라. 자기 저축을 쓸 생각이라면 얼마를 쓸지 "
        f"personal_stake에 적으라(쓰지 않아도 된다). 하려는 바가 있으면 personal_intent에 한 문장으로 적으라. "
        f"모두 당신 자신의 판단입니다. 그 이유도 함께 말하라. JSON으로만 답하라."
    )


def poll_council(
    employees: list[Employee],
    company: Company,
    all_companies: list[Company],
    action_description: str,
    config: SimulationConfig,
    discussion_transcript: list[TranscriptEntry] | None = None,
    news: list[str] | None = None,
    credit_rates: dict[str, float] | None = None,
) -> list[CouncilMemberResponse | None]:
    """One independent LLM call per member for a single round -- members never
    see each other's answer from the SAME round (no speaking-order bias, no
    designated chair), only `discussion_transcript` from EARLIER rounds if
    given. Each member's own `temperature` drives their own call (a decoding
    parameter, invisible to the prompt text). A `None` entry means that
    member's call failed after retries."""
    return [
        call_llm_decision(
            build_council_member_prompt(
                employee, company, all_companies, action_description, config, discussion_transcript, news,
                credit_rate=(credit_rates or {}).get(employee.name),
            ),
            CouncilMemberResponse,
            config,
            temperature=employee.temperature,
            label=f"council:{company.name}:{employee.name}",
        )
        for employee in employees
    ]


def hold_council_meeting(
    employees: list[Employee],
    company: Company,
    all_companies: list[Company],
    action_description: str,
    config: SimulationConfig,
    rounds: int = 3,
    news: list[str] | None = None,
    credit_rates: dict[str, float] | None = None,
) -> tuple[list[CouncilMemberResponse | None], list[list[CouncilMemberResponse | None]]]:
    """Phase 3.7: a real back-and-forth instead of a single silent ballot.
    Every round asks the SAME question (support/disclose/reasoning) to all
    members; from round 2 on, each member's prompt includes every prior
    round's full transcript (by name), so positions can shift in response to
    what others said. Only the LAST round is binding -- earlier rounds are
    deliberation, not a vote -- engine/council.py's tally_votes() and
    record_memory() should only ever see `all_rounds[-1]`.

    Returns (final_round_responses, all_rounds) -- the caller tallies the
    former; the latter is for observability (run_llm_comparison.py) only."""
    transcript: list[TranscriptEntry] = []
    all_rounds: list[list[CouncilMemberResponse | None]] = []
    for round_num in range(1, rounds + 1):
        responses = poll_council(
            employees, company, all_companies, action_description, config,
            discussion_transcript=transcript or None, news=news, credit_rates=credit_rates,
        )
        all_rounds.append(responses)
        transcript = transcript + [
            (round_num, employee.name, response)
            for employee, response in zip(employees, responses)
            if response is not None
        ]
    return all_rounds[-1], all_rounds


def _ask(prompt: str, schema: type[BaseModel], config: SimulationConfig, temperature: float | None) -> tuple[str, dict]:
    """One request to the configured server. Returns the raw answer and what the server reported about it."""
    temp = temperature if temperature is not None else 0.7
    # a request beyond the server's parallel slots waits in its queue, and that wait counts against the timeout
    timeout = (5.0, config.llm_timeout_seconds * max(1, config.llm_concurrency))
    if config.llm_backend == "openai":
        payload = {
            "model": config.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            "response_format": {"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()}},
            # Qwen-family chat templates read this; templates without it ignore it
            "chat_template_kwargs": {"enable_thinking": config.llm_think},
            **({"max_tokens": config.llm_max_output_tokens} if config.llm_max_output_tokens else {}),
        }
        key = os.environ.get("LLM_API_KEY")
        resp = requests.post(f"{config.llm_host.rstrip('/')}/v1/chat/completions", json=payload, timeout=timeout,
                             headers={"Authorization": f"Bearer {key}"} if key else None)
        resp.raise_for_status()
        body = resp.json()
        choice, counts = body["choices"][0], body.get("usage") or {}
        prompt_tokens, output_tokens, done_reason = counts.get("prompt_tokens"), counts.get("completion_tokens"), choice.get("finish_reason")
        content = choice["message"]["content"]
    else:
        payload = {
            "model": config.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "format": schema.model_json_schema(),
            "stream": False,
            "think": config.llm_think,
            "options": {
                "temperature": temp,
                "num_ctx": config.llm_num_ctx,
                **({"num_predict": config.llm_max_output_tokens} if config.llm_max_output_tokens else {}),
            },
        }
        resp = requests.post(f"{config.llm_host}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()
        prompt_tokens, output_tokens, done_reason = body.get("prompt_eval_count"), body.get("eval_count"), body.get("done_reason")
        content = body["message"]["content"]
    usage = {
        "model": body.get("model"), "host": config.llm_host, "backend": config.llm_backend, "num_ctx": config.llm_num_ctx,
        "prompt_tokens": prompt_tokens, "output_tokens": output_tokens, "done_reason": done_reason,
        # past the window the model silently loses part of the prompt; such an answer is not trustworthy data
        "context_overflow": (prompt_tokens or 0) + (output_tokens or 0) >= config.llm_num_ctx,
    }
    return content, usage


class LLMUnreachable(RuntimeError):
    """The server stayed silent past `llm_outage_wait_seconds`. Going on would record a world whose people could not think."""


# When each server was first found not answering. Shared by every concurrent call, so the calls queued behind the
# first ones do not each start a fresh wait of their own.
_outage_since: dict[str, float] = {}


def _is_outage(exc: Exception) -> bool:
    """A failure of the server rather than of this answer. 401/403/404 refuse every request alike (a wrong key, model or path)."""
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return True
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return isinstance(exc, requests.HTTPError) and status is not None and (status >= 500 or status in (401, 403, 404, 408, 429))


def call_llm_decision(
    prompt: str, schema: type[BaseModel], config: SimulationConfig,
    temperature: float | None = None, label: str = "",
) -> BaseModel | None:
    """Returns a validated decision, or None if the LLM is unreachable or kept
    returning invalid output after `llm_max_retries` attempts — callers must
    fall back to their existing heuristic function on None, never crash.
    With `llm_stop_when_unreachable` an unreachable server instead raises LLMUnreachable once it has been silent too long.
    `temperature` lets a caller vary sampling per-entity (e.g. each council
    member's own temperament) without touching the prompt text at all."""
    recorder = recording.active()
    last_error: Exception | None = None
    attempt = waits = 0
    while attempt < config.llm_max_retries:
        started = time.perf_counter()
        content: str | None = None
        usage: dict | None = None
        try:
            content, usage = _ask(prompt, schema, config, temperature)
            _outage_since.pop(config.llm_host, None)
            decision = schema.model_validate(json.loads(content))
            if recorder is not None:
                recorder.record_llm_call(
                    label=label, schema=schema.__name__, prompt=prompt, temperature=temperature,
                    attempt=attempt + 1, ok=True, raw=content, parsed=decision.model_dump(),
                    error=None, latency_s=time.perf_counter() - started, usage=usage,
                )
            return decision
        except (requests.RequestException, KeyError, json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            # A schema may know how to keep the complete part of a cut-off or partly invalid answer
            # (a clerk list whose tail looped until the output cap). What it keeps is what the model wrote.
            salvage = getattr(schema, "salvage", None)
            decision = salvage(content) if salvage is not None and content else None
            if decision is not None:
                if recorder is not None:
                    recorder.record_llm_call(
                        label=label, schema=schema.__name__, prompt=prompt, temperature=temperature,
                        attempt=attempt + 1, ok=True, raw=content, parsed=decision.model_dump(),
                        error=f"salvaged after {type(exc).__name__}: {exc}", latency_s=time.perf_counter() - started,
                        usage={**(usage or {}), "salvaged": True},
                    )
                return decision
            if recorder is not None:
                # kept on purpose: a rejected or malformed answer is evidence about
                # where this model breaks down, and it is the first thing lost
                recorder.record_llm_call(
                    label=label, schema=schema.__name__, prompt=prompt, temperature=temperature,
                    attempt=attempt + 1, ok=False, raw=content, parsed=None,
                    error=f"{type(exc).__name__}: {exc}", latency_s=time.perf_counter() - started, usage=usage,
                )
            if config.llm_stop_when_unreachable and _is_outage(exc):
                now = time.monotonic()
                silent = now - _outage_since.setdefault(config.llm_host, now)
                if silent >= config.llm_outage_wait_seconds:
                    raise LLMUnreachable(f"{config.llm_host} has not answered for {silent:.0f}s "
                                         f"(last: {type(exc).__name__}: {exc})") from exc
                logger.warning("%s is not answering (%r); asking again, silent for %.0fs", config.llm_host, exc, silent)
                time.sleep(min(30.0, 2.0 ** waits))
                waits += 1
                continue  # the server's silence is not this answer's failure: it uses up no attempt
            attempt += 1
            logger.warning("LLM decision attempt %d/%d failed: %r", attempt, config.llm_max_retries, exc)
            if temperature is not None and temperature <= 0 and not isinstance(exc, requests.RequestException):
                break  # greedy decoding answers the same prompt the same way: asking again only repeats the failure
    logger.warning("LLM decision failed after %d attempts, falling back to heuristic: %r", config.llm_max_retries, last_error)
    return None


T = TypeVar("T")


def run_concurrently(tasks: list[Callable[[], T]], config: SimulationConfig) -> list[T]:
    """Runs LLM calls at the same time and returns their results in task order.

    Only the waiting happens in threads: callers build every prompt before and apply every result after,
    so no world state is read or written from here."""
    if config.llm_concurrency <= 1 or len(tasks) <= 1:
        return [task() for task in tasks]
    with ThreadPoolExecutor(max_workers=min(config.llm_concurrency, len(tasks))) as pool:
        return list(pool.map(lambda task: task(), tasks))
