"""VR voice proximity — spatial voice with distance falloff.

A VR player talking out loud should be heard as if their
mouth is actually at their character's head position.
Two players standing next to a fountain in Bastok Markets
swapping strategy talk hear each other clearly. The same
conversation is INAUDIBLE to a player 30 yalms away.

This module owns:
    - per-player ListenerState (3D position + facing yaw)
    - per-talker SpeakerState (3D position + power_db)
    - the falloff curve that turns range into volume
    - per-listener channel selection (proximity, party,
      linkshell — players in your party always heard
      regardless of distance, mixed at constant volume)

Falloff:
    0..2y       full volume (1.0 mix)
    2..30y      linear roll-off from 1.0 down to 0.05
    30y+        muted (0.0)

Voice channels (each player can subscribe/unsubscribe):
    PROXIMITY   spatial mode (default ON)
    PARTY       party-only voice (ON if in a party)
    LINKSHELL   linkshell-only voice (player toggles)
    SHOUT       proximity but with 3x range — RP/event
                callouts. Off by default (you don't want
                random shouts intruding when leveling).

resolve(listener_id, talker_id) -> Optional[VoiceMix]
returns the volume + channel the listener will receive
the talker on, or None if they can't hear them at all.

PARTY/LINKSHELL ALWAYS WIN over proximity if the talker
is in those channels — full clarity for tactical comms.
PROXIMITY is the fallback. SHOUT is treated like proximity
with a bigger range — it doesn't override party but gives
the talker reach to non-party listeners nearby.

Public surface
--------------
    VoiceChannel enum
    SpeakerState dataclass (frozen) — per-talker pose
    ListenerState dataclass (frozen) — per-listener pose
    VoiceMix dataclass (frozen) — channel + volume (0..1)
    VrVoiceProximity
        .update_speaker(player_id, x, y, z, channels)
            -> bool
        .update_listener(player_id, x, y, z) -> bool
        .toggle_channel(player_id, channel, enabled)
            -> bool
        .resolve(listener_id, talker_id) -> Optional[VoiceMix]
        .audible_to(listener_id) -> list[(talker_id, VoiceMix)]
        .clear(player_id) -> bool
"""
from __future__ import annotations

import dataclasses
import enum
import math
import typing as t


_FULL_VOLUME_RANGE_M = 2.0
_AUDIBLE_RANGE_M = 30.0
_MIN_AUDIBLE_VOL = 0.05
_SHOUT_MULTIPLIER = 3.0


class VoiceChannel(str, enum.Enum):
    PROXIMITY = "proximity"
    PARTY = "party"
    LINKSHELL = "linkshell"
    SHOUT = "shout"


@dataclasses.dataclass(frozen=True)
class SpeakerState:
    player_id: str
    x: float
    y: float
    z: float
    channels: frozenset[VoiceChannel]


@dataclasses.dataclass(frozen=True)
class ListenerState:
    player_id: str
    x: float
    y: float
    z: float


@dataclasses.dataclass(frozen=True)
class VoiceMix:
    channel: VoiceChannel
    volume: float


def _dist(a, b) -> float:
    return math.sqrt(
        (a.x - b.x) ** 2
        + (a.y - b.y) ** 2
        + (a.z - b.z) ** 2
    )


def _proximity_volume(d: float, range_m: float) -> float:
    if d <= _FULL_VOLUME_RANGE_M:
        return 1.0
    if d >= range_m:
        return 0.0
    # Linear falloff between full-volume and edge
    span = range_m - _FULL_VOLUME_RANGE_M
    frac = (d - _FULL_VOLUME_RANGE_M) / span
    vol = 1.0 - frac * (1.0 - _MIN_AUDIBLE_VOL)
    return round(vol, 3)


