"""Linkshell voting — motions, quorum, weighted votes.

Linkshells (linkshell module) need to make decisions: declaring
war on a rival LS, kicking a member, allocating treasury gil,
choosing a name change, voting on event participation. This
module runs the formal vote: a leader files a MOTION with a
TYPE; members cast YEA / NAY / ABSTAIN. Higher ranks have more
weight (PEARL_HOLDER = 1, SACK_HOLDER = 2, LINKSHELL_HOLDER = 4).

Quorum is 50% of members, default. Motions with quorum and
majority pass; tie or below-quorum fails.

Public surface
--------------
    MotionKind enum
    Vote enum
    Rank enum
    Motion dataclass
    VoteOutcome dataclass
    LinkshellVoting
        .file_motion(linkshell_id, kind, filer_id, ...)
        .cast_vote(motion_id, voter_id, vote, rank)
        .tally(motion_id) -> VoteOutcome
        .close_motion(motion_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default quorum fraction.
DEFAULT_QUORUM_FRACTION = 0.5


class MotionKind(str, enum.Enum):
    DECLARE_WAR = "declare_war"
    KICK_MEMBER = "kick_member"
    TREASURY_ALLOCATION = "treasury_allocation"
    RENAME_LINKSHELL = "rename_linkshell"
    EVENT_PARTICIPATION = "event_participation"
    PROMOTE_MEMBER = "promote_member"


class Vote(str, enum.Enum):
    YEA = "yea"
    NAY = "nay"
    ABSTAIN = "abstain"


class Rank(str, enum.Enum):
    PEARL_HOLDER = "pearl_holder"          # 1
    SACK_HOLDER = "sack_holder"            # 2
    LINKSHELL_HOLDER = "linkshell_holder"  # 4 (leader)


_RANK_WEIGHT: dict[Rank, int] = {
    Rank.PEARL_HOLDER: 1,
    Rank.SACK_HOLDER: 2,
    Rank.LINKSHELL_HOLDER: 4,
}


class MotionStatus(str, enum.Enum):
    OPEN = "open"
    PASSED = "passed"
    FAILED = "failed"
    TIED = "tied"
    NO_QUORUM = "no_quorum"
    CLOSED = "closed"


@dataclasses.dataclass
class Motion:
    motion_id: str
    linkshell_id: str
    kind: MotionKind
    filer_id: str
    member_count: int             # member roll at filing time
    note: str = ""
    filed_at_seconds: float = 0.0
    votes: dict[str, tuple[Vote, Rank]] = dataclasses.field(
        default_factory=dict,
    )
    status: MotionStatus = MotionStatus.OPEN


@dataclasses.dataclass(frozen=True)
class VoteOutcome:
    motion_id: str
    status: MotionStatus
    weighted_yea: int
    weighted_nay: int
    abstain_count: int
    voters_count: int
    quorum_required: int


@dataclasses.dataclass
class LinkshellVoting:
    quorum_fraction: float = DEFAULT_QUORUM_FRACTION
    _motions: dict[str, Motion] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def file_motion(
        self, *, linkshell_id: str, filer_id: str,
        kind: MotionKind, member_count: int,
        note: str = "",
        filed_at_seconds: float = 0.0,
    ) -> t.Optional[Motion]:
        if member_count <= 0:
            return None
        mid = f"motion_{self._next_id}"
        self._next_id += 1
        m = Motion(
            motion_id=mid, linkshell_id=linkshell_id,
            kind=kind, filer_id=filer_id,
            member_count=member_count, note=note,
            filed_at_seconds=filed_at_seconds,
        )
        self._motions[mid] = m
        return m

    def get(self, motion_id: str) -> t.Optional[Motion]:
        return self._motions.get(motion_id)

    def cast_vote(
        self, *, motion_id: str, voter_id: str,
        vote: Vote, rank: Rank,
    ) -> bool:
        m = self._motions.get(motion_id)
        if m is None or m.status != MotionStatus.OPEN:
            return False
        # Replacing an existing vote is allowed (member can
        # change their mind before tally).
        m.votes[voter_id] = (vote, rank)
        return True

    def tally(self, *, motion_id: str) -> t.Optional[VoteOutcome]:
        m = self._motions.get(motion_id)
        if m is None:
            return None
        weighted_yea = 0
        weighted_nay = 0
        abstain = 0
        for voter, (vote, rank) in m.votes.items():
            w = _RANK_WEIGHT[rank]
            if vote == Vote.YEA:
                weighted_yea += w
            elif vote == Vote.NAY:
                weighted_nay += w
            else:
                abstain += 1
        voters = len(m.votes)
        # Quorum is by HEAD COUNT, not by weight
        quorum_required = max(
            1,
            int(m.member_count * self.quorum_fraction),
        )
        if voters < quorum_required:
            status = MotionStatus.NO_QUORUM
        elif weighted_yea > weighted_nay:
            status = MotionStatus.PASSED
        elif weighted_yea < weighted_nay:
            status = MotionStatus.FAILED
        else:
            status = MotionStatus.TIED
        # If not currently OPEN, keep its existing terminal
        # status (don't re-tally a CLOSED motion); but for
        # OPEN motions, freeze the result so callers can see
        # what would have happened.
        if m.status == MotionStatus.OPEN:
            m.status = status
        return VoteOutcome(
            motion_id=motion_id, status=status,
            weighted_yea=weighted_yea,
            weighted_nay=weighted_nay,
            abstain_count=abstain,
            voters_count=voters,
            quorum_required=quorum_required,
        )

    def close_motion(self, *, motion_id: str) -> bool:
        m = self._motions.get(motion_id)
        if m is None:
            return False
        if m.status == MotionStatus.CLOSED:
            return False
        m.status = MotionStatus.CLOSED
        return True

    def total_motions(self) -> int:
        return len(self._motions)


__all__ = [
    "DEFAULT_QUORUM_FRACTION",
    "MotionKind", "Vote", "Rank",
    "MotionStatus",
    "Motion", "VoteOutcome",
    "LinkshellVoting",
]
