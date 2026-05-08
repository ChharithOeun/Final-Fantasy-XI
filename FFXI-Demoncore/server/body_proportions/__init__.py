"""Body proportions — height/build sliders with stat tradeoffs.

A galka in retail is a fixed model. Demoncore lets the
player adjust proportions WITHIN race-bounded limits,
and trades visual customization for SMALL stat shifts
that recompute against character_stats.

Sliders (per-player):
    height_modifier      -1.0..+1.0; race-baseline shifted
                         within ±15% of canonical
    build_modifier       -1.0..+1.0; lean to bulky
    posture_modifier     -1.0..+1.0; hunched to upright

Stat impacts (small but real):
    height_modifier > 0   +reach (slightly bigger atk
                          range), -evasion (bigger
                          target)
    build_modifier > 0    +HP, +STR, -AGI
    posture_modifier > 0  +CHR, +ACC; <0 +stealth (sneak)

These deltas are CAPPED — you can't push +5 STR by
maxing build. The cap is derived from a slider * 3
formula (so a +1.0 build = +3 STR / +30 HP / -3 AGI
maximum).

Locked at character creation; can be re-rolled at the
"Vana'diel Surgeon" NPC for a major fee + 24-hour
cooldown.

Public surface
--------------
    BodyProfile dataclass (frozen)
    StatImpacts dataclass (frozen)
    BodyProportions
        .set_height(player, value, now_day) -> bool
        .set_build(player, value, now_day) -> bool
        .set_posture(player, value, now_day) -> bool
        .reset(player, now_day) -> bool
        .profile(player) -> BodyProfile
        .stat_impacts(player) -> StatImpacts
        .lockout_until(player) -> int
"""
from __future__ import annotations

import dataclasses
import typing as t


_LOCKOUT_DAYS = 1


@dataclasses.dataclass(frozen=True)
class BodyProfile:
    height_modifier: float
    build_modifier: float
    posture_modifier: float


@dataclasses.dataclass(frozen=True)
class StatImpacts:
    reach_bonus: int
    evasion_bonus: int
    hp_bonus: int
    str_bonus: int
    agi_bonus: int
    chr_bonus: int
    acc_bonus: int
    stealth_bonus: int


_DEFAULT = BodyProfile(
    height_modifier=0.0,
    build_modifier=0.0,
    posture_modifier=0.0,
)


@dataclasses.dataclass
class _PlayerState:
    profile: BodyProfile = _DEFAULT
    last_change_day: int = -1


@dataclasses.dataclass
class BodyProportions:
    _states: dict[str, _PlayerState] = dataclasses.field(
        default_factory=dict,
    )

    def _state(self, player_id: str) -> _PlayerState:
        if player_id not in self._states:
            self._states[player_id] = _PlayerState()
        return self._states[player_id]

    def _can_change(
        self, player_id: str, now_day: int,
    ) -> bool:
        st = self._state(player_id)
        if st.last_change_day < 0:
            return True
        return now_day >= st.last_change_day + _LOCKOUT_DAYS

    def set_height(
        self, *, player_id: str, value: float,
        now_day: int,
    ) -> bool:
        if not player_id:
            return False
        if value < -1.0 or value > 1.0:
            return False
        if not self._can_change(player_id, now_day):
            return False
        st = self._state(player_id)
        st.profile = dataclasses.replace(
            st.profile, height_modifier=value,
        )
        st.last_change_day = now_day
        return True

    def set_build(
        self, *, player_id: str, value: float,
        now_day: int,
    ) -> bool:
        if not player_id:
            return False
        if value < -1.0 or value > 1.0:
            return False
        if not self._can_change(player_id, now_day):
            return False
        st = self._state(player_id)
        st.profile = dataclasses.replace(
            st.profile, build_modifier=value,
        )
        st.last_change_day = now_day
        return True

    def set_posture(
        self, *, player_id: str, value: float,
        now_day: int,
    ) -> bool:
        if not player_id:
            return False
        if value < -1.0 or value > 1.0:
            return False
        if not self._can_change(player_id, now_day):
            return False
        st = self._state(player_id)
        st.profile = dataclasses.replace(
            st.profile, posture_modifier=value,
        )
        st.last_change_day = now_day
        return True

    def reset(
        self, *, player_id: str, now_day: int,
    ) -> bool:
        if player_id not in self._states:
            return False
        if not self._can_change(player_id, now_day):
            return False
        st = self._states[player_id]
        st.profile = _DEFAULT
        st.last_change_day = now_day
        return True

    def profile(
        self, *, player_id: str,
    ) -> BodyProfile:
        if player_id not in self._states:
            return _DEFAULT
        return self._states[player_id].profile

    def stat_impacts(
        self, *, player_id: str,
    ) -> StatImpacts:
        p = self.profile(player_id=player_id)
        # Each slider * 3 = max stat delta
        h = int(p.height_modifier * 3)
        b = int(p.build_modifier * 3)
        # posture > 0 = upright; < 0 = hunched
        post = p.posture_modifier
        return StatImpacts(
            reach_bonus=h,
            evasion_bonus=-h,
            hp_bonus=int(p.build_modifier * 30),
            str_bonus=b,
            agi_bonus=-b,
            chr_bonus=int(post * 3) if post > 0 else 0,
            acc_bonus=int(post * 3) if post > 0 else 0,
            stealth_bonus=int(-post * 3) if post < 0 else 0,
        )

    def lockout_until(
        self, *, player_id: str,
    ) -> int:
        if player_id not in self._states:
            return 0
        st = self._states[player_id]
        if st.last_change_day < 0:
            return 0
        return st.last_change_day + _LOCKOUT_DAYS


__all__ = [
    "BodyProfile", "StatImpacts", "BodyProportions",
]
