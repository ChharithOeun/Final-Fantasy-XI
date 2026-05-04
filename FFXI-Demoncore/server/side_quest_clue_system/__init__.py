"""Side quest clue system — cryptic-hint accumulator.

Demoncore side quests are NOT spoon-fed. The quest log shows a
side quest only after the player has captured at least one
CLUE FRAGMENT for it. Fragments come from:
  * OVERHEARD_CHATTER  — two NPCs conversing 18 yalms away
  * POSTER_HIT          — player examines a wanted/notice poster
  * SUBTLE_NPC_HINT    — speech bubble above an NPC, in earshot
  * MOB_DROP_NOTE      — note on a corpse / a slain enemy mutters
  * ENVIRONMENT_CLUE   — bloody footprints, scrawled wall text
  * RUMOR_OVERHEARD    — rumor_propagation tags the player

Each clue fragment is small. Collect enough (or the right ones)
and the side quest "becomes legible" — the log card grows from
"???" to a partial title to a full description. At full
legibility the player gets the start NPC + step list, but only
then.

Public surface
--------------
    ClueSourceKind enum
    LegibilityTier enum
    ClueFragment dataclass
    SideQuestCard dataclass
    SideQuestClueSystem
        .register_side_quest(quest_id, total_fragments_required)
        .add_fragment_kind(quest_id, source_kind, weight)
        .capture_fragment(player_id, quest_id, source_kind)
        .legibility_for(player_id, quest_id)
        .visible_quests(player_id) -> tuple[SideQuestCard]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
DEFAULT_TIER_1_FRAGMENTS = 1     # ??? -> faint smell
DEFAULT_TIER_2_FRAGMENTS = 3     # partial title
DEFAULT_TIER_3_FRAGMENTS = 6     # full description


class ClueSourceKind(str, enum.Enum):
    OVERHEARD_CHATTER = "overheard_chatter"
    POSTER_HIT = "poster_hit"
    SUBTLE_NPC_HINT = "subtle_npc_hint"
    MOB_DROP_NOTE = "mob_drop_note"
    ENVIRONMENT_CLUE = "environment_clue"
    RUMOR_OVERHEARD = "rumor_overheard"


class LegibilityTier(str, enum.Enum):
    HIDDEN = "hidden"
    SMELL = "smell"            # tier 1 — "you sense something..."
    PARTIAL_TITLE = "partial_title"   # tier 2
    FULL = "full"              # tier 3 — start NPC visible


@dataclasses.dataclass(frozen=True)
class ClueFragment:
    fragment_id: str
    quest_id: str
    source_kind: ClueSourceKind
    captured_at_seconds: float
    weight: int = 1


@dataclasses.dataclass
class SideQuestRegistration:
    quest_id: str
    title: str
    full_description: str = ""
    start_npc_id: t.Optional[str] = None
    fragment_weights: dict[
        ClueSourceKind, int,
    ] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class SideQuestCard:
    quest_id: str
    title_visible: str
    body_visible: str
    legibility: LegibilityTier
    captured_fragments: int
    start_npc_visible: t.Optional[str]


@dataclasses.dataclass
class _PlayerQuestState:
    fragments: list[ClueFragment] = dataclasses.field(
        default_factory=list,
    )
    score: int = 0


@dataclasses.dataclass
class SideQuestClueSystem:
    tier_1_fragments: int = DEFAULT_TIER_1_FRAGMENTS
    tier_2_fragments: int = DEFAULT_TIER_2_FRAGMENTS
    tier_3_fragments: int = DEFAULT_TIER_3_FRAGMENTS
    _quests: dict[str, SideQuestRegistration] = dataclasses.field(
        default_factory=dict,
    )
    _state: dict[
        tuple[str, str], _PlayerQuestState,
    ] = dataclasses.field(default_factory=dict)
    _next_fragment_id: int = 0

    def register_side_quest(
        self, *, quest_id: str, title: str,
        full_description: str = "",
        start_npc_id: t.Optional[str] = None,
    ) -> t.Optional[SideQuestRegistration]:
        if quest_id in self._quests:
            return None
        reg = SideQuestRegistration(
            quest_id=quest_id, title=title,
            full_description=full_description,
            start_npc_id=start_npc_id,
        )
        self._quests[quest_id] = reg
        return reg

    def add_fragment_kind(
        self, *, quest_id: str,
        source_kind: ClueSourceKind, weight: int = 1,
    ) -> bool:
        reg = self._quests.get(quest_id)
        if reg is None or weight <= 0:
            return False
        reg.fragment_weights[source_kind] = weight
        return True

    def capture_fragment(
        self, *, player_id: str, quest_id: str,
        source_kind: ClueSourceKind,
        captured_at_seconds: float = 0.0,
    ) -> t.Optional[ClueFragment]:
        reg = self._quests.get(quest_id)
        if reg is None:
            return None
        # If the quest hasn't declared this source kind, default
        # weight is 1 (lets us capture clues from generic sources).
        weight = reg.fragment_weights.get(source_kind, 1)
        fid = f"clue_{self._next_fragment_id}"
        self._next_fragment_id += 1
        frag = ClueFragment(
            fragment_id=fid, quest_id=quest_id,
            source_kind=source_kind,
            captured_at_seconds=captured_at_seconds,
            weight=weight,
        )
        key = (player_id, quest_id)
        st = self._state.setdefault(key, _PlayerQuestState())
        st.fragments.append(frag)
        st.score += weight
        return frag

    def legibility_for(
        self, *, player_id: str, quest_id: str,
    ) -> LegibilityTier:
        st = self._state.get((player_id, quest_id))
        if st is None or st.score < self.tier_1_fragments:
            return LegibilityTier.HIDDEN
        if st.score < self.tier_2_fragments:
            return LegibilityTier.SMELL
        if st.score < self.tier_3_fragments:
            return LegibilityTier.PARTIAL_TITLE
        return LegibilityTier.FULL

    def card_for(
        self, *, player_id: str, quest_id: str,
    ) -> t.Optional[SideQuestCard]:
        reg = self._quests.get(quest_id)
        if reg is None:
            return None
        tier = self.legibility_for(
            player_id=player_id, quest_id=quest_id,
        )
        if tier == LegibilityTier.HIDDEN:
            return None
        st = self._state.get((player_id, quest_id))
        captured = len(st.fragments) if st else 0
        if tier == LegibilityTier.SMELL:
            title = "???"
            body = (
                "Something's nagging at you. You can't"
                " quite place it."
            )
            start_npc_visible = None
        elif tier == LegibilityTier.PARTIAL_TITLE:
            # Show first half of title
            half = max(1, len(reg.title) // 2)
            title = reg.title[:half] + "..."
            body = "More clues might shed light."
            start_npc_visible = None
        else:
            title = reg.title
            body = reg.full_description
            start_npc_visible = reg.start_npc_id
        return SideQuestCard(
            quest_id=quest_id, title_visible=title,
            body_visible=body, legibility=tier,
            captured_fragments=captured,
            start_npc_visible=start_npc_visible,
        )

    def visible_quests(
        self, player_id: str,
    ) -> tuple[SideQuestCard, ...]:
        out: list[SideQuestCard] = []
        for (pid, qid), _ in self._state.items():
            if pid != player_id:
                continue
            card = self.card_for(
                player_id=player_id, quest_id=qid,
            )
            if card is not None:
                out.append(card)
        out.sort(key=lambda c: c.quest_id)
        return tuple(out)

    def total_quests(self) -> int:
        return len(self._quests)


__all__ = [
    "DEFAULT_TIER_1_FRAGMENTS",
    "DEFAULT_TIER_2_FRAGMENTS",
    "DEFAULT_TIER_3_FRAGMENTS",
    "ClueSourceKind", "LegibilityTier",
    "ClueFragment", "SideQuestRegistration",
    "SideQuestCard",
    "SideQuestClueSystem",
]
