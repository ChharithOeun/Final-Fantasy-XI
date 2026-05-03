"""Tests for NPC dialogue context assembly."""
from __future__ import annotations

from server.entity_memory import MemoryKind, MemoryRegistry
from server.faction_reputation import (
    PlayerFactionReputation,
    ReputationBand,
)
from server.mob_personality import (
    PersonalityRegistry,
    PersonalityVector,
)
from server.npc_daily_routines import (
    NPCRoutineRegistry,
    patrol_guard_schedule,
    shopkeeper_schedule,
)
from server.npc_dialogue_system import (
    DialogueAssembler,
    DialogueTone,
    InteractionKind,
    tone_for_band,
)
from server.rumor_propagation import (
    NodeKind,
    Rumor,
    RumorKind,
    RumorPropagationEngine,
    SocialGraph,
)


def _basic_assembler() -> DialogueAssembler:
    return DialogueAssembler()


def _rep(player_id: str = "alice") -> PlayerFactionReputation:
    return PlayerFactionReputation(player_id=player_id)


def test_tone_for_band_full_table():
    assert tone_for_band(
        ReputationBand.NEUTRAL,
    ) == DialogueTone.COOL
    assert tone_for_band(
        ReputationBand.FRIENDLY,
    ) == DialogueTone.WARM
    assert tone_for_band(
        ReputationBand.ALLIED,
    ) == DialogueTone.WARM
    assert tone_for_band(
        ReputationBand.HERO_OF_THE_FACTION,
    ) == DialogueTone.REVERENT
    assert tone_for_band(
        ReputationBand.UNFRIENDLY,
    ) == DialogueTone.WARY
    assert tone_for_band(
        ReputationBand.HOSTILE,
    ) == DialogueTone.RUDE
    assert tone_for_band(
        ReputationBand.KILL_ON_SIGHT,
    ) == DialogueTone.HOSTILE


def test_assemble_default_neutral_cool():
    a = _basic_assembler()
    rep = _rep()
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=rep,
    )
    assert ctx.tone == DialogueTone.COOL
    assert ctx.rep_band == ReputationBand.NEUTRAL
    assert ctx.will_speak


def test_assemble_friendly_warm():
    a = _basic_assembler()
    rep = _rep()
    rep.set(faction_id="bastok", value=100)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=rep,
    )
    assert ctx.tone == DialogueTone.WARM


def test_assemble_hostile_does_not_speak():
    a = _basic_assembler()
    rep = _rep()
    rep.set(faction_id="bastok", value=-800)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=rep,
    )
    assert ctx.tone == DialogueTone.HOSTILE
    assert not ctx.will_speak


def test_busy_routine_makes_warm_terse():
    """A friendly NPC who's mid-patrol gets TERSE, not WARM."""
    routine_reg = NPCRoutineRegistry()
    routine_reg.register(schedule=patrol_guard_schedule(
        npc_id="guard_1", beat_waypoint="gate",
        barracks_waypoint="barracks",
    ))
    a = DialogueAssembler(routine_registry=routine_reg)
    rep = _rep()
    rep.set(faction_id="bastok", value=100)
    ctx = a.assemble(
        npc_id="guard_1", player_id="alice",
        faction_id="bastok", rep=rep, now_hour=4,  # patrol hour
    )
    assert ctx.is_busy
    assert ctx.tone == DialogueTone.TERSE


def test_socializing_routine_does_not_force_terse():
    """Tavern routine (SOCIALIZE) is not in the busy set."""
    routine_reg = NPCRoutineRegistry()
    routine_reg.register(schedule=shopkeeper_schedule(
        npc_id="dabihook", shop_waypoint="stall",
        home_waypoint="home", tavern_waypoint="tavern",
    ))
    a = DialogueAssembler(routine_registry=routine_reg)
    rep = _rep()
    rep.set(faction_id="bastok", value=100)
    # 20h is socialize hour
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=rep, now_hour=20,
    )
    assert not ctx.is_busy
    assert ctx.tone == DialogueTone.WARM


def test_idle_observed_with_kill_on_sight_becomes_fearful():
    """If the NPC has KILL_ON_SIGHT but the player is just walking
    by silently observed, the tone goes FEARFUL not HOSTILE."""
    a = _basic_assembler()
    rep = _rep()
    rep.set(faction_id="bastok", value=-700)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=rep,
        interaction_kind=InteractionKind.IDLE_OBSERVED,
    )
    assert ctx.tone == DialogueTone.FEARFUL
    assert not ctx.will_speak


def test_memory_pulls_top_n_relevant_memories():
    mem_reg = MemoryRegistry()
    # 7 memories, capacity should clamp to 5
    for i in range(7):
        mem_reg.remember(
            entity_id="dabihook", kind=MemoryKind.HELPED,
            other_entity_id="alice", salience=20 + i * 10,
            now_seconds=float(i), details=f"event_{i}",
        )
    a = DialogueAssembler(memory_registry=mem_reg, memory_top_n=5)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=_rep(),
    )
    assert len(ctx.relevant_memories) == 5
    # First memory is the highest salience
    saliences = [m.salience for m in ctx.relevant_memories]
    assert saliences == sorted(saliences, reverse=True)


