"""Boss minion summons — adds spawned mid-fight.

Bosses summon waves of MINION ADDS during the fight: at HP
thresholds, at fixed timers, after specific abilities, or in
response to player actions (interrupting a cast, sneaking past
guards). Adds inherit a soft-link to the boss — they despawn
when the boss dies, and some bosses regenerate HP from add
proximity (rallying effect).

Trigger kinds
-------------
    HP_THRESHOLD       — fires when boss HP crosses a band
    TIMER              — fixed cadence (every N seconds)
    ABILITY_CAST       — fires after the boss uses a named ability
    PLAYER_RESPONSE    — fires when players do something
                         specific (silence the boss, etc.)

Add archetypes
--------------
    SUICIDAL_BOMBER    self-detonates after delay
    HEALER             cures the boss
    ELEMENTALIST       casts spells; soft target for MB
    HEAVY_GUARD        body-blocks party from boss
    FAST_HARASSER      speeds toward casters

Public surface
--------------
    SummonTriggerKind enum
    AddArchetype enum
    SummonRule dataclass
    BossSummonState dataclass
    SummonRegistry
        .register_boss(boss_id, rules)
        .on_hp_change(boss_id, hp_pct, now) -> tuple[Add,...]
        .on_timer_tick(boss_id, now) -> tuple[Add,...]
        .on_ability_cast(boss_id, ability_id, now)
        .on_player_response(boss_id, response, now)
        .on_boss_death(boss_id) — despawns all live adds
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class SummonTriggerKind(str, enum.Enum):
    HP_THRESHOLD = "hp_threshold"
    TIMER = "timer"
    ABILITY_CAST = "ability_cast"
    PLAYER_RESPONSE = "player_response"


class AddArchetype(str, enum.Enum):
    SUICIDAL_BOMBER = "suicidal_bomber"
    HEALER = "healer"
    ELEMENTALIST = "elementalist"
    HEAVY_GUARD = "heavy_guard"
    FAST_HARASSER = "fast_harasser"


@dataclasses.dataclass(frozen=True)
class SummonRule:
    rule_id: str
    trigger_kind: SummonTriggerKind
    archetype: AddArchetype
    count: int = 1
    # HP_THRESHOLD: fires when HP crosses 'hp_pct' from above.
    hp_pct: t.Optional[int] = None
    # TIMER: fires every 'period_seconds' from boss spawn.
    period_seconds: t.Optional[float] = None
    # ABILITY_CAST: ability id that triggers this rule.
    ability_id: t.Optional[str] = None
    # PLAYER_RESPONSE: response token that triggers.
    response_id: t.Optional[str] = None
    # Cooldown — how often this rule can re-fire (game seconds).
    cooldown_seconds: float = 60.0
    notes: str = ""


@dataclasses.dataclass(frozen=True)
class Add:
    add_id: str
    boss_id: str
    archetype: AddArchetype
    spawned_at_seconds: float
    rule_id: str


@dataclasses.dataclass
class BossSummonState:
    boss_id: str
    rules: tuple[SummonRule, ...]
    last_hp_pct_observed: int = 100
    spawned_at_seconds: float = 0.0
    # rule_id -> last fire timestamp (for cooldown)
    _last_fire: dict[str, float] = dataclasses.field(
        default_factory=dict,
    )
    live_add_ids: set[str] = dataclasses.field(
        default_factory=set,
    )
    next_add_id: int = 0


@dataclasses.dataclass
class SummonRegistry:
    _bosses: dict[str, BossSummonState] = dataclasses.field(
        default_factory=dict,
    )
    _all_adds: dict[str, Add] = dataclasses.field(
        default_factory=dict,
    )

    def register_boss(
        self, *, boss_id: str,
        rules: t.Iterable[SummonRule],
        spawned_at_seconds: float = 0.0,
    ) -> BossSummonState:
        state = BossSummonState(
            boss_id=boss_id, rules=tuple(rules),
            spawned_at_seconds=spawned_at_seconds,
        )
        self._bosses[boss_id] = state
        return state

    def state(self, boss_id: str) -> t.Optional[BossSummonState]:
        return self._bosses.get(boss_id)

    def _can_fire(
        self, *, state: BossSummonState, rule: SummonRule,
        now_seconds: float,
    ) -> bool:
        last = state._last_fire.get(rule.rule_id)
        if last is None:
            return True
        return (now_seconds - last) >= rule.cooldown_seconds

    def _spawn_adds(
        self, *, state: BossSummonState, rule: SummonRule,
        now_seconds: float,
    ) -> tuple[Add, ...]:
        if not self._can_fire(
            state=state, rule=rule, now_seconds=now_seconds,
        ):
            return ()
        out: list[Add] = []
        for _ in range(max(1, rule.count)):
            aid = f"{state.boss_id}_add_{state.next_add_id}"
            state.next_add_id += 1
            add = Add(
                add_id=aid, boss_id=state.boss_id,
                archetype=rule.archetype,
                spawned_at_seconds=now_seconds,
                rule_id=rule.rule_id,
            )
            self._all_adds[aid] = add
            state.live_add_ids.add(aid)
            out.append(add)
        state._last_fire[rule.rule_id] = now_seconds
        return tuple(out)

    def on_hp_change(
        self, *, boss_id: str, hp_pct: int,
        now_seconds: float,
    ) -> tuple[Add, ...]:
        state = self._bosses.get(boss_id)
        if state is None:
            return ()
        spawned: list[Add] = []
        for rule in state.rules:
            if rule.trigger_kind != SummonTriggerKind.HP_THRESHOLD:
                continue
            if rule.hp_pct is None:
                continue
            # Crossing band: previous > threshold, current <= threshold
            if (
                state.last_hp_pct_observed > rule.hp_pct
                and hp_pct <= rule.hp_pct
            ):
                spawned.extend(
                    self._spawn_adds(
                        state=state, rule=rule,
                        now_seconds=now_seconds,
                    ),
                )
        state.last_hp_pct_observed = hp_pct
        return tuple(spawned)

    def on_timer_tick(
        self, *, boss_id: str, now_seconds: float,
    ) -> tuple[Add, ...]:
        state = self._bosses.get(boss_id)
        if state is None:
            return ()
        spawned: list[Add] = []
        elapsed = now_seconds - state.spawned_at_seconds
        for rule in state.rules:
            if rule.trigger_kind != SummonTriggerKind.TIMER:
                continue
            if rule.period_seconds is None:
                continue
            last = state._last_fire.get(rule.rule_id)
            if last is None:
                # First tick must be at least period_seconds in
                if elapsed >= rule.period_seconds:
                    spawned.extend(
                        self._spawn_adds(
                            state=state, rule=rule,
                            now_seconds=now_seconds,
                        ),
                    )
            else:
                if (now_seconds - last) >= rule.period_seconds:
                    spawned.extend(
                        self._spawn_adds(
                            state=state, rule=rule,
                            now_seconds=now_seconds,
                        ),
                    )
        return tuple(spawned)

    def on_ability_cast(
        self, *, boss_id: str, ability_id: str,
        now_seconds: float,
    ) -> tuple[Add, ...]:
        state = self._bosses.get(boss_id)
        if state is None:
            return ()
        spawned: list[Add] = []
        for rule in state.rules:
            if rule.trigger_kind != SummonTriggerKind.ABILITY_CAST:
                continue
            if rule.ability_id != ability_id:
                continue
            spawned.extend(
                self._spawn_adds(
                    state=state, rule=rule,
                    now_seconds=now_seconds,
                ),
            )
        return tuple(spawned)

    def on_player_response(
        self, *, boss_id: str, response_id: str,
        now_seconds: float,
    ) -> tuple[Add, ...]:
        state = self._bosses.get(boss_id)
        if state is None:
            return ()
        spawned: list[Add] = []
        for rule in state.rules:
            if rule.trigger_kind != SummonTriggerKind.PLAYER_RESPONSE:
                continue
            if rule.response_id != response_id:
                continue
            spawned.extend(
                self._spawn_adds(
                    state=state, rule=rule,
                    now_seconds=now_seconds,
                ),
            )
        return tuple(spawned)

    def on_boss_death(self, *, boss_id: str) -> tuple[str, ...]:
        state = self._bosses.get(boss_id)
        if state is None:
            return ()
        despawned = tuple(state.live_add_ids)
        for aid in despawned:
            self._all_adds.pop(aid, None)
        state.live_add_ids.clear()
        return despawned

    def live_adds_of(
        self, boss_id: str,
    ) -> tuple[Add, ...]:
        state = self._bosses.get(boss_id)
        if state is None:
            return ()
        return tuple(
            self._all_adds[aid]
            for aid in state.live_add_ids
            if aid in self._all_adds
        )

    def kill_add(self, *, add_id: str) -> bool:
        add = self._all_adds.pop(add_id, None)
        if add is None:
            return False
        state = self._bosses.get(add.boss_id)
        if state is not None:
            state.live_add_ids.discard(add_id)
        return True

    def total_bosses(self) -> int:
        return len(self._bosses)


__all__ = [
    "SummonTriggerKind", "AddArchetype",
    "SummonRule", "Add", "BossSummonState",
    "SummonRegistry",
]
