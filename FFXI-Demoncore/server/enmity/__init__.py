"""Enmity — per-mob hate/threat tracker.

Two-tier hate model:
  CUMULATIVE - sticky portion of hate; doesn't decay naturally.
                Increased by big-impact actions (Provoke, slow heals).
  VOLATILE   - transient hate; decays linearly after the action.
                Most damage and heals add here.

When choosing the puller, total_hate = cumulative + current_volatile.
The mob targets the highest total_hate player; ties broken stably
by player_id (and hopefully rng_pool for high-end fight replay).

Public surface
--------------
    EnmityTier enum
    EnmityTable per (mob, all-players)
        .add(player, tier, amount, now_tick)
        .decay(now_tick)              <- caller advances on every tick
        .total(player_id, now_tick)
        .top_threat(now_tick)
        .clear_player(player_id)
    Constants for canonical FFXI actions:
        ENMITY_PROVOKE / ENMITY_FLASH / ENMITY_VOKE
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EnmityTier(str, enum.Enum):
    CUMULATIVE = "cumulative"
    VOLATILE = "volatile"


# Canonical action enmity payloads.
ENMITY_PROVOKE = {EnmityTier.CUMULATIVE: 1800,
                  EnmityTier.VOLATILE: 1800}
ENMITY_FLASH = {EnmityTier.CUMULATIVE: 1, EnmityTier.VOLATILE: 320}
ENMITY_HEAL_BASIC = {EnmityTier.CUMULATIVE: 0,
                     EnmityTier.VOLATILE: 80}
ENMITY_DAMAGE_PER_HIT = {EnmityTier.CUMULATIVE: 1,
                         EnmityTier.VOLATILE: 24}


# Volatile decay rate: 60 points per second. Means a 1800-volatile
# Provoke decays fully in 30 seconds.
VOLATILE_DECAY_PER_SECOND = 60


@dataclasses.dataclass
class _PlayerEnmity:
    cumulative: int = 0
    volatile: int = 0
    last_decay_tick: int = 0

    def total(self) -> int:
        return self.cumulative + max(0, self.volatile)


@dataclasses.dataclass
class EnmityTable:
    mob_id: str
    _entries: dict[str, _PlayerEnmity] = dataclasses.field(
        default_factory=dict, repr=False,
    )

    def add(
        self, *,
        player_id: str,
        amounts: t.Mapping[EnmityTier, int],
        now_tick: int,
    ) -> None:
        e = self._entries.setdefault(player_id, _PlayerEnmity(
            last_decay_tick=now_tick,
        ))
        # Decay catch-up before adding
        self._decay_one(e, now_tick)
        cum = amounts.get(EnmityTier.CUMULATIVE, 0)
        vol = amounts.get(EnmityTier.VOLATILE, 0)
        if cum < 0 or vol < 0:
            raise ValueError("enmity amounts must be >= 0")
        e.cumulative += cum
        e.volatile += vol

    def decay(self, *, now_tick: int) -> None:
        """Advance decay clock for all players. Caller drives this."""
        for e in self._entries.values():
            self._decay_one(e, now_tick)

    def _decay_one(
        self, e: _PlayerEnmity, now_tick: int,
    ) -> None:
        elapsed = now_tick - e.last_decay_tick
        if elapsed <= 0:
            return
        drop = elapsed * VOLATILE_DECAY_PER_SECOND
        e.volatile = max(0, e.volatile - drop)
        e.last_decay_tick = now_tick

    def total(self, *, player_id: str, now_tick: int) -> int:
        e = self._entries.get(player_id)
        if e is None:
            return 0
        # Apply pending decay before reading
        self._decay_one(e, now_tick)
        return e.total()

    def top_threat(
        self, *, now_tick: int,
    ) -> t.Optional[str]:
        """Player with highest current total. None if table empty."""
        if not self._entries:
            return None
        scores = []
        for pid, e in self._entries.items():
            self._decay_one(e, now_tick)
            scores.append((e.total(), pid))
        if not scores:
            return None
        # Highest score; tie-broken by player_id ascending for stability.
        scores.sort(key=lambda x: (-x[0], x[1]))
        if scores[0][0] == 0:
            return None
        return scores[0][1]

    def clear_player(self, player_id: str) -> bool:
        if player_id in self._entries:
            del self._entries[player_id]
            return True
        return False

    def player_count(self) -> int:
        return len(self._entries)


__all__ = [
    "EnmityTier",
    "ENMITY_PROVOKE", "ENMITY_FLASH",
    "ENMITY_HEAL_BASIC", "ENMITY_DAMAGE_PER_HIT",
    "VOLATILE_DECAY_PER_SECOND",
    "EnmityTable",
]
