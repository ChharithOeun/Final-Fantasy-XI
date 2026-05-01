# PVP_SCENARIOS.md

Worked PvP combat playtests demonstrating Demoncore's outlaw +
nation-vs-nation systems firing in concert. Sister doc to
`MAGIC_BURST_SCENARIOS.md` (PvE worked examples). Each scenario
walks frame-by-frame through a real outlaw fight and shows which
systems compose with what audible/visual outcomes.

These are the playtest scripts for the first end-to-end PvP trials.

Composes with:
- `PVP_GLOBAL_OUTLAWS.md` — outlaw bounty + safe-haven mechanics
- `HONOR_REPUTATION.md` — dual-gauge moral standing
- `WEIGHT_PHYSICS.md` — weight reads via /check on opponent
- `INTERVENTION_MB.md` — symmetric defensive saves
- `SEAMLESS_WORLD.md` — cross-zone pursuit between players
- `EQUIPMENT_WEAR.md` — death penalty durability hit
- `SKILLCHAIN_SYSTEM.md` — chains work in PvP same as PvE

---

## Scenario 1: First Outlaw Kill (cross-faction PvP)

**Setup**: Bastokan WAR Alice (lvl 70, +2000 honor, +500 Bastok rep)
encounters Sandyrian PLD Borgan (lvl 72, neutral) in Konschtat
Highlands. Borgan is on a quest delivery; Alice is xp-farming Orcs.
Konschtat is open-PvP territory between Bastok + Sandy.

