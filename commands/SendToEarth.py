#! python3
"""SendToEarth: send selected geometry to the EarthLink viewer (and optionally Google Earth Pro).

Options
  Set=Main       which design set this geometry belongs to (Scheme A, Landscape, ...); each set can be
                 shown, hidden or compared in the viewer
  Live=Off|On    re-send this set automatically about a second after its objects change
  Viewer, EarthPro  where to show it

A file without a site location can be placed by clicking on the map (writes the EarthAnchorPoint).
"""
import Rhino
import scriptcontext as sc

from earthlink import env, core, server, sync


def _ask_set_name(current):
    gs = Rhino.Input.Custom.GetString()
    gs.SetCommandPrompt("Design set name")
    gs.SetDefaultString(current)
    gs.AcceptNothing(True)
    if gs.Get() == Rhino.Input.GetResult.String and gs.StringResult().strip():
        return gs.StringResult().strip()
    return current


def _open_viewer(doc, first_time_msg=None):
    st = server.start()
    if st == "busy":
        Rhino.RhinoApp.WriteLine("SendToEarth: port %d is used by another program - viewer not started." % env.PORT)
        return False
    sync.start(doc)
    if st == "started" or first_time_msg:
        env.open_url(server.url())
    return True


def run(doc):
    s = env.load_settings()
    sets = core.get_sets(doc)
    set_name = sc.sticky.get("earthlink_last_set") or (next(iter(sets)) if sets else core.DEFAULT_SET)

    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Select geometry to send to Earth")
    t_view = Rhino.Input.Custom.OptionToggle(bool(s["viewer"]), "Off", "On")
    t_ep = Rhino.Input.Custom.OptionToggle(bool(s["earthpro"]), "Off", "On")
    t_live = Rhino.Input.Custom.OptionToggle(bool(sets.get(set_name, {}).get("live")), "Off", "On")
    go.GroupSelect = True
    go.SubObjectSelect = False
    go.EnablePreSelect(True, True)
    while True:
        go.ClearCommandOptions()
        i_set = go.AddOption("Set", env.safe_name(set_name).replace(" ", "_"))
        go.AddOptionToggle("Live", t_live)
        go.AddOptionToggle("Viewer", t_view)
        go.AddOptionToggle("EarthPro", t_ep)
        res = go.GetMultiple(1, 0)
        if res == Rhino.Input.GetResult.Option:
            if go.OptionIndex() == i_set:
                set_name = _ask_set_name(set_name)
                t_live.CurrentValue = bool(core.get_sets(doc).get(set_name, {}).get("live"))
            go.EnablePreSelect(False, True)
            continue
        if res != Rhino.Input.GetResult.Object:
            return Rhino.Commands.Result.Cancel
        break
    to_viewer, to_ep, live = t_view.CurrentValue, t_ep.CurrentValue, t_live.CurrentValue
    env.save_settings({"viewer": to_viewer, "earthpro": to_ep})
    sc.sticky["earthlink_last_set"] = set_name
    if not (to_viewer or to_ep):
        Rhino.RhinoApp.WriteLine("SendToEarth: Viewer and EarthPro are both Off.")
        return Rhino.Commands.Result.Nothing
    if to_ep and env.earth_pro_path() is None:
        Rhino.RhinoApp.WriteLine("SendToEarth: Google Earth Pro is not installed; sending to the viewer only.")
        to_ep = False
        env.save_settings({"earthpro": False})

    ids = [go.Object(i).ObjectId for i in range(go.ObjectCount)]

    # ---- no site location yet: place it on the map
    if not core.anchor_ok(doc):
        gk = Rhino.Input.Custom.GetOption()
        gk.SetCommandPrompt("This file has no site location. Pick it on the map in the viewer?")
        gk.AddOption("PickOnMap")
        gk.AddOption("UseEarthAnchorPoint")
        if gk.Get() != Rhino.Input.GetResult.Option or gk.Option().EnglishName != "PickOnMap":
            Rhino.RhinoApp.WriteLine("SendToEarth: run EarthAnchorPoint to set the site location, then SendToEarth again.")
            return Rhino.Commands.Result.Cancel
        core.put_set(doc, set_name, ids, live=live, pending=True)
        env.write_json(env.live_file("pick_request.json"),
                       {"project": core.project_id(doc), "name": core.project_name(doc), "set": set_name})
        if _open_viewer(doc, first_time_msg=True):
            at_origin = doc.EarthAnchorPoint.ModelBasePoint.DistanceTo(Rhino.Geometry.Point3d.Origin) < 1e-9
            Rhino.RhinoApp.WriteLine("SendToEarth: in the viewer, find the site (search or lat, lon), click where the model "
                                     "should stand (%s goes there), then Apply. It is sent right after."
                                     % ("the bottom centre of what you selected" if at_origin else "the EarthAnchorPoint base point"))
        return Rhino.Commands.Result.Success

    # ---- normal send
    core.put_set(doc, set_name, ids, live=live, pending=False)
    try:
        meta, msgs, master = core.send_set(doc, set_name, to_earthpro=to_ep)
    except Exception as ex:
        Rhino.RhinoApp.WriteLine("SendToEarth: %s" % ex)
        return Rhino.Commands.Result.Failure
    sync.mark_sent(doc, set_name)
    if master and not sc.sticky.get("earthlink_ep_opened"):
        if env.open_in_earth_pro(master):
            sc.sticky["earthlink_ep_opened"] = True
            msgs.append("opened in Google Earth Pro")
    if to_viewer and _open_viewer(doc):
        msgs.append("viewer updated")
    Rhino.RhinoApp.WriteLine("SendToEarth: '%s' v%d, %d object(s)%s: %s." % (
        set_name, meta["version"], len(ids), ", live" if live else "", "; ".join(msgs)))
    return Rhino.Commands.Result.Success


run(globals().get("__rhino_doc__") or sc.doc)
