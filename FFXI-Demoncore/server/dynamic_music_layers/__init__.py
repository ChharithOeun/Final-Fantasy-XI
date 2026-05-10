"""Dynamic music layers — multi-stem layers with combat-
state crossfade.

Where music_spotting decides "what cue plays on this beat",
this module decides "of the active stems, what gain does
each get RIGHT NOW". Take a Bastok Markets explore stem
(low gain piano + brass), a tension stem (the same brass
but on a low pulse), a light combat stem (drums + the
brass riff with snares), and a heavy combat stem (brass
plus the same drums plus a shouted vocal layer). Stack the
stems on top of each other; let the combat-state crossfade
decide which one is currently audible.

Crossfade rules:
  * threat_level < 3 and not in_combat -> EXPLORATION at 0db.
  * threat_level >= 3 and not in_combat -> TENSION fades in.
  * in_combat -> COMBAT_LIGHT replaces TENSION.
  * threat_level >= 7 and in_combat -> COMBAT_HEAVY
    replaces COMBAT_LIGHT.
  * is_boss_engaged -> BOSS overrides everything.
  * VICTORY plays once on combat-end-with-win.
  * DEFEAT on death.

Stings (one-shots): MAGIC_BURST_STING, SKILLCHAIN_STING
(parameterized by attribute), CRITICAL_HEALTH_STING (party
HP < 25%). Stings ride for 1-3s on top of the layer mix —
should_play_sting() decides whether to fire one for a given
state event.

Public surface
--------------
    LayerKind enum
    StingEvent enum
    MusicLayer dataclass (frozen)
    CombatState dataclass (frozen)
    DynamicMusicLayerSystem
    populate_default_layers
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LayerKind(enum.Enum):
    EXPLORATION = "exploration"
    TENSION = "tension"
    COMBAT_LIGHT = "combat_light"
    COMBAT_HEAVY = "combat_heavy"
    BOSS = "boss"
    VICTORY = "victory"
    DEFEAT = "defeat"
    MOG_HOUSE = "mog_house"
    TOWN_DAY = "town_day"
    TOWN_NIGHT = "town_night"


class StingEvent(enum.Enum):
    MAGIC_BURST = "magic_burst"
    SKILLCHAIN_LIGHT = "skillchain_light"
    SKILLCHAIN_DARKNESS = "skillchain_darkness"
    SKILLCHAIN_FUSION = "skillchain_fusion"
    SKILLCHAIN_FRAGMENTATION = "skillchain_fragmentation"
    SKILLCHAIN_DISTORTION = "skillchain_distortion"
    SKILLCHAIN_GRAVITATION = "skillchain_gravitation"
    SKILLCHAIN_CRYSTAL = "skillchain_crystal"
    SKILLCHAIN_UMBRA = "skillchain_umbra"
    CRITICAL_HEALTH = "critical_health"


@dataclasses.dataclass(frozen=True)
class MusicLayer:
    layer_id: str
    kind: LayerKind
    zone_id: str        # "" = global default
    stem_uri: str
    gain_db_default: float
    low_cut_hz: float
    high_cut_hz: float


@dataclasses.dataclass(frozen=True)
class CombatState:
    player_id: str
    in_combat: bool
    threat_level: float
    nearest_threat_distance_m: float
    is_boss_engaged: bool
    magic_burst_recent: bool
    party_below_25pct_hp: bool


# Below this dB the layer is functionally silent.
SILENT_DB = -60.0


_TOWN_PREFIXES: tuple[str, ...] = (
    "bastok_",
    "south_sandoria",
    "north_sandoria",
    "windurst_",
    "lower_jeuno",
    "upper_jeuno",
    "port_jeuno",
    "ru_lude",
    "norg",
    "selbina",
    "mhaura",
    "aht_urhgan_whitegate",
)


def _is_town_zone(zone_id: str) -> bool:
    if not zone_id:
        return False
    for prefix in _TOWN_PREFIXES:
        if zone_id.startswith(prefix):
            return True
    return False


@dataclasses.dataclass
class DynamicMusicLayerSystem:
    _layers: dict[str, MusicLayer] = dataclasses.field(
        default_factory=dict,
    )
    _by_zone_kind: dict[
        tuple[str, LayerKind], str,
    ] = dataclasses.field(default_factory=dict)
    _global_kind: dict[
        LayerKind, str,
    ] = dataclasses.field(default_factory=dict)
    # most-recent state events for sting decisions
    _last_combat_end_was_win: bool = False

    # ----------------------------------------------- register
    def register_layer(self, layer: MusicLayer) -> None:
        if not layer.layer_id:
            raise ValueError("layer_id required")
        if not layer.stem_uri:
            raise ValueError("stem_uri required")
        if layer.layer_id in self._layers:
            raise ValueError(
                f"duplicate layer_id: {layer.layer_id}",
            )
        if layer.high_cut_hz <= layer.low_cut_hz:
            raise ValueError(
                "high_cut_hz must exceed low_cut_hz",
            )
        if not (-60.0 <= layer.gain_db_default <= 12.0):
            raise ValueError(
                "gain_db_default must be in -60..12",
            )
        self._layers[layer.layer_id] = layer
        if layer.zone_id:
            key = (layer.zone_id, layer.kind)
            self._by_zone_kind[key] = layer.layer_id
        else:
            self._global_kind[layer.kind] = layer.layer_id

    def get_layer(self, layer_id: str) -> MusicLayer:
        if layer_id not in self._layers:
            raise KeyError(f"unknown layer_id: {layer_id}")
        return self._layers[layer_id]

    def layer_count(self) -> int:
        return len(self._layers)

    def resolve_layer(
        self, kind: LayerKind, zone_id: str,
    ) -> t.Optional[MusicLayer]:
        """Zone-specific override beats global default."""
        if zone_id and (zone_id, kind) in self._by_zone_kind:
            return self._layers[
                self._by_zone_kind[(zone_id, kind)]
            ]
        if kind in self._global_kind:
            return self._layers[self._global_kind[kind]]
        return None

    # ----------------------------------------------- target_gains
    def target_gains(
        self,
        zone_id: str,
        combat_state: CombatState,
        weather: str = "clear",
        time_of_day: str = "day",
    ) -> dict[LayerKind, float]:
        """Return target gain per layer kind for the
        crossfade engine.

        Returns dB values; SILENT_DB means "silent".
        """
        del weather  # reserved for future weather-specific stems
        gains: dict[LayerKind, float] = {
            LayerKind.EXPLORATION: SILENT_DB,
            LayerKind.TENSION: SILENT_DB,
            LayerKind.COMBAT_LIGHT: SILENT_DB,
            LayerKind.COMBAT_HEAVY: SILENT_DB,
            LayerKind.BOSS: SILENT_DB,
            LayerKind.VICTORY: SILENT_DB,
            LayerKind.DEFEAT: SILENT_DB,
            LayerKind.MOG_HOUSE: SILENT_DB,
            LayerKind.TOWN_DAY: SILENT_DB,
            LayerKind.TOWN_NIGHT: SILENT_DB,
        }
        # Boss overrides everything.
        if combat_state.is_boss_engaged:
            gains[LayerKind.BOSS] = self._gain_for(
                LayerKind.BOSS, zone_id,
            )
            return gains
        # Combat states.
        if combat_state.in_combat:
            if combat_state.threat_level >= 7.0:
                gains[LayerKind.COMBAT_HEAVY] = self._gain_for(
                    LayerKind.COMBAT_HEAVY, zone_id,
                )
            else:
                gains[LayerKind.COMBAT_LIGHT] = self._gain_for(
                    LayerKind.COMBAT_LIGHT, zone_id,
                )
            return gains
        # Out of combat.
        if combat_state.threat_level >= 3.0:
            gains[LayerKind.TENSION] = self._gain_for(
                LayerKind.TENSION, zone_id,
            )
            return gains
        # Idle: pick exploration / town / mog by zone
        # signal. Mog House zones win the mog stem; town
        # zones (zone_id starts with bastok/sandy/windurst/
        # jeuno/norg/whitegate prefixes) win the town stems
        # by tod; everything else gets exploration.
        if zone_id.startswith("mog_house"):
            gains[LayerKind.MOG_HOUSE] = self._gain_for(
                LayerKind.MOG_HOUSE, zone_id,
            )
            return gains
        if _is_town_zone(zone_id):
            tod_kind = (
                LayerKind.TOWN_DAY if time_of_day == "day"
                else LayerKind.TOWN_NIGHT
            )
            if self.resolve_layer(tod_kind, zone_id) is not None:
                gains[tod_kind] = self._gain_for(
                    tod_kind, zone_id,
                )
                return gains
        gains[LayerKind.EXPLORATION] = self._gain_for(
            LayerKind.EXPLORATION, zone_id,
        )
        return gains

    def _gain_for(
        self, kind: LayerKind, zone_id: str,
    ) -> float:
        layer = self.resolve_layer(kind, zone_id)
        if layer is None:
            return SILENT_DB
        return layer.gain_db_default

    # --------------------------------------- transition_to
    def transition_to(
        self,
        state_change_event: str,
        won: bool = True,
    ) -> tuple[LayerKind, ...]:
        """Identify which layer kinds activate on a
        state-change event. Returns the new active kinds.
        """
        ev = state_change_event.lower()
        if ev == "combat_start":
            return (LayerKind.COMBAT_LIGHT,)
        if ev == "combat_end":
            self._last_combat_end_was_win = won
            return (
                (LayerKind.VICTORY,) if won
                else (LayerKind.DEFEAT,)
            )
        if ev == "boss_engage":
            return (LayerKind.BOSS,)
        if ev == "death":
            return (LayerKind.DEFEAT,)
        if ev == "zone_enter":
            return (LayerKind.EXPLORATION,)
        if ev == "mog_house_enter":
            return (LayerKind.MOG_HOUSE,)
        raise ValueError(
            f"unknown state_change_event: {state_change_event}",
        )

    # --------------------------------------- stings
    def should_play_sting(
        self, state_event: StingEvent,
        combat_state: t.Optional[CombatState] = None,
    ) -> bool:
        """True if the sting should fire given the current
        state (the caller decided the event is happening;
        we decide if the sting layer should ride)."""
        if state_event == StingEvent.MAGIC_BURST:
            if combat_state is None:
                return True
            return combat_state.magic_burst_recent
        if state_event == StingEvent.CRITICAL_HEALTH:
            if combat_state is None:
                return False
            return combat_state.party_below_25pct_hp
        # Skillchain stings always fire when invoked.
        return True

    def all_layers_for_zone(
        self, zone_id: str,
    ) -> tuple[MusicLayer, ...]:
        out: list[MusicLayer] = []
        # Zone-specific overrides + globals not overridden.
        seen_kinds: set[LayerKind] = set()
        for (zid, kind), lid in self._by_zone_kind.items():
            if zid == zone_id:
                out.append(self._layers[lid])
                seen_kinds.add(kind)
        for kind, lid in self._global_kind.items():
            if kind not in seen_kinds:
                out.append(self._layers[lid])
        return tuple(
            sorted(out, key=lambda l: (l.kind.value, l.layer_id))
        )


# ---------------------------------------------------------
# Default layers — global stems for every kind.
# ---------------------------------------------------------

# (layer_id, kind, zone_id, stem_uri,
#  gain_db_default, low_cut_hz, high_cut_hz)
_DEFAULT_LAYERS: tuple[
    tuple[str, LayerKind, str, str, float, float, float], ...
] = (
    ("global_exploration",
        LayerKind.EXPLORATION, "",
        "music/layers/global_exploration.ogg",
        -6.0, 40.0, 16000.0),
    ("global_tension",
        LayerKind.TENSION, "",
        "music/layers/global_tension.ogg",
        -8.0, 40.0, 16000.0),
    ("global_combat_light",
        LayerKind.COMBAT_LIGHT, "",
        "music/layers/global_combat_light.ogg",
        -4.0, 40.0, 16000.0),
    ("global_combat_heavy",
        LayerKind.COMBAT_HEAVY, "",
        "music/layers/global_combat_heavy.ogg",
        -2.0, 40.0, 18000.0),
    ("global_boss",
        LayerKind.BOSS, "",
        "music/layers/global_boss.ogg",
        -1.0, 40.0, 18000.0),
    ("global_victory",
        LayerKind.VICTORY, "",
        "music/layers/global_victory.ogg",
        -2.0, 40.0, 16000.0),
    ("global_defeat",
        LayerKind.DEFEAT, "",
        "music/layers/global_defeat.ogg",
        -4.0, 30.0, 12000.0),
    ("global_mog_house",
        LayerKind.MOG_HOUSE, "",
        "music/layers/global_mog_house.ogg",
        -8.0, 60.0, 14000.0),
    ("global_town_day",
        LayerKind.TOWN_DAY, "",
        "music/layers/global_town_day.ogg",
        -6.0, 40.0, 16000.0),
    ("global_town_night",
        LayerKind.TOWN_NIGHT, "",
        "music/layers/global_town_night.ogg",
        -8.0, 40.0, 14000.0),
    # zone-specific
    ("bastok_markets_combat_light",
        LayerKind.COMBAT_LIGHT, "bastok_markets",
        "music/layers/bastok_markets_combat_light.ogg",
        -3.0, 40.0, 16000.0),
    ("iron_eater_boss",
        LayerKind.BOSS, "bastok_markets",
        "music/layers/iron_eater_boss.ogg",
        -1.0, 40.0, 18000.0),
)


def populate_default_layers(sys: DynamicMusicLayerSystem) -> int:
    n = 0
    for (lid, kind, zid, stem,
         gain, lc, hc) in _DEFAULT_LAYERS:
        sys.register_layer(MusicLayer(
            layer_id=lid,
            kind=kind,
            zone_id=zid,
            stem_uri=stem,
            gain_db_default=gain,
            low_cut_hz=lc,
            high_cut_hz=hc,
        ))
        n += 1
    return n


__all__ = [
    "LayerKind",
    "StingEvent",
    "MusicLayer",
    "CombatState",
    "DynamicMusicLayerSystem",
    "populate_default_layers",
    "SILENT_DB",
]
