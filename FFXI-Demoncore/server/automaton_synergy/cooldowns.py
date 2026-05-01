"""Per-master, per-ability synergy cooldowns.

Why this is its own module
--------------------------
Synergy cooldowns are long (3-15 minutes) and player-specific.
Two PUPs in the same party can each fire Death Spikes at the same
time — the cooldown is per master, not global. The tracker needs
to answer two questions cheaply:

  1. Is master M's ability A on cooldown right now?
  2. When can master M next fire ability A?

We model it as a dict keyed by (master_id, ability_id) holding
the earliest tick when the ability becomes available. Triggering
the ability sets the entry; checking compares current tick.

The tracker is a pure container — no IO, no wall clock. All time
values come from the caller, matching the rest of the server's
deterministic-time philosophy.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class CooldownTracker:
    """Per-master, per-ability cooldown tracker."""

    # (master_id, ability_id) -> earliest_next_trigger_tick
    _next_available: dict[tuple[str, str], int] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def trigger(
        self,
        *,
        master_id: str,
        ability_id: str,
        cooldown_seconds: int,
        now_tick: int,
    ) -> int:
        """Mark the ability triggered. Returns the tick at which
        it will next be available."""
        if cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be >= 0")
        next_tick = now_tick + cooldown_seconds
        self._next_available[(master_id, ability_id)] = next_tick
        return next_tick

    def can_trigger(
        self,
        *,
        master_id: str,
        ability_id: str,
        now_tick: int,
    ) -> bool:
        """True if the ability can fire right now."""
        next_tick = self._next_available.get(
            (master_id, ability_id),
        )
        if next_tick is None:
            return True
        return now_tick >= next_tick

    def next_available(
        self,
        *,
        master_id: str,
        ability_id: str,
    ) -> t.Optional[int]:
        """When can this ability next be triggered? None if never
        triggered (so always available)."""
        return self._next_available.get(
            (master_id, ability_id),
        )

    def remaining(
        self,
        *,
        master_id: str,
        ability_id: str,
        now_tick: int,
    ) -> int:
        """How many seconds remain on the cooldown? 0 if ready."""
        next_tick = self._next_available.get(
            (master_id, ability_id),
        )
        if next_tick is None:
            return 0
        return max(0, next_tick - now_tick)

    def clear(
        self,
        *,
        master_id: t.Optional[str] = None,
        ability_id: t.Optional[str] = None,
    ) -> int:
        """Clear cooldowns matching the filter. Returns number cleared.

        Both filters omitted -> clear everything (admin reset).
        Only master_id given -> clear all of one master's cooldowns.
        Only ability_id given -> clear all masters of one ability.
        Both given -> clear that one entry.
        """
        before = len(self._next_available)
        if master_id is None and ability_id is None:
            self._next_available.clear()
        else:
            survivors = {
                key: val
                for key, val in self._next_available.items()
                if not (
                    (master_id is None or key[0] == master_id)
                    and
                    (ability_id is None or key[1] == ability_id)
                )
            }
            self._next_available = survivors
        return before - len(self._next_available)

    def active_count(self, *, now_tick: int) -> int:
        """How many cooldowns are currently still pending?"""
        return sum(
            1 for v in self._next_available.values()
            if v > now_tick
        )


__all__ = ["CooldownTracker"]
