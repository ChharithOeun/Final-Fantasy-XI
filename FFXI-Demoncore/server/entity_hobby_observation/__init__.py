"""Entity hobby observation — players witness NPCs at hobbies.

When a player passes by an entity that's currently engaged in
a hobby (per entity_hobbies/), an observation can be recorded.
The first time a player witnesses a particular (entity, hobby)
pair, they earn discovery_fame proportional to whether the
pairing is rare-for-class. Subsequent sightings of the same
pair don't grant fame but still go into the witness log,
which gossip systems use to spread rumors.

Special hooks
-------------
- Rare-for-class sightings (e.g., a Tarutaru WEIGHTLIFTING)
  unlock dialog branches with that entity ("...wait, you saw
  me lifting? Don't tell my linkshell, please.")
- Aggregate witness counts feed reputation_cascade — entities
  whose hobbies become widely known shift their public
  identity in NPC gossip layers.

Public surface
--------------
    Observation dataclass (frozen)
    HobbyObservationSystem
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.entity_hobbies import HobbyKind


_RARE_DISCOVERY_FAME = 25
_NORMAL_DISCOVERY_FAME = 5


@dataclasses.dataclass(frozen=True)
class Observation:
    observation_id: str
    witness_id: str
    entity_id: str
    hobby: HobbyKind
    zone_id: str
    observed_day: int
    fame_earned: int
    is_rare: bool


@dataclasses.dataclass
class _WState:
    discovered_pairs: set[tuple[str, str]] = (
        dataclasses.field(default_factory=set)
    )
    total_fame: int = 0


@dataclasses.dataclass
class HobbyObservationSystem:
    _observations: dict[str, Observation] = (
        dataclasses.field(default_factory=dict)
    )
    _witnesses: dict[str, _WState] = dataclasses.field(
        default_factory=dict,
    )
    _entity_witness_counts: dict[str, int] = (
        dataclasses.field(default_factory=dict)
    )
    _next: int = 1

    def record_observation(
        self, *, witness_id: str, entity_id: str,
        hobby: HobbyKind, zone_id: str,
        observed_day: int, is_rare: bool,
    ) -> t.Optional[str]:
        if not witness_id or not entity_id:
            return None
        if witness_id == entity_id:
            return None
        if not zone_id:
            return None
        if observed_day < 0:
            return None
        if witness_id not in self._witnesses:
            self._witnesses[witness_id] = _WState()
        st = self._witnesses[witness_id]
        pair = (entity_id, hobby.value)
        is_first = pair not in st.discovered_pairs
        fame = 0
        if is_first:
            fame = (
                _RARE_DISCOVERY_FAME if is_rare
                else _NORMAL_DISCOVERY_FAME
            )
            st.discovered_pairs.add(pair)
            st.total_fame += fame
        oid = f"obs_{self._next}"
        self._next += 1
        self._observations[oid] = Observation(
            observation_id=oid, witness_id=witness_id,
            entity_id=entity_id, hobby=hobby,
            zone_id=zone_id,
            observed_day=observed_day,
            fame_earned=fame, is_rare=is_rare,
        )
        self._entity_witness_counts[entity_id] = (
            self._entity_witness_counts.get(entity_id, 0)
            + 1
        )
        return oid

    def discovered_pairs(
        self, *, witness_id: str,
    ) -> list[tuple[str, str]]:
        st = self._witnesses.get(witness_id)
        if st is None:
            return []
        return sorted(st.discovered_pairs)

    def total_fame(
        self, *, witness_id: str,
    ) -> int:
        st = self._witnesses.get(witness_id)
        return 0 if st is None else st.total_fame

    def entity_public_renown(
        self, *, entity_id: str,
    ) -> int:
        """How many witness events involve this
        entity overall — drives reputation_cascade
        gossip propagation."""
        return self._entity_witness_counts.get(
            entity_id, 0,
        )

    def witnesses_of(
        self, *, entity_id: str, hobby: HobbyKind,
    ) -> list[str]:
        """List of witness_ids who have ever
        observed this exact (entity, hobby) pair."""
        out: set[str] = set()
        for o in self._observations.values():
            if (
                o.entity_id == entity_id
                and o.hobby == hobby
            ):
                out.add(o.witness_id)
        return sorted(out)

    def observation(
        self, *, observation_id: str,
    ) -> t.Optional[Observation]:
        return self._observations.get(observation_id)

    def observations_by_witness(
        self, *, witness_id: str,
    ) -> list[Observation]:
        return [
            o for o in self._observations.values()
            if o.witness_id == witness_id
        ]


__all__ = [
    "Observation", "HobbyObservationSystem",
]
