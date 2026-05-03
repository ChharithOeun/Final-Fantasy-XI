"""Outlaw Linkshells — organized banditry, sanctioned with risk.

Demoncore allows linkshells to declare themselves outlaws. They
can murder, ambush, and harass other players in any non-safehaven
zone — but they pay for it with constant penalties AND a server-
wide bounty that any non-LS-member can collect by hunting them
down.

Mechanic:
* A linkshell self-declares OUTLAW status (24-hour cooldown
  between status changes — prevents flip-flop).
* While OUTLAW, every member's hostile-PvP penalty pool flows
  into the LS bounty pot.
* When ANY non-LS-member kills an outlaw LS member, that kill
  pulls a share of the LS bounty as the headhunter's reward.
* Long-lived outlaw LSes can graduate to INFAMOUS status
  (after 100 hostile kills) — bigger bounties, bigger
  headhunter rewards, server-wide alert when an INFAMOUS LS
  member is spotted.

Public surface
--------------
    OutlawStatus enum (CITIZEN / OUTLAW / INFAMOUS)
    StatusChangeResult / RegistrationResult
    OutlawLinkshell dataclass
        .declare_outlaw(now) / .renounce_outlaw(now)
        .add_hostile_kill(member_id, penalty_amount)
        .record_member_killed(killer_id) -> bounty share
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


STATUS_CHANGE_COOLDOWN_SECONDS = 24 * 60 * 60   # 24-hour cooldown
INFAMOUS_KILL_THRESHOLD = 100
BOUNTY_POOL_PCT_PER_KILL = 50      # 50% of LS pool per headhunt kill
INFAMOUS_BOUNTY_MULTIPLIER = 2     # bigger payouts when infamous


class OutlawStatus(str, enum.Enum):
    CITIZEN = "citizen"
    OUTLAW = "outlaw"
    INFAMOUS = "infamous"


@dataclasses.dataclass(frozen=True)
class StatusChangeResult:
    accepted: bool
    new_status: t.Optional[OutlawStatus] = None
    next_eligible_change_at: t.Optional[float] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class HeadhuntResult:
    accepted: bool
    bounty_paid: int = 0
    pool_remaining: int = 0
    triggers_infamous_alert: bool = False
    reason: t.Optional[str] = None


@dataclasses.dataclass
class OutlawLinkshell:
    linkshell_id: str
    members: list[str] = dataclasses.field(default_factory=list)
    status: OutlawStatus = OutlawStatus.CITIZEN
    last_status_change_at_seconds: float = 0.0
    bounty_pool: int = 0
    hostile_kills_total: int = 0
    members_killed_total: int = 0

    # ------------------------------------------------------------------
    # Membership
    # ------------------------------------------------------------------
    def add_member(self, *, player_id: str) -> bool:
        if player_id in self.members:
            return False
        self.members.append(player_id)
        return True

    def remove_member(self, *, player_id: str) -> bool:
        if player_id not in self.members:
            return False
        self.members.remove(player_id)
        return True

    def is_member(self, player_id: str) -> bool:
        return player_id in self.members

    # ------------------------------------------------------------------
    # Status changes
    # ------------------------------------------------------------------
    def declare_outlaw(self, *, now_seconds: float
                        ) -> StatusChangeResult:
        if self.status != OutlawStatus.CITIZEN:
            return StatusChangeResult(False, reason="already outlaw/infamous")
        if (now_seconds - self.last_status_change_at_seconds
                < STATUS_CHANGE_COOLDOWN_SECONDS
                and self.last_status_change_at_seconds > 0):
            return StatusChangeResult(
                False, reason="cooldown active",
                next_eligible_change_at=(
                    self.last_status_change_at_seconds
                    + STATUS_CHANGE_COOLDOWN_SECONDS
                ),
            )
        self.status = OutlawStatus.OUTLAW
        self.last_status_change_at_seconds = now_seconds
        return StatusChangeResult(True, new_status=OutlawStatus.OUTLAW)

    def renounce_outlaw(self, *, now_seconds: float
                         ) -> StatusChangeResult:
        if self.status == OutlawStatus.CITIZEN:
            return StatusChangeResult(False, reason="not outlaw")
        if (now_seconds - self.last_status_change_at_seconds
                < STATUS_CHANGE_COOLDOWN_SECONDS):
            return StatusChangeResult(
                False, reason="cooldown active",
                next_eligible_change_at=(
                    self.last_status_change_at_seconds
                    + STATUS_CHANGE_COOLDOWN_SECONDS
                ),
            )
        self.status = OutlawStatus.CITIZEN
        self.last_status_change_at_seconds = now_seconds
        # Bounty pool resets when the LS goes back legit.
        self.bounty_pool = 0
        return StatusChangeResult(True, new_status=OutlawStatus.CITIZEN)

    # ------------------------------------------------------------------
    # Bounty mechanics
    # ------------------------------------------------------------------
    def add_hostile_kill(
        self, *, member_id: str, penalty_amount: int,
    ) -> bool:
        """A member of this LS just landed a hostile-PvP kill.
        Penalty value flows into the bounty pool. Promotes to
        INFAMOUS at 100 cumulative hostile kills."""
        if self.status == OutlawStatus.CITIZEN:
            return False
        if not self.is_member(member_id):
            return False
        if penalty_amount <= 0:
            return False
        self.bounty_pool += penalty_amount
        self.hostile_kills_total += 1
        if (self.status == OutlawStatus.OUTLAW
                and self.hostile_kills_total >= INFAMOUS_KILL_THRESHOLD):
            self.status = OutlawStatus.INFAMOUS
        return True

    def record_member_killed(
        self, *, killer_id: str,
    ) -> HeadhuntResult:
        """A non-LS-member just headhunted an outlaw LS member.
        Pays out a share of the bounty pool to the killer."""
        if self.status == OutlawStatus.CITIZEN:
            return HeadhuntResult(False, reason="LS not outlaw")
        if self.is_member(killer_id):
            return HeadhuntResult(
                False, reason="LS members can't claim own bounty",
            )
        if self.bounty_pool <= 0:
            return HeadhuntResult(False, reason="bounty pool empty")
        share = self.bounty_pool * BOUNTY_POOL_PCT_PER_KILL // 100
        if self.status == OutlawStatus.INFAMOUS:
            share *= INFAMOUS_BOUNTY_MULTIPLIER
        share = min(share, self.bounty_pool)
        self.bounty_pool -= share
        self.members_killed_total += 1
        return HeadhuntResult(
            accepted=True, bounty_paid=share,
            pool_remaining=self.bounty_pool,
            triggers_infamous_alert=(self.status == OutlawStatus.INFAMOUS),
        )


__all__ = [
    "STATUS_CHANGE_COOLDOWN_SECONDS",
    "INFAMOUS_KILL_THRESHOLD",
    "BOUNTY_POOL_PCT_PER_KILL",
    "INFAMOUS_BOUNTY_MULTIPLIER",
    "OutlawStatus",
    "StatusChangeResult", "HeadhuntResult",
    "OutlawLinkshell",
]
