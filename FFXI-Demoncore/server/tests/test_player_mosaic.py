"""Tests for player_mosaic."""
from __future__ import annotations

from server.player_mosaic import (
    PlayerMosaicSystem, MosaicStage, TileColor,
)


def _commission(
    s: PlayerMosaicSystem, target: int = 1000,
) -> str:
    return s.commission_mosaic(
        artist_id="naji", commissioner_id="bastok_temple",
        title="Phoenix in Flight",
        target_tile_count=target,
        install_location="bastok_temple_atrium",
    )


def test_commission_happy():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    assert mid is not None


def test_commission_empty_artist():
    s = PlayerMosaicSystem()
    assert s.commission_mosaic(
        artist_id="", commissioner_id="x",
        title="t", target_tile_count=500,
        install_location="loc",
    ) is None


def test_commission_too_few_tiles():
    s = PlayerMosaicSystem()
    assert s.commission_mosaic(
        artist_id="a", commissioner_id="x",
        title="t", target_tile_count=50,
        install_location="loc",
    ) is None


def test_commission_too_many_tiles():
    s = PlayerMosaicSystem()
    assert s.commission_mosaic(
        artist_id="a", commissioner_id="x",
        title="t", target_tile_count=200_000,
        install_location="loc",
    ) is None


def test_begin_assembly_happy():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    assert s.begin_assembly(mosaic_id=mid) is True


def test_begin_assembly_double_blocked():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    s.begin_assembly(mosaic_id=mid)
    assert s.begin_assembly(mosaic_id=mid) is False


def test_place_tiles_happy():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    s.begin_assembly(mosaic_id=mid)
    total = s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE,
        count=100,
    )
    assert total == 100


def test_place_tiles_before_assembly_blocked():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    assert s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE,
        count=100,
    ) is None


def test_place_tiles_invalid_count():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    s.begin_assembly(mosaic_id=mid)
    assert s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE,
        count=0,
    ) is None


def test_place_tiles_overcommit_blocked():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE,
        count=150,
    )
    # Trying to place 100 more would exceed 200
    assert s.place_tiles(
        mosaic_id=mid, color=TileColor.SCARLET,
        count=100,
    ) is None


def test_color_diversity_tracked():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=100,
    )
    s.place_tiles(
        mosaic_id=mid, color=TileColor.SCARLET, count=100,
    )
    s.place_tiles(
        mosaic_id=mid, color=TileColor.GOLD, count=100,
    )
    # Same color again — diversity stays at 3.
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=100,
    )
    m = s.mosaic(mosaic_id=mid)
    assert m.color_diversity == 3


def test_begin_grouting_requires_full():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=100,
    )
    assert s.begin_grouting(mosaic_id=mid) is False


def test_begin_grouting_when_full():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=200,
    )
    assert s.begin_grouting(mosaic_id=mid) is True


def test_complete_after_grout():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=200,
    )
    s.begin_grouting(mosaic_id=mid)
    assert s.complete(mosaic_id=mid) is True
    assert s.mosaic(
        mosaic_id=mid,
    ).stage == MosaicStage.COMPLETE


def test_complete_before_grout_blocked():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=200,
    )
    assert s.complete(mosaic_id=mid) is False


def test_abandon_happy():
    s = PlayerMosaicSystem()
    mid = _commission(s)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=200,
    )
    assert s.abandon(mosaic_id=mid) is True
    assert s.mosaic(
        mosaic_id=mid,
    ).stage == MosaicStage.ABANDONED


def test_abandon_after_complete_blocked():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=200,
    )
    s.begin_grouting(mosaic_id=mid)
    s.complete(mosaic_id=mid)
    assert s.abandon(mosaic_id=mid) is False


def test_progress_pct():
    s = PlayerMosaicSystem()
    mid = _commission(s, target=200)
    s.begin_assembly(mosaic_id=mid)
    s.place_tiles(
        mosaic_id=mid, color=TileColor.AZURE, count=50,
    )
    assert s.progress_pct(mosaic_id=mid) == 25


def test_unknown_mosaic():
    s = PlayerMosaicSystem()
    assert s.mosaic(mosaic_id="ghost") is None
    assert s.progress_pct(mosaic_id="ghost") == 0


def test_enum_counts():
    assert len(list(TileColor)) == 6
    assert len(list(MosaicStage)) == 5
