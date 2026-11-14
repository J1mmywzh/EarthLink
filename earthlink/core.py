"""Exporting from Rhino, and EarthLink's per-file state.

Export happens in a hidden (headless) Rhino document: geometry and materials are copied into it,
re-oriented to east/north/up around the EarthAnchorPoint, and written as GLB. The user's document,
selection, redraw and undo history are never touched.

State saved inside the .3dm (Document User Text, section "EarthLink"):
  project_id : stable id for this project (views are keyed by it, so renaming the file keeps them)
  sets       : {name: {"ids": [object ids], "live": bool, "pending": bool}}
"""
import os, json, time, math, glob, shutil, uuid

import Rhino
import Rhino.Geometry as rg
import System

from earthlink import env, collada, geometry

KEEP_VERSIONS = 3
SECTION = "EarthLink"
DEFAULT_SET = "Main"
EXPORT_FORMAT = 2     # 2: see-through materials and texture mappings (0.2.0-beta.10); older exports are sent once more


# ----------------------------------------------------------------- anchor / frames
def anchor_ok(doc):
    return doc.EarthAnchorPoint.EarthLocationIsSet()


def enu_transform(doc):
    """Model -> local east/north/up around the anchor, in model units."""
    ep = doc.EarthAnchorPoint
    n = ep.ModelNorth
    alpha = math.atan2(-n.X, n.Y)
    return rg.Transform.Rotation(-alpha, rg.Vector3d.ZAxis, rg.Point3d.Origin) * \
        rg.Transform.Translation(rg.Point3d.Origin - ep.ModelBasePoint)


def north_angle(doc):
    """Angle of model north from the +X axis, in degrees (Rhino Sun's 'North' convention)."""
    n = doc.EarthAnchorPoint.ModelNorth
    return math.degrees(math.atan2(n.Y, n.X)) % 360.0


def anchor_info(doc):
    ep = doc.EarthAnchorPoint
    b = ep.ModelBasePoint
    return {"lat": ep.EarthBasepointLatitude, "lon": ep.EarthBasepointLongitude,
            "elev": ep.EarthBasepointElevation, "zero": str(ep.EarthBasepointElevationZero),
            "north": round(north_angle(doc), 6), "base": [b.X, b.Y, b.Z]}


def base_point_for(doc, ids):
    """Bottom centre of the objects' bounding box, in model coordinates (None: nothing to measure).
    A first placement puts this point on the spot picked on the map."""
    bbox = rg.BoundingBox.Empty
    for i in ids or []:
        try:
            obj = doc.Objects.FindId(System.Guid(str(i)))
        except Exception:
            obj = None
        if obj is not None and not obj.IsDeleted:
            bbox.Union(obj.Geometry.GetBoundingBox(True))
    if not bbox.IsValid:
        return None
    c = bbox.Center
    return rg.Point3d(c.X, c.Y, bbox.Min.Z)


def set_anchor(doc, lat=None, lon=None, rotate_deg=0.0, elev=None, zero=None, base=None):
    """Update the EarthAnchorPoint (the same thing the EarthAnchorPoint command edits).
    rotate_deg turns the model clockwise on the map (north turns counter-clockwise in the model).
    base: a new model base point (the point of the model that sits on the site location)."""
    ep = doc.EarthAnchorPoint
    new = Rhino.DocObjects.EarthAnchorPoint()
    new.EarthBasepointLatitude = ep.EarthBasepointLatitude if lat is None else lat
    new.EarthBasepointLongitude = ep.EarthBasepointLongitude if lon is None else lon
    new.EarthBasepointElevation = ep.EarthBasepointElevation if elev is None else elev
    new.EarthBasepointElevationZero = ep.EarthBasepointElevationZero if zero is None else zero
    new.ModelBasePoint = ep.ModelBasePoint if base is None else base
    north, east = rg.Vector3d(ep.ModelNorth), rg.Vector3d(ep.ModelEast)
    if not ep.EarthLocationIsSet() and north.IsZero:
        north, east = rg.Vector3d(0, 1, 0), rg.Vector3d(1, 0, 0)
    if rotate_deg:
        r = rg.Transform.Rotation(math.radians(rotate_deg), rg.Vector3d.ZAxis, rg.Point3d.Origin)
        north.Transform(r); east.Transform(r)
    new.ModelNorth, new.ModelEast = north, east
    new.Name, new.Description = ep.Name, ep.Description
    doc.EarthAnchorPoint = new


