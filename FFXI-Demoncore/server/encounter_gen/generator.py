"""Encounter generator.

Per `MOB_CLASS_LIBRARY.md` + `COMBAT_TEMPO.md` (10× mob density). Given
a zone + party level + party size, produces a balanced spawn plan
respecting:

- Zone-appropriate mob_class palette (Bastok-aligned zones favor
  Quadav, Sandy zones favor Yagudo, Windy zones favor Goblin/Yagudo,
  etc — canonical FFXI bestiary distribution)
- Party power-budget tuning (target challenge = "decent")
- Element-affinity diversity (don't spawn 6 fire-aligned mobs together)
- Composition rules (max 1 healer per pack; never two RL-policy
  named NMs in the same pack; etc)

Pure-Python; no I/O. The orchestrator + LSB call this on zone-load
or repop-tick.
"""
from __future__ import annotations

import dataclasses
import enum
import random
import typing as t


# ----------------------------------------------------------------------
# Inputs / outputs
# ----------------------------------------------------------------------

class ChallengeTarget(str, enum.Enum):
    EASY_PREY = "easy_prey"
    DECENT_CHALLENGE = "decent_challenge"
    TOUGH = "tough"
    INCREDIBLY_TOUGH = "incredibly_tough"


@dataclasses.dataclass
class EncounterRequest:
    zone: str                   # "south_gustaberg", "konschtat_highlands"
    party_avg_level: int = 30
    party_size: int = 1
    challenge: ChallengeTarget = ChallengeTarget.DECENT_CHALLENGE
    seed: int = 0               # deterministic generation when set
    target_pack_count: int = 8  # how many discrete packs to spawn
    boss_pack_chance: float = 0.05  # 5% chance one pack is boss-tier


@dataclasses.dataclass
class SpawnEntry:
    mob_class: str
    level: int
    spawn_position_hint: str = "random"  # zone-relative; LSB resolves
    is_named_NM: bool = False
    is_pack_leader: bool = False


@dataclasses.dataclass
class EncounterPlan:
    zone: str
    spawns: list[SpawnEntry]
    pack_count: int
    avg_level: float
    estimated_party_difficulty: ChallengeTarget
    seed: int


# ----------------------------------------------------------------------
# Zone bestiary palettes (which mob classes belong where)
# ----------------------------------------------------------------------

# Per-zone mob_class weights. Sum of weights per zone is the spawn
# distribution. Add new zones as we author their content.
ZONE_PALETTES: dict[str, dict[str, float]] = {
    # Bastok-aligned zones
    "bastok_mines":      {"goblin_pickpocket": 1.0, "goblin_smithy": 0.3,
                          "rat": 2.0},
    "south_gustaberg":   {"goblin_pickpocket": 1.0, "bee_soldier": 1.0,
                          "skeleton_warrior": 0.5},
    "konschtat_highlands":{"goblin_pickpocket": 0.5, "bee_soldier": 1.0,
                           "skeleton_warrior": 1.0,
                           "orc_footsoldier": 1.5,
                           "wolf": 1.0},
    "north_gustaberg":   {"goblin_pickpocket": 1.0, "skeleton_warrior": 1.0},
    "korroloka_tunnel":  {"quadav_helmsman": 2.0, "skeleton_warrior": 1.5,
                          "bee_soldier": 0.5},

    # Sandy-aligned
    "northern_san_doria":{"orc_footsoldier": 0.0},   # safe city
    "ronfaure_west":     {"orc_footsoldier": 1.5, "wolf": 1.0,
                          "bee_soldier": 1.0},
    "davoi":             {"orc_footsoldier": 3.0,
                          "yagudo_cleric": 0.0},   # not Yagudo zone

    # Windy-aligned
    "windurst_woods":    {"yagudo_cleric": 0.0},   # safe city
    "tahrongi_canyon":   {"yagudo_cleric": 1.0, "goblin_pickpocket": 1.0,
                          "bee_soldier": 1.5},
    "outer_horutoto":    {"yagudo_cleric": 1.5, "goblin_pickpocket": 0.5,
                          "skeleton_warrior": 1.0},

    # Beadeaux (Quadav stronghold) — CONNECTING zone for the canonical
    # Quadav arc
    "beadeaux":          {"quadav_helmsman": 3.0,
                          "skeleton_warrior": 0.5},

    # Aqueducts / cave zones (Naga)
    "phomiuna_aqueducts":{"naga_renja": 2.0, "tonberry_stalker": 0.5,
                          "skeleton_warrior": 1.0},

    # Coastal / underwater (Sahagin)
    "valkurm_dunes":     {"sahagin_swordsman": 0.5, "bee_soldier": 1.5,
                          "goblin_pickpocket": 1.0},
    "sea_serpent_grotto":{"sahagin_swordsman": 3.0,
                          "tonberry_stalker": 1.0},
}


