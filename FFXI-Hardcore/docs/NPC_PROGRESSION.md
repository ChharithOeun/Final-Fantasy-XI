# NPC Progression

> Every entity in the world levels up. Every entity buys gear. The NPC at the cooks' guild today is not the NPC who was there a month ago.

This is the system that makes the world *yield* to the players living in it. NPCs aren't static fixtures placed once at zone load. They're characters with goals, careers, and bank accounts.

## Three classes, three progression curves

| Class | Examples | How they level up | What they do with it |
|-------|----------|-------------------|----------------------|
| **Civilian NPCs** | Shopkeepers, guild masters, ambient townfolk | Slow ambient gain from doing their job; fast gain from witnessed events (a fomor wave hits Bastok → guards level up from the fight) | Save gil, buy better gear, gain higher-tier dialogue options, eventually retire and pass their stall to an heir NPC |
| **Mobs / NMs** | Goblins, orcs, named monsters | Fast gain from kill counts (a goblin that's killed 100 newbies is now a notably-tougher goblin); slow gain from time-survived | Spawn higher-tier loot, target higher-level players, evolve special abilities |
| **Bosses** | Avatars, sky gods, top-tier NMs | Per-fight memory — every player encounter teaches the boss patterns | Adapt tactics, unlock late-game phases, become legitimately harder for repeat raiders |

## Civilian NPC progression

Each NPC has a **role**, and the role defines what kind of XP they accumulate.

### Roles

| Role | XP source | Gear they want |
|------|-----------|----------------|
| **Shopkeeper** | Transactions completed, profit margin maintained | Better inventory (more stock slots, rarer base items), better shop equipment |
| **Guild master** | Quests they hand out + complete, students they train | Tools-of-the-trade (smith's hammer, alchemy lab), study books |
| **Guard** | Incidents responded to, monsters slain | Combat gear — same gear players use, sized to their build |
| **Ambient townfolk** | Time-in-zone, social interactions | Seasonal clothing, accessories, very rarely combat gear |
| **Quest-giver** | Quests completed, unique players helped | Cosmetic upgrades, status items |

### XP and levels

NPCs use the same level system as players (1-99 base, plus merit/JP for veterans). The progression rate is much slower — a typical shopkeeper might gain 1-2 levels per real month. Notable events compress that: a guard who survives a fomor invasion of Bastok Markets gains as much in one night as a year of patrols.

XP comes from:
- **Routine ticking** while their job is active (a shopkeeper at their stall earns slow-tick XP whether you visit or not, simulating sales to NPCs other than the player)
- **Witnessed events** — anything dramatic happening in their zone gives them a one-time XP burst
- **Player interactions** — selling to a player, completing a quest for one, giving them advice that they then use successfully (closing the loop costs us nothing if we just check whether the player succeeds at the recommended task)

### What leveling unlocks for an NPC

- **New dialogue branches.** A level-50 cooks' guild master has 30+ years of experience and her dialogue reflects it; a level-5 junior dropped into the role after a fomor wave doesn't.
- **Higher-tier inventory.** A level-30 weapons vendor stocks things a level-5 vendor doesn't. The shop's stock list is gated by the proprietor's level.
- **Quest difficulty tier.** A guild master gives quests proportional to her level; she won't send you on a Promyvion run if she's level 12 and only knows about the local kobolds.
- **Eventually: retirement.** When an NPC hits a personal goal (level cap for their role + sufficient gil saved), they retire. Their stall passes to their heir, an entirely new NPC with their own progression. The retired one shows up in their hometown, no longer doing business but available for nostalgic conversation.

## NPC economic agents (the gear-buying simulation)

This is the part the user named directly: NPCs buy and equip gear like players do, and that drives the economy.

### Per-NPC wallet

Each NPC has:
- A current **gil balance** (initial seed, growing from their job)
- A **savings goal** keyed to their next gear upgrade
- A **gear set** they're currently wearing (visible to players via inspect)
- A **wishlist** generated from their role + level + style

### Decision loop (one tick per game-day per NPC)

```
For each NPC:
  earn_gil(role × level × ambient activity)
  observe_market(local vendors + AH listings × NPC's stat priorities)
  
  if can_afford(top_wishlist_item) and item_is_better(item, current_gear):
    purchase(item)
    equip(item)
    update_visible_appearance()
    if savings_remain > goal_threshold:
      update_wishlist()
```

Vendors honor the same prices for NPCs as players. AH listings can be bought by NPCs (this is the part that drives prices: NPCs become buyers, not just stock-providers).

### Effects on the economy

- **Demand for mid-tier gear** stays high even when no players are around to buy it. Shopkeepers don't drop prices to zero just because the playerbase is asleep.
- **AH listings get cleared** if priced reasonably, even outside player active hours. Players who undercut compete against NPCs as well as each other.
- **Seasonal spending** — guards stock up on combat gear before known dangerous events; cooks' guild buys flour bulk before festivals. Predictable but not deterministic.
- **The cooks' guild master example** from `REACTIVE_WORLD.md` becomes literal: her ingredient prices change because her own NPC suppliers' wallets are growing or shrinking.

### Player-visible appearance

When an NPC equips new gear, players notice: "Hey, didn't Zaldon used to wear leather? Now he's in scale mail. Did something happen to his shop?" This becomes a *narrative cue* — the NPC's progression is the world telling the player a story.

## Mob progression

Mobs aren't characters in the same sense, but they DO accumulate.

### Per-mob memory

Each mob spawn has:
- A **kill count** of player characters this specific spawn has killed
- A **survival time** (real hours since spawn)
- A **territory** (small zone region)

### Level scaling

A goblin in West Ronfaure spawns at level 7. After it kills 3 newbies, it's level 8. After 10, level 9. Soft cap at base + 5 levels. The scaling resets when the mob is killed (next spawn starts at base level again).

This means there are *notable* spawns — the goblin everyone in the LS knows about because it's been killing people for a week. You learn the mob landscape by paying attention.

### NM progression

NMs are scarier. An NM that's gone unkilled accumulates power proportional to the time since its last death. A low-tier NM unkilled for a month becomes notably harder than its baseline — new abilities unlock, HP scales up, drop rate goes up to compensate (the longer it's been alive, the more it has to give).

This creates **NM hunting metagame**: do you kill the leveled-up NM (harder fight, better drops) or wait it out (it'll get scarier; you might miss the window)?

### Mob NMs respect the world

A goblin NM in West Ronfaure that's leveled up from 70 (base) to 85 (max) has:
- New dialogue (yes, NM gobbies talk now via Higgs Audio)
- More elaborate combat patterns (the RL combat policy has been training against player replays in that zone for a month)
- Reputation among the goblin tribe (other goblins in the area cluster near it; pull range is bigger)
- A unique drop in its loot table (something only THIS leveled NM drops, lost when it dies)

## Boss progression

Bosses are the deepest case.

Each boss has a **persistent identity** that survives death:
- Memory of every fight it's been in (party composition, abilities used by players, what worked, what didn't)
- A **policy ID** (the RL inference graph it currently uses for tactics)
- A **phase unlock state** (which mechanics it's revealed; unrevealed mechanics deploy when the boss "remembers" old strategies are stale)

When players progress, the boss progresses. Beat the boss with a tank/2-DPS/healer comp three times → next time, the boss prioritizes targeting the healer instead of the tank because that's the comp that beat it.

The fomor-add system from `HARDCORE_DEATH.md` ties in: high-level fomors that have died near the boss can spawn at its fights. This is intentional — the boss "remembers" the fomors and calls them.

### Anti-degenerate-strat

A boss that learns from every fight will eventually counter every popular strategy. To keep the meta moving but not unwinnable, the boss's policy is:
- **Sampled at fight start** from a pool of ~10 trained policies (variants of the same RL agent trained against different scenarios)
- **Locked for the duration of that fight**
- **Pool refreshes monthly** based on what's been working that month

So a strategy works for a fight; LS-meta-strategies stay viable for weeks; world-meta-strategies (everyone uses tanker-X) shift over months.

## The whole system, summarized

```
World tick (every Vana'diel hour):
  for each NPC:
    earn(); maybe_buy(); maybe_level_up(); maybe_retire()
  for each active mob:
    update_kill_count(); maybe_level_up()
  for each NM:
    update_survival_time(); maybe_unlock_ability(); maybe_buff_drops()
  for each boss:
    no per-tick change; updates happen per-fight only
```

Persistence is in chharbot's SQLite world-state DB next to the existing chharbot data. Tick is a chharbot MCP tool (`world_tick()`) called by a cron daemon.

## Tooling

We don't need new external repos for this. It's:
- **chharbot's existing world-sim hooks** (already designed in `REACTIVE_WORLD.md`)
- **The RL combat policy** trained via `Neural MMO 2.0` + `PettingZoo` (already cloned)
- **The generative-agents memory layer** (already cloned, Stanford repo)

The work is glue: connect the per-NPC memory + economic agent + leveling logic. All chharbot Python.

## Risks

- **Complexity blowup.** 1500 NPCs each saving gil and shopping is a lot of state. Mitigation: bucket NPCs by "active" (in zones with players) vs "idle" (offline ticking only); idle NPCs get coarse-grained ticks (one batched update per real day).
- **Player frustration.** A player who memorized that Zaldon sells X items gets confused when he stops. Mitigation: dialogue cue ("Sorry, sold out — try the new vendor next door"). Don't make NPCs vanish; rotate stock visibly.
- **Inflation runaway.** Lots of NPCs earning gil could pump the economy. Mitigation: NPC-to-NPC transactions don't mint new gil; the existing tax sinks (AH fees, transit fees) apply to NPC purchases too.
- **Boss meta becomes opaque.** Mitigation: the fight-log includes the boss's policy ID; players can read the patch notes for the policy pool. Strategy is information-discoverable.

## Build order

1. **Static NPC progression schema** — DB tables, level/gil/wishlist fields, no behaviors yet. Migration.
2. **One NPC role** — implement shopkeeper progression end-to-end. Zaldon in Bastok Markets is the test subject.
3. **Watch for a real day** — does Zaldon level up sensibly? Does he buy from the vendor next door? Does the dialogue change?
4. **Mob memory + level scaling** — apply to goblins in West Ronfaure. See if "the goblin that killed 5 noobs is harder" works.
5. **NM time-decay buffs** — apply to one NM (Leaping Lizzy is the canonical test target). Verify the drop rate goes up if she's left alone.
6. **Boss policy sampling** — apply to one early-tier boss (Maat). Train the policy pool. Watch the meta evolve.

After step 6 the system is shippable per-zone. Then it's a rollout exercise.
