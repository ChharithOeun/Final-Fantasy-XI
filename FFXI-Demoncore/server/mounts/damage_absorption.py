"""Damage absorption + dismount-on-zero spillover.

Per MOUNTS.md: 'Mounts do not block damage to the player; they
ABSORB it. If the mount has 4000 HP and you took a 1500-damage hit,
the mount took 1500. If the mount only had 100 HP left and a 1500-
damage hit lands, the mount dies and the remaining 1400 damage
spills onto the player.'
"""
from __future__ import annotations

import dataclasses

from .mount import MountSnapshot


@dataclasses.dataclass
class AbsorptionResult:
    """Outcome of one damage event landing on a mounted player."""
    mount_dmg_absorbed: int
    rider_dmg_spillover: int
    mount_died: bool
    mount_remaining_hp: int


class DamageAbsorption:
    """Resolves a single damage event hitting a mounted player.

    Mutates the mount snapshot in place; caller applies the
    rider_dmg_spillover via the player damage pipeline.
    """

    def apply_damage(self,
                       mount: MountSnapshot,
                       *,
                       incoming_dmg: int) -> AbsorptionResult:
        if incoming_dmg <= 0:
            return AbsorptionResult(
                mount_dmg_absorbed=0, rider_dmg_spillover=0,
                mount_died=False,
                mount_remaining_hp=mount.current_hp,
            )

        if not mount.is_alive or mount.current_hp <= 0:
            # Mount is already dead; everything spills to the rider.
            return AbsorptionResult(
                mount_dmg_absorbed=0,
                rider_dmg_spillover=incoming_dmg,
                mount_died=False,
                mount_remaining_hp=mount.current_hp,
            )

        # Mount absorbs up to its current HP
        absorbed = min(mount.current_hp, incoming_dmg)
        spillover = incoming_dmg - absorbed
        mount.current_hp -= absorbed
        mount_died = mount.current_hp <= 0
        if mount_died:
            mount.is_alive = False
        return AbsorptionResult(
            mount_dmg_absorbed=absorbed,
            rider_dmg_spillover=spillover,
            mount_died=mount_died,
            mount_remaining_hp=max(0, mount.current_hp),
        )

    def heal(self,
              mount: MountSnapshot,
              *,
              amount: int) -> int:
        """Cure / Gysahl Greens / stable healing. Returns actual amount
        healed (clamped to max_hp)."""
        if not mount.is_alive or amount <= 0:
            return 0
        before = mount.current_hp
        mount.current_hp = min(mount.max_hp, mount.current_hp + amount)
        return mount.current_hp - before

    def feed_gysahl_greens(self, mount: MountSnapshot) -> int:
        """30% HP restore over 30s out-of-combat. Returns the heal
        amount applied immediately; the orchestrator owns the 30s
        timer if it wants to model the channel."""
        if not mount.is_alive:
            return 0
        amount = int(mount.max_hp * 0.30)
        return self.heal(mount, amount=amount)
