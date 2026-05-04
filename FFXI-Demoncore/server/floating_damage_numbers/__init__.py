"""Floating damage numbers — combat popup numbers.

Damage / heal / miss / resist text rises from a target's head
when an event lands. Per-player preferences control:
* enabled (master toggle)
* show_others (your numbers always; others' numbers optional)
* size_pct
* lifespan_seconds
* crit_emphasis (bigger + brighter on crits)
* heal_color / damage_color / miss_color / resist_color
* element_tint (color tints damage by element)

The system queues popup events and the renderer pulls them per
viewer with current_popups(). Expired popups are pruned by tick().

Public surface
--------------
    PopupKind enum
    NumberPopup dataclass
    PopupPrefs dataclass
    FloatingDamageNumbers
        .prefs_for(player_id) / .set_pref(...)
        .emit(event_id, target_id, attacker_id, kind, amount,
              element, is_crit, zone, now_seconds)
        .current_popups(viewer_id, viewer_zone_id)
        .tick(now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Bounds.
MIN_SIZE_PCT = 50
MAX_SIZE_PCT = 250
DEFAULT_SIZE_PCT = 100
MIN_LIFESPAN = 0.5
MAX_LIFESPAN = 5.0
DEFAULT_LIFESPAN = 1.5


class PopupKind(str, enum.Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    MISS = "miss"
    RESIST = "resist"
    DODGE = "dodge"
    PARRY = "parry"
    BLOCK = "block"
    CRIT_TAG = "crit_tag"


class ElementTint(str, enum.Enum):
    NONE = "none"
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"


_ELEMENT_COLOR: dict[ElementTint, str] = {
    ElementTint.NONE: "white",
    ElementTint.FIRE: "#ff5533",
    ElementTint.ICE: "#66ccff",
    ElementTint.WIND: "#88ee88",
    ElementTint.EARTH: "#aa7744",
    ElementTint.LIGHTNING: "#eeee44",
    ElementTint.WATER: "#3377ee",
    ElementTint.LIGHT: "#ffffcc",
    ElementTint.DARK: "#aa44dd",
}


@dataclasses.dataclass
class PopupPrefs:
    player_id: str
    enabled: bool = True
    show_others: bool = True
    size_pct: int = DEFAULT_SIZE_PCT
    lifespan_seconds: float = DEFAULT_LIFESPAN
    crit_emphasis: bool = True
    damage_color: str = "white"
    heal_color: str = "lime"
    miss_color: str = "gray"
    resist_color: str = "blue"
    element_tint_enabled: bool = True


@dataclasses.dataclass(frozen=True)
class NumberPopup:
    popup_id: str
    target_id: str
    attacker_id: t.Optional[str]
    kind: PopupKind
    amount: int
    element: ElementTint
    color: str
    size_pct: int
    is_crit: bool
    zone_id: str
    spawned_at_seconds: float
    expires_at_seconds: float


def _clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _clamp_float(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclasses.dataclass
class FloatingDamageNumbers:
    _prefs: dict[str, PopupPrefs] = dataclasses.field(
        default_factory=dict,
    )
    _popups: dict[str, NumberPopup] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def prefs_for(
        self, *, player_id: str,
    ) -> PopupPrefs:
        p = self._prefs.get(player_id)
        if p is None:
            p = PopupPrefs(player_id=player_id)
            self._prefs[player_id] = p
        return p

    def set_pref(
        self, *, player_id: str,
        enabled: t.Optional[bool] = None,
        show_others: t.Optional[bool] = None,
        size_pct: t.Optional[int] = None,
        lifespan_seconds: t.Optional[float] = None,
        crit_emphasis: t.Optional[bool] = None,
        damage_color: t.Optional[str] = None,
        heal_color: t.Optional[str] = None,
        miss_color: t.Optional[str] = None,
        resist_color: t.Optional[str] = None,
        element_tint_enabled: t.Optional[bool] = None,
    ) -> PopupPrefs:
        p = self.prefs_for(player_id=player_id)
        if enabled is not None:
            p.enabled = enabled
        if show_others is not None:
            p.show_others = show_others
        if size_pct is not None:
            p.size_pct = _clamp_int(
                size_pct, MIN_SIZE_PCT, MAX_SIZE_PCT,
            )
        if lifespan_seconds is not None:
            p.lifespan_seconds = _clamp_float(
                lifespan_seconds,
                MIN_LIFESPAN, MAX_LIFESPAN,
            )
        if crit_emphasis is not None:
            p.crit_emphasis = crit_emphasis
        if damage_color:
            p.damage_color = damage_color
        if heal_color:
            p.heal_color = heal_color
        if miss_color:
            p.miss_color = miss_color
        if resist_color:
            p.resist_color = resist_color
        if element_tint_enabled is not None:
            p.element_tint_enabled = element_tint_enabled
        return p

    def emit(
        self, *,
        target_id: str,
        attacker_id: t.Optional[str] = None,
        kind: PopupKind = PopupKind.DAMAGE,
        amount: int = 0,
        element: ElementTint = ElementTint.NONE,
        is_crit: bool = False,
        zone_id: str,
        now_seconds: float = 0.0,
        size_pct: int = DEFAULT_SIZE_PCT,
        lifespan_seconds: float = DEFAULT_LIFESPAN,
        color: t.Optional[str] = None,
    ) -> NumberPopup:
        # Default color resolution if not overridden
        if color is None:
            if kind == PopupKind.HEAL:
                color = "lime"
            elif kind == PopupKind.MISS:
                color = "gray"
            elif kind == PopupKind.RESIST:
                color = "blue"
            else:
                color = _ELEMENT_COLOR[element]
        clamped_size = _clamp_int(
            size_pct, MIN_SIZE_PCT, MAX_SIZE_PCT,
        )
        clamped_life = _clamp_float(
            lifespan_seconds, MIN_LIFESPAN, MAX_LIFESPAN,
        )
        if is_crit:
            clamped_size = _clamp_int(
                int(clamped_size * 1.4),
                MIN_SIZE_PCT, MAX_SIZE_PCT,
            )
        pid = f"popup_{self._next_id}"
        self._next_id += 1
        popup = NumberPopup(
            popup_id=pid,
            target_id=target_id,
            attacker_id=attacker_id,
            kind=kind, amount=amount,
            element=element, color=color,
            size_pct=clamped_size,
            is_crit=is_crit,
            zone_id=zone_id,
            spawned_at_seconds=now_seconds,
            expires_at_seconds=(
                now_seconds + clamped_life
            ),
        )
        self._popups[pid] = popup
        return popup

    def current_popups(
        self, *, viewer_id: str,
        viewer_zone_id: str,
    ) -> tuple[NumberPopup, ...]:
        prefs = self.prefs_for(player_id=viewer_id)
        if not prefs.enabled:
            return ()
        out: list[NumberPopup] = []
        for popup in self._popups.values():
            if popup.zone_id != viewer_zone_id:
                continue
            # If the popup is from someone else and the viewer
            # has show_others off, skip.
            involves_self = (
                popup.target_id == viewer_id
                or popup.attacker_id == viewer_id
            )
            if not prefs.show_others and not involves_self:
                continue
            out.append(popup)
        out.sort(
            key=lambda p: -p.spawned_at_seconds,
        )
        return tuple(out)

    def tick(
        self, *, now_seconds: float,
    ) -> tuple[str, ...]:
        expired: list[str] = []
        for pid, p in list(self._popups.items()):
            if now_seconds >= p.expires_at_seconds:
                del self._popups[pid]
                expired.append(pid)
        return tuple(expired)

    def total_active(self) -> int:
        return len(self._popups)


__all__ = [
    "MIN_SIZE_PCT", "MAX_SIZE_PCT",
    "DEFAULT_SIZE_PCT",
    "MIN_LIFESPAN", "MAX_LIFESPAN",
    "DEFAULT_LIFESPAN",
    "PopupKind", "ElementTint",
    "PopupPrefs", "NumberPopup",
    "FloatingDamageNumbers",
]
