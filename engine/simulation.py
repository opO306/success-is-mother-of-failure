from __future__ import annotations

import random
from dataclasses import dataclass, field

from . import clerk, llm_agent
from . import recorder as recording
from .agent_prompts import Declaration, build_agent_vote_prompt, build_declaration_prompt, hold_agent_meeting
from .bankruptcy import CompanyState, apply_state
from .clerk import Operation, OrgOperation
from .config import SimulationConfig
from .council import CouncilOutcome, collect_proposals, record_memory, tally_votes
from .credit import Bank, CreditEvent, issue_loan, quoted_rate, release_bonded, settle_credit
from .entities import Company, CompanyArchetype, Employee, IndividualAgent, Proposal, Vigilante
from .exits import MemberExitEvent, apply_member_exits
from .formulas import apply_legitimacy_event, currency_value, decay_legitimacy_recovery, necessity
from .heuristics import (
    _ordinary_income,
    apply_company_heuristic,
    apply_individual_heuristic,
    apply_vigilante_heuristic,
)
from .interactions import (
    EspionageEvent,
    TradeEvent,
    VigilanteInterventionEvent,
    WmdAttemptEvent,
    attempt_espionage,
    attempt_wmd,
    run_trade_round,
)
from .knowledge import Knowledge, format_entries
from .llm_agent import CouncilMemberResponse, hold_council_meeting
from .payroll import PayrollEvent, run_payroll
from .personas import DISPLAY_NAME, VIGILANTE_DISPOSITION_BRIEF
from .physics import employer_of, find_person, money_of, resolve_org_ops, resolve_person_ops, tell, tell_members
from .scheduler import due_persons


@dataclass
class Tick:
    index: int
    company_states: dict[str, CompanyState]
    currency_values: dict[str, float]
    trades: list[TradeEvent] = field(default_factory=list)
    espionage_events: list[EspionageEvent] = field(default_factory=list)
    wmd_attempts: list[WmdAttemptEvent] = field(default_factory=list)
    vigilante_interventions: list[VigilanteInterventionEvent] = field(default_factory=list)
    council_votes: list[CouncilOutcome] = field(default_factory=list)
    member_exits: list[MemberExitEvent] = field(default_factory=list)
    payroll: list[PayrollEvent] = field(default_factory=list)
    credit: list[CreditEvent] = field(default_factory=list)


