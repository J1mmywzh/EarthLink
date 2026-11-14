"""Site context from open data, for Rhino: terrain, building massing and roads inside a rectangle.

Pure Python, run by the local server (never inside Rhino's interface thread). Sources, both free to export:
  * OpenStreetMap (buildings, roads) through the Overpass API. Data (c) OpenStreetMap contributors, ODbL.
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
import urllib.parse
import urllib.request
import zlib

OVERPASS = ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter")
TERRAIN = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
ATTRIBUTION = ("Buildings and roads (c) OpenStreetMap contributors, ODbL. "
               "Terrain: Terrain Tiles (Mapzen, AWS Open Data; USGS 3DEP, SRTM and other sources).")
MAX_SIDE, MIN_SIDE = 3000.0, 20.0          # metres
MAX_ZOOM, GRID = 15, 200                   # elevation tiles stop at zoom 15; at most GRID cells along the longer side
LEVEL, DEFAULT_HEIGHT = 3.2, 7.0           # metres per storey; height of a building OpenStreetMap gives no height for
A, E2 = 6378137.0, 6.69437999014e-3        # WGS84


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
def overpass_query(b, buildings, roads):
    box = "(%.7f,%.7f,%.7f,%.7f)" % (b["south"], b["west"], b["north"], b["east"])
    parts = []
    if buildings:
        parts += ['way["building"]%s;' % box, 'relation["building"]["type"="multipolygon"]%s;' % box]
    if roads:
        parts.append('way["highway"]%s;' % box)
    return "[out:json][timeout:40];(%s);out geom tags;" % "".join(parts)


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


def building_height(tags):
    """(height in metres, True if assumed)."""
    h = _number(tags.get("height") or tags.get("building:height"))
    if h and 1.0 <= h <= 1000.0:
        return h, False
    levels = _number(tags.get("building:levels"))
    if levels and 0.5 <= levels <= 250:
        return levels * LEVEL + (_number(tags.get("roof:levels")) or 0) * LEVEL, False
    return DEFAULT_HEIGHT, True


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
            elif "highway" in tags:
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


def _inside(p, ring):
    x, y, hit = p[1], p[0], False
    for i in range(len(ring)):
        (y1, x1), (y2, x2) = ring[i], ring[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def clip_line(pts, b):
    """A (lat, lon) polyline cut to the rectangle: a list of polylines."""
    out, cur = [], []
    for (la1, lo1), (la2, lo2) in zip(pts, pts[1:]):
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
        a, c = (la1 + dy * t0, lo1 + dx * t0), (la1 + dy * t1, lo1 + dx * t1)
        if not cur:
            cur = [a]
        cur.append(c)
        if t1 < 1.0:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [l for l in out if len(l) >= 2]


# ----------------------------------------------------------------- the build
def http_get(url, data=None, timeout=45):
    from earthlink import __version__
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "EarthLink/%s (Rhino plugin; github.com/J1mmywzh/EarthLink)" % __version__})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_osm(b, buildings, roads, fetch=http_get):
    body = urllib.parse.urlencode({"data": overpass_query(b, buildings, roads)}).encode()
    last = None
    for url in OVERPASS:
        try:
            return json.loads(fetch(url, body).decode("utf-8"))
        except Exception as e:          # a busy mirror: try the next one
            last = e
    raise ContextError("OpenStreetMap could not be reached (%s). Try again in a minute." % (last,))


def build(bounds, anchor, settings, terrain=True, buildings=True, roads=True, fetch=http_get, progress=lambda text: None):
    """The context inside `bounds`, in metres east/north/up of the model base point.

    anchor: the published EarthAnchorPoint (lat, lon, elev, zero). settings: ground_h, nudge, geoid_offset."""
    b = check_bounds(bounds)
    if not anchor or anchor.get("lat") is None:
        raise ContextError("Place the model on the map first (SendToEarth).")
    lat0, lon0 = float(anchor["lat"]), float(anchor["lon"])
    w, h = side_lengths(b)
    cell = max(max(w, h) / GRID, 1.0)
    progress("Reading the terrain")
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

    out = {"bounds": b, "size": [round(w, 1), round(h, 1)], "attribution": ATTRIBUTION, "terrain": None, "buildings": [], "roads": []}
    if terrain:
        nx, ny = max(2, int(round(w / cell)) + 1), max(2, int(round(h / cell)) + 1)
        pts = []
        for j in range(ny):
            la = b["south"] + (b["north"] - b["south"]) * j / (ny - 1)
            for i in range(nx):
                pts.append(point(la, b["west"] + (b["east"] - b["west"]) * i / (nx - 1)))
        out["terrain"] = {"nx": nx, "ny": ny, "points": pts, "cell": round(cell, 2)}
    if buildings or roads:
        progress("Reading OpenStreetMap")
        found, ways = parse_osm(fetch_osm(b, buildings, roads, fetch))
        for f in (found if buildings else []):
            c = [sum(p[k] for p in f["outer"]) / len(f["outer"]) for k in (0, 1)]
            if not (b["south"] <= c[0] <= b["north"] and b["west"] <= c[1] <= b["east"]):
                continue                                   # whole buildings only: those centred in the rectangle
            height, assumed = building_height(f["tags"])
            base = min(rel(la, lo) for la, lo in f["outer"])
            flat = lambda ring: [[round(v, 3) for v in enu(la, lo, base, lat0, lon0)[:2]] for la, lo in ring]
            out["buildings"].append({"outer": flat(f["outer"]), "inners": [flat(i) for i in f["inners"]],
                                     "base": round(enu(c[0], c[1], base, lat0, lon0)[2], 3), "height": round(height, 2), "assumed": assumed,
                                     "name": f["tags"].get("name") or f["tags"].get("addr:housenumber", "")})
        for r in (ways if roads else []):
            for line in clip_line(r["pts"], b):
                out["roads"].append({"pts": [point(la, lo) for la, lo in line], "kind": r["tags"].get("highway", ""), "name": r["tags"].get("name", "")})
    out["counts"] = {"terrain": (out["terrain"]["nx"] - 1) * (out["terrain"]["ny"] - 1) if out["terrain"] else 0,
                     "buildings": len(out["buildings"]), "assumed": sum(1 for x in out["buildings"] if x["assumed"]), "roads": len(out["roads"])}
    return out
