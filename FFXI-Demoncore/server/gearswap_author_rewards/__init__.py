"""GearSwap author rewards — fame turned into in-game gil
and titles.

This is the chunk that makes "becoming famous" matter
mechanically. Publishing is a creative act and authors
deserve more than a leaderboard rank. As your luas pile
up adopters and upvotes, the system pays out:

    GIL    a one-time stipend per adoption-tier crossed
           (10 / 50 / 200 / 1000 / 5000 adopters)

    TITLE  a permanent title equipped from the title_system,
           one per fame tier reached:
              Mentor's Voice          (10)
              Heard in Whispers       (50)
              Spoken in Marketplaces  (200)
              Sung in Linkshells      (1000)
              Bard's Ballad Subject   (5000)

Tiers are checked per-publish (a single hit can carry
the whole fame). Each tier pays out exactly once per
publish_id; if Chharith's RDM lua hits 200 adopters and
he later UNLISTS it, the previously paid 10/50/200 gil
+ title rewards STAY (they were earned).

Negative net-thumbs caps the title at the previously
earned tier — you can't claim fame for a build the
community thinks is bad.

Public surface
--------------
    FameTier dataclass (frozen)  - tier table
    RewardEvent dataclass (frozen)
    GearswapAuthorRewards
        .check_publish(publish_id) -> list[RewardEvent]
            run after each adoption tick — pays new tiers,
            returns the events that fired.
        .total_gil_earned(author_id) -> int
        .titles_earned(author_id) -> list[str]
        .events_for(author_id) -> list[RewardEvent]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.gearswap_adopt import GearswapAdopt
from server.gearswap_publisher import GearswapPublisher
from server.gearswap_rating import GearswapRating


class _TierKind(str, enum.Enum):
    GIL = "gil"
    TITLE = "title"


@dataclasses.dataclass(frozen=True)
class FameTier:
    threshold: int
    gil_payout: int
    title: str


# Strict ascending; threshold is "adopters_count >="
_TIERS: tuple[FameTier, ...] = (
    FameTier(10,    1000,    "Mentor's Voice"),
    FameTier(50,    5000,    "Heard in Whispers"),
    FameTier(200,   25000,   "Spoken in Marketplaces"),
    FameTier(1000,  100000,  "Sung in Linkshells"),
    FameTier(5000,  500000,  "Bard's Ballad Subject"),
)


@dataclasses.dataclass(frozen=True)
class RewardEvent:
    author_id: str
    publish_id: str
    threshold: int
    gil_paid: int
    title_awarded: str


@dataclasses.dataclass
class GearswapAuthorRewards:
    _publisher: GearswapPublisher
    _adopt: GearswapAdopt
    _rating: GearswapRating
    # publish_id -> set[threshold] already paid
    _paid_per_publish: dict[
        str, set[int],
    ] = dataclasses.field(default_factory=dict)
    _events: list[RewardEvent] = dataclasses.field(
        default_factory=list,
    )

    def check_publish(
        self, *, publish_id: str,
    ) -> list[RewardEvent]:
        entry = self._publisher.lookup(publish_id=publish_id)
        if entry is None:
            return []
        # Net thumbs gate — a publish with net-negative
        # thumbs cannot earn NEW titles (gil already
        # paid stays).
        s = self._rating.summary(publish_id=publish_id)
        net = s.thumbs_up - s.thumbs_down
        adopters = self._adopt.adopters_count(
            publish_id=publish_id,
        )
        already = self._paid_per_publish.setdefault(
            publish_id, set(),
        )
        new_events: list[RewardEvent] = []
        for tier in _TIERS:
            if adopters < tier.threshold:
                break
            if tier.threshold in already:
                continue
            if net < 0:
                # Locked out by community rejection;
                # don't even mark as paid so it can be
                # earned later if the rating recovers.
                continue
            ev = RewardEvent(
                author_id=entry.author_id,
                publish_id=publish_id,
                threshold=tier.threshold,
                gil_paid=tier.gil_payout,
                title_awarded=tier.title,
            )
            already.add(tier.threshold)
            self._events.append(ev)
            new_events.append(ev)
        return new_events

    def total_gil_earned(self, *, author_id: str) -> int:
        return sum(
            ev.gil_paid for ev in self._events
            if ev.author_id == author_id
        )

    def titles_earned(
        self, *, author_id: str,
    ) -> list[str]:
        # de-dupe + ordered by ascending threshold
        seen: dict[str, int] = {}
        for ev in self._events:
            if ev.author_id != author_id:
                continue
            if ev.title_awarded not in seen \
                    or ev.threshold < seen[ev.title_awarded]:
                seen[ev.title_awarded] = ev.threshold
        out = sorted(seen.items(), key=lambda kv: kv[1])
        return [t for t, _ in out]

    def events_for(
        self, *, author_id: str,
    ) -> list[RewardEvent]:
        return [
            ev for ev in self._events
            if ev.author_id == author_id
        ]

    @staticmethod
    def fame_tiers() -> list[FameTier]:
        return list(_TIERS)


__all__ = [
    "FameTier", "RewardEvent", "GearswapAuthorRewards",
]
