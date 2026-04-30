# MAGIC_BURST_SCENARIOS.md

Worked combat examples that demonstrate the full Demoncore stack
firing in concert. Each scenario walks frame-by-frame through a
real fight, showing which systems trigger when, what audible
callouts fire, and what the players see + hear.

These are **playtest scripts** — when we get to the first end-to-end
trial of the combat stack, we run these scenarios and verify each
beat behaves as documented.

---

## Scenario 1: The Anti-Cheese Lesson (first failed kite)

**Setup**: lvl-25 BLM/WHM facing a Naga Renja (lvl 28) in
Phomiuna Aqueducts. Player thinks BLM kiting + nuking is the
right strategy. Naga is sprint-NIN per `NIN_HAND_SIGNS.md` —
the lesson is they CAN'T be kited.

```
T+0.0  Player /checks Naga from 25m away. Sees: "Tough, (seems
       alert), (unharmed)". Decides to engage from range.
T+0.5  Player begins Stoneskin cast (1.5s cast time).
       BLM takes 1 step backward → 1.40x interrupt risk
       per WEIGHT_PHYSICS.md (BLM not RDM/BRD; running ~ 1.80x).
T+0.8  Naga audibly hisses. Begins Bird seal (Hyoton Ichi opener).
       Player sees the seal. Doesn't recognize it yet.
T+1.5  Stoneskin completes; +280 absorption shield.
T+1.6  Naga finishes 6-seal sequence: Bird → Snake → Ram → Boar
       → Ox → Tiger. Hyoton: Ichi launches.
       Niagara cyan-shift on Naga's hands; ice shard projectile.
T+1.9  Hyoton: Ichi hits player; Stoneskin absorbs 280, remaining
       110 damage hits the BLM. Visible-health stage transitions:
       pristine → scuffed (per VISUAL_HEALTH_SYSTEM.md).
       Player audibly grunts (auto pain reaction).
T+2.0  Player begins to kite. Backs up at 70% movement (medium
       weight, no Sprint).
T+2.1  Naga's RL policy detects target_velocity_magnitude high.
       Pops Sprint Pursuit. Naga's effective movement is now
       1.4× player's run speed (Naga is light + sprint mode).
T+2.5  Player tries Aspir to drain Naga MP. Aspir cast time 2.5s.
T+3.0  Naga starts Doton Ichi (3-seal Boar → Dragon → Rabbit, ~0.45s).
       The seal sequence is VISIBLE. Player would learn to read this
       on a second encounter.
T+3.5  Doton: Ichi seal completes. Bind lands on player.
       Player's feet are visibly rooted (per VISUAL_HEALTH_SYSTEM
       Bind cue).
T+3.6  Aspir cast interrupts because player got hit while casting.
       Player audibly grunts in frustration.
T+4.0  Naga reaches melee distance. Begins melee attack rotation.
       Player at ~50% HP; visible-health stage: scuffed.
T+4.5  Player panics. Tries to cast Sleep on the Naga (5s cast).
       Player still bound + low HP.
T+5.0  Naga's HP ~ 90%. Mood ALERT (Naga's starting_mood).
T+6.0  Naga attacks while signing Aisha (debuff stack). Player
       takes another wave of damage.
T+7.0  Player at 15% HP, broken stage. Audible gasp continuous.
T+8.0  Sleep finishes casting. Lands on Naga. Naga sleeps.
T+8.1  Player breaks Bind via natural recovery (5s).
T+9.0  Player runs back 30m, stops, casts Cure III on self. Cure
       III animation: crisp Light particles, "warm even tone"
       voice callout: "Cure!"
T+11.5 Naga wakes up (ambient sleep wake threshold ~3.5s).
T+12.0 Player sees Naga still alert, pulls out a real strategy
       (BLM solo isn't going to work).

LESSON LEARNED: The visible seal sequence + sprint pursuit
behavior teach the player that:
  1. Naga signs are visible — they could have read Hyoton Ichi
     early next time
  2. Naga ignores kite (Sprint Pursuit during signing)
  3. Bind is how the Naga finishes a kite-attempt
The player adapts on encounter #2.
```

**Systems firing**: VISUAL_HEALTH_SYSTEM (stages, grunts), WEIGHT_PHYSICS (1.40x interrupt during step), NIN_HAND_SIGNS (visible seals + sprint-cast), AUDIBLE_CALLOUTS (grunt + Cure!)

---

## Scenario 2: The First Skillchain (party tutorial completion)

**Setup**: lvl 12 party of 2 (WAR + WHM) facing 2 Goblin
Pickpockets + 1 Goblin Smithy (lvl 14, the first boss
recipe). The skillchain tutorial conversation has been done
with Cid; the players are supposed to chain-close on the boss.

