"""Enscape-style link with Rhino, driven by an Eto UI timer on Rhino's UI thread (no background threads).

Every tick (0.2 s), for the document being synced:
  * follow viewport  - Rhino's active camera -> live/camera.json (viewer follows)          [link_viewport]
  * live sets        - sets marked Live (or moved from the viewer) are re-sent ~1 s after they change
  * site location    - EarthAnchorPoint edits in Rhino re-send all sets; a location picked in the
                       viewer (live/anchor_request.json) is written into the EarthAnchorPoint
  * sun              - Rhino Sun date/time <-> viewer sun, and the Sun's location/north from the anchor [sync_sun]
  * named views      - two-way, about once a second                                       [sync_views]
"""
import os, time, math

import Rhino
import System
import scriptcontext as sc

from earthlink import env, views, core

_STICKY = "earthlink_sync_timer"
_S = {"doc_sn": None, "known": {}, "project": None, "last_cam": None, "was_linked": False,
      "slow": 0.0, "anchor": None, "live": {}, "follow": set(), "sun_utc": None, "sun_linked": False, "sun_seen": 0.0, "errors": 0}


def _doc():
    sn = _S["doc_sn"]
    return Rhino.RhinoDoc.FromRuntimeSerialNumber(sn) if sn is not None else None


def _shown(doc):
    """True when the viewer is showing this document's project."""
    return env.current_project() == core.project_id(doc)


def log(msg):
    Rhino.RhinoApp.WriteLine("EarthLink: " + msg)


# ------------------------------------------------------------------ sending
def send_sets(doc, names=None, reason=""):
    s = env.load_settings()
    names = list(core.get_sets(doc)) if names is None else names
    done = []
    for name in names:
        if not core.set_objects(doc, name):
            continue
        try:
            meta, msgs, master = core.send_set(doc, name, to_earthpro=bool(s.get("earthpro")))
            done.append(name)
        except Exception as ex:
            log("could not send '%s': %s" % (name, ex))
    if done:
        _S["anchor"] = core.anchor_info(doc)
        log("sent %s%s." % (", ".join(done), (" (" + reason + ")") if reason else ""))
    return done


# ------------------------------------------------------------------ camera
def push_camera(force=False):
    doc = _doc()
    if doc is None or not core.anchor_ok(doc) or not _shown(doc):
        return
    cam = views.active_camera(doc)
    if force or not views.same(cam, _S["last_cam"]):
        _S["last_cam"] = cam
        env.write_json(env.camera_path(), dict(cam, t=time.time()))


# ------------------------------------------------------------------ site location
def _apply_anchor_request(doc):
    path = env.live_file("anchor_request.json")
    req = env.read_json(path)
    if not req:
        return
    if req.get("project") != core.project_id(doc):
        return
    try:
        os.remove(path)
    except OSError:
        pass
    first = not core.anchor_ok(doc)
    # A new file gets "ground level, 0 m". An existing anchor keeps its elevation and reference;
    # with a ground-level reference the picked spot's ground height is used directly.
    core.set_anchor(doc, lat=req.get("lat"), lon=req.get("lon"), rotate_deg=float(req.get("rotate") or 0.0),
                    elev=0.0 if first else None,
                    zero=Rhino.DocObjects.BasepointZero.GroundLevel if first else None)
    if req.get("lat") is not None:
        patch = {"nudge": 0.0}
        if req.get("ground_h") is not None and str(doc.EarthAnchorPoint.EarthBasepointElevationZero) == "GroundLevel":
            patch["ground_h"] = float(req["ground_h"])
        env.save_settings(patch)
    log("site location updated from the viewer (%.6f, %.6f%s). EarthAnchorPoint shows the same values."
        % (doc.EarthAnchorPoint.EarthBasepointLatitude, doc.EarthAnchorPoint.EarthBasepointLongitude,
           ", turned %.1f deg" % float(req.get("rotate") or 0) if req.get("rotate") else ""))
    pending = [n for n, v in core.get_sets(doc).items() if v.get("pending")]
    for n in pending:
        core.put_set(doc, n, pending=False)
    try:
        os.remove(env.live_file("pick_request.json"))
    except OSError:
        pass
    send_sets(doc, reason="new site location")   # anchor watcher sees no change after this


def _watch_anchor(doc):
    if not core.anchor_ok(doc):
        return
    a = core.anchor_info(doc)
    if _S["anchor"] is None:
        _S["anchor"] = a
        return
    if a != _S["anchor"]:
        _S["anchor"] = a
        if _shown(doc) or not env.current_meta():
            send_sets(doc, reason="EarthAnchorPoint changed")
        _sun_location(doc, force=True)


