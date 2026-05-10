"""Zone pattern template — propagate the Bastok Markets demo
pattern across every zone in the atlas.

The Bastok Markets demo (the previous batch's deliverable —
asset_upgrade_pipeline + character_model_library + zone_dressing
+ showcase_choreography + demo_packaging) proved that a single
zone, fully dressed and choreographed, hits live-action quality.
This module *codifies* that pattern as a reusable template
applied to other zones at the right scale for each archetype.

Six archetypes:
    NATION_CAPITAL     — Bastok-style; dense, cinematic, vendor-heavy
    OUTPOST_TOWN       — Selbina-style; small, cozy, rest-stop
    OPEN_FIELD         — Konschtat-style; wide, atmospheric, low NPC
    DUNGEON_DARK       — Crawlers' Nest; claustrophobic, deep shadows
    BEASTMAN_FORTRESS  — Davoi; green-tinted, hostile, prop-heavy
    ENDGAME_INSTANCE   — Sky/Sea; exotic, surreal lighting

Per-zone application is *skeletal*: this module records WHAT to
build (target counts, archetype mix). The actual asset records
live in zone_dressing / character_model_library. Cross-module
calls are dependency-injected: callers wire ``zone_dressing_count``
and ``character_roster_count`` to the real registries; defaults
return 0 so unit tests don't need the whole project graph.

Public surface
--------------
    ZoneArchetype enum
    ZonePatternTemplate dataclass (frozen)
    ZonePatternRegistry
    DEFAULT_TEMPLATES dict[ZoneArchetype, ZonePatternTemplate]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ZoneArchetype(enum.Enum):
    NATION_CAPITAL = "nation_capital"
    OUTPOST_TOWN = "outpost_town"
    OPEN_FIELD = "open_field"
    DUNGEON_DARK = "dungeon_dark"
    BEASTMAN_FORTRESS = "beastman_fortress"
    ENDGAME_INSTANCE = "endgame_instance"


@dataclasses.dataclass(frozen=True)
class ZonePatternTemplate:
    template_id: str
    archetype: ZoneArchetype
    dressing_count_target: int
    character_roster_size: int
    npc_archetype_mix: tuple[tuple[str, float], ...]
    mob_archetype_mix: tuple[tuple[str, float], ...]
    lighting_profile_id: str
    atmosphere_preset_id: str
    render_preset_default: str
    choreography_beats_target: int
    asset_upgrade_priority: int  # 1 (top) .. 5 (background)


# Default per-archetype templates. The Bastok Markets numbers are
# the demonstrated baseline (32 dressing, 11 chars, 8 beats); the
# others scale relative to that.
DEFAULT_TEMPLATES: dict[ZoneArchetype, ZonePatternTemplate] = {
    ZoneArchetype.NATION_CAPITAL: ZonePatternTemplate(
        template_id="tmpl_nation_capital",
        archetype=ZoneArchetype.NATION_CAPITAL,
        dressing_count_target=32,
        character_roster_size=11,
        npc_archetype_mix=(
            ("vendor", 0.35), ("guard", 0.15),
            ("crowd", 0.40), ("named", 0.10),
        ),
        mob_archetype_mix=(),
        lighting_profile_id="lp_industrial_daylight",
        atmosphere_preset_id="atm_market_haze",
        render_preset_default="trailer_master",
        choreography_beats_target=8,
        asset_upgrade_priority=1,
    ),
    ZoneArchetype.OUTPOST_TOWN: ZonePatternTemplate(
        template_id="tmpl_outpost_town",
        archetype=ZoneArchetype.OUTPOST_TOWN,
        dressing_count_target=14,
        character_roster_size=5,
        npc_archetype_mix=(
            ("vendor", 0.40), ("crowd", 0.50), ("named", 0.10),
        ),
        mob_archetype_mix=(),
        lighting_profile_id="lp_coastal_warm",
        atmosphere_preset_id="atm_sea_breeze",
        render_preset_default="trailer_master",
        choreography_beats_target=4,
        asset_upgrade_priority=2,
    ),
    ZoneArchetype.OPEN_FIELD: ZonePatternTemplate(
        template_id="tmpl_open_field",
        archetype=ZoneArchetype.OPEN_FIELD,
        dressing_count_target=8,
        character_roster_size=2,
        npc_archetype_mix=(
            ("crowd", 0.50), ("named", 0.50),
        ),
        mob_archetype_mix=(
            ("ambient", 0.60), ("notorious", 0.10),
            ("named", 0.30),
        ),
        lighting_profile_id="lp_golden_hour",
        atmosphere_preset_id="atm_open_sky",
        render_preset_default="trailer_master",
        choreography_beats_target=3,
        asset_upgrade_priority=3,
    ),
    ZoneArchetype.DUNGEON_DARK: ZonePatternTemplate(
        template_id="tmpl_dungeon_dark",
        archetype=ZoneArchetype.DUNGEON_DARK,
        dressing_count_target=18,
        character_roster_size=1,
        npc_archetype_mix=(
            ("named", 1.0),
        ),
        mob_archetype_mix=(
            ("ambient", 0.55), ("notorious", 0.30),
            ("boss", 0.15),
        ),
        lighting_profile_id="lp_subterranean_amber",
        atmosphere_preset_id="atm_damp_cave",
        render_preset_default="cutscene_cinematic",
        choreography_beats_target=5,
        asset_upgrade_priority=2,
    ),
    ZoneArchetype.BEASTMAN_FORTRESS: ZonePatternTemplate(
        template_id="tmpl_beastman_fortress",
        archetype=ZoneArchetype.BEASTMAN_FORTRESS,
        dressing_count_target=22,
        character_roster_size=3,
        npc_archetype_mix=(
            ("named", 0.66), ("crowd", 0.34),
        ),
        mob_archetype_mix=(
            ("ambient", 0.50), ("notorious", 0.30),
            ("boss", 0.20),
        ),
        lighting_profile_id="lp_sickly_green",
        atmosphere_preset_id="atm_swamp_smoke",
        render_preset_default="trailer_master",
        choreography_beats_target=6,
        asset_upgrade_priority=2,
    ),
    ZoneArchetype.ENDGAME_INSTANCE: ZonePatternTemplate(
        template_id="tmpl_endgame_instance",
        archetype=ZoneArchetype.ENDGAME_INSTANCE,
        dressing_count_target=26,
        character_roster_size=2,
        npc_archetype_mix=(
            ("named", 1.0),
        ),
        mob_archetype_mix=(
            ("notorious", 0.30), ("boss", 0.70),
        ),
        lighting_profile_id="lp_surreal_aether",
        atmosphere_preset_id="atm_god_realm",
        render_preset_default="cutscene_cinematic",
        choreography_beats_target=10,
        asset_upgrade_priority=1,
    ),
}


# Heuristics for archetype_for(zone_id). Hand-tuned mapping of
# the canonical zone_atlas zone ids to archetypes. Anything not
# in this map falls through the heuristic chain at the bottom.
_ZONE_ARCHETYPE_OVERRIDES: dict[str, ZoneArchetype] = {
    # Bastok ring
    "bastok_mines": ZoneArchetype.NATION_CAPITAL,
    "bastok_markets": ZoneArchetype.NATION_CAPITAL,
    "bastok_metalworks": ZoneArchetype.NATION_CAPITAL,
    # Sandy ring
    "south_sandoria": ZoneArchetype.NATION_CAPITAL,
    "north_sandoria": ZoneArchetype.NATION_CAPITAL,
    # Windy ring
    "windurst_woods": ZoneArchetype.NATION_CAPITAL,
    "windurst_walls": ZoneArchetype.NATION_CAPITAL,
    # Jeuno
    "lower_jeuno": ZoneArchetype.NATION_CAPITAL,
    "upper_jeuno": ZoneArchetype.NATION_CAPITAL,
    "port_jeuno": ZoneArchetype.NATION_CAPITAL,
    "ru_lude_gardens": ZoneArchetype.NATION_CAPITAL,
    "aht_urhgan_whitegate": ZoneArchetype.NATION_CAPITAL,
    # Outposts
    "selbina": ZoneArchetype.OUTPOST_TOWN,
    "mhaura": ZoneArchetype.OUTPOST_TOWN,
    "norg": ZoneArchetype.OUTPOST_TOWN,
    # Open fields
    "south_gustaberg": ZoneArchetype.OPEN_FIELD,
    "north_gustaberg": ZoneArchetype.OPEN_FIELD,
    "east_ronfaure": ZoneArchetype.OPEN_FIELD,
    "west_ronfaure": ZoneArchetype.OPEN_FIELD,
    "la_theine_plateau": ZoneArchetype.OPEN_FIELD,
    "jugner_forest": ZoneArchetype.OPEN_FIELD,
    "east_sarutabaruta": ZoneArchetype.OPEN_FIELD,
    "west_sarutabaruta": ZoneArchetype.OPEN_FIELD,
    "tahrongi_canyon": ZoneArchetype.OPEN_FIELD,
    "buburimu_peninsula": ZoneArchetype.OPEN_FIELD,
    "yhoator_jungle": ZoneArchetype.OPEN_FIELD,
    "pashhow_marshlands": ZoneArchetype.OPEN_FIELD,
    "rolanberry_fields": ZoneArchetype.OPEN_FIELD,
    "bhaflau_thickets": ZoneArchetype.OPEN_FIELD,
    # Dungeons
    "zeruhn_mines": ZoneArchetype.DUNGEON_DARK,
    "dangruf_wadi": ZoneArchetype.DUNGEON_DARK,
    "korroloka_tunnel": ZoneArchetype.DUNGEON_DARK,
    "crawlers_nest": ZoneArchetype.DUNGEON_DARK,
    "phomiuna_aqueducts": ZoneArchetype.DUNGEON_DARK,
    # Beastman fortresses
    "beadeaux": ZoneArchetype.BEASTMAN_FORTRESS,
    "davoi": ZoneArchetype.BEASTMAN_FORTRESS,
    "castle_oztroja": ZoneArchetype.BEASTMAN_FORTRESS,
    # Endgame
    "dynamis_bastok": ZoneArchetype.ENDGAME_INSTANCE,
    "dynamis_jeuno": ZoneArchetype.ENDGAME_INSTANCE,
    "sky": ZoneArchetype.ENDGAME_INSTANCE,
    "sea": ZoneArchetype.ENDGAME_INSTANCE,
    "limbus": ZoneArchetype.ENDGAME_INSTANCE,
}


def _heuristic_archetype(zone_id: str) -> ZoneArchetype:
    """Fallback when zone isn't in the override table."""
    z = zone_id.lower()
    if "dynamis" in z or "limbus" in z or "sky" in z or "sea" in z:
        return ZoneArchetype.ENDGAME_INSTANCE
    if "mines" in z or "tunnel" in z or "wadi" in z or "nest" in z:
        return ZoneArchetype.DUNGEON_DARK
    if (
        "beadeaux" in z or "davoi" in z or "oztroja" in z
        or "castle" in z
    ):
        return ZoneArchetype.BEASTMAN_FORTRESS
    if (
        "selbina" in z or "mhaura" in z or "norg" in z
        or "outpost" in z
    ):
        return ZoneArchetype.OUTPOST_TOWN
    if (
        "jeuno" in z or "bastok" in z or "sandoria" in z
        or "windurst" in z or "whitegate" in z
    ):
        return ZoneArchetype.NATION_CAPITAL
    return ZoneArchetype.OPEN_FIELD