```
T+0.0  Alice and Borgan spot each other across the highland.
       Alice /checks Borgan: "Tough; (seems alert); (unharmed)"
       Audible: ambient highland wind, no music.
T+0.5  Alice's mood goes alert. Audibly grunts in commitment.
       She decides to engage. Sandy player on Bastok soil —
       cross-faction PvP per PVP_GLOBAL_OUTLAWS.md, no Honor cost.
T+1.0  Alice charges. Weight 95 (mythril plate + Curtana = 22+14
       gear). Movement multiplier 0.55x base (per WEIGHT_PHYSICS).
       Borgan's player /checks Alice in return — sees the gear
       weight bucket "heavy".
T+2.0  Borgan reads the closing WAR weight + sees the Curtana.
       Decides he can't outrun. Pops Flash (binding light).
       Audibly: "FLASH BURST!" (intervention enmity spike).
T+2.5  Alice's WAR melee swing windup begins. She's in stationary
       posture for the swing — eligible for the +14 stationary
       accuracy bonus on Curtana (per WEIGHT_PHYSICS Formula 4).
       Borgan, anticipating, casts Stoneskin (1.5s vocal cast).
T+4.0  Alice's swing connects: Crescent Moon (compression).
       Damage 580 raw; Curtana stationary +14 acc; lands.
       Audible: "Skillchain open!"
T+4.2  Borgan's Stoneskin completes. Absorbs 380 of next hit.
T+5.0  Alice swings again — auto-attack, no chain. 280 dmg.
       Stoneskin absorbs all of it.
T+6.0  Alice's TP refill. Tries Hexa Strike (transfixion).
       Compression + Transfixion = Transfixion L1 chain!
       Audible: "Closing — Transfixion!"
       White flash on Borgan; Niagara light halo.
       HP-flash visible to whole party (per VISUAL_HEALTH_SYSTEM).
       Borgan visible HP: 65%
T+6.5  Borgan reads the chain element — Transfixion (light).
       His MP is full. Casts Banish (light direct-damage spell)
       in the Magic Burst window.
T+8.0  Banish lands during MB window: 1.5x base × 1.0 element
       match (light on light) = mb factor 1.50. Damage to
       boss (would have been Alice if Borgan were attacker).
       Wait — Borgan is the target, not the attacker. He can
       only intervention-cast not MB.
T+8.0  CORRECTION: Borgan's a defender. He casts Cure IV
       on himself in the MB window — Intervention Cure!
       Audible: "Magic Burst — Cure IV!"
       3x amplification: heals 1800 HP (vs 600 base) + Regen 30s.
       Borgan unlocks dual-cast Cures for 30s.
T+8.2  Alice grunts in frustration. Her chain just got
       intervention-cancelled by an opponent's defensive cast.
       This is the symmetric jazz: PvP intervention-MB exists.
T+9.0  Alice changes strategy — she'll burst rather than chain.
       Pops Berserk (job ability, +20% atk -20% def).
T+10.0 Borgan dual-casts Cure III on himself + Reraise (just
       in case). Audible: "Plus one cure! Reraise loaded!"
T+12.0 Alice gets Asuran Fists WS off — heavy hit, no chain.
       Borgan at 70% HP after Cure III + Asuran Fists.
T+15.0 Sustained slugging. Alice at 50%, Borgan at 35%.
T+18.0 Alice triggers another chain attempt: Steel Cyclone
       (compression). Audible: "Skillchain open!"
T+19.0 Borgan, in dual-cast mode, casts Sleep on Alice. 1.5s cast.
T+20.5 Sleep lands. Alice slept.
       Borgan's mood goes content. Audible: "Sleep landed!"
T+21.0 Borgan walks 10m away. Out of Alice's defensive range.
T+22.0 Borgan casts Cure V (5s cast). His mastery is high; cast
       times shortened. Self-heal 2400 HP. Back to 95%.
T+27.0 Alice wakes from Sleep. Weight is on her — she's slow.
T+28.0 Borgan opens his own chain: Spirits Within (transfixion).
       Audible: "Skillchain open!"
T+29.0 Alice in scuffed phase. She has TP for Steel Cyclone but
       it doesn't combo with Transfixion well. She auto-attacks.
T+30.0 Borgan's chain expires (no closer). He's at 95% HP and
       Alice at 50%. He's winning the war of attrition.
T+35.0 Alice realizes she's losing. Tries to disengage by
       running back to Bastok side. But Borgan is on her —
       sensory aggro applies even though he's a player.
       Note: SEAMLESS_WORLD.md cross-zone pursuit applies to
       PvP too. Alice can outrun if she escapes sight + sound +
       smell. She has Sneak gear; pops Sneak.
T+36.0 Alice's Sneak: -10x sound. Borgan's sight is still on her.
T+37.0 Alice rounds a hill, breaks sight. Sound is dampened.
       Smell isn't a factor (Borgan is a hume, not a wolf).
       Per SEAMLESS_WORLD: persistence_seconds (45s for AGGRESSIVE).
T+50.0 At 13 seconds after losing sight. Borgan's aggro state
       still aggressive. Alice keeps running.
T+82.0 At 45 seconds since sight lost. Borgan deaggros.
       Audible: "Tch. Out of range." Mood -> gruff.
T+90.0 Alice escapes. Outlaw bounty: this was a fair PvP
       cross-faction encounter, no bounty applied.

OUTCOME:
  - Borgan won. Alice fled with 50% HP + minor gear damage.
  - No outlaw bounty for either side (cross-faction PvP, fair zone).
  - Alice +5 reputation in Bastok for "engaged Sandyrian fighter"
  - Borgan +5 reputation in Sandy for "defended himself successfully"

LESSON: PvP chains can be intervention-cancelled by the OPPONENT.
The 3x ailment/heal mechanic works symmetrically. Sleep + heal-up
is a viable defensive PLD strategy. Sneak gear actually helps
escape — sensory exit applies in PvP too.
```

**Systems firing**: SKILLCHAIN, INTERVENTION_MB (defensive cast),
WEIGHT_PHYSICS, AOE_TELEGRAPH (player-side preview), VISUAL_HEALTH,
AUDIBLE_CALLOUTS, SEAMLESS_WORLD aggro persistence, PVP_GLOBAL_OUTLAWS
fair-zone rules.

---

## Scenario 2: Outlawed (Same-Faction Kill in Bastok)

**Setup**: Bastokan THF Mavi (lvl 60, +800 honor) ambushes Bastokan
WHM Cornwall (lvl 55, +500 honor) in Bastok Mines. Same nation =
outlaw kill per `PVP_GLOBAL_OUTLAWS.md`. Mavi is committing
faction-crime.

