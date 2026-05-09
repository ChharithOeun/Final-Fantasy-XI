"""Player pottery — wheel-thrown clay through bisque + glaze fires.

Pottery follows a multi-day pipeline: throw on the wheel, dry,
bisque-fire, glaze, then high-fire to finish. Kiln capacity
gates daily output — only N vessels can fire at once. Glaze
choice affects final color and value.

Lifecycle
    WET             clay just thrown, drying
    SHAPED          dried, ready to bisque-fire
    BISQUE_FIRED    first firing done, porous
    GLAZED          glaze applied, ready for kiln
    COMPLETE        final firing done — usable
    CRACKED         failed in the kiln

Public surface
--------------
    PotteryStage enum
    GlazeKind enum
    Vessel dataclass (frozen)
    Kiln dataclass (frozen)
    PlayerPotterySystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_GLAZE_VALUE_BONUS = {
    "celadon": 30,      # green-blue, prized
    "tenmoku": 25,      # iron-black
    "shino": 15,        # white pinholes
    "ash": 5,           # rough natural
    "raku": 40,         # crackle, rare
}


class PotteryStage(str, enum.Enum):
    WET = "wet"
    SHAPED = "shaped"
    BISQUE_FIRED = "bisque_fired"
    GLAZED = "glazed"
    COMPLETE = "complete"
    CRACKED = "cracked"


class GlazeKind(str, enum.Enum):
    CELADON = "celadon"
    TENMOKU = "tenmoku"
    SHINO = "shino"
    ASH = "ash"
    RAKU = "raku"


@dataclasses.dataclass(frozen=True)
class Kiln:
    kiln_id: str
    capacity: int


@dataclasses.dataclass(frozen=True)
class Vessel:
    vessel_id: str
    potter_id: str
    title: str
    potter_skill: int       # 1..100
    stage: PotteryStage
    glaze: t.Optional[GlazeKind]
    quality_score: int


@dataclasses.dataclass
class _KState:
    spec: Kiln
    queued: list[str] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class PlayerPotterySystem:
    _kilns: dict[str, _KState] = dataclasses.field(
        default_factory=dict,
    )
    _vessels: dict[str, Vessel] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def register_kiln(
        self, *, kiln_id: str, capacity: int,
    ) -> bool:
        if not kiln_id or kiln_id in self._kilns:
            return False
        if capacity <= 0 or capacity > 50:
            return False
        self._kilns[kiln_id] = _KState(
            spec=Kiln(
                kiln_id=kiln_id, capacity=capacity,
            ),
        )
        return True

    def throw_vessel(
        self, *, potter_id: str, title: str,
        potter_skill: int,
    ) -> t.Optional[str]:
        if not potter_id or not title:
            return None
        if not 1 <= potter_skill <= 100:
            return None
        vid = f"pot_{self._next}"
        self._next += 1
        # Initial quality from skill alone
        quality = potter_skill // 2
        self._vessels[vid] = Vessel(
            vessel_id=vid, potter_id=potter_id,
            title=title, potter_skill=potter_skill,
            stage=PotteryStage.WET, glaze=None,
            quality_score=quality,
        )
        return vid

    def dry(
        self, *, vessel_id: str,
    ) -> bool:
        if vessel_id not in self._vessels:
            return False
        v = self._vessels[vessel_id]
        if v.stage != PotteryStage.WET:
            return False
        self._vessels[vessel_id] = dataclasses.replace(
            v, stage=PotteryStage.SHAPED,
        )
        return True

    def queue_for_bisque(
        self, *, vessel_id: str, kiln_id: str,
    ) -> bool:
        if vessel_id not in self._vessels:
            return False
        if kiln_id not in self._kilns:
            return False
        v = self._vessels[vessel_id]
        if v.stage != PotteryStage.SHAPED:
            return False
        kiln = self._kilns[kiln_id]
        if len(kiln.queued) >= kiln.spec.capacity:
            return False
        kiln.queued.append(vessel_id)
        return True

    def fire_bisque(
        self, *, kiln_id: str, seed: int,
    ) -> t.Optional[int]:
        """Fire all queued vessels at once. Returns
        count of vessels fired successfully. Each
        vessel has a small crack risk inversely
        proportional to skill."""
        if kiln_id not in self._kilns:
            return None
        kiln = self._kilns[kiln_id]
        if not kiln.queued:
            return None
        succeeded = 0
        for i, vid in enumerate(list(kiln.queued)):
            v = self._vessels[vid]
            risk = max(0, 20 - v.potter_skill // 5)
            roll = (seed + i * 7) % 100
            if roll < risk:
                self._vessels[vid] = (
                    dataclasses.replace(
                        v, stage=PotteryStage.CRACKED,
                    )
                )
            else:
                self._vessels[vid] = (
                    dataclasses.replace(
                        v,
                        stage=PotteryStage.BISQUE_FIRED,
                    )
                )
                succeeded += 1
        kiln.queued.clear()
        return succeeded

    def apply_glaze(
        self, *, vessel_id: str, glaze: GlazeKind,
    ) -> bool:
        if vessel_id not in self._vessels:
            return False
        v = self._vessels[vessel_id]
        if v.stage != PotteryStage.BISQUE_FIRED:
            return False
        bonus = _GLAZE_VALUE_BONUS[glaze.value]
        self._vessels[vessel_id] = dataclasses.replace(
            v, stage=PotteryStage.GLAZED, glaze=glaze,
            quality_score=v.quality_score + bonus,
        )
        return True

    def queue_for_glaze_fire(
        self, *, vessel_id: str, kiln_id: str,
    ) -> bool:
        if vessel_id not in self._vessels:
            return False
        if kiln_id not in self._kilns:
            return False
        v = self._vessels[vessel_id]
        if v.stage != PotteryStage.GLAZED:
            return False
        kiln = self._kilns[kiln_id]
        if len(kiln.queued) >= kiln.spec.capacity:
            return False
        kiln.queued.append(vessel_id)
        return True

    def fire_glaze(
        self, *, kiln_id: str, seed: int,
    ) -> t.Optional[int]:
        if kiln_id not in self._kilns:
            return None
        kiln = self._kilns[kiln_id]
        if not kiln.queued:
            return None
        succeeded = 0
        for i, vid in enumerate(list(kiln.queued)):
            v = self._vessels[vid]
            risk = max(0, 25 - v.potter_skill // 5)
            roll = (seed + i * 11) % 100
            if roll < risk:
                self._vessels[vid] = (
                    dataclasses.replace(
                        v, stage=PotteryStage.CRACKED,
                    )
                )
            else:
                self._vessels[vid] = (
                    dataclasses.replace(
                        v, stage=PotteryStage.COMPLETE,
                    )
                )
                succeeded += 1
        kiln.queued.clear()
        return succeeded

    def vessel(
        self, *, vessel_id: str,
    ) -> t.Optional[Vessel]:
        return self._vessels.get(vessel_id)

    def kiln_queued(
        self, *, kiln_id: str,
    ) -> list[str]:
        if kiln_id not in self._kilns:
            return []
        return list(self._kilns[kiln_id].queued)


__all__ = [
    "PotteryStage", "GlazeKind", "Vessel", "Kiln",
    "PlayerPotterySystem",
]
