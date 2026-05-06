"""Addon compat layer — Windower + Ashita as one API.

Both Windower 4 and Ashita are FFXI client addon platforms,
but their addon APIs differ in surface and shape:

    Windower:      windower.add_to_chat(8, "msg")
    Ashita:        AshitaCore:GetChatManager():AddChatMessage(8, false, "msg")

Players with Windower addons can't load Ashita addons
and vice versa. Demoncore unifies them: both APIs route
through this server-side compat layer to a single
canonical primitive set. An addon written against the
compat layer works on both, and an addon written against
either platform's native API translates through the
compat layer.

Eight canonical primitives cover ~90% of what addons do:
    chat_emit       send a chat-bar message
    chat_observe    register a callback on chat lines
    inv_query       read inventory contents
    gear_equip      equip a slot
    target_get      who is currently targeted
    spell_cast      enqueue a spell command
    party_query     party roster + status
    keybind_set     bind a key to a command

Each platform's native API maps to the canonical set, and
the compat layer ALSO offers the canonical names directly
so a forge-generated addon can target the compat layer
without referencing either platform.

Public surface
--------------
    Platform enum (WINDOWER/ASHITA/CANONICAL)
    ApiCall enum (the 8 canonical primitives)
    ApiSignature dataclass (frozen)
    AddonCompatLayer
        .register_native(platform, native_name, canonical) -> bool
        .resolve(platform, native_name) -> Optional[ApiCall]
        .canonical_signatures() -> dict[ApiCall, ApiSignature]
        .platforms_supporting(canonical) -> list[Platform]
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class Platform(str, enum.Enum):
    WINDOWER = "windower"
    ASHITA = "ashita"
    CANONICAL = "canonical"     # the compat layer's own surface


class ApiCall(str, enum.Enum):
    CHAT_EMIT = "chat_emit"
    CHAT_OBSERVE = "chat_observe"
    INV_QUERY = "inv_query"
    GEAR_EQUIP = "gear_equip"
    TARGET_GET = "target_get"
    SPELL_CAST = "spell_cast"
    PARTY_QUERY = "party_query"
    KEYBIND_SET = "keybind_set"


@dataclasses.dataclass(frozen=True)
class ApiSignature:
    canonical: ApiCall
    args: tuple[str, ...]    # named args in canonical order
    return_kind: str         # "void" / "table" / "string" / "int" / "bool"


_CANONICAL_SIGNATURES: dict[ApiCall, ApiSignature] = {
    ApiCall.CHAT_EMIT: ApiSignature(
        canonical=ApiCall.CHAT_EMIT,
        args=("color_id", "message"),
        return_kind="void",
    ),
    ApiCall.CHAT_OBSERVE: ApiSignature(
        canonical=ApiCall.CHAT_OBSERVE,
        args=("pattern", "callback_id"),
        return_kind="void",
    ),
    ApiCall.INV_QUERY: ApiSignature(
        canonical=ApiCall.INV_QUERY,
        args=("bag_id",),
        return_kind="table",
    ),
    ApiCall.GEAR_EQUIP: ApiSignature(
        canonical=ApiCall.GEAR_EQUIP,
        args=("slot", "item_id"),
        return_kind="bool",
    ),
    ApiCall.TARGET_GET: ApiSignature(
        canonical=ApiCall.TARGET_GET,
        args=(),
        return_kind="string",
    ),
    ApiCall.SPELL_CAST: ApiSignature(
        canonical=ApiCall.SPELL_CAST,
        args=("spell_name", "target_id"),
        return_kind="bool",
    ),
    ApiCall.PARTY_QUERY: ApiSignature(
        canonical=ApiCall.PARTY_QUERY,
        args=(),
        return_kind="table",
    ),
    ApiCall.KEYBIND_SET: ApiSignature(
        canonical=ApiCall.KEYBIND_SET,
        args=("key_combo", "command"),
        return_kind="void",
    ),
}


@dataclasses.dataclass
class AddonCompatLayer:
    # (platform, native_name) → canonical ApiCall
    _resolutions: dict[
        tuple[Platform, str], ApiCall,
    ] = dataclasses.field(default_factory=dict)

    def register_native(
        self, *, platform: Platform,
        native_name: str, canonical: ApiCall,
    ) -> bool:
        if not native_name:
            return False
        if platform == Platform.CANONICAL:
            # canonical names are intrinsic — no need to register
            return False
        key = (platform, native_name)
        if key in self._resolutions:
            return False
        self._resolutions[key] = canonical
        return True

    def resolve(
        self, *, platform: Platform, native_name: str,
    ) -> t.Optional[ApiCall]:
        if platform == Platform.CANONICAL:
            # The canonical layer accepts ApiCall name strings directly
            try:
                return ApiCall(native_name)
            except ValueError:
                return None
        return self._resolutions.get((platform, native_name))

    def canonical_signatures(
        self,
    ) -> dict[ApiCall, ApiSignature]:
        return dict(_CANONICAL_SIGNATURES)

    def platforms_supporting(
        self, *, canonical: ApiCall,
    ) -> list[Platform]:
        out: set[Platform] = set()
        # canonical layer always supports its own primitives
        out.add(Platform.CANONICAL)
        for (plat, _name), call in self._resolutions.items():
            if call == canonical:
                out.add(plat)
        return sorted(out, key=lambda p: p.value)

    def total_resolutions(self) -> int:
        return len(self._resolutions)


def default_compat_layer() -> AddonCompatLayer:
    """Bootstrap with canonical Windower + Ashita mappings."""
    layer = AddonCompatLayer()
    # Windower canonical names (windower.* namespace).
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.add_to_chat",
        canonical=ApiCall.CHAT_EMIT,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.register_event",
        canonical=ApiCall.CHAT_OBSERVE,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.ffxi.get_items",
        canonical=ApiCall.INV_QUERY,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.ffxi.set_equip",
        canonical=ApiCall.GEAR_EQUIP,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.ffxi.get_mob_by_target",
        canonical=ApiCall.TARGET_GET,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.send_command",
        canonical=ApiCall.SPELL_CAST,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.ffxi.get_party",
        canonical=ApiCall.PARTY_QUERY,
    )
    layer.register_native(
        platform=Platform.WINDOWER,
        native_name="windower.bind",
        canonical=ApiCall.KEYBIND_SET,
    )
    # Ashita canonical names (AshitaCore + addon.* shapes).
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetChatManager.AddChatMessage",
        canonical=ApiCall.CHAT_EMIT,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="ashita.events.register",
        canonical=ApiCall.CHAT_OBSERVE,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetMemoryManager.GetInventory",
        canonical=ApiCall.INV_QUERY,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetChatManager.QueueCommand_equip",
        canonical=ApiCall.GEAR_EQUIP,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetMemoryManager.GetTarget",
        canonical=ApiCall.TARGET_GET,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetChatManager.QueueCommand",
        canonical=ApiCall.SPELL_CAST,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetMemoryManager.GetParty",
        canonical=ApiCall.PARTY_QUERY,
    )
    layer.register_native(
        platform=Platform.ASHITA,
        native_name="AshitaCore.GetChatManager.QueueCommand_bind",
        canonical=ApiCall.KEYBIND_SET,
    )
    return layer


__all__ = [
    "Platform", "ApiCall", "ApiSignature",
    "AddonCompatLayer", "default_compat_layer",
]
