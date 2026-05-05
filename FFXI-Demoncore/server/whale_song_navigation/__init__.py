"""Whale song navigation — abyss safe-route decoder.

Whales sing through the abyss biomes on long, slow patterns
that map the safest paths through pressure pockets and the
DROWNED_PRINCES patrol corridors. A trained ear (BRD or SCH)
can DECODE the song and unlock a SAFE_ROUTE: a sequence of
zone hops that bypass the worst encounters.

Songs come in MOTIFS — repeating phrases of low-frequency
notes. Decoding requires the player to listen for at least
LISTEN_DURATION_SECONDS while a motif is active, then submit
their interpretation (a sequence of NOTE values). If the
sequence matches the motif's canonical answer, the route is
unlocked for the player.

Job gate: only BRD or SCH may decode. Other jobs can listen
but submit_decode rejects them.

Public surface
--------------
    NoteValue enum            LOW / MID / HIGH / OFF
    MotifProfile dataclass
    DecodeResult dataclass
    WhaleSongNavigation
        .register_motif(motif_id, notes, route_zones)
        .start_listen(player_id, motif_id, job, now_seconds)
        .submit_decode(player_id, notes, now_seconds) -> DecodeResult
        .has_route(player_id, route_zones)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NoteValue(str, enum.Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    OFF = "off"


LISTEN_DURATION_SECONDS = 30
DECODER_JOBS = ("BRD", "SCH")


@dataclasses.dataclass(frozen=True)
class MotifProfile:
    motif_id: str
    notes: tuple[NoteValue, ...]
    route_zones: tuple[str, ...]


@dataclasses.dataclass
class _Listen:
    player_id: str
    motif_id: str
    job: str
    started_at: int


@dataclasses.dataclass(frozen=True)
class DecodeResult:
    accepted: bool
    motif_id: t.Optional[str] = None
    route_unlocked: bool = False
    route_zones: tuple[str, ...] = ()
    reason: t.Optional[str] = None


@dataclasses.dataclass
class WhaleSongNavigation:
    _motifs: dict[str, MotifProfile] = dataclasses.field(
        default_factory=dict,
    )
    _listens: dict[str, _Listen] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> set of route signatures unlocked
    _routes: dict[str, set[tuple[str, ...]]] = dataclasses.field(
        default_factory=dict,
    )

    def register_motif(
        self, *, motif_id: str,
        notes: tuple[NoteValue, ...],
        route_zones: tuple[str, ...],
    ) -> bool:
        if not motif_id or not notes or len(route_zones) < 2:
            return False
        if motif_id in self._motifs:
            return False
        # validate every note value
        for n in notes:
            if n not in (NoteValue.LOW, NoteValue.MID,
                         NoteValue.HIGH, NoteValue.OFF):
                return False
        self._motifs[motif_id] = MotifProfile(
            motif_id=motif_id,
            notes=tuple(notes),
            route_zones=tuple(route_zones),
        )
        return True

    def start_listen(
        self, *, player_id: str,
        motif_id: str,
        job: str,
        now_seconds: int,
    ) -> bool:
        if not player_id:
            return False
        if motif_id not in self._motifs:
            return False
        if job not in DECODER_JOBS:
            return False
        self._listens[player_id] = _Listen(
            player_id=player_id,
            motif_id=motif_id,
            job=job,
            started_at=now_seconds,
        )
        return True

    def submit_decode(
        self, *, player_id: str,
        notes: tuple[NoteValue, ...],
        now_seconds: int,
    ) -> DecodeResult:
        listen = self._listens.pop(player_id, None)
        if listen is None:
            return DecodeResult(False, reason="not listening")
        elapsed = now_seconds - listen.started_at
        if elapsed < LISTEN_DURATION_SECONDS:
            return DecodeResult(
                False, motif_id=listen.motif_id,
                reason="listened too briefly",
            )
        motif = self._motifs[listen.motif_id]
        if tuple(notes) != motif.notes:
            return DecodeResult(
                False, motif_id=listen.motif_id,
                reason="incorrect interpretation",
            )
        # success — unlock the route
        sig = motif.route_zones
        self._routes.setdefault(player_id, set()).add(sig)
        return DecodeResult(
            accepted=True,
            motif_id=listen.motif_id,
            route_unlocked=True,
            route_zones=sig,
        )

    def has_route(
        self, *, player_id: str,
        route_zones: tuple[str, ...],
    ) -> bool:
        return tuple(route_zones) in self._routes.get(player_id, set())

    def total_motifs(self) -> int:
        return len(self._motifs)


__all__ = [
    "NoteValue", "MotifProfile", "DecodeResult",
    "WhaleSongNavigation",
    "LISTEN_DURATION_SECONDS", "DECODER_JOBS",
]
