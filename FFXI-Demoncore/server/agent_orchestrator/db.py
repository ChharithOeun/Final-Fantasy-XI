"""Persistence layer for the agent orchestrator.

Backed by sqlite for development and MariaDB/MySQL for production. The
schema is intentionally narrow:

    agents               static profile (loaded from YAML on boot)
    agent_state_tier2    mood + memory + last_reflection_at per Tier-2 agent
    agent_state_tier3    current goal + journal + schedule index per Tier-3 hero
    agent_events         FIFO inbox of events (damage_near, player_attack, etc.)
                         that the next reflection cycle should consider

We use sqlite3 stdlib for portability — no SQLAlchemy. That keeps
chharbot lightweight and removes one moving part from production.
"""
from __future__ import annotations

import dataclasses
import json
import sqlite3
import time
import typing as t


SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    zone            TEXT NOT NULL,
    tier            TEXT NOT NULL,
    role            TEXT NOT NULL,
    race            TEXT NOT NULL,
    gender          TEXT NOT NULL,
    voice_profile   TEXT,
    payload_json    TEXT NOT NULL,            -- full YAML round-tripped to JSON
    loaded_at       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS agents_zone_tier ON agents(zone, tier);

CREATE TABLE IF NOT EXISTS agent_state_tier2 (
    agent_id            TEXT PRIMARY KEY,
    mood                TEXT NOT NULL DEFAULT 'content',
    memory_summary      TEXT NOT NULL,
    last_reflection_at  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS agent_state_tier3 (
    agent_id            TEXT PRIMARY KEY,
    current_goal        TEXT,
    current_location    TEXT,
    schedule_index      INTEGER NOT NULL DEFAULT 0,
    journal_json        TEXT NOT NULL DEFAULT '[]',  -- list of dated entries
    last_reflection_at  INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS agent_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT NOT NULL,
    event_kind  TEXT NOT NULL,            -- damage_near | player_attack | ...
    payload     TEXT,                      -- JSON
    queued_at   INTEGER NOT NULL,
    processed_at INTEGER,
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);
CREATE INDEX IF NOT EXISTS events_inbox
    ON agent_events(agent_id, processed_at);
"""


@dataclasses.dataclass
class Tier2State:
    agent_id: str
    mood: str
    memory_summary: str
    last_reflection_at: int


@dataclasses.dataclass
class Tier3State:
    agent_id: str
    current_goal: t.Optional[str]
    current_location: t.Optional[str]
    schedule_index: int
    journal: list[dict]
    last_reflection_at: int


class AgentDB:
    """Thin wrapper over sqlite3 with the orchestrator's queries inlined."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- agents -------------------------------------------------------

    def upsert_agent(self, profile) -> None:
        """Insert or replace one agent profile (called on YAML load)."""
        self.conn.execute(
            """INSERT OR REPLACE INTO agents
               (id, name, zone, tier, role, race, gender, voice_profile,
                payload_json, loaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile.id, profile.name, profile.zone, profile.tier,
                profile.role, profile.race, profile.gender,
                profile.voice_profile,
                json.dumps(profile.raw),
                int(time.time()),
            ),
        )
        # Bootstrap state row if missing
        if profile.tier == "2_reflection":
            self.conn.execute(
                """INSERT OR IGNORE INTO agent_state_tier2
                   (agent_id, mood, memory_summary)
                   VALUES (?, ?, ?)""",
                (profile.id,
                 profile.raw.get("starting_mood", "content"),
                 profile.raw.get("starting_memory", "")),
            )
        elif profile.tier == "3_hero":
            self.conn.execute(
                """INSERT OR IGNORE INTO agent_state_tier3
                   (agent_id, current_goal, current_location,
                    schedule_index, journal_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (profile.id,
                 (profile.raw.get("goals") or [None])[0],
                 None,
                 0,
                 json.dumps([{
                     "ts": int(time.time()),
                     "entry": profile.raw.get("journal_seed", ""),
                 }])),
            )
        self.conn.commit()

    def list_agents(self, zone: t.Optional[str] = None,
                    tier: t.Optional[str] = None) -> list[sqlite3.Row]:
        q = "SELECT * FROM agents WHERE 1=1"
        params: list[t.Any] = []
        if zone:
            q += " AND zone = ?"
            params.append(zone)
        if tier:
            q += " AND tier = ?"
            params.append(tier)
        q += " ORDER BY id"
        return list(self.conn.execute(q, params).fetchall())

    # --- tier 2 -------------------------------------------------------

    def get_tier2_state(self, agent_id: str) -> t.Optional[Tier2State]:
        row = self.conn.execute(
            "SELECT * FROM agent_state_tier2 WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        return Tier2State(
            agent_id=row["agent_id"],
            mood=row["mood"],
            memory_summary=row["memory_summary"],
            last_reflection_at=row["last_reflection_at"],
        )

    def update_tier2(self, agent_id: str, mood: str, memory: str) -> None:
        self.conn.execute(
            """UPDATE agent_state_tier2
               SET mood = ?, memory_summary = ?, last_reflection_at = ?
               WHERE agent_id = ?""",
            (mood, memory, int(time.time()), agent_id),
        )
        self.conn.commit()

    def tier2_due_for_reflection(self, interval_seconds: int = 3600) -> list[str]:
        cutoff = int(time.time()) - interval_seconds
        rows = self.conn.execute(
            """SELECT agent_id FROM agent_state_tier2
               WHERE last_reflection_at < ?
               ORDER BY last_reflection_at ASC""",
            (cutoff,),
        ).fetchall()
        return [r["agent_id"] for r in rows]

    # --- tier 3 -------------------------------------------------------

    def get_tier3_state(self, agent_id: str) -> t.Optional[Tier3State]:
        row = self.conn.execute(
            "SELECT * FROM agent_state_tier3 WHERE agent_id = ?",
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        return Tier3State(
            agent_id=row["agent_id"],
            current_goal=row["current_goal"],
            current_location=row["current_location"],
            schedule_index=row["schedule_index"],
            journal=json.loads(row["journal_json"]),
            last_reflection_at=row["last_reflection_at"],
        )

    def update_tier3(self, agent_id: str, *,
                     current_goal: t.Optional[str] = None,
                     current_location: t.Optional[str] = None,
                     schedule_index: t.Optional[int] = None,
                     append_journal: t.Optional[dict] = None) -> None:
        # fetch current to merge
        cur = self.get_tier3_state(agent_id)
        if cur is None:
            return
        new_goal = cur.current_goal if current_goal is None else current_goal
        new_loc = cur.current_location if current_location is None else current_location
        new_idx = cur.schedule_index if schedule_index is None else schedule_index
        new_journal = list(cur.journal)
        if append_journal is not None:
            new_journal.append(append_journal)
        self.conn.execute(
            """UPDATE agent_state_tier3
               SET current_goal = ?, current_location = ?,
                   schedule_index = ?, journal_json = ?,
                   last_reflection_at = ?
               WHERE agent_id = ?""",
            (new_goal, new_loc, new_idx, json.dumps(new_journal),
             int(time.time()), agent_id),
        )
        self.conn.commit()

    # --- events -------------------------------------------------------

    def push_event(self, agent_id: str, event_kind: str,
                   payload: t.Optional[dict] = None) -> int:
        cur = self.conn.execute(
            """INSERT INTO agent_events (agent_id, event_kind, payload, queued_at)
               VALUES (?, ?, ?, ?)""",
            (agent_id, event_kind,
             json.dumps(payload) if payload else None,
             int(time.time())),
        )
        self.conn.commit()
        return cur.lastrowid or 0

    def drain_events(self, agent_id: str, limit: int = 20) -> list[sqlite3.Row]:
        rows = self.conn.execute(
            """SELECT * FROM agent_events
               WHERE agent_id = ? AND processed_at IS NULL
               ORDER BY queued_at ASC LIMIT ?""",
            (agent_id, limit),
        ).fetchall()
        if rows:
            ids = tuple(r["id"] for r in rows)
            placeholders = ",".join("?" * len(ids))
            self.conn.execute(
                f"UPDATE agent_events SET processed_at = ? "
                f"WHERE id IN ({placeholders})",
                (int(time.time()), *ids),
            )
            self.conn.commit()
        return list(rows)

    def close(self) -> None:
        self.conn.close()
