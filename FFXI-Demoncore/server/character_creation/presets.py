"""Preset import/export — the JSON shortcut path.

Per CHARACTER_CREATION.md: 'a player who's made the same character
on another server can paste a JSON preset and skip ahead to Name +
Begin.'
"""
from __future__ import annotations

import dataclasses
import json
import typing as t

from .creation_steps import CharacterDraft, CreationStep
from .nations_races import Nation, Race


@dataclasses.dataclass(frozen=True)
class CharacterPreset:
    """Serializable subset of a CharacterDraft sufficient to skip to Name."""
    nation: str
    race: str
    sub_race: t.Optional[str]
    face_id: str
    hair_id: str
    eyes_id: str
    skin_id: str
    gear_set: str
    voice_anchor_id: t.Optional[str]
    voice_bank_id: t.Optional[str]


def export_preset(draft: CharacterDraft) -> str:
    """Serialize a draft to a JSON string.

    Skips name (the player re-enters it) and any draft state that
    isn't Nation..Voice.
    """
    if not all([draft.nation, draft.race, draft.face_id,
                  draft.hair_id, draft.eyes_id, draft.skin_id,
                  draft.gear_set]):
        raise ValueError(
            "preset export requires a draft complete through GEAR")
    payload = {
        "nation": draft.nation.value if draft.nation else None,
        "race": draft.race.value if draft.race else None,
        "sub_race": draft.sub_race,
        "face_id": draft.face_id,
        "hair_id": draft.hair_id,
        "eyes_id": draft.eyes_id,
        "skin_id": draft.skin_id,
        "gear_set": draft.gear_set,
        "voice_anchor_id": draft.voice_anchor_id,
        "voice_bank_id": draft.voice_bank_id,
    }
    return json.dumps(payload, sort_keys=True)


def import_preset(preset_json: str) -> tuple[CharacterDraft, CreationStep]:
    """Apply a JSON preset to a fresh draft.

    Returns (draft, next_step) — next_step is NAME, since presets
    skip ahead to name + begin.
    """
    try:
        d = json.loads(preset_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid preset json: {e}") from e
    required = ("nation", "race", "face_id", "hair_id",
                  "eyes_id", "skin_id", "gear_set")
    for k in required:
        if d.get(k) in (None, ""):
            raise ValueError(f"preset missing required field {k!r}")
    draft = CharacterDraft(
        nation=Nation(d["nation"]),
        race=Race(d["race"]),
        sub_race=d.get("sub_race"),
        face_id=d["face_id"],
        hair_id=d["hair_id"],
        eyes_id=d["eyes_id"],
        skin_id=d["skin_id"],
        gear_set=d["gear_set"],
        voice_anchor_id=d.get("voice_anchor_id"),
        voice_bank_id=d.get("voice_bank_id"),
    )
    return draft, CreationStep.NAME
