"""Tests for net_voice_chat."""
from __future__ import annotations

import pytest

from server.net_voice_chat import (
    ALLIANCE_PROXIMITY_LIMIT_M,
    GAIN_DUCK_DB,
    GAIN_FAR_DB,
    GAIN_FULL_DB,
    GAIN_NEAR_DB,
    NetVoiceChatSystem,
    PROXIMITY_FAR_LIMIT_M,
    PROXIMITY_FULL_GAIN_M,
    PROXIMITY_NEAR_LIMIT_M,
    VAD_THRESHOLD_DB,
    VoiceChannel,
    VoicePacket,
)


def _packet(
    sender="s1",
    channel=VoiceChannel.ZONE_PROXIMITY,
    bytes_size=128,
    activity=-20.0,
    ts=1000,
    duck=0,
    scope="",
    target="",
):
    return VoicePacket(
        sender_player_id=sender,
        channel=channel,
        opus_data_size_bytes=bytes_size,
        voice_activity_db=activity,
        timestamp_ms=ts,
        ducking_priority=duck,
        scope_id=scope,
        target_player_id=target,
    )


# ---- enum ----

def test_voice_channel_count():
    assert len(list(VoiceChannel)) == 7


def test_voice_channel_has_staff_gm():
    assert VoiceChannel.STAFF_GM in list(VoiceChannel)


def test_voice_channel_has_public_auction():
    assert VoiceChannel.PUBLIC_AUCTION in list(VoiceChannel)


# ---- constants ----

def test_proximity_limits():
    assert PROXIMITY_FULL_GAIN_M == 3.0
    assert PROXIMITY_NEAR_LIMIT_M == 15.0
    assert PROXIMITY_FAR_LIMIT_M == 30.0


def test_alliance_limit():
    assert ALLIANCE_PROXIMITY_LIMIT_M == 60.0


def test_gain_table():
    assert GAIN_FULL_DB == 0.0
    assert GAIN_NEAR_DB == -6.0
    assert GAIN_FAR_DB == -24.0
    assert GAIN_DUCK_DB == -6.0


def test_vad_threshold():
    assert VAD_THRESHOLD_DB == -40.0


# ---- subscriptions ----

def test_register_subscription():
    s = NetVoiceChatSystem()
    s.register_subscription("p1", VoiceChannel.PARTY, "party1")
    assert s.is_subscribed("p1", VoiceChannel.PARTY)


def test_register_subscription_empty_player_raises():
    s = NetVoiceChatSystem()
    with pytest.raises(ValueError):
        s.register_subscription("", VoiceChannel.PARTY)


def test_unsubscribe():
    s = NetVoiceChatSystem()
    s.register_subscription("p1", VoiceChannel.PARTY, "party1")
    s.unsubscribe("p1", VoiceChannel.PARTY, "party1")
    assert not s.is_subscribed("p1", VoiceChannel.PARTY)


def test_channel_member_count():
    s = NetVoiceChatSystem()
    s.register_subscription("p1", VoiceChannel.PARTY, "party1")
    s.register_subscription("p2", VoiceChannel.PARTY, "party1")
    s.register_subscription("p3", VoiceChannel.PARTY, "party2")
    assert s.channel_member_count(VoiceChannel.PARTY, "party1") == 2
    assert s.channel_member_count(VoiceChannel.PARTY, "party2") == 1


# ---- mute ----

def test_mute():
    s = NetVoiceChatSystem()
    s.mute("p1", "p2")
    assert s.is_muted("p1", "p2")


def test_unmute():
    s = NetVoiceChatSystem()
    s.mute("p1", "p2")
    s.unmute("p1", "p2")
    assert not s.is_muted("p1", "p2")


def test_mute_self_raises():
    s = NetVoiceChatSystem()
    with pytest.raises(ValueError):
        s.mute("p1", "p1")


def test_blacklist():
    s = NetVoiceChatSystem()
    s.blacklist_add("griefer")
    assert s.is_blacklisted("griefer")
    s.blacklist_remove("griefer")
    assert not s.is_blacklisted("griefer")


# ---- VAD ----

def test_vad_passes_loud():
    s = NetVoiceChatSystem()
    assert s.passes_vad(_packet(activity=-20.0))


def test_vad_drops_quiet():
    s = NetVoiceChatSystem()
    assert not s.passes_vad(_packet(activity=-50.0))


# ---- staff ----

