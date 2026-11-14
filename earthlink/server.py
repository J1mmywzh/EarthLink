"""EarthLink viewer server - runs as its OWN process (never inside Rhino), with Rhino 8's bundled
CPython or any Python 3. Standard library only. Bound to 127.0.0.1.

    python server.py --viewer <folder with index.html> [--port 8765]

Rhino talks to it only through files in the EarthLink data folder:
  live/meta.json     -> 'model' event      live/camera.json -> 'camera' event
  views/<model>.json -> 'views' event      settings.json    (shared settings)

From Rhino use start()/stop()/running(); they launch or stop the process.
"""
import os, sys, json, math, time, socket, subprocess, base64, threading

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from earthlink import env, geometry, context  # noqa: E402
import earthlink  # noqa: E402

SETTING_KEYS = ("nudge", "geoid_offset", "ground_h", "clip", "clip_sets", "clip_margin", "shadows", "save_mode",
                "link_viewport", "sync_views", "sync_sun", "style", "ghost", "hidden_sets", "set_styles", "sun_enabled", "sun_utc", "lights", "view")
VIEWER_ASSETS = ("index.html", "navigation.js", "walk.js", "footprints.js", "footprint-worker.js")


# ======================================================================= Rhino-side control
def port_in_use(port=None):
    try:
        with socket.create_connection(("127.0.0.1", port or env.PORT), timeout=0.3):
            return True
    except OSError:
        return False


def _ping(full=False):
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % env.PORT, timeout=1) as r:
            info = json.loads(r.read())
            return info if full and info.get("earthlink") else bool(info.get("earthlink"))
    except Exception:
        return False


def _same_dir(a, b):
    return bool(a and b) and os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def running():
    return port_in_use() and bool(_ping())


def start(viewer_dir=None):
    """Launch the server process if needed. Returns 'started', 'running' or 'busy'.
    A server left over from another EarthLink version (it serves a different viewer folder, which an
    update may have removed) is replaced."""
    vdir = viewer_dir or env.viewer_dir()
    if port_in_use():
        info = _ping(full=True)
        if not info:
            return "busy"
        if _same_dir(info.get("viewer"), vdir):
            return "running"
        stop()
        for _ in range(30):
            time.sleep(0.1)
            if not port_in_use():
                break
        else:
            return "busy"
    py = env.python_exe()
    if not py:
        raise RuntimeError("no Python 3 found to run the viewer server")
    log = open(os.path.join(env.data_dir(), "server.log"), "a")
    kw = {}
    if env.IS_WIN:
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED | NEW_GROUP | NO_WINDOW
    else:
        kw["start_new_session"] = True
    subprocess.Popen([py, os.path.abspath(__file__), "--viewer", vdir, "--port", str(env.PORT)], cwd=env.data_dir(),
                     stdout=log, stderr=log, stdin=subprocess.DEVNULL, close_fds=True, **kw)
    for _ in range(50):
        time.sleep(0.1)
        if port_in_use():
            break
    return "started"


def stop():
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:%d/api/shutdown" % env.PORT, data=b"{}", method="POST",
                                     headers={"X-EarthLink": "1"})
        urllib.request.urlopen(req, timeout=2).read()
        return True
    except Exception:
        return False


def url():
    return "http://127.0.0.1:%d/" % env.PORT


# ======================================================================= server process
def _read(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


def _mtime(path):
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None


def _settings_out():
    s = env.load_settings()
    out = {k: s.get(k) for k in SETTING_KEYS}
    out["snapshot_dir"] = env.snapshot_dir()
    return out


def _save_snapshot(data):
    png = data.get("png") or ""
    if not png.startswith("data:image/png;base64,"):
        return {"error": "no image"}
    cam = data.get("camera") or {}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = "%s_%s_%s_%dx%d_%s" % (env.safe_name(cam.get("model") or "model"), env.safe_name(data.get("view") or "view"),
                                 env.safe_name(data.get("pass") or "full"), int(data.get("width", 0)), int(data.get("height", 0)), stamp)
    d = env.snapshot_dir()
    path = os.path.join(d, base + ".png")
    n = 2
    while os.path.exists(path):
        path = os.path.join(d, "%s_%d.png" % (base, n)); n += 1
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(png.split(",", 1)[1]))
    with open(os.path.splitext(path)[0] + ".json", "w") as fh:
        json.dump(cam, fh, indent=1)
    return {"file": path}


