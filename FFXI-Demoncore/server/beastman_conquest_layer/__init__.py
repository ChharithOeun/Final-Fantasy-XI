"""Beastman conquest layer — beastman-side conquest tally.

Mirrors the canon conquest_tally for the four beastman races.
Per-race totals tick up when a beastman player kills a hume
nation soldier (or vice versa flips the canon-side hostility).

Cross-faction influence: certain RIVAL race pairings convert
some of the kill into the rival's positive tally (a Yagudo
defeating a hume Sandorian also raises Quadav prestige
slightly, since both are Bastok rivals).

The tally produces a per-week RANKING that determines who
controls a region in the world.

Public surface
--------------
    BeastmanCanonRivalry enum (purely for cross-faction map)
    ContributionEvent dataclass
    TallyStanding dataclass
    BeastmanConquestLayer
        .record_kill(killer_race, victim_nation, points)
        .record_objective(race, points, label)
        .standings_for_week(week_index) -> tuple[TallyStanding]
        .leader_for_week(week_index) -> Optional[BeastmanRace]
        .reset_week(week_index)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


# Cross-faction conversion percentage — when a beastman race
# scores against a hume nation, allied beastman races get a
# small share (encourages co-belligerent dynamics).
_CROSS_SHARE_PCT = 20


# Map of which beastman race is "ally-of-convenience" against
# which hume nation.  These pairings mirror retail FFXI tribal
# overlap (Yagudos vs Windurst etc).
_NATION_ENEMIES: dict[
    str, tuple[BeastmanRace, ...],
] = {
    "san_doria": (BeastmanRace.ORC,),
    "bastok": (BeastmanRace.QUADAV,),
    "windurst": (BeastmanRace.YAGUDO,),
    "aht_urhgan": (BeastmanRace.LAMIA,),
}


_ALLY_PAIRINGS: dict[
    BeastmanRace, tuple[BeastmanRace, ...],
] = {
    BeastmanRace.ORC: (BeastmanRace.QUADAV,),
    BeastmanRace.QUADAV: (BeastmanRace.ORC,),
    BeastmanRace.YAGUDO: (BeastmanRace.LAMIA,),
    BeastmanRace.LAMIA: (BeastmanRace.YAGUDO,),
}


@dataclasses.dataclass(frozen=True)
class ContributionEvent:
    week_index: int
    race: BeastmanRace
    points: int
    label: str = ""


@dataclasses.dataclass(frozen=True)
class TallyStanding:
    week_index: int
    race: BeastmanRace
    points: int
    rank: int


@dataclasses.dataclass
class BeastmanConquestLayer:
    cross_share_pct: int = _CROSS_SHARE_PCT
    # (week_index, race) -> total points
    _totals: dict[
        tuple[int, BeastmanRace], int,
    ] = dataclasses.field(default_factory=dict)

    def _add(
        self, week: int, race: BeastmanRace, pts: int,
    ) -> None:
        if pts <= 0:
            return
        key = (week, race)
        self._totals[key] = self._totals.get(key, 0) + pts

    def record_kill(
        self, *, week_index: int,
        killer_race: BeastmanRace,
        victim_nation: str,
        points: int,
    ) -> bool:
        if points <= 0:
            return False
        if not victim_nation:
            return False
        # Direct attribution to killer.
        self._add(week_index, killer_race, points)
        # Cross-faction conversion to allies.
        share = points * self.cross_share_pct // 100
        if share > 0:
            for ally in _ALLY_PAIRINGS.get(
                killer_race, (),
            ):
                self._add(week_index, ally, share)
        return True

    def record_objective(
        self, *, week_index: int,
        race: BeastmanRace,
        points: int, label: str = "",
    ) -> bool:
        if points <= 0:
            return False
        self._add(week_index, race, points)
        return True

    def points_for(
        self, *, week_index: int,
        race: BeastmanRace,
    ) -> int:
        return self._totals.get((week_index, race), 0)

    def standings_for_week(
        self, *, week_index: int,
    ) -> tuple[TallyStanding, ...]:
        rows: list[tuple[BeastmanRace, int]] = []
        for race in BeastmanRace:
            pts = self.points_for(
                week_index=week_index, race=race,
            )
            rows.append((race, pts))
        rows.sort(
            key=lambda r: (-r[1], r[0].value),
        )
        out: list[TallyStanding] = []
        for rank, (race, pts) in enumerate(
            rows, start=1,
        ):
            out.append(TallyStanding(
                week_index=week_index, race=race,
                points=pts, rank=rank,
            ))
        return tuple(out)

    def leader_for_week(
        self, *, week_index: int,
    ) -> t.Optional[BeastmanRace]:
        standings = self.standings_for_week(
            week_index=week_index,
        )
        # Tie or zero: no decisive leader
        if not standings:
            return None
        leader = standings[0]
        if leader.points <= 0:
            return None
        if (
            len(standings) > 1
            and standings[1].points == leader.points
        ):
            return None      # tied
        return leader.race

    def reset_week(
        self, *, week_index: int,
    ) -> int:
        cleared = 0
        for key in list(self._totals.keys()):
            if key[0] == week_index:
                del self._totals[key]
                cleared += 1
        return cleared

    def total_entries(self) -> int:
        return len(self._totals)


__all__ = [
    "ContributionEvent", "TallyStanding",
    "BeastmanConquestLayer",
]
