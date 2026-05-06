"""Endgame solution journal — final per-player strategy unlocks.

This is the destination of the hint web. When a player
has assembled enough hints to confirm enough puzzle
pieces to unlock a `Solution` (per puzzle_assembly_journal),
that solution is published into THIS journal as a
`StrategyEntry` — a structured strategy nugget the
player can read in their endgame guide.

The Sahagin Royal Conquest has these strategy nuggets,
each gated by a different puzzle solution:

    KILL_ORDER_ALPHA  - Alpha alliance NM kill sequence
                        (kelp tunnels)
    KILL_ORDER_BRAVO  - Bravo alliance NM kill sequence
                        (sahagin docks)
    KILL_ORDER_CHARLIE- Charlie alliance NM kill sequence
                        (trench bone yards)
    QUEEN_DOUBLE_MB   - Double magic burst is required
                        for oxygen drops
    KING_PET_PRIORITY - Kill both wyrm pets fast or one
                        rages
    OXYGEN_ROTATION   - How to rotate guard kills to
                        keep the raid breathing
    SPIRIT_SURGE      - Interrupt the king's 30s SP cast
                        at 10% HP
    AVATAR_LIMIT      - Queen has 3 avatars — focus the
                        third dispel

A player may unlock SOME but not ALL strategy entries.
That's the point — they can attempt the raid with
partial information, but the more complete their
journal, the better their odds. A player at full
ENLIGHTENED with every MSQ done WILL have the full
strategy and is more likely to win the raid first try.

Public surface
--------------
    StrategyKey enum
    StrategyEntry dataclass (frozen)
    EndgameSolutionJournal
        .define_entry(strategy_key, solution_id, body)
        .sync_from(player_id, journal) -> tuple[StrategyEntry, ...]
        .entries_for(player_id) -> tuple[StrategyEntry, ...]
        .completion_pct(player_id) -> float
        .has_full_strategy(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.puzzle_assembly_journal import PuzzleAssemblyJournal


class StrategyKey(str, enum.Enum):
    KILL_ORDER_ALPHA = "kill_order_alpha"
    KILL_ORDER_BRAVO = "kill_order_bravo"
    KILL_ORDER_CHARLIE = "kill_order_charlie"
    QUEEN_DOUBLE_MB = "queen_double_mb"
    KING_PET_PRIORITY = "king_pet_priority"
    OXYGEN_ROTATION = "oxygen_rotation"
    SPIRIT_SURGE = "spirit_surge"
    AVATAR_LIMIT = "avatar_limit"


@dataclasses.dataclass(frozen=True)
class StrategyEntry:
    strategy_key: StrategyKey
    solution_id: str
    body: str


@dataclasses.dataclass
class EndgameSolutionJournal:
    # solution_id -> StrategyEntry definition
    _entries: dict[str, StrategyEntry] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> set[strategy_key]
    _unlocked: dict[str, set[StrategyKey]] = dataclasses.field(
        default_factory=dict,
    )

    def define_entry(
        self, *, strategy_key: StrategyKey,
        solution_id: str, body: str,
    ) -> bool:
        if not solution_id or not body:
            return False
        if solution_id in self._entries:
            return False
        # also reject if strategy_key already mapped to another solution
        for e in self._entries.values():
            if e.strategy_key == strategy_key:
                return False
        self._entries[solution_id] = StrategyEntry(
            strategy_key=strategy_key,
            solution_id=solution_id,
            body=body,
        )
        return True

    def sync_from(
        self, *, player_id: str,
        journal: PuzzleAssemblyJournal,
    ) -> tuple[StrategyEntry, ...]:
        """Read solutions from puzzle journal, unlock matching
        strategy entries. Returns the entries newly unlocked
        on THIS call (idempotent — already-unlocked entries
        are not returned again)."""
        if not player_id:
            return ()
        unlocked = self._unlocked.setdefault(player_id, set())
        newly: list[StrategyEntry] = []
        for sol in journal.solutions_unlocked(player_id=player_id):
            entry = self._entries.get(sol.solution_id)
            if entry is None:
                continue
            if entry.strategy_key in unlocked:
                continue
            unlocked.add(entry.strategy_key)
            newly.append(entry)
        return tuple(newly)

    def entries_for(
        self, *, player_id: str,
    ) -> tuple[StrategyEntry, ...]:
        unlocked = self._unlocked.get(player_id, set())
        out = [
            e for e in self._entries.values()
            if e.strategy_key in unlocked
        ]
        return tuple(sorted(out, key=lambda e: e.strategy_key.value))

    def completion_pct(self, *, player_id: str) -> float:
        if not self._entries:
            return 0.0
        unlocked = self._unlocked.get(player_id, set())
        return len(unlocked) / len(self._entries)

    def has_full_strategy(self, *, player_id: str) -> bool:
        if not self._entries:
            return False
        return self.completion_pct(player_id=player_id) >= 1.0

    def total_entries(self) -> int:
        return len(self._entries)


__all__ = [
    "StrategyKey", "StrategyEntry", "EndgameSolutionJournal",
]
