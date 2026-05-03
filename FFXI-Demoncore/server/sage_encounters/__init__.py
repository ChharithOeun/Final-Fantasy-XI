"""Sage encounters — rare wandering AI mentors with cryptic gifts.

Once in a long while, in a remote zone after a hard-fought
fight or a dangerous trek, the world produces a SAGE — an old
Tarutaru hermit, a cloaked elvaan ascetic, an exiled mithra
herbalist. The sage offers ONE OF: a cryptic hint, a one-shot
buff, a key item, or a direction toward a hidden NM.

Sages are rare and per-(player, sage_kind) gated — meeting the
same archetype again costs months of game-time. The system tracks
which sages a player has met and only spawns one when the player
hasn't seen any sage recently and the zone-encounter check passes.

Public surface
--------------
    SageArchetype enum
    GiftKind enum
    SageOffer dataclass
    SageEncounterResult dataclass
    SageEncounters
        .roll_for_encounter(player_id, zone_id, ...) -> Optional[Sage]
        .accept_offer(player_id, sage_id) -> SageOffer
        .player_has_met(player_id, archetype)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default cooldown between sages for a single player.
DEFAULT_SAGE_COOLDOWN_SECONDS = 30 * 24 * 3600  # 30 game-days
DEFAULT_REMOTE_ZONES: tuple[str, ...] = (
    "uleguerand_range", "attohwa_chasm", "ruaun_gardens",
    "yhoator_jungle_deep", "kuftal_tunnel_far",
    "carpenters_landing_north",
)


class SageArchetype(str, enum.Enum):
    TARUTARU_HERMIT = "tarutaru_hermit"
    ELVAAN_ASCETIC = "elvaan_ascetic"
    MITHRA_HERBALIST = "mithra_herbalist"
    GALKA_LOREKEEPER = "galka_lorekeeper"
    HUME_RECLUSE = "hume_recluse"


class GiftKind(str, enum.Enum):
    CRYPTIC_HINT = "cryptic_hint"
    ONESHOT_BUFF = "oneshot_buff"
    KEY_ITEM = "key_item"
    NM_DIRECTION = "nm_direction"
    OLD_RECIPE = "old_recipe"


# Default offer table per archetype — one offer kind each.
_OFFER_BY_ARCHETYPE: dict[SageArchetype, GiftKind] = {
    SageArchetype.TARUTARU_HERMIT: GiftKind.CRYPTIC_HINT,
    SageArchetype.ELVAAN_ASCETIC: GiftKind.ONESHOT_BUFF,
    SageArchetype.MITHRA_HERBALIST: GiftKind.OLD_RECIPE,
    SageArchetype.GALKA_LOREKEEPER: GiftKind.KEY_ITEM,
    SageArchetype.HUME_RECLUSE: GiftKind.NM_DIRECTION,
}


@dataclasses.dataclass(frozen=True)
class SageOffer:
    sage_id: str
    archetype: SageArchetype
    gift_kind: GiftKind
    payload: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    note: str = ""


@dataclasses.dataclass
class _SageRecord:
    sage_id: str
    archetype: SageArchetype
    zone_id: str
    spawned_for_player_id: str
    spawned_at_seconds: float
    accepted: bool = False


@dataclasses.dataclass(frozen=True)
class SageEncounterResult:
    accepted: bool
    sage: t.Optional[_SageRecord] = None
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SageEncounters:
    cooldown_seconds: float = DEFAULT_SAGE_COOLDOWN_SECONDS
    remote_zones: tuple[str, ...] = DEFAULT_REMOTE_ZONES
    _last_seen_by_player: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    _archetypes_met: dict[
        str, set[SageArchetype],
    ] = dataclasses.field(default_factory=dict)
    _sages: dict[str, _SageRecord] = dataclasses.field(
        default_factory=dict,
    )
    _next_id: int = 0

    def roll_for_encounter(
        self, *, player_id: str, zone_id: str,
        archetype: SageArchetype,
        now_seconds: float = 0.0,
        force: bool = False,
    ) -> SageEncounterResult:
        # Zone gate
        if not force and zone_id not in self.remote_zones:
            return SageEncounterResult(
                False, reason="not a remote zone",
            )
        # Cooldown gate
        last = self._last_seen_by_player.get(player_id)
        if (
            not force
            and last is not None
            and (now_seconds - last) < self.cooldown_seconds
        ):
            return SageEncounterResult(
                False, reason="player on sage cooldown",
            )
        # Archetype-already-met gate
        met = self._archetypes_met.get(player_id, set())
        if not force and archetype in met:
            return SageEncounterResult(
                False,
                reason="player has already met this archetype",
            )
        sid = f"sage_{self._next_id}"
        self._next_id += 1
        rec = _SageRecord(
            sage_id=sid, archetype=archetype,
            zone_id=zone_id,
            spawned_for_player_id=player_id,
            spawned_at_seconds=now_seconds,
        )
        self._sages[sid] = rec
        self._last_seen_by_player[player_id] = now_seconds
        self._archetypes_met.setdefault(
            player_id, set(),
        ).add(archetype)
        return SageEncounterResult(
            accepted=True, sage=rec,
        )

    def accept_offer(
        self, *, player_id: str, sage_id: str,
    ) -> t.Optional[SageOffer]:
        rec = self._sages.get(sage_id)
        if rec is None:
            return None
        if rec.spawned_for_player_id != player_id:
            return None
        if rec.accepted:
            return None
        rec.accepted = True
        gift_kind = _OFFER_BY_ARCHETYPE[rec.archetype]
        return SageOffer(
            sage_id=sage_id, archetype=rec.archetype,
            gift_kind=gift_kind,
            payload={"zone_id": rec.zone_id},
        )

    def player_has_met(
        self, *, player_id: str,
        archetype: SageArchetype,
    ) -> bool:
        return archetype in self._archetypes_met.get(
            player_id, set(),
        )

    def total_sages_spawned(self) -> int:
        return len(self._sages)


__all__ = [
    "DEFAULT_SAGE_COOLDOWN_SECONDS",
    "DEFAULT_REMOTE_ZONES",
    "SageArchetype", "GiftKind",
    "SageOffer", "SageEncounterResult",
    "SageEncounters",
]
