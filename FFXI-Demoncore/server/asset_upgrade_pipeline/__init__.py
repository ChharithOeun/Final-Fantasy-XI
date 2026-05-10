"""Asset upgrade pipeline — retail FFXI geometry → UE5 Nanite + 4K PBR.

The forge that takes the 2002-vintage low-poly Bastok the
retail extraction batch hands us — 256x256 textures, ~600
tri buildings, untextured normals — and walks every asset
through the open-source upgrade chain that ends in a UE5
Nanite mesh, 4K PBR materials, four LODs, and a ship-ready
manifest entry.

Per-asset state machine. Forward-only with one exception:
a FAILED asset can be retried from RAW. Every other illegal
jump (e.g. NANITE_BUILT → RAW, or skipping
MATERIAL_AUTHORED) is rejected at advance() time.

    RAW
      v
    UPSCALED_TEXTURE     (Real-ESRGAN 4x → 1024 / 2048 / 4096)
      v
    NANITE_BUILT         (Blender Geometry Nodes remesh +
                          UE5 Nanite import; tri budget set
                          by source poly_count_before)
      v
    MATERIAL_AUTHORED    (Material Maker procedural author;
                          albedo / roughness / metalness slots)
      v
    PBR_BAKED            (Marigold depth → normal + StableDelight
                          relight pass + CodeFormer face restore
                          for any face textures)
      v
    LOD_GENERATED        (4 LODs — nanite_dense / nanite_thin /
                          card_billboard / impostor)
      v
    SHIP_READY

    FAILED  ← any state on error; retry resets to RAW.

Public surface
--------------
    AssetKind enum
    AssetState enum
    UpgradeTool enum
    AssetRecord dataclass (frozen)
    AssetUpgradePipeline (System class)
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import enum
import typing as t


class AssetKind(enum.Enum):
    MESH = "mesh"
    TEXTURE = "texture"
    MATERIAL = "material"
    RIG = "rig"


class AssetState(enum.Enum):
    RAW = "raw"
    UPSCALED_TEXTURE = "upscaled_texture"
    NANITE_BUILT = "nanite_built"
    MATERIAL_AUTHORED = "material_authored"
    PBR_BAKED = "pbr_baked"
    LOD_GENERATED = "lod_generated"
    SHIP_READY = "ship_ready"
    FAILED = "failed"


class UpgradeTool(enum.Enum):
    REAL_ESRGAN = "real_esrgan"
    MARIGOLD = "marigold"
    STABLE_DELIGHT = "stable_delight"
    CODEFORMER = "codeformer"
    MATERIAL_MAKER = "material_maker"
    BLENDER_GEONODES = "blender_geonodes"
    UE5_NANITE = "ue5_nanite"


# Forward-only DAG (FAILED edges are special-cased).
_TRANSITIONS: dict[AssetState, frozenset[AssetState]] = {
    AssetState.RAW: frozenset({
        AssetState.UPSCALED_TEXTURE,
        AssetState.NANITE_BUILT,  # textures skip mesh build
        AssetState.FAILED,
    }),
    AssetState.UPSCALED_TEXTURE: frozenset({
        AssetState.NANITE_BUILT,
        AssetState.MATERIAL_AUTHORED,  # texture-only assets
        AssetState.FAILED,
    }),
    AssetState.NANITE_BUILT: frozenset({
        AssetState.MATERIAL_AUTHORED, AssetState.FAILED,
    }),
    AssetState.MATERIAL_AUTHORED: frozenset({
        AssetState.PBR_BAKED, AssetState.FAILED,
    }),
    AssetState.PBR_BAKED: frozenset({
        AssetState.LOD_GENERATED, AssetState.FAILED,
    }),
    AssetState.LOD_GENERATED: frozenset({
        AssetState.SHIP_READY, AssetState.FAILED,
    }),
    AssetState.SHIP_READY: frozenset(),  # terminal
    AssetState.FAILED: frozenset({AssetState.RAW}),  # retry only
}


@dataclasses.dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    source_path: str
    kind: AssetKind
    zone_id: str
    poly_count_before: int
    poly_count_after: int
    texture_resolution_before: int  # square edge px
    texture_resolution_after: int
    current_state: AssetState
    last_updated_iso: str
    errors: tuple[str, ...] = ()


def _now_iso() -> str:
    return _dt.datetime.utcnow().isoformat(timespec="seconds")


@dataclasses.dataclass
class AssetUpgradePipeline:
    """In-memory upgrade pipeline. Holds an asset book and a
    transition log for the producer's daily progress oracle.
    """
    _assets: dict[str, AssetRecord] = dataclasses.field(
        default_factory=dict,
    )
    _log: list[tuple[str, AssetState, AssetState, str]] = (
        dataclasses.field(default_factory=list)
    )

    # ---- registration -------------------------------------------
    def register_asset(
        self,
        asset_id: str,
        source_path: str,
        kind: AssetKind,
        zone_id: str,
        poly_count_before: int = 0,
        texture_resolution_before: int = 0,
    ) -> AssetRecord:
        if not asset_id:
            raise ValueError("asset_id required")
        if asset_id in self._assets:
            raise ValueError(
                f"asset_id already registered: {asset_id}",
            )
        if poly_count_before < 0:
            raise ValueError("poly_count_before must be >= 0")
        if texture_resolution_before < 0:
            raise ValueError(
                "texture_resolution_before must be >= 0",
            )
        rec = AssetRecord(
            asset_id=asset_id,
            source_path=source_path,
            kind=kind,
            zone_id=zone_id,
            poly_count_before=poly_count_before,
            poly_count_after=0,
            texture_resolution_before=texture_resolution_before,
            texture_resolution_after=0,
            current_state=AssetState.RAW,
            last_updated_iso=_now_iso(),
        )
        self._assets[asset_id] = rec
        return rec

    def lookup(self, asset_id: str) -> AssetRecord:
        if asset_id not in self._assets:
            raise KeyError(f"unknown asset: {asset_id}")
        return self._assets[asset_id]

    def all_assets(self) -> tuple[AssetRecord, ...]:
        return tuple(self._assets.values())

    # ---- state transitions --------------------------------------
    def _validate_transition(
        self, current: AssetState, new: AssetState,
    ) -> None:
        if new == current:
            raise ValueError(
                f"already in state {current.value}",
            )
        allowed = _TRANSITIONS.get(current, frozenset())
        if new not in allowed:
            raise ValueError(
                f"illegal transition {current.value} → "
                f"{new.value}",
            )

    def advance(
        self,
        asset_id: str,
        new_state: AssetState,
        poly_count_after: int = -1,
        texture_resolution_after: int = -1,
    ) -> AssetRecord:
        rec = self.lookup(asset_id)
        self._validate_transition(rec.current_state, new_state)
        new_poly = (
            rec.poly_count_after if poly_count_after < 0
            else poly_count_after
        )
        new_tex = (
            rec.texture_resolution_after
            if texture_resolution_after < 0
            else texture_resolution_after
        )
        # Retry from FAILED resets the build audit fields but
        # preserves the error history — the producer needs the
        # paper trail of past failures for the post-mortem.
        if (
            rec.current_state == AssetState.FAILED
            and new_state == AssetState.RAW
        ):
            new_poly = 0
            new_tex = 0
        errors = rec.errors
        nrec = dataclasses.replace(
            rec,
            current_state=new_state,
            poly_count_after=new_poly,
            texture_resolution_after=new_tex,
            last_updated_iso=_now_iso(),
            errors=errors,
        )
        self._assets[asset_id] = nrec
        self._log.append(
            (asset_id, rec.current_state, new_state, _now_iso()),
        )
        return nrec

    def mark_failed(
        self, asset_id: str, error: str,
    ) -> AssetRecord:
        rec = self.lookup(asset_id)
        if rec.current_state == AssetState.SHIP_READY:
            raise ValueError(
                "cannot fail SHIP_READY asset; ship cannot be unshipped",
            )
        if not error:
            raise ValueError("error message required")
        nrec = dataclasses.replace(
            rec,
            current_state=AssetState.FAILED,
            errors=rec.errors + (error,),
            last_updated_iso=_now_iso(),
        )
        self._assets[asset_id] = nrec
        self._log.append(
            (asset_id, rec.current_state, AssetState.FAILED, _now_iso()),
        )
        return nrec

    def bulk_advance(
        self,
        asset_ids: t.Sequence[str],
        new_state: AssetState,
    ) -> tuple[AssetRecord, ...]:
        out: list[AssetRecord] = []
        for aid in asset_ids:
            out.append(self.advance(aid, new_state))
        return tuple(out)

    # ---- batch ops / queries ------------------------------------
    def assets_in_state(
        self, state: AssetState,
    ) -> tuple[AssetRecord, ...]:
        return tuple(
            r for r in self._assets.values()
            if r.current_state == state
        )

    def assets_in_zone(
        self, zone_id: str,
    ) -> tuple[AssetRecord, ...]:
        return tuple(
            r for r in self._assets.values()
            if r.zone_id == zone_id
        )

    def upgrade_all_in_zone(
        self, zone_id: str, target: AssetState,
    ) -> tuple[AssetRecord, ...]:
        """Advance every non-terminal, non-failed asset in the
        zone one step toward ``target`` if a legal step exists.
        """
        results: list[AssetRecord] = []
        for rec in tuple(self.assets_in_zone(zone_id)):
            if rec.current_state in (
                AssetState.SHIP_READY, AssetState.FAILED,
            ):
                continue
            allowed = _TRANSITIONS.get(rec.current_state, frozenset())
            # Pick the step that moves toward target if possible.
            if target in allowed:
                results.append(self.advance(rec.asset_id, target))
            else:
                # No direct edge — advance to the next step in
                # the canonical RAW→SHIP order, if one exists.
                preferred_order = (
                    AssetState.UPSCALED_TEXTURE,
                    AssetState.NANITE_BUILT,
                    AssetState.MATERIAL_AUTHORED,
                    AssetState.PBR_BAKED,
                    AssetState.LOD_GENERATED,
                    AssetState.SHIP_READY,
                )
                next_step: t.Optional[AssetState] = None
                for st in preferred_order:
                    if st in allowed:
                        next_step = st
                        break
                if next_step is not None:
                    results.append(
                        self.advance(rec.asset_id, next_step),
                    )
        return tuple(results)

    def retry_failed(self) -> tuple[AssetRecord, ...]:
        out: list[AssetRecord] = []
        for rec in tuple(self.assets_in_state(AssetState.FAILED)):
            out.append(self.advance(rec.asset_id, AssetState.RAW))
        return tuple(out)

    def pending_count(self) -> int:
        """Anything not SHIP_READY and not FAILED."""
        return sum(
            1 for r in self._assets.values()
            if r.current_state not in (
                AssetState.SHIP_READY, AssetState.FAILED,
            )
        )

    def ship_ready_count(self) -> int:
        return sum(
            1 for r in self._assets.values()
            if r.current_state == AssetState.SHIP_READY
        )

    def failed_count(self) -> int:
        return sum(
            1 for r in self._assets.values()
            if r.current_state == AssetState.FAILED
        )

    def zone_progress(
        self, zone_id: str,
    ) -> tuple[int, int, int, float]:
        """Return (total, complete, failed, pct_complete)."""
        in_zone = self.assets_in_zone(zone_id)
        total = len(in_zone)
        if total == 0:
            return (0, 0, 0, 0.0)
        complete = sum(
            1 for r in in_zone
            if r.current_state == AssetState.SHIP_READY
        )
        failed = sum(
            1 for r in in_zone
            if r.current_state == AssetState.FAILED
        )
        pct = round(100.0 * complete / total, 2)
        return (total, complete, failed, pct)

    def throughput_per_hour(self, window_hours: float) -> float:
        """How many SHIP_READY transitions in the last N hours."""
        if window_hours <= 0:
            raise ValueError("window_hours must be > 0")
        cutoff = _dt.datetime.utcnow() - _dt.timedelta(
            hours=window_hours,
        )
        cutoff_iso = cutoff.isoformat(timespec="seconds")
        ship_count = 0
        for asset_id, _src, dst, when in self._log:
            if dst == AssetState.SHIP_READY and when >= cutoff_iso:
                ship_count += 1
        return round(ship_count / window_hours, 3)

    def transition_log(
        self,
    ) -> tuple[tuple[str, AssetState, AssetState, str], ...]:
        return tuple(self._log)

    def errors_for(self, asset_id: str) -> tuple[str, ...]:
        return self.lookup(asset_id).errors


__all__ = [
    "AssetKind", "AssetState", "UpgradeTool",
    "AssetRecord", "AssetUpgradePipeline",
]
