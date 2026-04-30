# CRAFTING_SYSTEM.md

How players become craftsmen — and how master crafters become
**apex social content** in Demoncore. Repair NPCs are the gil
sink that makes player crafters a real economic class. Master
crafters earn by keeping the world's gear running.

This is the design contract for the seven crafts, the level
curve, the synthesis ritual, the mood-aware crafting hooks, and
the master-tier Limit Break that elevates a few crafters into
named legends.

Composes with:
- `EQUIPMENT_WEAR.md` — repair is one of two ways crafts make money
- `PLAYER_PROGRESSION.md` — crafting is its own mastery axis 0-99
- `NPC_PROGRESSION.md` — crafter NPCs (Pellah, Cid, Yoran-Oran)
  level alongside players
- `MOOD_SYSTEM.md` — a mischievous-mood crafter has different
  proc tables than a content-mood crafter
- `AUDIBLE_CALLOUTS.md` — crafting has its own voice library
  (proc cries, master-crit shouts, breakage sighs)

---

## The seven crafts

| Craft           | Tools            | Repairs                                    | Crafts                                       |
| --------------- | ---------------- | ------------------------------------------ | --------------------------------------------- |
| Smithing        | hammer + anvil   | metal weapons + plate armor + shields      | weapons, plate armor, helmets                 |
| Goldsmithing    | jeweler's bench  | jewelry + foci                             | rings, earrings, amulets, gems                |
| Leatherworking  | tanning stand    | leather armor + bow strings                | leather sets, holsters, belts                 |
| Woodworking     | carpenter's bench | staves + bows + wooden shields            | staves, bows, polearms, magical foci          |
| Cloth           | loom             | robes + cloaks + hats                       | robe sets, banners, sashes                    |
| Alchemy         | alembic          | crystals + foci enchantments               | potions, ethers, status remedies, food         |
| Bonecraft       | bone shop        | bone equipment                              | bone jewelry, scrimshaw weapons, fish bait    |

Plus two universal tools:

| Tool                    | Use                                                |
| ----------------------- | -------------------------------------------------- |
| Cooking (universal)     | crafted food buffs (HP/MP/job-stat regen)         |
| Fishing (universal)     | gathered raw materials for Cooking + Alchemy       |

Each craft scales 0-99. **A character can pursue all 7** but
realistically reaches mastery in 2-3 over a Demoncore lifetime —
the time investment is real.

---

## Craft level (0-99)

```
0-15  : apprentice
16-40 : journeyman
41-65 : artisan
66-89 : master
90-99 : grandmaster
```

Each tier unlocks new recipes + opens new repair tier tags
(per `EQUIPMENT_WEAR.md`):

```
apprentice (0-15):  bronze + cotton + simple wood
journeyman (16-40): mythril + leather + standard wood/cloth
artisan (41-65):    scorpion + shadow + scholar gear
master (66-89):     adaman + kirin + endgame relic-imitation
grandmaster (90-99): mythic-tier + relic-tier (some recipes)
```

Levels are gained per successful synthesis or repair. 1 exp
per same-level synth. 0.5 per below-level. 2 per above-level
(harder = bigger reward).

---

## Synthesis ritual

A craft action is a **mini-game-with-physics** rather than a
button press. The player:

1. **Sets the recipe** at a craft station. The orchestrator
   notes their current mood (per `MOOD_SYSTEM.md`).
2. **Watches a 3-5 second timed sequence** with visible
   progress + audible cues:
   - Smithing: hammer-on-anvil rhythm; player presses to-the-beat
   - Alchemy: crystal-color shifts; player reacts to color cue
   - Cloth: thread-tension meter; player keeps it in green
3. **Mood determines proc table**:
   - `content` mood: standard proc rates
   - `mischievous` mood: +10% to creative procs (alternate output)
   - `weary` mood: -20% craft success, but +30% to mundane procs
     (extra material output)
   - `furious` mood: cannot craft (refuse to focus)
   - `contemplative` mood: +15% to higher-tier procs (rare quality)

Successful synthesis yields:
- **Standard outcome** — the recipe's base item
- **HQ tier 1 (15% chance)** — improved stats, "+1" suffix
- **HQ tier 2 (3% chance)** — much improved, "+2"
- **HQ tier 3 (0.3% chance)** — apex, "+3", trade-bound

A synthesis can FAIL, in which case:
- All materials are consumed
- Crafter loses 10% of one tool's durability
- Brief mood shift (`weary` += 0.10)
- An audible disappointed grunt

The mini-game rewards skill, not RNG-only. A skilled player
on a content mood can land HQs reliably; a tired player will
still fail occasionally. **Mastery 5 grants a "stable hands"
passive** that makes the mini-game timing more forgiving.

---

## The Master Synthesis Limit Break (apex play)

At grandmaster (90-99) per craft, a player unlocks **Master
Synthesis** — a once-per-day limit break that:

- Guarantees an HQ tier 2+ on the next synth
- Has a 5% chance to yield an **HQ tier 4** (signed item):
  the crafter's name is engraved into the gear's lore. Other
  players who buy or repair the item see "Crafted by [Name]"
  in its description.
- Audibly: the crafter shouts "Master Synthesis!" and visible
  golden particles wreath the item

Signed items become legendary across the server. A "Excalibur
forged by Cid" auctions for 10x base value. Players hunt for
specific crafters' work as collectible content. **The
high-skill crafter is THE celebrity of Demoncore's social
layer.**

