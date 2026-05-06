"""Cartographer guild — players submit maps, earn ranks.

The Wayfarer's Hall in Lower Jeuno is the central guild
office. Walk in, submit a fully-explored zone map, and the
master cartographer pays you and bumps your rank. Higher
ranks unlock map-related rewards: blank parchment supplies,
sextant key items, the "Wayfarer" hereditary title, and
eventually access to the rumored archive of unmapped
zones.

Rank ladder (cumulative submissions):
    APPRENTICE    0-2     blank
    JOURNEYMAN    3-9     +5 base item slot
    EXPERT        10-24   +10% gil from map sales
    MASTER        25-49   commissions to map specific zones
    GRANDMASTER   50+     access to the lost-zone archive

Each submission has a quality factor 0-100 (auto-derived
from map_discovery completion percentage). Quality below
50 is rejected — half-mapped scribbles don't count.

Public surface
--------------
    GuildRank enum
    MapSubmission dataclass (frozen)
    SubmissionOutcome dataclass (frozen)
    CartographerGuild
        .submit_map(player_id, zone_id, quality_pct,
                    submitted_at) -> SubmissionOutcome
        .rank_for(player_id) -> GuildRank
        .submission_count(player_id) -> int
        .total_paid_to(player_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class GuildRank(str, enum.Enum):
    APPRENTICE = "apprentice"
    JOURNEYMAN = "journeyman"
    EXPERT = "expert"
    MASTER = "master"
    GRANDMASTER = "grandmaster"


_MIN_QUALITY = 50
_BASE_REWARD = 1000
_RANK_THRESHOLDS = (
    (3, GuildRank.JOURNEYMAN),
    (10, GuildRank.EXPERT),
    (25, GuildRank.MASTER),
    (50, GuildRank.GRANDMASTER),
)


@dataclasses.dataclass(frozen=True)
class MapSubmission:
    submission_id: str
    player_id: str
    zone_id: str
    quality_pct: int
    submitted_at: int
    payout: int
    rank_at_submission: GuildRank


@dataclasses.dataclass(frozen=True)
class SubmissionOutcome:
    accepted: bool
    payout: int
    new_rank: GuildRank
    promoted: bool
    reason: str = ""


def _rank_for_count(n: int) -> GuildRank:
    rank = GuildRank.APPRENTICE
    for threshold, r in _RANK_THRESHOLDS:
        if n >= threshold:
            rank = r
    return rank


@dataclasses.dataclass
class CartographerGuild:
    _submissions: list[MapSubmission] = dataclasses.field(
        default_factory=list,
    )
    _next_id: int = 0
    # (player_id, zone_id) -> True means already submitted
    _already_submitted: set[tuple[str, str]] = dataclasses.field(
        default_factory=set,
    )
    _by_player: dict[str, list[int]] = dataclasses.field(
        default_factory=dict,
    )
    _paid_to: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def submit_map(
        self, *, player_id: str, zone_id: str,
        quality_pct: int, submitted_at: int,
    ) -> SubmissionOutcome:
        if not player_id or not zone_id:
            return SubmissionOutcome(
                accepted=False, payout=0,
                new_rank=GuildRank.APPRENTICE,
                promoted=False, reason="invalid input",
            )
        if quality_pct < _MIN_QUALITY:
            return SubmissionOutcome(
                accepted=False, payout=0,
                new_rank=self.rank_for(player_id=player_id),
                promoted=False,
                reason="quality below 50%",
            )
        if (player_id, zone_id) in self._already_submitted:
            return SubmissionOutcome(
                accepted=False, payout=0,
                new_rank=self.rank_for(player_id=player_id),
                promoted=False,
                reason="already submitted this zone",
            )
        # compute payout
        prior_rank = self.rank_for(player_id=player_id)
        payout = _BASE_REWARD * quality_pct // 100
        if prior_rank == GuildRank.EXPERT:
            payout = payout * 110 // 100
        elif prior_rank in (
            GuildRank.MASTER, GuildRank.GRANDMASTER,
        ):
            payout = payout * 120 // 100

        self._next_id += 1
        sid = f"sub_{self._next_id}"
        sub = MapSubmission(
            submission_id=sid,
            player_id=player_id, zone_id=zone_id,
            quality_pct=quality_pct,
            submitted_at=submitted_at, payout=payout,
            rank_at_submission=prior_rank,
        )
        idx = len(self._submissions)
        self._submissions.append(sub)
        self._already_submitted.add((player_id, zone_id))
        self._by_player.setdefault(player_id, []).append(idx)
        self._paid_to[player_id] = (
            self._paid_to.get(player_id, 0) + payout
        )
        new_rank = self.rank_for(player_id=player_id)
        promoted = new_rank != prior_rank
        return SubmissionOutcome(
            accepted=True, payout=payout,
            new_rank=new_rank, promoted=promoted,
        )

    def rank_for(self, *, player_id: str) -> GuildRank:
        n = len(self._by_player.get(player_id, []))
        return _rank_for_count(n)

    def submission_count(self, *, player_id: str) -> int:
        return len(self._by_player.get(player_id, []))

    def total_paid_to(self, *, player_id: str) -> int:
        return self._paid_to.get(player_id, 0)


__all__ = [
    "GuildRank", "MapSubmission", "SubmissionOutcome",
    "CartographerGuild",
]
