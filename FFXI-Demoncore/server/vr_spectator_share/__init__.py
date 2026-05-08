"""VR spectator share — non-VR friend watches your VR.

Tart's friend doesn't own a Quest but wants to watch
Tart fight a HNM in VR. This module turns Tart's
VR-stereo render into a "spectator stream" the friend
can subscribe to and watch on a flat monitor.

Two render modes:
    POV         spectator sees through the VR player's
                eyes — shaky-cam / motion-sickness risk
                for some viewers.
    SMOOTH      a virtual camera floats slightly behind
                + above the VR player's head, smoothed
                over a 0.4s window. Comfortable for
                viewers, no motion sickness.

The HOST opts in (start_share()), picks the mode, and
optionally adds a delay (3s default — gives them time
to react if they show something private). VIEWERS
subscribe; the host can revoke individual viewers or
end the share entirely.

Frame data is NOT actually carried in this module —
that's the streaming pipeline. We're the membership
+ permission + quality-state layer.

Public surface
--------------
    ShareMode enum
    ShareState dataclass (frozen)
    SpectatorTicket dataclass (frozen)
    VrSpectatorShare
        .start_share(host_id, mode, delay_seconds=3) -> bool
        .stop_share(host_id) -> bool
        .add_viewer(host_id, viewer_id) -> bool
        .remove_viewer(host_id, viewer_id) -> bool
        .change_mode(host_id, mode) -> bool
        .can_view(host_id, viewer_id) -> bool
        .ticket(host_id, viewer_id) -> Optional[SpectatorTicket]
        .active_hosts() -> list[str]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_DEFAULT_DELAY_S = 3
_MAX_DELAY_S = 30
_MAX_VIEWERS_PER_HOST = 50


class ShareMode(str, enum.Enum):
    POV = "pov"
    SMOOTH = "smooth"


@dataclasses.dataclass(frozen=True)
class ShareState:
    host_id: str
    mode: ShareMode
    delay_seconds: int


@dataclasses.dataclass(frozen=True)
class SpectatorTicket:
    host_id: str
    viewer_id: str
    mode: ShareMode
    delay_seconds: int


@dataclasses.dataclass
class _ShareInternal:
    state: ShareState
    viewers: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass
class VrSpectatorShare:
    _shares: dict[str, _ShareInternal] = dataclasses.field(
        default_factory=dict,
    )

    def start_share(
        self, *, host_id: str, mode: ShareMode,
        delay_seconds: int = _DEFAULT_DELAY_S,
    ) -> bool:
        if not host_id:
            return False
        if delay_seconds < 0 or delay_seconds > _MAX_DELAY_S:
            return False
        if host_id in self._shares:
            return False
        self._shares[host_id] = _ShareInternal(
            state=ShareState(
                host_id=host_id, mode=mode,
                delay_seconds=delay_seconds,
            ),
        )
        return True

    def stop_share(self, *, host_id: str) -> bool:
        if host_id not in self._shares:
            return False
        del self._shares[host_id]
        return True

    def add_viewer(
        self, *, host_id: str, viewer_id: str,
    ) -> bool:
        if host_id not in self._shares:
            return False
        if not viewer_id:
            return False
        if viewer_id == host_id:
            return False
        share = self._shares[host_id]
        if viewer_id in share.viewers:
            return False
        if len(share.viewers) >= _MAX_VIEWERS_PER_HOST:
            return False
        share.viewers.add(viewer_id)
        return True

    def remove_viewer(
        self, *, host_id: str, viewer_id: str,
    ) -> bool:
        if host_id not in self._shares:
            return False
        share = self._shares[host_id]
        if viewer_id not in share.viewers:
            return False
        share.viewers.remove(viewer_id)
        return True

    def change_mode(
        self, *, host_id: str, mode: ShareMode,
    ) -> bool:
        if host_id not in self._shares:
            return False
        share = self._shares[host_id]
        if share.state.mode == mode:
            return False
        share.state = ShareState(
            host_id=host_id, mode=mode,
            delay_seconds=share.state.delay_seconds,
        )
        return True

    def can_view(
        self, *, host_id: str, viewer_id: str,
    ) -> bool:
        if host_id not in self._shares:
            return False
        return viewer_id in self._shares[host_id].viewers

    def ticket(
        self, *, host_id: str, viewer_id: str,
    ) -> t.Optional[SpectatorTicket]:
        if not self.can_view(
            host_id=host_id, viewer_id=viewer_id,
        ):
            return None
        share = self._shares[host_id]
        return SpectatorTicket(
            host_id=host_id, viewer_id=viewer_id,
            mode=share.state.mode,
            delay_seconds=share.state.delay_seconds,
        )

    def active_hosts(self) -> list[str]:
        return sorted(self._shares.keys())

    def viewers_of(self, *, host_id: str) -> list[str]:
        if host_id not in self._shares:
            return []
        return sorted(self._shares[host_id].viewers)


__all__ = [
    "ShareMode", "ShareState", "SpectatorTicket",
    "VrSpectatorShare",
]
