"""Player woodworking — lumber → custom furniture.

A specialized craft track separate from the main
crafting system: PLAYER WOODWORKING focuses on
furniture pieces for Mog Houses (the existing
furnishings module wraps the result). The flow:

    seasoned_lumber + crafting_skill -> PROJECT
    PROJECT goes through:
        PLANED -> JOINED -> SANDED -> FINISHED
    Each stage requires player time + tool durability;
    skipping a stage -> visible quality penalty.

Public surface
--------------
    Stage enum
    Finish enum (5 wood finishes)
    Project dataclass (frozen)
    PlayerWoodworkingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Stage(str, enum.Enum):
    PLANED = "planed"
    JOINED = "joined"
    SANDED = "sanded"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class Finish(str, enum.Enum):
    OIL = "oil"
    LACQUER = "lacquer"
    STAIN = "stain"
    PAINTED = "painted"
    WAX = "wax"


@dataclasses.dataclass(frozen=True)
class Project:
    project_id: str
    crafter_id: str
    item_kind: str
    lumber_units: int
    started_day: int
    stage: Stage
    quality_score: int  # 0..100
    chosen_finish: t.Optional[Finish]
    completed_day: t.Optional[int]


_STAGE_ORDER = [
    Stage.PLANED, Stage.JOINED, Stage.SANDED,
    Stage.FINISHED,
]


@dataclasses.dataclass
class PlayerWoodworkingSystem:
    _projects: dict[str, Project] = (
        dataclasses.field(default_factory=dict)
    )
    _next_id: int = 1

    def begin(
        self, *, crafter_id: str, item_kind: str,
        lumber_units: int, started_day: int,
    ) -> t.Optional[str]:
        if not crafter_id or not item_kind:
            return None
        if lumber_units <= 0:
            return None
        if started_day < 0:
            return None
        pid = f"proj_{self._next_id}"
        self._next_id += 1
        self._projects[pid] = Project(
            project_id=pid,
            crafter_id=crafter_id,
            item_kind=item_kind,
            lumber_units=lumber_units,
            started_day=started_day,
            stage=Stage.PLANED,
            quality_score=20,
            chosen_finish=None,
            completed_day=None,
        )
        return pid

    def advance(
        self, *, project_id: str, skill_check: int,
    ) -> bool:
        """skill_check is 0..100; success scales
        quality_score gain. Each call advances one
        stage."""
        if project_id not in self._projects:
            return False
        if not 0 <= skill_check <= 100:
            return False
        p = self._projects[project_id]
        if p.stage in (
            Stage.FINISHED, Stage.ABANDONED,
        ):
            return False
        try:
            idx = _STAGE_ORDER.index(p.stage)
        except ValueError:
            return False
        if idx + 1 >= len(_STAGE_ORDER):
            return False
        new_stage = _STAGE_ORDER[idx + 1]
        # Quality gain: skill_check / 5 (so 100
        # = +20, ranges across 4 advances ~+80
        # max).
        gain = skill_check // 5
        new_quality = min(
            100, p.quality_score + gain,
        )
        self._projects[project_id] = (
            dataclasses.replace(
                p, stage=new_stage,
                quality_score=new_quality,
            )
        )
        return True

    def skip_stage(
        self, *, project_id: str,
    ) -> bool:
        """Skip the next stage with a quality
        penalty."""
        if project_id not in self._projects:
            return False
        p = self._projects[project_id]
        if p.stage in (
            Stage.FINISHED, Stage.ABANDONED,
        ):
            return False
        try:
            idx = _STAGE_ORDER.index(p.stage)
        except ValueError:
            return False
        if idx + 1 >= len(_STAGE_ORDER):
            return False
        new_stage = _STAGE_ORDER[idx + 1]
        new_quality = max(0, p.quality_score - 25)
        self._projects[project_id] = (
            dataclasses.replace(
                p, stage=new_stage,
                quality_score=new_quality,
            )
        )
        return True

    def apply_finish(
        self, *, project_id: str,
        finish: Finish, now_day: int,
    ) -> bool:
        if project_id not in self._projects:
            return False
        p = self._projects[project_id]
        if p.stage != Stage.FINISHED:
            return False
        if p.chosen_finish is not None:
            return False
        # Finish adds a small final quality bump
        new_quality = min(100, p.quality_score + 5)
        self._projects[project_id] = (
            dataclasses.replace(
                p, chosen_finish=finish,
                quality_score=new_quality,
                completed_day=now_day,
            )
        )
        return True

    def abandon(
        self, *, project_id: str,
    ) -> bool:
        if project_id not in self._projects:
            return False
        p = self._projects[project_id]
        if p.stage in (
            Stage.FINISHED, Stage.ABANDONED,
        ):
            return False
        self._projects[project_id] = (
            dataclasses.replace(
                p, stage=Stage.ABANDONED,
            )
        )
        return True

    def project(
        self, *, project_id: str,
    ) -> t.Optional[Project]:
        return self._projects.get(project_id)

    def projects_of(
        self, *, crafter_id: str,
    ) -> list[Project]:
        return [
            p for p in self._projects.values()
            if p.crafter_id == crafter_id
        ]

    def is_complete(
        self, *, project_id: str,
    ) -> bool:
        if project_id not in self._projects:
            return False
        p = self._projects[project_id]
        return (
            p.stage == Stage.FINISHED
            and p.chosen_finish is not None
        )


__all__ = [
    "Stage", "Finish", "Project",
    "PlayerWoodworkingSystem",
]
