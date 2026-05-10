"""Tests for asset_upgrade_pipeline."""
from __future__ import annotations

import pytest

from server.asset_upgrade_pipeline import (
    AssetKind,
    AssetRecord,
    AssetState,
    AssetUpgradePipeline,
    UpgradeTool,
)


def _pipe() -> AssetUpgradePipeline:
    return AssetUpgradePipeline()


def _reg(
    pipe: AssetUpgradePipeline,
    aid: str = "bastok_anvil",
    zone: str = "bastok_markets",
    kind: AssetKind = AssetKind.MESH,
) -> AssetRecord:
    return pipe.register_asset(
        asset_id=aid,
        source_path=f"retail/{aid}.dat",
        kind=kind,
        zone_id=zone,
        poly_count_before=600,
        texture_resolution_before=256,
    )


def test_register_creates_raw_record():
    pipe = _pipe()
    rec = _reg(pipe)
    assert rec.current_state == AssetState.RAW
    assert rec.poly_count_before == 600
    assert rec.poly_count_after == 0


def test_register_duplicate_raises():
    pipe = _pipe()
    _reg(pipe)
    with pytest.raises(ValueError):
        _reg(pipe)


def test_register_empty_id_raises():
    pipe = _pipe()
    with pytest.raises(ValueError):
        pipe.register_asset(
            asset_id="", source_path="x", kind=AssetKind.MESH,
            zone_id="z",
        )


def test_register_negative_poly_raises():
    pipe = _pipe()
    with pytest.raises(ValueError):
        pipe.register_asset(
            asset_id="x", source_path="x", kind=AssetKind.MESH,
            zone_id="z", poly_count_before=-1,
        )


def test_lookup_unknown_raises():
    pipe = _pipe()
    with pytest.raises(KeyError):
        pipe.lookup("nope")


def test_advance_raw_to_upscaled_legal():
    pipe = _pipe()
    _reg(pipe)
    out = pipe.advance(
        "bastok_anvil",
        AssetState.UPSCALED_TEXTURE,
        texture_resolution_after=4096,
    )
    assert out.current_state == AssetState.UPSCALED_TEXTURE
    assert out.texture_resolution_after == 4096


def test_advance_raw_to_nanite_legal():
    pipe = _pipe()
    _reg(pipe)
    out = pipe.advance(
        "bastok_anvil", AssetState.NANITE_BUILT,
        poly_count_after=2_500_000,
    )
    assert out.current_state == AssetState.NANITE_BUILT
    assert out.poly_count_after == 2_500_000


def test_advance_skip_raises():
    """RAW → MATERIAL_AUTHORED is illegal."""
    pipe = _pipe()
    _reg(pipe)
    with pytest.raises(ValueError):
        pipe.advance(
            "bastok_anvil", AssetState.MATERIAL_AUTHORED,
        )


def test_advance_backward_raises():
    pipe = _pipe()
    _reg(pipe)
    pipe.advance("bastok_anvil", AssetState.NANITE_BUILT)
    with pytest.raises(ValueError):
        pipe.advance("bastok_anvil", AssetState.RAW)


def test_advance_unknown_asset_raises():
    pipe = _pipe()
    with pytest.raises(KeyError):
        pipe.advance("nope", AssetState.NANITE_BUILT)


def test_advance_same_state_raises():
    pipe = _pipe()
    _reg(pipe)
    with pytest.raises(ValueError):
        pipe.advance("bastok_anvil", AssetState.RAW)


def test_full_walkthrough_to_ship_ready():
    pipe = _pipe()
    _reg(pipe)
    pipe.advance("bastok_anvil", AssetState.UPSCALED_TEXTURE)
    pipe.advance("bastok_anvil", AssetState.NANITE_BUILT)
    pipe.advance("bastok_anvil", AssetState.MATERIAL_AUTHORED)
    pipe.advance("bastok_anvil", AssetState.PBR_BAKED)
    pipe.advance("bastok_anvil", AssetState.LOD_GENERATED)
    out = pipe.advance("bastok_anvil", AssetState.SHIP_READY)
    assert out.current_state == AssetState.SHIP_READY


