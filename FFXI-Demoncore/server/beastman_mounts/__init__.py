"""Beastman mounts — race-specific traversal beasts.

Beastmen don't ride chocobos — Vana'diel's chocobo guilds
don't sell to them. Each race tames its own beast:

  Orc:    IRON BOAR        ground; charges through obstacles
  Lamia:  COILER           water-capable; lateral slither
  Yagudo: WING_STRIDER     short-glide leaps; not true flight
  Quadav: STONE_TREADER    extreme load capacity; slow

Each mount carries:
* base_speed_pct (vs running speed)
* terrain affinity (which terrain types it gets a speed bonus
  in)
* special trait (charge / slither / glide / load)

Mounts are summoned via tame items, ridden, dismissed. They
don't share Mount HP with the canon mount system — beastman
mounts use a tougher pool that doesn't permadeath as easily as
the chocobo-derived class did.

Public surface
--------------
    MountKind enum
    TerrainAffinity enum
    SpecialTrait enum
    MountProfile dataclass
    BeastmanMounts
        .acquire(player_id, race, mount_kind)
        .can_ride(player_id, race, mount_kind)
        .summon(player_id, race, mount_kind, terrain) -> Optional[speed_pct]
        .dismiss(player_id)
        .profile_for(mount_kind)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class MountKind(str, enum.Enum):
    IRON_BOAR = "iron_boar"
    COILER = "coiler"
    WING_STRIDER = "wing_strider"
    STONE_TREADER = "stone_treader"


class TerrainAffinity(str, enum.Enum):
    PLAINS = "plains"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    SHALLOW_WATER = "shallow_water"
    DESERT = "desert"
    SWAMP = "swamp"
    RUINS = "ruins"


class SpecialTrait(str, enum.Enum):
    CHARGE = "charge"
    SLITHER = "slither"
    GLIDE = "glide"
    LOAD = "load"


@dataclasses.dataclass(frozen=True)
class MountProfile:
    kind: MountKind
    race: BeastmanRace
    base_speed_pct: int
    affinities: tuple[TerrainAffinity, ...]
    affinity_bonus_pct: int
    special_trait: SpecialTrait
    label: str


_PROFILES: dict[MountKind, MountProfile] = {
    MountKind.IRON_BOAR: MountProfile(
        kind=MountKind.IRON_BOAR,
        race=BeastmanRace.ORC,
        base_speed_pct=140,
        affinities=(
            TerrainAffinity.FOREST,
            TerrainAffinity.PLAINS,
        ),
        affinity_bonus_pct=20,
        special_trait=SpecialTrait.CHARGE,
        label="Iron Boar",
    ),
    MountKind.COILER: MountProfile(
        kind=MountKind.COILER,
        race=BeastmanRace.LAMIA,
        base_speed_pct=130,
        affinities=(
            TerrainAffinity.SHALLOW_WATER,
            TerrainAffinity.SWAMP,
        ),
        affinity_bonus_pct=35,
        special_trait=SpecialTrait.SLITHER,
        label="Coiler",
    ),
    MountKind.WING_STRIDER: MountProfile(
        kind=MountKind.WING_STRIDER,
        race=BeastmanRace.YAGUDO,
        base_speed_pct=150,
        affinities=(
            TerrainAffinity.MOUNTAIN,
            TerrainAffinity.RUINS,
        ),
        affinity_bonus_pct=15,
        special_trait=SpecialTrait.GLIDE,
        label="Wing Strider",
    ),
    MountKind.STONE_TREADER: MountProfile(
        kind=MountKind.STONE_TREADER,
        race=BeastmanRace.QUADAV,
        base_speed_pct=110,
        affinities=(
            TerrainAffinity.MOUNTAIN,
            TerrainAffinity.DESERT,
        ),
        affinity_bonus_pct=15,
        special_trait=SpecialTrait.LOAD,
        label="Stone Treader",
    ),
}


@dataclasses.dataclass
class _PlayerMounts:
    player_id: str
    acquired: set[MountKind] = dataclasses.field(
        default_factory=set,
    )
    active_mount: t.Optional[MountKind] = None


@dataclasses.dataclass
class BeastmanMounts:
    _states: dict[str, _PlayerMounts] = dataclasses.field(
        default_factory=dict,
    )

    def profile_for(
        self, *, mount_kind: MountKind,
    ) -> MountProfile:
        return _PROFILES[mount_kind]

    def _state(self, player_id: str) -> _PlayerMounts:
        st = self._states.get(player_id)
        if st is None:
            st = _PlayerMounts(player_id=player_id)
            self._states[player_id] = st
        return st

    def acquire(
        self, *, player_id: str,
        race: BeastmanRace,
        mount_kind: MountKind,
    ) -> bool:
        prof = _PROFILES.get(mount_kind)
        if prof is None:
            return False
        if prof.race != race:
            return False
        st = self._state(player_id)
        if mount_kind in st.acquired:
            return False
        st.acquired.add(mount_kind)
        return True

    def can_ride(
        self, *, player_id: str,
        race: BeastmanRace,
        mount_kind: MountKind,
    ) -> bool:
        prof = _PROFILES.get(mount_kind)
        if prof is None:
            return False
        if prof.race != race:
            return False
        return mount_kind in self._state(player_id).acquired

    def summon(
        self, *, player_id: str,
        race: BeastmanRace,
        mount_kind: MountKind,
        terrain: t.Optional[TerrainAffinity] = None,
    ) -> t.Optional[int]:
        if not self.can_ride(
            player_id=player_id, race=race,
            mount_kind=mount_kind,
        ):
            return None
        prof = _PROFILES[mount_kind]
        speed = prof.base_speed_pct
        if (
            terrain is not None
            and terrain in prof.affinities
        ):
            speed += prof.affinity_bonus_pct
        st = self._state(player_id)
        st.active_mount = mount_kind
        return speed

    def active_mount(
        self, *, player_id: str,
    ) -> t.Optional[MountKind]:
        st = self._states.get(player_id)
        return st.active_mount if st else None

    def dismiss(
        self, *, player_id: str,
    ) -> bool:
        st = self._states.get(player_id)
        if st is None or st.active_mount is None:
            return False
        st.active_mount = None
        return True

    def acquired_for(
        self, *, player_id: str,
    ) -> tuple[MountKind, ...]:
        st = self._states.get(player_id)
        if st is None:
            return ()
        return tuple(sorted(
            st.acquired, key=lambda m: m.value,
        ))


__all__ = [
    "MountKind", "TerrainAffinity", "SpecialTrait",
    "MountProfile",
    "BeastmanMounts",
]
