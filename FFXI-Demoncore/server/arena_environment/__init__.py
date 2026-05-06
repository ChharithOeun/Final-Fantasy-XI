"""Arena environment — destructible feature registry for big battles.

Big battles aren't fought in empty rooms. They're fought
in PLACES — places with walls, floors, ceilings, ice
sheets, pillars, bridges, dams, balconies, ship decks.
Each of these features is a destructible HP bag with a
break threshold. When a feature breaks, it fires a
BreakEvent the rest of the environment system reacts to:
fall damage, swimming, debris stun, habitat disturbance.

Feature kinds
-------------
    WALL          - vertical surface; break exposes new
                    territory and disturbs whatever lives
                    on the other side
    FLOOR         - horizontal surface under the fight;
                    break drops everyone to a lower band
                    with fall damage
    CEILING       - horizontal surface above; break
                    rains debris (stun + crush damage)
    ICE_SHEET     - frozen water; break drops players
                    into freezing water (drown timer +
                    Frost Sleep risk)
    PILLAR        - column supporting a higher level;
                    break may cause partial floor cave-in
    BRIDGE        - thin connector; break may sever party
                    halves into two sub-fights
    DAM           - holds back water; break floods the
                    arena over N seconds, raising water
                    line by 1 depth band
    SHIP_HULL     - ship side; cannons & spells punch
                    holes; ship lists, players slide

Each feature has hp_max, current hp, a break_threshold
(typically hp <= 0 OR hp <= 25% for "cracked but holding"
two-stage breaks), and resistances per element so a fire
spell on an ice sheet melts it 3x faster than blunt
damage.

Public surface
--------------
    FeatureKind enum
    FeatureState enum (INTACT, DAMAGED, CRACKED, BROKEN)
    ArenaFeature dataclass (frozen)
    BreakResult dataclass (frozen)
    ArenaEnvironment
        .register_arena(arena_id, features)
        .feature(arena_id, feature_id) -> Optional[ArenaFeature]
        .features_for(arena_id) -> tuple[ArenaFeature, ...]
        .state(arena_id, feature_id) -> FeatureState
        .hp(arena_id, feature_id) -> int
        .apply_damage(arena_id, feature_id, amount,
                      element) -> BreakResult
        .reset(arena_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class FeatureKind(str, enum.Enum):
    WALL = "wall"
    FLOOR = "floor"
    CEILING = "ceiling"
    ICE_SHEET = "ice_sheet"
    PILLAR = "pillar"
    BRIDGE = "bridge"
    DAM = "dam"
    SHIP_HULL = "ship_hull"


class FeatureState(str, enum.Enum):
    INTACT = "intact"
    DAMAGED = "damaged"      # below 75%
    CRACKED = "cracked"      # below 25%, fires soft event
    BROKEN = "broken"        # 0 hp, fires hard event


# Two-stage break thresholds as fractions of hp_max
CRACK_THRESHOLD_PCT = 0.25
DAMAGED_THRESHOLD_PCT = 0.75


@dataclasses.dataclass(frozen=True)
class ArenaFeature:
    feature_id: str
    kind: FeatureKind
    hp_max: int
    band: int = 0                  # vertical band 0..4 in surface/sky/depth
    radius_yalms: int = 30         # blast radius when broken
    # element multipliers — e.g. fire vs ice = 3.0
    element_mults: dict[str, float] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class BreakResult:
    accepted: bool
    feature_id: str = ""
    new_state: FeatureState = FeatureState.INTACT
    crossed_crack: bool = False
    crossed_break: bool = False
    hp_remaining: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _FeatureState:
    feature: ArenaFeature
    hp: int


@dataclasses.dataclass
class ArenaEnvironment:
    _arenas: dict[str, dict[str, _FeatureState]] = dataclasses.field(
        default_factory=dict,
    )

    def register_arena(
        self, *, arena_id: str,
        features: t.Iterable[ArenaFeature],
    ) -> bool:
        if not arena_id or arena_id in self._arenas:
            return False
        feats = list(features)
        if not feats:
            return False
        ids = set()
        bag: dict[str, _FeatureState] = {}
        for f in feats:
            if not f.feature_id or f.feature_id in ids:
                return False
            if f.hp_max <= 0:
                return False
            ids.add(f.feature_id)
            bag[f.feature_id] = _FeatureState(feature=f, hp=f.hp_max)
        self._arenas[arena_id] = bag
        return True

    def feature(
        self, *, arena_id: str, feature_id: str,
    ) -> t.Optional[ArenaFeature]:
        a = self._arenas.get(arena_id)
        if a is None:
            return None
        s = a.get(feature_id)
        return s.feature if s else None

    def features_for(
        self, *, arena_id: str,
    ) -> tuple[ArenaFeature, ...]:
        a = self._arenas.get(arena_id, {})
        return tuple(s.feature for s in a.values())

    def hp(self, *, arena_id: str, feature_id: str) -> int:
        a = self._arenas.get(arena_id, {})
        s = a.get(feature_id)
        return s.hp if s else 0

    def state(
        self, *, arena_id: str, feature_id: str,
    ) -> FeatureState:
        a = self._arenas.get(arena_id, {})
        s = a.get(feature_id)
        if s is None:
            return FeatureState.INTACT
        return self._classify(s)

    @staticmethod
    def _classify(s: _FeatureState) -> FeatureState:
        if s.hp <= 0:
            return FeatureState.BROKEN
        pct = s.hp / s.feature.hp_max
        if pct <= CRACK_THRESHOLD_PCT:
            return FeatureState.CRACKED
        if pct <= DAMAGED_THRESHOLD_PCT:
            return FeatureState.DAMAGED
        return FeatureState.INTACT

    def apply_damage(
        self, *, arena_id: str, feature_id: str,
        amount: int, element: str = "neutral",
    ) -> BreakResult:
        if amount < 0:
            return BreakResult(False, reason="negative damage")
        a = self._arenas.get(arena_id)
        if a is None:
            return BreakResult(False, reason="unknown arena")
        s = a.get(feature_id)
        if s is None:
            return BreakResult(False, reason="unknown feature")
        if s.hp <= 0:
            return BreakResult(False, reason="already broken")
        before_state = self._classify(s)
        mult = s.feature.element_mults.get(element, 1.0)
        scaled = max(0, int(amount * mult))
        s.hp = max(0, s.hp - scaled)
        after_state = self._classify(s)
        return BreakResult(
            accepted=True,
            feature_id=feature_id,
            new_state=after_state,
            crossed_crack=(
                before_state in (FeatureState.INTACT, FeatureState.DAMAGED)
                and after_state in (FeatureState.CRACKED, FeatureState.BROKEN)
            ),
            crossed_break=(
                before_state != FeatureState.BROKEN
                and after_state == FeatureState.BROKEN
            ),
            hp_remaining=s.hp,
        )

    def reset(self, *, arena_id: str) -> bool:
        a = self._arenas.get(arena_id)
        if a is None:
            return False
        for s in a.values():
            s.hp = s.feature.hp_max
        return True


__all__ = [
    "FeatureKind", "FeatureState", "ArenaFeature",
    "BreakResult", "ArenaEnvironment",
    "CRACK_THRESHOLD_PCT", "DAMAGED_THRESHOLD_PCT",
]
