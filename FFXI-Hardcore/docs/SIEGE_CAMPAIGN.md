# Siege + Campaign

> Beastmen attack. Nations counter-attack. Both progress over time.

This is the macro-warfare layer that gives non-player entities (mobs, NMs, military NPCs) real XP routes and creates server-wide events that affect everyone. It's a deliberate fusion of OG FFXI's Besieged (Aht Urhgan) and Campaign (Wings of the Goddess) systems, modernized.

## Two pieces

### 1. Siege — beastman raids on nations

Periodically, a beastman horde attacks a nation. Players who are in or near the city get pulled into the defense. Defending player gear, NPCs, guards, and the city itself can take damage. Successful defense rewards the participants. Failed defense has consequences.

### 2. Campaign — nation military deployment

Nations deploy military NPCs to occupied zones based on weekly zone-control rankings. These NPCs:

- Patrol zones, fight beastmen they encounter
- Gain XP from kills (same XP system as everyone else)
- Can die in combat (dead NPCs respawn 8 hours later)
- Wear visible nation colors and respond to faction-aligned events

This both **balances the 10x mob density** (military NPCs help thin beastman populations in occupied zones) and **gives mobs/NMs/military a constant XP source** (the perpetual low-grade warfare across overland zones).

## Siege math

How often do beastmen attack a nation?

```
attack_probability_per_real_hour = 
  base_rate × beastman_strength × inverse_nation_strength × time_since_last_attack_modifier
```

Where:

- **base_rate** = 0.005 (so any given hour, the base chance is 0.5%)
- **beastman_strength** = sum of beastman zone-control percentages (per Campaign weekly rankings)
- **inverse_nation_strength** = 1 / nation's average military deployment density
- **time_since_last_attack_modifier** = `1 + hours_since_last_attack / 168` (so a week without attack doubles the chance)

Practical effect: a healthy, well-defended nation sees attacks roughly every 2-3 real weeks. A weak nation under heavy beastman pressure can see attacks every few days.

### Attack composition

The beastmen attacking are pulled from the surrounding occupied zones. A Bastok attack from Quadav-controlled Pashhow Marshlands draws from the Quadav forces in that zone. The attack force scales:

- **Small raid**: 50-100 beastmen, mostly basic mobs, few captains. ~30-min event. Solo and small parties can defend.
- **Medium raid**: 200-400 beastmen, multiple NMs as captains. ~60-min event. Requires party-level coordination.
- **Major siege**: 500+ beastmen with multiple NMs and a beastman boss. 90-180 min event. Server-wide call to arms; alliances form.

The size scales with the nation's vulnerability score (formula above). A long-untouched nation is a softer target — gets a smaller raid because beastmen find it less defended; but if a long-untouched nation IS doing well, the raid that comes will be a big one.

### Defense rewards

Players defending get:

- XP scaled by tier of beastmen killed (NMs are high XP)
- Loot from beastman drops (per normal rules)
- **Defense Medal** (unique participation token; tradable; required for some endgame quests)
- **Reputation gain in the defended nation** (per `HONOR_REPUTATION.md`) — major rep gain, +200 to +500 depending on raid size and player contribution
- **Honor gain** for high-contribution defenders — saving the nation is heroic (per Honor system)
- A chance at unique drops from beastman bosses (named NMs that only spawn in raids)

### Defense failure

If players + NPC garrison fail to repel the raid:

