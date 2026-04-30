# BPC_VisibleHealthState — Blueprint Component Spec

UE5 Blueprint Component contract that drives the Visual Health System
per `VISUAL_HEALTH_SYSTEM.md`. Sister component to
`BPC_HealingStructure` and `BPC_VisibleAilmentState`.

This is the bridge between the *data* (`VH:<archetype>` and
`VH_Stage:<stage>` actor tags placed by `bastok_layered_scene.py`) and
the *runtime behavior* (decal layers, idle anim blends, KawaiiPhysics
damping, attack-speed scaling, server sync).

---

## Asset path

```
/Game/Demoncore/Components/BPC_VisibleHealthState
```

---

## Public properties (Details panel exposed)

```
Archetype            FName   "hume_m" | "hume_f" | "elvaan_m" | "elvaan_f"
                             | "tarutaru_m" | "tarutaru_f" | "mithra_f"
                             | "galka_m" | "mob_quadav" | "mob_yagudo"
                             | "mob_goblin" | "mob_orc" | "mob_dragon"
                             | "mob_slime" | "mob_worm" | "wildlife_small"
                             | "wildlife_bird"

HPMax                int32   default 100
HPCurrent            int32   default = HPMax (set on BeginPlay)
CurrentStage         enum    pristine | scuffed | bloodied | wounded
                             | grievous | broken | dead

# Per-archetype asset libraries. Each is a Map<DamageStage, Asset>:
DecalLibrary         TMap<EDamageStage, UMaterialInterface*>
                             one decal per stage; applied as material
                             instance on the body slot
IdleAnimLibrary      TMap<EDamageStage, UAnimSequence*>
                             one idle override per stage; blended via
                             AnimGraph slot "Visible_Damage"
ActionAnimMultiplier TMap<EDamageStage, float>
                             attack-speed multiplier per stage
                             (pristine 1.0 -> broken 0.4)
PostureBlendBone     FName   the spine bone we lerp the stage's
                             posture-offset onto
VFXLibrary           TMap<EDamageStage, UNiagaraSystem*>
                             optional sweat / dust / blood-mist FX

# KawaiiPhysics integration
KawaiiPhysicsAnimNodeName    FName  default "VisibleDamage_Jiggle"
                                    name of the KP node in the AnimBP
                                    we tweak (cape/hair drag damping)
StageDampingMultiplier       TMap<EDamageStage, float>
                                    1.0 (pristine) → 2.5 (broken)
                                    higher = sluggish/heavy cloth

# Server replication
bReplicates                 = true
HPCurrent + CurrentStage replicate on change with RepNotifies.
```

---

## Core API

```
ApplyDamage(int32 Amount, FVector ImpactLocation, AActor* Causer)
  - decrements HPCurrent
  - re-evaluates stage; if it crossed a boundary, calls
    TransitionToStage(new_stage, healing=false)
  - emits OnDamageApplied event for downstream listeners
    (mood orchestrator, combat log, etc)

ApplyHealing(int32 Amount, AActor* Healer)
  - increments HPCurrent (clamped to HPMax)
  - on stage change in healing direction, calls
    TransitionToStage(new_stage, healing=true)

ForceStage(EDamageStage Stage)
  - editor-utility / debug-only; bypasses HP entirely so designers
    can preview each stage's look in the level

GetVisibleStateSummary() -> FVisibleHealthSummary
  - returns {stage, ailment_set, hp_pct} for /check responses
  - hp_pct is intentionally bucketed to the stage band (pristine = 1.0,
    broken = 0.05) so even the snapshot doesn't leak exact HP
```

---

## Stage thresholds

```
ComputeStageFromHP(hp):
    pct = hp / HPMax
    if pct >= 0.90: return pristine
    if pct >= 0.70: return scuffed
    if pct >= 0.50: return bloodied
    if pct >= 0.30: return wounded
    if pct >= 0.10: return grievous
    if pct >  0.00: return broken
    return dead
```

Note: bands match the doc table exactly. Don't fudge them — players
will learn these thresholds and any drift from the documented values
becomes player-facing inconsistency.

