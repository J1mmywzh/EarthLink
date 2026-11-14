"""Site context from open data, for Rhino: terrain, contours, building massing, roads, paths, railways and water inside a
rectangle, much as CADMapper offers it (roads as centrelines, outlines or surfaces).

Pure Python, run by the local server (never inside Rhino's interface thread). Sources, both free to export:
  * OpenStreetMap (buildings, roads): the map download openstreetmap.org's own Export uses, one request for a
    rectangle someone drew (more only when the area holds over 50,000 points); the public Overpass servers are the
    fallback. Data (c) OpenStreetMap contributors, ODbL.
  * Terrain Tiles on AWS Open Data ("terrarium" elevation tiles, from Mapzen): USGS 3DEP, SRTM and others.
Google's map is not used: its terms forbid exporting its content.

Everything is returned in metres east / north / up of the model base point (the EarthAnchorPoint), so Rhino only has
to undo its own model-to-site transform. The terrain is hung on the map's ground: the elevation model's height at the
site location is matched to the ground height EarthLink sampled there, so the imported terrain sits where the map's
ground is, whatever the elevation model's datum.
"""
import json
import math
import struct
import urllib.error
import urllib.parse
import urllib.request
import zlib

OSM_MAP = "https://api.openstreetmap.org/api/0.6/map.json?bbox=%.7f,%.7f,%.7f,%.7f"     # west, south, east, north
OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
TERRAIN = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ATTRIBUTION = ("Buildings, roads, railways and water (c) OpenStreetMap contributors, ODbL. "
               "Terrain: Terrain Tiles (Mapzen, AWS Open Data; USGS 3DEP, SRTM and other sources).")
MAX_SIDE, MIN_SIDE = 3000.0, 20.0          # metres
MAX_ZOOM, GRID = 15, 200                   # elevation tiles stop at zoom 15; at most GRID cells along the longer side
PAD = 200.0                                # metres of OpenStreetMap asked for around the rectangle (see fetch_osm)
LEVEL, DEFAULT_HEIGHT = 3.2, 7.0           # metres per storey; height of a building OpenStreetMap gives no height for
A, E2 = 6378137.0, 6.69437999014e-3        # WGS84

# What an OpenStreetMap line is drawn as. highway value -> (layer, usual width kerb to kerb in metres); a way's own
# width or lanes tag wins over the usual width. Layers as CADMapper has them: major roads, minor roads and paths.
ROADS = {"motorway": ("major", 14.0), "trunk": ("major", 12.0), "primary": ("major", 11.0), "secondary": ("major", 10.0),
         "motorway_link": ("major", 6.0), "trunk_link": ("major", 6.0), "primary_link": ("major", 6.0), "secondary_link": ("major", 6.0),
         "tertiary": ("minor", 8.0), "tertiary_link": ("minor", 6.0), "residential": ("minor", 7.0), "unclassified": ("minor", 6.0),
         "living_street": ("minor", 6.0), "road": ("minor", 6.0), "busway": ("minor", 6.0), "service": ("minor", 4.5),
         "track": ("minor", 3.5), "pedestrian": ("path", 5.0), "footway": ("path", 2.0), "path": ("path", 1.8),
         "cycleway": ("path", 2.2), "bridleway": ("path", 2.0), "steps": ("path", 2.0), "corridor": ("path", 2.0)}
LANE = 3.3                                 # metres a lane
RAILS = {"rail", "light_rail", "subway", "tram", "narrow_gauge", "monorail", "funicular", "preserved", "miniature"}
WATERWAYS = {"river", "stream", "canal", "drain", "ditch", "brook", "tidal_channel"}
STYLES = ("lines", "outlines", "surfaces")  # road geometry: centrelines, closed outlines, mesh surfaces
LIFT = {"major": 0.12, "minor": 0.08, "path": 0.04}   # road surfaces sit this much above the ground, the bigger road on top


class ContextError(Exception):
    pass


# ----------------------------------------------------------------- geodesy
def _ecef(lat, lon, h):
    la, lo = math.radians(lat), math.radians(lon)
    n = A / math.sqrt(1.0 - E2 * math.sin(la) ** 2)
    return ((n + h) * math.cos(la) * math.cos(lo), (n + h) * math.cos(la) * math.sin(lo), (n * (1.0 - E2) + h) * math.sin(la))


def enu(lat, lon, h, lat0, lon0):
    """East, north, up (m) of a point `h` m above the ellipsoid surface level of the origin (lat0, lon0, 0)."""
    x, y, z = _ecef(lat, lon, h)
    x0, y0, z0 = _ecef(lat0, lon0, 0.0)
    dx, dy, dz = x - x0, y - y0, z - z0
    la, lo = math.radians(lat0), math.radians(lon0)
    return (-math.sin(lo) * dx + math.cos(lo) * dy,
            -math.sin(la) * math.cos(lo) * dx - math.sin(la) * math.sin(lo) * dy + math.cos(la) * dz,
            math.cos(la) * math.cos(lo) * dx + math.cos(la) * math.sin(lo) * dy + math.sin(la) * dz)


