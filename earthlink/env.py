"""Paths, settings and OS helpers (macOS + Windows)."""
import os, sys, json, subprocess, tempfile
from contextlib import contextmanager

PLUGIN_ID = "6b3c2a8e-0f5d-4d7e-9a61-2e4c8b1d7f30"   # = "id" in EarthLink.rhproj (never change it)
PORT = int(os.environ.get("EARTHLINK_PORT", "8765"))
IS_WIN = sys.platform.startswith("win")

DEFAULTS = {
    # map access (each user enters their own)
    "ion_token": "", "google_key": "",
    # command defaults
    "viewer": True, "earthpro": False,
    # viewer placement settings (also edited from the viewer page)
    "nudge": 0.0, "geoid_offset": -33.5, "ground_h": None,
    "clip": False, "clip_sets": [], "clip_margin": 0.0, "shadows": True, "sun_enabled": True, "sun_utc": None,
    # where viewer screenshots go ("" = Pictures/EarthLink); save_mode "folder" or "ask"
    "snapshot_dir": "", "save_mode": "folder",
    # Rhino sync: two-way named views, the viewer following Rhino's active viewport, Rhino Sun <-> viewer sun
    "sync_views": True, "link_viewport": False, "sync_sun": True,
    # viewer display
    "style": "materials", "ghost": 0.45, "hidden_sets": [], "set_styles": {},
    # the Rhino model's lights are shown in the viewer
    "lights": True,
    # the last camera of the file being shown: {"project": id, "cam": camera}; kept in the .3dm by core.save_state
    "view": None,
}


def choose_folder(start, title="Choose a folder"):
    """Native folder picker run as its own small process (works from the server, Mac + Windows).
    Returns the chosen path, or None if cancelled / unavailable."""
    try:
        if IS_WIN:
            ps = ("Add-Type -AssemblyName System.Windows.Forms;"
                  "$d=New-Object System.Windows.Forms.FolderBrowserDialog;$d.Description='%s';$d.SelectedPath='%s';"
                  "if($d.ShowDialog() -eq 'OK'){Write-Output $d.SelectedPath}") % (title.replace("'", ""), (start or "").replace("'", ""))
            r = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps], capture_output=True, text=True, timeout=600)
        else:
            script = 'POSIX path of (choose folder with prompt "%s"%s)' % (
                title.replace('"', ""), (' default location POSIX file "%s"' % start.replace('"', "")) if start and os.path.isdir(start) else "")
            r = subprocess.run(["osascript", "-e", 'tell application "System Events" to activate', "-e", script],
                               capture_output=True, text=True, timeout=600)
        out = r.stdout.strip()
        return out.rstrip("/\\") or None if r.returncode == 0 and out else None
    except Exception:
        return None


def python_exe():
    """A CPython 3 to run the viewer server: Rhino 8's bundled one (Mac + Windows), else the system's."""
    home = os.path.expanduser("~")
    for c in (os.path.join(home, ".rhinocode", "py39-rh8", "python.exe"),
              os.path.join(home, ".rhinocode", "py39-rh8", "python3.9"),
              os.path.join(home, ".rhinocode", "py39-rh8", "bin", "python3.9"),
              "/usr/bin/python3"):
        if os.path.isfile(c):
            return c
    import shutil
    return shutil.which("python3") or shutil.which("python")


def camera_path():
    return live_file("camera.json")


def read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


def write_json(path, data):
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + ".", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=1, allow_nan=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def snapshot_dir():
    d = load_settings().get("snapshot_dir") or os.path.join(os.path.expanduser("~"), "Pictures", "EarthLink")
    os.makedirs(d, exist_ok=True)
    return d


def safe_name(s, fallback="untitled"):
    s = "".join(c if (c.isalnum() or c in "-_ .") else "_" for c in str(s)).strip(" ._")
    return s[:60] or fallback


def views_path(project):
    d = os.path.join(data_dir(), "views")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, safe_name(project) + ".json")


def load_views(model_name):
    try:
        with open(views_path(model_name)) as fh:
            return json.load(fh).get("views", [])
    except Exception:
        return []


def save_views(model_name, views):
    p = views_path(model_name)
    write_json(p, {"model": model_name, "views": views})


def put_view(model_name, view):
    views = [v for v in load_views(model_name) if v.get("name") != view.get("name")]
    views.append(view)
    save_views(model_name, views)
    return views


def current_meta():
    try:
        with open(os.path.join(live_dir(), "meta.json")) as fh:
            return json.load(fh)
    except Exception:
        return {}


def current_project():
    """Key for the project the viewer is showing (stable id stored in the .3dm)."""
    m = current_meta()
    return m.get("project") or m.get("name") or "Untitled"


def live_file(name):
    """Small exchange files between Rhino and the viewer server, e.g. camera.json, sun.json."""
    return os.path.join(live_dir(), name)


def data_dir():
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    else:
        base = os.path.expanduser("~/Library/Application Support")
    d = os.path.join(base, "EarthLink")
    os.makedirs(os.path.join(d, "live"), exist_ok=True)
    return d


def live_dir():
    return os.path.join(data_dir(), "live")


def viewer_dir():
    """Folder holding the viewer's index.html: the installed plugin's shared/ folder,
    or the source tree when the commands are run straight from the Script Editor."""
    roots = []
    try:
        import Rhino, System
        p = Rhino.PlugIns.PlugIn.PathFromId(System.Guid(PLUGIN_ID))
        if p:
            roots.append(os.path.join(os.path.dirname(str(p)), "shared"))
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(os.path.normpath(os.path.join(here, "..", "shared")))      # source tree
    for r in roots:
        for sub in ("viewer", "", os.path.join("shared", "viewer")):
            d = os.path.join(r, sub)
            if os.path.isfile(os.path.join(d, "index.html")):
                return d
        for dirpath, _, files in os.walk(r) if os.path.isdir(r) else []:
            if "index.html" in files:
                return dirpath
    raise RuntimeError("EarthLink: viewer files not found")


def _settings_path():
    return os.path.join(data_dir(), "settings.json")


def load_settings():
    s = dict(DEFAULTS)
    try:
        with open(_settings_path()) as fh:
            raw = json.load(fh)
            s.update(raw)
            if "sun_enabled" not in raw and "shadows" in raw:
                s["sun_enabled"] = bool(raw["shadows"])
    except Exception:
        pass
    return s


@contextmanager
def _settings_lock():
    # Coordinate Rhino and the separate server without creating threads in Rhino.
    with open(os.path.join(data_dir(), ".settings.lock"), "a+b") as lock:
        if IS_WIN:
            import msvcrt
            # Windows locks a byte range, and may lock one beyond the end of the file: the file stays empty.
            # (Writing a first byte here raced: a second writer hit the byte the first had just locked.)
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if IS_WIN:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def save_settings(patch):
    with _settings_lock():
        s = load_settings()
        s.update({k: v for k, v in patch.items() if k in DEFAULTS})
        write_json(_settings_path(), s)
        return s


def open_url(url):
    if IS_WIN:
        os.startfile(url)
    else:
        subprocess.Popen(["open", url])


def earth_pro_path():
    if IS_WIN:
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
            exe = os.path.join(base, "Google", "Google Earth Pro", "client", "googleearth.exe")
            if os.path.exists(exe):
                return exe
        return None
    app = "/Applications/Google Earth Pro.app"
    return app if os.path.exists(app) else None


def open_in_earth_pro(kml):
    exe = earth_pro_path()
    if exe is None:
        return False
    if IS_WIN:
        subprocess.Popen([exe, kml])
    else:
        subprocess.Popen(["open", "-a", exe, kml])
    return True