# ----------------------------------------------------------------- per-file state
def _get(doc, key, default=None):
    try:
        v = doc.Strings.GetValue(SECTION, key)
        return json.loads(v) if v else default
    except Exception:
        return default


def _put(doc, key, value):
    doc.Strings.SetString(SECTION, key, json.dumps(value))


def project_id(doc):
    pid = _get(doc, "project_id")
    if not pid:
        pid = str(uuid.uuid4())
        _put(doc, "project_id", pid)
    return pid


def project_name(doc):
    return os.path.splitext(doc.Name or "Untitled")[0]


def get_sets(doc):
    return _get(doc, "sets", {}) or {}


def put_set(doc, name, ids=None, **flags):
    sets = get_sets(doc)
    s = sets.get(name, {"ids": [], "live": False})
    if ids is not None:
        s["ids"] = [str(i) for i in ids]
    s.update(flags)
    sets[name] = s
    _put(doc, "sets", sets)
    return s


def drop_set(doc, name):
    sets = get_sets(doc)
    if sets.pop(name, None) is not None:
        _put(doc, "sets", sets)


def rename_set(doc, old, new):
    sets = get_sets(doc)
    if old not in sets or not new or new in sets:
        return False
    _put(doc, "sets", {(new if k == old else k): v for k, v in sets.items()})
    return True


def rename_set_in_viewer(old, new):
    meta = load_meta()
    if old in meta.get("sets", {}) and new not in meta["sets"]:
        meta["sets"] = {(new if k == old else k): v for k, v in meta["sets"].items()}
        meta["version"] = int(meta.get("version", 0)) + 1
        env.write_json(os.path.join(env.live_dir(), "meta.json"), meta)
        s = env.load_settings()
        st = dict(s.get("set_styles") or {})
        if old in st:
            st[new] = st.pop(old)
        ren = lambda key: [new if n == old else n for n in s.get(key) or []]
        env.save_settings({"hidden_sets": ren("hidden_sets"), "clip_sets": ren("clip_sets"), "set_styles": st})


# ----------------------------------------------------------------- placement (EarthLink only; Rhino geometry never moves)
def placement(doc, name):
    """A set's EarthLink placement: turned `rot` degrees clockwise on the map, then moved by `t`
    (metres east/north/up). The viewer applies it on top of the exported geometry (which stays where it is in
    Rhino), so moving a set needs no new export and the Rhino model keeps its own grid."""
    p = get_sets(doc).get(name, {}).get("placement") or {}
    return {"rot": float(p.get("rot", 0.0)), "t": [float(v) for v in (p.get("t") or [0.0, 0.0, 0.0])][:3]}


def place_set(doc, name, dx=0.0, dy=0.0, dz=0.0, rot=0.0, pivot=(0, 0, 0)):
    """Compose a viewer move (turn `rot` clockwise about `pivot`, then move) onto the set's placement."""
    if name not in get_sets(doc):
        return None
    new = geometry.compose_placement(get_sets(doc)[name].get("placement"), dx, dy, dz, rot, pivot)
    put_set(doc, name, placement=new)
    return new or {}


def set_placement(doc, name, rot=0.0, t=(0.0, 0.0, 0.0)):
    """Store a set's placement as the viewer gave it (absolute). Returns False for an unknown set."""
    if name not in get_sets(doc):
        return False
    put_set(doc, name, placement=geometry.clean_placement(rot, t))
    return True


def reset_placement(doc, name):
    if name in get_sets(doc):
        put_set(doc, name, placement=None)


def publish_placement(doc, name):
    """Make live/meta.json carry this file's placement for a set (after an edit, an Undo, a reopened file).
    No geometry is exported. Returns True when meta changed."""
    meta = load_meta()
    entry = (meta.get("sets") or {}).get(name)
    if entry is None or meta.get("project") != project_id(doc):
        return False
    want = get_sets(doc).get(name, {}).get("placement") or None
    changed = (entry.get("placement") or None) != want
    if changed:
        if want:
            entry["placement"] = placement(doc, name)
        else:
            entry.pop("placement", None)
        meta["version"] = int(meta.get("version", 0)) + 1
        env.write_json(os.path.join(env.live_dir(), "meta.json"), meta)
    if any(s.get("dae") for s in meta["sets"].values()):
        _write_earthpro(env.live_dir(), meta)
    return changed


