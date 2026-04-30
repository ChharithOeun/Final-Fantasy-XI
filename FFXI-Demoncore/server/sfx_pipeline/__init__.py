"""Demoncore SFX pipeline.

Per SFX_PIPELINE.md. Four classes of sound:
    1. Canonical-Preserved (HD upscale only — spell + WS sounds)
    2. Canonical-Remastered (HD + tone shaping — ambience, impacts)
    3. New Mechanic Sounds (custom-authored — chakra flow,
       intervention shimmer, dual-cast bell, etc)
    4. Procedural Variation (footsteps, hits, mob roars per-instance
       randomization)

Public surface:
    SFXPipeline(retail_extracted_dir, output_dir, backend)
    SFXPipeline.upscale_canonical(source, output)
    SFXPipeline.author_new_mechanic_sound(mechanic_id, prompt)
    SFXPipeline.generate_variation_set(base_sfx, num_variations)
    SFXPipeline.write_metadata_manifest(sfx_dir, manifest_path)
"""
from .pipeline import SFXJob, SFXPipeline, SFXClass

__all__ = ["SFXPipeline", "SFXJob", "SFXClass"]
