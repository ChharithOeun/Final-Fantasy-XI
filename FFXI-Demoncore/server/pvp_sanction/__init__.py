"""PvP Sanction registry — friendly vs hostile classification.

Demoncore policy: Brenner AND Ballista are the sanctioned
(friendly) forms of PvP. Both are formal arena/event PvP with
their own scoring and reward systems. Everything else — open-
world outlaw kills, duels, griefing — is HOSTILE and incurs a
penalty.

Hostile-PvP penalties (cumulative — every kill adds them):
* Honor loss        (server/honor_reputation HONOR_AXIS)
* Reputation hit    (per killed nation if applicable)
* Outlaw flag bump  (one strike toward outlaw status)
* Conquest impact   (your nation may lose conquest if you
                     killed in their zone)

This module is a thin classifier + penalty applicator. It does
NOT itself store player state — it returns structured penalty
records that callers apply to honor_reputation, outlaw_system,
and conquest_tally as appropriate.

Public surface
--------------
    PvpMode enum (BRENNER + every other mode in the project)
    PvpClassification enum (SANCTIONED / HOSTILE)
    classify(mode) -> PvpClassification
    HostilePenalty dataclass
    penalty_for(mode) -> Optional[HostilePenalty]
    is_sanctioned(mode) / is_hostile(mode)
    sanctioned_modes() / hostile_modes()
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PvpMode(str, enum.Enum):
    """Every distinct PvP mode in Demoncore."""
    # Sanctioned (friendly) modes
    BRENNER = "brenner"
    BALLISTA = "ballista"

    # Hostile / penalty-bearing modes
    OUTLAW_OPEN_WORLD = "outlaw_open_world"  # any open-world kill
    OUTLAW_AMBUSH = "outlaw_ambush"          # bounty hunting, hostile
    CONFLICT_DUEL = "conflict_duel"          # 1v1 duels (hostile)
    PVP_GRIEF_HEAL = "pvp_grief_heal"        # debuff/dispel a hostile
    PVP_GRIEF_PULL = "pvp_grief_pull"        # mob-pulling griefing
    SAFEHAVEN_VIOLATION = "safehaven_violation"  # PvP in safe-haven


class PvpClassification(str, enum.Enum):
    SANCTIONED = "sanctioned"
    HOSTILE = "hostile"


# Authoritative classification. Brenner AND Ballista are
# sanctioned arena PvP; everything else is hostile.
_CLASSIFICATION: dict[PvpMode, PvpClassification] = {
    PvpMode.BRENNER: PvpClassification.SANCTIONED,
    PvpMode.BALLISTA: PvpClassification.SANCTIONED,
    PvpMode.OUTLAW_OPEN_WORLD: PvpClassification.HOSTILE,
    PvpMode.OUTLAW_AMBUSH: PvpClassification.HOSTILE,
    PvpMode.CONFLICT_DUEL: PvpClassification.HOSTILE,
    PvpMode.PVP_GRIEF_HEAL: PvpClassification.HOSTILE,
    PvpMode.PVP_GRIEF_PULL: PvpClassification.HOSTILE,
    PvpMode.SAFEHAVEN_VIOLATION: PvpClassification.HOSTILE,
}


# Per-mode penalty severity. Higher numbers = bigger consequences.
@dataclasses.dataclass(frozen=True)
class HostilePenalty:
    mode: PvpMode
    honor_loss: int             # subtract from Honor axis
    reputation_loss: int        # subtract from killer's nation rep
    outlaw_strikes: int         # adds to outlaw_system strike count
    conquest_impact: int        # negative if killer was in friendly zone
    description: str = ""


_PENALTIES: dict[PvpMode, HostilePenalty] = {
    PvpMode.OUTLAW_OPEN_WORLD: HostilePenalty(
        mode=PvpMode.OUTLAW_OPEN_WORLD,
        honor_loss=40, reputation_loss=25,
        outlaw_strikes=1, conquest_impact=-50,
        description=(
            "Killing another adventurer in the open world is a "
            "serious offense. One outlaw strike, conquest hit, "
            "heavy honor + reputation loss."
        ),
    ),
    PvpMode.OUTLAW_AMBUSH: HostilePenalty(
        mode=PvpMode.OUTLAW_AMBUSH,
        honor_loss=20, reputation_loss=10,
        outlaw_strikes=0, conquest_impact=-25,
        description=(
            "Bounty-hunting an outlaw is still hostile combat. "
            "Smaller penalties than unprovoked kills."
        ),
    ),
    PvpMode.CONFLICT_DUEL: HostilePenalty(
        mode=PvpMode.CONFLICT_DUEL,
        honor_loss=15, reputation_loss=5,
        outlaw_strikes=0, conquest_impact=0,
        description=(
            "1v1 consensual duel — hostile but contained."
        ),
    ),
    PvpMode.PVP_GRIEF_HEAL: HostilePenalty(
        mode=PvpMode.PVP_GRIEF_HEAL,
        honor_loss=20, reputation_loss=15,
        outlaw_strikes=0, conquest_impact=0,
        description=(
            "Debuffing/dispelling a hostile mid-fight to grief is "
            "treated as PvP."
        ),
    ),
    PvpMode.PVP_GRIEF_PULL: HostilePenalty(
        mode=PvpMode.PVP_GRIEF_PULL,
        honor_loss=25, reputation_loss=15,
        outlaw_strikes=1, conquest_impact=0,
        description=(
            "Pulling a mob train onto another player's camp is "
            "outlaw-tier griefing."
        ),
    ),
    PvpMode.SAFEHAVEN_VIOLATION: HostilePenalty(
        mode=PvpMode.SAFEHAVEN_VIOLATION,
        honor_loss=80, reputation_loss=50,
        outlaw_strikes=2, conquest_impact=-100,
        description=(
            "PvP inside a safe-haven (capital city, Mog House zone) "
            "is the worst offense — double outlaw strikes, full "
            "honor reset risk."
        ),
    ),
}


def classify(mode: PvpMode) -> PvpClassification:
    return _CLASSIFICATION[mode]


def is_sanctioned(mode: PvpMode) -> bool:
    return classify(mode) == PvpClassification.SANCTIONED


def is_hostile(mode: PvpMode) -> bool:
    return classify(mode) == PvpClassification.HOSTILE


def penalty_for(mode: PvpMode) -> t.Optional[HostilePenalty]:
    """Returns the penalty record for a hostile mode, or None for
    sanctioned (no penalty)."""
    return _PENALTIES.get(mode)


def sanctioned_modes() -> tuple[PvpMode, ...]:
    return tuple(
        m for m, c in _CLASSIFICATION.items()
        if c == PvpClassification.SANCTIONED
    )


def hostile_modes() -> tuple[PvpMode, ...]:
    return tuple(
        m for m, c in _CLASSIFICATION.items()
        if c == PvpClassification.HOSTILE
    )


@dataclasses.dataclass(frozen=True)
class AppliedPenalty:
    """Structured record for the caller to apply against the
    killer's state. Returned by record_pvp_action()."""
    accepted: bool
    mode: PvpMode
    classification: PvpClassification
    penalty: t.Optional[HostilePenalty] = None
    reason: t.Optional[str] = None


def record_pvp_action(
    *, mode: PvpMode, killer_id: str, victim_id: str,
) -> AppliedPenalty:
    """Top-level dispatch. The caller is responsible for actually
    applying the returned HostilePenalty to honor_reputation,
    outlaw_system, and conquest_tally — this module just classifies
    and surfaces the cost."""
    if not killer_id or not victim_id:
        return AppliedPenalty(
            False, mode=mode,
            classification=classify(mode),
            reason="killer_id and victim_id required",
        )
    classification = classify(mode)
    penalty = penalty_for(mode) if classification == PvpClassification.HOSTILE \
        else None
    return AppliedPenalty(
        accepted=True, mode=mode,
        classification=classification, penalty=penalty,
    )


__all__ = [
    "PvpMode", "PvpClassification",
    "HostilePenalty", "AppliedPenalty",
    "classify", "is_sanctioned", "is_hostile",
    "penalty_for",
    "sanctioned_modes", "hostile_modes",
    "record_pvp_action",
]
