"""Player classifieds board — wants, offers, services, trades.

A player operator runs a classifieds board (a noticeboard
in town). Posters pay a listing fee at posting time; their
listing displays under one of four kinds — WANT (looking
to buy), OFFER (selling), SERVICE (offering a craft or
escort), or TRADE (swap). Listings expire on a fixed day,
or the poster can mark them RESOLVED early (gets a 50%
prorated refund of unused life) or CANCELED (no refund —
penalty for clutter). The operator collects all retained
fees as the board's revenue.

Lifecycle (listing)
    ACTIVE        live on the board
    EXPIRED       past expiry day
    RESOLVED      poster marked done
    CANCELED      poster pulled it (no refund)

Public surface
--------------
    ListingKind enum
    ListingState enum
    ClassifiedsBoard dataclass (frozen)
    Listing dataclass (frozen)
    PlayerClassifiedsBoardSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ListingKind(str, enum.Enum):
    WANT = "want"
    OFFER = "offer"
    SERVICE = "service"
    TRADE = "trade"


class ListingState(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RESOLVED = "resolved"
    CANCELED = "canceled"


@dataclasses.dataclass(frozen=True)
class ClassifiedsBoard:
    board_id: str
    operator_id: str
    name: str
    revenue_gil: int


@dataclasses.dataclass(frozen=True)
class Listing:
    listing_id: str
    board_id: str
    poster_id: str
    kind: ListingKind
    headline: str
    body: str
    listing_fee_gil: int
    post_day: int
    expiry_day: int
    state: ListingState


@dataclasses.dataclass
class _BState:
    spec: ClassifiedsBoard
    listings: dict[str, Listing] = dataclasses.field(
        default_factory=dict,
    )


@dataclasses.dataclass
class PlayerClassifiedsBoardSystem:
    _boards: dict[str, _BState] = dataclasses.field(
        default_factory=dict,
    )
    _next_board: int = 1
    _next_listing: int = 1

    def found_board(
        self, *, operator_id: str, name: str,
    ) -> t.Optional[str]:
        if not operator_id or not name:
            return None
        bid = f"board_{self._next_board}"
        self._next_board += 1
        self._boards[bid] = _BState(
            spec=ClassifiedsBoard(
                board_id=bid, operator_id=operator_id,
                name=name, revenue_gil=0,
            ),
        )
        return bid

    def post_listing(
        self, *, board_id: str, poster_id: str,
        kind: ListingKind, headline: str, body: str,
        listing_fee_gil: int, post_day: int,
        expiry_day: int,
    ) -> t.Optional[str]:
        if board_id not in self._boards:
            return None
        st = self._boards[board_id]
        if not poster_id or not headline:
            return None
        if listing_fee_gil <= 0:
            return None
        if expiry_day <= post_day:
            return None
        lid = f"listing_{self._next_listing}"
        self._next_listing += 1
        st.listings[lid] = Listing(
            listing_id=lid, board_id=board_id,
            poster_id=poster_id, kind=kind,
            headline=headline, body=body,
            listing_fee_gil=listing_fee_gil,
            post_day=post_day,
            expiry_day=expiry_day,
            state=ListingState.ACTIVE,
        )
        # Operator collects the listing fee up front;
        # half of it is retained against the listing
        # for possible early-resolve refund.
        st.spec = dataclasses.replace(
            st.spec,
            revenue_gil=(
                st.spec.revenue_gil + listing_fee_gil
            ),
        )
        return lid

    def expire_listings(
        self, *, board_id: str, current_day: int,
    ) -> int:
        """Returns the number of listings transitioned
        to EXPIRED."""
        if board_id not in self._boards:
            return 0
        st = self._boards[board_id]
        moved = 0
        for lid, lst in list(st.listings.items()):
            if (
                lst.state == ListingState.ACTIVE
                and current_day >= lst.expiry_day
            ):
                st.listings[lid] = dataclasses.replace(
                    lst, state=ListingState.EXPIRED,
                )
                moved += 1
        return moved

    def mark_resolved(
        self, *, board_id: str, listing_id: str,
        poster_id: str, current_day: int,
    ) -> t.Optional[int]:
        """Mark resolved early. Returns the prorated
        refund (50% of fee scaled by remaining life).
        Returns None on failure."""
        if board_id not in self._boards:
            return None
        st = self._boards[board_id]
        if listing_id not in st.listings:
            return None
        lst = st.listings[listing_id]
        if lst.state != ListingState.ACTIVE:
            return None
        if lst.poster_id != poster_id:
            return None
        if current_day >= lst.expiry_day:
            # past expiry — should have been EXPIRED,
            # but guard anyway
            return None
        total_life = lst.expiry_day - lst.post_day
        remaining = lst.expiry_day - current_day
        # Half of the prorated remaining-fee
        refund = (
            lst.listing_fee_gil
            * remaining
            // (2 * total_life)
        )
        st.listings[listing_id] = dataclasses.replace(
            lst, state=ListingState.RESOLVED,
        )
        st.spec = dataclasses.replace(
            st.spec,
            revenue_gil=st.spec.revenue_gil - refund,
        )
        return refund

    def cancel_listing(
        self, *, board_id: str, listing_id: str,
        poster_id: str,
    ) -> bool:
        """Pull a listing without refund."""
        if board_id not in self._boards:
            return False
        st = self._boards[board_id]
        if listing_id not in st.listings:
            return False
        lst = st.listings[listing_id]
        if lst.state != ListingState.ACTIVE:
            return False
        if lst.poster_id != poster_id:
            return False
        st.listings[listing_id] = dataclasses.replace(
            lst, state=ListingState.CANCELED,
        )
        return True

    def board(
        self, *, board_id: str,
    ) -> t.Optional[ClassifiedsBoard]:
        st = self._boards.get(board_id)
        return st.spec if st else None

    def listing(
        self, *, board_id: str, listing_id: str,
    ) -> t.Optional[Listing]:
        st = self._boards.get(board_id)
        if st is None:
            return None
        return st.listings.get(listing_id)

    def listings_by_kind(
        self, *, board_id: str, kind: ListingKind,
    ) -> list[Listing]:
        st = self._boards.get(board_id)
        if st is None:
            return []
        return [
            l for l in st.listings.values()
            if l.kind == kind
        ]

    def listings_by_poster(
        self, *, board_id: str, poster_id: str,
    ) -> list[Listing]:
        st = self._boards.get(board_id)
        if st is None:
            return []
        return [
            l for l in st.listings.values()
            if l.poster_id == poster_id
        ]

    def active_listings(
        self, *, board_id: str,
    ) -> list[Listing]:
        st = self._boards.get(board_id)
        if st is None:
            return []
        return [
            l for l in st.listings.values()
            if l.state == ListingState.ACTIVE
        ]


__all__ = [
    "ListingKind", "ListingState",
    "ClassifiedsBoard", "Listing",
    "PlayerClassifiedsBoardSystem",
]
