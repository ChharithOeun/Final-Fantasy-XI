"""Random encounters — travel ambushes scaled by zone risk.

In retail FFXI, you walked through Konschtat Highlands and the
mobs were wherever they spawned. In Demoncore, the open world
also has random TRAVEL encounters — a beastmen raid party
crossing the road, a downed caravan begging for help, a Fomor
ambush by night, a lost spirit asking to be put to rest. They
fire probabilistically as the party moves, scaled by:

* Zone base risk (calm farmland low; beastmen frontier high)
* Time of day (night bumps undead/Fomor; daytime bumps caravans)
* Party size (lone travelers more often ambushed)
* Beastmen raid pressure on this zone's trade routes
* Player faction reputation (allied tribes' members may approach
  to GIFT instead of attack)

Encounter kinds
---------------
    BEASTMEN_RAID        hostile, scaled mob count
    FOMOR_AMBUSH         night-only, hostile, hardcore-tier
    LOST_SPIRIT          neutral; quest hook (escort, lay to rest)
    CARAVAN_DOWNED       neutral; help quest hook (escort onward)
    PILGRIM_PATROL       neutral; faction-friendly NPCs
    WILDLIFE_PACK        hostile, mid-tier
    OUTLAW_BANDITS       hostile, drops bounty
    MERCHANT_HAWK        non-hostile, sale opportunity
    WANDERING_TRUST      offers to join the party temporarily

Public surface
--------------
    EncounterKind enum
    EncounterTriggerContext dataclass (zone, hour, party,...)
    EncounterRoll dataclass — what fired, parameters
    EncounterScheduler
        .register_zone_profile(zone_id, profile)
        .roll(context, rng) -> Optional[EncounterRoll]
        .reset_zone_cooldown(zone_id)
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# How many in-game seconds must pass between encounters in the
# same zone for the same party. Prevents back-to-back ambushes.
PER_ZONE_COOLDOWN_SECONDS = 300.0
# Default per-step roll probability (0.0..1.0). Multiplied by
# zone risk + adjustments.
DEFAULT_BASE_PROBABILITY = 0.05
NIGHT_HOUR_LOW = 18
NIGHT_HOUR_HIGH = 6


class EncounterKind(str, enum.Enum):
    BEASTMEN_RAID = "beastmen_raid"
    FOMOR_AMBUSH = "fomor_ambush"
    LOST_SPIRIT = "lost_spirit"
    CARAVAN_DOWNED = "caravan_downed"
    PILGRIM_PATROL = "pilgrim_patrol"
    WILDLIFE_PACK = "wildlife_pack"
    OUTLAW_BANDITS = "outlaw_bandits"
    MERCHANT_HAWK = "merchant_hawk"
    WANDERING_TRUST = "wandering_trust"


class TimeOfDay(str, enum.Enum):
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"
    DAWN = "dawn"


def time_of_day_for_hour(hour: int) -> TimeOfDay:
    h = hour % 24
    if 6 <= h < 18:
        return TimeOfDay.DAY
    if 18 <= h < 20:
        return TimeOfDay.DUSK
    if h < 5:
        return TimeOfDay.NIGHT
    if h < 6:
        return TimeOfDay.DAWN
    return TimeOfDay.NIGHT


# Per-encounter weights by time of day. The roll picks among
# eligible kinds weighted by these.
_TIME_WEIGHTS: dict[
    TimeOfDay, dict[EncounterKind, int],
] = {
    TimeOfDay.DAY: {
        EncounterKind.BEASTMEN_RAID: 4,
        EncounterKind.FOMOR_AMBUSH: 0,
        EncounterKind.LOST_SPIRIT: 1,
        EncounterKind.CARAVAN_DOWNED: 4,
        EncounterKind.PILGRIM_PATROL: 3,
        EncounterKind.WILDLIFE_PACK: 4,
        EncounterKind.OUTLAW_BANDITS: 2,
        EncounterKind.MERCHANT_HAWK: 3,
        EncounterKind.WANDERING_TRUST: 2,
    },
    TimeOfDay.DUSK: {
        EncounterKind.BEASTMEN_RAID: 3,
        EncounterKind.FOMOR_AMBUSH: 1,
        EncounterKind.LOST_SPIRIT: 3,
        EncounterKind.CARAVAN_DOWNED: 2,
        EncounterKind.PILGRIM_PATROL: 2,
        EncounterKind.WILDLIFE_PACK: 3,
        EncounterKind.OUTLAW_BANDITS: 4,
        EncounterKind.MERCHANT_HAWK: 1,
        EncounterKind.WANDERING_TRUST: 1,
    },
    TimeOfDay.NIGHT: {
        EncounterKind.BEASTMEN_RAID: 2,
        EncounterKind.FOMOR_AMBUSH: 6,
        EncounterKind.LOST_SPIRIT: 5,
        EncounterKind.CARAVAN_DOWNED: 0,
        EncounterKind.PILGRIM_PATROL: 0,
        EncounterKind.WILDLIFE_PACK: 4,
        EncounterKind.OUTLAW_BANDITS: 4,
        EncounterKind.MERCHANT_HAWK: 0,
        EncounterKind.WANDERING_TRUST: 0,
    },
    TimeOfDay.DAWN: {
        EncounterKind.BEASTMEN_RAID: 2,
        EncounterKind.FOMOR_AMBUSH: 1,
        EncounterKind.LOST_SPIRIT: 2,
        EncounterKind.CARAVAN_DOWNED: 1,
        EncounterKind.PILGRIM_PATROL: 1,
        EncounterKind.WILDLIFE_PACK: 3,
        EncounterKind.OUTLAW_BANDITS: 1,
        EncounterKind.MERCHANT_HAWK: 1,
        EncounterKind.WANDERING_TRUST: 1,
    },
}


@dataclasses.dataclass(frozen=True)
class ZoneEncounterProfile:
    zone_id: str
    base_risk: int                # 0..100; field=10, frontier=60
    eligible_kinds: frozenset[EncounterKind] = frozenset(
        EncounterKind,
    )


@dataclasses.dataclass(frozen=True)
class EncounterTriggerContext:
    zone_id: str
    party_id: str
    party_size: int
    hour_of_day: int                # 0..23
    now_seconds: float
    raid_pressure: int = 0         # 0..100
    party_outlaw: bool = False
    party_avg_level: int = 1


@dataclasses.dataclass(frozen=True)
class EncounterRoll:
    encounter_kind: EncounterKind
    zone_id: str
    triggered_at_seconds: float
    mob_count: int                 # for hostile encounters
    label: str
    notes: str = ""


@dataclasses.dataclass
class EncounterScheduler:
    base_probability: float = DEFAULT_BASE_PROBABILITY
    cooldown_seconds: float = PER_ZONE_COOLDOWN_SECONDS
    _zone_profiles: dict[
        str, ZoneEncounterProfile,
    ] = dataclasses.field(default_factory=dict)
    _last_encounter_at: dict[
        tuple[str, str], float,
    ] = dataclasses.field(default_factory=dict)

    def register_zone_profile(
        self, profile: ZoneEncounterProfile,
    ) -> ZoneEncounterProfile:
        if not (0 <= profile.base_risk <= 100):
            raise ValueError("base_risk must be in 0..100")
        self._zone_profiles[profile.zone_id] = profile
        return profile

    def profile_for(
        self, zone_id: str,
    ) -> t.Optional[ZoneEncounterProfile]:
        return self._zone_profiles.get(zone_id)

    def reset_zone_cooldown(
        self, *, zone_id: str, party_id: str,
    ) -> bool:
        return self._last_encounter_at.pop(
            (zone_id, party_id), None,
        ) is not None

    def _effective_probability(
        self, *, ctx: EncounterTriggerContext,
        profile: ZoneEncounterProfile,
    ) -> float:
        # Risk: base_probability scales with zone risk
        prob = self.base_probability * (profile.base_risk / 30.0)
        # Lone travelers more often ambushed
        if ctx.party_size <= 1:
            prob *= 1.5
        elif ctx.party_size >= 6:
            prob *= 0.7
        # Trade-route raid pressure adds to encounter rate
        if ctx.raid_pressure > 0:
            prob += (ctx.raid_pressure / 200.0)
        return min(0.95, max(0.0, prob))

    def _pick_kind(
        self, *,
        eligible: frozenset[EncounterKind],
        tod: TimeOfDay, rng: random.Random,
    ) -> t.Optional[EncounterKind]:
        weights = _TIME_WEIGHTS[tod]
        candidates: list[EncounterKind] = []
        candidate_weights: list[int] = []
        for kind in eligible:
            w = weights.get(kind, 0)
            if w > 0:
                candidates.append(kind)
                candidate_weights.append(w)
        if not candidates:
            return None
        return rng.choices(
            candidates, weights=candidate_weights, k=1,
        )[0]

    def _mob_count_for(
        self, *, kind: EncounterKind,
        ctx: EncounterTriggerContext, rng: random.Random,
    ) -> int:
        base = max(1, ctx.party_size)
        if kind == EncounterKind.BEASTMEN_RAID:
            return base + rng.randint(2, 4)
        if kind == EncounterKind.FOMOR_AMBUSH:
            return base + rng.randint(3, 5)
        if kind == EncounterKind.WILDLIFE_PACK:
            return rng.randint(2, 5)
        if kind == EncounterKind.OUTLAW_BANDITS:
            return rng.randint(3, 6)
        if kind == EncounterKind.PILGRIM_PATROL:
            return rng.randint(2, 4)
        # Non-combat encounters have an "actor count"
        return 1

    def _label_for(
        self, *, kind: EncounterKind, mob_count: int,
    ) -> str:
        labels = {
            EncounterKind.BEASTMEN_RAID:
                f"A beastmen raid party blocks the road ({mob_count} mobs)",
            EncounterKind.FOMOR_AMBUSH:
                f"Fomor materialize from the dark ({mob_count} mobs)",
            EncounterKind.LOST_SPIRIT:
                "A weeping spirit asks to be laid to rest",
            EncounterKind.CARAVAN_DOWNED:
                "A downed caravan begs for an escort",
            EncounterKind.PILGRIM_PATROL:
                f"A pilgrim patrol crosses your path ({mob_count} NPCs)",
            EncounterKind.WILDLIFE_PACK:
                f"A wild pack circles ({mob_count} beasts)",
            EncounterKind.OUTLAW_BANDITS:
                f"Outlaw bandits leap from cover ({mob_count} foes)",
            EncounterKind.MERCHANT_HAWK:
                "A traveling merchant hails you",
            EncounterKind.WANDERING_TRUST:
                "A wandering hero offers to join you",
        }
        return labels.get(kind, kind.value)

    def roll(
        self, *, context: EncounterTriggerContext,
        rng: t.Optional[random.Random] = None,
    ) -> t.Optional[EncounterRoll]:
        rng = rng or random.Random()
        profile = self._zone_profiles.get(context.zone_id)
        if profile is None:
            return None
        # Cooldown gate
        last = self._last_encounter_at.get(
            (context.zone_id, context.party_id),
        )
        if (
            last is not None
            and (context.now_seconds - last) < self.cooldown_seconds
        ):
            return None
        # Probability gate
        prob = self._effective_probability(
            ctx=context, profile=profile,
        )
        if rng.random() > prob:
            return None
        tod = time_of_day_for_hour(context.hour_of_day)
        kind = self._pick_kind(
            eligible=profile.eligible_kinds,
            tod=tod, rng=rng,
        )
        if kind is None:
            return None
        mob_count = self._mob_count_for(
            kind=kind, ctx=context, rng=rng,
        )
        roll = EncounterRoll(
            encounter_kind=kind,
            zone_id=context.zone_id,
            triggered_at_seconds=context.now_seconds,
            mob_count=mob_count,
            label=self._label_for(kind=kind, mob_count=mob_count),
        )
        self._last_encounter_at[
            (context.zone_id, context.party_id)
        ] = context.now_seconds
        return roll

    def total_zones(self) -> int:
        return len(self._zone_profiles)


__all__ = [
    "PER_ZONE_COOLDOWN_SECONDS", "DEFAULT_BASE_PROBABILITY",
    "EncounterKind", "TimeOfDay", "time_of_day_for_hour",
    "ZoneEncounterProfile", "EncounterTriggerContext",
    "EncounterRoll", "EncounterScheduler",
]
