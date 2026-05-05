"""Tests for siren tribute."""
from __future__ import annotations

from server.siren_tribute import SirenTribute, TributeKind


def test_siren_price_baseline_whisper():
    assert SirenTribute.siren_price(
        power="whisper", faction_rep=0, is_outlaw=False,
    ) == 500


def test_siren_price_baseline_requiem():
    assert SirenTribute.siren_price(
        power="requiem", faction_rep=0, is_outlaw=False,
    ) == 25_000


def test_siren_price_outlaw_3x():
    base = SirenTribute.siren_price(
        power="hymn", faction_rep=0, is_outlaw=False,
    )
    triple = SirenTribute.siren_price(
        power="hymn", faction_rep=0, is_outlaw=True,
    )
    assert triple == base * 3


def test_siren_price_rep_discount():
    full = SirenTribute.siren_price(
        power="hymn", faction_rep=0, is_outlaw=False,
    )
    discounted = SirenTribute.siren_price(
        power="hymn", faction_rep=200, is_outlaw=False,
    )
    # 200 rep -> 20% off
    assert discounted == full - (full * 20) // 100


def test_siren_price_unknown_power_zero():
    assert SirenTribute.siren_price(
        power="banshee", faction_rep=0, is_outlaw=False,
    ) == 0


def test_pay_gil_tribute_grants_passage():
    t = SirenTribute()
    g = t.pay_tribute(
        siren_id="serel",
        payer_ship_id="ship_a",
        lane_id="bastok_norg",
        kind=TributeKind.GIL,
        amount=600,
        faction_rep=0,
        is_outlaw=False,
        song_power="whisper",
        now_seconds=0,
    )
    assert g.accepted is True
    assert t.has_safe_passage(
        lane_id="bastok_norg", ship_id="ship_a", now_seconds=10,
    ) is True


def test_pay_insufficient_gil_rejected():
    t = SirenTribute()
    g = t.pay_tribute(
        siren_id="serel",
        payer_ship_id="ship_a",
        lane_id="L",
        kind=TributeKind.GIL,
        amount=100,
        faction_rep=0,
        is_outlaw=False,
        song_power="hymn",  # 8000 baseline
        now_seconds=0,
    )
    assert g.accepted is False
    assert g.reason == "insufficient"


def test_pearl_counts_3x():
    t = SirenTribute()
    # whisper 500g, pearl with face value 200 = 600 effective
    g = t.pay_tribute(
        siren_id="serel",
        payer_ship_id="s",
        lane_id="L",
        kind=TributeKind.PEARL,
        amount=200,
        faction_rep=0,
        is_outlaw=False,
        song_power="whisper",
        now_seconds=0,
    )
    assert g.accepted is True


def test_rescued_grants_passage_regardless_of_amount():
    t = SirenTribute()
    g = t.pay_tribute(
        siren_id="serel",
        payer_ship_id="s",
        lane_id="L",
        kind=TributeKind.RESCUED,
        amount=1,
        faction_rep=0,
        is_outlaw=False,
        song_power="requiem",
        now_seconds=0,
    )
    assert g.accepted is True
    # one full day duration
    assert g.expires_at == 24 * 3_600


def test_safe_passage_expires():
    t = SirenTribute()
    t.pay_tribute(
        siren_id="serel",
        payer_ship_id="s",
        lane_id="L",
        kind=TributeKind.GIL,
        amount=500,
        faction_rep=0,
        is_outlaw=False,
        song_power="whisper",
        now_seconds=0,
    )
    # 30 min duration
    assert t.has_safe_passage(
        lane_id="L", ship_id="s", now_seconds=29 * 60,
    ) is True
    assert t.has_safe_passage(
        lane_id="L", ship_id="s", now_seconds=31 * 60,
    ) is False


def test_safe_passage_specific_to_lane_and_ship():
    t = SirenTribute()
    t.pay_tribute(
        siren_id="serel",
        payer_ship_id="ship_a",
        lane_id="lane_a",
        kind=TributeKind.GIL,
        amount=500,
        faction_rep=0,
        is_outlaw=False,
        song_power="whisper",
        now_seconds=0,
    )
    # different ship has no passage
    assert t.has_safe_passage(
        lane_id="lane_a", ship_id="ship_b", now_seconds=10,
    ) is False
    # different lane has no passage
    assert t.has_safe_passage(
        lane_id="lane_b", ship_id="ship_a", now_seconds=10,
    ) is False


def test_pay_tribute_rejects_blank_ids():
    t = SirenTribute()
    g = t.pay_tribute(
        siren_id="", payer_ship_id="s", lane_id="L",
        kind=TributeKind.GIL, amount=500,
        faction_rep=0, is_outlaw=False,
        song_power="whisper", now_seconds=0,
    )
    assert g.accepted is False


def test_pay_tribute_rejects_zero_amount():
    t = SirenTribute()
    g = t.pay_tribute(
        siren_id="x", payer_ship_id="s", lane_id="L",
        kind=TributeKind.GIL, amount=0,
        faction_rep=0, is_outlaw=False,
        song_power="whisper", now_seconds=0,
    )
    assert g.accepted is False


def test_outlaw_pays_triple():
    t = SirenTribute()
    # whisper price = 500, outlaw = 1500. 1000 should fail.
    g_fail = t.pay_tribute(
        siren_id="x", payer_ship_id="s", lane_id="L",
        kind=TributeKind.GIL, amount=1_000,
        faction_rep=0, is_outlaw=True,
        song_power="whisper", now_seconds=0,
    )
    assert g_fail.accepted is False
    g_ok = t.pay_tribute(
        siren_id="x", payer_ship_id="s", lane_id="L",
        kind=TributeKind.GIL, amount=1_500,
        faction_rep=0, is_outlaw=True,
        song_power="whisper", now_seconds=0,
    )
    assert g_ok.accepted is True


def test_grant_includes_rep_delta():
    t = SirenTribute()
    g = t.pay_tribute(
        siren_id="x", payer_ship_id="s", lane_id="L",
        kind=TributeKind.GIL, amount=500,
        faction_rep=0, is_outlaw=False,
        song_power="whisper", now_seconds=0,
    )
    assert g.rep_delta == 25
