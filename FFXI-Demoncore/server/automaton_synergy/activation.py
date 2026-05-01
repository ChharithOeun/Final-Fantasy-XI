"""activate_synergy — the canonical entry point.

A PUP master tries to fire a synergy: the activation pipeline is

    1. Look up a matching synergy in the catalog.
       (head + frame + active maneuvers must match)
    2. If no match -> reject (NO_SYNERGY).
    3. Check the cooldown for this (master, ability).
       If still locked -> reject (ON_COOLDOWN) and report the
       remaining seconds.
    4. Compose the modified ability under Overdrive scaling.
    5. Build an EffectInstance.
    6. Stamp the cooldown on the tracker.
    7. Return the EffectInstance to the caller.

The caller is responsible for applying the effect — this module
only verifies, schedules, and packages.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .catalog import (
    Frame,
    Head,
    ManeuverElement,
    SynergyAbility,
    check_synergy,
)
from .cooldowns import CooldownTracker
from .effects import EffectInstance, build_effect_instance
from .overdrive import compute_modified_ability


class ActivationStatus(str, enum.Enum):
    SUCCESS = "success"
    NO_SYNERGY = "no_synergy"           # combo doesn't match catalog
    ON_COOLDOWN = "on_cooldown"          # still locked


@dataclasses.dataclass(frozen=True)
class ActivationResult:
    """Outcome of an activate_synergy call."""
    status: ActivationStatus
    instance: t.Optional[EffectInstance] = None
    matched_ability: t.Optional[SynergyAbility] = None
    cooldown_remaining_seconds: int = 0
    reason: t.Optional[str] = None

    @property
    def accepted(self) -> bool:
        return self.status == ActivationStatus.SUCCESS


def activate_synergy(
    *,
    master_id: str,
    head: Head,
    frame: Frame,
    active_maneuvers: t.Mapping[ManeuverElement, int],
    cooldowns: CooldownTracker,
    now_tick: int,
    overdrive_active: bool = False,
) -> ActivationResult:
    """Try to fire a synergy ability.

    Side effects: on success, stamps the cooldown tracker for
    (master_id, ability.ability_id). On failure, no state changes.
    """
    # Step 1-2: catalog lookup.
    ability = check_synergy(
        head=head,
        frame=frame,
        active_maneuvers=active_maneuvers,
    )
    if ability is None:
        return ActivationResult(
            status=ActivationStatus.NO_SYNERGY,
            reason=(
                f"no synergy matches head={head.value}, "
                f"frame={frame.value} with maneuvers="
                f"{dict(active_maneuvers)}"
            ),
        )

    # Step 3: cooldown gate.
    if not cooldowns.can_trigger(
        master_id=master_id,
        ability_id=ability.ability_id,
        now_tick=now_tick,
    ):
        remaining = cooldowns.remaining(
            master_id=master_id,
            ability_id=ability.ability_id,
            now_tick=now_tick,
        )
        return ActivationResult(
            status=ActivationStatus.ON_COOLDOWN,
            matched_ability=ability,
            cooldown_remaining_seconds=remaining,
            reason=(
                f"{ability.name} on cooldown for "
                f"{remaining}s on master {master_id}"
            ),
        )

    # Step 4: overdrive scaling.
    modified = compute_modified_ability(
        ability, overdrive_active=overdrive_active,
    )

    # Step 6: stamp cooldown FIRST (so even if the effect packager
    # raises later, the lockout still applies — defensive against
    # spam-via-exception).
    next_avail = cooldowns.trigger(
        master_id=master_id,
        ability_id=ability.ability_id,
        cooldown_seconds=ability.cooldown_seconds,
        now_tick=now_tick,
    )

    # Step 5: build the effect instance.
    instance = build_effect_instance(
        modified=modified,
        master_id=master_id,
        fired_at_tick=now_tick,
        next_available_tick=next_avail,
    )

    return ActivationResult(
        status=ActivationStatus.SUCCESS,
        instance=instance,
        matched_ability=ability,
    )


__all__ = [
    "ActivationStatus",
    "ActivationResult",
    "activate_synergy",
]
