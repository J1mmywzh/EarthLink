"""EarthLink placement: a transform layer on top of the Rhino geometry, composed from viewer moves."""
import math
from earthlink.geometry import clean_placement, compose_placement, placed_location


def apply(p, x, y):
    a = math.radians(-p["rot"])
    return (x * math.cos(a) - y * math.sin(a) + p["t"][0], x * math.sin(a) + y * math.cos(a) + p["t"][1])


def move(x, y, dx, dy, rot, pivot):
    a = math.radians(-rot)
    return ((x - pivot[0]) * math.cos(a) - (y - pivot[1]) * math.sin(a) + pivot[0] + dx,
            (x - pivot[0]) * math.sin(a) + (y - pivot[1]) * math.cos(a) + pivot[1] + dy)


def test_two_viewer_moves_compose_into_one_placement():
    pts = [(0, 0), (40, 0), (40, 12), (3, 7)]
    p1 = compose_placement(None, dx=10, dy=5, rot=30, pivot=(20, 6, 0))
    p2 = compose_placement(p1, dx=-2, dy=1, rot=-12.5, pivot=(25, 3, 0))
    for x, y in pts:
        e = move(*move(x, y, 10, 5, 30, (20, 6)), -2, 1, -12.5, (25, 3))
        g = apply(p2, x, y)
        assert abs(g[0] - e[0]) < 1e-6 and abs(g[1] - e[1]) < 1e-6


def test_height_adds_and_undoing_a_move_clears_the_placement():
    p = compose_placement(None, dz=1.5, rot=90, pivot=(0, 0, 0))
    assert p["t"][2] == 1.5 and p["rot"] == 90
    assert compose_placement(p, dz=-1.5, rot=-90, pivot=(0, 0, 0)) is None


def test_angles_stay_in_range():
    p = compose_placement(None, rot=170)
    assert compose_placement(p, rot=30)["rot"] == -160


def test_stored_placement_is_normalised_and_empty_when_at_the_rhino_position():
    assert clean_placement(190, [1, 2]) == {"rot": -170.0, "t": [1.0, 2.0, 0.0]}
    assert clean_placement(0, [0, 0, 0]) is None and clean_placement(360, None) is None
    assert clean_placement(None, [0, 0, 0.5]) == {"rot": 0.0, "t": [0.0, 0.0, 0.5]}


def test_earth_pro_location_moves_by_the_placement():
    lat, lon = placed_location(42.44, -76.5, [100.0, -50.0, 0.0])
    assert abs((lat - 42.44) * 111_100 + 50) < 0.5                       # about 111.1 km per degree of latitude here
    assert abs((lon + 76.5) * 111_320 * math.cos(math.radians(42.44)) - 100) < 0.5
    assert placed_location(10.0, 20.0, [0, 0, 5]) == (10.0, 20.0)
