"""Screen effects — camera-bound post-process layer.

Whatever the engine renders, this layer paints over the
top: a hit shake, a magic-burst flash, a knockout fadeout,
the heat-haze ripple of a dragon breath, the static
crackle of paralyze. Each effect has an intensity curve
sampled over its duration, a blend mode, and a flag
telling the camera whether it affects only the player's
view (PoV first-person) or the whole shot (everyone in the
party). The system holds a list of currently active
effects per player and ticks them forward in time; on each
sample call it returns the right intensity at the right t.

Stacking: most effects compose. Hit shakes layer with each
other, blur from intoxication runs alongside silence
muffle. Two effects are full-screen takeovers and block
stacking — KO_FADEOUT and DRAGON_BREATH_HEAT_HAZE — because
the screen is already saturated; piling more on top only
muddies the read.

IntensityCurve is a sparse list of (t, value) keyframes;
sample(t) does a linear interpolation between adjacent
keyframes and clamps to the endpoints. That keeps the
data tiny (a hit-shake is 4 keyframes) while still letting
us author non-linear ramps for the dramatic effects (KO is
a slow ease-out vignette).

Public surface
--------------
    EffectKind enum
    BlendMode enum
    IntensityCurve dataclass (frozen)
    ScreenEffect dataclass (frozen)
    ActiveEffectHandle dataclass (frozen)
    ScreenEffectSystem
"""
from __future__ import annotations

import dataclasses
import enum
import itertools
import typing as t


class EffectKind(enum.Enum):
    HIT_SHAKE_LIGHT = "hit_shake_light"
    HIT_SHAKE_MEDIUM = "hit_shake_medium"
    HIT_SHAKE_HEAVY = "hit_shake_heavy"
    HIT_SHAKE_ULTRA = "hit_shake_ultra"
    MB_FLASH = "mb_flash"
    KO_FADEOUT = "ko_fadeout"
    BLEED_OUT_RED = "bleed_out_red"
    LEVITATE_BOB = "levitate_bob"
    INTOXICATION_BLUR = "intoxication_blur"
    DRAGON_BREATH_HEAT_HAZE = "dragon_breath_heat_haze"
    UNDEATH_GRAIN = "undeath_grain"
    HASTE_TIME_DIALATION = "haste_time_dialation"
    SLOW_TIME_THICKEN = "slow_time_thicken"
    SLEEP_VIGNETTE = "sleep_vignette"
    SILENCE_MUFFLE_VISUAL = "silence_muffle_visual"
    CHARM_PINK_HAZE = "charm_pink_haze"
    PARALYZE_STATIC_CRACKLE = "paralyze_static_crackle"
    PETRIFICATION_GREY_FREEZE = "petrification_grey_freeze"


class BlendMode(enum.Enum):
    ADD = "add"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"


# Effects that take over the screen and block any further
# effect stacking on the same player.
_EXCLUSIVE: frozenset[EffectKind] = frozenset({
    EffectKind.KO_FADEOUT,
    EffectKind.DRAGON_BREATH_HEAT_HAZE,
})


@dataclasses.dataclass(frozen=True)
class IntensityCurve:
    curve_id: str
    keyframes: tuple[tuple[float, float], ...]

    def sample(self, t: float) -> float:
        if not self.keyframes:
            return 0.0
        if t <= self.keyframes[0][0]:
            return self.keyframes[0][1]
        if t >= self.keyframes[-1][0]:
            return self.keyframes[-1][1]
        # Linear interpolate.
        for (t0, v0), (t1, v1) in zip(
            self.keyframes, self.keyframes[1:],
        ):
            if t0 <= t <= t1:
                if t1 == t0:
                    return v0
                lerp = (t - t0) / (t1 - t0)
                return v0 + lerp * (v1 - v0)
        return self.keyframes[-1][1]


@dataclasses.dataclass(frozen=True)
class ScreenEffect:
    effect_id: str
    kind: EffectKind
    intensity_curve: IntensityCurve
    duration_s: float
    blend_mode: BlendMode
    affects_player_only: bool


@dataclasses.dataclass(frozen=True)
class ActiveEffectHandle:
    handle_id: str
    effect_id: str
    player_id: str
    elapsed_s: float


# Internal active record (mutable). The handle is the
# external snapshot.
@dataclasses.dataclass
class _ActiveRecord:
    handle_id: str
    effect: ScreenEffect
    player_id: str
    elapsed_s: float

    def snapshot(self) -> ActiveEffectHandle:
        return ActiveEffectHandle(
            handle_id=self.handle_id,
            effect_id=self.effect.effect_id,
            player_id=self.player_id,
            elapsed_s=self.elapsed_s,
        )


