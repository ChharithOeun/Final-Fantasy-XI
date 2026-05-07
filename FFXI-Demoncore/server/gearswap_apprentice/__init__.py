"""GearSwap apprentice — famous mentor takes on apprentices.

The mentor reputation system already gates publishing.
This chunk turns the mentor → newbie relationship into
a structured pipeline: a mentor accepts up to N concurrent
apprentices, who publish their first lua under
"apprentice of [Mentor Name]" and the mentor gets a
small fame credit when the apprentice's first lua
crosses the 10-adopt fame tier (the apprentice still
gets the gil + title themselves; the mentor gets the
"taught a famous author" credit on their dashboard).

This is intentionally small in scope:
    - mentors with rep > 0 can accept apprentices
    - apprentice cap of 5 concurrent (pedagogy: too
      many apprentices and the mentor can't actually
      mentor any of them)
    - apprentice can graduate (mentor releases them)
      or quit (apprentice releases the mentor); both
      directions allowed
    - "graduates_taught" = lifetime count of graduates
      who reached the first fame tier under your wing

This is the "sensei" stat. Some players will optimize
for max graduates. The leaderboard chunk could
optionally surface this in a future iteration.

Public surface
--------------
    ApprenticeStatus enum
    Apprenticeship dataclass (frozen)
    GearswapApprentice
        .accept(mentor_id, apprentice_id, started_at) -> bool
        .release(mentor_id, apprentice_id, by_mentor)
            -> bool
        .record_graduation(apprentice_id, graduated_at)
            -> Optional[str]   # mentor_id who taught them
        .apprentices_of(mentor_id) -> list[Apprenticeship]
        .mentor_of(apprentice_id) -> Optional[str]
        .graduates_taught(mentor_id) -> int
        .open_slots(mentor_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gearswap_publisher import GearswapPublisher


_APPRENTICE_CAP = 5


class ApprenticeStatus(str, enum.Enum):
    ACTIVE = "active"
    GRADUATED = "graduated"
    QUIT = "quit"


@dataclasses.dataclass(frozen=True)
class Apprenticeship:
    mentor_id: str
    apprentice_id: str
    started_at: int
    ended_at: int                      # 0 if still active
    status: ApprenticeStatus
    reached_first_fame_tier: bool      # apprentice
                                       # crossed 10 adopters


@dataclasses.dataclass
class GearswapApprentice:
    _publisher: GearswapPublisher
    # apprentice_id -> Apprenticeship (one current per
    # apprentice; history is collapsed via list).
    _records: list[Apprenticeship] = dataclasses.field(
        default_factory=list,
    )

    def _active(
        self, *, apprentice_id: str,
    ) -> t.Optional[Apprenticeship]:
        for r in self._records:
            if (r.apprentice_id == apprentice_id
                    and r.status == ApprenticeStatus.ACTIVE):
                return r
        return None

    def _is_mentor(self, mentor_id: str) -> bool:
        return self._publisher._mentor_flags.get(
            mentor_id, False,
        )

    def accept(
        self, *, mentor_id: str, apprentice_id: str,
        started_at: int,
    ) -> bool:
        if not mentor_id or not apprentice_id:
            return False
        if mentor_id == apprentice_id:
            return False
        # Must be a mentor in good standing — the
        # publisher's mentor flag is the source of truth.
        # If the live ops team revokes mentor status,
        # the mentor cannot take on NEW apprentices but
        # existing ones stay (graceful — they don't get
        # abandoned mid-term).
        if not self._is_mentor(mentor_id):
            return False
        # Apprentice can't already have an active mentor
        if self._active(apprentice_id=apprentice_id):
            return False
        # Mentor capacity
        if self.open_slots(mentor_id=mentor_id) <= 0:
            return False
        self._records.append(Apprenticeship(
            mentor_id=mentor_id,
            apprentice_id=apprentice_id,
            started_at=started_at, ended_at=0,
            status=ApprenticeStatus.ACTIVE,
            reached_first_fame_tier=False,
        ))
        return True

    def release(
        self, *, mentor_id: str, apprentice_id: str,
        by_mentor: bool, ended_at: int = 0,
    ) -> bool:
        for i, r in enumerate(self._records):
            if (r.apprentice_id == apprentice_id
                    and r.mentor_id == mentor_id
                    and r.status == ApprenticeStatus.ACTIVE):
                # Set status: GRADUATED if mentor releases
                # (graduation = mentor signs off), QUIT
                # if the apprentice walks away.
                new_status = (
                    ApprenticeStatus.GRADUATED
                    if by_mentor
                    else ApprenticeStatus.QUIT
                )
                self._records[i] = dataclasses.replace(
                    r, status=new_status,
                    ended_at=ended_at,
                )
                return True
        return False

    def record_graduation(
        self, *, apprentice_id: str, graduated_at: int,
    ) -> t.Optional[str]:
        """Called when an apprentice's first lua crosses
        the 10-adopt fame tier. Promotes them out of
        active status (mentor gets the credit), returns
        the mentor's id for the controller to then notify
        + render on the mentor's dashboard."""
        for i, r in enumerate(self._records):
            if (r.apprentice_id == apprentice_id
                    and r.status == ApprenticeStatus.ACTIVE):
                self._records[i] = dataclasses.replace(
                    r, status=ApprenticeStatus.GRADUATED,
                    ended_at=graduated_at,
                    reached_first_fame_tier=True,
                )
                return r.mentor_id
        return None

    def apprentices_of(
        self, *, mentor_id: str,
    ) -> list[Apprenticeship]:
        return [
            r for r in self._records
            if r.mentor_id == mentor_id
            and r.status == ApprenticeStatus.ACTIVE
        ]

    def mentor_of(
        self, *, apprentice_id: str,
    ) -> t.Optional[str]:
        cur = self._active(apprentice_id=apprentice_id)
        return cur.mentor_id if cur else None

    def graduates_taught(
        self, *, mentor_id: str,
    ) -> int:
        return sum(
            1 for r in self._records
            if r.mentor_id == mentor_id
            and r.status == ApprenticeStatus.GRADUATED
            and r.reached_first_fame_tier
        )

    def open_slots(self, *, mentor_id: str) -> int:
        used = len(self.apprentices_of(mentor_id=mentor_id))
        return max(0, _APPRENTICE_CAP - used)

    def total_active(self) -> int:
        return sum(
            1 for r in self._records
            if r.status == ApprenticeStatus.ACTIVE
        )


__all__ = [
    "ApprenticeStatus", "Apprenticeship",
    "GearswapApprentice",
]
