"""Tests for player legacy."""
from __future__ import annotations

from server.player_legacy import (
    DeceasedEstate,
    GearItem,
    LEGACY_CLAIM_WINDOW_SECONDS,
    PlayerLegacyRegistry,
)


def _basic_estate(
    *, player="alice", gil=10000,
    died_at=100.0,
) -> DeceasedEstate:
    return DeceasedEstate(
        player_id=player, gil=gil,
        fame_by_nation={"bastok": 100, "san_doria": 50},
        faction_reputations={"bastok": 800},
        gear=(
            GearItem(item_id="g_a", tier=5, value_gil=10000),
            GearItem(item_id="g_b", tier=3, value_gil=2000),
            GearItem(item_id="g_c", tier=4, value_gil=5000),
            GearItem(item_id="g_d", tier=1, value_gil=500),
        ),
        titles=("Knight",),
        died_at_seconds=died_at,
    )


def test_designate_heir_succeeds():
    reg = PlayerLegacyRegistry()
    assert reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    assert reg.has_designation("alice")
    assert reg.heir_for("alice") == "alice_heir"


def test_designate_self_rejected():
    reg = PlayerLegacyRegistry()
    assert not reg.designate_heir(
        player_id="alice", heir_player_id="alice",
    )


def test_redesignate_overwrites():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="heir_1",
    )
    reg.designate_heir(
        player_id="alice", heir_player_id="heir_2",
    )
    assert reg.heir_for("alice") == "heir_2"


def test_deceased_records_estate():
    reg = PlayerLegacyRegistry()
    assert reg.deceased(estate=_basic_estate())
    assert reg.total_estates() == 1


def test_double_deceased_rejected():
    reg = PlayerLegacyRegistry()
    reg.deceased(estate=_basic_estate())
    assert not reg.deceased(estate=_basic_estate())


def test_claim_without_designation_fails():
    reg = PlayerLegacyRegistry()
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert res is None


def test_claim_wrong_heir_fails():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="real_heir",
    )
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="impostor",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert res is None


def test_claim_succeeds():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert res is not None
    # 50% gil default = 5000
    assert res.gil_transferred == 5000
    # Top 3 gear (tier 5, 4, 3)
    transferred_ids = {g.item_id for g in res.gear_transferred}
    assert "g_a" in transferred_ids
    assert "g_c" in transferred_ids
    assert "g_b" in transferred_ids
    assert "g_d" not in transferred_ids


def test_claim_double_rejected():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate())
    reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    res2 = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=300.0,
    )
    assert res2 is None


def test_claim_outside_window_rejected():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate(died_at=100.0))
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=100.0 + LEGACY_CLAIM_WINDOW_SECONDS + 1,
    )
    assert res is None


def test_fame_inheritance():
    reg = PlayerLegacyRegistry(fame_fraction=0.5)
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert res.fame_transferred_by_nation["bastok"] == 50
    assert res.fame_transferred_by_nation["san_doria"] == 25


def test_faction_rep_inheritance():
    reg = PlayerLegacyRegistry(rep_fraction=0.4)
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    # 800 * 0.4 = 320
    assert res.rep_transferred["bastok"] == 320


def test_titles_pass_through():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert "Knight" in res.titles_transferred


def test_top_n_items_configurable():
    reg = PlayerLegacyRegistry(top_n_items=2)
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    reg.deceased(estate=_basic_estate())
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert len(res.gear_transferred) == 2


def test_no_estate_claim_rejected():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="alice", heir_player_id="alice_heir",
    )
    res = reg.claim_legacy(
        heir_player_id="alice_heir",
        deceased_player_id="alice",
        now_seconds=200.0,
    )
    assert res is None


def test_total_counts():
    reg = PlayerLegacyRegistry()
    reg.designate_heir(
        player_id="a", heir_player_id="ah",
    )
    reg.designate_heir(
        player_id="b", heir_player_id="bh",
    )
    assert reg.total_designations() == 2
