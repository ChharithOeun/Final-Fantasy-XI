"""Boss Critic LLM — adaptive boss strategy via Llama 3 reflection.

Per BOSS_GRAMMAR.md Layer 4. The boss's combat AI (LSB Lua) sends an
EncounterSnapshot every 30 seconds; the critic synthesizes a
StrategyHint that the AI consumes for the next 30s of combat.

Two backends mirror the rest of the AI stack:
- "ollama": real Llama 3 8B via the orchestrator's existing Ollama client
- "stub":   deterministic rule-based fallback for CI + offline play
            (the same logic the LLM would arrive at, hand-coded)

The stub is NOT just a placeholder. It's the production fallback —
when Ollama is unavailable, bosses still behave intelligently (just
without the LLM's narrative flourish in the contextual barks).
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
import typing as t


log = logging.getLogger("demoncore.boss_critic")


# ----------------------------------------------------------------------
# Inputs / outputs
# ----------------------------------------------------------------------

@dataclasses.dataclass
class PartyMember:
    agent_id: str
    job: str                    # "BLM", "WHM", "WAR" etc
    level: int = 75
    current_mood: str = "alert" # "alert" | "fearful" | "content" | "furious"
    hp_pct: float = 1.0
    is_back_row: bool = False   # mages typically back


@dataclasses.dataclass
class EncounterSnapshot:
    """30-second window of encounter state."""
    boss_id: str                              # e.g. "hero_maat"
    boss_phase: str                            # "pristine"|"scuffed"|"bloodied"|"wounded"|"grievous"|"broken"
    boss_hp_pct: float
    boss_mood: str

    party: list[PartyMember]

    # Last 30s of skillchain history per SKILLCHAIN_SYSTEM.md
    skillchains_last_30s: list[dict]   # [{element, level, contributors}]

    # Last 30s of magic bursts the party landed
    magic_bursts_last_30s: list[dict]  # [{element, target, was_ailment, was_amplified}]

    # Last 30s of intervention saves the party landed
    interventions_last_30s: int = 0

    # Recent boss-events
    boss_taken_silence_recently: bool = False
    boss_was_intervention_blocked: bool = False
    boss_just_used_ultimate: bool = False

    # Server-side learning across encounters
    boss_kill_count_by_party: int = 0   # how many times this party has killed this boss


@dataclasses.dataclass
class StrategyHint:
    """Output of one critic tick."""
    # Behavior priorities
    next_attack_priority: str           # mob_class.action key
    next_target_player: t.Optional[str] # agent_id or "tank"|"healer"|"blm"|"any"
    silence_priority_player: t.Optional[str] = None
    should_use_ultimate: bool = False
    should_yield: bool = False

    # Boss bark to fire mid-combat (one-off audible line)
    contextual_bark: t.Optional[str] = None

    # Mood shift the orchestrator should apply
    boss_mood_shift: t.Optional[str] = None

    # Diagnostic
    strategy_reason: str = ""
    confidence: float = 0.5


# ----------------------------------------------------------------------
# Backends
# ----------------------------------------------------------------------

class StubBackend:
    """Deterministic rule-based critic. Production fallback when Ollama is down."""

    def decide(self, snap: EncounterSnapshot) -> StrategyHint:
        return _rule_based_strategy(snap)


class OllamaBackend:
    """Real Llama 3 8B critic via Ollama HTTP."""

    def __init__(self, *, url: str = "http://localhost:11434",
                 model: str = "llama3.1:8b-instruct-q4_K_M",
                 timeout_seconds: float = 30.0):
        self.url = url
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def decide_async(self, snap: EncounterSnapshot,
                            personality: str = "",
                            backstory: str = "") -> StrategyHint:
        try:
            import httpx
        except ImportError:
            log.warning("httpx not installed; falling back to stub")
            return _rule_based_strategy(snap)

        prompt = _compose_critic_prompt(snap, personality, backstory)
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                r = await client.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_ctx": 4096, "temperature": 0.6},
                    },
                )
            if r.status_code != 200:
                log.warning("ollama returned %d; falling back to stub",
                            r.status_code)
                return _rule_based_strategy(snap)
            text = r.json().get("response", "")
            return _parse_llm_response(text, fallback=snap)
        except Exception as e:
            log.warning("ollama request failed: %s; falling back to stub", e)
            return _rule_based_strategy(snap)


# ----------------------------------------------------------------------
# Rule-based fallback (production-grade)
# ----------------------------------------------------------------------

def _rule_based_strategy(snap: EncounterSnapshot) -> StrategyHint:
    """Hand-coded critic behavior. Mirrors the prompted LLM decisions
    so that bosses remain intelligently adaptive even with Ollama down."""

    hint = StrategyHint(
        next_attack_priority="melee_attack",
        next_target_player="tank",
    )

    # Detect player BLM specifically (prefer over generic back-row casters)
    blm = next((p for p in snap.party if p.job == "BLM"), None)
    if blm is None:
        # Fallback: any back-row caster that isn't a healer
        blm = next((p for p in snap.party
                    if p.is_back_row and p.job not in ("WHM", "SCH")), None)
    healer = next((p for p in snap.party
                    if p.job in ("WHM", "SCH")), None)
    tank = next((p for p in snap.party
                  if p.job in ("PLD", "NIN", "RUN", "WAR")), None)

    # Count Magic Bursts the party has landed
    party_mb_count = len(snap.magic_bursts_last_30s)
    party_ailment_amp_count = sum(1 for mb in snap.magic_bursts_last_30s
                                    if mb.get("was_amplified"))
    party_l3_chains = sum(1 for sc in snap.skillchains_last_30s
                            if sc.get("level") == 3)

    # Detect strategies
    blm_cheese = (blm is not None and blm.is_back_row
                  and party_mb_count >= 3)
    party_using_skillchains = len(snap.skillchains_last_30s) >= 2
    party_panicked = sum(1 for p in snap.party
                          if p.current_mood == "fearful") >= len(snap.party) // 2

    # ---- BLM cheese: close the gap ----
    if blm_cheese and snap.boss_phase in ("pristine", "scuffed"):
        hint.next_attack_priority = "tornado_kick"   # Maat's gap-closer
        hint.next_target_player = blm.agent_id
        hint.boss_mood_shift = "gruff"
        hint.contextual_bark = "I see what you're doing, Tarutaru!"
        hint.strategy_reason = "Detected BLM kite cheese; closing gap"
        hint.confidence = 0.85
        return hint

    # ---- Boss in broken phase + apex party play: yield (more specific than L3) ----
    # Must be checked BEFORE the L3 contemplative branch since both fire on
    # an L3 chain — the broken-phase yield is the more specific outcome.
    if (snap.boss_phase == "broken"
            and party_l3_chains > 0
            and party_ailment_amp_count > 0
            and snap.boss_kill_count_by_party == 0):
        hint.should_yield = True
        hint.boss_mood_shift = "contemplative"
        hint.contextual_bark = "...you've earned this."
        hint.strategy_reason = "Boss impressed by party play; yield gracefully"
        hint.confidence = 0.70
        return hint

    # ---- L3 Light skillchain: respect the apex ----
    if party_l3_chains > 0:
        hint.next_attack_priority = "counterstance"
        hint.boss_mood_shift = "contemplative"
        hint.contextual_bark = "...I haven't seen Light in years."
        hint.strategy_reason = "Party landed L3 skillchain; mood -> contemplative"
        hint.confidence = 0.95
        return hint

    # ---- Skillchain spam without ailment burst: counter with silence ----
    if (party_using_skillchains and party_ailment_amp_count == 0
            and blm is not None):
        hint.silence_priority_player = blm.agent_id
        hint.next_attack_priority = "silence_aoe"
        hint.boss_mood_shift = "alert"
        hint.contextual_bark = "Silence them!"
        hint.strategy_reason = "Party chaining without ailment burst; cut off DD casts"
        hint.confidence = 0.75
        return hint

    # ---- 3x Ailment stack landed: cleanse next phase ----
    if party_ailment_amp_count >= 2:
        hint.next_attack_priority = "erase_self"
        hint.boss_mood_shift = "gruff"
        hint.contextual_bark = "GET — IT — OFF!"
        hint.strategy_reason = "Party landed multiple amplified ailments; pop Erase"
        hint.confidence = 0.85
        return hint

    # ---- Party panicked: press hard ----
    if party_panicked and snap.boss_hp_pct > 0.30:
        if healer is not None:
            hint.next_target_player = healer.agent_id
        hint.next_attack_priority = "final_heaven" if snap.boss_phase \
                                     in ("wounded", "grievous") else "asuran_fists"
        hint.should_use_ultimate = snap.boss_phase in ("wounded", "grievous")
        hint.boss_mood_shift = "furious"
        hint.contextual_bark = "ENOUGH PLAYING."
        hint.strategy_reason = "Party panicked; press for kill"
        hint.confidence = 0.80
        return hint

    # ---- Boss got intervention-blocked: enraged escalation ----
    if snap.boss_was_intervention_blocked:
        hint.next_attack_priority = "ultimate_charge"
        hint.boss_mood_shift = "furious"
        hint.contextual_bark = "YOU DARE!"
        hint.strategy_reason = "Intervention block on boss chain; escalate"
        hint.confidence = 0.80
        return hint

    # ---- Boss in broken phase + party very skilled: yield ----
    if (snap.boss_phase == "broken"
            and party_l3_chains > 0
            and party_ailment_amp_count > 0
            and snap.boss_kill_count_by_party == 0):
        hint.should_yield = True
        hint.boss_mood_shift = "contemplative"
        hint.contextual_bark = "...you've earned this."
        hint.strategy_reason = "Boss impressed by party play; yield gracefully"
        hint.confidence = 0.70
        return hint

    # ---- Default: standard rotation ----
    hint.next_attack_priority = "asuran_fists"
    hint.next_target_player = tank.agent_id if tank else "any"
    hint.strategy_reason = "Standard rotation"
    hint.confidence = 0.50
    return hint


# ----------------------------------------------------------------------
# Prompt + parser for the LLM path
# ----------------------------------------------------------------------

def _compose_critic_prompt(snap: EncounterSnapshot,
                            personality: str = "",
                            backstory: str = "") -> str:
    """Construct the LLM prompt for the critic. Returns text."""
    party_jobs = ", ".join(p.job for p in snap.party)
    moods = ", ".join(f"{p.agent_id}={p.current_mood}" for p in snap.party)
    sc_summary = ", ".join(
        f"{sc.get('element', '?')}/L{sc.get('level', 1)}"
        for sc in snap.skillchains_last_30s[-5:]
    ) or "(none)"
    mb_summary = ", ".join(
        f"{mb.get('element', '?')}{'+amp' if mb.get('was_amplified') else ''}"
        for mb in snap.magic_bursts_last_30s[-5:]
    ) or "(none)"

    return f"""You are the combat critic for boss {snap.boss_id} in a fight.
