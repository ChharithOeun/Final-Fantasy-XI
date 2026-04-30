"""MCP tool wrappers around the agent orchestrator.

Exposes the orchestrator's public API as MCP tools that chharbot
can call from chat. This is what turns the orchestrator from "a
package you import" into "a service the user talks to in plain
English".

Each tool here is a thin wrapper around the corresponding
orchestrator method, with:
- input validation suitable for MCP (string types, optional fields)
- output JSON-serialization (so the LLM can read the response)
- friendly error messages rather than tracebacks
- a docstring that becomes the tool's MCP description

Usage from chharbot:

    from agent_orchestrator import AgentOrchestrator
    from agent_orchestrator.mcp_tools import register_tools

    orch = AgentOrchestrator(config)
    orch.load_all()

    register_tools(mcp_server, orch)   # registers all 7 tools

After this, the user can type things like:
    "list all agents in bastok_markets"
    "what's Zaldon's current mood?"
    "queue an aoe_near event for Pellah"
    "force a reflection for Cid"
    "tick the world forward"
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
import typing as t

from .game_clock import vanadiel_at, vanadiel_now
from .loader import AgentProfile
from .mood_propagation import apply_event, propagate_once
from .orchestrator import AgentOrchestrator
from .scheduler import Scheduler


log = logging.getLogger("demoncore.mcp")


# ----------------------------------------------------------------------------
# Tool implementations — pure-Python, MCP-server-agnostic.
# Each returns a JSON-serializable dict.
# ----------------------------------------------------------------------------

def tool_list_agents(orch: AgentOrchestrator,
                     zone: t.Optional[str] = None,
                     tier: t.Optional[str] = None) -> dict:
    """List Demoncore agents, optionally filtered by zone or tier.

    Args:
        zone: zone slug to filter by (e.g. 'bastok_markets')
        tier: tier code to filter by ('0_reactive' | '1_scripted' |
              '2_reflection' | '3_hero' | '4_rl')
    """
    rows = orch.list_agents(zone=zone, tier=tier)
    return {
        "ok": True,
        "count": len(rows),
        "filter": {"zone": zone, "tier": tier},
        "agents": [
            {"id": r["id"], "name": r["name"], "zone": r["zone"],
             "tier": r["tier"], "role": r["role"]}
            for r in rows
        ],
    }


def tool_get_agent_state(orch: AgentOrchestrator,
                         agent_id: str) -> dict:
    """Inspect one agent's full state (profile + tier-specific state).

    Returns mood + memory_summary for Tier-2, current_goal + journal
    for Tier-3, just the profile for others.
    """
    state = orch.get_state(agent_id)
    if "error" in state:
        return {"ok": False, "error": state["error"]}
    return {"ok": True, "state": state}


def tool_push_event(orch: AgentOrchestrator,
                    agent_id: str,
                    event_kind: str,
                    payload_json: t.Optional[str] = None) -> dict:
    """Queue a combat / narrative event for an agent.

    The event flows through the deterministic event_deltas table —
    no LLM call. The agent's mood may change immediately if the
    event matches a delta entry.

    Args:
        agent_id: agent id
        event_kind: one of the canonical events from event_deltas
                    (aoe_near, structure_destroyed_near, outlaw_walked_past,
                    skillchain_called, intervention_mb_succeeded, etc)
        payload_json: optional JSON string with additional context
    """
    payload = None
    if payload_json:
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"invalid payload_json: {e}"}

    profile = orch._load_profile(agent_id)
    if profile is None:
        return {"ok": False, "error": f"unknown agent: {agent_id}"}

    # Apply event synchronously through the mood-delta path
    flipped = apply_event(orch.db, profile, event_kind, payload)
    # Also persist it to the inbox so the next reflection sees it
    event_id = orch.push_event(agent_id, event_kind, payload)

    return {
        "ok": True,
        "agent_id": agent_id,
        "event_kind": event_kind,
        "mood_changed": flipped,
        "queued_event_id": event_id,
    }


async def tool_force_reflection(orch: AgentOrchestrator,
                                 agent_id: str) -> dict:
    """Force a Tier-2 or Tier-3 reflection cycle now.

    Calls Ollama. Updates the agent's memory_summary (Tier-2) or
    appends a journal entry (Tier-3). Useful for testing the LLM
    pipeline end-to-end without waiting for the natural cycle.
    """
    state = await orch.force_reflection(agent_id)
    if "error" in state:
        return {"ok": False, "error": state["error"]}
    return {"ok": True, "state": state}


def tool_propagate_moods(orch: AgentOrchestrator) -> dict:
    """Run one mood-propagation pass across the relationship graph.

    Walks every Tier-2 agent's relationships, applies weighted mood
    pulls from related agents, snaps to nearest declared mood. No
    LLM call. Returns the mood changes that occurred.
    """
    profiles_by_id: dict[str, AgentProfile] = {}
    for row in orch.list_agents():
        prof = orch._load_profile(row["id"])
        if prof is not None:
            profiles_by_id[prof.id] = prof
    changes = propagate_once(orch.db, profiles_by_id)
    return {
        "ok": True,
        "changes": [{"agent_id": aid, "new_mood": mood}
                    for aid, mood in changes.items()],
    }


def tool_tick_scheduler(orch: AgentOrchestrator,
                        wall_seconds: t.Optional[float] = None) -> dict:
    """Advance the Vana'diel scheduler by one tick.

    By default uses the current real wall-clock time. Pass an
    explicit `wall_seconds` (since unix epoch) for deterministic
    testing.

    Fires schedule_slot_fired events for any agent whose schedule
    just crossed a boundary, and ENVIRONMENTAL_HOURS events for
    each zone whose hour just changed.
    """
    profiles_by_id: dict[str, AgentProfile] = {}
    for row in orch.list_agents():
        prof = orch._load_profile(row["id"])
        if prof is not None:
            profiles_by_id[prof.id] = prof

    if wall_seconds is None:
        vana = vanadiel_now()
    else:
        vana = vanadiel_at(wall_seconds)

    scheduler = Scheduler(orch.db)
    report = scheduler.tick(vana, profiles_by_id)
    return {
        "ok": True,
        "vana_time": str(vana),
        "schedule_events_fired": [
            {"agent_id": aid, "slot_index": idx}
            for (aid, idx) in report["schedule_events_fired"]
        ],
        "environmental_events_fired": [
            {"zone": z, "event": e}
            for (z, e) in report["environmental_events_fired"]
        ],
    }


def tool_summary(orch: AgentOrchestrator) -> dict:
    """High-level Demoncore world summary.

    Returns counts by tier, by zone, agents currently in non-default
    moods, and the current Vana'diel time. The 'state of the world'
    snapshot.
    """
    rows = orch.list_agents()

    by_tier: dict[str, int] = {}
    by_zone: dict[str, int] = {}
    for r in rows:
        by_tier[r["tier"]] = by_tier.get(r["tier"], 0) + 1
        by_zone[r["zone"]] = by_zone.get(r["zone"], 0) + 1

    # Tier-2 agents in non-default moods
    interesting_moods = []
    for r in rows:
        if r["tier"] != "2_reflection":
            continue
        st = orch.db.get_tier2_state(r["id"])
        if st is None or st.mood == "content":
            continue
        interesting_moods.append({
            "agent_id": r["id"],
            "name": r["name"],
            "mood": st.mood,
        })

    return {
        "ok": True,
        "vana_time": str(vanadiel_now()),
        "total_agents": len(rows),
        "by_tier": by_tier,
        "by_zone": by_zone,
        "agents_in_non_default_mood": interesting_moods,
    }


# ----------------------------------------------------------------------------
# MCP server registration helper
# ----------------------------------------------------------------------------

# We don't pin to one specific MCP framework here; we expose a small
# adapter that takes whatever `mcp_server` chharbot uses and registers
# all seven tools via its tool-decoration API. Different MCP server
# libraries name this slightly differently, so we accept the framework
# as a duck-typed callable.

def register_tools(mcp_server: t.Any, orch: AgentOrchestrator) -> int:
    """Register all orchestrator MCP tools with the given mcp_server.

    Expected interface: the mcp_server has a `tool()` decorator (FastMCP
    style) OR an `add_tool(callable, name, description)` method.

    Returns the number of tools registered.
    """
    tools_to_register = [
        ("list_agents",
         lambda zone=None, tier=None: tool_list_agents(orch, zone, tier),
         tool_list_agents.__doc__),
        ("get_agent_state",
         lambda agent_id: tool_get_agent_state(orch, agent_id),
         tool_get_agent_state.__doc__),
        ("push_event",
         lambda agent_id, event_kind, payload_json=None:
             tool_push_event(orch, agent_id, event_kind, payload_json),
         tool_push_event.__doc__),
        ("force_reflection",
         lambda agent_id: asyncio.run(tool_force_reflection(orch, agent_id)),
         tool_force_reflection.__doc__),
        ("propagate_moods",
         lambda: tool_propagate_moods(orch),
         tool_propagate_moods.__doc__),
        ("tick_scheduler",
         lambda wall_seconds=None: tool_tick_scheduler(orch, wall_seconds),
         tool_tick_scheduler.__doc__),
        ("summary",
         lambda: tool_summary(orch),
         tool_summary.__doc__),
    ]

    n = 0
    for name, fn, doc in tools_to_register:
        if hasattr(mcp_server, "tool"):
            # FastMCP style: @server.tool() decorator wraps the fn
            decorated = mcp_server.tool(name=name, description=doc)(fn)
            n += 1
        elif hasattr(mcp_server, "add_tool"):
            mcp_server.add_tool(fn, name=name, description=doc)
            n += 1
        else:
            log.warning("mcp_server lacks tool() and add_tool(); skipping %s",
                        name)
    log.info("registered %d MCP tools with %r", n, type(mcp_server).__name__)
    return n
