"""Standalone CLI runner for the orchestrator. Doubles as the smoke test.

Usage:
    python -m server.agent_orchestrator.cli load    --agents-dir agents/
    python -m server.agent_orchestrator.cli list    --zone bastok_markets
    python -m server.agent_orchestrator.cli show    --agent-id vendor_zaldon
    python -m server.agent_orchestrator.cli reflect --agent-id vendor_zaldon
    python -m server.agent_orchestrator.cli loop    --tick-seconds 30

The `loop` command runs the asyncio reflection loop until Ctrl+C.
The `reflect` command forces a one-off reflection (useful to verify
Ollama connectivity end-to-end).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import textwrap

from .orchestrator import AgentOrchestrator, OrchestratorConfig


def _build_orchestrator(args: argparse.Namespace) -> AgentOrchestrator:
    cfg = OrchestratorConfig(
        agents_dir=args.agents_dir,
        db_path=args.db_path,
        ollama_url=args.ollama_url,
        tier2_model=args.tier2_model,
        tier3_model=args.tier3_model,
        tick_seconds=getattr(args, "tick_seconds", 10.0),
    )
    return AgentOrchestrator(cfg)


def cmd_load(args: argparse.Namespace) -> int:
    orch = _build_orchestrator(args)
    n = orch.load_all()
    print(f"Loaded {n} agent profile(s) from {args.agents_dir}")
    print(f"DB: {args.db_path}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    orch = _build_orchestrator(args)
    rows = orch.list_agents(zone=args.zone, tier=args.tier)
    if not rows:
        print("(no agents — run `load` first)")
        return 0
    for r in rows:
        print(f"  [{r['tier']:14s}] {r['id']:30s} ({r['name']}, {r['zone']})")
    print(f"\n{len(rows)} total")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    orch = _build_orchestrator(args)
    state = orch.get_state(args.agent_id)
    print(json.dumps(state, indent=2, default=str))
    return 0 if "error" not in state else 1


def cmd_reflect(args: argparse.Namespace) -> int:
    orch = _build_orchestrator(args)

    async def run():
        # Need to start the http client
        orch._stop_event.clear()
        async with __import__("httpx").AsyncClient(timeout=60.0) as http:
            orch._http = http
            state = await orch.force_reflection(args.agent_id)
        print(json.dumps(state, indent=2, default=str))
        return 0 if "error" not in state else 1

    return asyncio.run(run())


def cmd_push_event(args: argparse.Namespace) -> int:
    orch = _build_orchestrator(args)
    payload = json.loads(args.payload) if args.payload else None
    eid = orch.push_event(args.agent_id, args.kind, payload)
    print(f"queued event id={eid}: {args.kind} -> {args.agent_id}")
    return 0


def cmd_loop(args: argparse.Namespace) -> int:
    orch = _build_orchestrator(args)
    orch.load_all()

    async def run():
        try:
            await orch.run_loop()
        except KeyboardInterrupt:
            await orch.stop()

    print("Orchestrator loop running. Ctrl+C to stop.")
    print(f"  Tier-2 interval: {orch.config.tier2_interval_seconds}s")
    print(f"  Tier-3 interval: {orch.config.tier3_interval_seconds}s")
    print(f"  Tick:            {orch.config.tick_seconds}s")
    asyncio.run(run())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="demoncore-agents",
        description="Demoncore agent orchestrator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              load all agents:
                python -m server.agent_orchestrator.cli load \\
                  --agents-dir agents/

              list agents in Bastok Markets:
                python -m server.agent_orchestrator.cli list \\
                  --zone bastok_markets

              run the reflection loop:
                python -m server.agent_orchestrator.cli loop
        """),
    )
    p.add_argument("--agents-dir", default="agents",
                   help="dir containing *.yaml agent profiles")
    p.add_argument("--db-path", default="demoncore_agents.sqlite")
    p.add_argument("--ollama-url", default="http://localhost:11434")
    p.add_argument("--tier2-model", default="llama3.1:8b-instruct-q4_K_M")
    p.add_argument("--tier3-model", default="llama3.1:8b-instruct-q4_K_M")
    p.add_argument("--log-level", default="INFO")

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("load", help="parse + persist all agent YAMLs")
    sp.set_defaults(func=cmd_load)

    sp = sub.add_parser("list", help="list loaded agents")
    sp.add_argument("--zone")
    sp.add_argument("--tier")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="show one agent's full state")
    sp.add_argument("--agent-id", required=True)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("reflect", help="force one reflection cycle (calls Ollama)")
    sp.add_argument("--agent-id", required=True)
    sp.set_defaults(func=cmd_reflect)

    sp = sub.add_parser("push-event", help="queue an event for an agent")
    sp.add_argument("--agent-id", required=True)
    sp.add_argument("--kind", required=True,
                    help="event kind, e.g. aoe_near, outlaw_walked_past")
    sp.add_argument("--payload", default=None,
                    help="optional JSON payload")
    sp.set_defaults(func=cmd_push_event)

    sp = sub.add_parser("loop", help="run the orchestrator main loop")
    sp.add_argument("--tick-seconds", type=float, default=10.0)
    sp.set_defaults(func=cmd_loop)

    args = p.parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
