"""The viewer server runs without Rhino, so it is tested end to end here."""
import json, os, socket, subprocess, sys, time, urllib.request, urllib.error, zipfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tests.fixtures import make_live  # noqa: E402


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


@pytest.fixture(scope="module")
def srv(tmp_path_factory):
    home = str(tmp_path_factory.mktemp("home"))
    live = make_live(home)
    port = _free_port()
    env = dict(os.environ, HOME=home, USERPROFILE=home, APPDATA=os.path.join(home, "AppData", "Roaming"), EARTHLINK_PORT=str(port))
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "earthlink", "server.py"), "--viewer", os.path.join(ROOT, "shared", "viewer"),
                          "--port", str(port)], env=env)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close(); break
        except OSError:
            time.sleep(0.1)
    yield {"base": "http://127.0.0.1:%d" % port, "live": live, "home": home}
    p.terminate()


def call(srv, path, body=None, headers=None):
    h = {"Content-Type": "application/json"}
    if body is not None:
        h["X-EarthLink"] = "1"
    h.update(headers or {})
    req = urllib.request.Request(srv["base"] + path, data=None if body is None else json.dumps(body).encode(), headers=h,
                                 method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read()) if r.headers.get("Content-Type") == "application/json" else r.read()


def test_ping_and_viewer(srv):
    assert call(srv, "/api/ping")["earthlink"]
    assert b"EarthLink" in call(srv, "/viewer/")
    assert call(srv, "/live/set_Main/v00001/model.glb")[:4] == b"glTF"


def test_rejects_other_websites(srv):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(urllib.request.Request(srv["base"] + "/api/settings", data=b"{}", method="POST"), timeout=5)
    assert e.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as e:
        call(srv, "/api/config", headers={"Host": "evil.example"})
    assert e.value.code == 403


def test_settings_and_views(srv):
    assert call(srv, "/api/settings", {"nudge": 1.5, "not_a_setting": 1})["nudge"] == 1.5
    v = {"name": "Corner", "projection": "two_point", "pos": [1, 2, 3], "dir": [0, 1, 0], "up": [0, 0, 1], "vfov": 0.7, "shift": 0.2}
    assert [x["name"] for x in call(srv, "/api/views", {"op": "put", "view": v})["views"]] == ["Corner"]
    assert call(srv, "/api/views")["views"][0]["shift"] == 0.2
    assert call(srv, "/api/views", {"op": "delete", "name": "Corner"})["views"] == []


def test_set_delete_tells_rhino(srv):
    assert call(srv, "/api/sets", {"op": "delete", "name": "Scheme B"})["ok"]
    assert "Scheme B" not in call(srv, "/api/meta")["sets"]
    d = json.load(open(os.path.join(srv["live"], "deleted_sets.json")))
    assert d == {"project": "p-test", "names": ["Scheme B"]}


def test_anchor_and_sun_requests(srv):
    assert call(srv, "/api/anchor", {"lat": 42.44, "lon": -76.51, "ground_h": 120.5, "rotate": 10})["project"] == "p-test"
    r = json.load(open(os.path.join(srv["live"], "anchor_request.json")))
    assert (r["project"], r["lat"], r["rotate"]) == ("p-test", 42.44, 10.0)
    call(srv, "/api/sun", {"utc": "2026-06-21T16:00:00Z"})
    s = call(srv, "/api/sun")
    assert (s["utc"], s["source"]) == ("2026-06-21T16:00:00Z", "viewer")


def test_snapshot_and_share(srv):
    png = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    f = call(srv, "/api/snapshot", {"view": "A/B", "pass": "full", "width": 1, "height": 1, "png": png, "camera": {"model": "TestModel"}})["file"]
    assert os.path.exists(f) and "/" not in os.path.basename(f).replace(".png", "")
    z = call(srv, "/api/export_share", {"embed_token": False})["file"]
    names = zipfile.ZipFile(z).namelist()
    assert {"index.html", "live/meta.json", "live/views.json", "live/share.json", "live/set_Main/v00001/model.glb"} <= set(names)


def _requests(srv):
    d = os.path.join(srv["live"], "requests")
    return [json.load(open(os.path.join(d, f))) for f in sorted(os.listdir(d))] if os.path.isdir(d) else []


def test_rename_and_move_set_are_queued_for_rhino(srv):
    call(srv, "/api/settings", {"hidden_sets": ["Main"], "set_styles": {"Main": "clay"}})
    assert call(srv, "/api/sets", {"op": "rename", "name": "Main", "new": "Tower"})["ok"]
    meta = call(srv, "/api/meta")
    assert "Tower" in meta["sets"] and "Main" not in meta["sets"]
    s = call(srv, "/api/settings")
    assert s["hidden_sets"] == ["Tower"] and s["set_styles"] == {"Tower": "clay"}
    assert call(srv, "/api/sets", {"op": "rename", "name": "Tower", "new": "Tower"}).get("error")
    assert call(srv, "/api/sets", {"op": "move", "name": "Tower", "dx": 2.5, "dy": -1, "rot": 15, "pivot": [15, 10, 0]})["ok"]
    reqs = _requests(srv)
    assert [r["type"] for r in reqs][-2:] == ["rename_set", "move_set"]
    assert (reqs[-1]["dx"], reqs[-1]["rot"], reqs[-1]["pivot"]) == (2.5, 15.0, [15.0, 10.0, 0.0])
    assert all(r["project"] == "p-test" for r in reqs)


def test_rename_view(srv):
    v = {"name": "North", "pos": [0, 0, 1], "dir": [0, 1, 0], "up": [0, 0, 1], "vfov": 0.7}
    call(srv, "/api/views", {"op": "put", "view": v})
    assert [x["name"] for x in call(srv, "/api/views", {"op": "rename", "name": "North", "new": "North (dusk)"})["views"]] == ["North (dusk)"]
