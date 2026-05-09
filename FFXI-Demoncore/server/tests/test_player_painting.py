"""Tests for player_painting."""
from __future__ import annotations

from server.player_painting import (
    PlayerPaintingSystem, PaintingSize, PaintingState,
)


def _begin(
    s: PlayerPaintingSystem,
    size: PaintingSize = PaintingSize.MEDIUM,
) -> str:
    return s.begin_painting(
        painter_id="naji", title="Sunset over Bastok",
        subject="cityscape", size=size,
        technique_quality=70, palette_richness=80,
    )


def test_begin_happy():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    assert pid is not None


def test_begin_empty_painter():
    s = PlayerPaintingSystem()
    assert s.begin_painting(
        painter_id="", title="X", subject="Y",
        size=PaintingSize.SMALL,
        technique_quality=50, palette_richness=50,
    ) is None


def test_begin_invalid_quality():
    s = PlayerPaintingSystem()
    assert s.begin_painting(
        painter_id="x", title="X", subject="Y",
        size=PaintingSize.SMALL,
        technique_quality=200, palette_richness=50,
    ) is None


def test_begin_invalid_palette():
    s = PlayerPaintingSystem()
    assert s.begin_painting(
        painter_id="x", title="X", subject="Y",
        size=PaintingSize.SMALL,
        technique_quality=50, palette_richness=0,
    ) is None


def test_finish_happy():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    value = s.finish_painting(painting_id=pid)
    # (70 + 80) * 5(medium) * 5 = 3750
    assert value == 3750


def test_finish_state_transition():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    s.finish_painting(painting_id=pid)
    p = s.painting(painting_id=pid)
    assert p.state == PaintingState.FINISHED
    assert p.appraised_value_gil > 0


def test_finish_double_blocked():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    s.finish_painting(painting_id=pid)
    assert s.finish_painting(
        painting_id=pid,
    ) is None


def test_size_scales_value():
    s = PlayerPaintingSystem()
    pid_small = _begin(s, PaintingSize.SMALL)
    pid_large = _begin(s, PaintingSize.LARGE)
    pid_mural = _begin(s, PaintingSize.MURAL)
    v_s = s.finish_painting(painting_id=pid_small)
    v_l = s.finish_painting(painting_id=pid_large)
    v_m = s.finish_painting(painting_id=pid_mural)
    assert v_s < v_l < v_m


def test_submit_to_gallery_happy():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    s.finish_painting(painting_id=pid)
    assert s.submit_to_gallery(
        painting_id=pid, gallery_id="bastok_gallery",
    ) is True


def test_submit_before_finish_blocked():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    assert s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    ) is False


def test_submit_empty_gallery_blocked():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    s.finish_painting(painting_id=pid)
    assert s.submit_to_gallery(
        painting_id=pid, gallery_id="",
    ) is False


def test_offer_purchase_happy():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    appraised = s.finish_painting(painting_id=pid)
    s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    )
    assert s.offer_purchase(
        painting_id=pid, buyer_id="bob",
        offer_gil=appraised,
    ) is True


def test_offer_below_appraisal_rejected():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    appraised = s.finish_painting(painting_id=pid)
    s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    )
    assert s.offer_purchase(
        painting_id=pid, buyer_id="bob",
        offer_gil=appraised - 1,
    ) is False


def test_offer_above_appraisal_accepted():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    appraised = s.finish_painting(painting_id=pid)
    s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    )
    s.offer_purchase(
        painting_id=pid, buyer_id="bob",
        offer_gil=appraised + 1000,
    )
    p = s.painting(painting_id=pid)
    assert p.sold_price_gil == appraised + 1000
    assert p.buyer_id == "bob"


def test_painter_cannot_buy_own():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    appraised = s.finish_painting(painting_id=pid)
    s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    )
    assert s.offer_purchase(
        painting_id=pid, buyer_id="naji",
        offer_gil=appraised,
    ) is False


def test_offer_before_exhibit_blocked():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    s.finish_painting(painting_id=pid)
    assert s.offer_purchase(
        painting_id=pid, buyer_id="bob",
        offer_gil=10000,
    ) is False


def test_close_show_unsold():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    s.finish_painting(painting_id=pid)
    s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    )
    assert s.close_show(painting_id=pid) is True
    assert s.painting(
        painting_id=pid,
    ).state == PaintingState.UNSOLD


def test_close_after_sold_blocked():
    s = PlayerPaintingSystem()
    pid = _begin(s)
    appraised = s.finish_painting(painting_id=pid)
    s.submit_to_gallery(
        painting_id=pid, gallery_id="g",
    )
    s.offer_purchase(
        painting_id=pid, buyer_id="bob",
        offer_gil=appraised,
    )
    assert s.close_show(painting_id=pid) is False


def test_painter_collection():
    s = PlayerPaintingSystem()
    p1 = _begin(s)
    p2 = _begin(s)
    s.begin_painting(
        painter_id="other", title="X", subject="Y",
        size=PaintingSize.SMALL,
        technique_quality=50, palette_richness=50,
    )
    coll = s.painter_collection(painter_id="naji")
    assert len(coll) == 2


def test_painting_unknown():
    s = PlayerPaintingSystem()
    assert s.painting(painting_id="ghost") is None


def test_enum_counts():
    assert len(list(PaintingSize)) == 5
    assert len(list(PaintingState)) == 5
