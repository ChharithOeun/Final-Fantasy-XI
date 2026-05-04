"""Beastman shadow dynamis — Shadowlands timed-instance Dynamis.

Each beastman city has a SHADOW DYNAMIS counterpart — a parallel
zone where the city's history is acted out against waves of
HUME ARMY ECHOES (canonical adventurer races as the invading
horde). Players enter with a HOURGLASS (key item) and must
clear waves before the time pool runs out.

Each WAVE has:
  - wave_index (0..N)
  - mob count
  - hourglass_extension (seconds added on clear)
  - boss_wave flag (final wave + currency drop)

Currency drop is SHADOW BYTNES (parallel to Dynamis hundred/
byne pieces). Used to upgrade beastman relic gear.

Public surface
--------------
    DynamisCity enum
    InstanceState enum   STAGED / RUNNING / CLEARED / EXPIRED
    Wave dataclass
    DynamisInstance dataclass
    EnterResult / ClearResult dataclasses
    BeastmanShadowDynamis
        .register_zone(city, total_waves, base_hourglass_seconds)
        .enter(instance_id, city, party_ids, now_seconds)
        .clear_wave(instance_id, wave_index, now_seconds)
        .award_currency(instance_id, player_id)
        .state_for(instance_id, now_seconds)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DynamisCity(str, enum.Enum):
    OZTROJA = "oztroja"
    PALBOROUGH = "palborough"
    HALVUNG = "halvung"
    ARRAPAGO = "arrapago"


class InstanceState(str, enum.Enum):
    STAGED = "staged"
    RUNNING = "running"
    CLEARED = "cleared"
    EXPIRED = "expired"


_BOSS_DROP_BYTNES = 100
_PER_WAVE_BYTNES = 25
_DEFAULT_EXTENSION = 180  # seconds added per cleared wave


@dataclasses.dataclass(frozen=True)
class Wave:
    wave_index: int
    mob_count: int
    is_boss_wave: bool
    hourglass_extension_seconds: int = _DEFAULT_EXTENSION


@dataclasses.dataclass(frozen=True)
class ZoneConfig:
    city: DynamisCity
    total_waves: int
    base_hourglass_seconds: int
    waves: tuple[Wave, ...]


@dataclasses.dataclass
class DynamisInstance:
    instance_id: str
    city: DynamisCity
    party_ids: tuple[str, ...]
    state: InstanceState
    started_at: int
    expires_at: int
    waves_cleared: int = 0
    currency_claimed: set[str] = dataclasses.field(default_factory=set)
    currency_pool: int = 0


@dataclasses.dataclass(frozen=True)
class EnterResult:
    accepted: bool
    instance_id: str
    expires_at: int
    state: InstanceState
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ClearResult:
    accepted: bool
    instance_id: str
    waves_cleared: int
    expires_at: int
    state: InstanceState
    bytnes_dropped: int = 0
    reason: t.Optional[str] = None


@dataclasses.dataclass(frozen=True)
class CurrencyResult:
    accepted: bool
    bytnes_awarded: int
    reason: t.Optional[str] = None


def _build_waves(total: int) -> tuple[Wave, ...]:
    waves: list[Wave] = []
    for i in range(total):
        is_boss = (i == total - 1)
        mob_count = 6 + i * 2
        if is_boss:
            mob_count = 1  # one big boss
        waves.append(
            Wave(
                wave_index=i,
                mob_count=mob_count,
                is_boss_wave=is_boss,
            ),
        )
    return tuple(waves)


@dataclasses.dataclass
class BeastmanShadowDynamis:
    _zones: dict[DynamisCity, ZoneConfig] = dataclasses.field(
        default_factory=dict,
    )
    _instances: dict[str, DynamisInstance] = dataclasses.field(
        default_factory=dict,
    )

    def register_zone(
        self, *, city: DynamisCity,
        total_waves: int,
        base_hourglass_seconds: int,
    ) -> t.Optional[ZoneConfig]:
        if city in self._zones:
            return None
        if total_waves <= 0 or base_hourglass_seconds <= 0:
            return None
        cfg = ZoneConfig(
            city=city,
            total_waves=total_waves,
            base_hourglass_seconds=base_hourglass_seconds,
            waves=_build_waves(total_waves),
        )
        self._zones[city] = cfg
        return cfg

    def enter(
        self, *, instance_id: str,
        city: DynamisCity,
        party_ids: tuple[str, ...],
        now_seconds: int,
    ) -> EnterResult:
        cfg = self._zones.get(city)
        if cfg is None:
            return EnterResult(
                False, instance_id, 0,
                InstanceState.STAGED,
                reason="unknown zone",
            )
        if instance_id in self._instances:
            return EnterResult(
                False, instance_id, 0,
                InstanceState.STAGED,
                reason="instance id already used",
            )
        if not party_ids:
            return EnterResult(
                False, instance_id, 0,
                InstanceState.STAGED,
                reason="empty party",
            )
        expires = now_seconds + cfg.base_hourglass_seconds
        inst = DynamisInstance(
            instance_id=instance_id,
            city=city,
            party_ids=tuple(party_ids),
            state=InstanceState.RUNNING,
            started_at=now_seconds,
            expires_at=expires,
        )
        self._instances[instance_id] = inst
        return EnterResult(
            accepted=True,
            instance_id=instance_id,
            expires_at=expires,
            state=InstanceState.RUNNING,
        )

    def clear_wave(
        self, *, instance_id: str,
        wave_index: int,
        now_seconds: int,
    ) -> ClearResult:
        inst = self._instances.get(instance_id)
        if inst is None:
            return ClearResult(
                False, instance_id, 0, 0,
                InstanceState.STAGED,
                reason="unknown instance",
            )
        if inst.state != InstanceState.RUNNING:
            return ClearResult(
                False, instance_id, inst.waves_cleared,
                inst.expires_at, inst.state,
                reason="instance not running",
            )
        if now_seconds >= inst.expires_at:
            inst.state = InstanceState.EXPIRED
            return ClearResult(
                False, instance_id, inst.waves_cleared,
                inst.expires_at, inst.state,
                reason="hourglass expired",
            )
        cfg = self._zones[inst.city]
        if wave_index != inst.waves_cleared:
            return ClearResult(
                False, instance_id, inst.waves_cleared,
                inst.expires_at, inst.state,
                reason="out-of-order wave",
            )
        if wave_index >= cfg.total_waves:
            return ClearResult(
                False, instance_id, inst.waves_cleared,
                inst.expires_at, inst.state,
                reason="no such wave",
            )
        wave = cfg.waves[wave_index]
        inst.waves_cleared += 1
        inst.expires_at += wave.hourglass_extension_seconds
        bytnes = (
            _BOSS_DROP_BYTNES if wave.is_boss_wave
            else _PER_WAVE_BYTNES
        )
        inst.currency_pool += bytnes
        if wave.is_boss_wave:
            inst.state = InstanceState.CLEARED
        return ClearResult(
            accepted=True,
            instance_id=instance_id,
            waves_cleared=inst.waves_cleared,
            expires_at=inst.expires_at,
            state=inst.state,
            bytnes_dropped=bytnes,
        )

    def award_currency(
        self, *, instance_id: str, player_id: str,
    ) -> CurrencyResult:
        inst = self._instances.get(instance_id)
        if inst is None:
            return CurrencyResult(
                False, 0, reason="unknown instance",
            )
        if inst.state != InstanceState.CLEARED:
            return CurrencyResult(
                False, 0, reason="instance not cleared",
            )
        if player_id not in inst.party_ids:
            return CurrencyResult(
                False, 0, reason="not in party",
            )
        if player_id in inst.currency_claimed:
            return CurrencyResult(
                False, 0, reason="already claimed",
            )
        # Even split across party
        share = inst.currency_pool // len(inst.party_ids)
        inst.currency_claimed.add(player_id)
        return CurrencyResult(
            accepted=True, bytnes_awarded=share,
        )

    def state_for(
        self, *, instance_id: str, now_seconds: int,
    ) -> InstanceState:
        inst = self._instances.get(instance_id)
        if inst is None:
            return InstanceState.STAGED
        if (
            inst.state == InstanceState.RUNNING
            and now_seconds >= inst.expires_at
        ):
            inst.state = InstanceState.EXPIRED
        return inst.state

    def get_instance(
        self, instance_id: str,
    ) -> t.Optional[DynamisInstance]:
        return self._instances.get(instance_id)

    def total_zones(self) -> int:
        return len(self._zones)


__all__ = [
    "DynamisCity", "InstanceState",
    "Wave", "ZoneConfig", "DynamisInstance",
    "EnterResult", "ClearResult", "CurrencyResult",
    "BeastmanShadowDynamis",
]
