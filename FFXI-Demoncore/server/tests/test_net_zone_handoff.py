"""Tests for net_zone_handoff."""
from __future__ import annotations

import pytest

from server.net_zone_handoff import (
    FailureReason,
    HandoffRecord,
    HandoffState,
    NetZoneHandoffSystem,
    PlayerSerializedState,
    SAFE_ZONE_DEFAULT,
)


def _state(
    pid="p1",
    inv=(("crystal_fire", 12),),
    buffs=(("protect", 60000),),
    party="party1",
    friends=("f1",),
    quests=(("rank_mission_1", 3),),
    voice="vc_session_1",
    home="bastok",
):
    return PlayerSerializedState(
        player_id=pid,
        inventory_items=inv,
        buffs=buffs,
        party_id=party,
        friend_ids=friends,
        quest_progress=quests,
        voice_chat_session_id=voice,
        home_nation=home,
    )


# ---- enum coverage ----

def test_handoff_state_count():
    assert len(list(HandoffState)) == 6


def test_handoff_state_has_loading_in():
    assert HandoffState.LOADING_IN in list(HandoffState)


def test_failure_reason_count():
    assert len(list(FailureReason)) == 6


def test_failure_reason_has_checksum_mismatch():
    assert FailureReason.CHECKSUM_MISMATCH in list(FailureReason)


# ---- safe zone ----

def test_safe_zone_default():
    assert SAFE_ZONE_DEFAULT == "rulude_gardens"


def test_fallback_safe_zone_bastok():
    s = NetZoneHandoffSystem()
    s.register_player_state(_state(home="bastok"))
    assert s.fallback_safe_zone("p1") == "bastok_mines_mh"


def test_fallback_safe_zone_windurst():
    s = NetZoneHandoffSystem()
    s.register_player_state(_state(home="windurst"))
    assert s.fallback_safe_zone("p1") == "windurst_woods_mh"


def test_fallback_safe_zone_unknown_default():
    s = NetZoneHandoffSystem()
    assert s.fallback_safe_zone("ghost") == SAFE_ZONE_DEFAULT


# ---- register state ----

def test_register_player_state():
    s = NetZoneHandoffSystem()
    s.register_player_state(_state())
    # no error.


def test_register_empty_player_id_raises():
    s = NetZoneHandoffSystem()
    with pytest.raises(ValueError):
        s.register_player_state(_state(pid=""))


# ---- serialize / deserialize ----

def test_serialize_roundtrip():
    state = _state()
    blob = state.to_blob()
    back = PlayerSerializedState.from_blob(blob)
    assert back == state


def test_serialize_state_requires_active_handoff():
    s = NetZoneHandoffSystem()
    s.register_player_state(_state())
    with pytest.raises(KeyError):
        s.serialize_state("p1")


def test_serialize_state_returns_checksum():
    s = NetZoneHandoffSystem()
    s.register_player_state(_state())
    s.set_server_reachable("srv2", True)
    s.initiate_handoff("p1", "qufim", "srv2")
    blob, checksum = s.serialize_state("p1")
    assert len(checksum) == 64  # sha256 hex
    assert blob


def test_deserialize_wrong_checksum_raises():
    state = _state()
    blob = state.to_blob()
    with pytest.raises(ValueError):
        s = NetZoneHandoffSystem()
        s.deserialize_state(blob, "0" * 64)


def test_deserialize_bad_blob_raises():
    s = NetZoneHandoffSystem()
    bad_blob = b"not_json"
    import hashlib
    cks = hashlib.sha256(bad_blob).hexdigest()
    with pytest.raises(ValueError):
        s.deserialize_state(bad_blob, cks)


# ---- initiate ----

def test_initiate_handoff_success():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    rec = s.initiate_handoff("p1", "qufim", "srv2")
    assert rec.state == HandoffState.HANDING_OFF
    assert rec.target_server_id == "srv2"


def test_initiate_handoff_unreachable_fails_immediately():
    s = NetZoneHandoffSystem()
    rec = s.initiate_handoff("p1", "qufim", "srv2")
    assert rec.state == HandoffState.FAILED
    assert rec.failure_reason == FailureReason.TARGET_UNREACHABLE


def test_initiate_handoff_empty_player_raises():
    s = NetZoneHandoffSystem()
    with pytest.raises(ValueError):
        s.initiate_handoff("", "qufim", "srv2")


def test_initiate_handoff_empty_zone_raises():
    s = NetZoneHandoffSystem()
    with pytest.raises(ValueError):
        s.initiate_handoff("p1", "", "srv2")


