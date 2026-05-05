"""Crew recruit board — public LFG board for joining crews.

Crews post POSTINGS to a public board. Solo players browse,
filter, and APPLY. Captains review applications and INVITE
the ones they want (the invite goes through
pirate_crew_charter.invite normally).

A posting has:
  charter_id          - which crew is recruiting
  flag                - PIRATE / PRIVATEER / MERCHANT
                        (cosmetic for filtering)
  min_level           - lvl gate (0 = no gate)
  preferred_role      - what they're looking for (job string)
  blurb               - short pitch
  expires_at          - postings auto-expire (default 7 days)

Players have at most 5 ACTIVE applications (drift gate to
prevent spam).

Public surface
--------------
    Posting dataclass
    Application dataclass
    CrewRecruitBoard
        .post(charter_id, captain_id, flag, min_level,
              preferred_role, blurb, now_seconds,
              duration_seconds)
        .browse(filter_flag, max_level, now_seconds)
        .apply(player_id, posting_id, now_seconds)
        .applications_for(charter_id) -> list[Application]
        .withdraw_application(player_id, posting_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PostingFlag(str, enum.Enum):
    PIRATE = "pirate"
    PRIVATEER = "privateer"
    MERCHANT = "merchant"


MAX_ACTIVE_APPLICATIONS = 5
DEFAULT_POSTING_DURATION = 7 * 24 * 3_600


@dataclasses.dataclass
class Posting:
    posting_id: str
    charter_id: str
    captain_id: str
    flag: PostingFlag
    min_level: int
    preferred_role: str
    blurb: str
    posted_at: int
    expires_at: int


@dataclasses.dataclass
class Application:
    posting_id: str
    player_id: str
    applied_at: int


@dataclasses.dataclass(frozen=True)
class PostResult:
    accepted: bool
    posting_id: t.Optional[str] = None
    expires_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ApplyResult:
    accepted: bool
    posting_id: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class CrewRecruitBoard:
    _postings: dict[str, Posting] = dataclasses.field(default_factory=dict)
    # player -> set of posting_ids they're applied to
    _applications: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # posting_id -> list of applications
    _by_posting: dict[str, list[Application]] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def post(
        self, *, charter_id: str,
        captain_id: str,
        flag: PostingFlag,
        min_level: int,
        preferred_role: str,
        blurb: str,
        now_seconds: int,
        duration_seconds: int = DEFAULT_POSTING_DURATION,
    ) -> PostResult:
        if not charter_id or not captain_id:
            return PostResult(False, reason="bad ids")
        if flag not in PostingFlag:
            return PostResult(False, reason="unknown flag")
        if min_level < 0 or min_level > 99:
            return PostResult(False, reason="bad level")
        if duration_seconds <= 0:
            return PostResult(False, reason="bad duration")
        self._next_id += 1
        posting_id = f"post_{self._next_id:06d}"
        expires = now_seconds + duration_seconds
        self._postings[posting_id] = Posting(
            posting_id=posting_id,
            charter_id=charter_id,
            captain_id=captain_id,
            flag=flag,
            min_level=min_level,
            preferred_role=preferred_role,
            blurb=blurb,
            posted_at=now_seconds,
            expires_at=expires,
        )
        return PostResult(
            accepted=True, posting_id=posting_id,
            expires_at=expires,
        )

    def browse(
        self, *, filter_flag: t.Optional[PostingFlag] = None,
        max_level: t.Optional[int] = None,
        now_seconds: int,
    ) -> tuple[Posting, ...]:
        out: list[Posting] = []
        for p in self._postings.values():
            if p.expires_at <= now_seconds:
                continue
            if filter_flag is not None and p.flag != filter_flag:
                continue
            if max_level is not None and p.min_level > max_level:
                continue
            out.append(p)
        return tuple(out)

    def apply(
        self, *, player_id: str,
        posting_id: str,
        now_seconds: int,
    ) -> ApplyResult:
        if not player_id:
            return ApplyResult(False, reason="bad player")
        p = self._postings.get(posting_id)
        if p is None:
            return ApplyResult(False, reason="unknown posting")
        if p.expires_at <= now_seconds:
            return ApplyResult(False, reason="expired")
        existing = self._applications.setdefault(player_id, set())
        if posting_id in existing:
            return ApplyResult(False, reason="already applied")
        if len(existing) >= MAX_ACTIVE_APPLICATIONS:
            return ApplyResult(
                False, reason="active app cap",
            )
        existing.add(posting_id)
        self._by_posting.setdefault(posting_id, []).append(
            Application(
                posting_id=posting_id,
                player_id=player_id,
                applied_at=now_seconds,
            )
        )
        return ApplyResult(accepted=True, posting_id=posting_id)

    def applications_for(
        self, *, charter_id: str,
    ) -> tuple[Application, ...]:
        out: list[Application] = []
        for p in self._postings.values():
            if p.charter_id != charter_id:
                continue
            out.extend(self._by_posting.get(p.posting_id, []))
        return tuple(out)

    def withdraw_application(
        self, *, player_id: str, posting_id: str,
    ) -> bool:
        s = self._applications.get(player_id)
        if s is None or posting_id not in s:
            return False
        s.discard(posting_id)
        # remove from posting's apps too
        apps = self._by_posting.get(posting_id, [])
        self._by_posting[posting_id] = [
            a for a in apps if a.player_id != player_id
        ]
        return True


__all__ = [
    "PostingFlag", "Posting", "Application",
    "PostResult", "ApplyResult",
    "CrewRecruitBoard",
    "MAX_ACTIVE_APPLICATIONS", "DEFAULT_POSTING_DURATION",
]
