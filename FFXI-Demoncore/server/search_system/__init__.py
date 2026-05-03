"""Search system — /search and /sea commands.

Players run /search to find others by name, job, level, zone,
or activity flag. Each player can post a /sea comment that
shows up in their own search entry: a short tagline like
"LFP for Sortie" or "AFK in Mog House."

Filters compose: you can search "RDM 99 in Lower Jeuno LFP"
and only see RDMs at level 99 in Lower Jeuno who have the
LFP flag set.

Public surface
--------------
    SearchEntry — per-player record (live state)
    ActivityFlag enum
    SearchRegistry
        .update(player_id, ...) -> SearchEntry
        .set_comment(player_id, comment)
        .search(...) -> tuple[SearchEntry, ...]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


MAX_COMMENT_LEN = 60      # canonical FFXI /sea comment is short


class ActivityFlag(str, enum.Enum):
    NONE = "none"
    LFP = "looking_for_party"           # /lfp
    LFG = "looking_for_group"           # /lfg
    AFK = "afk"
    AWAY = "away"
    DND = "do_not_disturb"
    MENTOR_ON = "mentor"                # mentor flag toggled


@dataclasses.dataclass
class SearchEntry:
    player_id: str
    name: str = ""
    main_job: str = ""
    main_level: int = 0
    sub_job: str = ""
    sub_level: int = 0
    zone: str = ""
    activity: ActivityFlag = ActivityFlag.NONE
    comment: str = ""
    online: bool = True


@dataclasses.dataclass
class SearchRegistry:
    _entries: dict[str, SearchEntry] = dataclasses.field(default_factory=dict)

    def update(
        self, *, player_id: str,
        name: t.Optional[str] = None,
        main_job: t.Optional[str] = None,
        main_level: t.Optional[int] = None,
        sub_job: t.Optional[str] = None,
        sub_level: t.Optional[int] = None,
        zone: t.Optional[str] = None,
        activity: t.Optional[ActivityFlag] = None,
        online: t.Optional[bool] = None,
    ) -> SearchEntry:
        e = self._entries.get(player_id)
        if e is None:
            e = SearchEntry(player_id=player_id)
            self._entries[player_id] = e
        if name is not None:
            e.name = name
        if main_job is not None:
            e.main_job = main_job
        if main_level is not None:
            e.main_level = main_level
        if sub_job is not None:
            e.sub_job = sub_job
        if sub_level is not None:
            e.sub_level = sub_level
        if zone is not None:
            e.zone = zone
        if activity is not None:
            e.activity = activity
        if online is not None:
            e.online = online
        return e

    def set_comment(self, *, player_id: str, comment: str) -> bool:
        if len(comment) > MAX_COMMENT_LEN:
            return False
        e = self._entries.get(player_id)
        if e is None:
            return False
        e.comment = comment
        return True

    def get(self, player_id: str) -> t.Optional[SearchEntry]:
        return self._entries.get(player_id)

    def remove(self, *, player_id: str) -> bool:
        return self._entries.pop(player_id, None) is not None

    def search(
        self, *,
        name_substring: t.Optional[str] = None,
        main_job: t.Optional[str] = None,
        min_level: t.Optional[int] = None,
        max_level: t.Optional[int] = None,
        zone: t.Optional[str] = None,
        activity: t.Optional[ActivityFlag] = None,
        online_only: bool = True,
    ) -> tuple[SearchEntry, ...]:
        out: list[SearchEntry] = []
        for e in self._entries.values():
            if online_only and not e.online:
                continue
            if name_substring and \
                    name_substring.lower() not in e.name.lower():
                continue
            if main_job and e.main_job != main_job:
                continue
            if min_level is not None and e.main_level < min_level:
                continue
            if max_level is not None and e.main_level > max_level:
                continue
            if zone and e.zone != zone:
                continue
            if activity is not None and e.activity != activity:
                continue
            out.append(e)
        # Stable name-sorted output
        out.sort(key=lambda e: (e.name.lower(), e.player_id))
        return tuple(out)


__all__ = [
    "MAX_COMMENT_LEN",
    "ActivityFlag", "SearchEntry", "SearchRegistry",
]