@dataclasses.dataclass
class ScreenEffectSystem:
    _effects: dict[str, ScreenEffect] = dataclasses.field(
        default_factory=dict,
    )
    _active: dict[str, _ActiveRecord] = dataclasses.field(
        default_factory=dict,
    )
    _by_player: dict[
        str, list[str],
    ] = dataclasses.field(default_factory=dict)
    _next_handle: t.Iterator[int] = dataclasses.field(
        default_factory=lambda: itertools.count(1),
    )

    # ------------------------------------------------- register
    def register_effect(self, effect: ScreenEffect) -> None:
        if not effect.effect_id:
            raise ValueError("effect_id required")
        if effect.duration_s <= 0:
            raise ValueError("duration_s must be > 0")
        if effect.effect_id in self._effects:
            raise ValueError(
                f"duplicate effect_id: {effect.effect_id}",
            )
        self._effects[effect.effect_id] = effect

    def get_effect(self, effect_id: str) -> ScreenEffect:
        if effect_id not in self._effects:
            raise KeyError(f"unknown effect: {effect_id}")
        return self._effects[effect_id]

    # ------------------------------------------------- apply
    def apply(
        self, effect_id: str, target_player_id: str,
    ) -> ActiveEffectHandle:
        eff = self.get_effect(effect_id)
        # Block stacking when a takeover is already active or
        # we are trying to add a takeover on top of others.
        for h_id in self._by_player.get(target_player_id, []):
            existing = self._active[h_id].effect
            if not self.is_stackable_with(eff.kind, existing.kind):
                raise RuntimeError(
                    f"effect {eff.kind.value} not stackable "
                    f"with active {existing.kind.value} for "
                    f"player {target_player_id}",
                )
        handle_id = f"h{next(self._next_handle)}"
        rec = _ActiveRecord(
            handle_id=handle_id, effect=eff,
            player_id=target_player_id, elapsed_s=0.0,
        )
        self._active[handle_id] = rec
        self._by_player.setdefault(
            target_player_id, [],
        ).append(handle_id)
        return rec.snapshot()

    # ------------------------------------------------- sample
    def sample(
        self, handle: ActiveEffectHandle, t_s: float,
    ) -> float:
        if handle.handle_id not in self._active:
            raise KeyError(f"unknown handle: {handle.handle_id}")
        rec = self._active[handle.handle_id]
        if t_s < 0:
            return 0.0
        if t_s > rec.effect.duration_s:
            return rec.effect.intensity_curve.sample(
                rec.effect.duration_s,
            )
        return rec.effect.intensity_curve.sample(t_s)

    # ------------------------------------------------- queries
    def all_active_for(
        self, player_id: str,
    ) -> tuple[ActiveEffectHandle, ...]:
        return tuple(
            self._active[hid].snapshot()
            for hid in self._by_player.get(player_id, [])
        )

    def is_stackable_with(
        self, a: EffectKind, b: EffectKind,
    ) -> bool:
        if a in _EXCLUSIVE or b in _EXCLUSIVE:
            return False
        return True

    def tick(self, dt: float) -> tuple[ActiveEffectHandle, ...]:
        if dt < 0:
            raise ValueError("dt must be >= 0")
        expired: list[ActiveEffectHandle] = []
        # advance all
        for rec in self._active.values():
            rec.elapsed_s += dt
        # find expired
        to_remove = [
            hid for hid, rec in self._active.items()
            if rec.elapsed_s >= rec.effect.duration_s
        ]
        for hid in to_remove:
            rec = self._active.pop(hid)
            expired.append(rec.snapshot())
            lst = self._by_player.get(rec.player_id, [])
            if hid in lst:
                lst.remove(hid)
        return tuple(expired)

    def active_count(self) -> int:
        return len(self._active)


# ---------------------------------------------------------
# Default catalog.
# ---------------------------------------------------------

def _shake_curve(curve_id: str, peak: float) -> IntensityCurve:
    # Quick rise, sustain, decay.
    return IntensityCurve(
        curve_id=curve_id,
        keyframes=(
            (0.0, 0.0),
            (0.05, peak),
            (0.15, peak * 0.6),
            (0.30, 0.0),
        ),
    )


