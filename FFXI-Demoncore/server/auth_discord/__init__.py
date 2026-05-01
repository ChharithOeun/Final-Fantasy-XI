"""Discord OAuth + chharbot moderation per AUTH_DISCORD.md.

PlayOnline is dead in this remake. Authentication, account
management, role gating, ban appeals, even patch announcements —
all of it routes through Discord. chharbot is the moderator.

Module layout:
    tokens.py        - 4 token kinds + lifetimes + slide_lsb_token
    oauth_flow.py    - VerificationRequest + 24h timeout + complete
    account.py       - LinkedAccount + AccountRegistry + ban propagation
    moderation.py    - 7-trigger -> action table + appeal resolver
    audit_log.py     - JSONL audit + /why history + /override marking
    threat_model.py  - hardware fingerprint + phone-ban + gate-closed
"""
from .account import AccountRegistry, LinkedAccount
from .audit_log import AuditEntry, AuditLog
from .moderation import (
    ModAction,
    ModerationDecision,
    Trigger,
    decide,
    resolve_appeal,
)
from .oauth_flow import (
    VERIFICATION_TIMEOUT_SECONDS,
    VERIFIED_ROLE,
    VerificationOutcome,
    VerificationRequest,
    VerificationStatus,
    complete_verification,
    maybe_timeout,
    open_verification_request,
    revoke_verification,
)
from .threat_model import (
    GateState,
    PhoneBanRegistry,
    PhoneBanResult,
    ReplayDecision,
    TokenReplayCheck,
    check_hardware_fingerprint,
)
from .tokens import (
    DISCORD_ACCESS_TOKEN_LIFETIME_S,
    DISCORD_REFRESH_TOKEN_LIFETIME_S,
    LSB_ACCOUNT_TOKEN_LIFETIME_S,
    SESSION_TOKEN_LIFETIME_S,
    Token,
    TokenKind,
    lifetime_for,
    mint_token,
    revoke,
    slide_lsb_token,
)

__all__ = [
    # tokens
    "TokenKind", "Token",
    "DISCORD_ACCESS_TOKEN_LIFETIME_S",
    "DISCORD_REFRESH_TOKEN_LIFETIME_S",
    "LSB_ACCOUNT_TOKEN_LIFETIME_S",
    "SESSION_TOKEN_LIFETIME_S",
    "lifetime_for", "mint_token", "slide_lsb_token", "revoke",
    # oauth_flow
    "VerificationStatus", "VerificationRequest",
    "VerificationOutcome",
    "VERIFICATION_TIMEOUT_SECONDS", "VERIFIED_ROLE",
    "open_verification_request", "maybe_timeout",
    "complete_verification", "revoke_verification",
    # account
    "LinkedAccount", "AccountRegistry",
    # moderation
    "Trigger", "ModAction", "ModerationDecision",
    "decide", "resolve_appeal",
    # audit_log
    "AuditEntry", "AuditLog",
    # threat_model
    "ReplayDecision", "TokenReplayCheck",
    "check_hardware_fingerprint",
    "PhoneBanRegistry", "PhoneBanResult",
    "GateState",
]
