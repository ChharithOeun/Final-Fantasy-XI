"""Foresight accessories — equipment & key items that grant sight.

A rare-and-precious tier of telegraph visibility unlock.
These aren't easy to come by — they're earned from
endgame content, fishing tournament prizes, ML-tier
trial chains, or 7-day domain invasions. Once equipped
or held, they grant the OTHER visibility source — a
weaker, conditional version of GEO/BRD foresight that
fits in a single accessory slot.

Item families
-------------
    FORESIGHT_LENS       earring; 25% damage taken
                         penalty for the slot, but
                         while equipped you SEE
                         tells. Tradeoff: you drop
                         it, you lose vision.
    ORACLE_PENDANT       neck slot; cooldown-based,
                         activate for 30s of vision
                         every 5 minutes
    PROPHET_RING         finger slot; vision for 8s
                         after taking a fatal-tier
                         hit (panic mode)
    SAGE_BRACELET        wrist; vision while standing
                         still (5y/sec movement
                         disables)
    SOOTHSAYER_KEY_ITEM  permanent key item from a
                         hidden quest; vision while
                         in specific zones (sea/sky
                         only)

Each item is independently registered with its
activation rule. The module owns the per-player
"equipped/held" state, the cooldown ledger, and the
condition checker that decides if visibility should be
granted on a tick.

Public surface
--------------
    AccessoryKind enum
    AccessoryProfile dataclass (frozen)
    EquipResult dataclass (frozen)
    ForesightAccessories
        .equip(player_id, accessory_kind, now_seconds)
            -> EquipResult
        .unequip(player_id, accessory_kind) -> bool
        .activate(player_id, accessory_kind, now_seconds)
            -> bool   # ORACLE_PENDANT only
        .on_fatal_hit(player_id, now_seconds)
            -> bool   # PROPHET_RING trigger
        .tick(player_id, now_seconds, gate,
              is_moving, current_zone)
        .equipped(player_id) -> tuple[AccessoryKind, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.telegraph_visibility_gate import (
    TelegraphVisibilityGate, VisibilitySource,
)


class AccessoryKind(str, enum.Enum):
    FORESIGHT_LENS = "foresight_lens"
    ORACLE_PENDANT = "oracle_pendant"
    PROPHET_RING = "prophet_ring"
    SAGE_BRACELET = "sage_bracelet"
    SOOTHSAYER_KEY_ITEM = "soothsayer_key_item"


# Activation modes — how an accessory grants visibility
class _ActivationMode(str, enum.Enum):
    PASSIVE = "passive"      # FORESIGHT_LENS — always-on while equipped
    COOLDOWN = "cooldown"    # ORACLE_PENDANT — activate for window
    ON_TRIGGER = "on_trigger"  # PROPHET_RING — fatal hit
    CONDITIONAL = "conditional"  # SAGE_BRACELET — standing still
    ZONE_GATED = "zone_gated"  # SOOTHSAYER_KEY_ITEM — sea/sky only


@dataclasses.dataclass(frozen=True)
class AccessoryProfile:
    kind: AccessoryKind
    mode: _ActivationMode
    grant_seconds_per_tick: int
    cooldown_seconds: int = 0
    activation_window: int = 0
    allowed_zones: tuple[str, ...] = ()


# Tuning knobs (reflected in profiles below)
LENS_DMG_TAKEN_PENALTY_PCT = 25
PENDANT_COOLDOWN = 300
PENDANT_WINDOW = 30
RING_TRIGGER_WINDOW = 8
SAGE_MOVE_GRACE_SECONDS = 1


_PROFILES: dict[AccessoryKind, AccessoryProfile] = {
    AccessoryKind.FORESIGHT_LENS: AccessoryProfile(
        kind=AccessoryKind.FORESIGHT_LENS,
        mode=_ActivationMode.PASSIVE,
        grant_seconds_per_tick=4,
    ),
    AccessoryKind.ORACLE_PENDANT: AccessoryProfile(
        kind=AccessoryKind.ORACLE_PENDANT,
        mode=_ActivationMode.COOLDOWN,
        grant_seconds_per_tick=4,
        cooldown_seconds=PENDANT_COOLDOWN,
        activation_window=PENDANT_WINDOW,
    ),
    AccessoryKind.PROPHET_RING: AccessoryProfile(
        kind=AccessoryKind.PROPHET_RING,
        mode=_ActivationMode.ON_TRIGGER,
        grant_seconds_per_tick=4,
        activation_window=RING_TRIGGER_WINDOW,
    ),
    AccessoryKind.SAGE_BRACELET: AccessoryProfile(
        kind=AccessoryKind.SAGE_BRACELET,
        mode=_ActivationMode.CONDITIONAL,
        grant_seconds_per_tick=4,
    ),
    AccessoryKind.SOOTHSAYER_KEY_ITEM: AccessoryProfile(
        kind=AccessoryKind.SOOTHSAYER_KEY_ITEM,
        mode=_ActivationMode.ZONE_GATED,
        grant_seconds_per_tick=4,
        allowed_zones=("sea", "sky", "abyssea"),
    ),
}


@dataclasses.dataclass(frozen=True)
class EquipResult:
    accepted: bool
    kind: t.Optional[AccessoryKind] = None
    damage_taken_penalty_pct: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PlayerState:
    equipped: set[AccessoryKind] = dataclasses.field(default_factory=set)
    pendant_last_activated_at: int = -10**9
    pendant_active_until: int = -10**9
    ring_active_until: int = -10**9
    last_movement_at: int = -10**9


@dataclasses.dataclass
class ForesightAccessories:
    _players: dict[str, _PlayerState] = dataclasses.field(default_factory=dict)

    def _get(self, player_id: str) -> _PlayerState:
        if player_id not in self._players:
            self._players[player_id] = _PlayerState()
        return self._players[player_id]

    def equip(
        self, *, player_id: str, kind: AccessoryKind,
        now_seconds: int = 0,
    ) -> EquipResult:
        if not player_id:
            return EquipResult(False, reason="blank player")
        s = self._get(player_id)
        if kind in s.equipped:
            return EquipResult(False, reason="already equipped")
        s.equipped.add(kind)
        penalty = (
            LENS_DMG_TAKEN_PENALTY_PCT
            if kind == AccessoryKind.FORESIGHT_LENS else 0
        )
        return EquipResult(
            accepted=True, kind=kind,
            damage_taken_penalty_pct=penalty,
        )

    def unequip(
        self, *, player_id: str, kind: AccessoryKind,
    ) -> bool:
        s = self._players.get(player_id)
        if s is None or kind not in s.equipped:
            return False
        s.equipped.discard(kind)
        return True

    def activate(
        self, *, player_id: str, kind: AccessoryKind,
        now_seconds: int,
    ) -> bool:
        s = self._players.get(player_id)
        if s is None or kind not in s.equipped:
            return False
        prof = _PROFILES[kind]
        if prof.mode != _ActivationMode.COOLDOWN:
            return False
        # cooldown gating
        if (now_seconds - s.pendant_last_activated_at) < prof.cooldown_seconds:
            return False
        s.pendant_last_activated_at = now_seconds
        s.pendant_active_until = now_seconds + prof.activation_window
        return True

    def on_fatal_hit(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        s = self._players.get(player_id)
        if s is None or AccessoryKind.PROPHET_RING not in s.equipped:
            return False
        s.ring_active_until = now_seconds + RING_TRIGGER_WINDOW
        return True

    def note_movement(
        self, *, player_id: str, now_seconds: int,
    ) -> None:
        s = self._players.get(player_id)
        if s is not None:
            s.last_movement_at = now_seconds

    def tick(
        self, *, player_id: str, now_seconds: int,
        gate: TelegraphVisibilityGate,
        is_moving: bool = False,
        current_zone: str = "",
    ) -> int:
        s = self._players.get(player_id)
        if s is None or not s.equipped:
            return 0
        if is_moving:
            s.last_movement_at = now_seconds
        granted = 0
        for kind in s.equipped:
            prof = _PROFILES[kind]
            should_grant = False
            if prof.mode == _ActivationMode.PASSIVE:
                should_grant = True
            elif prof.mode == _ActivationMode.COOLDOWN:
                should_grant = now_seconds < s.pendant_active_until
            elif prof.mode == _ActivationMode.ON_TRIGGER:
                should_grant = now_seconds < s.ring_active_until
            elif prof.mode == _ActivationMode.CONDITIONAL:
                # SAGE_BRACELET: must have been still for >= grace
                idle_for = now_seconds - s.last_movement_at
                should_grant = (
                    not is_moving
                    and idle_for >= SAGE_MOVE_GRACE_SECONDS
                )
            elif prof.mode == _ActivationMode.ZONE_GATED:
                should_grant = current_zone in prof.allowed_zones
            if should_grant:
                ok = gate.grant_visibility(
                    player_id=player_id,
                    source=VisibilitySource.OTHER,
                    granted_at=now_seconds,
                    expires_at=(
                        now_seconds + prof.grant_seconds_per_tick
                    ),
                    granted_by=kind.value,
                )
                if ok:
                    granted += 1
        return granted

    def equipped(self, *, player_id: str) -> tuple[AccessoryKind, ...]:
        s = self._players.get(player_id)
        return tuple(s.equipped) if s else ()

    def pendant_off_cooldown_at(
        self, *, player_id: str,
    ) -> int:
        s = self._players.get(player_id)
        if s is None:
            return 0
        return s.pendant_last_activated_at + PENDANT_COOLDOWN


__all__ = [
    "AccessoryKind", "AccessoryProfile", "EquipResult",
    "ForesightAccessories",
    "LENS_DMG_TAKEN_PENALTY_PCT",
    "PENDANT_COOLDOWN", "PENDANT_WINDOW",
    "RING_TRIGGER_WINDOW", "SAGE_MOVE_GRACE_SECONDS",
]
