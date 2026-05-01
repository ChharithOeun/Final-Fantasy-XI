"""Avatar pacts — Summoner BPs, perpetuation, summon lifecycle.

A SMN's avatar is summoned with a one-time MP cost, then drains
MP per tick (perpetuation) until released or until perpetuation
debt exceeds remaining MP (auto-release).

Blood Pacts come in two flavors:
  WARD - support/buff/heal/debuff
  RAGE - direct damage

Each has its own cooldown timer (separate from the SMN job
ability cooldowns); a "1-min" pact recovery accelerates the
shared BP cooldown post-cast.

Public surface
--------------
    Avatar enum
    BPType enum (WARD/RAGE)
    BloodPact catalog by avatar
    AvatarSession - active summon state
    perform_pact(...) - cooldown gate + cost
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Avatar(str, enum.Enum):
    CARBUNCLE = "carbuncle"
    SHIVA = "shiva"
    IFRIT = "ifrit"
    RAMUH = "ramuh"
    GARUDA = "garuda"
    TITAN = "titan"
    LEVIATHAN = "leviathan"
    FENRIR = "fenrir"
    DIABOLOS = "diabolos"
    ODIN = "odin"
    ALEXANDER = "alexander"
    CAIT_SITH = "cait_sith"


class BPType(str, enum.Enum):
    WARD = "ward"      # support/buff/heal/debuff
    RAGE = "rage"      # direct damage


@dataclasses.dataclass(frozen=True)
class BloodPact:
    pact_id: str
    name: str
    avatar: Avatar
    bp_type: BPType
    mp_cost: int
    cooldown_seconds: int = 60
    description: str = ""


# Sample catalog
BLOOD_PACT_CATALOG: tuple[BloodPact, ...] = (
    # Carbuncle
    BloodPact("healing_ruby", "Healing Ruby",
              Avatar.CARBUNCLE, BPType.WARD, mp_cost=23),
    BloodPact("poison_nails", "Poison Nails",
              Avatar.CARBUNCLE, BPType.RAGE, mp_cost=20),
    # Shiva
    BloodPact("frost_armor", "Frost Armor",
              Avatar.SHIVA, BPType.WARD, mp_cost=68),
    BloodPact("axe_kick", "Axe Kick",
              Avatar.SHIVA, BPType.RAGE, mp_cost=44),
    BloodPact("diamond_dust", "Diamond Dust",
              Avatar.SHIVA, BPType.RAGE, mp_cost=180,
              cooldown_seconds=300),
    # Ifrit
    BloodPact("crimson_howl", "Crimson Howl",
              Avatar.IFRIT, BPType.WARD, mp_cost=68),
    BloodPact("flaming_crush", "Flaming Crush",
              Avatar.IFRIT, BPType.RAGE, mp_cost=80),
    BloodPact("inferno", "Inferno",
              Avatar.IFRIT, BPType.RAGE, mp_cost=180,
              cooldown_seconds=300),
    # Garuda
    BloodPact("aerial_armor", "Aerial Armor",
              Avatar.GARUDA, BPType.WARD, mp_cost=68),
    BloodPact("predator_claws", "Predator Claws",
              Avatar.GARUDA, BPType.RAGE, mp_cost=51),
    # Titan
    BloodPact("earthen_ward", "Earthen Ward",
              Avatar.TITAN, BPType.WARD, mp_cost=68),
    BloodPact("rock_buster", "Rock Buster",
              Avatar.TITAN, BPType.RAGE, mp_cost=44),
    # Diabolos
    BloodPact("nightmare", "Nightmare",
              Avatar.DIABOLOS, BPType.WARD, mp_cost=104),
    # Odin
    BloodPact("zantetsuken", "Zantetsuken",
              Avatar.ODIN, BPType.RAGE, mp_cost=300,
              cooldown_seconds=3600),     # 1 hour
)

PACT_BY_ID: dict[str, BloodPact] = {p.pact_id: p
                                     for p in BLOOD_PACT_CATALOG}


def pacts_for_avatar(avatar: Avatar) -> tuple[BloodPact, ...]:
    return tuple(p for p in BLOOD_PACT_CATALOG if p.avatar == avatar)


# Perpetuation: 7 MP/tick base for low-tier avatars (Carbuncle),
# 12 MP/tick for "elemental" avatars (Shiva/Ifrit/etc).
PERPETUATION_MP: dict[Avatar, int] = {
    Avatar.CARBUNCLE: 5,
    Avatar.SHIVA: 12,
    Avatar.IFRIT: 12,
    Avatar.RAMUH: 12,
    Avatar.GARUDA: 12,
    Avatar.TITAN: 12,
    Avatar.LEVIATHAN: 12,
    Avatar.FENRIR: 12,
    Avatar.DIABOLOS: 14,
    Avatar.CAIT_SITH: 12,
    Avatar.ODIN: 0,            # special — fights once and leaves
    Avatar.ALEXANDER: 0,
}


@dataclasses.dataclass
class AvatarSession:
    """Active summon."""
    summoner_id: str
    avatar: Avatar
    summoned_at_tick: int
    last_perpetuation_tick: int
    mp_balance: int               # caller maintains; we mutate
    released: bool = False

    @property
    def perpetuation_per_tick(self) -> int:
        return PERPETUATION_MP[self.avatar]


@dataclasses.dataclass
class PactCooldownState:
    """Per-summoner BP cooldowns. Keyed by pact_id."""
    next_available: dict[str, int] = dataclasses.field(
        default_factory=dict,
    )

    def can_cast(self, *, pact_id: str, now_tick: int) -> bool:
        return now_tick >= self.next_available.get(pact_id, 0)


def summon_avatar(
    *, summoner_id: str, avatar: Avatar,
    summon_mp_cost: int, current_mp: int, now_tick: int,
) -> t.Optional[AvatarSession]:
    """Returns a session if MP suffices, otherwise None."""
    if current_mp < summon_mp_cost:
        return None
    return AvatarSession(
        summoner_id=summoner_id,
        avatar=avatar,
        summoned_at_tick=now_tick,
        last_perpetuation_tick=now_tick,
        mp_balance=current_mp - summon_mp_cost,
    )


def perpetuate(
    session: AvatarSession, *, now_tick: int,
    seconds_per_tick: int = 3,
) -> bool:
    """Apply perpetuation drain. Returns True if avatar is still
    summoned, False if MP ran dry (auto-released).

    seconds_per_tick: how many real seconds = one perpetuation tick.
    """
    if session.released:
        return False
    elapsed = now_tick - session.last_perpetuation_tick
    ticks = elapsed // seconds_per_tick
    if ticks <= 0:
        return True
    cost = ticks * session.perpetuation_per_tick
    session.mp_balance -= cost
    session.last_perpetuation_tick += ticks * seconds_per_tick
    if session.mp_balance < 0:
        session.released = True
        session.mp_balance = 0
        return False
    return True


def perform_pact(
    *,
    session: AvatarSession,
    pact_id: str,
    cooldowns: PactCooldownState,
    now_tick: int,
) -> tuple[bool, t.Optional[str]]:
    """Cast a Blood Pact. Returns (success, reason_if_fail)."""
    if session.released:
        return False, "no avatar summoned"
    pact = PACT_BY_ID.get(pact_id)
    if pact is None:
        return False, "unknown pact"
    if pact.avatar != session.avatar:
        return False, f"{pact.name} requires {pact.avatar.value}"
    if session.mp_balance < pact.mp_cost:
        return False, f"insufficient MP (need {pact.mp_cost})"
    if not cooldowns.can_cast(pact_id=pact_id, now_tick=now_tick):
        return False, "on cooldown"
    session.mp_balance -= pact.mp_cost
    cooldowns.next_available[pact_id] = (
        now_tick + pact.cooldown_seconds
    )
    return True, None


def release_avatar(session: AvatarSession) -> None:
    session.released = True


__all__ = [
    "Avatar", "BPType", "BloodPact",
    "BLOOD_PACT_CATALOG", "PACT_BY_ID", "PERPETUATION_MP",
    "pacts_for_avatar",
    "AvatarSession", "PactCooldownState",
    "summon_avatar", "perpetuate", "perform_pact",
    "release_avatar",
]
