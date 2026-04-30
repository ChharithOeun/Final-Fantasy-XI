# DAMAGE_PHYSICS_HEALING.md

The world has weight. Spells crater earth, swords splinter wood, beastman
sieges punch holes in city walls. And then — over time — it heals. Stone
re-knits, wood regrows, banners stitch themselves back together. The
city remembers the fight but doesn't carry the scar forever.

This is one of Demoncore's signature systems. It changes how PvP feels
(consequences are visible), how Besieged feels (defending Bastok during
a Quadav raid means watching the gate crack and praying it holds), and
how cinematic the world looks under any camera angle (every prop has
state, not just position).

---

## Why heal? (the design rationale)

Persistent destruction in MMOs has a known failure mode: after 6 months
the world looks like a landfill, because every dumb player has bombed
every wall, smashed every barrel, and nobody patched anything. The world
becomes ugly and stale.

Three knobs solve this:

1. **Heal over time** — natural repair without manual intervention
2. **Repair NPCs** — accelerate healing for a price (gil sink)
3. **Per-structure max-damage threshold** — some structures *can* be
   permanently destroyed during major events (sieges, story moments)
   but only above a damage threshold most players can't reach solo

The result: the world breathes. After a battle, you see craters and
splintered crates. An hour later the lanterns are back up. A day later
the wall is whole. The big sieges leave permanent scars in zones we
explicitly mark as scarable.

---

## The damage model

Every destructible thing in the world is a `HealingStructure`. It has:

```
HP_current        : int   = HP_max
HP_max            : int           e.g. 100 (barrel) → 1_000_000 (city wall)
heal_rate         : float         HP per real-world second
heal_delay_s      : float         seconds of "no damage taken" before heal starts
permanent_threshold : float = 1.0 fraction of HP_max where damage becomes permanent
                                 (1.0 = never permanent, 0.0 = always permanent;
                                  city walls typically 0.05 — once hit for 95%+,
                                  the chunk stays gone until manual repair)
visible_state     : enum  {pristine, cracked, battered, ruined, destroyed}
```

**Damage stages** (visible to players):
- 100-75% HP → `pristine` — original mesh, no decals
- 75-50% HP → `cracked` — damage decals applied, light dust particles
- 50-25% HP → `battered` — chunks broken off via Chaos Geometry Collection,
                          smoke trail, embers
- 25-1% HP → `ruined` — half the geometry gone, structural fire
- 0% HP → `destroyed` — Chaos full-fracture, debris on ground; if
                       within `permanent_threshold` heals back over time;
                       if past it, debris stays + smolder VFX

**Healing**: while no damage has been taken for `heal_delay_s` seconds,
each tick adds `heal_rate * dt` HP. When HP crosses a stage boundary
upward, the visible state animates back: chunks reverse-fly into place
on a 1-2 second tween, decals fade, dust clears, "magic stitch" particle
effect plays. Light enchanted shimmer for stone, sap-like wood-grain
shimmer for wood, sparks for metal.

The healing animation is the spectacle. Players will *want* to
sit in town after a battle just to watch the city stitch itself back
together. It's a visual reward.

---

## Heal rate presets (tuning anchors)

| Structure                | HP_max    | heal_rate (HP/s) | full-heal time |
| ------------------------ | --------- | ---------------- | -------------- |
| Barrel                   | 100       | 5                | 20 s           |
| Crate stack              | 200       | 5                | 40 s           |
| Wooden cart              | 500       | 5                | 100 s          |
| Lantern post             | 80        | 4                | 20 s           |
| Vendor stall awning      | 300       | 3                | 100 s          |
| Wooden palisade segment  | 2_000     | 8                | 250 s ≈ 4 min  |
| Stone wall section       | 50_000    | 30               | ~28 min        |
| Bastok city gate         | 200_000   | 50               | ~67 min        |
| Castle tower             | 1_000_000 | 80               | ~3.5 hours     |

Heal rates use a tempo curve: stuff that breaks frequently (barrels,
lanterns) heals fast so the city looks normal between encounters. Stuff
that breaks rarely (gates, walls) heals slowly so a defended siege still
matters.

`heal_delay_s` is typically 8-15 seconds — long enough that a sustained
attack drives HP down, short enough that the first 15 seconds of peace
already kicks off recovery.

---

## The repair NPC economy hook

Every nation has 2-4 Repair NPCs (e.g. `Voinaut [Bastok masonry guild]`,
`Pellah [Sandy carpenter]`, `Mihli [Windy hedge witch]`). They:

- Stand near commonly-damaged areas (city gates, lighthouse, mine entrances)
- Charge gil to fast-forward healing on a single structure
- Cost scales with HP missing: typically `(HP_missing / HP_max) * gil_per_HP_max`
- Repair NPCs themselves level up via the NPC progression system —
  high-skill repairers heal faster and unlock special structures
  (e.g. only Voinaut's apprentice past lvl 60 can repair the
  Metalworks elevator)

Gil sink + skill-progression NPC + economy reactivity all in one feature.

---

## Chaos integration (UE5 implementation)

UE5 ships with Chaos Destruction. Each destructible structure becomes a
`Geometry Collection` (asset that holds the fractured pieces of a static
mesh). The fracture is authored once in the editor:

