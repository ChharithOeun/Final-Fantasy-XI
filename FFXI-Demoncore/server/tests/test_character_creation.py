"""Tests for server.character_creation."""
from __future__ import annotations

import pytest

from server.character_creation import (
    CREATION_STEP_ORDER,
    NATION_OPENING_LINES,
    NATIONS,
    RACES,
    VOICE_ANCHORS,
    CharacterDraft,
    CharacterPreset,
    CreationSession,
    CreationStep,
    Nation,
    Race,
    export_preset,
    galka_tail_removed,
    import_preset,
    nation_unlocked_for,
    opening_line_for,
    register_custom_voice,
    voice_anchors_for_race,
)


class TestNationsRaces:

    def test_four_nations(self):
        # Bastok / San d'Oria / Windurst / Whitegate (veteran)
        assert len(NATIONS) == 4

    def test_whitegate_veteran_only(self):
        assert NATIONS[Nation.WHITEGATE].veteran_only is True
        assert nation_unlocked_for(Nation.WHITEGATE,
                                       is_veteran=False) is False
        assert nation_unlocked_for(Nation.WHITEGATE,
                                       is_veteran=True) is True

    def test_other_nations_open(self):
        for n in (Nation.BASTOK, Nation.SAN_DORIA, Nation.WINDURST):
            assert nation_unlocked_for(n, is_veteran=False) is True

    def test_five_races(self):
        assert len(RACES) == 5

    def test_galka_tail_removed(self):
        # Doc: 'Tail removed. User preference.'
        assert RACES[Race.GALKA].has_tail is False
        assert galka_tail_removed() is True

    def test_mithra_has_tail_and_groom(self):
        m = RACES[Race.MITHRA]
        assert m.has_tail is True
        assert m.fur_or_groom is True

    def test_galka_uses_groom(self):
        g = RACES[Race.GALKA]
        assert g.fur_or_groom is True

    def test_opening_lines_per_nation(self):
        # Doc: '...alright, let's see what's out there.' (Bastok)
        assert opening_line_for(Nation.BASTOK).startswith("...alright")
        assert opening_line_for(Nation.SAN_DORIA) == "Today is mine."
        assert "chimes" in opening_line_for(Nation.WINDURST)

    def test_opening_lines_complete(self):
        for n in NATIONS:
            assert n in NATION_OPENING_LINES


class TestVoiceBank:

    def test_fifteen_anchors(self):
        # 3 per race x 5 races
        assert len(VOICE_ANCHORS) == 15

    def test_three_per_race(self):
        for race in Race:
            assert len(voice_anchors_for_race(race)) == 3

    def test_register_custom_voice(self):
        rec = register_custom_voice(
            account_id="acct_42",
            duration_seconds=29.5,
            sample_rate_hz=48_000,
            saved_path="/voicebank/acct_42.wav",
        )
        assert rec.voice_bank_id == "voicebank_acct_42"

    def test_register_too_long_rejected(self):
        with pytest.raises(ValueError):
            register_custom_voice(account_id="x",
                                       duration_seconds=60.0,
                                       sample_rate_hz=48_000,
                                       saved_path="/x")

    def test_register_low_sample_rate_rejected(self):
        with pytest.raises(ValueError):
            register_custom_voice(account_id="x",
                                       duration_seconds=20.0,
                                       sample_rate_hz=8_000,
                                       saved_path="/x")

    def test_register_zero_duration_rejected(self):
        with pytest.raises(ValueError):
            register_custom_voice(account_id="x",
                                       duration_seconds=0.0,
                                       sample_rate_hz=48_000,
                                       saved_path="/x")


class TestCreationSession:

    def _filled_draft(self) -> CharacterDraft:
        return CharacterDraft(
            nation=Nation.BASTOK, race=Race.HUME,
            face_id="hume_m_01", hair_id="hume_h_03",
            eyes_id="hume_e_brown", skin_id="hume_s_warm",
            gear_set="bronze_smith",
            voice_anchor_id="hume_low_cogley",
            name="TestPlayer",
        )

    def test_initial_state(self):
        s = CreationSession(account_id="a")
        assert s.current_step == CreationStep.NATION
        assert s.draft.nation is None
        assert s.committed is False

    def test_advance_blocked_until_complete(self):
        s = CreationSession(account_id="a")
        # Nation not picked
        assert s.advance() == CreationStep.NATION
        s.draft.nation = Nation.BASTOK
        assert s.advance() == CreationStep.RACE

    def test_full_walkthrough(self):
        s = CreationSession(account_id="a")
        s.draft = self._filled_draft()
        # Walk all steps
        for step in CREATION_STEP_ORDER:
            assert s.draft.step_complete(step)

    def test_can_commit(self):
        s = CreationSession(account_id="a")
        ok, reason = s.can_commit()
        assert ok is False
        assert "not complete" in reason
        s.draft = self._filled_draft()
        ok, _ = s.can_commit()
        assert ok is True

    def test_commit_locks(self):
        s = CreationSession(account_id="a")
        s.draft = self._filled_draft()
        assert s.commit() is True
        assert s.committed is True
        # Re-roll is a no-op after commit
        s.reroll_step(CreationStep.NAME)
        assert s.draft.name == "TestPlayer"

    def test_commit_fails_without_complete(self):
        s = CreationSession(account_id="a")
        assert s.commit() is False

    def test_go_back(self):
        s = CreationSession(account_id="a")
        s.current_step = CreationStep.RACE
        s.go_back()
        assert s.current_step == CreationStep.NATION

    def test_reroll_appearance(self):
        s = CreationSession(account_id="a")
        s.draft.face_id = "f1"
        s.draft.hair_id = "h1"
        s.draft.eyes_id = "e1"
        s.draft.skin_id = "s1"
        s.reroll_step(CreationStep.APPEARANCE)
        assert s.draft.face_id is None
        assert s.draft.hair_id is None


class TestPresets:

    def _draft(self) -> CharacterDraft:
        return CharacterDraft(
            nation=Nation.BASTOK, race=Race.HUME,
            face_id="hume_m_01", hair_id="hume_h_03",
            eyes_id="hume_e_brown", skin_id="hume_s_warm",
            gear_set="bronze_smith",
            voice_anchor_id="hume_low_cogley",
        )

    def test_export_round_trip(self):
        d = self._draft()
        s = export_preset(d)
        d2, next_step = import_preset(s)
        assert d2.nation == Nation.BASTOK
        assert d2.race == Race.HUME
        assert d2.face_id == "hume_m_01"
        # Doc: presets skip ahead to Name + Begin
        assert next_step == CreationStep.NAME

    def test_export_incomplete_rejected(self):
        d = CharacterDraft(nation=Nation.BASTOK)   # no race
        with pytest.raises(ValueError):
            export_preset(d)

    def test_import_invalid_json(self):
        with pytest.raises(ValueError):
            import_preset("not even json")

    def test_import_missing_field(self):
        partial = '{"nation": "bastok"}'  # missing race + everything else
        with pytest.raises(ValueError):
            import_preset(partial)

    def test_import_unknown_nation(self):
        bad = ('{"nation": "atlantis", "race": "hume", '
                  '"face_id": "x", "hair_id": "x", "eyes_id": "x", '
                  '"skin_id": "x", "gear_set": "x"}')
        with pytest.raises(ValueError):
            import_preset(bad)
