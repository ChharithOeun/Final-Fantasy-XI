"""Player mosaic — tile-by-tile assembly of public art.

Mosaic artists work from a tile inventory of colored glass
pieces, placing them one at a time into a sketched pattern.
Mosaics are large group works typically commissioned by
temples, plazas, or guildhalls. Once assembled and grouted,
the work becomes a permanent public installation.

Lifecycle
    SKETCH       pattern outlined, no tiles placed
    ASSEMBLING   tiles being placed
    GROUTING     final layer applied
    COMPLETE     installed
    ABANDONED    artist gave up

Public surface
--------------
    MosaicStage enum
    TileColor enum
    Mosaic dataclass (frozen)
    PlayerMosaicSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TileColor(str, enum.Enum):
    AZURE = "azure"
    SCARLET = "scarlet"
    GOLD = "gold"
    EMERALD = "emerald"
    IVORY = "ivory"
    OBSIDIAN = "obsidian"


class MosaicStage(str, enum.Enum):
    SKETCH = "sketch"
    ASSEMBLING = "assembling"
    GROUTING = "grouting"
    COMPLETE = "complete"
    ABANDONED = "abandoned"


@dataclasses.dataclass(frozen=True)
class Mosaic:
    mosaic_id: str
    artist_id: str
    commissioner_id: str
    title: str
    target_tile_count: int
    tiles_placed: int
    color_diversity: int  # distinct colors used
    stage: MosaicStage
    install_location: str


@dataclasses.dataclass
class _MState:
    spec: Mosaic
    colors_used: set[str] = dataclasses.field(
        default_factory=set,
    )


@dataclasses.dataclass
class PlayerMosaicSystem:
    _mosaics: dict[str, _MState] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def commission_mosaic(
        self, *, artist_id: str, commissioner_id: str,
        title: str, target_tile_count: int,
        install_location: str,
    ) -> t.Optional[str]:
        if not artist_id or not commissioner_id:
            return None
        if not title or not install_location:
            return None
        if target_tile_count < 100:
            return None
        if target_tile_count > 100_000:
            return None
        mid = f"mosaic_{self._next}"
        self._next += 1
        spec = Mosaic(
            mosaic_id=mid, artist_id=artist_id,
            commissioner_id=commissioner_id,
            title=title,
            target_tile_count=target_tile_count,
            tiles_placed=0, color_diversity=0,
            stage=MosaicStage.SKETCH,
            install_location=install_location,
        )
        self._mosaics[mid] = _MState(spec=spec)
        return mid

    def begin_assembly(
        self, *, mosaic_id: str,
    ) -> bool:
        if mosaic_id not in self._mosaics:
            return False
        st = self._mosaics[mosaic_id]
        if st.spec.stage != MosaicStage.SKETCH:
            return False
        st.spec = dataclasses.replace(
            st.spec, stage=MosaicStage.ASSEMBLING,
        )
        return True

    def place_tiles(
        self, *, mosaic_id: str, color: TileColor,
        count: int,
    ) -> t.Optional[int]:
        """Place 'count' tiles of one color. Returns
        new tiles_placed total. Cannot exceed target.
        """
        if mosaic_id not in self._mosaics:
            return None
        st = self._mosaics[mosaic_id]
        if st.spec.stage != MosaicStage.ASSEMBLING:
            return None
        if count <= 0 or count > 1000:
            return None
        new_total = st.spec.tiles_placed + count
        if new_total > st.spec.target_tile_count:
            return None
        st.colors_used.add(color.value)
        st.spec = dataclasses.replace(
            st.spec, tiles_placed=new_total,
            color_diversity=len(st.colors_used),
        )
        return new_total

    def begin_grouting(
        self, *, mosaic_id: str,
    ) -> bool:
        """Begin grouting. Must have placed all tiles
        first.
        """
        if mosaic_id not in self._mosaics:
            return False
        st = self._mosaics[mosaic_id]
        if st.spec.stage != MosaicStage.ASSEMBLING:
            return False
        if (
            st.spec.tiles_placed
            != st.spec.target_tile_count
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, stage=MosaicStage.GROUTING,
        )
        return True

    def complete(
        self, *, mosaic_id: str,
    ) -> bool:
        if mosaic_id not in self._mosaics:
            return False
        st = self._mosaics[mosaic_id]
        if st.spec.stage != MosaicStage.GROUTING:
            return False
        st.spec = dataclasses.replace(
            st.spec, stage=MosaicStage.COMPLETE,
        )
        return True

    def abandon(
        self, *, mosaic_id: str,
    ) -> bool:
        if mosaic_id not in self._mosaics:
            return False
        st = self._mosaics[mosaic_id]
        if st.spec.stage in (
            MosaicStage.COMPLETE,
            MosaicStage.ABANDONED,
        ):
            return False
        st.spec = dataclasses.replace(
            st.spec, stage=MosaicStage.ABANDONED,
        )
        return True

    def mosaic(
        self, *, mosaic_id: str,
    ) -> t.Optional[Mosaic]:
        st = self._mosaics.get(mosaic_id)
        return st.spec if st else None

    def progress_pct(
        self, *, mosaic_id: str,
    ) -> int:
        st = self._mosaics.get(mosaic_id)
        if st is None:
            return 0
        return (
            st.spec.tiles_placed * 100
            // max(1, st.spec.target_tile_count)
        )


__all__ = [
    "TileColor", "MosaicStage", "Mosaic",
    "PlayerMosaicSystem",
]
