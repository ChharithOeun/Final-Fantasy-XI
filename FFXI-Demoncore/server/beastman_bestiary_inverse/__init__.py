"""Beastman bestiary inverse — adventurers as the NMs.

From the beastman side, the canonical "adventurers" are the
NAMED MONSTERS. A Hume warrior carving through your camp isn't
a hero — he's an NM that's killed your kin three times this
fortnight. This module maintains a per-(beastman_race, hume
race / job) catalog that reframes adventurer encounters as
beastman-side bestiary entries with kill quotas, fame
thresholds, and trophy drops.

Each entry tracks how many times a beastman PLAYER has slain
that NM type. Quotas — once met — unlock per-race rewards
(special gear, lore fragments, faction rep).

Public surface
--------------
    AdvRace enum        HUME / ELVAAN / TARUTARU / MITHRA /
                        GALKA / OUTLAW
    Threat enum         NUISANCE / RAIDER / VETERAN /
                        WARLORD / LEGEND
    AdvNmEntry dataclass
    QuotaResult dataclass
    BeastmanBestiaryInverse
        .register_entry(race, adv_race, threat, kill_quota,
                        fame_per_kill, lore_id)
        .record_slay(player_id, race, adv_race)
        .quota_progress(player_id, race, adv_race)
        .has_completed(player_id, race, adv_race)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.beastman_playable_races import BeastmanRace


class AdvRace(str, enum.Enum):
    HUME = "hume"
    ELVAAN = "elvaan"
    TARUTARU = "tarutaru"
    MITHRA = "mithra"
    GALKA = "galka"
    OUTLAW = "outlaw"          # any race; outlaw flagged


class Threat(str, enum.Enum):
    NUISANCE = "nuisance"
    RAIDER = "raider"
    VETERAN = "veteran"
    WARLORD = "warlord"
    LEGEND = "legend"


@dataclasses.dataclass(frozen=True)
class AdvNmEntry:
    race: BeastmanRace
    adv_race: AdvRace
    threat: Threat
    kill_quota: int
    fame_per_kill: int
    lore_fragment_id: str = ""


@dataclasses.dataclass(frozen=True)
class QuotaResult:
    accepted: bool
    kills_recorded: int
    quota_required: int
    completed: bool
    fame_awarded: int
    reason: t.Optional[str] = None


@dataclasses.dataclass
class _PlayerProgress:
    kills: dict[
        tuple[BeastmanRace, AdvRace], int,
    ] = dataclasses.field(default_factory=dict)
    completed: set[
        tuple[BeastmanRace, AdvRace],
    ] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class BeastmanBestiaryInverse:
    _entries: dict[
        tuple[BeastmanRace, AdvRace], AdvNmEntry,
    ] = dataclasses.field(default_factory=dict)
    _progress: dict[
        str, _PlayerProgress,
    ] = dataclasses.field(default_factory=dict)

    def register_entry(
        self, *, race: BeastmanRace,
        adv_race: AdvRace,
        threat: Threat,
        kill_quota: int,
        fame_per_kill: int,
        lore_fragment_id: str = "",
    ) -> t.Optional[AdvNmEntry]:
        if kill_quota <= 0:
            return None
        if fame_per_kill < 0:
            return None
        key = (race, adv_race)
        if key in self._entries:
            return None
        e = AdvNmEntry(
            race=race, adv_race=adv_race,
            threat=threat,
            kill_quota=kill_quota,
            fame_per_kill=fame_per_kill,
            lore_fragment_id=lore_fragment_id,
        )
        self._entries[key] = e
        return e

    def get_entry(
        self, *, race: BeastmanRace,
        adv_race: AdvRace,
    ) -> t.Optional[AdvNmEntry]:
        return self._entries.get((race, adv_race))

    def _progress_for(
        self, player_id: str,
    ) -> _PlayerProgress:
        p = self._progress.get(player_id)
        if p is None:
            p = _PlayerProgress()
            self._progress[player_id] = p
        return p

    def record_slay(
        self, *, player_id: str,
        race: BeastmanRace,
        adv_race: AdvRace,
    ) -> QuotaResult:
        e = self._entries.get((race, adv_race))
        if e is None:
            return QuotaResult(
                False,
                kills_recorded=0,
                quota_required=0,
                completed=False,
                fame_awarded=0,
                reason="no entry registered",
            )
        prog = self._progress_for(player_id)
        key = (race, adv_race)
        if key in prog.completed:
            cur = prog.kills.get(key, 0) + 1
            prog.kills[key] = cur
            return QuotaResult(
                accepted=True,
                kills_recorded=cur,
                quota_required=e.kill_quota,
                completed=True,
                fame_awarded=e.fame_per_kill,
                reason="quota already complete",
            )
        cur = prog.kills.get(key, 0) + 1
        prog.kills[key] = cur
        completed_now = cur >= e.kill_quota
        if completed_now:
            prog.completed.add(key)
        return QuotaResult(
            accepted=True,
            kills_recorded=cur,
            quota_required=e.kill_quota,
            completed=completed_now,
            fame_awarded=e.fame_per_kill,
        )

    def quota_progress(
        self, *, player_id: str,
        race: BeastmanRace,
        adv_race: AdvRace,
    ) -> tuple[int, int]:
        e = self._entries.get((race, adv_race))
        if e is None:
            return (0, 0)
        prog = self._progress.get(player_id)
        if prog is None:
            return (0, e.kill_quota)
        return (
            prog.kills.get((race, adv_race), 0),
            e.kill_quota,
        )

    def has_completed(
        self, *, player_id: str,
        race: BeastmanRace,
        adv_race: AdvRace,
    ) -> bool:
        prog = self._progress.get(player_id)
        if prog is None:
            return False
        return (race, adv_race) in prog.completed

    def total_entries(self) -> int:
        return len(self._entries)

    def total_kills_for(
        self, *, player_id: str,
    ) -> int:
        prog = self._progress.get(player_id)
        if prog is None:
            return 0
        return sum(prog.kills.values())


__all__ = [
    "AdvRace", "Threat",
    "AdvNmEntry", "QuotaResult",
    "BeastmanBestiaryInverse",
]
