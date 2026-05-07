"""Tests for gearswap_rating."""
from __future__ import annotations

from server.gearswap_rating import (
    GearswapRating, ReportReason, Thumb,
)


def test_rate_up():
    r = GearswapRating()
    out = r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.UP,
    )
    assert out is True
    assert r.thumb_for(
        player_id="bob", publish_id="pub_1",
    ) == Thumb.UP


def test_rate_down():
    r = GearswapRating()
    r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.DOWN,
    )
    assert r.thumb_for(
        player_id="bob", publish_id="pub_1",
    ) == Thumb.DOWN


def test_rate_blank_player_blocked():
    r = GearswapRating()
    out = r.rate(
        player_id="", publish_id="pub_1", thumb=Thumb.UP,
    )
    assert out is False


def test_rate_blank_publish_blocked():
    r = GearswapRating()
    out = r.rate(
        player_id="bob", publish_id="", thumb=Thumb.UP,
    )
    assert out is False


def test_re_rate_overwrites():
    r = GearswapRating()
    r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.UP,
    )
    r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.DOWN,
    )
    s = r.summary(publish_id="pub_1")
    assert s.thumbs_up == 0
    assert s.thumbs_down == 1


def test_un_rate():
    r = GearswapRating()
    r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.UP,
    )
    assert r.un_rate(
        player_id="bob", publish_id="pub_1",
    ) is True
    assert r.thumb_for(
        player_id="bob", publish_id="pub_1",
    ) is None


def test_un_rate_unknown():
    r = GearswapRating()
    assert r.un_rate(
        player_id="bob", publish_id="pub_1",
    ) is False


def test_summary_counts_thumbs():
    r = GearswapRating()
    r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.UP,
    )
    r.rate(
        player_id="cara", publish_id="pub_1", thumb=Thumb.UP,
    )
    r.rate(
        player_id="dan", publish_id="pub_1", thumb=Thumb.DOWN,
    )
    s = r.summary(publish_id="pub_1")
    assert s.thumbs_up == 2
    assert s.thumbs_down == 1


def test_summary_isolates_per_publish():
    r = GearswapRating()
    r.rate(
        player_id="bob", publish_id="pub_a", thumb=Thumb.UP,
    )
    r.rate(
        player_id="cara", publish_id="pub_b", thumb=Thumb.DOWN,
    )
    s_a = r.summary(publish_id="pub_a")
    s_b = r.summary(publish_id="pub_b")
    assert s_a.thumbs_up == 1
    assert s_a.thumbs_down == 0
    assert s_b.thumbs_up == 0
    assert s_b.thumbs_down == 1


def test_comment_happy():
    r = GearswapRating()
    c = r.comment(
        player_id="bob", publish_id="pub_1",
        body="great build", posted_at=1000,
    )
    assert c is not None
    assert c.body == "great build"


def test_comment_strips_whitespace():
    r = GearswapRating()
    c = r.comment(
        player_id="bob", publish_id="pub_1",
        body="   trimmed   ", posted_at=1000,
    )
    assert c.body == "trimmed"


def test_comment_blank_blocked():
    r = GearswapRating()
    c = r.comment(
        player_id="bob", publish_id="pub_1",
        body="   ", posted_at=1000,
    )
    assert c is None


def test_comment_too_long_blocked():
    r = GearswapRating()
    c = r.comment(
        player_id="bob", publish_id="pub_1",
        body="x" * 281, posted_at=1000,
    )
    assert c is None


def test_comment_blank_player_blocked():
    r = GearswapRating()
    c = r.comment(
        player_id="", publish_id="pub_1",
        body="hi", posted_at=1000,
    )
    assert c is None


def test_comments_for_sorted_by_time():
    r = GearswapRating()
    r.comment(
        player_id="bob", publish_id="pub_1",
        body="second", posted_at=2000,
    )
    r.comment(
        player_id="cara", publish_id="pub_1",
        body="first", posted_at=1000,
    )
    out = r.comments_for(publish_id="pub_1")
    assert out[0].body == "first"
    assert out[1].body == "second"


def test_report_happy():
    r = GearswapRating()
    rep = r.report(
        player_id="bob", publish_id="pub_1",
        reason=ReportReason.SPELLING, posted_at=1000,
    )
    assert rep is not None
    assert rep.reason == ReportReason.SPELLING


def test_report_blank_player_blocked():
    r = GearswapRating()
    rep = r.report(
        player_id="", publish_id="pub_1",
        reason=ReportReason.OTHER, posted_at=1000,
    )
    assert rep is None


def test_report_appends_duplicates():
    """Report log keeps every flag; no dedupe."""
    r = GearswapRating()
    r.report(
        player_id="bob", publish_id="pub_1",
        reason=ReportReason.EXPLOIT, posted_at=1000,
    )
    r.report(
        player_id="bob", publish_id="pub_1",
        reason=ReportReason.EXPLOIT, posted_at=2000,
    )
    out = r.reports_for(publish_id="pub_1")
    assert len(out) == 2


def test_reports_for_isolates():
    r = GearswapRating()
    r.report(
        player_id="bob", publish_id="pub_a",
        reason=ReportReason.SPELLING, posted_at=1000,
    )
    r.report(
        player_id="bob", publish_id="pub_b",
        reason=ReportReason.OUTDATED, posted_at=1000,
    )
    assert len(r.reports_for(publish_id="pub_a")) == 1
    assert len(r.reports_for(publish_id="pub_b")) == 1


def test_summary_counts_comments_and_reports():
    r = GearswapRating()
    r.comment(
        player_id="bob", publish_id="pub_1",
        body="nice", posted_at=1000,
    )
    r.report(
        player_id="cara", publish_id="pub_1",
        reason=ReportReason.WRONG_SLOT, posted_at=2000,
    )
    s = r.summary(publish_id="pub_1")
    assert s.comment_count == 1
    assert s.report_count == 1


def test_summary_unknown_publish_zero():
    r = GearswapRating()
    s = r.summary(publish_id="ghost")
    assert s.thumbs_up == 0
    assert s.thumbs_down == 0


def test_thumb_for_unknown_none():
    r = GearswapRating()
    assert r.thumb_for(
        player_id="bob", publish_id="pub_1",
    ) is None


def test_total_counts():
    r = GearswapRating()
    r.rate(
        player_id="bob", publish_id="pub_1", thumb=Thumb.UP,
    )
    r.rate(
        player_id="cara", publish_id="pub_2", thumb=Thumb.DOWN,
    )
    r.comment(
        player_id="bob", publish_id="pub_1",
        body="hi", posted_at=1000,
    )
    r.report(
        player_id="bob", publish_id="pub_1",
        reason=ReportReason.OTHER, posted_at=1000,
    )
    assert r.total_thumbs() == 2
    assert r.total_comments() == 1
    assert r.total_reports() == 1


def test_two_thumb_values():
    assert len(list(Thumb)) == 2


def test_five_report_reasons():
    assert len(list(ReportReason)) == 5
