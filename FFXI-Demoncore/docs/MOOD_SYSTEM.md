# MOOD_SYSTEM.md

Moods aren't decoration. In Demoncore, an NPC's mood drives:

- The bark they pick when you click on them
- The price they charge you (the gruff Zaldon takes 20% extra)
- Whether they hand over the quest item today or tell you "come back later"
- How quickly Pellah repairs your damaged structure
- Whether the guard lets you walk through with a low Honor score
- The animation set their idle plays (slumped shoulders for melancholy,
  crossed arms for gruff, whistling for content)

This doc is the contract. Every system that reads `mood` reads it the
same way, and every system that *changes* mood goes through the
propagation API so emergent social dynamics stay coherent.

---

## The mood vector (one axis per agent's declared `mood_axes`)

An agent's `mood_axes` list (from their YAML) is the closed set of
moods they can be in. Zaldon has `[content, gruff, melancholy]`.
Pellah has `[content, contemplative, weary, mischievous]`. Each agent
is in exactly one mood at a time — these are exclusive states, not
sliders.

We chose discrete moods over continuous valence/arousal because:
1. Authors can write bark pools per-mood instead of per-vector-region
2. The LLM is much better at picking from a labelled set than emitting floats
3. Visual cues (idle anims, voice tone) cluster cleanly into states

A small numeric `mood_intensity` (0.0 - 1.0) rides alongside the label
so we can express "Zaldon is mildly gruff vs furious" without bloating
the label set. The intensity decays toward 0.5 at a configurable rate
between reflections, so moods naturally settle.

---

## Mood transitions

Three sources can change an agent's mood:

### 1. Reflection (the slow path)
Once per game-hour (Tier 2) or per game-day (Tier 3), the orchestrator
asks the LLM to pick the next mood from the agent's `mood_axes` based
on recent events. Result becomes the new mood + memory.

### 2. Direct event (the fast path)
When something dramatic happens (PvP outlaw walks past, a barrel
breaks at their feet, a friend gets attacked), the orchestrator queues
an event AND immediately applies a per-event mood delta from a
**static lookup table**. No LLM round-trip — moods snap immediately.
The reflection cycle later refines the memory based on what the agent
did during that mood.

### 3. Propagation (the social path)
Moods spread through the relationship graph. If Cornelia goes to
`furious` (her mood_axes), Cid's mood probability shifts toward his
nearest negative state (`worried`) on the next propagation tick.

---

## Direct event mood-delta table

A small immutable table maps `(event_kind, role)` → mood shift.
Defined once, used everywhere. Authors can override per-agent in the
YAML's `damage_response` block.

```python
EVENT_MOOD_DELTAS = {
  ("aoe_near", "*vendor*"):           ("gruff", +0.3),
  ("aoe_near", "*"):                  ("alarm", +0.2),
  ("structure_destroyed_near", "*"):  ("gruff", +0.4),
  ("outlaw_walked_past", "*guard*"):  ("alert", +0.5),
  ("outlaw_walked_past", "*vendor*"): ("gruff", +0.2),
  ("outlaw_walked_past", "*beggar*"): ("fearful", +0.3),
  ("outlaw_walked_past", "*pickpocket*"): ("content", +0.2),  # peer recognition
  ("friend_attacked", "*"):           ("furious", +0.6),
  ("nation_raid_alarm", "*civilian*"):("fearful", +0.6),
  ("nation_raid_alarm", "*soldier*"): ("alert", +0.7),
  ("payment_received", "*vendor*"):   ("content", +0.2),
  ("haggle_failed", "*vendor*"):      ("gruff", +0.15),
  ("repair_completed", "pellah"):     ("content", +0.3),
  ("daily_loop_start", "*tavern_drunk*"): ("content", +0.2),  # they wake up okay
  ("daily_loop_evening", "*tavern_drunk*"): ("drunk", +0.5),  # then drink
  ("rain_started", "*"):              ("melancholy", +0.1),
  ("nighttime", "*pickpocket*"):      ("content", +0.2),
  ("daytime", "*pickpocket*"):        ("alert", +0.2),
}
```

The matching is by glob — `*vendor*` matches any role containing
`vendor`. First match wins; falls through to a `("*", "*")` no-op if
nothing matches.

When an event fires:
1. The mood delta lookup runs against the agent's role
2. If the result mood is in the agent's `mood_axes`, apply it (clamping intensity to [0, 1])
3. If not in `mood_axes`, fall back to the agent's nearest declared mood
   per a `mood_proximity_map` (e.g. `furious → gruff`, `alarm → fearful`)