def test_ship_ready_is_terminal():
    pipe = _pipe()
    _reg(pipe)
    for st in (
        AssetState.UPSCALED_TEXTURE,
        AssetState.NANITE_BUILT,
        AssetState.MATERIAL_AUTHORED,
        AssetState.PBR_BAKED,
        AssetState.LOD_GENERATED,
        AssetState.SHIP_READY,
    ):
        pipe.advance("bastok_anvil", st)
    with pytest.raises(ValueError):
        pipe.advance("bastok_anvil", AssetState.LOD_GENERATED)


def test_mark_failed_records_error():
    pipe = _pipe()
    _reg(pipe)
    pipe.advance("bastok_anvil", AssetState.NANITE_BUILT)
    out = pipe.mark_failed(
        "bastok_anvil", "nanite import OOM",
    )
    assert out.current_state == AssetState.FAILED
    assert out.errors == ("nanite import OOM",)


def test_mark_failed_blank_error_raises():
    pipe = _pipe()
    _reg(pipe)
    with pytest.raises(ValueError):
        pipe.mark_failed("bastok_anvil", "")


def test_mark_failed_ship_ready_raises():
    pipe = _pipe()
    _reg(pipe)
    for st in (
        AssetState.UPSCALED_TEXTURE,
        AssetState.NANITE_BUILT,
        AssetState.MATERIAL_AUTHORED,
        AssetState.PBR_BAKED,
        AssetState.LOD_GENERATED,
        AssetState.SHIP_READY,
    ):
        pipe.advance("bastok_anvil", st)
    with pytest.raises(ValueError):
        pipe.mark_failed("bastok_anvil", "rollback")


def test_failed_can_retry_to_raw():
    pipe = _pipe()
    _reg(pipe)
    pipe.advance(
        "bastok_anvil", AssetState.NANITE_BUILT,
        poly_count_after=999,
    )
    pipe.mark_failed("bastok_anvil", "broken normals")
    out = pipe.advance("bastok_anvil", AssetState.RAW)
    assert out.current_state == AssetState.RAW
    assert out.poly_count_after == 0  # reset
    # error history preserved for post-mortem audit.
    assert "broken normals" in out.errors


def test_failed_cannot_jump_anywhere_else():
    pipe = _pipe()
    _reg(pipe)
    pipe.mark_failed("bastok_anvil", "boom")
    with pytest.raises(ValueError):
        pipe.advance("bastok_anvil", AssetState.NANITE_BUILT)


def test_bulk_advance_moves_many():
    pipe = _pipe()
    for i in range(5):
        _reg(pipe, aid=f"prop_{i}")
    out = pipe.bulk_advance(
        [f"prop_{i}" for i in range(5)],
        AssetState.UPSCALED_TEXTURE,
    )
    assert len(out) == 5
    for r in out:
        assert r.current_state == AssetState.UPSCALED_TEXTURE


def test_bulk_advance_propagates_first_error():
    pipe = _pipe()
    _reg(pipe, aid="a")
    _reg(pipe, aid="b")
    pipe.advance("b", AssetState.NANITE_BUILT)
    with pytest.raises(ValueError):
        pipe.bulk_advance(
            ["a", "b"], AssetState.UPSCALED_TEXTURE,
        )


def test_assets_in_state_filters():
    pipe = _pipe()
    _reg(pipe, aid="a")
    _reg(pipe, aid="b")
    pipe.advance("a", AssetState.NANITE_BUILT)
    raws = pipe.assets_in_state(AssetState.RAW)
    assert len(raws) == 1
    assert raws[0].asset_id == "b"


def test_assets_in_zone_filters():
    pipe = _pipe()
    _reg(pipe, aid="a", zone="bastok_markets")
    _reg(pipe, aid="b", zone="bastok_mines")
    in_markets = pipe.assets_in_zone("bastok_markets")
    assert len(in_markets) == 1
    assert in_markets[0].asset_id == "a"


def test_upgrade_all_in_zone_advances_each():
    pipe = _pipe()
    _reg(pipe, aid="a", zone="z")
    _reg(pipe, aid="b", zone="z")
    moved = pipe.upgrade_all_in_zone(
        "z", AssetState.UPSCALED_TEXTURE,
    )
    assert len(moved) == 2
    for r in moved:
        assert r.current_state == AssetState.UPSCALED_TEXTURE