# Default mob class level ranges (read from MOB_CLASS_LIBRARY entries
# where authored)
DEFAULT_LEVEL_RANGES: dict[str, tuple[int, int]] = {
    "goblin_pickpocket":   (5,  15),
    "goblin_smithy":       (3,  7),
    "rat":                 (1,  5),
    "bee_soldier":         (8,  18),
    "skeleton_warrior":    (25, 40),
    "orc_footsoldier":     (10, 20),
    "wolf":                (12, 25),
    "quadav_helmsman":     (18, 28),
    "yagudo_cleric":       (20, 30),
    "naga_renja":          (25, 40),
    "tonberry_stalker":    (30, 45),
    "sahagin_swordsman":   (22, 35),
}


# ----------------------------------------------------------------------
# Pack composition rules
# ----------------------------------------------------------------------

# Mob classes that count as "healers" — at most one per pack
HEALER_CLASSES = {"yagudo_cleric"}

# Boss-tier classes that should be solo
BOSS_TIER_CLASSES = {"goblin_smithy"}


def _challenge_level_offset(challenge: ChallengeTarget) -> tuple[int, int]:
    """How many levels above/below the party's average to target."""
    return {
        ChallengeTarget.EASY_PREY:           (-5, -2),
        ChallengeTarget.DECENT_CHALLENGE:    (-2, +2),
        ChallengeTarget.TOUGH:               (+2, +5),
        ChallengeTarget.INCREDIBLY_TOUGH:    (+5, +10),
    }[challenge]


# ----------------------------------------------------------------------
# Generator
# ----------------------------------------------------------------------

