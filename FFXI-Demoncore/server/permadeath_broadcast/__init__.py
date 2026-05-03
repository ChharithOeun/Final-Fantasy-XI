"""Permadeath broadcast — server-wide announcements with sound.

Every permadeath fires a server-wide event: every online
player gets the message rendered as an event-style banner with
a distinct sound. Two flavors:

    MURDERED  — for victims who were NOT outlaw at time of death.
                Tone: somber. Sound: low-bell mourning chime.

    EXECUTED  — for victims who WERE outlaw at time of death.
                Tone: triumphant. Sound: justice-fanfare horn.

The killer can be a player (with title), a Notorious Monster,
or a regular Monster. Format strings include the title slot,
which renders as "[Title] PlayerName" if the player has one
equipped, or just "PlayerName" if not.

Public surface
--------------
    DeathFlavor enum (MURDERED / EXECUTED)
    KillerKind enum  (PLAYER / NM / MONSTER / ENVIRONMENT)
    KillerInfo / VictimInfo dataclasses
    PermadeathAnnouncement dataclass
    SoundCue enum
    render_announcement(...) -> PermadeathAnnouncement
    BroadcastBus       — subscribe / publish event listeners
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class DeathFlavor(str, enum.Enum):
    MURDERED = "murdered"
    EXECUTED = "executed"


class KillerKind(str, enum.Enum):
    PLAYER = "player"
    NM = "notorious_monster"
    MONSTER = "monster"
    ENVIRONMENT = "environment"   # falling damage, hostile zone, etc.


class SoundCue(str, enum.Enum):
    MOURNING_CHIME = "mourning_chime"
    JUSTICE_HORN = "justice_horn"


@dataclasses.dataclass(frozen=True)
class VictimInfo:
    name: str
    title: t.Optional[str] = None
    was_outlaw: bool = False


@dataclasses.dataclass(frozen=True)
class KillerInfo:
    name: str
    kind: KillerKind
    title: t.Optional[str] = None    # only meaningful for PLAYER


@dataclasses.dataclass(frozen=True)
class PermadeathAnnouncement:
    flavor: DeathFlavor
    sound: SoundCue
    message: str
    victim: VictimInfo
    killer: KillerInfo
    zone_id: t.Optional[str] = None
    timestamp_seconds: float = 0.0


def _format_actor(name: str, title: t.Optional[str]) -> str:
    if title:
        return f"[{title}] {name}"
    return name


def _format_killer(killer: KillerInfo) -> str:
    if killer.kind == KillerKind.PLAYER:
        return _format_actor(killer.name, killer.title)
    if killer.kind == KillerKind.NM:
        return f"the Notorious Monster {killer.name}"
    if killer.kind == KillerKind.MONSTER:
        return f"a {killer.name}"
    return f"the {killer.name}"   # ENVIRONMENT — "the Falling Stone"


def render_announcement(
    *, victim: VictimInfo, killer: KillerInfo,
    zone_id: t.Optional[str] = None,
    timestamp_seconds: float = 0.0,
) -> PermadeathAnnouncement:
    if victim.was_outlaw:
        flavor = DeathFlavor.EXECUTED
        sound = SoundCue.JUSTICE_HORN
        message = (
            f"The outlaw {_format_actor(victim.name, victim.title)} "
            f"has been executed by {_format_killer(killer)}."
        )
    else:
        flavor = DeathFlavor.MURDERED
        sound = SoundCue.MOURNING_CHIME
        message = (
            f"The adventurer {_format_actor(victim.name, victim.title)} "
            f"has been murdered by {_format_killer(killer)}."
        )
    return PermadeathAnnouncement(
        flavor=flavor, sound=sound, message=message,
        victim=victim, killer=killer,
        zone_id=zone_id, timestamp_seconds=timestamp_seconds,
    )


@dataclasses.dataclass
class BroadcastBus:
    """Subscriber pool for permadeath broadcasts. Anything
    server-wide that wants to react to a permadeath registers
    a callback and gets every announcement."""
    _subscribers: list[t.Callable[[PermadeathAnnouncement], None]] = (
        dataclasses.field(default_factory=list)
    )
    _history: list[PermadeathAnnouncement] = dataclasses.field(
        default_factory=list,
    )

    def subscribe(
        self, callback: t.Callable[[PermadeathAnnouncement], None],
    ) -> None:
        self._subscribers.append(callback)

    def unsubscribe(
        self, callback: t.Callable[[PermadeathAnnouncement], None],
    ) -> bool:
        try:
            self._subscribers.remove(callback)
        except ValueError:
            return False
        return True

    def publish(self, announcement: PermadeathAnnouncement) -> None:
        self._history.append(announcement)
        for cb in list(self._subscribers):
            cb(announcement)

    @property
    def history(self) -> tuple[PermadeathAnnouncement, ...]:
        return tuple(self._history)


__all__ = [
    "DeathFlavor", "KillerKind", "SoundCue",
    "VictimInfo", "KillerInfo",
    "PermadeathAnnouncement",
    "render_announcement",
    "BroadcastBus",
]
