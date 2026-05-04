"""Friend list status — online/zone/job/AFK presence feed.

Each player has a friend list. For each friend, we track:
* online state (ONLINE / OFFLINE / AFK / BUSY / IN_FIGHT /
  IN_CUTSCENE)
* current zone
* current job + level (e.g. WAR75/NIN37)
* last_seen_at_seconds

Helpers list a player's friends sorted by status (online
first), and a quick stats summary.

Public surface
--------------
    PresenceState enum
    FriendStatus dataclass
    FriendListStatus
        .add_friend(viewer_id, friend_id)
        .remove_friend(viewer_id, friend_id)
        .update_presence(player_id, state, zone, job, lvl, sub, sublvl)
        .friends_for(viewer_id) -> tuple[FriendStatus]
        .summary_for(viewer_id) -> dict
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class PresenceState(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AFK = "afk"
    BUSY = "busy"
    IN_FIGHT = "in_fight"
    IN_CUTSCENE = "in_cutscene"


_STATE_RANK: dict[PresenceState, int] = {
    PresenceState.ONLINE: 0,
    PresenceState.IN_FIGHT: 1,
    PresenceState.IN_CUTSCENE: 2,
    PresenceState.AFK: 3,
    PresenceState.BUSY: 4,
    PresenceState.OFFLINE: 5,
}


@dataclasses.dataclass
class _Presence:
    player_id: str
    state: PresenceState = PresenceState.OFFLINE
    zone_id: str = ""
    main_job: str = ""
    main_level: int = 0
    sub_job: str = ""
    sub_level: int = 0
    last_seen_at_seconds: float = 0.0


@dataclasses.dataclass(frozen=True)
class FriendStatus:
    friend_id: str
    state: PresenceState
    zone_id: str
    job_string: str       # e.g. "WAR75/NIN37"
    last_seen_at_seconds: float


@dataclasses.dataclass
class FriendListStatus:
    # viewer -> set of friend_ids
    _friends: dict[str, set[str]] = dataclasses.field(
        default_factory=dict,
    )
    # player_id -> presence
    _presence: dict[str, _Presence] = dataclasses.field(
        default_factory=dict,
    )

    def add_friend(
        self, *, viewer_id: str, friend_id: str,
    ) -> bool:
        if viewer_id == friend_id:
            return False
        s = self._friends.setdefault(viewer_id, set())
        if friend_id in s:
            return False
        s.add(friend_id)
        return True

    def remove_friend(
        self, *, viewer_id: str, friend_id: str,
    ) -> bool:
        s = self._friends.get(viewer_id)
        if s is None or friend_id not in s:
            return False
        s.remove(friend_id)
        return True

    def is_friend(
        self, *, viewer_id: str, friend_id: str,
    ) -> bool:
        return friend_id in self._friends.get(
            viewer_id, set(),
        )

    def update_presence(
        self, *, player_id: str,
        state: PresenceState,
        zone_id: str = "",
        main_job: str = "",
        main_level: int = 0,
        sub_job: str = "",
        sub_level: int = 0,
        now_seconds: float = 0.0,
    ) -> _Presence:
        p = self._presence.get(player_id)
        if p is None:
            p = _Presence(player_id=player_id)
            self._presence[player_id] = p
        p.state = state
        if zone_id:
            p.zone_id = zone_id
        if main_job:
            p.main_job = main_job
        if main_level > 0:
            p.main_level = main_level
        if sub_job:
            p.sub_job = sub_job
        if sub_level > 0:
            p.sub_level = sub_level
        p.last_seen_at_seconds = now_seconds
        return p

    def friends_for(
        self, *, viewer_id: str,
    ) -> tuple[FriendStatus, ...]:
        ids = self._friends.get(viewer_id, set())
        out: list[FriendStatus] = []
        for fid in ids:
            p = self._presence.get(fid)
            if p is None:
                p = _Presence(player_id=fid)
            job_str = ""
            if p.main_job and p.main_level > 0:
                job_str = f"{p.main_job}{p.main_level}"
                if p.sub_job and p.sub_level > 0:
                    job_str += (
                        f"/{p.sub_job}{p.sub_level}"
                    )
            out.append(FriendStatus(
                friend_id=fid,
                state=p.state,
                zone_id=p.zone_id,
                job_string=job_str,
                last_seen_at_seconds=p.last_seen_at_seconds,
            ))
        # Sort: state rank, then friend_id alpha
        out.sort(
            key=lambda f: (
                _STATE_RANK[f.state], f.friend_id,
            ),
        )
        return tuple(out)

    def summary_for(
        self, *, viewer_id: str,
    ) -> dict[str, int]:
        friends = self.friends_for(viewer_id=viewer_id)
        out: dict[str, int] = {
            s.value: 0 for s in PresenceState
        }
        out["total"] = len(friends)
        for f in friends:
            out[f.state.value] += 1
        return out

    def total_friend_pairs(self) -> int:
        return sum(
            len(s) for s in self._friends.values()
        )


__all__ = [
    "PresenceState",
    "FriendStatus",
    "FriendListStatus",
]
