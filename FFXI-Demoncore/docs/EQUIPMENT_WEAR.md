# EQUIPMENT_WEAR.md

Every piece of equipment in Demoncore has **durability**. Use
degrades it. Death penalizes it. Visual condition reads on the
character's body. NPCs charge gil to repair it; player crafters
can repair it themselves once they level the craft. Master-tier
gear (Mythic, Relic, Empyrean) can only be repaired by master
NPCs or master-craft players.

Wear is the missing economic layer. Without it, gil has nowhere
to go after the first month and crafters have no real role.
With it, gil flows continuously between players + NPCs,
crafters become apex roles, and gear visibly tells its own
combat history.

Composes with:
- `VISUAL_HEALTH_SYSTEM.md` — equipment wear uses the same
  visual grammar (decals, scratches, broken pieces) so the
  world reads coherently
- `WEIGHT_PHYSICS.md` — broken gear loses its weight bonus
- `DAMAGE_PHYSICS_HEALING.md` — Pellah's repair_capabilities
  now extend to equipment as well as structures
- `NPC_PROGRESSION.md` — repair NPCs level up with use; high-
  level Pellah repairs better than low-level Pellah
- `HARDCORE_DEATH.md` — death takes a 25% durability penalty
  on all equipped gear (extra kicker on top of the level loss)

---

## The durability number

Each piece of equipment has:
- **durability_max**: 100 for common gear, up to 5000 for mythic
- **durability_current**: the live state, 0-durability_max
- **wear_rate**: how fast it degrades per use action

A new Bronze Sword starts at durability_current = 100 = full.
After 200 swings against mobs, durability_current ~ 50% — the
sword starts showing visible nicks. At 25%, the sword is
"broken" — half the swings whiff (the blade catches on the
hilt) and the player loses the weapon's accuracy bonus from
WEIGHT_PHYSICS.md.

At 0%, the sword unequips itself. The player still carries it,
but it's now functionally a club until repaired.

---

## Wear rates per equipment + use action

**Target**: a player can XP-farm for ~8 hours of continuous play
before any piece needs a repair-NPC visit. Wear is the
*economic rhythm* of the game, not a constant tax. The numbers
below are calibrated against an estimated 6,000 active swings
in an 8-hour farm session.

```
Weapons
  per swing landed:       -0.010% durability
  per crit landed:        -0.020% (extra stress on a clean hit)
  per WS use:             -0.050% (concentrated stress)

Armor (per damage taken)
  light armor:           -0.005% per 100 damage absorbed
  medium armor:          -0.003% per 100 damage absorbed
  heavy armor:           -0.002% per 100 damage absorbed (heavy
                                                          lasts longer)

Magic foci (staves, grimoires)
  per cast:                -0.008% per cast
  per spell weight point:  -0.0005% per cast (heavier spells = more wear)

Jewelry (rings, earrings, etc)
  passive:                 -0.0001% per minute equipped
  procced:                 -0.10% on each proc trigger

Death penalty (hardcore)
  level 1-89:             -25% durability on all equipped pieces
  level 90-98:            -40% durability + 2-day Reraise lockout
  level 99:               100% durability LOSS (all gear unusable;
                                                permadeath fomor wears
                                                the broken gear visibly)
```

### Why these numbers (the playtime math)

A typical XP-farm session:
- ~30 swings/min during active combat
- ~40% of session time is active combat (rest is travel + buffs +
  downtime)
- 8 hours = ~5,760 active swings

At -0.010% per swing: 5,760 swings = 57.6% durability used.
The piece is at ~42% durability after 8 hours — `damaged` stage
just barely avoided. Time for a repair stop.

Combat-heavy events (BCNM, raids, sieges) burn faster because
of WS density and crits — those sessions might cost 70-80%
durability over 4-5 hours, which is the desired economic
intensity for endgame play.

Death stays punchy. The -25% on every death is a real loss but
a small repair charge fixes it; the lvl-99 100% loss is the
hardcore-tier penalty that makes apex play meaningful.

The principle: gear lasts a workday. Repair is a deliberate
visit, not a constant interruption. Players engaging the
economy (crafting, buying, repairing) is the natural rhythm of
play, not a grind tax.

