"""Mentor system — high-level players guiding newbies.

Modeled on canonical FFXI's mentor flag plus a queue-based
matchmaking for newbies looking for help. Mentors flag in,
newbies request help, and the queue pairs them.

Eligibility:
    Mentor flag requires a job at level 75+, no recent disciplinary
    action, and the player must have completed at least one nation
    mission storyline (rank 5).

    Newbie pool is open to any character whose highest job is < 30.

Rewards:
    Mentor sessions earn the mentor "Mentor JP" — a separate
    progress currency exchangeable for cosmetic items + a small
    JP injection on their main job.

Public surface
--------------
    MENTOR_MIN_JOB_LEVEL, NEWBIE_MAX_HIGHEST_JOB
    MentorEligibility / NewbieEligibility result types
    MentorMatch dataclass
    MentorRegistry
        .opt_in_mentor(player_id, ...) -> bool
        .request_help(newbie_id, topic) -> Optional[MentorMatch]
        .complete_session(match_id, ...) -> SessionResult
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MENTOR_MIN_JOB_LEVEL = 75
MENTOR_MIN_NATION_RANK = 5
NEWBIE_MAX_HIGHEST_JOB = 29

MENTOR_JP_PER_SESSION = 50
MENTOR_MAIN_JOB_JP_BONUS = 10


class HelpTopic(str, enum.Enum):
    JOB_BASICS = "job_basics"
    SUBJOB_GUIDE = "subjob_guide"
    NATION_MISSIONS = "nation_missions"
    CRAFTING = "crafting"
    GENERAL = "general"


@dataclasses.dataclass(frozen=True)
class MentorEligibility:
    eligible: bool
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class NewbieEligibility:
    eligible: bool
    reason: t.Optional[str] = None


def check_mentor_eligibility(
    *, highest_job_level: int, completed_rank_5: bool,
    has_recent_discipline: bool,
) -> MentorEligibility:
    if has_recent_discipline:
        return MentorEligibility(False, reason="recent disciplinary action")
    if highest_job_level < MENTOR_MIN_JOB_LEVEL:
        return MentorEligibility(
            False,
            reason=f"need a job at level {MENTOR_MIN_JOB_LEVEL}+",
        )
    if not completed_rank_5:
        return MentorEligibility(
            False, reason="must have completed nation rank 5",
        )
    return MentorEligibility(True)


def check_newbie_eligibility(*, highest_job_level: int) -> NewbieEligibility:
    if highest_job_level > NEWBIE_MAX_HIGHEST_JOB:
        return NewbieEligibility(
            False, reason="newbie pool is for highest-job-level < 30",
        )
    return NewbieEligibility(True)


@dataclasses.dataclass
class MentorMatch:
    match_id: str
    mentor_id: str
    newbie_id: str
    topic: HelpTopic
    matched_at: float = 0.0
    state: str = "open"        # open / completed / cancelled


@dataclasses.dataclass(frozen=True)
class SessionResult:
    accepted: bool
    mentor_jp_awarded: int = 0
    main_jp_bonus: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MentorRegistry:
    _flagged_mentors: list[str] = dataclasses.field(default_factory=list)
    _newbie_queue: list[tuple[str, HelpTopic]] = dataclasses.field(
        default_factory=list,
    )
    _matches: dict[str, MentorMatch] = dataclasses.field(
        default_factory=dict,
    )
    _next_match_id: int = 1

    def flagged_mentors(self) -> tuple[str, ...]:
        return tuple(self._flagged_mentors)

    def newbie_queue_size(self) -> int:
        return len(self._newbie_queue)

    def opt_in_mentor(
        self, *, player_id: str,
        highest_job_level: int, completed_rank_5: bool,
        has_recent_discipline: bool = False,
    ) -> MentorEligibility:
        elig = check_mentor_eligibility(
            highest_job_level=highest_job_level,
            completed_rank_5=completed_rank_5,
            has_recent_discipline=has_recent_discipline,
        )
        if not elig.eligible:
            return elig
        if player_id in self._flagged_mentors:
            return MentorEligibility(False, reason="already flagged")
        self._flagged_mentors.append(player_id)
        return MentorEligibility(True)

    def opt_out_mentor(self, *, player_id: str) -> bool:
        if player_id not in self._flagged_mentors:
            return False
        self._flagged_mentors.remove(player_id)
        return True

    def request_help(
        self, *, newbie_id: str, highest_job_level: int,
        topic: HelpTopic, now: float = 0.0,
    ) -> t.Optional[MentorMatch]:
        elig = check_newbie_eligibility(highest_job_level=highest_job_level)
        if not elig.eligible:
            return None
        # Try to immediately pair with a flagged mentor
        if not self._flagged_mentors:
            self._newbie_queue.append((newbie_id, topic))
            return None
        mentor_id = self._flagged_mentors.pop(0)
        match_id = f"mentor_{self._next_match_id}"
        self._next_match_id += 1
        match = MentorMatch(
            match_id=match_id, mentor_id=mentor_id,
            newbie_id=newbie_id, topic=topic, matched_at=now,
        )
        self._matches[match_id] = match
        return match

    def complete_session(self, *, match_id: str) -> SessionResult:
        match = self._matches.get(match_id)
        if match is None or match.state != "open":
            return SessionResult(False, reason="no such open session")
        match.state = "completed"
        return SessionResult(
            accepted=True,
            mentor_jp_awarded=MENTOR_JP_PER_SESSION,
            main_jp_bonus=MENTOR_MAIN_JOB_JP_BONUS,
        )

    def cancel_session(self, *, match_id: str) -> bool:
        match = self._matches.get(match_id)
        if match is None or match.state != "open":
            return False
        match.state = "cancelled"
        return True


__all__ = [
    "MENTOR_MIN_JOB_LEVEL", "NEWBIE_MAX_HIGHEST_JOB",
    "MENTOR_JP_PER_SESSION", "MENTOR_MAIN_JOB_JP_BONUS",
    "HelpTopic",
    "MentorEligibility", "NewbieEligibility",
    "MentorMatch", "SessionResult",
    "check_mentor_eligibility", "check_newbie_eligibility",
    "MentorRegistry",
]
