"""Net zone handoff — cross-server zone transitions with
session continuity.

zone_handoff (prior batch) covers the *same-server* case —
a 200ms cinematic fade while the new tile streams in.
world_streaming handles the geometry prefetch. seamless_
world ties it all together visually.

This module covers the *cross-server* case — the target
zone is on a different game server. That's harder, because
the player's authoritative state has to be teleported,
verified, deserialized, and re-instantiated without losing
inventory, buffs, party membership, or voice-chat session.

The protocol is six steps:
    1. SOURCE flags the player as HANDING_OFF; further
       state changes are blocked.
    2. SOURCE serializes everything — inventory, buffs,
       party_id, friends list, quest progress, voice
       session id — with a SHA-style checksum.
    3. TARGET receives the blob, verifies checksum,
       deserializes, marks the player as LOADING_IN.
    4. SOURCE destroys its local entity (frees the slot).
    5. TARGET instantiates and sends LOAD_COMPLETE.
    6. CLIENT renders the 200ms cinematic fade via the
       same path as same-server handoffs — never a load
       screen.

Failure modes:
    - target unreachable → fall back to source (player
      snaps back, gets a warning toast)
    - checksum mismatch → kick to safe zone (Mog House or
      Ru'Lude Gardens)
    - network split during step 4/5 → reconnect logic
      picks up from the last ack

Public surface
--------------
    HandoffState enum
    FailureReason enum
    PlayerSerializedState dataclass (frozen)
    HandoffRecord dataclass
    NetZoneHandoffSystem
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import typing as t


# Default safe zone — where you go if everything explodes.
SAFE_ZONE_DEFAULT = "rulude_gardens"

# Fallback safe zones per nation home.
_HOME_SAFE_ZONE: dict[str, str] = {
    "bastok": "bastok_mines_mh",
    "windurst": "windurst_woods_mh",
    "sandoria": "northern_sandoria_mh",
    "rulude_gardens": "rulude_gardens",
    "jeuno": "rulude_gardens",
}


class HandoffState(enum.Enum):
    IDLE = "idle"
    HANDING_OFF = "handing_off"
    SERIALIZED = "serialized"
    LOADING_IN = "loading_in"
    COMPLETE = "complete"
    FAILED = "failed"


class FailureReason(enum.Enum):
    NONE = "none"
    TARGET_UNREACHABLE = "target_unreachable"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    SERIALIZATION_MISMATCH = "serialization_mismatch"
    NETWORK_SPLIT = "network_split"
    TIMEOUT = "timeout"


@dataclasses.dataclass(frozen=True)
class PlayerSerializedState:
    player_id: str
    inventory_items: tuple[tuple[str, int], ...]  # (item_id, qty)
    buffs: tuple[tuple[str, int], ...]  # (buff_id, remaining_ms)
    party_id: str
    friend_ids: tuple[str, ...]
    quest_progress: tuple[tuple[str, int], ...]  # (quest_id, step)
    voice_chat_session_id: str
    home_nation: str

    def to_blob(self) -> bytes:
        d = {
            "player_id": self.player_id,
            "inventory": list(self.inventory_items),
            "buffs": list(self.buffs),
            "party_id": self.party_id,
            "friends": list(self.friend_ids),
            "quests": list(self.quest_progress),
            "voice": self.voice_chat_session_id,
            "home": self.home_nation,
        }
        return json.dumps(d, sort_keys=True).encode("utf-8")

    @classmethod
    def from_blob(cls, blob: bytes) -> "PlayerSerializedState":
        d = json.loads(blob.decode("utf-8"))
        return cls(
            player_id=d["player_id"],
            inventory_items=tuple(tuple(x) for x in d["inventory"]),
            buffs=tuple(tuple(x) for x in d["buffs"]),
            party_id=d["party_id"],
            friend_ids=tuple(d["friends"]),
            quest_progress=tuple(tuple(x) for x in d["quests"]),
            voice_chat_session_id=d["voice"],
            home_nation=d["home"],
        )


@dataclasses.dataclass
class HandoffRecord:
    player_id: str
    source_server_id: str
    target_server_id: str
    target_zone_id: str
    state: HandoffState
    failure_reason: FailureReason = FailureReason.NONE
    blob: bytes | None = None
    checksum: str = ""


def _checksum_for(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


@dataclasses.dataclass
class NetZoneHandoffSystem:
    _records: dict[str, HandoffRecord] = dataclasses.field(
        default_factory=dict,
    )
    # Stash serialized state by player_id (so target can fetch).
    _stashed_state: dict[
        str, PlayerSerializedState,
    ] = dataclasses.field(default_factory=dict)
    # Player home_nation registry.
    _home_nation: dict[str, str] = dataclasses.field(
        default_factory=dict,
    )
    # Servers known reachable.
    _reachable_servers: set[str] = dataclasses.field(
        default_factory=set,
    )

    # ---------------------------------------------- setup
    def register_player_state(
        self,
        state: PlayerSerializedState,
    ) -> None:
        if not state.player_id:
            raise ValueError("player_id required")
        self._stashed_state[state.player_id] = state
        self._home_nation[state.player_id] = state.home_nation

    def set_server_reachable(
        self, server_id: str, reachable: bool,
    ) -> None:
        if reachable:
            self._reachable_servers.add(server_id)
        else:
            self._reachable_servers.discard(server_id)

    def is_server_reachable(self, server_id: str) -> bool:
        return server_id in self._reachable_servers

    # ---------------------------------------------- initiate
    def initiate_handoff(
        self,
        player_id: str,
        target_zone_id: str,
        target_server_id: str,
        source_server_id: str = "src",
    ) -> HandoffRecord:
        if not player_id:
            raise ValueError("player_id required")
        if not target_zone_id:
            raise ValueError("target_zone_id required")
        if not target_server_id:
            raise ValueError("target_server_id required")
        if player_id in self._records:
            existing = self._records[player_id]
            if existing.state not in (
                HandoffState.COMPLETE, HandoffState.FAILED,
            ):
                raise ValueError(
                    f"player {player_id} already in handoff",
                )
        rec = HandoffRecord(
            player_id=player_id,
            source_server_id=source_server_id,
            target_server_id=target_server_id,
            target_zone_id=target_zone_id,
            state=HandoffState.HANDING_OFF,
        )
        self._records[player_id] = rec
        # Immediately check reachability.
        if not self.is_server_reachable(target_server_id):
            rec.state = HandoffState.FAILED
            rec.failure_reason = FailureReason.TARGET_UNREACHABLE
        return rec

    def state_of(self, player_id: str) -> HandoffState:
        if player_id not in self._records:
            return HandoffState.IDLE
        return self._records[player_id].state

    def failure_of(self, player_id: str) -> FailureReason:
        if player_id not in self._records:
            return FailureReason.NONE
        return self._records[player_id].failure_reason

    # ---------------------------------------------- serialize
    def serialize_state(
        self, player_id: str,
    ) -> tuple[bytes, str]:
        if player_id not in self._stashed_state:
            raise KeyError(
                f"no state registered for {player_id}",
            )
        rec = self._records.get(player_id)
        if rec is None:
            raise KeyError(
                f"no active handoff for {player_id}",
            )
        if rec.state != HandoffState.HANDING_OFF:
            raise ValueError(
                f"player {player_id} not in HANDING_OFF",
            )
        state = self._stashed_state[player_id]
        blob = state.to_blob()
        checksum = _checksum_for(blob)
        rec.blob = blob
        rec.checksum = checksum
        rec.state = HandoffState.SERIALIZED
        return blob, checksum

    def deserialize_state(
        self,
        blob: bytes,
        expected_checksum: str,
    ) -> PlayerSerializedState:
        actual = _checksum_for(blob)
        if actual != expected_checksum:
            raise ValueError("checksum mismatch")
        try:
            return PlayerSerializedState.from_blob(blob)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            raise ValueError(
                f"serialization mismatch: {e}",
            ) from e

    # ---------------------------------------------- target side
    def receive_at_target(
        self,
        player_id: str,
        blob: bytes,
        checksum: str,
    ) -> bool:
        rec = self._records.get(player_id)
        if rec is None:
            raise KeyError(f"no handoff for {player_id}")
        try:
            self.deserialize_state(blob, checksum)
        except ValueError as e:
            rec.state = HandoffState.FAILED
            if "checksum" in str(e):
                rec.failure_reason = FailureReason.CHECKSUM_MISMATCH
            else:
                rec.failure_reason = (
                    FailureReason.SERIALIZATION_MISMATCH
                )
            return False
        rec.state = HandoffState.LOADING_IN
        return True

    def on_target_load_complete(self, player_id: str) -> None:
        rec = self._records.get(player_id)
        if rec is None:
            raise KeyError(f"no handoff for {player_id}")
        if rec.state != HandoffState.LOADING_IN:
            raise ValueError(
                f"player {player_id} not in LOADING_IN",
            )
        rec.state = HandoffState.COMPLETE

    def on_handoff_failure(
        self,
        player_id: str,
        reason: FailureReason,
    ) -> None:
        rec = self._records.get(player_id)
        if rec is None:
            raise KeyError(f"no handoff for {player_id}")
        rec.state = HandoffState.FAILED
        rec.failure_reason = reason

    # ---------------------------------------------- pending
    def pending_handoffs(self) -> tuple[HandoffRecord, ...]:
        return tuple(
            r for r in self._records.values()
            if r.state in (
                HandoffState.HANDING_OFF,
                HandoffState.SERIALIZED,
                HandoffState.LOADING_IN,
            )
        )

    # ---------------------------------------------- safe zone
    def fallback_safe_zone(self, player_id: str) -> str:
        home = self._home_nation.get(player_id, "")
        return _HOME_SAFE_ZONE.get(home, SAFE_ZONE_DEFAULT)

    # ---------------------------------------------- cleanup
    def clear_record(self, player_id: str) -> None:
        self._records.pop(player_id, None)


__all__ = [
    "HandoffState",
    "FailureReason",
    "PlayerSerializedState",
    "HandoffRecord",
    "NetZoneHandoffSystem",
    "SAFE_ZONE_DEFAULT",
]
