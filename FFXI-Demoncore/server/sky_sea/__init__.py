"""Sky / Sea — endgame zones with key item gates and HNM windows.

Tu'Lia (Sky) and Al'Taieu (Sea) are gated by key items earned via
ANNM (Avatar / Notorious Monster) chains. Each god HNM has a 21h
pop window after the previous kill; pop is enabled by trading the
"god seal" key item which is itself farmed from the prior tier.

Public surface
--------------
    GodTier enum
    GodSpec catalog
    PopWindow tracker per God
    SkySeaState per server
        .record_kill(god_id)
        .can_pop(god_id, now)
        .pop(god_id, now)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


POP_WINDOW_SECONDS = 21 * 60 * 60        # 21 hours retail


class GodTier(int, enum.Enum):
    AVATAR = 1                           # base prereq
    SKY = 2                              # Tu'Lia tier
    SEA = 3                              # Al'Taieu tier


@dataclasses.dataclass(frozen=True)
class GodSpec:
    god_id: str
    name: str
    tier: GodTier
    zone_id: str
    prereq_god_id: t.Optional[str] = None    # must have killed this first
    seal_key_item: str = ""              # key item required to pop
    drops_key_item: str = ""             # what next-tier needs


# Sample catalog
SKY_SEA_CATALOG: tuple[GodSpec, ...] = (
    # Sky (Tu'Lia) HNMs
    GodSpec("byakko", "Byakko", GodTier.SKY,
            zone_id="ru_aun_gardens",
            seal_key_item="byakkos_hai",
            drops_key_item="byakko_token"),
    GodSpec("seiryu", "Seiryu", GodTier.SKY,
            zone_id="ru_aun_gardens",
            seal_key_item="seiryus_kote",
            drops_key_item="seiryu_token"),
    GodSpec("suzaku", "Suzaku", GodTier.SKY,
            zone_id="ru_aun_gardens",
            seal_key_item="suzakus_sune_ate",
            drops_key_item="suzaku_token"),
    GodSpec("genbu", "Genbu", GodTier.SKY,
            zone_id="ru_aun_gardens",
            seal_key_item="genbus_kabuto",
            drops_key_item="genbu_token"),
    GodSpec("kirin", "Kirin", GodTier.SKY,
            zone_id="ru_aun_gardens",
            prereq_god_id="byakko",     # actually requires all 4 in retail
            seal_key_item="kirins_pop_token",
            drops_key_item="rajas_ring_chunk"),
    # Sea (Al'Taieu) HNMs
    GodSpec("absolute_virtue", "Absolute Virtue",
            GodTier.SEA, zone_id="al_taieu",
            prereq_god_id="kirin",
            seal_key_item="av_invitation",
            drops_key_item="virtue_stone"),
    GodSpec("jailer_of_love", "Jailer of Love",
            GodTier.SEA, zone_id="al_taieu",
            prereq_god_id="absolute_virtue",
            seal_key_item="seal_of_love",
            drops_key_item=""),
)

GOD_BY_ID: dict[str, GodSpec] = {g.god_id: g for g in SKY_SEA_CATALOG}


@dataclasses.dataclass
class _GodKillRecord:
    last_kill_tick: int = -1


@dataclasses.dataclass(frozen=True)
class PopResult:
    accepted: bool
    god_id: str
    next_window_opens_at: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass
class SkySeaState:
    server_id: str
    _kills: dict[str, _GodKillRecord] = dataclasses.field(
        default_factory=dict, repr=False,
    )
    _alive: set[str] = dataclasses.field(default_factory=set)

    def record_kill(self, *, god_id: str, now_tick: int) -> bool:
        if god_id not in GOD_BY_ID:
            return False
        rec = self._kills.setdefault(god_id, _GodKillRecord())
        rec.last_kill_tick = now_tick
        self._alive.discard(god_id)
        return True

    def can_pop(
        self, *, god_id: str, party_seal_items: t.Sequence[str],
        now_tick: int,
    ) -> PopResult:
        spec = GOD_BY_ID.get(god_id)
        if spec is None:
            return PopResult(False, god_id, reason="unknown god")
        if spec.seal_key_item and \
                spec.seal_key_item not in party_seal_items:
            return PopResult(False, god_id,
                             reason=f"missing key item: "
                                    f"{spec.seal_key_item}")
        if spec.prereq_god_id and spec.prereq_god_id not in self._kills:
            return PopResult(False, god_id,
                             reason=f"prereq {spec.prereq_god_id} "
                                    "not killed")
        if god_id in self._alive:
            return PopResult(False, god_id, reason="already alive")
        rec = self._kills.get(god_id)
        if rec is not None:
            opens_at = rec.last_kill_tick + POP_WINDOW_SECONDS
            if now_tick < opens_at:
                return PopResult(
                    False, god_id,
                    next_window_opens_at=opens_at,
                    reason="pop window not open",
                )
        return PopResult(True, god_id)

    def pop(
        self, *, god_id: str, party_seal_items: t.Sequence[str],
        now_tick: int,
    ) -> PopResult:
        check = self.can_pop(
            god_id=god_id,
            party_seal_items=party_seal_items,
            now_tick=now_tick,
        )
        if not check.accepted:
            return check
        self._alive.add(god_id)
        return PopResult(True, god_id)

    def is_alive(self, god_id: str) -> bool:
        return god_id in self._alive


__all__ = [
    "POP_WINDOW_SECONDS",
    "GodTier", "GodSpec",
    "SKY_SEA_CATALOG", "GOD_BY_ID",
    "PopResult", "SkySeaState",
]
