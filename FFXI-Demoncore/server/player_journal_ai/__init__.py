"""Player journal AI — auto-summarize daily activity.

Reads the player_chronicle (the auto-recorded event stream) and
distills a per-day JOURNAL ENTRY: a short prose-style summary of
the day's highlights. Each entry classifies the day (TRIUMPH /
SETBACK / EXPLORATION / SOCIAL / ROUTINE) and surfaces the
single most notable moment.

The journal is a player-facing keepsake, not a data store: it
references chronicle events but doesn't duplicate them.

Public surface
--------------
    DayMood enum
    EventWeight enum
    JournalEntry dataclass
    PlayerJournalAI
        .ingest_event(player_id, kind, weight, label, day_index)
        .compose_entry(player_id, day_index) -> JournalEntry
        .entries_for(player_id) -> tuple[JournalEntry]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


# Default thresholds.
TRIUMPH_THRESHOLD = 30
SETBACK_THRESHOLD = -15


class EventWeight(str, enum.Enum):
    HUGE_POSITIVE = "huge_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    HUGE_NEGATIVE = "huge_negative"


_WEIGHT_VALUE: dict[EventWeight, int] = {
    EventWeight.HUGE_POSITIVE: 30,
    EventWeight.POSITIVE: 10,
    EventWeight.NEUTRAL: 1,
    EventWeight.NEGATIVE: -10,
    EventWeight.HUGE_NEGATIVE: -30,
}


class DayMood(str, enum.Enum):
    TRIUMPH = "triumph"
    SETBACK = "setback"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    ROUTINE = "routine"


class EventCategory(str, enum.Enum):
    COMBAT = "combat"
    EXPLORE = "explore"
    SOCIAL = "social"
    CRAFT = "craft"
    QUEST = "quest"
    DEATH = "death"


@dataclasses.dataclass
class _Event:
    kind: str
    label: str
    weight: EventWeight
    category: EventCategory
    day_index: int


@dataclasses.dataclass(frozen=True)
class JournalEntry:
    player_id: str
    day_index: int
    mood: DayMood
    headline: str
    score: int
    event_count: int
    notable_event_label: str = ""


@dataclasses.dataclass
class PlayerJournalAI:
    triumph_threshold: int = TRIUMPH_THRESHOLD
    setback_threshold: int = SETBACK_THRESHOLD
    _events: dict[
        tuple[str, int], list[_Event],
    ] = dataclasses.field(default_factory=dict)

    def ingest_event(
        self, *, player_id: str, kind: str,
        weight: EventWeight,
        category: EventCategory = EventCategory.COMBAT,
        label: str = "",
        day_index: int = 0,
    ) -> bool:
        if not kind:
            return False
        key = (player_id, day_index)
        ev = _Event(
            kind=kind, label=label or kind,
            weight=weight, category=category,
            day_index=day_index,
        )
        self._events.setdefault(key, []).append(ev)
        return True

    def _pick_mood(
        self, events: list[_Event], score: int,
    ) -> DayMood:
        if score >= self.triumph_threshold:
            return DayMood.TRIUMPH
        if score <= self.setback_threshold:
            return DayMood.SETBACK
        # Use category counts to bias
        counts: dict[EventCategory, int] = {}
        for ev in events:
            counts[ev.category] = (
                counts.get(ev.category, 0) + 1
            )
        if not counts:
            return DayMood.ROUTINE
        dominant = max(counts.items(), key=lambda kv: kv[1])
        if dominant[0] == EventCategory.EXPLORE:
            return DayMood.EXPLORATION
        if dominant[0] == EventCategory.SOCIAL:
            return DayMood.SOCIAL
        return DayMood.ROUTINE

    def _notable(
        self, events: list[_Event],
    ) -> t.Optional[_Event]:
        if not events:
            return None
        # Notable = highest absolute weight magnitude
        return max(
            events,
            key=lambda e: abs(_WEIGHT_VALUE[e.weight]),
        )

    def _headline_for(
        self, mood: DayMood, notable: t.Optional[_Event],
    ) -> str:
        if notable is None:
            return "A quiet day."
        templates: dict[DayMood, str] = {
            DayMood.TRIUMPH: "Today was glorious — {x}.",
            DayMood.SETBACK: "A bitter day — {x}.",
            DayMood.EXPLORATION: (
                "The road called — and answered: {x}."
            ),
            DayMood.SOCIAL: "Among friends today — {x}.",
            DayMood.ROUTINE: "An ordinary day, save for {x}.",
        }
        return templates[mood].format(x=notable.label)

    def compose_entry(
        self, *, player_id: str, day_index: int,
    ) -> t.Optional[JournalEntry]:
        events = self._events.get(
            (player_id, day_index),
        )
        if not events:
            return None
        score = sum(
            _WEIGHT_VALUE[e.weight] for e in events
        )
        mood = self._pick_mood(events, score)
        notable = self._notable(events)
        return JournalEntry(
            player_id=player_id, day_index=day_index,
            mood=mood,
            headline=self._headline_for(mood, notable),
            score=score,
            event_count=len(events),
            notable_event_label=(
                notable.label if notable else ""
            ),
        )

    def entries_for(
        self, *, player_id: str,
    ) -> tuple[JournalEntry, ...]:
        days = sorted(
            d for (pid, d) in self._events
            if pid == player_id
        )
        out: list[JournalEntry] = []
        for d in days:
            entry = self.compose_entry(
                player_id=player_id, day_index=d,
            )
            if entry is not None:
                out.append(entry)
        return tuple(out)

    def total_events(
        self, *, player_id: str,
    ) -> int:
        return sum(
            len(v) for (pid, _), v in self._events.items()
            if pid == player_id
        )


__all__ = [
    "TRIUMPH_THRESHOLD", "SETBACK_THRESHOLD",
    "DayMood", "EventWeight", "EventCategory",
    "JournalEntry",
    "PlayerJournalAI",
]