def archetype_for(zone_id: str) -> ZoneArchetype:
    """Best-fit archetype for a zone — override table first,
    then a name-based heuristic chain."""
    if not zone_id:
        raise ValueError("zone_id required")
    if zone_id in _ZONE_ARCHETYPE_OVERRIDES:
        return _ZONE_ARCHETYPE_OVERRIDES[zone_id]
    return _heuristic_archetype(zone_id)


def default_template_for(
    archetype: ZoneArchetype,
) -> ZonePatternTemplate:
    return DEFAULT_TEMPLATES[archetype]


@dataclasses.dataclass(frozen=True)
class ZoneApplication:
    """Records that a template was applied to a zone, and how
    far along its build is."""
    zone_id: str
    archetype: ZoneArchetype
    template_id: str
    dressing_count_actual: int
    roster_count_actual: int
    completeness_pct: float


# Dependency-injected lookups. Production wires these to
# zone_dressing.count_in_zone, character_model_library.roster_size.
DressingCountFn = t.Callable[[str], int]
RosterCountFn = t.Callable[[str], int]


def _zero(_: str) -> int:
    return 0


@dataclasses.dataclass
class ZonePatternRegistry:
    """In-memory registry of templates and per-zone applications."""
    dressing_count_fn: DressingCountFn = _zero
    roster_count_fn: RosterCountFn = _zero
    _templates: dict[str, ZonePatternTemplate] = dataclasses.field(
        default_factory=dict,
    )
    _applications: dict[str, ZoneApplication] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        # Pre-load defaults so callers don't have to bootstrap.
        for tmpl in DEFAULT_TEMPLATES.values():
            if tmpl.template_id not in self._templates:
                self._templates[tmpl.template_id] = tmpl

    def register_template(
        self, template: ZonePatternTemplate,
    ) -> None:
        if not template.template_id:
            raise ValueError("template_id required")
        self._templates[template.template_id] = template

    def get_template(
        self, template_id: str,
    ) -> ZonePatternTemplate:
        if template_id not in self._templates:
            raise KeyError(f"unknown template: {template_id}")
        return self._templates[template_id]

    def all_templates(
        self,
    ) -> tuple[ZonePatternTemplate, ...]:
        return tuple(self._templates.values())

    def apply_template_to(
        self,
        zone_id: str,
        archetype: t.Optional[ZoneArchetype] = None,
    ) -> ZoneApplication:
        if not zone_id:
            raise ValueError("zone_id required")
        if archetype is None:
            archetype = archetype_for(zone_id)
        tmpl = default_template_for(archetype)
        d_count = max(0, int(self.dressing_count_fn(zone_id)))
        r_count = max(0, int(self.roster_count_fn(zone_id)))
        # Completeness is the harmonic-ish min of dressing and
        # roster progress. Cap at 100.0.
        d_pct = (
            min(100.0, 100.0 * d_count / tmpl.dressing_count_target)
            if tmpl.dressing_count_target > 0 else 100.0
        )
        r_pct = (
            min(100.0, 100.0 * r_count / tmpl.character_roster_size)
            if tmpl.character_roster_size > 0 else 100.0
        )
        completeness = round((d_pct + r_pct) / 2.0, 2)
        app = ZoneApplication(
            zone_id=zone_id,
            archetype=archetype,
            template_id=tmpl.template_id,
            dressing_count_actual=d_count,
            roster_count_actual=r_count,
            completeness_pct=completeness,
        )
        self._applications[zone_id] = app
        return app

    def application_for(self, zone_id: str) -> ZoneApplication:
        if zone_id not in self._applications:
            raise KeyError(f"no application for zone: {zone_id}")
        return self._applications[zone_id]

    def all_applications(
        self,
    ) -> tuple[ZoneApplication, ...]:
        return tuple(self._applications.values())

    def all_zones_progress(
        self,
    ) -> dict[str, float]:
        """zone_id -> completeness_pct for every zone with an
        application registered."""
        return {
            zid: app.completeness_pct
            for zid, app in self._applications.items()
        }

    def zones_pending_template(
        self, all_zone_ids: t.Iterable[str],
    ) -> tuple[str, ...]:
        """Zones in the supplied universe that have no
        application yet."""
        return tuple(
            sorted(
                zid for zid in all_zone_ids
                if zid not in self._applications
            )
        )

    def zones_at_or_above(
        self, threshold_pct: float,
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                zid for zid, app in self._applications.items()
                if app.completeness_pct >= threshold_pct
            )
        )


__all__ = [
    "ZoneArchetype",
    "ZonePatternTemplate",
    "ZoneApplication",
    "ZonePatternRegistry",
    "DEFAULT_TEMPLATES",
    "archetype_for",
    "default_template_for",
]
