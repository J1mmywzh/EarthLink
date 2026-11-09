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


def set_anchor(doc, lat=None, lon=None, rotate_deg=0.0, elev=None, zero=None):
    """Update the EarthAnchorPoint (the same thing the EarthAnchorPoint command edits).
    rotate_deg turns the model clockwise on the map (north turns counter-clockwise in the model)."""
    ep = doc.EarthAnchorPoint
    new = Rhino.DocObjects.EarthAnchorPoint()
    new.EarthBasepointLatitude = ep.EarthBasepointLatitude if lat is None else lat
    new.EarthBasepointLongitude = ep.EarthBasepointLongitude if lon is None else lon
    new.EarthBasepointElevation = ep.EarthBasepointElevation if elev is None else elev
    new.EarthBasepointElevationZero = ep.EarthBasepointElevationZero if zero is None else zero
    new.ModelBasePoint = ep.ModelBasePoint
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
        env.save_settings({"hidden_sets": [new if n == old else n for n in s.get("hidden_sets") or []], "set_styles": st})


# ----------------------------------------------------------------- placement (EarthLink only; Rhino geometry never moves)
def placement(doc, name):
    """A set's EarthLink placement: turned `rot` degrees clockwise on the map, then moved by `t`
    (metres east/north/up). Applied on every export, so the Rhino model keeps its own grid."""
    p = get_sets(doc).get(name, {}).get("placement") or {}
    return {"rot": float(p.get("rot", 0.0)), "t": [float(v) for v in (p.get("t") or [0.0, 0.0, 0.0])][:3]}


def place_set(doc, name, dx=0.0, dy=0.0, dz=0.0, rot=0.0, pivot=(0, 0, 0)):
    """Compose a viewer move (turn `rot` clockwise about `pivot`, then move) onto the set's placement."""
    if name not in get_sets(doc):
        return None
    new = geometry.compose_placement(get_sets(doc)[name].get("placement"), dx, dy, dz, rot, pivot)
    put_set(doc, name, placement=new)
    return new or {}


def reset_placement(doc, name):
    if name in get_sets(doc):
        put_set(doc, name, placement=None)


def placement_transform(doc, name):
    """Placement as a Rhino transform in the ENU frame, model units."""
    p, s = placement(doc, name), Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    return rg.Transform.Translation(rg.Vector3d(*(v / s for v in p["t"]))) * \
        rg.Transform.Rotation(math.radians(-p["rot"]), rg.Vector3d.ZAxis, rg.Point3d.Origin)


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


def _export_glb(doc, objs, path, place=None):
    """Write `objs` (re-oriented to ENU, then placed) to a GLB. Returns their bounding box (model units, ENU)."""
    xf = enu_transform(doc) if place is None else place * enu_transform(doc)
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

        def add(geo, src_obj, parent=None):
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
            if tmp.Objects.Add(g, attrs) != System.Guid.Empty:
                bbox.Union(g.GetBoundingBox(True))

        for o in objs:
            if isinstance(o, Rhino.DocObjects.InstanceObject):
                res = o.Explode(True)
                pieces, pattrs, pxf = [r for r in res if not isinstance(r, bool)][-3:]
                for piece, t in zip(pieces, pxf):
                    g = piece.Geometry.Duplicate()
                    g.Transform(t)
                    add(g, piece, o)
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
        marks.append("""<Placemark><name>{n}</name><description>v{v}, sent {t}</description>
<Model><altitudeMode>{mode}</altitudeMode>
<Location><longitude>{lon:.9f}</longitude><latitude>{lat:.9f}</latitude><altitude>{alt:.3f}</altitude></Location>
<Orientation><heading>0</heading><tilt>0</tilt><roll>0</roll></Orientation><Scale><x>1</x><y>1</y><z>1</z></Scale>
<Link><href>../{dae}</href></Link></Model></Placemark>""".format(
            n=_xml(name), v=s["version"], t=s["sent_at"], mode=mode, lon=a["lon"], lat=a["lat"], alt=a["elev"], dae=s["dae"]))
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
    bbox = _export_glb(doc, objs, os.path.join(vd, "model.glb"), placement_transform(doc, name))
    scale = Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    entry = {"glb": vd_rel + "/model.glb", "version": version, "objects": len(objs),
             "bbox_m": [[bbox.Min.X * scale, bbox.Min.Y * scale, bbox.Min.Z * scale],
                        [bbox.Max.X * scale, bbox.Max.Y * scale, bbox.Max.Z * scale]] if bbox.IsValid else None,
             "sent_at": time.strftime("%Y-%m-%d %H:%M:%S"),
             "live": bool(get_sets(doc).get(name, {}).get("live"))}
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
                sent_at=entry["sent_at"])
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
