# Agent guide

This guide is for an assistant helping someone use or develop EarthLink. Start with `README.md`, then `USER_MANUAL.md`; use `ARCHITECTURE.md` and `DEVELOPMENT.md` for changes to the implementation.

## Before operating Rhino

1. Identify the active Rhino document, its unsaved state, model units, current selection, EarthAnchorPoint, and existing EarthLink sets. Do not assume a prior session's file or anchor is still current.
2. Establish whether the user wants a send, a named view, a site edit, a geometry move, a capture, a build, or publication. Keep the action within that scope.
3. Use an anchor supplied or approved by the user. Exact site coordinates and selected geometry can reach external map services or a shared viewer; do not invent a real project location or transmit it without authorization.
4. For a normal installed-plugin check, use the installed commands and confirm the plugin path. Do not silently substitute source-script execution.
5. A browser set move is only a preview until Apply to Rhino. That button changes source geometry. Removing a set does not delete geometry.

## Runtime constraints

- Never run Python background threads inside Rhino. The server is a separate process. Sync uses Eto UITimer on Rhino's UI thread.
- Export using a headless document. Preserve the user's selection, geometry, and undo state except for requested document changes.
- Use `tools/build.py`, retaining `earthlink/` as the project library base and the 24 px light/dark command icons.
- Rhino/pythonnet out-parameters can be tuples. Keep `_frustum` handling intact.
- Sun updates use DateTimeKind.Unspecified for construction and SetDateTime with Utc, plus the per-date offset received from the viewer.
- Validate Undo through Rhino's Edit → Undo menu. Scripted Undo is not equivalent in the recorded test workflow.
- `env.viewer_dir()` prefers installed resources. When testing source, pass an explicit source viewer directory to the server.
- If Rhino is unresponsive, stop trying to drive it and continue with work that does not need Rhino. Ask before restarting it.

## Test and release discipline

Use isolated temporary application data and the supplied fixture. Do not read or print user tokens. Do not publish live model exports, private notes, captures, account credentials, or runtime files. Keep plugin GUID stable. Test the installed package in Rhino separately from unit tests. Windows support is implemented but awaits integration testing. Track the three known issues in ARCHITECTURE.md rather than claiming they are resolved.

A build does not authorize installation, a Rhino restart, or public publication. For public uploads, confirm that the user requested the destination and visibility. Do not add a contact email or claim test results without evidence. Report exactly which checks ran and which remain pending.

## Git and cross-computer work

Pull before editing. Inspect changes, run appropriate checks, commit, and push completed source changes when authorized. Confirm the remote has the intended commit before calling it synchronized. An ignored file is not cloud-backed by Git. Do not force-add ignored local records or force-push to resolve divergence.
