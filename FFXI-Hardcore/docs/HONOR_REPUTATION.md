# Honor + Reputation

> Two gauges. Together they answer the question: "Will the world deal with you today?"

This is the dual-axis morality system that drives most of the NPC-facing gates in Demoncore. It's NOT just for outlaws — every character has both gauges, and both move constantly.

## What each gauge measures

### Honor

**What you would not do.** Internal moral standing. The world doesn't always see your honor directly, but it shows in your bearing, in your eyes, in the way guards size you up at the gate.

Honor moves on **major moral acts** — things that change the kind of person you are, not just what you've done lately:

| Act | Honor change |
|-----|--------------|
| Same-race kill (deliberate) | -200 (catastrophic) |
| Same-race kill (accidental, AoE on ally) | -50 (with mitigation: -25 if ally is unflagged collateral) |
| Theft from NPC | -30 per item, scales with item value |
| Oath-breaking (failing a sworn quest) | -100 |
| Murdering quest-giver mid-quest | -150 |
| Aiding an outlaw with active bounty | -50 |
| Failing to defend an ally from cross-faction attack | -10 |
| Completing a heroic deed (save a town from siege) | +200 |
| Slaying a high-bounty outlaw legitimately | +50 + bounty payout |
| Long-term ally service (linkshell stability over months) | +5 / week |

Honor floor: 0. Honor ceiling: 1000.

### Reputation

**What people are saying about you.** Public, visible, gossiped-about. Shopkeepers know your reputation. Children in the street know it. Reputation moves from **public-facing acts** — the parts of your life that other people watched.

