"""Tests for entity_skill_progression."""
from __future__ import annotations

from server.entity_skill_progression import (
    EntitySkillProgressionSystem, SkillTier,
)
from server.entity_hobbies import HobbyKind


def test_log_session_happy():
    s = EntitySkillProgressionSystem()
    assert s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) is True


def test_log_empty_entity_blocked():
    s = EntitySkillProgressionSystem()
    assert s.log_session(
        entity_id="", hobby=HobbyKind.FISHING,
    ) is False


def test_log_zero_gain_blocked():
    s = EntitySkillProgressionSystem()
    assert s.log_session(
        entity_id="x", hobby=HobbyKind.FISHING,
        gain=0,
    ) is False


def test_skill_grows():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
    )
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=5,
    )
    assert s.skill(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == 6


def test_starting_tier_novice():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
    )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == SkillTier.NOVICE


def test_journeyman_at_50():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=50,
    )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == SkillTier.JOURNEYMAN


def test_expert_at_150():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=150,
    )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == SkillTier.EXPERT


def test_master_at_400():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=400,
    )
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == SkillTier.MASTER
    assert s.has_master_title(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) is True


def test_master_title_text():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=500,
    )
    assert s.public_title(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == "Master Angler"


def test_no_title_below_master():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=200,
    )
    assert s.public_title(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) is None


def test_calligraphy_master_title():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="taru_whm",
        hobby=HobbyKind.CALLIGRAPHY,
        gain=400,
    )
    assert s.public_title(
        entity_id="taru_whm",
        hobby=HobbyKind.CALLIGRAPHY,
    ) == "Master Calligrapher"


def test_per_hobby_isolation():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=400,
    )
    # Master at fishing, novice at drinking
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == SkillTier.MASTER
    assert s.tier(
        entity_id="volker", hobby=HobbyKind.DRINKING,
    ) == SkillTier.NOVICE


def test_sessions_count_tracked():
    s = EntitySkillProgressionSystem()
    for _ in range(5):
        s.log_session(
            entity_id="volker",
            hobby=HobbyKind.FISHING, gain=10,
        )
    assert s.sessions(
        entity_id="volker", hobby=HobbyKind.FISHING,
    ) == 5


def test_unknown_entity_zero_skill():
    s = EntitySkillProgressionSystem()
    assert s.skill(
        entity_id="ghost", hobby=HobbyKind.FISHING,
    ) == 0
    assert s.tier(
        entity_id="ghost", hobby=HobbyKind.FISHING,
    ) == SkillTier.NOVICE


def test_all_skills_for_entity():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=10,
    )
    s.log_session(
        entity_id="volker", hobby=HobbyKind.DRINKING,
        gain=20,
    )
    skills = s.all_skills_for(entity_id="volker")
    assert len(skills) == 2


def test_all_masters_lookup():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=500,
    )
    s.log_session(
        entity_id="naji", hobby=HobbyKind.FISHING,
        gain=500,
    )
    s.log_session(
        entity_id="bob", hobby=HobbyKind.FISHING,
        gain=100,
    )
    masters = s.all_masters(hobby=HobbyKind.FISHING)
    assert set(masters) == {"naji", "volker"}


def test_all_masters_per_hobby():
    s = EntitySkillProgressionSystem()
    s.log_session(
        entity_id="volker", hobby=HobbyKind.FISHING,
        gain=500,
    )
    # Volker isn't master at drinking
    masters = s.all_masters(hobby=HobbyKind.DRINKING)
    assert masters == []


def test_unknown_sessions_zero():
    s = EntitySkillProgressionSystem()
    assert s.sessions(
        entity_id="ghost", hobby=HobbyKind.FISHING,
    ) == 0


def test_unknown_all_skills_empty():
    s = EntitySkillProgressionSystem()
    assert s.all_skills_for(entity_id="ghost") == []


def test_enum_count():
    assert len(list(SkillTier)) == 4
