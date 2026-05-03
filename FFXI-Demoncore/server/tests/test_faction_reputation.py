"""Tests for per-faction player reputation."""
from __future__ import annotations

from server.faction_reputation import (
    REP_MAX,
    REP_MIN,
    Faction,
    FactionKind,
    FactionRegistry,
    PlayerFactionReputation,
    ReputationBand,
    band_for_value,
)


def test_band_for_value_neutral_default():
    assert band_for_value(0) == ReputationBand.NEUTRAL


def test_band_for_value_band_boundaries():
    assert band_for_value(50) == ReputationBand.NEUTRAL
    assert band_for_value(51) == ReputationBand.FRIENDLY
    assert band_for_value(200) == ReputationBand.FRIENDLY
    assert band_for_value(201) == ReputationBand.ALLIED
    assert band_for_value(500) == ReputationBand.ALLIED
    assert band_for_value(501) == ReputationBand.HERO_OF_THE_FACTION


def test_band_for_value_negative_bands():
    assert band_for_value(-50) == ReputationBand.NEUTRAL
    assert band_for_value(-51) == ReputationBand.UNFRIENDLY
    assert band_for_value(-200) == ReputationBand.UNFRIENDLY
    assert band_for_value(-201) == ReputationBand.HOSTILE
    assert band_for_value(-500) == ReputationBand.HOSTILE
    assert band_for_value(-501) == ReputationBand.KILL_ON_SIGHT


def test_default_reputation_is_neutral():
    rep = PlayerFactionReputation(player_id="alice")
    assert rep.value("yagudo") == 0
    assert rep.band("yagudo") == ReputationBand.NEUTRAL


def test_adjust_rep_up():
    rep = PlayerFactionReputation(player_id="alice")
    res = rep.adjust(faction_id="yagudo", delta=100)
    assert res.new_value == 100
    assert res.new_band == ReputationBand.FRIENDLY
    assert res.band_changed
    assert res.delta_applied == 100


def test_adjust_rep_clamps_at_max():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="yagudo", value=REP_MAX)
    res = rep.adjust(faction_id="yagudo", delta=500)
    assert res.new_value == REP_MAX
    assert res.delta_applied == 0


def test_adjust_rep_clamps_at_min():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="yagudo", value=REP_MIN)
    res = rep.adjust(faction_id="yagudo", delta=-500)
    assert res.new_value == REP_MIN
    assert res.delta_applied == 0


def test_adjust_within_same_band_does_not_flag():
    rep = PlayerFactionReputation(player_id="alice")
    rep.adjust(faction_id="yagudo", delta=100)   # Friendly
    res = rep.adjust(faction_id="yagudo", delta=10)  # still Friendly
    assert not res.band_changed


def test_kill_on_sight_means_hostile():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="yagudo", value=-800)
    assert rep.is_hostile("yagudo")
    assert not rep.is_friendly("yagudo")
    assert not rep.can_enter_homeland("yagudo")


def test_friendly_can_use_vendors():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="bastok", value=100)
    assert rep.can_use_vendors("bastok")
    assert rep.can_enter_homeland("bastok")


def test_unfriendly_blocks_vendors_but_allows_homeland():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="bastok", value=-100)
    assert not rep.can_use_vendors("bastok")
    # Unfriendly is not yet hostile, so still in homeland
    assert rep.can_enter_homeland("bastok")


def test_alliance_requires_allied_band():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="bastok", value=100)
    assert not rep.can_join_alliance("bastok")
    rep.set(faction_id="bastok", value=300)
    assert rep.can_join_alliance("bastok")


def test_set_value_clamps():
    rep = PlayerFactionReputation(player_id="alice")
    rep.set(faction_id="yagudo", value=99999)
    assert rep.value("yagudo") == REP_MAX
    rep.set(faction_id="yagudo", value=-99999)
    assert rep.value("yagudo") == REP_MIN


def test_all_factions_with_rep_lists_only_seen():
    rep = PlayerFactionReputation(player_id="alice")
    rep.adjust(faction_id="bastok", delta=10)
    rep.adjust(faction_id="yagudo", delta=-20)
    seen = set(rep.all_factions_with_rep())
    assert seen == {"bastok", "yagudo"}


def test_registry_seeds_canonical_factions():
    reg = FactionRegistry()
    # Spot check: every beastmen tribe represented
    for tribe in (
        "orc", "quadav", "yagudo", "goblin", "sahagin",
        "tonberry", "antica", "mamool_ja", "troll", "lamia",
        "merrow",
    ):
        f = reg.get(tribe)
        assert f is not None
        assert f.kind == FactionKind.BEASTMEN
    # Spot check: nations
    for nation in ("bastok", "san_doria", "windurst", "jeuno",
                    "kazham"):
        f = reg.get(nation)
        assert f is not None
        assert f.kind == FactionKind.NATION
    # Spot check: guilds
    assert reg.get("tenshodo").kind == FactionKind.GUILD
    assert reg.get("mythril_musketeers").kind == FactionKind.GUILD


def test_registry_by_kind_filters():
    reg = FactionRegistry()
    beastmen = reg.by_kind(FactionKind.BEASTMEN)
    assert len(beastmen) == 11
    nations = reg.by_kind(FactionKind.NATION)
    assert len(nations) == 5


def test_registry_register_new_faction():
    reg = FactionRegistry()
    custom = Faction(
        faction_id="rogue_alliance", label="Rogue Alliance",
        kind=FactionKind.GUILD, homeland_zone_id="dynamis_d_jeuno",
    )
    reg.register(custom)
    assert reg.get("rogue_alliance") is custom


def test_full_lifecycle_alice_climbs_then_falls():
    """Alice grinds Bastok rep, joins their alliance, then betrays
    them and ends KILL_ON_SIGHT."""
    rep = PlayerFactionReputation(player_id="alice")
    rep.adjust(faction_id="bastok", delta=300)
    assert rep.band("bastok") == ReputationBand.ALLIED
    assert rep.can_join_alliance("bastok")
    # Big betrayal
    rep.adjust(faction_id="bastok", delta=-1300)
    assert rep.band("bastok") == ReputationBand.KILL_ON_SIGHT
    assert not rep.can_enter_homeland("bastok")
