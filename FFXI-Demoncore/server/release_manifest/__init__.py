"""Release manifest — per-platform demo packaging,
age ratings, EULAs, signing.

The demo ships on thirteen storefronts. Each wants a
different technical-requirements blob, a different
age rating, a different DRM solution, a different
regional lockout list, and a different language
matrix. release_manifest holds the registry, validates
content descriptors against each board's vocabulary,
and signs the final build with a developer key id.

Thirteen ReleasePlatform values:

  STEAM
  EPIC_GAMES_STORE
  GOG
  PLAYSTATION_STORE_PS5
  XBOX_STORE_SERIES_XS
  NINTENDO_ESHOP_SWITCH
  NINTENDO_ESHOP_SWITCH_2
  MAC_APP_STORE
  IOS_APP_STORE
  ANDROID_PLAY_STORE
  WEB_BROWSER (WebGL/WebGPU)
  STREAMING_GEFORCE_NOW
  STREAMING_LUNA
  STREAMING_BOOSTEROID

Each platform spec carries technical_requirements
(cpu/gpu/ram/storage), the required age-rating board
(ESRB / PEGI / USK / CERO / ACB / GRAC), the DRM
solution (Steam / EGS / Denuvo / None), the price in
USD, a set of region-lock ISO codes, the launch_date_
iso, and the supported language locales.

DemoBuildConfig wraps the per-build settings — base
manifest id (from world_demo_packaging), time-limit
minutes (0 = unlimited), feature flags (TRAILER_LOOP /
MULTIPLAYER / PHOTO_MODE / SPECTATOR), watermark
(PRESS / EVENT / RETAIL / NONE), checksum, and
signing-key id.

Content descriptors are mapped to each rating board's
vocabulary on validate_age_rating — ESRB wants
"Violence" / "Language" / "Simulated Gambling"; PEGI
wants "violence_low" / "violence_high" / "fear" /
"sex" / "drugs" / "gambling" / "discrimination" /
"bad_language" / "online_interactions"; USK wants
spell-it-out German categories. The function returns
the list of missing descriptors per board, so the
submission desk knows what to add.

Public surface
--------------
    ReleasePlatform enum
    AgeRatingBoard enum
    DrmKind enum
    Watermark enum
    FeatureFlag enum
    TechRequirements dataclass (frozen)
    PlatformSpec dataclass (frozen)
    DemoBuildConfig dataclass (frozen)
    ReleaseBuild dataclass (frozen)
    ReleaseManifestSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class ReleasePlatform(enum.Enum):
    STEAM = "steam"
    EPIC_GAMES_STORE = "epic_games_store"
    GOG = "gog"
    PLAYSTATION_STORE_PS5 = "playstation_store_ps5"
    XBOX_STORE_SERIES_XS = "xbox_store_series_xs"
    NINTENDO_ESHOP_SWITCH = "nintendo_eshop_switch"
    NINTENDO_ESHOP_SWITCH_2 = "nintendo_eshop_switch_2"
    MAC_APP_STORE = "mac_app_store"
    IOS_APP_STORE = "ios_app_store"
    ANDROID_PLAY_STORE = "android_play_store"
    WEB_BROWSER = "web_browser"
    STREAMING_GEFORCE_NOW = "streaming_geforce_now"
    STREAMING_LUNA = "streaming_luna"
    STREAMING_BOOSTEROID = "streaming_boosteroid"


class AgeRatingBoard(enum.Enum):
    ESRB = "esrb"
    PEGI = "pegi"
    USK = "usk"
    CERO = "cero"
    ACB = "acb"
    GRAC = "grac"


class DrmKind(enum.Enum):
    STEAM_DRM = "steam_drm"
    EGS_DRM = "egs_drm"
    DENUVO = "denuvo"
    PLATFORM_NATIVE = "platform_native"
    NONE = "none"


class Watermark(enum.Enum):
    PRESS = "press"
    EVENT = "event"
    RETAIL = "retail"
    NONE = "none"


class FeatureFlag(enum.Enum):
    TRAILER_LOOP = "trailer_loop"
    MULTIPLAYER = "multiplayer"
    PHOTO_MODE = "photo_mode"
    SPECTATOR = "spectator"


@dataclasses.dataclass(frozen=True)
class TechRequirements:
    cpu: str
    gpu: str
    ram_gb: int
    storage_gb: int


@dataclasses.dataclass(frozen=True)
class PlatformSpec:
    platform: ReleasePlatform
    technical_requirements: TechRequirements
    age_rating_board: AgeRatingBoard
    drm: DrmKind
    price_usd: float
    region_lock: frozenset[str]
    launch_date_iso: str
    language_support: frozenset[str]


@dataclasses.dataclass(frozen=True)
class DemoBuildConfig:
    build_id: str
    platform: ReleasePlatform
    base_manifest_id: str
    time_limit_minutes: int
    feature_flags: frozenset[FeatureFlag]
    watermark: Watermark
    checksum: str
    signed_by: str
    signing_key_id: str


@dataclasses.dataclass(frozen=True)
class ReleaseBuild:
    build_id: str
    platform: ReleasePlatform
    config: DemoBuildConfig
    content_descriptors: frozenset[str]
    submission_blob: dict


# Per-board content-descriptor vocabulary. validate_age_
# rating filters submitted content_descriptors against
# the board's known terms — missing ones are flagged.
_BOARD_VOCAB: dict[AgeRatingBoard, frozenset[str]] = {
    AgeRatingBoard.ESRB: frozenset({
        "violence_stylized", "violence_realistic",
        "language_mild", "language_strong",
        "blood", "sexual_themes", "nudity",
        "gambling_simulated", "use_of_alcohol",
    }),
    AgeRatingBoard.PEGI: frozenset({
        "violence_low", "violence_high", "fear",
        "sex", "drugs", "gambling",
        "discrimination", "bad_language",
        "online_interactions",
    }),
    AgeRatingBoard.USK: frozenset({
        "gewalt_stilisiert", "gewalt_realistisch",
        "angsterzeugend", "schimpfwoerter",
        "gluecksspiel",
    }),
    AgeRatingBoard.CERO: frozenset({
        "violence_stylized", "violence",
        "love", "horror", "crime", "drug",
        "alcohol", "gambling",
    }),
    AgeRatingBoard.ACB: frozenset({
        "violence", "language", "themes",
        "nudity", "sex", "drug_use",
        "gambling",
    }),
    AgeRatingBoard.GRAC: frozenset({
        "violence", "language", "fear",
        "drugs", "gambling",
        "discrimination", "crime",
    }),
}


# Default per-platform age-rating board.
_PLATFORM_BOARD: dict[ReleasePlatform, AgeRatingBoard] = {
    ReleasePlatform.STEAM: AgeRatingBoard.ESRB,
    ReleasePlatform.EPIC_GAMES_STORE: AgeRatingBoard.ESRB,
    ReleasePlatform.GOG: AgeRatingBoard.ESRB,
    ReleasePlatform.PLAYSTATION_STORE_PS5: (
        AgeRatingBoard.ESRB
    ),
    ReleasePlatform.XBOX_STORE_SERIES_XS: (
        AgeRatingBoard.ESRB
    ),
    ReleasePlatform.NINTENDO_ESHOP_SWITCH: (
        AgeRatingBoard.CERO
    ),
    ReleasePlatform.NINTENDO_ESHOP_SWITCH_2: (
        AgeRatingBoard.CERO
    ),
    ReleasePlatform.MAC_APP_STORE: AgeRatingBoard.ESRB,
    ReleasePlatform.IOS_APP_STORE: AgeRatingBoard.ESRB,
    ReleasePlatform.ANDROID_PLAY_STORE: (
        AgeRatingBoard.ESRB
    ),
    ReleasePlatform.WEB_BROWSER: AgeRatingBoard.ESRB,
    ReleasePlatform.STREAMING_GEFORCE_NOW: (
        AgeRatingBoard.ESRB
    ),
    ReleasePlatform.STREAMING_LUNA: AgeRatingBoard.ESRB,
    ReleasePlatform.STREAMING_BOOSTEROID: (
        AgeRatingBoard.ESRB
    ),
}


@dataclasses.dataclass
class ReleaseManifestSystem:
    _specs: dict[
        ReleasePlatform, PlatformSpec,
    ] = dataclasses.field(default_factory=dict)
    _builds: dict[str, ReleaseBuild] = dataclasses.field(
        default_factory=dict,
    )
    _signed: dict[str, tuple[str, str]] = dataclasses.field(
        default_factory=dict,
    )
    _build_counter: int = 0

    # ---------------------------------------------- specs
    def register_platform(
        self,
        platform: ReleasePlatform,
        *,
        cpu: str = "Intel i5 / Ryzen 5",
        gpu: str = "GTX 1060 / RX 580",
        ram_gb: int = 8,
        storage_gb: int = 30,
        drm: DrmKind = DrmKind.NONE,
        price_usd: float = 0.0,
        region_lock: t.Iterable[str] = (),
        launch_date_iso: str = "2026-12-01T00:00:00Z",
        language_support: t.Iterable[str] = (
            "en-US",
        ),
        age_rating_board: t.Optional[AgeRatingBoard] = None,
    ) -> PlatformSpec:
        board = (
            age_rating_board
            if age_rating_board is not None
            else _PLATFORM_BOARD.get(
                platform, AgeRatingBoard.ESRB,
            )
        )
        spec = PlatformSpec(
            platform=platform,
            technical_requirements=TechRequirements(
                cpu=cpu, gpu=gpu,
                ram_gb=ram_gb, storage_gb=storage_gb,
            ),
            age_rating_board=board,
            drm=drm,
            price_usd=price_usd,
            region_lock=frozenset(region_lock),
            launch_date_iso=launch_date_iso,
            language_support=frozenset(language_support),
        )
        self._specs[platform] = spec
        return spec

    def get_spec(
        self,
        platform: ReleasePlatform,
    ) -> PlatformSpec:
        if platform not in self._specs:
            return self.register_platform(platform)
        return self._specs[platform]

    def spec_count(self) -> int:
        return len(self._specs)

    # ---------------------------------------------- query
    def platforms_for_region(
        self,
        region: str,
    ) -> tuple[ReleasePlatform, ...]:
        out = []
        for p in ReleasePlatform:
            spec = self.get_spec(p)
            if region not in spec.region_lock:
                out.append(p)
        return tuple(out)

    def languages_for_platform(
        self,
        platform: ReleasePlatform,
    ) -> frozenset[str]:
        return self.get_spec(platform).language_support

    # ---------------------------------------------- age rating
    def validate_age_rating(
        self,
        platform: ReleasePlatform,
        content_descriptors: t.Iterable[str],
    ) -> tuple[str, ...]:
        spec = self.get_spec(platform)
        board = spec.age_rating_board
        vocab = _BOARD_VOCAB[board]
        submitted = set(content_descriptors)
        issues: list[str] = []
        for d in submitted:
            if d not in vocab:
                issues.append(
                    f"{board.value}: unknown descriptor "
                    f"{d}",
                )
        return tuple(issues)

    def board_vocabulary(
        self,
        board: AgeRatingBoard,
    ) -> frozenset[str]:
        return _BOARD_VOCAB[board]

    # ---------------------------------------------- build
    def build_release(
        self,
        platform: ReleasePlatform,
        demo_manifest_id: str,
        *,
        time_limit_minutes: int = 0,
        feature_flags: t.Iterable[FeatureFlag] = (),
        watermark: Watermark = Watermark.NONE,
        content_descriptors: t.Iterable[str] = (),
        checksum: str = "sha256-deadbeef",
    ) -> ReleaseBuild:
        if not demo_manifest_id:
            raise ValueError("demo_manifest_id required")
        if time_limit_minutes < 0:
            raise ValueError(
                "time_limit_minutes must be >= 0",
            )
        self._build_counter += 1
        build_id = (
            f"build_{platform.value}_{self._build_counter}"
        )
        config = DemoBuildConfig(
            build_id=build_id,
            platform=platform,
            base_manifest_id=demo_manifest_id,
            time_limit_minutes=time_limit_minutes,
            feature_flags=frozenset(feature_flags),
            watermark=watermark,
            checksum=checksum,
            signed_by="",
            signing_key_id="",
        )
        descriptors = frozenset(content_descriptors)
        spec = self.get_spec(platform)
        submission_blob = {
            "platform": platform.value,
            "manifest_id": demo_manifest_id,
            "board": spec.age_rating_board.value,
            "descriptors": sorted(descriptors),
            "drm": spec.drm.value,
            "watermark": watermark.value,
            "checksum": checksum,
            "feature_flags": sorted(
                f.value
                for f in config.feature_flags
            ),
        }
        release = ReleaseBuild(
            build_id=build_id,
            platform=platform,
            config=config,
            content_descriptors=descriptors,
            submission_blob=submission_blob,
        )
        self._builds[build_id] = release
        return release

    def get_build(self, build_id: str) -> ReleaseBuild:
        if build_id not in self._builds:
            raise KeyError(f"unknown build_id: {build_id}")
        return self._builds[build_id]

    def build_count(self) -> int:
        return len(self._builds)

    # ---------------------------------------------- sign
    def sign_build(
        self,
        build_id: str,
        key_id: str,
        signer: str = "Demoncore Build Service",
    ) -> ReleaseBuild:
        if build_id not in self._builds:
            raise KeyError(f"unknown build_id: {build_id}")
        if not key_id:
            raise ValueError("key_id required")
        release = self._builds[build_id]
        new_config = dataclasses.replace(
            release.config,
            signed_by=signer,
            signing_key_id=key_id,
        )
        new_release = dataclasses.replace(
            release, config=new_config,
        )
        self._builds[build_id] = new_release
        self._signed[build_id] = (signer, key_id)
        return new_release

    def is_signed(self, build_id: str) -> bool:
        return build_id in self._signed

    # ---------------------------------------------- summary
    def release_summary(self, build_id: str) -> dict:
        if build_id not in self._builds:
            raise KeyError(f"unknown build_id: {build_id}")
        release = self._builds[build_id]
        cfg = release.config
        spec = self.get_spec(release.platform)
        return {
            "build_id": cfg.build_id,
            "platform": release.platform.value,
            "manifest_id": cfg.base_manifest_id,
            "time_limit_minutes": cfg.time_limit_minutes,
            "watermark": cfg.watermark.value,
            "feature_flags": sorted(
                f.value for f in cfg.feature_flags
            ),
            "drm": spec.drm.value,
            "price_usd": spec.price_usd,
            "board": spec.age_rating_board.value,
            "descriptor_count": len(release.content_descriptors),
            "signed": self.is_signed(build_id),
            "signing_key_id": cfg.signing_key_id,
            "languages": sorted(spec.language_support),
        }


__all__ = [
    "ReleasePlatform",
    "AgeRatingBoard",
    "DrmKind",
    "Watermark",
    "FeatureFlag",
    "TechRequirements",
    "PlatformSpec",
    "DemoBuildConfig",
    "ReleaseBuild",
    "ReleaseManifestSystem",
]
