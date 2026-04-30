"""Schedule + environmental ticker.

Walks every agent's schedule each tick, detects schedule-entry boundary
crossings, and emits `schedule_event` events through `apply_event` so
the existing mood + memory machinery handles them. Also fires
zone-wide environmental events (morning/evening/night, rain/clear,
festival_active) on a Vana'diel time basis.

This is what makes the agent YAMLs *live*. Without it, schedules are
inert prose. With it:

  - Bondrak's mood drifts from `content` at sunrise to `drunk` by 18:00
    because the daily_loop_evening event fires
  - Mavi the pickpocket is `alert` during the day and `content` at
    night (peer-recognition mood)
  - Zaldon `setup_stall` -> `vendor_idle` -> `lunch_break` cycle
    drives location updates pushed back to the UE5 client

The scheduler does NOT call the LLM. It's pure event dispatch on top
of the static event_deltas table.
"""
from __future__ import annotations

import dataclasses
import logging
import typing as t

from .db import AgentDB
from .game_clock import (
    VanadielTime,
    parse_schedule_time,
    schedule_index_at,
    vanadiel_at,
)
from .loader import AgentProfile
from .mood_propagation import apply_event


log = logging.getLogger("demoncore.scheduler")


# Vana'diel-hour → environmental event mapping. Fires once per
# Vana'diel-day per zone. The role wildcard "*" in the event_deltas
# table does the per-role specialization.
ENVIRONMENTAL_HOURS: dict[int, str] = {
    5:  "daily_loop_predawn",
    6:  "morning",
    7:  "daily_loop_morning",
    11: "daily_loop_late_morning",
    12: "daily_loop_noon",
    13: "daily_loop_afternoon",
    17: "daily_loop_evening_starts",
    18: "daily_loop_evening",
    20: "nighttime",
    21: "daily_loop_late_night",
}


@dataclasses.dataclass
class ScheduleState:
    """Bookkeeping for one agent — the most recent fired schedule index,
    plus the Vana'diel day on which it fired (so we re-fire after a wrap)."""
    last_fired_index: int = -1
    last_fired_day_of_year: int = -1


@dataclasses.dataclass
class EnvironmentalState:
    """Bookkeeping for one zone's environmental tick."""
    last_fired_hour: int = -1
    last_fired_day_of_year: int = -1


class Scheduler:
    """Periodic scheduler. Call `tick(vana_time)` to advance.

    The scheduler is intentionally separate from the orchestrator's
    main loop so the same tick can be driven by either real time
    (production) or fast-forward simulation (24h playtest).
    """

    def __init__(self, db: AgentDB):
        self.db = db
        self._agent_state: dict[str, ScheduleState] = {}
        self._zone_env_state: dict[str, EnvironmentalState] = {}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def tick(self,
             vana: VanadielTime,
             profiles_by_id: dict[str, AgentProfile]) -> dict:
        """Walk all agents + zones, fire any boundary-crossing events.

        Returns a small report dict for diagnostics:
            {
              "vana_time": str(vana),
              "schedule_events_fired": list[(agent_id, slot_index)],
              "environmental_events_fired": list[(zone, event_kind)],
            }
        """
        report = {
            "vana_time": str(vana),
            "schedule_events_fired": [],
            "environmental_events_fired": [],
        }

        # 1. Per-agent schedule tick
        for agent_id, profile in profiles_by_id.items():
            schedule = profile.raw.get("schedule") or []
            if not schedule:
                continue
            new_index = schedule_index_at(schedule, vana)
            if new_index < 0:
                continue
            state = self._agent_state.setdefault(agent_id, ScheduleState())
            if (state.last_fired_index == new_index
                    and state.last_fired_day_of_year == vana.day_of_year):
                continue   # same slot, same day -> already handled
            state.last_fired_index = new_index
            state.last_fired_day_of_year = vana.day_of_year

            # Compose a schedule_slot_<index> event so the event_deltas
            # table can match per-slot if it wants. We also push the
            # location and animation hints into the payload so
            # downstream consumers (LSB position sync) see them.
            slot = schedule[new_index]
            payload = {
                "slot_index": new_index,
                "vana_time": vana.hhmm,
            }
            if len(slot) > 1:
                payload["location"] = slot[1]
            if len(slot) > 2:
                payload["animation"] = slot[2]

            apply_event(self.db, profile, "schedule_slot_fired", payload)
            # Persist a queued event so the next reflection pass sees it
            self.db.push_event(agent_id, "schedule_slot_fired", payload)

            # If the schedule entry's animation maps to a known mood
            # event (e.g. "drinks_at_tavern"), we also fire that.
            if len(slot) > 2 and isinstance(slot[2], str):
                mood_event = ANIM_TO_MOOD_EVENT.get(slot[2])
                if mood_event:
                    apply_event(self.db, profile, mood_event, payload)
                    self.db.push_event(agent_id, mood_event, payload)

            report["schedule_events_fired"].append((agent_id, new_index))

        # 2. Per-zone environmental tick
        zones = {p.zone for p in profiles_by_id.values()}
        for zone in zones:
            env_state = self._zone_env_state.setdefault(zone, EnvironmentalState())
            event_kind = ENVIRONMENTAL_HOURS.get(vana.hour)
            if event_kind is None:
                continue
            if (env_state.last_fired_hour == vana.hour
                    and env_state.last_fired_day_of_year == vana.day_of_year):
                continue
            env_state.last_fired_hour = vana.hour
            env_state.last_fired_day_of_year = vana.day_of_year

            # Fan out to every agent in the zone (synchronous, cheap)
            for profile in profiles_by_id.values():
                if profile.zone != zone:
                    continue
                apply_event(self.db, profile, event_kind, {"zone": zone})
                self.db.push_event(profile.id, event_kind, {"zone": zone})

            report["environmental_events_fired"].append((zone, event_kind))

        return report


# Mapping from schedule animation strings to mood-relevant event names.
# Schedule entries like [18:00, "tavern", "evening_drinking_starts"] fire
# "daily_loop_evening" automatically because the env tick fires at hour 18,
# but per-anim hints can fire additional events.
ANIM_TO_MOOD_EVENT: dict[str, str] = {
    "wake_with_headache":            "daily_loop_morning",
    "first_pint":                    "daily_loop_late_morning",
    "evening_drinking_starts":       "daily_loop_evening",
    "fight_picking_or_storytelling": "daily_loop_late_night",
    "passed_out":                    "daily_loop_late_night",
    "scout_marks":                   "daytime",
    "afternoon_lifting":             "daytime",
    "post_dinner_lifts":             "nighttime",
    "morning_meditation":            "morning",
    "evening_repairs":               "daily_loop_evening",
}