```
T+0.0  Mavi spots Cornwall in a quiet mine corridor. No witnesses.
T+0.5  Mavi pops Hide + Sneak Attack. Crit chance 100% from behind.
T+1.0  Backstab. Cornwall takes 2400 damage (back-shot crit).
       Cornwall at 60% HP from full.
T+2.0  Mavi grunts in commitment. No skillchain opener — just burst.
T+2.5  Cornwall whips around. Sees Bastokan colors on Mavi's
       cloak. Confused — same nation. Audible: "What?!"
T+3.0  Cornwall starts Cure IV cast (3.5s).
T+3.5  Mavi pops Mug. THF guarantee from SA prep: reveals Cornwall's
       HP for 3 seconds.
T+4.0  Mavi sees Cornwall at 60%. Decides full burst.
       Trick Attack + auto-attack chain. 1800 damage.
T+5.0  Cornwall finishes Cure IV. Heals 1100 HP. At 75%.
       Cornwall starts Banishga (light AOE).
T+6.0  Mavi's mood furious — Cornwall didn't die fast enough.
T+7.0  Banishga lands. Mavi takes 800 damage. 60% HP.
T+8.0  Mavi closes in for melee. Cornwall casts Holy on her.
       400 damage; Mavi at 50%.
T+9.0  Mavi WS Mercy Stroke (compression). 700 damage.
       Cornwall at 50%.
T+10.0 Cornwall WS Brainshaker (impaction). Compression+impaction
       doesn't combo. No chain. But damage: 600. Mavi at 35%.
T+12.0 Mavi pops Flee (THF 60s ability, -90% effective weight).
       Audible: "Flee active!"
       Mavi runs at 1.4x speed.
T+13.0 Cornwall casts Bind (water-element). Lands. Mavi rooted.
T+14.0 Cornwall casts Banish III (3s cast time). Hits. Mavi at 8%.
T+17.0 Mavi WS Last Breath (free); 800 dmg; Cornwall at 30%.
T+18.0 Cornwall finishes Cure IV. Self heal. At 60%.
T+19.0 Mavi at 8%, bound, exposed. Cornwall casts Banish IV.
       Mavi dies.

OUTCOME:
  - Mavi killed. Same-nation kill = OUTLAW status applied.
  - Mavi's bounty: 5 million gil (per PVP_GLOBAL_OUTLAWS first
    same-nation kill scaling).
  - Mavi's Honor: -2000 (immediate).
  - Mavi's Bastok reputation: -1500.
  - Mavi forced out of all 3 nation safe havens (Bastok/Sandy/Windy)
    after 48 hours of no pardon-quest progress.
  - Norg becomes Mavi's only safe sanctuary.
  - Mavi's death is at lvl 60 — standard tier; she loses 1 level
    + 25% gear durability + dies in Bastok Mines.
  - Cornwall gains +500 reputation for "defended self vs outlaw" +
    +1000 honor for the outlaw-defense.

LESSON: Same-nation PvP is HUGELY costly. The Mavi player who tried
this loses millions of gil + a level + a faction. Outlawing is
deliberately punitive per HONOR_REPUTATION + PVP_GLOBAL_OUTLAWS.
Norg becomes her new home until pardon quests grind down the bounty.
```

---

## Scenario 3: Outlaw Pardon Run (the redemption arc)

**Setup**: Mavi (now outlaw, 5M gil bounty, -1500 Bastok rep) wants
back into Bastok. The pardon-quest path requires:
- Pay 5M gil to a master NPC (in this case Maat at the mountain)
- OR complete 16 outlaw-pardon quests + retain >0 honor

She has 200K gil saved. So the gil path is closed; she has to grind
the quest path.