def test_memory_filters_by_player():
    mem_reg = MemoryRegistry()
    mem_reg.remember(
        entity_id="dabihook", kind=MemoryKind.HELPED,
        other_entity_id="alice", salience=80,
    )
    mem_reg.remember(
        entity_id="dabihook", kind=MemoryKind.HURT,
        other_entity_id="bob", salience=70,
    )
    a = DialogueAssembler(memory_registry=mem_reg)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=_rep(),
    )
    # Only alice memories surface
    other_ids = {m.other_entity_id for m in ctx.relevant_memories}
    assert other_ids == {"alice"}


def test_rumors_pulled_from_engine():
    g = SocialGraph()
    g.add_node(node_id="dabihook", kind=NodeKind.NPC)
    eng = RumorPropagationEngine(graph=g)
    eng.seed(
        rumor=Rumor(
            rumor_id="r1", kind=RumorKind.PLAYER_KILLED_BOSS,
            subject_id="alice", origin_npc_id="dabihook",
            salience=80, fidelity=100,
            summary="Alice slew the dragon",
        ),
        origin_node_id="dabihook",
    )
    a = DialogueAssembler(rumor_engine=eng)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=_rep(),
    )
    assert "Alice slew the dragon" in ctx.recent_rumors


def test_personality_tags_pulled():
    p_reg = PersonalityRegistry()
    p_reg.assign(
        mob_id="dabihook",
        vector=PersonalityVector(
            cunning=0.9, aggression=0.4, loyalty=0.85,
        ),
    )
    a = DialogueAssembler(personality_registry=p_reg)
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=_rep(),
    )
    assert "schemer" in ctx.personality_tags
    assert ctx.personality_vector is not None


def test_personality_missing_returns_empty_tags():
    a = DialogueAssembler(personality_registry=PersonalityRegistry())
    ctx = a.assemble(
        npc_id="ghost", player_id="alice",
        faction_id="bastok", rep=_rep(),
    )
    assert ctx.personality_tags == ()
    assert ctx.personality_vector is None


def test_assembler_with_no_registries_degrades_gracefully():
    a = DialogueAssembler()
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=_rep(),
    )
    assert ctx.relevant_memories == ()
    assert ctx.recent_rumors == ()
    assert ctx.personality_tags == ()
    assert ctx.routine is None


def test_full_lifecycle_friendly_npc_with_rich_context():
    """Player Alice walks up to the friendly shopkeeper at lunch
    time. Shopkeeper remembers Alice helped him last week, has
    heard a rumor about Alice's heroics, and is at his stall."""
    mem_reg = MemoryRegistry()
    mem_reg.remember(
        entity_id="dabihook", kind=MemoryKind.HELPED,
        other_entity_id="alice", salience=85,
        details="returned the lost ledger",
    )
    g = SocialGraph()
    g.add_node(node_id="dabihook", kind=NodeKind.NPC)
    rumor_eng = RumorPropagationEngine(graph=g)
    rumor_eng.seed(
        rumor=Rumor(
            rumor_id="r1",
            kind=RumorKind.PLAYER_KILLED_BOSS,
            subject_id="alice", origin_npc_id="dabihook",
            salience=70, fidelity=90,
            summary="Alice slew the goblin chief",
        ),
        origin_node_id="dabihook",
    )
    routine_reg = NPCRoutineRegistry()
    routine_reg.register(schedule=shopkeeper_schedule(
        npc_id="dabihook", shop_waypoint="stall",
        home_waypoint="home", tavern_waypoint="tavern",
    ))
    p_reg = PersonalityRegistry()
    p_reg.assign(
        mob_id="dabihook",
        vector=PersonalityVector(
            aggression=0.3, courage=0.5, cunning=0.6,
            loyalty=0.85,
        ),
    )
    rep = _rep()
    rep.set(faction_id="bastok", value=200)
    a = DialogueAssembler(
        memory_registry=mem_reg, rumor_engine=rumor_eng,
        routine_registry=routine_reg,
        personality_registry=p_reg,
    )
    ctx = a.assemble(
        npc_id="dabihook", player_id="alice",
        faction_id="bastok", rep=rep,
        interaction_kind=InteractionKind.GREETING,
        now_hour=12,   # LUNCH for the shopkeeper
    )
    # Friendly + LUNCH (not in busy set) -> WARM
    assert ctx.tone == DialogueTone.WARM
    assert ctx.will_speak
    assert any(
        m.details == "returned the lost ledger"
        for m in ctx.relevant_memories
    )
    assert "Alice slew the goblin chief" in ctx.recent_rumors
