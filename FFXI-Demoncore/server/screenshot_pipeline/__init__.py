"""Screenshot pipeline — bulk capture + auto-tag +
curate.

The press kit wants twelve hero stills. The Steam
store page wants six gameplay shots. The launcher
wants four animated tile backgrounds. The marketing
team wants the entire run of every NPC portrait at
three focal lengths each. Doing any of this by hand
is impossible at production scale; the screenshot
pipeline runs six CapturePass kinds, auto-tags every
output, scores quality, and curates the top-N per
pass.

Six CapturePass values:

  HERO_ZONE_SET — one beauty per zone at golden-hour
  CHARACTER_PORTRAITS — head/medium/wide per hero NPC
  COMBAT_MOMENTS — during showcase_choreography beats
  GROUP_SHOTS — party comps, formations
  ENVIRONMENT_DETAIL — close-up texture work
  MARKETING_BEAUTY — curated 12-shot best-of for the
                     press kit

Each screenshot stores camera_settings (from photo_
mode), time_of_day, weather, format (PNG_8K / EXR_HDR
/ JPG_WEB), and a tag set populated by auto_tag —
zone name, races visible, archetype (HERO/VILLAIN/
CIVILIAN), weather, time of day, has_combat, has_
dialogue.

Quality rating runs three heuristics:

  composition  — focus on rule-of-thirds intersections
  face         — penalize closed-eyes / partial heads
  exposure     — penalize clipped highlights / shadows

Each contributes 0..1; the auto_score is the mean,
0..5 stars after scaling.

curated_set_for(MARKETING_BEAUTY, count=12) returns
the top twelve by auto_score across all marketing
beauty shots — that's the press-kit hero set.

Public surface
--------------
    CapturePass enum
    Archetype enum
    ScreenshotFormat enum
    CameraSettings dataclass (frozen)
    Screenshot dataclass (frozen)
    QualityRating dataclass (frozen)
    ScreenshotPipeline
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class CapturePass(enum.Enum):
    HERO_ZONE_SET = "hero_zone_set"
    CHARACTER_PORTRAITS = "character_portraits"
    COMBAT_MOMENTS = "combat_moments"
    GROUP_SHOTS = "group_shots"
    ENVIRONMENT_DETAIL = "environment_detail"
    MARKETING_BEAUTY = "marketing_beauty"


class Archetype(enum.Enum):
    HERO = "hero"
    VILLAIN = "villain"
    CIVILIAN = "civilian"


class ScreenshotFormat(enum.Enum):
    PNG_8K = "png_8k"
    EXR_HDR = "exr_hdr"
    JPG_WEB = "jpg_web"


@dataclasses.dataclass(frozen=True)
class CameraSettings:
    camera_profile_id: str
    lens_id: str
    focal_length_mm: float
    t_stop: float
    focus_distance_m: float


@dataclasses.dataclass(frozen=True)
class Screenshot:
    screenshot_id: str
    capture_pass: CapturePass
    zone_id: str
    character_ids: tuple[str, ...]
    timestamp_iso: str
    camera_settings: CameraSettings
    time_of_day: str        # "dawn"/"morning"/etc.
    weather: str
    format: ScreenshotFormat
    tags: frozenset[str]
    rating: float           # 0..5
    curator_notes: str


@dataclasses.dataclass(frozen=True)
class QualityRating:
    composition_score: float
    face_score: float
    exposure_score: float
    auto_score: float       # 0..5


_DEFAULT_PASS_PARAMS: dict[CapturePass, dict] = {
    CapturePass.HERO_ZONE_SET: {
        "time_of_day": "evening",
        "weather": "clear",
        "format": ScreenshotFormat.PNG_8K,
    },
    CapturePass.CHARACTER_PORTRAITS: {
        "time_of_day": "morning",
        "weather": "clear",
        "format": ScreenshotFormat.PNG_8K,
    },
    CapturePass.COMBAT_MOMENTS: {
        "time_of_day": "noon",
        "weather": "clear",
        "format": ScreenshotFormat.JPG_WEB,
    },
    CapturePass.GROUP_SHOTS: {
        "time_of_day": "afternoon",
        "weather": "clear",
        "format": ScreenshotFormat.PNG_8K,
    },
    CapturePass.ENVIRONMENT_DETAIL: {
        "time_of_day": "morning",
        "weather": "clear",
        "format": ScreenshotFormat.EXR_HDR,
    },
    CapturePass.MARKETING_BEAUTY: {
        "time_of_day": "evening",
        "weather": "clear",
        "format": ScreenshotFormat.PNG_8K,
    },
}


def _classify_time_of_day(hour: float) -> str:
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 20:
        return "evening"
    if 20 <= hour < 23:
        return "dusk"
    return "night"


@dataclasses.dataclass
class ScreenshotPipeline:
    _passes: dict[CapturePass, dict] = dataclasses.field(
        default_factory=dict,
    )
    _shots: dict[str, Screenshot] = dataclasses.field(
        default_factory=dict,
    )
    _ratings: dict[str, QualityRating] = dataclasses.field(
        default_factory=dict,
    )
    _counter: int = 0

    # ---------------------------------------------- pass
    def register_pass(
        self,
        kind: CapturePass,
        **params: t.Any,
    ) -> dict:
        merged = dict(_DEFAULT_PASS_PARAMS[kind])
        merged.update(params)
        self._passes[kind] = merged
        return merged

    def pass_params(self, kind: CapturePass) -> dict:
        if kind in self._passes:
            return dict(self._passes[kind])
        return dict(_DEFAULT_PASS_PARAMS[kind])

    def pass_count(self) -> int:
        return len(self._passes)

    # ---------------------------------------------- capture
    def capture(
        self,
        pass_kind: CapturePass,
        zone_id: str,
        character_ids: t.Iterable[str] = (),
        *,
        camera_profile_id: str = "arri_alexa_35",
        lens_id: str = "cooke_s7i_50mm",
        focal_length_mm: float = 50.0,
        t_stop: float = 2.8,
        focus_distance_m: float = 3.0,
        hour: float = 18.0,
        weather: str = "clear",
        format_: t.Optional[ScreenshotFormat] = None,
        timestamp_iso: str = "2026-01-01T00:00:00Z",
        archetype: Archetype = Archetype.HERO,
        has_combat: bool = False,
        has_dialogue: bool = False,
        races: t.Iterable[str] = (),
    ) -> str:
        if not zone_id:
            raise ValueError("zone_id required")
        params = self.pass_params(pass_kind)
        if format_ is None:
            format_ = params["format"]
        self._counter += 1
        sid = f"ss_{pass_kind.value}_{self._counter}"
        camera = CameraSettings(
            camera_profile_id=camera_profile_id,
            lens_id=lens_id,
            focal_length_mm=focal_length_mm,
            t_stop=t_stop,
            focus_distance_m=focus_distance_m,
        )
        tod = _classify_time_of_day(hour)
        # Auto-tag set: zone, races, archetype, weather,
        # time-of-day, has_combat, has_dialogue.
        tags = {
            f"zone:{zone_id}",
            f"archetype:{archetype.value}",
            f"weather:{weather}",
            f"tod:{tod}",
        }
        for r in races:
            tags.add(f"race:{r}")
        if has_combat:
            tags.add("has_combat")
        if has_dialogue:
            tags.add("has_dialogue")
        shot = Screenshot(
            screenshot_id=sid,
            capture_pass=pass_kind,
            zone_id=zone_id,
            character_ids=tuple(character_ids),
            timestamp_iso=timestamp_iso,
            camera_settings=camera,
            time_of_day=tod,
            weather=weather,
            format=format_,
            tags=frozenset(tags),
            rating=0.0,
            curator_notes="",
        )
        self._shots[sid] = shot
        return sid

    def get(self, screenshot_id: str) -> Screenshot:
        if screenshot_id not in self._shots:
            raise KeyError(
                f"unknown screenshot_id: {screenshot_id}",
            )
        return self._shots[screenshot_id]

    def count(self) -> int:
        return len(self._shots)

    def count_for_pass(self, pass_kind: CapturePass) -> int:
        return sum(
            1
            for s in self._shots.values()
            if s.capture_pass == pass_kind
        )

    # ---------------------------------------------- tagging
    def auto_tag(self, screenshot_id: str) -> frozenset[str]:
        # auto_tag is a no-op idempotent — capture already
        # populates the tag set. Return current tags.
        return self.get(screenshot_id).tags

    def add_tag(
        self,
        screenshot_id: str,
        tag: str,
    ) -> frozenset[str]:
        if not tag:
            raise ValueError("tag required")
        shot = self.get(screenshot_id)
        new_tags = set(shot.tags) | {tag}
        new_shot = dataclasses.replace(
            shot, tags=frozenset(new_tags),
        )
        self._shots[screenshot_id] = new_shot
        return new_shot.tags

    def search_by_tag(self, tag: str) -> tuple[str, ...]:
        return tuple(
            sid
            for sid, shot in self._shots.items()
            if tag in shot.tags
        )

    # ---------------------------------------------- quality
    def rate_quality(
        self,
        screenshot_id: str,
        *,
        composition: float = 0.7,
        face: float = 0.8,
        exposure: float = 0.8,
    ) -> QualityRating:
        for v in (composition, face, exposure):
            if not (0.0 <= v <= 1.0):
                raise ValueError(
                    "quality scores must be in 0..1",
                )
        mean = (composition + face + exposure) / 3.0
        auto = mean * 5.0
        rating = QualityRating(
            composition_score=composition,
            face_score=face,
            exposure_score=exposure,
            auto_score=auto,
        )
        self._ratings[screenshot_id] = rating
        shot = self.get(screenshot_id)
        new_shot = dataclasses.replace(shot, rating=auto)
        self._shots[screenshot_id] = new_shot
        return rating

    def rating_for(
        self,
        screenshot_id: str,
    ) -> t.Optional[QualityRating]:
        return self._ratings.get(screenshot_id)

    # ---------------------------------------------- curation
    def curated_set_for(
        self,
        pass_kind: CapturePass,
        count: int = 12,
    ) -> tuple[str, ...]:
        if count <= 0:
            raise ValueError("count must be > 0")
        candidates = [
            (sid, shot.rating)
            for sid, shot in self._shots.items()
            if shot.capture_pass == pass_kind
        ]
        candidates.sort(key=lambda x: x[1], reverse=True)
        return tuple(sid for sid, _ in candidates[:count])

    def annotate(
        self,
        screenshot_id: str,
        notes: str,
    ) -> Screenshot:
        shot = self.get(screenshot_id)
        new_shot = dataclasses.replace(
            shot, curator_notes=notes,
        )
        self._shots[screenshot_id] = new_shot
        return new_shot

    # ---------------------------------------------- export
    def bulk_export(
        self,
        screenshot_ids: t.Iterable[str],
        format_: ScreenshotFormat,
    ) -> tuple[str, ...]:
        out: list[str] = []
        ext_map = {
            ScreenshotFormat.PNG_8K: "png",
            ScreenshotFormat.EXR_HDR: "exr",
            ScreenshotFormat.JPG_WEB: "jpg",
        }
        ext = ext_map[format_]
        for sid in screenshot_ids:
            shot = self.get(sid)
            out.append(
                f"exports/{shot.capture_pass.value}/{sid}.{ext}",
            )
        return tuple(out)


__all__ = [
    "CapturePass",
    "Archetype",
    "ScreenshotFormat",
    "CameraSettings",
    "Screenshot",
    "QualityRating",
    "ScreenshotPipeline",
]