def publish_anchor(doc):
    """The site moved but the geometry did not (same base point and north): update meta only, export nothing."""
    meta = load_meta()
    if not meta.get("sets") or meta.get("project") != project_id(doc):
        return False
    meta["anchor"] = anchor_info(doc)
    meta["version"] = int(meta.get("version", 0)) + 1
    env.write_json(os.path.join(env.live_dir(), "meta.json"), meta)
    if any(s.get("dae") for s in meta["sets"].values()):
        _write_earthpro(env.live_dir(), meta)
    return True


def set_objects(doc, name):
    """Live RhinoObjects of a set (objects that were deleted are skipped)."""
    out = []
    for sid in get_sets(doc).get(name, {}).get("ids", []):
        o = doc.Objects.FindId(System.Guid(sid))
        if o is not None and not o.IsDeleted:
            out.append(o)
    return out


def signature(objs):
    """Changes whenever a set's geometry or look changes (Rhino gives edited objects a new serial)."""
    return tuple((o.RuntimeSerialNumber, o.Attributes.MaterialIndex, str(o.Attributes.ObjectColor.ToArgb()),
                  str(o.RenderMaterial.Id) if o.RenderMaterial else "") for o in objs)


# ----------------------------------------------------------------- export (headless document)
_MESHABLE = (rg.Brep, rg.Extrusion, rg.Mesh, rg.SubD, rg.Surface)


def _effective_material(obj, parent_obj=None):
    src = obj.Attributes.MaterialSource
    if parent_obj is not None and src == Rhino.DocObjects.ObjectMaterialSource.MaterialFromParent:
        obj = parent_obj
    try:
        return obj.GetRenderMaterial(True)
    except Exception:
        return obj.RenderMaterial


def _display_color(doc, obj, parent_obj=None):
    a = obj.Attributes
    if a.ColorSource == Rhino.DocObjects.ObjectColorSource.ColorFromObject:
        return a.ObjectColor
    if a.ColorSource == Rhino.DocObjects.ObjectColorSource.ColorFromParent and parent_obj is not None:
        return _display_color(doc, parent_obj)
    return doc.Layers[a.LayerIndex].Color


# ----------------------------------------------------------------- site context from open data
CONTEXT_LAYER = "EarthLink Context"


def _layer(doc, path, color):
    """Index of the layer `A::B` (created with its parents if missing)."""
    i = doc.Layers.FindByFullPath(path, -1)
    if i >= 0:
        return i
    parent, index = System.Guid.Empty, -1
    for part in path.split("::"):
        full = part if index < 0 else doc.Layers[index].FullPath + "::" + part
        j = doc.Layers.FindByFullPath(full, -1)
        if j < 0:
            layer = Rhino.DocObjects.Layer()
            layer.Name, layer.Color = part, color
            if parent != System.Guid.Empty:
                layer.ParentLayerId = parent
            j = doc.Layers.Add(layer)
        index, parent = j, doc.Layers[j].Id
    return index


