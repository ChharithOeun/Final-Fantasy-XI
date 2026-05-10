"""Music spotting — the conductor that synchronizes cues
to gameplay beats.

Spotting is the film-scoring term for "what music plays
exactly here". A composer hands the editor a list of cues:
when the door opens, swell into the love theme; when the
hero draws his sword, hit the brass sting; on the cut to
black, fade out. This module is that list, made playable
in real time.

Cues fire on triggers — ZONE_ENTER, COMBAT_START, MAGIC_
BURST_FIRED, SKILLCHAIN_CLOSED, BOSS_INTRO_TRIGGER,
DIALOGUE_LINE_STARTED, PLAYER_DEATH, LEVEL_UP, NIGHT_FALLS,
WEATHER_CHANGED, plus showcase-choreography beat overrides.
Each cue carries a layer (BASE always plays; TENSION fades
in when threats nearby; COMBAT replaces TENSION on engage;
BOSS replaces COMBAT on boss-engage; stings ride for 2-6s
on top), a fade_in/out_ms, a priority (0..10) that wins on
collision within the same layer, and a loop flag.

Spot inheritance: a zone has a default BASE stem; a
showcase_choreography beat can override it for the duration
of the beat (the bandit raid swaps Bastok Markets' day-
march for a fast tension cut). When the beat ends, the
override is released and the zone's BASE stem fades back
in.

The module owns *cue selection* — what plays, when, at
what fade. It does NOT own the actual audio mixer — that's
surround_audio_mixer. Cues are emitted as plans the mixer
consumes.

Public surface
--------------
    SpotTrigger enum
    SpotLayer enum
    SpotCue dataclass (frozen)
    SpotPlan dataclass (frozen)
    MusicSpottingSystem
    populate_default_cues
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SpotTrigger(enum.Enum):
    ZONE_ENTER = "zone_enter"
    SHOWCASE_BEAT = "showcase_beat"
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    BOSS_INTRO_TRIGGER = "boss_intro_trigger"
    MAGIC_BURST_FIRED = "magic_burst_fired"
    SKILLCHAIN_CLOSED = "skillchain_closed"
    DIALOGUE_LINE_STARTED = "dialogue_line_started"
    PLAYER_DEATH = "player_death"
    LEVEL_UP = "level_up"
    NIGHT_FALLS = "night_falls"
    WEATHER_CHANGED = "weather_changed"


class SpotLayer(enum.Enum):
    BASE = "base"
    TENSION = "tension"
    COMBAT = "combat"
    BOSS = "boss"
    VICTORY = "victory"
    DEFEAT = "defeat"
    DIALOGUE_STING = "dialogue_sting"
    REVEAL_STING = "reveal_sting"


# Layer priority order — higher number wins as the
# "currently playing" foreground when multiple layers are
# eligible.
_LAYER_PRIORITY: dict[SpotLayer, int] = {
    SpotLayer.BASE: 1,
    SpotLayer.TENSION: 3,
    SpotLayer.COMBAT: 5,
    SpotLayer.BOSS: 7,
    SpotLayer.VICTORY: 4,
    SpotLayer.DEFEAT: 6,
    SpotLayer.DIALOGUE_STING: 2,
    SpotLayer.REVEAL_STING: 2,
}


# Stings overlay rather than replace; they don't suppress
# the layer beneath.
_STING_LAYERS: frozenset[SpotLayer] = frozenset({
    SpotLayer.DIALOGUE_STING,
    SpotLayer.REVEAL_STING,
})


@dataclasses.dataclass(frozen=True)
class SpotCue:
    cue_id: str
    trigger_kind: SpotTrigger
    music_stem_uri: str
    fade_in_ms: int
    fade_out_ms: int
    layer: SpotLayer
    priority: int
    loop: bool
    zone_id: str = ""        # optional — empty means any
    context_tag: str = ""    # optional — discriminator key


@dataclasses.dataclass(frozen=True)
class SpotPlan:
    cue_id: str
    music_stem_uri: str
    layer: SpotLayer
    fade_in_ms: int
    fade_out_ms: int
    loop: bool


@dataclasses.dataclass
class MusicSpottingSystem:
    _cues: dict[str, SpotCue] = dataclasses.field(
        default_factory=dict,
    )
    _by_trigger: dict[
        SpotTrigger, list[str],
    ] = dataclasses.field(default_factory=dict)
    _zone_base: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- register
    def register_cue(self, cue: SpotCue) -> None:
        if not cue.cue_id:
            raise ValueError("cue_id required")
        if cue.cue_id in self._cues:
            raise ValueError(
                f"duplicate cue_id: {cue.cue_id}",
            )
        if not (0 <= cue.priority <= 10):
            raise ValueError("priority must be in 0..10")
        if cue.fade_in_ms < 0 or cue.fade_out_ms < 0:
            raise ValueError("fade times must be >= 0")
        if not cue.music_stem_uri:
            raise ValueError("music_stem_uri required")
        self._cues[cue.cue_id] = cue
        self._by_trigger.setdefault(
            cue.trigger_kind, [],
        ).append(cue.cue_id)
        # ZONE_ENTER + BASE = canonical zone-base stem
        if (
            cue.trigger_kind == SpotTrigger.ZONE_ENTER
            and cue.layer == SpotLayer.BASE
            and cue.zone_id
        ):
            self._zone_base[cue.zone_id] = cue.cue_id

    def get_cue(self, cue_id: str) -> SpotCue:
        if cue_id not in self._cues:
            raise KeyError(f"unknown cue_id: {cue_id}")
        return self._cues[cue_id]

    def cue_count(self) -> int:
        return len(self._cues)

    # ---------------------------------------------- fire
    def fire(
        self,
        trigger_kind: SpotTrigger,
        context: t.Mapping[str, t.Any] | None = None,
    ) -> tuple[SpotPlan, ...]:
        ctx = dict(context or {})
        zone_id = ctx.get("zone_id", "")
        context_tag = ctx.get("context_tag", "")
        candidates = [
            self._cues[cid]
            for cid in self._by_trigger.get(trigger_kind, [])
        ]
        # Filter by zone/tag if provided on the cue.
        filtered: list[SpotCue] = []
        for cue in candidates:
            if cue.zone_id and zone_id and cue.zone_id != zone_id:
                continue
            if (
                cue.context_tag and context_tag
                and cue.context_tag != context_tag
            ):
                continue
            filtered.append(cue)
        # If a context_tag is provided, prefer tag-matching
        # cues (drop cues with empty tag when any tagged
        # match exists for the same layer).
        if context_tag:
            tagged_layers = {
                c.layer for c in filtered if c.context_tag
            }
            filtered = [
                c for c in filtered
                if c.context_tag or c.layer not in tagged_layers
            ]
        # Group per layer; within a layer, highest priority
        # wins; ties break alphabetically by cue_id for
        # determinism.
        per_layer: dict[SpotLayer, SpotCue] = {}
        for cue in filtered:
            cur = per_layer.get(cue.layer)
            if (
                cur is None
                or cue.priority > cur.priority
                or (
                    cue.priority == cur.priority
                    and cue.cue_id < cur.cue_id
                )
            ):
                per_layer[cue.layer] = cue
        # Emit a SpotPlan for every winning cue, ordered by
        # layer priority then cue_id.
        winners = sorted(
            per_layer.values(),
            key=lambda c: (
                -_LAYER_PRIORITY[c.layer], c.cue_id,
            ),
        )
        return tuple(
            SpotPlan(
                cue_id=c.cue_id,
                music_stem_uri=c.music_stem_uri,
                layer=c.layer,
                fade_in_ms=c.fade_in_ms,
                fade_out_ms=c.fade_out_ms,
                loop=c.loop,
            )
            for c in winners
        )

    # ---------------------------------------------- queries
    def currently_playing(
        self,
        zone_id: str,
        combat_state: t.Mapping[str, t.Any] | None = None,
    ) -> tuple[SpotLayer, ...]:
        cs = dict(combat_state or {})
        layers: list[SpotLayer] = [SpotLayer.BASE]
        threat = float(cs.get("threat_level", 0.0))
        in_combat = bool(cs.get("in_combat", False))
        boss = bool(cs.get("is_boss_engaged", False))
        if threat >= 3.0 and not in_combat:
            layers.append(SpotLayer.TENSION)
        if in_combat and not boss:
            # combat replaces tension
            layers = [
                l for l in layers if l != SpotLayer.TENSION
            ]
            layers.append(SpotLayer.COMBAT)
        if boss:
            layers = [
                l for l in layers
                if l not in (SpotLayer.TENSION, SpotLayer.COMBAT)
            ]
            layers.append(SpotLayer.BOSS)
        # zone_id is honored by callers picking from
        # zone_base; we just expose layer hierarchy.
        del zone_id  # not used in layer derivation
        return tuple(layers)

    def transition_to(
        self, layer: SpotLayer, cue_id: str,
    ) -> SpotPlan:
        cue = self.get_cue(cue_id)
        if cue.layer != layer:
            raise ValueError(
                f"cue {cue_id} is layer {cue.layer.value}, "
                f"not {layer.value}",
            )
        return SpotPlan(
            cue_id=cue.cue_id,
            music_stem_uri=cue.music_stem_uri,
            layer=cue.layer,
            fade_in_ms=cue.fade_in_ms,
            fade_out_ms=cue.fade_out_ms,
            loop=cue.loop,
        )

    def all_cues_for_layer(
        self, layer: SpotLayer,
    ) -> tuple[SpotCue, ...]:
        return tuple(
            sorted(
                (c for c in self._cues.values() if c.layer == layer),
                key=lambda c: c.cue_id,
            )
        )

    def cue_priority_for(
        self, trigger_kind: SpotTrigger,
    ) -> int:
        cues = [
            self._cues[cid]
            for cid in self._by_trigger.get(trigger_kind, [])
        ]
        if not cues:
            return 0
        return max(c.priority for c in cues)

    def zone_base_cue(self, zone_id: str) -> str:
        return self._zone_base.get(zone_id, "")

    def is_sting(self, layer: SpotLayer) -> bool:
        return layer in _STING_LAYERS


# ---------------------------------------------------------
# Default catalog — 30+ canonical cues pre-populated.
# ---------------------------------------------------------

# (cue_id, trigger, stem_uri, fade_in_ms, fade_out_ms,
#  layer, priority, loop, zone_id, context_tag)
_DEFAULT_CUES: tuple[
    tuple[
        str, SpotTrigger, str, int, int,
        SpotLayer, int, bool, str, str,
    ],
    ...,
] = (
    # ---- Zone BASE stems ----
    ("base_bastok_mines",
        SpotTrigger.ZONE_ENTER,
        "music/base/bastok_mines_industrial_march.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "bastok_mines", ""),
    ("base_bastok_markets",
        SpotTrigger.ZONE_ENTER,
        "music/base/bastok_markets_vanadiel_march.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "bastok_markets", ""),
    ("base_bastok_metalworks",
        SpotTrigger.ZONE_ENTER,
        "music/base/bastok_metalworks_anvil_theme.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "bastok_metalworks", ""),
    ("base_south_sandoria",
        SpotTrigger.ZONE_ENTER,
        "music/base/sandoria_kingdom_chorale.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "south_sandoria", ""),
    ("base_north_sandoria",
        SpotTrigger.ZONE_ENTER,
        "music/base/sandoria_kingdom_chorale.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "north_sandoria", ""),
    ("base_windurst_woods",
        SpotTrigger.ZONE_ENTER,
        "music/base/windurst_chime_pavilion.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "windurst_woods", ""),
    ("base_windurst_walls",
        SpotTrigger.ZONE_ENTER,
        "music/base/windurst_chime_pavilion.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "windurst_walls", ""),
    ("base_norg",
        SpotTrigger.ZONE_ENTER,
        "music/base/norg_pirate_haven.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "norg", ""),
    ("base_lower_jeuno",
        SpotTrigger.ZONE_ENTER,
        "music/base/jeuno_neutral_sway.ogg",
        2400, 1600, SpotLayer.BASE, 5, True,
        "lower_jeuno", ""),
    ("base_konschtat",
        SpotTrigger.ZONE_ENTER,
        "music/base/konschtat_open_winds.ogg",
        3000, 2000, SpotLayer.BASE, 5, True,
        "konschtat_highlands", ""),
    ("base_pashhow",
        SpotTrigger.ZONE_ENTER,
        "music/base/pashhow_marshlands_bog.ogg",
        3000, 2000, SpotLayer.BASE, 5, True,
        "pashhow_marshlands", ""),
    ("base_jugner",
        SpotTrigger.ZONE_ENTER,
        "music/base/jugner_forest_horns.ogg",
        3000, 2000, SpotLayer.BASE, 5, True,
        "jugner_forest", ""),
    # ---- Combat themes (light/medium/heavy) ----
    ("combat_light_default",
        SpotTrigger.COMBAT_START,
        "music/combat/battle_theme_light.ogg",
        300, 800, SpotLayer.COMBAT, 5, True,
        "", "light"),
    ("combat_medium_default",
        SpotTrigger.COMBAT_START,
        "music/combat/battle_theme_medium.ogg",
        300, 800, SpotLayer.COMBAT, 6, True,
        "", "medium"),
    ("combat_heavy_default",
        SpotTrigger.COMBAT_START,
        "music/combat/battle_theme_heavy.ogg",
        300, 800, SpotLayer.COMBAT, 7, True,
        "", "heavy"),
    # ---- Tension layer ----
    ("tension_threat_nearby",
        SpotTrigger.COMBAT_START,
        "music/tension/threat_pulse.ogg",
        1200, 1600, SpotLayer.TENSION, 4, True, "", ""),
    # ---- Boss themes ----
    ("boss_iron_eater",
        SpotTrigger.BOSS_INTRO_TRIGGER,
        "music/boss/iron_eater_ridill_theme.ogg",
        600, 1200, SpotLayer.BOSS, 9, True,
        "", "iron_eater"),
    ("boss_default",
        SpotTrigger.BOSS_INTRO_TRIGGER,
        "music/boss/awakening_theme.ogg",
        600, 1200, SpotLayer.BOSS, 8, True, "", ""),
    # ---- Stings ----
    ("sting_magic_burst",
        SpotTrigger.MAGIC_BURST_FIRED,
        "music/stings/magic_burst_brass.ogg",
        50, 800, SpotLayer.REVEAL_STING, 8, False, "", ""),
    ("sting_skillchain_light",
        SpotTrigger.SKILLCHAIN_CLOSED,
        "music/stings/skillchain_light_choir.ogg",
        50, 1200, SpotLayer.REVEAL_STING, 8, False,
        "", "light"),
    ("sting_skillchain_darkness",
        SpotTrigger.SKILLCHAIN_CLOSED,
        "music/stings/skillchain_darkness_low_brass.ogg",
        50, 1200, SpotLayer.REVEAL_STING, 8, False,
        "", "darkness"),
    ("sting_skillchain_crystal",
        SpotTrigger.SKILLCHAIN_CLOSED,
        "music/stings/skillchain_crystal_prism.ogg",
        50, 1500, SpotLayer.REVEAL_STING, 9, False,
        "", "crystal"),
    ("sting_skillchain_umbra",
        SpotTrigger.SKILLCHAIN_CLOSED,
        "music/stings/skillchain_umbra_void.ogg",
        50, 1500, SpotLayer.REVEAL_STING, 9, False,
        "", "umbra"),
    ("sting_dialogue_emotional",
        SpotTrigger.DIALOGUE_LINE_STARTED,
        "music/stings/dialogue_strings_warm.ogg",
        300, 1500, SpotLayer.DIALOGUE_STING, 6, False,
        "", "emotional"),
    ("sting_dialogue_comedic",
        SpotTrigger.DIALOGUE_LINE_STARTED,
        "music/stings/dialogue_pizzicato_wink.ogg",
        200, 800, SpotLayer.DIALOGUE_STING, 6, False,
        "", "comedic"),
    ("sting_dialogue_menacing",
        SpotTrigger.DIALOGUE_LINE_STARTED,
        "music/stings/dialogue_low_drone.ogg",
        300, 1500, SpotLayer.DIALOGUE_STING, 7, False,
        "", "menacing"),
    ("sting_weather_change",
        SpotTrigger.WEATHER_CHANGED,
        "music/stings/weather_shift_aerial.ogg",
        400, 1200, SpotLayer.REVEAL_STING, 5, False, "", ""),
    ("sting_level_up",
        SpotTrigger.LEVEL_UP,
        "music/stings/level_up_fanfare.ogg",
        100, 1500, SpotLayer.REVEAL_STING, 9, False, "", ""),
    ("sting_night_falls",
        SpotTrigger.NIGHT_FALLS,
        "music/stings/night_falls_ambient_pad.ogg",
        2000, 2000, SpotLayer.REVEAL_STING, 4, False, "", ""),
    # ---- Victory / Defeat ----
    ("victory_default",
        SpotTrigger.COMBAT_END,
        "music/victory/victory_fanfare.ogg",
        100, 1500, SpotLayer.VICTORY, 7, False, "", "victory"),
    ("defeat_default",
        SpotTrigger.PLAYER_DEATH,
        "music/defeat/defeat_low_strings.ogg",
        500, 2000, SpotLayer.DEFEAT, 9, False, "", ""),
    # ---- Showcase beat overrides ----
    ("showcase_bandit_raid",
        SpotTrigger.SHOWCASE_BEAT,
        "music/beats/bandit_raid_kinetic.ogg",
        400, 1000, SpotLayer.COMBAT, 8, True,
        "bastok_markets", "bandit_raid"),
    ("showcase_market_dawn",
        SpotTrigger.SHOWCASE_BEAT,
        "music/beats/market_dawn_strings.ogg",
        2000, 2000, SpotLayer.BASE, 6, True,
        "bastok_markets", "market_dawn"),
)


def populate_default_cues(sys: MusicSpottingSystem) -> int:
    n = 0
    for row in _DEFAULT_CUES:
        (cue_id, trigger, stem, fi, fo, layer,
         prio, loop, zid, tag) = row
        sys.register_cue(SpotCue(
            cue_id=cue_id,
            trigger_kind=trigger,
            music_stem_uri=stem,
            fade_in_ms=fi,
            fade_out_ms=fo,
            layer=layer,
            priority=prio,
            loop=loop,
            zone_id=zid,
            context_tag=tag,
        ))
        n += 1
    return n


__all__ = [
    "SpotTrigger",
    "SpotLayer",
    "SpotCue",
    "SpotPlan",
    "MusicSpottingSystem",
    "populate_default_cues",
]
