# SEAMLESS_WORLD.md

Vana'diel as one continuous world, not 200 separate instance
loads. As you approach a zone boundary, the next zone is already
streaming in. As you cross, no loading screen — the world just
*continues*. The Quadav patrol you spotted at the boundary is
still where it was; the Bastokan guards on the other side are
already alert.

And the mobs you provoked don't forget. They follow you. Across
zones. Until you outrun their senses, or until their enrage
timer burns out. Veterans will tell stories about Adamantoise
that chased them from Tahrongi all the way back to Windurst.

Three coupled designs in this doc:

1. **Streaming zone load** — UE5 World Partition + LSB
   server-side zone-stitching so transitions are instant
2. **Sensory aggro model** — sight + sound + smell envelopes
   per mob class; players can outrun by escaping all three
3. **Enrage + cross-zone pursuit** — mobs at high aggro levels
   chase through zone boundaries with extended persistence

Composes with:
- `MOB_CLASS_LIBRARY.md` — each mob class needs per-class
  sensory ranges + chase behavior
- `MOB_RESISTANCES.md` — enraged mobs have shifted affinity
  (more aggressive elements available)
- `MOOD_SYSTEM.md` — `enraged` is a new mood state at the
  apex of `furious`
- `WEIGHT_PHYSICS.md` — heavily-armored players make more
  sound (footstep amplitude scales with weight)
- `VISUAL_HEALTH_SYSTEM.md` — wounded mobs have shorter
  sensory ranges (visible damage = degraded perception)

---

## Why seamless (the design rationale)

Original FFXI zone transitions had three problems:

1. **Loading screen breaks immersion.** A 5-10 second screen
   for crossing a line on a map.
2. **Aggro instantly resets.** Players abused this — pull a
   monster to the zone line, cross, freedom. The "zone
   strategy" became canon.
3. **Zones felt like rooms.** The world's apparent size was
   constrained by the loading delay between rooms.

Demoncore inverts all three:

1. **No loading screen.** UE5 World Partition streams
   adjacent tiles in advance. Crossing is instant.
2. **Aggro persists.** Mobs cross zone boundaries to chase.
   The "zone strategy" stops working — players have to actually
   escape.
3. **The world is continuous.** Walking from Bastok to
   Windurst feels like a journey, not 4 loading screens.

Combined with `WEIGHT_PHYSICS.md`'s 25× faster Vana'diel time,
a long cross-continent run feels like an actual expedition.

---

## Streaming zone load (UE5 World Partition)

### How it works

UE5's World Partition (5.x) divides large worlds into a grid of
streaming cells. Each cell loads when the player gets within a
configured distance (default 50m) and unloads when they exceed
a hysteresis distance (default 80m).

For Demoncore, we treat **the whole continent as one World
Partition map** rather than per-zone .uassets:

```
/Game/Demoncore/Worlds/
  Quon.umap          (Quon continent — Bastok side)
  Mindartia.umap     (Mindartia continent — Sandy/Windy side)
  Tu_Lia.umap        (small islands; Norg)
```

Each .umap has hundreds of streaming cells covering the
extracted geometry from `ZONE_EXTRACTION_PIPELINE.md`. The
"zones" we still talk about (Bastok Markets, South Gustaberg,
Konschtat Highlands) are now just **named regions inside a
continuous World Partition map**.

### LSB server-side zone stitching

The LSB FFXI server canonically maintains separate "zone
processes" per zone. We modify this:

- **Continent-level master process** owns the whole continent's
  state. Player movement, mob movement, combat all happen in
  the master process.
- Per-zone processes still exist for *NPC dialog scripting*
  (Lua per zone) but talk to the continent master for
  position + combat.
- Cross-zone communication uses Redis pub/sub (same channel
  set as `LSB_BRIDGE.md`).
- A player's "current zone" is now metadata, not a process
  boundary.

When a player crosses what used to be a zone boundary:
- LSB updates their `current_zone` field
- The continent master process sees no break in their
  position-update stream
- Mobs that were chasing them keep chasing — the master
  process knows about the chase
- The orchestrator's mood propagation continues unaffected

This is a **substantial LSB refactor** but it's the single
biggest player-experience improvement in the entire project.

---

## Sensory aggro model

Each mob has three independent sensory envelopes:

```yaml
sensory_ranges:
  sight_range_cm:   1500       # 15m default
  sight_cone_deg:   180        # forward arc; 360 = omnidirectional
  sight_requires_los: true     # raycast check
  sound_range_cm:   800        # 8m default
  sound_passive_threshold: 0.3 # how loud something needs to be
  smell_range_cm:   0          # 0 = doesn't smell; predators have 4000+
  smell_decay_seconds: 30      # smell trail persistence
```

### Sight

A mob sees the player if:
1. Distance ≤ `sight_range_cm`
2. Player is within `sight_cone_deg` arc of the mob's facing
3. Line-of-sight raycast clears (no walls/cover)
4. Player is not invisible (Sneak/Invisible spells, Stealth)