def add_context(doc, data):
    """Add terrain, buildings and roads from context.build() to the document, on EarthLink Context layers, as one
    undo step. `data` is in metres east/north/up of the model base point. Returns what was added, as a sentence."""
    scale = Rhino.RhinoMath.UnitScale(Rhino.UnitSystem.Meters, doc.ModelUnitSystem)
    ok, inv = enu_transform(doc).TryGetInverse()
    if not ok:
        raise ValueError("the site transform cannot be inverted")
    pt = lambda p: inv * rg.Point3d(p[0] * scale, p[1] * scale, (p[2] if len(p) > 2 else 0.0) * scale)
    tol = doc.ModelAbsoluteTolerance
    C = System.Drawing.Color
    undo = doc.BeginUndoRecord("EarthLink context")
    ids, counts = [], {"terrain": 0, "buildings": 0, "roads": 0}
    try:
        note = lambda a, kind: (a.SetUserString("EarthLink", "context"), a.SetUserString("source", kind))
        t = data.get("terrain")
        if t and t.get("points"):
            mesh, nx, ny = rg.Mesh(), int(t["nx"]), int(t["ny"])
            for p in t["points"]:
                mesh.Vertices.Add(pt(p))
            for j in range(ny - 1):
                for i in range(nx - 1):
                    a = j * nx + i
                    mesh.Faces.AddFace(a, a + 1, a + nx + 1, a + nx)
            mesh.Normals.ComputeNormals()
            mesh.Compact()
            at = Rhino.DocObjects.ObjectAttributes()
            at.LayerIndex, at.Name = _layer(doc, CONTEXT_LAYER + "::Terrain", C.FromArgb(120, 140, 110)), "Terrain"
            note(at, "Terrain Tiles (Mapzen, AWS Open Data)")
            ids.append(doc.Objects.AddMesh(mesh, at))
            counts["terrain"] = mesh.Faces.Count
        for b in data.get("buildings") or []:
            base, up = b.get("base", 0.0), b.get("height", 0.0)
            loops = []
            for ring in [b["outer"]] + list(b.get("inners") or []):
                pts = [pt((p[0], p[1], base)) for p in ring]
                if len(pts) >= 3:
                    loops.append(rg.Polyline(pts + [pts[0]]).ToNurbsCurve())
            if not loops:
                continue
            path = rg.LineCurve(pt((0, 0, base)), pt((0, 0, base + up)))
            path.Translate(loops[0].PointAtStart - path.PointAtStart)
            solid = None
            faces = rg.Brep.CreatePlanarBreps(System.Array[rg.Curve](loops), tol)
            if faces and len(faces) > 0:
                solid = faces[0].Faces[0].CreateExtrusion(path, True)
            if solid is None:                             # a footprint Rhino cannot make planar: extrude its outline
                solid = rg.Surface.CreateExtrusion(loops[0], path.PointAtEnd - path.PointAtStart).ToBrep().CapPlanarHoles(tol)
            if solid is None:
                continue
            at = Rhino.DocObjects.ObjectAttributes()
            layer = "::Buildings (height assumed)" if b.get("assumed") else "::Buildings"
            at.LayerIndex, at.Name = _layer(doc, CONTEXT_LAYER + layer, C.FromArgb(200, 200, 195)), b.get("name") or ""
            note(at, "OpenStreetMap")
            at.SetUserString("height_m", "%.2f" % up)
            ids.append(doc.Objects.AddBrep(solid, at))
            counts["buildings"] += 1
        for r in data.get("roads") or []:
            pts = [pt(p) for p in r["pts"]]
            if len(pts) < 2:
                continue
            at = Rhino.DocObjects.ObjectAttributes()
            at.LayerIndex, at.Name = _layer(doc, CONTEXT_LAYER + "::Roads", C.FromArgb(90, 90, 95)), r.get("name") or r.get("kind") or ""
            note(at, "OpenStreetMap")
            if r.get("kind"):
                at.SetUserString("highway", r["kind"])
            ids.append(doc.Objects.AddCurve(rg.Polyline(pts).ToNurbsCurve(), at))
            counts["roads"] += 1
        ids = [i for i in ids if i != System.Guid.Empty]
        if ids:
            doc.Groups.Add("EarthLink context", System.Array[System.Guid](ids))
        doc.Layers[_layer(doc, CONTEXT_LAYER, C.FromArgb(120, 120, 120))].SetUserString("attribution", data.get("attribution", ""))
    finally:
        doc.EndUndoRecord(undo)
    doc.Views.Redraw()
    parts = []
    if counts["terrain"]:
        parts.append("terrain (%d faces)" % counts["terrain"])
    if counts["buildings"]:
        parts.append("%d building%s" % (counts["buildings"], "" if counts["buildings"] == 1 else "s"))
    if counts["roads"]:
        parts.append("%d road line%s" % (counts["roads"], "" if counts["roads"] == 1 else "s"))
    return ("added " + ", ".join(parts) + " on layer '%s'" % CONTEXT_LAYER) if parts else "nothing was found in that rectangle"


# ----------------------------------------------------------------- lights
_LIGHT_KINDS = {"WorldPoint": "point", "WorldSpot": "spot", "WorldDirectional": "directional",
                "WorldRectangular": "rect", "WorldLinear": "linear"}