def _queue_for_rhino(req):
    """Requests Rhino applies on its next sync tick (it is the owner of the geometry and the .3dm)."""
    d = env.live_file("requests")
    os.makedirs(d, exist_ok=True)
    req = dict(req, t=time.time())
    env.write_json(os.path.join(d, "%.6f.json" % req["t"]), req)


# ----------------------------------------------------------------- site context from open data (context.py)
_CONTEXT = {"state": "idle"}


def _context_start(data, build=None):
    """Fetch terrain, buildings and roads for a rectangle in a worker thread; Rhino adds the result on its next tick."""
    if _CONTEXT.get("state") == "working":
        return dict(_CONTEXT)
    meta = env.current_meta()
    try:
        bounds = context.check_bounds(data.get("bounds") or {})
        if not (meta.get("anchor") or {}).get("lat") and (meta.get("anchor") or {}).get("lat") != 0:
            raise context.ContextError("Place the model on the map first (SendToEarth).")
    except context.ContextError as e:
        _CONTEXT.clear(); _CONTEXT.update(state="error", message=str(e))
        return dict(_CONTEXT)
    job = "context_%d.json" % int(time.time() * 1000)
    _CONTEXT.clear(); _CONTEXT.update(state="working", message="Starting", job=job, progress=0.02)
    want = {k: data.get(k, True) is not False for k in ("terrain", "buildings", "roads")}

    def run():
        try:
            out = (build or context.build)(bounds, meta.get("anchor"), env.load_settings(),
                                           progress=lambda text, part=None: _CONTEXT.update(message=text, **({"progress": part} if part is not None else {})), **want)
            env.write_json(env.live_file(job), out)
            _queue_for_rhino({"type": "context", "file": job, "project": meta.get("project")})
            _CONTEXT.update(state="sent", message="Rhino is adding it", counts=out["counts"], progress=0.9)
        except context.ContextError as e:
            _CONTEXT.update(state="error", message=str(e))
        except Exception as e:           # never leave the viewer waiting
            _CONTEXT.update(state="error", message="The import failed: %s" % (e,))
    threading.Thread(target=run, daemon=True).start()
    return dict(_CONTEXT)


def _context_status():
    if _CONTEXT.get("state") == "sent":      # Rhino reports back in a small file
        done = env.read_json(env.live_file("context_result.json")) or {}
        if done.get("file") == _CONTEXT.get("job"):
            _CONTEXT.update(state="done" if done.get("ok") else "error", message=done.get("message", ""))
    return dict(_CONTEXT)


def _rename_in_settings(old, new):
    s = env.load_settings()
    ren = lambda key: [new if n == old else n for n in s.get(key) or []]
    st = dict(s.get("set_styles") or {})
    if old in st:
        st[new] = st.pop(old)
    env.save_settings({"hidden_sets": ren("hidden_sets"), "clip_sets": ren("clip_sets"), "set_styles": st})


