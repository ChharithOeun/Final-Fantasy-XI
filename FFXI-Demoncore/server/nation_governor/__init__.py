"""Nation governor — head-of-state with term-limited reign.

Each nation (Bastok, San d'Oria, Windurst, plus the
beastman cities) has a GOVERNOR — the in-fiction
authority who signs treaties, passes edicts, sets
tax rates, and pardons prisoners. The governor's
position is FILLED via nation_election (or by initial
appointment for new nations) and held for a fixed term.

A governor's term has a definite end: the term_end_day.
nation_election.start() should be called in the lead-up
to that date; whoever wins is INSTALLED on term_end_day,
displacing the incumbent into HISTORICAL state.

State machine:
    APPOINTED      seated by founding decree (no
                   election required)
    ELECTED        seated by election win
    SUSPENDED      removed temporarily (scandal/
                   illness); may be RESTORED or
                   DEPOSED
    DEPOSED        removed permanently before term end
    HISTORICAL     term completed; archived

Public surface
--------------
    GovernorState enum
    GovernorRecord dataclass (frozen)
    NationGovernorSystem
        .install_appointed(nation_id, governor_id,
                           term_days, now_day) ->
                           Optional[str]
        .install_elected(nation_id, governor_id,
                         term_days, now_day) ->
                         Optional[str]
        .suspend(record_id, now_day, reason) -> bool
        .restore(record_id, now_day) -> bool
        .depose(record_id, now_day, reason) -> bool
        .tick(now_day) -> list[(record_id,
                                GovernorState)]
        .current(nation_id) -> Optional[GovernorRecord]
        .history(nation_id) -> list[GovernorRecord]
        .term_remaining(nation_id, now_day) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GovernorState(str, enum.Enum):
    APPOINTED = "appointed"
    ELECTED = "elected"
    SUSPENDED = "suspended"
    DEPOSED = "deposed"
    HISTORICAL = "historical"


@dataclasses.dataclass(frozen=True)
class GovernorRecord:
    record_id: str
    nation_id: str
    governor_id: str
    installed_day: int
    term_end_day: int
    by_election: bool
    state: GovernorState
    suspended_reason: str
    deposed_reason: str
    archived_day: t.Optional[int]


@dataclasses.dataclass
class NationGovernorSystem:
    _records: dict[str, GovernorRecord] = (
        dataclasses.field(default_factory=dict)
    )
    _current: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    _history: dict[str, list[str]] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def _install(
        self, *, nation_id: str, governor_id: str,
        term_days: int, now_day: int,
        by_election: bool,
    ) -> t.Optional[str]:
        if not nation_id or not governor_id:
            return None
        if term_days <= 0 or now_day < 0:
            return None
        if nation_id in self._current:
            return None
        rid = f"gov_{self._next_id}"
        self._next_id += 1
        state = (
            GovernorState.ELECTED
            if by_election
            else GovernorState.APPOINTED
        )
        self._records[rid] = GovernorRecord(
            record_id=rid, nation_id=nation_id,
            governor_id=governor_id,
            installed_day=now_day,
            term_end_day=now_day + term_days,
            by_election=by_election, state=state,
            suspended_reason="", deposed_reason="",
            archived_day=None,
        )
        self._current[nation_id] = rid
        self._history.setdefault(
            nation_id, [],
        ).append(rid)
        return rid

    def install_appointed(
        self, *, nation_id: str, governor_id: str,
        term_days: int, now_day: int,
    ) -> t.Optional[str]:
        return self._install(
            nation_id=nation_id,
            governor_id=governor_id,
            term_days=term_days, now_day=now_day,
            by_election=False,
        )

    def install_elected(
        self, *, nation_id: str, governor_id: str,
        term_days: int, now_day: int,
    ) -> t.Optional[str]:
        return self._install(
            nation_id=nation_id,
            governor_id=governor_id,
            term_days=term_days, now_day=now_day,
            by_election=True,
        )

    def suspend(
        self, *, record_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state not in (
            GovernorState.APPOINTED,
            GovernorState.ELECTED,
        ):
            return False
        if not reason:
            return False
        self._records[record_id] = dataclasses.replace(
            r, state=GovernorState.SUSPENDED,
            suspended_reason=reason,
        )
        return True

    def restore(
        self, *, record_id: str, now_day: int,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state != GovernorState.SUSPENDED:
            return False
        prior = (
            GovernorState.ELECTED
            if r.by_election
            else GovernorState.APPOINTED
        )
        self._records[record_id] = dataclasses.replace(
            r, state=prior,
        )
        return True

    def depose(
        self, *, record_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if record_id not in self._records:
            return False
        r = self._records[record_id]
        if r.state in (
            GovernorState.DEPOSED,
            GovernorState.HISTORICAL,
        ):
            return False
        if not reason:
            return False
        self._records[record_id] = dataclasses.replace(
            r, state=GovernorState.DEPOSED,
            deposed_reason=reason,
            archived_day=now_day,
        )
        if (self._current.get(r.nation_id)
                == record_id):
            self._current.pop(r.nation_id)
        return True

    def tick(
        self, *, now_day: int,
    ) -> list[tuple[str, GovernorState]]:
        changes: list[tuple[str, GovernorState]] = []
        for rid, r in list(self._records.items()):
            if r.state in (
                GovernorState.DEPOSED,
                GovernorState.HISTORICAL,
            ):
                continue
            if now_day < r.term_end_day:
                continue
            self._records[rid] = dataclasses.replace(
                r, state=GovernorState.HISTORICAL,
                archived_day=now_day,
            )
            if (self._current.get(r.nation_id)
                    == rid):
                self._current.pop(r.nation_id)
            changes.append(
                (rid, GovernorState.HISTORICAL),
            )
        return changes

    def current(
        self, *, nation_id: str,
    ) -> t.Optional[GovernorRecord]:
        rid = self._current.get(nation_id)
        if rid is None:
            return None
        return self._records[rid]

    def history(
        self, *, nation_id: str,
    ) -> list[GovernorRecord]:
        return [
            self._records[rid]
            for rid in self._history.get(nation_id, ())
        ]

    def term_remaining(
        self, *, nation_id: str, now_day: int,
    ) -> int:
        cur = self.current(nation_id=nation_id)
        if cur is None:
            return 0
        return max(0, cur.term_end_day - now_day)


__all__ = [
    "GovernorState", "GovernorRecord",
    "NationGovernorSystem",
]
