"""Tests for guard_salute."""
from __future__ import annotations

from server.guard_salute import (
    GuardResponse,
    GuardSaluteRegistry,
    SALUTE_COOLDOWN,
)
from server.npc_legend_awareness import (
    RecognitionResult,
    RecognitionTier,
)


def _rec(tier: RecognitionTier) -> RecognitionResult:
    return RecognitionResult(
        tier=tier, highest_title_id=None,
        faction_friendly=False, faction_hostile=False,
        reaction_phrase="",
    )


def test_register_post_happy():
    g = GuardSaluteRegistry()
    ok = g.register_post(
        post_id="bastok_north", zone_id="bastok_markets",
        allows_gate_pass=True,
    )
    assert ok is True


def test_register_blank_post_rejected():
    g = GuardSaluteRegistry()
    assert g.register_post(
        post_id="", zone_id="x", allows_gate_pass=False,
    ) is False


def test_duplicate_post_rejected():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    assert g.register_post(post_id="p", zone_id="z2") is False


def test_unknown_recognition_ignored():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.UNKNOWN),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.IGNORE


def test_noted_gets_nod():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.NOTED),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.NOD


def test_honored_gets_salute():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.HONORED),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.SALUTE


def test_revered_gets_salute():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.SALUTE


def test_mythical_opens_gate_when_allowed():
    g = GuardSaluteRegistry()
    g.register_post(
        post_id="p", zone_id="z", allows_gate_pass=True,
    )
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.OPEN_GATE
    assert out.granted_passage is True
    assert out.waived_toll is True


def test_mythical_no_gate_pass_still_no_passage():
    g = GuardSaluteRegistry()
    g.register_post(
        post_id="p", zone_id="z", allows_gate_pass=False,
    )
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.OPEN_GATE
    # response is OPEN_GATE but the post doesn't actually
    # have passage authority
    assert out.granted_passage is False


def test_outlaw_overrides_legend():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=True, now_seconds=10,
    )
    assert out.response == GuardResponse.HOSTILE
    assert out.granted_passage is False


def test_unknown_post_ignored():
    g = GuardSaluteRegistry()
    out = g.request_passage(
        post_id="ghost", player_id="alice",
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.IGNORE


def test_blank_player_ignored():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    out = g.request_passage(
        post_id="p", player_id="",
        recognition=_rec(RecognitionTier.MYTHICAL),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.IGNORE


def test_cooldown_demotes_repeat_salute():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10,
    )
    # immediate repeat
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=15,
    )
    assert out.response == GuardResponse.NOD


def test_cooldown_expires_then_resalutes():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10,
    )
    out = g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10 + SALUTE_COOLDOWN + 1,
    )
    assert out.response == GuardResponse.SALUTE


def test_per_player_cooldown_independent():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10,
    )
    # bob's first salute
    out = g.request_passage(
        post_id="p", player_id="bob",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10,
    )
    assert out.response == GuardResponse.SALUTE


def test_seconds_until_ready_zero_when_never_saluted():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    assert g.seconds_until_ready(
        post_id="p", player_id="alice", now_seconds=10,
    ) == 0


def test_seconds_until_ready_after_salute():
    g = GuardSaluteRegistry()
    g.register_post(post_id="p", zone_id="z")
    g.request_passage(
        post_id="p", player_id="alice",
        recognition=_rec(RecognitionTier.REVERED),
        is_outlaw=False, now_seconds=10,
    )
    remaining = g.seconds_until_ready(
        post_id="p", player_id="alice", now_seconds=15,
    )
    assert remaining == SALUTE_COOLDOWN - 5


def test_five_guard_responses():
    assert len(list(GuardResponse)) == 5
