"""Zone lighting atlas — per-zone cinematic lighting profiles.

The atmospheric_render + film_grade + cinematic_camera +
lens_optics modules from the cinematic batch describe HOW to
shoot a given mood; this module records the mood *for each
zone*, so the director_ai can ask "what does Bastok Mines look
like at noon?" and get back a key/fill/back triplet, sky dome,
HDRI, fog density, and recommended LUT/camera/lens.

Twelve hand-tuned distinctive zones; the rest fall through to
an archetype default (NATION_CAPITAL / OUTPOST_TOWN / OPEN_FIELD
/ DUNGEON_DARK / BEASTMAN_FORTRESS / ENDGAME_INSTANCE) so every
zone in zone_atlas has something to render with.

Public surface
--------------
    LightingProfile dataclass (frozen)
    LightingAtlas
    DISTINCTIVE_PROFILES tuple of the twelve hand-tuned ids
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class LightingProfile:
    zone_id: str
    mood_descriptor: str
    key_light_kelvin: int
    key_light_intensity_lux: float
    fill_ratio: float                      # 0..1
    back_light_kelvin: int
    sky_dome_uri: str
    hdri_uri: str
    sun_angle_at_noon_deg: float
    fog_density: float                     # 0..1
    fog_color_rgb: tuple[int, int, int]
    god_ray_strength: float                # 0..1
    atmospheric_perspective_meters: float  # haze falloff distance
    recommended_film_lut: str
    recommended_camera_profile: str
    recommended_lens_profile: str


# --- Hand-tuned distinctive profiles ---
# All twelve are zones present in zone_atlas. (Konschtat is
# substituted with north_gustaberg, the canonical "Bastok-side
# golden-hour open field" in the atlas.)
_BASTOK_MINES = LightingProfile(
    zone_id="bastok_mines",
    mood_descriptor="smelter-warm industrial twilight",
    key_light_kelvin=2700,
    key_light_intensity_lux=4500.0,
    fill_ratio=0.20,
    back_light_kelvin=8200,
    sky_dome_uri="sky/bastok_mines_overcast.hdr",
    hdri_uri="hdri/bastok_smelter_indoor.exr",
    sun_angle_at_noon_deg=45.0,
    fog_density=0.18,
    fog_color_rgb=(78, 56, 44),
    god_ray_strength=0.55,
    atmospheric_perspective_meters=120.0,
    recommended_film_lut="vision3_500t",
    recommended_camera_profile="arri_alexa_35",
    recommended_lens_profile="atlas_orion_anamorphic_40mm",
)
_BASTOK_MARKETS = LightingProfile(
    zone_id="bastok_markets",
    mood_descriptor="industrial daylight, dust in shafts",
    key_light_kelvin=5600,
    key_light_intensity_lux=18000.0,
    fill_ratio=0.45,
    back_light_kelvin=7500,
    sky_dome_uri="sky/bastok_markets_haze.hdr",
    hdri_uri="hdri/bastok_markets_noon.exr",
    sun_angle_at_noon_deg=60.0,
    fog_density=0.10,
    fog_color_rgb=(190, 175, 150),
    god_ray_strength=0.70,
    atmospheric_perspective_meters=400.0,
    recommended_film_lut="vision3_250d",
    recommended_camera_profile="arri_alexa_35",
    recommended_lens_profile="cooke_s4_32mm",
)
_SOUTH_SANDORIA = LightingProfile(
    zone_id="south_sandoria",
    mood_descriptor="medieval-warm cathedral light",
    key_light_kelvin=3400,
    key_light_intensity_lux=12000.0,
    fill_ratio=0.30,
    back_light_kelvin=6800,
    sky_dome_uri="sky/sandoria_evening.hdr",
    hdri_uri="hdri/sandoria_courtyard.exr",
    sun_angle_at_noon_deg=55.0,
    fog_density=0.06,
    fog_color_rgb=(220, 200, 165),
    god_ray_strength=0.50,
    atmospheric_perspective_meters=600.0,
    recommended_film_lut="eterna",
    recommended_camera_profile="red_v_raptor",
    recommended_lens_profile="cooke_s4_25mm",
)
_WINDURST_WOODS = LightingProfile(
    zone_id="windurst_woods",
    mood_descriptor="jewel-tone candy color, dappled canopy",
    key_light_kelvin=5200,
    key_light_intensity_lux=14000.0,
    fill_ratio=0.55,
    back_light_kelvin=7800,
    sky_dome_uri="sky/windurst_canopy.hdr",
    hdri_uri="hdri/windurst_dappled.exr",
    sun_angle_at_noon_deg=70.0,
    fog_density=0.08,
    fog_color_rgb=(160, 200, 180),
    god_ray_strength=0.85,
    atmospheric_perspective_meters=350.0,
    recommended_film_lut="cinestyle",
    recommended_camera_profile="sony_venice_2",
    recommended_lens_profile="zeiss_supreme_35mm",
)
_LOWER_JEUNO = LightingProfile(
    zone_id="lower_jeuno",
    mood_descriptor="cosmopolitan neutral grade",
    key_light_kelvin=5000,
    key_light_intensity_lux=11000.0,
    fill_ratio=0.50,
    back_light_kelvin=7000,
    sky_dome_uri="sky/jeuno_overcast.hdr",
    hdri_uri="hdri/jeuno_plaza_noon.exr",
    sun_angle_at_noon_deg=65.0,
    fog_density=0.05,
    fog_color_rgb=(195, 195, 200),
    god_ray_strength=0.30,
    atmospheric_perspective_meters=800.0,
    recommended_film_lut="demoncore_standard",
    recommended_camera_profile="arri_alexa_35",
    recommended_lens_profile="cooke_s4_50mm",
)
_NORG = LightingProfile(
    zone_id="norg",
    mood_descriptor="twilight pirate cove, lantern-lit",
    key_light_kelvin=2200,
    key_light_intensity_lux=2200.0,
    fill_ratio=0.18,
    back_light_kelvin=8800,
    sky_dome_uri="sky/norg_dusk.hdr",
    hdri_uri="hdri/norg_dusk.exr",
    sun_angle_at_noon_deg=15.0,
    fog_density=0.30,
    fog_color_rgb=(50, 70, 95),
    god_ray_strength=0.20,
    atmospheric_perspective_meters=250.0,
    recommended_film_lut="bleach_bypass",
    recommended_camera_profile="bmd_ursa_12k",
    recommended_lens_profile="atlas_orion_anamorphic_32mm",
)
_NORTH_GUSTABERG = LightingProfile(
    zone_id="north_gustaberg",
    mood_descriptor="golden hour, low rolling plains",
    key_light_kelvin=3000,
    key_light_intensity_lux=22000.0,
    fill_ratio=0.40,
    back_light_kelvin=8500,
    sky_dome_uri="sky/gustaberg_dusk.hdr",
    hdri_uri="hdri/gustaberg_golden_hour.exr",
    sun_angle_at_noon_deg=20.0,
    fog_density=0.08,
    fog_color_rgb=(230, 175, 110),
    god_ray_strength=0.65,
    atmospheric_perspective_meters=900.0,
    recommended_film_lut="vision3_250d",
    recommended_camera_profile="arri_alexa_35",
    recommended_lens_profile="cooke_s4_25mm",
)
_PASHHOW = LightingProfile(
    zone_id="pashhow_marshlands",
    mood_descriptor="overcast green-grey, low haze",
    key_light_kelvin=6500,
    key_light_intensity_lux=8000.0,
    fill_ratio=0.65,
    back_light_kelvin=7200,
    sky_dome_uri="sky/pashhow_overcast.hdr",
    hdri_uri="hdri/pashhow_marsh.exr",
    sun_angle_at_noon_deg=55.0,
    fog_density=0.35,
    fog_color_rgb=(120, 130, 110),
    god_ray_strength=0.15,
    atmospheric_perspective_meters=500.0,
    recommended_film_lut="eterna",
    recommended_camera_profile="sony_venice_2",
    recommended_lens_profile="cooke_s4_40mm",
)
_TAHRONGI = LightingProfile(
    zone_id="tahrongi_canyon",
    mood_descriptor="red-rock dusk, monolithic shadows",
    key_light_kelvin=3200,
    key_light_intensity_lux=20000.0,
    fill_ratio=0.25,
    back_light_kelvin=8200,
    sky_dome_uri="sky/tahrongi_dusk.hdr",
    hdri_uri="hdri/tahrongi_canyon.exr",
    sun_angle_at_noon_deg=22.0,
    fog_density=0.12,
    fog_color_rgb=(180, 95, 70),
    god_ray_strength=0.75,
    atmospheric_perspective_meters=1200.0,
    recommended_film_lut="vision3_500t",
    recommended_camera_profile="arri_alexa_35",
    recommended_lens_profile="atlas_orion_anamorphic_40mm",
)
_DAVOI = LightingProfile(
    zone_id="davoi",
    mood_descriptor="sickly green-tint orcish swamp",
    key_light_kelvin=4200,
    key_light_intensity_lux=6500.0,
    fill_ratio=0.35,
    back_light_kelvin=5800,
    sky_dome_uri="sky/davoi_swamp.hdr",
    hdri_uri="hdri/davoi_dusk.exr",
    sun_angle_at_noon_deg=40.0,
    fog_density=0.40,
    fog_color_rgb=(95, 130, 70),
    god_ray_strength=0.45,
    atmospheric_perspective_meters=300.0,
    recommended_film_lut="bleach_bypass",
    recommended_camera_profile="red_v_raptor",
    recommended_lens_profile="cooke_s4_32mm",
)
_CRAWLERS_NEST = LightingProfile(
    zone_id="crawlers_nest",
    mood_descriptor="subterranean amber, pheromone glow",
    key_light_kelvin=2400,
    key_light_intensity_lux=900.0,
    fill_ratio=0.10,
    back_light_kelvin=2900,
    sky_dome_uri="sky/none_underground.hdr",
    hdri_uri="hdri/crawlers_nest_amber.exr",
    sun_angle_at_noon_deg=0.0,
    fog_density=0.55,
    fog_color_rgb=(110, 75, 30),
    god_ray_strength=0.10,
    atmospheric_perspective_meters=80.0,
    recommended_film_lut="day_for_night",
    recommended_camera_profile="bmd_ursa_12k",
    recommended_lens_profile="cooke_s4_25mm",
)
_BEADEAUX = LightingProfile(
    zone_id="beadeaux",
    mood_descriptor="cold-blue moonlight on quadav stone",
    key_light_kelvin=8800,
    key_light_intensity_lux=3500.0,
    fill_ratio=0.18,
    back_light_kelvin=10500,
    sky_dome_uri="sky/beadeaux_moonlit.hdr",
    hdri_uri="hdri/beadeaux_night.exr",
    sun_angle_at_noon_deg=0.0,
    fog_density=0.28,
    fog_color_rgb=(40, 65, 110),
    god_ray_strength=0.30,
    atmospheric_perspective_meters=400.0,
    recommended_film_lut="day_for_night",
    recommended_camera_profile="arri_alexa_35",
    recommended_lens_profile="zeiss_supreme_50mm",
)


_HAND_TUNED: tuple[LightingProfile, ...] = (
    _BASTOK_MINES,
    _BASTOK_MARKETS,
    _SOUTH_SANDORIA,
    _WINDURST_WOODS,
    _LOWER_JEUNO,
    _NORG,
    _NORTH_GUSTABERG,
    _PASHHOW,
    _TAHRONGI,
    _DAVOI,
    _CRAWLERS_NEST,
    _BEADEAUX,
)


DISTINCTIVE_PROFILES: tuple[str, ...] = tuple(
    p.zone_id for p in _HAND_TUNED
)


# Archetype defaults for any zone without a hand-tuned override.
_ARCHETYPE_DEFAULTS: dict[str, LightingProfile] = {
    "nation_capital": dataclasses.replace(
        _LOWER_JEUNO, zone_id="<archetype:nation_capital>",
    ),
    "outpost_town": dataclasses.replace(
        _NORG, zone_id="<archetype:outpost_town>",
    ),
    "open_field": dataclasses.replace(
        _NORTH_GUSTABERG, zone_id="<archetype:open_field>",
    ),
    "dungeon_dark": dataclasses.replace(
        _CRAWLERS_NEST, zone_id="<archetype:dungeon_dark>",
    ),
    "beastman_fortress": dataclasses.replace(
        _DAVOI, zone_id="<archetype:beastman_fortress>",
    ),
    "endgame_instance": LightingProfile(
        zone_id="<archetype:endgame_instance>",
        mood_descriptor="surreal aether, otherworld bloom",
        key_light_kelvin=6500,
        key_light_intensity_lux=15000.0,
        fill_ratio=0.50,
        back_light_kelvin=10000,
        sky_dome_uri="sky/sky_tulia.hdr",
        hdri_uri="hdri/sky_tulia_aether.exr",
        sun_angle_at_noon_deg=80.0,
        fog_density=0.20,
        fog_color_rgb=(200, 220, 255),
        god_ray_strength=0.95,
        atmospheric_perspective_meters=1500.0,
        recommended_film_lut="cinestyle",
        recommended_camera_profile="arri_alexa_35",
        recommended_lens_profile="cooke_s4_50mm",
    ),
}


@dataclasses.dataclass
class LightingAtlas:
    """Registry of per-zone lighting profiles."""
    _profiles: dict[str, LightingProfile] = dataclasses.field(
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        for p in _HAND_TUNED:
            self._profiles.setdefault(p.zone_id, p)

    def register_profile(self, profile: LightingProfile) -> None:
        if not profile.zone_id:
            raise ValueError("zone_id required")
        if not (0.0 <= profile.fill_ratio <= 1.0):
            raise ValueError("fill_ratio must be in [0,1]")
        if not (0.0 <= profile.fog_density <= 1.0):
            raise ValueError("fog_density must be in [0,1]")
        if not (0.0 <= profile.god_ray_strength <= 1.0):
            raise ValueError("god_ray_strength must be in [0,1]")
        if profile.atmospheric_perspective_meters <= 0:
            raise ValueError(
                "atmospheric_perspective_meters > 0",
            )
        for c in profile.fog_color_rgb:
            if not (0 <= c <= 255):
                raise ValueError("fog_color_rgb in [0,255]")
        self._profiles[profile.zone_id] = profile

    def lookup(self, zone_id: str) -> LightingProfile:
        if zone_id not in self._profiles:
            raise KeyError(f"no profile for zone: {zone_id}")
        return self._profiles[zone_id]

    def has_profile(self, zone_id: str) -> bool:
        return zone_id in self._profiles

    def all_profiles(self) -> tuple[LightingProfile, ...]:
        return tuple(self._profiles.values())

    def profiles_with_lut(
        self, lut_name: str,
    ) -> tuple[LightingProfile, ...]:
        return tuple(
            p for p in self._profiles.values()
            if p.recommended_film_lut == lut_name
        )

    def profiles_with_camera(
        self, camera_profile: str,
    ) -> tuple[LightingProfile, ...]:
        return tuple(
            p for p in self._profiles.values()
            if p.recommended_camera_profile == camera_profile
        )

    def distinctive_profiles(
        self,
    ) -> tuple[LightingProfile, ...]:
        return _HAND_TUNED

    def derive_for(
        self, zone_id: str, archetype: str,
    ) -> LightingProfile:
        """Look up the explicit profile for the zone, or fall
        back to the archetype default copied with the zone_id
        rebound."""
        if zone_id in self._profiles:
            return self._profiles[zone_id]
        if archetype not in _ARCHETYPE_DEFAULTS:
            raise KeyError(f"unknown archetype: {archetype}")
        base = _ARCHETYPE_DEFAULTS[archetype]
        return dataclasses.replace(base, zone_id=zone_id)


__all__ = [
    "LightingProfile",
    "LightingAtlas",
    "DISTINCTIVE_PROFILES",
]
