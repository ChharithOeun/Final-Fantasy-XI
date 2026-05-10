"""Trailer generator — auto-assemble trailers from
gameplay highlights.

The marketing team needs a 30-second teaser for the
investor deck on Monday, a 90-second sizzle for the
Gamescom booth on Wednesday, and a 2-minute gameplay
walkthrough for the press embargo on Friday. The
trailer generator builds all three from the same
ingredients — the rolling replay buffer from
spectator_mode, the curated shot sequences from
showcase_choreography, and the director_ai shot
grammar — using scene_pacing's Murch six-axis to
score each cut.

Seven TrailerKind values cover every marketing
context:

  TEASER_30S          — one-shot, no spoilers, hero zone
                        + logo
  STORY_60S           — three-act intro/conflict/resolution
  GAMEPLAY_2MIN       — mechanics-focused walkthrough
  DEEP_DIVE_5MIN      — extended cinematic narration
  CONVENTION_SIZZLE_90S — E3/PAX/Gamescom impact reel
  LAUNCH_PROMO_90S    — release-day "available now" cut
  FEATURE_VERTICAL_VIDEO_30S — TikTok-style 9:16 portrait

Each kind has its own montage tempo:

  TEASER         — fast cuts (1-2s avg)
  CONVENTION     — fast cuts (1.5-2.5s)
  STORY          — medium cuts (2-4s)
  GAMEPLAY       — medium cuts (2-4s)
  LAUNCH         — medium cuts (2-4s)
  VERTICAL       — fast cuts (1-2s, mobile attention)
  DEEP_DIVE      — slow cuts (5-8s)

Edit decisions sync to music: opening logo card,
hero shot establishes, beats cut on the bar, mid-
trailer "Coming Soon" or "Available Now" card, end
credits roll with key voice cast (pulled from
voice_role_registry) + licensing line.

Validation tells you why your trailer won't fly:

  TEASER must hide spoiler shots (no final-boss
  bait, no climax payoff in the first 30 seconds)
  STORY must contain intro + conflict + resolution
  beats
  GAMEPLAY must show real mechanics (not pre-rendered
  cinematics)
  Every kind must be within the runtime budget

trailer_for_event(event) is the auto-trailer hook —
called by spectator_mode.save_replay() on a CRITICAL_
KILL or WORLD_FIRST_NM, produces a quick 30-second
share-clip the player can post to Twitter without
opening the editor.

Public surface
--------------
    TrailerKind enum
    SourceKind enum
    TrailerInput dataclass (frozen)
    ShotSlot dataclass (frozen)
    TitleCard dataclass (frozen)
    TrailerBuildPlan dataclass (frozen)
    TrailerSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Per-kind runtime budgets (seconds).
_RUNTIME_S: dict[str, int] = {
    "teaser_30s": 30,
    "story_60s": 60,
    "gameplay_2min": 120,
    "deep_dive_5min": 300,
    "convention_sizzle_90s": 90,
    "launch_promo_90s": 90,
    "feature_vertical_video_30s": 30,
}

# Average shot duration per kind (seconds).
_SHOT_DURATION_S: dict[str, float] = {
    "teaser_30s": 1.5,
    "story_60s": 3.0,
    "gameplay_2min": 3.0,
    "deep_dive_5min": 6.5,
    "convention_sizzle_90s": 2.0,
    "launch_promo_90s": 3.0,
    "feature_vertical_video_30s": 1.5,
}


class TrailerKind(enum.Enum):
    TEASER_30S = "teaser_30s"
    STORY_60S = "story_60s"
    GAMEPLAY_2MIN = "gameplay_2min"
    DEEP_DIVE_5MIN = "deep_dive_5min"
    CONVENTION_SIZZLE_90S = "convention_sizzle_90s"
    LAUNCH_PROMO_90S = "launch_promo_90s"
    FEATURE_VERTICAL_VIDEO_30S = "feature_vertical_video_30s"


class SourceKind(enum.Enum):
    REPLAY_BUFFER = "replay_buffer"
    CHOREOGRAPHY = "choreography"
    MANUAL_SHOT_LIST = "manual_shot_list"
    MIXED = "mixed"


@dataclasses.dataclass(frozen=True)
class TrailerInput:
    source_kind: SourceKind
    target_kind: TrailerKind
    music_cue_id: str
    hero_character_ids: tuple[str, ...] = ()
    hero_zone_ids: tuple[str, ...] = ()
    replay_event_ids: tuple[str, ...] = ()
    showcase_seq_name: str = ""
    manual_shot_list: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ShotSlot:
    index: int
    label: str           # director_ai vocabulary
    source_ref: str      # replay_id / shot_name / manual_id
    duration_s: float
    music_beat_index: int
    is_hero: bool
    is_spoiler_risk: bool


@dataclasses.dataclass(frozen=True)
class TitleCard:
    position: str        # "open" / "mid" / "end"
    text: str
    duration_s: float


@dataclasses.dataclass(frozen=True)
class TrailerBuildPlan:
    plan_id: str
    target_kind: TrailerKind
    shot_list: tuple[ShotSlot, ...]
    title_cards: tuple[TitleCard, ...]
    music_cue_id: str
    target_runtime_s: int
    estimated_runtime_s: float
    hero_zone_ids: tuple[str, ...]
    hero_character_ids: tuple[str, ...]
    end_credits_voice_cast: tuple[str, ...]


# Spoiler-risk source-ref tokens — anything containing
# these substrings is treated as a spoiler by validate().
_SPOILER_TOKENS = (
    "final_boss",
    "ending",
    "endgame_reveal",
    "climax_payoff",
    "twist",
)

# Story-act tokens that label which beat a manual shot
# represents. validate() requires all three for STORY_60S.
_STORY_INTRO_TOKENS = ("intro_", "establishing_", "open_")
_STORY_CONFLICT_TOKENS = ("conflict_", "battle_", "tension_")
_STORY_RESOLUTION_TOKENS = (
    "resolution_", "victory_", "payoff_", "climax_",
)

# Gameplay-mechanic tokens — at least one must be present
# in a GAMEPLAY_2MIN cut.
_GAMEPLAY_MECHANIC_TOKENS = (
    "combat_", "spell_", "weaponskill_", "skillchain_",
    "magic_burst_", "crafting_", "fishing_", "gathering_",
    "mounts_", "exploration_",
)


def _runtime_for(kind: TrailerKind) -> int:
    return _RUNTIME_S[kind.value]


def _shot_duration_for(kind: TrailerKind) -> float:
    return _SHOT_DURATION_S[kind.value]


@dataclasses.dataclass
class TrailerSystem:
    _plans: dict[str, TrailerBuildPlan] = dataclasses.field(
        default_factory=dict,
    )
    _voice_cast: list[str] = dataclasses.field(
        default_factory=list,
    )
    _plan_counter: int = 0

    # ---------------------------------------------- registry
    def register_voice_cast(
        self,
        cast_member: str,
    ) -> int:
        if not cast_member:
            raise ValueError("cast_member required")
        if cast_member not in self._voice_cast:
            self._voice_cast.append(cast_member)
        return len(self._voice_cast)

    def voice_cast(self) -> tuple[str, ...]:
        return tuple(self._voice_cast)

    # ---------------------------------------------- estimates
    def estimated_runtime(self, kind: TrailerKind) -> int:
        return _runtime_for(kind)

    def shots_per_kind(self, kind: TrailerKind) -> int:
        budget = _runtime_for(kind)
        # Title cards eat about 4 seconds total (1.5 open,
        # 1.0 mid, 1.5 end).
        usable = max(1, budget - 4)
        per_shot = _shot_duration_for(kind)
        return max(1, int(round(usable / per_shot)))

    # ---------------------------------------------- build
    def build_trailer(
        self,
        input_: TrailerInput,
    ) -> TrailerBuildPlan:
        if not input_.music_cue_id:
            raise ValueError("music_cue_id required")
        kind = input_.target_kind
        self._plan_counter += 1
        plan_id = f"trailer_{kind.value}_{self._plan_counter}"

        n_shots = self.shots_per_kind(kind)
        per_shot = _shot_duration_for(kind)
        budget = _runtime_for(kind)

        # Assemble shot sources by source kind.
        sources = self._assemble_sources(input_, n_shots)
        shot_list: list[ShotSlot] = []
        for i, src in enumerate(sources):
            label = self._director_label(i, n_shots, kind)
            is_hero = (i == 0) or (i == n_shots - 1)
            is_spoiler = any(
                tok in src.lower()
                for tok in _SPOILER_TOKENS
            )
            shot_list.append(
                ShotSlot(
                    index=i,
                    label=label,
                    source_ref=src,
                    duration_s=per_shot,
                    music_beat_index=i,
                    is_hero=is_hero,
                    is_spoiler_risk=is_spoiler,
                ),
            )

        # Title cards: open logo, mid call-to-action, end
        # credits.
        title_cards = self._title_cards_for(kind)

        estimated = (
            sum(s.duration_s for s in shot_list)
            + sum(c.duration_s for c in title_cards)
        )

        plan = TrailerBuildPlan(
            plan_id=plan_id,
            target_kind=kind,
            shot_list=tuple(shot_list),
            title_cards=title_cards,
            music_cue_id=input_.music_cue_id,
            target_runtime_s=budget,
            estimated_runtime_s=estimated,
            hero_zone_ids=tuple(input_.hero_zone_ids),
            hero_character_ids=tuple(input_.hero_character_ids),
            end_credits_voice_cast=tuple(self._voice_cast),
        )
        self._plans[plan_id] = plan
        return plan

    def _assemble_sources(
        self,
        input_: TrailerInput,
        n_shots: int,
    ) -> list[str]:
        sk = input_.source_kind
        out: list[str] = []
        if sk == SourceKind.REPLAY_BUFFER:
            out = list(input_.replay_event_ids)
        elif sk == SourceKind.CHOREOGRAPHY:
            base = input_.showcase_seq_name or "showcase_main"
            out = [f"{base}_shot_{i}" for i in range(n_shots)]
        elif sk == SourceKind.MANUAL_SHOT_LIST:
            out = list(input_.manual_shot_list)
        elif sk == SourceKind.MIXED:
            # Half replay, half choreography.
            base = input_.showcase_seq_name or "showcase_main"
            half = max(1, n_shots // 2)
            replays = list(input_.replay_event_ids)[:half]
            choreo = [
                f"{base}_shot_{i}"
                for i in range(n_shots - len(replays))
            ]
            out = replays + choreo
        # Pad / truncate.
        if len(out) < n_shots:
            # Pad with hero zone shots.
            for i in range(len(out), n_shots):
                if input_.hero_zone_ids:
                    out.append(
                        f"hero_zone_{input_.hero_zone_ids[i % len(input_.hero_zone_ids)]}_{i}",
                    )
                else:
                    out.append(f"filler_shot_{i}")
        elif len(out) > n_shots:
            out = out[:n_shots]
        return out

    def _director_label(
        self,
        i: int,
        n: int,
        kind: TrailerKind,
    ) -> str:
        # Director_ai grammar — wide_establishing opens
        # and closes; the middle alternates across the
        # vocabulary in a kind-specific way.
        if i == 0:
            return "wide_establishing"
        if i == n - 1:
            return "wide_establishing"
        # Fast-tempo trailers prefer handheld + close_up.
        fast_kinds = {
            TrailerKind.TEASER_30S,
            TrailerKind.CONVENTION_SIZZLE_90S,
            TrailerKind.FEATURE_VERTICAL_VIDEO_30S,
        }
        if kind in fast_kinds:
            cycle = (
                "handheld",
                "close_up",
                "medium",
                "extreme_close_up",
            )
        else:
            cycle = (
                "medium",
                "over_the_shoulder",
                "close_up",
                "overhead",
                "handheld",
            )
        return cycle[(i - 1) % len(cycle)]

    def _title_cards_for(
        self,
        kind: TrailerKind,
    ) -> tuple[TitleCard, ...]:
        mid_text_by_kind: dict[TrailerKind, str] = {
            TrailerKind.TEASER_30S: "Coming Soon",
            TrailerKind.STORY_60S: "Coming Soon",
            TrailerKind.GAMEPLAY_2MIN: "Coming Soon",
            TrailerKind.DEEP_DIVE_5MIN: "A New Adventure",
            TrailerKind.CONVENTION_SIZZLE_90S: (
                "See It Live On The Show Floor"
            ),
            TrailerKind.LAUNCH_PROMO_90S: "Available Now",
            TrailerKind.FEATURE_VERTICAL_VIDEO_30S: (
                "Coming Soon"
            ),
        }
        return (
            TitleCard(
                position="open",
                text="Demoncore",
                duration_s=1.5,
            ),
            TitleCard(
                position="mid",
                text=mid_text_by_kind[kind],
                duration_s=1.0,
            ),
            TitleCard(
                position="end",
                text=(
                    "Demoncore — © Demoncore Team — "
                    "voice cast inside"
                ),
                duration_s=1.5,
            ),
        )

    # ---------------------------------------------- access
    def get_plan(self, plan_id: str) -> TrailerBuildPlan:
        if plan_id not in self._plans:
            raise KeyError(f"unknown plan_id: {plan_id}")
        return self._plans[plan_id]

    def plan_count(self) -> int:
        return len(self._plans)

    # ---------------------------------------------- validation
    def validate(
        self,
        plan: TrailerBuildPlan,
    ) -> tuple[str, ...]:
        issues: list[str] = []

        # Runtime within budget (+/- 3 seconds).
        if abs(plan.estimated_runtime_s - plan.target_runtime_s) > 3:
            issues.append(
                "estimated runtime "
                f"{plan.estimated_runtime_s:.1f}s does not "
                f"match target {plan.target_runtime_s}s",
            )

        kind = plan.target_kind
        sources = [s.source_ref.lower() for s in plan.shot_list]
        joined = " ".join(sources)

        # TEASER must hide spoilers.
        if kind == TrailerKind.TEASER_30S:
            if any(s.is_spoiler_risk for s in plan.shot_list):
                issues.append(
                    "teaser contains spoiler-risk shots",
                )

        # STORY requires intro + conflict + resolution.
        if kind == TrailerKind.STORY_60S:
            has_intro = any(
                tok in joined for tok in _STORY_INTRO_TOKENS
            )
            has_conflict = any(
                tok in joined
                for tok in _STORY_CONFLICT_TOKENS
            )
            has_resolution = any(
                tok in joined
                for tok in _STORY_RESOLUTION_TOKENS
            )
            if not has_intro:
                issues.append("story trailer missing intro")
            if not has_conflict:
                issues.append(
                    "story trailer missing conflict",
                )
            if not has_resolution:
                issues.append(
                    "story trailer missing resolution",
                )

        # GAMEPLAY must contain real mechanics.
        if kind == TrailerKind.GAMEPLAY_2MIN:
            has_mechanic = any(
                tok in joined
                for tok in _GAMEPLAY_MECHANIC_TOKENS
            )
            if not has_mechanic:
                issues.append(
                    "gameplay trailer missing real "
                    "mechanics references",
                )

        # All kinds need a hero shot at open and close.
        if plan.shot_list:
            if not plan.shot_list[0].is_hero:
                issues.append("trailer must open on hero shot")
            if not plan.shot_list[-1].is_hero:
                issues.append("trailer must end on hero shot")

        return tuple(issues)

    # ---------------------------------------------- auto
    def trailer_for_event(
        self,
        event_id: str,
        zone_id: str = "",
        character_id: str = "",
        music_cue_id: str = "demoncore_share_loop",
    ) -> TrailerBuildPlan:
        """Quick auto-trailer for save_replay events.
        Always produces a 30-second vertical share clip.
        """
        if not event_id:
            raise ValueError("event_id required")
        input_ = TrailerInput(
            source_kind=SourceKind.REPLAY_BUFFER,
            target_kind=(
                TrailerKind.FEATURE_VERTICAL_VIDEO_30S
            ),
            music_cue_id=music_cue_id,
            hero_zone_ids=(zone_id,) if zone_id else (),
            hero_character_ids=(
                (character_id,) if character_id else ()
            ),
            replay_event_ids=(event_id,),
        )
        return self.build_trailer(input_)


__all__ = [
    "TrailerKind",
    "SourceKind",
    "TrailerInput",
    "ShotSlot",
    "TitleCard",
    "TrailerBuildPlan",
    "TrailerSystem",
]