- Nation **loses zone-control points** for this week
- Some NPCs die (8-hour respawn, but they're gone for the rest of the day)
- **Some city NPCs die** — and per `REACTIVE_WORLD.md`, they don't respawn for 8 real hours, replaced by junior NPCs
- City vendors stocked at reduced inventory until the next regular tick
- A **defeat scar** persists in the city — visible damage on buildings that takes 24 real hours to repair
- Mood-shift in NPC dialogue across the nation for a real day or two — they're somber

This is design-intentional. Failing siege defense matters. Players who care about their nation will defend.

## Campaign — military deployment

### Weekly zone ranking

Once a real week, the system computes per-zone metrics:

- **Beastman activity** (kills, NMs spawned, territory pressure)
- **Player presence** (hours spent in zone by players)
- **Nation interest** (proximity to nation borders, strategic value)
- **Current control percentage** (how much of the zone is "controlled" — nation-friendly vs beastman-friendly)

Zones rank from "stable nation control" through "contested" to "beastman-dominant." Each rank has a deployment recommendation.

### Deployment process

Each Sunday at server-week-tick, each nation reads its rankings and deploys military NPCs to zones according to the recommendations:

| Zone status | Deployment |
|-------------|------------|
| **Stable nation control** | 5-10 patrol NPCs, low-density |
| **Contested** | 20-40 active military NPCs, mid-density, some officers |
| **Beastman-dominant** | 50-100 military NPCs, full unit composition (officers, mages, archers, vanguard); marked as a campaign push |

Total deployments per nation per week is capped (so a nation can't infinite-deploy). Roughly 200-500 military NPCs deployed per nation across all zones at any time.

### Military NPC composition

Per nation:

- **Bastok** — Republican Guard (heavy infantry + musketeers + Galkan officers); fewer mages
- **San d'Oria** — Royal Knights (cavalry + paladin captains + halberds); strong defense
- **Windurst** — Mithra Mercenary Captains + Tarutaru mages + Star Sibyl mages; magic-heavy
- **Aht Urhgan** — Salaheem mercenaries (ranged + corsairs + dancers); flexible

Each unit has a captain (NM-tier, harder kill, bigger XP). Some units have a flag-bearer (their death demoralizes the unit; immediate -10% combat effectiveness for the squad).

### Military XP + death + respawn

Per the user spec:

- Military NPCs gain XP per kill on the same scale as players
- They level up; veteran military NPCs are noticeably tougher
- Death is real — combat death drops them to 0 HP, they're gone
- **Respawn timer: 8 hours** — they come back at full level (death doesn't reset progression)
- A military NPC that's died many times doesn't lose anything but the time-cost of respawning

### Player interaction with deployed military

Players in a zone with deployed military can:

- **Aid them** — fight alongside; the military NPCs drop into "ally" mode and don't accidentally aoe you
- **Coordinate** — talk to a deployed officer; ask for the squad's deployment, get tactical info
- **Recruit them as escort** — pay a small fee, the squad will follow you to a destination
- **Be aided by them** — if you're in trouble in their zone, nearby military will assist if your reputation in their nation is good
- **Receive missions from them** — campaign-specific missions that flow from current zone state

Outlaws can NOT do any of the above. Military aggro outlaws on sight (per the outlaw system).

## Beastmen, in turn

The beastmen aren't passive. They have their own version of the same system:

- **Tribal hordes** are the beastman equivalent of nation military — leveling, coordinated, drawn from the controlled zones
- Beastman zones run their own internal politics; tribes have rivalries
- Sometimes beastman tribes attack EACH OTHER (per the cross-race PvP rules from `PVP_GLOBAL_OUTLAWS.md`) which is great content for players: a goblin-vs-orc battle in the wilderness is XP for everyone
- Beastman raids on nations come from the strongest beastman zones; defending those zones pre-emptively (campaigning IN the beastman zones) reduces incoming siege risk

## XP economy that this fixes

The user's concern: mobs/NMs/bosses need to level up too, and fomors need daytime XP. Siege+Campaign solves this:

- Every hour of every day, military NPCs are fighting beastmen somewhere on the continent
- Beastmen get XP from killing military NPCs (cross-race, legitimate)
- Military NPCs get XP from killing beastmen (cross-race, legitimate)
- NMs and high-tier beastmen accumulate combat experience constantly
- Fomors who roam into these conflict zones get pulled into the fighting, gain XP

Players, NPCs, mobs, NMs, fomors are ALL feeding the same XP economy. The world is alive even when a single player isn't online. The world generates content for the player who logs in: "There's a major Quadav campaign in Pashhow this week; would you like to join the Bastok Republican Guard's counter-push?"

## Consequences for zone behavior

- **Stable zones** are usually safer to traverse — military patrol density helps thin mob populations
- **Contested zones** are dangerous BUT have richer XP (lots of cross-race combat happening = lots of mobs in active combat = ripe for player engagement)
- **Beastman-dominant zones** are travel hazards (overland routes through them are nightmares) but are where the biggest events happen — server pushes to retake a zone are major content events

Players choose their level of engagement. A casual player can stay in stable zones and skirt the big events. A hardcore player lives in contested zones.

## Build order

1. **Zone-ranking computer** — weekly cron that reads per-zone metrics + emits the rank-list. Runs Sunday.
2. **Deployment selector** — each nation reads ranks + dispatches military NPCs into zones per rules.
3. **Military NPC AI** — patrol behavior, combat behavior (RL policy), 8hr respawn, death handling.
4. **Siege probability + trigger** — per-hour roll for each nation; if triggered, draw composition from beastman-controlled zones.
5. **Siege event flow** — UI for "raid incoming," 30-min warning, raid wave logic, success/fail handling, reward distribution.
6. **Defense scars + city damage** — visual + functional consequences of failed defense.
7. **Player coordination tools** — talk-to-officer, recruit-escort, ally-mode squad behavior.

After step 5 the system is live. Steps 6-7 deepen it.

## What we get

A world where there's always something happening. Even the player logging in for a quick 30 minutes can drop into an ongoing Campaign push, fight beside Republican Guard NPCs, gain XP, leave. The world is producing content for itself; the player joins or leaves at will.

This is the missing piece that makes a 10x-mob-density world *coherent* instead of just chaotic — there's now a meta-structure to the wars happening across Vana'diel.