def _sets_op(data):
    meta = _read(os.path.join(env.live_dir(), "meta.json"), {})
    op, name = data.get("op"), data.get("name")
    if name not in meta.get("sets", {}):
        return {"error": "unknown set"}
    if op == "delete":
        meta["sets"].pop(name)
        dpath = env.live_file("deleted_sets.json")
        d = _read(dpath, {}) or {}
        if d.get("project") != meta.get("project"):
            d = {"project": meta.get("project"), "names": []}
        d["names"] = sorted(set(d["names"]) | {name})
        env.write_json(dpath, d)
    elif op == "rename":
        new = str(data.get("new") or "").strip()[:60]
        if not new or new in meta["sets"]:
            return {"error": "pick a new, unused name"}
        meta["sets"] = {(new if k == name else k): v for k, v in meta["sets"].items()}
        _rename_in_settings(name, new)
        _queue_for_rhino({"type": "rename_set", "project": meta.get("project"), "name": name, "new": new})
    elif op == "live":          # the same switch as SendToEarth's Live option
        on = bool(data.get("on"))
        _queue_for_rhino({"type": "set_live", "project": meta.get("project"), "name": name, "on": on})
        meta["sets"][name]["live"] = on
    elif op == "resend":        # "Update now": Rhino sends the set again
        _queue_for_rhino({"type": "send_set", "project": meta.get("project"), "name": name})
        return {"ok": True}
    elif op in ("place", "unplace"):   # EarthLink placement only: numbers the viewer applies. No geometry moves.
        try:
            p = None if op == "unplace" else geometry.clean_placement(data.get("rot"), data.get("t"))
        except (TypeError, ValueError):
            return {"error": "invalid placement"}
        if p and not all(math.isfinite(v) and abs(v) < 1e7 for v in [p["rot"]] + p["t"]):
            return {"error": "invalid placement"}
        # Rhino keeps it in the .3dm (queued first, so Rhino never sees meta ahead of its own copy without a request)
        q = p or {"rot": 0.0, "t": [0.0, 0.0, 0.0]}
        _queue_for_rhino({"type": "placement", "project": meta.get("project"), "name": name, "rot": q["rot"], "move": q["t"]})   # "t" is the request's time
        if p:
            meta["sets"][name]["placement"] = p
        else:
            meta["sets"][name].pop("placement", None)
    else:
        return {"error": "unknown operation"}
    meta["version"] = int(meta.get("version", 0)) + 1
    env.write_json(os.path.join(env.live_dir(), "meta.json"), meta)
    return {"ok": True}


def _anchor_request(data):
    pick = _read(env.live_file("pick_request.json"), {}) or {}
    project = pick.get("project") or _read(os.path.join(env.live_dir(), "meta.json"), {}).get("project")
    if not project:
        return {"error": "no Rhino file to update - run SendToEarth first"}
    req = {"project": project, "t": time.time()}
    for k in ("lat", "lon", "ground_h", "rotate"):
        if data.get(k) is not None:
            req[k] = float(data[k])
    env.write_json(env.live_file("anchor_request.json"), req)
    return {"ok": True, "project": project}


def _export_share(viewer_dir, embed_token):
    """A self-contained folder (zipped) that any static web host can serve: viewer + latest models + views."""
    import zipfile
    meta = _read(os.path.join(env.live_dir(), "meta.json"), {})
    if not meta.get("sets"):
        return {"error": "nothing sent yet"}
    s = env.load_settings()
    path = os.path.join(env.snapshot_dir(), "%s_share_%s.zip" % (env.safe_name(meta.get("name", "model")), time.strftime("%Y%m%d-%H%M%S")))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for asset in VIEWER_ASSETS:
            source = os.path.join(viewer_dir, *asset.split("/"))
            if os.path.isfile(source):
                z.write(source, asset)
        z.writestr("live/meta.json", json.dumps(meta, indent=1))
        for st in meta["sets"].values():
            z.write(os.path.join(env.live_dir(), *st["glb"].split("/")), "live/" + st["glb"])
            if st.get("geometry"):
                z.write(os.path.join(env.live_dir(), *st["geometry"].split("/")), "live/" + st["geometry"])
        z.writestr("live/views.json", json.dumps({"views": env.load_views(meta.get("project") or meta.get("name"))}, indent=1))
        z.writestr("live/settings.json", json.dumps({k: s.get(k) for k in SETTING_KEYS}, indent=1))
        z.writestr("live/share.json", json.dumps({"static": True, "ion_token": s.get("ion_token", "") if embed_token else "",
                                                  "google_key": s.get("google_key", "") if embed_token else ""}))
        z.writestr("README.txt", "EarthLink share - %s\n\nUpload this folder to any static web host (GitHub Pages, Netlify Drop, a "
                   "university web space) and open index.html there, or run  python3 -m http.server  inside it and visit "
                   "http://localhost:8000.\nOpening index.html straight from disk will not load the model (browser security).\n"
                   "%s\nMap data (c) Google, via Cesium.\n" % (meta.get("name", ""),
                   "This copy contains the sender's map token - in Cesium ion, restrict that token to this site's address."
                   if embed_token else "Visitors paste their own free Cesium ion token the first time."))
    return {"file": path}


