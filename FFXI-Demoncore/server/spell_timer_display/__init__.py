"""Spell timer display — buff/debuff timer panel.

Tracks ACTIVE EFFECTS on a player so the renderer can paint a
sortable, prioritized timer strip. Each effect carries a kind
(BUFF / DEBUFF / FOOD / SPIRIT_LINK / TWO_HOUR / SONG / GEO_BUBBLE),
a remaining-duration, an importance rank, and an optional
expiry-warning threshold.

Sorting:
* DEBUFFs always show before BUFFs by default
* Inside each group, sort by remaining seconds ASC (soon-to-expire
  first) so the player sees what to refresh
* Optional priority_override moves an effect to the top of its
  group (e.g. RR clock just above all)

Public surface
--------------
    EffectKind enum
    Effect dataclass
    TimerEntry dataclass
    SpellTimerDisplay
        .apply(player_id, effect_id, kind, remaining, importance,
               warning_at_remaining)
        .extend(player_id, effect_id, by_seconds)
        .remove(player_id, effect_id)
        .tick(player_id, elapsed_seconds) -> tuple[expired ids]
        .timers_for(player_id) -> tuple[TimerEntry]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class EffectKind(str, enum.Enum):
    BUFF = "buff"
    DEBUFF = "debuff"
    FOOD = "food"
    SPIRIT_LINK = "spirit_link"
    TWO_HOUR = "two_hour"
    SONG = "song"
    GEO_BUBBLE = "geo_bubble"


# Default group ordering — debuffs always render first.
_GROUP_ORDER: dict[EffectKind, int] = {
    EffectKind.DEBUFF: 0,
    EffectKind.TWO_HOUR: 1,
    EffectKind.BUFF: 2,
    EffectKind.SONG: 3,
    EffectKind.GEO_BUBBLE: 4,
    EffectKind.FOOD: 5,
    EffectKind.SPIRIT_LINK: 6,
}


@dataclasses.dataclass
class Effect:
    effect_id: str
    label: str
    kind: EffectKind
    remaining_seconds: float
    initial_seconds: float
    importance: int = 0
    warning_at_remaining: float = 5.0
    priority_override: bool = False


@dataclasses.dataclass(frozen=True)
class TimerEntry:
    effect_id: str
    label: str
    kind: EffectKind
    remaining_seconds: float
    initial_seconds: float
    pct_remaining: int
    color_hint: str
    is_warning: bool


def _color_for(
    *, kind: EffectKind, pct_remaining: int,
    is_warning: bool,
) -> str:
    if is_warning:
        return "red"
    if kind == EffectKind.DEBUFF:
        return "purple"
    if pct_remaining > 75:
        return "lime"
    if pct_remaining > 25:
        return "yellow"
    return "orange"


@dataclasses.dataclass
class SpellTimerDisplay:
    _effects: dict[
        str, dict[str, Effect],
    ] = dataclasses.field(default_factory=dict)

    def apply(
        self, *, player_id: str, effect_id: str,
        label: str, kind: EffectKind,
        remaining_seconds: float,
        importance: int = 0,
        warning_at_remaining: float = 5.0,
        priority_override: bool = False,
    ) -> bool:
        if remaining_seconds <= 0:
            return False
        bucket = self._effects.setdefault(player_id, {})
        bucket[effect_id] = Effect(
            effect_id=effect_id, label=label, kind=kind,
            remaining_seconds=remaining_seconds,
            initial_seconds=remaining_seconds,
            importance=importance,
            warning_at_remaining=warning_at_remaining,
            priority_override=priority_override,
        )
        return True

    def extend(
        self, *, player_id: str, effect_id: str,
        by_seconds: float,
    ) -> bool:
        bucket = self._effects.get(player_id)
        if bucket is None or effect_id not in bucket:
            return False
        if by_seconds <= 0:
            return False
        eff = bucket[effect_id]
        eff.remaining_seconds += by_seconds
        eff.initial_seconds = max(
            eff.initial_seconds,
            eff.remaining_seconds,
        )
        return True

    def remove(
        self, *, player_id: str, effect_id: str,
    ) -> bool:
        bucket = self._effects.get(player_id)
        if bucket is None:
            return False
        return bucket.pop(effect_id, None) is not None

    def tick(
        self, *, player_id: str,
        elapsed_seconds: float,
    ) -> tuple[str, ...]:
        bucket = self._effects.get(player_id)
        if bucket is None or elapsed_seconds <= 0:
            return ()
        expired: list[str] = []
        for eid, eff in list(bucket.items()):
            eff.remaining_seconds -= elapsed_seconds
            if eff.remaining_seconds <= 0:
                expired.append(eid)
                del bucket[eid]
        return tuple(expired)

    def timers_for(
        self, *, player_id: str,
    ) -> tuple[TimerEntry, ...]:
        bucket = self._effects.get(player_id, {})
        rows: list[TimerEntry] = []
        for eff in bucket.values():
            denom = max(0.0001, eff.initial_seconds)
            pct = int(
                (eff.remaining_seconds / denom) * 100,
            )
            pct = max(0, min(100, pct))
            warning = (
                eff.remaining_seconds
                <= eff.warning_at_remaining
            )
            color = _color_for(
                kind=eff.kind, pct_remaining=pct,
                is_warning=warning,
            )
            rows.append(TimerEntry(
                effect_id=eff.effect_id,
                label=eff.label,
                kind=eff.kind,
                remaining_seconds=eff.remaining_seconds,
                initial_seconds=eff.initial_seconds,
                pct_remaining=pct,
                color_hint=color,
                is_warning=warning,
            ))
        # Sort: priority_override first (within group), then
        # group order, then remaining_seconds ASC.
        def _key(entry: TimerEntry) -> tuple:
            eff = bucket[entry.effect_id]
            return (
                _GROUP_ORDER[eff.kind],
                0 if eff.priority_override else 1,
                entry.remaining_seconds,
                eff.label,
            )
        rows.sort(key=_key)
        return tuple(rows)

    def total_effects(
        self, *, player_id: str,
    ) -> int:
        return len(self._effects.get(player_id, {}))


__all__ = [
    "EffectKind",
    "Effect", "TimerEntry",
    "SpellTimerDisplay",
]
