# AOE_TELEGRAPH.md

How players see — and don't see — area-of-effect spells and abilities.

The grammar is simple and asymmetric:

- **You see your own AOE preview** before you commit to the cast.
  A dashed translucent shape on the ground, in your faction's color,
  visible only to you.
- **Once you start casting, the AOE becomes a solid telegraph**
  visible to *everyone* in range. Players inside it have ~half the
  cast time to step out before it lands.
- **Enemy AOE is NEVER preview-visible to players.** No ground decals
  for incoming boss attacks. You read the enemy's wind-up animation,
  position, and chant — same as the visual-health system makes you
  read damage state. Skill ceiling lives in the visual reading.

Combined with `VISUAL_HEALTH_SYSTEM.md`'s no-HP-bars and `WEIGHT_PHYSICS.md`'s
movement-while-casting math, AOE telegraphs become the highest-leverage
combat readability surface in Demoncore.

---

## Why telegraphs (the design rationale)

FFXI originally exposed AOE as a binary "you got hit / you didn't" —
the spell announced the result, not the threat. Players who got good
at FFXI raids learned positioning by memorizing what each boss could
do, not by seeing where it would land.

Modern combat games (FFXIV, Lost Ark, WoW M+) use ground telegraphs
to externalize this. Telegraphs let new players see the threat and
veterans optimize their dodging. The skill ceiling rises because
*reading* and *acting* are now separable observable skills.

Demoncore inherits this — but *only* for player-cast AOE. Enemy AOE
stays animation-readable. You can't dodge what you can't read off the
boss's wind-up, the same way you can't HP-bar a target without using
Scan. The hardcore difficulty pillar holds.

---

## The two states

### State 1: PREVIEW (only-self-visible)

When the player begins targeting an AOE spell or ability, a dashed
translucent shape draws on the ground at the cursor / target.

