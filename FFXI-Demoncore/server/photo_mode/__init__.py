"""Photo mode — marketing capture + social share.

The trailer master needs hero shots. The streamer
needs share-worthy stills. The player needs to brag.
Photo mode is the same camera, lens, and grade pipeline
the production team uses for cinematics — exposed in-
game, with the same Cooke / Atlas / Zeiss lens catalog
from lens_optics and the same Arri / RED / Sony bodies
from cinematic_camera.

PhotoState is INACTIVE / ACTIVE_FREEROAM / ACTIVE_POSE_
LOCK / CAPTURING. Players enter freeroam — fly the
camera, scrub time-of-day, swap weather, change the
LUT — then either capture freely, or POSE_LOCK on a
target so the photographer can frame mid-jump or mid-
casting and have the subject hold for the click.

Filters extend the production grade with the photo-mode
classics — vignette, chromatic aberration, lens dust,
film grain, bloom, sepia, vintage-faded — and one
trailer-flavor "demoncore-trailer-master" preset that
maps to the same LUT used in the launch reel.

Export targets cover web (GIF_5S), social (PNG_4K),
print (PNG_8K), color-grading-later (EXR_HDR), and
short clips (MP4_60s_4K).

Sticker overlay templates frame the export with
"Demoncore — <zone> — <character_name>" and a date
corner — Apple Photos / Instagram-friendly out of the
box.

Public surface
--------------
    PhotoState enum
    ExportTarget enum
    Filter enum
    PhotoCamera dataclass (frozen)
    PhotoCapture dataclass (frozen)
    PhotoModeSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Minimum / maximum scrub bounds.
MIN_FOCAL_MM = 12
MAX_FOCAL_MM = 800
MIN_T_STOP = 1.0
MAX_T_STOP = 22.0
MIN_FOCUS_M = 0.2
MAX_FOCUS_M = 1000.0


class PhotoState(enum.Enum):
    INACTIVE = "inactive"
    ACTIVE_FREEROAM = "active_freeroam"
    ACTIVE_POSE_LOCK = "active_pose_lock"
    CAPTURING = "capturing"


class ExportTarget(enum.Enum):
    PNG_4K = "png_4k"
    PNG_8K = "png_8k"
    EXR_HDR = "exr_hdr"
    MP4_60S_4K = "mp4_60s_4k"
    GIF_5S = "gif_5s"


class Filter(enum.Enum):
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    DUST_ON_LENS = "dust_on_lens"
    FILM_GRAIN = "film_grain"
    BLOOM = "bloom"
    SEPIA = "sepia"
    VINTAGE_FADED = "vintage_faded"
    DEMONCORE_TRAILER_MASTER = "demoncore_trailer_master"


_VALID_WEATHER: frozenset[str] = frozenset({
    "clear", "rain", "fog", "snow", "aurora", "sandstorm",
})


@dataclasses.dataclass(frozen=True)
class PhotoCamera:
    camera_profile_id: str   # cinematic_camera profile name
    lens_id: str             # lens_optics name
    focal_length_mm: float
    t_stop: float
    focus_distance_m: float
    position_xyz: tuple[float, float, float]
    look_at_xyz: tuple[float, float, float]
    dolly_path: tuple[
        tuple[float, float, float], ...
    ] = ()  # video keyframes


@dataclasses.dataclass(frozen=True)
class PhotoCapture:
    capture_id: str
    player_id: str
    target: ExportTarget
    camera: PhotoCamera
    zone_id: str
    character_name: str
    captured_at_ms: int
    file_path_stub: str
    sticker_overlay: str
    filter_chain: tuple[tuple[Filter, float], ...]
    time_of_day_hour: float
    weather_override: str
    film_grade_lut: str
    hide_hud: bool
    hide_other_players: bool


_RECOMMENDED_BY_ZONE: dict[str, tuple[str, str, float]] = {
    # zone_id -> (camera_profile, lens_id, focal_length_mm)
    "bastok_markets": ("arri_alexa_35", "cooke_s7i_75mm", 75.0),
    "bastok_mines": ("arri_alexa_mini_lf", "cooke_s7i_50mm", 50.0),
    "sandoria_castle": ("arri_alexa_35", "zeiss_supreme_135mm", 135.0),
    "windurst_woods": ("sony_venice_2", "atlas_orion_65mm", 65.0),
    "jeuno_ruaun": ("red_v_raptor", "cooke_s7i_100mm", 100.0),
    "valkurm_dunes": (
        "arri_alexa_mini_lf", "atlas_orion_40mm", 40.0,
    ),
}


@dataclasses.dataclass
class _PlayerInternal:
    state: PhotoState = PhotoState.INACTIVE
    camera: t.Optional[PhotoCamera] = None
    pose_lock_target: str = ""
    time_of_day_hour: float = 12.0
    weather: str = "clear"
    film_grade_lut: str = "demoncore_standard"
    hide_hud: bool = False
    hide_other_players: bool = False
    filter_chain: list[tuple[Filter, float]] = (
        dataclasses.field(default_factory=list)
    )
    capture_counter: int = 0


@dataclasses.dataclass
class PhotoModeSystem:
    _players: dict[str, _PlayerInternal] = dataclasses.field(
        default_factory=dict,
    )

    def _player(self, player_id: str) -> _PlayerInternal:
        if not player_id:
            raise ValueError("player_id required")
        if player_id not in self._players:
            self._players[player_id] = _PlayerInternal()
        return self._players[player_id]

    # ---------------------------------------------- state
    def enter_photo_mode(self, player_id: str) -> PhotoState:
        pl = self._player(player_id)
        if pl.state == PhotoState.INACTIVE:
            pl.state = PhotoState.ACTIVE_FREEROAM
        return pl.state

    def exit_photo_mode(self, player_id: str) -> PhotoState:
        pl = self._player(player_id)
        pl.state = PhotoState.INACTIVE
        pl.camera = None
        pl.pose_lock_target = ""
        pl.filter_chain.clear()
        return pl.state

    def state_for(self, player_id: str) -> PhotoState:
        return self._player(player_id).state

    def is_active(self, player_id: str) -> bool:
        return self._player(player_id).state != (
            PhotoState.INACTIVE
        )

    # ---------------------------------------------- camera
    def set_camera(
        self,
        player_id: str,
        camera_profile_id: str,
        lens_id: str,
        focal_length_mm: float,
        t_stop: float,
        focus_distance_m: float,
        position_xyz: tuple[float, float, float],
        look_at_xyz: tuple[float, float, float],
    ) -> PhotoCamera:
        pl = self._player(player_id)
        if pl.state == PhotoState.INACTIVE:
            raise ValueError("not in photo mode")
        if not (MIN_FOCAL_MM <= focal_length_mm <= MAX_FOCAL_MM):
            raise ValueError(
                f"focal_length_mm out of range "
                f"[{MIN_FOCAL_MM}, {MAX_FOCAL_MM}]",
            )
        if not (MIN_T_STOP <= t_stop <= MAX_T_STOP):
            raise ValueError("t_stop out of range")
        if not (MIN_FOCUS_M <= focus_distance_m <= MAX_FOCUS_M):
            raise ValueError("focus_distance out of range")
        cam = PhotoCamera(
            camera_profile_id=camera_profile_id,
            lens_id=lens_id,
            focal_length_mm=focal_length_mm,
            t_stop=t_stop,
            focus_distance_m=focus_distance_m,
            position_xyz=position_xyz,
            look_at_xyz=look_at_xyz,
        )
        pl.camera = cam
        return cam

    def camera_for(
        self,
        player_id: str,
    ) -> t.Optional[PhotoCamera]:
        return self._player(player_id).camera

    def set_dolly_path(
        self,
        player_id: str,
        keyframes: t.Iterable[tuple[float, float, float]],
    ) -> PhotoCamera:
        pl = self._player(player_id)
        if pl.camera is None:
            raise ValueError(
                "set_camera before set_dolly_path",
            )
        kf = tuple(keyframes)
        pl.camera = dataclasses.replace(pl.camera, dolly_path=kf)
        return pl.camera

    # ---------------------------------------------- pose lock
    def pose_lock(
        self,
        player_id: str,
        target_player_id: str,
    ) -> PhotoState:
        pl = self._player(player_id)
        if pl.state == PhotoState.INACTIVE:
            raise ValueError("not in photo mode")
        if not target_player_id:
            raise ValueError("target_player_id required")
        pl.pose_lock_target = target_player_id
        pl.state = PhotoState.ACTIVE_POSE_LOCK
        return pl.state

    def pose_lock_target(self, player_id: str) -> str:
        return self._player(player_id).pose_lock_target

    def release_pose_lock(self, player_id: str) -> PhotoState:
        pl = self._player(player_id)
        pl.pose_lock_target = ""
        if pl.state == PhotoState.ACTIVE_POSE_LOCK:
            pl.state = PhotoState.ACTIVE_FREEROAM
        return pl.state

    # ---------------------------------------------- TOD
    def scrub_time_of_day(
        self,
        player_id: str,
        hour: float,
    ) -> float:
        if not (0.0 <= hour < 24.0):
            raise ValueError("hour must be in [0, 24)")
        pl = self._player(player_id)
        pl.time_of_day_hour = hour
        return pl.time_of_day_hour

    def time_of_day(self, player_id: str) -> float:
        return self._player(player_id).time_of_day_hour

    # ---------------------------------------------- weather
    def set_weather_override(
        self,
        player_id: str,
        weather: str,
    ) -> str:
        if weather not in _VALID_WEATHER:
            raise ValueError(
                f"unknown weather: {weather}",
            )
        pl = self._player(player_id)
        pl.weather = weather
        return pl.weather

    def weather_for(self, player_id: str) -> str:
        return self._player(player_id).weather

    # ---------------------------------------------- LUT
    def set_film_grade(
        self,
        player_id: str,
        lut_name: str,
    ) -> str:
        if not lut_name:
            raise ValueError("lut_name required")
        pl = self._player(player_id)
        pl.film_grade_lut = lut_name
        return lut_name

    def film_grade_for(self, player_id: str) -> str:
        return self._player(player_id).film_grade_lut

    # ---------------------------------------------- HUD toggle
    def set_hide_hud(self, player_id: str, hide: bool) -> bool:
        pl = self._player(player_id)
        pl.hide_hud = hide
        return hide

    def set_hide_other_players(
        self,
        player_id: str,
        hide: bool,
    ) -> bool:
        pl = self._player(player_id)
        pl.hide_other_players = hide
        return hide

    # ---------------------------------------------- filters
    def apply_filter(
        self,
        player_id: str,
        filter_name: Filter,
        intensity: float,
    ) -> tuple[tuple[Filter, float], ...]:
        if not (0.0 <= intensity <= 1.0):
            raise ValueError("intensity must be in [0, 1]")
        pl = self._player(player_id)
        # Replace if already present.
        pl.filter_chain = [
            (f, i) for f, i in pl.filter_chain
            if f != filter_name
        ]
        if intensity > 0.0:
            pl.filter_chain.append((filter_name, intensity))
        return tuple(pl.filter_chain)

    def active_filters(
        self,
        player_id: str,
    ) -> tuple[tuple[Filter, float], ...]:
        return tuple(self._player(player_id).filter_chain)

    # ---------------------------------------------- recommended
    def recommended_camera_for(
        self,
        zone_id: str,
    ) -> tuple[str, str, float]:
        if zone_id in _RECOMMENDED_BY_ZONE:
            return _RECOMMENDED_BY_ZONE[zone_id]
        # Fallback default.
        return ("arri_alexa_35", "cooke_s7i_50mm", 50.0)

    def has_recommended_for(self, zone_id: str) -> bool:
        return zone_id in _RECOMMENDED_BY_ZONE

    # ---------------------------------------------- capture
    def capture(
        self,
        player_id: str,
        target: ExportTarget,
        *,
        zone_id: str = "",
        character_name: str = "",
        now_ms: int = 0,
    ) -> PhotoCapture:
        pl = self._player(player_id)
        if pl.state == PhotoState.INACTIVE:
            raise ValueError("not in photo mode")
        if pl.camera is None:
            raise ValueError("camera not set")
        pl.state = PhotoState.CAPTURING
        pl.capture_counter += 1
        cap_id = f"{player_id}_cap_{pl.capture_counter}"
        ext_map = {
            ExportTarget.PNG_4K: "png",
            ExportTarget.PNG_8K: "png",
            ExportTarget.EXR_HDR: "exr",
            ExportTarget.MP4_60S_4K: "mp4",
            ExportTarget.GIF_5S: "gif",
        }
        ext = ext_map[target]
        file_path = (
            f"captures/{player_id}/{cap_id}.{ext}"
        )
        sticker = (
            f"Demoncore - {zone_id} - {character_name}"
            if zone_id or character_name
            else ""
        )
        cap = PhotoCapture(
            capture_id=cap_id,
            player_id=player_id,
            target=target,
            camera=pl.camera,
            zone_id=zone_id,
            character_name=character_name,
            captured_at_ms=now_ms,
            file_path_stub=file_path,
            sticker_overlay=sticker,
            filter_chain=tuple(pl.filter_chain),
            time_of_day_hour=pl.time_of_day_hour,
            weather_override=pl.weather,
            film_grade_lut=pl.film_grade_lut,
            hide_hud=pl.hide_hud,
            hide_other_players=pl.hide_other_players,
        )
        # Return to freeroam (or pose_lock) after capture.
        if pl.pose_lock_target:
            pl.state = PhotoState.ACTIVE_POSE_LOCK
        else:
            pl.state = PhotoState.ACTIVE_FREEROAM
        return cap

    def capture_count(self, player_id: str) -> int:
        return self._player(player_id).capture_counter


__all__ = [
    "PhotoState",
    "ExportTarget",
    "Filter",
    "PhotoCamera",
    "PhotoCapture",
    "PhotoModeSystem",
    "MIN_FOCAL_MM",
    "MAX_FOCAL_MM",
    "MIN_T_STOP",
    "MAX_T_STOP",
    "MIN_FOCUS_M",
    "MAX_FOCUS_M",
]
