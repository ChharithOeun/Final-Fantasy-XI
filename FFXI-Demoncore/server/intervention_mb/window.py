"""InterventionWindow — the 3-second timer per INTERVENTION_MB.md.

When an enemy closes a skillchain on a friendly target, a 3-second
window opens. The friendly intervention spell must LAND (not start)
inside that window for the cancellation + amplification path to
fire.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Doc: '3-second Magic Burst window opens — same as offensive'.
INTERVENTION_WINDOW_SECONDS: float = 3.0


class ChainElement(str, enum.Enum):
    """The skillchain element whose halo opened the window.

    Per the doc, Light is the apex element (5x bonus); the others
    fall back to the base 3x amplification.
    """
    LIGHT = "light"
    DARKNESS = "darkness"
    FUSION = "fusion"
    DISTORTION = "distortion"
    FRAGMENTATION = "fragmentation"
    GRAVITATION = "gravitation"
    LIQUEFACTION = "liquefaction"
    SCISSION = "scission"
    DETONATION = "detonation"
    IMPACTION = "impaction"
    REVERBERATION = "reverberation"
    INDURATION = "induration"
    TRANSFIXION = "transfixion"
    COMPRESSION = "compression"


@dataclasses.dataclass
class InterventionWindow:
    """One open intervention opportunity.

    The damage broker fires `enemy_chain_window_open` when an enemy
    chain closes on a friendly target; this dataclass is the payload.
    """
    target_id: str                  # the friendly about to take MB damage
    chain_element: ChainElement
    opens_at: float                 # absolute time the window opened
    predicted_mb_damage: int        # the wipe-grade damage incoming
    enemy_caster_id: t.Optional[str] = None
    expires_at: float = 0.0         # filled in __post_init__

    def __post_init__(self) -> None:
        if self.expires_at == 0.0:
            self.expires_at = self.opens_at + INTERVENTION_WINDOW_SECONDS

    def is_open(self, *, now: float) -> bool:
        return self.opens_at <= now <= self.expires_at

    def remaining(self, *, now: float) -> float:
        if now >= self.expires_at:
            return 0.0
        if now < self.opens_at:
            return INTERVENTION_WINDOW_SECONDS
        return self.expires_at - now

    def is_light(self) -> bool:
        return self.chain_element == ChainElement.LIGHT


def open_window(*,
                  target_id: str,
                  chain_element: ChainElement,
                  predicted_mb_damage: int,
                  now: float,
                  enemy_caster_id: t.Optional[str] = None
                  ) -> InterventionWindow:
    """Construct a fresh window. The damage broker calls this."""
    if predicted_mb_damage < 0:
        raise ValueError("predicted_mb_damage must be non-negative")
    return InterventionWindow(
        target_id=target_id,
        chain_element=chain_element,
        opens_at=now,
        predicted_mb_damage=predicted_mb_damage,
        enemy_caster_id=enemy_caster_id,
    )


def lands_in_window(window: InterventionWindow, *, land_time: float) -> bool:
    """Decide whether a spell that lands at `land_time` qualifies."""
    return window.opens_at <= land_time <= window.expires_at
