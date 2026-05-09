"""Tests for nation_propaganda."""
from __future__ import annotations

from server.nation_propaganda import (
    NationPropagandaSystem, Narrative,
)


def _post(s, **overrides):
    args = dict(
        nation_id="bastok",
        subject_npc="off_volker",
        narrative=Narrative.TRAITOR,
        public_text="Volker the traitor — wanted dead or alive.",
        intensity=4, posted_day=400,
    )
    args.update(overrides)
    return s.post_line(**args)


def test_post_happy():
    s = NationPropagandaSystem()
    assert _post(s) is not None


def test_post_blank_nation():
    s = NationPropagandaSystem()
    assert _post(s, nation_id="") is None


def test_post_blank_text():
    s = NationPropagandaSystem()
    assert _post(s, public_text="") is None


def test_post_invalid_intensity():
    s = NationPropagandaSystem()
    assert _post(s, intensity=0) is None
    assert _post(s, intensity=6) is None


def test_post_negative_day():
    s = NationPropagandaSystem()
    assert _post(s, posted_day=-1) is None


def test_post_dup_active_blocked():
    s = NationPropagandaSystem()
    _post(s)
    assert _post(s) is None


def test_post_after_retire_ok():
    s = NationPropagandaSystem()
    lid = _post(s)
    s.retire_line(line_id=lid, now_day=500)
    assert _post(s, posted_day=500) is not None


def test_retire_line():
    s = NationPropagandaSystem()
    lid = _post(s)
    assert s.retire_line(
        line_id=lid, now_day=500,
    ) is True


def test_retire_double_blocked():
    s = NationPropagandaSystem()
    lid = _post(s)
    s.retire_line(line_id=lid, now_day=500)
    assert s.retire_line(
        line_id=lid, now_day=501,
    ) is False


def test_retire_before_posted_blocked():
    s = NationPropagandaSystem()
    lid = _post(s, posted_day=400)
    assert s.retire_line(
        line_id=lid, now_day=300,
    ) is False


def test_active_narrative():
    s = NationPropagandaSystem()
    _post(s)
    active = s.active_narrative(
        nation_id="bastok",
        subject_npc="off_volker",
    )
    assert active is not None
    assert active.narrative == Narrative.TRAITOR


def test_active_narrative_after_retire_none():
    s = NationPropagandaSystem()
    lid = _post(s)
    s.retire_line(line_id=lid, now_day=500)
    active = s.active_narrative(
        nation_id="bastok",
        subject_npc="off_volker",
    )
    assert active is None


def test_pivot_narrative():
    s = NationPropagandaSystem()
    _post(s, narrative=Narrative.TRAITOR)
    new_lid = s.pivot_narrative(
        nation_id="bastok",
        subject_npc="off_volker",
        new_narrative=Narrative.HERO_RECLAIMED,
        new_text="Volker the redeemed.",
        new_intensity=3, now_day=900,
    )
    assert new_lid is not None
    active = s.active_narrative(
        nation_id="bastok",
        subject_npc="off_volker",
    )
    assert active.narrative == Narrative.HERO_RECLAIMED


def test_pivot_no_active_blocked():
    s = NationPropagandaSystem()
    new_lid = s.pivot_narrative(
        nation_id="bastok",
        subject_npc="off_volker",
        new_narrative=Narrative.TRAITOR,
        new_text="x", new_intensity=3,
        now_day=900,
    )
    assert new_lid is None


def test_boost_intensity():
    s = NationPropagandaSystem()
    lid = _post(s, intensity=3)
    assert s.boost_intensity(
        line_id=lid, delta=1,
    ) is True
    assert s.line(line_id=lid).intensity == 4


def test_boost_at_max_no_change_returns_false():
    s = NationPropagandaSystem()
    lid = _post(s, intensity=5)
    assert s.boost_intensity(
        line_id=lid, delta=1,
    ) is False


def test_boost_clamps_at_min():
    s = NationPropagandaSystem()
    lid = _post(s, intensity=2)
    s.boost_intensity(line_id=lid, delta=-10)
    assert s.line(line_id=lid).intensity == 1


def test_boost_retired_blocked():
    s = NationPropagandaSystem()
    lid = _post(s)
    s.retire_line(line_id=lid, now_day=500)
    assert s.boost_intensity(
        line_id=lid, delta=1,
    ) is False


def test_history_for():
    s = NationPropagandaSystem()
    lid_a = _post(s, posted_day=400,
                  narrative=Narrative.TRAITOR,
                  public_text="enemy")
    s.retire_line(line_id=lid_a, now_day=500)
    _post(s, posted_day=500,
          narrative=Narrative.TRAGIC_EXILE,
          public_text="tragic")
    out = s.history_for(
        nation_id="bastok",
        subject_npc="off_volker",
    )
    assert len(out) == 2
    assert (
        out[0].narrative == Narrative.TRAITOR
    )


def test_lines_in_nation():
    s = NationPropagandaSystem()
    _post(s, subject_npc="a")
    _post(s, subject_npc="b")
    _post(s, nation_id="windy",
          subject_npc="c",
          public_text="windy line")
    out = s.lines_in_nation(nation_id="bastok")
    assert len(out) == 2


def test_line_unknown():
    s = NationPropagandaSystem()
    assert s.line(line_id="ghost") is None


def test_enum_count():
    assert len(list(Narrative)) == 5
