"""Threat-model defenses per AUTH_DISCORD.md.

| Threat                          | Mitigation                              |
|---------------------------------|-----------------------------------------|
| Discord account compromise      | /me re-verification flow                |
|                                 | Banned IP list for compromised tokens   |
|                                 | Loss tolerance: 12h until session expiry|
| Token replay                    | Hardware fingerprint binding            |
|                                 | Mismatch -> revoke + re-verify          |
| Ban evasion via alt Discords    | Unique-on-phone rule (opt-in scope)     |
| chharbot misbehaving            | Every action reversible by /override    |
|                                 | If chharbot offline, gate STAYS CLOSED  |
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TokenReplayCheck(str, enum.Enum):
    OK = "ok"
    REVOKE = "revoke"


@dataclasses.dataclass(frozen=True)
class ReplayDecision:
    outcome: TokenReplayCheck
    reason: str


def check_hardware_fingerprint(*,
                                    expected: t.Optional[str],
                                    reported: str
                                    ) -> ReplayDecision:
    """Doc: 'LSB account tokens are bound to a hardware fingerprint
    reported by the launcher. Mismatch -> revoke + re-verify.'

    A first-time link (expected is None) accepts any fingerprint —
    the link operation pins it. Subsequent reports must match.
    """
    if not reported:
        return ReplayDecision(
            outcome=TokenReplayCheck.REVOKE,
            reason="empty fingerprint reported",
        )
    if expected is None:
        return ReplayDecision(
            outcome=TokenReplayCheck.OK,
            reason="first link; pinning fingerprint",
        )
    if expected != reported:
        return ReplayDecision(
            outcome=TokenReplayCheck.REVOKE,
            reason=("hardware fingerprint mismatch; suspecting "
                      "token replay - revoke + re-verify"),
        )
    return ReplayDecision(
        outcome=TokenReplayCheck.OK,
        reason="fingerprint matches",
    )


# Phone-number ban-evasion enforcement.
class PhoneBanResult(str, enum.Enum):
    OK = "ok"
    BLOCKED_BY_PHONE = "blocked_by_phone"


class PhoneBanRegistry:
    """Tracks phone numbers from previously-banned Discord accounts.

    Per the doc: 'unique-on-phone-number rule for new verifications
    (Discord exposes this via the OAuth `phone` scope, opt-in).'
    """

    def __init__(self) -> None:
        self._banned_phones: set[str] = set()

    def record_banned_phone(self, phone_number: str) -> None:
        if phone_number:
            self._banned_phones.add(phone_number)

    def check_new_verification(self,
                                    *,
                                    phone_number: t.Optional[str],
                                    ) -> PhoneBanResult:
        if phone_number is None:
            # User declined the phone scope; allow but flag.
            return PhoneBanResult.OK
        if phone_number in self._banned_phones:
            return PhoneBanResult.BLOCKED_BY_PHONE
        return PhoneBanResult.OK


# chharbot offline => closed-gate fail-safe.
@dataclasses.dataclass
class GateState:
    """Tracks chharbot heartbeat. If down, no new verifications process."""
    last_heartbeat_at: float = 0.0
    is_chharbot_online: bool = True

    def heartbeat(self, *, now: float) -> None:
        self.last_heartbeat_at = now
        self.is_chharbot_online = True

    def mark_offline(self) -> None:
        self.is_chharbot_online = False

    def can_accept_new_verifications(self) -> bool:
        """Doc: 'if chharbot is offline, the gate stays closed (no new
        verifications until owner restores it).'"""
        return self.is_chharbot_online
