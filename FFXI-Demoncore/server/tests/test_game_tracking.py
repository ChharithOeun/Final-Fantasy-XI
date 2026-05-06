"""Tests for game_tracking."""
from __future__ import annotations

from server.game_tracking import GameTrackingRegistry, SignKind


def _place(r, sid="s1", **overrides):
    kwargs = dict(
        sign_id=sid, kind=SignKind.PAW_PRINT,
        zone="east_wood", x=0.0, y=0.0,
        quarry_id="rabbit", freshness_seconds=60,
        difficulty=30, direction_bearing=90,
    )
    kwargs.update(overrides)
    return r.place_sign(**kwargs)


def test_place_happy():
    r = GameTrackingRegistry()
    assert _place(r) is True


def test_place_blank_id_blocked():
    r = GameTrackingRegistry()
    assert _place(r, sid="") is False


def test_place_blank_zone_blocked():
    r = GameTrackingRegistry()
    assert _place(r, zone="") is False


def test_place_blank_quarry_blocked():
    r = GameTrackingRegistry()
    assert _place(r, quarry_id="") is False


def test_place_duplicate_blocked():
    r = GameTrackingRegistry()
    _place(r)
    assert _place(r) is False


def test_place_negative_freshness_blocked():
    r = GameTrackingRegistry()
    assert _place(r, freshness_seconds=-5) is False


def test_place_difficulty_out_of_range_blocked():
    r = GameTrackingRegistry()
    assert _place(r, difficulty=150) is False
    assert _place(r, difficulty=-1) is False


def test_bearing_normalized():
    r = GameTrackingRegistry()
    _place(r, direction_bearing=450)
    s = r.signs_in_zone(zone="east_wood")[0]
    assert s.direction_bearing == 90


def test_age_signs_increments():
    r = GameTrackingRegistry()
    _place(r, freshness_seconds=10)
    out = r.age_signs(dt_seconds=20)
    assert out == 0
    s = r.signs_in_zone(zone="east_wood")[0]
    assert s.freshness_seconds == 30


def test_age_signs_expires():
    r = GameTrackingRegistry()
    _place(r, freshness_seconds=10)
    # 3 days = 259200, push past it
    out = r.age_signs(dt_seconds=300000)
    assert out == 1
    assert r.total_signs() == 0


def test_age_signs_zero_dt():
    r = GameTrackingRegistry()
    _place(r)
    assert r.age_signs(dt_seconds=0) == 0


def test_signs_in_zone_filters():
    r = GameTrackingRegistry()
    _place(r, sid="a", zone="east_wood")
    _place(r, sid="b", zone="south_marsh")
    out = r.signs_in_zone(zone="east_wood")
    assert len(out) == 1
    assert out[0].sign_id == "a"


def test_signs_in_zone_empty():
    r = GameTrackingRegistry()
    assert r.signs_in_zone(zone="ghost") == []


def test_read_skill_high_reveals_all():
    r = GameTrackingRegistry()
    _place(r, difficulty=30)
    out = r.read(sign_id="s1", tracker_skill=80)
    assert out is not None
    assert out.quarry_revealed is True
    assert out.freshness_revealed is True
    assert out.direction_revealed is True
    assert out.direction_misled is False


def test_read_skill_mid_reveals_quarry_and_freshness():
    r = GameTrackingRegistry()
    _place(r, difficulty=30)
    # margin = 0 → quarry + fresh, NOT direction
    out = r.read(sign_id="s1", tracker_skill=30)
    assert out.quarry_revealed is True
    assert out.freshness_revealed is True
    assert out.direction_revealed is False


def test_read_skill_low_reveals_only_quarry():
    r = GameTrackingRegistry()
    _place(r, difficulty=30)
    # margin = -5 → quarry only
    out = r.read(sign_id="s1", tracker_skill=25)
    assert out.quarry_revealed is True
    assert out.freshness_revealed is False
    assert out.direction_revealed is False


def test_read_skill_too_low_misleads():
    r = GameTrackingRegistry()
    _place(r, difficulty=80)
    # margin = -50 → quarry false, direction MISLED
    out = r.read(sign_id="s1", tracker_skill=30)
    assert out.quarry_revealed is False
    assert out.direction_revealed is False
    assert out.direction_misled is True


def test_read_unknown_sign():
    r = GameTrackingRegistry()
    out = r.read(sign_id="ghost", tracker_skill=99)
    assert out is None


def test_remove():
    r = GameTrackingRegistry()
    _place(r)
    assert r.remove(sign_id="s1") is True
    assert r.total_signs() == 0


def test_remove_unknown():
    r = GameTrackingRegistry()
    assert r.remove(sign_id="ghost") is False


def test_six_sign_kinds():
    assert len(list(SignKind)) == 6


def test_total_signs():
    r = GameTrackingRegistry()
    _place(r, sid="a")
    _place(r, sid="b")
    assert r.total_signs() == 2
