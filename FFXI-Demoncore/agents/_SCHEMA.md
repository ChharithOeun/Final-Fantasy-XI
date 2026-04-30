# Agent YAML schema

Every NPC, vendor, hero, mob, and ambient creature in Demoncore has a
profile YAML in this directory. Server-side, the chharbot agent
orchestrator walks `agents/*.yaml` on boot, instantiates each agent at
the right tier (per `AI_WORLD_DENSITY.md`), and connects it to the LSB
event bus.

## Fields (all tiers)

```yaml
id:              # unique snake_case id, matches the in-level actor's tag
name:            # display name in chat / floating-name UI
zone:            # canonical zone slug (bastok_markets, southern_sandoria, ...)
position: [x, y, z]  # world cm, matches the placeholder in bastok_layered_scene.py
tier:            # 0_reactive | 1_scripted | 2_reflection | 3_hero | 4_rl
role:            # short label (vendor_zaldon, soldier_patrol, hero_cid, ...)
race:            # hume | elvaan | tarutaru | mithra | galka | beastman_quadav | etc.
gender:          # m | f | n
voice_profile:   # path to 30s wav for Higgs Audio cloning, or "none" for ambient
appearance:      # short prose used by the character generator
```

## Tier-specific fields

### Tier 0 (reactive)
```yaml
behavior_tree:   # path to a UE5 BT asset, e.g. "/Game/AI/BT/Wildlife_Rat"
flee_radius_cm:  # how close before the creature flees
```

### Tier 1 (scripted+bark)
```yaml
schedule:        # list of [time_of_day, location, animation] tuples
bark_pool:       # list of strings; one chosen per encounter weighted by mood
```

### Tier 2 (scripted + LLM reflection)
```yaml
personality:     # one-paragraph personality prompt for the LLM
starting_memory: # one-sentence seed memory; LLM rewrites this every game-hour
mood_axes:       # any of [happy, drunk, fearful, proud, lonely, angry, content]
bark_pool:       # mood-conditional barks, dict[mood -> [strings]]
schedule:        # same shape as Tier 1; locations the agent moves through
relationships:   # dict[other_agent_id -> short prose]; affects barks toward them
```

### Tier 3 (full generative)
```yaml
personality:     # multi-paragraph personality
backstory:       # 5-10 sentences; the agent's life before play started
goals:           # list of medium-term goals the agent is pursuing
schedule:        # detailed daily schedule
relationships:   # rich dict, mutual references between hero NPCs
journal_seed:    # first journal entry; LLM appends one per game-day
```

### Tier 4 (RL combat policy)
```yaml
mob_class:       # the policy is per-class, not per-instance
policy_onnx:     # path to trained ONNX policy
state_features:  # the input feature vector schema
action_space:    # list of action ids the policy can output
```

## Damage hooks (any tier may also include)

```yaml
damage_response:
  on_aoe_near:   # what bark / behavior fires when a structure is damaged nearby
  on_player_attacked_me: # what fires if the player aggros this agent
  on_outlaw_nearby:      # what fires when an outlawed player walks past
```

## Voice cloning

`voice_profile` points at a 30-second wav stored under
`/Content/Voices/profiles/`. Higgs Audio v2 uses it as the conditioning
sample; every line the agent ever says is generated with that voice.
For ambient creatures (rats, pigeons), set to `none` and the audio
system uses pre-recorded sound effects per role.

## Ingestion

The chharbot orchestrator reads each YAML, validates against the tier
schema, writes to MariaDB:

```sql
agents (id, zone, tier, role, payload_yaml)
agent_state_tier2 (agent_id, mood, memory_summary, last_reflection_at)
agent_state_tier3 (agent_id, current_goal, current_location,
                   journal_yaml, last_reflection_at)
```

LSB queries the agents table when populating a zone for a logging-in
player; the orchestrator pushes mood / memory updates back via Redis
pub/sub so chat-bark selection always uses the live state.
