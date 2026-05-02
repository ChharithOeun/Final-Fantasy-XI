"""Maw portals — Cavernous Maws warping to past WotG zones.

Each modern zone has a Cavernous Maw that, once attuned, lets you
jump back 20 years to its [S] (Wings of the Goddess) version. Maws
require a one-time attunement quest and have a 12-hour personal
cooldown after each use.

Public surface
--------------
    MawPortal catalog (present zone -> past zone)
    PlayerMawState
        .attune(maw_id)
        .use(maw_id, now_tick) -> UseResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAW_COOLDOWN_SECONDS = 12 * 60 * 60   # 12 hours


@dataclasses.dataclass(frozen=True)
class MawPortal:
    maw_id: str
    label: str
    present_zone_id: str
    past_zone_id: str
    attunement_quest_id: str = ""


# Sample maw catalog
MAW_CATALOG: tuple[MawPortal, ...] = (
    MawPortal(
        maw_id="maw_jugner",
        label="Jugner Forest Maw",
        present_zone_id="jugner_forest",
        past_zone_id="jugner_forest_s",
        attunement_quest_id="recollections_of_jugner",
    ),
    MawPortal(
        maw_id="maw_pashhow",
        label="Pashhow Marshlands Maw",
        present_zone_id="pashhow_marshlands",
        past_zone_id="pashhow_marshlands_s",
        attunement_quest_id="recollections_of_pashhow",
    ),
    MawPortal(
        maw_id="maw_east_ronfaure",
        label="East Ronfaure Maw",
        present_zone_id="east_ronfaure",
        past_zone_id="east_ronfaure_s",
        attunement_quest_id="recollections_of_ronfaure",
    ),
    MawPortal(
        maw_id="maw_north_gustaberg",
        label="North Gustaberg Maw",
        present_zone_id="north_gustaberg",
        past_zone_id="north_gustaberg_s",
        attunement_quest_id="recollections_of_gustaberg",
    ),
    MawPortal(
        maw_id="maw_west_sarutabaruta",
        label="West Sarutabaruta Maw",
        present_zone_id="west_sarutabaruta",
        past_zone_id="west_sarutabaruta_s",
        attunement_quest_id="recollections_of_sarutabaruta",
    ),
)

MAW_BY_ID: dict[str, MawPortal] = {m.maw_id: m for m in MAW_CATALOG}


@dataclasses.dataclass(frozen=True)
class UseResult:
    accepted: bool
    maw_id: str
    past_zone_id: t.Optional[str] = None
    next_available_tick: t.Optional[int] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class PlayerMawState:
    player_id: str
    attuned: set[str] = dataclasses.field(default_factory=set)
    last_used: dict[str, int] = dataclasses.field(default_factory=dict)

    def attune(self, *, maw_id: str) -> bool:
        if maw_id not in MAW_BY_ID:
            return False
        if maw_id in self.attuned:
            return False
        self.attuned.add(maw_id)
        return True

    def is_attuned(self, maw_id: str) -> bool:
        return maw_id in self.attuned

    def use(
        self, *, maw_id: str, now_tick: int,
    ) -> UseResult:
        maw = MAW_BY_ID.get(maw_id)
        if maw is None:
            return UseResult(False, maw_id, reason="unknown maw")
        if maw_id not in self.attuned:
            return UseResult(
                False, maw_id, reason="not attuned",
            )
        last = self.last_used.get(maw_id)
        if last is not None:
            next_avail = last + MAW_COOLDOWN_SECONDS
            if now_tick < next_avail:
                return UseResult(
                    False, maw_id,
                    next_available_tick=next_avail,
                    reason="on cooldown",
                )
        self.last_used[maw_id] = now_tick
        return UseResult(
            accepted=True, maw_id=maw_id,
            past_zone_id=maw.past_zone_id,
            next_available_tick=now_tick + MAW_COOLDOWN_SECONDS,
        )


__all__ = [
    "MAW_COOLDOWN_SECONDS",
    "MawPortal", "MAW_CATALOG", "MAW_BY_ID",
    "UseResult", "PlayerMawState",
]
