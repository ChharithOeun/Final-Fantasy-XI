"""Tannery rack — turn raw hide into usable leather.

A raw hide rotting in your pack is worse than worthless;
a properly tanned hide is the input for half the
crafting tree (insulation_clothing's leather slots,
water_skin tiers, bedroll covers, hunting_bow grips).

Tanning is a 3-stage process spread across days:
    SOAKING    submerged in tanning solution
    SCRAPING   flesh removed, salt applied
    DRYING     stretched on rack until cured

Each stage takes time. You can't fast-forward — interrupt
the rack with bad weather (rain) and the SOAKING/DRYING
stages stall (and may regress, like jerky_drying).
SCRAPING is a manual operator action — you click "scrape"
yourself once SOAKING is complete.

A finished hide produces "leather_<quarry>" suitable for
crafting. A ruined hide (from butcher_yield.hide_ruined)
can't be loaded — the engine refuses, telling the player
to use a less-destructive arrowhead next time.

Public surface
--------------
    TanStage enum
    HideOnRack dataclass (mutable)
    TanneryRack
        .load(hide_id, owner_id, quarry_id, hide_ruined,
              loaded_at) -> bool
        .tick(dt_seconds, weather_rain) -> int
            (returns count of completed hides)
        .scrape(hide_id) -> bool
            (manual step from SOAKING -> DRYING)
        .pull(hide_id) -> Optional[str]   ("leather_<quarry>")
        .stage_of(hide_id) -> Optional[TanStage]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TanStage(str, enum.Enum):
    SOAKING = "soaking"
    SCRAPING = "scraping"   # waiting for player to scrape
    DRYING = "drying"
    READY = "ready"


# stage durations in seconds — each stage is "real time"
# (game-tempo, so plenty short for testing).
_SOAK_SECONDS = 1800   # 30 min real
_DRY_SECONDS = 3600    # 60 min real


@dataclasses.dataclass
class HideOnRack:
    hide_id: str
    owner_id: str
    quarry_id: str
    stage: TanStage
    seconds_in_stage: int
    loaded_at: int


@dataclasses.dataclass
class TanneryRack:
    _hides: dict[str, HideOnRack] = dataclasses.field(
        default_factory=dict,
    )

    def load(
        self, *, hide_id: str, owner_id: str,
        quarry_id: str, hide_ruined: bool,
        loaded_at: int,
    ) -> bool:
        if not hide_id or not owner_id or not quarry_id:
            return False
        if hide_id in self._hides:
            return False
        if hide_ruined:
            # tannery refuses ruined hides — they're scrap
            return False
        self._hides[hide_id] = HideOnRack(
            hide_id=hide_id, owner_id=owner_id,
            quarry_id=quarry_id, stage=TanStage.SOAKING,
            seconds_in_stage=0, loaded_at=loaded_at,
        )
        return True

    def tick(
        self, *, dt_seconds: int,
        weather_rain: bool = False,
    ) -> int:
        if dt_seconds <= 0:
            return self._count_ready()
        completed_this_tick: list[str] = []
        for hide in self._hides.values():
            if hide.stage == TanStage.SOAKING:
                if weather_rain:
                    # rain dilutes the tanning solution — stalls
                    continue
                hide.seconds_in_stage += dt_seconds
                if hide.seconds_in_stage >= _SOAK_SECONDS:
                    hide.stage = TanStage.SCRAPING
                    hide.seconds_in_stage = 0
            elif hide.stage == TanStage.SCRAPING:
                # SCRAPING is operator-driven; tick can't move it.
                continue
            elif hide.stage == TanStage.DRYING:
                if weather_rain:
                    # rain on a drying hide regresses it
                    hide.seconds_in_stage = max(
                        0, hide.seconds_in_stage - dt_seconds,
                    )
                    continue
                hide.seconds_in_stage += dt_seconds
                if hide.seconds_in_stage >= _DRY_SECONDS:
                    hide.stage = TanStage.READY
                    hide.seconds_in_stage = 0
                    completed_this_tick.append(hide.hide_id)
        return self._count_ready()

    def _count_ready(self) -> int:
        return sum(
            1 for h in self._hides.values()
            if h.stage == TanStage.READY
        )

    def scrape(self, *, hide_id: str) -> bool:
        h = self._hides.get(hide_id)
        if h is None:
            return False
        if h.stage != TanStage.SCRAPING:
            return False
        h.stage = TanStage.DRYING
        h.seconds_in_stage = 0
        return True

    def pull(self, *, hide_id: str) -> t.Optional[str]:
        h = self._hides.get(hide_id)
        if h is None:
            return None
        if h.stage != TanStage.READY:
            return None
        out = "leather_" + h.quarry_id
        del self._hides[hide_id]
        return out

    def stage_of(
        self, *, hide_id: str,
    ) -> t.Optional[TanStage]:
        h = self._hides.get(hide_id)
        if h is None:
            return None
        return h.stage

    def total_hides(self) -> int:
        return len(self._hides)


__all__ = [
    "TanStage", "HideOnRack", "TanneryRack",
]