Personality: {personality or '(generic boss)'}
Backstory: {backstory or '(none)'}

Current encounter state:
  Boss phase: {snap.boss_phase}
  Boss HP: {snap.boss_hp_pct:.0%}
  Boss mood: {snap.boss_mood}
  Party: {party_jobs}
  Party moods: {moods}
  Skillchains last 30s: {sc_summary}
  Magic bursts last 30s: {mb_summary}
  Interventions last 30s: {snap.interventions_last_30s}
  Recent: silenced={snap.boss_taken_silence_recently}, intervention-blocked={snap.boss_was_intervention_blocked}, ult-used={snap.boss_just_used_ultimate}
  Party kill-history: {snap.boss_kill_count_by_party}

Decide the boss's next 30-second strategy. Output STRICT JSON:
{{
  "next_attack_priority": "string (action_id)",
  "next_target_player": "agent_id or 'tank'|'healer'|'blm'|'any'",
  "silence_priority_player": "agent_id or null",
  "should_use_ultimate": bool,
  "should_yield": bool,
  "contextual_bark": "one short sentence the boss says aloud",
  "boss_mood_shift": "content|gruff|alert|furious|contemplative|null",
  "strategy_reason": "one sentence why",
  "confidence": float 0.0-1.0
}}
Output only the JSON object, no preamble."""


def _parse_llm_response(text: str,
                         fallback: EncounterSnapshot) -> StrategyHint:
    """Lenient JSON extraction. Falls back to stub on parse failure."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        log.warning("critic LLM emitted non-JSON; falling back to rules")
        return _rule_based_strategy(fallback)

    try:
        parsed = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return _rule_based_strategy(fallback)

    return StrategyHint(
        next_attack_priority=parsed.get("next_attack_priority", "melee_attack"),
        next_target_player=parsed.get("next_target_player"),
        silence_priority_player=parsed.get("silence_priority_player"),
        should_use_ultimate=bool(parsed.get("should_use_ultimate", False)),
        should_yield=bool(parsed.get("should_yield", False)),
        contextual_bark=parsed.get("contextual_bark"),
        boss_mood_shift=parsed.get("boss_mood_shift"),
        strategy_reason=parsed.get("strategy_reason", ""),
        confidence=float(parsed.get("confidence", 0.5)),
    )


