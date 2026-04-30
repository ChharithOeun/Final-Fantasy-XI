# LSB_BRIDGE.md

How the LandSandBoat (LSB) FFXI server tells the chharbot agent
orchestrator what's happening in-game.

The LSB server runs the canonical FFXI logic: combat resolution,
spell casts, mob spawns, AOE damage, party formation, NPC dialog
calls. The agent orchestrator runs the AI density layer: moods,
schedules, reflections, intervention timing.

These two need to talk. Without the bridge, the orchestrator is a
sandbox. With it, the world breathes — every in-game event flows
into the orchestrator's mood + memory pipeline.

---

## What the bridge moves

### Inbound (LSB → orchestrator)
The orchestrator's `apply_event()` and `push_event()` methods are
the receiving channels. LSB pushes:

- **Combat events**: `aoe_near`, `damage_stage_<X>`, `friend_attacked`,
  `friend_died`, `spell_completed`, `spell_interrupted`,
  `skillchain_called`, `magic_burst_landed`,
  `intervention_mb_succeeded`
- **Player interaction**: `payment_received`, `haggle_failed`,
  `outlaw_walked_past`, `repair_completed`
- **World rhythm**: `nation_raid_alarm`, `festival_active`,
  `major_npc_died_today`, `boss_phase_transition`,
  `boss_cried_phase_transition`
- **Damage stages**: `damage_stage_bloodied`, `damage_stage_wounded`
  etc. (per `VISUAL_HEALTH_SYSTEM.md`)

### Outbound (orchestrator → LSB)
Less frequent. The orchestrator pushes back:
- **Bark selection**: when a player clicks a Tier-2 NPC, LSB asks
  the orchestrator "what bark should I show?" — orchestrator
  returns a mood-appropriate bark from the agent's pool
- **Schedule-driven movement**: orchestrator has the agent's
  schedule; pushes "move to location X with animation Y" commands
  on schedule transitions
- **Hero-NPC active goal hints**: "Cid is currently focused on
  Galka-3 prototype" — LSB uses this to gate quest dialogue

---

## Transport: HTTP webhook + Redis pub/sub

Two channels because LSB is C++ and chharbot is Python:

### Channel 1 — HTTP webhook (LSB → orchestrator)
LSB makes synchronous HTTP POST to chharbot's bridge endpoint
when an event fires. Sub-millisecond local-loopback latency.

```
POST http://localhost:7777/lsb/event
Content-Type: application/json

{
  "agent_id": "vendor_zaldon",
  "event_kind": "aoe_near",
  "payload": {"distance_m": 3, "damage_estimate": 250},
  "timestamp": 1735594800.123
}
```

Endpoint replies with the resulting state change (or an error):

```
200 OK
{
  "ok": true,
  "agent_id": "vendor_zaldon",
  "mood_changed": true,
  "new_mood": "gruff",
  "queued_event_id": 42
}
```

LSB doesn't *need* the response (event is fire-and-forget for
mood/memory updates), but it's useful for debugging and bark
selection (where LSB does need a response in real time).

### Channel 2 — Redis pub/sub (orchestrator → LSB)
For schedule-driven movements and reflection-cycle outputs, the
orchestrator publishes to Redis topics. LSB subscribes:

- `demoncore:agent:<agent_id>:move` — schedule transition fires;
  payload includes new location + animation hint
- `demoncore:agent:<agent_id>:bark_pool_changed` — reflection
  rewrote the agent's mood / memory; LSB invalidates cached
  barks
- `demoncore:zone:<zone>:env_event` — environmental events
  (rain_started, nighttime, festival_active)
- `demoncore:zone:<zone>:nation_alarm` — siege / raid mobilization

LSB's existing Redis client (used for player session caching)
adds these subscriptions on boot. Cost: zero (Redis is already in
the LSB stack).

---

## Sample flows

### Flow 1: Player AoE near Zaldon's stall

```
1. Player casts Earthquake at coord (-2400, -2400, 130) radius 8m
2. LSB damage broker computes affected entities
3. LSB sees Zaldon (vendor_zaldon) is within 8m of impact center
4. LSB POSTs:
     {agent_id: "vendor_zaldon",
      event_kind: "aoe_near",
      payload: {damage_estimate: 250}}
5. Orchestrator's bridge endpoint receives POST
6. Orchestrator calls apply_event()
   → matches ("aoe_near", "*vendor*") → ("gruff", +0.3)
   → mood_axes match → applied
   → DB updated: zaldon mood "content" → "gruff"
7. Orchestrator returns {ok, mood_changed: true, new_mood: "gruff"}
8. Orchestrator publishes Redis: "demoncore:agent:vendor_zaldon:bark_pool_changed"
9. LSB invalidates Zaldon's cached bark
10. Next time the player clicks Zaldon, LSB asks orchestrator
    for a fresh bark — gets one from the gruff pool
```

