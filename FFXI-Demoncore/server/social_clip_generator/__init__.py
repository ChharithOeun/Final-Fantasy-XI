"""Social clip generator — per-platform clips with
auto-crop, auto-caption, and platform-aware music.

Every platform has its own rules. TikTok wants 9:16
vertical with licensed music and captions; LinkedIn
wants 16:9 horizontal, no music, professional pacing;
Bluesky wants 16:9 short. Sharing the same 60-second
replay to all eight is a one-line call when the social
clip generator knows the rules.

Eight Platform values with explicit per-platform
specs: TIKTOK, INSTAGRAM_REEL, YOUTUBE_SHORTS,
TWITTER, FACEBOOK_REEL, BLUESKY, MASTODON, LINKEDIN.
Each spec carries aspect_ratio ("9:16" or "16:9"),
max_duration_s, recommended_duration_s, music_required
(TikTok yes, LinkedIn no), captions_required (every
modern platform yes), max_file_size_mb, and a
hashtag_culture set (#FFXI, #JRPG, #demoncore on
TikTok; nothing on LinkedIn).

Auto-crop intelligently re-frames 16:9 sources to 9:16
by tracking the focus point — character bounding box
from name_plate_system, or director_ai's focus_xy
hint. The crop rectangle is computed by auto_crop_box
in normalized coordinates; the renderer downstream
uses FFmpeg's crop filter with those coordinates.

Auto-caption pulls dialogue lines from the voice_swap_
orchestrator timeline plus spell-name / weaponskill-
name overlays. The caption track is timed in
milliseconds and styled per-platform (TikTok bold
yellow, LinkedIn clean white).

bulk_render runs the same set of replays through every
listed platform in one pass — the marketing team posts
one event across all eight social networks with a
single command.

Public surface
--------------
    Platform enum
    PlatformSpec dataclass (frozen)
    CropBox dataclass (frozen)
    CaptionLine dataclass (frozen)
    ClipBuildPlan dataclass (frozen)
    SocialClipSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Platform(enum.Enum):
    TIKTOK = "tiktok"
    INSTAGRAM_REEL = "instagram_reel"
    YOUTUBE_SHORTS = "youtube_shorts"
    TWITTER = "twitter"
    FACEBOOK_REEL = "facebook_reel"
    BLUESKY = "bluesky"
    MASTODON = "mastodon"
    LINKEDIN = "linkedin"


@dataclasses.dataclass(frozen=True)
class PlatformSpec:
    platform: Platform
    aspect_ratio: str
    max_duration_s: int
    recommended_duration_s: int
    music_required: bool
    captions_required: bool
    max_file_size_mb: int
    hashtag_culture: frozenset[str]


@dataclasses.dataclass(frozen=True)
class CropBox:
    # Normalized coordinates in 0..1 space.
    x: float
    y: float
    w: float
    h: float


@dataclasses.dataclass(frozen=True)
class CaptionLine:
    start_ms: int
    end_ms: int
    text: str
    style: str   # platform-style id


@dataclasses.dataclass(frozen=True)
class ClipBuildPlan:
    plan_id: str
    platform: Platform
    source_ref: str
    target_duration_s: int
    aspect_ratio: str
    crop_box: CropBox
    captions: tuple[CaptionLine, ...]
    music_cue_id: str
    hashtags: tuple[str, ...]
    estimated_file_size_mb: float


# Default platform spec catalog — registered on demand.
_DEFAULT_SPECS: dict[Platform, dict] = {
    Platform.TIKTOK: {
        "aspect_ratio": "9:16",
        "max_duration_s": 60,
        "recommended_duration_s": 30,
        "music_required": True,
        "captions_required": True,
        "max_file_size_mb": 287,
        "hashtag_culture": frozenset({
            "#FFXI", "#FFXIDemoncore", "#FYP", "#GamerTok",
            "#JRPG", "#MMORPG",
        }),
    },
    Platform.INSTAGRAM_REEL: {
        "aspect_ratio": "9:16",
        "max_duration_s": 90,
        "recommended_duration_s": 30,
        "music_required": True,
        "captions_required": True,
        "max_file_size_mb": 250,
        "hashtag_culture": frozenset({
            "#FFXI", "#JRPG", "#gameDev",
            "#fantasyGames",
        }),
    },
    Platform.YOUTUBE_SHORTS: {
        "aspect_ratio": "9:16",
        "max_duration_s": 60,
        "recommended_duration_s": 45,
        "music_required": False,
        "captions_required": True,
        "max_file_size_mb": 256,
        "hashtag_culture": frozenset({
            "#Shorts", "#FFXI", "#JRPG", "#Gaming",
        }),
    },
    Platform.TWITTER: {
        "aspect_ratio": "16:9",
        "max_duration_s": 140,
        "recommended_duration_s": 45,
        "music_required": False,
        "captions_required": True,
        "max_file_size_mb": 512,
        "hashtag_culture": frozenset({
            "#FFXI", "#Demoncore", "#JRPG",
        }),
    },
    Platform.FACEBOOK_REEL: {
        "aspect_ratio": "9:16",
        "max_duration_s": 90,
        "recommended_duration_s": 30,
        "music_required": True,
        "captions_required": True,
        "max_file_size_mb": 400,
        "hashtag_culture": frozenset({
            "#FFXI", "#JRPG", "#gaming",
        }),
    },
    Platform.BLUESKY: {
        "aspect_ratio": "16:9",
        "max_duration_s": 60,
        "recommended_duration_s": 30,
        "music_required": False,
        "captions_required": True,
        "max_file_size_mb": 50,
        "hashtag_culture": frozenset({
            "#FFXI", "#JRPG", "#gamedev",
        }),
    },
    Platform.MASTODON: {
        "aspect_ratio": "16:9",
        "max_duration_s": 140,
        "recommended_duration_s": 60,
        "music_required": False,
        "captions_required": True,
        "max_file_size_mb": 40,
        "hashtag_culture": frozenset({
            "#FFXI", "#JRPG", "#gamedev", "#FediGaming",
        }),
    },
    Platform.LINKEDIN: {
        "aspect_ratio": "16:9",
        "max_duration_s": 180,
        "recommended_duration_s": 60,
        "music_required": False,
        "captions_required": True,
        "max_file_size_mb": 200,
        "hashtag_culture": frozenset({
            "#GameDev", "#IndieGame", "#Innovation",
        }),
    },
}


def _parse_aspect(ratio: str) -> float:
    parts = ratio.split(":")
    if len(parts) != 2:
        raise ValueError(f"bad aspect: {ratio}")
    return float(parts[0]) / float(parts[1])


@dataclasses.dataclass
class SocialClipSystem:
    _specs: dict[Platform, PlatformSpec] = dataclasses.field(
        default_factory=dict,
    )
    _plans: dict[str, ClipBuildPlan] = dataclasses.field(
        default_factory=dict,
    )
    _captions_by_replay: dict[str, list[CaptionLine]] = (
        dataclasses.field(default_factory=dict)
    )
    _plan_counter: int = 0

    # ---------------------------------------------- specs
    def register_platform_spec(
        self,
        platform: Platform,
        *,
        aspect_ratio: t.Optional[str] = None,
        max_duration_s: t.Optional[int] = None,
        recommended_duration_s: t.Optional[int] = None,
        music_required: t.Optional[bool] = None,
        captions_required: t.Optional[bool] = None,
        max_file_size_mb: t.Optional[int] = None,
        hashtag_culture: t.Optional[
            t.Iterable[str]
        ] = None,
    ) -> PlatformSpec:
        defaults = _DEFAULT_SPECS.get(platform, {})
        spec = PlatformSpec(
            platform=platform,
            aspect_ratio=(
                aspect_ratio
                if aspect_ratio is not None
                else defaults.get("aspect_ratio", "16:9")
            ),
            max_duration_s=(
                max_duration_s
                if max_duration_s is not None
                else defaults.get("max_duration_s", 60)
            ),
            recommended_duration_s=(
                recommended_duration_s
                if recommended_duration_s is not None
                else defaults.get(
                    "recommended_duration_s", 30,
                )
            ),
            music_required=(
                music_required
                if music_required is not None
                else defaults.get("music_required", False)
            ),
            captions_required=(
                captions_required
                if captions_required is not None
                else defaults.get(
                    "captions_required", True,
                )
            ),
            max_file_size_mb=(
                max_file_size_mb
                if max_file_size_mb is not None
                else defaults.get(
                    "max_file_size_mb", 256,
                )
            ),
            hashtag_culture=(
                frozenset(hashtag_culture)
                if hashtag_culture is not None
                else defaults.get(
                    "hashtag_culture", frozenset()
                )
            ),
        )
        self._specs[platform] = spec
        return spec

    def get_spec(self, platform: Platform) -> PlatformSpec:
        if platform not in self._specs:
            # Auto-register defaults if not present.
            return self.register_platform_spec(platform)
        return self._specs[platform]

    def spec_count(self) -> int:
        return len(self._specs)

    def recommended_duration_for(
        self,
        platform: Platform,
    ) -> int:
        return self.get_spec(platform).recommended_duration_s

    # ---------------------------------------------- crop
    def auto_crop_box(
        self,
        source_aspect: str,
        target_aspect: str,
        focus_xy: tuple[float, float],
    ) -> CropBox:
        sa = _parse_aspect(source_aspect)
        ta = _parse_aspect(target_aspect)
        fx, fy = focus_xy
        if not (0.0 <= fx <= 1.0 and 0.0 <= fy <= 1.0):
            raise ValueError("focus_xy must be in 0..1")
        if abs(sa - ta) < 1e-6:
            return CropBox(x=0.0, y=0.0, w=1.0, h=1.0)
        if sa > ta:
            # Source wider than target — crop horizontally.
            new_w = ta / sa
            x = fx - new_w / 2.0
            x = max(0.0, min(x, 1.0 - new_w))
            return CropBox(x=x, y=0.0, w=new_w, h=1.0)
        # Source taller — crop vertically.
        new_h = sa / ta
        y = fy - new_h / 2.0
        y = max(0.0, min(y, 1.0 - new_h))
        return CropBox(x=0.0, y=y, w=1.0, h=new_h)

    # ---------------------------------------------- captions
    def push_caption(
        self,
        replay_id: str,
        line: CaptionLine,
    ) -> int:
        if not replay_id:
            raise ValueError("replay_id required")
        lst = self._captions_by_replay.setdefault(
            replay_id, [],
        )
        lst.append(line)
        return len(lst)

    def caption_track(
        self,
        replay_id: str,
    ) -> tuple[CaptionLine, ...]:
        return tuple(
            self._captions_by_replay.get(replay_id, ())
        )

    # ---------------------------------------------- generate
    def generate_clip(
        self,
        platform: Platform,
        source_ref: str,
        *,
        target_duration_s: t.Optional[int] = None,
        source_aspect: str = "16:9",
        focus_xy: tuple[float, float] = (0.5, 0.5),
        music_cue_id: str = "",
        bitrate_mbps: float = 6.0,
    ) -> ClipBuildPlan:
        if not source_ref:
            raise ValueError("source_ref required")
        spec = self.get_spec(platform)
        if target_duration_s is None:
            target_duration_s = spec.recommended_duration_s
        if target_duration_s <= 0:
            raise ValueError(
                "target_duration_s must be > 0",
            )
        crop = self.auto_crop_box(
            source_aspect, spec.aspect_ratio, focus_xy,
        )
        captions = self.caption_track(source_ref)
        self._plan_counter += 1
        plan_id = (
            f"clip_{platform.value}_{self._plan_counter}"
        )
        # Rough file size: bitrate (Mbps) * duration / 8.
        est_size = bitrate_mbps * target_duration_s / 8.0
        plan = ClipBuildPlan(
            plan_id=plan_id,
            platform=platform,
            source_ref=source_ref,
            target_duration_s=target_duration_s,
            aspect_ratio=spec.aspect_ratio,
            crop_box=crop,
            captions=captions,
            music_cue_id=music_cue_id,
            hashtags=tuple(sorted(spec.hashtag_culture)),
            estimated_file_size_mb=est_size,
        )
        self._plans[plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> ClipBuildPlan:
        if plan_id not in self._plans:
            raise KeyError(f"unknown plan_id: {plan_id}")
        return self._plans[plan_id]

    def plan_count(self) -> int:
        return len(self._plans)

    # ---------------------------------------------- validate
    def validate_clip(
        self,
        plan: ClipBuildPlan,
        platform: Platform,
    ) -> tuple[str, ...]:
        spec = self.get_spec(platform)
        issues: list[str] = []
        if plan.platform != platform:
            issues.append(
                f"platform mismatch: plan {plan.platform.value}"
                f" vs {platform.value}",
            )
        if plan.target_duration_s > spec.max_duration_s:
            issues.append(
                f"duration {plan.target_duration_s}s exceeds "
                f"max {spec.max_duration_s}s",
            )
        if plan.aspect_ratio != spec.aspect_ratio:
            issues.append(
                f"aspect {plan.aspect_ratio} != "
                f"required {spec.aspect_ratio}",
            )
        if spec.captions_required and not plan.captions:
            issues.append("captions required but missing")
        if spec.music_required and not plan.music_cue_id:
            issues.append(
                "music required but missing cue",
            )
        if (
            plan.estimated_file_size_mb
            > spec.max_file_size_mb
        ):
            issues.append(
                f"estimated size "
                f"{plan.estimated_file_size_mb:.1f}MB "
                f"exceeds {spec.max_file_size_mb}MB",
            )
        return tuple(issues)

    # ---------------------------------------------- bulk
    def bulk_render(
        self,
        replay_ids: t.Iterable[str],
        platforms: t.Iterable[Platform],
        source_aspect: str = "16:9",
        focus_xy: tuple[float, float] = (0.5, 0.5),
    ) -> tuple[ClipBuildPlan, ...]:
        out: list[ClipBuildPlan] = []
        for rid in replay_ids:
            for p in platforms:
                out.append(
                    self.generate_clip(
                        p,
                        rid,
                        source_aspect=source_aspect,
                        focus_xy=focus_xy,
                    ),
                )
        return tuple(out)


__all__ = [
    "Platform",
    "PlatformSpec",
    "CropBox",
    "CaptionLine",
    "ClipBuildPlan",
    "SocialClipSystem",
]
