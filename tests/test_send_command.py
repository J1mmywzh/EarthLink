"""SendToEarth's first send, with Rhino stubbed: a file without a site asks for a base point (as for a block),
exports the preview around it and asks the viewer for the spot. Catches slips that only show inside Rhino."""
import importlib.util, os, sys, types
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class P3(object):
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.X, self.Y, self.Z = x, y, z

    def DistanceTo(self, o):
        return ((self.X - o.X) ** 2 + (self.Y - o.Y) ** 2 + (self.Z - o.Z) ** 2) ** 0.5


P3.Origin = P3()


def load(point_result, picked=None, base_in_anchor=None, located=False):
    """Run commands/SendToEarth.py once. Returns (result, core, env, written lines)."""
    R = types.ModuleType("Rhino")
    GR = types.SimpleNamespace(Option="Option", Object="Object", Point="Point", Nothing="Nothing", Cancel="Cancel", String="String")
    lines = []

    class GetObject(object):
        GroupSelect = SubObjectSelect = False
        ObjectCount = 2

        def __getattr__(self, n):
            return lambda *a, **k: 0

        def GetMultiple(self, a, b):
            return GR.Object

        def Object(self, i):
            return types.SimpleNamespace(ObjectId="id%d" % i)

    class GetPoint(object):
        def __init__(self):
            self.prompt, self.nothing = None, False

        def SetCommandPrompt(self, t):
            self.prompt = t

        def AcceptNothing(self, v):
            self.nothing = v

        def Get(self):
            lines.append("PROMPT " + self.prompt)
            assert self.nothing, "Enter must be accepted for the default"
            return point_result

        def Point(self):
            return picked

    class Toggle(object):
        def __init__(self, v, a, b):
            self.CurrentValue = v

    R.Input = types.SimpleNamespace(GetResult=GR, Custom=types.SimpleNamespace(GetObject=GetObject, GetPoint=GetPoint, OptionToggle=Toggle, GetString=mock.MagicMock(), GetOption=mock.MagicMock()))
    R.Commands = types.SimpleNamespace(Result=types.SimpleNamespace(Success="Success", Cancel="Cancel", Nothing="Nothing", Failure="Failure"))
    R.RhinoApp = types.SimpleNamespace(WriteLine=lines.append)
    R.Geometry = types.SimpleNamespace(Point3d=P3)
    sc = types.ModuleType("scriptcontext"); sc.sticky = {}; sc.doc = None
    env = mock.MagicMock(); env.load_settings.return_value = {"viewer": True, "earthpro": False}; env.safe_name.side_effect = lambda s: s
    env.live_file.side_effect = lambda n: "/live/" + n
    core = mock.MagicMock(); core.get_sets.return_value = {}; core.DEFAULT_SET = "Main"; core.anchor_ok.return_value = located
    core.send_set.return_value = ({"version": 3}, ["sent"], None)
    core.base_point_for.return_value = P3(10, 5, 0); core.project_id.return_value = "pid"; core.project_name.return_value = "Tower"
    core.export_preview.return_value = {"glb": "preview/model_1.glb"}
    server = mock.MagicMock(); server.start.return_value = "running"; server.viewer_open.return_value = True
    sync = mock.MagicMock()
    pkg = types.ModuleType("earthlink"); pkg.env, pkg.core, pkg.server, pkg.sync = env, core, server, sync
    doc = types.SimpleNamespace(EarthAnchorPoint=types.SimpleNamespace(ModelBasePoint=base_in_anchor or P3()))
    mods = {"Rhino": R, "scriptcontext": sc, "earthlink": pkg, "earthlink.env": env, "earthlink.core": core, "earthlink.server": server, "earthlink.sync": sync}
    with mock.patch.dict(sys.modules, mods):
        spec = importlib.util.spec_from_file_location("SendToEarth_under_test", os.path.join(ROOT, "commands", "SendToEarth.py"))
        m = importlib.util.module_from_spec(spec)
        m.__rhino_doc__ = doc
        src = open(os.path.join(ROOT, "commands", "SendToEarth.py")).read().replace('run(globals().get("__rhino_doc__") or sc.doc)', "RESULT = run(__rhino_doc__)")
        exec(compile(src, "SendToEarth.py", "exec"), m.__dict__)
    return m.RESULT, core, env, lines


def test_first_send_asks_for_a_base_point_and_sends_it_with_the_request():
    res, core, env, lines = load("Point", picked=P3(1, 2, 3))
    assert res == "Success" and any(l.startswith("PROMPT Base point") for l in lines)
    base = core.set_pending_base.call_args[0][1]; assert (base.X, base.Y, base.Z) == (1, 2, 3)
    assert core.export_preview.call_args[0][2] is base                       # the preview stands on that point
    path, req = env.write_json.call_args[0]
    assert path == "/live/pick_request.json" and req["base"] == [1, 2, 3] and req["preview"] == {"glb": "preview/model_1.glb"} and req["set"] == "Main"
    assert core.put_set.call_args[1]["pending"] is True and not core.send_set.called   # sent only after the spot is applied
    assert env.open_url.called                                               # the viewer opens for the placement


def test_enter_takes_the_bottom_centre_and_escape_cancels():
    res, core, env, lines = load("Nothing")
    base = core.set_pending_base.call_args[0][1]; assert res == "Success" and (base.X, base.Y, base.Z) == (10, 5, 0)
    res, core, env, lines = load("Nothing", base_in_anchor=P3(7, 7, 7))      # EarthAnchorPoint already names a base point
    base = core.set_pending_base.call_args[0][1]; assert (base.X, base.Y, base.Z) == (7, 7, 7)
    res, core, env, lines = load("Cancel")
    assert res == "Cancel" and not core.set_pending_base.called and not env.write_json.called and not core.put_set.called


def test_a_file_with_a_site_is_sent_at_once_without_any_question():
    res, core, env, lines = load("Cancel", located=True)                     # any question would cancel it
    assert res == "Success" and core.send_set.called and not core.set_pending_base.called
    assert not any(l.startswith("PROMPT") for l in lines), lines
    assert core.put_set.call_args[1]["pending"] is False
