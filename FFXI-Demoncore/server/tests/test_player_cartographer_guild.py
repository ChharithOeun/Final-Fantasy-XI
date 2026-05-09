"""Tests for player_cartographer_guild."""
from __future__ import annotations

from server.player_cartographer_guild import (
    PlayerCartographerGuildSystem,
    GuildState, CartographerRank,
)


def _found(s: PlayerCartographerGuildSystem) -> str:
    return s.found_guild(
        guildmaster_id="naji",
        name="Cartographers of Vana'diel",
    )


def _induct(
    s: PlayerCartographerGuildSystem,
    gid: str, member: str = "alice",
) -> None:
    s.induct(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id=member, survey_skill=50,
    )


def test_found_happy():
    s = PlayerCartographerGuildSystem()
    assert _found(s) is not None


def test_found_empty_blocked():
    s = PlayerCartographerGuildSystem()
    assert s.found_guild(
        guildmaster_id="", name="x",
    ) is None


def test_induct_happy():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.induct(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="alice", survey_skill=50,
    ) is True


def test_induct_low_skill_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.induct(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="alice", survey_skill=10,
    ) is False


def test_induct_self_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.induct(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="naji", survey_skill=99,
    ) is False


def test_induct_dup_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    assert s.induct(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="alice", survey_skill=50,
    ) is False


def test_induct_wrong_master_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.induct(
        guild_id=gid, guildmaster_id="bob",
        cartographer_id="alice", survey_skill=50,
    ) is False


def test_apprentice_initial_rank():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    assert s.member(
        guild_id=gid, cartographer_id="alice",
    ).rank == CartographerRank.APPRENTICE


def test_submit_survey_promotes_to_novice():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    s.submit_survey(
        guild_id=gid, cartographer_id="alice",
    )
    assert s.member(
        guild_id=gid, cartographer_id="alice",
    ).rank == CartographerRank.NOVICE


def test_submit_survey_promotes_to_journeyman():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    for _ in range(10):
        s.submit_survey(
            guild_id=gid, cartographer_id="alice",
        )
    assert s.member(
        guild_id=gid, cartographer_id="alice",
    ).rank == CartographerRank.JOURNEYMAN


def test_submit_survey_promotes_to_master():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    for _ in range(50):
        s.submit_survey(
            guild_id=gid, cartographer_id="alice",
        )
    assert s.member(
        guild_id=gid, cartographer_id="alice",
    ).rank == CartographerRank.MASTER


def test_submit_survey_count_advances():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    for _ in range(7):
        s.submit_survey(
            guild_id=gid, cartographer_id="alice",
        )
    assert s.member(
        guild_id=gid, cartographer_id="alice",
    ).surveys_submitted == 7


def test_submit_survey_non_member_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.submit_survey(
        guild_id=gid, cartographer_id="stranger",
    ) is False


def test_expel_happy():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    assert s.expel(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="alice",
    ) is True


def test_expel_wrong_master_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid)
    assert s.expel(
        guild_id=gid, guildmaster_id="bob",
        cartographer_id="alice",
    ) is False


def test_expel_unknown_member_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.expel(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="ghost",
    ) is False


def test_close_happy():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.close(
        guild_id=gid, guildmaster_id="naji",
    ) is True
    assert s.guild(
        guild_id=gid,
    ).state == GuildState.CLOSED


def test_close_wrong_master_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    assert s.close(
        guild_id=gid, guildmaster_id="bob",
    ) is False


def test_induct_after_close_blocked():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    s.close(
        guild_id=gid, guildmaster_id="naji",
    )
    assert s.induct(
        guild_id=gid, guildmaster_id="naji",
        cartographer_id="alice", survey_skill=50,
    ) is False


def test_members_listing():
    s = PlayerCartographerGuildSystem()
    gid = _found(s)
    _induct(s, gid, member="alice")
    _induct(s, gid, member="bob")
    assert len(s.members(guild_id=gid)) == 2


def test_unknown_guild():
    s = PlayerCartographerGuildSystem()
    assert s.guild(guild_id="ghost") is None


def test_state_count():
    assert len(list(GuildState)) == 2


def test_rank_count():
    assert len(list(CartographerRank)) == 4
