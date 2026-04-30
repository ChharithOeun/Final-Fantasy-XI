"""24-Vana'diel-hour fast-forward demo.

Loads all agent YAMLs, runs the scheduler tick at 30-Vana'diel-minute
intervals across one full day, prints the world breathing.

Usage:
    cd <repo>/server
    python -m agent_orchestrator.demo_24h --agents-dir ../agents

This is the "visceral proof" that the data layer + scheduler combine
into living agents. No LLM calls — just the deterministic event_deltas
+ mood_propagation + scheduler tick. Even without Ollama, the world
moves: Bondrak shifts content -> drunk -> drunk -> melancholy across
the day, Mavi the pickpocket goes alert -> alert -> content as night
falls.

Output is a small terminal log — one line per state change. Easy to
read. Easy to share. Easy to use as a sanity check before turning on
the LLM reflection loop in production.
"""
from __future__ import annotations

import argparse
import logging
import pathlib
import sys

from .db import AgentDB
from .game_clock import (
    WALL_SECONDS_PER_VANADIEL_DAY,
    WALL_SECONDS_PER_VANADIEL_HOUR,
    vanadiel_at,
)
from .loader import load_all_agents
from .mood_propagation import propagate_once
from .scheduler import Scheduler


def _moods_snapshot(db: AgentDB, profile_ids: list[str]) -> dict[str, str]:
    out = {}
    for aid in profile_ids:
        st = db.get_tier2_state(aid)
        if st:
            out[aid] = st.mood
    return out


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--agents-dir", default="../agents")
    p.add_argument("--db-path", default=":memory:")
    p.add_argument("--minutes-per-tick", type=int, default=30,
                   help="Vana'diel minutes between scheduler ticks")
    p.add_argument("--ticks", type=int, default=48,
                   help="Number of ticks to run (default 48 = 24 game-hours)")
    p.add_argument("--verbose", action="store_true",
                   help="Print env-events fired per tick")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    agents_path = pathlib.Path(args.agents_dir).resolve()
    print(f"Loading agents from {agents_path}")
    profiles = load_all_agents(agents_path)
    print(f"Loaded {len(profiles)} profiles\n")

    db = AgentDB(args.db_path)
    for p_ in profiles:
        db.upsert_agent(p_)

    profiles_by_id = {p_.id: p_ for p_ in profiles}
    tier2_ids = [p_.id for p_ in profiles if p_.tier == "2_reflection"]
    scheduler = Scheduler(db)

    # Print initial state
    print("=" * 72)
    print("INITIAL STATE")
    print("=" * 72)
    for aid in tier2_ids:
        st = db.get_tier2_state(aid)
        prof = profiles_by_id[aid]
        print(f"  {prof.name:25s} mood={st.mood}  ({prof.role})")
    print()

    # Step through Vana'diel time
    minutes_per_tick = args.minutes_per_tick
    seconds_per_tick = WALL_SECONDS_PER_VANADIEL_HOUR * (minutes_per_tick / 60.0)

    prev_moods = _moods_snapshot(db, tier2_ids)
    state_changes_total = 0

    print("=" * 72)
    print(f"RUNNING {args.ticks} TICKS — {minutes_per_tick} Vana'diel min each")
    print("=" * 72)

    for tick in range(args.ticks):
        wall_seconds = tick * seconds_per_tick
        vana = vanadiel_at(wall_seconds)
        report = scheduler.tick(vana, profiles_by_id)

        # Run a propagation pass every 4 ticks
        if tick % 4 == 0:
            propagate_once(db, profiles_by_id)

        new_moods = _moods_snapshot(db, tier2_ids)
        for aid, new_mood in new_moods.items():
            if prev_moods.get(aid) != new_mood:
                prof = profiles_by_id[aid]
                print(f"  [{vana.hhmm}] {prof.name:25s} "
                      f"{prev_moods.get(aid, '-'):>11s} -> {new_mood}")
                state_changes_total += 1
        prev_moods = new_moods

        if args.verbose and report["environmental_events_fired"]:
            for (zone, ev) in report["environmental_events_fired"]:
                print(f"  [{vana.hhmm}]   ENV  {zone}: {ev}")

    # Final state
    print()
    print("=" * 72)
    print(f"FINAL STATE  (after {state_changes_total} mood transitions)")
    print("=" * 72)
    for aid in tier2_ids:
        st = db.get_tier2_state(aid)
        prof = profiles_by_id[aid]
        print(f"  {prof.name:25s} mood={st.mood}  memory={st.memory_summary[:60]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
