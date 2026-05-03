"""Tests for the NPC emotional cascade."""
from __future__ import annotations

from server.npc_emotional_cascade import (
    EmotionKind,
    EmotionalEvent,
    NPCEmotionalCascade,
)


def test_empty_graph_origin_only():
    cas = NPCEmotionalCascade()
    touched = cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    assert touched == 1
    st = cas.state_for("ayame")
    assert st is not None
    assert st.magnitudes[EmotionKind.GRIEF] == 80


def test_close_friend_inherits_grief():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="ayame", npc_b="kaede", closeness=1.0,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    kaede = cas.state_for("kaede")
    assert kaede is not None
    # Hop 1: 80 * 0.6 = 48 * closeness 1.0 = 48
    assert kaede.magnitudes[EmotionKind.GRIEF] == 48


def test_distant_acquaintance_dampened():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="ayame", npc_b="bob", closeness=0.2,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    bob = cas.state_for("bob")
    # 80 * 0.6 = 48 * 0.2 = 9
    assert bob is not None
    assert bob.magnitudes[EmotionKind.GRIEF] == 9


def test_very_distant_below_floor_skipped():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="ayame", npc_b="cousin", closeness=0.05,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=20,
    ))
    # 20 * 0.6 = 12 * 0.05 = 0.6 -> below floor (5)
    assert cas.state_for("cousin") is None


def test_two_hop_propagation():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="ayame", npc_b="kaede", closeness=1.0,
    )
    cas.add_relationship(
        npc_a="kaede", npc_b="hina", closeness=1.0,
    )
    touched = cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=100,
    ))
    # ayame, kaede, hina
    assert touched == 3
    hina = cas.state_for("hina")
    assert hina is not None
    # 100 -> 60 -> 36
    assert hina.magnitudes[EmotionKind.GRIEF] == 36


def test_decay_step_reduces_magnitudes():
    cas = NPCEmotionalCascade(
        temporal_decay_per_sec=0.1,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=100,
    ))
    cas.decay_step(elapsed_seconds=2.0)
    # 1 - 0.1 * 2 = 0.8
    assert cas.state_for("ayame").magnitudes[
        EmotionKind.GRIEF
    ] == 80


def test_decay_to_zero_removes_emotion():
    cas = NPCEmotionalCascade(temporal_decay_per_sec=2.0)
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.JOY,
        magnitude=20,
    ))
    cas.decay_step(elapsed_seconds=1.0)
    st = cas.state_for("ayame")
    assert EmotionKind.JOY not in st.magnitudes


def test_dominant_emotion():
    cas = NPCEmotionalCascade()
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="ayame", emotion=EmotionKind.JOY,
        magnitude=30,
    ))
    assert cas.state_for("ayame").dominant() == EmotionKind.GRIEF


def test_pride_inverts_for_rival():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="hero", npc_b="rival",
        closeness=0.0, rivalry=1.0,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="hero", emotion=EmotionKind.PRIDE,
        magnitude=100,
    ))
    rival = cas.state_for("rival")
    # rivalry_factor for PRIDE is -0.3
    # propagation: 100 * 0.6 = 60 -> closeness 0 + rivalry
    # 60 * 1.0 * 0.3 = 18 -> opposite (SHAME)
    assert rival is not None
    assert EmotionKind.SHAME in rival.magnitudes


def test_anger_amplifies_through_rivalry():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="hero", npc_b="ally",
        closeness=1.0, rivalry=0.5,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="hero", emotion=EmotionKind.ANGER,
        magnitude=100,
    ))
    # rivalry_factor for ANGER is +0.5 (abs)
    # 100 * 0.6 = 60 -> closeness 60 + rivalry (60*0.5*0.5=15)
    # = 75
    ally = cas.state_for("ally")
    assert ally is not None
    assert ally.magnitudes[EmotionKind.ANGER] == 75


def test_magnitude_capped_at_100():
    cas = NPCEmotionalCascade()
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="x", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="x", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    assert cas.state_for("x").magnitudes[
        EmotionKind.GRIEF
    ] == 100


def test_origin_below_floor_still_recorded():
    cas = NPCEmotionalCascade()
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="x", emotion=EmotionKind.JOY,
        magnitude=2,
    ))
    # Origin always recorded even if too small to propagate
    assert cas.state_for("x").magnitudes[
        EmotionKind.JOY
    ] == 2


def test_no_state_for_unknown():
    cas = NPCEmotionalCascade()
    assert cas.state_for("ghost") is None


def test_total_tracked_count():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="a", npc_b="b", closeness=1.0,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="a", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    assert cas.total_npcs_tracked() == 2


def test_betrayal_propagates_far():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="a", npc_b="b", closeness=1.0, rivalry=0.5,
    )
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="a", emotion=EmotionKind.BETRAYAL,
        magnitude=100,
    ))
    b = cas.state_for("b")
    # rivalry_factor for BETRAYAL is +0.7
    # 100 * 0.6 = 60 -> closeness 60 + rivalry (60*0.5*0.7=21)
    # = 81
    assert b is not None
    assert b.magnitudes[EmotionKind.BETRAYAL] == 81


def test_relationship_is_bidirectional():
    cas = NPCEmotionalCascade()
    cas.add_relationship(
        npc_a="a", npc_b="b", closeness=1.0,
    )
    # Trigger from b
    cas.ingest(event=EmotionalEvent(
        origin_npc_id="b", emotion=EmotionKind.GRIEF,
        magnitude=80,
    ))
    a = cas.state_for("a")
    assert a is not None
    assert a.magnitudes[EmotionKind.GRIEF] == 48
