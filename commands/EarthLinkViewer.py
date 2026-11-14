#! python3
"""EarthLinkViewer: open the viewer (starts the local server and the Rhino sync if needed)."""
import Rhino
import scriptcontext as sc
from earthlink import env, server, sync, core

doc = globals().get("__rhino_doc__") or sc.doc
st = server.start()
if st == "busy":
    Rhino.RhinoApp.WriteLine("EarthLinkViewer: port %d is used by another program." % env.PORT)
else:
    sync.start(doc)
    # Another file (or nothing) is in the viewer: bring this file back as it was left. Its sets are exported again;
    # its site, placements, views, display settings, sun and last camera come from the file (core.restore_state).
    try:
        if core.anchor_ok(doc) and core.get_sets(doc) and env.current_project() != core.project_id(doc):
            sync.send_sets(doc, reason="this file's sets, as it was left")
    except Exception as ex:
        Rhino.RhinoApp.WriteLine("EarthLinkViewer: could not send this file's sets: %s" % ex)
    env.open_url(server.url())
    Rhino.RhinoApp.WriteLine("EarthLinkViewer: %s" % server.url())
