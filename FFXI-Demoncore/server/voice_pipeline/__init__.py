"""Demoncore voice generation pipeline.

Takes a 30-second voice reference WAV per character/mob class plus the
canonical callout library (data/skillchain_callouts.yaml) and generates
the full ~58-line voice library via Higgs Audio v2 (or stub if Higgs
isn't connected).

Public surface:
    VoicePipeline.generate_for_agent(agent_profile)
    VoicePipeline.generate_for_mob_class(mob_class_yaml)
    VoicePipeline.generate_for_player(player_id, reference_wav)
"""
from .pipeline import VoicePipeline, VoiceLine, VoiceJob

__all__ = ["VoicePipeline", "VoiceLine", "VoiceJob"]
