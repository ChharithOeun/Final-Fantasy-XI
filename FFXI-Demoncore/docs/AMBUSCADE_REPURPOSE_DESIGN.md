# Ambuscade Repurpose System

*Design doc for: Tier-VI magic, item-level ceiling revamp, Synergy
Workbench (Escutcheon-gated group craft), and the Ambuscade
upgrade recipe ladder that turns every old piece of gear back
into a meaningful drop.*

## Problem statement

Three problems become acute at the new ML 100-150 cap:

1. **Magic ceiling.** Cure V, Fire IV, Stone V, Cura III etc. were
   tuned for a level-99 economy. A level-150 RDM nuking with Fire
   IV looks anemic. We need a higher tier of magic that scales
   with the new HP/MP and stat bumps Master Levels grant.

2. **Item-level ceiling.** Canonical FFXI's i-lvl system locks
   gear at i-lvl 119 over a level 99 character (a +20 effective-
   level bump). At level 150 that ceiling is irrelevant — the
   player's own stats already exceed what i-lvl 119 represents.
   Without a fix, ML players just wear their lvl-99 gear forever
   and the upgrade economy stalls.

3. **Dead gear.** Hundreds of items dropped from old NMs, ENMs,
   and quests are completely unfarmed. New characters skip them
   on the way to the canonical i-lvl meta. We want to reanimate
   that content — make every existing piece of gear matter again
   by giving it a purpose in the new craft economy.

## Four systems

We solve this with four cooperating systems. Each can ship as its
own module or pair of modules.

### System 1 — Tier-VI / Shadow magic

A new spell tier appropriate for ML 100-150 casters.

* Cure VI, Curaga V, Fire V, Blizzard V, Thunder V, Stone V,
  Aero V, Water V, Holy II, Banishga III, Bio IV, Dia IV
* Each tier-VI spell is a scroll dropped (R/EX) by Shadow Genkai
  bosses or rare Fomor mobs in shadow zones
* Scaling: tier-VI base damage / cure potency is tuned so that
  a lvl 150 caster with their full ML stat bonus can land
  numbers proportional to a lvl 75 caster casting Cure V — the
  shape of the curve stays familiar
* Skill-cap dependency: tier-VI spells require post-99 skill
  points that only ML can provide (skill cap +5 per ML)

**Suggested module:** extend `server/spell_catalog/` with a
`TIER_VI` family enum and 12-15 sample scrolls.

### System 2 — Item-level ceiling = level + 25

Replace the hardcoded i-lvl 119 ceiling with a **level-relative
ceiling**.

| Player level | i-lvl ceiling |
|---|---|
| 75 | (n/a — pre-iLvl era) |
| 99 | 124 |
| 100 | 125 |
| 125 | 150 |
| 150 | **175** |

The ceiling is the **average** of equipped i-lvls — same averaging
math the canonical system uses, just with a moving cap. A piece
of gear at i-lvl 175 in one slot can be carried by lower-i-lvl
gear in other slots, exactly like canonical i-lvl behaves today.

**Why +25 specifically:** matches the canonical +20 differential
players are already used to (lvl 99 → i-lvl 119) with a small
buffer. Easier to tune monsters around than an arbitrary new
formula.

**Suggested module:** extend `server/equipment_stats/` with a
`level_relative_ceiling(player_level)` helper and revisit any
hardcoded i-lvl 119 references.

### System 3 — Synergy Workbench (group craft, Escutcheon-gated)

The crafting machine that turns recipe slips + raw inputs into
upgraded ambuscade pieces.

**Inputs the machine pulls from anywhere on the player(s):**
* Mog Safe / Mog Safe 2
* Mog Locker (rented foreign storage)
* Mog Wardrobe 1-4
* Mog Slip storage (canonical FFXI slip-stored gear)
* Storage Slip / NPC slip storage
* Active inventory (held)
* Optional: party members' inventories — a member can volunteer
  their pieces to the synth without trading them first

**Hard requirements:**
* A **Recipe Slip** (R/EX) loaded into the slot
* At least one participating crafter must have an **Escutcheon**
  shield equipped (the PLD/RUN trial chain we built earlier)
* All input materials must be present somewhere accessible

**Group dynamic:**
* 1-6 players can contribute. More players raise the
  "synergy charge" — more charge → higher final stat roll
* Lead crafter (with the Escutcheon) drives the synth and gets
  the output piece in their inventory; non-leads contribute
  and earn JP / craft skill XP
* Real synergy on a real workbench is canonical FFXI; this is
  the same UX, just generalized

**Solo / no-Escutcheon bypass — NPC Master Crafter:**
* Available in capital cities for a steep gil cost
* No shield requirement, no party requirement
* Slower turn-around (synth resolves over real-time, e.g. 30
  minutes per i-lvl tier — the NPC is "working on it")
* Lower max stat roll (NPC craft caps at +0 quality — so you
  get the piece but not the +N variants from solo NPC route)
