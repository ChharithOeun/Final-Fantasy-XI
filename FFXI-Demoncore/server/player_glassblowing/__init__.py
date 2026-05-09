"""Player glassblowing — fragile production with shatter risk.

Glassblowers heat sand to liquid glass, gather a gob, then
work it through shape -> manipulate -> anneal stages. Each
manipulation step risks shattering the piece — heated glass
is unforgiving and the artist's hand has to be steady.
Annealing in the lehr finishes the work.

Lifecycle
    GATHERED      gob collected from the furnace
    SHAPING       being formed
    MANIPULATED   detail work added (handle, lip, etc.)
    ANNEALING     in the lehr cooling oven
    FINISHED      cooled, ready to sell
    SHATTERED     broke during work or annealing

Public surface
--------------
    VesselKind enum
    GlassStage enum
    Vessel dataclass (frozen)
    PlayerGlassblowingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Per stage, base shatter risk pct before skill offset
_STAGE_RISK = {
    "shaping": 20,
    "manipulating": 35,
    "annealing": 15,
}


class VesselKind(str, enum.Enum):
    BOTTLE = "bottle"
    VASE = "vase"
    GOBLET = "goblet"
    BOWL = "bowl"
    CHANDELIER = "chandelier"


class GlassStage(str, enum.Enum):
    GATHERED = "gathered"
    SHAPING = "shaping"
    MANIPULATED = "manipulated"
    ANNEALING = "annealing"
    FINISHED = "finished"
    SHATTERED = "shattered"


@dataclasses.dataclass(frozen=True)
class Vessel:
    vessel_id: str
    artist_id: str
    kind: VesselKind
    artist_skill: int       # 1..100
    stage: GlassStage
    quality_score: int


@dataclasses.dataclass
class PlayerGlassblowingSystem:
    _vessels: dict[str, Vessel] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def gather_gob(
        self, *, artist_id: str, kind: VesselKind,
        artist_skill: int,
    ) -> t.Optional[str]:
        if not artist_id:
            return None
        if not 1 <= artist_skill <= 100:
            return None
        vid = f"vessel_{self._next}"
        self._next += 1
        self._vessels[vid] = Vessel(
            vessel_id=vid, artist_id=artist_id,
            kind=kind, artist_skill=artist_skill,
            stage=GlassStage.GATHERED,
            quality_score=0,
        )
        return vid

    def _maybe_shatter(
        self, *, vessel: Vessel, stage_risk: int,
        seed: int,
    ) -> bool:
        # risk = max(0, base_risk - skill // 5)
        risk = max(0, stage_risk - vessel.artist_skill // 2)
        roll = seed % 100
        return roll < risk

    def shape(
        self, *, vessel_id: str, seed: int,
    ) -> t.Optional[GlassStage]:
        if vessel_id not in self._vessels:
            return None
        v = self._vessels[vessel_id]
        if v.stage != GlassStage.GATHERED:
            return None
        if self._maybe_shatter(
            vessel=v, stage_risk=_STAGE_RISK["shaping"],
            seed=seed,
        ):
            self._vessels[vessel_id] = (
                dataclasses.replace(
                    v, stage=GlassStage.SHATTERED,
                )
            )
            return GlassStage.SHATTERED
        new_quality = v.quality_score + (
            v.artist_skill // 4
        )
        self._vessels[vessel_id] = dataclasses.replace(
            v, stage=GlassStage.SHAPING,
            quality_score=new_quality,
        )
        return GlassStage.SHAPING

    def manipulate(
        self, *, vessel_id: str, seed: int,
    ) -> t.Optional[GlassStage]:
        if vessel_id not in self._vessels:
            return None
        v = self._vessels[vessel_id]
        if v.stage != GlassStage.SHAPING:
            return None
        if self._maybe_shatter(
            vessel=v,
            stage_risk=_STAGE_RISK["manipulating"],
            seed=seed,
        ):
            self._vessels[vessel_id] = (
                dataclasses.replace(
                    v, stage=GlassStage.SHATTERED,
                )
            )
            return GlassStage.SHATTERED
        new_quality = v.quality_score + (
            v.artist_skill // 3
        )
        self._vessels[vessel_id] = dataclasses.replace(
            v, stage=GlassStage.MANIPULATED,
            quality_score=new_quality,
        )
        return GlassStage.MANIPULATED

    def begin_annealing(
        self, *, vessel_id: str,
    ) -> bool:
        if vessel_id not in self._vessels:
            return False
        v = self._vessels[vessel_id]
        if v.stage != GlassStage.MANIPULATED:
            return False
        self._vessels[vessel_id] = dataclasses.replace(
            v, stage=GlassStage.ANNEALING,
        )
        return True

    def remove_from_lehr(
        self, *, vessel_id: str, seed: int,
    ) -> t.Optional[GlassStage]:
        if vessel_id not in self._vessels:
            return None
        v = self._vessels[vessel_id]
        if v.stage != GlassStage.ANNEALING:
            return None
        if self._maybe_shatter(
            vessel=v, stage_risk=_STAGE_RISK["annealing"],
            seed=seed,
        ):
            self._vessels[vessel_id] = (
                dataclasses.replace(
                    v, stage=GlassStage.SHATTERED,
                )
            )
            return GlassStage.SHATTERED
        self._vessels[vessel_id] = dataclasses.replace(
            v, stage=GlassStage.FINISHED,
        )
        return GlassStage.FINISHED

    def vessel(
        self, *, vessel_id: str,
    ) -> t.Optional[Vessel]:
        return self._vessels.get(vessel_id)

    def artist_finished(
        self, *, artist_id: str,
    ) -> list[Vessel]:
        return [
            v for v in self._vessels.values()
            if (v.artist_id == artist_id
                and v.stage == GlassStage.FINISHED)
        ]


__all__ = [
    "VesselKind", "GlassStage", "Vessel",
    "PlayerGlassblowingSystem",
]