---

## Mood propagation through relationships

Once per propagation tick (every 5 minutes), the orchestrator walks
the relationship graph and applies a soft mood pull:

```
for each agent A with relationships R:
  for each (target_id, kind) in R:
    if target's mood is "negative" (gruff, melancholy, furious, fearful):
      A.mood_intensity *= 1.0
      A.mood -> agent's nearest_negative_mood
        with intensity = 0.3 * target.intensity * RELATIONSHIP_WEIGHT[kind]
    elif target's mood is "positive" (content, mischievous):
      A.mood -> nearest_positive_mood
        with intensity = 0.15 * target.intensity * RELATIONSHIP_WEIGHT[kind]
```

`RELATIONSHIP_WEIGHT` defaults:
```
"family"        : 1.0    (deepest pull — Cid→Cornelia, parent→child)
"best_friend"   : 0.9    (Cid↔Volker)
"professional"  : 0.5    (Cornelia↔Pellah)
"acquaintance"  : 0.2    (Zaldon↔Pellah)
"adversary"     : -0.3   (their bad mood makes you content)
```

Authors mark the relationship type in the YAML. If unmarked, the kind
is inferred from the prose (the reflection LLM tags it on first parse).

The result: when Cornelia is `furious` (relationship dispute with
Cid), Cid's next reflection runs with a small `worried` lean. The
LLM sees this in the prompt context as "Cid is feeling worried
because Cornelia is furious" and writes a journal entry that touches
on the rift. **The world stitches itself together emotionally.**

---

## Environmental mood (weather, time, zone events)

A separate ambient mood tick runs every 10 minutes, applies global
deltas to ALL agents in a zone:

| Trigger                        | Delta target          | Notes                         |
| ------------------------------ | --------------------- | ----------------------------- |
| Rain just started              | melancholy +0.10      | inverse for amphibian races   |
| First snow of season           | content +0.15         | nostalgic                     |
| Nighttime in safe zone         | content +0.05         | quiet streets                 |
| Nighttime in dangerous zone    | fearful +0.10         | night beasts                  |
| Smokestack puffing extra       | gruff +0.05           | Bastok-only                   |
| Forge fire visible from plaza  | content +0.08         | Bastok-only — pride           |
| Nation military mobilizing     | alert +0.20           | siege incoming                |
| Major NPC died this game-day   | melancholy +0.15      | only if relationship > 0.3    |
| Festival event in zone         | content +0.30         | overrides almost everything   |

The `LSB` server emits these triggers on its event bus; the
orchestrator subscribes via Redis pub/sub.

---

## Mood → gameplay hooks (the player-visible payoff)

### Vendors
| Mood          | Price modifier | Inventory available | Tone of bark      |
| ------------- | --------------- | ------------------- | ----------------- |
| content       | x1.00           | full                | warm              |
| gruff         | x1.20           | hides premium gear  | curt              |
| melancholy    | x0.85 (firesale)| haphazard           | distant           |
| furious       | refuses to sell | n/a                 | shouted           |

A player can game this. Buy from Zaldon at 5am when he's freshly
content; haggle with Cornelia after a rough day for a discount;
DON'T try to shop with Volker the morning after a Quadav raid alarm.

### Repair NPCs (Pellah and similar)
| Mood          | Repair speed | Cost   |
| ------------- | ------------- | ------ |
| content       | x1.00         | base   |
| contemplative | x0.85         | base   |
| weary         | x0.70         | base   |
| mischievous   | x1.10         | -10%   |

Mischievous Pellah is a well-known buff. Players will time their
repair runs to hit him in his "Heh, today I'll show off" mood.

### Quest givers
| Mood          | Behavior                                            |
| ------------- | --------------------------------------------------- |
| content       | normal — hands over quest item                      |
| gruff         | demands a small additional task first               |
| melancholy    | tells you to come back tomorrow (instance reset)    |
| fearful       | gives an emergency-flavored variant of the quest    |

### Combatants (soldier_patrol_*, RL-policy mobs)
| Mood          | Combat effect                                       |
| ------------- | --------------------------------------------------- |
| alert         | +20% accuracy, +10% damage                          |
| furious       | +30% damage, -15% defense                           |
| fearful       | -20% accuracy, considers fleeing                    |
| content       | baseline                                            |