# ----------------------------------------------------------------------
# BossCritic — owns one boss instance
# ----------------------------------------------------------------------

class BossCritic:
    def __init__(self, *,
                 boss_id: str,
                 backend: str = "stub",
                 backend_kwargs: t.Optional[dict] = None,
                 personality: str = "",
                 backstory: str = "",
                 min_seconds_between_calls: float = 30.0):
        self.boss_id = boss_id
        self.personality = personality
        self.backstory = backstory
        self.min_seconds_between_calls = min_seconds_between_calls

        if backend == "ollama":
            self.backend = OllamaBackend(**(backend_kwargs or {}))
        elif backend == "stub":
            self.backend = StubBackend()
        else:
            raise ValueError(f"unknown critic backend: {backend!r}")
        self.backend_name = backend

        self._last_call_at: float = 0.0
        self._last_hint: t.Optional[StrategyHint] = None

    def evaluate_sync(self, snap: EncounterSnapshot,
                       now: t.Optional[float] = None) -> StrategyHint:
        """Synchronous evaluate. Uses stub if rate-limited or backend
        is StubBackend; otherwise runs the async LLM path via asyncio."""
        now = now if now is not None else time.time()

        if (now - self._last_call_at < self.min_seconds_between_calls
                and self._last_hint is not None):
            return self._last_hint

        if isinstance(self.backend, StubBackend):
            hint = self.backend.decide(snap)
        else:
            # Run the async LLM path
            hint = asyncio.run(
                self.backend.decide_async(snap, self.personality, self.backstory)
            )

        self._last_call_at = now
        self._last_hint = hint
        return hint

    async def evaluate_async(self, snap: EncounterSnapshot,
                              now: t.Optional[float] = None) -> StrategyHint:
        now = now if now is not None else time.time()

        if (now - self._last_call_at < self.min_seconds_between_calls
                and self._last_hint is not None):
            return self._last_hint

        if isinstance(self.backend, StubBackend):
            hint = self.backend.decide(snap)
        else:
            hint = await self.backend.decide_async(
                snap, self.personality, self.backstory
            )

        self._last_call_at = now
        self._last_hint = hint
        return hint
