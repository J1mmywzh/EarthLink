#! python3
"""EarthLinkSettings: map token/key, Earth Pro default, design sets, screenshot folder, server control."""
import Rhino
import scriptcontext as sc
from earthlink import env, server, core

doc = globals().get("__rhino_doc__") or sc.doc


def mask(s):
    return (s[:4] + "…" + s[-4:]) if s and len(s) > 10 else ("set" if s else "not set")


while True:
    s = env.load_settings()
    Rhino.RhinoApp.WriteLine("EarthLink: Cesium ion token %s | Google key %s | Earth Pro %s | screenshots: %s | data: %s"
                             % (mask(s["ion_token"]), mask(s["google_key"]), "on" if s["earthpro"] else "off",
                                env.snapshot_dir(), env.data_dir()))
    go = Rhino.Input.Custom.GetOption()
    go.SetCommandPrompt("EarthLink settings")
    i_map = go.AddOption("ConnectMap")
    i_tok = go.AddOption("CesiumToken")
    i_key = go.AddOption("GoogleKey")
    t_ep = Rhino.Input.Custom.OptionToggle(bool(s["earthpro"]), "Off", "On")
    i_ep = go.AddOptionToggle("EarthProByDefault", t_ep)
    i_ren = go.AddOption("RenameSet")
    i_rm = go.AddOption("RemoveSet")
    i_snap = go.AddOption("ScreenshotFolder")
    i_data = go.AddOption("OpenDataFolder")
    i_stop = go.AddOption("StopViewerServer")
    go.AcceptNothing(True)
    r = go.Get()
    if r != Rhino.Input.GetResult.Option:
        break
    idx = go.OptionIndex()
    if idx == i_map:
        # The viewer's own dialog: links to Cesium ion's sign-up and token pages, and a field that checks the token.
        if server.start() == "busy":
            Rhino.RhinoApp.WriteLine("EarthLink: port %d is used by another program." % env.PORT)
        else:
            env.open_url(server.url() + "?connect=1")
            Rhino.RhinoApp.WriteLine("EarthLink: the viewer shows how to get a free Cesium ion token and checks it.")
        break
    elif idx in (i_tok, i_key):
        key = "ion_token" if idx == i_tok else "google_key"
        gs = Rhino.Input.Custom.GetString()
        gs.SetCommandPrompt("Paste the %s (Enter to keep, '-' to clear)" % ("Cesium ion token" if key == "ion_token" else "Google Maps Platform key"))
        gs.AcceptNothing(True)
        if gs.Get() == Rhino.Input.GetResult.String:
            v = gs.StringResult().strip()
            env.save_settings({key: "" if v == "-" else v})
            Rhino.RhinoApp.WriteLine("Saved. Reload the viewer page to use it.")
    elif idx == i_ep:
        env.save_settings({"earthpro": t_ep.CurrentValue})
    elif idx == i_snap:
        folder = None
        try:
            import Eto.Forms as ef
            d = ef.SelectFolderDialog()
            d.Title = "Folder for EarthLink screenshots"
            d.Directory = env.snapshot_dir()
            if d.ShowDialog(Rhino.UI.RhinoEtoApp.MainWindow) == ef.DialogResult.Ok:
                folder = d.Directory
        except Exception:
            gs = Rhino.Input.Custom.GetString()
            gs.SetCommandPrompt("Screenshot folder path")
            gs.SetDefaultString(env.snapshot_dir())
            if gs.Get() == Rhino.Input.GetResult.String:
                folder = gs.StringResult().strip()
        if folder:
            env.save_settings({"snapshot_dir": folder})
    elif idx == i_ren:
        names = list(core.get_sets(doc))
        if not names:
            Rhino.RhinoApp.WriteLine("No design sets in this file.")
            continue
        gl = Rhino.Input.Custom.GetOption()
        gl.SetCommandPrompt("Rename which set")
        gl.AddOptionList("Set", [env.safe_name(n).replace(" ", "_") for n in names], 0)
        if gl.Get() == Rhino.Input.GetResult.Option:
            old = names[gl.Option().CurrentListOptionIndex]
            gs = Rhino.Input.Custom.GetString()
            gs.SetCommandPrompt("New name for '%s'" % old)
            if gs.Get() == Rhino.Input.GetResult.String and gs.StringResult().strip():
                new = gs.StringResult().strip()[:60]
                if core.rename_set(doc, old, new):
                    core.rename_set_in_viewer(old, new)
                    Rhino.RhinoApp.WriteLine("Renamed '%s' to '%s' (Rhino and viewer)." % (old, new))
                else:
                    Rhino.RhinoApp.WriteLine("That name is already used.")
    elif idx == i_rm:
        names = list(core.get_sets(doc))
        if not names:
            Rhino.RhinoApp.WriteLine("No design sets in this file.")
            continue
        gl = Rhino.Input.Custom.GetOption()
        gl.SetCommandPrompt("Remove which set from EarthLink (geometry is not touched)")
        safe = [env.safe_name(n).replace(" ", "_") for n in names]
        gl.AddOptionList("Set", safe, 0)
        if gl.Get() == Rhino.Input.GetResult.Option:
            name = names[gl.Option().CurrentListOptionIndex]
            core.drop_set(doc, name)
            core.remove_set_from_viewer(name)
            Rhino.RhinoApp.WriteLine("Removed set '%s' from EarthLink." % name)
    elif idx == i_data:
        env.open_url(env.data_dir())
    elif idx == i_stop:
        Rhino.RhinoApp.WriteLine("Viewer server stopped." if server.stop() else "Viewer server was not running.")
