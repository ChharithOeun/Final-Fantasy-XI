# Hardcore Death + Fomor Resurrection

The defining mechanic of this remake. Every other system answers to it.

## The rule

- A character that dies has **1 real-time hour** to be raised by another player or NPC.
- If the timer expires, that character is **permanently lost** to its owner — no /unstuck, no GM intervention, no second chance.
- The character does not vanish. It is **resurrected as a Fomor** with the *same look, gear, jobs, sub-skills, name, and level* it had at the moment of death.
- The Fomor is no longer player-controlled. It is owned by the **AI orchestration layer**.

This honors FFXI's existing Fomor lore — Vana'diel's fallen adventurers, twisted into ghostly hostiles. We're just making the lore literal.

## Lifecycle

```
Player character dies
        │
        ▼
┌──────────────────────────┐
│ Death state: KO          │
│ 1-hour countdown begins  │
│ Owner can be raised:     │
│  - Raise / Raise II/III  │
│  - Tractor + raise       │
│  - Raise scroll item     │
└──────────────────────────┘
        │ timer reaches 0
        ▼
┌──────────────────────────┐
│ Snapshot taken           │
│  - appearance (race/face/│
│    hair/gear/dye)        │
│  - all jobs + levels     │
│  - all sub-skills        │
│  - merits + JP totals    │
│  - name (preserved)      │
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│ Character flagged FOMOR  │
│  - account loses access  │
│    to that toon          │
│  - toon enters fomor     │
│    spawn pool            │
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│ AI orchestration assumes │
│ control                  │
└──────────────────────────┘
```

## Fomor behavior

- **Active hours**: night-cycle only (Vana'diel time, ~8pm–6am game time). During day, fomors are dormant in their last-died zone.
- **Roaming**: fomors wander their last-died zone by default but can travel to adjacent zones via standard zonelines if pulled by AI.
- **Aggression**: hostile to all live players regardless of level. Aggro range scales with fomor level relative to player.
- **Combat skill**: a fomor uses its preserved jobs and skills. A 75WHM/BLM fomor will buff itself, kite, nuke. A 75WAR/NIN fomor will tank-DPS-stance.
- **Party / alliance**: fomors can party with each other, with regular monsters, and with NMs. The AI matchmaker pairs fomors that died near each other or share linkshell history.
- **Boss support**: when an LSB-flagged boss / NM fight starts, eligible fomors (level-banded, in-zone or adjacent) can be summoned as adds. Caps: max 6 fomors per boss fight, max 1 alliance worth at end-game.
- **Drops**: fomors drop the gear they were wearing at death (not all of it — a pool weighted by rarity). This is *the* gearing economy: you kill the fallen to inherit their kit.

## LSB hooks needed

Implementation lives in chharbot's domain (it owns the agent layer) plus minimal LSB-side patches for the death pipeline.

| Hook | Where | What it does |
|------|-------|--------------|
| `onPlayerDeath` | `server/scripts/globals/death.lua` (existing) | Start the 1-hour timer; persist to `char_fomor_pending` table |
| `onRaise` | `server/src/map/spell.cpp` (existing) | Cancel timer, restore normal flow |
| `fomorTimerExpire` | new server cron, 60s tick | Convert pending → fomor, snapshot, mark account |
| `fomorSpawnTick` | new server cron, 5min tick during night | Pull fomors from pool, spawn in their zone |
| `fomorPartyEligibility` | new C++ helper | Decide which fomors group up |
| `fomorBossAssist` | new hook in `mob_controller.cpp` | When boss aggros, request N fomor adds |
| `fomorAI` | chharbot MCP layer (external) | Drives moment-to-moment behavior; LSB calls out via the `ai_bridge` we already built |

## Owner experience

- Pre-death: visible 1-hour timer in the death UI plus a Discord DM (chharbot pings the owner).
- During timer: owner can spectate (camera attached), call for raise in Discord, log out and risk it.
- On expiry: account is told "Your character has fallen." A new character slot opens up. The fomor goes live within ~5 minutes.
- Forever after: owner can hunt their own fomor. Killing it grants nothing special mechanically but it's *cathartic*.

## Anti-grief considerations

- **Power creep risk.** A high-end fomor with a full set of relic + empyrean gear is genuinely dangerous. We accept that. The world should feel deadly.
- **Spawn rate cap.** No more than `floor(zone_player_count * 1.5)` fomors active per zone. Prevents server-load + screen-clutter explosions.
- **Town safety.** Fomors do not enter Bastok/Sandy/Windy/Jeuno/Whitegate proper. They patrol the outskirts and zonelines. (Outpost zones are fair game.)
- **Death loops.** A character cannot become a fomor twice in 24h on the same account, to prevent rage-deletion farming.

## Why this matters

Permadeath alone is too punishing — it just makes people stop playing. Permadeath that *creates content* turns every loss into a story. The PT that wiped to a Fomor War/Nin in Beadeaux remembers because that fomor *was* somebody's main. The whole zone has history. The economy has churn.

This is the mechanic that makes 4K visuals matter. It's why the soundtrack needs to be re-mastered. The world has to look and sound earned.

## Open questions

- **Fomor evolution.** Do fomors level up by killing players? Lean toward yes, capped at +5 levels above their original. Let them get more dangerous over time.
- **Shared fomor.** If two players were dueling and both die in the same 5min window, do they spawn as a fomor PT? Maybe. Prototype-level question.
- **Player choice on resurrection.** Should a fomor's owner get a one-time prompt at expiry to decline (toon goes to grave, no fomor spawns)? Probably yes — opt-out preserves player agency.
- **Mythological fomors.** Reserved tier — when a notable player (server-first kill, etc.) dies and becomes a fomor, the system flags the spawn as Mythological. Stronger, named, bestiary entry. Kill drops a unique trophy.