def test_set_staff():
    s = NetVoiceChatSystem()
    s.set_staff("gm1", True)
    assert s.is_staff("gm1")
    s.set_staff("gm1", False)
    assert not s.is_staff("gm1")


# ---- should_receive ----

def test_should_receive_proximity_in_range():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    pkt = _packet(sender="s1")
    assert s.should_receive("r1", pkt, 10.0)


def test_should_receive_proximity_out_of_range():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    assert not s.should_receive("r1", _packet(sender="s1"), 35.0)


def test_should_receive_proximity_different_zone():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "windurst")
    assert not s.should_receive("r1", _packet(sender="s1"), 10.0)


def test_should_receive_self_no():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    assert not s.should_receive("s1", _packet(sender="s1"), 0.0)


def test_should_receive_muted_no():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    s.mute("r1", "s1")
    assert not s.should_receive("r1", _packet(sender="s1"), 5.0)


def test_should_receive_blacklisted_no():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    s.blacklist_add("s1")
    assert not s.should_receive("r1", _packet(sender="s1"), 5.0)


def test_should_receive_vad_drops():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    pkt = _packet(sender="s1", activity=-60.0)
    assert not s.should_receive("r1", pkt, 5.0)


def test_should_receive_party_member():
    s = NetVoiceChatSystem()
    s.register_subscription("r1", VoiceChannel.PARTY, "party1")
    pkt = _packet(
        sender="s1", channel=VoiceChannel.PARTY, scope="party1",
    )
    assert s.should_receive("r1", pkt)


def test_should_receive_party_non_member():
    s = NetVoiceChatSystem()
    s.register_subscription("r1", VoiceChannel.PARTY, "party2")
    pkt = _packet(
        sender="s1", channel=VoiceChannel.PARTY, scope="party1",
    )
    assert not s.should_receive("r1", pkt)


def test_should_receive_linkshell():
    s = NetVoiceChatSystem()
    s.register_subscription("r1", VoiceChannel.LINKSHELL, "ls_top")
    pkt = _packet(
        sender="s1", channel=VoiceChannel.LINKSHELL, scope="ls_top",
    )
    assert s.should_receive("r1", pkt)


def test_should_receive_whisper_target():
    s = NetVoiceChatSystem()
    pkt = _packet(
        sender="s1",
        channel=VoiceChannel.WHISPER_DIRECT,
        target="r1",
    )
    assert s.should_receive("r1", pkt)


def test_should_receive_whisper_not_target():
    s = NetVoiceChatSystem()
    pkt = _packet(
        sender="s1",
        channel=VoiceChannel.WHISPER_DIRECT,
        target="r2",
    )
    assert not s.should_receive("r1", pkt)


def test_should_receive_staff_gm_yes():
    s = NetVoiceChatSystem()
    s.set_staff("gm_recv", True)
    pkt = _packet(sender="gm_sender", channel=VoiceChannel.STAFF_GM)
    assert s.should_receive("gm_recv", pkt)


def test_should_receive_staff_gm_no():
    s = NetVoiceChatSystem()
    pkt = _packet(sender="gm_sender", channel=VoiceChannel.STAFF_GM)
    assert not s.should_receive("player1", pkt)


def test_should_receive_alliance_in_range():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    pkt = _packet(sender="s1", channel=VoiceChannel.ALLIANCE)
    assert s.should_receive("r1", pkt, 50.0)


def test_should_receive_alliance_out_of_range():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    pkt = _packet(sender="s1", channel=VoiceChannel.ALLIANCE)
    assert not s.should_receive("r1", pkt, 80.0)


# ---- gain_for ----

def test_gain_proximity_full_close():
    s = NetVoiceChatSystem()
    pkt = _packet()
    assert s.gain_for("r1", pkt, 1.0) == GAIN_FULL_DB


def test_gain_proximity_mid():
    s = NetVoiceChatSystem()
    pkt = _packet()
    # at 15m exactly = -6 dB.
    assert s.gain_for("r1", pkt, 15.0) == GAIN_NEAR_DB


def test_gain_proximity_far_max():
    s = NetVoiceChatSystem()
    pkt = _packet()
    assert s.gain_for("r1", pkt, 30.0) == GAIN_FAR_DB


def test_gain_proximity_beyond_far():
    s = NetVoiceChatSystem()
    pkt = _packet()
    assert s.gain_for("r1", pkt, 40.0) == GAIN_FAR_DB


