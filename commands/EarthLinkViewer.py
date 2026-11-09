#! python3
"""EarthLinkViewer: open the viewer (starts the local server and the Rhino sync if needed)."""
import Rhino
import scriptcontext as sc
from earthlink import env, server, sync

doc = globals().get("__rhino_doc__") or sc.doc
st = server.start()
if st == "busy":
    Rhino.RhinoApp.WriteLine("EarthLinkViewer: port %d is used by another program." % env.PORT)
else:
    sync.start(doc)
    env.open_url(server.url())
    Rhino.RhinoApp.WriteLine("EarthLinkViewer: %s" % server.url())
