# Agent guide

This guide is for an assistant helping someone use or develop EarthLink. Start with `README.md`, then `USER_MANUAL.md`; use `ARCHITECTURE.md` and `DEVELOPMENT.md` for changes to the implementation.

## Before operating Rhino

1. Identify the active Rhino document, its unsaved state, model units, current selection, EarthAnchorPoint, and existing EarthLink sets. Do not assume a prior session's file or anchor is still current.
2. Establish whether the user wants a send, a named view, a site edit, a set placement, a capture, a build, or publication. Keep the action within that scope.
3. Use an anchor supplied or approved by the user. Exact site coordinates and selected geometry can reach external map services or a shared viewer; do not invent a real project location or transmit it without authorization.
4. For a normal installed-plugin check, use the installed commands and confirm the plugin path. Do not silently substitute source-script execution.
5. A browser set move is applied by the viewer at once and saved automatically as an EarthLink-only placement with the set; it never moves Rhino geometry and never needs an export. Removing a set does not delete geometry.

## Runtime constraints

- Never run Python background threads inside Rhino. The server is a separate process. Sync uses Eto UITimer on Rhino's UI thread.
- Export using a headless document. Preserve the user's selection, geometry, and undo state except for requested document changes.
- Use `tools/build.py`, retaining `earthlink/` as the project library base and the 24 px light/dark command icons.
- Rhino/pythonnet out-parameters can be tuples. Keep `_frustum` handling intact.
- Sun updates use DateTimeKind.Unspecified for construction and SetDateTime with Utc, plus the per-date offset received from the viewer.
- `env.viewer_dir()` prefers installed resources. When testing source, pass an explicit source viewer directory to the server.
- If Rhino is unresponsive, stop trying to drive it and continue with work that does not need Rhino. Ask before restarting it.

## Test and release discipline

Use isolated temporary application data and the supplied fixture. Do not read or print user tokens. Do not publish live model exports, private notes, captures, account credentials, or runtime files. Keep plugin GUID stable. Test the installed package in Rhino separately from unit tests. Windows support is implemented but awaits integration testing. Track the retained known issues in ARCHITECTURE.md rather than claiming they are resolved.

A build does not authorize installation, a Rhino restart, or public publication. For public uploads, confirm that the user requested the destination and visibility. Do not add a contact email or claim test results without evidence. Report exactly which checks ran and which remain pending.

## Git and cross-computer work

Pull before editing. Inspect changes, run appropriate checks, commit, and push completed source changes when authorized. Confirm the remote has the intended commit before calling it synchronized. An ignored file is not cloud-backed by Git. Do not force-add ignored local records or force-push to resolve divergence.

## Viewer development preview

Read the README navigation and walking controls before driving the viewer. Do not reintroduce permanent gesture legends, eye-height labels or explanatory subtitles; use short labels, essential values and actionable messages. Resend legacy sets to create geometry sidecars. Walking and cutouts must use the same displayed export/version and set transforms. Preserve courtyard holes and disconnected regions; never fall back to an enclosing rectangle.

Navigation follows Rhino 8 for Mac and Windows (README table) and is the only thing that moves the camera: keep Cesium's screenSpaceCameraController inputs AND its collision detection off, and `enableCollision` off on the tileset (left on, Cesium lifted the camera by tens of metres with no input). The pivot is distance-limited (`pivotDistance`) and the ground rule never pushes the camera up suddenly (`Floor`); both have unit tests, and `tests/viewer_review.cjs` holds the regressions measured on 2026-11-13. Do not add inertia or per-device modes; tune the rates in `navigation.js` RATE (one user-facing Sensitivity). A gesture does one thing: keep the pinch/scroll latch and the pivot kept between rotations (re-picking the pivot every gesture is what made rotation swing). Two-Point must stay a rendering of the same camera (`pose`/`setPose`), never a second set of gestures. Never move the real camera to produce something else (0.2.0-beta.8 photographed the ground that way: a visible jump and white patches); the map cut-out and the night tint live in the map's `CustomShader`. Real trackpad feel cannot be verified by automation: ask for an input recording (Navigation > Record input). Surface picks (pivot, walking, placement) use CPU ray tests: the exported mesh and `tile.content.pick`; avoid `scene.pickFromRay`/`pickPosition`, which depend on the depth buffer and were unreliable. Parallel cameras stay 20 km behind their centre point and Cesium's orthographic width adjustment is disabled.

Walking probes what is drawn each frame (`walk.js`). Nothing from Google's tiles is extracted or stored beyond Cesium's in-memory pick buffers. Test streamed context separately from synthetic fixtures; scan holes and loading can stop motion. Keep person/camera parameters in the manual, not the interface. Preserve the previous camera on exit and stop movement on blur, capture or competing tools.
