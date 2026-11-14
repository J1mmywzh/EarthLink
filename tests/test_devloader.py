"""EarthLink Dev: the dev copy of the source keeps to its own port, data folder, file section and timer, and its
imports never reach the released `earthlink` package (both run in Rhino's one Python)."""
import os, re, subprocess, sys, json, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import devloader  # noqa: E402


def staged(tmp_path):
    return devloader.stage(ROOT, str(tmp_path / "runtime"))


def test_the_copy_is_its_own_plugin(tmp_path):
    rt = staged(tmp_path)
    pkg = os.path.join(rt, devloader.PACKAGE)
    env = open(os.path.join(pkg, "env.py")).read(); core = open(os.path.join(pkg, "core.py")).read(); sync = open(os.path.join(pkg, "sync.py")).read()
    assert "PORT = 8766" in env and "'EarthLink Dev'" in env and devloader.DEV_PLUGIN_ID in env and "6b3c2a8e" not in env
    assert "SECTION = 'EarthLinkDev'" in core and '_STICKY = "earthlink_dev_sync_timer"' in sync
    assert '-dev"' in open(os.path.join(pkg, "__init__.py")).read()
    for folder in (pkg, os.path.join(rt, "commands")):
        for f in os.listdir(folder):
            if f.endswith(".py"):
                t = open(os.path.join(folder, f)).read()
                compile(t, f, "exec")
                assert not re.search(r"\bfrom earthlink(\.| import)", t), f
                assert not re.search(r"^\s*import earthlink\b(?! as)", t, re.M), f
                assert '"earthlink_last_set"' not in t and '"earthlink_ep_opened"' not in t, f
    assert os.path.isfile(os.path.join(rt, "shared", "viewer", "index.html"))


def test_env_of_the_copy(tmp_path):
    rt = staged(tmp_path)
    out = subprocess.run([sys.executable, "-c", "import json; from earthlink_dev import env; print(json.dumps([env.PORT, env.data_dir(), env.viewer_dir()]))"],
                         cwd=rt, env=dict(os.environ, HOME=str(tmp_path), PYTHONPATH=rt), capture_output=True, text=True)
    port, data, viewer = json.loads(out.stdout)
    assert port == 8766 and data.endswith("EarthLink Dev") and str(tmp_path) in data
    assert viewer == os.path.join(rt, "shared", "viewer")


def test_the_dev_server_runs_from_the_copy_with_its_own_data(tmp_path):
    rt = staged(tmp_path)
    port = 18766
    p = subprocess.Popen([sys.executable, os.path.join(rt, devloader.PACKAGE, "server.py"), "--viewer", os.path.join(rt, "shared", "viewer"), "--port", str(port)],
                         env=dict(os.environ, HOME=str(tmp_path)), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        info = None
        for _ in range(60):
            try:
                info = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % port, timeout=1).read()); break
            except Exception:
                time.sleep(0.1)
        assert info and info["viewer"] == os.path.join(rt, "shared", "viewer") and info["version"].endswith("-dev"), info
        assert os.path.isdir(os.path.join(str(tmp_path), "Library", "Application Support", "EarthLink Dev")) or sys.platform.startswith("win")
    finally:
        p.terminate(); p.wait(5)


def test_a_missing_patch_stops_loading():
    try:
        devloader.patch_text("core.py", "SECTION = 'Renamed'\n", True)
    except RuntimeError as e:
        assert "update tools/devloader.py" in str(e)
    else:
        raise AssertionError("a moved constant must stop the dev copy from loading")


def test_map_keys_are_copied_once_and_never_overwritten(tmp_path):
    rel, dev = tmp_path / "rel", tmp_path / "dev"; rel.mkdir()
    (rel / "settings.json").write_text(json.dumps({"ion_token": "T", "google_key": "", "nudge": 3}))
    assert devloader.copy_map_keys(str(rel), str(dev)) is True
    assert json.loads((dev / "settings.json").read_text()) == {"ion_token": "T"}
    (dev / "settings.json").write_text(json.dumps({"ion_token": "mine"}))
    assert devloader.copy_map_keys(str(rel), str(dev)) is False and json.loads((dev / "settings.json").read_text())["ion_token"] == "mine"


def test_the_launchers_compile():
    import build_dev
    for title, command, _ in build_dev.COMMANDS:
        compile(build_dev.LAUNCHER % {"title": title, "what": "x", "command": command, "repo": build_dev.REPO, "first": build_dev.FIRST_BRANCH}, title, "exec")
    assert len({c[2] for c in build_dev.COMMANDS}) == len(build_dev.COMMANDS)
    assert all(t.startswith("Dev") for t, _, _ in build_dev.COMMANDS)
