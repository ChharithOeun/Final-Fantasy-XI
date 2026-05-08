"""Mentor/apprentice bond — formal teaching relationship.

mentor_system (existing) is the high-level mentor flag
that lets players be paired with newbies in a queue.
mentor_apprentice_bond is the FORMAL one-to-one
relationship — a senior player takes a junior under
their wing, teaches a job over time, and both benefit.

A bond goes through 3 stages:
    PROPOSED        senior offers; junior hasn't accepted
    ACTIVE          both parties bonded; teaching ongoing
    GRADUATED       junior hit master-of-job; severed by
                    completion, not failure
    DISSOLVED       either party walked away

Per-bond state:
    job_being_taught           which job mentor focused
                               on (e.g. WAR)
    sessions_completed         times they've grouped to
                               party-XP this job
    skill_transferred_pct      0..100 — how far the
                               apprentice has come
    apprentice_caps_unlocked   capped abilities the
                               apprentice can now access
                               (a small list of teach-only
                               JAs)

Mentor benefits:
    +1 to a "Master Teacher" fame counter per session
    Up to 3 active apprentices simultaneously

Apprentice benefits:
    +20% XP gain in the taught job while in a party
    that includes the mentor
    Access to teach-only "rookie shortcuts"
    The mentor's name is recorded in their player_chronicle

Public surface
--------------
    BondStage enum
    MentorBond dataclass (frozen)
    MentorApprenticeBond
        .propose(mentor, apprentice, job) -> bool
        .accept(apprentice) -> bool
        .record_session(mentor, apprentice, gain_pct)
            -> bool
        .unlock_cap(mentor, apprentice, ability_id) -> bool
        .graduate(mentor, apprentice) -> bool
        .dissolve(by_player, other) -> bool
        .bond(mentor, apprentice) -> Optional[MentorBond]
        .active_apprentices(mentor) -> list[str]
        .mentor_of(apprentice) -> Optional[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_MAX_APPRENTICES_PER_MENTOR = 3
_GRADUATION_PCT = 100


class BondStage(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    GRADUATED = "graduated"
    DISSOLVED = "dissolved"


@dataclasses.dataclass(frozen=True)
class MentorBond:
    mentor: str
    apprentice: str
    job: str
    stage: BondStage
    sessions_completed: int
    skill_transferred_pct: int
    apprentice_caps: tuple[str, ...]


@dataclasses.dataclass
class _Bond:
    job: str
    stage: BondStage = BondStage.PROPOSED
    sessions: int = 0
    pct: int = 0
    caps: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class MentorApprenticeBond:
    # (mentor, apprentice) -> bond state
    _bonds: dict[
        tuple[str, str], _Bond,
    ] = dataclasses.field(default_factory=dict)

    def propose(
        self, *, mentor: str, apprentice: str, job: str,
    ) -> bool:
        if not mentor or not apprentice or not job:
            return False
        if mentor == apprentice:
            return False
        # Apprentice can have only ONE active mentor
        if self.mentor_of(apprentice=apprentice) is not None:
            return False
        # Mentor cap on simultaneous active apprentices
        active = self.active_apprentices(mentor=mentor)
        if len(active) >= _MAX_APPRENTICES_PER_MENTOR:
            return False
        key = (mentor, apprentice)
        if key in self._bonds:
            cur = self._bonds[key].stage
            if cur in (BondStage.PROPOSED, BondStage.ACTIVE):
                return False
        self._bonds[key] = _Bond(job=job)
        return True

    def accept(
        self, *, mentor: str, apprentice: str,
    ) -> bool:
        key = (mentor, apprentice)
        if key not in self._bonds:
            return False
        b = self._bonds[key]
        if b.stage != BondStage.PROPOSED:
            return False
        b.stage = BondStage.ACTIVE
        return True

    def record_session(
        self, *, mentor: str, apprentice: str,
        gain_pct: int,
    ) -> bool:
        if gain_pct <= 0:
            return False
        key = (mentor, apprentice)
        if key not in self._bonds:
            return False
        b = self._bonds[key]
        if b.stage != BondStage.ACTIVE:
            return False
        b.sessions += 1
        b.pct = min(_GRADUATION_PCT, b.pct + gain_pct)
        return True

    def unlock_cap(
        self, *, mentor: str, apprentice: str,
        ability_id: str,
    ) -> bool:
        if not ability_id:
            return False
        key = (mentor, apprentice)
        if key not in self._bonds:
            return False
        b = self._bonds[key]
        if b.stage != BondStage.ACTIVE:
            return False
        if ability_id in b.caps:
            return False
        b.caps.append(ability_id)
        return True

    def graduate(
        self, *, mentor: str, apprentice: str,
    ) -> bool:
        key = (mentor, apprentice)
        if key not in self._bonds:
            return False
        b = self._bonds[key]
        if b.stage != BondStage.ACTIVE:
            return False
        if b.pct < _GRADUATION_PCT:
            return False
        b.stage = BondStage.GRADUATED
        return True

    def dissolve(
        self, *, by_player: str, other: str,
    ) -> bool:
        # Either direction can be the bond key
        for key in [(by_player, other), (other, by_player)]:
            if key not in self._bonds:
                continue
            b = self._bonds[key]
            if b.stage in (
                BondStage.GRADUATED, BondStage.DISSOLVED,
            ):
                return False
            b.stage = BondStage.DISSOLVED
            return True
        return False

    def bond(
        self, *, mentor: str, apprentice: str,
    ) -> t.Optional[MentorBond]:
        key = (mentor, apprentice)
        if key not in self._bonds:
            return None
        b = self._bonds[key]
        return MentorBond(
            mentor=mentor, apprentice=apprentice,
            job=b.job, stage=b.stage,
            sessions_completed=b.sessions,
            skill_transferred_pct=b.pct,
            apprentice_caps=tuple(b.caps),
        )

    def active_apprentices(
        self, *, mentor: str,
    ) -> list[str]:
        return sorted(
            apprentice
            for (m, apprentice), b in self._bonds.items()
            if m == mentor
            and b.stage in (
                BondStage.PROPOSED, BondStage.ACTIVE,
            )
        )

    def mentor_of(
        self, *, apprentice: str,
    ) -> t.Optional[str]:
        for (m, a), b in self._bonds.items():
            if a == apprentice and b.stage in (
                BondStage.PROPOSED, BondStage.ACTIVE,
            ):
                return m
        return None


__all__ = [
    "BondStage", "MentorBond", "MentorApprenticeBond",
]
