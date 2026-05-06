"""Sleep dream — bed-rest produces dream sequences with rewards.

Sleeping in a real bed (Mog House, inn, etc.) for at
least N seconds triggers a dream. Most dreams are flavor —
the player's character has visions tied to recent
events. A small fraction yield a meaningful drop:

    - lore_fragment_id (page from a hidden book)
    - blue_magic_set_point (BLU spell hint)
    - random_seal (AF gear seal)
    - skill_unlock (rare-and-precious key item)

Dreams are seeded by the player's recent activity in the
exploration journal — players who've been doing legendary
deeds get richer dreams.

Public surface
--------------
    DreamKind enum
    DreamReward dataclass (frozen)
    SleepSession dataclass (mutable)
    SleepDreamEngine
        .begin_sleep(player_id, location_kind, started_at)
            -> bool
        .end_sleep(player_id, ended_at) -> Optional[DreamReward]
        .min_sleep_for_dream() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DreamKind(str, enum.Enum):
    EMPTY = "empty"               # no reward
    LORE_FRAGMENT = "lore_fragment"
    BLUE_MAGIC_HINT = "blue_magic_hint"
    AF_SEAL = "af_seal"
    SKILL_UNLOCK = "skill_unlock"


class LocationKind(str, enum.Enum):
    MOG_HOUSE = "mog_house"
    INN = "inn"
    BEDROLL = "bedroll"        # outdoor / temporary
    OUTLAW_HIDEOUT = "outlaw_hideout"


_MIN_SLEEP = 60   # seconds — minimum for any dream
_RICH_THRESHOLD_SECONDS = 480
# location-kind base reward chance (out of 100)
_LOC_QUALITY = {
    LocationKind.MOG_HOUSE: 100,
    LocationKind.INN: 80,
    LocationKind.BEDROLL: 30,
    LocationKind.OUTLAW_HIDEOUT: 50,
}


@dataclasses.dataclass(frozen=True)
class DreamReward:
    kind: DreamKind
    payload: str        # opaque ref to a lore_id / spell / etc.
    summary: str


@dataclasses.dataclass
class SleepSession:
    player_id: str
    location_kind: LocationKind
    started_at: int


@dataclasses.dataclass
class SleepDreamEngine:
    _sessions: dict[str, SleepSession] = dataclasses.field(
        default_factory=dict,
    )
    # Optional injectable dream-roller: takes (slept_seconds,
    # location_quality_pct) -> Optional[DreamReward]
    _roller: t.Optional[t.Callable[
        [int, int], t.Optional[DreamReward],
    ]] = None

    def set_roller(
        self, *, roller: t.Callable[
            [int, int], t.Optional[DreamReward],
        ],
    ) -> None:
        self._roller = roller

    def begin_sleep(
        self, *, player_id: str,
        location_kind: LocationKind,
        started_at: int,
    ) -> bool:
        if not player_id:
            return False
        if player_id in self._sessions:
            return False
        self._sessions[player_id] = SleepSession(
            player_id=player_id,
            location_kind=location_kind,
            started_at=started_at,
        )
        return True

    def end_sleep(
        self, *, player_id: str, ended_at: int,
    ) -> t.Optional[DreamReward]:
        s = self._sessions.pop(player_id, None)
        if s is None:
            return None
        slept = ended_at - s.started_at
        if slept < _MIN_SLEEP:
            return DreamReward(
                kind=DreamKind.EMPTY,
                payload="",
                summary="A dreamless rest.",
            )
        loc_quality = _LOC_QUALITY[s.location_kind]
        if self._roller is not None:
            return self._roller(slept, loc_quality)
        return self._default_roll(
            slept_seconds=slept, location_quality_pct=loc_quality,
        )

    def _default_roll(
        self, *, slept_seconds: int,
        location_quality_pct: int,
    ) -> DreamReward:
        # without an injected roller, prefer to be generous
        # at high location quality + long sleeps
        if (slept_seconds >= _RICH_THRESHOLD_SECONDS
                and location_quality_pct >= 80):
            return DreamReward(
                kind=DreamKind.LORE_FRAGMENT,
                payload="lore_fragment_default",
                summary="A clear vision of an ancient page.",
            )
        if slept_seconds >= _RICH_THRESHOLD_SECONDS:
            return DreamReward(
                kind=DreamKind.AF_SEAL,
                payload="seal_random",
                summary="A glimmering seal in your dream.",
            )
        return DreamReward(
            kind=DreamKind.EMPTY, payload="",
            summary="Light rest, no visions.",
        )

    def is_sleeping(self, *, player_id: str) -> bool:
        return player_id in self._sessions

    def min_sleep_for_dream(self) -> int:
        return _MIN_SLEEP


__all__ = [
    "DreamKind", "LocationKind", "DreamReward",
    "SleepSession", "SleepDreamEngine",
]
