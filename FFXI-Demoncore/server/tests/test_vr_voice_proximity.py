"""Tests for vr_voice_proximity."""
from __future__ import annotations

from server.vr_voice_proximity import (
    VoiceChannel, VrVoiceProximity,
)


def _setup(positions, channels=None):
    """positions: dict player_id -> (x,y,z); channels:
    dict player_id -> set or None for default proximity."""
    v = VrVoiceProximity()
    for pid, (x, y, z) in positions.items():
        v.update_listener(
            player_id=pid, x=x, y=y, z=z,
        )
        ch = (channels or {}).get(
            pid, {VoiceChannel.PROXIMITY},
        )
        v.update_speaker(
            player_id=pid, x=x, y=y, z=z, channels=ch,
        )
    return v


def test_proximity_close_full_volume():
    v = _setup({"bob": (0, 1.5, 0), "cara": (1, 1.5, 0)})
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is not None
    assert mix.channel == VoiceChannel.PROXIMITY
    assert mix.volume == 1.0


def test_proximity_falloff_mid():
    v = _setup({"bob": (0, 1.5, 0), "cara": (16, 1.5, 0)})
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is not None
    # 16y is roughly halfway through 2..30 falloff
    assert 0.4 < mix.volume < 0.7


def test_proximity_out_of_range_silent():
    v = _setup({"bob": (0, 1.5, 0), "cara": (50, 1.5, 0)})
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is None


def test_party_wins_at_distance():
    v = VrVoiceProximity()
    v.update_listener(player_id="bob", x=0, y=1.5, z=0)
    v.update_listener(player_id="cara", x=100, y=1.5, z=0)
    v.update_speaker(
        player_id="cara", x=100, y=1.5, z=0,
        channels={VoiceChannel.PROXIMITY, VoiceChannel.PARTY},
    )
    v.set_party(player_id="bob", party_id="p1")
    v.set_party(player_id="cara", party_id="p1")
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is not None
    assert mix.channel == VoiceChannel.PARTY
    assert mix.volume == 1.0


def test_party_only_if_subscribed():
    v = VrVoiceProximity()
    v.update_listener(player_id="bob", x=0, y=1.5, z=0)
    v.update_listener(player_id="cara", x=100, y=1.5, z=0)
    v.update_speaker(
        player_id="cara", x=100, y=1.5, z=0,
        channels={VoiceChannel.PARTY},
    )
    v.set_party(player_id="bob", party_id="p1")
    v.set_party(player_id="cara", party_id="p1")
    # Bob unsubs from party
    v.toggle_channel(
        player_id="bob",
        channel=VoiceChannel.PARTY, enabled=False,
    )
    mix = v.resolve(listener_id="bob", talker_id="cara")
    # Cara isn't on proximity; bob blocked party -> silent
    assert mix is None


def test_linkshell_routes():
    v = VrVoiceProximity()
    v.update_listener(player_id="bob", x=0, y=1.5, z=0)
    v.update_listener(player_id="cara", x=200, y=1.5, z=0)
    v.update_speaker(
        player_id="cara", x=200, y=1.5, z=0,
        channels={VoiceChannel.LINKSHELL},
    )
    v.set_linkshell(player_id="bob", linkshell_id="ls1")
    v.set_linkshell(player_id="cara", linkshell_id="ls1")
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is not None
    assert mix.channel == VoiceChannel.LINKSHELL


def test_linkshell_different_silent():
    v = VrVoiceProximity()
    v.update_listener(player_id="bob", x=0, y=1.5, z=0)
    v.update_listener(player_id="cara", x=200, y=1.5, z=0)
    v.update_speaker(
        player_id="cara", x=200, y=1.5, z=0,
        channels={VoiceChannel.LINKSHELL},
    )
    v.set_linkshell(player_id="bob", linkshell_id="ls1")
    v.set_linkshell(player_id="cara", linkshell_id="ls2")
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is None


def test_shout_extends_range():
    v = VrVoiceProximity()
    v.update_listener(player_id="bob", x=0, y=1.5, z=0)
    v.update_listener(player_id="cara", x=60, y=1.5, z=0)
    v.update_speaker(
        player_id="cara", x=60, y=1.5, z=0,
        channels={VoiceChannel.PROXIMITY, VoiceChannel.SHOUT},
    )
    mix = v.resolve(listener_id="bob", talker_id="cara")
    assert mix is not None
    # 60y is within 30*3 = 90y SHOUT range
    assert mix.channel == VoiceChannel.SHOUT


def test_self_returns_none():
    v = _setup({"bob": (0, 1.5, 0)})
    assert v.resolve(
        listener_id="bob", talker_id="bob",
    ) is None


def test_unknown_listener():
    v = _setup({"bob": (0, 1.5, 0)})
    assert v.resolve(
        listener_id="ghost", talker_id="bob",
    ) is None


def test_unknown_talker():
    v = _setup({"bob": (0, 1.5, 0)})
    assert v.resolve(
        listener_id="bob", talker_id="ghost",
    ) is None


def test_audible_to_returns_all_audible():
    v = _setup({
        "bob": (0, 1.5, 0),
        "cara": (3, 1.5, 0),    # close
        "dave": (20, 1.5, 0),   # mid
        "evan": (100, 1.5, 0),  # too far
    })
    out = v.audible_to(listener_id="bob")
    pids = [p for p, _ in out]
    assert "cara" in pids
    assert "dave" in pids
    assert "evan" not in pids
    # Sorted by volume desc
    assert out[0][0] == "cara"


def test_update_speaker_blank_player_blocked():
    v = VrVoiceProximity()
    out = v.update_speaker(
        player_id="", x=0, y=1.5, z=0,
        channels={VoiceChannel.PROXIMITY},
    )
    assert out is False


def test_update_speaker_no_channels_blocked():
    v = VrVoiceProximity()
    out = v.update_speaker(
        player_id="bob", x=0, y=1.5, z=0, channels=set(),
    )
    assert out is False


def test_toggle_channel_returns_diff():
    v = VrVoiceProximity()
    v.update_listener(player_id="bob", x=0, y=1.5, z=0)
    # Default: subscribed to PROXIMITY/PARTY/LINKSHELL
    # so disabling proximity should return True (changed)
    assert v.toggle_channel(
        player_id="bob",
        channel=VoiceChannel.PROXIMITY, enabled=False,
    ) is True
    # Disabling again is no-change
    assert v.toggle_channel(
        player_id="bob",
        channel=VoiceChannel.PROXIMITY, enabled=False,
    ) is False


def test_clear_player():
    v = _setup({"bob": (0, 1.5, 0), "cara": (1, 1.5, 0)})
    assert v.clear(player_id="bob") is True
    out = v.audible_to(listener_id="bob")
    assert out == []  # no listener anymore


def test_four_voice_channels():
    assert len(list(VoiceChannel)) == 4
