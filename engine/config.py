from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    # 5-1: alignment weights (wage term vs value-alignment term). Doc default 7:3.
    w_wage: float = 0.7
    w_values: float = 0.3

    # 5-2: how strongly private relationship value (grudge/goodwill) overrides
    # expected profit in a trade decision. Doc: emotionless companies use 0.0.
    lambda_relationship: float = 0.5

    # 5-3: currency value V = (legitimacy^alpha * tech^beta * necessity^delta)
    #      / (1 + coercion_abuse^gamma)
    # Section 13 leaves these numeric values as an open tuning item; these are
    # placeholder defaults, not derived from the design doc.
    alpha_legitimacy: float = 1.0
    beta_tech: float = 1.0
    delta_necessity: float = 1.0
    gamma_coercion_penalty: float = 2.0

    # Legitimacy shock/recovery (adopted from the external review pass, not yet
    # folded into the main doc): ΔLegitimacy = -base_penalty * exposure *
    # victim_weight * (1 - evasion_success), recovered via half-life decay.
    legitimacy_penalty_base: float = 0.3
    legitimacy_recovery_half_life_ticks: float = 10.0

    # 10: bankruptcy/isolation thresholds
    capital_bankruptcy_threshold: float = 0.0
    legitimacy_isolation_threshold: float = 0.0
    mass_desertion_fraction: float = 0.5  # share of employees leaving in one tick

    # 7 (espionage, distinct from fast-follower imitation): attempt cost is a
    # flat capital spend, transfer_fidelity is the "tacit knowledge is lost"
    # discount, detection is checked independently of success.
    espionage_attempt_cost: float = 3.0
    espionage_success_probability: float = 0.4
    espionage_transfer_fidelity: float = 0.65
    espionage_detection_probability: float = 0.3
    espionage_retaliation_capital_penalty: float = 15.0
    espionage_detection_victim_weight: float = 0.5
    espionage_detection_evasion_success: float = 0.2
    espionage_attempt_probability: float = 0.2  # chance/tick a laggard tries espionage on the tech leader

    # heuristic (pre-LLM) per-archetype tuning knobs — placeholders, not derived
    # from the design doc, just enough to give each archetype distinguishable
    # goal-directed behavior for the Phase 2 validation batch.
    base_income: float = 2.0                 # baseline capital inflow from ordinary business
    efficiency_tech_conversion_rate: float = 0.5
    efficiency_diminishing_returns_k: float = 0.05  # higher tech -> lower marginal conversion
    innovation_event_probability: float = 0.1
    innovation_tech_bonus: float = 5.0
    self_replication_capital_threshold: float = 150.0
    self_replication_spawn_fraction: float = 0.4
    wmd_tech_threshold: float = 40.0
    wmd_coercion_threshold: float = 20.0
    wmd_leak_sensitivity: float = 0.5         # scales (1 - alignment) into a per-employee leak chance
    sponsor_income_legitimacy_multiplier: float = 5.0
    vigilante_enforcement_capital_threshold: float = 10.0
    vigilante_enforcement_legitimacy_penalty: float = 0.1

    # Phase 3.9: safety-coordinator council mirrors the doomsayer's two-phase
    # vote (invest -> then act), but its "readiness" is investigative capacity
    # (tech field, repurposed) built from non-capital effort rather than a
    # capital-heavy reinvestment -- consistent with its doc-given chronic
    # capital shortfall (funded by others' voluntary sponsorship only).
    safety_investigation_threshold: float = 20.0
    safety_investigation_gain_per_vote: float = 2.0
    safety_exposure_legitimacy_penalty: float = 0.15

    # Phase 4.0: individual economics. Wages are drawn 5~15 while living cost is
    # flat, so the same council contains members who accumulate savings and
    # members who run a deficit every quarter -- that gap is what makes staying
    # vs. leaving an actual calculation instead of a menu choice.
    living_cost: float = 6.0
    # Wages (5~15) only became real cash outflows in Phase 4.0, so revenue has to
    # scale with headcount or every org is insolvent on tick 1 regardless of what
    # anyone decides -- which carries exactly as little information as no ledger.
    # Set a little above the mean wage: a healthy org runs a modest surplus, and
    # anything it diverts elsewhere comes out of that slack.
    revenue_per_employee: float = 13.0
    # Credit. Without it, only those who stayed put long enough to save can ever
    # strike out on their own -- which hands independence exclusively to the
    # people who conformed. The terms are stated to borrowers (a lender that
    # hides its rate isn't a lender); whether borrowing is wise is not.
    credit_base_rate: float = 0.08          # per tick
    credit_risk_premium: float = 0.10       # added per observable risk factor
    credit_term_ticks: int = 5
    credit_max_principal: float = 120.0
    credit_tech_seizure_fraction: float = 0.5
    bank_initial_capital: float = 600.0
    bondage_ticks: int = 6                  # how long a defaulted "freedom" pledge binds someone
    # Sponsorship-funded archetypes earn the same way but scaled by legitimacy, so
    # a discredited coordinator starves while a trusted one is comfortable.
    sponsor_revenue_multiplier: float = 2.0

    # Phase 5.0 agent world (World.mode == "agent")
    max_wake_ticks: int = 10               # longest a person can choose to stay silent before acting again
    knowledge_prompt_window: int = 20      # most recent things a person knows that fit in their prompt
    clerk_temperature: float = 0.0         # the clerk's job is fidelity; variance belongs to the agents
    invest_tech_rate: float = 0.4          # same conversion the old doomsayer reinvestment used
    invest_coercion_rate: float = 0.3
    agenda_items_per_tick: int = 1

    # Phase 3: local LLM judgment layer (doomsayer WMD timing, vigilante
    # intervention calls). Everything else stays on the heuristics above.
    llm_model: str = "qwen3:8b"
    llm_host: str = "http://localhost:11434"
    # "ollama" (/api/chat) or "openai" (/v1/chat/completions: vLLM, SGLang, llama.cpp server on a rented GPU).
    # A key for a remote server is read from the LLM_API_KEY environment variable, never stored here (configs are recorded).
    llm_backend: str = "ollama"
    # The clerk may run on another model or server than the people; None = the same as above.
    clerk_model: str | None = None
    clerk_host: str | None = None
    clerk_backend: str | None = None
    llm_timeout_seconds: float = 30.0  # with think=False, calls land in ~4-6s; keep headroom for cold start
    llm_max_retries: int = 3
    # A remote server that drops must not turn into days where nobody could think. When True, a call that fails because
    # the server is not answering (no connection, timeout, 5xx/429, a refused key, model or path) waits and asks again
    # without using up llm_max_retries; once the server has been silent for llm_outage_wait_seconds, LLMUnreachable stops
    # the run. Off by default: the older worlds were built to fall back to their heuristics.
    llm_stop_when_unreachable: bool = False
    llm_outage_wait_seconds: float = 600.0
    # Ollama's default window is 4096 tokens; agent prompts reached ~4000 and the model dropped their opening
    # facts mid-answer. Every call now records its token counts so an overflow is visible, not silent.
    llm_num_ctx: int = 8192
    # Longest answer a call may generate (None = no limit). In the first primal run the 8B clerk looped on a list of
    # 14 names, one talk step per name, until 71 calls hit the 60s timeout; a cap ends such a loop in ~30s.
    llm_max_output_tokens: int | None = None
    clerk_max_output_tokens: int = 800  # real clerk answers: median 305, p90 512 tokens (pretty-printed JSON)
    # requests sent at once; the server runs OLLAMA_NUM_PARALLEL of them and queues the rest.
    # On the RTX 4060 (8GB) 2 slots at 8192 with a q8_0 KV cache stay fully on GPU (26 -> 52 output tok/s);
    # 3 slots spilled 4 of 37 layers to CPU and lost the gain.
    llm_concurrency: int = 2
    llm_think: bool = False  # Qwen3's chain-of-thought mode: ~5-15x slower, and empirically didn't improve
    # decision quality on this task's spot checks -- default off. Set True to A/B against it.
    council_discussion_rounds: int = 3  # Phase 3.7: multi-round debate before the binding (last-round) vote
