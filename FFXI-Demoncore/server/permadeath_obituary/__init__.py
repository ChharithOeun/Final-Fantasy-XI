"""Permadeath obituary — auto-generated death notices.

When a level-30+ player permadies, the loss isn't just
mechanical — they leave a record. This module composes
an OBITUARY chronicle article from the death event:
who they were, how they died, what they accomplished,
how long they lived. Then the chronicle holds it.

Composition phases
------------------
    BIO       short biographical line (race / job / level)
    DEATH     cause-of-death summary
    DEEDS     up to 3 highlight history entries from
              their lifetime (world-firsts, records, etc.)
    EPITAPH   a generated closing line, drawn from the
              tone bank by death_kind

DeathKind tone selection — different deaths get different
elegies:
    HEROIC          "fell in valor against ..."
    SACRIFICE       "gave their life so others lived"
    AMBUSH          "struck down without warning"
    OUTLAW          "perished outside the law"
    TRAVELER        "lost on the road"
    FOMOR_ASCENSION "ascended to the Fomor host"

Public surface
--------------
    DeathKind enum
    DeathRecord dataclass (frozen)
    PermadeathObituary
        .compose(death_record, history_log, world_chronicle,
                 published_at) -> article_id
        .total_published() -> int
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t

from server.server_history_log import (
    EventKind,
    QueryFilter,
    ServerHistoryLog,
)
from server.world_chronicle import ArticleKind, WorldChronicle


class DeathKind(str, enum.Enum):
    HEROIC = "heroic"
    SACRIFICE = "sacrifice"
    AMBUSH = "ambush"
    OUTLAW = "outlaw"
    TRAVELER = "traveler"
    FOMOR_ASCENSION = "fomor_ascension"


_EPITAPH = {
    DeathKind.HEROIC:
        "fell in valor against the foes of Vana'diel.",
    DeathKind.SACRIFICE:
        "gave their life so that others might live.",
    DeathKind.AMBUSH:
        "was struck down without warning.",
    DeathKind.OUTLAW:
        "perished outside the law, far from home.",
    DeathKind.TRAVELER:
        "was lost on the road, far from any aid.",
    DeathKind.FOMOR_ASCENSION:
        "ascended to the Fomor host. The mist takes them now.",
}

_DEED_KINDS = (
    EventKind.WORLD_FIRST_KILL,
    EventKind.SECOND_KILL,
    EventKind.SPEED_RECORD,
    EventKind.PERFECT_RUN,
    EventKind.LEGENDARY_DUEL,
    EventKind.NATION_VICTORY,
)


@dataclasses.dataclass(frozen=True)
class DeathRecord:
    player_id: str
    player_name: str
    race: str
    job: str
    level: int
    cause: str
    death_kind: DeathKind
    died_at: int
    born_at: int = 0  # 0 means unknown


@dataclasses.dataclass
class PermadeathObituary:
    _published: int = 0

    def compose(
        self, *, death: DeathRecord,
        history_log: ServerHistoryLog,
        world_chronicle: WorldChronicle,
        published_at: int,
    ) -> str:
        if not death.player_id or not death.player_name:
            return ""
        if death.level < 30:
            # below the permadeath threshold; nothing to record
            return ""

        # collect up to 3 deeds
        deeds = history_log.query(qf=QueryFilter(
            participant_id=death.player_id,
            kinds=_DEED_KINDS,
        ))[:3]

        # compose body
        bio = (
            f"{death.player_name}, {death.race} {death.job} "
            f"of level {death.level}."
        )
        cause_line = f"Cause of death: {death.cause}."
        if deeds:
            deed_lines = "\n".join(
                f"  - {d.summary}" for d in deeds
            )
            deeds_block = "Notable deeds:\n" + deed_lines
        else:
            deeds_block = (
                "No deeds were recorded — but they were "
                "remembered nonetheless."
            )
        epitaph = _EPITAPH[death.death_kind]
        if death.born_at and death.died_at > death.born_at:
            lifespan = death.died_at - death.born_at
            life_line = f"Lifespan: {lifespan} seconds."
        else:
            life_line = ""

        body_parts = [bio, cause_line, deeds_block]
        if life_line:
            body_parts.append(life_line)
        body_parts.append(epitaph)
        body = "\n\n".join(body_parts)

        title = f"In memoriam: {death.player_name}"
        article_id = world_chronicle.publish_article(
            kind=ArticleKind.OBITUARY,
            title=title, body=body,
            author_id="system",
            tags=["obituary", death.race.lower(),
                  death.job.lower(),
                  death.death_kind.value],
            published_at=published_at,
        )
        if article_id:
            self._published += 1
        return article_id

    def total_published(self) -> int:
        return self._published


__all__ = [
    "DeathKind", "DeathRecord", "PermadeathObituary",
]