```
DAY 1
  Mavi visits Yorisha in Norg. "Captain. I need pardon-quest leads."
  Yorisha: "Outlaw, eh? I can use someone like you. Three jobs, in
           order. Each pays in pardon-quest progress, not gil.
           Want them?"
  Mavi: "Take them."

  Quest 1: "Sneak into Bastok Mines, recover a Mythril Sword from
           the smithy backroom, return to Norg. Don't kill anyone."
  Mavi must use Sneak + Hide + careful timing to avoid Bastok
  guards. She succeeds. +1 pardon progress (1/16).

  Mavi's mood: gruff (frustrated by the grind). NPCs in Norg
  audibly note her: "...Outlaw with a story. Watch yourself."

DAY 2-7
  Mavi runs more pardon quests. Each completes adds 1-2 progress.
  She gets to 8/16 by day 7.

DAY 7
  An emergency: Beastman raid alarm in Bastok. Mavi is in Norg.
  She CAN go help defend Bastok — outlaws CAN engage non-civic mobs.
  She does. Kills 4 Quadav defending the gate. Earns +500 reputation
  back to Bastok and +2 pardon progress for the defense.

DAY 14
  Mavi at 14/16 pardon. Her last 2 quests are escort missions —
  longer + more dangerous. She finishes them.

  Final ceremony: Mavi presents to Volker in Bastok at the
  Republican Council. Voice-cloned Volker says: "Adventurer Mavi.
  The Republic acknowledges your debt is paid. Welcome back."
  Mavi's outlaw status removed. Honor restored to 0 (neutral).
  Bastok reputation restored to -500 (still earning it back).

  Mavi can re-enter all safe havens. Her bounty is cleared.
  Cornwall still hates her, but the system doesn't.

LESSON: The pardon path EXISTS but is expensive. ~14 game-days of
focused quest-grinding. Most casual outlaw players give up after 5-7
days. The system is calibrated so outlawing is regretted. The
players who PERSEVERE through pardon quests come out as legitimate
characters who earned their place back.
```

---

## Scenario 4: Nation-vs-Nation Skirmish at the Border

**Setup**: 6-player Bastok party (DRK + WAR + SCH + WHM + RDM + BLM)
encounters 6-player Sandy party of similar comp at the Vollbow
Mountains border between Konschtat and Ronfaure West. Open-PvP
border zone.

```
T+0.0  Both parties spot each other. Mood across both: alert.
       No engagement yet — territorial standoff.
T+5.0  Bastok DRK shouts "FOR BASTOK!" Audible. Both parties
       re-position into combat formations.
T+10.0 Bastok BLM begins Sleep AOE (3.5s cast).
T+12.0 Sandy SCH lands Helix DoT on Bastok BLM during her cast.
       BLM takes interrupt damage (Helix is dot). Cast survives.
T+13.0 Bastok BLM Sleep AOE lands. Sandy DRK + WHM sleep.
T+14.0 Sandy RDM casts Erase on the WHM. Wakes the WHM.
T+15.0 Sandy WHM Cure V on the SCH (whose Helix is still
       running on BLM). SCH at full.
T+18.0 Bastok WAR opens chain on Sandy DRK with Steel Cyclone
       (compression). Audible: "Skillchain open!"
T+19.5 Bastok DRK closes with Spinning Slash (impaction).
       Compression + Impaction doesn't combo (per LEVEL_1_TABLE).
       No chain. Audible grunt of frustration.
T+20.0 Sandy DRK wakes. Mood furious. Charges Bastok WAR.
T+22.0 Bastok WHM casts Cure IV on Bastok WAR (mid-combat heal).
T+24.0 Sandy BLM casts Sleep II on Bastok WHM (3s cast).
T+27.0 Sandy BLM Sleep II lands. Bastok WHM sleeps.
T+28.0 Now Sandy presses. Bastok WAR low HP, no healer awake.
T+30.0 Bastok BLM races Cure cast on the WAR. Sandy DRK
       interrupts BLM with WS knockback.
T+33.0 Bastok WAR dies. Sandy gets first kill of the skirmish.
       Per cross-faction PvP no Honor cost.
T+35.0 Bastok loses two more in quick succession.
T+45.0 Bastok SCH still up + RDM still up. They commit to
       chain: SCH lands Compression, RDM closes with Detonation.
       Chain: Compression + Detonation = Detonation L1!
       Audible: "Detonation!"
T+47.0 Bastok BLM in MB window casts Aero IV (wind = light overlap).
       Element_match for Aero on Detonation = 1.0 exact.
       MB damage: 850 × 1.5 (L1 MB) × 1.0 (match) × 1.15 (stationary)
       = 1465.
       Sandy DRK at 60% pre, 35% after Aero IV MB.
T+50.0 Sandy WHM intervention-cures the DRK.
       Audible: "Magic Burst — Cure V!"
       3x amp: 1800 HP heal + Regen 30s. DRK back to 80%.
T+52.0 Bastok BLM angry. "They cancelled my chain!"
T+55.0 Sandy WHM dual-cast Cures unlock for 30s. Major HPS spike.
T+60.0 Sandy presses + finishes off Bastok survivors.

OUTCOME:
  - Sandy 6-0 victory.
  - Both nations gain reputation gain for the engagement.
  - 6 cross-faction kills, no Honor cost on either side.
  - Bastok party's Honor: +20 each for fighting bravely
  - Sandy party's reputation: +50 each for the win

LESSON: Cross-faction nation-vs-nation skirmishes are real wars.
Skillchain + intervention dynamics work the same in 6v6 as in 1v1.
The 6 Sandy players coordinated; the Bastok side didn't pop their
own chain until too late. Coordination wins.
```

