"""Magic Burst window — skillchain element + amplification timing.

A skillchain finisher tags a target with an ELEMENT for a brief
window. Spells matching that element cast inside the window
deal bonus damage (the canonical Magic Burst):

    +30% baseline burst bonus
    +5% per "Magic Burst Bonus" gear/JA tier (cap +20)

Window timing:
    OPEN_DURATION_MS = 12000   (12-second canonical window)

Public surface
--------------
    SkillchainElement enum (matching damage_resolver elements)
    BurstWindow dataclass — single open window
    PlayerMagicBurst tracker
        .open_window(target_id, element, now_ms, opener_id)
        .check_burst(target_id, spell_element, now_ms, mb_bonus_pct)
            -> BurstResolution
        .close_window(target_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


OPEN_DURATION_MS = 12000     # 12-second window
BURST_BASE_BONUS_PCT = 30
MAX_MB_BONUS_GEAR_PCT = 20   # capped MBB stack


class SkillchainElement(str, enum.Enum):
    LIGHT = "light"
    DARK = "darkness"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    EARTH = "earth"
    WIND = "wind"
    WATER = "water"


@dataclasses.dataclass
class BurstWindow:
    target_id: str
    element: SkillchainElement
    opened_at_ms: int
    opener_id: str
    closed: bool = False

    def is_open(self, *, now_ms: int) -> bool:
        if self.closed:
            return False
        return (now_ms - self.opened_at_ms) <= OPEN_DURATION_MS


@dataclasses.dataclass(frozen=True)
class BurstResolution:
    accepted: bool
    burst_landed: bool = False
    multiplier_pct: int = 100
    opener_credit: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class MagicBurstTracker:
    """Server-side tracker for open burst windows by target."""
    _windows: dict[str, BurstWindow] = dataclasses.field(
        default_factory=dict,
    )

    def open_window(
        self, *, target_id: str, element: SkillchainElement,
        now_ms: int, opener_id: str,
    ) -> bool:
        """Skillchain finished — open or refresh a window on target."""
        if not target_id:
            return False
        self._windows[target_id] = BurstWindow(
            target_id=target_id, element=element,
            opened_at_ms=now_ms, opener_id=opener_id,
        )
        return True

    def close_window(self, *, target_id: str) -> bool:
        win = self._windows.pop(target_id, None)
        return win is not None

    def get_window(self, *, target_id: str) -> t.Optional[BurstWindow]:
        return self._windows.get(target_id)

    def check_burst(
        self, *, target_id: str,
        spell_element: SkillchainElement,
        now_ms: int, mb_bonus_pct: int = 0,
    ) -> BurstResolution:
        """Resolve a spell-cast against any open window. Spell that
        matches the window element AND lands inside the time window
        gets the burst multiplier."""
        win = self._windows.get(target_id)
        if win is None:
            return BurstResolution(
                accepted=True, multiplier_pct=100, reason="no window",
            )
        if not win.is_open(now_ms=now_ms):
            # Window expired — clean it up lazily
            self._windows.pop(target_id, None)
            return BurstResolution(
                accepted=True, multiplier_pct=100,
                reason="window expired",
            )
        if win.element != spell_element:
            return BurstResolution(
                accepted=True, multiplier_pct=100,
                reason="element mismatch",
            )
        bonus = BURST_BASE_BONUS_PCT + min(mb_bonus_pct, MAX_MB_BONUS_GEAR_PCT)
        # The window CONSUMES on burst — only one MB per chain
        self._windows.pop(target_id, None)
        return BurstResolution(
            accepted=True, burst_landed=True,
            multiplier_pct=100 + bonus,
            opener_credit=win.opener_id,
        )


__all__ = [
    "OPEN_DURATION_MS",
    "BURST_BASE_BONUS_PCT", "MAX_MB_BONUS_GEAR_PCT",
    "SkillchainElement",
    "BurstWindow", "BurstResolution",
    "MagicBurstTracker",
]
