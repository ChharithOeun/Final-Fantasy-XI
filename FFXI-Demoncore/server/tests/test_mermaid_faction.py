"""Tests for mermaid faction."""
from __future__ import annotations

from server.mermaid_faction import (
    HONORED_THRESHOLD,
    HOSTILE_THRESHOLD,
    MermaidFaction,
    MermaidStanding,
    REVERED_THRESHOLD,
    SAHAGIN_KILL_BONUS,
    SHRINE_DEFENDED_BONUS,
    TRUSTED_THRESHOLD,
)


def test_reputation_default_zero():
    m = MermaidFaction()
    assert m.reputation_of(player_id="p1") == 0


def test_adjust_reputation_increases():
    m = MermaidFaction()
    new = m.adjust_reputation(player_id="p1", delta=20)
    assert new == 20


def test_adjust_blank_player():
    m = MermaidFaction()
    new = m.adjust_reputation(player_id="", delta=20)
    assert new == 0


def test_sahagin_kill_bonus():
    m = MermaidFaction()
    new = m.adjust_reputation(
        player_id="p1", delta=10, sahagin_kill=True,
    )
    assert new == 10 + SAHAGIN_KILL_BONUS


def test_shrine_defended_bonus():
    m = MermaidFaction()
    new = m.adjust_reputation(
        player_id="p1", delta=10, shrine_defended=True,
    )
    assert new == 10 + SHRINE_DEFENDED_BONUS


def test_both_bonuses_stack():
    m = MermaidFaction()
    new = m.adjust_reputation(
        player_id="p1", delta=10,
        sahagin_kill=True, shrine_defended=True,
    )
    assert new == 10 + SAHAGIN_KILL_BONUS + SHRINE_DEFENDED_BONUS


def test_standing_default_distrusted():
    m = MermaidFaction()
    assert m.standing_of(
        player_id="p1",
    ) == MermaidStanding.DISTRUSTED


def test_standing_neutral():
    m = MermaidFaction()
    m.adjust_reputation(player_id="p1", delta=10)
    assert m.standing_of(
        player_id="p1",
    ) == MermaidStanding.NEUTRAL


def test_standing_trusted():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=TRUSTED_THRESHOLD,
    )
    assert m.standing_of(
        player_id="p1",
    ) == MermaidStanding.TRUSTED


def test_standing_honored():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=HONORED_THRESHOLD,
    )
    assert m.standing_of(
        player_id="p1",
    ) == MermaidStanding.HONORED


def test_standing_revered():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=REVERED_THRESHOLD,
    )
    assert m.standing_of(
        player_id="p1",
    ) == MermaidStanding.REVERED


def test_standing_hostile():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=HOSTILE_THRESHOLD - 1,
    )
    assert m.standing_of(
        player_id="p1",
    ) == MermaidStanding.HOSTILE


def test_blessings_at_neutral_empty():
    m = MermaidFaction()
    m.adjust_reputation(player_id="p1", delta=10)
    out = m.blessings_unlocked(player_id="p1")
    assert len(out) == 0


def test_blessings_at_trusted():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=TRUSTED_THRESHOLD,
    )
    out = m.blessings_unlocked(player_id="p1")
    assert any(b.blessing_id == "songs_of_the_tide" for b in out)


def test_blessings_at_revered_includes_all():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=REVERED_THRESHOLD,
    )
    out = m.blessings_unlocked(player_id="p1")
    ids = {b.blessing_id for b in out}
    assert "songs_of_the_tide" in ids
    assert "pearl_sigil" in ids
    assert "sirens_oath" in ids


def test_can_invoke_trust_at_revered():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=REVERED_THRESHOLD,
    )
    assert m.can_invoke_trust(player_id="p1") is True


def test_cannot_invoke_trust_below_revered():
    m = MermaidFaction()
    m.adjust_reputation(
        player_id="p1", delta=HONORED_THRESHOLD,
    )
    assert m.can_invoke_trust(player_id="p1") is False


def test_reputation_floored():
    m = MermaidFaction()
    m.adjust_reputation(player_id="p1", delta=-500)
    assert m.reputation_of(player_id="p1") == -100


def test_reputation_ceilinged():
    m = MermaidFaction()
    m.adjust_reputation(player_id="p1", delta=500)
    assert m.reputation_of(player_id="p1") == 100


def test_per_player_isolation():
    m = MermaidFaction()
    m.adjust_reputation(player_id="p1", delta=20)
    assert m.reputation_of(player_id="p2") == 0
