"""Player restaurant — owner-run eateries with menus & staff.

A player owner founds a restaurant. They publish a menu of
dishes (each with price and cooking_skill_required), hire
waitstaff who collect a per-order wage, and serve customers.
Each order pays the dish price; the waitstaff handling the
order takes a flat wage; the owner banks the rest as
revenue. Closing the restaurant prevents new orders but
preserves the historical record.

Lifecycle
    OPEN          accepting orders
    CLOSED        wound down

Public surface
--------------
    RestaurantState enum
    Restaurant dataclass (frozen)
    Dish dataclass (frozen)
    PlayerRestaurantSystem
"""
from __future__ import annotations

import dataclasses
import enum
import typing as t


_WAGE_PER_ORDER = 20


class RestaurantState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclasses.dataclass(frozen=True)
class Restaurant:
    restaurant_id: str
    owner_id: str
    name: str
    state: RestaurantState
    revenue_gil: int
    orders_filled: int


@dataclasses.dataclass(frozen=True)
class Dish:
    dish_id: str
    name: str
    price_gil: int
    cooking_skill_required: int


@dataclasses.dataclass
class _RState:
    spec: Restaurant
    menu: dict[str, Dish] = dataclasses.field(
        default_factory=dict,
    )
    waitstaff: set[str] = dataclasses.field(
        default_factory=set,
    )
    waitstaff_earnings: dict[str, int] = (
        dataclasses.field(default_factory=dict)
    )


@dataclasses.dataclass
class PlayerRestaurantSystem:
    _restaurants: dict[str, _RState] = (
        dataclasses.field(default_factory=dict)
    )
    _next_r: int = 1
    _next_d: int = 1

    def found_restaurant(
        self, *, owner_id: str, name: str,
    ) -> t.Optional[str]:
        if not owner_id or not name:
            return None
        rid = f"rest_{self._next_r}"
        self._next_r += 1
        self._restaurants[rid] = _RState(
            spec=Restaurant(
                restaurant_id=rid, owner_id=owner_id,
                name=name, state=RestaurantState.OPEN,
                revenue_gil=0, orders_filled=0,
            ),
        )
        return rid

    def add_dish(
        self, *, restaurant_id: str, name: str,
        price_gil: int, cooking_skill_required: int,
    ) -> t.Optional[str]:
        if restaurant_id not in self._restaurants:
            return None
        st = self._restaurants[restaurant_id]
        if st.spec.state != RestaurantState.OPEN:
            return None
        if not name:
            return None
        if price_gil <= _WAGE_PER_ORDER:
            return None
        if cooking_skill_required < 0:
            return None
        did = f"dish_{self._next_d}"
        self._next_d += 1
        st.menu[did] = Dish(
            dish_id=did, name=name,
            price_gil=price_gil,
            cooking_skill_required=(
                cooking_skill_required
            ),
        )
        return did

    def hire_waitstaff(
        self, *, restaurant_id: str, staff_id: str,
    ) -> bool:
        if restaurant_id not in self._restaurants:
            return False
        st = self._restaurants[restaurant_id]
        if st.spec.state != RestaurantState.OPEN:
            return False
        if not staff_id:
            return False
        if staff_id == st.spec.owner_id:
            return False
        if staff_id in st.waitstaff:
            return False
        st.waitstaff.add(staff_id)
        st.waitstaff_earnings[staff_id] = 0
        return True

    def fire_waitstaff(
        self, *, restaurant_id: str, staff_id: str,
    ) -> bool:
        if restaurant_id not in self._restaurants:
            return False
        st = self._restaurants[restaurant_id]
        if staff_id not in st.waitstaff:
            return False
        st.waitstaff.remove(staff_id)
        return True

    def order_dish(
        self, *, restaurant_id: str, dish_id: str,
        customer_id: str, staff_id: str,
        cook_skill: int,
    ) -> t.Optional[int]:
        """Returns the gil paid by the customer
        (= dish price). Owner gains price-wage,
        staff gains wage."""
        if restaurant_id not in self._restaurants:
            return None
        st = self._restaurants[restaurant_id]
        if st.spec.state != RestaurantState.OPEN:
            return None
        if dish_id not in st.menu:
            return None
        if not customer_id:
            return None
        if customer_id == st.spec.owner_id:
            return None
        if staff_id not in st.waitstaff:
            return None
        dish = st.menu[dish_id]
        if cook_skill < dish.cooking_skill_required:
            return None
        st.waitstaff_earnings[staff_id] += (
            _WAGE_PER_ORDER
        )
        st.spec = dataclasses.replace(
            st.spec,
            revenue_gil=(
                st.spec.revenue_gil
                + dish.price_gil
                - _WAGE_PER_ORDER
            ),
            orders_filled=st.spec.orders_filled + 1,
        )
        return dish.price_gil

    def close_restaurant(
        self, *, restaurant_id: str, owner_id: str,
    ) -> bool:
        if restaurant_id not in self._restaurants:
            return False
        st = self._restaurants[restaurant_id]
        if st.spec.state != RestaurantState.OPEN:
            return False
        if st.spec.owner_id != owner_id:
            return False
        st.spec = dataclasses.replace(
            st.spec, state=RestaurantState.CLOSED,
        )
        return True

    def restaurant(
        self, *, restaurant_id: str,
    ) -> t.Optional[Restaurant]:
        st = self._restaurants.get(restaurant_id)
        return st.spec if st else None

    def menu(
        self, *, restaurant_id: str,
    ) -> list[Dish]:
        st = self._restaurants.get(restaurant_id)
        if st is None:
            return []
        return list(st.menu.values())

    def waitstaff(
        self, *, restaurant_id: str,
    ) -> list[str]:
        st = self._restaurants.get(restaurant_id)
        if st is None:
            return []
        return sorted(st.waitstaff)

    def staff_earnings(
        self, *, restaurant_id: str, staff_id: str,
    ) -> int:
        st = self._restaurants.get(restaurant_id)
        if st is None:
            return 0
        return st.waitstaff_earnings.get(staff_id, 0)


__all__ = [
    "RestaurantState", "Restaurant", "Dish",
    "PlayerRestaurantSystem",
]
