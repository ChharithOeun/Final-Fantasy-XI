"""Telegraph shape geometry — pure containment math.

Coordinates are 2D (x, y) in centimeters; the elevation axis is
ignored for telegraph containment (a circle on the floor catches
anyone standing inside it horizontally regardless of height).

7 shapes per the design doc:
    circle      - classic AOE radius (Firaga, Cure, Banish)
    donut       - 'stand close to boss' (rare boss mechanic)
    cone        - breath weapons, sword arcs (variable angle 30-180)
    line        - spear thrust, dragon arc (rectangular along facing)
    square      - floor tile based abilities (rare)
    chevron     - charge attacks (elongated triangle along facing)
    irregular   - hand-authored polygon for unique boss attacks
"""
from __future__ import annotations

import enum
import math
import typing as t


class TelegraphShape(str, enum.Enum):
    CIRCLE = "circle"
    DONUT = "donut"
    CONE = "cone"
    LINE = "line"
    SQUARE = "square"
    CHEVRON = "chevron"
    IRREGULAR = "irregular"


# Type alias to keep annotations short
Point = tuple[float, float]


def _dist(a: Point, b: Point) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _angle_between(facing_deg: float, from_pt: Point, to_pt: Point) -> float:
    """Signed angular deviation (degrees) between the facing vector and
    the vector from `from_pt` to `to_pt`. Range -180..180."""
    dx = to_pt[0] - from_pt[0]
    dy = to_pt[1] - from_pt[1]
    target_deg = math.degrees(math.atan2(dy, dx))
    delta = target_deg - facing_deg
    # Normalize to -180..180
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta


def point_inside_telegraph(*,
                            shape: TelegraphShape,
                            origin: Point,
                            point: Point,
                            radius_cm: t.Optional[float] = None,
                            inner_radius_cm: t.Optional[float] = None,
                            length_cm: t.Optional[float] = None,
                            angle_deg: t.Optional[float] = None,
                            facing_deg: float = 0.0,
                            polygon: t.Optional[list[Point]] = None) -> bool:
    """Is `point` inside the telegraph centered at `origin`?

    Required parameters per shape:
        circle:    radius_cm
        donut:     radius_cm + inner_radius_cm
        cone:      radius_cm + angle_deg + facing_deg
        line:      radius_cm (= half-width) + length_cm + facing_deg
        square:    radius_cm (= half-side)
        chevron:   length_cm + angle_deg + facing_deg
        irregular: polygon (list of vertices)
    """
    if shape == TelegraphShape.CIRCLE:
        if radius_cm is None:
            raise ValueError("circle requires radius_cm")
        return _dist(origin, point) <= radius_cm

    if shape == TelegraphShape.DONUT:
        if radius_cm is None or inner_radius_cm is None:
            raise ValueError("donut requires radius_cm + inner_radius_cm")
        d = _dist(origin, point)
        return inner_radius_cm <= d <= radius_cm

    if shape == TelegraphShape.CONE:
        if radius_cm is None or angle_deg is None:
            raise ValueError("cone requires radius_cm + angle_deg")
        d = _dist(origin, point)
        if d > radius_cm:
            return False
        if d == 0:
            return True
        delta = _angle_between(facing_deg, origin, point)
        return abs(delta) <= angle_deg / 2

    if shape == TelegraphShape.LINE:
        if radius_cm is None or length_cm is None:
            raise ValueError("line requires radius_cm (half-width) + length_cm")
        # Translate + rotate the point into facing-aligned coordinates
        local = _to_local(origin, point, facing_deg)
        # Line lies along positive x in local coords
        return 0 <= local[0] <= length_cm and abs(local[1]) <= radius_cm

    if shape == TelegraphShape.SQUARE:
        if radius_cm is None:
            raise ValueError("square requires radius_cm (half-side)")
        # Axis-aligned around origin
        dx = abs(point[0] - origin[0])
        dy = abs(point[1] - origin[1])
        return dx <= radius_cm and dy <= radius_cm

    if shape == TelegraphShape.CHEVRON:
        if length_cm is None or angle_deg is None:
            raise ValueError("chevron requires length_cm + angle_deg")
        # Elongated triangle along facing direction
        local = _to_local(origin, point, facing_deg)
        if local[0] < 0 or local[0] > length_cm:
            return False
        # Width tapers from 0 at origin to length*tan(angle/2) at the tip
        max_width = local[0] * math.tan(math.radians(angle_deg / 2))
        return abs(local[1]) <= max_width

    if shape == TelegraphShape.IRREGULAR:
        if polygon is None:
            raise ValueError("irregular requires polygon")
        return _point_in_polygon(point, polygon)

    return False


def _to_local(origin: Point, point: Point, facing_deg: float) -> Point:
    """Translate `point` into facing-aligned local coordinates with
    `origin` at (0, 0) and facing along +x."""
    dx = point[0] - origin[0]
    dy = point[1] - origin[1]
    rad = math.radians(facing_deg)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)
    # Rotate by -facing_deg
    local_x = dx * cos_r + dy * sin_r
    local_y = -dx * sin_r + dy * cos_r
    return (local_x, local_y)


def _point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    """Standard ray-cast point-in-polygon for irregular shapes.

    Returns True if `point` lies inside the simple polygon defined
    by `polygon`'s vertices (in any winding order)."""
    if len(polygon) < 3:
        return False
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > point[1]) != (yj > point[1])):
            x_intersect = xi + (point[1] - yi) * (xj - xi) / (yj - yi)
            if point[0] < x_intersect:
                inside = not inside
        j = i
    return inside