class EncounterGenerator:
    def __init__(self):
        pass

    def generate(self, req: EncounterRequest) -> EncounterPlan:
        rng = random.Random(req.seed) if req.seed else random.Random()

        if req.zone not in ZONE_PALETTES:
            return EncounterPlan(
                zone=req.zone, spawns=[], pack_count=0,
                avg_level=req.party_avg_level,
                estimated_party_difficulty=req.challenge,
                seed=req.seed,
            )

        palette = {k: v for k, v in ZONE_PALETTES[req.zone].items() if v > 0}
        if not palette:
            return EncounterPlan(
                zone=req.zone, spawns=[], pack_count=0,
                avg_level=req.party_avg_level,
                estimated_party_difficulty=req.challenge,
                seed=req.seed,
            )

        # Per COMBAT_TEMPO.md: 10x more mobs per zone than canonical FFXI.
        # We over-populate the spawn count.
        target_pack_count = max(1, int(req.target_pack_count * 1.0))
        spawns: list[SpawnEntry] = []
        boss_spawned = False

        for pack_idx in range(target_pack_count):
            spawn_boss_this_pack = (
                not boss_spawned
                and rng.random() < req.boss_pack_chance
            )
            pack_spawns = self._make_pack(
                palette=palette, party_level=req.party_avg_level,
                party_size=req.party_size, challenge=req.challenge,
                rng=rng, allow_boss=spawn_boss_this_pack,
            )
            if any(s.is_named_NM for s in pack_spawns):
                boss_spawned = True
            spawns.extend(pack_spawns)

        # Element diversity: if pack has too many of one element-aligned
        # class, swap some out — this is a coarse heuristic; production
        # version pulls element from the mob_class YAML
        spawns = self._enforce_element_diversity(spawns, palette, rng)

        avg = (sum(s.level for s in spawns) / len(spawns)) if spawns else 0
        return EncounterPlan(
            zone=req.zone,
            spawns=spawns,
            pack_count=target_pack_count,
            avg_level=avg,
            estimated_party_difficulty=req.challenge,
            seed=req.seed,
        )

    def _make_pack(self, *, palette: dict[str, float],
                    party_level: int, party_size: int,
                    challenge: ChallengeTarget, rng: random.Random,
                    allow_boss: bool) -> list[SpawnEntry]:
        # Pack size based on party size + challenge tier
        if challenge == ChallengeTarget.INCREDIBLY_TOUGH:
            pack_size = max(1, party_size + 2)
        elif challenge == ChallengeTarget.TOUGH:
            pack_size = max(1, party_size + 1)
        elif challenge == ChallengeTarget.DECENT_CHALLENGE:
            pack_size = party_size
        else:
            pack_size = max(1, party_size - 1)

        # Boss spawns are solo
        if allow_boss:
            boss_class = self._pick_boss_class(palette, rng)
            if boss_class:
                lo, hi = DEFAULT_LEVEL_RANGES.get(boss_class, (party_level, party_level))
                lvl = rng.randint(max(1, lo), max(lo, hi))
                return [SpawnEntry(
                    mob_class=boss_class, level=lvl,
                    is_named_NM=True, is_pack_leader=True,
                )]

        spawns: list[SpawnEntry] = []
        healer_added = False
        for i in range(pack_size):
            cls = self._pick_class(palette, rng,
                                    allow_healer=not healer_added,
                                    allow_boss=False)
            if cls is None:
                break
            if cls in HEALER_CLASSES:
                healer_added = True
            level = self._pick_level(cls, party_level, challenge, rng)
            spawns.append(SpawnEntry(
                mob_class=cls, level=level,
                is_pack_leader=(i == 0),
            ))
        return spawns

    def _pick_class(self, palette: dict[str, float], rng: random.Random,
                     *, allow_healer: bool, allow_boss: bool) -> t.Optional[str]:
        candidates = []
        weights = []
        for cls, w in palette.items():
            if not allow_healer and cls in HEALER_CLASSES:
                continue
            if not allow_boss and cls in BOSS_TIER_CLASSES:
                continue
            candidates.append(cls)
            weights.append(w)
        if not candidates:
            return None
        return rng.choices(candidates, weights=weights, k=1)[0]

    def _pick_boss_class(self, palette: dict[str, float],
                          rng: random.Random) -> t.Optional[str]:
        candidates = [cls for cls in palette if cls in BOSS_TIER_CLASSES]
        if not candidates:
            return None
        return rng.choice(candidates)

    def _pick_level(self, cls: str, party_level: int,
                     challenge: ChallengeTarget,
                     rng: random.Random) -> int:
        # Use the mob class's default range, clamped to challenge offset
        lo, hi = DEFAULT_LEVEL_RANGES.get(cls, (party_level, party_level))
        offset_lo, offset_hi = _challenge_level_offset(challenge)
        target_lo = max(lo, party_level + offset_lo)
        target_hi = min(hi, party_level + offset_hi)
        if target_hi < target_lo:
            # Offset target outside class range; clamp to class range
            return rng.randint(max(1, lo), max(lo, hi))
        return rng.randint(max(1, target_lo), max(target_lo, target_hi))

    def _enforce_element_diversity(self, spawns: list[SpawnEntry],
                                     palette: dict[str, float],
                                     rng: random.Random) -> list[SpawnEntry]:
        # Coarse heuristic: count occurrences per mob_class. If any one
        # class dominates >50% of the spawn list, swap some out.
        if len(spawns) < 4:
            return spawns
        counts: dict[str, int] = {}
        for s in spawns:
            counts[s.mob_class] = counts.get(s.mob_class, 0) + 1
        threshold = max(2, len(spawns) // 2)
        for cls, c in counts.items():
            if c > threshold:
                # Find different alternatives in the palette
                alternatives = [k for k in palette if k != cls and k not in BOSS_TIER_CLASSES]
                if not alternatives:
                    continue
                # Replace the last (c - threshold) occurrences
                excess = c - threshold
                replaced = 0
                for i in range(len(spawns) - 1, -1, -1):
                    if spawns[i].mob_class == cls and replaced < excess:
                        new_cls = rng.choice(alternatives)
                        spawns[i] = SpawnEntry(
                            mob_class=new_cls,
                            level=spawns[i].level,
                            spawn_position_hint=spawns[i].spawn_position_hint,
                            is_named_NM=spawns[i].is_named_NM,
                            is_pack_leader=spawns[i].is_pack_leader,
                        )
                        replaced += 1
        return spawns