def lights_info(doc):
    """The document's lights that are on, for the viewer: positions and sizes in metres east/north/up of the model
    base point (the frame the exported geometry is in), colours as Rhino shows them (0..1), Rhino's own intensity and
    attenuation. The sun and the skylight are not in this table; they follow the viewer's time of day."""
    if not anchor_ok(doc):
        return []
    xf = enu_transform(doc)
    scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    r = lambda v: round(float(v), 4)

    def point(p):
        q = rg.Point3d(p)
        q.Transform(xf)
        return [r(q.X * scale), r(q.Y * scale), r(q.Z * scale)]

    def vector(v, unit=False):
        w = rg.Vector3d(v)
        w.Transform(xf)
        if unit:
            if not w.Unitize():
                return [0.0, 0.0, -1.0]
            return [round(w.X, 5), round(w.Y, 5), round(w.Z, 5)]
        return [r(w.X * scale), r(w.Y * scale), r(w.Z * scale)]

    out = []
    for lo in doc.Lights:
        try:
            lg = lo.LightGeometry
            kind = _LIGHT_KINDS.get(str(lg.LightStyle))
            if kind is None or lo.IsDeleted or not lg.IsEnabled or not lo.Visible:
                continue
            c = lg.Diffuse
            a = lg.AttenuationVector
            item = {"id": str(lo.Id), "name": lo.Name or "", "kind": kind, "pos": point(lg.Location),
                    "dir": vector(lg.Direction, True), "color": [round(c.R / 255.0, 4), round(c.G / 255.0, 4), round(c.B / 255.0, 4)],
                    "intensity": r(lg.Intensity),
                    # 1 / (a0 + a1 d + a2 d^2) with d in model units, rewritten for metres
                    "att": [r(a.X), round(a.Y / scale, 6), round(a.Z / (scale * scale), 8)],
                    "att_type": str(lg.AttenuationType), "shadow": r(lg.ShadowIntensity)}
            if kind == "spot":
                item["angle"] = r(lg.SpotAngleRadians)          # half the cone
                item["hot"] = r(lg.HotSpot)                      # 0..1 of the cone at full strength
            if kind in ("rect", "linear"):
                item["length"] = vector(lg.Length)
                item["width"] = vector(lg.Width)
            out.append(item)
        except Exception:
            continue                                             # an odd light never stops the others
    out.sort(key=lambda x: x["id"])
    return out


def publish_lights(doc, lights=None):
    """Make live/meta.json carry the document's lights. No geometry is exported. Returns True when meta changed."""
    meta = load_meta()
    if not meta.get("sets") or meta.get("project") != project_id(doc):
        return False
    lights = lights_info(doc) if lights is None else lights
    if (meta.get("lights") or []) == lights:
        return False
    meta["lights"] = lights
    meta["version"] = int(meta.get("version", 0)) + 1
    env.write_json(os.path.join(env.live_dir(), "meta.json"), meta)
    return True


def _copy_texture_mappings(src, dst, xform):
    """Carry an object's texture mappings (box, planar, ...) to its copy, which was moved by `xform`.
    Without them a mapped texture falls back to the surface's own UVs: the wrong size and direction."""
    try:
        import clr
        for ch in src.GetTextureChannels():
            own = clr.Reference[rg.Transform]()
            mapping = src.GetTextureMapping(ch, own)     # also returns how the object moved since it was mapped
            if mapping is not None:
                dst.SetTextureMapping(ch, mapping, xform * own.Value)
    except Exception:
        pass


