# Fomor Gear Progression

> The recursive purple-stat loop. Killing fomors is the endgame because every fomor is wearing what someone else lost.

This is the loot system that makes the permadeath mechanic *load-bearing economically*. Every fomor on the server is wearing a snapshot of someone's past gear. Killing them returns that gear (sometimes, with bonuses) to the live economy. It's the entire reason hardcore-death matters at the system level — fomor gear is real, scarce, and improving.

## The drop rule

When a player (or NPC, or other entity) kills a fomor, **each piece of gear the fomor was wearing is rolled independently**:

- **3% chance per piece, independent**, NOT a combined 3% for the whole set
- A fomor wearing 16 pieces (full set + accessories) generates 16 independent 3% rolls per kill
- Average expected drops per kill: 16 × 0.03 = 0.48 pieces (about half the time you get something)

Each successful roll drops that piece **with improved stats** — visually marked with **purple stat numbers** in the tooltip. The improvement is real:

| Improvement tier | Stat boost | Visible label |
|------------------|------------|---------------|
| **Purple I** | +5% to all stats on the piece | `+I` purple |
| **Purple II** | +10% to all stats | `+II` purple |
| **Purple III** | +15% to all stats | `+III` purple |
| **Purple IV** | +20% to all stats | `+IV` purple |
| **Purple V** | +25% to all stats (cap) | `+V` purple |

Stats include the piece's offensive numbers (attack, accuracy, magic burst, etc.), defensive numbers (defense, resists, evasion), and any specific procs the piece carries. They scale uniformly — no random rolls on which stats improve. A +I Hauberk has +5% on every stat the base Hauberk has.

The improved gear **respects all original requirements**: level, job, sub-job, race (if any), elemental affinity (if any). A +III Cobra Tunic still requires WAR55. The improvement doesn't relax constraints; it amplifies the gear's existing power within them.

## The recursion

This is the loop:

```
Living player wears Cobra Tunic (vanilla)
    ↓ dies, becomes fomor
Fomor wears Cobra Tunic (vanilla)
    ↓ killed by another player, 3% drop roll succeeds
That player loots Cobra Tunic +I (+5% stats)
    ↓ wears it, dies, becomes fomor
Fomor wears Cobra Tunic +I
    ↓ killed by another player, 3% drop roll succeeds
That player loots Cobra Tunic +II (+10% stats)
    ↓ recursion continues until +V cap
```

A piece of gear in the world has a **lineage** — every successful drop adds another tier. The stat improvement caps at +V (25% over base) so the system doesn't trend infinite. Once a piece is at +V, future fomor drops of that same piece pop at +V with no further escalation.

## Player tools to read the lineage

Each piece of gear remembers its lineage:

- The tooltip shows the current tier (`Cobra Tunic +III`)
- Right-click → "Inspect Lineage" shows the chain: who originally crafted it, who wore it as a player, which fomors carried it, who killed each fomor
- For high-tier pieces (+IV/+V) the lineage is a *story* — players track infamous gear like infamous fomors

This makes a piece of gear emotionally weighty. The +V Octave Club isn't just a weapon; it's a record of every player who lived and died wearing it.

## Where fomors spawn

User specified clearly: **fomors only spawn in zones that match their level**, and **can roam/spawn elsewhere if they level up**.

Implementation:

- A fomor at level 35 spawns in Pashhow Marshlands (level 28-42 zone) routinely
- That fomor starts with kill behavior tied to that zone's PvE difficulty band
- As the fomor accumulates kills (per `NPC_PROGRESSION.md` mob memory), it levels up
- A leveled-up fomor's spawn pool expands: a level-50 fomor can spawn in Pashhow OR Crawlers' Nest OR Garlaige Citadel
- A level-75 fomor's spawn pool covers high-tier zones across the continent

Fomors that haven't been killed in long stretches accumulate level (per the NM time-decay buff in NPC_PROGRESSION). A fomor that's gone unkilled for 4 real days becomes notably stronger and roams further.

## Why this works

Three feedback loops:

### 1. Permadeath has economic stakes

Without this, a player who dies and becomes a fomor "loses their gear." With this, their gear *becomes loot* for the next person to take it down. The death isn't a deletion; it's a redistribution.

### 2. Endgame becomes hunt-the-fomors

Top-tier players need top-tier gear. The *only* path to +III/IV/V pieces is hunting fomors — and the higher the fomor's level, the better the gear it carries (because it was someone late-game who died wearing late-game gear).

A level-90 fomor wearing relic gear, that's been roaming for two real weeks accumulating level, is a server-event-tier hunt. The drops would set whoever finally takes it down for the rest of the expansion.