def test_initiate_handoff_empty_server_raises():
    s = NetZoneHandoffSystem()
    with pytest.raises(ValueError):
        s.initiate_handoff("p1", "qufim", "")


def test_initiate_handoff_already_active_raises():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.initiate_handoff("p1", "qufim", "srv2")
    with pytest.raises(ValueError):
        s.initiate_handoff("p1", "qufim", "srv2")


# ---- state machine ----

def test_state_idle_for_unknown():
    s = NetZoneHandoffSystem()
    assert s.state_of("ghost") == HandoffState.IDLE


def test_state_transition_serialized():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    s.serialize_state("p1")
    assert s.state_of("p1") == HandoffState.SERIALIZED


def test_state_transition_loading_in():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    blob, ck = s.serialize_state("p1")
    assert s.receive_at_target("p1", blob, ck)
    assert s.state_of("p1") == HandoffState.LOADING_IN


def test_state_transition_complete():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    blob, ck = s.serialize_state("p1")
    s.receive_at_target("p1", blob, ck)
    s.on_target_load_complete("p1")
    assert s.state_of("p1") == HandoffState.COMPLETE


def test_complete_without_loading_raises():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    with pytest.raises(ValueError):
        s.on_target_load_complete("p1")


def test_complete_unknown_raises():
    s = NetZoneHandoffSystem()
    with pytest.raises(KeyError):
        s.on_target_load_complete("ghost")


# ---- failure paths ----

def test_receive_bad_checksum_fails():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    blob, _ck = s.serialize_state("p1")
    ok = s.receive_at_target("p1", blob, "0" * 64)
    assert not ok
    assert s.state_of("p1") == HandoffState.FAILED
    assert s.failure_of("p1") == FailureReason.CHECKSUM_MISMATCH


def test_receive_bad_blob_fails():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    import hashlib
    bad = b"junk"
    ck = hashlib.sha256(bad).hexdigest()
    ok = s.receive_at_target("p1", bad, ck)
    assert not ok
    assert s.failure_of("p1") == FailureReason.SERIALIZATION_MISMATCH


def test_on_handoff_failure_marks():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    s.on_handoff_failure("p1", FailureReason.NETWORK_SPLIT)
    assert s.state_of("p1") == HandoffState.FAILED
    assert s.failure_of("p1") == FailureReason.NETWORK_SPLIT


def test_failure_unknown_raises():
    s = NetZoneHandoffSystem()
    with pytest.raises(KeyError):
        s.on_handoff_failure("ghost", FailureReason.TIMEOUT)


# ---- pending ----

def test_pending_handoffs_empty():
    s = NetZoneHandoffSystem()
    assert s.pending_handoffs() == ()


def test_pending_handoffs_active():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.initiate_handoff("p1", "qufim", "srv2")
    s.initiate_handoff("p2", "qufim", "srv2")
    pending = s.pending_handoffs()
    assert len(pending) == 2


def test_pending_excludes_complete():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.register_player_state(_state())
    s.initiate_handoff("p1", "qufim", "srv2")
    blob, ck = s.serialize_state("p1")
    s.receive_at_target("p1", blob, ck)
    s.on_target_load_complete("p1")
    assert s.pending_handoffs() == ()


def test_pending_excludes_failed():
    s = NetZoneHandoffSystem()
    s.initiate_handoff("p1", "qufim", "srv_unreachable")
    # Failed immediately.
    assert s.pending_handoffs() == ()


# ---- after failed, can re-initiate ----

def test_re_initiate_after_failure():
    s = NetZoneHandoffSystem()
    s.initiate_handoff("p1", "qufim", "srv2")  # fails
    s.set_server_reachable("srv2", True)
    rec = s.initiate_handoff("p1", "qufim", "srv2")
    assert rec.state == HandoffState.HANDING_OFF


# ---- reachability registry ----

def test_set_server_reachable():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    assert s.is_server_reachable("srv2")
    s.set_server_reachable("srv2", False)
    assert not s.is_server_reachable("srv2")


def test_clear_record():
    s = NetZoneHandoffSystem()
    s.set_server_reachable("srv2", True)
    s.initiate_handoff("p1", "qufim", "srv2")
    s.clear_record("p1")
    assert s.state_of("p1") == HandoffState.IDLE


# ---- serialized state fields ----

def test_serialized_state_includes_voice_session():
    state = _state(voice="vc_42")
    blob = state.to_blob()
    back = PlayerSerializedState.from_blob(blob)
    assert back.voice_chat_session_id == "vc_42"


def test_serialized_state_includes_party_id():
    state = _state(party="my_party")
    blob = state.to_blob()
    back = PlayerSerializedState.from_blob(blob)
    assert back.party_id == "my_party"