---

## Scenario 5: The Cross-Zone Outlaw Hunt

**Setup**: Bastok bounty hunter Garron (lvl 75 PLD, official
deputized) hunts outlaw Mavi (lvl 60 THF, +5M gil bounty open).
Mavi is hiding in Outer Horutoto Ruins.

```
T+0.0  Garron reaches Outer Horutoto entrance. Pops a Bounty Glass
       quest item — reveals Mavi's location on his minimap.
       Garron's mood is alert.
T+3.0  Garron tracks Mavi to a back chamber.
T+5.0  Mavi spotted Garron entering. Pops Hide + Sneak.
       Sound dampening x10. Sight blocked.
T+7.0  Garron checks the chamber. Doesn't see Mavi.
       His sight perception fails. But he has a Tracking
       enchantment on his shield — a smell-equivalent that
       senses outlaw status within 30m.
T+8.0  Tracking proc: "Outlaw scent NW!"
T+10.0 Garron walks NW. Mavi runs SE.
T+13.0 Mavi exits the room into Tahrongi Canyon zone.
       Per SEAMLESS_WORLD: cross-zone pursuit.
       Garron's Tracking persists across zone boundary.
T+18.0 Mavi tries to lose the trail. Pops a Deodorize-equivalent
       outlaw item (-Cologne). Tracking dampened by 50%.
T+22.0 Garron's trail is harder to follow. He continues by sight.
T+30.0 Mavi reaches Tahrongi mountain pass. Cliff jump → Buburimu
       Peninsula. Cross-zone again.
T+35.0 Garron persists. His mood enraged at 5M bounty target
       fleeing through 3 zones now.
T+45.0 Mavi turns and engages — last stand. She knows she'll
       lose normal combat but has one trick.
T+46.0 Mavi pops a "Dispel" scroll on Garron. Removes his
       Tracking enchantment. Now he can only see normally.
T+48.0 Mavi pops Hide + sprints away. Sight broken.
T+50.0 Garron's senses fail. Per SEAMLESS_WORLD aggression-state
       persistence: 45s for AGGRESSIVE. He's chasing.
T+95.0 45s after sight loss. Garron's pursuit timer expires.
       Audible: "She got away. Hmph."
T+96.0 Mavi escapes. Bounty unclaimed this run.

OUTCOME:
  - Garron returns empty-handed to Bastok. Reputation hit -10.
  - Mavi survives — but her bounty grows during the chase
    (each minute of pursuit + 100K gil).
  - Mavi at 5.5M bounty now. Closer to forced-into-Norg.

LESSON: Cross-zone bounty hunting works mechanically. The
combination of Tracking + Hide + Deodorize + sensory loss creates
a real cat-and-mouse dynamic.
```

---

## Status

- [x] 5 worked PvP scenarios
- [ ] First playtest: Scenario 2 (same-faction Backstab on
      Cornwall) — verify outlaw status applies + bounty fires
- [ ] Scenario 3 pardon-quest path — full 14-day playtest
      with quest list + Yorisha dialog
- [ ] Scenario 4 6v6 skirmish — coordinate two playtest groups
- [ ] Scenario 5 cross-zone bounty hunt — verify Tracking +
      Hide + sensory loss interaction
- [ ] Video capture of each scenario for marketing
