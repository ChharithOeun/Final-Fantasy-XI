"""Nation assets forfeit — property/titles seized on defection.

When an officer defects, the nation they leave can
SEIZE assets tied to them: real estate, official
titles, public funds in their name, ceremonial gear,
and sometimes inherited honors.

This module manages a per-NPC ASSET REGISTRY and a
SEIZURE LIFECYCLE. Some asset kinds auto-forfeit on
defection; others require a council vote (we expose a
flag, the caller routes to nation_council_advisory).

Asset kinds:
    REAL_ESTATE        Mog House plot / private manor
    OFFICIAL_TITLE     "Knight Commander", "Court
                       Mage", etc.
    GIL_ACCOUNT        public-treasury sub-account
    CEREMONIAL_GEAR    AF / nation-issued artifact
    INHERITED_HONOR    grandfathered nobility status
    PENSION            retirement entitlement

Seizure states:
    INTACT             still held by NPC, untouched
    FROZEN             temporarily blocked pending
                       review
    SEIZED             nation has taken it
    RETURNED           restored to NPC after appeal /
                       diplomatic settlement

Public surface
--------------
    AssetKind enum
    SeizureState enum
    Asset dataclass (frozen)
    NationAssetsForfeitSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_AUTO_FORFEIT_KINDS = {
    "official_title", "ceremonial_gear",
}


class AssetKind(str, enum.Enum):
    REAL_ESTATE = "real_estate"
    OFFICIAL_TITLE = "official_title"
    GIL_ACCOUNT = "gil_account"
    CEREMONIAL_GEAR = "ceremonial_gear"
    INHERITED_HONOR = "inherited_honor"
    PENSION = "pension"


class SeizureState(str, enum.Enum):
    INTACT = "intact"
    FROZEN = "frozen"
    SEIZED = "seized"
    RETURNED = "returned"


@dataclasses.dataclass(frozen=True)
class Asset:
    asset_id: str
    npc_id: str
    nation_id: str
    kind: AssetKind
    description: str
    value_gil: int
    state: SeizureState
    state_reason: str
    state_changed_day: t.Optional[int]


@dataclasses.dataclass
class NationAssetsForfeitSystem:
    _assets: dict[str, Asset] = dataclasses.field(
        default_factory=dict,
    )

    def register_asset(
        self, *, asset_id: str, npc_id: str,
        nation_id: str, kind: AssetKind,
        description: str, value_gil: int,
    ) -> bool:
        if not asset_id or not npc_id:
            return False
        if not nation_id or not description:
            return False
        if value_gil < 0:
            return False
        if asset_id in self._assets:
            return False
        self._assets[asset_id] = Asset(
            asset_id=asset_id, npc_id=npc_id,
            nation_id=nation_id, kind=kind,
            description=description,
            value_gil=value_gil,
            state=SeizureState.INTACT,
            state_reason="",
            state_changed_day=None,
        )
        return True

    def freeze(
        self, *, asset_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if asset_id not in self._assets:
            return False
        if not reason:
            return False
        a = self._assets[asset_id]
        if a.state != SeizureState.INTACT:
            return False
        self._assets[asset_id] = dataclasses.replace(
            a, state=SeizureState.FROZEN,
            state_reason=reason,
            state_changed_day=now_day,
        )
        return True

    def seize(
        self, *, asset_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if asset_id not in self._assets:
            return False
        if not reason:
            return False
        a = self._assets[asset_id]
        if a.state not in (
            SeizureState.INTACT, SeizureState.FROZEN,
        ):
            return False
        self._assets[asset_id] = dataclasses.replace(
            a, state=SeizureState.SEIZED,
            state_reason=reason,
            state_changed_day=now_day,
        )
        return True

    def returns(
        self, *, asset_id: str, now_day: int,
        reason: str,
    ) -> bool:
        if asset_id not in self._assets:
            return False
        if not reason:
            return False
        a = self._assets[asset_id]
        if a.state not in (
            SeizureState.FROZEN,
            SeizureState.SEIZED,
        ):
            return False
        self._assets[asset_id] = dataclasses.replace(
            a, state=SeizureState.RETURNED,
            state_reason=reason,
            state_changed_day=now_day,
        )
        return True

    def auto_forfeit_on_defection(
        self, *, npc_id: str, now_day: int,
    ) -> list[str]:
        """Auto-seize INTACT assets whose kind is in
        the auto-forfeit set. Returns list of seized
        asset_ids.
        """
        seized: list[str] = []
        for aid, a in list(self._assets.items()):
            if a.npc_id != npc_id:
                continue
            if a.state != SeizureState.INTACT:
                continue
            if a.kind.value not in _AUTO_FORFEIT_KINDS:
                continue
            self._assets[aid] = dataclasses.replace(
                a, state=SeizureState.SEIZED,
                state_reason="auto_defection",
                state_changed_day=now_day,
            )
            seized.append(aid)
        return seized

    def freeze_pending_review_on_defection(
        self, *, npc_id: str, now_day: int,
    ) -> list[str]:
        """Freeze INTACT non-auto-forfeit assets
        pending council vote.
        """
        frozen: list[str] = []
        for aid, a in list(self._assets.items()):
            if a.npc_id != npc_id:
                continue
            if a.state != SeizureState.INTACT:
                continue
            if a.kind.value in _AUTO_FORFEIT_KINDS:
                continue
            self._assets[aid] = dataclasses.replace(
                a, state=SeizureState.FROZEN,
                state_reason="defection_review",
                state_changed_day=now_day,
            )
            frozen.append(aid)
        return frozen

    def asset(
        self, *, asset_id: str,
    ) -> t.Optional[Asset]:
        return self._assets.get(asset_id)

    def assets_for_npc(
        self, *, npc_id: str,
    ) -> list[Asset]:
        return [
            a for a in self._assets.values()
            if a.npc_id == npc_id
        ]

    def total_seized_value(
        self, *, npc_id: str,
    ) -> int:
        return sum(
            a.value_gil
            for a in self._assets.values()
            if (a.npc_id == npc_id
                and a.state == SeizureState.SEIZED)
        )


__all__ = [
    "AssetKind", "SeizureState", "Asset",
    "NationAssetsForfeitSystem",
]