def side_lengths(b):
    """Width and height (m) of a west/south/east/north rectangle."""
    mid = (b["south"] + b["north"]) / 2.0
    w = enu(mid, b["east"], 0, mid, b["west"])[0]
    h = enu(b["north"], b["west"], 0, b["south"], b["west"])[1]
    return abs(w), abs(h)


def check_bounds(b):
    try:
        b = {k: float(b[k]) for k in ("west", "south", "east", "north")}
    except (KeyError, TypeError, ValueError):
        raise ContextError("Draw a rectangle on the map first.")
    if not all(math.isfinite(v) for v in b.values()) or not (-85 < b["south"] < b["north"] < 85) or not (-180 <= b["west"] < b["east"] <= 180):
        raise ContextError("That rectangle is not valid.")
    w, h = side_lengths(b)
    if max(w, h) > MAX_SIDE:
        raise ContextError("The rectangle is %.0f x %.0f m; the limit is %.0f m a side." % (w, h, MAX_SIDE))
    if min(w, h) < MIN_SIDE:
        raise ContextError("The rectangle is too small (under %.0f m)." % MIN_SIDE)
    return b


# ----------------------------------------------------------------- elevation tiles
def decode_png(data):
    """Rows of (r, g, b) from an 8-bit RGB or RGBA, non-interlaced PNG (what the elevation tiles are)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ContextError("The elevation tile is not a PNG.")
    pos, idat, head = 8, [], None
    while pos + 8 <= len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    if not head or head[2] != 8 or head[3] not in (2, 6) or head[6] != 0:
        raise ContextError("The elevation tile has an unexpected format.")
    w, h, bpp = head[0], head[1], 3 if head[3] == 2 else 4
    raw, stride = zlib.decompress(b"".join(idat)), w * bpp
    rows, prev = [], bytearray(stride)
    for y in range(h):
        f = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                line[i] = (line[i] + (((line[i - bpp] if i >= bpp else 0) + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b, c = prev[i], (prev[i - bpp] if i >= bpp else 0)
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif f != 0:
            raise ContextError("The elevation tile has an unexpected format.")
        rows.append(line)
        prev = line
    return rows, w, h, bpp


def tile_xy(lat, lon, z):
    """Fractional web-mercator tile coordinates."""
    n = 2.0 ** z
    la = math.radians(lat)
    return (lon + 180.0) / 360.0 * n, (1.0 - math.asinh(math.tan(la)) / math.pi) / 2.0 * n


class Elevation(object):
    """Bilinear elevation (m) from terrarium tiles, fetched once each."""

    def __init__(self, zoom, fetch):
        self.zoom, self.fetch, self.tiles = zoom, fetch, {}

    def _pixel(self, tx, ty, px, py):
        n = 2 ** self.zoom
        tx, ty = tx % n, min(n - 1, max(0, ty))
        if (tx, ty) not in self.tiles:
            rows, w, h, bpp = decode_png(self.fetch(TERRAIN.format(z=self.zoom, x=tx, y=ty)))
            self.tiles[(tx, ty)] = (rows, w, bpp)
        rows, w, bpp = self.tiles[(tx, ty)]
        r, g, b = rows[py][px * bpp:px * bpp + 3]
        return r * 256.0 + g + b / 256.0 - 32768.0

    def at(self, lat, lon):
        fx, fy = tile_xy(lat, lon, self.zoom)
        gx, gy = fx * 256.0 - 0.5, fy * 256.0 - 0.5          # pixel centres
        x0, y0 = int(math.floor(gx)), int(math.floor(gy))
        u, v = gx - x0, gy - y0
        s = lambda x, y: self._pixel(x // 256, y // 256, x % 256, y % 256)
        return (s(x0, y0) * (1 - u) + s(x0 + 1, y0) * u) * (1 - v) + (s(x0, y0 + 1) * (1 - u) + s(x0 + 1, y0 + 1) * u) * v


def zoom_for(lat, cell):
    """The coarsest zoom whose pixels are no larger than `cell` metres (at most MAX_ZOOM)."""
    for z in range(8, MAX_ZOOM + 1):
        if 156543.03392 * math.cos(math.radians(lat)) / 2 ** z <= cell:
            return z
    return MAX_ZOOM


# ----------------------------------------------------------------- OpenStreetMap
def overpass_query(b, buildings, roads, railways=False, water=False):
    box = "(%.7f,%.7f,%.7f,%.7f)" % (b["south"], b["west"], b["north"], b["east"])
    parts = []
    if buildings:
        parts += ['way["building"]%s;' % box, 'relation["building"]["type"="multipolygon"]%s;' % box]
    if roads:
        parts.append('way["highway"]%s;' % box)
    if railways:
        parts.append('way["railway"]%s;' % box)
    if water:
        for key in ('["natural"="water"]', '["waterway"]', '["landuse"~"^(reservoir|basin)$"]'):
            parts += ['way%s%s;' % (key, box), 'relation%s%s;' % (key, box)]
    return "[out:json][timeout:40];(%s);out geom tags;" % "".join(parts)


def road_kind(tags):
    """('major' | 'minor' | 'path', width in metres) of an OpenStreetMap way, or None when it is not a road to draw."""
    k = ROADS.get(tags.get("highway"))
    if not k:
        return None
    w = _number(tags.get("width") or tags.get("est_width"))
    if not (w and 1.0 <= w <= 60.0):
        lanes = _number(tags.get("lanes"))
        w = max(3.0, lanes * LANE) if k[0] != "path" and lanes and 1 <= lanes <= 16 else k[1]
    return k[0], round(w, 2)


def is_railway(tags):
    return tags.get("railway") in RAILS


def is_water(tags):
    """A water area: lake, pond, river surface, reservoir."""
    return (tags.get("natural") == "water" or tags.get("waterway") == "riverbank"
            or tags.get("landuse") in ("reservoir", "basin"))


def _straight(tags):
    """Bridges and tunnels run straight between their ends, not over the valley floor or the hill above them."""
    return tags.get("bridge") not in (None, "no") or tags.get("tunnel") not in (None, "no")


def _number(text):
    """'12', '12.5 m', '40 ft' -> metres, or None."""
    try:
        t = str(text).strip().lower().replace(",", ".")
        feet = t.endswith(("ft", "'", "feet"))
        num = ""
        for ch in t:
            if ch.isdigit() or ch in ".-":
                num += ch
            elif num:
                break
        v = float(num)
        return v * 0.3048 if feet else v
    except (TypeError, ValueError):
        return None


def building_height(tags, default=DEFAULT_HEIGHT, level=LEVEL):
    """(height in metres, True if assumed)."""
    h = _number(tags.get("height") or tags.get("building:height"))
    if h and 1.0 <= h <= 1000.0:
        return h, False
    levels = _number(tags.get("building:levels"))
    if levels and 0.5 <= levels <= 250:
        return levels * level + (_number(tags.get("roof:levels")) or 0) * level, False
    return default, True


def contour_lines(nx, ny, value, point, interval, base=0.0):
    """Contour lines of a grid. value(i, j) is the height that is contoured (metres above sea level), point(i, j, t_i,
    t_j) the 3D point at a fractional grid position. Returns [{"elevation": e, "pts": [...]}], lines joined end to end."""
    if not interval or interval <= 0:
        return []
    vals = [[value(i, j) for i in range(nx)] for j in range(ny)]
    lo, hi = min(map(min, vals)), max(map(max, vals))
    out, k = [], math.ceil((lo - base) / interval)
    while base + k * interval <= hi and len(out) < 4000:
        level = base + k * interval
        e = level + 1e-7                                     # a line through a grid point exactly would split in two there
        k += 1
        segs = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                c = (vals[j][i], vals[j][i + 1], vals[j + 1][i + 1], vals[j + 1][i])        # corners, counter-clockwise
                pos = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
                cut = []
                for a in range(4):
                    b = (a + 1) % 4
                    if (c[a] < e) != (c[b] < e):
                        t = (e - c[a]) / (c[b] - c[a])
                        cut.append((pos[a][0] + (pos[b][0] - pos[a][0]) * t, pos[a][1] + (pos[b][1] - pos[a][1]) * t))
                if len(cut) == 2:
                    segs.append((cut[0], cut[1]))
                elif len(cut) == 4:                              # a saddle: pair the cuts by the cell's middle
                    mid = sum(c) / 4.0 < e
                    pairs = ((0, 1), (2, 3)) if mid == (c[0] < e) else ((0, 3), (1, 2))
                    segs += [(cut[a], cut[b]) for a, b in pairs]
        key = lambda q: (round(q[0], 6), round(q[1], 6))
        ends = {}
        for n, (a, b) in enumerate(segs):
            ends.setdefault(key(a), []).append(n)
            ends.setdefault(key(b), []).append(n)
        used = [False] * len(segs)
        for n in range(len(segs)):
            if used[n]:
                continue
            used[n] = True
            line = [segs[n][0], segs[n][1]]
            for front in (False, True):                          # grow from the end, then from the start
                while True:
                    tip = line[0] if front else line[-1]
                    nxt = next((m for m in ends.get(key(tip), []) if not used[m]), None)
                    if nxt is None:
                        break
                    used[nxt] = True
                    a, b = segs[nxt]
                    other = b if key(a) == key(tip) else a
                    if front:
                        line.insert(0, other)
                    else:
                        line.append(other)
            if len(line) >= 2:
                out.append({"elevation": round(level, 3), "pts": [point(q[0], q[1], level) for q in line]})
    return out


def _ring(geometry):
    pts = [(p["lat"], p["lon"]) for p in geometry or [] if p]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def _join(ways):
    """Member ways of a multipolygon joined end to end into closed rings."""
    rings, open_ = [], [list(w) for w in ways if len(w) >= 2]
    while open_:
        ring = open_.pop()
        if ring[0] == ring[-1]:
            rings.append(ring[:-1])
            continue
        for i, other in enumerate(open_):
            if other[0] == ring[-1]:
                ring += other[1:]
            elif other[-1] == ring[-1]:
                ring += other[-2::-1]
            elif other[-1] == ring[0]:
                ring = other[:-1] + ring
            elif other[0] == ring[0]:
                ring = other[:0:-1] + ring
            else:
                continue
            open_.pop(i)
            open_.append(ring)
            break
    return [r for r in rings if len(r) >= 3]


def parse_osm(data):
    """-> buildings [{outer, inners, tags}], roads [{pts, tags}] with (lat, lon) points."""
    buildings, roads = [], []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        if el.get("type") == "way":
            if "building" in tags:
                ring = _ring(el.get("geometry"))
                if len(ring) >= 3:
                    buildings.append({"outer": ring, "inners": [], "tags": tags})
            elif "highway" in tags or "railway" in tags or tags.get("waterway") in WATERWAYS:
                pts = [(p["lat"], p["lon"]) for p in el.get("geometry") or [] if p]
                if len(pts) >= 2:
                    roads.append({"pts": pts, "tags": tags})
        elif el.get("type") == "relation" and "building" in tags:
            ways = lambda role: [[(p["lat"], p["lon"]) for p in m.get("geometry") or [] if p]
                                 for m in el.get("members", []) if m.get("type") == "way" and m.get("role") == role]
            outers, inners = _join(ways("outer")), _join(ways("inner"))
            for o in outers:
                buildings.append({"outer": o, "inners": [i for i in inners if _inside(i[0], o)], "tags": tags})
    return buildings, roads


def parse_water(data):
    """-> water areas [{outer, inners, tags}] with (lat, lon) points, and the ids of water relations that came without
    all of their outer ways (OpenStreetMap's map download leaves out the parts of a big lake outside the area)."""
    areas, missing = [], []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        if not is_water(tags):
            continue
        if el.get("type") == "way":
            geo = [p for p in el.get("geometry") or [] if p]
            if len(geo) >= 4 and geo[0] == geo[-1]:
                areas.append({"outer": _ring(geo), "inners": [], "tags": tags})
        elif el.get("type") == "relation":
            members = [m for m in el.get("members", []) if m.get("type") == "way"]
            if any(not m.get("geometry") for m in members if m.get("role") in ("outer", "")):
                missing.append(el.get("id"))
                continue
            ways = lambda roles: [[(p["lat"], p["lon"]) for p in m.get("geometry") or [] if p] for m in members if m.get("role") in roles]
            inners = _join(ways(("inner",)))
            for o in _join(ways(("outer", ""))):
                areas.append({"outer": o, "inners": [i for i in inners if _inside(i[0], o)], "tags": tags})
    return areas, missing


def _inside(p, ring):
    x, y, hit = p[1], p[0], False
    for i in range(len(ring)):
        (y1, x1), (y2, x2) = ring[i], ring[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def _lerp(p, q, t):
    return tuple(a + (c - a) * t for a, c in zip(p, q))


def clip_line(pts, b):
    """A (lat, lon, ...) polyline cut to the rectangle: a list of polylines. Further values of a point (a distance
    along the way, say) are interpolated where a line is cut."""
    out, cur = [], []
    for p1, p2 in zip(pts, pts[1:]):
        (la1, lo1), (la2, lo2) = p1[:2], p2[:2]
        t0, t1, dx, dy = 0.0, 1.0, lo2 - lo1, la2 - la1
        for p, q in ((-dx, lo1 - b["west"]), (dx, b["east"] - lo1), (-dy, la1 - b["south"]), (dy, b["north"] - la1)):
            if p == 0:
                if q < 0:
                    t0 = 2.0
                    break
            else:
                r = q / p
                if p < 0:
                    t0 = max(t0, r)
                else:
                    t1 = min(t1, r)
        if t0 > t1:
            if cur:
                out.append(cur)
                cur = []
            continue
        a, c = _lerp(p1, p2, t0), _lerp(p1, p2, t1)
        if not cur:
            cur = [a]
        cur.append(c)
        if t1 < 1.0:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [l for l in out if len(l) >= 2]


def clip_polygon(poly, inside):
    """A closed polygon cut by half-planes (Sutherland-Hodgman). `inside` are functions f(point) >= 0 inside; values
    after the first two of a point are interpolated. Returns the points of the part inside, or []."""
    for f in inside:
        if not poly:
            break
        out = []
        for i, cur in enumerate(poly):
            prev = poly[i - 1]
            fc, fp = f(cur), f(prev)
            if (fc >= 0) != (fp >= 0):
                out.append(_lerp(prev, cur, fp / (fp - fc)))
            if fc >= 0:
                out.append(cur)
        poly = out
    return poly if len(poly) >= 3 else []


def clip_ring(ring, b):
    """A closed (lat, lon) ring cut to the rectangle."""
    return clip_polygon(list(ring), [lambda p: p[1] - b["west"], lambda p: b["east"] - p[1],
                                     lambda p: p[0] - b["south"], lambda p: b["north"] - p[0]])


def _metres(p, q):
    return math.hypot((q[0] - p[0]) * 111320.0, (q[1] - p[1]) * 111320.0 * math.cos(math.radians(p[0])))


def densify(line, step):
    """A (lat, lon, ...) polyline with points added so that none is more than `step` metres from the next: a road
    then follows the ground between the points OpenStreetMap has."""
    out = [line[0]]
    for p, q in zip(line, line[1:]):
        n = int(_metres(p, q) // step)
        out += [_lerp(p, q, k / (n + 1.0)) for k in range(1, n + 1)]
        out.append(q)
    return out


# ----------------------------------------------------------------- road outlines and surfaces
class Mesh(object):
    """Vertices and faces (3 or 4 indices) cut to a convex site outline; equal points are shared."""

    def __init__(self, inside):
        self.v, self.f, self._at, self.inside = [], [], {}, inside

    def _index(self, p):
        key = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
        i = self._at.get(key)
        if i is None:
            i = self._at[key] = len(self.v)
            self.v.append(list(key))
        return i

    def add(self, poly):
        if not all(f(p) >= 0 for f in self.inside for p in poly):
            poly = clip_polygon(poly, self.inside)
        if len(poly) < 3:
            return
        ids = [self._index(p) for p in poly]
        ids = [i for k, i in enumerate(ids) if i != ids[k - 1]]
        if len(ids) in (3, 4):
            self.f.append(ids)
        else:
            self.f += [[ids[0], ids[k], ids[k + 1]] for k in range(1, len(ids) - 1)]

    def disk(self, c, r, n=12, z=None):
        ring = [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        ring = [(x, y, z(x, y) if z else c[2]) for x, y in ring]
        for k in range(n):
            self.add([c, ring[k], ring[(k + 1) % n]])

    def strip(self, pts, w, lift=0.0, ground=None):
        """A road `w` metres wide along a polyline of (x, y, z) points, with round ends and round outer corners where
        it turns sharply. Its edges lie on `ground(x, y)` (lifted as its line is), or level with its line without one,
        as a bridge's are. Faces point up."""
        pts = [p for k, p in enumerate(pts) if k == 0 or math.hypot(p[0] - pts[k - 1][0], p[1] - pts[k - 1][1]) > 1e-3]
        if len(pts) < 2:
            return
        dirs = []
        for p, q in zip(pts, pts[1:]):
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            dirs.append(((q[0] - p[0]) / d, (q[1] - p[1]) / d))
        half, left, right = w / 2.0, [], []
        for k, p in enumerate(pts):
            a, b = dirs[max(0, k - 1)], dirs[min(len(dirs) - 1, k)]
            tx, ty = a[0] + b[0], a[1] + b[1]
            t = math.hypot(tx, ty)
            tx, ty = (tx / t, ty / t) if t > 1e-9 else b
            cos = tx * b[0] + ty * b[1]
            m = 1.0 / cos if cos > 0.5 else 1.0                # the mitre keeps the width; a sharp turn gets a round corner
            z = p[2] + lift
            at = (lambda x, y: ground(x, y) + lift) if ground else (lambda x, y: z)
            lx, ly, rx, ry = p[0] - ty * half * m, p[1] + tx * half * m, p[0] + ty * half * m, p[1] - tx * half * m
            left.append((lx, ly, at(lx, ly)))
            right.append((rx, ry, at(rx, ry)))
            if k in (0, len(pts) - 1) or cos <= 0.5:
                self.disk((p[0], p[1], z), half, z=at)
        for k in range(len(pts) - 1):
            self.add([left[k], right[k], right[k + 1], left[k + 1]])

    def data(self):
        return {"v": self.v, "f": self.f}


# ----------------------------------------------------------------- the build
def http_get(url, data=None, timeout=30):
    from earthlink import __version__
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "EarthLink/%s (Rhino plugin; https://github.com/J1mmywzh/EarthLink)" % __version__,
        "Referer": "https://github.com/J1mmywzh/EarthLink", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:                     # keep the server's own words ("too many nodes", ...)
        try:
            words = e.read(300).decode("utf-8", "replace").strip()
        except Exception:
            words = ""
        raise ContextError("HTTP %d %s" % (e.code, words or e.reason))


def _with_geometry(data):
    """OpenStreetMap's map download lists points, ways and relations separately; give ways and relation members
    their points, the form parse_osm reads (and the Overpass servers answer in)."""
    nodes, ways, out = {}, {}, []
    for el in data.get("elements", []):
        if el.get("type") == "node":
            nodes[el["id"]] = {"lat": el["lat"], "lon": el["lon"]}
    for el in data.get("elements", []):
        if el.get("type") == "way":
            geo = [nodes[n] for n in el.get("nodes", []) if n in nodes]
            if len(geo) == len(el.get("nodes", [])):       # a way with a point missing is not drawn half
                ways[el["id"]] = geo
                out.append({"type": "way", "id": el["id"], "tags": el.get("tags") or {}, "geometry": geo})
    for el in data.get("elements", []):
        if el.get("type") == "relation":
            out.append({"type": "relation", "id": el["id"], "tags": el.get("tags") or {},
                        "members": [{"type": "way", "role": m.get("role", ""), "geometry": ways.get(m.get("ref"), [])}
                                    for m in el.get("members", []) if m.get("type") == "way"]})
    return out


def _osm_map(b, fetch, depth=0):
    """Everything OpenStreetMap has in the rectangle; an area with too many points is asked for in quarters."""
    try:
        return _with_geometry(json.loads(fetch(OSM_MAP % (b["west"], b["south"], b["east"], b["north"])).decode("utf-8")))
    except ContextError as e:
        if "too many nodes" not in str(e) or depth >= 2:
            raise
    mx, my, seen, out = (b["west"] + b["east"]) / 2.0, (b["south"] + b["north"]) / 2.0, {}, []
    for w, e_ in ((b["west"], mx), (mx, b["east"])):
        for s_, n in ((b["south"], my), (my, b["north"])):
            for el in _osm_map({"west": w, "south": s_, "east": e_, "north": n}, fetch, depth + 1):
                key = (el["type"], el["id"])
                if key not in seen:
                    seen[key] = len(out)
                    out.append(el)
                elif el["type"] == "relation":             # a quarter holds only part of a relation: keep the fullest
                    size = lambda r: sum(len(m["geometry"]) for m in r["members"])
                    if size(el) > size(out[seen[key]]):
                        out[seen[key]] = el
    return out


def fetch_osm(b, buildings, roads, fetch=http_get, railways=False, water=False):
    """Buildings and roads in the rectangle, as {"elements": [...]} with each way's points.

    A way is only listed when one of its points lies in the area asked for, so the area is PAD metres wider on every
    side: a street that crosses the rectangle between two of its points, or a building around it, is still found."""
    mid = math.radians((b["south"] + b["north"]) / 2.0)
    dy, dx = PAD / 111320.0, PAD / (111320.0 * max(0.2, math.cos(mid)))
    b = {"west": b["west"] - dx, "east": b["east"] + dx, "south": b["south"] - dy, "north": b["north"] + dy}
    last = None
    try:
        return {"elements": _osm_map(b, fetch)}
    except Exception as e:                                  # busy or unreachable: the Overpass servers know the same map
        last = e
    body = urllib.parse.urlencode({"data": overpass_query(b, buildings, roads, railways, water)}).encode()
    for url in OVERPASS:
        try:
            return json.loads(fetch(url, body).decode("utf-8"))
        except Exception as e:                              # a busy mirror: try the next one
            last = e
    raise ContextError("OpenStreetMap could not be reached (%s). Try again in a minute." % (last,))


def fetch_relations(ids, fetch=http_get):
    """Whole relations (all their ways' points) from the Overpass servers, or {"elements": []} when none answers."""
    ids = [int(i) for i in ids if i is not None][:20]
    if not ids:
        return {"elements": []}
    body = urllib.parse.urlencode({"data": "[out:json][timeout:60];relation(id:%s);out geom tags;" % ",".join(map(str, ids))}).encode()
    for url in OVERPASS:
        try:
            return json.loads(fetch(url, body).decode("utf-8"))
        except Exception:
            pass
    return {"elements": []}


def build(bounds, anchor, settings, terrain=True, buildings=True, roads=True, fetch=http_get, progress=lambda text, part=None: None,
          contours=0.0, default_height=DEFAULT_HEIGHT, level_height=LEVEL, paths=True, railways=True, water=True,
          road_style="lines", assume_height=True):
    """The context inside `bounds`, in metres east/north/up of the model base point.

    anchor: the published EarthAnchorPoint (lat, lon, elev, zero). settings: ground_h, nudge, geoid_offset.
    road_style: "lines" (centrelines), "outlines" or "surfaces" for roads and paths; railways and rivers are lines.
    assume_height: a building OpenStreetMap gives no height for gets default_height; otherwise only its footprint."""
    b = check_bounds(bounds)
    if not anchor or anchor.get("lat") is None:
        raise ContextError("Place the model on the map first (SendToEarth).")
    lat0, lon0 = float(anchor["lat"]), float(anchor["lon"])
    w, h = side_lengths(b)
    cell = max(max(w, h) / GRID, 1.0)
    progress("Terrain", 0.05)
    dem = Elevation(zoom_for((b["south"] + b["north"]) / 2.0, cell), lambda url: fetch(url))
    try:
        dem0 = dem.at(lat0, lon0)
    except ContextError:
        raise
    except Exception as e:
        raise ContextError("The terrain data could not be reached (%s)." % (e,))
    # Height of a point of the elevation model above the model base point (see the module text).
    elev, zero = float(anchor.get("elev") or 0.0), anchor.get("zero") or "GroundLevel"
    nudge = float(settings.get("nudge") or 0.0)
    if zero == "GroundLevel":
        offset = -dem0 - elev - nudge
    elif zero == "MeanSeaLevel":
        offset = -elev - nudge
    else:                                              # heights above the ellipsoid
        offset = float(settings.get("geoid_offset", -33.5)) - elev - nudge
    rel = lambda la, lo: dem.at(la, lo) + offset       # metres above the base point, before the Earth's curve
    point = lambda la, lo: [round(v, 3) for v in enu(la, lo, rel(la, lo), lat0, lon0)]

    default_height = min(300.0, max(1.0, float(default_height or DEFAULT_HEIGHT)))
    level_height = min(10.0, max(2.0, float(level_height or LEVEL)))
    contours = float(contours or 0.0)
    road_style = road_style if road_style in STYLES else "lines"
    out = {"bounds": b, "size": [round(w, 1), round(h, 1)], "attribution": ATTRIBUTION, "terrain": None, "buildings": [], "roads": [],
           "railways": [], "water": [], "contours": [], "road_style": road_style}
    if terrain or contours > 0:
        nx, ny = max(2, int(round(w / cell)) + 1), max(2, int(round(h / cell)) + 1)
        pts = []
        for j in range(ny):
            if j % 8 == 0:
                progress("Terrain", 0.08 + 0.42 * j / ny)
            la = b["south"] + (b["north"] - b["south"]) * j / (ny - 1)
            for i in range(nx):
                pts.append(point(la, b["west"] + (b["east"] - b["west"]) * i / (nx - 1)))
        if terrain:
            out["terrain"] = {"nx": nx, "ny": ny, "points": pts, "cell": round(cell, 2)}
        if contours > 0:                                   # at round heights above sea level, on the same surface as the mesh
            lat_of = lambda fj: b["south"] + (b["north"] - b["south"]) * fj / (ny - 1)
            lon_of = lambda fi: b["west"] + (b["east"] - b["west"]) * fi / (nx - 1)
            sea = [[dem.at(lat_of(j), lon_of(i)) for i in range(nx)] for j in range(ny)]
            wanted = max(contours, 0.1)
            step = wanted * max(1, math.ceil((max(map(max, sea)) - min(map(min, sea))) / 400.0 / wanted))   # never thousands of lines: every 2nd, 3rd... of yours
            out["contours"] = contour_lines(nx, ny, lambda i, j: sea[j][i],
                                            lambda fi, fj, e: [round(v, 3) for v in enu(lat_of(fj), lon_of(fi), e + offset, lat0, lon0)], step)
            out["contour_interval"] = round(step, 3)
    if buildings or roads or paths or railways or water:
        progress("Buildings and roads", 0.55 if terrain else 0.1)
        data = fetch_osm(b, buildings, roads or paths, fetch, railways, water)
        found, ways = parse_osm(data)
        areas, missing = parse_water(data) if water else ([], [])
        if missing:                                        # a lake bigger than the area: fetch it whole, then cut it
            progress("Water", 0.7)
            areas += parse_water(fetch_relations(missing, fetch))[0]
        progress("Buildings and roads", 0.8)
        for f in (found if buildings else []):
            c = [sum(p[k] for p in f["outer"]) / len(f["outer"]) for k in (0, 1)]
            if not (b["south"] <= c[0] <= b["north"] and b["west"] <= c[1] <= b["east"]):
                continue                                   # whole buildings only: those centred in the rectangle
            height, assumed = building_height(f["tags"], default_height, level_height)
            if assumed and not assume_height:
                height = 0.0                               # only its footprint
            base = min(rel(la, lo) for la, lo in f["outer"])
            flat = lambda ring: [[round(v, 3) for v in enu(la, lo, base, lat0, lon0)[:2]] for la, lo in ring]
            out["buildings"].append({"outer": flat(f["outer"]), "inners": [flat(i) for i in f["inners"]],
                                     "base": round(enu(c[0], c[1], base, lat0, lon0)[2], 3), "height": round(height, 2), "assumed": assumed,
                                     "name": f["tags"].get("name") or f["tags"].get("addr:housenumber", ""),
                                     "tags": {str(k)[:60]: str(v)[:200] for k, v in list(f["tags"].items())[:40]}})
        step = min(max(cell, 2.0), 10.0)                   # metres between the points of a line, so it follows the ground
        keep = lambda tags: {str(k)[:60]: str(v)[:200] for k, v in list(tags.items())[:40]}
        corners = [enu(la, lo, 0.0, lat0, lon0)[:2] for la, lo in ((b["south"], b["west"]), (b["south"], b["east"]),
                                                                   (b["north"], b["east"]), (b["north"], b["west"]))]
        inside = [(lambda a, c: lambda p: (c[0] - a[0]) * (p[1] - a[1]) - (c[1] - a[1]) * (p[0] - a[0]))(corners[k], corners[(k + 1) % 4])
                  for k in range(4)]                       # the rectangle on the ground, counter-clockwise
        meshes = {}
        per_lon = enu(lat0, lon0 + 1e-4, 0.0, lat0, lon0)[0] / 1e-4
        per_lat = enu(lat0 + 1e-4, lon0, 0.0, lat0, lon0)[1] / 1e-4

        def ground(x, y):                                  # the ground's height at a point east/north of the base point
            la, lo = lat0 + y / per_lat, lon0 + x / per_lon
            return enu(la, lo, rel(la, lo), lat0, lon0)[2]
        for r in ways:
            tags = r["tags"]
            kind = road_kind(tags)
            if kind:
                cls, width = kind
                if not (paths if cls == "path" else roads):
                    continue
                into = out["roads"]
            elif is_railway(tags) and railways:
                into, cls, width = out["railways"], "rail", 0.0
            elif tags.get("waterway") in WATERWAYS and water:
                into, cls, width = out["water"], "waterway", 0.0
            else:
                continue
            full, run = r["pts"], [0.0]
            for p, q in zip(full, full[1:]):
                run.append(run[-1] + _metres(p, q))
            straight = _straight(tags) and run[-1] > 0
            if straight:
                z0, z1 = rel(*full[0]), rel(*full[-1])
            for line in clip_line([(la, lo, s) for (la, lo), s in zip(full, run)], b):
                pts = [[round(v, 3) for v in enu(la, lo, z0 + (z1 - z0) * s / run[-1] if straight else rel(la, lo), lat0, lon0)]
                       for la, lo, s in densify(line, step)]
                item = {"pts": pts, "kind": tags.get("highway") or tags.get("railway") or tags.get("waterway") or "",
                        "name": tags.get("name", ""), "tags": keep(tags)}
                if into is out["roads"]:
                    item.update({"class": cls, "width": width})
                    if road_style != "lines":
                        if cls not in meshes:
                            meshes[cls] = Mesh(inside)
                        meshes[cls].strip(pts, width, LIFT[cls], None if straight else ground)
                into.append(item)
        if meshes:
            out["road_meshes"] = {k: m.data() for k, m in meshes.items()}
        for a in areas:                                    # lakes, ponds and rivers: flat at the water level
            outer = clip_ring(a["outer"], b)
            if not outer:
                continue
            level = min(rel(la, lo) for la, lo in outer)
            ring = lambda pts: [[round(v, 3) for v in enu(la, lo, level, lat0, lon0)] for la, lo in pts]
            name, kind = a["tags"].get("name", ""), a["tags"].get("water") or a["tags"].get("natural") or a["tags"].get("landuse") or "water"
            out["water"].append({"pts": ring(outer), "closed": True, "kind": kind, "name": name, "tags": keep(a["tags"])})
            for i in a["inners"]:
                inner = clip_ring(i, b)
                if inner:
                    out["water"].append({"pts": ring(inner), "closed": True, "island": True, "kind": kind, "name": name, "tags": keep(a["tags"])})
    out["counts"] = {"terrain": (out["terrain"]["nx"] - 1) * (out["terrain"]["ny"] - 1) if out["terrain"] else 0,
                     "buildings": len(out["buildings"]), "assumed": sum(1 for x in out["buildings"] if x["assumed"]),
                     "roads": sum(1 for r in out["roads"] if r["class"] != "path"), "paths": sum(1 for r in out["roads"] if r["class"] == "path"),
                     "railways": len(out["railways"]), "water": len(out["water"]), "contours": len(out["contours"]), "road_style": road_style}
    return out
