"""Boss morale & rage — bosses get angrier as fights drag on.

The longer a boss fights, the angrier it gets. Rage is
a 0..1000 gauge that climbs continuously with elapsed
fight time AND on specific provocations:

    elapsed time            +1 rage/sec baseline
    boss took >= MAJOR_HP%   +50 rage immediately
    add was killed in <5s    +20 rage
    player parried/dodged    +5 rage
    HP dropped past phase    +100 rage
    boss interrupted while
      mid-cast               +75 rage

When rage crosses a threshold, a RageBand triggers. Each
band unlocks new abilities, boosts damage, and shortens
cooldowns. There are 5 bands:

    CALM       (0..199)    - baseline, no modifiers
    AGITATED   (200..399)  - +10% damage, -10% recast
    ENRAGED    (400..599)  - +25% damage, -20% recast,
                              unlocks "rage" abilities
    BERSERK    (600..799)  - +50% damage, -30% recast,
                              ignores 50% of mitigation
    APOCALYPTIC(800..1000) - +100% damage, -50% recast,
                              unlocks 2hr-tier ability,
                              ignores all mitigation

Bosses can be calmed slightly: if no provocation happens
for 30 seconds, rage decays at 5/sec. Some abilities
(BRD lullaby, SCH addendum:white) can shed rage on hit.

Public surface
--------------
    RageBand enum
    Provocation enum
    RageProfile dataclass (frozen)
    RageState dataclass (mutable)
    BossMoraleRage
        .start_fight(boss_id, fight_id, now_seconds)
        .tick(boss_id, fight_id, dt_seconds, now_seconds)
            -> RageState
        .provoke(boss_id, fight_id, provocation,
                 now_seconds, magnitude=1)
        .calm(boss_id, fight_id, amount, now_seconds)
        .band(boss_id, fight_id) -> RageBand
        .modifiers(boss_id, fight_id) -> RageModifiers
        .ability_unlocked(boss_id, fight_id,
                          ability_tier) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class RageBand(str, enum.Enum):
    CALM = "calm"
    AGITATED = "agitated"
    ENRAGED = "enraged"
    BERSERK = "berserk"
    APOCALYPTIC = "apocalyptic"


class Provocation(str, enum.Enum):
    HEAVY_DAMAGE = "heavy_damage"
    ADD_KILLED_FAST = "add_killed_fast"
    PARRIED_OR_DODGED = "parried_or_dodged"
    PHASE_CROSSED = "phase_crossed"
    INTERRUPTED_MID_CAST = "interrupted_mid_cast"


# Rage thresholds for bands
BAND_THRESHOLDS: tuple[tuple[int, RageBand], ...] = (
    (800, RageBand.APOCALYPTIC),
    (600, RageBand.BERSERK),
    (400, RageBand.ENRAGED),
    (200, RageBand.AGITATED),
    (0, RageBand.CALM),
)

# Rage gain per provocation
PROVOCATION_GAIN: dict[Provocation, int] = {
    Provocation.HEAVY_DAMAGE: 50,
    Provocation.ADD_KILLED_FAST: 20,
    Provocation.PARRIED_OR_DODGED: 5,
    Provocation.PHASE_CROSSED: 100,
    Provocation.INTERRUPTED_MID_CAST: 75,
}

RAGE_PER_SECOND_BASELINE = 1
RAGE_DECAY_AFTER_QUIET_SECONDS = 30
RAGE_DECAY_PER_SECOND = 5
RAGE_MAX = 1000


@dataclasses.dataclass(frozen=True)
class RageModifiers:
    damage_out_pct: int = 100
    recast_pct: int = 100         # 100 = baseline; <100 = faster
    mitigation_ignore_pct: int = 0   # 0..100 — fraction of player
                                      # mitigation the boss ignores


_BAND_MODS: dict[RageBand, RageModifiers] = {
    RageBand.CALM: RageModifiers(),
    RageBand.AGITATED: RageModifiers(
        damage_out_pct=110, recast_pct=90,
    ),
    RageBand.ENRAGED: RageModifiers(
        damage_out_pct=125, recast_pct=80,
    ),
    RageBand.BERSERK: RageModifiers(
        damage_out_pct=150, recast_pct=70,
        mitigation_ignore_pct=50,
    ),
    RageBand.APOCALYPTIC: RageModifiers(
        damage_out_pct=200, recast_pct=50,
        mitigation_ignore_pct=100,
    ),
}


# Ability tiers — lower number = always available; higher tier
# requires a higher band
ABILITY_TIER_BAND: dict[int, RageBand] = {
    0: RageBand.CALM,
    1: RageBand.AGITATED,
    2: RageBand.ENRAGED,
    3: RageBand.BERSERK,
    4: RageBand.APOCALYPTIC,
}


@dataclasses.dataclass
class RageState:
    fight_id: str
    boss_id: str
    rage: float
    last_provocation_at: int
    started_at: int


@dataclasses.dataclass
class BossMoraleRage:
    _fights: dict[str, RageState] = dataclasses.field(default_factory=dict)

    def start_fight(
        self, *, boss_id: str, fight_id: str, now_seconds: int,
    ) -> bool:
        if not boss_id or not fight_id:
            return False
        if fight_id in self._fights:
            return False
        self._fights[fight_id] = RageState(
            fight_id=fight_id, boss_id=boss_id,
            rage=0.0, last_provocation_at=now_seconds,
            started_at=now_seconds,
        )
        return True

    def tick(
        self, *, boss_id: str, fight_id: str,
        dt_seconds: float, now_seconds: int,
    ) -> t.Optional[RageState]:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id or dt_seconds <= 0:
            return f
        # baseline rage gain
        f.rage += RAGE_PER_SECOND_BASELINE * dt_seconds
        # decay if quiet
        quiet = now_seconds - f.last_provocation_at
        if quiet >= RAGE_DECAY_AFTER_QUIET_SECONDS:
            f.rage -= RAGE_DECAY_PER_SECOND * dt_seconds
        f.rage = max(0.0, min(RAGE_MAX, f.rage))
        return f

    def provoke(
        self, *, boss_id: str, fight_id: str,
        provocation: Provocation, now_seconds: int,
        magnitude: int = 1,
    ) -> bool:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id or magnitude <= 0:
            return False
        gain = PROVOCATION_GAIN[provocation] * magnitude
        f.rage = min(RAGE_MAX, f.rage + gain)
        f.last_provocation_at = now_seconds
        return True

    def calm(
        self, *, boss_id: str, fight_id: str,
        amount: int, now_seconds: int,
    ) -> bool:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id or amount <= 0:
            return False
        f.rage = max(0.0, f.rage - amount)
        return True

    def band(
        self, *, boss_id: str, fight_id: str,
    ) -> RageBand:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id:
            return RageBand.CALM
        for threshold, band in BAND_THRESHOLDS:
            if f.rage >= threshold:
                return band
        return RageBand.CALM

    def modifiers(
        self, *, boss_id: str, fight_id: str,
    ) -> RageModifiers:
        return _BAND_MODS[self.band(boss_id=boss_id, fight_id=fight_id)]

    def ability_unlocked(
        self, *, boss_id: str, fight_id: str,
        ability_tier: int,
    ) -> bool:
        if ability_tier not in ABILITY_TIER_BAND:
            return False
        required = ABILITY_TIER_BAND[ability_tier]
        current = self.band(boss_id=boss_id, fight_id=fight_id)
        # Bands are ordered by index in BAND_THRESHOLDS
        order = [b for _, b in BAND_THRESHOLDS][::-1]
        return order.index(current) >= order.index(required)

    def rage_value(
        self, *, boss_id: str, fight_id: str,
    ) -> int:
        f = self._fights.get(fight_id)
        if f is None or f.boss_id != boss_id:
            return 0
        return int(f.rage)


__all__ = [
    "RageBand", "Provocation", "RageModifiers",
    "RageState", "BossMoraleRage",
    "BAND_THRESHOLDS", "PROVOCATION_GAIN",
    "RAGE_PER_SECOND_BASELINE",
    "RAGE_DECAY_AFTER_QUIET_SECONDS",
    "RAGE_DECAY_PER_SECOND", "RAGE_MAX",
    "ABILITY_TIER_BAND",
]
