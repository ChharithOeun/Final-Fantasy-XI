"""Demoncore agent orchestrator.

Reads agents/*.yaml profiles, instantiates each agent at the right AI tier
per AI_WORLD_DENSITY.md, runs Tier-2 reflection cycles and Tier-3 generative
loops, and exposes MCP tools chharbot can call.

Public surface:
    AgentOrchestrator              — main class; one instance per server
    AgentOrchestrator.load_all     — walk agents/ dir, populate DB
    AgentOrchestrator.run_loop     — async main loop
    AgentOrchestrator.push_event   — feed an event to an agent's reflection queue
    AgentOrchestrator.get_state    — snapshot for chharbot inspection
    AgentOrchestrator.list_agents  — list all known agents

The orchestrator is intentionally not a long-running daemon — chharbot
spawns it as a coroutine inside its existing event loop. That way one
process owns Ollama connections, the LSB event bus subscription, and the
agent state instead of a fleet of mini-services.
"""
from .orchestrator import AgentOrchestrator
from .loader import load_agent_yaml, AgentProfile, ProfileError

__all__ = [
    "AgentOrchestrator",
    "AgentProfile",
    "load_agent_yaml",
    "ProfileError",
]
