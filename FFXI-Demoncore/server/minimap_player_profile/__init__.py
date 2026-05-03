"""Minimap player profile — click player dot, get snapshot.

When a viewer clicks (or hovers) another player's dot on the
minimap, this module returns a profile snapshot card. The card
respects PRIVACY: each player chooses what they expose to
strangers vs party-mates vs linkshell-mates vs friends. A
party-mate may see the player's full job/level/title; a stranger
may only see name and nation.

Public surface
--------------
    AudienceLevel enum
    PrivacyPreferences dataclass
    ProfileSnapshot dataclass
    MinimapPlayerProfileRegistry
        .upsert_profile(player_id, name, level, ...)
        .set_privacy(player_id, audience -> shown_fields)
        .declare_relation(viewer_id, target_id, level)
        .snapshot_for(viewer_id, target_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AudienceLevel(str, enum.Enum):
    STRANGER = "stranger"
    LINKSHELL = "linkshell"
    PARTY = "party"
    FRIEND = "friend"


# Field names a player can expose.
SHOWABLE_FIELDS: tuple[str, ...] = (
    "name", "nation", "level", "main_job", "sub_job",
    "title", "linkshell", "fame", "playtime_hours",
    "outlaw_flag",
)


# Default exposure per audience.
_DEFAULT_PRIVACY: dict[AudienceLevel, set[str]] = {
    AudienceLevel.STRANGER: {"name", "nation"},
    AudienceLevel.LINKSHELL: {
        "name", "nation", "level", "main_job",
        "linkshell", "title",
    },
    AudienceLevel.PARTY: {
        "name", "nation", "level", "main_job", "sub_job",
        "title", "linkshell",
    },
    AudienceLevel.FRIEND: set(SHOWABLE_FIELDS),
}


@dataclasses.dataclass
class PrivacyPreferences:
    player_id: str
    exposure: dict[AudienceLevel, set[str]] = dataclasses.field(
        default_factory=lambda: {
            level: set(fields)
            for level, fields in _DEFAULT_PRIVACY.items()
        },
    )


@dataclasses.dataclass
class _PlayerProfile:
    player_id: str
    name: str = ""
    nation: str = ""
    level: int = 1
    main_job: str = ""
    sub_job: str = ""
    title: str = ""
    linkshell: str = ""
    fame: int = 0
    playtime_hours: int = 0
    outlaw_flag: bool = False


@dataclasses.dataclass(frozen=True)
class ProfileSnapshot:
    target_player_id: str
    audience: AudienceLevel
    fields: dict[str, t.Any]


@dataclasses.dataclass
class MinimapPlayerProfileRegistry:
    _profiles: dict[str, _PlayerProfile] = dataclasses.field(
        default_factory=dict,
    )
    _privacy: dict[str, PrivacyPreferences] = dataclasses.field(
        default_factory=dict,
    )
    # viewer -> target -> AudienceLevel
    _relations: dict[
        str, dict[str, AudienceLevel],
    ] = dataclasses.field(default_factory=dict)

    def upsert_profile(
        self, *, player_id: str, **fields: t.Any,
    ) -> _PlayerProfile:
        prof = self._profiles.get(player_id)
        if prof is None:
            prof = _PlayerProfile(player_id=player_id)
            self._profiles[player_id] = prof
        for k, v in fields.items():
            if hasattr(prof, k):
                setattr(prof, k, v)
        # Initialize privacy on first sight
        self._privacy.setdefault(
            player_id,
            PrivacyPreferences(player_id=player_id),
        )
        return prof

    def set_privacy(
        self, *, player_id: str,
        audience: AudienceLevel,
        shown_fields: t.Iterable[str],
    ) -> bool:
        prefs = self._privacy.get(player_id)
        if prefs is None:
            return False
        # Filter to only valid fields
        valid = {
            f for f in shown_fields
            if f in SHOWABLE_FIELDS
        }
        prefs.exposure[audience] = valid
        return True

    def declare_relation(
        self, *, viewer_id: str, target_id: str,
        audience: AudienceLevel,
    ) -> bool:
        if viewer_id == target_id:
            return False
        self._relations.setdefault(
            viewer_id, {},
        )[target_id] = audience
        return True

    def relation(
        self, *, viewer_id: str, target_id: str,
    ) -> AudienceLevel:
        return self._relations.get(
            viewer_id, {},
        ).get(target_id, AudienceLevel.STRANGER)

    def snapshot_for(
        self, *, viewer_id: str, target_id: str,
    ) -> t.Optional[ProfileSnapshot]:
        prof = self._profiles.get(target_id)
        if prof is None:
            return None
        prefs = self._privacy.get(target_id)
        if prefs is None:
            return None
        audience = self.relation(
            viewer_id=viewer_id, target_id=target_id,
        )
        shown = prefs.exposure.get(audience, set())
        # OUTLAW_FLAG is special: if set, every audience sees it
        # (you don't hide a server-bounty status)
        out: dict[str, t.Any] = {}
        for field in shown:
            out[field] = getattr(prof, field, None)
        if prof.outlaw_flag:
            out["outlaw_flag"] = True
        return ProfileSnapshot(
            target_player_id=target_id,
            audience=audience,
            fields=out,
        )

    def total_profiles(self) -> int:
        return len(self._profiles)


__all__ = [
    "SHOWABLE_FIELDS",
    "AudienceLevel", "PrivacyPreferences",
    "ProfileSnapshot",
    "MinimapPlayerProfileRegistry",
]