def test_gain_proximity_with_walls():
    s = NetVoiceChatSystem()
    pkt = _packet()
    # at 1m (full), -3 dB damping → -3 dB.
    g = s.gain_for("r1", pkt, 1.0, wall_damping_db=3.0)
    assert g == -3.0


def test_gain_party_full_no_falloff():
    s = NetVoiceChatSystem()
    pkt = _packet(channel=VoiceChannel.PARTY)
    assert s.gain_for("r1", pkt, 1000.0) == GAIN_FULL_DB


def test_gain_whisper_full():
    s = NetVoiceChatSystem()
    pkt = _packet(channel=VoiceChannel.WHISPER_DIRECT)
    assert s.gain_for("r1", pkt, 9999.0) == GAIN_FULL_DB


def test_gain_alliance_falloff():
    s = NetVoiceChatSystem()
    pkt = _packet(channel=VoiceChannel.ALLIANCE)
    # At 3m = full; at 60m = -24; linearly interpolated.
    g_close = s.gain_for("r1", pkt, 3.0)
    g_far = s.gain_for("r1", pkt, 60.0)
    assert g_close == GAIN_FULL_DB
    assert g_far == GAIN_FAR_DB


def test_gain_negative_distance_raises():
    s = NetVoiceChatSystem()
    with pytest.raises(ValueError):
        s.gain_for("r1", _packet(), -1.0)


def test_gain_negative_wall_raises():
    s = NetVoiceChatSystem()
    with pytest.raises(ValueError):
        s.gain_for("r1", _packet(), 1.0, wall_damping_db=-1.0)


# ---- batched packets ----

def test_packets_for_ducks_proximity_when_party_present():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("s2", "bastok")
    s.set_zone("r1", "bastok")
    s.register_subscription("r1", VoiceChannel.PARTY, "party1")
    prox = _packet(sender="s1", ts=1000)
    party = _packet(
        sender="s2",
        channel=VoiceChannel.PARTY,
        scope="party1",
        ts=1001,
    )
    out = s.packets_for(
        "r1", [prox, party], distances_m={"s1": 1.0, "s2": 0.0},
    )
    # Party should be first (priority), proximity should be ducked.
    assert out[0][0].channel == VoiceChannel.PARTY
    # Find the proximity entry and verify -6 dB duck.
    prox_entries = [
        (p, g) for (p, g) in out if p.channel == VoiceChannel.ZONE_PROXIMITY
    ]
    assert len(prox_entries) == 1
    assert prox_entries[0][1] == GAIN_DUCK_DB


def test_packets_for_no_duck_without_party():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    prox = _packet(sender="s1")
    out = s.packets_for(
        "r1", [prox], distances_m={"s1": 1.0},
    )
    assert len(out) == 1
    assert out[0][1] == GAIN_FULL_DB


def test_packets_for_drops_muted():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    s.mute("r1", "s1")
    out = s.packets_for(
        "r1", [_packet(sender="s1")], distances_m={"s1": 1.0},
    )
    assert out == []


def test_packets_for_drops_vad_quiet():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("r1", "bastok")
    out = s.packets_for(
        "r1",
        [_packet(sender="s1", activity=-50.0)],
        distances_m={"s1": 1.0},
    )
    assert out == []


def test_packets_for_orders_by_priority():
    s = NetVoiceChatSystem()
    s.set_zone("s1", "bastok")
    s.set_zone("s2", "bastok")
    s.set_zone("r1", "bastok")
    s.register_subscription("r1", VoiceChannel.PARTY, "party1")
    s.set_staff("r1", True)
    prox = _packet(sender="s1", ts=2000)
    party = _packet(
        sender="s2",
        channel=VoiceChannel.PARTY,
        scope="party1",
        ts=2001,
    )
    gm = _packet(
        sender="gm1",
        channel=VoiceChannel.STAFF_GM,
        ts=2002,
    )
    s.set_zone("gm1", "bastok")
    out = s.packets_for(
        "r1",
        [prox, party, gm],
        distances_m={"s1": 1.0, "s2": 0.0, "gm1": 0.0},
    )
    # GM first, then party, then proximity.
    assert out[0][0].channel == VoiceChannel.STAFF_GM
    assert out[1][0].channel == VoiceChannel.PARTY
    assert out[2][0].channel == VoiceChannel.ZONE_PROXIMITY