| Act | Reputation change |
|-----|-------------------|
| Completed quest (any) | +5 to +50 depending on tier |
| Completed mission (main story) | +100 to +500 per nation chapter |
| Caught stealing (NPC witnesses) | -100 (public scandal) |
| Caught stealing (no witnesses) | 0 (Honor takes the hit but Rep doesn't) |
| Slain a notable NM publicly | +50 + zone-specific bump |
| Defeated in PvP duel (legitimate) | +5 (you fought; people respect you tried) |
| Won PvP duel | +10 |
| Defeating an outlaw publicly | +20 |
| Becoming an outlaw | -500 (immediate, public knowledge) |
| Spending substantial gil at a vendor (loyal customer) | +1 per 100k gil |
| Long-term residence in a city (not skipping it) | +2 / week |
| Public misbehavior in a town (drunken brawls, etc.) | -10 to -50 |

Reputation is **per-nation** and **global**. You have separate Bastok / Sandy / Windy / Aht Urhgan rep pools, plus a global rep average that the rest of the world reads.

Rep floor: -1000 (universally despised). Rep ceiling: 5000 (legendary).

## What the gauges gate

### Low Honor

| Honor < 200 | Effect |
|-------------|--------|
| **Nation guards** | Refuse entry to all major cities. You can still enter overland zones, you just can't get past the city gates. |
| **Teleports** | Refuse to teleport you to safe zones. You can teleport to wilderness markers (Holla, Dem, Mea) but not Bastok/Sandy/Windy/Jeuno. |
| **Mog houses** | Inaccessible — innkeepers won't rent rooms |
| **Auction House** | You can list, but not search/buy (NPCs won't trust you to take possession) |
| **Linkshell formation** | You can't found new linkshells. You can join them if invited. |
| **Quest acceptance** | Most NPCs refuse to give you quests. Outlaw-flagged quests are unaffected. |

Honor between 200 and 600: city guards still let you in but watch you. Some quests are gated. Teleports work normally.

Honor 600+: free access. Welcomed.

### Low Reputation

| Reputation < -200 | Effect |
|-------------------|-------|
| **NPC vendors** | Refuse to sell. They'll buy from you (gil is gil) but won't sell. |
| **AH** | Listings cap at 1/3 normal slot count (vendors don't trust you with much volume) |
| **Quest progression** | Many side-quests refuse you. Main missions still progress *if* you have the rank prerequisites. |
| **Bonuses** | Vendors charge you 50% MORE for items they DO sell |
| **Conversation** | Most ambient NPCs refuse to talk; quest-givers are curt |

Reputation -200 to 200: neutral. Things work but no one loves you.

Reputation 200-1000: liked. You get tipped off about quest opportunities; vendors give you 5% discounts.

Reputation 1000+: loved. Vendors greet you by name, NPCs offer you secret quests, your fame precedes you.

Reputation -1000: pariah. NPCs WALK AWAY when you approach. Nation guards openly hostile.

### Quests / Main story branching

The reactive-world LLM (per `REACTIVE_WORLD.md`) reads both gauges as part of the NPC's quest-decision context. A quest-giver with a high-rep player gets a different quest text than one with a low-rep player. Some quests are *only* available at high reputation; others *only* at low (the underground-economy questline).

Main missions don't cut you off entirely — they're the spine of the game — but **mission cutscene dialogue, NPC reactions, and quest reward variants all read from your gauges**. A high-honor character liberating a town gets a different cutscene than a barely-tolerated one doing the same.

## What's exempt

### Outlaw safe havens (Norg / Selbina / Mhaura)

Per `PVP_GLOBAL_OUTLAWS.md`, these towns are gauge-blind. Honor + Reputation don't matter inside their borders:

- All vendors sell normally to anyone
- All NPCs talk to anyone
- The Auction House works for anyone

But — and this is the trade — **the AH stock is reduced**. Norg's AH carries roughly 30% of what Bastok's AH carries. Selbina and Mhaura carry less. Outlaws can shop, but the goods aren't the same. High-end gear flows through legitimate cities; mid-tier gear flows through everywhere.

Also, vendor prices in safe havens carry a 20% black-market markup. You pay more for your anonymity.

### Specific occupations

A few vocations sidestep the gauge system:

- **Bounty hunters** with active commission can enter low-honor cities to pursue marks (timed pass)
- **Couriers** carrying mission-critical items have a temporary honor immunity for delivery
- **Outlaw-faction members** (people who chose the outlaw path) operate by different rules — see Outlaw doc

## Public visibility

Reputation is publicly visible — you can `/inspect` anyone in town and see their reputation tier (tier, not exact number). Honor is private — only the character themselves and certain high-tier NPCs (priests, magistrates, certain gods' avatars) can read it.

This means: a high-rep low-honor character is the dangerous archetype — looks fine on paper, walks into town freely, the priests of San d'Oria see something darker but the guards don't. They could be a corrupted ex-paladin. Players will read this character type as "trouble."

A low-rep high-honor character is the unjustly-shunned archetype — the priests respect them, the cathedral lets them in, but the city watch sneers. The classic "wronged knight" trope.

## Recovery paths

Both gauges have rebuilding paths, but at different rates.

### Reputation recovery

Easy in principle:

- Time decay toward neutral (+1/day to neutral; if reputation is at -800 it takes 800 days for time alone, so other paths matter)
- Visible community service (quests for the town: cleanup, defense, supply)
- Public donation to nation treasury (+5 rep per 100k gil donated)
- Long-term residence + spending in one city focuses gain on that city's pool
- Linkshell sponsorship (a high-rep linkshell can vouch for a member, transferring +50 rep one-time per quarter)

Reputation rebuilds fast IF you're willing to do public-facing work. A truly fallen character can be back at 0 in ~3 real months of consistent good behavior.

### Honor recovery

Hard. By design.

- Honor does NOT decay toward neutral on its own (drops are permanent until reversed)
- Slow gain from sustained ally service (+5/week max for linkshell stability)
- Single-point gains from heroic deeds (+50 to +200 for major events)
- Pardon quests for specific Honor crimes (the player-kill pardon mentioned by the user is brutal — see PVP_GLOBAL_OUTLAWS update)
- Pilgrimage routes (ancient Vana'diel paths; visit specific shrines in specific order; +200 honor on completion; one allowed per real year)

A character who falls to Honor 0 can rebuild, but it's the work of months at minimum. By design — the player who decides to start murdering NPCs has bought themselves a long climb back, if they want one.

## Gauge interaction

The two gauges are independent but they correlate over time:

- A bad-honor act usually generates witnesses → -rep
- A high-rep character has more to lose → small honor hits hurt more in social effect
- Some acts are bilateral: theft hurts both depending on whether you're caught

This means a player can't trivially "Honor up" by farming visible deeds while doing private evil — the honor side doesn't move from public stuff. They have to ACTUALLY change their behavior.

## NPCs use this system too

Per `NPC_PROGRESSION.md`, NPCs accumulate. NPCs ALSO have honor + reputation. An NPC guard that captures an outlaw gains rep. A shopkeeper caught short-weighting customers loses rep. NPCs use the same gauges as players.

This means **an NPC can become an outlaw NPC through gauge degradation** even without committing the cross-race kill — if their reputation crashes hard enough (gauge < -800), they're effectively pariah and can drift to outlaw-aligned behavior. Adds depth to the simulation.

## Build order

1. **Schema + persistence** — DB columns for honor + reputation per character/NPC.
2. **Mutator hooks** — onKill, onSteal, onQuestComplete all push gauge changes through a central `apply_morality(actor, kind, magnitude)` function.
3. **Gate enforcement** — guard aggro logic, vendor refuse logic, teleport refuse logic all read the gauges.
4. **One-zone test** — Bastok Markets only, watch the gauges drive NPC behavior over a few hours.
5. **Recovery paths** — the pilgrimage shrines, the donation desk, the linkshell sponsorship.
6. **Public visibility** — the `/inspect` UI shows reputation tier (not exact number).

After step 4 the system is feeling-out. Steps 5-6 fill it in.

## What this enables

The gauges are the connective tissue between the Outlaw system, the NPC progression, the reactive world, the dynamic quests, and the player's day-to-day moral choices. Without them, "outlaw" is binary (you are or aren't); with them, the world is gradient.

A player can be *almost* an outlaw — bad rep, low honor, technically not flagged — and the world treats them like one. They have agency to climb back, or fall further. The gauges are the dial.