_DEFAULTS: tuple[
    tuple[EffectKind, IntensityCurve, float, BlendMode, bool],
    ...,
] = (
    (EffectKind.HIT_SHAKE_LIGHT,
        _shake_curve("c_hsl", 0.3), 0.30, BlendMode.ADD, True),
    (EffectKind.HIT_SHAKE_MEDIUM,
        _shake_curve("c_hsm", 0.6), 0.35, BlendMode.ADD, True),
    (EffectKind.HIT_SHAKE_HEAVY,
        _shake_curve("c_hsh", 0.9), 0.45, BlendMode.ADD, True),
    (EffectKind.HIT_SHAKE_ULTRA,
        _shake_curve("c_hsu", 1.2), 0.60, BlendMode.ADD, True),
    (EffectKind.MB_FLASH,
        IntensityCurve(
            curve_id="c_mbf",
            keyframes=(
                (0.0, 0.0), (0.10, 1.0),
                (0.30, 0.5), (0.80, 0.0),
            ),
        ), 0.80, BlendMode.SCREEN, False),
    (EffectKind.KO_FADEOUT,
        IntensityCurve(
            curve_id="c_ko",
            keyframes=(
                (0.0, 0.0), (0.5, 0.6), (1.2, 1.0),
            ),
        ), 1.20, BlendMode.MULTIPLY, True),
    (EffectKind.BLEED_OUT_RED,
        IntensityCurve(
            curve_id="c_bleed",
            keyframes=(
                (0.0, 0.4), (3.0, 0.4), (6.0, 0.0),
            ),
        ), 6.0, BlendMode.OVERLAY, True),
    (EffectKind.LEVITATE_BOB,
        IntensityCurve(
            curve_id="c_lev",
            keyframes=(
                (0.0, 0.0), (1.0, 0.3), (2.0, 0.0),
                (3.0, 0.3), (4.0, 0.0),
            ),
        ), 4.0, BlendMode.ADD, True),
    (EffectKind.INTOXICATION_BLUR,
        IntensityCurve(
            curve_id="c_intox",
            keyframes=(
                (0.0, 0.5), (10.0, 0.5), (15.0, 0.0),
            ),
        ), 15.0, BlendMode.OVERLAY, True),
    (EffectKind.DRAGON_BREATH_HEAT_HAZE,
        IntensityCurve(
            curve_id="c_drhaze",
            keyframes=(
                (0.0, 0.0), (0.5, 1.0),
                (2.0, 0.7), (3.0, 0.0),
            ),
        ), 3.0, BlendMode.OVERLAY, False),
    (EffectKind.UNDEATH_GRAIN,
        IntensityCurve(
            curve_id="c_undeath",
            keyframes=(
                (0.0, 0.4), (10.0, 0.4),
            ),
        ), 10.0, BlendMode.OVERLAY, True),
    (EffectKind.HASTE_TIME_DIALATION,
        IntensityCurve(
            curve_id="c_haste",
            keyframes=(
                (0.0, 0.0), (0.5, 0.3),
                (180.0, 0.3), (180.5, 0.0),
            ),
        ), 180.5, BlendMode.SCREEN, True),
    (EffectKind.SLOW_TIME_THICKEN,
        IntensityCurve(
            curve_id="c_slow",
            keyframes=(
                (0.0, 0.0), (0.5, 0.3),
                (180.0, 0.3), (180.5, 0.0),
            ),
        ), 180.5, BlendMode.MULTIPLY, True),
    (EffectKind.SLEEP_VIGNETTE,
        IntensityCurve(
            curve_id="c_sleep",
            keyframes=(
                (0.0, 0.0), (1.0, 0.7), (60.0, 0.7),
            ),
        ), 60.0, BlendMode.MULTIPLY, True),
    (EffectKind.SILENCE_MUFFLE_VISUAL,
        IntensityCurve(
            curve_id="c_silence",
            keyframes=(
                (0.0, 0.4), (60.0, 0.4),
            ),
        ), 60.0, BlendMode.MULTIPLY, True),
    (EffectKind.CHARM_PINK_HAZE,
        IntensityCurve(
            curve_id="c_charm",
            keyframes=(
                (0.0, 0.0), (1.0, 0.4), (60.0, 0.4),
            ),
        ), 60.0, BlendMode.OVERLAY, True),
    (EffectKind.PARALYZE_STATIC_CRACKLE,
        IntensityCurve(
            curve_id="c_para",
            keyframes=(
                (0.0, 0.6), (0.2, 0.0), (0.4, 0.6),
                (0.6, 0.0), (60.0, 0.0),
            ),
        ), 60.0, BlendMode.ADD, True),
    (EffectKind.PETRIFICATION_GREY_FREEZE,
        IntensityCurve(
            curve_id="c_petri",
            keyframes=(
                (0.0, 0.0), (1.5, 1.0), (60.0, 1.0),
            ),
        ), 60.0, BlendMode.MULTIPLY, True),
)


def populate_default_library(sys: ScreenEffectSystem) -> int:
    n = 0
    for kind, curve, dur, blend, player_only in _DEFAULTS:
        sys.register_effect(ScreenEffect(
            effect_id=kind.value,
            kind=kind,
            intensity_curve=curve,
            duration_s=dur,
            blend_mode=blend,
            affects_player_only=player_only,
        ))
        n += 1
    return n


__all__ = [
    "EffectKind",
    "BlendMode",
    "IntensityCurve",
    "ScreenEffect",
    "ActiveEffectHandle",
    "ScreenEffectSystem",
    "populate_default_library",
]