@dataclasses.dataclass
class VrVoiceProximity:
    _speakers: dict[str, SpeakerState] = dataclasses.field(
        default_factory=dict,
    )
    _listeners: dict[str, ListenerState] = dataclasses.field(
        default_factory=dict,
    )
    # listener_id -> set of channels they SUBSCRIBE to
    _subscriptions: dict[
        str, set[VoiceChannel],
    ] = dataclasses.field(default_factory=dict)
    # listener_id -> party_id (membership lookup)
    _party_of: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    # listener_id -> linkshell_id
    _ls_of: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    def update_speaker(
        self, *, player_id: str, x: float, y: float, z: float,
        channels: t.Iterable[VoiceChannel],
    ) -> bool:
        if not player_id:
            return False
        ch = frozenset(channels)
        if not ch:
            return False
        self._speakers[player_id] = SpeakerState(
            player_id=player_id, x=x, y=y, z=z, channels=ch,
        )
        return True

    def update_listener(
        self, *, player_id: str, x: float, y: float, z: float,
    ) -> bool:
        if not player_id:
            return False
        self._listeners[player_id] = ListenerState(
            player_id=player_id, x=x, y=y, z=z,
        )
        # Default subscriptions on first sight
        if player_id not in self._subscriptions:
            self._subscriptions[player_id] = {
                VoiceChannel.PROXIMITY, VoiceChannel.PARTY,
                VoiceChannel.LINKSHELL,
            }
        return True

    def toggle_channel(
        self, *, player_id: str,
        channel: VoiceChannel, enabled: bool,
    ) -> bool:
        if player_id not in self._subscriptions:
            self._subscriptions[player_id] = set()
        subs = self._subscriptions[player_id]
        was_in = channel in subs
        if enabled:
            subs.add(channel)
        else:
            subs.discard(channel)
        return (channel in subs) != was_in

    def set_party(
        self, *, player_id: str, party_id: t.Optional[str],
    ) -> None:
        if party_id is None:
            self._party_of.pop(player_id, None)
        else:
            self._party_of[player_id] = party_id

    def set_linkshell(
        self, *, player_id: str, linkshell_id: t.Optional[str],
    ) -> None:
        if linkshell_id is None:
            self._ls_of.pop(player_id, None)
        else:
            self._ls_of[player_id] = linkshell_id

    def resolve(
        self, *, listener_id: str, talker_id: str,
    ) -> t.Optional[VoiceMix]:
        if listener_id == talker_id:
            return None
        speaker = self._speakers.get(talker_id)
        listener = self._listeners.get(listener_id)
        if speaker is None or listener is None:
            return None
        subs = self._subscriptions.get(listener_id, set())
        # PARTY wins if both share a party AND listener
        # subscribes AND speaker is broadcasting it
        if (VoiceChannel.PARTY in speaker.channels
                and VoiceChannel.PARTY in subs):
            l_party = self._party_of.get(listener_id)
            t_party = self._party_of.get(talker_id)
            if l_party is not None and l_party == t_party:
                return VoiceMix(
                    channel=VoiceChannel.PARTY, volume=1.0,
                )
        # LINKSHELL same logic
        if (VoiceChannel.LINKSHELL in speaker.channels
                and VoiceChannel.LINKSHELL in subs):
            l_ls = self._ls_of.get(listener_id)
            t_ls = self._ls_of.get(talker_id)
            if l_ls is not None and l_ls == t_ls:
                return VoiceMix(
                    channel=VoiceChannel.LINKSHELL,
                    volume=1.0,
                )
        # PROXIMITY (or SHOUT) — distance-falloff
        d = _dist(listener, speaker)
        if (VoiceChannel.SHOUT in speaker.channels
                and VoiceChannel.PROXIMITY in subs):
            vol = _proximity_volume(
                d, _AUDIBLE_RANGE_M * _SHOUT_MULTIPLIER,
            )
            if vol > 0:
                return VoiceMix(
                    channel=VoiceChannel.SHOUT, volume=vol,
                )
        if (VoiceChannel.PROXIMITY in speaker.channels
                and VoiceChannel.PROXIMITY in subs):
            vol = _proximity_volume(d, _AUDIBLE_RANGE_M)
            if vol > 0:
                return VoiceMix(
                    channel=VoiceChannel.PROXIMITY,
                    volume=vol,
                )
        return None

    def audible_to(
        self, *, listener_id: str,
    ) -> list[tuple[str, VoiceMix]]:
        out = []
        for tid in self._speakers:
            mix = self.resolve(
                listener_id=listener_id, talker_id=tid,
            )
            if mix is not None:
                out.append((tid, mix))
        out.sort(key=lambda pair: -pair[1].volume)
        return out

    def clear(self, *, player_id: str) -> bool:
        touched = False
        if player_id in self._speakers:
            del self._speakers[player_id]
            touched = True
        if player_id in self._listeners:
            del self._listeners[player_id]
            touched = True
        if player_id in self._subscriptions:
            del self._subscriptions[player_id]
            touched = True
        self._party_of.pop(player_id, None)
        self._ls_of.pop(player_id, None)
        return touched


__all__ = [
    "VoiceChannel", "SpeakerState", "ListenerState",
    "VoiceMix", "VrVoiceProximity",
]
