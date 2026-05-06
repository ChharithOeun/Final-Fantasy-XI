"""Field commander role — alliance-wide formation orders.

One player per alliance can be designated FIELD COMMANDER
(elected by the alliance leader). The commander has a
limited menu of FORMATION ORDERS they can issue. Each
order grants every alliance member a small synchronized
buff for a duration, and applies a corresponding
collective constraint (turtle = no movement, rush = no
heals received, etc.).

Formation orders:
    TURTLE        +30% damage reduction, -50% movement speed
    FLANK         +15% positional damage, players must
                  reposition every 5 seconds or lose buff
    RUSH          +20% damage out, -50% healing received
    HOLD          +25% threat, +20% block/parry, no chase
                  permitted
    REGROUP       +30% MP regen, +20% HP regen, no
                  damage spells permitted
    SCATTER       +25% evasion, +20% movement speed,
                  no synergy abilities

Orders have a 90-second cooldown per commander, and a
20-second base duration. Issuing a new order overrides
the active one on the same alliance.

Public surface
--------------
    FormationOrder enum
    FormationModifiers dataclass (frozen)
    OrderResult dataclass (frozen)
    FieldCommanderRole
        .designate(alliance_id, commander_id) -> bool
        .vacate(alliance_id) -> bool
        .commander(alliance_id) -> Optional[str]
        .issue_order(commander_id, alliance_id, order,
                     now_seconds) -> OrderResult
        .active_order(alliance_id, now_seconds)
            -> Optional[FormationOrder]
        .modifiers(alliance_id, now_seconds)
            -> FormationModifiers
        .blocked_actions(alliance_id, now_seconds)
            -> tuple[str, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class FormationOrder(str, enum.Enum):
    TURTLE = "turtle"
    FLANK = "flank"
    RUSH = "rush"
    HOLD = "hold"
    REGROUP = "regroup"
    SCATTER = "scatter"


ORDER_DURATION_SECONDS = 20
ORDER_COOLDOWN_SECONDS = 90


@dataclasses.dataclass(frozen=True)
class FormationModifiers:
    damage_out_pct: int = 100
    damage_taken_pct: int = 100
    movement_pct: int = 100
    threat_pct: int = 100
    healing_recv_pct: int = 100
    mp_regen_pct: int = 100
    hp_regen_pct: int = 100
    evasion_pct: int = 100
    block_parry_pct: int = 100
    positional_damage_pct: int = 100


_ORDER_PROFILES: dict[FormationOrder, tuple[FormationModifiers, tuple[str, ...]]] = {
    FormationOrder.TURTLE: (
        FormationModifiers(damage_taken_pct=70, movement_pct=50),
        ("rush_movement",),
    ),
    FormationOrder.FLANK: (
        FormationModifiers(positional_damage_pct=115),
        (),  # repositioning enforced by caller
    ),
    FormationOrder.RUSH: (
        FormationModifiers(damage_out_pct=120, healing_recv_pct=50),
        (),
    ),
    FormationOrder.HOLD: (
        FormationModifiers(threat_pct=125, block_parry_pct=120),
        ("chase",),
    ),
    FormationOrder.REGROUP: (
        FormationModifiers(mp_regen_pct=130, hp_regen_pct=120),
        ("damage_spell",),
    ),
    FormationOrder.SCATTER: (
        FormationModifiers(evasion_pct=125, movement_pct=120),
        ("synergy_ability",),
    ),
}


@dataclasses.dataclass(frozen=True)
class OrderResult:
    accepted: bool
    order: t.Optional[FormationOrder] = None
    expires_at: int = 0
    next_cooldown_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _AllianceState:
    alliance_id: str
    commander_id: t.Optional[str] = None
    active_order: t.Optional[FormationOrder] = None
    order_started_at: int = 0
    order_expires_at: int = 0
    last_order_at: int = -10**9


@dataclasses.dataclass
class FieldCommanderRole:
    _alliances: dict[str, _AllianceState] = dataclasses.field(
        default_factory=dict,
    )

    def _get(self, alliance_id: str) -> _AllianceState:
        if alliance_id not in self._alliances:
            self._alliances[alliance_id] = _AllianceState(
                alliance_id=alliance_id,
            )
        return self._alliances[alliance_id]

    def designate(
        self, *, alliance_id: str, commander_id: str,
    ) -> bool:
        if not alliance_id or not commander_id:
            return False
        a = self._get(alliance_id)
        if a.commander_id == commander_id:
            return False
        a.commander_id = commander_id
        return True

    def vacate(self, *, alliance_id: str) -> bool:
        a = self._alliances.get(alliance_id)
        if a is None or a.commander_id is None:
            return False
        a.commander_id = None
        return True

    def commander(self, *, alliance_id: str) -> t.Optional[str]:
        a = self._alliances.get(alliance_id)
        return a.commander_id if a else None

    def issue_order(
        self, *, alliance_id: str, commander_id: str,
        order: FormationOrder, now_seconds: int,
    ) -> OrderResult:
        a = self._alliances.get(alliance_id)
        if a is None:
            return OrderResult(False, reason="unknown alliance")
        if a.commander_id != commander_id:
            return OrderResult(False, reason="not commander")
        next_allowed = a.last_order_at + ORDER_COOLDOWN_SECONDS
        if now_seconds < next_allowed:
            return OrderResult(
                False, reason="cooldown",
                next_cooldown_at=next_allowed,
            )
        a.active_order = order
        a.order_started_at = now_seconds
        a.order_expires_at = now_seconds + ORDER_DURATION_SECONDS
        a.last_order_at = now_seconds
        return OrderResult(
            accepted=True, order=order,
            expires_at=a.order_expires_at,
            next_cooldown_at=now_seconds + ORDER_COOLDOWN_SECONDS,
        )

    def active_order(
        self, *, alliance_id: str, now_seconds: int,
    ) -> t.Optional[FormationOrder]:
        a = self._alliances.get(alliance_id)
        if a is None or a.active_order is None:
            return None
        if now_seconds >= a.order_expires_at:
            a.active_order = None
            return None
        return a.active_order

    def modifiers(
        self, *, alliance_id: str, now_seconds: int,
    ) -> FormationModifiers:
        order = self.active_order(
            alliance_id=alliance_id, now_seconds=now_seconds,
        )
        if order is None:
            return FormationModifiers()
        return _ORDER_PROFILES[order][0]

    def blocked_actions(
        self, *, alliance_id: str, now_seconds: int,
    ) -> tuple[str, ...]:
        order = self.active_order(
            alliance_id=alliance_id, now_seconds=now_seconds,
        )
        if order is None:
            return ()
        return _ORDER_PROFILES[order][1]


__all__ = [
    "FormationOrder", "FormationModifiers", "OrderResult",
    "FieldCommanderRole",
    "ORDER_DURATION_SECONDS", "ORDER_COOLDOWN_SECONDS",
]
