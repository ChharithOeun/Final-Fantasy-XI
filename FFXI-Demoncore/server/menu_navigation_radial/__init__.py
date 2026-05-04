"""Menu navigation radial — turn-based menu, same logic as palette.

Old-school FFXI menus felt like a turn-based JRPG: pick from a
list, drill down, back out. Demoncore preserves that feel but
arranges menu items in a CIRCLE (same logic as the macro
palette). Players cycle items with directional input or aim
the analog stick at one. Drilling INTO an item pushes a child
menu onto a stack; BACK pops it.

Public surface
--------------
    NavInput enum
    MenuItem dataclass
    MenuNode dataclass
    NavState dataclass
    MenuNavigationRadial
        .define_menu(menu_id, items, label)
        .open_root(player_id, menu_id)
        .input(player_id, NavInput) -> Optional[MenuItem confirmed]
        .point_to(player_id, slot_index)
        .back(player_id)
        .close(player_id)
        .current_node(player_id)
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


class NavInput(str, enum.Enum):
    NEXT = "next"        # cycle next slot
    PREV = "prev"        # cycle prev slot
    CONFIRM = "confirm"
    BACK = "back"
    CLOSE = "close"


@dataclasses.dataclass(frozen=True)
class MenuItem:
    item_id: str
    label: str
    drill_into: t.Optional[str] = None   # menu_id of child menu
    payload: str = ""                    # opaque ID
    enabled: bool = True


@dataclasses.dataclass
class MenuNode:
    menu_id: str
    label: str
    items: tuple[MenuItem, ...]


@dataclasses.dataclass
class NavState:
    player_id: str
    stack: list[str] = dataclasses.field(
        default_factory=list,
    )
    highlighted_index: int = 0


@dataclasses.dataclass(frozen=True)
class ConfirmResult:
    accepted: bool
    item: t.Optional[MenuItem] = None
    drilled_into: bool = False
    note: str = ""


@dataclasses.dataclass
class MenuNavigationRadial:
    _menus: dict[str, MenuNode] = dataclasses.field(
        default_factory=dict,
    )
    _states: dict[str, NavState] = dataclasses.field(
        default_factory=dict,
    )

    def define_menu(
        self, *, menu_id: str, label: str,
        items: tuple[MenuItem, ...],
    ) -> t.Optional[MenuNode]:
        if menu_id in self._menus:
            return None
        if not items:
            return None
        node = MenuNode(
            menu_id=menu_id, label=label, items=items,
        )
        self._menus[menu_id] = node
        return node

    def open_root(
        self, *, player_id: str, menu_id: str,
    ) -> bool:
        if menu_id not in self._menus:
            return False
        st = NavState(
            player_id=player_id,
            stack=[menu_id],
            highlighted_index=0,
        )
        self._states[player_id] = st
        return True

    def close(self, *, player_id: str) -> bool:
        return self._states.pop(player_id, None) is not None

    def current_node(
        self, *, player_id: str,
    ) -> t.Optional[MenuNode]:
        st = self._states.get(player_id)
        if st is None or not st.stack:
            return None
        return self._menus.get(st.stack[-1])

    def state_for(
        self, player_id: str,
    ) -> t.Optional[NavState]:
        return self._states.get(player_id)

    def point_to(
        self, *, player_id: str, slot_index: int,
    ) -> bool:
        node = self.current_node(player_id=player_id)
        if node is None:
            return False
        if not (0 <= slot_index < len(node.items)):
            return False
        self._states[player_id].highlighted_index = (
            slot_index
        )
        return True

    def input(
        self, *, player_id: str,
        action: NavInput,
    ) -> t.Optional[ConfirmResult]:
        st = self._states.get(player_id)
        if st is None:
            return None
        if action == NavInput.CLOSE:
            self.close(player_id=player_id)
            return ConfirmResult(
                accepted=True, note="closed",
            )
        node = self.current_node(player_id=player_id)
        if node is None:
            return None
        if action == NavInput.NEXT:
            st.highlighted_index = (
                st.highlighted_index + 1
            ) % len(node.items)
            return ConfirmResult(accepted=True)
        if action == NavInput.PREV:
            st.highlighted_index = (
                st.highlighted_index - 1
            ) % len(node.items)
            return ConfirmResult(accepted=True)
        if action == NavInput.BACK:
            if len(st.stack) <= 1:
                return ConfirmResult(
                    accepted=False, note="at root",
                )
            st.stack.pop()
            st.highlighted_index = 0
            return ConfirmResult(
                accepted=True, note="popped",
            )
        if action == NavInput.CONFIRM:
            item = node.items[st.highlighted_index]
            if not item.enabled:
                return ConfirmResult(
                    accepted=False, item=item,
                    note="item disabled",
                )
            if item.drill_into is not None:
                if item.drill_into not in self._menus:
                    return ConfirmResult(
                        accepted=False, item=item,
                        note="drill target not defined",
                    )
                st.stack.append(item.drill_into)
                st.highlighted_index = 0
                return ConfirmResult(
                    accepted=True, item=item,
                    drilled_into=True,
                )
            return ConfirmResult(
                accepted=True, item=item,
                drilled_into=False,
            )
        return None

    def total_menus(self) -> int:
        return len(self._menus)


__all__ = [
    "NavInput",
    "MenuItem", "MenuNode", "NavState",
    "ConfirmResult",
    "MenuNavigationRadial",
]
