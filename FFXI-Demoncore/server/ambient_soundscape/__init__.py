"""Ambient soundscape — per-zone ambient bed.

Take any zone in the demo. Mute the music. Mute the
combat. The space should still sound like a place. Bastok
Mines is industrial hum + steam vent + a distant hammer
+ the occasional shift-whistle. Bastok Markets is crowd
murmur + cart wheels + vendor cries + Cid's anvil clang
in the next building over. Norg is ocean waves on the
hull + ship-creak + pirate banter from the porch. The
ambient bed is what tells your ear "you're somewhere".

Each zone gets a SoundscapeBed — a stack of AmbientLayer
records. Layers come in five kinds:
  * LOW_FREQ_HUM — the carrier rumble (smelter, ocean,
    cave drone). Always-on, looped, mixed low.
  * MID_TEXTURE — the texture of the place (footstep
    floor, leaf-rustle, market chatter). Looped.
  * HIGH_DETAIL — bright detail (wind chimes, insects,
    seagulls). Looped, panned slightly.
  * SPATIAL_POINT — a fixed-position point source (Cid's
    anvil clang, distant fountain). Distance-attenuated.
  * ONE_SHOT — fires periodically with random interval
    (vendor cry, Yagudo gong, distant chocobo). Each one-
    shot has interval_min/max seconds — the system schedules
    the next firing somewhere in that range.

Beds also have time-of-day + weather variants. Bastok
Markets at DAY is full crowd cacophony; at NIGHT it's a
single drunk cart wheel and a cricket. Pashhow on RAIN
adds dripping water + thunder + a higher leech-splosh
density.

Public surface
--------------
    LayerKind enum
    TimeOfDay enum
    Weather enum
    AmbientLayer dataclass (frozen)
    SoundscapeBed dataclass (frozen)
    OneShotSchedule dataclass (frozen)
    AmbientSoundscapeSystem
    populate_default_beds
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class LayerKind(enum.Enum):
    LOW_FREQ_HUM = "low_freq_hum"
    MID_TEXTURE = "mid_texture"
    HIGH_DETAIL = "high_detail"
    SPATIAL_POINT = "spatial_point"
    ONE_SHOT = "one_shot"


class TimeOfDay(enum.Enum):
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"
    DAWN = "dawn"
    ALL = "all"


class Weather(enum.Enum):
    CLEAR = "clear"
    RAIN = "rain"
    FOG = "fog"
    SANDSTORM = "sandstorm"
    SNOW = "snow"
    AURORA = "aurora"
    ALL = "all"


@dataclasses.dataclass(frozen=True)
class AmbientLayer:
    layer_id: str
    sample_uri: str
    gain_db: float
    kind: LayerKind
    loop: bool
    interval_s_min: float
    interval_s_max: float
    pan_lr: float
    distance_attenuation_m: float


@dataclasses.dataclass(frozen=True)
class SoundscapeBed:
    bed_id: str
    zone_id: str
    layers: tuple[AmbientLayer, ...]
    time_of_day_variant: TimeOfDay
    weather_variant: Weather


@dataclasses.dataclass(frozen=True)
class OneShotSchedule:
    layer_id: str
    sample_uri: str
    eta_seconds: float


def _validate_layer(layer: AmbientLayer) -> None:
    if not layer.layer_id:
        raise ValueError("layer_id required")
    if not layer.sample_uri:
        raise ValueError("sample_uri required")
    if not (-60.0 <= layer.gain_db <= 12.0):
        raise ValueError("gain_db must be in -60..12")
    if not (-1.0 <= layer.pan_lr <= 1.0):
        raise ValueError("pan_lr must be in -1..1")
    if layer.distance_attenuation_m < 0.0:
        raise ValueError("distance_attenuation_m must be >= 0")
    if layer.kind == LayerKind.ONE_SHOT:
        if layer.interval_s_min <= 0.0:
            raise ValueError("ONE_SHOT interval_min must be > 0")
        if layer.interval_s_max < layer.interval_s_min:
            raise ValueError(
                "interval_max must be >= interval_min",
            )


def _matches(
    bed: SoundscapeBed, tod: TimeOfDay, weather: Weather,
) -> bool:
    if (
        bed.time_of_day_variant != TimeOfDay.ALL
        and bed.time_of_day_variant != tod
    ):
        return False
    if (
        bed.weather_variant != Weather.ALL
        and bed.weather_variant != weather
    ):
        return False
    return True


@dataclasses.dataclass
class AmbientSoundscapeSystem:
    _beds: dict[str, SoundscapeBed] = dataclasses.field(
        default_factory=dict,
    )
    _by_zone: dict[
        str, list[str],
    ] = dataclasses.field(default_factory=dict)

    # ----------------------------------------------- register
    def register_bed(self, bed: SoundscapeBed) -> None:
        if not bed.bed_id:
            raise ValueError("bed_id required")
        if not bed.zone_id:
            raise ValueError("zone_id required")
        if bed.bed_id in self._beds:
            raise ValueError(
                f"duplicate bed_id: {bed.bed_id}",
            )
        if not bed.layers:
            raise ValueError("bed must have at least one layer")
        for layer in bed.layers:
            _validate_layer(layer)
        self._beds[bed.bed_id] = bed
        self._by_zone.setdefault(
            bed.zone_id, [],
        ).append(bed.bed_id)

    def get_bed(self, bed_id: str) -> SoundscapeBed:
        if bed_id not in self._beds:
            raise KeyError(f"unknown bed_id: {bed_id}")
        return self._beds[bed_id]

    def bed_count(self) -> int:
        return len(self._beds)

    # ----------------------------------------------- queries
    def bed_for(
        self,
        zone_id: str,
        time_of_day: TimeOfDay,
        weather: Weather,
    ) -> SoundscapeBed:
        # Score candidates: exact tod + exact weather wins;
        # otherwise prefer ALL-tod + exact-weather over
        # exact-tod + ALL-weather; ALL+ALL is fallback.
        candidates = [
            self._beds[bid]
            for bid in self._by_zone.get(zone_id, [])
            if _matches(self._beds[bid], time_of_day, weather)
        ]
        if not candidates:
            raise KeyError(
                f"no soundscape bed for zone={zone_id} "
                f"tod={time_of_day.value} weather={weather.value}",
            )

        def score(b: SoundscapeBed) -> int:
            s = 0
            if b.time_of_day_variant == time_of_day:
                s += 4
            if b.weather_variant == weather:
                s += 8
            return s

        candidates.sort(key=lambda b: (-score(b), b.bed_id))
        return candidates[0]

    def playlist_for(
        self,
        zone_id: str,
        listener_pos: tuple[float, float, float],
        time_of_day: TimeOfDay,
        weather: Weather,
    ) -> tuple[tuple[str, float], ...]:
        """Return list of (layer_id, current_gain_db).

        Spatial points are attenuated by distance from the
        listener; loops and one-shots use base gain.
        """
        bed = self.bed_for(zone_id, time_of_day, weather)
        out: list[tuple[str, float]] = []
        lx, ly, lz = listener_pos
        for layer in bed.layers:
            if (
                layer.kind == LayerKind.SPATIAL_POINT
                and layer.distance_attenuation_m > 0.0
            ):
                # Use distance from origin as proxy for the
                # source position relative to listener; the
                # caller passes the listener-source offset
                # in listener_pos for clarity.
                dist = (lx * lx + ly * ly + lz * lz) ** 0.5
                if dist >= layer.distance_attenuation_m:
                    continue
                # Linear falloff to silence at the
                # attenuation radius.
                falloff_db = -60.0 * (
                    dist / layer.distance_attenuation_m
                )
                out.append(
                    (layer.layer_id,
                     layer.gain_db + falloff_db),
                )
            else:
                out.append((layer.layer_id, layer.gain_db))
        return tuple(out)

    def schedule_next_one_shot(
        self,
        zone_id: str,
        now_t: float,
        time_of_day: TimeOfDay = TimeOfDay.ALL,
        weather: Weather = Weather.ALL,
    ) -> tuple[OneShotSchedule, ...]:
        """Return one schedule per ONE_SHOT layer in the
        active bed. ETA = midpoint of (interval_min,
        interval_max). Deterministic — no random sources."""
        try:
            bed = self.bed_for(zone_id, time_of_day, weather)
        except KeyError:
            return ()
        out: list[OneShotSchedule] = []
        for layer in bed.layers:
            if layer.kind != LayerKind.ONE_SHOT:
                continue
            mid = (
                layer.interval_s_min + layer.interval_s_max
            ) / 2.0
            out.append(OneShotSchedule(
                layer_id=layer.layer_id,
                sample_uri=layer.sample_uri,
                eta_seconds=now_t + mid,
            ))
        return tuple(out)

    def beds_with_weather(
        self, weather: Weather,
    ) -> tuple[SoundscapeBed, ...]:
        return tuple(
            sorted(
                (
                    b for b in self._beds.values()
                    if b.weather_variant == weather
                ),
                key=lambda b: b.bed_id,
            )
        )

    def beds_for_zone(
        self, zone_id: str,
    ) -> tuple[SoundscapeBed, ...]:
        return tuple(
            self._beds[bid]
            for bid in self._by_zone.get(zone_id, [])
        )


# ---------------------------------------------------------
# Default beds for ≥12 zones.
# ---------------------------------------------------------

def _layer(
    lid: str, kind: LayerKind, sample: str,
    gain: float = -12.0, pan: float = 0.0,
    loop: bool = True, attenuation: float = 0.0,
    interval_min: float = 0.0, interval_max: float = 0.0,
) -> AmbientLayer:
    return AmbientLayer(
        layer_id=lid,
        sample_uri=sample,
        gain_db=gain,
        kind=kind,
        loop=loop,
        interval_s_min=interval_min,
        interval_s_max=interval_max,
        pan_lr=pan,
        distance_attenuation_m=attenuation,
    )


_DEFAULT_BEDS: tuple[SoundscapeBed, ...] = (
    SoundscapeBed(
        bed_id="bed_bastok_mines_all",
        zone_id="bastok_mines",
        layers=(
            _layer("bm_low_hum", LayerKind.LOW_FREQ_HUM,
                   "amb/bastok_mines_industrial_hum.ogg",
                   gain=-15.0),
            _layer("bm_steam_vent", LayerKind.MID_TEXTURE,
                   "amb/bastok_mines_steam_vent_loop.ogg",
                   gain=-18.0),
            _layer("bm_dist_hammer", LayerKind.SPATIAL_POINT,
                   "amb/bastok_mines_distant_hammer.ogg",
                   gain=-20.0, attenuation=80.0),
            _layer("bm_whistle_oneshot", LayerKind.ONE_SHOT,
                   "amb/bastok_mines_shift_whistle.ogg",
                   gain=-14.0, loop=False,
                   interval_min=180.0, interval_max=420.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_bastok_markets_day",
        zone_id="bastok_markets",
        layers=(
            _layer("mkt_crowd", LayerKind.MID_TEXTURE,
                   "amb/markets_crowd_murmur.ogg",
                   gain=-13.0),
            _layer("mkt_carts", LayerKind.MID_TEXTURE,
                   "amb/markets_cart_wheels.ogg",
                   gain=-18.0),
            _layer("mkt_smelter_low", LayerKind.LOW_FREQ_HUM,
                   "amb/markets_smelter_lowend.ogg",
                   gain=-22.0),
            _layer("mkt_anvil", LayerKind.SPATIAL_POINT,
                   "amb/cids_anvil_clang.ogg",
                   gain=-10.0, attenuation=60.0),
            _layer("mkt_vendor_cry", LayerKind.ONE_SHOT,
                   "amb/markets_vendor_cry.ogg",
                   gain=-12.0, loop=False,
                   interval_min=8.0, interval_max=20.0),
        ),
        time_of_day_variant=TimeOfDay.DAY,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_bastok_markets_night",
        zone_id="bastok_markets",
        layers=(
            _layer("mkt_n_cricket", LayerKind.HIGH_DETAIL,
                   "amb/night_cricket.ogg", gain=-22.0),
            _layer("mkt_n_dist_cart", LayerKind.SPATIAL_POINT,
                   "amb/distant_cart_wheel.ogg",
                   gain=-24.0, attenuation=120.0),
        ),
        time_of_day_variant=TimeOfDay.NIGHT,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_sandy_all",
        zone_id="south_sandoria",
        layers=(
            _layer("sd_choir_dist", LayerKind.MID_TEXTURE,
                   "amb/sandy_cathedral_choir_distant.ogg",
                   gain=-20.0),
            _layer("sd_cobble_bg", LayerKind.MID_TEXTURE,
                   "amb/sandy_cobble_foot_bg.ogg",
                   gain=-22.0),
            _layer("sd_fountain", LayerKind.SPATIAL_POINT,
                   "amb/sandy_fountain_trickle.ogg",
                   gain=-12.0, attenuation=30.0),
            _layer("sd_lutist", LayerKind.SPATIAL_POINT,
                   "amb/sandy_lute_corner.ogg",
                   gain=-14.0, attenuation=40.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_windy_all",
        zone_id="windurst_woods",
        layers=(
            _layer("wd_chime_wind", LayerKind.HIGH_DETAIL,
                   "amb/windy_chimes.ogg", gain=-16.0,
                   pan=0.2),
            _layer("wd_taru_chatter", LayerKind.MID_TEXTURE,
                   "amb/windy_tarutaru_chatter.ogg",
                   gain=-18.0),
            _layer("wd_yagudo_gong", LayerKind.ONE_SHOT,
                   "amb/yagudo_distant_gong.ogg",
                   gain=-20.0, loop=False,
                   interval_min=60.0, interval_max=180.0),
            _layer("wd_petals", LayerKind.HIGH_DETAIL,
                   "amb/windy_flower_petals.ogg",
                   gain=-22.0, pan=-0.2),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_norg_all",
        zone_id="norg",
        layers=(
            _layer("ng_waves", LayerKind.LOW_FREQ_HUM,
                   "amb/norg_ocean_waves.ogg", gain=-13.0),
            _layer("ng_ship_creak", LayerKind.MID_TEXTURE,
                   "amb/norg_ship_creak.ogg", gain=-18.0),
            _layer("ng_pirate_banter", LayerKind.ONE_SHOT,
                   "amb/norg_pirate_banter.ogg",
                   gain=-12.0, loop=False,
                   interval_min=15.0, interval_max=45.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_konschtat_all",
        zone_id="konschtat_highlands",
        layers=(
            _layer("kn_grass_wind", LayerKind.MID_TEXTURE,
                   "amb/konschtat_wind_through_grass.ogg",
                   gain=-14.0),
            _layer("kn_chocobo_far", LayerKind.ONE_SHOT,
                   "amb/chocobo_distant_whinny.ogg",
                   gain=-22.0, loop=False,
                   interval_min=30.0, interval_max=120.0),
            _layer("kn_insects", LayerKind.HIGH_DETAIL,
                   "amb/konschtat_insects.ogg",
                   gain=-22.0),
            _layer("kn_sheep", LayerKind.ONE_SHOT,
                   "amb/sheep_bleat.ogg", gain=-20.0,
                   loop=False, interval_min=20.0,
                   interval_max=60.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.CLEAR,
    ),
    SoundscapeBed(
        bed_id="bed_pashhow_rain",
        zone_id="pashhow_marshlands",
        layers=(
            _layer("ps_frogs", LayerKind.MID_TEXTURE,
                   "amb/pashhow_frogs.ogg", gain=-15.0),
            _layer("ps_dripping", LayerKind.HIGH_DETAIL,
                   "amb/pashhow_dripping.ogg", gain=-18.0),
            _layer("ps_leech_splosh", LayerKind.ONE_SHOT,
                   "amb/pashhow_leech_splosh.ogg",
                   gain=-20.0, loop=False,
                   interval_min=10.0, interval_max=30.0),
            _layer("ps_thunder", LayerKind.ONE_SHOT,
                   "amb/pashhow_thunder_distant.ogg",
                   gain=-12.0, loop=False,
                   interval_min=40.0, interval_max=120.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.RAIN,
    ),
    SoundscapeBed(
        bed_id="bed_davoi_all",
        zone_id="davoi",
        layers=(
            _layer("dv_drum", LayerKind.MID_TEXTURE,
                   "amb/davoi_orc_drum.ogg", gain=-15.0),
            _layer("dv_howl", LayerKind.ONE_SHOT,
                   "amb/davoi_orc_howl.ogg",
                   gain=-18.0, loop=False,
                   interval_min=40.0, interval_max=90.0),
            _layer("dv_axe_wood", LayerKind.ONE_SHOT,
                   "amb/davoi_axe_on_wood.ogg",
                   gain=-16.0, loop=False,
                   interval_min=8.0, interval_max=24.0),
            _layer("dv_cooking", LayerKind.SPATIAL_POINT,
                   "amb/davoi_cooking_fire.ogg",
                   gain=-15.0, attenuation=40.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_crawlers_nest",
        zone_id="crawlers_nest",
        layers=(
            _layer("cn_chitin", LayerKind.MID_TEXTURE,
                   "amb/crawlers_chitin_loop.ogg",
                   gain=-16.0),
            _layer("cn_skitter", LayerKind.HIGH_DETAIL,
                   "amb/crawlers_skitter.ogg", gain=-19.0),
            _layer("cn_drip", LayerKind.HIGH_DETAIL,
                   "amb/crawlers_drip.ogg", gain=-22.0),
            _layer("cn_ovum", LayerKind.ONE_SHOT,
                   "amb/crawlers_ovum_hatch.ogg",
                   gain=-15.0, loop=False,
                   interval_min=60.0, interval_max=180.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_eldieme_all",
        zone_id="the_eldieme_necropolis",
        layers=(
            _layer("el_wind_moan", LayerKind.LOW_FREQ_HUM,
                   "amb/eldieme_wind_ghost_moan.ogg",
                   gain=-14.0),
            _layer("el_bone_creak", LayerKind.HIGH_DETAIL,
                   "amb/eldieme_bone_creak.ogg",
                   gain=-22.0),
            _layer("el_crow", LayerKind.ONE_SHOT,
                   "amb/eldieme_crow_caw.ogg",
                   gain=-18.0, loop=False,
                   interval_min=30.0, interval_max=90.0),
            _layer("el_organ_dist", LayerKind.SPATIAL_POINT,
                   "amb/eldieme_organ_distant.ogg",
                   gain=-22.0, attenuation=120.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_qufim_all",
        zone_id="qufim_island",
        layers=(
            _layer("qu_waves", LayerKind.LOW_FREQ_HUM,
                   "amb/qufim_waves.ogg", gain=-13.0),
            _layer("qu_seagull", LayerKind.ONE_SHOT,
                   "amb/qufim_seagull.ogg",
                   gain=-18.0, loop=False,
                   interval_min=15.0, interval_max=45.0),
            _layer("qu_lost_souls", LayerKind.HIGH_DETAIL,
                   "amb/qufim_lost_souls_wail.ogg",
                   gain=-20.0),
            _layer("qu_palm", LayerKind.MID_TEXTURE,
                   "amb/qufim_island_palm.ogg",
                   gain=-22.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
    SoundscapeBed(
        bed_id="bed_tahrongi_all",
        zone_id="tahrongi_canyon",
        layers=(
            _layer("th_canyon_wind", LayerKind.LOW_FREQ_HUM,
                   "amb/tahrongi_canyon_wind.ogg",
                   gain=-15.0),
            _layer("th_rockslide", LayerKind.ONE_SHOT,
                   "amb/tahrongi_rockslide_distant.ogg",
                   gain=-18.0, loop=False,
                   interval_min=120.0, interval_max=300.0),
            _layer("th_falcon", LayerKind.ONE_SHOT,
                   "amb/tahrongi_falcon_screech.ogg",
                   gain=-16.0, loop=False,
                   interval_min=20.0, interval_max=60.0),
            _layer("th_hooves", LayerKind.SPATIAL_POINT,
                   "amb/tahrongi_hoofstep_distant.ogg",
                   gain=-22.0, attenuation=80.0),
        ),
        time_of_day_variant=TimeOfDay.ALL,
        weather_variant=Weather.ALL,
    ),
)


def populate_default_beds(sys: AmbientSoundscapeSystem) -> int:
    n = 0
    for bed in _DEFAULT_BEDS:
        sys.register_bed(bed)
        n += 1
    return n


__all__ = [
    "LayerKind",
    "TimeOfDay",
    "Weather",
    "AmbientLayer",
    "SoundscapeBed",
    "OneShotSchedule",
    "AmbientSoundscapeSystem",
    "populate_default_beds",
]
