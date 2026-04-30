"""The orchestrator core: runs reflection cycles for Tier-2 and Tier-3 agents.

Design notes
------------
* The orchestrator does NOT block. It runs a single asyncio task that
  wakes every `tick_seconds`, finds agents past their reflection deadline,
  and dispatches them to a worker pool that calls Ollama. Multiple agents
  reflect concurrently — tunable via `max_inflight`.

* Reflection is intentionally cheap. A Tier-2 agent's reflection is one
  LLM call returning a one-sentence memory + a mood label. We don't ask
  the model for free-form essays; the prompt is constrained.

* Tier-3 agents get a richer reflection (one journal entry per game-day,
  goal progress check) but still constrained — we want predictable token
  budgets, not creative writing.

* The orchestrator owns the Ollama HTTP connection pool. It does NOT
  own a Redis client, MariaDB driver, or any other heavyweight thing.
  Those plug in via callbacks if chharbot needs them.

* If Ollama is offline, reflections are skipped (not retried in a tight
  loop). The next tick tries again. Agents stay alive with stale state.

Public methods called by chharbot's MCP server:
    orchestrator.list_agents(zone=..., tier=...)
    orchestrator.get_state(agent_id)
    orchestrator.push_event(agent_id, kind, payload)
    orchestrator.force_reflection(agent_id)
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
import typing as t

import httpx

from .db import AgentDB
from .loader import AgentProfile, load_all_agents


log = logging.getLogger("demoncore.orchestrator")


# Reflection prompts — small enough to fit in 4k context, opinionated.

TIER2_REFLECTION_PROMPT = """\
You are roleplaying as {name}, an NPC in the FFXI city of {zone}.

Personality:
{personality}

Your current mood is: {current_mood}
Your current memory of recent events:
{memory_summary}

Recent events that just happened to you (newest last):
{events}

Reflect on these events as {name}. Output STRICT JSON with two keys:
{{
  "new_mood": one of [{mood_options}],
  "new_memory_summary": one or two sentences in first person, capturing
                        what {name} now remembers about recent events.
                        Stay in character. Do NOT mention this is a game.
}}

Output only the JSON object, no preamble.
"""


TIER3_REFLECTION_PROMPT = """\
You are roleplaying as {name}, a major figure in {zone}.

Personality:
{personality}

Backstory (do not summarize, internalize):
{backstory}

Active goals:
{goals}

Last journal entry:
{last_journal}

Recent events that affected you (newest last):
{events}

Write a brief journal entry (3-5 sentences) as {name} would write it
tonight. Stay strictly in voice. Reference one of the active goals if
relevant. Then identify which goal you'll focus on tomorrow.

Output STRICT JSON:
{{
  "journal_entry": "...",
  "focus_goal": "exact text of the goal you'll focus on next"
}}

