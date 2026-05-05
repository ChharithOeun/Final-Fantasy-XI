"""Harpoon fishing — underwater spear-fishing variant.

Surface fishing uses a rod, bait, and patience. Harpoon
fishing uses a SPEAR or HARPOON, a SPEAR_DIVER (or any job
with the underwater swim mastery), and a tracked TARGET in
front of you. It rewards aim and reaction, not waiting.

Each underwater biome has a HARPOON_CATCH_TABLE keyed by
target species; deeper biomes carry rarer prey. A cast goes
through stages:
  TRACK   - lock on a fish target in range
  THRUST  - the actual aim/swing; aim_score determines
            whether you skewer the fish or it bolts
  RECLAIM - retrieve the speared catch (counts as caught)

Aim formula: aim_score = (player_aim_skill + harpoon_quality)
- target_evasion. If aim_score >= ESCAPE_THRESHOLD the catch
succeeds. We surface a CatchResult with the species, weight,
and a flag for HQ (quality x triggered) catches.

Public surface
--------------
    SpearKind enum     SHORT_SPEAR / LONG_HARPOON / GAFFEHOOK
    Stage enum         IDLE / TRACK / THRUST / RECLAIM
    BiomeCatchTable
    CatchResult dataclass
    HarpoonFishing
        .start_cast(player_id, biome_id, spear_kind, now_seconds)
        .resolve_thrust(player_id, target_species,
                        player_aim_skill, target_evasion,
                        is_hq_roll)
        .session_for(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SpearKind(str, enum.Enum):
    SHORT_SPEAR = "short_spear"
    LONG_HARPOON = "long_harpoon"
    GAFFEHOOK = "gaffehook"


class Stage(str, enum.Enum):
    IDLE = "idle"
    TRACK = "track"
    THRUST = "thrust"
    RECLAIM = "reclaim"


_SPEAR_QUALITY: dict[SpearKind, int] = {
    SpearKind.SHORT_SPEAR: 5,
    SpearKind.LONG_HARPOON: 12,
    SpearKind.GAFFEHOOK: 20,
}

ESCAPE_THRESHOLD = 25


# biome -> (species_name, base_weight, evasion)
_CATCH_TABLES: dict[str, tuple[tuple[str, int, int], ...]] = {
    "tideplate_shallows": (
        ("blueglass_minnow", 2, 5),
        ("striped_seabass", 8, 12),
    ),
    "kelp_labyrinth": (
        ("kelp_eel", 18, 18),
        ("ribbon_serpentfish", 14, 22),
    ),
    "wreckage_graveyard": (
        ("wreckwood_crab", 22, 24),
        ("ghost_haddock", 30, 30),
    ),
    "abyss_trench": (
        ("abyssal_anglerfish", 60, 40),
        ("trench_lurker", 95, 55),
    ),
}


@dataclasses.dataclass
class _Session:
    player_id: str
    biome_id: str
    spear_kind: SpearKind
    stage: Stage = Stage.TRACK
    started_at: int = 0


@dataclasses.dataclass(frozen=True)
class CatchResult:
    accepted: bool
    species: t.Optional[str] = None
    weight: int = 0
    is_hq: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class HarpoonFishing:
    _sessions: dict[str, _Session] = dataclasses.field(default_factory=dict)

    @staticmethod
    def biome_catch_table(
        *, biome_id: str,
    ) -> tuple[tuple[str, int, int], ...]:
        return _CATCH_TABLES.get(biome_id, ())

    def start_cast(
        self, *, player_id: str,
        biome_id: str,
        spear_kind: SpearKind,
        now_seconds: int,
    ) -> bool:
        if not player_id or not biome_id:
            return False
        if biome_id not in _CATCH_TABLES:
            return False
        if spear_kind not in _SPEAR_QUALITY:
            return False
        self._sessions[player_id] = _Session(
            player_id=player_id,
            biome_id=biome_id,
            spear_kind=spear_kind,
            stage=Stage.TRACK,
            started_at=now_seconds,
        )
        return True

    def session_for(
        self, *, player_id: str,
    ) -> t.Optional[_Session]:
        return self._sessions.get(player_id)

    def resolve_thrust(
        self, *, player_id: str,
        target_species: str,
        player_aim_skill: int,
        target_evasion: int,
        is_hq_roll: bool,
    ) -> CatchResult:
        sess = self._sessions.get(player_id)
        if sess is None:
            return CatchResult(False, reason="no session")
        if sess.stage != Stage.TRACK:
            return CatchResult(False, reason="bad stage")
        if player_aim_skill < 0 or target_evasion < 0:
            return CatchResult(False, reason="invalid metrics")
        # find the species in the biome
        table = _CATCH_TABLES.get(sess.biome_id, ())
        match = next(
            (e for e in table if e[0] == target_species),
            None,
        )
        if match is None:
            return CatchResult(
                False, reason="species not in biome",
            )
        species, base_weight, _ = match
        quality = _SPEAR_QUALITY[sess.spear_kind]
        aim_score = player_aim_skill + quality - target_evasion
        sess.stage = Stage.THRUST
        if aim_score < ESCAPE_THRESHOLD:
            # fish escaped; session resets
            sess.stage = Stage.IDLE
            return CatchResult(
                accepted=True, species=species,
                weight=0, reason="escaped",
            )
        # success
        weight = base_weight
        if is_hq_roll:
            weight = int(weight * 1.5)
        sess.stage = Stage.RECLAIM
        return CatchResult(
            accepted=True, species=species,
            weight=weight, is_hq=is_hq_roll,
        )

    def total_biomes(self) -> int:
        return len(_CATCH_TABLES)


__all__ = [
    "SpearKind", "Stage",
    "CatchResult", "HarpoonFishing",
    "ESCAPE_THRESHOLD",
]
