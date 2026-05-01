"""Cavalry action catalog + resolver.

Per the user spec: cavalry-style mounted combat. Each action is a
specific maneuver — Charge (cone on a sprint), Lance Attack (long
line strike), Trample (run-through line), Rear Kick (cone behind),
Drive-by Strike (sword swipe at lateral target).

Some actions require minimum momentum (Charge needs the mount to be
moving above a threshold speed). Resolution goes through the
SAMPLE_X tables to get base damage; final damage layers in:
  - mount_level scaling (+1.5% per level over 75)
  - rider weapon_fit_multiplier
  - cavalry_stance bonus (+10% over transit baseline)

Caller is responsible for AOE containment via aoe_telegraph; this
module only computes per-target damage for entities the caller
already filtered as 'inside the shape'.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .combat_stance import (
    CAVALRY_UNLOCK_LEVEL,
    CavalryStance,
    weapon_fit_multiplier,
)


@dataclasses.dataclass(frozen=True)
class CavalryAction:
    """One mounted combat maneuver."""
    name: str
    base_damage: int
    aoe_shape: str                # 'cone' / 'line' / 'circle'
    aoe_radius_cm: float
    aoe_angle_deg: t.Optional[float] = None    # cones only
    requires_charge: bool = False              # mount must be moving
    min_speed_ms: float = 0.0                  # minimum momentum
    cooldown_seconds: float = 8.0
    tp_cost: int = 0
    notes: str = ""


# Headline cavalry library — 5 actions covering the canonical maneuvers.
CAVALRY_CATALOG: dict[str, CavalryAction] = {
    "charge": CavalryAction(
        name="Charge",
        base_damage=400,
        aoe_shape="cone",
        aoe_radius_cm=1000,
        aoe_angle_deg=60,
        requires_charge=True,
        min_speed_ms=8.0,
        cooldown_seconds=15.0,
        notes="cone-shaped impact at sprint speed; knocks back",
    ),
    "lance_attack": CavalryAction(
        name="Lance Attack",
        base_damage=600,
        aoe_shape="line",
        aoe_radius_cm=200,
        aoe_angle_deg=None,
        requires_charge=False,
        cooldown_seconds=10.0,
        tp_cost=100,
        notes="single-target line spear thrust from horseback",
    ),
    "trample": CavalryAction(
        name="Trample",
        base_damage=300,
        aoe_shape="line",
        aoe_radius_cm=150,
        requires_charge=True,
        min_speed_ms=6.0,
        cooldown_seconds=8.0,
        notes="run-through path damage; hits everything in the line",
    ),
    "rear_kick": CavalryAction(
        name="Rear Kick",
        base_damage=250,
        aoe_shape="cone",
        aoe_radius_cm=400,
        aoe_angle_deg=90,
        requires_charge=False,
        cooldown_seconds=6.0,
        notes="reverse cone, hits anything behind the mount",
    ),
    "drive_by_strike": CavalryAction(
        name="Drive-by Strike",
        base_damage=350,
        aoe_shape="circle",
        aoe_radius_cm=300,
        requires_charge=True,
        min_speed_ms=5.0,
        cooldown_seconds=7.0,
        notes="lateral swipe; hits a tight circle alongside the mount",
    ),
}


# Mount-level scaling: +1.5% per level over 75
CAVALRY_LEVEL_SCALING_PER_LEVEL = 0.015
# Stance bonus over baseline transit damage
CAVALRY_STANCE_BONUS = 0.10


@dataclasses.dataclass
class CavalryActionResult:
    """Outcome of a cavalry action attempt."""
    success: bool
    action: t.Optional[CavalryAction]
    base_damage: int = 0
    final_damage_per_target: int = 0
    reason: str = ""
    aoe_shape: str = ""
    aoe_radius_cm: float = 0.0
    aoe_angle_deg: t.Optional[float] = None


def resolve_cavalry_action(*,
                             action_id: str,
                             stance: CavalryStance,
                             rider_level: int,
                             mount_level: int,
                             mount_is_alive: bool,
                             current_speed_ms: float,
                             weapon_class: str,
                             ) -> CavalryActionResult:
    """Resolve whether the action fires + compute per-target damage.

    Returns a CavalryActionResult with success=False and a `reason`
    string when the action can't be used (wrong stance, mount dead,
    not moving fast enough, action unknown). On success, the caller
    feeds the AOE shape into aoe_telegraph for actual containment.
    """
    if stance != CavalryStance.CAVALRY:
        return CavalryActionResult(
            success=False, action=None,
            reason="not in cavalry stance — only transit-mode actions allowed",
        )
    if not mount_is_alive:
        return CavalryActionResult(
            success=False, action=None,
            reason="mount is dead",
        )
    if rider_level < CAVALRY_UNLOCK_LEVEL:
        return CavalryActionResult(
            success=False, action=None,
            reason=f"rider must be level {CAVALRY_UNLOCK_LEVEL}+",
        )
    action = CAVALRY_CATALOG.get(action_id.lower())
    if action is None:
        return CavalryActionResult(
            success=False, action=None,
            reason=f"unknown cavalry action: {action_id}",
        )
    if action.requires_charge and current_speed_ms < action.min_speed_ms:
        return CavalryActionResult(
            success=False, action=action,
            reason=(f"{action.name} requires speed >= {action.min_speed_ms} m/s; "
                     f"current {current_speed_ms:.2f}"),
        )

    # Damage scaling
    levels_above = max(0, mount_level - 75)
    level_factor = 1.0 + CAVALRY_LEVEL_SCALING_PER_LEVEL * levels_above
    weapon_factor = weapon_fit_multiplier(weapon_class)
    stance_factor = 1.0 + CAVALRY_STANCE_BONUS

    final = int(round(action.base_damage * level_factor
                        * weapon_factor * stance_factor))

    return CavalryActionResult(
        success=True,
        action=action,
        base_damage=action.base_damage,
        final_damage_per_target=final,
        aoe_shape=action.aoe_shape,
        aoe_radius_cm=action.aoe_radius_cm,
        aoe_angle_deg=action.aoe_angle_deg,
    )
