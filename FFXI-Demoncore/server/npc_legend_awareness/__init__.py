"""NPC legend awareness — NPCs recognize famous players.

When a player walks into a tavern and the inkeep recognizes
them as Vorrak's Bane, that interaction should land
differently than the same inkeep meeting a level-30 stranger.
This module reads the player's hero_titles AND their
faction_reputation gauges, and produces a structured
RecognitionResult that other modules use to color their
behavior (vendor pricing, quest unlocks, salutes, dialogue).

Recognition tiers (from highest title held):
    UNKNOWN       no notable titles
    NOTED         RARE-tier title in their record
    HONORED       EPIC-tier title
    REVERED       LEGENDARY-tier title
    MYTHICAL      MYTHIC-tier title — the rarest reaction

Public surface
--------------
    RecognitionTier enum
    RecognitionResult dataclass (frozen)
    NpcLegendAwareness
        .recognize(player_id, title_registry,
                   faction_id=None, faction_rep_score=0)
            -> RecognitionResult
        .reaction_phrase_for(tier) -> str
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.hero_titles import HeroTitleRegistry, TitleTier


class RecognitionTier(str, enum.Enum):
    UNKNOWN = "unknown"
    NOTED = "noted"
    HONORED = "honored"
    REVERED = "revered"
    MYTHICAL = "mythical"


_REACTION_PHRASES = {
    RecognitionTier.UNKNOWN:
        "The NPC barely looks up.",
    RecognitionTier.NOTED:
        "The NPC nods in faint recognition.",
    RecognitionTier.HONORED:
        "The NPC straightens, eyes widening.",
    RecognitionTier.REVERED:
        "The NPC bows their head respectfully.",
    RecognitionTier.MYTHICAL:
        "The NPC drops what they were doing and stares.",
}


_TIER_TO_RECOGNITION = {
    TitleTier.COMMON: RecognitionTier.UNKNOWN,
    TitleTier.RARE: RecognitionTier.NOTED,
    TitleTier.EPIC: RecognitionTier.HONORED,
    TitleTier.LEGENDARY: RecognitionTier.REVERED,
    TitleTier.MYTHIC: RecognitionTier.MYTHICAL,
}


@dataclasses.dataclass(frozen=True)
class RecognitionResult:
    tier: RecognitionTier
    highest_title_id: t.Optional[str]
    faction_friendly: bool       # rep ≥ +50
    faction_hostile: bool        # rep ≤ -50
    reaction_phrase: str


@dataclasses.dataclass
class NpcLegendAwareness:
    _calls: int = 0

    def recognize(
        self, *, player_id: str,
        title_registry: HeroTitleRegistry,
        faction_id: t.Optional[str] = None,
        faction_rep_score: int = 0,
    ) -> RecognitionResult:
        self._calls += 1
        if not player_id:
            return RecognitionResult(
                tier=RecognitionTier.UNKNOWN,
                highest_title_id=None,
                faction_friendly=False,
                faction_hostile=False,
                reaction_phrase=_REACTION_PHRASES[
                    RecognitionTier.UNKNOWN
                ],
            )
        # find their highest tier
        grants = title_registry.titles_for_player(
            player_id=player_id,
        )
        best_tier: t.Optional[TitleTier] = None
        best_id: t.Optional[str] = None
        for g in grants:
            td = title_registry.get_title(title_id=g.title_id)
            if td is None:
                continue
            if best_tier is None:
                best_tier = td.tier
                best_id = g.title_id
                continue
            # higher = better
            from server.hero_titles import _TIER_ORDER  # type: ignore
            if _TIER_ORDER[td.tier] > _TIER_ORDER[best_tier]:
                best_tier = td.tier
                best_id = g.title_id

        if best_tier is None:
            tier = RecognitionTier.UNKNOWN
        else:
            tier = _TIER_TO_RECOGNITION[best_tier]

        friendly = faction_rep_score >= 50
        hostile = faction_rep_score <= -50
        return RecognitionResult(
            tier=tier,
            highest_title_id=best_id,
            faction_friendly=friendly,
            faction_hostile=hostile,
            reaction_phrase=_REACTION_PHRASES[tier],
        )

    def reaction_phrase_for(
        self, *, tier: RecognitionTier,
    ) -> str:
        return _REACTION_PHRASES[tier]

    def total_recognitions(self) -> int:
        return self._calls


__all__ = [
    "RecognitionTier", "RecognitionResult",
    "NpcLegendAwareness",
]