---

## Visible-condition stages (composes with VISUAL_HEALTH)

Per `VISUAL_HEALTH_SYSTEM.md`, equipment renders 5 stages on
top of the base mesh. Players see condition as part of the
character's silhouette:

| Durability % | Stage         | Visible cues (humanoid)                 |
| ------------ | ------------- | ---------------------------------------- |
| 90-100       | pristine      | clean armor, fresh edges                 |
| 70-90        | scuffed       | minor scratches, edge nicks visible       |
| 50-70        | worn          | dirt grime; clear tool marks; faded paint |
| 25-50        | damaged       | visible cracks, missing rivets, frayed cloth |
| 1-25         | broken        | half the piece visibly broken; severely degraded |
| 0           | unusable     | item visibly snapped/falling apart       |

**Per-archetype overrides**:
- Galkan armor stays clean longer (higher durability_max baseline)
- Tarutaru cloth tears earlier visually but functional cost is the same
- Mythic gear has its own decay aesthetic (Excalibur develops
  battle-runes that glow more dimly as durability drops)
- Magic foci wear shows as ink fading on grimoires, dust on staves

The visual stage is RUNTIME-COMPUTED from durability_current,
not a separate per-stage texture. We use one wear-decal layer +
material parameters that fade nicks/dirt in as durability drops.
Authoring overhead: ~6 wear textures per archetype. ~30 textures
total for the base game.

---

## Combat impact