Latency: end-to-end ~5-10ms on local-loopback. Player perceives no delay.

### Flow 2: Bondrak schedule transition (18:00 → drinks)

```
1. Orchestrator's scheduler ticks; Vana'diel time crosses 18:00
2. Scheduler fires "daily_loop_evening" environmental event
3. Bondrak's mood flips content → drunk via apply_event
4. Bondrak's schedule index advances to slot[6] (evening_drinking_starts)
5. Orchestrator publishes Redis:
     demoncore:agent:tavern_drunk:move
     payload: {location: "tavern_table_corner",
               animation: "evening_drinking_starts"}
6. LSB subscribes; receives the message
7. LSB moves Bondrak's NPC actor to the tavern corner
8. LSB triggers Bondrak's "drunk" idle anim
9. Players in the tavern see Bondrak shuffle to his corner with a
   visible mood shift (per VISUAL_HEALTH_SYSTEM idle anim slot)
```

Latency: orchestrator tick is 10s; messages flush in <1ms on Redis.

### Flow 3: Boss phase transition (Maat goes to wounded)

```
1. Player party hits Maat below 50% HP
2. LSB damage broker sees Maat crossed visible-health stage:
   bloodied → wounded
3. LSB POSTs:
     {agent_id: "hero_maat",
      event_kind: "damage_stage_wounded",
      payload: {hp_pct: 0.48}}
4. Orchestrator updates Maat's mood (per the hero
   damage_stage_wounded event_delta entry: alert +0.30)
5. LSB additionally fires:
     {agent_id: "hero_maat",
      event_kind: "boss_cried_phase_transition",
      payload: {new_phase: "wounded"}}
6. Orchestrator notes — passes to the Tier-3 critic LLM
   (next reflection cycle considers "Maat is in wounded phase
   with party using cheese strategy")
7. Critic LLM outputs strategy hints back via Redis
   demoncore:agent:hero_maat:critic_hints
8. LSB reads hints; instructs Maat's combat AI to use
   Tornado Kick instead of Hundred Fists for next attack
   (close gap on the BLM kiting at range)
```

This is where the Tier-3 critic LLM truly lives — in the LSB
bridge round-trip during fight.

---

## Implementation outline (FastAPI sidecar)

A simple FastAPI sidecar process runs alongside the orchestrator
and exposes the HTTP endpoint. ~80 lines of Python including
auth + structured logging. See
`server/lsb_bridge/bridge.py` for the implementation.

### Authentication
LSB and the bridge run on the same host. We use a shared secret
in a header `X-Demoncore-Bridge-Token`. The bridge rejects
requests without the token. Token rotates on chharbot restart.

This is intentionally simple — we're not exposing this endpoint
to the network. It's loopback-only. If the user's deployment
exposes it (multi-host setup), the bridge upgrades to mTLS via
config.

### Failure modes
- **Orchestrator down**: LSB POSTs return 503; LSB caches the
  event for retry. Combat doesn't break — bark selection falls
  through to a hard-coded default bark per role.
- **LSB down**: orchestrator continues ticking schedules,
  reflections, and propagation. When LSB comes back, it
  catches up via Redis pub/sub backlog.
- **Network partition**: Redis pub/sub uses `at-most-once`
  delivery so the orchestrator may push movement commands LSB
  never receives. Acceptable for ambient NPCs; for hero NPCs
  the LSB requests a position-sync on reconnect.

---

## Status

- [x] Design doc (this file)
- [ ] FastAPI sidecar at server/lsb_bridge/bridge.py (stub committed)
- [ ] Token-auth header check
- [ ] Redis pub/sub publisher in orchestrator
- [ ] LSB Lua extension to POST events to the bridge
- [ ] LSB Lua extension to subscribe to Redis topics
- [ ] First playtest: Earthquake near Zaldon → bark changes
- [ ] First playtest: Bondrak goes drunk at 18:00 → moves to tavern corner
