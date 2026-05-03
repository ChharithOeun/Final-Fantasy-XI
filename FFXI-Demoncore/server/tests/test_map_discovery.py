"""Tests for map discovery / fog of war."""
from __future__ import annotations

import pytest

from server.map_discovery import (
    DEFAULT_FIRST_DISCOVERY_HONOR,
    DiscoveryMethod,
    Landmark,
    MapRegistry,
    ZoneMapDef,
)


def _zone(
    zone_id: str = "ronfaure", total_chunks: int = 16,
) -> ZoneMapDef:
    return ZoneMapDef(
        zone_id=zone_id, label="East Ronfaure",
        total_chunks=total_chunks,
        purchase_price_gil=5000, region="san_doria",
    )


def test_register_zone_validation():
    reg = MapRegistry()
    with pytest.raises(ValueError):
        reg.register_zone(ZoneMapDef(
            zone_id="bad", label="x", total_chunks=0,
        ))


def test_register_zone_lookup():
    reg = MapRegistry()
    reg.register_zone(_zone())
    assert reg.zone("ronfaure") is not None
    assert reg.total_zones() == 1


def test_register_landmark_lookup():
    reg = MapRegistry()
    reg.register_zone(_zone())
    lm = Landmark(
        landmark_id="lm_crag", label="Crag of Holla",
        zone_id="ronfaure", title_id="title_holla_pilgrim",
    )
    reg.register_landmark(lm)
    assert reg.landmark("lm_crag") is lm
    assert reg.total_landmarks() == 1


def test_landmarks_in_zone_filters():
    reg = MapRegistry()
    reg.register_zone(_zone())
    reg.register_zone(_zone(zone_id="other"))
    reg.register_landmark(Landmark(
        landmark_id="a", label="A", zone_id="ronfaure",
    ))
    reg.register_landmark(Landmark(
        landmark_id="b", label="B", zone_id="other",
    ))
    in_ronfaure = reg.landmarks_in_zone("ronfaure")
    assert len(in_ronfaure) == 1
    assert in_ronfaure[0].landmark_id == "a"


def test_player_state_lazy_create():
    reg = MapRegistry()
    s = reg.player("alice")
    assert s.player_id == "alice"
    assert reg.player("alice") is s


def test_visit_zone_chunk_marks_new():
    reg = MapRegistry()
    s = reg.player("alice")
    assert s.visit_zone_chunk(zone_id="ronfaure", chunk_id=0)
    assert not s.visit_zone_chunk(
        zone_id="ronfaure", chunk_id=0,
    )
    assert s.chunks_seen("ronfaure") == 1


def test_has_zone_after_first_chunk():
    reg = MapRegistry()
    s = reg.player("alice")
    assert not s.has_zone("ronfaure")
    s.visit_zone_chunk(zone_id="ronfaure", chunk_id=3)
    assert s.has_zone("ronfaure")


def test_grant_full_map_purchased():
    reg = MapRegistry()
    s = reg.player("alice")
    s.grant_full_map(
        zone_id="ronfaure", method=DiscoveryMethod.PURCHASED,
    )
    assert s.own_full_map("ronfaure")
    assert s.has_zone("ronfaure")


def test_coverage_pct_partial():
    reg = MapRegistry()
    reg.register_zone(_zone(total_chunks=16))
    s = reg.player("alice")
    for c in (0, 1, 2, 3):
        s.visit_zone_chunk(zone_id="ronfaure", chunk_id=c)
    pct = reg.coverage_pct(
        player_id="alice", zone_id="ronfaure",
    )
    assert pct == 25


def test_coverage_pct_full_when_purchased():
    reg = MapRegistry()
    reg.register_zone(_zone(total_chunks=16))
    s = reg.player("alice")
    s.grant_full_map(
        zone_id="ronfaure", method=DiscoveryMethod.PURCHASED,
    )
    assert reg.coverage_pct(
        player_id="alice", zone_id="ronfaure",
    ) == 100


def test_coverage_pct_unknown_zone_zero():
    reg = MapRegistry()
    assert reg.coverage_pct(
        player_id="alice", zone_id="ghost",
    ) == 0


def test_first_discovery_reward_grants_once():
    reg = MapRegistry()
    reg.register_zone(_zone())
    reg.register_landmark(Landmark(
        landmark_id="lm_crag", label="Crag of Holla",
        zone_id="ronfaure", title_id="title_holla_pilgrim",
        honor_reward=10,
    ))
    res = reg.first_discovery_reward(
        player_id="alice", landmark_id="lm_crag",
        now_seconds=0.0,
    )
    assert res.accepted
    assert res.honor_gained == 10
    assert res.title_id == "title_holla_pilgrim"
    # Second time = nothing
    res2 = reg.first_discovery_reward(
        player_id="alice", landmark_id="lm_crag",
        now_seconds=10.0,
    )
    assert not res2.accepted
    assert "already" in res2.reason


def test_first_discovery_unknown_landmark():
    reg = MapRegistry()
    res = reg.first_discovery_reward(
        player_id="alice", landmark_id="ghost",
    )
    assert not res.accepted


def test_default_honor_reward():
    reg = MapRegistry()
    reg.register_landmark(Landmark(
        landmark_id="basic", label="x", zone_id="ronfaure",
    ))
    res = reg.first_discovery_reward(
        player_id="alice", landmark_id="basic",
    )
    assert res.honor_gained == DEFAULT_FIRST_DISCOVERY_HONOR


def test_total_zones_seen_via_chunks_or_full_map():
    reg = MapRegistry()
    s = reg.player("alice")
    s.visit_zone_chunk(zone_id="zone_a", chunk_id=0)
    s.grant_full_map(
        zone_id="zone_b", method=DiscoveryMethod.PURCHASED,
    )
    assert s.total_zones_seen() == 2


def test_full_lifecycle_alice_explores_san_doria_region():
    """Alice walks through East Ronfaure chunk by chunk, hits
    the Crag of Holla landmark, then later buys the Konschtat
    map from a cartographer."""
    reg = MapRegistry()
    reg.register_zone(_zone(total_chunks=16))
    reg.register_zone(_zone(zone_id="konschtat", total_chunks=16))
    reg.register_landmark(Landmark(
        landmark_id="lm_crag", label="Crag of Holla",
        zone_id="ronfaure", honor_reward=10,
    ))
    s = reg.player("alice")
    # Chunk by chunk
    for c in range(8):
        s.visit_zone_chunk(zone_id="ronfaure", chunk_id=c)
    pct = reg.coverage_pct(
        player_id="alice", zone_id="ronfaure",
    )
    assert pct == 50
    # Hit landmark
    landmark_res = reg.first_discovery_reward(
        player_id="alice", landmark_id="lm_crag",
        now_seconds=100.0,
    )
    assert landmark_res.accepted
    assert landmark_res.honor_gained == 10
    # Buy konschtat map
    s.grant_full_map(
        zone_id="konschtat", method=DiscoveryMethod.PURCHASED,
    )
    assert reg.coverage_pct(
        player_id="alice", zone_id="konschtat",
    ) == 100
    # Total zones seen
    assert s.total_zones_seen() == 2
