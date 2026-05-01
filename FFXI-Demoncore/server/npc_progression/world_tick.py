"""world_tick — the per-Vana'diel-hour cron coordinator.

Per NPC_PROGRESSION.md the simulation outline:

    World tick (every Vana'diel hour):
      for each NPC:
        earn(); maybe_buy(); maybe_level_up(); maybe_retire()
      for each active mob:
        update_kill_count(); maybe_level_up()
      for each NM:
        update_survival_time(); maybe_unlock_ability(); maybe_buff_drops()
      for each boss:
        no per-tick change; updates happen per-fight only

This module is the coordinator: caller passes the live entity sets
+ the market listings, and we walk the loop. Returns a summary
WorldTickResult so the cron daemon can log activity.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .civilian import (
    NpcSnapshot,
    award_xp,
    ready_to_retire,
)
from .economic_agent import (
    EconomicAgent,
    MarketListing,
)


@dataclasses.dataclass
class WorldTickResult:
    """Summary of one world-tick. The cron daemon logs this for
    operator visibility."""
    npcs_processed: int = 0
    npcs_levelled_up: int = 0
    npcs_purchases: int = 0
    npcs_total_gil_spent: int = 0
    npcs_ready_to_retire: list[str] = dataclasses.field(default_factory=list)
    notable_events: list[str] = dataclasses.field(default_factory=list)


def world_tick(*,
                economic_agents: list[EconomicAgent],
                market_listings: list[MarketListing],
                hours_elapsed: float = 1.0,
                now: float = 0.0,
                ) -> WorldTickResult:
    """Run one Vana'diel-hour tick across all NPCs.

    Caller batches in 'active' (in-zone-with-players) and 'idle'
    NPCs separately — the doc recommends idle NPCs receive coarse
    once-per-real-day batched ticks while active NPCs tick every
    in-game hour. This function doesn't distinguish; the caller
    chooses the granularity by which agents they include + the
    hours_elapsed parameter.
    """
    result = WorldTickResult()

    for agent in economic_agents:
        if agent.state.is_retired:
            continue
        result.npcs_processed += 1

        level_before = agent.state.level
        # Ambient XP tick (scaled by hours_elapsed)
        for _ in range(int(hours_elapsed)):
            award_xp(agent.state, kind="ambient_tick", now=now)

        # Earn + decide purchase
        purchase = agent.tick(
            hours_elapsed=hours_elapsed,
            listings=market_listings,
            now=now,
        )
        if purchase is not None:
            result.npcs_purchases += 1
            result.npcs_total_gil_spent += purchase.price

        if agent.state.level > level_before:
            result.npcs_levelled_up += 1

        if ready_to_retire(agent.state):
            result.npcs_ready_to_retire.append(agent.state.npc_id)

    return result
