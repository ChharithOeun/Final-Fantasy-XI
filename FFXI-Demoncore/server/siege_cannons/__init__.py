"""Siege cannons — player-crewed environment-damage tools.

Some big-fight arenas place cannons on the deck, the
parapet, or the battlement. A player can MAN one (single-
gunner crew of 1, or AIM/LOAD/FIRE three-role crew of 3
for bigger guns), aim it at a feature_id or boss, load
the appropriate ammunition (round-shot vs hull, chain-
shot vs masts, grape-shot vs adds, magic shells for
elemental damage), and fire after a reload window.

Cannons emit a DamageEvent (source=CANNON_VOLLEY) into
environment_damage. They can also fire at mobs/bosses,
emitting plain BOSS_DAMAGE events for the combat layer.

Public surface
--------------
    CannonSize enum
    AmmoKind enum
    CrewRole enum
    Cannon dataclass (mutable state)
    FireResult dataclass (frozen)
    SiegeCannons
        .register_cannon(cannon_id, size, arena_id, band)
        .assign_role(cannon_id, player_id, role) -> bool
        .leave_role(cannon_id, player_id) -> bool
        .load_ammo(cannon_id, ammo_kind, now) -> bool
        .aim(cannon_id, target_feature_id, target_mob_id, now)
        .fire(cannon_id, now) -> FireResult
        .can_fire(cannon_id, now) -> bool

Cannon sizes:
    LIGHT  - 1-crew, 12s reload, 800 dmg base
    MEDIUM - 2-crew (LOADER + GUNNER), 24s reload,
             2200 dmg base
    HEAVY  - 3-crew (LOADER + AIMER + GUNNER), 40s
             reload, 5000 dmg base
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CannonSize(str, enum.Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class AmmoKind(str, enum.Enum):
    ROUND_SHOT = "round_shot"        # baseline, hull-buster
    CHAIN_SHOT = "chain_shot"        # mast/pillar specialist
    GRAPE_SHOT = "grape_shot"        # anti-personnel
    FIRE_SHELL = "fire_shell"        # fire element
    ICE_SHELL = "ice_shell"          # ice element
    LIGHTNING_SHELL = "lightning_shell"  # lightning element


class CrewRole(str, enum.Enum):
    LOADER = "loader"
    AIMER = "aimer"
    GUNNER = "gunner"


# Per-size profile: required roles, reload seconds, base damage,
# ammo damage multiplier table.
@dataclasses.dataclass(frozen=True)
class _SizeProfile:
    required_roles: tuple[CrewRole, ...]
    reload_seconds: int
    base_damage: int


_SIZE_PROFILES: dict[CannonSize, _SizeProfile] = {
    CannonSize.LIGHT: _SizeProfile(
        required_roles=(CrewRole.GUNNER,),
        reload_seconds=12, base_damage=800,
    ),
    CannonSize.MEDIUM: _SizeProfile(
        required_roles=(CrewRole.LOADER, CrewRole.GUNNER),
        reload_seconds=24, base_damage=2200,
    ),
    CannonSize.HEAVY: _SizeProfile(
        required_roles=(CrewRole.LOADER, CrewRole.AIMER, CrewRole.GUNNER),
        reload_seconds=40, base_damage=5000,
    ),
}


# Per-ammo kind: which element + which target_kind tag is bonus
@dataclasses.dataclass(frozen=True)
class _AmmoProfile:
    element: str
    feature_kind_bonus_pct: dict[str, int]


_AMMO_PROFILES: dict[AmmoKind, _AmmoProfile] = {
    AmmoKind.ROUND_SHOT: _AmmoProfile(
        element="neutral",
        feature_kind_bonus_pct={"ship_hull": 50, "wall": 30},
    ),
    AmmoKind.CHAIN_SHOT: _AmmoProfile(
        element="neutral",
        feature_kind_bonus_pct={"pillar": 100, "bridge": 80},
    ),
    AmmoKind.GRAPE_SHOT: _AmmoProfile(
        element="neutral",
        feature_kind_bonus_pct={},   # primarily anti-mob
    ),
    AmmoKind.FIRE_SHELL: _AmmoProfile(
        element="fire",
        feature_kind_bonus_pct={"ice_sheet": 50},
    ),
    AmmoKind.ICE_SHELL: _AmmoProfile(
        element="ice",
        feature_kind_bonus_pct={},
    ),
    AmmoKind.LIGHTNING_SHELL: _AmmoProfile(
        element="lightning",
        feature_kind_bonus_pct={"dam": 60},
    ),
}


@dataclasses.dataclass
class Cannon:
    cannon_id: str
    size: CannonSize
    arena_id: str
    band: int
    crew: dict[CrewRole, str] = dataclasses.field(default_factory=dict)
    loaded_ammo: t.Optional[AmmoKind] = None
    last_fired_at: int = -10**9
    target_feature_id: t.Optional[str] = None
    target_mob_id: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class FireResult:
    accepted: bool
    cannon_id: str = ""
    target_feature_id: t.Optional[str] = None
    target_mob_id: t.Optional[str] = None
    damage: int = 0
    element: str = "neutral"
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SiegeCannons:
    _cannons: dict[str, Cannon] = dataclasses.field(default_factory=dict)

    def register_cannon(
        self, *, cannon_id: str, size: CannonSize,
        arena_id: str, band: int = 0,
    ) -> bool:
        if not cannon_id or not arena_id:
            return False
        if cannon_id in self._cannons:
            return False
        self._cannons[cannon_id] = Cannon(
            cannon_id=cannon_id, size=size,
            arena_id=arena_id, band=band,
        )
        return True

    def cannon(self, *, cannon_id: str) -> t.Optional[Cannon]:
        return self._cannons.get(cannon_id)

    def assign_role(
        self, *, cannon_id: str, player_id: str, role: CrewRole,
    ) -> bool:
        c = self._cannons.get(cannon_id)
        if c is None or not player_id:
            return False
        prof = _SIZE_PROFILES[c.size]
        if role not in prof.required_roles:
            return False
        if role in c.crew:
            return False
        # one player per role; one role per player on this cannon
        if player_id in c.crew.values():
            return False
        c.crew[role] = player_id
        return True

    def leave_role(
        self, *, cannon_id: str, player_id: str,
    ) -> bool:
        c = self._cannons.get(cannon_id)
        if c is None:
            return False
        for r, p in list(c.crew.items()):
            if p == player_id:
                del c.crew[r]
                return True
        return False

    def fully_crewed(self, *, cannon_id: str) -> bool:
        c = self._cannons.get(cannon_id)
        if c is None:
            return False
        prof = _SIZE_PROFILES[c.size]
        return all(r in c.crew for r in prof.required_roles)

    def load_ammo(
        self, *, cannon_id: str, ammo: AmmoKind, now_seconds: int,
    ) -> bool:
        c = self._cannons.get(cannon_id)
        if c is None:
            return False
        if not self.fully_crewed(cannon_id=cannon_id):
            return False
        if not self.can_fire(cannon_id=cannon_id, now_seconds=now_seconds):
            # still in reload — can't reload
            return False
        c.loaded_ammo = ammo
        return True

    def aim(
        self, *, cannon_id: str,
        target_feature_id: t.Optional[str] = None,
        target_mob_id: t.Optional[str] = None,
    ) -> bool:
        c = self._cannons.get(cannon_id)
        if c is None:
            return False
        if not target_feature_id and not target_mob_id:
            return False
        if target_feature_id and target_mob_id:
            return False   # one or the other
        c.target_feature_id = target_feature_id
        c.target_mob_id = target_mob_id
        return True

    def can_fire(
        self, *, cannon_id: str, now_seconds: int,
    ) -> bool:
        c = self._cannons.get(cannon_id)
        if c is None:
            return False
        prof = _SIZE_PROFILES[c.size]
        return (now_seconds - c.last_fired_at) >= prof.reload_seconds

    def fire(
        self, *, cannon_id: str, now_seconds: int,
        target_feature_kind: t.Optional[str] = None,
    ) -> FireResult:
        c = self._cannons.get(cannon_id)
        if c is None:
            return FireResult(False, reason="unknown cannon")
        if not self.fully_crewed(cannon_id=cannon_id):
            return FireResult(False, reason="not fully crewed")
        if c.loaded_ammo is None:
            return FireResult(False, reason="no ammo loaded")
        if not c.target_feature_id and not c.target_mob_id:
            return FireResult(False, reason="no target")
        if not self.can_fire(cannon_id=cannon_id, now_seconds=now_seconds):
            return FireResult(False, reason="reloading")
        prof = _SIZE_PROFILES[c.size]
        ammo_prof = _AMMO_PROFILES[c.loaded_ammo]
        dmg = prof.base_damage
        if c.target_feature_id and target_feature_kind:
            bonus_pct = ammo_prof.feature_kind_bonus_pct.get(
                target_feature_kind, 0,
            )
            dmg += dmg * bonus_pct // 100
        result = FireResult(
            accepted=True, cannon_id=cannon_id,
            target_feature_id=c.target_feature_id,
            target_mob_id=c.target_mob_id,
            damage=dmg, element=ammo_prof.element,
        )
        c.last_fired_at = now_seconds
        c.loaded_ammo = None
        return result


__all__ = [
    "CannonSize", "AmmoKind", "CrewRole",
    "Cannon", "FireResult", "SiegeCannons",
]
