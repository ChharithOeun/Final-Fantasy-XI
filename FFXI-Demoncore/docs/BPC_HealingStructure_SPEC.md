# BPC_HealingStructure — Blueprint Component Spec

Contract for the UE5 Blueprint Component that drives the Damage Physics
+ Healing system per `DAMAGE_PHYSICS_HEALING.md`.

This is the bridge between the *data* (`HS:<kind>:<hp>:<rate>:<delay>`
actor tags placed by `bastok_layered_scene.py`) and the *runtime
behavior* (Chaos fracture, heal tween, VFX, server sync).

---

## Asset path

```
/Game/Demoncore/Components/BPC_HealingStructure
```

Created from:
- Blueprint Class → ActorComponent → BPC_HealingStructure

---

## Public properties (Details panel exposed)

```
StructureKind        FName     "wood" | "stone_brick" | "stone_carved"
                               | "metal_industrial" | "cloth_banner"
                               | "glass_window"

HPMax                int32     default 100
HPCurrent            int32     default = HPMax (set on BeginPlay)
HealRate             float     HP per second (default 5.0)
HealDelaySeconds     float     seconds of no-damage before heal starts (8.0)
PermanentThreshold   float     0.0 - 1.0 (default 1.0 = always heals)

GeometryCollection   TSoftObjectPtr<UGeometryCollection>
                               (the fractured asset; can be null for
                                "soft destructibles" that just visually
                                degrade without actually breaking apart)

VFXLibrary           TMap<FName, UNiagaraSystem*>
                               keyed by event name:
                               "break_dust", "break_sparks",
                               "heal_shimmer", "heal_chime"

DamageDecals         TArray<UMaterialInterface*>
                               applied by stage:
                               [0] cracked, [1] battered, [2] ruined

bIsPermanent         bool      true once damage_taken >= permanent_threshold
                               * HPMax. Stops healing.
```

## Internal state

```
LastDamageTime       double    GetWorld()->GetTimeSeconds() at last damage
CurrentVisibleStage  enum      pristine | cracked | battered | ruined | destroyed
ChunkRestPoses       TMap<int32, FTransform>
                               original transforms of every chunk in the
                               GC; cached on BeginPlay; used to tween chunks
                               back during heal
ServerStructureID    int64     id from zone_structures SQL table
```

---

## Public API (callable from Blueprint or C++)

```
// Apply damage. Returns the new HPCurrent (clamped to >= 0).
ApplyDamage(int32 Amount, FVector ImpactLocation, AActor* Causer)

// Force a heal tick (used by repair NPCs to accelerate healing).
ForceHeal(int32 Amount)

// Snapshot for save/load. Returns a struct {HPCurrent, bIsPermanent,
// CurrentVisibleStage} that can be serialized.
GetReplicationState() -> FHealingStructureState

// Restore from snapshot (called on player login when LSB pushes the
// per-zone structure state).
SetReplicationState(FHealingStructureState State)
```

---

## Tick logic (every 0.25s — quarter-second is fine, this is not combat-precision)

```
on tick (DeltaTime):
    if bIsPermanent:
        return  // no healing on permanently scarred structures

    if HPCurrent >= HPMax:
        return  // already full

    seconds_since_damage = world_time - LastDamageTime
    if seconds_since_damage < HealDelaySeconds:
        return  // still in damage cooldown

    HealAmount = HealRate * DeltaTime
    HPCurrent = min(HPMax, HPCurrent + HealAmount)

    new_stage = ComputeStageFromHP(HPCurrent)
    if new_stage != CurrentVisibleStage:
        TransitionToStage(new_stage, healing_direction = true)
```

---

## Damage logic

```
ApplyDamage(amount, impact_loc, causer):
    if bIsPermanent:
        return HPCurrent

    HPCurrent = max(0, HPCurrent - amount)
    LastDamageTime = world_time

    new_stage = ComputeStageFromHP(HPCurrent)
    if new_stage != CurrentVisibleStage:
        TransitionToStage(new_stage, healing_direction = false)

    if HPCurrent == 0:
        damage_taken_pct = 1.0  // fully destroyed this hit
        if damage_taken_pct >= PermanentThreshold:
            bIsPermanent = true

    return HPCurrent
```

---

## Stage computation

```
ComputeStageFromHP(hp):
    pct = hp / HPMax
    if pct >= 0.75: return pristine
    if pct >= 0.50: return cracked
    if pct >= 0.25: return battered
    if pct > 0.00:  return ruined
    return destroyed
```

---

## TransitionToStage

