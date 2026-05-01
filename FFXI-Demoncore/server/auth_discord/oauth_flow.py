"""Discord OAuth2 flow — the verification path per AUTH_DISCORD.md.

new player -> guild invite -> chharbot DM with verification button
-> click -> OAuth code grant -> chharbot reads identify scope ->
assigns @Verified role -> mints LSB account token -> DMs launcher
download link.

24h timeout: if no click, auto-kick.
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from .tokens import Token, TokenKind, mint_token


# Doc: 'Verification timeout (24h, no click) -> Auto-kick'.
VERIFICATION_TIMEOUT_SECONDS: int = 24 * 3600

VERIFIED_ROLE: str = "Verified"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    TIMED_OUT = "timed_out"
    REVOKED = "revoked"


@dataclasses.dataclass
class VerificationRequest:
    """One pending verification keyed by Discord user."""
    discord_id: str
    requested_at: float
    expires_at: float
    status: VerificationStatus = VerificationStatus.PENDING
    verified_at: t.Optional[float] = None

    def is_expired(self, *, now: float) -> bool:
        return now >= self.expires_at


def open_verification_request(*,
                                    discord_id: str,
                                    now: float
                                    ) -> VerificationRequest:
    return VerificationRequest(
        discord_id=discord_id,
        requested_at=now,
        expires_at=now + VERIFICATION_TIMEOUT_SECONDS,
    )


def maybe_timeout(req: VerificationRequest, *, now: float) -> bool:
    """Auto-kick if past timeout. Returns True if a state change."""
    if req.status != VerificationStatus.PENDING:
        return False
    if req.is_expired(now=now):
        req.status = VerificationStatus.TIMED_OUT
        return True
    return False


@dataclasses.dataclass(frozen=True)
class VerificationOutcome:
    discord_id: str
    granted_role: t.Optional[str]
    discord_access_token: t.Optional[Token]
    discord_refresh_token: t.Optional[Token]
    lsb_account_token: t.Optional[Token]
    launcher_download_link: t.Optional[str]
    reason: str


def complete_verification(req: VerificationRequest,
                              *,
                              now: float,
                              launcher_download_url: str,
                              ) -> VerificationOutcome:
    """Player clicked the verification button → run the OAuth path.

    Returns the OAuth tokens + the launcher link the user is DM'd.
    """
    if req.status == VerificationStatus.TIMED_OUT:
        return VerificationOutcome(
            discord_id=req.discord_id, granted_role=None,
            discord_access_token=None, discord_refresh_token=None,
            lsb_account_token=None, launcher_download_link=None,
            reason="verification request already timed out",
        )
    if req.status == VerificationStatus.REVOKED:
        return VerificationOutcome(
            discord_id=req.discord_id, granted_role=None,
            discord_access_token=None, discord_refresh_token=None,
            lsb_account_token=None, launcher_download_link=None,
            reason="verification request revoked",
        )
    # Treat PENDING and already-VERIFIED as both completing
    # idempotently so a double-click doesn't error.
    req.status = VerificationStatus.VERIFIED
    req.verified_at = now
    access = mint_token(kind=TokenKind.DISCORD_ACCESS,
                          discord_id=req.discord_id, now=now)
    refresh = mint_token(kind=TokenKind.DISCORD_REFRESH,
                            discord_id=req.discord_id, now=now)
    lsb = mint_token(kind=TokenKind.LSB_ACCOUNT,
                        discord_id=req.discord_id, now=now)
    return VerificationOutcome(
        discord_id=req.discord_id,
        granted_role=VERIFIED_ROLE,
        discord_access_token=access,
        discord_refresh_token=refresh,
        lsb_account_token=lsb,
        launcher_download_link=launcher_download_url,
        reason="verified",
    )


def revoke_verification(req: VerificationRequest) -> None:
    """Owner forced /me re-verification or hardware-fingerprint mismatch."""
    req.status = VerificationStatus.REVOKED
