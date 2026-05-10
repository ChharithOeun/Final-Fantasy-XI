"""Demo packaging — the demo build packager.

The end of the showcase pipeline. Bundles a Bastok-Markets
demo into one ``DemoBuildManifest`` — zone, characters,
voice tracks, dressing items, choreography, music cues,
render preset, target platform — and validates that every
referenced asset actually exists somewhere up-stack.

Validation is dependency-injected so this module never
imports the upstream registries directly. Callers pass in
a set of existence-check functions (``has_character``,
``has_voice_line``, ``has_dressing_item``,
``known_render_preset``); a no-op default treats every
reference as valid (handy for stubs in unit tests).

Estimated size formula (GB):
    zone:                 8.0
    per character:        1.2
    per voice line:       0.05
    per dressing item:    0.001
    multiplier by preset:
      gameplay_realtime:    1.0
      cutscene_cinematic:   3.0
      trailer_master:       4.0
      social_clip:          1.5
      led_virtual_production: 2.5

Public surface
--------------
    TargetPlatform enum
    ValidationStatus enum
    DemoBuildManifest dataclass (frozen)
    ValidationReport dataclass (frozen)
    DemoPackager
    KNOWN_RENDER_PRESETS frozenset
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class TargetPlatform(enum.Enum):
    PC_HIGH = "pc_high"
    PC_ULTRA = "pc_ultra"
    XBOX_SERIES_X = "xbox_series_x"
    PS5 = "ps5"


class ValidationStatus(enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


KNOWN_RENDER_PRESETS: frozenset[str] = frozenset({
    "gameplay_realtime",
    "cutscene_cinematic",
    "trailer_master",
    "social_clip",
    "led_virtual_production",
})


_ZONE_GB = 8.0
_PER_CHAR_GB = 1.2
_PER_VOICE_LINE_GB = 0.05
_PER_DRESSING_GB = 0.001
_PRESET_MULTIPLIER: dict[str, float] = {
    "gameplay_realtime": 1.0,
    "cutscene_cinematic": 3.0,
    "trailer_master": 4.0,
    "social_clip": 1.5,
    "led_virtual_production": 2.5,
}


@dataclasses.dataclass(frozen=True)
class DemoBuildManifest:
    manifest_id: str
    name: str
    target_platform: TargetPlatform
    zone_id: str
    character_ids: tuple[str, ...]
    voice_track_uris: tuple[str, ...]
    dressing_item_ids: tuple[str, ...]
    choreography_seq_name: str
    music_cue_ids: tuple[str, ...]
    render_preset: str
    estimated_size_gb: float
    validation_status: ValidationStatus
    missing_assets: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ValidationReport:
    manifest_id: str
    status: ValidationStatus
    missing_characters: tuple[str, ...]
    missing_voice_lines: tuple[str, ...]
    missing_dressing: tuple[str, ...]
    unknown_render_preset: bool


# Existence-check function signatures.
ExistsFn = t.Callable[[str], bool]
PresetFn = t.Callable[[str], bool]


def _accept_all(_: str) -> bool:
    return True


def _accept_known_preset(name: str) -> bool:
    return name in KNOWN_RENDER_PRESETS


def _compute_estimated_size_gb(
    n_chars: int,
    n_voice: int,
    n_dressing: int,
    render_preset: str,
) -> float:
    base = (
        _ZONE_GB
        + n_chars * _PER_CHAR_GB
        + n_voice * _PER_VOICE_LINE_GB
        + n_dressing * _PER_DRESSING_GB
    )
    mult = _PRESET_MULTIPLIER.get(render_preset, 1.0)
    return round(base * mult, 4)


# ----------------------------------------------------------------
# DemoPackager
# ----------------------------------------------------------------
@dataclasses.dataclass
class DemoPackager:
    """In-memory manifest book.

    Existence-check callables are dependency-injected at
    constructor time so tests can swap them for stubs and
    production can plug in the real registries.
    """
    has_character: ExistsFn = _accept_all
    has_voice_line: ExistsFn = _accept_all
    has_dressing_item: ExistsFn = _accept_all
    known_render_preset: PresetFn = _accept_known_preset
    _manifests: dict[str, DemoBuildManifest] = dataclasses.field(
        default_factory=dict,
    )
    _next_manifest_seq: int = 1

    def _next_id(self) -> str:
        out = f"manifest_{self._next_manifest_seq:04d}"
        self._next_manifest_seq += 1
        return out

    def build_manifest(
        self,
        name: str,
        zone_id: str,
        target_platform: TargetPlatform = TargetPlatform.PC_ULTRA,
        character_ids: t.Sequence[str] = (),
        voice_track_uris: t.Sequence[str] = (),
        dressing_item_ids: t.Sequence[str] = (),
        choreography_seq_name: str = "",
        music_cue_ids: t.Sequence[str] = (),
        render_preset: str = "trailer_master",
    ) -> DemoBuildManifest:
        if not name:
            raise ValueError("name required")
        if not zone_id:
            raise ValueError("zone_id required")
        if not choreography_seq_name:
            raise ValueError(
                "choreography_seq_name required",
            )
        size = _compute_estimated_size_gb(
            n_chars=len(character_ids),
            n_voice=len(voice_track_uris),
            n_dressing=len(dressing_item_ids),
            render_preset=render_preset,
        )
        manifest = DemoBuildManifest(
            manifest_id=self._next_id(),
            name=name,
            target_platform=target_platform,
            zone_id=zone_id,
            character_ids=tuple(character_ids),
            voice_track_uris=tuple(voice_track_uris),
            dressing_item_ids=tuple(dressing_item_ids),
            choreography_seq_name=choreography_seq_name,
            music_cue_ids=tuple(music_cue_ids),
            render_preset=render_preset,
            estimated_size_gb=size,
            validation_status=ValidationStatus.PENDING,
        )
        self._manifests[manifest.manifest_id] = manifest
        return manifest

    def lookup(self, manifest_id: str) -> DemoBuildManifest:
        if manifest_id not in self._manifests:
            raise KeyError(
                f"unknown manifest: {manifest_id}",
            )
        return self._manifests[manifest_id]

    def all_manifests(
        self,
    ) -> tuple[DemoBuildManifest, ...]:
        return tuple(self._manifests.values())

    def validate(self, manifest_id: str) -> ValidationReport:
        m = self.lookup(manifest_id)
        missing_chars = tuple(
            cid for cid in m.character_ids
            if not self.has_character(cid)
        )
        missing_voices = tuple(
            v for v in m.voice_track_uris
            if not self.has_voice_line(v)
        )
        missing_dress = tuple(
            d for d in m.dressing_item_ids
            if not self.has_dressing_item(d)
        )
        unknown_preset = not self.known_render_preset(
            m.render_preset,
        )
        any_missing = (
            missing_chars or missing_voices
            or missing_dress or unknown_preset
        )
        status = (
            ValidationStatus.FAILED if any_missing
            else ValidationStatus.PASSED
        )
        report = ValidationReport(
            manifest_id=manifest_id,
            status=status,
            missing_characters=missing_chars,
            missing_voice_lines=missing_voices,
            missing_dressing=missing_dress,
            unknown_render_preset=unknown_preset,
        )
        # Persist status + missing list back onto the manifest.
        all_missing: tuple[str, ...] = (
            tuple(f"char:{c}" for c in missing_chars)
            + tuple(f"voice:{v}" for v in missing_voices)
            + tuple(f"dress:{d}" for d in missing_dress)
            + (
                (f"preset:{m.render_preset}",)
                if unknown_preset else ()
            )
        )
        new_m = dataclasses.replace(
            m,
            validation_status=status,
            missing_assets=all_missing,
        )
        self._manifests[manifest_id] = new_m
        return report

    def missing_assets_for(
        self, manifest_id: str,
    ) -> tuple[str, ...]:
        return self.lookup(manifest_id).missing_assets

    def estimated_size_gb(
        self, manifest_id: str,
    ) -> float:
        return self.lookup(manifest_id).estimated_size_gb

    def manifests_for_platform(
        self, target_platform: TargetPlatform,
    ) -> tuple[DemoBuildManifest, ...]:
        return tuple(
            m for m in self._manifests.values()
            if m.target_platform == target_platform
        )

    def passing_manifests(
        self,
    ) -> tuple[DemoBuildManifest, ...]:
        return tuple(
            m for m in self._manifests.values()
            if m.validation_status == ValidationStatus.PASSED
        )

    def bastok_markets_default(self) -> DemoBuildManifest:
        """Pre-built default manifest for the Bastok Markets demo.

        Uses the canonical character ids from
        ``character_model_library``, the canonical dressing ids
        from ``zone_dressing``, the canonical sequence name from
        ``showcase_choreography``, and the trailer_master preset
        from ``render_queue``.
        """
        return self.build_manifest(
            name="Bastok Markets Showcase Demo",
            zone_id="bastok_markets",
            target_platform=TargetPlatform.PC_ULTRA,
            character_ids=(
                "volker", "cid", "iron_eater", "naji",
                "romaa_mihgo", "cornelia", "lhe_lhangavo",
                "generic_galka_smith",
                "generic_hume_engineer",
                "generic_mithra_musketeer",
                "generic_taru_apprentice",
            ),
            voice_track_uris=(
                "vline_narrator_intro_001",
                "vline_cid_forging_001",
                "vline_cid_forging_002",
                "vline_volker_handoff_001",
                "vline_volker_handoff_002",
                "vline_volker_handoff_003",
                "vline_bandit_yell_001",
                "vline_skillchain_callout_001",
                "vline_iron_eater_intro_001",
                "vline_iron_eater_intro_002",
            ),
            dressing_item_ids=(
                "cid_forge", "cid_anvil", "cid_lathe",
                "cid_hammer_rack", "cid_mythril_ingot_pile",
                "cid_water_trough",
                "cid_sparks_particle_anchor",
                "cid_leather_apron_stand",
                "stall_mythril_smith", "stall_weapons",
                "stall_armor", "stall_fish", "stall_fruit",
                "stall_ironworks_tickets",
                "poster_notices_board",
                "poster_wanted_bandit",
                "poster_musketeer_recruit",
                "poster_mythril_industry",
                "crate_a", "crate_b", "crate_c_stacked",
                "barrel_water", "barrel_oil", "rope_coil",
                "oil_drum_a", "hanging_lantern_a",
                "gallery_railing_lower",
                "gallery_railing_mid",
                "gallery_railing_upper",
                "evidence_dagger", "evidence_torn_sash",
            ),
            choreography_seq_name="bastok_markets_demo",
            music_cue_ids=(
                "cue_mines_amb_intro",
                "cue_markets_arrival",
                "cue_workshop_loop",
                "cue_volker_theme",
                "cue_markets_loop",
                "cue_combat_bandits",
                "cue_skillchain_burst",
                "cue_iron_eater_theme",
            ),
            render_preset="trailer_master",
        )


__all__ = [
    "TargetPlatform", "ValidationStatus",
    "DemoBuildManifest", "ValidationReport",
    "DemoPackager", "KNOWN_RENDER_PRESETS",
]
