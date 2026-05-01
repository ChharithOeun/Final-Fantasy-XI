"""LSB account record — discord_id linked to LSB token + game state.

Per AUTH_DISCORD.md: 'extend the existing schema with a discord_id
and linked_at column'. The LSB account token is what the modified
launcher sends instead of the PlayOnline ID/POL handshake.
"""
from __future__ import annotations

import dataclasses
import typing as t

from .tokens import Token


@dataclasses.dataclass
class LinkedAccount:
    """One row in the extended `accounts` table."""
    account_id: str
    discord_id: str
    linked_at: float
    lsb_token: t.Optional[Token] = None
    hardware_fingerprint: t.Optional[str] = None
    is_banned: bool = False
    ban_reason: t.Optional[str] = None
    ban_origin: t.Optional[str] = None      # 'discord' | 'game_side' | None


class AccountRegistry:
    """In-memory registry stub of the LSB accounts table."""

    def __init__(self) -> None:
        self._by_discord: dict[str, LinkedAccount] = {}
        self._by_account: dict[str, LinkedAccount] = {}

    def link(self,
                *,
                account_id: str,
                discord_id: str,
                now: float,
                lsb_token: t.Optional[Token] = None,
                hardware_fingerprint: t.Optional[str] = None,
                ) -> LinkedAccount:
        """Doc: 'A character is already a person to its Discord guild.
        Linking the game account to that Discord identity is a small
        step that pays back enormously.'

        Idempotent: re-linking the same Discord-id refreshes
        linked_at + token.
        """
        if discord_id in self._by_discord:
            existing = self._by_discord[discord_id]
            if existing.account_id != account_id:
                raise ValueError(
                    f"discord {discord_id} already linked to "
                    f"{existing.account_id}; can't relink to {account_id}")
            existing.linked_at = now
            if lsb_token is not None:
                existing.lsb_token = lsb_token
            if hardware_fingerprint is not None:
                existing.hardware_fingerprint = hardware_fingerprint
            return existing
        account = LinkedAccount(
            account_id=account_id, discord_id=discord_id,
            linked_at=now, lsb_token=lsb_token,
            hardware_fingerprint=hardware_fingerprint,
        )
        self._by_discord[discord_id] = account
        self._by_account[account_id] = account
        return account

    def by_discord(self, discord_id: str) -> t.Optional[LinkedAccount]:
        return self._by_discord.get(discord_id)

    def by_account(self, account_id: str) -> t.Optional[LinkedAccount]:
        return self._by_account.get(account_id)

    def __len__(self) -> int:
        return len(self._by_discord)

    # ------------------------------------------------------------------
    # Ban propagation
    # ------------------------------------------------------------------

    def apply_ban(self,
                     *,
                     discord_id: str,
                     reason: str,
                     origin: str,
                     ) -> bool:
        account = self._by_discord.get(discord_id)
        if account is None:
            return False
        account.is_banned = True
        account.ban_reason = reason
        account.ban_origin = origin
        return True

    def lift_ban(self, discord_id: str) -> bool:
        account = self._by_discord.get(discord_id)
        if account is None or not account.is_banned:
            return False
        account.is_banned = False
        account.ban_reason = None
        account.ban_origin = None
        return True
