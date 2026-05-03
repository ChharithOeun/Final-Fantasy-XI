"""AI quest curator — surfaces best-fit quests per player.

Out of the dozens (eventually hundreds) of quests live at any
moment — authored chains, dynamic_quest_gen output, ai_plot_generator
hooks, faction tasks — the curator picks WHICH ones a particular
player sees lit up on their NPCs.

Selection signals
-----------------
* level proximity (within +/- 5 of player level scores high)
* faction reputation (matches/exceeds faction rep gate)
* player mood preference (combat-leaning vs craft-leaning)
* quest tag affinity (genres player has finished before)
* zone proximity (player in/near quest zone scores higher)
* NM-kill recency (revenge arcs spike if player just slew a boss)

The curator does NOT push the quest into the player's log; it
just decides which NPCs SHOW the "!" beacon. dialogue_tree picks
it up from there.

Public surface
--------------
    QuestCard dataclass — a candidate
    PlayerProfile dataclass — current state
    CurationResult dataclass
    AIQuestCurator
        .add_card(QuestCard)
        .remove_card(quest_id)
        .curate(player_profile, max_results=N) -> tuple[QuestCard]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default cap on visible quests per player per session.
DEFAULT_MAX_VISIBLE_QUESTS = 10
LEVEL_PROXIMITY_WINDOW = 5
ZONE_PROXIMITY_BONUS = 25
FACTION_MISMATCH_PENALTY = 50
TAG_AFFINITY_BONUS_PER_HIT = 5


class QuestKind(str, enum.Enum):
    AUTHORED = "authored"
    DYNAMIC = "dynamic"
    PLOT_HOOK = "plot_hook"
    FACTION_CHAIN = "faction_chain"
    DAILY_TASK = "daily_task"


@dataclasses.dataclass(frozen=True)
class QuestCard:
    quest_id: str
    title: str
    kind: QuestKind
    suggested_level: int
    faction_id: t.Optional[str] = None
    min_faction_rep: int = 0
    zone_id: t.Optional[str] = None
    tags: tuple[str, ...] = ()
    npc_giver_id: t.Optional[str] = None
    is_revenge_arc: bool = False
    target_player_id: t.Optional[str] = None
    base_score: int = 50


@dataclasses.dataclass
class PlayerProfile:
    player_id: str
    level: int = 1
    current_zone_id: t.Optional[str] = None
    faction_reputations: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    completed_tags: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )
    mood_preference: str = ""    # e.g. "combat", "craft"
    recently_killed_bosses: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class CurationResult:
    quest_id: str
    title: str
    kind: QuestKind
    score: int
    npc_giver_id: t.Optional[str] = None


@dataclasses.dataclass
class AIQuestCurator:
    max_visible_quests: int = DEFAULT_MAX_VISIBLE_QUESTS
    _cards: dict[str, QuestCard] = dataclasses.field(
        default_factory=dict,
    )

    def add_card(self, card: QuestCard) -> bool:
        if card.quest_id in self._cards:
            return False
        self._cards[card.quest_id] = card
        return True

    def remove_card(self, quest_id: str) -> bool:
        return self._cards.pop(quest_id, None) is not None

    def total_cards(self) -> int:
        return len(self._cards)

    def _score(
        self, *, card: QuestCard,
        player: PlayerProfile,
    ) -> int:
        score = card.base_score

        # Level proximity (in window = +20, far = penalized)
        delta = abs(card.suggested_level - player.level)
        if delta <= LEVEL_PROXIMITY_WINDOW:
            score += (LEVEL_PROXIMITY_WINDOW - delta) * 4
        else:
            score -= min(40, delta * 2)

        # Faction rep gate
        if card.faction_id is not None:
            rep = player.faction_reputations.get(
                card.faction_id, 0,
            )
            if rep < card.min_faction_rep:
                score -= FACTION_MISMATCH_PENALTY
            else:
                # Above gate gives a small bonus
                score += 10

        # Zone proximity
        if (
            card.zone_id is not None
            and card.zone_id == player.current_zone_id
        ):
            score += ZONE_PROXIMITY_BONUS

        # Tag affinity (player likes what they completed before)
        for tag in card.tags:
            score += (
                player.completed_tags.get(tag, 0)
                * TAG_AFFINITY_BONUS_PER_HIT
            )

        # Mood preference
        if (
            player.mood_preference
            and player.mood_preference in card.tags
        ):
            score += 15

        # Revenge arc must match player
        if card.is_revenge_arc:
            if (
                card.target_player_id != player.player_id
            ):
                # not for this player
                score = 0
            else:
                score += 30

        # Daily tasks float to top when player has nothing in
        # progress (we don't know in-progress here, so just a
        # mild bias)
        if card.kind == QuestKind.DAILY_TASK:
            score += 5

        return max(0, score)

    def curate(
        self, *, player: PlayerProfile,
        max_results: t.Optional[int] = None,
    ) -> tuple[CurationResult, ...]:
        cap = max_results or self.max_visible_quests
        scored: list[tuple[int, QuestCard]] = []
        for card in self._cards.values():
            s = self._score(card=card, player=player)
            if s <= 0:
                continue
            scored.append((s, card))
        # Sort: higher score first, then deterministic by id
        scored.sort(
            key=lambda t: (-t[0], t[1].quest_id),
        )
        out: list[CurationResult] = []
        for s, card in scored[:cap]:
            out.append(CurationResult(
                quest_id=card.quest_id, title=card.title,
                kind=card.kind, score=s,
                npc_giver_id=card.npc_giver_id,
            ))
        return tuple(out)


__all__ = [
    "DEFAULT_MAX_VISIBLE_QUESTS",
    "LEVEL_PROXIMITY_WINDOW",
    "QuestKind", "QuestCard", "PlayerProfile",
    "CurationResult", "AIQuestCurator",
]