# ------------------------------------------------------------------ design sets
def _watch_sets(doc):
    """Sets deleted in the viewer are forgotten here; sets missing from the viewer (e.g. after
    another file was shown) are sent again."""
    path = env.live_file("deleted_sets.json")
    d = env.read_json(path)
    if d and d.get("project") == core.project_id(doc):
        for n in d.get("names", []):
            core.drop_set(doc, n)
            _S["live"].pop(n, None)
            _S["follow"].discard(n)
        try:
            os.remove(path)
        except OSError:
            pass
        log("removed set(s) %s (deleted in the viewer; geometry untouched)." % ", ".join(d.get("names", [])))
    meta_sets = env.current_meta().get("sets", {})
    missing = [n for n, v in core.get_sets(doc).items()
               if not v.get("pending") and n not in meta_sets and core.set_objects(doc, n)]
    if missing:
        send_sets(doc, missing, reason="restoring")


def _apply_requests(doc):
    """Renames and moves made in the viewer (live/requests/*.json), applied in order."""
    d = env.live_file("requests")
    if not os.path.isdir(d):
        return
    pid = core.project_id(doc)
    for f in sorted(os.listdir(d)):
        path = os.path.join(d, f)
        req = env.read_json(path) or {}
        if req.get("project") != pid:
            continue
        try:
            os.remove(path)
        except OSError:
            continue
        name = req.get("name")
        if req.get("type") == "rename_set":
            if core.rename_set(doc, name, req.get("new")):
                if name in _S["live"]:
                    _S["live"][req["new"]] = _S["live"].pop(name)
                if name in _S["follow"]:
                    _S["follow"].discard(name); _S["follow"].add(req["new"])
                if sc.sticky.get("earthlink_last_set") == name:
                    sc.sticky["earthlink_last_set"] = req["new"]
                log("renamed set '%s' to '%s'." % (name, req["new"]))
        elif req.get("type") == "move_set":
            n = core.move_set(doc, name, req.get("dx", 0), req.get("dy", 0), req.get("dz", 0), req.get("rot", 0), req.get("pivot", (0, 0, 0)))
            if n:
                log("moved %d object(s) of '%s' as placed in the viewer (Undo reverts it)." % (n, name))
                send_sets(doc, [name], reason="moved")
                mark_sent(doc, name)
                _S["follow"].add(name)   # watched from now on, so Undo/Redo in Rhino shows in the viewer


# ------------------------------------------------------------------ live sets
def _watch_live(doc):
    now = time.time()
    for name, info in core.get_sets(doc).items():
        if not info.get("live") and name not in _S["follow"]:
            continue
        objs = core.set_objects(doc, name)
        sig = core.signature(objs)
        st = _S["live"].setdefault(name, {"sent": sig, "changed": None})
        if sig == st["sent"]:
            st["changed"] = None
            continue
        if st["changed"] is None:
            st["changed"] = now
        elif now - st["changed"] > 0.8 and not Rhino.Commands.Command.InCommand() and objs:
            st["sent"], st["changed"] = sig, None
            send_sets(doc, [name], reason="live")


def mark_sent(doc, name):
    _S["live"][name] = {"sent": core.signature(core.set_objects(doc, name)), "changed": None}


# ------------------------------------------------------------------ sun
def _rhino_sun(doc):
    try:
        return doc.Lights.Sun
    except Exception:
        return None


def _change(sun, fn):
    began = False
    try:
        sun.BeginChange(Rhino.Render.RenderContent.ChangeContexts.Program); began = True
    except Exception:
        pass
    try:
        fn()
    finally:
        if began:
            try:
                sun.EndChange()
            except Exception:
                pass


def _sun_location(doc, force=False):
    sun = _rhino_sun(doc)
    if sun is None or not core.anchor_ok(doc):
        return
    ep = doc.EarthAnchorPoint
    lat, lon, north = ep.EarthBasepointLatitude, ep.EarthBasepointLongitude, core.north_angle(doc)
    if force or abs(sun.Latitude - lat) > 1e-6 or abs(sun.Longitude - lon) > 1e-6 or abs(sun.North - north) > 1e-3:
        def apply():
            sun.Latitude, sun.Longitude, sun.North = lat, lon, north
        _change(sun, apply)


def _utc_str(dt):
    return dt.ToString("yyyy-MM-ddTHH:mm:ss") + "Z"


