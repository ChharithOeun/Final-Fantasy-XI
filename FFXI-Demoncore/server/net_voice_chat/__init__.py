"""Net voice chat — spatial voice with falloff, Opus codec,
Mumble-compatible protocol.

FFXI shipped without voice chat. Players ran TeamSpeak or
Ventrilo or just a separate Discord call. This module bakes
spatial voice *into the game world* — the goblin shouting
across the field gets attenuated by distance, the wall in
front of you damps reverb, the party channel ducks the
proximity channel so the healer's "WATCH OUT" cuts through.

The transport is Opus + Mumble's positional-audio wire
format. The server-side decisions live here: which
subscribers receive which packets, what gain to apply, and
which mute lists to honor.

Channels:
    ZONE_PROXIMITY  — 30m spatial radius in the same zone,
                      3D positioning
    PARTY           — only the player's party, any zone
    LINKSHELL       — only LS members online
    ALLIANCE        — 3-party expanded proximity, 60m
    WHISPER_DIRECT  — point-to-point, full gain
    STAFF_GM        — admin only
    PUBLIC_AUCTION  — Jeuno AH only, region-scoped

Spatial falloff for ZONE_PROXIMITY:
    0-3m   → 0 dB (full gain)
    3-15m  → linear lerp 0 dB → -6 dB
    15-30m → linear lerp -6 dB → -24 dB
    >30m   → culled

Wall occlusion: reverb_zones provides damping_db; gain is
reduced by that amount (a damping profile of -3 dB means
the wall blocks 3 dB).

Voice Activity Detection (VAD): packets below -40 dB voice
activity are dropped at the source to save bandwidth — no
point sending "silence".

Mute lists: per-player mute + global blacklist (GMs can
add/remove from global). Muting is one-way (you don't hear
them; they still hear you).

Ducking: when a PARTY or WHISPER_DIRECT packet arrives,
ZONE_PROXIMITY voices drop -6 dB for that frame so the
important channel reads.

Public surface
--------------
    VoiceChannel enum
    VoicePacket dataclass (frozen)
    NetVoiceChatSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Falloff radius and breakpoints (meters).
PROXIMITY_FULL_GAIN_M = 3.0
PROXIMITY_NEAR_LIMIT_M = 15.0
PROXIMITY_FAR_LIMIT_M = 30.0
ALLIANCE_PROXIMITY_LIMIT_M = 60.0

# Gain table.
GAIN_FULL_DB = 0.0
GAIN_NEAR_DB = -6.0
GAIN_FAR_DB = -24.0
GAIN_DUCK_DB = -6.0  # how much ZONE_PROXIMITY ducks for party/whisper

# VAD threshold — packets below this are dropped.
VAD_THRESHOLD_DB = -40.0


class VoiceChannel(enum.Enum):
    ZONE_PROXIMITY = "zone_proximity"
    PARTY = "party"
    LINKSHELL = "linkshell"
    ALLIANCE = "alliance"
    WHISPER_DIRECT = "whisper_direct"
    STAFF_GM = "staff_gm"
    PUBLIC_AUCTION = "public_auction"


@dataclasses.dataclass(frozen=True)
class VoicePacket:
    sender_player_id: str
    channel: VoiceChannel
    opus_data_size_bytes: int
    voice_activity_db: float
    timestamp_ms: int
    ducking_priority: int = 0
    # Routing scope context (party id, ls id, etc.) used for
    # PARTY / LINKSHELL / ALLIANCE / WHISPER / PUBLIC_AUCTION.
    scope_id: str = ""
    # For WHISPER_DIRECT, the explicit receiver.
    target_player_id: str = ""


@dataclasses.dataclass
class NetVoiceChatSystem:
    # player_id -> set of channels subscribed.
    _subscriptions: dict[
        str, set[VoiceChannel],
    ] = dataclasses.field(default_factory=dict)
    # Per-channel scope membership:
    #   (channel, scope_id) -> set[player_id]
    _channel_members: dict[
        tuple[VoiceChannel, str], set[str],
    ] = dataclasses.field(default_factory=dict)
    # Per-player mute lists.
    _muted: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # Global blacklist (admin-managed).
    _blacklist: set[str] = dataclasses.field(default_factory=set)
    # Is the GM allowed flag.
    _is_staff: set[str] = dataclasses.field(default_factory=set)
    # Per-player zone (for ZONE_PROXIMITY same-zone check).
    _zone_of: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )

    # ---------------------------------------------- subscriptions
    def register_subscription(
        self,
        player_id: str,
        channel: VoiceChannel,
        scope_id: str = "",
    ) -> None:
        if not player_id:
            raise ValueError("player_id required")
        self._subscriptions.setdefault(
            player_id, set(),
        ).add(channel)
        # Scope membership — empty scope_id is fine for
        # ZONE_PROXIMITY / WHISPER_DIRECT / STAFF_GM.
        key = (channel, scope_id)
        self._channel_members.setdefault(
            key, set(),
        ).add(player_id)

    def unsubscribe(
        self,
        player_id: str,
        channel: VoiceChannel,
        scope_id: str = "",
    ) -> None:
        if player_id in self._subscriptions:
            self._subscriptions[player_id].discard(channel)
        key = (channel, scope_id)
        if key in self._channel_members:
            self._channel_members[key].discard(player_id)

    def is_subscribed(
        self, player_id: str, channel: VoiceChannel,
    ) -> bool:
        return channel in self._subscriptions.get(
            player_id, set(),
        )

    def channel_member_count(
        self, channel: VoiceChannel, scope_id: str = "",
    ) -> int:
        return len(self._channel_members.get(
            (channel, scope_id), set(),
        ))

    def set_zone(self, player_id: str, zone_id: str) -> None:
        self._zone_of[player_id] = zone_id

    def zone_of(self, player_id: str) -> str:
        return self._zone_of.get(player_id, "")

    def set_staff(self, player_id: str, is_staff: bool) -> None:
        if is_staff:
            self._is_staff.add(player_id)
        else:
            self._is_staff.discard(player_id)

    def is_staff(self, player_id: str) -> bool:
        return player_id in self._is_staff

    # ---------------------------------------------- mute
    def mute(self, player_id: str, target_id: str) -> None:
        if player_id == target_id:
            raise ValueError("cannot mute self")
        self._muted.setdefault(player_id, set()).add(target_id)

    def unmute(self, player_id: str, target_id: str) -> None:
        if player_id in self._muted:
            self._muted[player_id].discard(target_id)

    def is_muted(self, player_id: str, target_id: str) -> bool:
        return target_id in self._muted.get(player_id, set())

    def blacklist_add(self, target_id: str) -> None:
        self._blacklist.add(target_id)

    def blacklist_remove(self, target_id: str) -> None:
        self._blacklist.discard(target_id)

    def is_blacklisted(self, target_id: str) -> bool:
        return target_id in self._blacklist

    # ---------------------------------------------- VAD
    def passes_vad(self, packet: VoicePacket) -> bool:
        return packet.voice_activity_db >= VAD_THRESHOLD_DB

    # ---------------------------------------------- receive
    def should_receive(
        self,
        receiver_id: str,
        packet: VoicePacket,
        distance_m_if_proximity: float = 0.0,
    ) -> bool:
        if receiver_id == packet.sender_player_id:
            return False
        if self.is_blacklisted(packet.sender_player_id):
            return False
        if self.is_muted(receiver_id, packet.sender_player_id):
            return False
        if not self.passes_vad(packet):
            return False
        ch = packet.channel
        if ch == VoiceChannel.STAFF_GM:
            return self.is_staff(receiver_id)
        if ch == VoiceChannel.WHISPER_DIRECT:
            return receiver_id == packet.target_player_id
        if ch == VoiceChannel.ZONE_PROXIMITY:
            if self.zone_of(receiver_id) != self.zone_of(
                packet.sender_player_id,
            ):
                return False
            return distance_m_if_proximity <= PROXIMITY_FAR_LIMIT_M
        if ch == VoiceChannel.ALLIANCE:
            # Alliance proximity check (zone-cross within 60m).
            if self.zone_of(receiver_id) != self.zone_of(
                packet.sender_player_id,
            ):
                return False
            return distance_m_if_proximity <= ALLIANCE_PROXIMITY_LIMIT_M
        # PARTY / LINKSHELL / PUBLIC_AUCTION → scope check.
        key = (ch, packet.scope_id)
        members = self._channel_members.get(key, set())
        return receiver_id in members

    # ---------------------------------------------- gain
    def gain_for(
        self,
        receiver_id: str,
        packet: VoicePacket,
        distance_m: float = 0.0,
        wall_damping_db: float = 0.0,
    ) -> float:
        if distance_m < 0:
            raise ValueError("distance_m must be >= 0")
        if wall_damping_db < 0:
            raise ValueError("wall_damping_db must be >= 0")
        ch = packet.channel
        if ch in (
            VoiceChannel.PARTY,
            VoiceChannel.WHISPER_DIRECT,
            VoiceChannel.STAFF_GM,
            VoiceChannel.LINKSHELL,
            VoiceChannel.PUBLIC_AUCTION,
        ):
            # Non-spatial — full gain, no falloff, no walls.
            return GAIN_FULL_DB
        if ch == VoiceChannel.ZONE_PROXIMITY:
            base = self._falloff_proximity(distance_m)
            return base - wall_damping_db
        if ch == VoiceChannel.ALLIANCE:
            # 60m extended falloff — extend the lerp.
            if distance_m <= PROXIMITY_FULL_GAIN_M:
                return GAIN_FULL_DB - wall_damping_db
            if distance_m >= ALLIANCE_PROXIMITY_LIMIT_M:
                return GAIN_FAR_DB - wall_damping_db
            u = (
                distance_m - PROXIMITY_FULL_GAIN_M
            ) / (
                ALLIANCE_PROXIMITY_LIMIT_M - PROXIMITY_FULL_GAIN_M
            )
            return (
                GAIN_FULL_DB
                + (GAIN_FAR_DB - GAIN_FULL_DB) * u
                - wall_damping_db
            )
        return GAIN_FULL_DB

    def _falloff_proximity(self, distance_m: float) -> float:
        if distance_m <= PROXIMITY_FULL_GAIN_M:
            return GAIN_FULL_DB
        if distance_m >= PROXIMITY_FAR_LIMIT_M:
            return GAIN_FAR_DB
        if distance_m <= PROXIMITY_NEAR_LIMIT_M:
            # 3m → 15m: 0 → -6
            u = (distance_m - PROXIMITY_FULL_GAIN_M) / (
                PROXIMITY_NEAR_LIMIT_M - PROXIMITY_FULL_GAIN_M
            )
            return GAIN_FULL_DB + (GAIN_NEAR_DB - GAIN_FULL_DB) * u
        # 15m → 30m: -6 → -24
        u = (distance_m - PROXIMITY_NEAR_LIMIT_M) / (
            PROXIMITY_FAR_LIMIT_M - PROXIMITY_NEAR_LIMIT_M
        )
        return GAIN_NEAR_DB + (GAIN_FAR_DB - GAIN_NEAR_DB) * u

    # ---------------------------------------------- batch
    def packets_for(
        self,
        receiver_id: str,
        queued_packets: t.Iterable[VoicePacket],
        distances_m: dict[str, float] | None = None,
        wall_damping_db: dict[str, float] | None = None,
    ) -> list[tuple[VoicePacket, float]]:
        """Return ordered (packet, gain_db) pairs for the
        receiver. Applies ducking: if a PARTY or
        WHISPER_DIRECT packet is in the queue, all
        ZONE_PROXIMITY packets are ducked by GAIN_DUCK_DB.
        """
        distances_m = distances_m or {}
        walls = wall_damping_db or {}
        kept: list[VoicePacket] = []
        for pkt in queued_packets:
            d = distances_m.get(pkt.sender_player_id, 0.0)
            if self.should_receive(receiver_id, pkt, d):
                kept.append(pkt)
        # Determine ducking.
        duck = any(
            p.channel
            in (VoiceChannel.PARTY, VoiceChannel.WHISPER_DIRECT)
            for p in kept
        )
        # Sort: WHISPER > PARTY > ALLIANCE > others > PROXIMITY last.
        priority = {
            VoiceChannel.STAFF_GM: 0,
            VoiceChannel.WHISPER_DIRECT: 1,
            VoiceChannel.PARTY: 2,
            VoiceChannel.ALLIANCE: 3,
            VoiceChannel.LINKSHELL: 4,
            VoiceChannel.PUBLIC_AUCTION: 5,
            VoiceChannel.ZONE_PROXIMITY: 6,
        }
        kept.sort(
            key=lambda p: (
                priority.get(p.channel, 7),
                p.timestamp_ms,
            )
        )
        out: list[tuple[VoicePacket, float]] = []
        for pkt in kept:
            d = distances_m.get(pkt.sender_player_id, 0.0)
            w = walls.get(pkt.sender_player_id, 0.0)
            g = self.gain_for(receiver_id, pkt, d, w)
            if duck and pkt.channel == VoiceChannel.ZONE_PROXIMITY:
                g += GAIN_DUCK_DB
            out.append((pkt, g))
        return out


__all__ = [
    "VoiceChannel",
    "VoicePacket",
    "NetVoiceChatSystem",
    "PROXIMITY_FULL_GAIN_M",
    "PROXIMITY_NEAR_LIMIT_M",
    "PROXIMITY_FAR_LIMIT_M",
    "ALLIANCE_PROXIMITY_LIMIT_M",
    "GAIN_FULL_DB",
    "GAIN_NEAR_DB",
    "GAIN_FAR_DB",
    "GAIN_DUCK_DB",
    "VAD_THRESHOLD_DB",
]
