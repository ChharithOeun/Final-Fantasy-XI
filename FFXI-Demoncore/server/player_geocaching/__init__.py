"""Player geocaching — hide and find caches across zones.

Players hide caches at zone coordinates with cryptic clues.
Other players hunt by guessing coordinates from the clue
text; finds within tolerance log a successful discovery.
Each cache tracks its find_count; popular caches build
fame for their hiders. Caches can be retired to reclaim
the placement slot.

Public surface
--------------
    CacheState enum
    Cache dataclass (frozen)
    Find dataclass (frozen)
    PlayerGeocachingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_FIND_TOLERANCE = 5    # coords within +/- 5 count


class CacheState(str, enum.Enum):
    HIDDEN = "hidden"
    RETIRED = "retired"


@dataclasses.dataclass(frozen=True)
class Cache:
    cache_id: str
    hider_id: str
    zone_id: str
    coord_x: int
    coord_y: int
    clue: str
    state: CacheState
    find_count: int


@dataclasses.dataclass(frozen=True)
class Find:
    find_id: str
    cache_id: str
    finder_id: str
    found_day: int


@dataclasses.dataclass
class _CState:
    spec: Cache
    finders: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerGeocachingSystem:
    _caches: dict[str, _CState] = dataclasses.field(
        default_factory=dict,
    )
    _finds: dict[str, Find] = dataclasses.field(
        default_factory=dict,
    )
    _next_cache: int = 1
    _next_find: int = 1

    def hide_cache(
        self, *, hider_id: str, zone_id: str,
        coord_x: int, coord_y: int, clue: str,
    ) -> t.Optional[str]:
        if not hider_id or not zone_id:
            return None
        if not clue:
            return None
        if not 0 <= coord_x < 1000:
            return None
        if not 0 <= coord_y < 1000:
            return None
        cid = f"cache_{self._next_cache}"
        self._next_cache += 1
        self._caches[cid] = _CState(
            spec=Cache(
                cache_id=cid, hider_id=hider_id,
                zone_id=zone_id, coord_x=coord_x,
                coord_y=coord_y, clue=clue,
                state=CacheState.HIDDEN, find_count=0,
            ),
        )
        return cid

    def attempt_find(
        self, *, cache_id: str, finder_id: str,
        guess_x: int, guess_y: int, found_day: int,
    ) -> t.Optional[str]:
        """Returns find_id if guess is within
        tolerance, None otherwise. Hider can't find
        their own cache; one find per finder per
        cache.
        """
        if cache_id not in self._caches:
            return None
        st = self._caches[cache_id]
        if st.spec.state != CacheState.HIDDEN:
            return None
        if not finder_id:
            return None
        if finder_id == st.spec.hider_id:
            return None
        if finder_id in st.finders:
            return None
        if found_day < 0:
            return None
        if abs(guess_x - st.spec.coord_x) > _FIND_TOLERANCE:
            return None
        if abs(guess_y - st.spec.coord_y) > _FIND_TOLERANCE:
            return None
        fid = f"find_{self._next_find}"
        self._next_find += 1
        self._finds[fid] = Find(
            find_id=fid, cache_id=cache_id,
            finder_id=finder_id, found_day=found_day,
        )
        st.finders.add(finder_id)
        st.spec = dataclasses.replace(
            st.spec, find_count=st.spec.find_count + 1,
        )
        return fid

    def retire(
        self, *, cache_id: str, hider_id: str,
    ) -> bool:
        """Only the hider can retire."""
        if cache_id not in self._caches:
            return False
        st = self._caches[cache_id]
        if st.spec.state != CacheState.HIDDEN:
            return False
        if st.spec.hider_id != hider_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=CacheState.RETIRED,
        )
        return True

    def hider_fame(
        self, *, hider_id: str,
    ) -> int:
        """Sum of find_counts across all this hider's
        caches."""
        return sum(
            st.spec.find_count
            for st in self._caches.values()
            if st.spec.hider_id == hider_id
        )

    def finder_count(
        self, *, finder_id: str,
    ) -> int:
        return sum(
            1 for f in self._finds.values()
            if f.finder_id == finder_id
        )

    def cache(
        self, *, cache_id: str,
    ) -> t.Optional[Cache]:
        st = self._caches.get(cache_id)
        return st.spec if st else None

    def find(
        self, *, find_id: str,
    ) -> t.Optional[Find]:
        return self._finds.get(find_id)

    def caches_in_zone(
        self, *, zone_id: str,
    ) -> list[Cache]:
        return [
            st.spec for st in self._caches.values()
            if (st.spec.zone_id == zone_id
                and st.spec.state == CacheState.HIDDEN)
        ]


__all__ = [
    "CacheState", "Cache", "Find",
    "PlayerGeocachingSystem",
]
