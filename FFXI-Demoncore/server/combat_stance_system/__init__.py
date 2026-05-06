"""Combat stance system — five stances that re-weight a fighter.

Players can be one of five active stances at any time
during combat. Each stance applies multiplicative
modifiers to the player's offensive, defensive, evasive,
and support stats, and gates which abilities are
available.

Stances
-------
    OFFENSIVE   +30% damage out, -20% damage taken
                resistance, +10% TP gain.
                Disabled: defensive cooldowns (Sentinel,
                Invincible, etc.)
    DEFENSIVE   -25% damage out, +30% damage reduction
                taken, +20% threat. Disabled: 2hr SPs.
    BALANCED    no modifiers. All abilities available.
    EVASIVE     -15% damage out, +25% evasion, +10%
                movement speed. Disabled: heavy WS,
                heavy spells.
    SUPPORT     -40% damage out, +20% healing/buff
                magnitude, +20% MP regen. Disabled:
                damage-dealing WS, attack spells.

Stance switches have a small cooldown (8 seconds) to
prevent rapid-toggling exploits, and incur a brief
"settling" period (1 second) during which neither old
nor new stance modifiers apply.

Public surface
--------------
    Stance enum
    StanceProfile dataclass (frozen)
    StanceModifiers dataclass (frozen)
    CombatStanceSystem
        .set_stance(player_id, stance, now_seconds)
            -> StanceSwitchResult
        .current(player_id) -> Stance
        .modifiers(player_id, now_seconds) -> StanceModifiers
        .ability_allowed(player_id, ability_tag,
                         now_seconds) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Stance(str, enum.Enum):
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    BALANCED = "balanced"
    EVASIVE = "evasive"
    SUPPORT = "support"


# Common ability tags that stances gate. Combat layer
# tags each ability with one of these so the stance
# system can look it up.
class AbilityTag(str, enum.Enum):
    DEFENSIVE_COOLDOWN = "defensive_cooldown"   # Sentinel, etc.
    TWO_HOUR_SP = "two_hour_sp"
    HEAVY_WS = "heavy_ws"
    HEAVY_SPELL = "heavy_spell"
    DAMAGE_WS = "damage_ws"
    ATTACK_SPELL = "attack_spell"
    HEAL_SPELL = "heal_spell"
    BUFF_SPELL = "buff_spell"
    LIGHT_WS = "light_ws"
    LIGHT_SPELL = "light_spell"


SWITCH_COOLDOWN_SECONDS = 8
SETTLING_SECONDS = 1


@dataclasses.dataclass(frozen=True)
class StanceModifiers:
    damage_out_pct: int = 100      # 100 = baseline
    damage_taken_pct: int = 100
    evasion_pct: int = 100
    movement_pct: int = 100
    tp_gain_pct: int = 100
    threat_pct: int = 100
    healing_pct: int = 100
    mp_regen_pct: int = 100


@dataclasses.dataclass(frozen=True)
class StanceProfile:
    stance: Stance
    modifiers: StanceModifiers
    blocked_tags: tuple[AbilityTag, ...]


_PROFILES: dict[Stance, StanceProfile] = {
    Stance.OFFENSIVE: StanceProfile(
        stance=Stance.OFFENSIVE,
        modifiers=StanceModifiers(
            damage_out_pct=130,
            damage_taken_pct=120,
            tp_gain_pct=110,
        ),
        blocked_tags=(AbilityTag.DEFENSIVE_COOLDOWN,),
    ),
    Stance.DEFENSIVE: StanceProfile(
        stance=Stance.DEFENSIVE,
        modifiers=StanceModifiers(
            damage_out_pct=75,
            damage_taken_pct=70,
            threat_pct=120,
        ),
        blocked_tags=(AbilityTag.TWO_HOUR_SP,),
    ),
    Stance.BALANCED: StanceProfile(
        stance=Stance.BALANCED,
        modifiers=StanceModifiers(),
        blocked_tags=(),
    ),
    Stance.EVASIVE: StanceProfile(
        stance=Stance.EVASIVE,
        modifiers=StanceModifiers(
            damage_out_pct=85,
            evasion_pct=125,
            movement_pct=110,
        ),
        blocked_tags=(AbilityTag.HEAVY_WS, AbilityTag.HEAVY_SPELL),
    ),
    Stance.SUPPORT: StanceProfile(
        stance=Stance.SUPPORT,
        modifiers=StanceModifiers(
            damage_out_pct=60,
            healing_pct=120,
            mp_regen_pct=120,
        ),
        blocked_tags=(AbilityTag.DAMAGE_WS, AbilityTag.ATTACK_SPELL),
    ),
}


@dataclasses.dataclass(frozen=True)
class StanceSwitchResult:
    accepted: bool
    new_stance: t.Optional[Stance] = None
    settles_at: int = 0
    next_switch_allowed_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PlayerStance:
    stance: Stance
    last_switch_at: int


@dataclasses.dataclass
class CombatStanceSystem:
    _players: dict[str, _PlayerStance] = dataclasses.field(
        default_factory=dict,
    )

    def set_stance(
        self, *, player_id: str, stance: Stance, now_seconds: int,
    ) -> StanceSwitchResult:
        if not player_id:
            return StanceSwitchResult(False, reason="blank player")
        existing = self._players.get(player_id)
        if existing is None:
            self._players[player_id] = _PlayerStance(
                stance=stance, last_switch_at=now_seconds,
            )
            return StanceSwitchResult(
                accepted=True, new_stance=stance,
                settles_at=now_seconds + SETTLING_SECONDS,
                next_switch_allowed_at=(
                    now_seconds + SWITCH_COOLDOWN_SECONDS
                ),
            )
        if existing.stance == stance:
            return StanceSwitchResult(False, reason="already in stance")
        next_allowed = existing.last_switch_at + SWITCH_COOLDOWN_SECONDS
        if now_seconds < next_allowed:
            return StanceSwitchResult(
                False, reason="switch cooldown",
                next_switch_allowed_at=next_allowed,
            )
        existing.stance = stance
        existing.last_switch_at = now_seconds
        return StanceSwitchResult(
            accepted=True, new_stance=stance,
            settles_at=now_seconds + SETTLING_SECONDS,
            next_switch_allowed_at=now_seconds + SWITCH_COOLDOWN_SECONDS,
        )

    def current(self, *, player_id: str) -> Stance:
        p = self._players.get(player_id)
        return p.stance if p else Stance.BALANCED

    def modifiers(
        self, *, player_id: str, now_seconds: int,
    ) -> StanceModifiers:
        p = self._players.get(player_id)
        if p is None:
            return StanceModifiers()
        # During settling, modifiers are neutral
        if (now_seconds - p.last_switch_at) < SETTLING_SECONDS:
            return StanceModifiers()
        return _PROFILES[p.stance].modifiers

    def ability_allowed(
        self, *, player_id: str, ability_tag: AbilityTag,
        now_seconds: int,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return True   # default BALANCED → all allowed
        if (now_seconds - p.last_switch_at) < SETTLING_SECONDS:
            # during settling: cannot use any ability
            return False
        prof = _PROFILES[p.stance]
        return ability_tag not in prof.blocked_tags

    def time_to_next_switch(
        self, *, player_id: str, now_seconds: int,
    ) -> int:
        p = self._players.get(player_id)
        if p is None:
            return 0
        return max(0,
            p.last_switch_at + SWITCH_COOLDOWN_SECONDS - now_seconds,
        )


__all__ = [
    "Stance", "AbilityTag", "StanceProfile", "StanceModifiers",
    "StanceSwitchResult", "CombatStanceSystem",
    "SWITCH_COOLDOWN_SECONDS", "SETTLING_SECONDS",
]
