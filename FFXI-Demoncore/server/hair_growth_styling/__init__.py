"""Hair growth & styling — hair grows over real time.

Other MMOs let a player set hair length once and forget.
Demoncore tracks hair length over real-world days. Hair
GROWS — about 1cm per real-world week. Players who don't
visit a barber periodically end up with shaggy
characters; intentional shaggy is a look, intentional
buzzed is a look, and the in-between requires upkeep.

State:
    base_length_cm        length at last cut/style
    last_styled_day       game-day of last barber visit
    style_id              last applied hairstyle template
    color_id              hair color
    natural_growth_rate   per-race multiplier (mithra
                          grow faster, galka shed
                          differently — handled in race
                          baseline curve, applied here)

A barber NPC visit consumes:
    - Setting style_id + base_length_cm to whatever the
      player wants
    - Resetting last_styled_day to now
    - Modest gil fee

current_length_cm() = base_length_cm + (now_day -
last_styled_day) * 0.14 * natural_growth_rate

Public surface
--------------
    HairColor enum
    HairProfile dataclass (frozen)
    HairGrowthStyling
        .style(player, style_id, length_cm, color, day)
            -> bool
        .set_growth_rate(player, multiplier) -> bool
        .current_length_cm(player, now_day) -> float
        .profile(player, now_day) -> HairProfile
        .needs_barber(player, now_day, max_length_cm)
            -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_GROWTH_CM_PER_DAY = 0.14  # ~1cm/week


class HairColor(str, enum.Enum):
    BLACK = "black"
    BROWN = "brown"
    BLOND = "blond"
    RED = "red"
    SILVER = "silver"
    WHITE = "white"
    DYED_BLUE = "dyed_blue"
    DYED_GREEN = "dyed_green"
    DYED_PINK = "dyed_pink"


@dataclasses.dataclass(frozen=True)
class HairProfile:
    style_id: str
    base_length_cm: float
    last_styled_day: int
    color: HairColor
    growth_rate: float
    current_length_cm: float


@dataclasses.dataclass
class _HairState:
    style_id: str = "default_short"
    base_length_cm: float = 5.0
    last_styled_day: int = 0
    color: HairColor = HairColor.BLACK
    growth_rate: float = 1.0


@dataclasses.dataclass
class HairGrowthStyling:
    _states: dict[str, _HairState] = dataclasses.field(
        default_factory=dict,
    )

    def _state(self, player_id: str) -> _HairState:
        if player_id not in self._states:
            self._states[player_id] = _HairState()
        return self._states[player_id]

    def style(
        self, *, player_id: str, style_id: str,
        length_cm: float, color: HairColor,
        now_day: int,
    ) -> bool:
        if not player_id or not style_id:
            return False
        if length_cm < 0.0 or length_cm > 200.0:
            return False
        if now_day < 0:
            return False
        st = self._state(player_id)
        st.style_id = style_id
        st.base_length_cm = length_cm
        st.color = color
        st.last_styled_day = now_day
        return True

    def set_growth_rate(
        self, *, player_id: str, multiplier: float,
    ) -> bool:
        if not player_id:
            return False
        if multiplier <= 0.0 or multiplier > 5.0:
            return False
        st = self._state(player_id)
        st.growth_rate = multiplier
        return True

    def current_length_cm(
        self, *, player_id: str, now_day: int,
    ) -> float:
        if player_id not in self._states:
            return 5.0  # default
        st = self._states[player_id]
        days_elapsed = max(0, now_day - st.last_styled_day)
        grown = (
            days_elapsed * _GROWTH_CM_PER_DAY * st.growth_rate
        )
        return round(st.base_length_cm + grown, 2)

    def profile(
        self, *, player_id: str, now_day: int,
    ) -> HairProfile:
        st = self._state(player_id)
        cur = self.current_length_cm(
            player_id=player_id, now_day=now_day,
        )
        return HairProfile(
            style_id=st.style_id,
            base_length_cm=st.base_length_cm,
            last_styled_day=st.last_styled_day,
            color=st.color,
            growth_rate=st.growth_rate,
            current_length_cm=cur,
        )

    def needs_barber(
        self, *, player_id: str, now_day: int,
        max_length_cm: float,
    ) -> bool:
        cur = self.current_length_cm(
            player_id=player_id, now_day=now_day,
        )
        return cur > max_length_cm


__all__ = [
    "HairColor", "HairProfile", "HairGrowthStyling",
]
