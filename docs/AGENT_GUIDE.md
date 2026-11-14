# Agent guide

For an assistant helping someone use or develop EarthLink. Read the [README](../README.md) and the [user manual](USER_MANUAL.md) first, then [architecture](ARCHITECTURE.md) and [development](DEVELOPMENT.md) before changing code.

## Operating Rhino for someone

1. Find out which document is active, whether it is saved, its units, the selection, the EarthAnchorPoint and the existing sets. Do not assume an earlier session's file is still open.
2. Do only what was asked: a send, a view, a site change, a capture, a build and a publication are different actions, each needing its own go-ahead.
3. Use only site locations the person gave or approved. Never invent coordinates. A site location reaches map and data services, so do not send one without permission.
4. Moving a set in the viewer never moves Rhino geometry; removing a set never deletes objects.
5. If Rhino stops responding, stop driving it and ask before restarting it.

## Code rules

- No Python background threads in Rhino. Document changes happen on the sync timer (Eto UITimer); the server is its own process.
- Export through a headless document.
- Never export the photorealistic map. Site geometry comes from OpenStreetMap, open elevation tiles and public parcel data only (`earthlink/context.py`). Keep requests single, started by the person, with the EarthLink User-Agent. Never request owners' names from parcel services.
- Navigation (`navigation.js`) is the only thing that moves the camera. Keep Cesium's camera inputs and collision off. A gesture does one thing until it ends. Tune speeds only in `RATE`. Two-Point is a rendering of the same camera.
- Surface picks are CPU ray tests on the exported mesh and the map tiles, never depth-buffer reads.
- Never move the real camera to produce an image of something else; map effects live in the map's custom shader.
- Rhino lights are matched to Rendered mode by measurement; measure again before changing the light formulas.
- Use `tools/build.py`. Keep the plugin id and the 24 px light/dark command icons.

## Tests and releases

- Use the fixture server and temporary data folders. Never read or print map keys, and never write test data into a real profile.
- Trackpad feel cannot be automated: record the person's input (`?record` in the viewer address) and replay it in tests. Try changes with EarthLink Dev before a release.
- A build does not authorize installing, restarting Rhino or publishing. Publishing needs an explicit yes.
- Report exactly which checks ran and which did not.

## Git

Pull before editing, commit and push finished work, and confirm the remote has the commit. Never force-add ignored files or force-push.