def _sync_sun(doc):
    sun = _rhino_sun(doc)
    if sun is None:
        return
    _sun_location(doc)
    path = env.live_file("sun.json")
    f = env.read_json(path, {}) or {}
    rh = _utc_str(sun.GetDateTime(System.DateTimeKind.Utc))
    project = core.project_id(doc)
    state = (rh, bool(sun.Enabled))
    if _S["sun_utc"] is None:    # Rhino owns the sun on first connection/reconnection.
        t = time.time()
        _S["sun_utc"], _S["sun_seen"] = state, t
        env.write_json(path, {"utc": rh, "enabled": state[1], "project": project, "source": "rhino", "t": t})
        env.save_settings({"sun_enabled": state[1], "sun_utc": rh})
        return
    if f.get("source") == "viewer" and f.get("project", project) == project and f.get("t", 0) > _S["sun_seen"]:
        _S["sun_seen"] = f["t"]
        u = f.get("utc", "")
        try:
            y, mo, d = int(u[0:4]), int(u[5:7]), int(u[8:10])
            h, mi = int(u[11:13]), int(u[14:16])
            dt = System.DateTime(y, mo, d, h, mi, 0, System.DateTimeKind.Unspecified)
            def apply():
                if f.get("tz") is not None:
                    sun.TimeZone = float(f["tz"]) / 60.0
                    sun.DaylightSavingOn = False
                sun.SetDateTime(dt, System.DateTimeKind.Utc)
                if isinstance(f.get("enabled"), bool):
                    sun.Enabled = f["enabled"]
            _change(sun, apply)
            _S["sun_utc"] = (_utc_str(sun.GetDateTime(System.DateTimeKind.Utc)), bool(sun.Enabled))
        except Exception as ex:
            log("could not set the Rhino Sun: %s" % ex)
        return
    if state != _S["sun_utc"]:
        _S["sun_utc"] = state
        t = time.time()
        _S["sun_seen"] = t
        env.write_json(path, {"utc": rh, "enabled": state[1], "project": project, "source": "rhino", "t": t})
        env.save_settings({"sun_enabled": state[1], "sun_utc": rh})


# ------------------------------------------------------------------ timer
def _tick(sender, e):
    doc = _doc()
    if doc is None:
        return
    try:
        _apply_anchor_request(doc)
        s = env.load_settings()
        if core.anchor_ok(doc):
            linked = bool(s.get("link_viewport"))
            if linked:
                push_camera(force=not _S["was_linked"])
            _S["was_linked"] = linked
            now = time.time()
            if now - _S["slow"] > 0.5:
                _S["slow"] = now
                _watch_anchor(doc)
                if _shown(doc):
                    _apply_requests(doc)
                    _watch_sets(doc)
                _watch_live(doc)
                sun_linked = bool(s.get("sync_sun", True) and _shown(doc))
                if sun_linked and not _S.get("sun_linked"):
                    _S["sun_utc"] = None
                _S["sun_linked"] = sun_linked
                if sun_linked:
                    _sync_sun(doc)
                if s.get("sync_views", True) and _shown(doc):
                    pid = core.project_id(doc)
                    if pid != _S["project"]:
                        _S["project"], _S["known"] = pid, {}
                    a, b, c = views.reconcile(doc, pid, _S["known"])
                    if a or b or c:
                        log("named views synced (%d to Rhino, %d to viewer, %d deleted)." % (a, b, c))
        _S["errors"] = 0
    except Exception as ex:
        _S["errors"] += 1
        if _S["errors"] in (1, 5):
            log("sync problem: %s" % ex)
        if _S["errors"] >= 5:
            log("sync paused after repeated errors - run EarthLinkSync to restart it.")
            stop()


def start(doc):
    """Start (or retarget) syncing for `doc`. Safe to call repeatedly."""
    if _S["doc_sn"] != doc.RuntimeSerialNumber:
        _S.update(doc_sn=doc.RuntimeSerialNumber, known={}, project=None, last_cam=None, anchor=None,
                  live={}, follow=set(), sun_utc=None, sun_linked=False, errors=0)
    old = sc.sticky.get(_STICKY)
    if old is not None and old.get("sid") == id(_S):
        return
    stop()
    import Eto.Forms as ef
    t = ef.UITimer()
    t.Interval = 0.2
    t.Elapsed += _tick
    t.Start()
    sc.sticky[_STICKY] = {"timer": t, "sid": id(_S)}


def stop():
    old = sc.sticky.pop(_STICKY, None)
    if old is not None:
        try:
            old["timer"].Stop()
        except Exception:
            pass
        return True
    return False


def running():
    return sc.sticky.get(_STICKY) is not None