Wounded mobs have reduced sight: `effective_range = base × visible_health_pct`.
A `wounded`-stage Quadav can only see ~50% as far.

### Sound

The world has an ambient noise floor (varies per zone — Bastok
forge is loud, dungeon depths are quiet). Player-generated
sounds layer on top:

```python
def player_sound_level(player) -> float:
    base = 0.2  # quiet movement
    if player.in_combat:
        base += 0.5
    if player.casting:
        base += 0.3   # vocal casts; NIN signs are silent
    if player.weapon_just_swung:
        base += 0.4
    base += player.weight / 200.0  # heavy = louder
    base *= player.movement_speed_pct  # running = louder
    if player.has_buff("sneak"):
        base *= 0.1
    return base
```

A mob hears the player if `player_sound_level > sound_passive_threshold`
within `sound_range_cm`. Sound passes through walls (less effectively
— attenuated by 50%).

### Smell

Predator mobs (wolves, demons, undead) use smell. Smell:

- Has a wider radius than sight (default 4000cm = 40m for predators)
- Doesn't require line of sight
- Persists as a "smell trail" for `smell_decay_seconds`
- Wind direction affects detection (downwind = +25% range; upwind = -25%)
- Some buffs counter (Deodorize spell, Cologne consumable)

A wolf that smells the player from 30m away will follow the
trail to the player even if the player has run out of sight.
This is what makes wolves *terrifying* in Demoncore.

---

## Per-mob-class sensory profiles (sample)

| Mob class           | sight_cm | sound_cm | smell_cm | sight_cone | predator |
| ------------------- | -------- | -------- | -------- | ---------- | -------- |
| Quadav Footsoldier  | 1500     | 800      | 0        | 180°       | no       |
| Yagudo Acolyte      | 1800     | 1000     | 0        | 360°       | no       |
| Orc Footsoldier     | 1200     | 1200     | 0        | 200°       | no       |
| Goblin Pickpocket   | 1000     | 600      | 0        | 270°       | no       |
| Tonberry Stalker    | 800      | 400      | 5000     | 180°       | YES      |
| Naga Renja          | 2000     | 800      | 0        | 360°       | no       |
| Wolf (Konschtat)    | 1500     | 1500     | 6000     | 270°       | YES      |
| Skeleton            | 600      | 0        | 4000     | 360°       | YES      |
| Bee Soldier         | 800      | 1500     | 800      | 360°       | partial  |
| Demon NM            | 3000     | 2500     | 8000     | 360°       | YES      |
| Adamantoise         | 2000     | 4000     | 10000    | 360°       | YES      |
| Ghost (undead)      | 2500     | 0        | 0        | 360°       | no       |

The sensory profile is part of each mob class YAML's
`sensory_ranges` block.

---

## Aggro state machine

Each mob has a current aggro level toward each player. States:

```
                provoked +
                 sensory
   neutral  ──────────────►  aggressive
       ▲                          │
       │                          │ damaged or
       │ time decay               │ provoked
       │ (after losing senses)    ▼
   neutral  ◄──────────────  enraged
                    time decay
                  + lost senses
```

### Aggro level numeric

```
0:    neutral
1:    suspicious      (sensed but not engaged; investigates)
2:    aggressive      (engaged in combat)
3:    enraged         (took heavy damage or provoked specifically)
4:    boss-enraged    (NM/boss state; cross-zone pursuit unlimited)
```

### Persistence per state

```yaml
aggro_persistence_seconds:
  suspicious:    20    # short — quick to forget after losing trail
  aggressive:    45    # vanilla FFXI-equivalent
  enraged:       300   # 5 minutes; player can't out-zone the mob
  boss_enraged:  1800  # 30 minutes; only sanctuary or death
```

### Persistence affected by

- Player damage to mob: each damage instance refreshes persistence
- Player Provoke ability: forces enraged for 60s minimum
- Successful intervention or skillchain on the mob:
  refreshes persistence + may push state up
