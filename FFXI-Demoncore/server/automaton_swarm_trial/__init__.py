"""Automaton Swarm Trial — the world-first impossible Master Trial.

A Demoncore-original Master Trial designed for prestige-seeking
veterans. Spawns waves of automaton variants from EVERY Head ×
Frame combination in the automaton_synergy catalog. Each
variant uses its full SP arsenal:

  * Maneuver-stacked synergies
  * Overdrive (5x multiplier on the SP)
  * The "secret" combinations that produce special abilities
    (built earlier in the synergy catalog)

The waves arrive in escalating tiers. By Wave 5 the boss room
is producing simultaneous Stormwaker + Spiritreaver + RDM
overdrives — actually un-survivable without a perfect
composition.

The trial is BALANCED to be next-to-impossible: only an
exceptionally well-coordinated alliance has a real shot. The
first kill earns the "First-of-Vana'diel" title, broadcast
server-wide.

Public surface
--------------
    SwarmWave dataclass / TRIAL_WAVES
    AutomatonVariant dataclass — one of the 64 Head×Frame
    enumerate_variants() -> tuple[AutomatonVariant, ...]
    SwarmTrialAttempt
        .start(party_ids, alliance_ids)
        .wave_complete(wave_index)
        .clear()  -> ClearResult (with title award if first server)
"""
from __future__ import annotations

import dataclasses
import typing as t

from server.automaton_synergy.catalog import (
    Frame,
    Head,
    SynergyAbility,
    all_synergy_ids,
    get_synergy,
    synergies_for,
)


# -----------------------------------------------------------------------
# Variants & waves
# -----------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class AutomatonVariant:
    head: Head
    frame: Frame
    label: str
    synergies: tuple[SynergyAbility, ...]   # full SP arsenal
    overdrive_capable: bool                 # True when ALL maneuver
                                            # slots could be one element
    secret_combos: tuple[str, ...]          # synergy ids that need
                                            # specific head+frame pairs


def _is_overdrive_capable(head: Head, frame: Frame) -> bool:
    """An automaton can Overdrive when its head/frame stack tolerates
    a triple-element maneuver stack (any synergy uses 3 of the same
    element). All 8 frames support this in canonical retail."""
    return True   # every frame can Overdrive in Demoncore


def _secret_combos_for(head: Head, frame: Frame) -> tuple[str, ...]:
    """Synergies that ONLY trigger when a head and frame match (or
    when a specific Demoncore-extended pairing fires). We treat the
    matched-pair (Head.X + Frame.X) as a 'secret combo' bucket."""
    if head.value == frame.value:
        return tuple(
            ability.ability_id
            for ability in synergies_for(head=head, frame=frame)
        )
    return ()


def _build_variants() -> tuple[AutomatonVariant, ...]:
    out: list[AutomatonVariant] = []
    for head in Head:
        for frame in Frame:
            syns = synergies_for(head=head, frame=frame)
            out.append(AutomatonVariant(
                head=head, frame=frame,
                label=f"{head.value.title()}/{frame.value.title()}",
                synergies=tuple(syns),
                overdrive_capable=_is_overdrive_capable(head, frame),
                secret_combos=_secret_combos_for(head, frame),
            ))
    return tuple(out)


VARIANTS: tuple[AutomatonVariant, ...] = _build_variants()


def enumerate_variants() -> tuple[AutomatonVariant, ...]:
    return VARIANTS


@dataclasses.dataclass(frozen=True)
class SwarmWave:
    wave_index: int
    label: str
    variants_per_player: int        # how many variants spawn per player
    overdrives_active: bool
    secret_combos_active: bool
    timer_seconds: int


# Five waves of escalating chaos.
TRIAL_WAVES: tuple[SwarmWave, ...] = (
    SwarmWave(
        wave_index=1,
        label="Wave I — The Awakening",
        variants_per_player=2,
        overdrives_active=False,
        secret_combos_active=False,
        timer_seconds=10 * 60,
    ),
    SwarmWave(
        wave_index=2,
        label="Wave II — Cascading Maneuvers",
        variants_per_player=3,
        overdrives_active=False,
        secret_combos_active=False,
        timer_seconds=10 * 60,
    ),
    SwarmWave(
        wave_index=3,
        label="Wave III — The Overdrive Symphony",
        variants_per_player=4,
        overdrives_active=True,
        secret_combos_active=False,
        timer_seconds=15 * 60,
    ),
    SwarmWave(
        wave_index=4,
        label="Wave IV — Secret Couplings",
        variants_per_player=5,
        overdrives_active=True,
        secret_combos_active=True,
        timer_seconds=15 * 60,
    ),
    SwarmWave(
        wave_index=5,
        label="Wave V — Total Cataclysm",
        variants_per_player=8,
        overdrives_active=True,
        secret_combos_active=True,
        timer_seconds=20 * 60,
    ),
)


WAVE_BY_INDEX: dict[int, SwarmWave] = {w.wave_index: w for w in TRIAL_WAVES}


# -----------------------------------------------------------------------
# Trial attempt
# -----------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class ClearResult:
    accepted: bool
    cleared_in_seconds: float = 0.0
    is_world_first: bool = False
    awarded_title: t.Optional[str] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SwarmTrialAttempt:
    party_ids: tuple[str, ...] = ()
    alliance_ids: tuple[str, ...] = ()
    start_time_seconds: float = 0.0
    state: str = "open"            # open / waving / cleared / failed
    current_wave_index: int = 0
    waves_cleared: list[int] = dataclasses.field(default_factory=list)

    def start(self, *, party_ids: tuple[str, ...],
                alliance_ids: tuple[str, ...] = (),
                now_seconds: float = 0.0) -> bool:
        if self.state != "open":
            return False
        if not party_ids:
            return False
        # Trial requires full alliance for Wave 5+; we permit smaller
        # parties to try but they will hit a brick wall.
        self.party_ids = party_ids
        self.alliance_ids = alliance_ids or party_ids
        self.start_time_seconds = now_seconds
        self.state = "waving"
        self.current_wave_index = 1
        return True

    def wave_complete(self, *, wave_index: int) -> bool:
        if self.state != "waving":
            return False
        if wave_index != self.current_wave_index:
            return False
        if wave_index not in WAVE_BY_INDEX:
            return False
        self.waves_cleared.append(wave_index)
        if wave_index == max(WAVE_BY_INDEX.keys()):
            self.state = "cleared"
        else:
            self.current_wave_index += 1
        return True

    def fail(self) -> bool:
        if self.state in ("cleared", "failed"):
            return False
        self.state = "failed"
        return True

    def clear(self, *, now_seconds: float,
                server_first_record_holder: t.Optional[str] = None,
                ) -> ClearResult:
        if self.state != "cleared":
            return ClearResult(False, reason="trial not cleared")
        elapsed = now_seconds - self.start_time_seconds
        is_first = server_first_record_holder is None
        title = "First-of-Vana'diel" if is_first else None
        return ClearResult(
            accepted=True,
            cleared_in_seconds=elapsed,
            is_world_first=is_first,
            awarded_title=title,
        )


def total_variants() -> int:
    return len(VARIANTS)


def known_synergy_ids() -> tuple[str, ...]:
    return tuple(all_synergy_ids())


def synergy_for_id(ability_id: str) -> SynergyAbility:
    return get_synergy(ability_id)


__all__ = [
    "AutomatonVariant", "SwarmWave",
    "VARIANTS", "TRIAL_WAVES", "WAVE_BY_INDEX",
    "enumerate_variants", "total_variants",
    "known_synergy_ids", "synergy_for_id",
    "ClearResult", "SwarmTrialAttempt",
]
