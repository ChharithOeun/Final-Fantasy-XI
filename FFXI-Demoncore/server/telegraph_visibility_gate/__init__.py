"""Telegraph visibility gate — sight is EARNED, not passive.

The earlier telegraph_reading_skill module assumed every
player saw boss telegraphs by default and that perception
XP simply made the warning longer. That was wrong: it
gives away too much for free. The redesign:

    Without an active VISIBILITY SOURCE, a player sees ONLY:
        - audio cues / voice lines (audible_callouts)
        - the boss's hand gestures / wind-up animation
        - environment reactions (boss_ability_tells)

    To get the actual graphical TELEGRAPH OVERLAY (the
    AOE shape, the cone, the ring marker), the player
    must be inside an active visibility source:
        GEO_FORESIGHT     a GEO indi/geo bubble spell
        BARD_FORESIGHT    a BRD song
        SKILLCHAIN_BONUS  closing a skillchain grants
                           8 seconds of free telegraphs to
                           all chain participants
        OTHER             custom designer-registered
                           sources (key item, scholar
                           addendum, etc.)

The telegraph_reading_skill bonuses (warning_bonus_seconds,
tag_bonus_pct, prediction_count) ONLY APPLY when at least
one source is currently active for the player. A MASTER-
tier player without any source still has to read the boss
by sight and ear — they just react better when SOMEONE
gives them visibility.

This module owns the visibility ledger. Other modules
(geo_foresight_bubble, bard_foresight_etude,
skillchain_telegraph_reward) call grant_visibility() and
revoke_visibility() to register sources. Combat layer
calls is_visible() and effective_warning_bonus() to know
what to render and how early.

Public surface
--------------
    VisibilitySource enum
    VisibilityGrant dataclass (frozen)
    TelegraphVisibilityGate
        .grant_visibility(player_id, source, expires_at,
                           granted_by) -> bool
        .revoke_visibility(player_id, source) -> bool
        .is_visible(player_id, now_seconds) -> bool
        .active_sources(player_id, now_seconds)
            -> tuple[VisibilitySource, ...]
        .effective_warning_bonus(player_id,
                                  base_bonus_seconds,
                                  now_seconds) -> float
        .clear(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class VisibilitySource(str, enum.Enum):
    GEO_FORESIGHT = "geo_foresight"
    BARD_FORESIGHT = "bard_foresight"
    SKILLCHAIN_BONUS = "skillchain_bonus"
    OTHER = "other"


@dataclasses.dataclass(frozen=True)
class VisibilityGrant:
    player_id: str
    source: VisibilitySource
    granted_at: int
    expires_at: int
    granted_by: t.Optional[str] = None   # caster, chain_id, etc.


@dataclasses.dataclass
class TelegraphVisibilityGate:
    # player_id -> source -> VisibilityGrant
    _grants: dict[str, dict[VisibilitySource, VisibilityGrant]] = (
        dataclasses.field(default_factory=dict)
    )

    def grant_visibility(
        self, *, player_id: str, source: VisibilitySource,
        granted_at: int, expires_at: int,
        granted_by: t.Optional[str] = None,
    ) -> bool:
        if not player_id or expires_at <= granted_at:
            return False
        bag = self._grants.setdefault(player_id, {})
        existing = bag.get(source)
        # if existing grant is stronger (later expiration), keep it
        if existing is not None and existing.expires_at >= expires_at:
            return False
        bag[source] = VisibilityGrant(
            player_id=player_id, source=source,
            granted_at=granted_at, expires_at=expires_at,
            granted_by=granted_by,
        )
        return True

    def revoke_visibility(
        self, *, player_id: str, source: VisibilitySource,
    ) -> bool:
        bag = self._grants.get(player_id)
        if bag is None or source not in bag:
            return False
        del bag[source]
        return True

    def active_sources(
        self, *, player_id: str, now_seconds: int,
    ) -> tuple[VisibilitySource, ...]:
        bag = self._grants.get(player_id, {})
        out: list[VisibilitySource] = []
        # opportunistic GC of expired grants
        expired_keys: list[VisibilitySource] = []
        for src, g in bag.items():
            if now_seconds < g.expires_at:
                out.append(src)
            else:
                expired_keys.append(src)
        for k in expired_keys:
            del bag[k]
        return tuple(out)

    def is_visible(
        self, *, player_id: str, now_seconds: int,
    ) -> bool:
        return len(self.active_sources(
            player_id=player_id, now_seconds=now_seconds,
        )) > 0

    def effective_warning_bonus(
        self, *, player_id: str,
        base_bonus_seconds: float, now_seconds: int,
    ) -> float:
        """If the player has visibility, their reading-skill
        bonus applies. Otherwise it's 0 (they still get
        audio/gesture cues — but no graphical
        early-warning advantage)."""
        if self.is_visible(
            player_id=player_id, now_seconds=now_seconds,
        ):
            return base_bonus_seconds
        return 0.0

    def clear(self, *, player_id: str) -> bool:
        if player_id in self._grants:
            self._grants[player_id].clear()
            return True
        return False


__all__ = [
    "VisibilitySource", "VisibilityGrant",
    "TelegraphVisibilityGate",
]