Wear has REAL combat consequences (it's not just cosmetic):

| Stage      | Combat effect                                              |
| ---------- | ---------------------------------------------------------- |
| pristine   | full stats, full WEIGHT_PHYSICS bonuses                    |
| scuffed    | -1% to weapon damage / armor defense                       |
| worn       | -3% to stats; some procs unreliable                        |
| damaged    | -8% to stats; weapon weight bonus halved; Fast Cast halved |
| broken     | -25% to stats; weapon misses 30%; armor only 50% absorbing |
| unusable   | unequipped automatically at end of next swing/cast         |

A WAR fighting in broken Plate Mail is functionally a WAR in
medium armor — but he visibly LOOKS like he's coming apart.
Players can tell at a glance that someone's gear is failing.

Bosses also have wear consequences. Maat dropping his wrist
guard at bloodied stage (per `agents/hero_maat.yaml`) is a
**real durability event** — that piece's durability hit 0 from
combat damage taken.

---

## Repair pathways

There are four ways to repair gear, ordered by accessibility.

### 1. Repair Kit (consumable)
Single-use item. Restores +25% durability to one piece. Sold
by general-goods vendors for 100 gil. Limited; doesn't restore
mythic gear. Universal first-aid for new players.

Wear rate of consumables: 1 use, gone.

### 2. NPC repair (gil sink)
Each nation has 2-4 repair NPCs (Voinaut in Bastok, Pellah in
Bastok Markets, Pelinaut in Sandy, Mihli in Windy). They:
- Restore equipment to 100% durability for a gil cost
- Cost = `(durability_missing / durability_max) * gil_per_max`
- gil_per_max varies by gear tier (50 for bronze, 5000 for
  endgame, 50000 for mythic)
- Master NPCs can repair what apprentice NPCs can't
- Repair NPCs LEVEL UP per `NPC_PROGRESSION.md` — Pellah at lvl
  60 can repair stone_brick + wood + cloth; at lvl 70 unlocks
  Metalworks elevator + relic gear

Repair takes time. While working, the NPC is `busy`. Mood-aware
repair speed: a `mischievous` Pellah works 1.10x speed and
charges 10% less; a `weary` Pellah works 0.70x speed.

### 3. Player crafting
Players who level the appropriate craft can repair their own
gear (and others' gear, for tip):
- Smithing (Bastok signature): repairs metal weapons + plate armor
- Leatherworking (Sandy signature): repairs leather + cloak
- Woodworking (Windy signature): repairs staves + bows + wooden shields
- Goldsmithing (universal): repairs jewelry
- Alchemy (universal): repairs magical foci + crystals
- Bonecraft (specialty): repairs bone equipment
- Cloth (universal): repairs robes + outfits

To repair a piece: Craft skill required = piece's tier-level + 5.
A lvl 60 smithing player can repair lvl 55 Mythril gear. A lvl 99
master smith can repair endgame mythic.

Mastery (per `PLAYER_PROGRESSION.md`) extends this:
- Mastery 0 in the craft = repair to 80% of original
- Mastery 3 = repair to 95% of original
- Mastery 5 = repair to 100%, with an occasional CRIT-REPAIR
  that adds +5% to durability_max

This makes master crafters apex content. A WAR who's also a
mastery-5 smith never has to pay for repairs and can sell
Excalibur repair services for ~10000 gil per use.

### 4. Master NPC repair (relic / mythic / empyrean)
Some gear can ONLY be repaired by named master NPCs:
- **Cid** (Bastok) — repairs Galka-3 airship-grade weapons +
  relic-tier weapons (Excalibur, Curtana). Charges 50000+ gil.
- **Volker** — repairs musketeer-grade weapons.
- **Maat** — refuses payment but repairs *only* if the player
  has earned his respect (Genkai 5 cleared).
- **Yoran-Oran** (Windy Star Sibyl candidate) — repairs Star
  Sibyl-grade jewelry.
- **Yorisha** (Norg) — repairs corsair-grade weapons. Will
  also repair anything if the player has Norg outlaw status
  (the loophole).

Master-NPC repair is the rare end-of-the-world economic event.
Players coordinate with the rest of their guild to plan
repair-runs.

---

## Repair flow (worked example)

A player's Joyeuse (durability 35%, broken stage) needs repair.

```
Path A — Repair Kit:
  1. Player buys Repair Kit (100 gil)
  2. Uses Repair Kit on Joyeuse → +25% durability → 60%
     (still worn, not pristine)
  3. Player still needs gil-sink path for full repair

Path B — Repair NPC (Pellah at lvl 60):
  1. Pellah refuses; Joyeuse is relic-tier (above lvl 65)
  2. Player travels to Cid in Metalworks
  3. Cid charges (durability_missing / 100) * 80000 = 0.65 * 80000 =
     52000 gil for full repair
  4. Cid takes 5 game-minutes (1 wall-minute) to do the work
  5. Cid's mood was content; mood-aware speed bonus 1.0x
  6. Joyeuse restored to 100% durability

Path C — Player Crafter (the player herself, lvl 75 smith mastery 4):
  1. Player has 75 smithing; can repair gear up to lvl 70
     (lvl 75 - 5 = 70)
  2. Joyeuse is lvl 75; AT the cap; repair possible
  3. Player crafts a Repair Hammer (Bronze, Crystal of Light) at
     a Bastok crafting station
  4. Uses Repair Hammer on Joyeuse → durability restored to 95%
     (mastery 4 limit)
  5. Player needs to keep their own smithing leveled to maintain
     this self-sufficiency

Path D — Master Crafter (offers repair to others):
  1. Player Alice is a mastery-5 smith
  2. Bob asks Alice to repair his Joyeuse, offers 30000 gil
  3. Alice agrees. Crafts a Repair Hammer + uses it on Bob's Joyeuse
  4. Roll for crit-repair: 10% chance to add +5% to durability_max
  5. Joyeuse restored to 100% (Alice's mastery 5) — 10% chance,
     Alice rolls a crit, max durability becomes 110/100.
  6. Bob's gear is now slightly above-average. Word spreads.
  7. Alice's repair-services-rendered count goes up. Reputation +.
```

---

## Death penalty (hardcore integration)

Per `HARDCORE_DEATH.md`, when a player dies:

```
Levels 1-89:
  - Equipment: -25% durability instantly
  - Player respawns; gear is now 25% closer to broken
  - Repair runs become a regular part of play

Levels 90-98:
  - Equipment: -40% durability instantly
  - Plus 2-day Reraise lockout

Level 99:
  - Equipment: 100% durability LOSS (all gear unusable)
  - Permadeath timer starts; player becomes Fomor in 1 hour
  - The fomor wears the broken gear visibly — other players who
    encounter the fomor can see "this used to be a player who died
    here" as part of the world's lore
```

This makes the durability hit at lvl 90+ EXTREMELY costly —
gearing back up takes hours of repair-cycle play. It's
intentionally gnarly.

---

## Mood event hooks (additions to event_deltas.py)

```
("equipment_broke",        "*hero*")     -> ("furious",  +0.30)
("equipment_broke",        "*soldier*")  -> ("alert",    +0.30)
("equipment_broke",        "*civilian*") -> ("fearful",  +0.30)
("equipment_repaired",     "*")          -> ("content",  +0.20)
("repair_npc_busy",        "*pellah*")   -> ("content",  +0.10)
("master_repair_completed","*hero*")     -> ("content",  +0.40)
("crit_repair_proc",       "*hero*")     -> ("content",  +0.50)
("died_with_full_durability_loss", "*")  -> ("furious",  +0.50)  # lvl 99 death
```

When a hero NPC's gear breaks (e.g. Maat's wrist guard at
bloodied), the mood shifts to furious — visibly compounding the
phase-transition mood shift that's already authored.

---

## Pellah's repair_capabilities (extended)

Update Pellah's existing `agents/pellah.yaml`:

```yaml
repair_capabilities:
  speed_multiplier: 5.0          # already authored
  cost_per_hp_max: 2              # already authored — now also per
                                   # durability_missing/durability_max
  level: 60
  repair_animation: "slow_chant_with_carving_motions"

  # NEW: equipment repair extension
  repairs_structures: true        # already implicit
  repairs_equipment_tiers:
    - bronze        # always
    - mythril       # at lvl 60+
    - leather       # always
    - cotton        # always
    - cloth         # always
    - wooden        # always
    - banded_mail   # at lvl 65+
    - scale_armor   # at lvl 65+
    # NOT: relic, mythic, empyrean (need master NPCs)
  master_unlocks_at_level: 75    # at lvl 75 Pellah unlocks one
                                  # mythic-tier repair recipe
  current_master_recipe: null     # designer-flagged when story unlocks it
```

So a player who brings a Mythril Sword to Pellah at lvl 60 can
get it repaired. A player who brings Excalibur cannot — needs Cid.

---

## What this enables

1. **Continuous economy.** Gil flows daily from players to repair
   NPCs and master crafters. The market doesn't stagnate after
   Month 1.
2. **Crafter players are apex content.** A mastery-5 smith is more
   valuable to an endgame raid than another DD — they keep the
   raid's gear running.
3. **Visible character history.** A player walking through Bastok
   in dented Mythril looks like they've been *adventuring*. New
   players in pristine Bronze look new.
4. **Death has stakes beyond xp.** The 25% durability hit on every
   death means repair-cycle is part of the natural rhythm of play.
5. **Boss gear drops have personality.** Maat's wrist guard hits
   ground with low durability already — the player sees a
   battle-marked piece, not a museum piece.
6. **Master NPC repair runs are events.** Coordinating a guild
   trip to Cid for endgame repair becomes a content moment, not
   a chore.

---

## Status

- [x] Design doc (this file)
- [ ] LSB items.sql: add `durability_max`, `durability_current`,
      `wear_rate` columns to every gear entry
- [ ] LSB combat formula: per-swing + per-cast wear deduction
- [ ] LSB damage formula: armor wear per damage taken
- [ ] UE5 character ABP: per-stage equipment material parameter
- [ ] 6 wear-decal textures per archetype (~30 total textures)
- [ ] Repair Kit consumable item + Bastok general-goods vendor entry
- [ ] Repair NPC dialogue: Voinaut, Pellah, Pelinaut, Mihli updates
- [ ] Master-NPC repair entries: Cid, Volker, Maat, Yoran-Oran, Yorisha
- [ ] Player crafting: extend smithing/leatherworking/etc with repair recipes
- [ ] Mastery-5 crit-repair proc table
- [ ] Hardcore death durability penalty integration
- [ ] Mood event hooks in event_deltas.py
- [ ] First playtest: 100 swings of a Bronze Sword → wear visible