```
T+0.0  WAR pulls aggro on Goblin Smithy with Provoke.
T+1.0  Smithy starts Hammer Slam cast (1.5s cone, 4m forward).
       Visible AOE telegraph appears under WAR — orange dashed
       border (player-cast preview), then snaps to solid red
       once Smithy commits the cast.
T+2.0  WAR steps to side. Hammer Slam misses.
T+2.1  WHM /checks Goblin Smithy. Sees: "Tough, (seems gruff),
       (slightly hurt)" — the goblin is at 90%+ HP.
T+3.0  WAR's TP = 100. Uses Crescent Moon (a compression-property
       weapon skill). Audibly shouts: "Skillchain open!"
       Chain marker visible on Smithy.
T+3.5  WAR reaches Smithy melee, chain marker has 8s left.
T+4.0  WHM has 100 TP. Could close with Hexa Strike (a
       transfixion-property club WS) — but doesn't know.
       WAR voice callout: "Close it — transfixion!"
T+4.2  WHM casts Hexa Strike (1s wind-up). Compression +
       transfixion = Compression Level 1 chain (8 elements per
       SKILLCHAIN_SYSTEM.md table).
T+5.0  Hexa Strike connects. Chain detonates.
       Niagara halo: desaturated purple + dark inhalation.
       Audible: "Closing — Compression!"
       Visible-health flash: target HP visible to entire
       party for 2 seconds — Smithy is at 67%.
T+5.5  3-second Magic Burst window opens. WHM recognizes the
       window — but is at lvl 12, not yet trained on
       intervention/MB timing per PLAYER_PROGRESSION.md.
       Window expires.
T+6.0  Standard combat resumes. WAR and WHM beat the Smithy
       down via auto-attacks.
T+9.0  Smithy at scuffed. Audible labored breathing starts.
T+12.0 Smithy at bloodied. Visible blood decals; limp on left side.
T+14.0 Smithy at wounded. Hammer drops; goblin claws furiously.
T+16.0 Smithy at grievous. Stagger.
T+18.0 Smithy at broken. Death animation.
T+18.1 Cinematic plays (4s defeat). Cid's voice off-camera:
       "Now THAT was a chain. Welcome, kids."
T+22.0 Loot drops. Bronze Ore + 200 gil.

PROGRESSION GAINED:
  - WAR: Crescent Moon mastery 1 → 2 (chain opener earned exp)
  - WHM: Hexa Strike mastery 0 → 1 (first chain close)
  - Both: +5 reputation in Bastok Mines (party-tutorial-clear flag)
```

**Systems firing**: AOE_TELEGRAPH (player AOE preview + solid telegraph),
SKILLCHAIN_SYSTEM (chain marker + halo + HP flash), AUDIBLE_CALLOUTS (every callout),
VISUAL_HEALTH_SYSTEM (5 stage transitions on Smithy), PLAYER_PROGRESSION (mastery exp + reputation)

---

## Scenario 3: The Save (Intervention MB at apex)

**Setup**: 6-player endgame raid on Maat (Genkai 5 rematch).
Maat is in `wounded` phase (mood `gruff`). Maat is winding up
his Final Heaven ultimate (5s arena-wide AOE, predicted ~6800
damage on the WHM/RDM back-row).

