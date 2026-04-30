# Global PvP + Outlaw Bounty System

> Anyone can fight anyone of a different race. Killing your own kind makes you wanted. Norg, Selbina, and Mhaura are the only places you're safe afterwards.

This is the system that makes Vana'diel actually dangerous, and that gives **fomors / mobs / NMs the XP routes they need to keep growing during the day** when fomor-spawn-windows are closed. The outlaw economy is the most cohesive piece of the world simulation — the moral hazard of cross-faction warfare powering both progression and player drama.

## The core rules

1. **Cross-race combat is XP for everyone.** A goblin killing an orc gains XP. A player killing a goblin gains XP. A galka NPC guard killing a yagudo gains XP. Any cross-race kill = legitimate XP for the killer (or killing party).

2. **Same-race combat is outlawing.** A player killing a player → outlaw. A goblin killing a goblin → outlaw. An NPC killing an NPC → outlaw. The "race" check is by faction tag, not literal racial classification (humes/elvaan/taru/mithra/galka all count as "civilized races" for this purpose; goblins are one race; orcs are another; yagudo are another; quadav are another).

3. **Outlaws are huntable everywhere except outlaw safe-haven cities.** Once flagged, the outlaw is fair game for *any* entity in *any* nation — players, NPCs, beastmen, mobs, NMs all aggro the outlaw on sight.

