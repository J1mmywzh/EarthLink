#!/usr/bin/env python3
"""Build the EarthLink Dev plugin: a second, separate Rhino plugin for trying changes before they are released.

  python3 tools/build_dev.py            # writes build_dev/EarthLinkDev.rhp (drag it into Rhino once to install)

Its commands are DevSendToEarth, DevEarthLinkViewer, DevEarthLinkSync, DevEarthLinkSettings and DevEarthLinkUpdate.
They are launchers: each one runs the code of a source checkout (~/EarthLinkDev, cloned on first use) through
tools/devloader.py, with its own port, data folder and file section, so the released EarthLink is untouched.
DevEarthLinkUpdate moves the checkout to a branch of the repository; the next Dev command uses the new code,
without restarting Rhino. The launchers themselves rarely change, so this plugin rarely needs rebuilding.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import devloader  # noqa: E402
from build import RHINOCODE  # noqa: E402

VERSION = "1.0.0"
REPO = "https://github.com/J1mmywzh/EarthLink.git"
FIRST_BRANCH = "main"       # what a new checkout starts on (it must contain tools/devloader.py)
COMMANDS = [   # (Dev command, released command it runs, id)
    ("DevSendToEarth", "SendToEarth", "a1e5c0d2-3b4f-4a6e-8c7d-1f2e3a4b5c61"),
    ("DevEarthLinkViewer", "EarthLinkViewer", "b2f6d1e3-4c5a-4b7f-9d8e-2a3f4b5c6d72"),
    ("DevEarthLinkSync", "EarthLinkSync", "c3a7e2f4-5d6b-4c8a-8e9f-3b4a5c6d7e83"),
    ("DevEarthLinkSettings", "EarthLinkSettings", "d4b8f3a5-6e7c-4d9b-9fa0-4c5b6d7e8f94"),
    ("DevEarthLinkUpdate", None, "e5c9a4b6-7f8d-4eac-8ab1-5d6c7e8f9a05"),
]

LAUNCHER = '''#! python3
"""%(title)s: %(what)s (EarthLink Dev: the code of the source checkout, beside the released EarthLink)."""
import os, subprocess
import Rhino
import scriptcontext as sc

COMMAND = %(command)r
REPO = %(repo)r
FIRST = %(first)r
SRC = os.environ.get("EARTHLINK_DEV_SRC") or os.path.join(os.path.expanduser("~"), "EarthLinkDev")


def git(*args, cwd=None):
    env = dict(os.environ, PATH=os.pathsep.join(["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", os.environ.get("PATH", "")]))
    r = subprocess.run(["git"] + list(args), cwd=cwd or SRC, env=env, capture_output=True, text=True, timeout=180)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-400:])
    return r.stdout.strip()


def branch():
    p = os.path.join(SRC, ".devbranch")
    return open(p).read().strip() if os.path.isfile(p) else FIRST


def checkout(name):
    git("fetch", "--quiet", "origin")
    git("checkout", "--quiet", "--force", "--detach", "origin/" + name)
    with open(os.path.join(SRC, ".devbranch"), "w") as fh:
        fh.write(name)
    ex = os.path.join(SRC, ".git", "info", "exclude")
    if ".devbranch" not in (open(ex).read() if os.path.isfile(ex) else ""):
        with open(ex, "a") as fh:
            fh.write("\\n.devbranch\\n")
    return git("log", "-1", "--format=%%h %%s")


def ensure():
    if os.path.isdir(os.path.join(SRC, ".git")):
        return True
    Rhino.RhinoApp.WriteLine("EarthLink Dev: getting the source into %%s ..." %% SRC)
    git("clone", "--quiet", REPO, SRC, cwd=os.path.dirname(SRC))
    Rhino.RhinoApp.WriteLine("EarthLink Dev: at " + checkout(FIRST))
    return True


def update():
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Branch to try (Enter = %%s)" %% branch())
    gs.SetDefaultString(branch())
    gs.AcceptNothing(True)
    res = gs.Get()
    if res not in (Rhino.Input.GetResult.String, Rhino.Input.GetResult.Nothing):
        return
    name = (gs.StringResult() or "").strip() if res == Rhino.Input.GetResult.String else ""
    Rhino.RhinoApp.WriteLine("EarthLink Dev: %%s is now at %%s. The next Dev command uses it." %% (name or branch(), checkout(name or branch())))


try:
    ensure()
    if COMMAND is None:
        update()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location("earthlink_devloader", os.path.join(SRC, "tools", "devloader.py"))
        loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loader)
        loader.run(COMMAND, globals().get("__rhino_doc__") or sc.doc, SRC)
except Exception as ex:
    Rhino.RhinoApp.WriteLine("EarthLink Dev: %%s" %% ex)
'''


def main():
    with open(os.path.join(ROOT, "EarthLink.rhproj"), encoding="utf-8") as fh:
        proj = json.load(fh)
    images = {c["title"]: c.get("image") for c in proj["codes"]}
    tmp = os.path.join(tempfile.gettempdir(), "EarthLinkDev_build")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "commands"))
    codes = []
    for title, command, cid in COMMANDS:
        what = "runs %s" % command if command else "moves the source checkout to a branch of the repository"
        with open(os.path.join(tmp, "commands", title + ".py"), "w", encoding="utf-8") as fh:
            fh.write(LAUNCHER % {"title": title, "what": what, "command": command, "repo": REPO, "first": FIRST_BRANCH})
        code = {"id": cid, "language": {"id": "*.*.python", "version": "3.*.*"}, "title": title, "uri": "commands/%s.py" % title}
        if images.get(command or "EarthLinkSettings"):
            code["image"] = images[command or "EarthLinkSettings"]
        codes.append(code)
    dev = dict(proj, id=devloader.DEV_PLUGIN_ID, codes=codes, libraries=[], resources=[])
    dev["identity"] = dict(proj["identity"], name="EarthLinkDev", version=VERSION,
                           description="EarthLink Dev: try EarthLink changes from a source checkout beside the released plugin. "
                                       "Commands start with Dev; nothing is shared with EarthLink but what Rhino itself holds.")
    with open(os.path.join(tmp, "EarthLinkDev.rhproj"), "w", encoding="utf-8") as fh:
        json.dump(dev, fh, indent=2)
    subprocess.check_call([RHINOCODE, "project", "build", os.path.join(tmp, "EarthLinkDev.rhproj"),
                           "--buildversion", VERSION, "--buildtarget", "8.*", "--buildpath", os.path.join(tmp, "build")])
    out = os.path.join(ROOT, "build_dev")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    rhps = [os.path.join(d, f) for d, _, fs in os.walk(os.path.join(tmp, "build")) for f in fs if f.endswith(".rhp")]
    if not rhps:
        sys.exit("no .rhp produced")
    shutil.copy2(rhps[0], os.path.join(out, "EarthLinkDev.rhp"))
    print("built", os.path.join(out, "EarthLinkDev.rhp"))


if __name__ == "__main__":
    main()