### 3. The gear pool is finite-but-self-replenishing

Total +V pieces in the world stay roughly stable: as some get destroyed (yes — see "loss" below), new ones bubble up through the recursion. The economy stays in motion without runaway inflation.

## Loss conditions

Pieces can be destroyed:

- **Permadeath of the wearer + recursion miss**: when a player wearing fomor gear dies, becomes a fomor, and the next killer DOESN'T succeed on the 3% roll, the piece returns to the live world (it's lost from the fomor's wardrobe, not destroyed). 
- **Crystal-Strike** (rare PvP mechanic): a special ability or item that breaks gear permanently. Used vs. outlaws hoarding too much purple gear.
- **Fomor-vs-fomor combat**: when fomors kill other fomors (which happens — they're aggressive entities), the dead fomor's gear is GONE. Not dropped to anyone. Permanently. This is a slow but real attrition path.

This means the +V pool isn't infinite. It's a function of player count × death rate × kill rate × fomor-vs-fomor friction. Tunable.

## Anti-farming protections

A player who could repeatedly farm one weak fomor for a +III Crayon (or whatever low-tier piece) would break the economy. Protections:

- **Per-fomor cooldown**: after a fomor is killed, that specific fomor's spawn point has a 1-hour cooldown before the next fomor of that level can spawn there. Prevents campers from chain-killing the same individual.

- **Per-player fomor-kill limit**: a player can't successfully drop fomor gear more than 3 times per real day. After 3 successful drops, additional kills proceed but don't roll for gear (just XP). Forces players to spread their hunting. Resets at server day-tick.

- **Drop diminishing returns within session**: the 3% per-piece rate is ONLY 3% on the first fomor of a session. Subsequent fomor kills in the same session see the rate decrease (3%, then 2%, then 1.5%, etc., with refresh on logout/login).

- **The piece must be wearable by the killer**: a level-30 character killing a level-90 fomor wearing relic gear doesn't roll for gear they can't equip. The system checks usability and skips ineligible drops. (Anti-griefing-via-low-level-bait.)

## Anti-perma-loss frustration

Players who lose +V gear feel terrible. We mitigate:

- A player whose +V piece becomes fomor gear gets a "lineage notification" — they know their piece is in play. They can hunt their own former character + their own gear.
- A player can `/will` a piece of gear to a specific other character. If the wearer dies and becomes a fomor, the will-recipient gets first crack at the inheritance (a 24-hour priority kill window).
- The bounty board lists the most-coveted-gear fomors, sorted by lineage tier. Public knowledge of where the high-tier loot is roaming.

## Why fomors only spawn at matching levels

User specified the rule. The reasoning is gameplay clarity:

- A level-30 zone shouldn't have level-90 fomors stomping starter players. That's grief.
- A level-30 fomor in Ifrit's Cauldron is a joke; a level-30 player wouldn't bother.
- Match the zone tier to the fomor level so encounters are interesting.

The "roam and spawn elsewhere if they level up" rule means that fomors who've been around long enough get to expand their territory naturally. A fomor that started in Ronfaure as a level-15 has, by the time it's level-50 from accumulated kills, earned the right to range into Jugner Forest. By level 75 it can show up almost anywhere appropriate.

## Implementation outline

| Hook | What it does |
|------|--------------|
| `onFomorKill(killer, fomor)` | Roll 3% per equipped piece; for each success, generate piece at fomor's tier+1 (cap +V); apply per-player + per-fomor cooldowns; check killer eligibility |
| `onFomorSpawnCheck(level)` | Pick a zone from level-band-matching pool; if fomor is leveled-up, expand pool |
| `onFomorWearablePieceTier(piece)` | Tracks the piece's current tier; persists across player death + fomor recursion |
| `onFomorVsFomorKill(killer_fomor, victim_fomor)` | DESTROY all of victim's gear permanently |

## Storage

Each piece of gear is a row in a global gear DB:

```
gear_id | base_template | current_tier | lineage_history | current_holder | current_holder_type
```

`lineage_history` is a JSON array of (timestamp, holder_id, holder_type, event) tuples. This grows over the gear's life — eventually big, but a +V piece is rare enough that the chain is finite.

## What this means for the player

The economy in Demoncore has a heartbeat. Gear flows: from crafters into the market, from market into player hands, from player hands into fomor hands on death, from fomor hands back into player hands on kill — each cycle an upgrade. The most legendary gear in the world has a paper trail that touches a dozen names. Some pieces become *known*: "the +V Cobra Tunic that Lion of San d'Oria wore in 2027" is a real piece of gear in the world database.

This is what makes Demoncore not a single-player roguelike with hardcore death — it's an economy with hardcore death. The gear remembers.
