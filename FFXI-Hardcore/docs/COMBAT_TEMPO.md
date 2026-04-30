# Combat Tempo

> Original FFXI is slow. Modern FFXI is barely faster. Demoncore is fast.

This doc fixes the single biggest gameplay-feel difference between 2002 FFXI and what 2026 players expect. UE5 can render fluid motion at high frame rate with response-time under a frame. We use that. Combat in Demoncore feels like a modern action RPG, not a 2002 turn-based-disguised-as-real-time MMO.

## The numbers

| Metric | OG FFXI | Demoncore | Why |
|--------|---------|-----------|-----|
| Auto-attack swing interval | 4-7s | **1.5-2.5s** | UE5 animations are fluid; the 2002 cadence was a server-tick limitation we no longer have |
| Weapon Skill cast time (low-tier) | 1.5s | **0.4-0.8s** | Tight enough to chain into combos |
| Skillchain window | 2-7s | **1.5-3s** | Chain timing tighter, more skillful |
| Spell cast time (single-target) | 2-5s | **1-3s** | Spells feel responsive |
| Spell recast | 4-30s | **2-12s** | Halve most recasts; specific keystone spells (raise, etc.) keep their weight |
| Mob density per zone | ~50-200 | **500-2000** | 10x. Zones stop being empty corridors |
| Mob respawn timer | 5min - 24hr | **1-15min routine, 30min-2hr NMs** | Aggressive |
| Player run speed (no mount) | 5.0 m/s | **6.5 m/s** | Modest baseline lift; mounts amplify |
| Mounted run speed | 8.0 m/s | **12-15 m/s** | Real difference |

These numbers are starting points. Per-zone tuning is expected.

## What gets faster, what stays slow

### Faster

- **Auto-attacks.** Almost halved. Players are clicking actions, not waiting for them.
- **Spell cast bars.** Most lifestyle spells (Cure, Stone, Refresh, Haste) are sub-2s. Battle-mage feels good.
- **Weapon Skill chains.** The whole skillchain mechanic is preserved but the *timing* tightens — you have to actually be paying attention. Magic Burst is still possible; the window is short.
- **Mount speed.** A chocobo run from Bastok to Sandy that took 8 OG minutes now takes 3-4.
- **Movement and animation.** UE5 anim blueprints with proper root motion. No "skating" frames. Strafing, jumping, climbing all responsive.
- **Mob respawn.** A camped spot is alive again in 10 minutes routine, not 4 hours.

### Stays slow (intentionally)

- **Raise** — long, weighty, the cost of failure stays heavy. Especially in a permadeath world.
- **Tractor / Reraise** — same.
- **Teleports / warps** — long cast (8-10s), interruptable. Travel still has friction.
- **Boss enrage timers** — boss fights have *length* on purpose; we want the marathon energy.
- **Crafting** — a synth still takes seconds. Crafting is meditative; we don't speed it up.

The principle: **action that's about reflex gets faster; action that's about commitment stays slow.**

## Animation cancellation

This is the modern-action-RPG signature feature OG FFXI lacked entirely:

