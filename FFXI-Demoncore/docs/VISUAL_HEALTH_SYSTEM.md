# VISUAL_HEALTH_SYSTEM.md

In Demoncore, **HP and MP bars are not visible by default**. Not on
mobs. Not on NMs. Not on bosses. Not on other players. Not on you.

You read damage the way a soldier reads a battlefield: posture, blood,
limp, cough, the way a sword starts trembling in tired hands. You read
status ailments the way you'd read someone with the flu — pale skin,
slow movement, glazed eyes.

This is the highest skill-ceiling lift in Demoncore. Once a player
adapts, they see things FFXI players have never seen. They feel a
boss's wing droop two seconds before phase change. They notice the
back-row WHM is poisoned because she's coughing every cast. They hear
a Quadav's breathing get ragged and call the kill-shot timing.

---

## Why no bars (the design rationale)

The original FFXI was already an information-rich combat game — but
because every entity had a floating health bar, players watched the
bars instead of the world. The bars became the primary source of
truth, and the actual character animations became cosmetic.

Removing the bars inverts this. Animations and visual state become
the canonical truth, and combat becomes about perception: what does
this enemy LOOK like right now? What does my tank LOOK like? Did
that cough mean what I think it meant?

Three concrete benefits:
1. **Skill ceiling rises sharply.** Veterans who learn the visual
   language read encounters with sub-second precision. New players
   die more often, but their improvement curve is steeper because
   the world is *teaching them* every fight.
2. **Cinematic combat.** No HUD overlays cluttering the camera. The
   game looks like a film during a boss fight.
3. **Real party communication.** "WHM is at half" stops being
   instant glance, becomes spoken voice chat. Parties get *closer*.

The intended difficulty curve isn't punishment — it's revelation.
A late-game player isn't memorizing HP percentages, they're reading
faces.

---

## What you DO see (your own UI)

The player's own HUD shows:
- **Their own** HP/MP (numerical + bar) — you always know your own
  body
