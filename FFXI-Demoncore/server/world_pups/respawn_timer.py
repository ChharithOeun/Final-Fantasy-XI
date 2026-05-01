"""24-hour earth-time respawn tracker for Rogue Automaton NMs.

Per the user direction: 'each respawns every 24hrs earth time'. The
tracker is a simple per-NM last-killed-at -> next-spawn-at map.
"""
from __future__ import annotations

import dataclasses
import typing as t


ROGUE_AUTOMATON_RESPAWN_SECONDS = 24 * 3600


@dataclasses.dataclass
class RespawnRecord:
    nm_id: str
    last_killed_at: float
    next_spawn_at: float


class RespawnTracker:
    """Tracks 24hr respawn windows for Rogue Automaton NMs.

    The tracker is intentionally small and pure: caller persists the
    state externally and re-hydrates the records on server restart.
    """

    def __init__(self) -> None:
        self._records: dict[str, RespawnRecord] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def notify_killed(self, nm_id: str, *, now: float) -> RespawnRecord:
        """Record a kill. Returns the resulting RespawnRecord with
        next_spawn_at set 24h ahead."""
        rec = RespawnRecord(
            nm_id=nm_id, last_killed_at=now,
            next_spawn_at=now + ROGUE_AUTOMATON_RESPAWN_SECONDS,
        )
        self._records[nm_id] = rec
        return rec

    def force_spawn(self, nm_id: str) -> bool:
        """GM force-respawn (or initial spawn at server start)."""
        return self._records.pop(nm_id, None) is not None

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def is_spawned(self, nm_id: str, *, now: float) -> bool:
        """An NM is 'spawned' if it's never been killed OR its respawn
        timer has elapsed."""
        rec = self._records.get(nm_id)
        if rec is None:
            return True
        return now >= rec.next_spawn_at

    def time_until_spawn(self, nm_id: str, *, now: float) -> float:
        rec = self._records.get(nm_id)
        if rec is None:
            return 0.0
        remaining = rec.next_spawn_at - now
        return max(0.0, remaining)

    def last_killed_at(self, nm_id: str) -> t.Optional[float]:
        rec = self._records.get(nm_id)
        return rec.last_killed_at if rec is not None else None

    def all_records(self) -> dict[str, RespawnRecord]:
        return dict(self._records)