def _export_glb(doc, objs, path):
    """Write `objs`, re-oriented to east/north/up, to a GLB. Returns their bounding box (model units, ENU)."""
    xf = enu_transform(doc)
    tmp = Rhino.RhinoDoc.CreateHeadless(None)
    bbox = rg.BoundingBox.Empty
    try:
        tmp.ModelUnitSystem = doc.ModelUnitSystem
        try:
            tmp.SetCustomMeshingParameters(doc.GetMeshingParameters(doc.MeshingParameterStyle))
            tmp.MeshingParameterStyle = Rhino.Geometry.MeshingParameterStyle.Custom
        except Exception:
            pass
        mats = {}

        def add(geo, src_obj, parent=None, moved=None):
            if not isinstance(geo, _MESHABLE):
                return
            g = geo.Duplicate()
            g.Transform(xf)
            attrs = Rhino.DocObjects.ObjectAttributes()
            rm = _effective_material(src_obj, parent)
            if rm is not None:
                key = str(rm.Id)
                if key not in mats:
                    c = rm.MakeCopy()
                    tmp.RenderMaterials.Add(c)
                    mats[key] = c
                attrs.RenderMaterial = mats[key]
            else:
                attrs.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
                attrs.ObjectColor = _display_color(doc, src_obj, parent)
            oid = tmp.Objects.Add(g, attrs)
            if oid != System.Guid.Empty:
                bbox.Union(g.GetBoundingBox(True))
                _copy_texture_mappings(src_obj, tmp.Objects.FindId(oid), xf if moved is None else xf * moved)

        for o in objs:
            if isinstance(o, Rhino.DocObjects.InstanceObject):
                res = o.Explode(True)
                pieces, pattrs, pxf = [r for r in res if not isinstance(r, bool)][-3:]
                for piece, t in zip(pieces, pxf):
                    g = piece.Geometry.Duplicate()
                    g.Transform(t)
                    add(g, piece, o, t)
            else:
                add(o.Geometry, o)

        opt = Rhino.FileIO.FileGltfWriteOptions()
        opt.MapZToY = True
        opt.ExportMaterials = True
        opt.UseDracoCompression = False
        if not Rhino.FileIO.FileGltf.Write(path, tmp, opt) or not os.path.exists(path):
            raise RuntimeError("glTF export failed")
    finally:
        tmp.Dispose()
    return bbox


# ----------------------------------------------------------------- publish
def _set_dir(name):
    return "set_" + env.safe_name(name, "set").replace(" ", "_")


