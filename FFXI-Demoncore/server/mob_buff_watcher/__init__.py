"""Mob buff watcher — bosses observe player buff timers.

The Windower/Ashita "BuffMonitor" addon shows the player
which buffs are active on every party member, with timers.
This module gives mobs the same vision: a boss subscribes
to the buff list of the player on top of its hate list,
and reacts to specific patterns.

Examples of useful patterns:
    - "WHM has Stoneskin + Aquaveil up" → Dispel before
      Stun lands so the cast goes through
    - "PLD just used Sentinel" → switch target to someone
      who isn't immune to my big melee
    - "BLM has Manafont up" → use my dispel SP NOW
    - "alliance member just got Reraise" → focus that
      one to lock them out

A mob's reactive playbook is a list of (predicate,
action) pairs. The predicate inspects the buff list;
the action is opaque (the AI controller decides what
to do with it). This module is the OBSERVATION layer —
the controller layer sits above.

Public surface
--------------
    BuffSnapshot dataclass (frozen) — what the mob sees
    BuffPattern dataclass (frozen) — predicate + action
    MobBuffWatcher
        .observe(player_id, buff_ids, ts) -> bool
        .snapshot(player_id) -> Optional[BuffSnapshot]
        .register_pattern(mob_id, pattern) -> bool
        .check_patterns(mob_id, player_id)
            -> list[str]   (matched action_ids)
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass(frozen=True)
class BuffSnapshot:
    player_id: str
    buff_ids: tuple[str, ...]      # active buffs at observation time
    observed_at: int


# A predicate is a callable: (snapshot) -> bool.
# A pattern bundles a predicate with an opaque action_id
# the AI controller will dispatch on match.


@dataclasses.dataclass(frozen=True)
class BuffPattern:
    pattern_id: str
    predicate: t.Callable[[BuffSnapshot], bool]
    action_id: str    # opaque — controller chooses what to do


@dataclasses.dataclass
class MobBuffWatcher:
    _snapshots: dict[str, BuffSnapshot] = dataclasses.field(
        default_factory=dict,
    )
    # patterns indexed by mob_id; each mob has its own playbook
    _patterns: dict[str, list[BuffPattern]] = dataclasses.field(
        default_factory=dict,
    )

    def observe(
        self, *, player_id: str,
        buff_ids: t.Sequence[str], ts: int,
    ) -> bool:
        if not player_id:
            return False
        self._snapshots[player_id] = BuffSnapshot(
            player_id=player_id,
            buff_ids=tuple(buff_ids),
            observed_at=ts,
        )
        return True

    def snapshot(
        self, *, player_id: str,
    ) -> t.Optional[BuffSnapshot]:
        return self._snapshots.get(player_id)

    def register_pattern(
        self, *, mob_id: str, pattern: BuffPattern,
    ) -> bool:
        if not mob_id or not pattern.pattern_id:
            return False
        if not pattern.action_id:
            return False
        existing = self._patterns.setdefault(mob_id, [])
        if any(p.pattern_id == pattern.pattern_id for p in existing):
            return False
        existing.append(pattern)
        return True

    def check_patterns(
        self, *, mob_id: str, player_id: str,
    ) -> list[str]:
        snap = self._snapshots.get(player_id)
        if snap is None:
            return []
        patterns = self._patterns.get(mob_id, [])
        out: list[str] = []
        for p in patterns:
            try:
                if p.predicate(snap):
                    out.append(p.action_id)
            except Exception:
                # predicate failures are non-fatal — a
                # bad addon shouldn't crash the mob
                continue
        return out

    def clear_snapshot(self, *, player_id: str) -> bool:
        if player_id not in self._snapshots:
            return False
        del self._snapshots[player_id]
        return True

    def total_observed(self) -> int:
        return len(self._snapshots)


__all__ = [
    "BuffSnapshot", "BuffPattern", "MobBuffWatcher",
]
