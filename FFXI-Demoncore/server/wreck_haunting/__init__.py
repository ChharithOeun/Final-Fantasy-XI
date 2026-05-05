"""Wreck haunting — abandoned wrecks attract drowned-fomor mobs.

Once a wreck is filed in missing_ship_registry, drowned crew
that became fomor variants linger near the hull. The longer
the wreck sits unsalvaged, the denser the haunt. Salvaging
disturbs the haunt and SCATTERS the mobs (they aggro the
diver instead of guarding the wreck).

Haunt levels (escalate over time):
  QUIET    -    < 1h since wreck filed
  STIRRING -  1h ..  6h
  RESTLESS -  6h .. 24h
  RAVENOUS - 24h+

Each level has a population coefficient used by callers to
decide how many fomor mobs spawn around the wreck. We don't
spawn the mobs ourselves — we just publish the haunt level
and an aggro multiplier that callers can apply to encounter
density tables.

Salvage events SHATTER the haunt for a cooldown window
(default 30 minutes), during which the haunt level resets to
QUIET — the disturbed fomor have engaged the diver instead.

Public surface
--------------
    HauntLevel enum   QUIET / STIRRING / RESTLESS / RAVENOUS
    HauntStatus dataclass
    WreckHaunting
        .observe(ship_id, filed_at, last_salvaged_at, now_seconds)
        .aggro_multiplier_for(ship_id, ...)
        .disturb(ship_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class HauntLevel(str, enum.Enum):
    QUIET = "quiet"
    STIRRING = "stirring"
    RESTLESS = "restless"
    RAVENOUS = "ravenous"


_LEVEL_BANDS_SECONDS: tuple[tuple[int, HauntLevel], ...] = (
    (3_600,         HauntLevel.QUIET),
    (6 * 3_600,     HauntLevel.STIRRING),
    (24 * 3_600,    HauntLevel.RESTLESS),
    # past 24h => RAVENOUS
)

_AGGRO_MULT: dict[HauntLevel, float] = {
    HauntLevel.QUIET:    0.5,
    HauntLevel.STIRRING: 1.0,
    HauntLevel.RESTLESS: 1.5,
    HauntLevel.RAVENOUS: 2.5,
}

_DISTURB_COOLDOWN_SECONDS = 30 * 60


@dataclasses.dataclass(frozen=True)
class HauntStatus:
    ship_id: str
    level: HauntLevel
    age_seconds: int
    aggro_multiplier: float


@dataclasses.dataclass
class WreckHaunting:
    _disturbed_until: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    @staticmethod
    def _level_for_age(age: int) -> HauntLevel:
        if age < 0:
            return HauntLevel.QUIET
        for ceiling, level in _LEVEL_BANDS_SECONDS:
            if age < ceiling:
                return level
        return HauntLevel.RAVENOUS

    def observe(
        self, *, ship_id: str,
        filed_at: int,
        now_seconds: int,
    ) -> HauntStatus:
        age = max(0, now_seconds - filed_at)
        # disturbed window keeps haunt at QUIET
        end = self._disturbed_until.get(ship_id, 0)
        if now_seconds < end:
            level = HauntLevel.QUIET
        else:
            level = self._level_for_age(age)
        return HauntStatus(
            ship_id=ship_id,
            level=level,
            age_seconds=age,
            aggro_multiplier=_AGGRO_MULT[level],
        )

    def disturb(
        self, *, ship_id: str, now_seconds: int,
    ) -> bool:
        if not ship_id:
            return False
        self._disturbed_until[ship_id] = (
            now_seconds + _DISTURB_COOLDOWN_SECONDS
        )
        return True

    def disturbed_until(
        self, *, ship_id: str,
    ) -> t.Optional[int]:
        return self._disturbed_until.get(ship_id)

    @staticmethod
    def aggro_multiplier_for(*, level: HauntLevel) -> float:
        return _AGGRO_MULT[level]


__all__ = [
    "HauntLevel", "HauntStatus", "WreckHaunting",
]
