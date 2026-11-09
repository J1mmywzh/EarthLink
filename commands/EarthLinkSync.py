#! python3
"""EarthLinkSync: Enscape-style link between Rhino and the EarthLink viewer.

  NamedViews      named views sync both ways (save, update, delete in either app)
  FollowViewport  the viewer follows Rhino's active viewport live
  Sun             the viewer's date/time and Rhino's Sun stay the same (Sun location/north from the EarthAnchorPoint)
"""
import Rhino
import scriptcontext as sc

from earthlink import env, sync, server

doc = globals().get("__rhino_doc__") or sc.doc
s = env.load_settings()
go = Rhino.Input.Custom.GetOption()
go.SetCommandPrompt("EarthLink sync (Enter to apply)")
t_nv = Rhino.Input.Custom.OptionToggle(bool(s.get("sync_views", True)), "Off", "On")
t_fv = Rhino.Input.Custom.OptionToggle(bool(s.get("link_viewport", False)), "Off", "On")
t_sun = Rhino.Input.Custom.OptionToggle(bool(s.get("sync_sun", True)), "Off", "On")
go.AddOptionToggle("NamedViews", t_nv)
go.AddOptionToggle("FollowViewport", t_fv)
go.AddOptionToggle("Sun", t_sun)
go.AcceptNothing(True)
while go.Get() == Rhino.Input.GetResult.Option:
    pass
env.save_settings({"sync_views": t_nv.CurrentValue, "link_viewport": t_fv.CurrentValue, "sync_sun": t_sun.CurrentValue})
if server.start() != "busy":
    sync.start(doc)          # also keeps Live sets and site-location changes flowing
    if t_fv.CurrentValue:
        sync.push_camera(force=True)
on = lambda v: "on" if v else "off"
Rhino.RhinoApp.WriteLine("EarthLinkSync: named views %s, follow viewport %s, sun %s." %
                         (on(t_nv.CurrentValue), on(t_fv.CurrentValue), on(t_sun.CurrentValue)))