```
TransitionToStage(new_stage, healing_direction):
    old_stage = CurrentVisibleStage
    CurrentVisibleStage = new_stage

    if healing_direction:
        // shrinking damage: reverse-tween chunks back, fade decals out
        PlayHealVFX(new_stage)
        ReattachChunksTween(target_stage = new_stage)
        FadeDecal(stage_to_decal[new_stage], duration = 1.0)
    else:
        // accumulating damage: detach chunks, apply decals, dust + sparks
        PlayBreakVFX(new_stage)
        DetachChunks(target_stage = new_stage)
        ApplyDecal(stage_to_decal[new_stage])
```

### ReattachChunksTween

For each chunk that was detached at `old_stage` but should be present
at `new_stage`:
```
chunk.SetSimulatePhysics(false)
chunk.SetEnableGravity(false)

current_pose = chunk.GetTransform()
rest_pose = ChunkRestPoses[chunk.id]

// Smoothly tween over 1.5 seconds with ease-out
play_timeline:
    on tick (alpha):
        t = ease_out_quad(alpha)
        chunk.SetTransform(lerp(current_pose, rest_pose, t))
    on finish:
        chunk.AttachToComponent(GeometryCollectionComponent)
        spawn_niagara(VFXLibrary["heal_shimmer"], rest_pose.Location)
```

### DetachChunks

For each chunk that should be loose at `new_stage`:
```
chunk.SetSimulatePhysics(true)
chunk.SetEnableGravity(true)

// Eject from impact direction with a small randomization
impulse_dir = (chunk.Location - LastImpactLocation).Normalized()
impulse_dir += RandomVectorInCone(angle = 30deg)
chunk.AddImpulse(impulse_dir * BreakImpulseStrength)

spawn_niagara(VFXLibrary["break_dust"], chunk.Location)
```

---

## Server replication

The component is configured `Replicated = true` with:
- `HPCurrent` replicates on change with a RepNotify
- `bIsPermanent` replicates on change
- `CurrentVisibleStage` replicates with RepNotify that triggers
  `TransitionToStage()` client-side (so each client plays the correct
  VFX even if they joined mid-transition)

LSB pushes structure damage events via the `lsb_admin_api` sidecar →
the UE5 game server's damage broker → this component's `ApplyDamage`.

Heal ticks happen authoritatively on the UE5 game server (which trusts
the LSB heal_rate). Clients receive the resulting HPCurrent updates and
play the correct visuals.

---

## Tag-driven setup helper

Companion editor utility (Python, runs once after layering):

```python
# scripts/wire_healing_structures.py
import unreal, re

eas = unreal.EditorActorSubsystem()
HS_RE = re.compile(r"^HS:([^:]+):(\d+):([\d.]+):([\d.]+)$")

bp_path = "/Game/Demoncore/Components/BPC_HealingStructure"
bpc = unreal.EditorAssetLibrary.load_asset(bp_path)

for actor in eas.get_all_level_actors():
    for tag in actor.tags:
        m = HS_RE.match(str(tag))
        if not m:
            continue
        kind, hp_max, heal_rate, heal_delay = m.groups()

        # Skip if already wired
        if any(c.get_class() == bpc for c in actor.get_components_by_class(
                unreal.ActorComponent)):
            break

        # Add the component
        comp = unreal.add_component(actor, bpc)
        comp.set_editor_property("structure_kind", kind)
        comp.set_editor_property("hp_max", int(hp_max))
        comp.set_editor_property("heal_rate", float(heal_rate))
        comp.set_editor_property("heal_delay_seconds", float(heal_delay))
        # PermanentThreshold defaults to 1.0; designers override
        # via Details panel for siege-scarable structures.
        break
```

A future revision can also fracture the static mesh into a Geometry
Collection automatically using the editor utility framework.

---

## Implementation order

1. Create the BPC asset, expose all properties
2. Implement `ApplyDamage` + `ComputeStageFromHP` + bare-bones `TransitionToStage`
   (just swap material decals for now — chunk physics in step 4)
3. Implement the heal tick
4. Wire up Geometry Collection chunk detach/reattach
5. Author the 6 Niagara VFX templates (one per material kind)
6. Add server replication
7. Wire the LSB damage broker (sidecar API → UE5 game server →
   `ApplyDamage` per affected structure)
8. Run the tag-driven setup helper to attach BPC to every
   `HS:`-tagged actor
9. Tune heal rates per structure_kind in playtest

Steps 1-3 ship the visual feel. Steps 4-5 ship the spectacle. Steps
6-7 ship the multiplayer correctness. Steps 8-9 ship the polish.
