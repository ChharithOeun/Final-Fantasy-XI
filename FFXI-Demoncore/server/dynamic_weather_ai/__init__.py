"""Dynamic weather AI — weather drives AI decisions.

Distinct from terrain_weather (mechanical effect modifiers like
fire-day amp). This layer is the AI BRAIN that says: "It's raining
in Sarutabaruta, so the orc patrols are sheltered, the merchants
delay caravan launch, the fishermen stayed home, and the dragon
NM is more likely to roost."

The world's brains read live weather and adjust schedules,
ambushes, route choices, mood baselines, and prey availability.

Public surface
--------------
    WeatherKind enum
    WeatherIntensity enum
    WeatherSnapshot dataclass
    AIWeatherDirective dataclass — what the AI brain should do
    DynamicWeatherAI
        .observe(zone_id, weather, intensity)
        .directive_for(actor_kind, zone_id) -> AIWeatherDirective
        .clear(zone_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class WeatherKind(str, enum.Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    THUNDER = "thunder"
    SNOW = "snow"
    BLIZZARD = "blizzard"
    SANDSTORM = "sandstorm"
    HEATWAVE = "heatwave"
    FOG = "fog"
    AURORA = "aurora"


class WeatherIntensity(str, enum.Enum):
    NONE = "none"           # background weather only
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    EXTREME = "extreme"     # rare; world-shaping


# Canonical actor types whose AI cares about weather.
class ActorKind(str, enum.Enum):
    BEASTMAN_PATROL = "beastman_patrol"
    MERCHANT_CARAVAN = "merchant_caravan"
    FISHERMAN_NPC = "fisherman_npc"
    FARMER_NPC = "farmer_npc"
    DRAGON_NM = "dragon_nm"
    BIRD_FLOCK = "bird_flock"
    PLAYER_GUARD_NPC = "player_guard_npc"


@dataclasses.dataclass(frozen=True)
class WeatherSnapshot:
    zone_id: str
    kind: WeatherKind
    intensity: WeatherIntensity = WeatherIntensity.LIGHT
    observed_at_seconds: float = 0.0
    is_night: bool = False


@dataclasses.dataclass(frozen=True)
class AIWeatherDirective:
    """What an AI brain should do given current weather."""
    actor_kind: ActorKind
    zone_id: str
    take_shelter: bool = False
    delay_route: bool = False
    aggression_mod_pct: int = 0       # +/- aggression
    speed_mod_pct: int = 0            # +/- movement speed
    visibility_mod_pct: int = 0       # +/- vision range
    mood_shift: str = ""              # short label
    notes: str = ""


# Internal directive table — keyed by (actor, weather, intensity).
# Returns a dict of overrides applied to a base AIWeatherDirective.
_DIRECTIVE_TABLE: dict[
    tuple[ActorKind, WeatherKind, WeatherIntensity],
    dict[str, t.Any],
] = {
    # Beastmen patrols shelter in heavy rain/snow, fight harder
    # in their preferred element.
    (
        ActorKind.BEASTMAN_PATROL, WeatherKind.RAIN,
        WeatherIntensity.HEAVY,
    ): {
        "take_shelter": True, "speed_mod_pct": -30,
        "mood_shift": "miserable",
    },
    (
        ActorKind.BEASTMAN_PATROL, WeatherKind.RAIN,
        WeatherIntensity.EXTREME,
    ): {
        "take_shelter": True, "delay_route": True,
        "speed_mod_pct": -50, "mood_shift": "miserable",
    },
    (
        ActorKind.BEASTMAN_PATROL, WeatherKind.THUNDER,
        WeatherIntensity.HEAVY,
    ): {
        "take_shelter": True, "aggression_mod_pct": -20,
        "mood_shift": "spooked",
    },
    (
        ActorKind.BEASTMAN_PATROL, WeatherKind.SANDSTORM,
        WeatherIntensity.HEAVY,
    ): {
        "speed_mod_pct": -25, "visibility_mod_pct": -60,
        "aggression_mod_pct": +10,
        "notes": "thrives in sandstorm; ambush from cover",
    },

    # Merchant caravans delay or detour in bad weather.
    (
        ActorKind.MERCHANT_CARAVAN, WeatherKind.RAIN,
        WeatherIntensity.HEAVY,
    ): {
        "delay_route": True, "mood_shift": "anxious",
    },
    (
        ActorKind.MERCHANT_CARAVAN, WeatherKind.SNOW,
        WeatherIntensity.HEAVY,
    ): {
        "delay_route": True, "speed_mod_pct": -50,
        "mood_shift": "anxious",
    },
    (
        ActorKind.MERCHANT_CARAVAN, WeatherKind.BLIZZARD,
        WeatherIntensity.HEAVY,
    ): {
        "delay_route": True, "take_shelter": True,
        "mood_shift": "frightened",
    },
    (
        ActorKind.MERCHANT_CARAVAN, WeatherKind.BLIZZARD,
        WeatherIntensity.EXTREME,
    ): {
        "delay_route": True, "take_shelter": True,
        "mood_shift": "terrified",
    },
    (
        ActorKind.MERCHANT_CARAVAN, WeatherKind.SANDSTORM,
        WeatherIntensity.HEAVY,
    ): {
        "delay_route": True, "take_shelter": True,
        "visibility_mod_pct": -80, "mood_shift": "panicked",
    },

    # Fishermen stay home in storms.
    (
        ActorKind.FISHERMAN_NPC, WeatherKind.THUNDER,
        WeatherIntensity.MODERATE,
    ): {
        "take_shelter": True, "mood_shift": "cautious",
    },
    (
        ActorKind.FISHERMAN_NPC, WeatherKind.THUNDER,
        WeatherIntensity.HEAVY,
    ): {
        "take_shelter": True, "delay_route": True,
        "mood_shift": "anxious",
    },
    (
        ActorKind.FISHERMAN_NPC, WeatherKind.RAIN,
        WeatherIntensity.LIGHT,
    ): {
        "mood_shift": "lucky",
        "notes": "light rain = good fishing",
    },

    # Farmers love light rain, fear sandstorms.
    (
        ActorKind.FARMER_NPC, WeatherKind.RAIN,
        WeatherIntensity.LIGHT,
    ): {
        "mood_shift": "content",
        "notes": "good for crops",
    },
    (
        ActorKind.FARMER_NPC, WeatherKind.SANDSTORM,
        WeatherIntensity.HEAVY,
    ): {
        "delay_route": True, "mood_shift": "alarmed",
        "notes": "storm threatens harvest",
    },
    (
        ActorKind.FARMER_NPC, WeatherKind.HEATWAVE,
        WeatherIntensity.HEAVY,
    ): {
        "speed_mod_pct": -20, "mood_shift": "exhausted",
    },

    # Dragon NMs roost in calm; aggressive in thunder.
    (
        ActorKind.DRAGON_NM, WeatherKind.THUNDER,
        WeatherIntensity.HEAVY,
    ): {
        "aggression_mod_pct": +30,
        "notes": "drawn to lightning",
    },
    (
        ActorKind.DRAGON_NM, WeatherKind.AURORA,
        WeatherIntensity.MODERATE,
    ): {
        "aggression_mod_pct": +20,
        "notes": "primal awakening",
    },
    (
        ActorKind.DRAGON_NM, WeatherKind.CLEAR,
        WeatherIntensity.NONE,
    ): {
        "mood_shift": "roosting",
    },

    # Bird flocks scatter in thunder/blizzard.
    (
        ActorKind.BIRD_FLOCK, WeatherKind.THUNDER,
        WeatherIntensity.HEAVY,
    ): {
        "take_shelter": True, "mood_shift": "scattered",
    },
    (
        ActorKind.BIRD_FLOCK, WeatherKind.BLIZZARD,
        WeatherIntensity.HEAVY,
    ): {
        "take_shelter": True,
    },
    (
        ActorKind.BIRD_FLOCK, WeatherKind.FOG,
        WeatherIntensity.HEAVY,
    ): {
        "visibility_mod_pct": -40,
    },

    # Player guards push patrol in fog (covers approach).
    (
        ActorKind.PLAYER_GUARD_NPC, WeatherKind.FOG,
        WeatherIntensity.HEAVY,
    ): {
        "aggression_mod_pct": +15, "visibility_mod_pct": -30,
        "notes": "fog cover for ambushers",
    },
    (
        ActorKind.PLAYER_GUARD_NPC, WeatherKind.CLEAR,
        WeatherIntensity.NONE,
    ): {
        "mood_shift": "alert",
    },
}


@dataclasses.dataclass
class DynamicWeatherAI:
    _zones: dict[str, WeatherSnapshot] = dataclasses.field(
        default_factory=dict,
    )

    def observe(
        self, *, snapshot: WeatherSnapshot,
    ) -> None:
        self._zones[snapshot.zone_id] = snapshot

    def current(
        self, zone_id: str,
    ) -> t.Optional[WeatherSnapshot]:
        return self._zones.get(zone_id)

    def clear(self, zone_id: str) -> bool:
        if zone_id not in self._zones:
            return False
        del self._zones[zone_id]
        return True

    def directive_for(
        self, *, actor_kind: ActorKind, zone_id: str,
    ) -> AIWeatherDirective:
        snap = self._zones.get(zone_id)
        if snap is None:
            return AIWeatherDirective(
                actor_kind=actor_kind, zone_id=zone_id,
            )
        key = (actor_kind, snap.kind, snap.intensity)
        overrides = _DIRECTIVE_TABLE.get(key, {})
        # Tweak: night amplifies blizzard/sandstorm shelter
        # for caravans/fishermen.
        if snap.is_night and overrides:
            if "speed_mod_pct" in overrides:
                overrides = dict(overrides)
                overrides["speed_mod_pct"] = int(
                    overrides["speed_mod_pct"] * 1.2,
                )
        base = AIWeatherDirective(
            actor_kind=actor_kind, zone_id=zone_id,
        )
        return dataclasses.replace(base, **overrides)

    def total_zones_observed(self) -> int:
        return len(self._zones)


__all__ = [
    "WeatherKind", "WeatherIntensity", "ActorKind",
    "WeatherSnapshot", "AIWeatherDirective",
    "DynamicWeatherAI",
]
