"""Tests for environment_storytelling."""
from __future__ import annotations

from server.environment_storytelling import (
    EnvironmentStorytelling, PropKind, StoryProp,
)


def _statue(pid="statue_1", zid="bastok_mines",
            title="King's Statue", body="A weathered hero.",
            fame=None, value=2):
    return StoryProp(
        prop_id=pid, zone_id=zid, kind=PropKind.STATUE,
        title=title, body=body, fame_unlock=fame,
        research_value=value,
    )


def test_register_happy():
    s = EnvironmentStorytelling()
    assert s.register_prop(_statue()) is True


def test_register_blank_id_blocked():
    s = EnvironmentStorytelling()
    bad = StoryProp(
        prop_id="", zone_id="x", kind=PropKind.STATUE,
        title="t", body="b",
    )
    assert s.register_prop(bad) is False


def test_register_blank_zone_blocked():
    s = EnvironmentStorytelling()
    bad = StoryProp(
        prop_id="x", zone_id="", kind=PropKind.STATUE,
        title="t", body="b",
    )
    assert s.register_prop(bad) is False


def test_register_blank_title_blocked():
    s = EnvironmentStorytelling()
    bad = StoryProp(
        prop_id="x", zone_id="z", kind=PropKind.STATUE,
        title="", body="b",
    )
    assert s.register_prop(bad) is False


def test_register_negative_value_blocked():
    s = EnvironmentStorytelling()
    bad = StoryProp(
        prop_id="x", zone_id="z", kind=PropKind.STATUE,
        title="t", body="b", research_value=-1,
    )
    assert s.register_prop(bad) is False


def test_register_dup_blocked():
    s = EnvironmentStorytelling()
    s.register_prop(_statue())
    assert s.register_prop(_statue()) is False


def test_read_first_credits_research():
    s = EnvironmentStorytelling()
    s.register_prop(_statue(value=3))
    out = s.read(player_id="bob", prop_id="statue_1")
    assert out is not None
    assert out.is_first_discovery is True
    assert out.research_credited == 3
    assert out.is_server_first_discoverer is True


def test_read_second_no_credit():
    s = EnvironmentStorytelling()
    s.register_prop(_statue(value=3))
    s.read(player_id="bob", prop_id="statue_1")
    out = s.read(player_id="bob", prop_id="statue_1")
    assert out.is_first_discovery is False
    assert out.research_credited == 0


def test_second_player_credits_themselves_not_server_first():
    s = EnvironmentStorytelling()
    s.register_prop(_statue(value=3))
    s.read(player_id="bob", prop_id="statue_1")
    out = s.read(player_id="cara", prop_id="statue_1")
    assert out.is_first_discovery is True
    assert out.research_credited == 3
    assert out.is_server_first_discoverer is False


def test_fame_lock_blocks():
    s = EnvironmentStorytelling()
    s.register_prop(_statue(fame=("bastok", 5)))
    out = s.read(
        player_id="bob", prop_id="statue_1",
        fame_levels={"bastok": 3},
    )
    assert out is None


def test_fame_lock_unlocks():
    s = EnvironmentStorytelling()
    s.register_prop(_statue(fame=("bastok", 5)))
    out = s.read(
        player_id="bob", prop_id="statue_1",
        fame_levels={"bastok": 6},
    )
    assert out is not None
    assert out.is_first_discovery is True


def test_read_unknown_prop():
    s = EnvironmentStorytelling()
    assert s.read(
        player_id="bob", prop_id="ghost",
    ) is None


def test_read_blank_player():
    s = EnvironmentStorytelling()
    s.register_prop(_statue())
    assert s.read(
        player_id="", prop_id="statue_1",
    ) is None


def test_is_discovered():
    s = EnvironmentStorytelling()
    s.register_prop(_statue())
    assert s.is_discovered(
        player_id="bob", prop_id="statue_1",
    ) is False
    s.read(player_id="bob", prop_id="statue_1")
    assert s.is_discovered(
        player_id="bob", prop_id="statue_1",
    ) is True


def test_props_in_zone():
    s = EnvironmentStorytelling()
    s.register_prop(_statue("a", "bastok"))
    s.register_prop(_statue("b", "bastok"))
    s.register_prop(_statue("c", "sandy"))
    out = s.props_in_zone(zone_id="bastok")
    assert len(out) == 2
    assert {p.prop_id for p in out} == {"a", "b"}


def test_undiscovered_in_zone():
    s = EnvironmentStorytelling()
    s.register_prop(_statue("a", "bastok"))
    s.register_prop(_statue("b", "bastok"))
    s.read(player_id="bob", prop_id="a")
    out = s.undiscovered_in_zone(
        player_id="bob", zone_id="bastok",
    )
    assert len(out) == 1
    assert out[0].prop_id == "b"


def test_undiscovered_excludes_fame_locked():
    s = EnvironmentStorytelling()
    s.register_prop(_statue("a", "bastok"))
    s.register_prop(_statue(
        "b", "bastok", fame=("bastok", 5),
    ))
    out = s.undiscovered_in_zone(
        player_id="bob", zone_id="bastok",
        fame_levels={"bastok": 1},
    )
    pids = {p.prop_id for p in out}
    assert pids == {"a"}


def test_discoverer():
    s = EnvironmentStorytelling()
    s.register_prop(_statue())
    s.read(player_id="bob", prop_id="statue_1")
    s.read(player_id="cara", prop_id="statue_1")
    assert s.discoverer(
        prop_id="statue_1",
    ) == "bob"


def test_discoverer_unread_returns_none():
    s = EnvironmentStorytelling()
    s.register_prop(_statue())
    assert s.discoverer(prop_id="statue_1") is None


def test_nine_prop_kinds():
    assert len(list(PropKind)) == 9
