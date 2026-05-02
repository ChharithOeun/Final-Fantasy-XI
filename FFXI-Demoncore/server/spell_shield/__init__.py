"""Spell Shields — Stoneskin / Phalanx / Sentinel / Cocoon damage absorbers.

Buffs that sit between the attack and the defender's HP. They
come in two shapes:

POOL absorbers — a fixed HP pool that drains as it absorbs hits.
    Stoneskin: 350 HP pool (+modifiers from MND/skill)
    Wing Slash (DRG): smaller pool, breath defense
    The pool wears off when depleted OR when the timer expires.

PER-HIT absorbers — flat damage reduction subtracted from each hit
    Phalanx: -X dmg per hit (does not deplete; capped by remaining)
    Sentinel: -50% dmg + huge enmity (PLD JA, 30s)
    Cocoon (BLU): -50% physical for 60s
    Defender (WAR): +N defense for 3 minutes

Public surface
--------------
    ShieldKind enum
    ActiveShield dataclass
    SpellShieldStack
        .add_pool_shield(kind, hp_pool, expires_at)
        .add_per_hit_shield(kind, reduction_pct/_flat, expires_at)
        .absorb(damage, now) -> AbsorbResult
        .tick(now)  — purge expired
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ShieldKind(str, enum.Enum):
    STONESKIN = "stoneskin"        # POOL
    WING_SLASH = "wing_slash"      # POOL (small, breath def)
    PHALANX = "phalanx"            # PER_HIT_FLAT
    SENTINEL = "sentinel"          # PER_HIT_PCT (PLD)
    COCOON = "cocoon"              # PER_HIT_PCT (BLU)
    DEFENDER = "defender"          # def boost, not damage absorber
    BARFIRA = "barfira"            # element-specific
    BARBLIZZARDRA = "barblizzardra"
    BARTHUNDRA = "barthundra"
    BARSTONRA = "barstonra"
    BARAERA = "baraera"
    BARWATERA = "barwatera"


# Per-shield default behavior. POOL shields drain; PER_HIT_X don't.
class _ShieldType(str, enum.Enum):
    POOL = "pool"
    PER_HIT_FLAT = "per_hit_flat"
    PER_HIT_PCT = "per_hit_pct"


_SHIELD_TYPES: dict[ShieldKind, _ShieldType] = {
    ShieldKind.STONESKIN: _ShieldType.POOL,
    ShieldKind.WING_SLASH: _ShieldType.POOL,
    ShieldKind.PHALANX: _ShieldType.PER_HIT_FLAT,
    ShieldKind.SENTINEL: _ShieldType.PER_HIT_PCT,
    ShieldKind.COCOON: _ShieldType.PER_HIT_PCT,
    ShieldKind.DEFENDER: _ShieldType.PER_HIT_PCT,
    ShieldKind.BARFIRA: _ShieldType.PER_HIT_PCT,
    ShieldKind.BARBLIZZARDRA: _ShieldType.PER_HIT_PCT,
    ShieldKind.BARTHUNDRA: _ShieldType.PER_HIT_PCT,
    ShieldKind.BARSTONRA: _ShieldType.PER_HIT_PCT,
    ShieldKind.BARAERA: _ShieldType.PER_HIT_PCT,
    ShieldKind.BARWATERA: _ShieldType.PER_HIT_PCT,
}


@dataclasses.dataclass
class ActiveShield:
    kind: ShieldKind
    expires_at: float
    pool_remaining: int = 0          # for POOL
    flat_reduction: int = 0          # for PER_HIT_FLAT (e.g. -25 dmg)
    pct_reduction: int = 0           # for PER_HIT_PCT (e.g. 50 means -50%)
    damage_kind_filter: t.Optional[str] = None  # 'physical' / 'fire' / etc


@dataclasses.dataclass(frozen=True)
class AbsorbResult:
    final_damage: int
    absorbed: int
    triggered_kinds: tuple[ShieldKind, ...] = ()
    pool_kinds_depleted: tuple[ShieldKind, ...] = ()


@dataclasses.dataclass
class SpellShieldStack:
    target_id: str
    _shields: list[ActiveShield] = dataclasses.field(default_factory=list)

    @property
    def active_kinds(self) -> tuple[ShieldKind, ...]:
        return tuple(s.kind for s in self._shields)

    def add_pool_shield(
        self, *, kind: ShieldKind, hp_pool: int, expires_at: float,
    ) -> bool:
        if _SHIELD_TYPES[kind] != _ShieldType.POOL:
            return False
        self._remove_kind(kind)
        self._shields.append(ActiveShield(
            kind=kind, expires_at=expires_at, pool_remaining=hp_pool,
        ))
        return True

    def add_per_hit_shield(
        self, *, kind: ShieldKind, expires_at: float,
        flat_reduction: int = 0, pct_reduction: int = 0,
        damage_kind_filter: t.Optional[str] = None,
    ) -> bool:
        st = _SHIELD_TYPES[kind]
        if st == _ShieldType.POOL:
            return False
        self._remove_kind(kind)
        self._shields.append(ActiveShield(
            kind=kind, expires_at=expires_at,
            flat_reduction=flat_reduction,
            pct_reduction=pct_reduction,
            damage_kind_filter=damage_kind_filter,
        ))
        return True

    def _remove_kind(self, kind: ShieldKind) -> None:
        self._shields = [s for s in self._shields if s.kind != kind]

    def tick(self, *, now: float) -> int:
        """Purge expired shields. Returns count removed."""
        before = len(self._shields)
        self._shields = [s for s in self._shields if s.expires_at > now]
        return before - len(self._shields)

    def absorb(
        self, *, damage: int, damage_kind: str = "physical",
        now: float = 0.0,
    ) -> AbsorbResult:
        if damage <= 0:
            return AbsorbResult(final_damage=0, absorbed=0)
        # Purge expired so we never absorb with a dead shield
        self.tick(now=now)

        triggered: list[ShieldKind] = []
        depleted: list[ShieldKind] = []
        remaining = damage

        # ---- Pool shields drain first (Stoneskin always layered first)
        for s in list(self._shields):
            if _SHIELD_TYPES[s.kind] != _ShieldType.POOL:
                continue
            if remaining <= 0:
                break
            if s.damage_kind_filter and s.damage_kind_filter != damage_kind:
                continue
            absorbed = min(remaining, s.pool_remaining)
            s.pool_remaining -= absorbed
            remaining -= absorbed
            triggered.append(s.kind)
            if s.pool_remaining <= 0:
                depleted.append(s.kind)
                self._shields.remove(s)

        # ---- Per-hit pct reduction (largest first stack-wise)
        per_hit_pct = [
            s for s in self._shields
            if _SHIELD_TYPES[s.kind] == _ShieldType.PER_HIT_PCT
            and (s.damage_kind_filter is None
                 or s.damage_kind_filter == damage_kind)
        ]
        for s in per_hit_pct:
            triggered.append(s.kind)
            remaining = remaining * (100 - s.pct_reduction) // 100

        # ---- Per-hit flat reduction (Phalanx etc.)
        per_hit_flat = [
            s for s in self._shields
            if _SHIELD_TYPES[s.kind] == _ShieldType.PER_HIT_FLAT
            and (s.damage_kind_filter is None
                 or s.damage_kind_filter == damage_kind)
        ]
        for s in per_hit_flat:
            triggered.append(s.kind)
            remaining = max(0, remaining - s.flat_reduction)

        return AbsorbResult(
            final_damage=remaining,
            absorbed=damage - remaining,
            triggered_kinds=tuple(triggered),
            pool_kinds_depleted=tuple(depleted),
        )


__all__ = [
    "ShieldKind", "ActiveShield", "AbsorbResult",
    "SpellShieldStack",
]
