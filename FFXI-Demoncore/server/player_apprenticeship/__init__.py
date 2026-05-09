"""Player apprenticeship — formal master/apprentice bond.

A 1:1 relationship where a master in a craft takes on an
apprentice. Each training session passes a small chunk of the
master's skill to the apprentice (master.skill // 20 per
session, capped to not exceed master). After enough sessions,
the apprentice can graduate — earning their own master title
in that craft, and the relationship resolves into peer
status.

Lifecycle
    PROPOSED      master offered, apprentice hasn't accepted
    ACTIVE        formal apprenticeship under way
    GRADUATED     apprentice reached graduation criteria
    DISSOLVED     either party walked away

Public surface
--------------
    ApprenticeshipState enum
    Apprenticeship dataclass (frozen)
    PlayerApprenticeshipSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_GRADUATION_THRESHOLD = 100


class ApprenticeshipState(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    GRADUATED = "graduated"
    DISSOLVED = "dissolved"


@dataclasses.dataclass(frozen=True)
class Apprenticeship:
    apprenticeship_id: str
    master_id: str
    apprentice_id: str
    craft: str
    master_skill: int
    apprentice_skill: int
    sessions_logged: int
    state: ApprenticeshipState
    started_day: int


@dataclasses.dataclass
class PlayerApprenticeshipSystem:
    _apps: dict[str, Apprenticeship] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def propose(
        self, *, master_id: str, apprentice_id: str,
        craft: str, master_skill: int,
        apprentice_starting_skill: int,
        proposed_day: int,
    ) -> t.Optional[str]:
        if not master_id or not apprentice_id:
            return None
        if master_id == apprentice_id:
            return None
        if not craft:
            return None
        if not 1 <= master_skill <= 100:
            return None
        if not 0 <= apprentice_starting_skill <= 100:
            return None
        if apprentice_starting_skill >= master_skill:
            return None
        if proposed_day < 0:
            return None
        # Block if the apprentice is already in an
        # active apprenticeship for this craft.
        for a in self._apps.values():
            if (
                a.craft == craft
                and a.apprentice_id == apprentice_id
                and a.state in (
                    ApprenticeshipState.PROPOSED,
                    ApprenticeshipState.ACTIVE,
                )
            ):
                return None
        aid = f"app_{self._next}"
        self._next += 1
        self._apps[aid] = Apprenticeship(
            apprenticeship_id=aid,
            master_id=master_id,
            apprentice_id=apprentice_id,
            craft=craft, master_skill=master_skill,
            apprentice_skill=(
                apprentice_starting_skill
            ),
            sessions_logged=0,
            state=ApprenticeshipState.PROPOSED,
            started_day=proposed_day,
        )
        return aid

    def accept(
        self, *, apprenticeship_id: str,
        apprentice_id: str,
    ) -> bool:
        if apprenticeship_id not in self._apps:
            return False
        a = self._apps[apprenticeship_id]
        if a.state != ApprenticeshipState.PROPOSED:
            return False
        if a.apprentice_id != apprentice_id:
            return False
        self._apps[apprenticeship_id] = (
            dataclasses.replace(
                a, state=ApprenticeshipState.ACTIVE,
            )
        )
        return True

    def train_session(
        self, *, apprenticeship_id: str,
    ) -> t.Optional[int]:
        """Returns the apprentice's new skill level."""
        if apprenticeship_id not in self._apps:
            return None
        a = self._apps[apprenticeship_id]
        if a.state != ApprenticeshipState.ACTIVE:
            return None
        # Skill gain decays as apprentice approaches
        # master — last 5 points are the hardest
        gain = max(
            1, (a.master_skill - a.apprentice_skill) // 5,
        )
        new_skill = min(
            a.master_skill, a.apprentice_skill + gain,
        )
        self._apps[apprenticeship_id] = (
            dataclasses.replace(
                a, apprentice_skill=new_skill,
                sessions_logged=a.sessions_logged + 1,
            )
        )
        return new_skill

    def graduate(
        self, *, apprenticeship_id: str,
    ) -> t.Optional[int]:
        """Returns final apprentice skill on
        success. Requires master_skill threshold
        and at least 5 sessions.
        """
        if apprenticeship_id not in self._apps:
            return None
        a = self._apps[apprenticeship_id]
        if a.state != ApprenticeshipState.ACTIVE:
            return None
        if a.apprentice_skill < _GRADUATION_THRESHOLD:
            return None
        if a.sessions_logged < 5:
            return None
        self._apps[apprenticeship_id] = (
            dataclasses.replace(
                a, state=(
                    ApprenticeshipState.GRADUATED
                ),
            )
        )
        return a.apprentice_skill

    def dissolve(
        self, *, apprenticeship_id: str,
        party_id: str,
    ) -> bool:
        if apprenticeship_id not in self._apps:
            return False
        a = self._apps[apprenticeship_id]
        if a.state not in (
            ApprenticeshipState.PROPOSED,
            ApprenticeshipState.ACTIVE,
        ):
            return False
        if party_id not in (
            a.master_id, a.apprentice_id,
        ):
            return False
        self._apps[apprenticeship_id] = (
            dataclasses.replace(
                a, state=(
                    ApprenticeshipState.DISSOLVED
                ),
            )
        )
        return True

    def apprenticeship(
        self, *, apprenticeship_id: str,
    ) -> t.Optional[Apprenticeship]:
        return self._apps.get(apprenticeship_id)

    def apprentices_of(
        self, *, master_id: str,
    ) -> list[Apprenticeship]:
        return [
            a for a in self._apps.values()
            if a.master_id == master_id
        ]


__all__ = [
    "ApprenticeshipState", "Apprenticeship",
    "PlayerApprenticeshipSystem",
]
