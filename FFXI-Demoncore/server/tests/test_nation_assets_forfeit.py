"""Tests for nation_assets_forfeit."""
from __future__ import annotations

from server.nation_assets_forfeit import (
    NationAssetsForfeitSystem, AssetKind,
    SeizureState,
)


def _reg(s, **overrides):
    args = dict(
        asset_id="manor_volker",
        npc_id="off_volker",
        nation_id="bastok",
        kind=AssetKind.REAL_ESTATE,
        description="Volker's manor in Port Bastok",
        value_gil=500_000,
    )
    args.update(overrides)
    return s.register_asset(**args)


def test_register_happy():
    s = NationAssetsForfeitSystem()
    assert _reg(s) is True


def test_register_blank():
    s = NationAssetsForfeitSystem()
    assert _reg(s, asset_id="") is False


def test_register_negative_value():
    s = NationAssetsForfeitSystem()
    assert _reg(s, value_gil=-1) is False


def test_register_dup_blocked():
    s = NationAssetsForfeitSystem()
    _reg(s)
    assert _reg(s) is False


def test_freeze_happy():
    s = NationAssetsForfeitSystem()
    _reg(s)
    assert s.freeze(
        asset_id="manor_volker", now_day=400,
        reason="defection_review",
    ) is True


def test_freeze_no_reason():
    s = NationAssetsForfeitSystem()
    _reg(s)
    assert s.freeze(
        asset_id="manor_volker", now_day=400,
        reason="",
    ) is False


def test_seize_happy():
    s = NationAssetsForfeitSystem()
    _reg(s)
    assert s.seize(
        asset_id="manor_volker", now_day=410,
        reason="defection_confirmed",
    ) is True


def test_seize_after_return_blocked():
    s = NationAssetsForfeitSystem()
    _reg(s)
    s.freeze(asset_id="manor_volker", now_day=400,
             reason="x")
    s.returns(asset_id="manor_volker", now_day=420,
              reason="diplomatic")
    assert s.seize(
        asset_id="manor_volker", now_day=430,
        reason="x",
    ) is False


def test_returns_after_freeze():
    s = NationAssetsForfeitSystem()
    _reg(s)
    s.freeze(asset_id="manor_volker", now_day=400,
             reason="x")
    assert s.returns(
        asset_id="manor_volker", now_day=420,
        reason="appealed",
    ) is True


def test_returns_after_seize():
    s = NationAssetsForfeitSystem()
    _reg(s)
    s.seize(asset_id="manor_volker", now_day=400,
            reason="x")
    assert s.returns(
        asset_id="manor_volker", now_day=420,
        reason="treaty_settlement",
    ) is True


def test_returns_intact_blocked():
    s = NationAssetsForfeitSystem()
    _reg(s)
    assert s.returns(
        asset_id="manor_volker", now_day=400,
        reason="x",
    ) is False


def test_auto_forfeit_titles_and_gear():
    s = NationAssetsForfeitSystem()
    _reg(s, asset_id="title_kc",
         kind=AssetKind.OFFICIAL_TITLE,
         description="Knight Commander",
         value_gil=0)
    _reg(s, asset_id="af_set",
         kind=AssetKind.CEREMONIAL_GEAR,
         description="Bastok ceremonial AF",
         value_gil=100_000)
    _reg(s, asset_id="manor_volker",
         kind=AssetKind.REAL_ESTATE,
         description="manor", value_gil=500_000)
    seized = s.auto_forfeit_on_defection(
        npc_id="off_volker", now_day=400,
    )
    assert "title_kc" in seized
    assert "af_set" in seized
    assert "manor_volker" not in seized


def test_auto_forfeit_skips_already_seized():
    s = NationAssetsForfeitSystem()
    _reg(s, asset_id="title_kc",
         kind=AssetKind.OFFICIAL_TITLE,
         description="x", value_gil=0)
    s.seize(asset_id="title_kc", now_day=399,
            reason="manual")
    out = s.auto_forfeit_on_defection(
        npc_id="off_volker", now_day=400,
    )
    assert out == []


def test_freeze_pending_review():
    s = NationAssetsForfeitSystem()
    _reg(s, asset_id="manor",
         kind=AssetKind.REAL_ESTATE,
         description="x", value_gil=500_000)
    _reg(s, asset_id="gil_acc",
         kind=AssetKind.GIL_ACCOUNT,
         description="x", value_gil=20_000)
    _reg(s, asset_id="title_kc",
         kind=AssetKind.OFFICIAL_TITLE,
         description="x", value_gil=0)
    frozen = s.freeze_pending_review_on_defection(
        npc_id="off_volker", now_day=400,
    )
    assert "manor" in frozen
    assert "gil_acc" in frozen
    # Auto-forfeit kinds skipped
    assert "title_kc" not in frozen


def test_assets_for_npc():
    s = NationAssetsForfeitSystem()
    _reg(s, asset_id="a")
    _reg(s, asset_id="b",
         description="another asset")
    _reg(s, asset_id="c", npc_id="other",
         description="other npc")
    out = s.assets_for_npc(npc_id="off_volker")
    assert len(out) == 2


def test_total_seized_value():
    s = NationAssetsForfeitSystem()
    _reg(s, asset_id="a", value_gil=100_000)
    _reg(s, asset_id="b",
         description="x", value_gil=50_000)
    _reg(s, asset_id="c",
         description="x", value_gil=200_000)
    s.seize(asset_id="a", now_day=400,
            reason="x")
    s.seize(asset_id="b", now_day=400,
            reason="x")
    # c stays intact
    assert s.total_seized_value(
        npc_id="off_volker",
    ) == 150_000


def test_asset_unknown():
    s = NationAssetsForfeitSystem()
    assert s.asset(asset_id="ghost") is None


def test_freeze_unknown():
    s = NationAssetsForfeitSystem()
    assert s.freeze(
        asset_id="ghost", now_day=400, reason="x",
    ) is False


def test_enum_counts():
    assert len(list(AssetKind)) == 6
    assert len(list(SeizureState)) == 4
