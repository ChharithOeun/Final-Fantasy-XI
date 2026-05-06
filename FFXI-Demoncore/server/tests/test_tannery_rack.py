"""Tests for tannery_rack."""
from __future__ import annotations

from server.tannery_rack import TanneryRack, TanStage


def _load(r, hid="h1", **overrides):
    kwargs = dict(
        hide_id=hid, owner_id="alice",
        quarry_id="dhalmel", hide_ruined=False,
        loaded_at=10,
    )
    kwargs.update(overrides)
    return r.load(**kwargs)


def test_load_happy():
    r = TanneryRack()
    assert _load(r) is True
    assert r.stage_of(hide_id="h1") == TanStage.SOAKING


def test_load_blank_id():
    r = TanneryRack()
    assert _load(r, hid="") is False


def test_load_blank_owner():
    r = TanneryRack()
    assert _load(r, owner_id="") is False


def test_load_blank_quarry():
    r = TanneryRack()
    assert _load(r, quarry_id="") is False


def test_load_duplicate_blocked():
    r = TanneryRack()
    _load(r)
    assert _load(r) is False


def test_load_ruined_hide_refused():
    r = TanneryRack()
    assert _load(r, hide_ruined=True) is False


def test_soak_progresses_to_scraping():
    r = TanneryRack()
    _load(r)
    r.tick(dt_seconds=1800)
    assert r.stage_of(hide_id="h1") == TanStage.SCRAPING


def test_soak_partial_stays_soaking():
    r = TanneryRack()
    _load(r)
    r.tick(dt_seconds=900)
    assert r.stage_of(hide_id="h1") == TanStage.SOAKING


def test_rain_stalls_soaking():
    r = TanneryRack()
    _load(r)
    # 30 min of rain → no progress
    r.tick(dt_seconds=1800, weather_rain=True)
    assert r.stage_of(hide_id="h1") == TanStage.SOAKING


def test_scrape_advances_to_drying():
    r = TanneryRack()
    _load(r)
    r.tick(dt_seconds=1800)
    assert r.scrape(hide_id="h1") is True
    assert r.stage_of(hide_id="h1") == TanStage.DRYING


def test_scrape_too_early_blocked():
    r = TanneryRack()
    _load(r)
    # still SOAKING
    assert r.scrape(hide_id="h1") is False


def test_scrape_unknown():
    r = TanneryRack()
    assert r.scrape(hide_id="ghost") is False


def test_drying_to_ready():
    r = TanneryRack()
    _load(r)
    r.tick(dt_seconds=1800)
    r.scrape(hide_id="h1")
    out = r.tick(dt_seconds=3600)
    assert out == 1
    assert r.stage_of(hide_id="h1") == TanStage.READY


def test_rain_regresses_drying():
    r = TanneryRack()
    _load(r)
    r.tick(dt_seconds=1800)
    r.scrape(hide_id="h1")
    r.tick(dt_seconds=1000)  # 1000s into 3600s
    r.tick(dt_seconds=500, weather_rain=True)  # regress 500s
    # Still DRYING, not READY
    assert r.stage_of(hide_id="h1") == TanStage.DRYING


def test_pull_when_ready():
    r = TanneryRack()
    _load(r, quarry_id="boar")
    r.tick(dt_seconds=1800)
    r.scrape(hide_id="h1")
    r.tick(dt_seconds=3600)
    out = r.pull(hide_id="h1")
    assert out == "leather_boar"
    assert r.total_hides() == 0


def test_pull_when_not_ready():
    r = TanneryRack()
    _load(r)
    out = r.pull(hide_id="h1")
    assert out is None


def test_pull_unknown():
    r = TanneryRack()
    assert r.pull(hide_id="ghost") is None


def test_tick_zero_dt_returns_ready_count():
    r = TanneryRack()
    _load(r)
    out = r.tick(dt_seconds=0)
    assert out == 0


def test_stage_of_unknown_none():
    r = TanneryRack()
    assert r.stage_of(hide_id="ghost") is None


def test_total_hides():
    r = TanneryRack()
    _load(r, hid="a")
    _load(r, hid="b")
    assert r.total_hides() == 2


def test_four_tan_stages():
    assert len(list(TanStage)) == 4


def test_full_lifecycle_smoke():
    r = TanneryRack()
    _load(r, hid="h1", quarry_id="dhalmel")
    # SOAKING → SCRAPING
    r.tick(dt_seconds=1800)
    # operator scrapes → DRYING
    r.scrape(hide_id="h1")
    # DRYING → READY
    r.tick(dt_seconds=3600)
    # operator pulls → leather
    out = r.pull(hide_id="h1")
    assert out == "leather_dhalmel"
