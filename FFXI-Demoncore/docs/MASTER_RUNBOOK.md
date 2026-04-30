# MASTER RUNBOOK — FFXI Demoncore

The single page that says: which batch / script do I run, and in what order.

Everything Demoncore-related runs from one of two roots:
- `F:\ffxi\stage-monorepo\` — staging ground for batches and design docs
- `F:\ChharithOeun\Final-Fantasy-XI\` — the actual monorepo (Demoncore project + repos)

---

## Phase 0 — Make sure your tools are real (one-time, ~1 hour)

```
F:\ffxi\stage-monorepo\INVENTORY_TOOLS.bat
```
Surveys `repos/` and reports which open-source tools are cloned.
For anything missing, the report includes the exact `git clone` URL.
Run the missing clones, then re-run `INVENTORY_TOOLS.bat`.

```
F:\ffxi\stage-monorepo\CHECK_VS2022.bat
```
Verifies Visual Studio 2022 + the C++ workloads are installed.
If it reports MISSING, run `INSTALL_VS2022.bat` and wait ~45 min.

```
F:\ffxi\stage-monorepo\INSTALL_DEMONCORE_PLUGINS.bat
```
Copies KawaiiPhysics into `demoncore/Plugins/`, enables 14 plugins
(Python, EditorScripting, Sequencer, KawaiiPhysics, LiveLink, VirtualCamera,
VPUtilities, Takes, Recorder, Niagara, Water, Bridge, NNE+ORTCpu+RDG)
in `demoncore.uproject`. UE5 compiles them on next launch (3-5 min once).

---

## Phase 1 — See Bastok tonight (procedural blockout)

```
F:\ffxi\stage-monorepo\RUN_BASTOK_BLOCKOUT.bat
```
Closes UE5, copies the blockout script into `demoncore/Content/Python/`,
relaunches UE5 with `-ExecutePythonScript`. ~30 placeholder actors pop in
representing Bastok Markets — walls, central elevator pillar, vendor
stalls, shops, smokestack, forge, sunset lighting. Good for validating
that the editor pipeline works before the heavier extraction.

---

## Phase 2 — Pull canonical Bastok from retail (overnight-safe)

```
F:\ffxi\stage-monorepo\EXTRACT_BASTOK_FROM_RETAIL.bat
```
Auto-installs Noesis + the FFXI plugin if not present, runs Noesis CLI
against the retail client at `F:\ffxi\client\FINAL FANTASY XI\`,
outputs `bastok_markets.fbx` + `textures/*.png` + collision mesh to
`F:\ChharithOeun\Final-Fantasy-XI\FFXI-Demoncore\extracted\bastok_markets\`.
Falls back to Noesis GUI if CLI flags don't match the plugin version.

```
F:\ffxi\stage-monorepo\UPSCALE_BASTOK_TEXTURES.bat
```
Auto-installs Real-ESRGAN ncnn-vulkan (works on AMD via Vulkan, no
DirectML/CUDA needed). Walks `textures/` and writes `textures_4k/` x4
upscaled siblings. Same filenames, same UV layout.

---

## Phase 3 — Compose the scene like a film cut (run in UE5)

In UE5 (with the demoncore project open):
```
Tools → Execute Python Script... → bastok_layered_scene.py
```
Builds five depth layers + two cross-cutting systems:

| Layer / System              | Folder in World Outliner              |
| --------------------------- | ------------------------------------- |
| Sky                         | `Demoncore/Layer_1_Sky`               |
| Far Background              | `Demoncore/Layer_2_FarBackground`     |
| Mid Background              | `Demoncore/Layer_3_MidBackground`     |
| Foreground Props            | `Demoncore/Layer_4_Props`             |
| Hero Actors                 | `Demoncore/Layer_5_HeroActors`        |
| **System A — Destructibles**| `Demoncore/System_A_Destructibles`    |
| **System B — AI Density**   | `Demoncore/System_B_AI_Density`       |

If `extracted/bastok_markets.fbx` exists, layer 3 imports the canonical
zone. Otherwise it builds the procedural blockout. Re-run the script
freely — each layer wipes its own tag-set first. Toggle layer/system
folders' eye icons to compose the shot.

---

## Phase 4 — Wire the agent + damage data (server side)

Each agent in the world reads from `agents/<id>.yaml`. The chharbot
agent orchestrator (still being written) walks this directory on boot,
validates against `_SCHEMA.md`, instantiates each agent at the right
tier per `AI_WORLD_DENSITY.md`, and connects to the LSB event bus.

Authored so far:
- `agents/zaldon.yaml`         (Tier 2 vendor)
- `agents/cid.yaml`            (Tier 3 hero)
- `agents/volker.yaml`         (Tier 3 hero)
- `agents/cornelia.yaml`       (Tier 3 hero)
- `agents/pellah.yaml`         (Tier 2 repair NPC)

Damage / heal presets ride on actor tags in the level
(`HS:<kind>:<hp>:<rate>:<delay>`), parsed by a Blueprint setup pass
that attaches `BPC_HealingStructure` to each tagged actor.

---

## Phase 5 — Capture and ship

For session screenshots / bug logs / AAR docs:
- Window → High Resolution Screenshot in UE5
- Files land in `demoncore/Saved/Screenshots/`

To ship a milestone to GitHub:
- `SHIP_EXPLICIT.bat` (already used) — per-file `git add` then commit + push

---

## Reference docs (alphabetical)

| Doc                                | What it covers                                        |
| ---------------------------------- | ----------------------------------------------------- |
| AI_ORCHESTRATION.md                | LLM NPC + RL combat + boss critic                     |
| AI_WORLD_DENSITY.md                | 4 AI tiers, density targets, compute budget           |
| ASSETS.md                          | Asset extraction + Megascans strategy                 |
| AUTH_DISCORD.md                    | Discord OAuth replacing PlayOnline                    |
| CHARACTER_CREATION.md              | Hero screen, galka redesign, naming                   |
| CINEMATICS.md + VIRTUAL_PROD.md    | Cutscene pipeline + Mandalorian StageCraft adaptation |
| COMBAT_TEMPO.md                    | 10x mobs, faster auto-attacks                         |
| **DAMAGE_PHYSICS_HEALING.md**      | Destructible structures with heal-over-time          |
| FOMOR_GEAR_PROGRESSION.md          | Recursive purple-stat drop loop                       |
| GPU_COMPAT.md                      | AMD/DirectML strategy per tool                        |
| HARDCORE_DEATH.md                  | 1-hour permadeath → fomor mechanic                    |
| HONOR_REPUTATION.md                | Dual moral / public gauges                            |
| **LAYERED_COMPOSITION.md**         | 5-layer film directing approach                       |
| MOUNTS.md                          | Mount = speed only, mount has HP                      |
| MUSIC_PIPELINE.md                  | ACE-Step + LoRA per zone                              |
| NPC_PROGRESSION.md                 | NPCs / mobs / NMs / bosses level up + buy gear        |
| PVP_GLOBAL_OUTLAWS.md              | Cross-faction PvP + outlaw bounty                     |
| REACTIVE_WORLD.md                  | Server-wide event reactivity                          |
| SIEGE_CAMPAIGN.md                  | Beastman raids + nation military deployment           |
| VOICE_PIPELINE.md                  | Higgs Audio + F5-TTS + Bark per NPC                   |
| **ZONE_EXTRACTION_PIPELINE.md**    | Pull canonical zones from retail client               |

Bolded docs are the ones you'll touch most while building Bastok.

---

## What "done" looks like for a single zone

A zone is fully shipped when:

1. Sky preset authored (Layer 1)
2. Far background hero meshes selected from Megascans (Layer 2)
3. Canonical mesh extracted + 4K textures imported (Layer 3)
4. Foreground props placed by hand using Megascans (Layer 4)
5. NPC anchors swapped for SkeletalMesh actors with KawaiiPhysics
   + AI4Animation (Layer 5)
6. Destructible tags converted to BPC_HealingStructure components
   (System A)
7. Agent YAMLs authored for every named NPC + ambient agent in the
   zone (System B)
8. Voice profiles cloned for every Tier-2/3 agent (Higgs Audio)
9. Music preset assigned to the zone (ACE-Step LoRA)
10. PlayerStart placed, PlayerCharacter spawnable, world saved

Bastok Markets is the canonical first zone — once it ships, the same
process generalizes to all 200+ FFXI zones. ~2 hours of human work +
~8 hours overnight compute per zone after that.

---

## Open in-progress threads

- Task #85: VS2022 install (re-check via CHECK_VS2022.bat)
- Task #91: Bastok Markets prototype scene (procedural built; canonical
  pending Phase 2 run)
- chharbot agent orchestrator (server side; reads `agents/*.yaml`)
- BPC_HealingStructure Blueprint component (UE5 BP/C++)
- Tier-2/3 reflection cycle scheduling (LSB cron-style task)
- Zone extraction batch parameterized for any zone ID
- Voice cloning pipeline for the 5 flagship agent profiles