4. **The outlaw safe havens are Norg, Selbina, and Mhaura.** Bandits, pirates, wanted players, wanted NPCs, *and even wanted beastmen* can walk into these towns, trade freely, and not be attacked by the local guards. Player-vs-outlaw violence is allowed in the safe havens (the towns don't enforce peace) but the *town factions themselves* are neutral.

5. **Bounties scale with the kill count.** Each same-race kill adds bounty. The bounty is the gil reward for the killer who takes down the outlaw. Big bounties = big-game-hunting.

6. **Cleansing the outlaw status takes work.** A formal pardon quest, a long delay, or paying off the bounty (to whom: the regional council, an NPC bounty registrar in the outlaw's home nation).

## Why this works for the game

### It gives non-players XP routes

Per `NPC_PROGRESSION.md`, every entity needs to level up. Civilians do it slowly through ambient activity. Mobs do it through kill counts. But fomors only spawn at night, and bosses progress per-fight. **Cross-race PvP fills the daytime XP gap** for fomors, and gives mobs/NMs ongoing incentives to fight each other instead of just camping spawns.

A goblin that kills an orc gains XP. Two goblin packs that meet in the wilderness fight each other for XP. Beastman tribes have territorial wars — and those wars exist because they're how beastmen level up. Suddenly the world is *active* even when no players are around.

### It makes morality weighty

A player who kills another player is not just "PvPing." They're branded. They lose access to their nation. Their guards aggro them on sight. NPCs they used to talk to refuse them service. Players who used to be friends can now profit from killing them. The moral cost is high; the strategic upside is rare.

This is the OPPOSITE of EverQuest red-shard rules. There, killing other players gave you nothing but bragging rights. Here, killing other players is a strategic *escalation* — once you've done it, you've cut a one-way ticket to a different way of playing the game.

### It creates a real reason for the outlaw cities

Norg, Selbina, Mhaura existed in OG FFXI as flavor towns. In Demoncore they have *function* — they're the only places outlaws can do business. This makes them economic hubs; black markets, illicit auction houses, pirate-friendly merchant chains. The outlaw economy is parallel to the civilized economy.

## Bounty math

A player's bounty is calculated per same-race kill:

```
bounty_per_kill = 1000 gil × victim_level × (1 + same_race_kills_in_last_24h × 0.25)
```

Examples:
- First kill: 75-level victim → 1000 × 75 × 1 = 75,000 gil bounty
- Second kill that day: 80-level victim → 1000 × 80 × 1.25 = 100,000 gil bounty (escalation premium)
- Third kill: 70-level victim → 1000 × 70 × 1.5 = 105,000 gil
- A weekend rampage of 10 kills: bounties stack progressively, total can hit millions

Bounties do NOT decay over time on their own. They decay only via:

- **The outlaw is killed** by a bounty hunter (full bounty paid out, slate clean for victim's killer; outlaw goes through normal death loop including the 1hr permadeath timer; if it expires they become a fomor — which is *thematically perfect* for outlaws)
- **The outlaw pays off the bounty** at a regional bounty registrar (cost: 2x the bounty in gil, plus a long quest)
- **The outlaw completes a pardon questline** (per nation: each has its own redemption arc, takes weeks of real time)
- **The outlaw retreats to monastic seclusion** (an extreme cleanse: log out for 30 real days, return with bounty wiped — this exists for the player who wants to break a streak)

## Outlaws by entity type

### Player outlaws

A player who kills another civilized-race player becomes an outlaw. They lose:

- Nation citizenship (can't enter their home nation's main city without aggroing guards)
- Vendor access in non-outlaw cities (vendors refuse them; AH listings don't show)
- Mission progress (their flagged status blocks main quest progression in standard nations)
- Faction reputation with their original beastman-aligned tribes (if any)

They gain:

- The ability to take outlaw-only quests (assassination contracts, smuggling, theft, sabotage)
- The respect of other outlaws (NPCs in safe havens treat them better the more bounty they carry)
- Access to outlaw-exclusive gear (smuggler's cloak, bandit's mask, pirate-flag-bearer set)
- A spot in the outlaw leaderboard, which is publicly visible (this is the *vainglory* system)

### NPC outlaws

A civilian NPC that kills another civilian NPC of their nation becomes an outlaw. Mostly this happens through quest cause-and-effect — a quest that explicitly involves an NPC turning on another. Once turned:

- The NPC vanishes from their old job (rarely — most quests reset their state instead)
- They can be encountered as a hostile NPC in the wilderness
- They can be encountered as a vendor / quest-giver in an outlaw safe haven
- They show up on the bounty board

NPCs leveling up through cross-race PvP (per the earlier rule) sometimes accidentally become outlaws — a guard pursuing a bandit through a town who hits a civilian goes outlaw. The simulation is consistent with the rules.

### Mob and NM outlaws

This is where it gets fun. A goblin that kills another goblin becomes an outlaw goblin. Goblin tribes turn on it; orc tribes ALSO consider it suspect (it's now a free-agent goblin with no tribe protection). Mob outlaws:

- Get aggroed by their own race
- Get *less* aggroed by other races (they're now politically interesting; some other races will *use* them)
- Spawn in unusual places (caves, ruins, hidden spots)
- Drop better loot proportional to their bounty

A high-bounty NM outlaw is the most lucrative possible kill for a player who can pull it off. Years of accumulated PvE XP plus thousands of gil in bounty plus exclusive drops.

### Beastman outlaws

Beastmen play by the same rules. A goblin chief who kills another goblin chief is an outlaw goblin chief. Their tribe turns on them; they retreat to one of the outlaw safe havens; they hire mercenaries (other outlaws — possibly players) to defend their newly-claimed pirate stronghold. The outlaw economy is genuinely cross-faction.

## Safe haven cities

Norg, Selbina, Mhaura. Each has a slightly different vibe but the same rule: **no faction is hostile here**.

| City | Vibe | Specialty |
|------|------|-----------|
| **Norg** | Pirate stronghold (already canonically a pirate town) | The big one. Black-market AH. Ship-to-ship piracy contracts. Linkshell-gathered crews. |
| **Selbina** | Coastal trade town (canonically neutral) | Mercantile. Smugglers' guild. Items that aren't legal in nations are sold openly here. |
| **Mhaura** | Sister-port to Selbina | Smaller. Boatswains, mariners, mercenary crews. The pirate equivalent of a "starter town." |

Inside these cities:

- Guards are neutral. They protect property (block theft) but don't enforce nation laws.
- Players can attack each other freely (this is the only PvP-allowed civilian space).
- Outlaws can hire NPC mercenaries.
- Vendors sell normally; AH listings work; banks function.
- BUT: there is no mission-progression infrastructure. You can't advance the main story line in an outlaw city. You're outside the nation system.

Players who *aren't* outlaws can still go to outlaw cities. They're just walking into a place where everyone else can attack them, and where the local economy is the gray market. Some of the best gear deals (and worst risks) live there.

## Aggro rules per zone type

| Zone | Outlaw treatment | Citizen treatment |
|------|------------------|-------------------|
| **Bastok / Sandy / Windy / Jeuno** | Aggroed by all guards + bounty hunters | Safe |
| **Whitegate (Aht Urhgan)** | Aggroed by salaheem mercs + Salahem-aligned NPCs | Safe |
| **Norg / Selbina / Mhaura** | Safe | Vulnerable to other players |
| **Open zones** (overland) | Open season — beastmen, NPCs, players, mobs all aggro | Standard |
| **Beastman strongholds** (Davoi, Beadeaux, Castle Oztroja) | Beastmen still aggro outlaws (you're still a hume/etc to them); but other outlaws within the stronghold tribe might shelter you — case by case | Standard hostile |
| **Sky / Sea / Dynamis** | No special outlaw rules; everyone there by definition | Standard hostile |

## Bounty board

A regional bounty board lives in every nation's capital plus every outlaw city. The board lists active outlaws above a certain threshold (e.g. > 50,000 gil bounty). For each:

- Outlaw name + faction + level
- Current bounty value
- Last known sighting (auto-updated when seen by NPCs or guards)
- Contract: who's offering the bounty (a player, a nation, a beastman tribe, a private NPC)

Players can *issue* bounties on specific targets if they have the gil to fund them. This makes bounty-hunting a side-economy: rich players paying poor players to hunt people they're mad at.

## Anti-grief mitigations

The system has obvious abuse vectors. Mitigations:

- **Anti-spawn-camp**: a player who's been killed by the same outlaw 3 times in 4 hours triggers a "rejoinder" mechanic — the killer's bounty doubles for further kills of the same victim, AND the victim gets a 30-min "tracker" buff that highlights the killer on their map for retaliation. Repeat-griefing becomes economically irrational.

- **Anti-nation-wipe**: a player can't outlaw-kill more than 5 NPCs in the same nation per real day before guards become *substantially* tougher and territorial. A high-bounty player walking into Bastok at level 75 is fighting a small army. The system pushes back proportionally.

- **Outlaw-on-outlaw**: outlaws killing other outlaws is FINE — that's still cross-faction (outlaw is a faction). No additional bounty stacks for it. This means outlaw-vs-outlaw is the most *legal* PvP available.

- **No safe-haven escape mid-fight**: a player taking damage in a non-safe-haven zone can't zone-line into Norg as an emergency escape. The zone-line is gated by a non-combat-state check; you have to disengage first.

- **Permadeath interaction**: outlaws who die start the 1-hour permadeath timer like everyone else. If they expire they become fomors. This means **outlaw fomors are a thing** — players who lived as outlaws and died become AI bandits. They have their own outlaw-themed AI behavior in the fomor pool.

## Implementation outline (LSB hooks)

| Hook | What it does |
|------|--------------|
| `onKill` | Check killer + victim factions; if same-race and not already outlaw → flag outlaw + mint bounty |
| `onZoneLine` | Check outlaw status; if entering a non-safe-haven nation → trigger guard aggro + bounty-board update |
| `onAggro` | Check outlaw status; if outlaw and target is faction-aligned NPC → aggro |
| `onBountyKill` | Pay bounty to killer; mark target as cleansed |
| `worldTick` | Update outlaw decay (none auto, but track elapsed time for cleanse-quest progress) |

These hooks get added to the existing LSB onKill / onZoneLine / onAggro mechanism we already use for fomor and reactive-world systems.

## Build order

1. **Static outlaw flag + bounty schema** — DB migration. Add `outlaw_status`, `bounty_value`, `outlaw_kills_24h` to player + NPC + mob accounts.
2. **Same-race kill detection** — onKill hook checks faction; flags + mints bounty.
3. **Aggro logic** — guards aggro outlaws on zone-entry; bounty hunters can target.
4. **Outlaw safe-havens** — make Norg + Selbina + Mhaura faction-neutral; disable guard aggro there.
5. **Bounty board UI** — in-game UI element listing active outlaws + claim mechanics.
6. **Cleanse paths** — pardon quest for each nation; bounty registrar NPCs.
7. **NPC + mob outlaw integration** — same rules apply to non-player entities; AI logic respects outlaw faction.

After step 7 the system is functional. Tune the bounty math after watching real player behavior.

## What this enables that nothing else does

The combination of (a) global cross-race PvP, (b) same-race outlaw flagging, (c) safe-haven outlaw cities makes Vana'diel feel like a *world*, not a collection of zones. Players are not the only actors. Beastmen wars happen. Goblin civil wars happen. The outlaw NM that's been roaming Beadeaux for two months is famous — and worth a fortune to the player who finally takes it down.

This is the design pivot that makes Demoncore not-FFXI-with-better-graphics. It's a different game living in FFXI's world.
 
--- 
 
# PVP_GLOBAL_OUTLAWS — Patch / Addendum

Three additions on top of the original `PVP_GLOBAL_OUTLAWS.md` per user direction. Apply these to the live doc when we land the next batch.

## 1. Pardon quest for player-killing is BRUTAL

The original doc mentioned a "long quest" for cleansing outlaw status. This is the spec. **The pardon quest for killing another live player must be intentionally rough.** Demoncore is the hardest FF game in history; MPK abuse is corrosive; the pardon path must be expensive enough that no one player-kills on a whim.

### The quest

Tiered by number of player-kills committed:

| Player-kills committed | Pardon quest length | Cost |
|------------------------|---------------------|------|
| 1 | 1 real week | 5,000,000 gil + escort 3 NPCs across hostile zones (high-risk) |
| 2-5 | 2 real weeks | 20,000,000 gil + complete a multi-step retrieval quest involving travel to all four nations + 2 dungeon clears |
| 6-15 | 4 real weeks | 80,000,000 gil + a public reparation quest where the player works as an indentured-NPC for victims' linkshells (pre-arranged compensation outside game) |
| 16+ | NOT cleansable | Player remains permanent outlaw. Their only path is to embrace the role. |

### The quest mechanics

- **Cannot fast-travel** during pardon quest — teleports refuse, airships refuse, ferries refuse. Must walk.
- **Cannot accept other quests** — your full attention must be on the pardon
- **Cannot enter the home nations** of victims unless explicitly part of the quest step
- **Bounty does not decay** during the quest — if you give up partway, you're back where you started
- **Failure conditions**: dying during the pardon resets quest progress; declining quest dialogue locks the pardon for 30 real days

### Why the harshness

- A 5-million gil quest is a working-class player's months of grinding. They don't decide to player-kill lightly.
- A real-week-minimum pardon means a player who PKs on impulse loses substantial play time to repentance.
- The lockout for 16+ kills is the moral statement: you've made your bed.

## 2. Accidental outlaws — collateral damage is real

Per user: "collateral damage to environment stays (slowly heals) and collateral damage to allies are possible, even accidental killings, making people become accidental outlaws."

### The mechanic

- **AoE friendly fire is ON.** A WHM's Banishga or a BLM's Comet can damage allies caught in radius. With the 10x mob density and tight skillchains of fast combat, accidental hits will happen.
- **A friendly fire that kills an ally** is treated as a same-race kill: outlaw flag triggers + bounty mints.
- BUT: the system tags the kill as **"accidental"** if:
  - The killer's ability was AoE
  - The target was in their party or alliance
  - There was no hostile flag toward the victim in the prior 60 seconds
- Accidental outlaws have:
  - **Half-bounty** (50% of the same-race kill rate)
  - **No witness penalty** (Reputation hit reduced to 1/4)
  - **A faster pardon path** — 1 real day, 500k gil, plus the ally must accept an in-game apology + restitution offer

### Environment damage

Per user: environment takes damage but slowly heals. Most ground destruction reverts in 30-60 minutes. But:

- **City buildings damaged by player negligence** (running fire spells in town center, etc.) generate Reputation loss in that nation
- **Critical structures damaged** (signposts, vendor stalls, etc.) trigger NPC complaint dialogue + a small repair fee charged to the offender
- **Beastman raids cause environmental damage** that takes 24 real hours to repair (per `SIEGE_CAMPAIGN.md`)

The whole system says: **everything is consequential.** A player's actions echo into the world.

### Ally damage rules

- AoE ally damage is **scaled** — you do 50% of your normal damage to allies caught in your AoE (mitigation, not zero — players have to LEARN positioning)
- Ally HP can be reduced to zero. The killer is flagged outlaw (with accidental tag).
- Tank classes (PLD, NIN, RUN) carry a passive ability "Comradeship" that further halves AoE damage to allies — slight protection for the front-line role.
- **Healers** do NOT enable friendly-fire (you don't accidentally damage someone with a Cure). Healing AoE always heals only.

## 3. Force-outlaws-from-safe-havens

User specified: outlaws can't camp safe havens forever. They must be forced to leave occasionally.

### The mechanic

Each outlaw has a **safe-haven residency timer**. When entering Norg / Selbina / Mhaura, the timer starts. The maximum continuous stay is **48 real hours**.

Beyond 48 hours:

- **Hour 48-50**: warning dialogue from local NPCs ("Your kind ain't welcome forever, friend.")
- **Hour 50-52**: vendor refusal escalates — even Norg vendors stop selling
- **Hour 52-54**: aggressive NPCs ("Bouncer NPCs") spawn near the outlaw and demand they leave; combat is initiated if the outlaw refuses
- **Hour 54+**: the outlaw is forcibly teleported to a random hostile zone with no warning

The timer **resets** when the outlaw leaves the safe haven for at least **6 real hours**. So legitimate use of the haven (drop in, conduct business, leave, hunt your bounty mark, return another day) is fine. The system specifically targets **camping** — extended residency.

### What the timer does to the player

- A forced eviction at hour 54 dumps them in a random hostile zone with **3 hostile mobs spawned within 30m** (the eviction is dramatic, not gentle)
- They retain inventory, status, etc. but their position is random
- They cannot zone-line BACK into a safe haven for 12 real hours after eviction
- During that 12-hour cooldown, they're hunted — their bounty board listing flags them as "recently evicted" which is a public marker that bounty hunters use

### Why this works

- Safe havens become functional shelter, not bunkers
- Outlaws have to be *active* to maintain their lifestyle — they can't just hide
- Bounty hunters get periodic windows to find marks
- The world is in motion; no equilibrium where outlaws settle and the live game doesn't see them

### NPC outlaws use the same timer

A wanted goblin chief who flees to Norg can use the safe haven, but the same 48-hour rule applies. Eventually the goblin chief is forced back out, and the bounty hunter players hunting them get a fresh shot.

## How these three things compose

The system as a whole now has *teeth*:

- **Player-killing is so expensive to recover from** that it's a strategic decision, not a tantrum
- **Accidental outlawing keeps positioning and party-coordination meaningful** — sloppy AoE has cost
- **Safe-haven eviction keeps the world in motion** — outlaws can't park and disappear

Combined with the existing outlaw-flag, bounty, fomor mechanics, this is a system where every PvP decision ripples outward. Kill another player and you've signed up for a real-week of repentance. AoE through your party and you've signed up for a real-day. Camp Norg too long and the world rejects you.

This is what makes Demoncore the hardest FF game ever — not just permadeath, but **consequences for every action that scale to actually matter.**
