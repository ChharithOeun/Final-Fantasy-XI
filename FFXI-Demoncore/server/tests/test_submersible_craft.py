"""Tests for submersible craft."""
from __future__ import annotations

from server.submersible_craft import SubClass, SubmersibleCraft


def test_total_classes():
    s = SubmersibleCraft()
    assert s.total_classes() == 4


def test_profile_lookup():
    p = SubmersibleCraft.profile_for(sub_class=SubClass.CORSAIR_SUB)
    assert p.crew_capacity == 4
    assert p.depth_cap_yalms == 500


def test_deploy_happy():
    s = SubmersibleCraft()
    ok = s.deploy(
        sub_id="s1",
        sub_class=SubClass.SCOUT_SUB,
        occupants=("p1", "p2"),
        now_seconds=0,
    )
    assert ok is True


def test_deploy_rejects_overcrew():
    s = SubmersibleCraft()
    ok = s.deploy(
        sub_id="s1",
        sub_class=SubClass.DIVING_BELL,  # cap 1
        occupants=("p1", "p2"),
        now_seconds=0,
    )
    assert ok is False


def test_deploy_rejects_empty_crew():
    s = SubmersibleCraft()
    ok = s.deploy(
        sub_id="s1",
        sub_class=SubClass.DIVING_BELL,
        occupants=(),
        now_seconds=0,
    )
    assert ok is False


def test_deploy_rejects_duplicate_id():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        occupants=("p1",), now_seconds=0,
    )
    assert s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        occupants=("p2",), now_seconds=0,
    ) is False


def test_deploy_rejects_dup_occupant():
    s = SubmersibleCraft()
    ok = s.deploy(
        sub_id="s1",
        sub_class=SubClass.SCOUT_SUB,
        occupants=("p1", "p1"),
        now_seconds=0,
    )
    assert ok is False


def test_descend_happy():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.CORSAIR_SUB,
        occupants=("p1",), now_seconds=0,
    )
    r = s.descend(sub_id="s1", target_depth_yalms=400)
    assert r.accepted is True
    assert r.new_depth == 400


def test_descend_rejects_past_cap():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,  # cap 200
        occupants=("p1",), now_seconds=0,
    )
    r = s.descend(sub_id="s1", target_depth_yalms=300)
    assert r.accepted is False
    assert r.reason == "exceeds depth cap"


def test_descend_rejects_negative():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        occupants=("p1",), now_seconds=0,
    )
    r = s.descend(sub_id="s1", target_depth_yalms=-5)
    assert r.accepted is False


def test_descend_unknown_sub():
    s = SubmersibleCraft()
    r = s.descend(sub_id="ghost", target_depth_yalms=100)
    assert r.accepted is False


def test_take_damage_partial():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.SCOUT_SUB,  # 900 hp
        occupants=("p1",), now_seconds=0,
    )
    r = s.take_damage(sub_id="s1", dmg=300)
    assert r.accepted is True
    assert r.hp_remaining == 600
    assert r.breached is False


def test_take_damage_breach():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,  # 400 hp
        occupants=("p1",), now_seconds=0,
    )
    s.descend(sub_id="s1", target_depth_yalms=180)
    r = s.take_damage(sub_id="s1", dmg=999)
    assert r.breached is True
    assert r.hp_remaining == 0
    assert r.dumped_at_depth == 180


def test_descend_after_breach_blocked():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        occupants=("p1",), now_seconds=0,
    )
    s.take_damage(sub_id="s1", dmg=9999)
    r = s.descend(sub_id="s1", target_depth_yalms=50)
    assert r.accepted is False
    assert r.reason == "hull breached"


def test_take_damage_negative_rejected():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.DIVING_BELL,
        occupants=("p1",), now_seconds=0,
    )
    r = s.take_damage(sub_id="s1", dmg=-5)
    assert r.accepted is False


def test_occupants_returns_crew():
    s = SubmersibleCraft()
    s.deploy(
        sub_id="s1", sub_class=SubClass.CORSAIR_SUB,
        occupants=("a", "b", "c"), now_seconds=0,
    )
    assert s.occupants(sub_id="s1") == ("a", "b", "c")
    assert s.occupants(sub_id="ghost") == ()