- Mob taking AOE damage (player wasn't even targeting):
  pushes to suspicious if the mob wasn't already aware

---

## Cross-zone pursuit rules

If a mob is in `aggressive` or higher when the player crosses
a zone boundary:

- **Mob crosses too.** Continue chase in the new zone.
- **Mob's sensory ranges apply across boundary.** If the player
  outpaces the mob's senses for `aggro_persistence_seconds` of
  the current state, mob deaggros and walks back to spawn.
- **Enrage tier sticks.** A boss-enraged Adamantoise stays
  boss-enraged across 5+ zones until the timer burns or the
  player dies/zones into a sanctuary.
- **Sanctuary zones cancel pursuit.** Cities, NPC safe houses,
  Norg port — entering these zones immediately deaggros pursuing
  mobs. They wait at the sanctuary edge for ~30 seconds, then
  walk away.
- **Mob respawn timer pauses while chasing.** A mob chasing
  you for 5 minutes doesn't get its respawn started until the
  chase ends.

---

## How a player escapes (sensory exit)

Player can break aggro by escaping ALL THREE sensory envelopes
for the duration of `aggro_persistence_seconds`:

```python
def is_player_lost_by_mob(mob, player) -> bool:
    if not in_sight(mob, player):
        if mob.sight_range_cm == 0:
            in_sight_pass = True
        else:
            in_sight_pass = True   # out of sight
    else:
        return False   # still seen

    if mob.smell_range_cm > 0:
        if smell_distance(mob, player) <= mob.smell_range_cm:
            return False    # still smelled
    if player_sound_level(player) > mob.sound_passive_threshold:
        if distance(mob, player) <= mob.sound_range_cm:
            return False    # still heard

    # All three failed → player is lost
    return True
```

When `is_player_lost_by_mob` returns True, the mob's
`time_since_lost_player` timer starts. After
`aggro_persistence_seconds` elapse, mob deaggros.

### Player tactics

- **Sneak + Invisible**: removes sight + sound; smell still
  applies (wolves are still trouble)
- **Deodorize**: removes smell trail; sight + sound still apply
- **Mount with Mazurka**: -25% effective player sound (mount
  is fast but quiet)
- **NIN sign-cast in shadows**: silent; can hide in plain sight
- **Stealth gear**: reduces sound by 30-50%
- **Climbing onto cover**: breaks sight raycast
- **Crossing into different terrain**: doesn't help directly,
  but combined with other tactics extends escape

---

## Enrage triggers

A mob escalates to `enraged`:
- Took >50% of its HP_max in damage from one player
- Was provoked specifically
- Has been attacked by player party for more than 30 seconds
- Player landed a Magic Burst on it
- Boss critic LLM flagged the player as "high threat"

A mob escalates to `boss_enraged` (NM/boss only):
- Took >70% of HP_max
- Took a Level 3 Light or Darkness skillchain
- Took an Intervention MB save against its own ultimate
- Its critic LLM flagged "humiliated by party play"

Audible cues per state:
- `enraged`: mob roars audibly (~10m radius — players know
  they made it angry)
- `boss_enraged`: full audible "I AM ANGRY" line per boss
  voice library + visible body change (red aura, posture
  shift, sometimes armor falls off per `BOSS_GRAMMAR.md`)

---

## Mood-system integration

Per `MOOD_SYSTEM.md`, we add `enraged` as a recognized mood
state. Existing mobs gain it as a `mood_axes` option.

Event hooks (additions to `event_deltas.py`):

```
("became_enraged",          "*"            ) -> ("furious",  +0.50)
("became_enraged",          "*hero*"       ) -> ("furious",  +0.40)
("escaped_pursuing_mob",    "*hero*"       ) -> ("content",  +0.40)
("escaped_pursuing_mob",    "*civilian*"   ) -> ("content",  +0.30)
("crossed_zone_while_chased","*hero*"      ) -> ("alert",    +0.20)
("entered_sanctuary_safe",  "*"            ) -> ("content",  +0.30)
("mob_lost_my_trail",       "*"            ) -> ("content",  +0.20)
```

The world reacts when a player runs through it being chased.
Civilians visibly panic if a Quadav patrol pursues a player
through Bastok Mines. Soldiers go alert. The chase is part of
the city's living narrative.

---

## Performance budget

Streaming zone load + cross-zone pursuit costs more than the
canonical FFXI architecture. Estimates:

- **World Partition tile streaming**: ~50ms first-load per
  tile, ~5ms re-show. Tiles are ~200m × 200m. Player movement
  triggers ~1 tile load per ~10 seconds of running.
- **Cross-zone aggro tracking**: ~10 mob × player aggro pairs
  × server tick = ~600 records updated per second per
  continent. Trivial CPU cost.
- **LSB master-process refactor**: significant initial work.
  ~2-3 weeks of LSB Lua + C++ work to merge zones into
  continent processes. **The single biggest engineering risk
  in Demoncore.**

If the LSB refactor proves too costly, a fallback design is:
- Keep per-zone LSB processes
- Add a "cross-zone aggro relay" between processes via Redis
  pub/sub
- Mob "teleports" to the new zone process when it crosses
- Pursuit feels seamless to the player even though the
  server-side mob is technically a new instance
- Slightly less elegant but ships in days not weeks

---

## Status

- [x] Architecture doc (this file)
- [ ] UE5 World Partition setup for first continent (Quon)
      with extracted Bastok + Gustaberg geometry
- [ ] LSB master-process refactor OR cross-zone aggro relay
- [ ] Per-mob-class sensory_ranges YAML extension
- [ ] server/aggro_system/ — sensory + persistence model
- [ ] Player escape tactics: Sneak/Invisible/Deodorize integration
- [ ] First playtest: pull a Quadav from Beadeaux, cross the
      zone boundary, see if it follows
- [ ] Boss-enraged Adamantoise cross-zone-chase test (the
      story-generating moment)
- [ ] Sanctuary-zone deaggro behavior verification
- [ ] Audible cue library for enrage transitions
