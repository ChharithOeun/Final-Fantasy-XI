"""Memorial registry — permadeath player wall.

Players who hit permadeath get listed on a memorial wall in
their home nation. The memorial:

* Lists name, level at death, job, age (game-time), cause of
  death, recorded epitaph
* Persists FOREVER — no purge, no overwrite
* Visiting (paying respects) grants the visitor a small honor
  reward, ONE-TIME per visitor
* The slain player's NAME is locked: a new character cannot be
  re-rolled with that name on the same server

Public surface
--------------
    DeathCause enum
    MemorialEntry dataclass
    PayRespectsResult dataclass
    MemorialRegistry
        .inscribe(name, level, job, cause, epitaph, ...)
        .lookup(name) / .for_nation(nation)
        .pay_respects(visitor_id, name)
        .name_taken(name) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default honor granted to a respect-payer (one-time per pair).
RESPECT_HONOR_REWARD = 5


class DeathCause(str, enum.Enum):
    KO_TIMEOUT = "ko_timeout"
    OUTLAW_HUNT = "outlaw_hunt"
    NM_ENCOUNTER = "nm_encounter"
    BOSS_RAID = "boss_raid"
    PVP_DUEL = "pvp_duel"
    BEASTMEN_RAID = "beastmen_raid"
    HARDCORE_FALL = "hardcore_fall"
    UNKNOWN = "unknown"


@dataclasses.dataclass(frozen=True)
class MemorialEntry:
    name: str
    nation: str
    level_at_death: int
    main_job_id: str
    cause: DeathCause
    age_in_game_days: int
    epitaph: str = ""
    inscribed_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class InscribeResult:
    accepted: bool
    entry: t.Optional[MemorialEntry] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class PayRespectsResult:
    accepted: bool
    name: str
    honor_gained: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MemorialRegistry:
    respect_reward: int = RESPECT_HONOR_REWARD
    _entries: dict[str, MemorialEntry] = dataclasses.field(
        default_factory=dict,
    )
    # (visitor_id, name) -> already paid respects
    _paid_respects: set[
        tuple[str, str],
    ] = dataclasses.field(default_factory=set)

    def inscribe(
        self, *, name: str, nation: str,
        level_at_death: int, main_job_id: str,
        cause: DeathCause = DeathCause.UNKNOWN,
        age_in_game_days: int = 0,
        epitaph: str = "",
        inscribed_at_seconds: float = 0.0,
    ) -> InscribeResult:
        if not name.strip():
            return InscribeResult(
                accepted=False, reason="name required",
            )
        if name in self._entries:
            return InscribeResult(
                accepted=False,
                reason="name already inscribed",
            )
        if level_at_death < 1:
            return InscribeResult(
                accepted=False, reason="invalid level",
            )
        entry = MemorialEntry(
            name=name, nation=nation,
            level_at_death=level_at_death,
            main_job_id=main_job_id,
            cause=cause,
            age_in_game_days=age_in_game_days,
            epitaph=epitaph,
            inscribed_at_seconds=inscribed_at_seconds,
        )
        self._entries[name] = entry
        return InscribeResult(accepted=True, entry=entry)

    def lookup(self, name: str) -> t.Optional[MemorialEntry]:
        return self._entries.get(name)

    def for_nation(
        self, nation: str,
    ) -> tuple[MemorialEntry, ...]:
        return tuple(
            e for e in self._entries.values()
            if e.nation == nation
        )

    def pay_respects(
        self, *, visitor_id: str, name: str,
    ) -> PayRespectsResult:
        entry = self._entries.get(name)
        if entry is None:
            return PayRespectsResult(
                accepted=False, name=name,
                reason="no such memorial",
            )
        key = (visitor_id, name)
        if key in self._paid_respects:
            return PayRespectsResult(
                accepted=False, name=name,
                reason="already paid respects",
            )
        self._paid_respects.add(key)
        return PayRespectsResult(
            accepted=True, name=name,
            honor_gained=self.respect_reward,
        )

    def respects_count_for(self, name: str) -> int:
        return sum(
            1 for (_v, n) in self._paid_respects
            if n == name
        )

    def name_taken(self, name: str) -> bool:
        return name in self._entries

    def total_inscribed(self) -> int:
        return len(self._entries)


__all__ = [
    "RESPECT_HONOR_REWARD",
    "DeathCause",
    "MemorialEntry",
    "InscribeResult", "PayRespectsResult",
    "MemorialRegistry",
]
