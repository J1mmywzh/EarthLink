# Changelog

## 0.1.1 — 2026-11-08
- Refined the public product description. No runtime functionality changes.

## 0.1.0 — initial public preview, 2026-11-08
- Initial public version selected by Jimmy Wang. Based on the internal 0.2.0 development snapshot below.
- Release numbering restarts at 0.1.0; internal 0.2.0 is archived and is not a newer public release.
- Plugin implementation is unchanged; release identity and public documentation are updated.
- Author reports testing the 0.1.0 package in Rhino 8 before production publication.
- Simplified the public project and package descriptions.
- Known preview limitations: re-sample height when changing sites; an emptied live set can retain its last export;
  browser-only updates can prune an older Earth Pro conversion still in use.

## 0.2.0 — unreleased
- Export through a hidden Rhino document: no temporary objects, selection, redraw or undo changes in your file.
- Project id stored in the file (Document User Text) — views follow the project, not the file name.
- Design sets (`SendToEarth Set=`), shown/hidden/compared in the viewer; `Live=On` re-sends a set after edits.
- Edit a set in the viewer: rename (synced to Rhino), per-set display style, move/rotate (drag or nudge) previewed live,
  then applied to the Rhino objects as one undo step. Rename named views in either app.
- Site location both ways: pick/search on the map writes the EarthAnchorPoint; EarthAnchorPoint edits re-send.
- Sun both ways: viewer date/time ⇄ Rhino Sun (Sun location and north follow the EarthAnchorPoint).
- Viewer: clay and ghost display, section cut, measure, in-page dialogs, two-point picking fix, share export.
- Named views are created without taking over the active viewport (falls back if Rhino needs it).
- Server no longer depends on the folder it was launched from.
- Tested in Rhino 8 (Mac): sync runs on Rhino's UI timer and the server in its own process (fixes two crashes).
- Sun: correct local time in Rhino's Sun panel (time zone from the viewer, per date); the viewer starts from the shared sun.
- Sets moved from the viewer stay watched, so Undo/Redo in Rhino also updates the viewer.
- Follow Rhino viewport: turning it on in Rhino reaches an open viewer without a reload; the camera stays on the
  model when the site frame changes (ground re-sampled, height adjusted).
- Site location: typing exact “lat, lon” picks that point (ground height sampled from the 3D map).
- Tests (pytest + headless viewer) and GitHub Actions on macOS/Windows/Linux.

## 0.1.x — 2026-11-08
- Commands: `SendToEarth`, `EarthLinkViewer`, `EarthLinkSync`, `EarthLinkSettings`, each with its own icon.
- Viewer on Google Photorealistic 3D Tiles, Apple Maps–style UI; projections; two-way named views; follow viewport;
  resolution-exact captures with passes; Google Earth Pro live link; localhost-only server.
