"""Player sculpture — multi-day stone work that risks cracking.

Sculptors start with a stone block and chisel through stages,
each stage advancing the work but carrying a small crack risk
based on stage difficulty vs sculptor skill. Once polished,
the work can be installed at a public location as a permanent
monument or sold to a private collector.

Lifecycle
    BLOCK         raw stone, untouched
    ROUGH_CUT     gross shape established
    REFINED       details emerging
    POLISHED      finished surface
    INSTALLED     placed at a public location
    CRACKED       structural failure during work — ruined

Public surface
--------------
    SculptureStage enum
    StoneKind enum
    Sculpture dataclass (frozen)
    PlayerSculptureSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_STAGE_DIFFICULTY = {
    "block": 0,           # only used as starting state
    "rough_cut": 30,
    "refined": 50,
    "polished": 70,
}


class StoneKind(str, enum.Enum):
    LIMESTONE = "limestone"
    MARBLE = "marble"
    GRANITE = "granite"
    OBSIDIAN = "obsidian"


class SculptureStage(str, enum.Enum):
    BLOCK = "block"
    ROUGH_CUT = "rough_cut"
    REFINED = "refined"
    POLISHED = "polished"
    INSTALLED = "installed"
    CRACKED = "cracked"


_STONE_BASE_QUALITY = {
    "limestone": 30,
    "marble": 60,
    "granite": 50,
    "obsidian": 80,
}


@dataclasses.dataclass(frozen=True)
class Sculpture:
    sculpture_id: str
    sculptor_id: str
    title: str
    stone: StoneKind
    sculptor_skill: int          # 1..100
    stage: SculptureStage
    quality_score: int
    install_location: str
    days_worked: int


@dataclasses.dataclass
class PlayerSculptureSystem:
    _sculptures: dict[str, Sculpture] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def begin_sculpture(
        self, *, sculptor_id: str, title: str,
        stone: StoneKind, sculptor_skill: int,
    ) -> t.Optional[str]:
        if not sculptor_id or not title:
            return None
        if not 1 <= sculptor_skill <= 100:
            return None
        sid = f"sculpture_{self._next}"
        self._next += 1
        self._sculptures[sid] = Sculpture(
            sculpture_id=sid, sculptor_id=sculptor_id,
            title=title, stone=stone,
            sculptor_skill=sculptor_skill,
            stage=SculptureStage.BLOCK,
            quality_score=_STONE_BASE_QUALITY[
                stone.value
            ],
            install_location="", days_worked=0,
        )
        return sid

    def advance_stage(
        self, *, sculpture_id: str, seed: int,
    ) -> t.Optional[SculptureStage]:
        """Advance one stage. Crack risk = max(0,
        difficulty - skill) — higher difficulty for
        the next stage above your skill level means
        catastrophic failure chance.
        """
        if sculpture_id not in self._sculptures:
            return None
        s = self._sculptures[sculpture_id]
        next_stage_map = {
            SculptureStage.BLOCK:
                SculptureStage.ROUGH_CUT,
            SculptureStage.ROUGH_CUT:
                SculptureStage.REFINED,
            SculptureStage.REFINED:
                SculptureStage.POLISHED,
        }
        if s.stage not in next_stage_map:
            return None
        nxt = next_stage_map[s.stage]
        difficulty = _STAGE_DIFFICULTY[nxt.value]
        # Deterministic crack check
        crack_pressure = max(0, difficulty - s.sculptor_skill)
        roll = seed % 100
        if roll < crack_pressure:
            self._sculptures[sculpture_id] = (
                dataclasses.replace(
                    s, stage=SculptureStage.CRACKED,
                    days_worked=s.days_worked + 1,
                )
            )
            return SculptureStage.CRACKED
        # Successful advance — quality grows with
        # skill / difficulty.
        gain = max(1, s.sculptor_skill // 5)
        new_quality = min(200, s.quality_score + gain)
        self._sculptures[sculpture_id] = (
            dataclasses.replace(
                s, stage=nxt, quality_score=new_quality,
                days_worked=s.days_worked + 1,
            )
        )
        return nxt

    def install(
        self, *, sculpture_id: str,
        install_location: str,
    ) -> bool:
        if sculpture_id not in self._sculptures:
            return False
        s = self._sculptures[sculpture_id]
        if s.stage != SculptureStage.POLISHED:
            return False
        if not install_location:
            return False
        self._sculptures[sculpture_id] = (
            dataclasses.replace(
                s, stage=SculptureStage.INSTALLED,
                install_location=install_location,
            )
        )
        return True

    def sculpture(
        self, *, sculpture_id: str,
    ) -> t.Optional[Sculpture]:
        return self._sculptures.get(sculpture_id)

    def installed_at(
        self, *, install_location: str,
    ) -> list[Sculpture]:
        return [
            s for s in self._sculptures.values()
            if (
                s.stage == SculptureStage.INSTALLED
                and s.install_location
                == install_location
            )
        ]


__all__ = [
    "StoneKind", "SculptureStage", "Sculpture",
    "PlayerSculptureSystem",
]