### Outlaws walking past guards
The guard's mood determines whether they call for backup, ignore,
or arrest:

| Mood          | Threshold                                           |
| ------------- | --------------------------------------------------- |
| content       | only arrests if Honor < -10000                      |
| alert         | arrests if Honor < -3000                            |
| furious       | arrests on sight regardless of Honor                |
| fearful       | retreats; does not engage                           |

This makes the outlaw lifestyle dynamic instead of binary — running
errands as an outlaw means watching the guards' moods.

---

## Visual mood cues (the player should feel it without reading text)

Each mood has an idle-animation variant + a voice-tone preset for the
TTS pipeline:

| Mood          | Idle anim hint                          | Voice tone (Higgs prompt)        |
| ------------- | --------------------------------------- | --------------------------------- |
| content       | relaxed weight, occasional whistle/hum  | "warm, even"                      |
| gruff         | crossed arms, jaw set, side glance      | "clipped, lower register"         |
| melancholy    | slumped shoulders, looking at nothing   | "softer, slower, breathy"         |
| furious       | hands clenched, sharp head turns        | "louder, sharper, faster"         |
| fearful       | small body, eyes scanning, shifting     | "higher pitch, shaky"             |
| alert         | upright stance, tracking head movement  | "crisp, professional"             |
| drunk         | sway, exaggerated gestures              | "slurred, drawling"               |
| contemplative | hand-on-chin, slow head nod, distant    | "slower, lower energy"            |
| mischievous   | slight smirk, quick gestures            | "playful, slight upward inflect"  |

Each mood maps to **one** SkeletalMesh idle-anim slot and **one** Higgs
voice condition prompt. Authoring overhead: ~9 idle anims authored once
across all races, reused across thousands of agents.

For named hero NPCs (Cid, Volker, Cornelia, Maat), we author per-character
mood idle variants for personality. For everyone else, the race-default
idle variants do the work.

---

## Implementation in the orchestrator

The `mood_propagation` module hooks in after each reflection batch:

```python
# server/agent_orchestrator/mood_propagation.py

def propagate_moods_once(db, profiles_by_id):
    """One pass of social propagation. Call after reflection cycles."""
    snapshot = {p.id: db.get_tier2_state(p.id) or db.get_tier3_state(p.id)
                for p in profiles_by_id.values()}
    deltas = {}
    for prof in profiles_by_id.values():
        my = snapshot.get(prof.id)
        if not my: continue
        for target_id, edge_descr in (prof.raw.get("relationships") or {}).items():
            target_state = snapshot.get(target_id)
            if not target_state: continue
            edge_kind = infer_edge_kind(edge_descr)
            weight = RELATIONSHIP_WEIGHT.get(edge_kind, 0.2)
            deltas[prof.id] = compute_delta(my, target_state, weight)
    for agent_id, (new_mood, intensity) in deltas.items():
        # apply if the agent's mood_axes accepts this label
        prof = profiles_by_id[agent_id]
        if new_mood in (prof.raw.get("mood_axes") or []):
            db.update_tier2(agent_id, new_mood, ...)
```

Direct events use a similar but synchronous path: when an event hits,
the orchestrator looks up the delta, applies it immediately, persists.

---

## Authoring contract

Authoring a new agent doesn't require any mood-system knowledge if
you follow the YAML schema:

1. List `mood_axes` — the closed set of moods this agent can be in
2. Pick a `starting_mood`
3. Write `bark_pool` keyed by mood
4. (Optional) Add `damage_response` overrides for specific events
5. (Optional) Mark relationships with `kind: family|best_friend|professional|acquaintance|adversary`

Everything else — propagation, environmental ticks, gameplay hooks —
is driven by the orchestrator using the schema you authored. The
mood system *just works*.

---

## Status

- [x] Mood system design (this file)
- [x] Per-agent mood_axes in YAML (5 flagship profiles authored)
- [x] DB column for mood + intensity (extend agent_state_tier2)
- [ ] Direct event delta table (`server/agent_orchestrator/event_deltas.py`)
- [ ] Propagation tick (`server/agent_orchestrator/mood_propagation.py`)
- [ ] Environmental tick subscriber (LSB Redis pub/sub)
- [ ] Per-mood idle anim slots wired into UE5 character ABP
- [ ] Per-mood Higgs voice condition prompts
- [ ] First in-game smoke test: Zaldon mood gates his price
