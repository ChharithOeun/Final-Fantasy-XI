"""Boss ability tells — the world tips you off, even without visibility.

Without telegraph visibility, players can't see the AOE
overlay. But they can still observe the world. This module
is the registry of TELLS — the environment and gesture
cues that fire 1-3 seconds before a boss ability lands.

A tell is small and diegetic:
    DUST_FALLING        ceiling tremors before a slam
    WATER_RIPPLE        ripples in pool before a tidal AOE
    HAND_GESTURE        boss raises arm before a cone
    WEAPON_GLOW         weapon charges before a heavy WS
    SHADOW_LENGTHENS    floor darkens before a curse
    GUSTING_WIND        wind whips before a lightning bolt
    EARTH_CRACK         ground splits before a quake
    AIR_DISTORTS        heat shimmer before a fire AOE

Every boss ability is registered with a list of tells and
a "lead time" (how long the tell shows before the ability
lands). Tells are PLAYED to all players in range — they
don't require visibility. They're WHAT the world is doing,
not a gameplay overlay. The audible_callouts module narrates
them; the SFX pipeline plays them; the visual layer shows
them.

This module emits TellEvents the rest of the engine
consumes. It also tracks per-player "tell ID" — your
telegraph_reading_skill XP can teach you which tell
predicts which ability, so an EXPERT-tier player who sees
"ripples in the pool" can act WITHOUT telegraph visibility
ever flipping on.

Public surface
--------------
    TellKind enum
    AbilityTell dataclass (frozen)
    TellEvent dataclass (frozen)
    BossAbilityTells
        .register_ability(boss_id, ability_id, tells,
                          lead_time_seconds)
        .on_ability_wind_up(boss_id, ability_id,
                            anchor_position, now_seconds)
            -> tuple[TellEvent, ...]
        .ability_tells(boss_id, ability_id)
            -> tuple[AbilityTell, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TellKind(str, enum.Enum):
    DUST_FALLING = "dust_falling"
    WATER_RIPPLE = "water_ripple"
    HAND_GESTURE = "hand_gesture"
    WEAPON_GLOW = "weapon_glow"
    SHADOW_LENGTHENS = "shadow_lengthens"
    GUSTING_WIND = "gusting_wind"
    EARTH_CRACK = "earth_crack"
    AIR_DISTORTS = "air_distorts"


@dataclasses.dataclass(frozen=True)
class AbilityTell:
    boss_id: str
    ability_id: str
    tells: tuple[TellKind, ...]
    lead_time_seconds: float
    anchor_label: str = ""    # e.g. "ceiling above boss",
                               # "boss feet", "boss right arm"


@dataclasses.dataclass(frozen=True)
class TellEvent:
    boss_id: str
    ability_id: str
    tell: TellKind
    anchor_label: str
    fires_at: float       # absolute time the tell becomes visible
    ability_lands_at: float


@dataclasses.dataclass
class BossAbilityTells:
    _registry: dict[tuple[str, str], AbilityTell] = dataclasses.field(
        default_factory=dict,
    )

    def register_ability(
        self, *, boss_id: str, ability_id: str,
        tells: t.Iterable[TellKind],
        lead_time_seconds: float,
        anchor_label: str = "",
    ) -> bool:
        if not boss_id or not ability_id:
            return False
        if lead_time_seconds <= 0:
            return False
        tell_tuple = tuple(tells)
        if not tell_tuple:
            return False
        key = (boss_id, ability_id)
        if key in self._registry:
            return False
        self._registry[key] = AbilityTell(
            boss_id=boss_id, ability_id=ability_id,
            tells=tell_tuple,
            lead_time_seconds=lead_time_seconds,
            anchor_label=anchor_label,
        )
        return True

    def on_ability_wind_up(
        self, *, boss_id: str, ability_id: str,
        now_seconds: float,
    ) -> tuple[TellEvent, ...]:
        key = (boss_id, ability_id)
        a = self._registry.get(key)
        if a is None:
            return ()
        lands_at = now_seconds + a.lead_time_seconds
        out: list[TellEvent] = []
        for t_ in a.tells:
            out.append(TellEvent(
                boss_id=boss_id, ability_id=ability_id,
                tell=t_, anchor_label=a.anchor_label,
                fires_at=now_seconds,
                ability_lands_at=lands_at,
            ))
        return tuple(out)

    def ability_tells(
        self, *, boss_id: str, ability_id: str,
    ) -> tuple[TellKind, ...]:
        a = self._registry.get((boss_id, ability_id))
        if a is None:
            return ()
        return a.tells

    def get(
        self, *, boss_id: str, ability_id: str,
    ) -> t.Optional[AbilityTell]:
        return self._registry.get((boss_id, ability_id))

    def all_for_boss(
        self, *, boss_id: str,
    ) -> tuple[AbilityTell, ...]:
        return tuple(
            a for (b, _), a in self._registry.items()
            if b == boss_id
        )


__all__ = [
    "TellKind", "AbilityTell", "TellEvent",
    "BossAbilityTells",
]
