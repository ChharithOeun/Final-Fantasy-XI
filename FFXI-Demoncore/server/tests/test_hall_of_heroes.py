"""Tests for hall_of_heroes."""
from __future__ import annotations

from server.hall_of_heroes import HallOfHeroes, HallSection


def _setup():
    h = HallOfHeroes()
    h.register_hall(
        hall_id="bastok_hall", zone_id="metalworks",
        region_id="bastok",
    )
    return h


def test_register_hall_happy():
    h = _setup()
    out = h.get_hall(hall_id="bastok_hall")
    assert out is not None
    assert out.region_id == "bastok"


def test_register_blank_blocked():
    h = HallOfHeroes()
    assert h.register_hall(
        hall_id="", zone_id="z", region_id="r",
    ) is False


def test_duplicate_hall_blocked():
    h = _setup()
    again = h.register_hall(
        hall_id="bastok_hall", zone_id="z", region_id="r",
    )
    assert again is False


def test_curate_statue_happy():
    h = _setup()
    sid = h.curate_statue(
        hall_id="bastok_hall", title_id="vorraks_bane",
        player_id="alice", sculptor_id="iron_chisel",
        unveiled_at=100, section=HallSection.SANCTUM,
    )
    assert sid == "statue_1"
    assert h.total_statues() == 1


def test_curate_unknown_hall():
    h = HallOfHeroes()
    sid = h.curate_statue(
        hall_id="ghost", title_id="t", player_id="p",
        sculptor_id="s", unveiled_at=10,
        section=HallSection.NAVE,
    )
    assert sid == ""


def test_curate_blank_title():
    h = _setup()
    sid = h.curate_statue(
        hall_id="bastok_hall", title_id="",
        player_id="alice", sculptor_id="s",
        unveiled_at=10, section=HallSection.NAVE,
    )
    assert sid == ""


def test_curate_blank_player():
    h = _setup()
    sid = h.curate_statue(
        hall_id="bastok_hall", title_id="t",
        player_id="", sculptor_id="s",
        unveiled_at=10, section=HallSection.NAVE,
    )
    assert sid == ""


def test_no_duplicate_player_title_in_hall():
    h = _setup()
    h.curate_statue(
        hall_id="bastok_hall", title_id="t",
        player_id="alice", sculptor_id="s",
        unveiled_at=10, section=HallSection.NAVE,
    )
    again = h.curate_statue(
        hall_id="bastok_hall", title_id="t",
        player_id="alice", sculptor_id="s2",
        unveiled_at=20, section=HallSection.NAVE,
    )
    assert again == ""


def test_remove_statue_happy():
    h = _setup()
    sid = h.curate_statue(
        hall_id="bastok_hall", title_id="t",
        player_id="alice", sculptor_id="s",
        unveiled_at=10, section=HallSection.NAVE,
    )
    assert h.remove_statue(statue_id=sid) is True
    assert h.total_statues() == 0


def test_remove_unknown_statue():
    h = _setup()
    assert h.remove_statue(statue_id="ghost") is False


def test_visit_counts():
    h = _setup()
    for v in ["alice", "bob", "carol"]:
        h.visit(
            hall_id="bastok_hall",
            visitor_id=v, visited_at=10,
        )
    hall = h.get_hall(hall_id="bastok_hall")
    assert hall is not None
    assert hall.visit_count == 3


def test_visit_blank_visitor_rejected():
    h = _setup()
    out = h.visit(
        hall_id="bastok_hall", visitor_id="",
        visited_at=10,
    )
    assert out is False


def test_visit_unknown_hall_rejected():
    h = _setup()
    out = h.visit(
        hall_id="ghost", visitor_id="alice",
        visited_at=10,
    )
    assert out is False


def test_statues_in_section():
    h = _setup()
    h.curate_statue(
        hall_id="bastok_hall", title_id="a",
        player_id="alice", sculptor_id="s",
        unveiled_at=1, section=HallSection.SANCTUM,
    )
    h.curate_statue(
        hall_id="bastok_hall", title_id="b",
        player_id="bob", sculptor_id="s",
        unveiled_at=2, section=HallSection.NAVE,
    )
    h.curate_statue(
        hall_id="bastok_hall", title_id="c",
        player_id="carol", sculptor_id="s",
        unveiled_at=3, section=HallSection.SANCTUM,
    )
    sanctum = h.statues_in_section(
        hall_id="bastok_hall", section=HallSection.SANCTUM,
    )
    assert len(sanctum) == 2


def test_statues_for_player():
    h = _setup()
    h.register_hall(
        hall_id="sandy_hall", zone_id="cathedral",
        region_id="san_doria",
    )
    h.curate_statue(
        hall_id="bastok_hall", title_id="t1",
        player_id="alice", sculptor_id="s",
        unveiled_at=1, section=HallSection.SANCTUM,
    )
    h.curate_statue(
        hall_id="sandy_hall", title_id="t2",
        player_id="alice", sculptor_id="s",
        unveiled_at=2, section=HallSection.CHANCEL,
    )
    out = h.statues_for_player(player_id="alice")
    assert len(out) == 2


def test_statues_in_unknown_section_returns_empty():
    h = _setup()
    out = h.statues_in_section(
        hall_id="bastok_hall", section=HallSection.SANCTUM,
    )
    assert out == ()


def test_four_hall_sections():
    assert len(list(HallSection)) == 4


def test_remove_clears_player_index():
    h = _setup()
    sid = h.curate_statue(
        hall_id="bastok_hall", title_id="t",
        player_id="alice", sculptor_id="s",
        unveiled_at=10, section=HallSection.NAVE,
    )
    h.remove_statue(statue_id=sid)
    out = h.statues_for_player(player_id="alice")
    assert out == ()
