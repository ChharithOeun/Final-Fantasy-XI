"""Tests for the MCP tool wrappers.

Run:  python -m pytest server/tests/test_mcp_tools.py -v
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from agent_orchestrator import AgentOrchestrator
from agent_orchestrator.mcp_tools import (
    register_tools,
    tool_get_agent_state,
    tool_list_agents,
    tool_propagate_moods,
    tool_push_event,
    tool_summary,
    tool_tick_scheduler,
)
from agent_orchestrator.orchestrator import OrchestratorConfig


@pytest.fixture
def orch(tmp_path):
    """Build an orchestrator with the real flagship agent profiles."""
    # agents/ lives as a sibling of server/ in the staging tree, but in
    # /tmp test copies we replicate it into server/agents/. Try both.
    here = pathlib.Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "agents",   # staged tree: stage-monorepo/agents
        here.parent / "agents",          # /tmp test copy: server/agents
    ]
    agents_dir = next((p for p in candidates if p.is_dir()), candidates[0])
    if not agents_dir.is_dir():
        pytest.skip(f"agents dir not present at {agents_dir}")
    cfg = OrchestratorConfig(
        agents_dir=str(agents_dir),
        db_path=str(tmp_path / "test.sqlite"),
    )
    o = AgentOrchestrator(cfg)
    o.load_all()
    yield o
    o.db.close()


def test_list_agents_no_filter(orch):
    result = tool_list_agents(orch)
    assert result["ok"] is True
    assert result["count"] >= 20
    # spot-check known agents
    ids = {a["id"] for a in result["agents"]}
    assert "vendor_zaldon" in ids
    assert "hero_cid" in ids


def test_list_agents_zone_filter(orch):
    result = tool_list_agents(orch, zone="bastok_markets")
    assert result["ok"] is True
    assert all(a["zone"] == "bastok_markets" for a in result["agents"])


def test_list_agents_tier_filter(orch):
    result = tool_list_agents(orch, tier="3_hero")
    assert result["ok"] is True
    assert all(a["tier"] == "3_hero" for a in result["agents"])
    # We should have Cid, Volker, Cornelia, Maat, Curilla, Kerutoto, Yorisha
    assert result["count"] >= 7


def test_get_agent_state_known(orch):
    result = tool_get_agent_state(orch, "vendor_zaldon")
    assert result["ok"] is True
    assert result["state"]["agent_id"] == "vendor_zaldon"
    assert result["state"]["state"]["mood"] == "content"


def test_get_agent_state_unknown(orch):
    result = tool_get_agent_state(orch, "definitely_not_a_real_agent")
    assert result["ok"] is False
    assert "unknown" in result["error"]


def test_push_event_flips_mood(orch):
    # Start mood
    before = tool_get_agent_state(orch, "vendor_zaldon")
    assert before["state"]["state"]["mood"] == "content"

    # AOE near a vendor → gruff (per event_deltas table)
    result = tool_push_event(orch, "vendor_zaldon", "aoe_near")
    assert result["ok"] is True
    assert result["mood_changed"] is True

    # Verify
    after = tool_get_agent_state(orch, "vendor_zaldon")
    assert after["state"]["state"]["mood"] == "gruff"


def test_push_event_with_json_payload(orch):
    result = tool_push_event(
        orch, "vendor_zaldon", "outlaw_walked_past",
        payload_json='{"distance_m": 3, "outlaw_id": "alice"}',
    )
    assert result["ok"] is True


def test_push_event_invalid_json(orch):
    result = tool_push_event(
        orch, "vendor_zaldon", "outlaw_walked_past",
        payload_json="this is not json",
    )
    assert result["ok"] is False
    assert "invalid payload_json" in result["error"]


def test_push_event_unknown_agent(orch):
    result = tool_push_event(orch, "ghost_agent", "aoe_near")
    assert result["ok"] is False


def test_propagate_moods_runs(orch):
    # Push Cornelia gruff first
    tool_push_event(orch, "hero_cornelia", "structure_destroyed_near")
    # (hero_cornelia mood may stay the same because tier 3 doesn't track
    # mood column today; but propagation across tier-2s should still run)
    result = tool_propagate_moods(orch)
    assert result["ok"] is True


def test_tick_scheduler_with_explicit_time(orch):
    # Tick at Vana'diel hour 18 (daily_loop_evening fires)
    from agent_orchestrator.game_clock import WALL_SECONDS_PER_VANADIEL_HOUR
    result = tool_tick_scheduler(orch, wall_seconds=18 * WALL_SECONDS_PER_VANADIEL_HOUR)
    assert result["ok"] is True
    # daily_loop_evening event should have fired
    env_events = result["environmental_events_fired"]
    assert any(e["event"] == "daily_loop_evening" for e in env_events)


def test_summary_shape(orch):
    result = tool_summary(orch)
    assert result["ok"] is True
    assert "vana_time" in result
    assert result["total_agents"] >= 20
    assert "by_tier" in result
    assert "by_zone" in result
    # agents_in_non_default_mood is always a list
    assert isinstance(result["agents_in_non_default_mood"], list)


def test_summary_after_event(orch):
    """After an AOE event flips Zaldon, the summary should reflect it."""
    tool_push_event(orch, "vendor_zaldon", "aoe_near")
    result = tool_summary(orch)
    moods = {a["agent_id"]: a["mood"] for a in result["agents_in_non_default_mood"]}
    assert moods.get("vendor_zaldon") == "gruff"


# ---------------------------------------------------------------------------
# register_tools adapter
# ---------------------------------------------------------------------------

class FakeFastMcpServer:
    """Minimal FastMCP-style server for testing register_tools()."""
    def __init__(self):
        self.registered = []

    def tool(self, name, description):
        def decorator(fn):
            self.registered.append((name, fn, description))
            return fn
        return decorator


class FakeAddToolServer:
    """Alternative add_tool() style server."""
    def __init__(self):
        self.registered = []

    def add_tool(self, fn, name, description):
        self.registered.append((name, fn, description))


def test_register_tools_fastmcp_style(orch):
    server = FakeFastMcpServer()
    n = register_tools(server, orch)
    assert n == 7
    names = {r[0] for r in server.registered}
    assert names == {
        "list_agents", "get_agent_state", "push_event",
        "force_reflection", "propagate_moods", "tick_scheduler", "summary",
    }


def test_register_tools_addtool_style(orch):
    server = FakeAddToolServer()
    n = register_tools(server, orch)
    assert n == 7


def test_register_tools_handles_missing_interface(orch, caplog):
    class EmptyServer:
        pass
    n = register_tools(EmptyServer(), orch)
    assert n == 0  # nothing registered, gracefully handled