def serve(viewer_dir, port):
    import threading
    from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
    live = env.live_dir()
    state = {"alive": True}

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):   # never depend on the process's working directory
            super().__init__(*a, directory=viewer_dir, **kw)

        def log_message(self, *a):
            pass

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def translate_path(self, path):
            p = path.split("?", 1)[0].split("#", 1)[0]
            if p.startswith("/live/"):
                root, rel = live, p[len("/live/"):]
            elif p.startswith("/viewer/"):
                root, rel = viewer_dir, p[len("/viewer/"):]
            else:
                return os.path.join(viewer_dir, "__nope__")
            full = os.path.normpath(os.path.join(root, *[x for x in rel.split("/") if x not in ("", ".", "..")]))
            if not full.startswith(os.path.normpath(root)):
                return os.path.join(viewer_dir, "__nope__")
            return os.path.join(full, "index.html") if os.path.isdir(full) else full

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _allowed(self, post=False):
            # only this machine's viewer page: right Host (blocks DNS rebinding) and, for changes,
            # a custom header that other websites cannot send without a CORS preflight we never answer
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                return False
            return not post or self.headers.get("X-EarthLink") == "1"

        def do_GET(self):
            if not self._allowed():
                return self.send_error(403)
            path = self.path.split("?")[0]
            if path == "/":
                query = self.path[1:] if self.path.startswith("/?") else ""   # keep options such as ?controls=mac
                self.send_response(302); self.send_header("Location", "/viewer/" + query); self.end_headers()
            elif path == "/api/ping":
                self._json({"earthlink": True, "pid": os.getpid(), "viewer": viewer_dir, "version": earthlink.__version__})
            elif path == "/api/config":
                s = env.load_settings()
                self._json({"ion_token": s.get("ion_token", ""), "google_key": s.get("google_key", "")})
            elif path == "/api/settings":
                self._json(_settings_out())
            elif path == "/api/meta":
                self._json(_read(os.path.join(live, "meta.json"), {}))
            elif path == "/api/pick":
                self._json(_read(env.live_file("pick_request.json"), {}))
            elif path == "/api/context":
                self._json(_context_status())
            elif path == "/api/sun":
                self._json(_read(env.live_file("sun.json"), {}))
            elif path == "/api/camera":
                self._json(_read(env.camera_path(), {}))
            elif path == "/api/views":
                self._json({"views": env.load_views(env.current_project())})
            elif path == "/events":
                self._events()
            else:
                super().do_GET()

        def do_POST(self):
            if not self._allowed(post=True):
                return self.send_error(403)
            n = int(self.headers.get("Content-Length", 0) or 0)
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "bad json"}, 400)
            path = self.path.split("?")[0]
            if path == "/api/settings":
                env.save_settings({k: v for k, v in data.items() if k in SETTING_KEYS})
                self._json(_settings_out())
            elif path == "/api/config":
                env.save_settings({k: (data.get(k) or "").strip() for k in ("ion_token", "google_key") if k in data})
                self._json({"ok": True})
            elif path == "/api/context":
                self._json(_context_start(data))
            elif path == "/api/views":
                name = env.current_project()
                if data.get("op") == "put" and isinstance(data.get("view"), dict) and data["view"].get("name"):
                    views = env.put_view(name, data["view"])
                elif data.get("op") == "delete":
                    views = [v for v in env.load_views(name) if v.get("name") != data.get("name")]
                    env.save_views(name, views)
                elif data.get("op") == "rename":
                    new = str(data.get("new") or "").strip()[:60]
                    views = env.load_views(name)
                    if not new or any(v.get("name") == new for v in views):
                        return self._json({"error": "pick a new, unused name"})
                    views = [dict(v, name=new) if v.get("name") == data.get("name") else v for v in views]
                    env.save_views(name, views)
                else:
                    return self._json({"error": "bad request"}, 400)
                self._json({"views": views})
            elif path == "/api/snapshot":
                self._json(_save_snapshot(data))
            elif path == "/api/open_snapshots":
                env.open_url(env.snapshot_dir())
                self._json({"ok": True})
            elif path == "/api/choose_folder":
                chosen = env.choose_folder(env.snapshot_dir(), "Default folder for EarthLink screenshots")
                if chosen:
                    env.save_settings({"snapshot_dir": chosen})
                self._json({"snapshot_dir": env.snapshot_dir(), "changed": bool(chosen), "available": True})
            elif path == "/api/sets":
                self._json(_sets_op(data))
            elif path == "/api/anchor":
                self._json(_anchor_request(data))
            elif path == "/api/sun":
                import datetime
                enabled = data.get("enabled", env.load_settings().get("sun_enabled", True))
                utc = data.get("utc")
                try:
                    if not isinstance(enabled, bool) or not isinstance(utc, str) or len(utc) != 20 or not utc.endswith("Z"):
                        raise ValueError()
                    datetime.datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ")
                    tz = data.get("tz")
                    if tz is not None and (isinstance(tz, bool) or not isinstance(tz, (int,float)) or not -840 <= tz <= 840):
                        raise ValueError()
                except (ValueError, TypeError):
                    return self._json({"error":"Invalid sun settings"}, 400)
                sj = {"utc": utc, "enabled": enabled, "project": env.current_project(), "source": "viewer", "t": time.time()}
                if isinstance(data.get("tz"), (int, float)):
                    sj["tz"] = int(data["tz"])
                env.write_json(env.live_file("sun.json"), sj)
                env.save_settings({"sun_enabled": enabled, "sun_utc": utc})
                self._json({"ok": True})
            elif path == "/api/export_share":
                self._json(_export_share(viewer_dir, bool(data.get("embed_token"))))
            elif path == "/api/shutdown":
                self._json({"ok": True})
                state["alive"] = False
                threading.Thread(target=httpd.shutdown, daemon=True).start()
            else:
                self._json({"error": "not found"}, 404)

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            meta, cam = os.path.join(live, "meta.json"), env.camera_path()
            last_m, last_c, last_v, first_v, beat = None, _mtime(cam), None, True, time.time()
            watch = {"sun": _mtime(env.live_file("sun.json")), "pick": "unset"}
            try:
                while state["alive"]:
                    m = _mtime(meta)
                    if m is not None and m != last_m:
                        last_m = m
                        self.wfile.write(("event: model\ndata: %s\n\n" % json.dumps(_read(meta, {}))).encode()); self.wfile.flush()
                    c = _mtime(cam)
                    if c is not None and c != last_c:
                        last_c = c
                        self.wfile.write(("event: camera\ndata: %s\n\n" % json.dumps(_read(cam, {}))).encode()); self.wfile.flush()
                    for key, fname in (("sun", "sun.json"), ("pick", "pick_request.json")):
                        t = _mtime(env.live_file(fname))
                        if t != watch.get(key):
                            if watch.get(key, "unset") != "unset":
                                self.wfile.write(("event: %s\ndata: %s\n\n" % (key, json.dumps(_read(env.live_file(fname), {})))).encode())
                                self.wfile.flush()
                            watch[key] = t
                    v = _mtime(env.views_path(env.current_project()))
                    if v != last_v:
                        if not first_v:
                            self.wfile.write(b"event: views\ndata: {}\n\n"); self.wfile.flush()
                        last_v, first_v = v, False
                    if time.time() - beat > 15:
                        self.wfile.write(b": keepalive\n\n"); self.wfile.flush()
                        beat = time.time()
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    httpd.daemon_threads = True
    print("EarthLink viewer on http://127.0.0.1:%d (pid %d)" % (port, os.getpid()), flush=True)
    try:
        httpd.serve_forever()
    finally:
        state["alive"] = False


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--viewer", required=True)
    ap.add_argument("--port", type=int, default=env.PORT)
    a = ap.parse_args()
    serve(a.viewer, a.port)
