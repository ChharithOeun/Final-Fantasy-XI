"""Chronicle publication — periodic published volumes.

Beyond the raw server_chronicle (server's memory), the
world has PUBLISHERS — NPC scribes who curate chronicle
entries into bound VOLUMES sold periodically. The
"Vana'diel Chronicle" releases a new edition each game-
month; the "Tenshodo Tribune" weekly. Players buy a
copy, take it home, and read it like an in-game
newspaper.

A Volume is a curated selection of ChronicleEntry IDs
plus an editorial headline + cover_image_id. Different
publishers pick different angles — the Bastok edition
emphasizes Bastok victories, the Sandy edition leads
with Cathedral news.

Per-volume:
    publisher_id, title, edition_number, release_day,
    front_page_headline, included_entry_ids,
    price_gil, copies_sold

Volumes are PUBLIC RECORD — once released, they cannot
be edited (unlike a forum post). They become part of
the world's printed history and can be re-bought from
publisher archives forever.

Public surface
--------------
    Publisher dataclass (frozen)
    Volume dataclass (frozen)
    PurchaseRecord dataclass (frozen)
    ChroniclePublication
        .register_publisher(publisher) -> bool
        .publish_volume(publisher_id, title, edition,
                        headline, entry_ids, price,
                        release_day) -> Optional[str]
        .buy(player_id, volume_id) -> bool
        .volume(volume_id) -> Optional[Volume]
        .volumes_by_publisher(publisher_id) -> list[Volume]
        .total_sold(volume_id) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class Publisher:
    publisher_id: str
    name: str
    nation: str
    cadence_days: int  # nominal release cadence


@dataclasses.dataclass(frozen=True)
class Volume:
    volume_id: str
    publisher_id: str
    title: str
    edition_number: int
    front_page_headline: str
    included_entry_ids: tuple[str, ...]
    price_gil: int
    release_day: int


@dataclasses.dataclass(frozen=True)
class PurchaseRecord:
    volume_id: str
    player_id: str
    bought_day: int


@dataclasses.dataclass
class _VState:
    spec: Volume
    purchases: list[PurchaseRecord] = dataclasses.field(
        default_factory=list,
    )


@dataclasses.dataclass
class ChroniclePublication:
    _publishers: dict[str, Publisher] = dataclasses.field(
        default_factory=dict,
    )
    _volumes: dict[str, _VState] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 1

    def register_publisher(
        self, publisher: Publisher,
    ) -> bool:
        if not publisher.publisher_id:
            return False
        if not publisher.name or not publisher.nation:
            return False
        if publisher.cadence_days <= 0:
            return False
        if publisher.publisher_id in self._publishers:
            return False
        self._publishers[publisher.publisher_id] = publisher
        return True

    def publish_volume(
        self, *, publisher_id: str, title: str,
        edition_number: int, front_page_headline: str,
        included_entry_ids: t.Sequence[str],
        price_gil: int, release_day: int,
    ) -> t.Optional[str]:
        if publisher_id not in self._publishers:
            return None
        if not title or not front_page_headline:
            return None
        if edition_number <= 0:
            return None
        if not included_entry_ids:
            return None
        if price_gil < 0:
            return None
        if release_day < 0:
            return None
        # No two volumes from the same publisher with same
        # edition number
        for st in self._volumes.values():
            if (st.spec.publisher_id == publisher_id
                    and st.spec.edition_number
                    == edition_number):
                return None
        volume_id = f"vol_{self._next_id}"
        self._next_id += 1
        v = Volume(
            volume_id=volume_id,
            publisher_id=publisher_id,
            title=title,
            edition_number=edition_number,
            front_page_headline=front_page_headline,
            included_entry_ids=tuple(included_entry_ids),
            price_gil=price_gil,
            release_day=release_day,
        )
        self._volumes[volume_id] = _VState(spec=v)
        return volume_id

    def buy(
        self, *, player_id: str, volume_id: str,
        bought_day: int,
    ) -> bool:
        if not player_id:
            return False
        if volume_id not in self._volumes:
            return False
        if bought_day < 0:
            return False
        st = self._volumes[volume_id]
        if bought_day < st.spec.release_day:
            return False
        st.purchases.append(PurchaseRecord(
            volume_id=volume_id, player_id=player_id,
            bought_day=bought_day,
        ))
        return True

    def volume(
        self, *, volume_id: str,
    ) -> t.Optional[Volume]:
        if volume_id not in self._volumes:
            return None
        return self._volumes[volume_id].spec

    def volumes_by_publisher(
        self, *, publisher_id: str,
    ) -> list[Volume]:
        return sorted(
            (st.spec for st in self._volumes.values()
             if st.spec.publisher_id == publisher_id),
            key=lambda v: v.edition_number,
        )

    def total_sold(
        self, *, volume_id: str,
    ) -> int:
        if volume_id not in self._volumes:
            return 0
        return len(self._volumes[volume_id].purchases)

    def buyers_of(
        self, *, volume_id: str,
    ) -> list[str]:
        if volume_id not in self._volumes:
            return []
        return sorted({
            p.player_id
            for p in self._volumes[volume_id].purchases
        })


__all__ = [
    "Publisher", "Volume", "PurchaseRecord",
    "ChroniclePublication",
]