def _write_earthpro(live, meta):
    ep_dir = os.path.join(live, "earthpro")
    os.makedirs(ep_dir, exist_ok=True)
    a = meta["anchor"]
    mode = "absolute" if a["zero"] == "MeanSeaLevel" else "relativeToGround"
    marks = []
    for name, s in sorted(meta["sets"].items()):
        if not s.get("dae"):
            continue
        p = (s.get("unplaced") and s.get("placement")) or {"rot": 0.0, "t": [0.0, 0.0, 0.0]}   # the EarthLink placement
        lat, lon = geometry.placed_location(a["lat"], a["lon"], p["t"])
        marks.append("""<Placemark><name>{n}</name><description>v{v}, sent {t}</description>
<Model><altitudeMode>{mode}</altitudeMode>
<Location><longitude>{lon:.9f}</longitude><latitude>{lat:.9f}</latitude><altitude>{alt:.3f}</altitude></Location>
<Orientation><heading>{heading:.6f}</heading><tilt>0</tilt><roll>0</roll></Orientation><Scale><x>1</x><y>1</y><z>1</z></Scale>
<Link><href>../{dae}</href></Link></Model></Placemark>""".format(
            n=_xml(name), v=s["version"], t=s["sent_at"], mode=mode, lon=lon, lat=lat, alt=a["elev"] + p["t"][2],
            heading=p["rot"] % 360.0, dae=s["dae"]))
    with open(os.path.join(ep_dir, "model.kml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>%s</name>\n%s\n</Document></kml>'
                 % (_xml(meta["name"]), "\n".join(marks)))
    master = os.path.join(ep_dir, "EarthLink.kml")
    with open(master, "w", encoding="utf-8") as fh:
        fh.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document><name>EarthLink (live from Rhino)</name>
<LookAt><longitude>{lon:.7f}</longitude><latitude>{lat:.7f}</latitude><altitude>0</altitude>
<heading>0</heading><tilt>60</tilt><range>350</range><altitudeMode>relativeToGround</altitudeMode></LookAt>
<NetworkLink><name>Rhino model</name><flyToView>0</flyToView><refreshVisibility>0</refreshVisibility>
<Link><href>model.kml</href><refreshMode>onInterval</refreshMode><refreshInterval>2</refreshInterval></Link>
</NetworkLink></Document></kml>""".format(lon=a["lon"], lat=a["lat"]))
    return master


def _xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_meta():
    try:
        with open(os.path.join(env.live_dir(), "meta.json")) as fh:
            return json.load(fh)
    except Exception:
        return {}


def send_set(doc, name, to_earthpro=False):
    """Export one set and publish it. Returns (meta, messages, earthpro_master_kml or None)."""
    objs = set_objects(doc, name)
    if not objs:
        raise RuntimeError("set '%s' has no objects left" % name)
    live = env.live_dir()
    pid = project_id(doc)
    meta = load_meta()
    if meta.get("project") != pid:          # another file was showing: start fresh
        meta = {"version": meta.get("version", 0), "sets": {}}
    version = int(meta.get("version", 0)) + 1
    sd = _set_dir(name)
    vd_rel = "%s/v%05d" % (sd, version)
    vd = os.path.join(live, sd, "v%05d" % version)
    os.makedirs(vd, exist_ok=True)
    bbox = _export_glb(doc, objs, os.path.join(vd, "model.glb"))
    try:            # one piece per material: the browser draws tens, not tens of thousands, of pieces per frame
        geometry.merge_glb(os.path.join(vd, "model.glb"))
    except Exception:
        pass        # the unmerged file still displays, only slower
    try:            # glass and other see-through materials: Rhino writes them in a form real-time viewers ignore
        geometry.screen_materials(os.path.join(vd, "model.glb"))
    except Exception:
        pass
    scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    entry = {"glb": vd_rel + "/model.glb", "version": version, "objects": len(objs),
             "bbox_m": [[bbox.Min.X * scale, bbox.Min.Y * scale, bbox.Min.Z * scale],
                        [bbox.Max.X * scale, bbox.Max.Y * scale, bbox.Max.Z * scale]] if bbox.IsValid else None,
             "sent_at": time.strftime("%Y-%m-%d %H:%M:%S"),
             "live": bool(get_sets(doc).get(name, {}).get("live")),
             "unplaced": True,     # the geometry is where it is in Rhino; the viewer applies "placement"
             "format": EXPORT_FORMAT}
    if get_sets(doc).get(name, {}).get("placement"):
        entry["placement"] = placement(doc, name)
    msgs, master = [], None
    try:
        mesh = geometry.derive(os.path.join(vd, "model.glb"))
        env.write_json(os.path.join(vd, "geometry.json"), mesh)
        entry["geometry"] = vd_rel + "/geometry.json"
    except Exception as ex:
        entry["geometry_error"] = str(ex)
        msgs.append("Cutout unavailable for this export")
    if to_earthpro:
        try:
            tris = collada.glb_to_dae(os.path.join(vd, "model.glb"), vd)
            entry["dae"] = vd_rel + "/model.dae"
            msgs.append("Earth Pro updated (%d triangles)" % tris)
        except Exception as ex:
            msgs.append("Earth Pro export failed: %s" % ex)
    elif meta.get("sets", {}).get(name, {}).get("dae"):
        entry["dae"] = meta["sets"][name]["dae"]   # keep showing the last Earth Pro version

    meta.update(version=version, project=pid, name=project_name(doc), anchor=anchor_info(doc),
                sent_at=entry["sent_at"], lights=lights_info(doc))
    meta.setdefault("sets", {})[name] = entry
    if entry.get("dae") or any(s.get("dae") for s in meta["sets"].values()):
        master = _write_earthpro(live, meta)
    env.write_json(os.path.join(live, "meta.json"), meta)   # atomic: the viewer only sees complete files
    _prune(live, sd)
    return meta, msgs, master


def remove_set_from_viewer(name):
    meta = load_meta()
    if name in meta.get("sets", {}):
        meta["sets"].pop(name)
        meta["version"] = int(meta.get("version", 0)) + 1
        env.write_json(os.path.join(env.live_dir(), "meta.json"), meta)
        shutil.rmtree(os.path.join(env.live_dir(), _set_dir(name)), ignore_errors=True)
        if meta.get("anchor"):
            _write_earthpro(env.live_dir(), meta)


def _prune(live, sd):
    for old in sorted(glob.glob(os.path.join(live, sd, "v[0-9]*")))[:-KEEP_VERSIONS]:
        shutil.rmtree(old, ignore_errors=True)