- **Active status icons** on themselves
- **Aggro indicators** (FFXI-canonical: who's targeting whom)
- **Skillchain / Magic Burst windows** — the timing UI, never the
  damage numbers
- **Floating damage numbers** are **OPT-IN** in settings (default off
  for hard-mode)

The player does NOT see:
- HP bars on other players, NPCs, mobs, NMs, bosses
- MP bars on anyone
- Status ailment icons on other entities
- Numerical damage dealt by anyone unless opted in

---

## How you read enemy HP visually

Each entity has 7 visible damage stages mapped to HP bands. The HP
itself is server-side; the client renders the appropriate stage.

| HP band | Stage label | Humanoid cues                                          | Mob/beast cues                       |
| ------- | ----------- | ------------------------------------------------------ | ------------------------------------ |
| 100-90% | pristine    | clean armor, full posture, normal breathing            | full color saturation, alert posture |
| 90-70%  | scuffed     | minor scratches, dust on armor, occasional wince       | one fur patch matted; ear flick      |
| 70-50%  | bloodied    | visible blood on armor, slight limp on damaged side    | favors one leg, lower head           |
| 50-30%  | wounded     | heavy blood, slower attacks, audible labored breathing | wing/tail droops, slower charges     |
| 30-10%  | grievous    | gash visible on body, severe limp, occasional stagger  | half-collapsed posture, weak roars   |
| 10-1%   | broken      | stumbling, swaying, weapon held loosely, near-fall     | crawling, drag-walk, shrill cries    |
| 0%      | dead        | death animation                                        | death animation                      |

Cues are additive — at `wounded` (50-30%) the entity has all of:
"clean armor scuffed", "minor scratches", "visible blood on armor",
"limp", "heavy blood", "slower attacks", "labored breathing".

Per-race overrides for humanoids:
- **Galka**: blood is harder to see on dark hide; instead they
  visibly tense / clench more, and breathing becomes a low growl
- **Tarutaru**: blood is more visible (smaller body, larger relative
  wounds); voice gets higher and faster at low HP
- **Mithra**: ears flatten progressively; tail gets twitchy at <30%
- **Elvaan**: posture is the tell — proud-stance erodes into hunched
  shoulders by `wounded`
- **Hume**: standard reference

Per-mob-class overrides — examples:
- **Dragon NMs**: at `wounded` the wing droops on the damaged side;
  at `broken` the wing tip drags the ground; at the same time the
  fire-breath windup is visibly slower
- **Slime/jelly mobs**: lose translucency progressively; at `broken`
  they're fully opaque and trail goo
- **Goblin mobs**: limp + drop sack of stolen junk by `grievous`
- **Quadav warriors**: shield drops by `wounded`; helmet falls off
  at `broken`
- **Yagudo**: feathers fall progressively across stages
- **Worms**: segments visibly split apart from `wounded` onward

KawaiiPhysics is the secret sauce. Capes/cloth/hair drag harder when
the entity stumbles. A galka warrior's tail goes from a confident
upward curl to a low slow droop as he loses HP. The damage isn't
just textures — it's animation + physics.

---

## Status ailments — visible on bodies

Each ailment has a per-stage cue. Players learn to read them like a
medical chart.

| Ailment   | Visible cue                                                    |
| --------- | -------------------------------------------------------------- |
| poison    | green particle sweat; occasional cough; skin tone tints green  |
| sleep     | eyes closed; Z-particle drifts up; slumped posture; can't move |
| paralyze  | jerky animation; staggers mid-action; weapon swings wobble     |
| silence   | hand-to-throat reflex; cast animation plays but NO audio       |
| bind      | feet rooted to ground (visibly snared); body can twist         |
| stun      | stars/dazed particles around head; posture lurches             |
| curse     | dark wisps trail off the body; eyes occasionally darken        |
| disease   | pale skin; lethargic movement; coughs; can't eat food (UI gating) |
| plague    | pustule decals on skin; faster MP drain (visible MP-aspir hint) |
| confuse   | walks in random directions; head swivels; mis-targets          |
| charm     | pink-tinged gaze locked on charmer; follows obediently         |
| petrify   | stone slowly creeps up from feet; full statue at end           |
| doom      | dark countdown aura visible ONLY to the afflicted; clock ticks |
| weakness  | post-death — translucent body for the duration                 |
| amnesia   | no special abilities used; small "?" particle when attempted   |
| terror    | full-body shaking; can't act; eyes wide                        |
| en-aura   | weapon glows the element's color (player-applied buff visible) |

These are NOT iconified above the head. They are integrated into
the character's visible body. A player with three ailments looks
genuinely sick — green tinge, pustules, jerky walk all at once.

For the player's own status: same visible cues PLUS the icon row in
their own HUD. (Self-knowledge is full; reading-others requires
attention.)

---

## Reveal skills (canonical FFXI mechanics)

The user requested we use existing FFXI skills, not invent new ones.
Here's the mapping. All numbers are starting points; balanced in
playtest.

### /check (every player, free, on cooldown)
The vanilla FFXI con-check. Returns a vague descriptor only — no
numbers. Now reads:
- "Easy Prey" / "Decent Challenge" / "Tough" / "Incredibly Tough" /
  "Impossible to Gauge"
- Plus a **mood read**: "(seems content)" / "(seems agitated)" /
  "(looks furious)" — links into MOOD_SYSTEM.md
- Plus a **damage read**: "(unharmed)" / "(slightly hurt)" /
  "(badly wounded)" — same buckets as the visible damage stages

Cooldown: 5 seconds per target.

### Scan (BLU lvl 60, SCH lvl 40 — already canonical FFXI)
Reveals **exact HP and MP** for 5 seconds. Single target. The
caster's UI shows the bars; the rest of the party doesn't.

Cost: ~25 MP. Cooldown: 30 seconds.

### Drain (BLM/RDM/DRK)
While casting and for 2 seconds after the spell lands, the caster
sees the **target's HP** as a number. Magic-school synergy: BLM/DRK
who lead with Drain get free HP intel for the opening burst.

### Aspir (BLM/RDM/SCH)
Same mechanic but for **target's MP**. Lets healers spot when an
enemy mage is dry.

### THF Mug (lvl 25)
Successful Mug has a **30% chance** to reveal target HP for 3
seconds. Stacks Sneak Attack chance: SA-Mug guarantees the reveal.
This makes THF the recon job.

### Bard "Glee Tango" (custom new song that fits the canon)
A short song. While active, the bard sees ALL party members'
exact HP/MP. ~3 minutes duration. ~30 MP cost. Doesn't reveal
enemies.

This song is the answer to "but how does my healer know I need a
cure?" — bring a bard. (Healers can also see party HP via WHM
Cure-cast targeting — see below.)

### WHM Cure / Cura (and other healing magic)
While casting Cure on a party member, the caster sees that target's
**HP for the duration of the cast + 2 seconds**. This means
healers learn to "tap" Cure to peek at HP. There's no penalty to
spamming low-tier Cure as a sight tool other than MP cost.

Cura (AOE) reveals all party member HP for the duration of the
cast.

### Magic Burst (any caster)
Successfully magic-bursting (>100 burst damage) reveals the target's
HP for **2 seconds** to the entire party. This makes
chain-reading a real party-coordination tool.

### Geomancer Indicolure (added later in FFXI canon)
Indicolure: Aspir or Indicolure: Drain — places a passive HP/MP read
on a target for the geomancer's view. Long cooldown.

