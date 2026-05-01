"""Token lifecycle — 4 token kinds per AUTH_DISCORD.md.

| Token                 | Lifetime          | Stored where             |
|-----------------------|-------------------|--------------------------|
| Discord access token  | 7 days            | chharbot DB, encrypted   |
| Discord refresh token | indefinite        | chharbot DB, encrypted   |
| LSB account token     | 30 days, sliding  | LSB account DB, hashed   |
| Session token         | 12 hours          | In-memory, server-side   |
"""
from __future__ import annotations

import dataclasses
import enum
import secrets
import typing as t


# Lifetimes in seconds.
DISCORD_ACCESS_TOKEN_LIFETIME_S: int = 7 * 24 * 3600
LSB_ACCOUNT_TOKEN_LIFETIME_S: int = 30 * 24 * 3600
SESSION_TOKEN_LIFETIME_S: int = 12 * 3600
# Refresh token has no fixed expiry; revoke explicitly.
DISCORD_REFRESH_TOKEN_LIFETIME_S: t.Optional[int] = None


class TokenKind(str, enum.Enum):
    DISCORD_ACCESS = "discord_access"
    DISCORD_REFRESH = "discord_refresh"
    LSB_ACCOUNT = "lsb_account"
    SESSION = "session"


_LIFETIMES: dict[TokenKind, t.Optional[int]] = {
    TokenKind.DISCORD_ACCESS: DISCORD_ACCESS_TOKEN_LIFETIME_S,
    TokenKind.DISCORD_REFRESH: DISCORD_REFRESH_TOKEN_LIFETIME_S,
    TokenKind.LSB_ACCOUNT: LSB_ACCOUNT_TOKEN_LIFETIME_S,
    TokenKind.SESSION: SESSION_TOKEN_LIFETIME_S,
}


def lifetime_for(kind: TokenKind) -> t.Optional[int]:
    """Seconds. None for refresh (indefinite until revoked)."""
    return _LIFETIMES[kind]


@dataclasses.dataclass
class Token:
    """A minted token. Caller persists according to TokenKind storage."""
    kind: TokenKind
    value: str
    minted_at: float
    expires_at: t.Optional[float]   # None for indefinite
    discord_id: str
    revoked: bool = False
    last_refreshed_at: t.Optional[float] = None    # for sliding LSB token

    def is_active(self, *, now: float) -> bool:
        if self.revoked:
            return False
        if self.expires_at is None:
            return True
        return now < self.expires_at

    def remaining_seconds(self, *, now: float) -> float:
        if self.expires_at is None:
            return float("inf")
        return max(0.0, self.expires_at - now)


def mint_token(*,
                  kind: TokenKind,
                  discord_id: str,
                  now: float,
                  value: t.Optional[str] = None,
                  ) -> Token:
    """Mint a fresh token. Random URL-safe value if not provided."""
    if value is None:
        value = secrets.token_urlsafe(32)
    lifetime = lifetime_for(kind)
    expires_at = now + lifetime if lifetime is not None else None
    return Token(
        kind=kind, value=value, minted_at=now,
        expires_at=expires_at, discord_id=discord_id,
        last_refreshed_at=now if kind == TokenKind.LSB_ACCOUNT else None,
    )


def slide_lsb_token(token: Token, *, now: float) -> Token:
    """LSB account token uses a sliding 30-day window per the doc.

    Each time the launcher uses the token, slide the expiry forward
    by another 30 days. Returns the same token mutated.
    """
    if token.kind != TokenKind.LSB_ACCOUNT:
        raise ValueError("slide is only valid for LSB account tokens")
    if token.revoked:
        return token
    token.expires_at = now + LSB_ACCOUNT_TOKEN_LIFETIME_S
    token.last_refreshed_at = now
    return token


def revoke(token: Token) -> None:
    token.revoked = True
