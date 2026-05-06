"""Secret passage — hidden zone-to-zone routes.

The world has obvious paths and the rest. Secret passages
are the rest: a crack in the canyon wall that only opens
during a thunderstorm, a tile in the cathedral that turns
when a specific rune is held, a path through the swamp
visible only at night.

Every passage has:
    - source_zone, target_zone
    - one or more UnlockConditions (ALL must be true)
    - per-player discovered flag (one player discovers
      it; the world remembers, but the *path* is open
      to everyone going forward)

UnlockCondition kinds:
    WEATHER     specific weather is active
    TIME_OF_DAY one of (NIGHT, DAY, DUSK, DAWN)
    KEY_ITEM    player holds a specific key item
    SEASON      a particular game-season tag
    NPC_PROXIMITY a specific NPC must be alive nearby

Public surface
--------------
    UnlockCondition dataclass (frozen, with `kind` and
        per-kind `data` payload)
    SecretPassage dataclass (mutable; tracks first_discoverer)
    PassageOutcome enum
    SecretPassageRegistry
        .define_passage(...) -> bool
        .attempt_passage(passage_id, player_id,
                         active_weather, time_of_day,
                         key_items, season, nearby_npcs,
                         attempted_at) -> PassageOutcome
        .first_discoverer(passage_id) -> Optional[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ConditionKind(str, enum.Enum):
    WEATHER = "weather"
    TIME_OF_DAY = "time_of_day"
    KEY_ITEM = "key_item"
    SEASON = "season"
    NPC_PROXIMITY = "npc_proximity"


class PassageOutcome(str, enum.Enum):
    OPEN = "open"
    BLOCKED = "blocked"
    UNKNOWN_PASSAGE = "unknown_passage"
    INVALID_PLAYER = "invalid_player"


@dataclasses.dataclass(frozen=True)
class UnlockCondition:
    kind: ConditionKind
    expected: str    # weather id, time-of-day, ki id, season, npc id


@dataclasses.dataclass
class SecretPassage:
    passage_id: str
    source_zone_id: str
    target_zone_id: str
    conditions: tuple[UnlockCondition, ...]
    first_discoverer: t.Optional[str] = None
    discovered_at: t.Optional[int] = None
    use_count: int = 0


@dataclasses.dataclass
class SecretPassageRegistry:
    _passages: dict[str, SecretPassage] = dataclasses.field(
        default_factory=dict,
    )

    def define_passage(
        self, *, passage_id: str,
        source_zone_id: str, target_zone_id: str,
        conditions: t.Iterable[UnlockCondition],
    ) -> bool:
        if not passage_id:
            return False
        if not source_zone_id or not target_zone_id:
            return False
        if source_zone_id == target_zone_id:
            return False
        cs = tuple(conditions)
        if not cs:
            return False
        if passage_id in self._passages:
            return False
        self._passages[passage_id] = SecretPassage(
            passage_id=passage_id,
            source_zone_id=source_zone_id,
            target_zone_id=target_zone_id,
            conditions=cs,
        )
        return True

    def get(
        self, *, passage_id: str,
    ) -> t.Optional[SecretPassage]:
        return self._passages.get(passage_id)

    def attempt_passage(
        self, *, passage_id: str, player_id: str,
        active_weather: str = "",
        time_of_day: str = "",
        key_items: t.Iterable[str] = (),
        season: str = "",
        nearby_npcs: t.Iterable[str] = (),
        attempted_at: int = 0,
    ) -> PassageOutcome:
        p = self._passages.get(passage_id)
        if p is None:
            return PassageOutcome.UNKNOWN_PASSAGE
        if not player_id:
            return PassageOutcome.INVALID_PLAYER
        kis = set(key_items)
        npcs = set(nearby_npcs)
        for c in p.conditions:
            if c.kind == ConditionKind.WEATHER:
                if c.expected != active_weather:
                    return PassageOutcome.BLOCKED
            elif c.kind == ConditionKind.TIME_OF_DAY:
                if c.expected != time_of_day:
                    return PassageOutcome.BLOCKED
            elif c.kind == ConditionKind.KEY_ITEM:
                if c.expected not in kis:
                    return PassageOutcome.BLOCKED
            elif c.kind == ConditionKind.SEASON:
                if c.expected != season:
                    return PassageOutcome.BLOCKED
            elif c.kind == ConditionKind.NPC_PROXIMITY:
                if c.expected not in npcs:
                    return PassageOutcome.BLOCKED
        # all conditions met
        if p.first_discoverer is None:
            p.first_discoverer = player_id
            p.discovered_at = attempted_at
        p.use_count += 1
        return PassageOutcome.OPEN

    def first_discoverer(
        self, *, passage_id: str,
    ) -> t.Optional[str]:
        p = self._passages.get(passage_id)
        return p.first_discoverer if p else None

    def total_passages(self) -> int:
        return len(self._passages)


__all__ = [
    "ConditionKind", "UnlockCondition", "PassageOutcome",
    "SecretPassage", "SecretPassageRegistry",
]