---

## TransitionToStage (the spectacle)

This is where the visible-damage system feels alive. On each stage
change, the component runs the full transition routine — *not* a
stage-snap.

```
TransitionToStage(new_stage, healing):
    old_stage = CurrentStage
    CurrentStage = new_stage

    # 1. Material decals — fade old out, fade new in over 0.6s
    if old_stage in DecalLibrary:
        StartFadeMaterialParam("DecalAlpha", 1.0, 0.0, 0.6)
    if new_stage in DecalLibrary:
        SetMaterialParam("DecalTexture", DecalLibrary[new_stage])
        StartFadeMaterialParam("DecalAlpha", 0.0, 1.0, 0.6)

    # 2. Idle animation blend (AnimGraph slot "Visible_Damage")
    target_anim = IdleAnimLibrary[new_stage]
    PlaySlotAnimationAsDynamicMontage(
        target_anim, slot="Visible_Damage",
        blend_in=0.4, blend_out=0.4,
    )

    # 3. KawaiiPhysics damping — cape/hair starts dragging more
    kp_node = AnimInstance->GetKawaiiPhysicsNode(KawaiiPhysicsAnimNodeName)
    if kp_node:
        kp_node.OverrideDamping(StageDampingMultiplier[new_stage])

    # 4. Action speed (server-authoritative — replicated)
    if HasAuthority():
        SetAttackRateMultiplier(ActionAnimMultiplier[new_stage])

    # 5. Spawn the transition VFX (blood mist on hit, dust on heal)
    fx = VFXLibrary[new_stage]
    if fx:
        SpawnNiagaraSystemAttached(
            fx, root_component, "spine_03",
            location_type=KeepRelativeOffset,
            attachment_rule=SnapToTargetIncludingScale,
        )

    # 6. Spine posture offset (the slump). Lerps Y-axis pelvis offset
    #    from 0 (pristine) to -8cm (broken) over 1.5 seconds.
    target_offset = STAGE_POSTURE_OFFSET[new_stage]
    StartTimeline_BlendPostureOffset(
        from=current_posture_offset,
        to=target_offset,
        duration=1.5,
    )

    # 7. Audio
    if not healing:
        PlayStageHurtSound(new_stage, archetype)
    else:
        PlayStageRecoverSound(new_stage, archetype)

    # 8. Broadcast to listeners (mood orchestrator, combat log, etc.)
    OnStageChanged.Broadcast(old_stage, new_stage, healing)
```

---

## Per-archetype overrides

Each archetype provides its own libraries. Authored once per
archetype; the component picks the right library based on the
`Archetype` property.

For galka: blood decals are subtle, but the idle anim library shows
visible tension/clenching at lower stages. The voice line library
substitutes growls for verbal pain reactions.

For tarutaru: blood is more visible (smaller body, larger relative
wounds); the audio library has higher-pitched pain reactions.

For mob_dragon: the IdleAnimLibrary's "wounded" entry has wing-droop;
"broken" has wing-tip dragging. The KP damping multiplier scales the
wing physics sim.

For mob_slime: instead of a decal layer, a material parameter
`Translucency` ramps from 0.6 (pristine) to 0.0 (broken). The slime
gets less translucent as it dies.

For wildlife_small: simpler — just an "ouch" anim and a small blood
decal. No multi-stage idle library.

---

## Server replication detail

`HPCurrent` replicates with `RepNotify_OnHPChanged`:
```
RepNotify_OnHPChanged():
    new_stage = ComputeStageFromHP(HPCurrent)
    if new_stage != CurrentStage:
        TransitionToStage(new_stage, healing = (HPCurrent > prior_HPCurrent))
```

`CurrentStage` also replicates with its own RepNotify so a client
joining mid-transition snaps to the correct visual state without
needing to receive the HP delta.

---

## Tag-driven setup helper

Editor utility script (Python, runs once after layering):

