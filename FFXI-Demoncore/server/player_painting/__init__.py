"""Player painting — canvas works for galleries and collectors.

Players paint pieces of varying sizes, finish them, and submit
to galleries where collectors bid. Appraised value scales
with technique * palette richness * size multiplier; offers at
or above appraised auto-accept, lower offers are refused. After
a show closes, unsold pieces return to the painter's collection.

Lifecycle
    DRAFT       painter still working
    FINISHED    appraised, ready to exhibit or sell direct
    EXHIBITED   gallery showing in progress
    SOLD        collector bought
    UNSOLD      show closed without buyer

Public surface
--------------
    PaintingSize enum
    PaintingState enum
    Painting dataclass (frozen)
    PlayerPaintingSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_SIZE_MULTIPLIER = {
    "miniature": 1,
    "small": 2,
    "medium": 5,
    "large": 10,
    "mural": 25,
}


class PaintingSize(str, enum.Enum):
    MINIATURE = "miniature"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    MURAL = "mural"


class PaintingState(str, enum.Enum):
    DRAFT = "draft"
    FINISHED = "finished"
    EXHIBITED = "exhibited"
    SOLD = "sold"
    UNSOLD = "unsold"


@dataclasses.dataclass(frozen=True)
class Painting:
    painting_id: str
    painter_id: str
    title: str
    subject: str
    size: PaintingSize
    technique_quality: int   # 1..100
    palette_richness: int    # 1..100
    state: PaintingState
    appraised_value_gil: int
    gallery_id: str
    sold_price_gil: int
    buyer_id: str


@dataclasses.dataclass
class PlayerPaintingSystem:
    _paintings: dict[str, Painting] = dataclasses.field(
        default_factory=dict,
    )
    _next: int = 1

    def begin_painting(
        self, *, painter_id: str, title: str,
        subject: str, size: PaintingSize,
        technique_quality: int, palette_richness: int,
    ) -> t.Optional[str]:
        if not painter_id or not title or not subject:
            return None
        if not 1 <= technique_quality <= 100:
            return None
        if not 1 <= palette_richness <= 100:
            return None
        pid = f"painting_{self._next}"
        self._next += 1
        self._paintings[pid] = Painting(
            painting_id=pid, painter_id=painter_id,
            title=title, subject=subject, size=size,
            technique_quality=technique_quality,
            palette_richness=palette_richness,
            state=PaintingState.DRAFT,
            appraised_value_gil=0, gallery_id="",
            sold_price_gil=0, buyer_id="",
        )
        return pid

    def finish_painting(
        self, *, painting_id: str,
    ) -> t.Optional[int]:
        """Compute appraisal & lock the work. Returns
        appraised value in gil.
        """
        if painting_id not in self._paintings:
            return None
        p = self._paintings[painting_id]
        if p.state != PaintingState.DRAFT:
            return None
        mult = _SIZE_MULTIPLIER[p.size.value]
        # Appraised = (tech + palette) * mult * 5
        value = (
            (p.technique_quality + p.palette_richness)
            * mult * 5
        )
        self._paintings[painting_id] = (
            dataclasses.replace(
                p, state=PaintingState.FINISHED,
                appraised_value_gil=value,
            )
        )
        return value

    def submit_to_gallery(
        self, *, painting_id: str, gallery_id: str,
    ) -> bool:
        if painting_id not in self._paintings:
            return False
        p = self._paintings[painting_id]
        if p.state != PaintingState.FINISHED:
            return False
        if not gallery_id:
            return False
        self._paintings[painting_id] = (
            dataclasses.replace(
                p, state=PaintingState.EXHIBITED,
                gallery_id=gallery_id,
            )
        )
        return True

    def offer_purchase(
        self, *, painting_id: str, buyer_id: str,
        offer_gil: int,
    ) -> bool:
        """Collector tries to buy. Auto-accepts if
        offer_gil >= appraised; rejects below.
        """
        if painting_id not in self._paintings:
            return False
        p = self._paintings[painting_id]
        if p.state != PaintingState.EXHIBITED:
            return False
        if not buyer_id or buyer_id == p.painter_id:
            return False
        if offer_gil < p.appraised_value_gil:
            return False
        self._paintings[painting_id] = (
            dataclasses.replace(
                p, state=PaintingState.SOLD,
                sold_price_gil=offer_gil,
                buyer_id=buyer_id,
            )
        )
        return True

    def close_show(
        self, *, painting_id: str,
    ) -> bool:
        if painting_id not in self._paintings:
            return False
        p = self._paintings[painting_id]
        if p.state != PaintingState.EXHIBITED:
            return False
        self._paintings[painting_id] = (
            dataclasses.replace(
                p, state=PaintingState.UNSOLD,
            )
        )
        return True

    def painting(
        self, *, painting_id: str,
    ) -> t.Optional[Painting]:
        return self._paintings.get(painting_id)

    def painter_collection(
        self, *, painter_id: str,
    ) -> list[Painting]:
        return [
            p for p in self._paintings.values()
            if p.painter_id == painter_id
        ]


__all__ = [
    "PaintingSize", "PaintingState", "Painting",
    "PlayerPaintingSystem",
]
