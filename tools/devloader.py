"""EarthLink Dev: run EarthLink from a source checkout inside Rhino, beside the released plugin, without a build.

The EarthLink Dev plugin (tools/build_dev.py) only holds small launchers: DevSendToEarth, DevEarthLinkViewer,
DevEarthLinkSync, DevEarthLinkSettings and DevEarthLinkUpdate. Each one calls run() here, which

  1. copies the checkout's earthlink/, commands/ and shared/ into the dev data folder as the package
     `earthlink_dev` (both plugins share one Python inside Rhino: the same package name would mix their code),
  2. gives that copy its own everything: port 8766, data folder "EarthLink Dev" (settings, views, live files),
     its own section in the .3dm ("EarthLinkDev"), its own sync timer and its own viewer files,
  3. imports it and runs the command.

Nothing is copied again until the checkout changes; then the old dev sync and server are stopped and the new code
is loaded, so an update needs no restart of Rhino. The released plugin is never touched. What both share is what
Rhino itself holds: the EarthAnchorPoint, named views and the Sun.
"""
import os, re, sys, json, shutil, hashlib

PACKAGE = "earthlink_dev"
PORT = 8766
DATA_NAME = "EarthLink Dev"
SECTION = "EarthLinkDev"
DEV_PLUGIN_ID = "9d5e3b71-4c2a-4f8e-b6d0-7a1c3e5f2b94"      # = "id" of the EarthLink Dev plugin (tools/build_dev.py)
RELEASE_DATA = "EarthLink"

# Text changes to the copy. Each must match exactly once (counted per file), or loading stops with a clear message:
# a refactor that moves one of these must not leave the dev copy writing into the released plugin's data.
PATCHES = {
    "env.py": [
        ('PORT = int(os.environ.get("EARTHLINK_PORT", "8765"))', 'PORT = %d' % PORT),
        ('d = os.path.join(base, "EarthLink")', 'd = os.path.join(base, %r)' % DATA_NAME),
        ('PLUGIN_ID = "6b3c2a8e-0f5d-4d7e-9a61-2e4c8b1d7f30"', 'PLUGIN_ID = %r' % DEV_PLUGIN_ID),
    ],
    "core.py": [('SECTION = "EarthLink"', 'SECTION = %r' % SECTION)],
    "sync.py": [('_STICKY = "earthlink_sync_timer"', '_STICKY = "earthlink_dev_sync_timer"')],
}
IMPORTS = [
    (re.compile(r"\bfrom earthlink(\.| import)"), r"from %s\1" % PACKAGE),
    (re.compile(r"^(\s*)import earthlink\b(?! as)", re.M), r"\1import %s as earthlink" % PACKAGE),
]
STICKY = re.compile(r'"earthlink_(last_set|ep_opened)"')


def data_root(name=DATA_NAME):
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    else:
        base = os.path.expanduser("~/Library/Application Support")
    return os.path.join(base, name)


def source_signature(src):
    """Changes whenever a file the dev copy is made from changes."""
    h = hashlib.sha1()
    for sub in ("earthlink", "commands", "shared"):
        top = os.path.join(src, sub)
        for dirpath, dirs, files in os.walk(top):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for f in sorted(files):
                if f.endswith(".pyc"):
                    continue
                p = os.path.join(dirpath, f)
                st = os.stat(p)
                h.update(("%s|%d|%d\n" % (os.path.relpath(p, src), st.st_size, int(st.st_mtime_ns))).encode())
    return h.hexdigest()


def patch_text(name, text, in_package):
    """The dev copy of one .py file."""
    for old, new in PATCHES.get(name, []) if in_package else []:
        n = text.count(old)
        if n != 1:
            raise RuntimeError("EarthLink Dev: %s has %d copies of %r (expected 1); update tools/devloader.py" % (name, n, old))
        text = text.replace(old, new)
    for rx, rep in IMPORTS:
        text = rx.sub(rep, text)
    text = STICKY.sub(r'"earthlink_dev_\1"', text)
    if in_package and name == "__init__.py":
        text = re.sub(r'(__version__\s*=\s*")([^"]+)(")', r"\1\2-dev\3", text)
    return text


