"""Deterministic RNG pool — seeded streams for every random source.

Why this exists
---------------
Demoncore wants determinism for two reasons:

  1. Reproducibility. When a player reports "the boss critic gave me
     a Mythological roll on the wrong fight," we need to be able to
     replay the scene from the same seed and observe the same dice.

  2. Server-side anti-tampering. Every stream is keyed by
     ``(world_seed, stream_name)`` so that distinct concerns
     (loot drops, fomor variation, boss-critic gates) don't share
     entropy. A drop roll cannot "consume" entropy that would have
     determined a fomor's gear color.

The pool is a pure-Python wrapper over ``random.Random`` — no global
state. Each named stream gets its own ``Random`` instance, deterministic
from the world seed. Tests use ``RngPool(world_seed=0xABCDEF)`` and get
fully reproducible draws.

Public surface
--------------
    StreamId               named-tuple alias for stream identifier
    RngPool                container managing per-stream Random objects
        .stream(name)      get the ``random.Random`` for a stream
        .randint(...)      convenience inclusive integer draw
        .uniform(...)      convenience float draw
        .choice(...)       convenience list pick
        .roll_pct(...)     0-100 inclusive integer (FFXI convention)
        .gate(...)         True/False from a 0-1 probability
        .reset(name)       re-seed one stream from world_seed
        .reset_all()       re-seed every stream from world_seed
"""
from __future__ import annotations

import dataclasses
import hashlib
import random
import typing as t


# Type alias — keeping it stringly-typed for now, but consumers can
# define enums in their own module if they want stricter checks.
StreamId = str


# Reserved well-known stream names. Modules SHOULD use these so the
# replay system can match scene events to the right stream.
STREAM_LOOT_DROPS = "loot_drops"
STREAM_BOSS_CRITIC = "boss_critic"
STREAM_FOMOR_GEAR = "fomor_gear"
STREAM_FOMOR_APPEARANCE = "fomor_appearance"
STREAM_ENCOUNTER_GEN = "encounter_gen"
STREAM_WEATHER = "weather"
STREAM_ACHIEVEMENT_TIE_BREAK = "achievement_tie_break"

KNOWN_STREAMS: tuple[StreamId, ...] = (
    STREAM_LOOT_DROPS,
    STREAM_BOSS_CRITIC,
    STREAM_FOMOR_GEAR,
    STREAM_FOMOR_APPEARANCE,
    STREAM_ENCOUNTER_GEN,
    STREAM_WEATHER,
    STREAM_ACHIEVEMENT_TIE_BREAK,
)


def _derive_stream_seed(world_seed: int, name: StreamId) -> int:
    """Combine world_seed + stream name into a 64-bit seed.

    SHA-256 keeps the derivation collision-resistant: two streams
    cannot accidentally end up with the same seed, no matter how
    similar their names look.
    """
    payload = f"{world_seed}:{name}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    # Take 8 bytes -> 64-bit unsigned int. Plenty of headroom.
    return int.from_bytes(digest[:8], "big", signed=False)


@dataclasses.dataclass
class RngPool:
    """Per-stream deterministic random.Random container."""

    world_seed: int
    _streams: dict[StreamId, random.Random] = dataclasses.field(
        default_factory=dict, repr=False
    )

    def stream(self, name: StreamId) -> random.Random:
        """Get (lazily create) the random.Random for *name*."""
        rng = self._streams.get(name)
        if rng is None:
            rng = random.Random(_derive_stream_seed(self.world_seed, name))
            self._streams[name] = rng
        return rng

    # -- convenience draws -------------------------------------------

    def randint(self, name: StreamId, lo: int, hi: int) -> int:
        """Inclusive integer in [lo, hi]."""
        return self.stream(name).randint(lo, hi)

    def uniform(self, name: StreamId, lo: float, hi: float) -> float:
        """Float in [lo, hi]."""
        return self.stream(name).uniform(lo, hi)

    def choice(self, name: StreamId, items: t.Sequence[t.Any]) -> t.Any:
        """Pick one item. Raises IndexError on empty sequence."""
        if not items:
            raise IndexError("cannot choice() from empty sequence")
        return self.stream(name).choice(list(items))

    def roll_pct(self, name: StreamId) -> int:
        """0..100 inclusive — FFXI's classic percent roll convention."""
        return self.stream(name).randint(0, 100)

    def gate(self, name: StreamId, probability: float) -> bool:
        """True with the given probability in [0, 1]."""
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be in [0, 1]")
        if probability == 0.0:
            return False
        if probability == 1.0:
            return True
        return self.stream(name).random() < probability

    # -- replay control ----------------------------------------------

    def reset(self, name: StreamId) -> None:
        """Re-seed a single stream back to its world-seed-derived
        initial state. Used for replays."""
        self._streams[name] = random.Random(
            _derive_stream_seed(self.world_seed, name)
        )

    def reset_all(self) -> None:
        """Re-seed every active stream back to its initial state."""
        for name in list(self._streams.keys()):
            self.reset(name)

    # -- introspection ------------------------------------------------

    def active_streams(self) -> tuple[StreamId, ...]:
        """All stream names this pool has handed out so far."""
        return tuple(sorted(self._streams.keys()))


__all__ = [
    "StreamId",
    "STREAM_LOOT_DROPS", "STREAM_BOSS_CRITIC", "STREAM_FOMOR_GEAR",
    "STREAM_FOMOR_APPEARANCE", "STREAM_ENCOUNTER_GEN",
    "STREAM_WEATHER", "STREAM_ACHIEVEMENT_TIE_BREAK",
    "KNOWN_STREAMS",
    "RngPool",
]
