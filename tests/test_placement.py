"""EarthLink placement: a transform layer on top of the Rhino geometry, composed from viewer moves."""
import math
from earthlink.geometry import compose_placement


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
