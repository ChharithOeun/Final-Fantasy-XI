"""Skillchain + Magic-Burst UI hints — the doc's hero UI specs.

Per COMBAT_TEMPO.md (Weapon Skills + skillchains in fast combat):

    - A small, glowing indicator on the target-of-target showing
      the active skillchain element + a countdown
    - Tighter Magic Burst window (1.5s) - but a fat damage bonus
      inside it
    - Multi-character skillchain telegraphs when more than one
      player is queueing - visible to the whole party
    - Auto-WS toggle - like /assist for skillchains: a player can
      flag 'auto-WS into the chain when partner X opens'

This module exposes the tuning anchors as constants + provides a
small AutoWsToggle dataclass the orchestrator can pick up to
auto-fire WS into a chain.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# The doc's tightened Magic Burst window during fast combat.
MB_WINDOW_SECONDS: float = 1.5

# Default damage bonus inside the MB window — the doc says 'a fat
# damage bonus'. We anchor at 1.30x; tunable per encounter.
MB_DAMAGE_BONUS_MULTIPLIER: float = 1.30


class SkillchainIndicatorPlacement(str, enum.Enum):
    """Where the chain-indicator UI element renders."""
    TARGET_OF_TARGET = "target_of_target"
    ABOVE_TARGET = "above_target"


@dataclasses.dataclass(frozen=True)
class SkillchainIndicator:
    """One target-of-target chain-indicator render spec."""
    target_id: str
    chain_element: str             # 'fire' | 'ice' | 'fragmentation' | ...
    countdown_seconds: float       # remaining seconds in chain window
    placement: SkillchainIndicatorPlacement = (
        SkillchainIndicatorPlacement.TARGET_OF_TARGET)
    is_multi_character: bool = False    # 2+ players queuing


@dataclasses.dataclass
class AutoWsToggle:
    """The 'auto-WS into the chain when partner X opens' flag.

    Per the doc this is opt-in — 'less control, more party-friendliness'.
    The combat pipeline checks active toggles when a chain opens and
    auto-fires the configured WS for any toggle that matches.
    """
    actor_id: str
    partner_actor_id: t.Optional[str] = None    # None == 'any partner'
    ws_id: t.Optional[str] = None
    active: bool = True

    def matches_opener(self, *, opener_actor_id: str) -> bool:
        """Should this toggle fire for the given chain opener?"""
        if not self.active:
            return False
        if self.ws_id is None:
            return False
        if self.partner_actor_id is None:
            return True
        return self.partner_actor_id == opener_actor_id


def make_indicator(*,
                      target_id: str,
                      chain_element: str,
                      countdown_seconds: float,
                      multi_character: bool = False
                      ) -> SkillchainIndicator:
    """Convenience constructor for the orchestrator."""
    if countdown_seconds < 0:
        raise ValueError("countdown_seconds must be non-negative")
    return SkillchainIndicator(
        target_id=target_id,
        chain_element=chain_element,
        countdown_seconds=countdown_seconds,
        is_multi_character=multi_character,
    )


def damage_in_mb_window(base_damage: float,
                            *,
                            elapsed_seconds: float,
                            ) -> tuple[bool, float]:
    """Apply the 1.5s MB window math.

    Returns (in_window, scaled_damage). Inside the window the damage
    is multiplied by MB_DAMAGE_BONUS_MULTIPLIER; outside it the
    damage is unchanged.
    """
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    in_window = elapsed_seconds <= MB_WINDOW_SECONDS
    if in_window:
        return True, base_damage * MB_DAMAGE_BONUS_MULTIPLIER
    return False, base_damage
