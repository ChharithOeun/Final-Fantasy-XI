"""Letter of marque — privateer license; legal piracy under a flag.

A LETTER OF MARQUE is a nation-issued license that lets the
holder legally raid pirate fleets and (if the holder's
nation is at war) enemy nation shipping. The bearer is a
PRIVATEER — a sanctioned pirate. Without a letter, the same
acts make the player an OUTLAW (per outlaw_system).

Issuing nations: BASTOK / SAN_DORIA / WINDURST. Each can
issue letters; expired letters or letters from a defeated
nation become void. A player can hold ONE letter at a time.

License scope:
  TARGETS_PIRATE_ONLY  - cheap; can only attack pirate fleets
  TARGETS_ENEMY_NAVY   - mid; pirate + at-war-nation ships
  ANY_VESSEL_AT_SEA    - rare; "all is fair at sea" wartime
                          letter; expires fast (7 days)

A letter has a duration; all expire at expiry_seconds.
Renewing requires a new application + nation rep.

Public surface
--------------
    Nation enum
    LicenseScope enum
    LetterRecord dataclass
    LetterOfMarque
        .issue(player_id, nation, scope, issued_at_seconds,
               duration_seconds)
        .revoke(player_id, reason)
        .is_target_lawful(player_id, target_kind, attacker_nation_at_war,
                          now_seconds)
        .holder_status(player_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Nation(str, enum.Enum):
    BASTOK = "bastok"
    SAN_DORIA = "san_doria"
    WINDURST = "windurst"


class LicenseScope(str, enum.Enum):
    TARGETS_PIRATE_ONLY = "pirate_only"
    TARGETS_ENEMY_NAVY = "enemy_navy"
    ANY_VESSEL_AT_SEA = "any_vessel"


class TargetKind(str, enum.Enum):
    PIRATE_FLEET = "pirate_fleet"
    ENEMY_NATION_SHIP = "enemy_nation_ship"
    NEUTRAL_NATION_SHIP = "neutral_nation_ship"
    OWN_NATION_SHIP = "own_nation_ship"


@dataclasses.dataclass
class LetterRecord:
    player_id: str
    nation: Nation
    scope: LicenseScope
    issued_at: int
    expires_at: int
    revoked: bool = False
    revoke_reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class IssueResult:
    accepted: bool
    expires_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class LetterOfMarque:
    _letters: dict[str, LetterRecord] = dataclasses.field(
        default_factory=dict,
    )

    def issue(
        self, *, player_id: str,
        nation: Nation,
        scope: LicenseScope,
        issued_at_seconds: int,
        duration_seconds: int,
    ) -> IssueResult:
        if not player_id:
            return IssueResult(False, reason="bad player")
        if nation not in Nation:
            return IssueResult(False, reason="unknown nation")
        if scope not in LicenseScope:
            return IssueResult(False, reason="unknown scope")
        if duration_seconds <= 0:
            return IssueResult(False, reason="bad duration")
        existing = self._letters.get(player_id)
        if existing is not None and not existing.revoked:
            if existing.expires_at > issued_at_seconds:
                return IssueResult(
                    False, reason="already holds an active letter",
                )
        expires = issued_at_seconds + duration_seconds
        self._letters[player_id] = LetterRecord(
            player_id=player_id,
            nation=nation,
            scope=scope,
            issued_at=issued_at_seconds,
            expires_at=expires,
        )
        return IssueResult(accepted=True, expires_at=expires)

    def revoke(
        self, *, player_id: str, reason: str,
    ) -> bool:
        rec = self._letters.get(player_id)
        if rec is None or rec.revoked:
            return False
        rec.revoked = True
        rec.revoke_reason = reason
        return True

    def holder_status(
        self, *, player_id: str, now_seconds: int,
    ) -> t.Optional[LetterRecord]:
        rec = self._letters.get(player_id)
        if rec is None:
            return None
        if rec.revoked or rec.expires_at <= now_seconds:
            return None
        return rec

    def is_target_lawful(
        self, *, player_id: str,
        target_kind: TargetKind,
        attacker_nation_at_war: bool,
        now_seconds: int,
    ) -> bool:
        rec = self.holder_status(
            player_id=player_id, now_seconds=now_seconds,
        )
        if rec is None:
            return False
        # OWN_NATION_SHIP is never lawful regardless of scope
        if target_kind == TargetKind.OWN_NATION_SHIP:
            return False
        if rec.scope == LicenseScope.TARGETS_PIRATE_ONLY:
            return target_kind == TargetKind.PIRATE_FLEET
        if rec.scope == LicenseScope.TARGETS_ENEMY_NAVY:
            if target_kind == TargetKind.PIRATE_FLEET:
                return True
            if target_kind == TargetKind.ENEMY_NATION_SHIP:
                return attacker_nation_at_war
            return False
        # ANY_VESSEL_AT_SEA — anything that's not OWN_NATION
        return True


__all__ = [
    "Nation", "LicenseScope", "TargetKind",
    "LetterRecord", "IssueResult",
    "LetterOfMarque",
]
