"""Player tell journal — learned tell→ability associations.

Players accumulate knowledge over many fights. Every time
a player WITNESSES a tell precede an ability they survive
to see, the journal records the (tell, ability) pair.
Once they've seen the same pairing N times, they LEARN
the association — and the world starts displaying the
predicted ability_id label next to the tell, even WITHOUT
visibility.

This is the third tier of the "no visibility, no overlay"
design:
    - everyone sees the tell (boss_ability_tells)
    - patient players develop a hunch ("dust always meant
      slam")
    - learned players SEE the predicted ability name
      ("dust falling — Apocalyptic Slam incoming")

Confidence levels:
    SEEN_ONCE      1 observation; pure trivia
    HUNCH          2-4 observations; "I think this means…"
    PATTERNED      5-9 observations; the journal labels
                   the prediction with confidence%
    LEARNED       10+ observations; the engine displays
                   the predicted ability name as a stable
                   prediction
    DEFEATED      Marked once the player kills the boss
                  using prediction; bonus +20% confidence
                  toward this boss's tells

Public surface
--------------
    Confidence enum
    Observation dataclass (frozen)
    Prediction dataclass (frozen)
    PlayerTellJournal
        .observe(player_id, boss_id, ability_id, tell)
        .predictions_for_tell(player_id, boss_id, tell)
            -> tuple[Prediction, ...]
        .confidence(player_id, boss_id, ability_id, tell)
            -> Confidence
        .mark_defeat(player_id, boss_id)
        .total_observations(player_id) -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.boss_ability_tells import TellKind


class Confidence(str, enum.Enum):
    UNKNOWN = "unknown"
    SEEN_ONCE = "seen_once"
    HUNCH = "hunch"
    PATTERNED = "patterned"
    LEARNED = "learned"
    DEFEATED = "defeated"


# Thresholds (count of observations)
HUNCH_THRESHOLD = 2
PATTERNED_THRESHOLD = 5
LEARNED_THRESHOLD = 10
DEFEATED_BONUS_OBSERVATIONS = 5   # killing the boss is worth +5
                                    # observations toward all its
                                    # tell pairs


@dataclasses.dataclass(frozen=True)
class Observation:
    player_id: str
    boss_id: str
    ability_id: str
    tell: TellKind


@dataclasses.dataclass(frozen=True)
class Prediction:
    boss_id: str
    ability_id: str
    tell: TellKind
    observations: int
    confidence: Confidence


@dataclasses.dataclass
class PlayerTellJournal:
    # player_id -> (boss_id, tell, ability_id) -> obs count
    _obs: dict[str, dict[tuple[str, TellKind, str], int]] = (
        dataclasses.field(default_factory=dict)
    )
    # player_id -> set[boss_id]
    _defeated: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )

    def observe(
        self, *, player_id: str, boss_id: str,
        ability_id: str, tell: TellKind,
    ) -> bool:
        if not player_id or not boss_id or not ability_id:
            return False
        bag = self._obs.setdefault(player_id, {})
        key = (boss_id, tell, ability_id)
        bag[key] = bag.get(key, 0) + 1
        return True

    def mark_defeat(
        self, *, player_id: str, boss_id: str,
    ) -> bool:
        if not player_id or not boss_id:
            return False
        self._defeated.setdefault(player_id, set()).add(boss_id)
        return True

    def has_defeated(
        self, *, player_id: str, boss_id: str,
    ) -> bool:
        return boss_id in self._defeated.get(player_id, set())

    def _count(
        self, *, player_id: str, boss_id: str,
        tell: TellKind, ability_id: str,
    ) -> int:
        raw = self._obs.get(
            player_id, {},
        ).get((boss_id, tell, ability_id), 0)
        if self.has_defeated(player_id=player_id, boss_id=boss_id):
            raw += DEFEATED_BONUS_OBSERVATIONS
        return raw

    def confidence(
        self, *, player_id: str, boss_id: str,
        ability_id: str, tell: TellKind,
    ) -> Confidence:
        n = self._count(
            player_id=player_id, boss_id=boss_id,
            tell=tell, ability_id=ability_id,
        )
        if n <= 0:
            return Confidence.UNKNOWN
        if (self.has_defeated(player_id=player_id, boss_id=boss_id)
                and n >= LEARNED_THRESHOLD):
            return Confidence.DEFEATED
        if n >= LEARNED_THRESHOLD:
            return Confidence.LEARNED
        if n >= PATTERNED_THRESHOLD:
            return Confidence.PATTERNED
        if n >= HUNCH_THRESHOLD:
            return Confidence.HUNCH
        return Confidence.SEEN_ONCE

    def predictions_for_tell(
        self, *, player_id: str, boss_id: str, tell: TellKind,
    ) -> tuple[Prediction, ...]:
        bag = self._obs.get(player_id, {})
        out: list[Prediction] = []
        for (b, t_, ability), count in bag.items():
            if b != boss_id or t_ != tell:
                continue
            obs = count
            if self.has_defeated(player_id=player_id, boss_id=boss_id):
                obs += DEFEATED_BONUS_OBSERVATIONS
            out.append(Prediction(
                boss_id=boss_id, ability_id=ability,
                tell=tell, observations=obs,
                confidence=self.confidence(
                    player_id=player_id, boss_id=boss_id,
                    ability_id=ability, tell=tell,
                ),
            ))
        # rank by observations desc — most likely prediction first
        out.sort(key=lambda p: p.observations, reverse=True)
        return tuple(out)

    def total_observations(self, *, player_id: str) -> int:
        return sum(self._obs.get(player_id, {}).values())

    def known_bosses(self, *, player_id: str) -> tuple[str, ...]:
        bag = self._obs.get(player_id, {})
        return tuple(sorted({b for (b, _, _) in bag.keys()}))


__all__ = [
    "Confidence", "Observation", "Prediction",
    "PlayerTellJournal",
    "HUNCH_THRESHOLD", "PATTERNED_THRESHOLD",
    "LEARNED_THRESHOLD", "DEFEATED_BONUS_OBSERVATIONS",
]