```
T+0.0  Maat winds up Final Heaven. Audible: "...and this is for me."
       Animation tells: foot plant + hands raised + chi gathering glow.
T+0.0  Critic LLM has been watching. Notes: party using ailment
       chains (Distortion x3 in last 90s). Recommends ultimate.
T+0.5  Visible health: Maat's wing/torso animations show wounded
       stage. Audibly heavy breathing between his lines.
T+1.0  WAR opens chain on Maat: Steel Cyclone (compression).
       Audible: "Skillchain open!" Chain marker on Maat.
T+1.5  NIN signs Hyoton: Ichi (6 seals at sprint speed). Naga-style
       hand-signing visible. Niagara chakra-cyan trails.
T+1.8  NIN seal sequence completes. Hyoton lands.
       Compression + Induration = Distortion (Level 2 water+ice).
       Audible: "Distortion!"
       Element halo on Maat: deep blue concentric rings.
       HP flash to party for 2s — Maat 28%.
T+2.0  WHM is positioned. Reads Maat's Final Heaven cast at 2/5
       complete (3s remaining). Reads the Distortion element halo.
       Decides: cast Cure V on the WHM herself before Final Heaven
       lands. Cure V cast time 5s.
T+2.0  RDM hits Magic Burst with Bind (3-second window after the
       chain). Bind is an ailment spell — 3x amplification.
       Audible: "Magic Burst — Bind! 3x for 30!"
       Maat is bound for ~6 seconds (3x base 2s). His Final
       Heaven cast continues but he can't reposition.
T+2.5  Critic LLM updates: "Party landed Bind ail-burst. Maat's
       mobility neutralized. Ultimate still loaded."
T+3.0  WHM begins Cure V cast (5s, but with Quick Magic + Stoneskin
       cooldown rotation she's targeting a 3.5s effective time).
T+4.0  Maat's Final Heaven still casting. 1.5s remaining.
       Maat audibly: "[strain] ENOUGH..."
T+5.5  Cure V cast lands. Lands within Maat's MB window!
       Audible: "**MAGIC BURST — CURE V!**"
       Element bonus: Distortion is water+ice; not Light. So
       3x amplification not 5x. Still: 3x Cure V on the WHM
       herself = ~7800 HP heal + Regen V for 30s.
T+5.6  Maat's Final Heaven cast completes. Hits the party for
       6800 each. WHM had been at 4500 HP; 7800 heal had
       just landed. WHM survives at 4500 HP again. Other
       party members eat the damage but survive (they had
       Stoneskin + were buffed Regen by RDM dual-cast).
T+5.7  Audible: "Saved us!" "Healer pulled it!"
T+6.0  Critic LLM updates: "WHM Cure V intervention with
       3x amplification. Party impressed. Mood -> contemplative."
T+6.0  Maat audibly: "...skilled. Truly."
T+6.5  WHM unlocks DualCast_Cure for 30s.
T+7.0  Party DPS continues. WHM dual-casts Cure V on tank +
       Cure IV on RDM simultaneously (DualCast active).
T+12.0 Maat at 12% HP. broken stage. Bind expires (was 3x for
       6s = wore off at T+8). Maat regains mobility but at
       very low HP.
T+13.0 Maat audibly (mood contemplative now): "...you've
       earned this."
T+14.0 WAR finishes the kill. Final blow. Maat collapses.
T+14.5 Cinematic plays: defeat sequence. Maat kneels respectfully.
T+15.0 Maat (last line): "Excellent. You've earned the right."
T+15.5 Maat hands the apprentice a Maat's Cap. Reputation +500.
       Mood permanently shifts to `content` toward this player.

NOTABLE: This is the Demoncore endgame combat experience. Every
system fires in concert:
  - Skillchain reading (Distortion close)
  - Element identification from halo color
  - Magic Burst window timing (RDM Bind ail-burst + WHM Cure V)
  - Intervention MB (Cure V landing in window cancels Final Heaven death)
  - Ailment 3x amplification
  - Dual-cast unlock from intervention success
  - Boss critic LLM responding to skill demonstrations
  - Cinematic defeat sequence
  - All this without HP bars, AOE telegraph for enemy spell, or chatbox text.
```

**Systems firing**: every major system in `MASTER_RUNBOOK.md`. This is the showcase scenario for endgame Demoncore combat.

---

## Scenario 4: The Mob-Healer Block (player chain failure)

**Setup**: 4-player party of (PLD, WAR, BLM, WHM) attacking a
Quadav patrol of (3× Quadav Footsoldier + 1× Quadav Healer +
1× Quadav Helmsman) in Beadeaux entrance. The party doesn't yet
know Quadav Healers can intervention-cancel.

```
T+0.0  PLD pulls aggro on Quadav Helmsman with Flash. Fight begins.
T+5.0  WAR builds TP. Audible: "[heavy breathing]" as he closes.
T+8.0  WAR opens chain on Helmsman: Steel Cyclone (compression).
       Audible: "Skillchain open!"
T+8.5  BLM positions for Magic Burst window — plans to nuke
       Blizzard III.
T+9.0  Quadav Healer (off to side) sees the chain marker.
       Quadav Healer's RL policy detects "friendly_skillchain
       _closing" and queues Cure IV intervention. Voice
       callout: "[Yagudo voice — wait, this is Quadav]
       [Quadav healer voice] Cure burst!"
T+9.5  WAR's chain closer lands (Crescent Moon). Closing
       Compression Level 1.
       Niagara halo on Helmsman: desat purple.
T+9.7  Cure IV lands on Helmsman from the Quadav Healer DURING
       the MB window. Intervention succeeds!
T+9.8  Damage cancellation: chain damage to Helmsman is 0.
       3x heal: Helmsman gains 3000 HP (was at 75%, now back
       to ~95%).
       Quadav Healer unlocks DualCast_Cure for 30s.
T+9.9  Audible callouts overlap:
       Quadav Healer: "[triumph cry]"
       BLM (player party): "[snarl] FUCK — too slow!"
       PLD: "Get that healer!"
T+10.0 BLM's planned Blizzard III cast was already started.
       It lands but as a non-MB cast (not in window because
       chain damage was cancelled). Damage: 1200 (vs 1800 if
       MB succeeded).
T+10.5 Party realizes the lesson: kill the healer first.
T+12.0 PLD switches Provoke target to the Quadav Healer.
T+15.0 BLM Magic Burst Silence (an ailment) on the Healer
       during a future chain. Once landed, the 3x silence
       prevents more cures.
T+18.0 Now stack-kill the Helmsman.
T+25.0 Fight ends. Party cleared the patrol.

LESSON LEARNED:
  - Mob healers are real threat actors
  - Audibly identifying the healer (the voice callout was the
    first hint) is the first step to victory
  - Future encounters: party silences healer first,
    THEN chains the boss
```

