"""Entity skill progression — NPCs improve at hobbies over time.

Every hobby session an NPC completes adds to their hobby_skill
in that domain. Thresholds promote them: NOVICE 0..49,
JOURNEYMAN 50..149, EXPERT 150..399, MASTER 400+. NPCs at
MASTER tier earn public titles ("Volker the Master Fisher")
that propagate through gossip and dialog. The same NPC can be
master at one hobby and novice at another.

This is the "world has weekends, and NPCs grow at them" axis:
a Tarutaru WHM who spends a year at calligraphy can become
genuinely renowned for it, and players will hunt down
"signed by the Master Calligrapher" works the way they hunt
relic weapons.

Public surface
--------------
    SkillTier enum
    Skill dataclass (frozen)
    EntitySkillProgressionSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.entity_hobbies import HobbyKind


_TIER_THRESHOLDS = (
    (0, "novice"),
    (50, "journeyman"),
    (150, "expert"),
    (400, "master"),
)


class SkillTier(str, enum.Enum):
    NOVICE = "novice"
    JOURNEYMAN = "journeyman"
    EXPERT = "expert"
    MASTER = "master"


@dataclasses.dataclass(frozen=True)
class Skill:
    entity_id: str
    hobby: HobbyKind
    skill_score: int
    sessions_logged: int


_TITLE_FORMATS = {
    "fishing": "Master Angler",
    "drinking": "Master Drinker",
    "painting": "Master Painter",
    "metalwork": "Master Smith",
    "reading": "Master Scholar",
    "gambling": "Master Gambler",
    "gardening": "Master Gardener",
    "meditation": "Master of Stillness",
    "singing": "Master Singer",
    "weightlifting": "Master Strongman",
    "calligraphy": "Master Calligrapher",
    "birdwatching": "Master Watcher",
}


def _tier_for_score(score: int) -> SkillTier:
    label = "novice"
    for thresh, name in _TIER_THRESHOLDS:
        if score >= thresh:
            label = name
    return SkillTier(label)


@dataclasses.dataclass
class EntitySkillProgressionSystem:
    _skills: dict[tuple[str, str], Skill] = (
        dataclasses.field(default_factory=dict)
    )

    def log_session(
        self, *, entity_id: str, hobby: HobbyKind,
        gain: int = 1,
    ) -> bool:
        if not entity_id:
            return False
        if gain <= 0:
            return False
        key = (entity_id, hobby.value)
        cur = self._skills.get(key)
        if cur is None:
            self._skills[key] = Skill(
                entity_id=entity_id, hobby=hobby,
                skill_score=gain, sessions_logged=1,
            )
        else:
            self._skills[key] = dataclasses.replace(
                cur, skill_score=cur.skill_score + gain,
                sessions_logged=cur.sessions_logged + 1,
            )
        return True

    def skill(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> int:
        key = (entity_id, hobby.value)
        s = self._skills.get(key)
        return 0 if s is None else s.skill_score

    def tier(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> SkillTier:
        return _tier_for_score(
            self.skill(
                entity_id=entity_id, hobby=hobby,
            ),
        )

    def has_master_title(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> bool:
        return self.tier(
            entity_id=entity_id, hobby=hobby,
        ) == SkillTier.MASTER

    def public_title(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> t.Optional[str]:
        if not self.has_master_title(
            entity_id=entity_id, hobby=hobby,
        ):
            return None
        return _TITLE_FORMATS.get(
            hobby.value, "Master Hobbyist",
        )

    def sessions(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> int:
        key = (entity_id, hobby.value)
        s = self._skills.get(key)
        return 0 if s is None else s.sessions_logged

    def all_skills_for(
        self, *, entity_id: str,
    ) -> list[Skill]:
        return [
            s for s in self._skills.values()
            if s.entity_id == entity_id
        ]

    def all_masters(
        self, *, hobby: HobbyKind,
    ) -> list[str]:
        return sorted(
            s.entity_id for s in self._skills.values()
            if s.hobby == hobby
            and s.skill_score >= 400
        )


__all__ = [
    "SkillTier", "Skill",
    "EntitySkillProgressionSystem",
]
