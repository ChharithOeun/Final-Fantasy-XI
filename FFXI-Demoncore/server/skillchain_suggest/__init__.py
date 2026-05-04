"""Skillchain suggest — UI hints for next WS in a chain.

Reads the live chain context (the previous WS's elemental
properties) and produces a ranked list of WS candidates a
player has access to that could CLOSE or EXTEND the chain. The
suggestion includes the resulting chain element and the chain
TIER (Lv1 detonation, Lv2 fragmentation, etc.).

Catalog of element pairs (subset of canonical FFXI pairs):
  fire + thunder       -> fusion
  earth + dark         -> gravitation
  ice + water          -> distortion
  wind + light         -> fragmentation
  fire + earth         -> liquefaction
  thunder + wind       -> impaction
  ...

Public surface
--------------
    Element enum
    ChainOutcome dataclass
    WSCandidate dataclass
    Suggestion dataclass
    SkillchainSuggest
        .register_ws(ws_id, label, primary_element, secondary,
                     min_tp, level_required)
        .grant_ws(player_id, ws_id, current_tp, level)
        .observe_chain(player_id, prev_ws_id) — opens the window
        .clear_window(player_id)
        .suggestions_for(player_id) -> tuple[Suggestion]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Element(str, enum.Enum):
    FIRE = "fire"
    ICE = "ice"
    WIND = "wind"
    EARTH = "earth"
    LIGHTNING = "lightning"
    WATER = "water"
    LIGHT = "light"
    DARK = "dark"


class ChainTier(str, enum.Enum):
    LV1 = "lv1"     # detonation/scission etc
    LV2 = "lv2"     # fusion/distortion etc
    LV3 = "lv3"     # darkness/light
    NONE = "none"


@dataclasses.dataclass(frozen=True)
class ChainOutcome:
    chain_element: str
    tier: ChainTier


# Pair definitions. Symmetric: (a,b) and (b,a) both yield the
# same outcome. We keep a "raw" list of unordered pairs and
# build the canonical lookup dict from it once at import time.
_RAW_PAIRS: tuple[
    tuple[Element, Element, str, "ChainTier"], ...,
] = (
    (Element.FIRE, Element.LIGHTNING, "fusion", None),
    (Element.EARTH, Element.DARK, "gravitation", None),
    (Element.ICE, Element.WATER, "distortion", None),
    (Element.WIND, Element.LIGHT, "fragmentation", None),
    (Element.FIRE, Element.EARTH, "liquefaction", None),
    (Element.LIGHTNING, Element.WIND, "impaction", None),
    (Element.ICE, Element.EARTH, "scission", None),
    (Element.WATER, Element.WIND, "reverberation", None),
    (Element.DARK, Element.LIGHT, "darkness", None),
)


def _canon_pair(
    a: Element, b: Element,
) -> tuple[Element, Element]:
    return tuple(sorted((a, b), key=lambda e: e.value))


# Build the canonical lookup map.
_PAIRS: dict[tuple[Element, Element], ChainOutcome] = {}
_TIER_FOR_LABEL: dict[str, ChainTier] = {
    "fusion": ChainTier.LV2,
    "gravitation": ChainTier.LV2,
    "distortion": ChainTier.LV2,
    "fragmentation": ChainTier.LV2,
    "liquefaction": ChainTier.LV1,
    "impaction": ChainTier.LV1,
    "scission": ChainTier.LV1,
    "reverberation": ChainTier.LV1,
    "darkness": ChainTier.LV3,
}
for _a, _b, _label, _ in _RAW_PAIRS:
    _PAIRS[_canon_pair(_a, _b)] = ChainOutcome(
        _label, _TIER_FOR_LABEL[_label],
    )


@dataclasses.dataclass(frozen=True)
class WSDef:
    ws_id: str
    label: str
    primary_element: Element
    secondary_element: t.Optional[Element]
    min_tp: int
    level_required: int


@dataclasses.dataclass(frozen=True)
class Suggestion:
    ws_id: str
    label: str
    chain_element: str
    tier: ChainTier
    feasible: bool                 # have TP + level
    needed_tp: int


@dataclasses.dataclass
class _Player:
    player_id: str
    granted: set[str] = dataclasses.field(
        default_factory=set,
    )
    current_tp: int = 0
    level: int = 1
    last_ws_id: t.Optional[str] = None


@dataclasses.dataclass
class SkillchainSuggest:
    _ws: dict[str, WSDef] = dataclasses.field(
        default_factory=dict,
    )
    _players: dict[str, _Player] = dataclasses.field(
        default_factory=dict,
    )

    def register_ws(
        self, *, ws_id: str, label: str,
        primary_element: Element,
        secondary_element: t.Optional[Element] = None,
        min_tp: int = 1000,
        level_required: int = 1,
    ) -> bool:
        if ws_id in self._ws:
            return False
        self._ws[ws_id] = WSDef(
            ws_id=ws_id, label=label,
            primary_element=primary_element,
            secondary_element=secondary_element,
            min_tp=min_tp,
            level_required=level_required,
        )
        return True

    def _player(self, player_id: str) -> _Player:
        p = self._players.get(player_id)
        if p is None:
            p = _Player(player_id=player_id)
            self._players[player_id] = p
        return p

    def grant_ws(
        self, *, player_id: str, ws_id: str,
        current_tp: int = 0, level: int = 1,
    ) -> bool:
        if ws_id not in self._ws:
            return False
        p = self._player(player_id)
        p.granted.add(ws_id)
        p.current_tp = current_tp
        p.level = level
        return True

    def update_state(
        self, *, player_id: str,
        current_tp: t.Optional[int] = None,
        level: t.Optional[int] = None,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None:
            return False
        if current_tp is not None:
            p.current_tp = current_tp
        if level is not None:
            p.level = level
        return True

    def observe_chain(
        self, *, player_id: str, prev_ws_id: str,
    ) -> bool:
        if prev_ws_id not in self._ws:
            return False
        p = self._player(player_id)
        p.last_ws_id = prev_ws_id
        return True

    def clear_window(
        self, *, player_id: str,
    ) -> bool:
        p = self._players.get(player_id)
        if p is None or p.last_ws_id is None:
            return False
        p.last_ws_id = None
        return True

    def _outcome_for(
        self, prev: WSDef, candidate: WSDef,
    ) -> t.Optional[ChainOutcome]:
        """Try the candidate's primary first, then secondary,
        against the prev's primary or secondary. Highest tier
        wins on multi-match."""
        prev_elements = [prev.primary_element]
        if prev.secondary_element is not None:
            prev_elements.append(prev.secondary_element)
        cand_elements = [candidate.primary_element]
        if candidate.secondary_element is not None:
            cand_elements.append(candidate.secondary_element)
        best: t.Optional[ChainOutcome] = None
        for pe in prev_elements:
            for ce in cand_elements:
                if pe == ce:
                    continue
                key = _canon_pair(pe, ce)
                outcome = _PAIRS.get(key)
                if outcome is None:
                    continue
                if best is None:
                    best = outcome
                else:
                    rank = {
                        ChainTier.NONE: 0,
                        ChainTier.LV1: 1,
                        ChainTier.LV2: 2,
                        ChainTier.LV3: 3,
                    }
                    if rank[outcome.tier] > rank[best.tier]:
                        best = outcome
        return best

    def suggestions_for(
        self, *, player_id: str,
    ) -> tuple[Suggestion, ...]:
        p = self._players.get(player_id)
        if p is None or p.last_ws_id is None:
            return ()
        prev = self._ws.get(p.last_ws_id)
        if prev is None:
            return ()
        out: list[Suggestion] = []
        for ws_id in p.granted:
            if ws_id == p.last_ws_id:
                continue
            candidate = self._ws[ws_id]
            outcome = self._outcome_for(prev, candidate)
            if outcome is None:
                continue
            feasible = (
                p.current_tp >= candidate.min_tp
                and p.level >= candidate.level_required
            )
            needed = max(
                0,
                candidate.min_tp - p.current_tp,
            )
            out.append(Suggestion(
                ws_id=ws_id, label=candidate.label,
                chain_element=outcome.chain_element,
                tier=outcome.tier,
                feasible=feasible,
                needed_tp=needed,
            ))
        # Higher tier first; feasible before unfeasible; lower
        # needed_tp before higher; deterministic by ws_id.
        order = {
            ChainTier.LV3: 0,
            ChainTier.LV2: 1,
            ChainTier.LV1: 2,
            ChainTier.NONE: 3,
        }
        out.sort(
            key=lambda s: (
                order[s.tier],
                0 if s.feasible else 1,
                s.needed_tp,
                s.ws_id,
            ),
        )
        return tuple(out)

    def total_ws(self) -> int:
        return len(self._ws)


__all__ = [
    "Element", "ChainTier",
    "ChainOutcome", "WSDef", "Suggestion",
    "SkillchainSuggest",
]
