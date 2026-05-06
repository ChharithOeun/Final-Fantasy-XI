"""Battle environment announcer — narrate the room as it falls.

When the floor caves in, when the dam bursts, when the
ceiling cracks, when the kelp wall breaches and elasmos
swoop in — somebody has to TELL the alliance that just
happened. The audible-callouts module is for combat-
specific calls. This module is for the ENVIRONMENT.

It produces structured announcement records with:
    severity (WHISPER / SAY / SHOUT / RAID_BANNER)
    audio_cue (sound id for surround mixer)
    voice_line (text to TTS, with optional voice profile)
    duration_seconds (how long the banner stays up)

It debounces to avoid spam — if the same feature cracks
3 times in a row from boss tells, the alliance hears one
big "THE WALL IS GIVING WAY!" not three identical lines.
And it has SEVERITY UPGRADE: cracks are SAY, breaks are
SHOUT, alliance-wide hazards are RAID_BANNER.

Public surface
--------------
    Severity enum
    AnnouncementKind enum
    Announcement dataclass (frozen)
    BattleEnvironmentAnnouncer
        .on_crack(arena_id, feature_id, feature_kind, now)
            -> Optional[Announcement]
        .on_break(arena_id, feature_id, feature_kind, now)
            -> Optional[Announcement]
        .on_habitat_swoop(arena_id, biome, count, now)
            -> Announcement
        .on_cascade(arena_id, source_id, target_id, now)
            -> Announcement
        .recent(arena_id, since_seconds)
            -> tuple[Announcement, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.arena_environment import FeatureKind
from server.habitat_disturbance import HabitatBiome


class Severity(str, enum.Enum):
    WHISPER = "whisper"
    SAY = "say"
    SHOUT = "shout"
    RAID_BANNER = "raid_banner"


class AnnouncementKind(str, enum.Enum):
    CRACK_WARNING = "crack_warning"
    BREAK_EVENT = "break_event"
    HABITAT_SWOOP = "habitat_swoop"
    CASCADE = "cascade"


# Debounce window: same (kind, feature_id) within this many
# seconds collapses into the previous announcement.
DEBOUNCE_SECONDS = 5

# Per-feature one-line library. Keys are FeatureKind values.
_BREAK_LINES: dict[FeatureKind, str] = {
    FeatureKind.WALL: "THE WALL CAVES IN!",
    FeatureKind.FLOOR: "THE FLOOR GIVES WAY!",
    FeatureKind.CEILING: "THE CEILING COMES DOWN!",
    FeatureKind.ICE_SHEET: "THE ICE SHATTERS!",
    FeatureKind.PILLAR: "THE PILLAR FALLS!",
    FeatureKind.BRIDGE: "THE BRIDGE SNAPS!",
    FeatureKind.DAM: "THE DAM BURSTS!",
    FeatureKind.SHIP_HULL: "THE HULL IS BREACHED!",
}

_CRACK_LINES: dict[FeatureKind, str] = {
    FeatureKind.WALL: "the wall groans, near collapse",
    FeatureKind.FLOOR: "the floor sags ominously",
    FeatureKind.CEILING: "dust rains from above — the ceiling is failing",
    FeatureKind.ICE_SHEET: "spider-web cracks spread across the ice",
    FeatureKind.PILLAR: "the pillar leans — it won't hold much longer",
    FeatureKind.BRIDGE: "the rope-bridge frays",
    FeatureKind.DAM: "water hisses through cracks in the dam",
    FeatureKind.SHIP_HULL: "the hull creaks — a breach is coming",
}

_HABITAT_SWOOP_LINES: dict[HabitatBiome, str] = {
    HabitatBiome.UNDERSEA: "Sharks swarm in through the breach!",
    HabitatBiome.KELP_FOREST: "The kelp parts — beasts emerge!",
    HabitatBiome.CAVE: "Bats flood the room!",
    HabitatBiome.SHIPWRECK: "Ghouls climb up from the wreck!",
    HabitatBiome.SKY_NEST: "Birds dive through the gap!",
    HabitatBiome.FROZEN_DEEP: "Things from the deep slither up!",
    HabitatBiome.LAVA_VENT: "Magma elementals burst through!",
    HabitatBiome.JUNGLE_CANOPY: "The canopy shakes — predators drop in!",
}


@dataclasses.dataclass(frozen=True)
class Announcement:
    arena_id: str
    kind: AnnouncementKind
    severity: Severity
    voice_line: str
    audio_cue: str
    duration_seconds: int
    fired_at: int


@dataclasses.dataclass
class BattleEnvironmentAnnouncer:
    # arena_id -> list[Announcement]
    _log: dict[str, list[Announcement]] = dataclasses.field(
        default_factory=dict,
    )
    # (arena_id, kind, key) -> last fired at
    _last: dict[tuple[str, AnnouncementKind, str], int] = dataclasses.field(
        default_factory=dict,
    )

    def _debounced(
        self, *, arena_id: str, kind: AnnouncementKind,
        key: str, now_seconds: int,
    ) -> bool:
        last = self._last.get((arena_id, kind, key), -10**9)
        if (now_seconds - last) < DEBOUNCE_SECONDS:
            return True
        self._last[(arena_id, kind, key)] = now_seconds
        return False

    def _record(
        self, *, arena_id: str, ann: Announcement,
    ) -> None:
        self._log.setdefault(arena_id, []).append(ann)

    def on_crack(
        self, *, arena_id: str, feature_id: str,
        feature_kind: FeatureKind, now_seconds: int,
    ) -> t.Optional[Announcement]:
        if self._debounced(
            arena_id=arena_id, kind=AnnouncementKind.CRACK_WARNING,
            key=feature_id, now_seconds=now_seconds,
        ):
            return None
        line = _CRACK_LINES.get(feature_kind, "something cracks")
        ann = Announcement(
            arena_id=arena_id,
            kind=AnnouncementKind.CRACK_WARNING,
            severity=Severity.SAY,
            voice_line=line,
            audio_cue=f"sfx_crack_{feature_kind.value}",
            duration_seconds=4,
            fired_at=now_seconds,
        )
        self._record(arena_id=arena_id, ann=ann)
        return ann

    def on_break(
        self, *, arena_id: str, feature_id: str,
        feature_kind: FeatureKind, now_seconds: int,
    ) -> t.Optional[Announcement]:
        if self._debounced(
            arena_id=arena_id, kind=AnnouncementKind.BREAK_EVENT,
            key=feature_id, now_seconds=now_seconds,
        ):
            return None
        line = _BREAK_LINES.get(feature_kind, "SOMETHING BREAKS!")
        # Major breaks fire RAID_BANNER; lesser feature kinds use SHOUT
        major = feature_kind in (
            FeatureKind.FLOOR, FeatureKind.CEILING,
            FeatureKind.DAM, FeatureKind.SHIP_HULL,
        )
        sev = Severity.RAID_BANNER if major else Severity.SHOUT
        ann = Announcement(
            arena_id=arena_id,
            kind=AnnouncementKind.BREAK_EVENT,
            severity=sev,
            voice_line=line,
            audio_cue=f"sfx_break_{feature_kind.value}",
            duration_seconds=8 if major else 5,
            fired_at=now_seconds,
        )
        self._record(arena_id=arena_id, ann=ann)
        return ann

    def on_habitat_swoop(
        self, *, arena_id: str, biome: HabitatBiome,
        count: int, now_seconds: int,
    ) -> Announcement:
        # No debounce — every swoop is news
        line = _HABITAT_SWOOP_LINES.get(biome, "Things emerge from the gap!")
        if count >= 4:
            line = f"{line} ({count})"
        ann = Announcement(
            arena_id=arena_id,
            kind=AnnouncementKind.HABITAT_SWOOP,
            severity=Severity.SHOUT,
            voice_line=line,
            audio_cue=f"sfx_swoop_{biome.value}",
            duration_seconds=6,
            fired_at=now_seconds,
        )
        self._record(arena_id=arena_id, ann=ann)
        return ann

    def on_cascade(
        self, *, arena_id: str, source_feature_id: str,
        target_feature_id: str, now_seconds: int,
    ) -> Announcement:
        line = (
            f"{source_feature_id} drags {target_feature_id} down with it!"
        )
        ann = Announcement(
            arena_id=arena_id,
            kind=AnnouncementKind.CASCADE,
            severity=Severity.SAY,
            voice_line=line,
            audio_cue="sfx_cascade",
            duration_seconds=4,
            fired_at=now_seconds,
        )
        self._record(arena_id=arena_id, ann=ann)
        return ann

    def recent(
        self, *, arena_id: str, since_seconds: int,
    ) -> tuple[Announcement, ...]:
        log = self._log.get(arena_id, [])
        return tuple(a for a in log if a.fired_at >= since_seconds)

    def clear_arena(self, *, arena_id: str) -> bool:
        if arena_id in self._log:
            del self._log[arena_id]
        # also drop debounce keys
        for k in list(self._last.keys()):
            if k[0] == arena_id:
                del self._last[k]
        return True


__all__ = [
    "Severity", "AnnouncementKind", "Announcement",
    "BattleEnvironmentAnnouncer",
    "DEBOUNCE_SECONDS",
]
