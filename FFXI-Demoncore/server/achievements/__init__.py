"""Achievements & milestones tracker.

Demoncore wants permanent bragging rights for the things hardcore
players actually care about: world-firsts, mastery 5 unlocks, Genkai
clears, fomor +5 cap, and so on. This module is the authoritative
record — every event is timestamped and immutable; consumers (UI,
chat, leaderboard) read from here.

Design notes
------------

* Achievements are *world-scoped* by default. A "server-first" can
  only fire once per world.
* Each entry stores who claimed it, what they claimed, and when. The
  fomor evolution module references this to flag mythological-tier
  victims.
* The tracker is a pure container — no IO, no time wall-clock. All
  ``timestamp`` values come from the caller, which keeps it
  deterministic and testable. (In production the caller is the
  game-tick clock.)

Public surface
--------------
    AchievementType           enum of milestone categories
    Achievement               immutable entry: type, key, player,
                                  timestamp, metadata
    AchievementBoard          per-world record + claim helpers
        .claim(...)           record a milestone (idempotent for
                                  unique types)
        .has(...)             quick membership check
        .holders(type)        every claimant of a type
        .first_holder(type, key)   the world-first holder
        .achievements_of(player)   what one player has earned
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AchievementType(str, enum.Enum):
    """Milestone categories.

    UNIQUE-by-(type, key) means only the first claimant counts.
    REPEATABLE means any player can earn the same key.
    """

    # World-first kill on a named NM/HNM/boss.
    SERVER_FIRST_KILL = "server_first_kill"

    # First clear of a Genkai mission (limit-break) on the server.
    SERVER_FIRST_GENKAI = "server_first_genkai"

    # Mastery V (5) unlocked on a job — repeatable per (player, job).
    JOB_MASTERY_5 = "job_mastery_5"

    # Reached the +5 evolution cap on a fomor — repeatable.
    FOMOR_PLUS_FIVE = "fomor_plus_five"

    # Personal Genkai clear — repeatable per (player, genkai_key).
    PERSONAL_GENKAI = "personal_genkai"

    # Killed a Mythological-tier fomor — repeatable.
    MYTHOLOGICAL_TROPHY = "mythological_trophy"


# Types where only the FIRST claim per key matters server-wide.
_UNIQUE_TYPES: frozenset[AchievementType] = frozenset({
    AchievementType.SERVER_FIRST_KILL,
    AchievementType.SERVER_FIRST_GENKAI,
})


@dataclasses.dataclass(frozen=True)
class Achievement:
    """One milestone record."""
    type: AchievementType
    key: str                          # what was achieved (e.g. "fafnir")
    player_id: str                    # who claimed it
    timestamp: int                    # caller-supplied epoch seconds
    metadata: t.Mapping[str, t.Any] = dataclasses.field(
        default_factory=dict
    )


@dataclasses.dataclass
class ClaimResult:
    """Outcome of a claim() attempt."""
    accepted: bool
    achievement: t.Optional[Achievement]
    reason: t.Optional[str] = None    # human-readable reject reason


@dataclasses.dataclass
class AchievementBoard:
    """World-scoped achievement record."""

    world_id: str
    _entries: list[Achievement] = dataclasses.field(
        default_factory=list, repr=False
    )
    # (type, key) -> first Achievement for that pair, set only for
    # UNIQUE types. Lookup helper, NOT canonical storage.
    _unique_holder: dict[tuple[AchievementType, str], Achievement] = (
        dataclasses.field(default_factory=dict, repr=False)
    )

    def claim(
        self,
        *,
        type: AchievementType,
        key: str,
        player_id: str,
        timestamp: int,
        metadata: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> ClaimResult:
        """Try to record a milestone.

        For UNIQUE types, only the first claimant for a given key
        succeeds; later attempts return accepted=False with a reason.
        """
        if not key:
            return ClaimResult(False, None, "empty key")
        if not player_id:
            return ClaimResult(False, None, "empty player_id")

        ach = Achievement(
            type=type,
            key=key,
            player_id=player_id,
            timestamp=timestamp,
            metadata=dict(metadata or {}),
        )

        if type in _UNIQUE_TYPES:
            existing = self._unique_holder.get((type, key))
            if existing is not None:
                return ClaimResult(
                    False, None,
                    f"already held by {existing.player_id} at "
                    f"{existing.timestamp}",
                )
            self._unique_holder[(type, key)] = ach

        self._entries.append(ach)
        return ClaimResult(True, ach, None)

    # -- read helpers ------------------------------------------------

    def has(
        self,
        *,
        type: AchievementType,
        key: str,
        player_id: t.Optional[str] = None,
    ) -> bool:
        """True iff a matching achievement exists.

        If player_id is None, checks whether *any* claimant holds it.
        """
        for e in self._entries:
            if e.type != type or e.key != key:
                continue
            if player_id is None or e.player_id == player_id:
                return True
        return False

    def holders(self, type: AchievementType) -> tuple[str, ...]:
        """All distinct player_ids that have claimed this type
        (across any key). Order: first-claim order."""
        out: list[str] = []
        seen: set[str] = set()
        for e in self._entries:
            if e.type == type and e.player_id not in seen:
                out.append(e.player_id)
                seen.add(e.player_id)
        return tuple(out)

    def first_holder(
        self,
        *,
        type: AchievementType,
        key: str,
    ) -> t.Optional[Achievement]:
        """Earliest achievement of (type, key), or None.

        For UNIQUE types this is identical to the only entry. For
        repeatable types it's the chronologically first claimant."""
        if type in _UNIQUE_TYPES:
            return self._unique_holder.get((type, key))

        candidates = [
            e for e in self._entries
            if e.type == type and e.key == key
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda e: e.timestamp)

    def achievements_of(self, player_id: str) -> tuple[Achievement, ...]:
        """All achievements held by one player, in claim order."""
        return tuple(e for e in self._entries
                     if e.player_id == player_id)

    def all_entries(self) -> tuple[Achievement, ...]:
        """Chronological dump of every claim."""
        return tuple(self._entries)

    def count(self) -> int:
        return len(self._entries)


__all__ = [
    "AchievementType",
    "Achievement",
    "ClaimResult",
    "AchievementBoard",
]
