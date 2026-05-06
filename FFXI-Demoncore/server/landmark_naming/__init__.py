"""Landmark naming — first discoverers can name unnamed places.

Walk into a cave nobody's ever recorded. Spelunk to the
end. The cartographer guild grants you the right to name
the place. The chronicle records that you did, the map
shows your name, NPCs in the area mention "the famous
[name] cave."

Names are filtered:
    - empty / blank → reject
    - too long (>40 chars) → reject
    - contains profanity (per a configurable filter) → reject
    - duplicates an existing landmark name → reject
    - claimant doesn't have ownership of the discovery → reject

Once accepted, a name is final unless explicitly rescinded
by an admin (e.g. for harassment). Re-naming by the same
discoverer is not allowed — first impression sticks.

Public surface
--------------
    NamingOutcome enum
    NamedLandmark dataclass (frozen)
    LandmarkNamingRegistry
        .register_discovery(landmark_id, zone_id,
                            discoverer_id, discovered_at)
            -> bool
        .propose_name(landmark_id, proposed_name,
                      proposer_id, proposed_at,
                      profanity_filter) -> NamingOutcome
        .name_for(landmark_id) -> Optional[str]
        .landmarks_named_by(player_id)
            -> tuple[NamedLandmark, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NamingOutcome(str, enum.Enum):
    ACCEPTED = "accepted"
    REJECT_BLANK = "reject_blank"
    REJECT_TOO_LONG = "reject_too_long"
    REJECT_PROFANITY = "reject_profanity"
    REJECT_DUPLICATE = "reject_duplicate"
    REJECT_NOT_DISCOVERER = "reject_not_discoverer"
    REJECT_ALREADY_NAMED = "reject_already_named"
    REJECT_UNKNOWN_LANDMARK = "reject_unknown_landmark"


MAX_NAME_LENGTH = 40


@dataclasses.dataclass(frozen=True)
class NamedLandmark:
    landmark_id: str
    zone_id: str
    discoverer_id: str
    discovered_at: int
    name: str
    named_at: int


@dataclasses.dataclass
class _LandmarkSeed:
    landmark_id: str
    zone_id: str
    discoverer_id: str
    discovered_at: int
    name: t.Optional[str] = None
    named_at: t.Optional[int] = None


@dataclasses.dataclass
class LandmarkNamingRegistry:
    _landmarks: dict[str, _LandmarkSeed] = dataclasses.field(
        default_factory=dict,
    )
    # lowercase name -> landmark_id (for duplicate check)
    _name_index: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def register_discovery(
        self, *, landmark_id: str, zone_id: str,
        discoverer_id: str, discovered_at: int,
    ) -> bool:
        if not landmark_id or not zone_id or not discoverer_id:
            return False
        if landmark_id in self._landmarks:
            return False
        self._landmarks[landmark_id] = _LandmarkSeed(
            landmark_id=landmark_id, zone_id=zone_id,
            discoverer_id=discoverer_id,
            discovered_at=discovered_at,
        )
        return True

    def propose_name(
        self, *, landmark_id: str, proposed_name: str,
        proposer_id: str, proposed_at: int,
        profanity_filter: t.Iterable[str] = (),
    ) -> NamingOutcome:
        seed = self._landmarks.get(landmark_id)
        if seed is None:
            return NamingOutcome.REJECT_UNKNOWN_LANDMARK
        if seed.name is not None:
            return NamingOutcome.REJECT_ALREADY_NAMED
        if seed.discoverer_id != proposer_id:
            return NamingOutcome.REJECT_NOT_DISCOVERER

        clean = proposed_name.strip()
        if not clean:
            return NamingOutcome.REJECT_BLANK
        if len(clean) > MAX_NAME_LENGTH:
            return NamingOutcome.REJECT_TOO_LONG

        lowered = clean.lower()
        # profanity check: substring match against any filter word
        for bad in profanity_filter:
            if not bad or not bad.strip():
                continue
            if bad.strip().lower() in lowered:
                return NamingOutcome.REJECT_PROFANITY

        if lowered in self._name_index:
            return NamingOutcome.REJECT_DUPLICATE

        seed.name = clean
        seed.named_at = proposed_at
        self._name_index[lowered] = landmark_id
        return NamingOutcome.ACCEPTED

    def name_for(
        self, *, landmark_id: str,
    ) -> t.Optional[str]:
        seed = self._landmarks.get(landmark_id)
        if seed is None:
            return None
        return seed.name

    def landmarks_named_by(
        self, *, player_id: str,
    ) -> tuple[NamedLandmark, ...]:
        out: list[NamedLandmark] = []
        for seed in self._landmarks.values():
            if seed.discoverer_id != player_id:
                continue
            if seed.name is None or seed.named_at is None:
                continue
            out.append(NamedLandmark(
                landmark_id=seed.landmark_id,
                zone_id=seed.zone_id,
                discoverer_id=seed.discoverer_id,
                discovered_at=seed.discovered_at,
                name=seed.name, named_at=seed.named_at,
            ))
        return tuple(out)

    def total_named(self) -> int:
        return sum(
            1 for s in self._landmarks.values()
            if s.name is not None
        )


__all__ = [
    "NamingOutcome", "NamedLandmark", "MAX_NAME_LENGTH",
    "LandmarkNamingRegistry",
]
