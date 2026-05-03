"""Job training — AI mentor apprenticeship.

Players don't level skills in a vacuum. Master crafters and job
trainers (also AI agents) take on apprentices and accelerate
their growth — but only if they LIKE you. Faction reputation +
the mentor's memory of you + their available teaching slots all
gate the relationship.

Apprenticeship effects
----------------------
* Skill XP gain bonus (+25% baseline, scales with mentor tier)
* Access to the mentor's signed/HQ recipes
* Periodic stipend or gear gift
* The mentor periodically asks for an errand (faction quest hook)

Slots
-----
A mentor has a fixed number of apprentice slots — usually 1-3.
They prioritize ALLIED+/HERO_OF_THE_FACTION players. If full,
they refuse new apprentices.

Lifecycle
---------
PROPOSE  → ACTIVE  → COMPLETED (player hits skill cap with mentor)
                  → DISMISSED (mentor fired the apprentice)
                  → ABANDONED (player walked away)

Public surface
--------------
    MentorTier enum
    TrainingSubject enum (which skill / job)
    MentorProfile dataclass
    Apprenticeship dataclass
    ApprenticeshipStatus enum
    JobTrainingRegistry
        .register_mentor(profile)
        .propose_apprenticeship(player_id, mentor_id, subject)
        .accept(...)
        .skill_gain_bonus(player_id, subject)
        .complete / .dismiss / .abandon
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.faction_reputation import (
    PlayerFactionReputation,
    ReputationBand,
)


class MentorTier(str, enum.Enum):
    JOURNEYMAN = "journeyman"     # +15% bonus
    MASTER = "master"             # +25% bonus
    GRANDMASTER = "grandmaster"   # +40% bonus, signed gear access


class TrainingSubject(str, enum.Enum):
    # Crafts
    SMITHING = "smithing"
    GOLDSMITHING = "goldsmithing"
    LEATHERCRAFT = "leathercraft"
    BONECRAFT = "bonecraft"
    CLOTHCRAFT = "clothcraft"
    ALCHEMY = "alchemy"
    WOODWORKING = "woodworking"
    COOKING = "cooking"
    # Jobs (combat skills)
    SWORD = "sword"
    GREATSWORD = "greatsword"
    AXE = "axe"
    SCYTHE = "scythe"
    HAND_TO_HAND = "hand_to_hand"
    DAGGER = "dagger"
    STAFF = "staff"
    ARCHERY = "archery"
    HEALING_MAGIC = "healing_magic"
    ELEMENTAL_MAGIC = "elemental_magic"
    DARK_MAGIC = "dark_magic"
    NINJUTSU = "ninjutsu"
    SUMMONING = "summoning"


class ApprenticeshipStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    COMPLETED = "completed"
    DISMISSED = "dismissed"
    ABANDONED = "abandoned"


# Per-tier XP multipliers.
_TIER_BONUS: dict[MentorTier, float] = {
    MentorTier.JOURNEYMAN: 1.15,
    MentorTier.MASTER: 1.25,
    MentorTier.GRANDMASTER: 1.40,
}


# Bands at which the mentor will accept a proposal at all.
_ACCEPT_BANDS: frozenset[ReputationBand] = frozenset({
    ReputationBand.FRIENDLY, ReputationBand.ALLIED,
    ReputationBand.HERO_OF_THE_FACTION,
})


@dataclasses.dataclass
class MentorProfile:
    mentor_id: str
    faction_id: str
    subject: TrainingSubject
    tier: MentorTier = MentorTier.JOURNEYMAN
    max_apprentices: int = 1
    grants_signed_recipes: bool = False
    notes: str = ""


@dataclasses.dataclass
class Apprenticeship:
    player_id: str
    mentor_id: str
    subject: TrainingSubject
    status: ApprenticeshipStatus = ApprenticeshipStatus.PROPOSED
    started_at_seconds: float = 0.0
    completed_at_seconds: t.Optional[float] = None
    cause: str = ""


@dataclasses.dataclass(frozen=True)
class ProposeResult:
    accepted: bool
    apprenticeship: t.Optional[Apprenticeship] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class JobTrainingRegistry:
    _mentors: dict[str, MentorProfile] = dataclasses.field(
        default_factory=dict,
    )
    _apprenticeships: list[Apprenticeship] = dataclasses.field(
        default_factory=list,
    )

    def register_mentor(
        self, profile: MentorProfile,
    ) -> MentorProfile:
        self._mentors[profile.mentor_id] = profile
        return profile

    def mentor(self, mentor_id: str) -> t.Optional[MentorProfile]:
        return self._mentors.get(mentor_id)

    def _active_apprentices(
        self, mentor_id: str,
    ) -> tuple[Apprenticeship, ...]:
        return tuple(
            a for a in self._apprenticeships
            if a.mentor_id == mentor_id
            and a.status in (
                ApprenticeshipStatus.PROPOSED,
                ApprenticeshipStatus.ACTIVE,
            )
        )

    def _player_active_with_mentor(
        self, *, player_id: str, mentor_id: str,
    ) -> t.Optional[Apprenticeship]:
        for a in self._apprenticeships:
            if (a.player_id == player_id
                    and a.mentor_id == mentor_id
                    and a.status in (
                        ApprenticeshipStatus.PROPOSED,
                        ApprenticeshipStatus.ACTIVE,
                    )):
                return a
        return None

    def propose_apprenticeship(
        self, *, player_id: str, mentor_id: str,
        subject: TrainingSubject,
        rep: PlayerFactionReputation,
        now_seconds: float = 0.0,
    ) -> ProposeResult:
        mentor = self._mentors.get(mentor_id)
        if mentor is None:
            return ProposeResult(False, reason="no such mentor")
        if mentor.subject != subject:
            return ProposeResult(
                False,
                reason="mentor doesn't teach that subject",
            )
        # Already mentoring this player?
        if self._player_active_with_mentor(
            player_id=player_id, mentor_id=mentor_id,
        ):
            return ProposeResult(
                False, reason="already mentoring this player",
            )
        # Slot check
        if len(self._active_apprentices(
            mentor_id,
        )) >= mentor.max_apprentices:
            return ProposeResult(False, reason="mentor at capacity")
        # Faction-rep gate
        band = rep.band(mentor.faction_id)
        if band not in _ACCEPT_BANDS:
            return ProposeResult(
                False,
                reason=f"rep too low ({band.value}); need FRIENDLY+",
            )
        ap = Apprenticeship(
            player_id=player_id, mentor_id=mentor_id,
            subject=subject,
            status=ApprenticeshipStatus.PROPOSED,
            started_at_seconds=now_seconds,
        )
        self._apprenticeships.append(ap)
        return ProposeResult(True, apprenticeship=ap)

    def accept(
        self, *, player_id: str, mentor_id: str,
        now_seconds: float = 0.0,
    ) -> bool:
        ap = self._player_active_with_mentor(
            player_id=player_id, mentor_id=mentor_id,
        )
        if ap is None or ap.status != ApprenticeshipStatus.PROPOSED:
            return False
        ap.status = ApprenticeshipStatus.ACTIVE
        ap.started_at_seconds = now_seconds
        return True

    def skill_gain_bonus(
        self, *, player_id: str, subject: TrainingSubject,
    ) -> float:
        """Multiplier applied to skill_levels XP gain. 1.0 = no
        bonus. Picks the BEST active apprenticeship if multiple
        mentors of different tiers cover the same subject (rare
        but possible)."""
        best = 1.0
        for a in self._apprenticeships:
            if (
                a.player_id == player_id
                and a.subject == subject
                and a.status == ApprenticeshipStatus.ACTIVE
            ):
                mentor = self._mentors.get(a.mentor_id)
                if mentor is None:
                    continue
                bonus = _TIER_BONUS[mentor.tier]
                if bonus > best:
                    best = bonus
        return best

    def grants_signed_for(
        self, *, player_id: str, subject: TrainingSubject,
    ) -> bool:
        for a in self._apprenticeships:
            if (
                a.player_id == player_id
                and a.subject == subject
                and a.status == ApprenticeshipStatus.ACTIVE
            ):
                mentor = self._mentors.get(a.mentor_id)
                if mentor and mentor.grants_signed_recipes:
                    return True
        return False

    def complete(
        self, *, player_id: str, mentor_id: str,
        now_seconds: float = 0.0,
    ) -> bool:
        ap = self._player_active_with_mentor(
            player_id=player_id, mentor_id=mentor_id,
        )
        if ap is None or ap.status != ApprenticeshipStatus.ACTIVE:
            return False
        ap.status = ApprenticeshipStatus.COMPLETED
        ap.completed_at_seconds = now_seconds
        return True

    def dismiss(
        self, *, player_id: str, mentor_id: str,
        now_seconds: float = 0.0, cause: str = "",
    ) -> bool:
        ap = self._player_active_with_mentor(
            player_id=player_id, mentor_id=mentor_id,
        )
        if ap is None:
            return False
        ap.status = ApprenticeshipStatus.DISMISSED
        ap.completed_at_seconds = now_seconds
        ap.cause = cause
        return True

    def abandon(
        self, *, player_id: str, mentor_id: str,
        now_seconds: float = 0.0,
    ) -> bool:
        ap = self._player_active_with_mentor(
            player_id=player_id, mentor_id=mentor_id,
        )
        if ap is None:
            return False
        ap.status = ApprenticeshipStatus.ABANDONED
        ap.completed_at_seconds = now_seconds
        return True

    def apprentices_of(
        self, mentor_id: str,
    ) -> tuple[Apprenticeship, ...]:
        return tuple(
            a for a in self._apprenticeships
            if a.mentor_id == mentor_id
        )

    def apprenticeships_of_player(
        self, player_id: str,
    ) -> tuple[Apprenticeship, ...]:
        return tuple(
            a for a in self._apprenticeships
            if a.player_id == player_id
        )

    def total_mentors(self) -> int:
        return len(self._mentors)


__all__ = [
    "MentorTier", "TrainingSubject",
    "ApprenticeshipStatus",
    "MentorProfile", "Apprenticeship",
    "ProposeResult", "JobTrainingRegistry",
]