Output only the JSON object, no preamble.
"""


@dataclasses.dataclass
class OrchestratorConfig:
    agents_dir: str
    db_path: str = "demoncore_agents.sqlite"
    ollama_url: str = "http://localhost:11434"
    tier2_model: str = "llama3.1:8b-instruct-q4_K_M"
    tier3_model: str = "llama3.1:8b-instruct-q4_K_M"
    tier2_interval_seconds: int = 3600     # 1 game-hour ≈ 1 wall-hour
    tier3_interval_seconds: int = 86400    # 1 game-day ≈ 1 wall-day
    tick_seconds: float = 10.0
    max_inflight: int = 3
    request_timeout_seconds: float = 60.0


class AgentOrchestrator:
    """Owns agent state + reflection loop. Plug into chharbot's event loop."""

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.db = AgentDB(config.db_path)
        self._http: t.Optional[httpx.AsyncClient] = None
        self._task: t.Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._inflight = asyncio.Semaphore(config.max_inflight)

    # ------------------------------------------------------------------
    # boot
    # ------------------------------------------------------------------

    def load_all(self) -> int:
        """Walk agents/ directory; return number of profiles loaded."""
        profiles = load_all_agents(self.config.agents_dir)
        for p in profiles:
            self.db.upsert_agent(p)
        log.info("loaded %d agent profiles from %s",
                 len(profiles), self.config.agents_dir)
        return len(profiles)

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------

    async def run_loop(self) -> None:
        """Tick forever until stop() is called."""
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.request_timeout_seconds),
        )
        try:
            while not self._stop_event.is_set():
                await self._tick_once()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.config.tick_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            if self._http:
                await self._http.aclose()

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            await self._task
        self.db.close()

    async def _tick_once(self) -> None:
        # Tier 2: agents whose last_reflection_at is older than tier2_interval
        tier2_due = self.db.tier2_due_for_reflection(
            self.config.tier2_interval_seconds
        )
        # Filter to only those that have events queued OR are ALL stale
        # past 2x interval (so even quiet agents reflect occasionally to
        # keep memory_summary from going stale)
        tier3_agents = [r["id"] for r in self.db.list_agents(tier="3_hero")]
        tier3_due = []
        for aid in tier3_agents:
            st = self.db.get_tier3_state(aid)
            if not st:
                continue
            if int(time.time()) - st.last_reflection_at >= self.config.tier3_interval_seconds:
                tier3_due.append(aid)

        for aid in tier2_due:
            asyncio.create_task(self._reflect_tier2(aid))
        for aid in tier3_due:
            asyncio.create_task(self._reflect_tier3(aid))

    # ------------------------------------------------------------------
    # tier 2 reflection
    # ------------------------------------------------------------------

    async def _reflect_tier2(self, agent_id: str) -> None:
        async with self._inflight:
            try:
                profile = self._load_profile(agent_id)
                if profile is None or profile.tier != "2_reflection":
                    return
                state = self.db.get_tier2_state(agent_id)
                if state is None:
                    return

                events = self.db.drain_events(agent_id, limit=10)
                event_summary = self._summarize_events(events) or "(quiet day)"
                mood_options = profile.raw.get(
                    "mood_axes", ["content", "happy", "weary"]
                )

                prompt = TIER2_REFLECTION_PROMPT.format(
                    name=profile.name,
                    zone=profile.zone,
                    personality=profile.raw.get("personality", ""),
                    current_mood=state.mood,
                    memory_summary=state.memory_summary,
                    events=event_summary,
                    mood_options=", ".join(mood_options),
                )

                resp = await self._ollama_generate(self.config.tier2_model, prompt)
                if resp is None:
                    return

                try:
                    parsed = self._extract_json(resp)
                    new_mood = parsed.get("new_mood", state.mood)
                    if new_mood not in mood_options:
                        new_mood = state.mood  # ignore hallucinated moods
                    new_memory = parsed.get("new_memory_summary",
                                            state.memory_summary)[:1000]
                    self.db.update_tier2(agent_id, new_mood, new_memory)
                    log.info("tier2 reflected: %s mood=%s mem=%r",
                             agent_id, new_mood, new_memory[:80])
                except Exception as e:
                    log.warning("tier2 parse failed for %s: %s; raw=%r",
                                agent_id, e, resp[:200])
            except Exception as e:
                log.exception("tier2 reflect crashed for %s: %s", agent_id, e)

    # ------------------------------------------------------------------
    # tier 3 reflection
    # ------------------------------------------------------------------

    async def _reflect_tier3(self, agent_id: str) -> None:
        async with self._inflight:
            try:
                profile = self._load_profile(agent_id)
                if profile is None or profile.tier != "3_hero":
                    return
                state = self.db.get_tier3_state(agent_id)
                if state is None:
                    return

                events = self.db.drain_events(agent_id, limit=20)
                event_summary = self._summarize_events(events) or "(no major events)"
                last_journal = (state.journal[-1]["entry"]
                                if state.journal else "(no entries yet)")
                goals = profile.raw.get("goals", [])

                prompt = TIER3_REFLECTION_PROMPT.format(
                    name=profile.name,
                    zone=profile.zone,
                    personality=profile.raw.get("personality", ""),
                    backstory=profile.raw.get("backstory", ""),
                    goals="\n".join(f"  - {g}" for g in goals),
                    last_journal=last_journal,
                    events=event_summary,
                )

                resp = await self._ollama_generate(self.config.tier3_model, prompt)
                if resp is None:
                    return

                try:
                    parsed = self._extract_json(resp)
                    entry = parsed.get("journal_entry", "")[:2000]
                    focus = parsed.get("focus_goal")
                    if focus and focus not in goals:
                        focus = state.current_goal  # keep prior if hallucinated

                    self.db.update_tier3(
                        agent_id,
                        current_goal=focus or state.current_goal,
                        append_journal={
                            "ts": int(time.time()),
                            "entry": entry,
                        },
                    )
                    log.info("tier3 reflected: %s focus=%r entry=%r",
                             agent_id, focus, entry[:80])
                except Exception as e:
                    log.warning("tier3 parse failed for %s: %s; raw=%r",
                                agent_id, e, resp[:200])
            except Exception as e:
                log.exception("tier3 reflect crashed for %s: %s", agent_id, e)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def list_agents(self, zone: t.Optional[str] = None,
                    tier: t.Optional[str] = None) -> list[dict]:
        return [dict(r) for r in self.db.list_agents(zone=zone, tier=tier)]

    def get_state(self, agent_id: str) -> dict:
        result: dict = {"agent_id": agent_id}
        rows = self.db.list_agents()
        match = next((r for r in rows if r["id"] == agent_id), None)
        if not match:
            return {"error": f"unknown agent {agent_id}"}
        result["profile"] = dict(match)
        if match["tier"] == "2_reflection":
            st = self.db.get_tier2_state(agent_id)
            if st:
                result["state"] = dataclasses.asdict(st)
        elif match["tier"] == "3_hero":
            st = self.db.get_tier3_state(agent_id)
            if st:
                result["state"] = dataclasses.asdict(st)
        return result

    def push_event(self, agent_id: str, kind: str,
                   payload: t.Optional[dict] = None) -> int:
        return self.db.push_event(agent_id, kind, payload)

    async def force_reflection(self, agent_id: str) -> dict:
        rows = self.db.list_agents()
        match = next((r for r in rows if r["id"] == agent_id), None)
        if not match:
            return {"error": f"unknown agent {agent_id}"}
        if match["tier"] == "2_reflection":
            await self._reflect_tier2(agent_id)
        elif match["tier"] == "3_hero":
            await self._reflect_tier3(agent_id)
        else:
            return {"error": f"tier {match['tier']} doesn't reflect"}
        return self.get_state(agent_id)

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _load_profile(self, agent_id: str) -> t.Optional[AgentProfile]:
        """Reconstruct a profile from the DB row (round-tripped JSON)."""
        rows = self.db.list_agents()
        match = next((r for r in rows if r["id"] == agent_id), None)
        if not match:
            return None
        raw = json.loads(match["payload_json"])
        pos = raw.get("position", [0, 0, 0])
        return AgentProfile(
            id=raw["id"],
            name=raw["name"],
            zone=raw["zone"],
            position=tuple(float(x) for x in pos),  # type: ignore[arg-type]
            tier=raw["tier"],
            role=raw["role"],
            race=raw["race"],
            gender=raw["gender"],
            voice_profile=raw.get("voice_profile"),
            appearance=raw.get("appearance"),
            raw=raw,
        )

    @staticmethod
    def _summarize_events(events) -> str:
        lines = []
        for e in events:
            payload = e["payload"]
            if payload:
                try:
                    payload_str = json.dumps(json.loads(payload))
                except Exception:
                    payload_str = payload
                lines.append(f"  - {e['event_kind']}: {payload_str}")
            else:
                lines.append(f"  - {e['event_kind']}")
        return "\n".join(lines)

    async def _ollama_generate(self, model: str, prompt: str) -> t.Optional[str]:
        """One Ollama /api/generate call. Returns None on failure (logs)."""
        if self._http is None:
            return None
        try:
            r = await self._http.post(
                f"{self.config.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_ctx": 4096, "temperature": 0.7},
                },
            )
            if r.status_code != 200:
                log.warning("ollama returned %d: %s", r.status_code, r.text[:200])
                return None
            data = r.json()
            return data.get("response")
        except Exception as e:
            log.warning("ollama request failed: %s", e)
            return None

    @staticmethod
    def _extract_json(s: str) -> dict:
        """LLMs sometimes wrap JSON in markdown fences. Be lenient."""
        s = s.strip()
        if s.startswith("```"):
            # strip leading code fence and language tag
            s = s.split("\n", 1)[1] if "\n" in s else s[3:]
            if s.endswith("```"):
                s = s[:-3]
        # find the outermost { ... }
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError(f"no JSON object found in response")
        return json.loads(s[start:end + 1])