```python
# scripts/wire_visible_health.py
import unreal, re

eas = unreal.EditorActorSubsystem()
VH_RE = re.compile(r"^VH:(.+)$")
STAGE_RE = re.compile(r"^VH_Stage:(.+)$")

bp_path = "/Game/Demoncore/Components/BPC_VisibleHealthState"
bpc_class = unreal.EditorAssetLibrary.load_asset(bp_path)

ARCHETYPE_LIB_PATHS = {
    "hume_m":     "/Game/Demoncore/VH_Libraries/Lib_Hume_M",
    "elvaan_f":   "/Game/Demoncore/VH_Libraries/Lib_Elvaan_F",
    # ... one per archetype
}

for actor in eas.get_all_level_actors():
    archetype = None
    forced_stage = None
    for tag in actor.tags:
        m = VH_RE.match(str(tag))
        if m:
            archetype = m.group(1)
        m = STAGE_RE.match(str(tag))
        if m:
            forced_stage = m.group(1)

    if not archetype:
        continue

    # Skip if already wired
    if any(c.get_class() == bpc_class
           for c in actor.get_components_by_class(unreal.ActorComponent)):
        continue

    comp = unreal.add_component(actor, bpc_class)
    comp.set_editor_property("archetype", archetype)

    lib_path = ARCHETYPE_LIB_PATHS.get(archetype)
    if lib_path:
        # The "library" asset bundles all four maps (Decal/Anim/VFX/Damping)
        lib = unreal.EditorAssetLibrary.load_asset(lib_path)
        if lib:
            comp.set_editor_property("decal_library", lib.decal_library)
            comp.set_editor_property("idle_anim_library", lib.idle_anim_library)
            comp.set_editor_property("vfx_library", lib.vfx_library)
            comp.set_editor_property("stage_damping_multiplier",
                                     lib.stage_damping_multiplier)

    if forced_stage:
        # Demo / preview — set the stage directly without going through HP
        comp.call_method("ForceStage", [unreal.DamageStage[forced_stage]])
```

---

## /check + reveal-skill API

The component exposes a thin function for /check and the reveal
skills. Per `VISUAL_HEALTH_SYSTEM.md` reveal table:

```
GetCheckSummary(observer_skill: ECheckSkill) -> FCheckResponse
  - if observer_skill == None (default /check):
      response = {
          challenge_label: "Easy Prey" | ... | "Impossible to Gauge",
          mood_label: "(seems content)" | ... | "(looks furious)",
          damage_label: "(unharmed)" | "(slightly hurt)" | ... | "(near death)",
      }
  - if observer_skill == Scan (BLU60/SCH40):
      response.exact_hp = HPCurrent
      response.exact_mp = MPCurrent
      response.reveal_expires = world_time + 5.0
  - if observer_skill == Drain / Aspir:
      response.exact_hp_or_mp = ...
      response.reveal_expires = world_time + 2.0   # while-cast + 2s
  - if observer_skill == Mug + 30% roll OR SneakAttack+Mug:
      response.exact_hp = HPCurrent
      response.reveal_expires = world_time + 3.0
```

The reveal duration is server-authoritative; client UI just renders
the remaining time on a small floating bar above the target.

---

## Implementation order

1. Author the EDamageStage enum + STAGE_POSTURE_OFFSET map (~30 min)
2. Build the component with HP/stage logic + RepNotifies (~2 hr)
3. Author the first archetype library (hume_m) end-to-end:
   decals, idle anims, VFX, damping (~1 day for the visual quality bar)
4. Wire `TransitionToStage` with the 8-step routine (~3 hr)
5. KawaiiPhysics damping override (requires a custom anim node hook;
   ~2 hr — pafuhana1213's docs cover this)
6. Spine posture offset timeline (~1 hr)
7. Server replication tests in PIE (~1 hr)
8. Tag-driven setup helper Python script (~30 min)
9. Per-archetype library authoring sweep (24 archetypes total — the
   bulk of the work; ~5 days for the 8 PC-relevant ones, ~5 days for
   mobs, ~1 day for wildlife)
10. Reveal-skill API + UI overlay widget (~2 days)

After step 4 the system *moves*. After step 9 it *sells*. Step 10 is
the depth that takes Demoncore combat from "indie passion project"
to "AAA cinematic combat".