**Systems firing**: SKILLCHAIN_SYSTEM, INTERVENTION_MB (mob-side!), AUDIBLE_CALLOUTS, AI_WORLD_DENSITY (Tier 4 RL policy)

---

## Scenario 5: The Open World Tense (random encounter)

**Setup**: A lone player at lvl 30 walking through Konschtat
Highlands at night. A pack of Goblin Pickpockets sees them.

```
T+0.0  Player walking. Visible: pristine.
T+1.0  Player enters detection range of Goblin Pickpocket pack
       (3 mobs).
T+1.0  Goblins audibly: "[soft cackle... heh heh!]"
T+1.5  Goblin Pickpocket #1 begins Stealth Approach.
T+3.0  Player's character grunts ambient because they noticed
       a noise (passive perception trigger).
T+5.0  Goblin Pickpocket #1 reaches behind-player position.
       Triggers Pickpocket ability — RL policy chose this because
       target_facing_away = true and player has visible gil pouch.
       Audibly: "[heh heh!] Goblin take!"
T+5.5  Player loses 250 gil. Visible: a tiny "−" particle floats
       from player's belt.
T+6.0  Player notices, turns. Goblin Pickpocket #1 is now visible
       and audibly: "[laugh] Goblin run!" — flees 30m.
T+7.0  Goblin Pickpockets #2 and #3 emerge from shadows. Engage.
T+7.5  Player audibly battle-cry. Combat begins.
T+10.0 Player kills #2 with a clean weapon skill.
       Audible: "[grunt of effort]" + opens skillchain marker.
T+12.0 Player closes Level 1 Liquefaction with a fire attack.
       Niagara halo: orange.
T+12.5 Audible: "Closing — Liquefaction!"
T+13.0 Goblin #3 sees the chain. Mood -> fearful.
       Audible: "[whimper, Goblin run!]"
T+14.0 #3 attempts to flee. Player gets last hit.
T+15.0 Combat ends. Player audibly: "[satisfied breath]"
       Mood: content.
T+15.5 Player checks belt — recovered 200 gil from #2 corpse.
       Net: -50 gil from the encounter.

REWARDS:
  - Combat XP gained (small — player out-leveled mobs)
  - Liquefaction skillchain mastery exp
  - "Goblin Knowledge" reputation increment
  - Pickpocket #1 escaped — that goblin is now "remembered"
    by the orchestrator. Next encounter, that specific goblin
    knows the player's gear silhouette.
```

**Systems firing**: AI_WORLD_DENSITY (Tier 4 RL pickpocket behavior), MOOD_SYSTEM (mob fear at chain), AUDIBLE_CALLOUTS, SKILLCHAIN_SYSTEM (open world chain), and an ambient open-world hostile encounter.

---

## What these scenarios prove

1. **Every system composes** — no scenario fires only one system. Combat
   reads as a unified language because the systems are designed to
   compose, not to layer.
2. **No HP bars or chatbox** — the player's experience in every
   scenario is mediated by visible cues (animations, decals, particle
   effects) and audible cues (callouts, grunts, voice tones).
3. **Mob-side symmetry is real** — Scenario 4 demonstrates that mob
   healers using the intervention MB mechanic against the player
   creates legitimate strategic depth, not asymmetric "bosses cheat".
4. **Player progression is observable** — Scenario 2 shows mastery
   exp gains; Scenario 3 shows the apex behavior of dual-cast unlock
   + critic LLM responses.
5. **The world breathes outside combat** — Scenario 5 shows ambient
   pickpocket behavior without scripted spawn points.

---

## Status

- [x] 5 worked scenarios authored
- [ ] First playtest: Scenario 1 (Naga vs lvl-25 BLM) — verify seal
      sequence visibility + sprint-pursuit behavior
- [ ] Scenario 2 in tutorial zone — verify the audible callouts +
      first-chain detonation
- [ ] Scenario 3 endgame Maat — full system showcase
- [ ] Scenario 4 Quadav patrol — verify mob-side intervention works
      both client + server side
- [ ] Scenario 5 random encounter — verify pickpocket RL policy
      behavior
- [ ] Video capture of each scenario for marketing + design review