def stage(src, dst):
    """Copy the checkout into dst as the dev package. Returns dst."""
    tmp = dst + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    ign = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(os.path.join(src, "earthlink"), os.path.join(tmp, PACKAGE), ignore=ign)
    shutil.copytree(os.path.join(src, "commands"), os.path.join(tmp, "commands"), ignore=ign)
    shutil.copytree(os.path.join(src, "shared"), os.path.join(tmp, "shared"), ignore=ign)
    for folder, in_package in ((os.path.join(tmp, PACKAGE), True), (os.path.join(tmp, "commands"), False)):
        for f in os.listdir(folder):
            if f.endswith(".py"):
                p = os.path.join(folder, f)
                with open(p, encoding="utf-8") as fh:
                    text = fh.read()
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(patch_text(f, text, in_package))
    shutil.rmtree(dst, ignore_errors=True)
    os.replace(tmp, dst)
    return dst


def copy_map_keys(release_dir, dev_dir):
    """The dev viewer uses the map keys already entered in the released one (a local file copy, nothing is sent)."""
    rel = os.path.join(release_dir, "settings.json")
    dev = os.path.join(dev_dir, "settings.json")
    try:
        with open(rel) as fh:
            r = json.load(fh)
    except Exception:
        return False
    try:
        with open(dev) as fh:
            d = json.load(fh)
    except Exception:
        d = {}
    keys = {k: r.get(k) for k in ("ion_token", "google_key") if r.get(k) and not d.get(k)}
    if not keys:
        return False
    d.update(keys)
    os.makedirs(dev_dir, exist_ok=True)
    with open(dev, "w") as fh:
        json.dump(d, fh, indent=1)
    return True


def _purge():
    for name in [m for m in sys.modules if m == PACKAGE or m.startswith(PACKAGE + ".")]:
        del sys.modules[name]


def load(src):
    """Import the dev package from checkout `src`, copying it again first when it changed. Returns the package."""
    import scriptcontext as sc
    root = data_root()
    runtime = os.path.join(root, "runtime")
    sig = source_signature(src)
    state = sc.sticky.get("earthlink_dev_loader") or {}
    if state.get("sig") == sig and PACKAGE in sys.modules:
        return sys.modules[PACKAGE]
    old = sys.modules.get(PACKAGE)
    if old is not None:                                   # new code: stop what the old code started
        for mod, fn in (("sync", "stop"), ("server", "stop")):
            try:
                getattr(sys.modules.get(PACKAGE + "." + mod), fn)()
            except Exception:
                pass
    _purge()
    stage(src, runtime)
    if runtime not in sys.path:
        sys.path.insert(0, runtime)
    import importlib
    importlib.invalidate_caches()
    pkg = importlib.import_module(PACKAGE)
    for m in ("env", "core", "geometry", "views", "sync", "server", "context", "collada"):
        try:
            importlib.import_module(PACKAGE + "." + m)
        except ImportError:
            pass
    copy_map_keys(data_root(RELEASE_DATA), root)
    sc.sticky["earthlink_dev_loader"] = {"sig": sig, "src": src}
    return pkg


def describe(src):
    """'branch @ abc1234 subject' for the checkout, or ''."""
    import subprocess
    try:
        env = dict(os.environ, PATH=os.pathsep.join(["/opt/homebrew/bin", "/usr/local/bin", os.environ.get("PATH", "")]))
        out = subprocess.run(["git", "log", "-1", "--format=%h %s"], cwd=src, env=env, capture_output=True, text=True, timeout=10).stdout.strip()
        br = ""
        p = os.path.join(src, ".devbranch")
        if os.path.isfile(p):
            br = open(p).read().strip()
        return ("%s @ %s" % (br, out) if br else out)[:100]
    except Exception:
        return ""


def run(command, doc, src):
    """Run commands/<command>.py from the dev copy for `doc`."""
    import Rhino
    pkg = load(src)
    path = os.path.join(data_root(), "runtime", "commands", command + ".py")
    with open(path, encoding="utf-8") as fh:
        code = compile(fh.read(), path, "exec")
    Rhino.RhinoApp.WriteLine("EarthLink Dev %s (%s)" % (getattr(pkg, "__version__", "?"), describe(src)))
    g = {"__name__": "__main__", "__file__": path, "__rhino_doc__": doc}
    exec(code, g)
