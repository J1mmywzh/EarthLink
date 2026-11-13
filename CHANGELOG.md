# Changelog

## 0.2.0-beta.10 — preview, 2026-11-13
Placing
- A first SendToEarth with **PickOnMap** puts the bottom centre of what you sent on the spot you click, wherever the geometry is in the Rhino file. Before, the picked spot was Rhino's world origin, so a model drawn away from the origin landed away from the click. (It becomes the EarthAnchorPoint's model base point; one you set yourself is kept.)

Hide map underneath
- The map itself is reshaped as it is drawn: not drawn inside a set's base, and graded to the base's level within 3 m around it. The separate band is gone. That band was coloured by moving the real camera to a top-down view for an instant to photograph the ground: this was the jump when a model was first placed or the map was hidden, and the white patches were photographs taken before the map had loaded. Nothing moves the camera now, and switching the cut-out on costs about 50 ms.
- The cut-out returns after a set is moved (it stayed off in one case), and walking follows the graded ground.

Navigation
- A gesture does one thing from start to finish. macOS reports a pinch when two scrolling fingers drift apart; that pinch zoomed the view in the middle of a rotation. It is ignored unless it takes over.
- The point you rotate about stays the same from one rotation to the next, until you pan, zoom or fly. Before, it was chosen again on every gesture, so a tree passing through the centre of the view, or the model's depth against the ground behind it, made the scene swing differently each time.
- The glide macOS adds after your fingers lift is faded out, so a flick does not keep turning the view.
- Two-Point navigates like Perspective: tilting moves the camera around what you look at and shifts the lens, up to 65°. Before, tilt only shifted the lens, up to 80°, where the picture stretched into streaks.
- Everything is 10 % less sensitive. Walking, sprinting and flying are 25 % faster (4.4, 11.9 and 13.6 m/s; 27 m/s sprint-flying).
- Flying has no collision: it passes through buildings, trees, your model and the ground.
- A device guessed wrong from its first event (a trackpad step that looks like a wheel notch on a zoomed page) is corrected by the next events.
- **Record input for 10 s** (sidebar, Navigation > Controls) saves what your trackpad or mouse sends, to report a navigation problem.

Views
- Fixed: a view saved in the viewer never reached Rhino. Creating a Perspective named view failed inside Rhino (a wrong call), which also paused all syncing after five tries. Views saved, updated, renamed or deleted in either app now change in the other, in all three projections, without touching the viewport you are working in.
- Named views are always shared; the switch (and EarthLinkSync's NamedViews option) is gone.

Light, sky and materials
- Time of day: the map turns warm with a low sun and dark blue at night, with stars and a dim moonlight on the model, which takes the same tint. Cast shadows fade out as the sun reaches the horizon; before, a sun under the horizon drew streaks and stipple over a daytime map.
- No stars or dark sky by day when you look up.
- Materials are lit like Rhino's Rendered mode, measured on the same colour swatches in both: a sunlit white is white (it was grey), colours are as vivid as in Rhino, and shadows are as light as Rhino's.
- Glass, polycarbonate and any transparent material are see-through. Rhino writes them in a form real-time viewers ignore, so they showed as opaque blocks.
- Textures keep the object's box, planar or other mapping (it was dropped, so a mapped texture came out at the wrong size). Polished metal shows its colour instead of turning dark. Resend a set to pick these up.

Interface
- Delete is the leftmost action on a set and on a view, then edit.
- The Navigation pop-up is gone. Click the compass for north up, or drag it to turn and tilt; Sensitivity and the controls list are in the sidebar.

Fixed on Windows
- The very first settings save could fail with "Permission denied" when Rhino and the viewer saved at the same moment.

## 0.2.0-beta.9 — preview, 2026-11-13
Navigation
- Fixed the camera jumping by itself: Cesium's own camera collision was still running under EarthLink's navigation and lifted the camera (by 89 m in one measured case) with no input. It is off; only EarthLink moves the camera.
- Fixed the snap when tilting while looking up at something (the camera jumped above the point it turns around; 7.6 m in one frame). Tilt now runs from straight down to straight up, as in Rhino.
- Rotation turns about the centre of the view at the depth you are looking at, like Rhino's camera target. When the centre of the view runs past the model to far ground or sky (shallow and Two-Point views), the pivot stays at the model's depth or the last focus, not 1 to 2 km away, so the model no longer swings off-screen. Pan speed uses the same depth.
- The camera passes through trees and buildings on the map. It rests only on a surface it descends onto from above, follows gently rising ground, and is never pushed up suddenly (the old rule popped the camera by metres and never let it back down).
- A wheel mouse on a Mac is recognised from its first slow notch (it zooms, as in Rhino). A Magic Mouse cannot be told from the trackpad by a web page.

Placing sets
- Placement is a live layer: the viewer applies each set's position and rotation itself. Dragging, nudging and rotating show at once and are saved automatically; nothing is exported again and the Apply button is gone. Before, every move made Rhino export the whole set again, and a second adjustment made before that finished was applied twice.
- The set card shows the total offset of the base centre and the total rotation. Rotation turns the set about the centre of its base.
- Dragging a set no longer rebuilds the map cut-out on every mouse movement (frames of 0.4 s); the cut-out pauses and returns when you stop. A drag near the horizon can no longer fling the set kilometres away.
- Site Location no longer rotates the model (that changed Rhino's north and sun); turn a set with Edit. The model stays at the new site while Rhino takes it over, at the right height, with no jump back.
- Changing only the site location exports nothing. Sets sent by earlier versions are sent once more automatically.
- Walking no longer ends when a ground-height sample arrives.

Interface
- Edit Set: type the East / North / Up offset and the rotation exactly (the twelve nudge buttons are gone); select a set's name to open it. New **Update when it changes in Rhino** switch (SendToEarth's Live option) and **Update now** button, so a set can be refreshed without Rhino's command line. Sets that update by themselves are marked Live in the list.
- Each sync switch sits with what it syncs: named views under Views, the viewport under Camera, the sun in the Sun panel.
- Site: one Height offset field replaces the four nudge buttons.
- Navigation panel: a Controls list for your platform (Mac or Windows).

## 0.2.0-beta.8 — preview, 2026-11-09
- **Hide map underneath** now has a clean edge and no black gap. The map is cut 0.4 m beyond a set's base, and a band redraws the map's ground from a top-down picture of it, from 3 m outside the base up to the base, then stretches its last pixels down or up to the base's own level. The cut's ragged edge is hidden, and where Google's ground is higher or lower than the model's the step is filled instead of showing black. The band follows the ground only (trees and buildings next to the cut are bridged), receives shadows, and is rebuilt when the cut changes or sharper map detail loads. It is a presentation fill, not survey data, and is left out of the model-only capture pass.

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