Per game-day per craft, the limit break can fire once. A
master can effectively make ~7 signed items per real-week if
they invest the time.

---

## Master Crafter player identity

A player who hits grandmaster in multiple crafts is a real
celebrity. They get:

- **Title**: "Bastok Master Smith" / "Windy Master Loomweaver"
  / etc — visible above their character name
- **Reputation cap raise**: +1000 nation reputation cap per
  grandmaster craft
- **NPC respect**: city NPCs greet them by craft title
  ("Master Alice. The blade you forged for my brother
  saved his life.") — the orchestrator's tier-2/3 agents
  recognize them per their relationship graph
- **Repair-service network**: other players hire them for
  repair work; the orchestrator tracks reputation per crafter
- **Master Synthesis** limit break (above)

Players who pursue solo crafting paths AND combat play are
the apex social class. The grandmaster smith who soloed Maat
at lvl 75 is the rarest archetype in the server.

---

## NPC crafters and their level

Per `NPC_PROGRESSION.md`, crafter NPCs level too. Pellah at
lvl 60 in carpentry repairs only mid-tier wood. At lvl 75 he
unlocks one master-tier recipe. The orchestrator tracks each
NPC's craft level + skill mastery. Dialogue references their
craft progression naturally:

```yaml
# in pellah.yaml or generated by the orchestrator
craft_level:
  carpentry: 65          # currently at artisan tier
  woodworking_passive: 12 # learned from years of working

craft_progression:
  carpentry_target: 75   # working toward master-tier
  carpentry_progress_pct: 40
```

A high-level Pellah charges more for repairs (his time is
worth more) and can repair higher-tier gear. Players can
"hire" Pellah to do extended repair work for a guild raid —
a real economic relationship.

---

## Crafting as identity

Demoncore's player base will roughly split:

- **30% pure combatants** — focus on combat content, occasionally
  buy from crafters
- **30% combat + light crafting** — primary craft to grandmaster
  for self-sufficiency on their primary gear
- **30% crafter-first** — primary identity is craft mastery,
  combat is secondary
- **10% hybrid masters** — multi-craft + endgame combat. The
  apex.

This is by design. Demoncore wants both pure DPS-mains AND
pure crafter-mains to feel meaningful. The 8-hour repair
cycle means the economy's *steady state* is defined by the
crafter community supporting the combatant community.

---

## Audible callouts (additions to skillchain_callouts.yaml)

Per `AUDIBLE_CALLOUTS.md`, crafting has its own voice library:

```
synthesis_started:        ["Smithing now."]
synthesis_in_progress:    [hammer rhythm or alchemy bubble SFX]
hq_tier_1_landed:         ["Plus one!", "Sharp!"]
hq_tier_2_landed:         ["Plus two!"]
hq_tier_3_landed:         ["Plus three!"]
hq_tier_4_signed:         ["Master Synthesis!"]
synth_failed:             ["[disappointed grunt]"]
master_synthesis_LB:      ["Master Synthesis!", "[golden particle SFX]"]
repair_started_for_player: ["Mind the splinters."]
repair_completed:         ["Done. Don't break it again."]
crit_repair_proc:         ["Plus five durability! [grin]"]
```

These compose mood-conditioned per the existing pattern.

---

## Mood event hooks (additions to event_deltas.py)

```
("crafted_hq_tier_2_or_higher", "*hero*")    -> ("content",   +0.30)
("crafted_signed_item",        "*")          -> ("content",   +0.50)
("master_synthesis_LB_used",   "*")          -> ("content",   +0.40)
("synthesis_failed",           "*")          -> ("weary",     +0.10)
("crafted_for_player",         "*pellah*")   -> ("content",   +0.20)
("crafted_for_player",         "*"           )-> ("content",  +0.15)
("became_grandmaster",         "*hero*")     -> ("content",   +0.50)
```

The world reacts to crafting milestones: a master-synth LB
spawns audible reactions across the city; a server-first
grandmaster smith gets nation-wide rep recognition.

---

## Why this design (rationale)

The original FFXI crafting was numerical synthesis. Demoncore
turns it into a small physical ritual + a mood-aware skill
system + a mastery curve that ties crafters into the social
fabric. Three things compound:

1. **Repair is the steady-state economic engine.** Players
   need it weekly. Master crafters supply it. Gil flows
   continuously, not stagnantly.
2. **Master synthesis is the apex of crafter content.** Pure
   crafters have a real "endgame" — server-wide reputation
   for signed items + nation-wide title.
3. **Combat-mains and craft-mains both win.** No combat
   player ever feels they "have to" craft; no crafter feels
   they "have to" combat. The two communities are
   genuinely interdependent.

---

## Status

- [x] Design doc (this file)
- [ ] LSB items.sql + crafts.sql additions for the 7 crafts
- [ ] Synthesis mini-game UI (per craft, ~2-3 days each = 14-21 days total)
- [ ] Mood-conditioned proc tables per craft
- [ ] Master Synthesis LB system + signed-item lore engraving
- [ ] Title system: "Bastok Master Smith" etc.
- [ ] Per-crafter NPC reputation tracking
- [ ] Audible callout extensions
- [ ] Mood event hook additions in event_deltas.py
- [ ] First playtest: low-level player crafts a Bronze Sword from raw materials
- [ ] Second playtest: master smith repairs Excalibur for Cid