* Designed for: solo players, players whose mains have died
  and are running a fresh alt, players whose linkshell is
  thin

**Suggested modules:**
* `server/synergy_workbench/` — the machine, recipe slot,
  multi-source material gather, group charge, NPC bypass
* `server/recipe_slip_registry/` — slip catalog, drop sources,
  decode rules

### System 4 — Ambuscade Repurpose recipe ladder

The actual catalog of upgrades. Each piece of gear in the game
flows into a corresponding ambuscade-tier piece.

**Two-axis upgrade grid per piece:**
* **i-lvl tier** (T0 - T11) — twelve i-lvl steps from 120 to 175
  in +5 increments. Each tier costs a fresh recipe slip + input
  bundle. Stages T0-T4 consume **old gear** (lvl 99 to i-lvl 119
  brackets); stages T5-T11 consume **new R/EX drops** from ML
  100-150 content.
* **Quality tier** (NQ → +1 → +2 → +3 → +4) — cosmetic + stat
  bump. Each quality bump consumes a separate R/EX bundle from
  high-tier content. Quality is independent of i-lvl tier;
  upgrade either axis at any time.

**i-lvl ladder example for "ambuscade head, RDM":**

| Tier | Output i-lvl | Input requires |
|---|---|---|
| T0 | 120 | One lvl-99 RDM-eligible head + slip + base mats |
| T1 | 125 | One i-lvl 100-104 RDM-eligible head + slip + mats |
| T2 | 130 | One i-lvl 105-109 RDM-eligible head + slip + mats |
| T3 | 135 | One i-lvl 110-114 RDM-eligible head + slip + mats |
| T4 | 140 | One i-lvl 115-119 RDM-eligible head + slip + mats |
| T5 | 145 | Shadow Genkai T1 (Khaa'Vex) drops + slip |
| T6 | 150 | Shadow Genkai T2 (Zharzag) drops + slip |
| T7 | 155 | Shadow Genkai T3 (Mor'rho) drops + slip |
| T8 | 160 | Shadow Genkai T4 (Skhal'ya) drops + slip |
| T9 | 165 | Shadow Genkai T5 (Tro'Khaeb) drops + slip |
| T10 | 170 | Shadow Genkai T6 (Kael Nox) drops + slip |
| T11 | 175 | Shadow Genkai T7+ (Ssylvyrr / Mok'tor / Hriath / Asmodeus) drops + slip |

**Why this shape works:**
* T0-T4 (the "old gear consumption" half) reanimates every
  existing 99 → 119 piece. Players will farm Salvage, Voidwatch,
  Sky/Sea, Adoulin content again because that gear becomes
  craft-fodder.
* T5-T11 ride the Shadow Genkai chain we already have. The
  same bosses that gate the level cap also drop the materials
  for the i-lvl ladder. Single content stream serves both
  purposes — efficient design.
* Quality tier (+1 → +4) sits orthogonal to i-lvl. A min-maxer
  who wants stats but doesn't have ML 50 can grind T6 +4
  before grinding T11 +0.

**Output piece is always "Ambuscade [slot]"** — same name
regardless of input job. The piece has slot-specific stats but
also carries:
* Job-restriction inherited from the highest-i-lvl input piece
  used in T0 (the seed)
* Stat profile that adapts to the equipping job at use time
  (so a Resolute Ambuscade Head adapts WAR-flavored vs RDM-
  flavored stats based on who wears it)

**Excluded from input pool:**
* Relic, Empyrean, Mythic, Aeonic, Ergon, Prime weapons & armor
* Existing ambuscade R/EX pieces from canonical FFXI content
  (those are separate progression)

These get their own future progression system.

## Data shapes (sketch)

```python
class RecipeSlip:
    slip_id: str               # 'rdm_head_t0_slip' etc.
    slot: ItemSlot             # head / body / hands / legs / feet / etc.
    job_filter: tuple[JobId, ...]   # which jobs this output equips
    target_tier: int           # 0 - 11
    target_ilvl: int           # 120, 125, ... 175
    input_bracket: tuple[int, int]  # i-lvl bracket of consumed gear
    bonus_materials: tuple[str, ...]  # ('elemental_cluster_x4', ...)
    is_quality_recipe: bool    # False for i-lvl ladder, True for +N

class AmbuscadePiece:
    piece_id: str              # 'ambuscade_rdm_head_<id>'
    slot: ItemSlot
    base_job: JobId
    ilvl_tier: int             # 0..11
    quality: int               # 0..4
    @property
    def ilvl(self) -> int: return 120 + 5 * self.ilvl_tier
    @property
    def stat_block(self) -> dict[str, int]: ...

class SynergyWorkbenchSession:
    lead_player_id: str
    contributors: tuple[str, ...]
    slip_loaded: Optional[str]
    bench_zone: str
    has_escutcheon_equipped: bool
    materials_gathered: dict[str, int]
    npc_assist: Optional[str]   # which NPC crafter is bypassing

class NpcCrafterBypass:
    npc_id: str
    zone: str
    base_gil_cost: int
    quality_cap: int = 0       # NPC bypass only makes NQ pieces
    real_time_seconds_per_tier: int = 30 * 60
```

## Open decisions

Before code lands, lock these in. None of them are blocking
forever — we can take a default and revisit — but some have
big downstream effects.

**D1. Tier-VI naming.** "Tier VI" is functional but boring. Call it
"Shadow magic" to match Shadow Genkai? "Master tier"? Something
fresh? *Default: keep "Tier VI" until you have a flavor name.*

**D2. T5-T11 input source.** Is each tier locked to a specific
Shadow Genkai boss's drops, or is there a shared "shadow
fragment" currency that all the bosses drop at varying rates?
*Recommendation: shared shadow fragments + boss-specific
"signature shards" required at certain tiers. Lets every
boss feel rewarding without forcing one specific kill chain.*

**D3. Quality (+N) materials.** Do +1 through +4 use the same
material, just more of it? Or distinct materials per quality
tier? *Default: tiered. +1 needs Common Shadow Sigils, +4 needs
Pristine Sigils. More farmable variety, more economy depth.*

**D4. Solo NPC bypass cap.** Is the NPC capped at NQ output
forever, or can they reach +1/+2 with steeper gil cost?
*Recommendation: NPC caps at NQ. Forces players who want max
stats to engage with the group-craft system or eventually find
a partner. Solo players still have a viable path; min-maxers
have a reason to socialize.*

**D5. Recipe slip drop rates.** Where exactly do recipe slips
drop, and at what rate? *Recommendation: each Shadow Genkai
boss drops 1 random slip at ~3% rate, plus high-end Fomor
trash mobs drop common slips at ~0.5%. Gives both casual and
focused farmers a path.*

**D6. Are old-content drops still valuable for things other
than ambuscade craft?** Salvage gear, Sea cards, etc. — do
they retain their original use, or get fully consumed by the
ladder? *Recommendation: keep canonical use AND make them
ladder fodder. Don't double-destroy the existing economy.*

**D7. Per-job vs per-archetype recipes.** RDM head, BLM head,
WHM head — do they share a slip, or three separate slips?
*Recommendation: archetype-bundled slips ("Caster Head Slip
T0" works for RDM/BLM/WHM/SCH/SMN/BRD), with a few job-locked
slips for outliers like PUP and BST. Cuts the recipe count
dramatically without losing flavor.*

**D8. Recipe coverage tooling.** Do we want a validator script
that loads every existing piece in the game and confirms each
maps to at least one recipe? *Recommendation: yes — this is
the kind of thing a 30-line Python script catches that a
human review would miss. Worth building once.*

## Proposed build order

This is a 6-7 chunk slice across two ship batches. Hold off on
the wiki-level data authoring until the engine works and you've
locked decisions D1-D8.

**Batch A — engine (5 modules, fits one ship batch):**
1. `server/spell_catalog/` extension — Tier-VI scrolls
2. `server/equipment_stats/` extension — level-relative i-lvl
   ceiling (`level + 25`)
3. `server/recipe_slip_registry/` — slip catalog + drop source
   spec
4. `server/synergy_workbench/` — machine, multi-source material
   gather, group charge, NPC bypass
5. `server/ambuscade_progression/` — per-player per-piece
   tier+quality tracker, upgrade attempt logic, output stat
   computation

**Batch B — content + tooling (3-5 chunks):**
6. Sample recipe data: 1 slot × 3 archetypes (caster/melee/
   ranger) × all 12 i-lvl tiers + 4 quality tiers — enough
   to prove the system end-to-end
7. Recipe coverage validator script — surfaces unmapped old
   gear
8. Wiki-format recipe chart export — generates a markdown
   table from the recipe catalog (drives data authoring later)
9. NPC Master Crafter NPC YAMLs (3-4 craft NPCs, one per
   nation)
10. Integration test — a full run from "RDM head lvl 99
    drops" through "T11 +4 Ambuscade Head equipped at i-lvl
    175"

## What I need from you

Pick a path forward:

**A — Lock decisions then build.** Answer (or ratify defaults
on) D1-D8 above and I'll start Batch A immediately.

**B — Build with defaults, iterate.** I take the recommended
defaults on every decision, ship Batch A, and you correct
course on the implementation when you see it running.

**C — Discuss further first.** Some part of the design above
doesn't feel right and we should keep talking before code
lands.

I think **option B** is the right move — the recommended
defaults are conservative and any of them is reversible in a
single chunk if you don't like them once you see them in
action. But it's your call.

---

*Coming after this system: lvl 200 cap and our own expansion
(new shadow zones, fresh boss content, new NPC casts). We are
intentionally NOT designing that here — finishing 150 first.*