### Stoneskin (defensive — visible to caster only)
While Stoneskin is active, you can faintly read the surface stage
of attackers (one stage less precise). Not a primary recon tool but
a defensive perk.

### /pol command (extended for Demoncore)
A free, vague summary of the party: how many people are at each
stage. "Party: 3 pristine, 1 wounded, 1 broken." No names, no
numbers. Useful in chaotic raids.

---

## Player skill curve (what the game teaches)

**Day 1**: player loses early because they can't tell when to
flee. They die a few times.

**Day 3**: they notice mobs slow down at the bloodied stage. They
start chaining kills with confidence on green-mob trash.

**Week 1**: party play. Healers learn to "tap Cure" for HP peeks.
Mages start running Drain even when they don't need MP. THFs start
opening every fight with Sneak Attack + Mug for the reveal.

**Week 4**: they start reading enemy *posture* before damage even
manifests. They can call "boss is about to phase" two seconds
before the wing droops.

**Month 3**: high-end raid groups recruit specifically for the
"bard with Glee Tango" or "scholar with Scan" because the visual
reveal is the difference between a clean kill and a wipe.

**Month 6**: the player no longer thinks about HP at all. They
read the world.

---

## UE5 implementation outline

### `BPC_VisibleHealthState` (Blueprint Component)
Each character (skeletal mesh actor) has this component:

```
- bind to OnDamageApplied event
- read current HP / max HP
- compute current_stage = pristine | scuffed | bloodied | wounded | grievous | broken
- on stage change:
    - swap material decal layer (blood/grime per stage per race)
    - blend in stage-appropriate idle anim (limping, posture)
    - spawn / despawn Niagara FX (sweat-poison, dust on armor)
    - adjust KawaiiPhysics damping (drooping cloth)
    - adjust attack speed multiplier (server-authoritative)
```

Material decals are pre-authored once per (race × damage_stage).
~6 stages × 5 races + ~10 mob_classes × 6 stages = ~80 decal sets
authored, reused across thousands of agents. Same idea as the mood
idle anims — author once, reuse everywhere.

### `BPC_VisibleAilmentState` (Blueprint Component)
Each character also has this. Listens to status-ailment events from
LSB. Per ailment, drives:
- particle emitter (sweat, sleep-Z, plague pustule decals)
- material parameter (skin tone tint for poison, opacity for charm)
- anim layer override (bind = root motion off feet)
- audio override (silence = mute spell-cast SFX)

### `WBP_RevealOverlay` (Widget Blueprint)
The transient HP/MP bar that appears when a reveal skill activates.
Driven by a server-authoritative `RevealHandle` data type with
`{target_id, expires_at, source_skill}`. Multiple reveals can be
active simultaneously per player. The widget pools and reuses a
small fixed number of bars (no per-target allocation).

The reveal duration is **client-authoritative for display only** —
the server's reveal expires at the canonical timestamp; the client
just renders the remaining time.

---

## LSB integration

Server-side changes:
1. New endpoint `lsb_admin_api/reveal/{caster_id}/{target_id}` —
   returns `{hp, mp, max_hp, max_mp, expires_at}` if the caster has
   an active reveal handle on the target. Otherwise 403.
2. Existing damage broker emits `damage_stage_changed` events when
   any entity crosses a stage boundary. Clients in the zone receive
   these and update their visible_health_state component.
3. New SQL column `entities.damage_stage` (replicated, denormalized
   from HP for fast client lookup).

---

## What this enables for the rest of the design

- **Mood + visible damage compose.** Zaldon at `bloodied` stage
  with `gruff` mood looks visibly hurt and angry. The orchestrator's
  apply_event(`damage_taken`) triggers both a stage transition AND a
  mood event delta — the world reads coherently.
- **Healing structures use the same grammar.** Damage-stage labels
  on structures (pristine→cracked→battered→ruined) match the
  damage-stage labels on entities. Players read both with the same
  visual language. Wounded city = wounded soldier.
- **Cutscenes look like cinema.** Removing the HUD overlays means
  the camera framing is uncluttered. Boss fights record like
  documentary footage.

---

## Status

- [x] Design doc (this file)
- [ ] BPC_VisibleHealthState component (UE5)
- [ ] BPC_VisibleAilmentState component (UE5)
- [ ] Material decal sets per (race × stage) — 30 decal sets
- [ ] Mob_class decal sets — first 10 mob classes
- [ ] Niagara templates per ailment — 16 ailments
- [ ] WBP_RevealOverlay widget
- [ ] Reveal endpoint in lsb_admin_api
- [ ] /check / Scan / Drain / Aspir / Mug / Cure / MB hooks in LSB
- [ ] Glee Tango BRD song authored
- [ ] Indicolure: Aspir / Drain GEO entries
- [ ] First playtest pass on a single zone (Bastok)
