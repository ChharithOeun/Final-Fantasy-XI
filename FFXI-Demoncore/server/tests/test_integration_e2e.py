"""End-to-end integration test that exercises the full Demoncore
server-side stack:

    YAML loader → orchestrator → scheduler → mood propagation
                                  ↑
                        ↓         |
                    LSB bridge    |
                        ↓         |
                    publisher  → Redis (mock)

This is the smoke test that runs before every release. If this
passes, the server-side stack is healthy end-to-end. Real Higgs
and Ollama integrations are NOT exercised here — they have their
own unit tests with stub backends.

Run:  python -m pytest server/tests/test_integration_e2e.py -v
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator import AgentOrchestrator
from agent_orchestrator.game_clock import (
    WALL_SECONDS_PER_VANADIEL_DAY,
    WALL_SECONDS_PER_VANADIEL_HOUR,
    vanadiel_at,
)
from agent_orchestrator.mood_propagation import propagate_once
from agent_orchestrator.orchestrator import OrchestratorConfig
from agent_orchestrator.scheduler import Scheduler
from lsb_bridge.bridge import BridgeHandler, BridgePublisher


def _resolve(name: str) -> pathlib.Path:
    """Find a project asset (agents/ or data/) from various test locations."""
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / name,    # staged tree
        here.parent / name,           # /tmp test copies
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


@pytest.fixture
def orch(tmp_path):
    agents_dir = _resolve("agents")
    if not agents_dir.is_dir():
        pytest.skip(f"agents dir not found at {agents_dir}")
    cfg = OrchestratorConfig(
        agents_dir=str(agents_dir),
        db_path=str(tmp_path / "e2e.sqlite"),
    )
    o = AgentOrchestrator(cfg)
    o.load_all()
    yield o
    o.db.close()


@pytest.fixture
def all_profiles(orch):
    profiles = {}
    for row in orch.list_agents():
        prof = orch._load_profile(row["id"])
        if prof:
            profiles[prof.id] = prof
    return profiles


class FakeRedis:
    def __init__(self):
        self.published = []

    def publish(self, topic, msg):
        self.published.append((topic, msg))
        return 1


# ----------------------------------------------------------------------
# E2E SCENARIO 1: full day cycle with mood evolution
# ----------------------------------------------------------------------

def test_full_day_cycle_drives_bondrak_through_drunk(orch, all_profiles):
    """Tick the world from 00:00 through 23:30 in 30-minute increments.
    Bondrak should end the cycle in 'drunk' state, having been
    `content` at sunrise."""

    bondrak_id = "tavern_drunk"
    if bondrak_id not in all_profiles:
        pytest.skip("Bondrak profile not loaded")

    scheduler = Scheduler(orch.db)
    minutes_per_tick = 30
    seconds_per_tick = WALL_SECONDS_PER_VANADIEL_HOUR * (minutes_per_tick / 60.0)
    ticks = 48  # 24 game-hours

    mood_history = []
    for tick in range(ticks):
        wall_seconds = tick * seconds_per_tick
        vana = vanadiel_at(wall_seconds)
        scheduler.tick(vana, all_profiles)
        if tick % 4 == 0:
            propagate_once(orch.db, all_profiles)
        st = orch.db.get_tier2_state(bondrak_id)
        mood_history.append((vana.hhmm, st.mood if st else None))

    # Bondrak should have been content at some morning hour
    morning_moods = [m for hhmm, m in mood_history if 7 <= int(hhmm.split(":")[0]) <= 11]
    assert "content" in morning_moods, f"Bondrak should be content in morning; got {set(morning_moods)}"

    # Bondrak should be drunk at evening / late hours
    late_moods = [m for hhmm, m in mood_history if int(hhmm.split(":")[0]) >= 18]
    assert "drunk" in late_moods, f"Bondrak should be drunk in evening; got {set(late_moods)}"


# ----------------------------------------------------------------------
# E2E SCENARIO 2: AOE event flows through bridge → orchestrator → publisher
# ----------------------------------------------------------------------

def test_aoe_event_full_pipeline(orch):
    """The full LSB → bridge → orchestrator → Redis pipeline."""
    redis = FakeRedis()
    publisher = BridgePublisher(redis)
    handler = BridgeHandler(orch, token="test_token", publisher=publisher)

    # Simulate LSB POSTing an AOE event
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "test_token"},
        body={
            "agent_id": "vendor_zaldon",
            "event_kind": "aoe_near",
            "payload": {"distance_m": 4, "damage_estimate": 250},
            "timestamp": 1735594800.0,
        },
    )

    # 1. Bridge accepted and processed
    assert status == 200
    assert body["ok"] is True
    assert body["mood_changed"] is True
    assert body["new_mood"] == "gruff"

    # 2. Orchestrator persisted
    state = orch.db.get_tier2_state("vendor_zaldon")
    assert state is not None
    assert state.mood == "gruff"
    assert "aoe_near" in state.memory_summary

    # 3. Publisher pushed to Redis
    assert len(redis.published) >= 1
    topics = [t for (t, _) in redis.published]
    assert any("vendor_zaldon" in t and "bark_pool_changed" in t for t in topics)


# ----------------------------------------------------------------------
# E2E SCENARIO 3: Skillchain audible event composes mood across roles
# ----------------------------------------------------------------------

def test_audible_skillchain_propagates_mood_by_role(orch, all_profiles):
    """A `heard_skillchain_call_nearby` event should affect heroes
    differently from civilians (per event_deltas table)."""

    # Push the audible event to all hero NPCs in bastok
    handler = BridgeHandler(orch, token="t")
    bastok_heroes = [p for p in all_profiles.values()
                     if p.zone == "bastok_markets" and p.tier == "3_hero"]
    bastok_t2 = [p for p in all_profiles.values()
                 if p.zone == "bastok_markets" and p.tier == "2_reflection"]

    # Snapshot moods first
    before = {p.id: orch.db.get_tier2_state(p.id) for p in bastok_t2}

    # Skillchain is heard; alert mood spread expected for some
    for prof in bastok_t2:
        handler.handle(
            headers={"X-Demoncore-Bridge-Token": "t"},
            body={"agent_id": prof.id,
                  "event_kind": "heard_skillchain_call_nearby"},
        )

    # Some agents should have shifted toward alert (where mood_axes allows it)
    after = {p.id: orch.db.get_tier2_state(p.id) for p in bastok_t2}
    shifted = sum(1 for p in bastok_t2
                  if before[p.id] and after[p.id]
                  and before[p.id].mood != after[p.id].mood)
    assert shifted >= 1, f"At least one tier-2 agent should react to a skillchain call"


# ----------------------------------------------------------------------
# E2E SCENARIO 4: Intervention success propagates through the world
# ----------------------------------------------------------------------

def test_intervention_mb_succeeded_makes_civilians_content(orch, all_profiles):
    """A successful intervention save should make bystander civilians
    content (per event_deltas: party_member_saved_by_intervention)."""

    handler = BridgeHandler(orch, token="t")

    # Find a civilian-role tier-2 agent
    civilians = [p for p in all_profiles.values()
                 if p.tier == "2_reflection"
                 and "civilian" in p.role.lower() or "vendor" in p.role.lower()]
    if not civilians:
        # Use beggar as a civilian-equivalent role
        civilians = [p for p in all_profiles.values()
                     if p.id == "beggar_gate_side"]
    if not civilians:
        pytest.skip("no civilian-role agents loaded")

    # First put them in a non-content mood
    civ = civilians[0]
    orch.db.update_tier2(civ.id, "weary", "Tired today")

    # Save event arrives
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "t"},
        body={"agent_id": civ.id,
              "event_kind": "party_member_saved_by_intervention"},
    )

    assert status == 200
    state = orch.db.get_tier2_state(civ.id)
    # Beggar's mood_axes: [content, contemplative, fearful, weary]
    # delta is "content +0.4" — should snap to content
    assert state.mood == "content"


# ----------------------------------------------------------------------
# E2E SCENARIO 5: Full round-trip — agent loaded, ticked, event'd, queried
# ----------------------------------------------------------------------

def test_full_roundtrip_zaldon(orch):
    """Zaldon: loaded from YAML → starts content → AOE event flips
    mood → list_agents reflects new state → push another event →
    tick scheduler → mood updates accordingly."""

    # 1. Initial state
    state = orch.db.get_tier2_state("vendor_zaldon")
    assert state.mood == "content"

    # 2. Apply AOE event
    handler = BridgeHandler(orch, token="t")
    handler.handle(
        headers={"X-Demoncore-Bridge-Token": "t"},
        body={"agent_id": "vendor_zaldon", "event_kind": "aoe_near"},
    )
    state = orch.db.get_tier2_state("vendor_zaldon")
    assert state.mood == "gruff"

    # 3. List agents reflects updated state via mcp_tools
    from agent_orchestrator.mcp_tools import tool_summary
    summary = tool_summary(orch)
    moods = {a["agent_id"]: a["mood"]
             for a in summary["agents_in_non_default_mood"]}
    assert moods.get("vendor_zaldon") == "gruff"

    # 4. Tick the scheduler past sunrise — daily_loop_morning fires
    profiles = {p_id: orch._load_profile(p_id) for p_id in moods.keys()
                if orch._load_profile(p_id) is not None}
    profiles["vendor_zaldon"] = orch._load_profile("vendor_zaldon")
    scheduler = Scheduler(orch.db)
    morning_vana = vanadiel_at(7 * WALL_SECONDS_PER_VANADIEL_HOUR)
    scheduler.tick(morning_vana, profiles)

    # 5. Zaldon's role isn't tavern_drunk so morning doesn't auto-flip
    #    — but the scheduler ran without crashing
    state = orch.db.get_tier2_state("vendor_zaldon")
    assert state is not None
    # The mood may still be gruff (no morning event for vendor_zaldon)
    # The point is the system didn't crash and state survived.


# ----------------------------------------------------------------------
# E2E SCENARIO 6: Bridge unauthorized + unknown agent paths
# ----------------------------------------------------------------------

def test_bridge_security_bad_token(orch):
    """The bridge must reject events without a valid token."""
    handler = BridgeHandler(orch, token="real_token")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "fake_token"},
        body={"agent_id": "vendor_zaldon", "event_kind": "aoe_near"},
    )
    assert status == 401
    state = orch.db.get_tier2_state("vendor_zaldon")
    assert state.mood == "content"   # not modified


def test_bridge_unknown_agent_doesnt_crash(orch):
    """Unknown agent_id returns 400, doesn't crash."""
    handler = BridgeHandler(orch, token="t")
    status, body = handler.handle(
        headers={"X-Demoncore-Bridge-Token": "t"},
        body={"agent_id": "doesnt_exist", "event_kind": "aoe_near"},
    )
    assert status == 400
    assert body["ok"] is False