- **Cancel auto-attack startup** by initiating a Weapon Skill or moving (commits to whatever you canceled into).
- **Cancel WS recovery** by moving (lose the WS bonus damage but you're not stuck mid-pose).
- **Cancel spell mid-cast** by moving (interrupts the spell, like always — but you regain control instantly, no recovery animation).

This single feature is what makes combat feel *good*. Player input has agency.

## Mob density: the 10x problem

500-2000 mobs per zone is a real CPU/GPU/network challenge. Mitigations:

### Tier the mobs

| Tier | Behavior | Cost |
|------|----------|------|
| **Hero** (current target, 1 per player) | Full RL combat policy, full animation, full audio | High |
| **Active** (2-15 in combat radius) | Scripted+RL hybrid, full anim, partial audio | Medium |
| **Ambient** (everything else) | Patrol-only, low-tick AI, animation LOD'd, no audio | Low |

When a player approaches an Ambient mob, it gets promoted to Active. When they leave combat range it demotes back. Single mob never costs full Hero-tier compute unless it actually matters.

### Spawn density per zone

Zones get budgeted, not flat-rate:

| Zone type | Mob density | Rationale |
|-----------|-------------|-----------|
| **Newbie** (Ronfaure, Sarutabaruta, Gustaberg) | 500-800 | Lots of trash to feel alive; XP is plentiful |
| **Mid-tier** (Jugner, Yhoator, Pashhow) | 800-1500 | Bigger, denser, more variety |
| **High-tier** (Beadeaux, Ifrit's Cauldron) | 1500-2500 | Hostile, oppressive, players move slowly |
| **End-game** (Sky, Sea, Dynamis, Limbus) | 2000+, with NM density 5x normal | The reason you go there |

### Network cost

A zone with 2000 active mobs broadcasting positions is 10x the bandwidth of OG FFXI. We mitigate:

- **Position deltas, not absolute positions.** UE5 client interpolates between sparse server updates.
- **Active radius**: only mobs within 80m of any player get full position broadcasts. Beyond that, ambient mobs get coarse position updates every few seconds.
- **Persistent connections** — same network architecture LSB already uses; we tune buffer sizes.

If we hit a hard cap, we lower per-zone density. Better to ship a zone at 800 mobs that runs smoothly than 2000 that lags.

## Respawn rates

### Trash mobs

Routine trash respawns in 1-15 minutes depending on zone tier. The fixed timer is a compromise:

- Too fast (under a minute) and a parked AoE-grinder farms infinite XP.
- Too slow (over 30 min for trash) and we recreate OG FFXI's empty-zone problem.

10 minutes is the sweet spot for most tiers. Newbie zones lean to 5; end-game leans to 15.

### Named monsters / NMs

- **Standard NMs**: 30 min - 2 hr
- **Tougher NMs**: 4-12 hr
- **Endgame placeholder-chain NMs** (HNMs): 24 hr but with PoP spawn condition or trigger items, not pure timer

The spawn behavior is the same as OG FFXI — placeholders for trigger NMs, time-based for fixed-spawn NMs. We just halve most timers and accept that Leaping Lizzy gets killed every hour instead of every 24.

## Mount-not-invincible rule

User specified: **a mounted player is fast but not safe.**

Mechanic:

- Mount has its own HP scaled to player level (chocobo at level 50 has ~4000 HP; eventually we add more mount types).
- Mounted player takes damage to the mount first. Mount HP drops; player HP doesn't.
- When mount HP reaches zero, rider is forcibly dismounted. Mount despawns. Rider is now in normal combat at the mount's death position.
- Mount can be healed (Cure works on chocobos), repaired (whistle of restoration item), or fed (gysahl greens + 30s safe time).
- Mounts can be ATTACKED by players, NPCs, mobs. A player riding through Beadeaux is not safe just because they're mounted; they're just *faster than a hostile spawn can react*.

In effect: mounts let you **outrun** danger, not **ignore** it. If you stop, get caught, or run into a dense pack, the mount eats damage until it dies and then you're on foot in the worst possible position.

This single rule fundamentally changes overland travel. Riding through hostile territory is risk-managed *speed*, not safe *transit*.

### Mount progression

Per `NPC_PROGRESSION.md` style: chocobos accumulate XP from being ridden through danger, level up, gain HP / speed / abilities. A 50-level chocobo is meaningfully tougher than a starter. Players who care can grind a mount.

## Weapon Skills + skillchains in fast combat

Tighter timings demand cleaner UI. The skillchain window indicator becomes a hero UI element:

- A small, glowing indicator on the target-of-target showing the active skillchain element + a countdown
- Tighter Magic Burst window (1.5s) — but a fat damage bonus inside it
- Multi-character skillchain telegraphs when more than one player is queueing — visible to the whole party
- Auto-WS toggle — like /assist for skillchains: a player can flag "auto-WS into the chain when partner X opens" to make the skillchain happen without millisecond-perfect manual input. Trade: less control, more party-friendliness.

## Skill speed thresholds

Speed has limits that respect game balance:

- Min auto-swing: **0.8s** (no faster, even with Haste II + Hasso + Spirit Surge stacking)
- Min spell cast: **0.5s** (most spells respect a hardcap)
- Min weapon-skill recovery: **0.3s** (cancel-into-WS chains stay possible)

Above these floors stays balanced. We avoid the EverQuest-style "spam-click for max DPS" hellscape; weapon skills always have meaningful gating.

## Build order

1. **Animation pipeline upgrade** — port FFXI character anims to UE5 anim blueprints with root motion, swing-to-impact frames, cancellation windows.
2. **Auto-attack timing rework** — server-side, halve all weapon delay values, validate skill rates still progress reasonably.
3. **Spell timing rework** — same, for spells.
4. **Mob density bump** — multiply zone spawn lists 5x first (not 10), measure CPU/network. Iterate to 10x.
5. **Respawn rate bump** — halve all spawn timers across the board. Measure player XP rate, AH input flux. Adjust.
6. **Mount HP system** — add mount HP table, dismount-on-zero logic, healing paths.
7. **Animation cancellation** — last big feature; ties to all the above.

After step 7 the game *feels* fundamentally different. That's the point.