def test_upgrade_all_in_zone_skips_terminal():
    pipe = _pipe()
    _reg(pipe, aid="a", zone="z")
    _reg(pipe, aid="b", zone="z")
    pipe.mark_failed("b", "boom")
    moved = pipe.upgrade_all_in_zone(
        "z", AssetState.UPSCALED_TEXTURE,
    )
    assert len(moved) == 1
    assert moved[0].asset_id == "a"


def test_retry_failed_resets_all():
    pipe = _pipe()
    _reg(pipe, aid="a")
    _reg(pipe, aid="b")
    pipe.mark_failed("a", "x")
    pipe.mark_failed("b", "y")
    out = pipe.retry_failed()
    assert len(out) == 2
    assert all(r.current_state == AssetState.RAW for r in out)


def test_pending_count_excludes_terminal():
    pipe = _pipe()
    _reg(pipe, aid="a")
    _reg(pipe, aid="b")
    _reg(pipe, aid="c")
    pipe.mark_failed("c", "x")
    assert pipe.pending_count() == 2


def test_zone_progress_pct():
    pipe = _pipe()
    _reg(pipe, aid="a", zone="z")
    _reg(pipe, aid="b", zone="z")
    _reg(pipe, aid="c", zone="z")
    _reg(pipe, aid="d", zone="z")
    for st in (
        AssetState.UPSCALED_TEXTURE,
        AssetState.NANITE_BUILT,
        AssetState.MATERIAL_AUTHORED,
        AssetState.PBR_BAKED,
        AssetState.LOD_GENERATED,
        AssetState.SHIP_READY,
    ):
        pipe.advance("a", st)
    pipe.mark_failed("b", "boom")
    total, complete, failed, pct = pipe.zone_progress("z")
    assert total == 4
    assert complete == 1
    assert failed == 1
    assert pct == 25.0


def test_zone_progress_empty_zone():
    pipe = _pipe()
    assert pipe.zone_progress("nope") == (0, 0, 0, 0.0)


def test_throughput_per_hour_zero_window_raises():
    pipe = _pipe()
    with pytest.raises(ValueError):
        pipe.throughput_per_hour(0)


def test_throughput_per_hour_counts_ship_ready():
    pipe = _pipe()
    _reg(pipe, aid="a")
    for st in (
        AssetState.UPSCALED_TEXTURE,
        AssetState.NANITE_BUILT,
        AssetState.MATERIAL_AUTHORED,
        AssetState.PBR_BAKED,
        AssetState.LOD_GENERATED,
        AssetState.SHIP_READY,
    ):
        pipe.advance("a", st)
    rate = pipe.throughput_per_hour(1.0)
    assert rate == 1.0


def test_transition_log_appends():
    pipe = _pipe()
    _reg(pipe)
    pipe.advance("bastok_anvil", AssetState.NANITE_BUILT)
    pipe.advance("bastok_anvil", AssetState.MATERIAL_AUTHORED)
    log = pipe.transition_log()
    assert len(log) == 2
    assert log[0][1] == AssetState.RAW
    assert log[0][2] == AssetState.NANITE_BUILT
    assert log[1][2] == AssetState.MATERIAL_AUTHORED


def test_errors_accumulate_across_failures():
    pipe = _pipe()
    _reg(pipe)
    pipe.mark_failed("bastok_anvil", "first")
    pipe.advance("bastok_anvil", AssetState.RAW)
    pipe.mark_failed("bastok_anvil", "second")
    errs = pipe.errors_for("bastok_anvil")
    assert "first" in errs
    assert "second" in errs


def test_upgrade_tool_enum_has_open_source_chain():
    names = {t.value for t in UpgradeTool}
    assert "real_esrgan" in names
    assert "marigold" in names
    assert "stable_delight" in names
    assert "codeformer" in names
    assert "material_maker" in names
    assert "blender_geonodes" in names


def test_ship_ready_count():
    pipe = _pipe()
    _reg(pipe, aid="a")
    _reg(pipe, aid="b")
    for st in (
        AssetState.UPSCALED_TEXTURE,
        AssetState.NANITE_BUILT,
        AssetState.MATERIAL_AUTHORED,
        AssetState.PBR_BAKED,
        AssetState.LOD_GENERATED,
        AssetState.SHIP_READY,
    ):
        pipe.advance("a", st)
    assert pipe.ship_ready_count() == 1
    assert pipe.failed_count() == 0