1. Static mesh in → Fracture mode → Voronoi or Uniform fracture
2. Resulting Geometry Collection saved to `/Game/Zones/<zone>/Destructibles/`
3. Spawn as a `GeometryCollectionActor` instead of `StaticMeshActor`

Per-structure HP/heal logic lives in a Blueprint component:
`BPC_HealingStructure`. The component holds the HP state, listens for
damage events from the LSB damage broker, drives the visible state
machine, and runs the heal tick.

When healing crosses a stage boundary upward, the component re-attaches
fractured chunks via Chaos's `SetEnableGravity(false) +
SetSimulatePhysics(false) + Tween-to-rest-pose + SnapBackToOrigin`
sequence. Plays the heal VFX and a chime sound while doing it.

---

## Server authority (LSB integration)

Damage and healing are server-authoritative. The flow:

```
client → LSB: "I cast Earthquake at coord X,Y,Z, radius R, damage D"
LSB →   compute_aoe_damage(X, Y, Z, R, D, structure_table)
LSB →   for each structure within radius:
            structure.hp -= damage
            structure.last_hit_at = now()
            if structure.hp <= 0 and structure.permanent_threshold reached:
                structure.permanent = true
LSB →   broadcast: "structure_damaged" {id, new_hp, new_state}
clients in zone →  BPC_HealingStructure.on_damage(new_hp, new_state)

(separately, every 1s)
LSB →   for each structure where hp < hp_max and time_since_hit > heal_delay:
            structure.hp = min(hp_max, hp + heal_rate)
LSB →   broadcast structure_healed updates only when state stage changes
        (so the network doesn't flood with HP ticks)
```

A new SQL table `zone_structures` stores the static structure registry:

```sql
CREATE TABLE zone_structures (
  id              INT PRIMARY KEY,
  zone_id         INT NOT NULL,
  structure_kind  VARCHAR(32),        -- "barrel" | "wall_stone" | "gate" | ...
  position        VARCHAR(64),        -- "x,y,z" world coords
  hp_max          INT NOT NULL,
  heal_rate       FLOAT NOT NULL,
  heal_delay_s    FLOAT NOT NULL,
  permanent_threshold FLOAT DEFAULT 1.0,
  KEY zone_idx (zone_id)
);
```

A separate `zone_structures_state` table holds the live HP per structure
per server. On server restart we reload the state — partial damage
persists across server restarts, so a wall hit in last night's siege is
still visibly damaged in the morning while it heals.

---

## Permanent damage and big events

Sometimes the world *should* keep a scar. The `permanent_threshold`
field controls this. During a Besieged-tier raid, beastman bosses can
push damage past the threshold; once past, the structure stops healing
and stays in the `ruined` or `destroyed` state until:

- A player-funded gil contribution unlocks repair NPCs to start work
  (gil sink for the whole community)
- OR a story mission reaches a "the city rebuilds" beat

This is how the world grows lore. Six months in, a player walks past
the West Bastok wall and sees a permanent crater from the Quadav raid
of three weeks ago. The crater becomes part of the city's identity.

We mark a small subset of structures (~1% — the iconic ones) with low
`permanent_threshold` so they CAN scar. Everything else heals fully.

---

## Player-driven destruction (PvP and griefing)

PvP damage to structures is allowed but expensive:
- Damaging structures inside your own nation lowers your **Honor** gauge
  (see `HONOR_REPUTATION.md`) and racks up a fine
- Damaging structures inside an enemy nation as part of an outlaw raid
  is normal (encouraged during nation-vs-nation periods)
- Destroying iconic structures triggers a server-wide alert and tags
  the perpetrator with a high-priority bounty

Mob AoE during normal play does *not* damage structures unless the mob
is part of a Besieged-tier event. This prevents accidental griefing and
keeps fishing-for-XP-near-stalls a viable activity.

---

## Visual VFX library (per material class)

Each structure_kind references a Niagara VFX preset:

| structure_kind  | break VFX         | heal VFX                  | break SFX          |
| --------------- | ----------------- | ------------------------- | ------------------ |
| wood            | splinters + dust  | sap shimmer + grain glow  | wood crack         |
| stone_brick     | rocks + dust      | white mineral shimmer     | stone shatter      |
| stone_carved    | rocks + dust      | rune shimmer (Bastok)     | heavy stone        |
| metal_industrial| sparks + smoke    | molten weld glow          | metal clang        |
| cloth_banner    | shred fragments   | weave-loom shimmer        | cloth tear         |
| glass_window    | shards            | crystalline regrow        | glass shatter      |

Niagara templates live at `/Game/VFX/HealingStructures/`. Hand-authored
once; reused across every zone.

---

## Status and open work

- [x] Design doc (this file)
- [ ] `BPC_HealingStructure` Blueprint component (with damage + heal tick)
- [ ] `zone_structures` + `zone_structures_state` SQL tables in LSB
- [ ] LSB damage broker that converts AoE casts into structure damage events
- [ ] Niagara VFX templates per structure_kind (6 templates)
- [ ] Editor utility: select static mesh actors → bulk-convert to
      `GeometryCollectionActor` + add `BPC_HealingStructure`
- [ ] First-pass tuning sweep on Bastok Markets structures (set HP /
      heal_rate per actor in the layered scene)
- [ ] PvP damage rule integration (Honor + bounty hooks)
- [ ] Permanent-damage flag UI for designers (so they can mark which
      structures scar)
