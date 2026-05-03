"""NPC dialogue system — assembling what the NPC says.

When a player walks up to an NPC and starts a conversation, the
orchestrator needs to produce a turn of dialogue. The NPC is
driven by a real AI model, so the actual words come from the
LLM. This module's job is to BUILD THE PROMPT — assemble all
the contextual signals the LLM needs to stay in character:

* The NPC's own persona (handled by entity_ai_binding)
* The player's identity + reputation with the NPC's faction
* Memories the NPC holds about this specific player
* The NPC's current routine (selling vs. drinking vs. patrolling)
* Recent rumors the NPC has heard
* The NPC's mood (tired, anxious, curious)
* The NPC's personality (gives the LLM a register / tone)

This module is deterministic — no LLM calls, no flavor text.
The orchestrator gets a `DialogueContext` back; from there the
LLM produces the actual line. Other systems consume the context
shape too (the bark system, the quest-offer system).

Public surface
--------------
    InteractionKind enum (GREETING / SHOP / QUEST_OFFER /
                          QUEST_PROGRESS / QUEST_TURN_IN /
                          GOSSIP / FAREWELL / IDLE_OBSERVED)
    DialogueTone enum (WARM / COOL / TERSE / WARY / RUDE /
                        REVERENT / FEARFUL / HOSTILE)
    MemorySummary dataclass
    DialogueContext dataclass — the full assembled bundle
    DialogueAssembler
        .assemble(npc_id, player_id, ...)  -> DialogueContext
    tone_for_band(band) -> DialogueTone   helper
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.entity_memory import (
    Memory,
    MemoryRegistry,
)
from server.faction_reputation import (
    PlayerFactionReputation,
    ReputationBand,
)
from server.mob_personality import (
    PersonalityRegistry,
    PersonalityVector,
    describe as describe_personality,
)
from server.npc_daily_routines import (
    ActiveRoutine,
    NPCRoutineRegistry,
)
from server.rumor_propagation import (
    Rumor,
    RumorPropagationEngine,
)


class InteractionKind(str, enum.Enum):
    GREETING = "greeting"
    SHOP = "shop"
    QUEST_OFFER = "quest_offer"
    QUEST_PROGRESS = "quest_progress"
    QUEST_TURN_IN = "quest_turn_in"
    GOSSIP = "gossip"
    FAREWELL = "farewell"
    IDLE_OBSERVED = "idle_observed"   # player observed, no talk yet


class DialogueTone(str, enum.Enum):
    WARM = "warm"           # FRIENDLY+ rep
    COOL = "cool"           # NEUTRAL rep
    TERSE = "terse"         # rushed (busy routine) but neutral
    WARY = "wary"           # UNFRIENDLY rep
    RUDE = "rude"           # HOSTILE rep
    REVERENT = "reverent"   # ALLIED+ rep
    FEARFUL = "fearful"     # KILL_ON_SIGHT but cornered
    HOSTILE = "hostile"     # combat-imminent


# Default tone derived from rep band; the assembler can override
# (e.g. terse if the NPC is in PATROL routine).
_TONE_BY_BAND: dict[ReputationBand, DialogueTone] = {
    ReputationBand.HERO_OF_THE_FACTION: DialogueTone.REVERENT,
    ReputationBand.ALLIED: DialogueTone.WARM,
    ReputationBand.FRIENDLY: DialogueTone.WARM,
    ReputationBand.NEUTRAL: DialogueTone.COOL,
    ReputationBand.UNFRIENDLY: DialogueTone.WARY,
    ReputationBand.HOSTILE: DialogueTone.RUDE,
    ReputationBand.KILL_ON_SIGHT: DialogueTone.HOSTILE,
}


def tone_for_band(band: ReputationBand) -> DialogueTone:
    return _TONE_BY_BAND[band]


# Routines that justify a TERSE override regardless of rep —
# the NPC is busy and can't stop to chat.
_TERSE_ROUTINES: frozenset[str] = frozenset({
    "patrol", "guard_post", "craft", "study", "pray", "train",
})


@dataclasses.dataclass(frozen=True)
class MemorySummary:
    """Compact memory pulled into the prompt. Top-N by salience."""
    kind: str
    other_entity_id: t.Optional[str]
    salience: int
    details: str


@dataclasses.dataclass(frozen=True)
class DialogueContext:
    """Everything the LLM needs to stay in character."""
    npc_id: str
    player_id: str
    interaction_kind: InteractionKind
    tone: DialogueTone
    rep_band: ReputationBand
    rep_value: int
    faction_id: str
    routine: t.Optional[ActiveRoutine]
    is_busy: bool
    relevant_memories: tuple[MemorySummary, ...]
    recent_rumors: tuple[str, ...]
    personality_tags: tuple[str, ...]
    personality_vector: t.Optional[PersonalityVector]
    notes: str = ""

    @property
    def will_speak(self) -> bool:
        """Hostile NPCs don't TALK, they fight. Fearful only if
        cornered. Use this to decide whether to dispatch to LLM
        at all or just emit a combat reaction."""
        return self.tone not in (
            DialogueTone.HOSTILE, DialogueTone.FEARFUL,
        )


@dataclasses.dataclass
class DialogueAssembler:
    """Pulls signal from all the registries and shapes a context.

    All registries are optional — pass only what you have. Missing
    inputs degrade gracefully (no memory pull, no rumor pull, etc).
    """
    memory_registry: t.Optional[MemoryRegistry] = None
    rumor_engine: t.Optional[RumorPropagationEngine] = None
    routine_registry: t.Optional[NPCRoutineRegistry] = None
    personality_registry: t.Optional[PersonalityRegistry] = None
    # How many memories / rumors to lift into the prompt.
    memory_top_n: int = 5
    rumor_top_n: int = 3

    def assemble(
        self, *, npc_id: str, player_id: str, faction_id: str,
        rep: PlayerFactionReputation,
        interaction_kind: InteractionKind = InteractionKind.GREETING,
        now_seconds: float = 0.0, now_hour: int = 12,
    ) -> DialogueContext:
        rep_value = rep.value(faction_id)
        rep_band = rep.band(faction_id)
        # Memory pull — top-N by decayed salience about this player
        memories: tuple[MemorySummary, ...] = ()
        if self.memory_registry is not None:
            store = self.memory_registry.store_for(npc_id)
            relevant = store.about(
                other_entity_id=player_id,
                now_seconds=now_seconds,
                top_n=self.memory_top_n,
            )
            memories = tuple(
                MemorySummary(
                    kind=m.kind.value,
                    other_entity_id=m.other_entity_id,
                    salience=store.salience_at(
                        memory_id=m.memory_id,
                        now_seconds=now_seconds,
                    ) or 0,
                    details=m.details,
                )
                for m in relevant
            )
        # Rumor pull — what gossip the NPC is currently sitting on
        rumors: tuple[str, ...] = ()
        if self.rumor_engine is not None:
            held = self.rumor_engine.rumors_at(npc_id)
            # Sort by salience desc, take top-N summaries
            sorted_rumors = sorted(
                held, key=lambda pair: pair[0].salience,
                reverse=True,
            )[:self.rumor_top_n]
            rumors = tuple(
                _format_rumor(r) for r, _ in sorted_rumors
            )
        # Active routine
        active: t.Optional[ActiveRoutine] = None
        if self.routine_registry is not None:
            active = self.routine_registry.active_routine(
                npc_id=npc_id, hour=now_hour,
            )
        is_busy = (
            active is not None
            and active.routine.value in _TERSE_ROUTINES
        )
        # Personality
        pvec: t.Optional[PersonalityVector] = None
        ptags: tuple[str, ...] = ()
        if self.personality_registry is not None:
            pvec = self.personality_registry.vector_for(npc_id)
            if pvec is not None:
                ptags = describe_personality(pvec)
        # Tone — band-derived, then narrow by routine busy-ness
        tone = tone_for_band(rep_band)
        if is_busy and tone in (
            DialogueTone.WARM, DialogueTone.COOL,
        ):
            tone = DialogueTone.TERSE
        # Hostile + cornered + this is greeting -> FEARFUL preview
        if (
            tone == DialogueTone.HOSTILE
            and interaction_kind == InteractionKind.IDLE_OBSERVED
        ):
            tone = DialogueTone.FEARFUL
        return DialogueContext(
            npc_id=npc_id, player_id=player_id,
            interaction_kind=interaction_kind,
            tone=tone, rep_band=rep_band, rep_value=rep_value,
            faction_id=faction_id,
            routine=active, is_busy=is_busy,
            relevant_memories=memories,
            recent_rumors=rumors,
            personality_tags=ptags,
            personality_vector=pvec,
        )


def _format_rumor(rumor: Rumor) -> str:
    """One-line summary of the rumor for the prompt."""
    if rumor.summary:
        return rumor.summary
    return f"{rumor.kind.value} re {rumor.subject_id}"


__all__ = [
    "InteractionKind", "DialogueTone", "tone_for_band",
    "MemorySummary", "DialogueContext", "DialogueAssembler",
]
