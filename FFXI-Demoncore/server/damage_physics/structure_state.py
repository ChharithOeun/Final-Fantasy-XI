"""HealingStructure — per-instance HP + visible state machine.

Per DAMAGE_PHYSICS_HEALING.md the model is:
    HP_current        (clamped 0..HP_max)
    HP_max            (set from preset on construction)
    heal_rate         (HP/s)
    heal_delay_s      (no-damage-taken seconds before heal starts)
    permanent_threshold (fraction of HP_max where damage becomes
                         permanent; 1.0 = never permanent)
    visible_state     (pristine | cracked | battered | ruined | destroyed)

Stage thresholds are exact:
  100-75% HP -> pristine
  75-50%     -> cracked
  50-25%     -> battered
  25-1%      -> ruined
  0%         -> destroyed
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .structure_kinds import StructurePreset


class VisibleState(str, enum.Enum):
    """Stage of damage visible to players."""
    PRISTINE = "pristine"
    CRACKED = "cracked"
    BATTERED = "battered"
    RUINED = "ruined"
    DESTROYED = "destroyed"


# Stage boundaries, descending. Entry: (lower_fraction_inclusive, state).
# A structure at exactly 75% HP is `cracked` (lower bound of pristine
# is exclusive on the way down). 0% is destroyed.
_STAGE_BANDS: tuple[tuple[float, VisibleState], ...] = (
    (0.75, VisibleState.PRISTINE),
    (0.50, VisibleState.CRACKED),
    (0.25, VisibleState.BATTERED),
    (1e-9, VisibleState.RUINED),
    (0.0, VisibleState.DESTROYED),
)


def resolve_visible_state(hp_current: int, hp_max: int) -> VisibleState:
    """Map HP fraction to a visible state. Doc-exact bands."""
    if hp_max <= 0:
        return VisibleState.DESTROYED
    fraction = max(0.0, hp_current / hp_max)
    if fraction <= 0:
        return VisibleState.DESTROYED
    if fraction >= 0.75:
        return VisibleState.PRISTINE
    if fraction >= 0.50:
        return VisibleState.CRACKED
    if fraction >= 0.25:
        return VisibleState.BATTERED
    return VisibleState.RUINED


@dataclasses.dataclass
class HealingStructure:
    """One destructible thing in the world.

    Created by the registry from a StructurePreset; the registry
    owns persistence + zone wiring. The damage / heal pipeline only
    needs this dataclass.
    """
    structure_id: str
    zone_id: str
    kind: str
    position: tuple[float, float, float]
    hp_max: int
    heal_rate: float
    heal_delay_s: float
    permanent_threshold: float
    hp_current: int = 0
    visible_state: VisibleState = VisibleState.PRISTINE
    last_hit_at: t.Optional[float] = None
    permanent: bool = False

    def __post_init__(self) -> None:
        if self.hp_current == 0 and not self.permanent:
            # New structure. Default to pristine HP.
            self.hp_current = self.hp_max
            self.visible_state = VisibleState.PRISTINE

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def from_preset(
        cls,
        *,
        structure_id: str,
        zone_id: str,
        position: tuple[float, float, float],
        preset: StructurePreset,
    ) -> "HealingStructure":
        return cls(
            structure_id=structure_id,
            zone_id=zone_id,
            kind=preset.kind,
            position=position,
            hp_max=preset.hp_max,
            heal_rate=preset.heal_rate,
            heal_delay_s=preset.heal_delay_s,
            permanent_threshold=preset.permanent_threshold,
            hp_current=preset.hp_max,
            visible_state=VisibleState.PRISTINE,
        )

    def hp_fraction(self) -> float:
        if self.hp_max <= 0:
            return 0.0
        return max(0.0, self.hp_current / self.hp_max)

    def is_pristine(self) -> bool:
        return self.visible_state == VisibleState.PRISTINE

    def is_destroyed(self) -> bool:
        return self.visible_state == VisibleState.DESTROYED

    def is_permanently_destroyed(self) -> bool:
        return self.permanent and self.is_destroyed()

    def reconcile_visible_state(self) -> VisibleState:
        """Re-derive visible_state from current HP. Returns the new state."""
        self.visible_state = resolve_visible_state(self.hp_current,
                                                       self.hp_max)
        return self.visible_state