- Visible only to the casting player
- Faction-tinted color (your nation's hue)
- Dashed border (clearly "still preview")
- Soft inner glow at 30% opacity
- Animates: subtle pulse 1Hz so it reads as "selecting"

This lets the player see the radius and adjust their cursor / target
position before committing. Cancel mid-target = no other players see
anything.

### State 2: ACTIVE (everyone sees)

The instant the cast bar starts, the preview snaps to the active
telegraph state.

- Visible to ALL players in range (party, alliance, enemies if PvP)
- **Element / damage type colored** (see palette below)
- Solid border, brighter
- Inner fills smoothly from 0 → 100% over the cast duration as a
  visual countdown
- Lands at fill = 100%

Players who walk OUT of the active telegraph before fill=100% are
safe. Players still in at fill=100% take damage. Cast can be canceled
or interrupted; if so the telegraph fades over 0.3s with no fill.

---

## Element / damage type palette

Each element and damage type has a deliberate color so the
battlefield reads at a glance.

| Type        | Color                            | Hex     |
| ----------- | -------------------------------- | ------- |
| Fire        | warm orange                      | #ff6633 |
| Ice         | cyan                              | #66ccff |
| Lightning   | yellow-violet (alternating)       | #ffd633 / #cc66ff (animated stripe) |
| Earth       | umber                             | #996633 |
| Wind        | pale green                        | #99ff99 |
| Water       | deep blue                         | #3366cc |
| Light       | white-gold                        | #fff5cc |
| Dark        | desaturated purple                | #663366 |
| Physical    | pale red                          | #ff9999 |
| Healing     | soft green                        | #99ffcc |
| Buff zone   | pale gold                         | #ffe699 |
| Debuff zone | desaturated red                   | #cc6666 |

Friend / foe coloring is conveyed by **color saturation + border**:
- High saturation + thick border = enemy AOE (incoming hostile)
- Lower saturation + thin border = ally AOE (be aware, not panicked)

Players quickly learn to treat thick-bordered orange = enemy Firaga
incoming, thin-bordered green = ally Curaga, friendly.

---

## Shape vocabulary

Standard shapes cover ~95% of FFXI spells/abilities. Each is a single
Niagara decal pattern parameterized at runtime.

| Shape       | Use case                                           |
| ----------- | -------------------------------------------------- |
| circle      | classic AOE radius (Firaga, Cure, Banish)          |
| donut       | "stand close to boss" (rare boss mechanic)         |
| cone        | breath weapons, sword arc (variable angle 30-180°) |
| line        | spear thrust, magic line, dragon arc               |
| square      | floor tile-based abilities (rare)                  |
| chevron     | charge attacks (boss telegraphed dash path)        |
| irregular   | hand-authored polygon for unique boss attacks      |

Per-spell shape is data-driven. The LSB spell table grows a `shape`
column + parameters (`radius`, `angle_deg`, `length`, etc).

---

## Enemy AOE — how players read it without the telegraph

This is where Demoncore's skill ceiling lives. Players never see a
ground decal for enemy AOE. They read:

1. **The wind-up animation.** Each boss/mob has a unique animation
   per AOE type. Players learn the bestiary visually:
   - Quadav Roundshield raises shield + slams ground = circle radius
     ~6m around itself
   - Yagudo Acolyte fans wing = cone forward, ~10m, ~90°
   - Goblin Pickpocket pulls bomb from sack = circle ~3m at target
   - Aspidochelone (worm boss) lifts head = line forward, ~30m
   - Dragon NM tilts back + inhales = cone forward, ~20m, ~120°
2. **The cast bar (FFXI canonical).** A boss with a visible cast bar
   is casting *something*. Players learn from animation what that
   something is.
3. **Positional cues.** Boss faces a direction → cone hits in that
   direction. Boss centers on a player → circle on that player. Boss
   raises into the air → circle around itself.

The animation library is the codex. New players die to attacks they
haven't learned yet; experienced players never die to the same
animation twice.

This pairs beautifully with the visible health system. **A wounded
boss has fewer wind-up tells available** because his anims slow
down + truncate at low HP — the player needs *more* mastery to read
him at low HP, not less. Late-game dungeon bosses become readable
performances.

---

## The half-time rule

When an enemy starts an AOE cast, the player has roughly half the
cast time to position out of where they predict the AOE will be:

- 1.5s cast → ~0.75s reaction window
- 3.0s cast → ~1.5s reaction window

This is because the wind-up animation and the cast bar both start
at t=0. Players who recognize the animation immediately can act
within that window. Players who don't → they get hit, take damage,
re-watch their footage, learn the tell.

---

## Player AOE preview — UI behavior

```
on player begins targeting AOE spell/ability:
    spawn preview decal at cursor / target lock-on
    decal: dashed border, 30% inner alpha, faction color
    update decal position every frame as cursor moves
    only this player's client renders it

on player commits cast (cast bar appears):
    swap preview decal → active telegraph
    color = spell.element_color
    border thickness = high
    inner fill animates 0% → 100% across cast_time
    server replicates the active telegraph to all clients in range
    other players see it from this point onward

on cast cancel / interrupt:
    fade telegraph over 0.3s
    no damage applied

on cast complete (fill = 100%):
    apply damage / effect to entities in shape
    play impact VFX
    fade telegraph over 0.5s
```

---

## UE5 implementation outline

### `BPC_AoeTelegraph` (Blueprint Component on the casting actor)

```
SpellShape       enum  circle | donut | cone | line | square | chevron | irregular
RadiusOrLength   float meters
AngleDeg         float (cone only)
ElementColor     LinearColor
CastDuration     float (replicated from server)
PreviewDecal     UDecalComponent (only-self)
ActiveDecal      UDecalComponent (replicated)

OnTargetingStart()
OnTargetingMoved(new_target_world_loc)
OnCastCommit()
OnCastInterrupted()
OnCastComplete()
```

Decal materials live in `/Game/Demoncore/AoeTelegraph/Materials/`:
- `M_AOE_Preview` (dashed)
- `M_AOE_Active` (solid + fill animation parameter)

One material per shape × {preview, active} = 14 materials. Authored
once. Color is a parameter passed from the spell definition.

### Server replication

The active telegraph is server-authoritative. The server sends
`{caster_id, shape, params, element_color, cast_time, server_start_at}`
to all clients in range. Clients render the telegraph using their
own clock, sync-corrected to the server time.

This avoids client de-sync where a client thinks the AOE lands at
T but the server thinks T+0.05s.

### Tag-driven actor setup

Every spell's actor (the casting NPC, the boss, the player) gets
this component attached at runtime when they're cast-ready, removed
on cast complete. We don't pre-attach to every entity.

---

## Mood event hooks (orchestrator integration)

Adding to `event_deltas.py`:

```
("aoe_telegraph_visible_to_self", "*civilian*")  -> ("fearful", +0.4)
("aoe_telegraph_visible_to_self", "*soldier*")   -> ("alert",   +0.3)
("aoe_telegraph_visible_to_self", "*hero*")      -> ("alert",   +0.4)
("dodged_aoe", "*hero*")                          -> ("content", +0.2)
("hit_by_aoe", "*hero*")                          -> ("furious", +0.3)
```

So when an AOE telegraph appears under an NPC, their mood reacts.
A civilian-mobbed Bastok during a Quadav siege has visibly panicked
NPCs running outward from telegraph centers. The world reacts to
the threat physically.

---

## Edge cases

### Stacked telegraphs
Multiple active telegraphs can overlap. Each renders independently,
sorted by sphere depth. The player has to track multiple shapes
when several casters target the same area. Healers especially.

### Performance ceiling
A 6-person party + 6 mobs all casting simultaneously = 12 telegraphs
on screen at once. Niagara handles this; we cap at ~30 visible
telegraphs per frame and gracefully drop the lowest-priority ones.

### Custom boss telegraph types (rare)
Some boss attacks deserve unique telegraphs that aren't in the
standard shape set. We support custom polygonal decals via the
`irregular` shape. Authored per-boss.

### Mood-on-boss-AOE-incoming
**Bosses don't telegraph to players** (intentional). However, NPCs
in the area DO get the `aoe_telegraph_visible_to_self` mood event
because they "see the swing coming" via animation cue. So a city
under siege has bystander NPCs reacting to incoming AOE while
players have to read the cues themselves.

---

## Status

- [x] Design doc (this file)
- [ ] Material library: M_AOE_Preview + M_AOE_Active per shape
      (14 materials authored once)
- [ ] Niagara templates for spell impact VFX (per element)
- [ ] BPC_AoeTelegraph component
- [ ] LSB spell table: add `shape`, `radius`, `angle_deg`, `length`
      columns
- [ ] First-pass spell sweep: tag every existing FFXI spell with
      its shape (~150 spells, ~1 hour of data entry)
- [ ] Server replication of active telegraph
- [ ] Mood event hooks in event_deltas.py
- [ ] Cross-reference COMBAT_TEMPO.md and VISUAL_HEALTH_SYSTEM.md
- [ ] First playtest pass: WAR vs Quadav with full visual stack
