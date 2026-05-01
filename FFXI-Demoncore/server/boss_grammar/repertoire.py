"""Layer 2: the boss's attack repertoire.

Per BOSS_GRAMMAR.md a standard hero boss has 7-12 attacks split into:
    - 3-4 small AOE  (~8m radius, 1.5s cast)
    - 2-3 medium AOE (~15m radius, 3s cast)
    - 1-2 huge ultimate (~25m radius, 5s cast, often arena-wide)
    - 1 signature WS that closes a skillchain
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class AttackSize(str, enum.Enum):
    SMALL = "small"
    MEDIUM = "medium"
    HUGE = "huge"
    SIGNATURE_WS = "signature_ws"


@dataclasses.dataclass(frozen=True)
class AOESizeBand:
    size: AttackSize
    typical_radius_m: float
    typical_cast_seconds: float
    min_count: int
    max_count: int


AOE_SIZE_BANDS: dict[AttackSize, AOESizeBand] = {
    AttackSize.SMALL: AOESizeBand(
        size=AttackSize.SMALL,
        typical_radius_m=8.0, typical_cast_seconds=1.5,
        min_count=3, max_count=4,
    ),
    AttackSize.MEDIUM: AOESizeBand(
        size=AttackSize.MEDIUM,
        typical_radius_m=15.0, typical_cast_seconds=3.0,
        min_count=2, max_count=3,
    ),
    AttackSize.HUGE: AOESizeBand(
        size=AttackSize.HUGE,
        typical_radius_m=25.0, typical_cast_seconds=5.0,
        min_count=1, max_count=2,
    ),
    AttackSize.SIGNATURE_WS: AOESizeBand(
        size=AttackSize.SIGNATURE_WS,
        typical_radius_m=0.0, typical_cast_seconds=2.0,
        min_count=1, max_count=1,
    ),
}


# Doc: '7-12 unique attacks'.
MIN_REPERTOIRE_SIZE: int = 7
MAX_REPERTOIRE_SIZE: int = 12


@dataclasses.dataclass(frozen=True)
class BossAttack:
    """One signature attack."""
    attack_id: str
    label: str
    size: AttackSize
    radius_m: float
    cast_seconds: float
    aoe_shape: str             # 'circle' | 'cone' | 'line' | etc.
    element: str               # 'fire' | 'ice' | 'physical' | 'none'
    damage_profile: str        # 'flat' | 'falloff' | 'tip_max'
    chain_property: t.Optional[str] = None    # for signature_ws only


@dataclasses.dataclass
class Repertoire:
    """A boss's attack catalog."""
    boss_id: str
    attacks: tuple[BossAttack, ...]

    def by_size(self, size: AttackSize) -> tuple[BossAttack, ...]:
        return tuple(a for a in self.attacks if a.size == size)

    def count_by_size(self) -> dict[AttackSize, int]:
        out: dict[AttackSize, int] = {s: 0 for s in AttackSize}
        for a in self.attacks:
            out[a.size] += 1
        return out


def classify_attack_size(*,
                              radius_m: float,
                              cast_seconds: float,
                              has_chain_property: bool = False
                              ) -> AttackSize:
    """Heuristic: which size band does this attack land in?"""
    if has_chain_property:
        return AttackSize.SIGNATURE_WS
    if radius_m >= 20.0 or cast_seconds >= 4.0:
        return AttackSize.HUGE
    if radius_m >= 12.0 or cast_seconds >= 2.5:
        return AttackSize.MEDIUM
    return AttackSize.SMALL


def validate_repertoire(rep: Repertoire) -> list[str]:
    """Doc-conformance check. Returns complaint list (empty == valid)."""
    complaints: list[str] = []
    n = len(rep.attacks)
    if n < MIN_REPERTOIRE_SIZE:
        complaints.append(
            f"repertoire {rep.boss_id} has {n} attacks; "
            f"doc requires >= {MIN_REPERTOIRE_SIZE}")
    if n > MAX_REPERTOIRE_SIZE:
        complaints.append(
            f"repertoire {rep.boss_id} has {n} attacks; "
            f"doc max is {MAX_REPERTOIRE_SIZE}")
    counts = rep.count_by_size()
    for size, band in AOE_SIZE_BANDS.items():
        c = counts[size]
        if c < band.min_count:
            complaints.append(
                f"{rep.boss_id} has {c} {size.value} attacks; "
                f"doc requires >= {band.min_count}")
        if c > band.max_count:
            complaints.append(
                f"{rep.boss_id} has {c} {size.value} attacks; "
                f"doc max is {band.max_count}")
    # IDs unique
    ids = [a.attack_id for a in rep.attacks]
    if len(set(ids)) != len(ids):
        complaints.append(f"{rep.boss_id} has duplicate attack IDs")
    return complaints
