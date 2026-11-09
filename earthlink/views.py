"""Camera conversion and two-way named-view sync between Rhino and the EarthLink viewer.

Cameras are stored in the model's local frame: metres east/north/up from the EarthAnchorPoint
(the frame SendToEarth exports in):
  projection: "perspective" | "two_point" | "parallel"
  pos, dir, up : [x, y, z]
  vfov         : vertical field of view (rad)               (perspective, two_point)
  shift        : vertical lens shift = tan(view-centre elevation)  (two_point)
  half_height  : half the view height in metres             (parallel)
"""
import math

import Rhino
import Rhino.Geometry as rg

from earthlink import env, core

CAM_KEYS = ("projection", "pos", "dir", "up", "vfov", "shift", "half_height")


def _frames(doc):
    to_enu = core.enu_transform(doc)
    ok, from_enu = to_enu.TryGetInverse()
    return to_enu, from_enu, Rhino.RhinoMath.UnitScale(doc.ModelUnitSystem, Rhino.UnitSystem.Meters)


def _frustum(vi):
    """(left, right, bottom, top, near, far), whichever way pythonnet returns out-parameters."""
    try:
        r = vi.GetFrustum()
    except TypeError:
        r = vi.GetFrustum(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return [v for v in r if not isinstance(v, bool)][-6:]


def vi_to_cam(doc, vi):
    to_enu, _, s = _frames(doc)
    loc = rg.Point3d(vi.CameraLocation); loc.Transform(to_enu)
    d = rg.Vector3d(vi.CameraDirection); d.Transform(to_enu); d.Unitize()
    up = rg.Vector3d(vi.CameraUp); up.Transform(to_enu); up.Unitize()
    l, r, b, t, n, f = _frustum(vi)
    cam = {"pos": [loc.X * s, loc.Y * s, loc.Z * s], "dir": [d.X, d.Y, d.Z], "up": [up.X, up.Y, up.Z]}
    if vi.IsParallelProjection:
        cam.update(projection="parallel", half_height=(t - b) / 2.0 * s)
    elif getattr(vi, "IsTwoPointPerspectiveProjection", False):
        cam.update(projection="two_point", vfov=2 * math.atan((t - b) / 2.0 / n), shift=((t + b) / 2.0) / n)
    else:
        cam.update(projection="perspective", vfov=2 * math.atan((t - b) / 2.0 / n))
    return cam


def cam_to_vi(doc, vp, cam):
    """A ViewportInfo (sized like viewport `vp`) showing `cam`."""
    _, from_enu, s = _frames(doc)
    loc = rg.Point3d(*(c / s for c in cam["pos"])); loc.Transform(from_enu)
    d = rg.Vector3d(*cam["dir"]); d.Transform(from_enu); d.Unitize()
    up = rg.Vector3d(*cam["up"]); up.Transform(from_enu); up.Unitize()
    vi = Rhino.DocObjects.ViewportInfo(vp)
    proj = cam.get("projection", "perspective")
    aspect = float(vp.Size.Width or 1) / float(vp.Size.Height or 1)
    if proj == "parallel":
        vi.ChangeToParallelProjection(True)
    elif proj == "two_point" and hasattr(vi, "ChangeToTwoPointPerspectiveProjection"):
        vi.ChangeToTwoPointPerspectiveProjection(60.0 / s, rg.Vector3d.ZAxis, 50.0)
    else:
        vi.ChangeToPerspectiveProjection(True, 50.0)
    vi.SetCameraLocation(loc)
    vi.SetCameraDirection(d)
    vi.SetCameraUp(up)
    l, r, b, t, n, f = _frustum(vi)
    if proj == "parallel":
        hh = cam.get("half_height", 50.0) / s
        vi.SetFrustum(-hh * aspect, hh * aspect, -hh, hh, n, f)
    else:
        th = math.tan(float(cam.get("vfov") or math.radians(45)) / 2.0)
        sh = float(cam.get("shift") or 0.0) if proj == "two_point" else 0.0
        vi.SetFrustum(-th * aspect * n, th * aspect * n, (sh - th) * n, (sh + th) * n, n, f)
    vi.TargetPoint = loc + d * (60.0 / s)
    return vi


def same(a, b):
    if not a or not b or a.get("projection", "perspective") != b.get("projection", "perspective"):
        return False
    close = lambda x, y, tol: all(abs(p - q) <= tol for p, q in zip(x, y))
    if not (close(a["pos"], b["pos"], 0.02) and close(a["dir"], b["dir"], 2e-3) and close(a["up"], b["up"], 2e-3)):
        return False
    if a.get("projection") == "parallel":
        return abs(a.get("half_height", 0) - b.get("half_height", 0)) <= 1e-3 * max(1.0, abs(a.get("half_height", 1)))
    return abs(a.get("vfov", 0) - b.get("vfov", 0)) <= 2e-3 and abs(a.get("shift", 0) - b.get("shift", 0)) <= 2e-3


def cam_only(v):
    return {k: v[k] for k in CAM_KEYS if k in v}


# ----------------------------------------------------------------- Rhino named views
def rhino_views(doc):
    out = {}
    for i in range(doc.NamedViews.Count):
        nv = doc.NamedViews[i]
        try:
            out[nv.Name] = vi_to_cam(doc, nv.Viewport)
        except Exception:
            pass
    return out


def _add_direct(doc, name, vi):
    """Add a named view without touching any visible viewport (verified after adding)."""
    info = Rhino.DocObjects.ViewInfo(doc.Views.ActiveView.ActiveViewport)
    info.Name = name
    info.Viewport = vi
    doc.NamedViews.Add(info)
    idx = doc.NamedViews.FindByName(name)
    return idx >= 0


def put_rhino_view(doc, name, cam):
    vp = doc.Views.ActiveView.ActiveViewport
    vi = cam_to_vi(doc, vp, cam)
    idx = doc.NamedViews.FindByName(name)
    if idx >= 0:
        doc.NamedViews.Delete(idx)
    try:
        if _add_direct(doc, name, vi) and same(vi_to_cam(doc, doc.NamedViews[doc.NamedViews.FindByName(name)].Viewport), cam):
            return
        idx = doc.NamedViews.FindByName(name)
        if idx >= 0:
            doc.NamedViews.Delete(idx)
    except Exception:
        pass
    # fallback: briefly set the active viewport (no redraw), save it, restore it
    backup = Rhino.DocObjects.ViewportInfo(vp)
    redraw = doc.Views.RedrawEnabled
    doc.Views.RedrawEnabled = False
    try:
        vp.SetViewProjection(vi, False)
        doc.NamedViews.Add(name, vp.Id)
    finally:
        vp.SetViewProjection(backup, False)
        doc.Views.RedrawEnabled = redraw


def delete_rhino_view(doc, name):
    idx = doc.NamedViews.FindByName(name)
    if idx >= 0:
        doc.NamedViews.Delete(idx)


def reconcile(doc, project, known):
    """Two-way sync. `known` maps name -> camera as of the last sync (kept by the caller).
    A side that changed since the last sync wins; on first contact Rhino wins.
    Returns (to_rhino, to_viewer, deleted)."""
    R = rhino_views(doc)
    V = {v["name"]: v for v in env.load_views(project) if v.get("name")}
    first = not known
    to_r = to_v = dele = 0
    changed = False
    for name in set(R) | set(V):
        r, v, k = R.get(name), V.get(name), known.get(name)
        vc = cam_only(v) if v else None
        if r is not None and v is not None:
            if same(r, vc):
                continue
            if first or not same(r, k):             # Rhino changed (or first contact): Rhino wins
                V[name] = dict({x: y for x, y in v.items() if x not in CAM_KEYS}, **r); changed = True; to_v += 1
            else:                                   # the viewer changed it
                put_rhino_view(doc, name, vc); R[name] = vc; to_r += 1
        elif r is not None:
            if k is not None and not first:         # deleted in the viewer
                delete_rhino_view(doc, name); R.pop(name); dele += 1
            else:                                   # new in Rhino - or renamed there: keep the viewer's extras (sun time)
                gone = next((n for n, x in V.items() if n not in R and known.get(n) and same(cam_only(x), r)), None)
                extra = {x: y for x, y in V[gone].items() if x not in CAM_KEYS and x != "name"} if gone else {"source": "rhino"}
                V[name] = dict(extra, **r, name=name); changed = True; to_v += 1
        else:
            if k is not None and not first:         # deleted in Rhino
                V.pop(name); changed = True; dele += 1
            else:                                   # new in the viewer
                put_rhino_view(doc, name, vc); R[name] = vc; to_r += 1
    if changed:
        env.save_views(project, sorted(V.values(), key=lambda x: x["name"].lower()))
    known.clear()
    known.update({n: cam_only(V[n]) for n in V})
    return to_r, to_v, dele


def active_camera(doc):
    return vi_to_cam(doc, Rhino.DocObjects.ViewportInfo(doc.Views.ActiveView.ActiveViewport))
