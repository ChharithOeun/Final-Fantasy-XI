"""Tests for fomor crew spawn."""
from __future__ import annotations

from server.fomor_crew_spawn import FomorCrewSpawn, SpawnKind


def test_abducted_emits_captive_intent():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="argo",
        crew_fate=("abducted", "abducted"),
        wreck_zone_id="wreckage_graveyard",
        pirate_zone_id="abyss_trench",
        original_race="hume",
    )
    assert len(intents) == 2
    assert all(i.kind == SpawnKind.CAPTIVE for i in intents)
    assert all(i.zone_id == "abyss_trench" for i in intents)


def test_drowned_to_fomor_emits_mob_intent():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="hymnal",
        crew_fate=("drowned_to_fomor", "drowned_to_fomor"),
        wreck_zone_id="abyss_trench",
        pirate_zone_id="abyss_trench",
        original_race="elvaan",
    )
    assert len(intents) == 2
    assert all(i.kind == SpawnKind.FOMOR_MOB for i in intents)
    assert intents[0].fomor_race == "fomor_elvaan"
    assert intents[0].zone_id == "abyss_trench"


def test_mixed_fate_split():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="lull_1",
        crew_fate=(
            "abducted", "abducted",
            "drowned_to_fomor", "drowned_to_fomor",
        ),
        wreck_zone_id="kelp_labyrinth",
        pirate_zone_id="wreckage_graveyard",
        original_race="tarutaru",
    )
    captives = [i for i in intents if i.kind == SpawnKind.CAPTIVE]
    fomors = [i for i in intents if i.kind == SpawnKind.FOMOR_MOB]
    assert len(captives) == 2
    assert len(fomors) == 2
    assert captives[0].zone_id == "wreckage_graveyard"
    assert fomors[0].zone_id == "kelp_labyrinth"


def test_drowned_no_spawn():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="storm",
        crew_fate=("drowned", "drowned"),
        wreck_zone_id="tideplate_shallows",
        pirate_zone_id="tideplate_shallows",
        original_race="hume",
    )
    assert intents == ()


def test_missing_no_spawn():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="ghost",
        crew_fate=("missing",),
        wreck_zone_id="z",
        pirate_zone_id="z",
        original_race="mithra",
    )
    assert intents == ()


def test_emit_idempotent():
    s = FomorCrewSpawn()
    s.emit_intents(
        ship_id="argo",
        crew_fate=("abducted",),
        wreck_zone_id="z",
        pirate_zone_id="abyss_trench",
        original_race="hume",
    )
    second = s.emit_intents(
        ship_id="argo",
        crew_fate=("abducted",),
        wreck_zone_id="z",
        pirate_zone_id="abyss_trench",
        original_race="hume",
    )
    # second pass returns nothing new
    assert second == ()
    assert s.total_intents() == 1


def test_intents_for_ship():
    s = FomorCrewSpawn()
    s.emit_intents(
        ship_id="A",
        crew_fate=("abducted",),
        wreck_zone_id="z",
        pirate_zone_id="z2",
        original_race="hume",
    )
    s.emit_intents(
        ship_id="B",
        crew_fate=("abducted",),
        wreck_zone_id="z",
        pirate_zone_id="z2",
        original_race="hume",
    )
    a = s.intents_for_ship(ship_id="A")
    assert len(a) == 1
    assert a[0].ship_id == "A"


def test_mark_resolved():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="x",
        crew_fate=("abducted",),
        wreck_zone_id="z",
        pirate_zone_id="z2",
        original_race="hume",
    )
    sid = intents[0].spawn_id
    assert s.mark_resolved(spawn_id=sid) is True
    open_after = s.open_intents()
    assert len(open_after) == 0


def test_mark_resolved_unknown():
    s = FomorCrewSpawn()
    assert s.mark_resolved(spawn_id="ghost") is False


def test_open_intents_filter_by_kind():
    s = FomorCrewSpawn()
    s.emit_intents(
        ship_id="a",
        crew_fate=("abducted", "drowned_to_fomor"),
        wreck_zone_id="z", pirate_zone_id="z2",
        original_race="hume",
    )
    captives = s.open_intents(kind=SpawnKind.CAPTIVE)
    fomors = s.open_intents(kind=SpawnKind.FOMOR_MOB)
    assert len(captives) == 1
    assert len(fomors) == 1


def test_emit_blank_ship_id_rejected():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="",
        crew_fate=("abducted",),
        wreck_zone_id="z", pirate_zone_id="z2",
        original_race="hume",
    )
    assert intents == ()


def test_emit_blank_race_rejected():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="x",
        crew_fate=("abducted",),
        wreck_zone_id="z", pirate_zone_id="z2",
        original_race="",
    )
    assert intents == ()


def test_spawn_ids_deterministic():
    s = FomorCrewSpawn()
    intents = s.emit_intents(
        ship_id="argo",
        crew_fate=("abducted", "abducted"),
        wreck_zone_id="z", pirate_zone_id="z2",
        original_race="hume",
    )
    assert intents[0].spawn_id == "argo#crew000"
    assert intents[1].spawn_id == "argo#crew001"
