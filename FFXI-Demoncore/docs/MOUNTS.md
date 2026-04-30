# Mounts — Speed Without Safety

> "A mount makes you fast. Not invincible." — user spec.

Mounts in OG FFXI are passage tokens. You ride a chocobo from Bastok to Sandy, you can't be attacked, you arrive. In Demoncore the mount is a *vehicle* — fast, vulnerable, and meaningfully part of combat.

## The rule

A mounted player has TWO HP pools that matter: their own, and the mount's. Damage taken while mounted goes to the mount first. When the mount dies:

1. Player is forcibly dismounted at the mount's death position.
2. Mount despawns. There's a corpse for ~30 seconds for retrieval.
3. Player is now in normal combat at that position. Whatever was attacking the mount is now attacking the player.
4. If the player was already debuffed or low HP from earlier in the encounter, they're in trouble.

Mounts do not block damage to the player; they ABSORB it. If the mount has 4000 HP and you took a 1500-damage hit while riding, the mount took 1500. If the mount only had 100 HP left and a 1500-damage hit lands, the mount dies and the remaining 1400 damage spills onto the player.

This makes mounted travel through hostile zones a real risk-management exercise:

- **Outrun threats** — that's the win condition. Mount speed is the tool.
- **Tank threats** — your mount has HP; you can absorb a goblin pull and keep moving.
- **Get caught** — your mount dies, then you die, in that order.

## Mount types

### Chocobo (starter)

Available from level 20 via the standard chocobo licenses we keep from OG FFXI.

| Stat | Value (level 20) | Scaling |
|------|------------------|---------|
| HP | 2000 | +200 per level (mount has its own level) |
| Speed | 12 m/s | +0.05/level |
| Defense | Player's level × 5 | scales with rider |
| Aggro range | 60% of player's | smaller, but exists |

Chocobos can be HEALED (Cure works), FED (gysahl greens restore 30% HP, 30s out-of-combat), and EQUIPPED with light barding (cosmetic + stat boost via crafted items).

### Future mount types

Reserved for later content:

- **Wyvern (Dragoon AF reward)** — flies; faster; less HP than chocobo; can dodge ground hazards
- **Tiger** (Beastmaster mount) — slower than chocobo but tankier; only available to BST job
- **Crystal Dragon (post-mission reward)** — flies + breathes fire (one combat use per long cooldown)
- **Demon mount** (outlaw-only, summoned via outlaw-only quest) — ground-based; same speed as chocobo; aggros most NPCs; intimidating

These are post-v1; chocobo is the only mount at launch.

## Combat while mounted

A mounted player can do limited combat:

- **Auto-attack from mount** — half normal damage, mount's auto-target nearest threat
- **Cast spells from mount** — full damage but +50% cast time (you're balancing on a chocobo)
- **Use Weapon Skills** — possible but +25% TP cost (the mount partially absorbs the energy)
- **Cannot use 2hr / Job Master abilities while mounted** — too unstable

Cannot use Stealth / Sneak / Invisible abilities while mounted (you're more visible, not less). Mount is also visible to mobs that would otherwise miss the player.

## Mount progression

Per `NPC_PROGRESSION.md` style:

- Mount has its own XP track
- XP gain: ridden through hostile territory + survived encounters + race wins (chocobo races, when those exist)
- Per-level: +200 HP, +1% speed, occasional ability unlock (e.g. level 30 chocobo: "Sprint" — temporary speed burst)
- Mount death does not reset progression; mount can be Re-Raised via stable quest
- Mount can be killed permanently (after 3 deaths in 24 hours, the chocobo is "lost" and the player needs a new license)

This makes the mount a *character* of its own. A player who's grinded a level-50 chocobo with full bardings cares about that mount. They don't ride it carelessly into Beadeaux.

## Aggro mechanics

Most mobs treat a mounted player the same as an unmounted one — they'll aggro if in range. A few special cases:

- **Sound-aggro mobs** (skeletons, ghosts) hear hooves at 1.5x normal range — mounts make noise
- **Sight-aggro mobs** (goblins, orcs) see mounted players at the same range as unmounted ones (the mount doesn't help silhouette-wise)
- **True-sight mobs** (some NMs) ignore mount visibility entirely; they aggro on player presence regardless
- **Magic-aggro mobs** (undead) see mana auras; mount HP doesn't shield the player's mana signature

Mounted travel is *generally* safer because of speed, not because of detection avoidance.

## Mount death scenarios

What happens when the mount dies depends on context:

| Scenario | What happens |
|----------|--------------|
| **Solo, in routine zone** | Dismount, normal combat. Player likely survives if they keep their head. |
| **Solo, in high-tier zone** | Dismount, panic, probable death within seconds. Permadeath timer starts. |
| **In a party** | Dismount, can be raised by the party. Mount-loss is recoverable; player-loss is hour-permadeath. |
| **PvP scenario** | Outlaw or hunter who killed the mount now turns on the rider. Mount kill is one act; rider kill is a second act. Mount-only kills don't outlaw-flag (mount isn't sapient). Rider kill does. |

## Travel grammar

Players plan around mount HP. A trip from Bastok to Norg involves:

1. Mount up at Bastok stables (full HP)
2. Outrun goblins through Pashhow Marshlands (lose ~600 HP if you push pace)
3. Stop at Selbina, feed mount (recover 600 HP, takes 30s)
4. Ride hard through Buburimu Peninsula (lose 400 HP but save 5min)
5. Take ferry to Mhaura (mount on ship, no HP loss)
6. Final ride to Norg (mostly safe)

The mount HP becomes a resource you spend like mana. Trips have planning. Travel feels real.

## Stable quests + the mount lifestyle

Each major city has a stable. The stables provide:

- **Healing** (over real time, mount HP regenerates)
- **Bardings** (gear for the mount)
- **Pedigrees** (chocobo color/coat customization)
- **Racing** (PvE chocobo races on tracks; XP source for mount)
- **Breeding** (long quest line; produce a chocobo with custom stat focus)

These are content gates. Players who care about their chocobo can sink dozens of hours into it. Players who don't can ignore it.

## What gets cut

OG FFXI features we explicitly DROP from the mount system:

- **Chocobo Riding License auto-renewal** — gone. License lasts 30 real days; renew at the stable
- **Free chocobo at every chocobo stable for visiting players** — gone. You bring your own chocobo or you walk
- **Chocobo invulnerability** — obviously gone

The user wanted mounts to be *meaningfully part of the game*. These cuts make that real.

## Build order

1. **Mount HP system** — server-side schema; absorption logic in damage pipeline.
2. **Dismount-on-zero** — when mount HP hits zero, dismount logic + mount despawn.
3. **Aggro pull-through** — mobs targeting the mount stay engaged after dismount.
4. **Mount progression** — mount XP track, level-up logic, progression rewards.
5. **Stable quests** — racing, breeding, bardings.
6. **Future mount types** — wyvern, tiger, crystal dragon, demon mount (post-v1).

After step 5 the mount system is shippable. Step 6 is content for later.
