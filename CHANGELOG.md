# Changelog

## 0.2.0-beta.6 — preview, 2026-11-09
- Areas of the map that stayed blurry at normal viewing distances (sharp only when zoomed right in) now load full detail. Google's map contains empty placeholder tiles; Cesium refused to swap a coarse tile for its sharper sub-tiles while one of those placeholders was still too small on screen to open. Placeholders are now always opened.

## 0.2.0-beta.5 — preview, 2026-11-09
- Blurry patches of the map that never sharpen are fixed. When a map tile request failed once (Wi-Fi drop, waking from sleep, a rate limit), Cesium never asked again, so that area stayed at its coarse overview until the page was reloaded. Failed tiles are now retried with a growing delay, at once when the connection or the tab comes back, and the map reconnects by itself if its session has expired.

## 0.2.0-beta.4 — preview, 2026-11-09
- Large models are fast in the viewer. Rhino's glTF writer makes one piece per Brep face (43,072 pieces for a 7,000-object building), and the browser drew each separately every frame (about 4 fps). Each export is now merged into one piece per material (39 for that building): under 4 ms per frame instead of about 240 ms, a file a third the size (63 MB → 19 MB), and faster loading. The shape, materials and the placement layer are unchanged. Resend each set once.
- **Hide map under model** works on large models. The outline used to be built by merging every triangle and timed out after 30 s; it is now painted on a fine grid and traced in about 0.1 s. Courtyards, separate buildings and concave corners are kept, and the outline is a handful of polygons (11 for that building), so the cut-out map stays fast too. Removed the two geometry libraries it needed.

## 0.2.0-beta.3 — preview, 2026-11-09
- Search: addresses that start with a house number ("180 Cayuga Park Lane") were mistaken for coordinates and never searched; suggestions now stay while you type on.
- Orbit and zoom about 10 % slower (trackpad, mouse and − / +).
- Opening the viewer after an update replaces a server left running by the previous version (it served a removed folder: "File not found").

## 0.2.0-beta.2 — preview, 2026-11-09
- Navigation rebuilt to follow Rhino 8 for Mac, with or without a model and at any scale: two fingers orbit about the point at the centre of the view, Shift pans with the ground following the fingers, pinch zooms toward the cursor; Parallel pans (Shift changes nothing). Mouse: right-drag, Shift/middle-drag, wheel, Ctrl + right-drag.
- No more roll, Earth flips, inverted pans or mouse/trackpad mix-ups: one input path (Cesium's own controls are off), gestures keep one mode through their momentum, per-frame easing, level horizon near straight-down views, camera kept above Google's mesh.
- Parallel views no longer show a black half or tile seams and no longer drift while panning; switching back to Perspective keeps the framing.
- One Sensitivity setting; the input-device selector is gone. Continuous hold-to-zoom on − / +. Compass shows north.
- Search bar (top left) like Google Earth: suggestions refine as you type, recent searches, Google Earth-style names, fly to your site.
- Walk works anywhere on the map, with or without a model, at 3.5 m/s (sprint 9.5 m/s), smooth at full frame rate; climbs 45 cm steps, follows stairs down, slides along walls. Replaced the physics library and map-contact modules (about 600 KB) with a small ray-probing walker.
- Surface picking for pivots, walking and placement uses CPU ray tests on your exported mesh and Google's tiles, independent of the GPU depth buffer.
- Removed self-shadow stripes on Google's mesh that shimmered while moving.
- Placing a design set (drag, nudge, rotate, **Apply**) no longer moves Rhino geometry: the placement is an EarthLink layer saved with the set and applied on every export. **Original position** removes it.

## 0.2.0-beta.1 — development preview, 2026-11-09
- Site-local Rhino-style navigation, compass/heading/tilt, true-north reset, fit and zoom controls.
- Physical walking prototype: surface placement, WASD, sprint, jump, gravity, wall/ceiling collisions and steps; sampled map contacts pause at missing surfaces.
- One sunlight enabled state, neutral off lighting, reciprocal Rhino sun enable/time and a compact Sun panel; removed the permanent timebar.
- Exported mesh footprints preserve concave shapes, islands and courtyard holes without padded rectangular masks.
- Removed persistent instructions and redundant secondary interface copy; expanded the manuals.
- Fixed concurrent temporary-file collisions in JSON/settings saves. Added behavioral/browser tests, bundled dependency licenses, complete share resources and compatible CI runners.
- Preserved panned orbit targets and upward Two-Point framing; cancelled map contacts on Walk exit and rejected delayed live exports. Corrected prerelease package filenames.
- Restored nested viewer-library paths after the Rhino build so installed packages retain working imports.
- Published 0.1.0/0.1.1 artifacts are unchanged. Installed-Rhino/Windows acceptance remains separate.

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