@dataclass
class World:
    companies: list[Company]
    individuals: list[IndividualAgent] = field(default_factory=list)
    vigilantes: list[Vigilante] = field(default_factory=list)
    config: SimulationConfig = field(default_factory=SimulationConfig)
    rng: random.Random = field(default_factory=random.Random)
    history: list[Tick] = field(default_factory=list)
    # company -> (roster at meeting time, every round's responses). The roster is
    # captured here because members can leave right after a vote (engine/exits.py),
    # so an end-of-run roster would no longer line up with these responses.
    last_meeting_transcripts: dict[str, tuple[list[str], list[list[CouncilMemberResponse | None]]]] = field(
        default_factory=dict
    )
    news_log: list[str] = field(default_factory=list)  # Phase 3.9: pure-code fact log, never LLM-written
    label: str = ""  # distinguishes worlds sharing one recorded run (e.g. heuristic vs llm)
    bank: Bank = field(default_factory=Bank)
    mode: str = "formula"  # "agent": code holds only truth and arithmetic; every decision comes from a person
    knowledge: dict[str, Knowledge] = field(default_factory=dict)
    acquaintances: dict[str, set[str]] = field(default_factory=dict)
    next_wake: dict[str, int] = field(default_factory=dict)
    last_acted: dict[str, int] = field(default_factory=dict)

    def _add_news(self, entry: str) -> None:
        self.news_log.append(entry)

    @staticmethod
    def _format_exit_news(tick_index: int, event: MemberExitEvent) -> str:
        """A departure is the one kind of news that carries someone's own words
        (`intent`) rather than only engine facts -- that sentence is what other
        agents actually get to react to."""
        label = {
            "leave": "조직을 떠남",
            "join_other_org": "다른 조직으로 옮김",
            "found_new_org": "조직을 떠나 새 조직을 세움",
            "retire": "일을 그만둠",
        }[event.action]
        if event.blocked_reason:
            return f"틱 {tick_index}: {event.company}의 {event.member}이(가) {label}으려 했으나 무산됨 ({event.blocked_reason})."
        line = f"틱 {tick_index}: {event.company}의 {event.member}이(가) {label}"
        if event.became:
            line += f" ({event.became})"
        if event.intent:
            line += f". 본인의 말: {event.intent}"
        return line + "."

    def _council_vote(self, company: Company, action_description: str) -> CouncilOutcome:
        """Each member sees only their own personal facts + their own
        accumulated memory of past votes + (from round 2 on) every prior
        round's statements this meeting + recent world news -- never the
        org's stated goal -- so a "yes" or a disclosure has to come from
        their own reasoning, not from being told what to think. Majority of
        the LAST round decides `proceeds`; any single disclosure exposes the
        vote regardless of the majority (both are pure-code aggregation, not
        the LLM's call)."""
        credit_rates = {
            e.name: quoted_rate(
                self.config, unpaid_streak=e.unpaid_streak, savings=e.savings,
                has_income=company.resources.capital > 0,
            )
            for e in company.employees
        }
        final_round, all_rounds = hold_council_meeting(
            company.employees, company, self.companies, action_description, self.config,
            rounds=self.config.council_discussion_rounds, news=self.news_log[-10:],
            credit_rates=credit_rates,
        )
        roster = [e.name for e in company.employees]
        self.last_meeting_transcripts[company.name] = (roster, all_rounds)
        recorder = recording.active()
        if recorder is not None:
            # every round, permanently -- last_meeting_transcripts is wiped each tick
            recorder.record_meeting(
                tick_index=len(self.history), company=company.name,
                action_description=action_description, roster=roster, all_rounds=all_rounds,
            )
        outcome = tally_votes(final_round, company.employees, self.config, self.rng)
        outcome.action_description = action_description
        outcome.company = company.name
        return outcome

    def _run_espionage_round(self) -> list[EspionageEvent]:
        alive = [c for c in self.companies if c.alive]
        if len(alive) < 2:
            return []
        leader = max(alive, key=lambda c: c.resources.tech)
        events: list[EspionageEvent] = []
        for company in alive:
            if company.name == leader.name:
                continue
            if company.resources.tech >= 0.8 * leader.resources.tech:
                continue
            if self.rng.random() < self.config.espionage_attempt_probability:
                event = attempt_espionage(company, leader, self.config, self.rng)
                if event is not None:
                    events.append(event)
        return events

    def _process_borrowing(
        self, company: Company, outcome: CouncilOutcome, tick_index: int
    ) -> list[CreditEvent]:
        events: list[CreditEvent] = []
        by_name = {e.name: e for e in company.employees}
        for result in outcome.member_results:
            if not result.borrow_amount or result.borrow_amount <= 0:
                continue
            employee = by_name.get(result.name)
            if employee is None:
                continue
            collateral = result.borrow_collateral or "savings"
            rate = quoted_rate(
                self.config, unpaid_streak=employee.unpaid_streak, savings=employee.savings,
                has_income=company.resources.capital > 0,
            )
            loan, event = issue_loan(
                self.bank, borrower=employee.name, borrower_kind="employee",
                principal=result.borrow_amount, collateral=collateral, rate=rate,
                tick=tick_index, config=self.config,
            )
            events.append(event)
            if loan is not None:
                employee.savings += loan.principal
                self._add_news(
                    f"틱 {tick_index}: {employee.name}이(가) {loan.principal:.1f}을 빌림 "
                    f"(이자 {loan.rate:.0%}/분기, 담보={collateral}, {loan.due_tick}분기 상환)."
                )
        return events

    def _doomsayer_council_tick(
        self, company: Company, tick_index: int, wmd_attempts: list[WmdAttemptEvent], council_votes: list[CouncilOutcome]
    ) -> CouncilOutcome | None:
        r = company.resources
        ready = r.tech >= self.config.wmd_tech_threshold and r.coercion >= self.config.wmd_coercion_threshold

        if company.decision_mode != "llm":
            if ready:
                wmd_attempts.append(attempt_wmd(company, self.config, self.rng))
            return None

        if not ready:
            # Phase 3.6: a recurring, low-stakes vote from tick 0 -- whether
            # THIS quarter's reinvestment goes toward weapons capability at
            # all. Only when many such votes accumulate does "ready" ever
            # become true; there is no head start.
            action_description = "이번 분기 재투자 자원을 무기 개발(기술/강제력)에 투입한다"
            outcome = self._council_vote(company, action_description)
            council_votes.append(outcome)
            if outcome.disclosed:
                apply_legitimacy_event(
                    company, exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=self.config
                )
            if outcome.proceeds:
                # same mechanical reinvestment the heuristic uses (heuristics.py's
                # _heuristic_doomsayer skips it for llm-mode so this is the only path)
                reinvest = r.capital * 0.4
                r.capital -= reinvest
                r.tech += reinvest * 0.4
                r.coercion += reinvest * 0.3
            record_memory(company.employees, outcome, tick_index, r, action_description)
            self._add_news(
                f"틱 {tick_index}: {DISPLAY_NAME.get(company.archetype, company.name)} 내부 표결('{action_description}') "
                f"{'가결' if outcome.proceeds else '부결'}{', 외부에 알려짐' if outcome.disclosed else ''}."
            )
            return outcome

        action_description = "이번 틱에 세계 종결급(핵급 이상) 무기를 실행한다"
        outcome = self._council_vote(company, action_description)
        council_votes.append(outcome)
        if outcome.proceeds:
            if outcome.disclosed:
                apply_legitimacy_event(
                    company, exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=self.config
                )
            wmd_attempts.append(
                WmdAttemptEvent(
                    company=company.name, leaked=outcome.disclosed,
                    leak_probability=(outcome.votes_for / outcome.votes_total) if outcome.votes_total else 0.0,
                )
            )
        record_memory(company.employees, outcome, tick_index, r, action_description)
        self._add_news(
            f"틱 {tick_index}: {DISPLAY_NAME.get(company.archetype, company.name)} 내부 표결('{action_description}') "
            f"{'가결' if outcome.proceeds else '부결'}{', 외부에 알려짐' if outcome.disclosed else ''}."
        )
        return outcome

    def _safety_coordinator_council_tick(
        self, company: Company, tick_index: int, council_votes: list[CouncilOutcome]
    ) -> CouncilOutcome | None:
        """Mirrors the doomsayer's two-phase vote structurally (invest -> then
        act), reusing hold_council_meeting/tally_votes/record_memory as-is.
        Readiness is investigative capacity (tech, repurposed) built without a
        capital cost, consistent with this archetype's chronic capital
        shortage. Once ready, the TARGET is picked by pure code (the alive
        company with the highest tech+coercion -- an observable danger proxy
        already visible to the council in their own world-snapshot section,
        not a hint about who that happens to be), and the council votes on
        whether to publicly expose that specific company."""
        if company.decision_mode != "llm":
            return None

        r = company.resources
        ready = r.tech >= self.config.safety_investigation_threshold

        if not ready:
            action_description = "이번 분기 재투자 자원을 감시·조사 역량 강화에 투입한다"
            outcome = self._council_vote(company, action_description)
            council_votes.append(outcome)
            if outcome.disclosed:
                apply_legitimacy_event(
                    company, exposure=1.0, victim_weight=1.0, evasion_success=0.0, config=self.config
                )
            if outcome.proceeds:
                r.tech += self.config.safety_investigation_gain_per_vote
            record_memory(company.employees, outcome, tick_index, r, action_description)
            self._add_news(
                f"틱 {tick_index}: {DISPLAY_NAME.get(company.archetype, company.name)} 내부 표결('{action_description}') "
                f"{'가결' if outcome.proceeds else '부결'}{', 외부에 알려짐' if outcome.disclosed else ''}."
            )
            return outcome
        else:
            candidates = [c for c in self.companies if c.alive and c.name != company.name]
            if not candidates:
                return None
            target = max(candidates, key=lambda c: c.resources.tech + c.resources.coercion)
            action_description = f"이번 틱에 {DISPLAY_NAME.get(target.archetype, target.name)}의 활동에 대한 공개 조사 결과를 발표한다"
            outcome = self._council_vote(company, action_description)
            council_votes.append(outcome)
            if outcome.proceeds:
                target.resources.legitimacy = max(
                    0.0,
                    target.resources.legitimacy
                    - self.config.safety_exposure_legitimacy_penalty * (outcome.votes_for / outcome.votes_total),
                )
                self._add_news(
                    f"틱 {tick_index}: {DISPLAY_NAME.get(company.archetype, company.name)}이(가) "
                    f"{DISPLAY_NAME.get(target.archetype, target.name)}의 활동에 대한 공개 조사 결과를 발표함."
                )
            record_memory(company.employees, outcome, tick_index, r, action_description)
            return outcome

    def tick(self) -> Tick:
        if self.mode == "agent":
            return self._agent_tick()
        self.last_meeting_transcripts = {}  # only this tick's meetings -- 2 companies can hold councils now
        spawned: list[Company] = []
        for company in self.companies:
            if not company.alive:
                continue
            child = apply_company_heuristic(company, self.companies, self.config, self.rng)
            if child is not None:
                spawned.append(child)
        self.companies.extend(spawned)

        for individual in self.individuals:
            if individual.alive:
                apply_individual_heuristic(individual, self.companies, self.config, self.rng)

        vigilante_interventions: list[VigilanteInterventionEvent] = []
        for vigilante in self.vigilantes:
            if vigilante.alive:
                event = apply_vigilante_heuristic(
                    vigilante, self.companies, self.config, self.rng, news=self.news_log[-10:]
                )
                if event is not None:
                    vigilante_interventions.append(event)
                    if event.intervened:
                        self._add_news(f"{vigilante.name}이(가) {event.target}에 개입함(강도 {event.intensity:.2f}).")

        for company in self.companies:
            if company.alive and not company.is_hive_mind:
                decay_legitimacy_recovery(company, self.config, target=company.resources.legitimacy_baseline)

        trades = run_trade_round(self.companies, self.config, self.rng)
        espionage_events = self._run_espionage_round()
        # before the councils meet, so a member's ledger reflects the quarter they
        # are about to vote on the back of
        payroll_events = run_payroll(self.companies, self.config, bank=self.bank, tick=len(self.history))
        for event in payroll_events:
            if event.unpaid_members:
                self._add_news(
                    f"{event.company}이(가) 이번 분기 급여를 다 지급하지 못함 "
                    f"({event.paid:.1f}/{event.owed:.1f})."
                )

        wmd_attempts: list[WmdAttemptEvent] = []
        council_votes: list[CouncilOutcome] = []
        member_exits: list[MemberExitEvent] = []
        founded: list[Company] = []
        departed: list[IndividualAgent] = []
        tick_index = len(self.history)
        credit_events: list[CreditEvent] = settle_credit(
            self.bank, self.companies, tick_index, self.config
        )
        for event in credit_events:
            if event.kind in ("defaulted", "seized"):
                self._add_news(f"틱 {tick_index}: {event.borrower} 채무 불이행 — {event.detail}")
        for company in self.companies:
            for name in release_bonded(company.employees, tick_index):
                self._add_news(f"틱 {tick_index}: {name}의 채무 구속이 끝남.")
        for company in list(self.companies):  # a founded splinter must not vote in the tick it was founded
            if not company.alive:
                continue
            if company.archetype is CompanyArchetype.DOOMSAYER:
                outcome = self._doomsayer_council_tick(company, tick_index, wmd_attempts, council_votes)
            elif company.archetype is CompanyArchetype.SAFETY_COORDINATOR:
                outcome = self._safety_coordinator_council_tick(company, tick_index, council_votes)
            else:
                continue
            if outcome is None:
                continue
            for raised in collect_proposals(company, outcome):
                self._add_news(f"틱 {tick_index}: {company.name} 내부에서 나온 이야기 — {raised}")
            # before exits on purpose: money borrowed this quarter is money they can
            # walk out the door with, which is the whole point of having credit
            credit_events.extend(self._process_borrowing(company, outcome, tick_index))
            exits, spawned_orgs, spawned_individuals = apply_member_exits(company, outcome, self.companies)
            for event in exits:
                self._add_news(self._format_exit_news(tick_index, event))
            if exits and not company.employees:
                # an org everyone walked out of has nobody left to act for it
                company.alive = False
                self._add_news(f"틱 {tick_index}: {company.name}에 남은 인원이 아무도 없음.")
            member_exits.extend(exits)
            founded.extend(spawned_orgs)
            departed.extend(spawned_individuals)
        self.companies.extend(founded)
        self.individuals.extend(departed)

        states: dict[str, CompanyState] = {}
        values: dict[str, float] = {}
        for company in self.companies:
            state = apply_state(company, self.config)
            states[company.name] = state
            necessity_score = necessity(company.resources.tech, num_alternative_suppliers=len(company.copied_by))
            values[company.name] = currency_value(company.resources, necessity_score, self.config)

        record = Tick(
            index=len(self.history),
            company_states=states,
            currency_values=values,
            trades=trades,
            espionage_events=espionage_events,
            wmd_attempts=wmd_attempts,
            vigilante_interventions=vigilante_interventions,
            council_votes=council_votes,
            member_exits=member_exits,
            payroll=payroll_events,
            credit=credit_events,
        )
        self.history.append(record)
        recorder = recording.active()
        if recorder is not None:
            recorder.record_tick(tick_index=record.index, world=self, tick=record)
            recorder.record_news(self.news_log)
        return record

    def _own_facts(self, name: str) -> list[str]:
        person = find_person(self, name)
        if person is None:
            return []
        c = self.config
        if isinstance(person, Employee):
            company = employer_of(self, name)
            facts = [
                f"소속: {company.name}" if company is not None else "소속: 없음",
                f"계약 급여: 분기당 {person.wage:.1f}",
                f"지난 분기에 실제로 받은 급여: {person.last_wage_paid:.1f}"
                + (f" (급여가 {person.unpaid_streak}분기째 밀리는 중)" if person.unpaid_streak else ""),
                f"저축: {person.savings:.1f}",
                f"분기마다 드는 생활비: {c.living_cost:.1f}",
            ]
            if person.bound_to:
                facts.append(
                    f"채무 불이행으로 {person.bound_to}에 묶여 있음: {person.bound_until}분기까지 조직을 떠날 수 없고, "
                    "그동안 급여는 채권자에게 감"
                )
            if company is not None:
                rate = quoted_rate(
                    c, unpaid_streak=person.unpaid_streak, savings=person.savings,
                    has_income=company.resources.capital > 0,
                )
                facts.append(
                    f"은행에서 빌릴 수 있는 조건: 이자 분기당 {rate:.0%}, {c.credit_term_ticks}분기 뒤 상환, "
                    f"최대 {c.credit_max_principal:.0f}. 담보는 savings(못 갚으면 저축 압류) 또는 "
                    f"freedom(못 갚으면 {c.bondage_ticks}분기간 조직을 떠날 수 없고 그동안 급여가 채권자에게 감) "
                    "중 하나를 정해야 함"
                )
        else:
            facts = ["소속: 없음", f"가진 돈: {person.resources.capital:.1f}", f"분기마다 드는 생활비: {c.living_cost:.1f}"]
            if isinstance(person, Vigilante):
                disposition = VIGILANTE_DISPOSITION_BRIEF[person.disposition]
                if person.disposition == "grudge" and person.grudge_target:
                    disposition += f" 그 대상은 {person.grudge_target}이다."
                facts.append(disposition)
        for loan in self.bank.loans:
            if not loan.closed and loan.borrower == name:
                facts.append(f"갚아야 할 빚: {loan.outstanding:.1f} ({loan.due_tick}분기 만기, 담보={loan.collateral})")
        return facts

    def _org_lines(self, company: Company | None) -> list[str]:
        if company is None:
            return []
        r = company.resources
        lines = [
            f"조직: {company.name}",
            f"자본: {r.capital:.1f}, 기술: {r.tech:.1f}, 강제력: {r.coercion:.2f}",
            f"분기 인건비 합계: {sum(e.wage for e in company.employees):.1f}",
            f"구성원: {', '.join(e.name for e in company.employees)}",
        ]
        if company.agenda:
            lines.append(f"아직 표결되지 않은 안건: {len(company.agenda)}건")
        return lines

    def _known_lines(self, name: str) -> list[str]:
        knowledge = self.knowledge.get(name)
        return format_entries(knowledge.recent(self.config.knowledge_prompt_window)) if knowledge else []

    def _agent_council_vote(self, company: Company, proposal: Proposal, tick_index: int) -> CouncilOutcome:
        members = list(company.employees)
        org_lines = self._org_lines(company)

        def build(member: Employee, transcript: list | None) -> str:
            return build_agent_vote_prompt(
                member.name, company.name, self._own_facts(member.name), org_lines,
                self._known_lines(member.name), proposal.proposer, proposal.text, transcript,
            )

        final_round, all_rounds = hold_agent_meeting(
            members, build, self.config, rounds=self.config.council_discussion_rounds,
            label_prefix=f"council:{company.name}",
        )
        roster = [m.name for m in members]
        action = f"{proposal.proposer}의 안건: {proposal.text}"
        self.last_meeting_transcripts[company.name] = (roster, all_rounds)
        recorder = recording.active()
        if recorder is not None:
            recorder.record_meeting(
                tick_index=tick_index, company=company.name, action_description=action,
                roster=roster, all_rounds=all_rounds,
            )
        # a member whose call failed abstains; the engine does not guess their vote
        voters = [(m, r) for m, r in zip(members, final_round) if r is not None]
        outcome = tally_votes([r for _, r in voters], [m for m, _ in voters], self.config, self.rng)
        outcome.action_description = action
        outcome.company = company.name
        verdict = "가결" if outcome.proceeds else "부결"
        tell_members(
            self, company, tick_index,
            f"{company.name} 의회에서 {proposal.proposer}의 안건 \"{proposal.text}\"이(가) {verdict}됨 "
            f"(찬성 {outcome.votes_for}/{outcome.votes_total})",
        )
        if not outcome.proceeds:
            return outcome
        known = set(roster)
        for member in members:
            known |= self.acquaintances.get(member.name, set())
        transcription = clerk.transcribe_resolution(
            company.name, proposal.text, roster, sorted(known), company.resources.capital, self.config
        )
        # a failed transcription executes nothing rather than guessing what the org meant
        clerk_ops = (
            transcription.operations if transcription is not None else [OrgOperation(op="intent", content=proposal.text)]
        )
        ops = clerk.keep_said_amounts(clerk_ops, proposal.text)
        results = resolve_org_ops(self, company, ops, tick_index)
        if recorder is not None:
            recorder.write("resolutions", {
                "tick": tick_index, "org": company.name, "proposer": proposal.proposer,
                "proposal": proposal.text, "operations": [o.model_dump() for o in ops], "results": results,
                "clerk_operations": [o.model_dump() for o in clerk_ops],
            })
        return outcome

    def _agent_turns(self, names: list[str], tick_index: int) -> list[MemberExitEvent]:
        # Everyone due this tick decides at once from what they knew when the tick began. Nobody hears what
        # another did this tick until the next one, so no turn order hands anyone a head start.
        people = [(name, person) for name in names if (person := find_person(self, name)) is not None]
        prompts = [
            build_declaration_prompt(
                name, self._own_facts(name), self._org_lines(employer_of(self, name)), self._known_lines(name)
            )
            for name, _ in people
        ]
        for name, _ in people:
            # read before anything lands, so what arrives while this tick resolves wakes them next tick
            self.knowledge.setdefault(name, Knowledge()).mark_read()
            self.last_acted[name] = tick_index
        declarations = llm_agent.run_concurrently(
            [
                lambda name=name, person=person, prompt=prompt: llm_agent.call_llm_decision(
                    prompt, Declaration, self.config, temperature=person.temperature, label=f"declare:{name}"
                )
                for (name, person), prompt in zip(people, prompts)
            ],
            self.config,
        )

        recorder = recording.active()
        spoken: list[tuple[str, str, list[str], float]] = []
        for (name, person), declaration in zip(people, declarations):
            if declaration is None:
                self.next_wake[name] = tick_index + 1
                continue
            self.next_wake[name] = tick_index + min(max(1, declaration.next_wake_in), self.config.max_wake_ticks)
            text = declaration.declaration.strip()
            if recorder is not None:
                recorder.write("declarations", {
                    "tick": tick_index, "person": name, "declaration": text,
                    "reasoning": declaration.reasoning, "next_wake_in": declaration.next_wake_in,
                })
            if not text:
                continue
            self.knowledge[name].add(tick_index, f"당신의 선언: {text}", incoming=False)
            spoken.append((name, text, sorted(self.acquaintances.get(name, set())), money_of(person)))

        transcriptions = llm_agent.run_concurrently(
            [lambda said=said: clerk.transcribe(*said, self.config) for said in spoken], self.config
        )
        # physics still needs an order when two acts touch the same money or the same org; it is drawn at random
        order = list(zip(spoken, transcriptions))
        self.rng.shuffle(order)
        exits: list[MemberExitEvent] = []
        for (name, text, _, _), transcription in order:
            if find_person(self, name) is None:
                continue
            # a failed transcription changes nothing in the world rather than guessing what they meant
            clerk_ops = transcription.operations if transcription is not None else [Operation(op="intent", content=text)]
            ops = clerk.keep_said_amounts(clerk_ops, text)
            results, person_exits = resolve_person_ops(self, name, ops, tick_index)
            exits.extend(person_exits)
            if recorder is not None:
                recorder.write("transcriptions", {
                    "tick": tick_index, "person": name, "declaration": text,
                    "operations": [o.model_dump() for o in ops], "results": results,
                    "clerk_operations": [o.model_dump() for o in clerk_ops],
                })
        return exits

    def _agent_tick(self) -> Tick:
        tick_index = len(self.history)
        self.last_meeting_transcripts = {}

        # arithmetic: outside-market revenue, the cost of staying alive, standing wage contracts, debts
        for company in self.companies:
            if company.alive:
                _ordinary_income(company, self.config, self.rng)
        for person in [*self.vigilantes, *self.individuals]:
            if person.alive:
                person.resources.capital -= self.config.living_cost

        payroll_events = run_payroll(self.companies, self.config, bank=self.bank, tick=tick_index)
        for event in payroll_events:
            for name in event.unpaid_members:
                employee = find_person(self, name)
                if employee is not None:
                    tell(
                        self, name, tick_index,
                        f"이번 분기 급여를 계약({employee.wage:.1f})만큼 받지 못함: {employee.last_wage_paid:.1f}만 받음",
                    )

        credit_events = settle_credit(self.bank, self.companies, tick_index, self.config)
        for event in credit_events:
            if find_person(self, event.borrower) is None:
                continue
            if event.kind == "repaid":
                tell(self, event.borrower, tick_index, f"빚 {event.amount:.1f}을 만기에 갚음(저축에서 빠져나감)")
            elif event.kind in ("seized", "defaulted"):
                tell(self, event.borrower, tick_index, f"만기에 빚을 갚지 못함: {event.detail}")
        for company in self.companies:
            for name in release_bonded(company.employees, tick_index):
                tell(self, name, tick_index, "채무 구속이 끝남")

        council_votes: list[CouncilOutcome] = []
        for company in list(self.companies):
            for _ in range(self.config.agenda_items_per_tick):
                if not company.alive or not company.employees or not company.agenda:
                    break
                council_votes.append(self._agent_council_vote(company, company.agenda.pop(0), tick_index))

        member_exits = self._agent_turns(due_persons(self, tick_index), tick_index)

        for company in self.companies:
            if company.alive and not company.employees:
                company.alive = False

        states = {c.name: CompanyState.ALIVE if c.alive else CompanyState.DEAD for c in self.companies}
        values = {
            c.name: currency_value(
                c.resources, necessity(c.resources.tech, num_alternative_suppliers=len(c.copied_by)), self.config
            )
            for c in self.companies
        }
        record = Tick(
            index=tick_index, company_states=states, currency_values=values,
            council_votes=council_votes, member_exits=member_exits, payroll=payroll_events, credit=credit_events,
        )
        self.history.append(record)
        recorder = recording.active()
        if recorder is not None:
            recorder.record_tick(tick_index=tick_index, world=self, tick=record)
        return record

    def run(self, ticks: int) -> list[Tick]:
        return [self.tick() for _ in range(ticks)]
