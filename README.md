# EarthLink

EarthLink connects Rhino to an interactive browser viewer on Google Photorealistic 3D Tiles. Send selected geometry to its real-world location, then see design changes update live. Synchronize named views and sun settings, capture images, and optionally export to Google Earth Pro.

**Preview: 0.2.0-beta.10** (a pre-release in PackageManager: tick *Include pre-releases*). The stable release is 0.1.1.

## Install

In Rhino 8, run **PackageManager**, search **EarthLink** (tick *Include pre-releases* for this beta), and install. Restart Rhino when ready.

You need your own Cesium ion token or Google Maps Platform key with Map Tiles API access. Enter it in **EarthLinkSettings** or the viewer's connection dialog. Google Earth Pro is optional.

## Send a model

1. Check the Rhino file's units and EarthAnchorPoint.
2. Select geometry and run **SendToEarth**.
3. Choose a design set. Enable **Live** to update it as you edit.
4. If the file has no location, choose **PickOnMap**, click where the model should stand, and apply it to Rhino. The bottom centre of what you sent goes on that spot, wherever the geometry is in the Rhino file (it becomes the EarthAnchorPoint's model base point; a base point you set yourself is kept). To turn a set on the map, use **Edit** on the set (Rhino's north is not changed).
5. Inspect the model in the browser. Use **Fit** to frame it.

Meshes, surfaces, polysurfaces, extrusions, SubDs, and nested blocks are supported. Curves and annotations are not exported as surfaces.

After upgrading from 0.1.x, send each set once to generate the geometry needed for precise cutouts and walking on your model.

## Find a place

Type in the search bar (top left). Suggestions from Google refine as you type, under your **Recent searches**; names read like Google Earth's ("180 Cayuga Park Lane, Ithaca, NY"). Press Enter or pick a result to fly there, or type exact `lat, lon`. With the field empty, the first result is your site. Search needs your Cesium ion token or Google key; coordinates always work.

## Navigate

Controls follow Rhino 8's defaults, including its small differences between Mac and Windows. On a Mac, **Mod** is ⌘ and **Alt** is Option; on Windows, Mod is Ctrl.

| Action | Mouse (Mac and Windows) | Mac trackpad | Windows touchpad |
| --- | --- | --- | --- |
| Rotate about the point at the centre of the view | Right-drag | Two fingers | Right-drag |
| Pan (the ground follows the pointer) | Shift + right-drag, or middle-drag | Shift + two fingers | Shift + right-drag |
| Zoom toward the cursor | Wheel, or Mod + right-drag (drag up = in) | Pinch | Two-finger scroll or pinch |
| Dolly (move in / out) | Alt + right-drag | | |
| Rotate a Parallel view | Mod + Shift + right-drag | | |
| Turn the camera where it stands | Mod + Alt + right-drag | | |
| Lens length | Mod + Shift + Alt + right-drag, or Shift + Page Up / Down | | |

Keys: the arrows rotate (pan in Parallel), Shift + arrows pan, and Page Up / Page Down zoom. Press Shift partway through a right-drag to lock it to one direction. In **Parallel**, right-drag and two fingers pan, as in Rhino. On a Mac, Option + middle-drag rotates; on Windows, Alt + middle-drag dollies. Rhino's view roll (Shift + Alt + right-drag) is not used, because the horizon always stays level.

Each gesture keeps one mode until it ends, including its momentum, and movement is eased frame by frame. Pan and zoom scale with distance and orbit is angular, so one swipe feels the same from orbit to a single room.

Rotation turns about what is at the centre of the view when you start, like Rhino's camera target, and keeps that point from one rotation to the next until you pan, zoom or fly (a tree passing in front does not move it). When the centre of the view runs to far ground or sky it is your model's depth. A gesture does one thing from start to finish: a pinch that slips into a two-finger rotation is ignored, and the glide after your fingers lift is shortened. You can tilt below the horizon to look up at a facade. The camera passes through trees and buildings on the map, as in Rhino; it only comes to rest when it descends onto a surface from above, and it follows gently rising ground. Nothing lifts the camera by itself.

On a Mac a web page cannot tell a Magic Mouse from the trackpad, so a Magic Mouse swipe rotates like two fingers on the trackpad (in Rhino it zooms). A wheel mouse zooms.

The compass shows north: click it for north up, or drag it to turn (sideways) and tilt (up and down). **Fit** frames the visible design sets. Click **− / +** for a step, or hold them to zoom continuously. **Sensitivity** (one value for every movement) and the list of controls are under **Navigation** in the sidebar; **Record input for 10 s** there saves what your trackpad or mouse sends, to report a navigation problem.

Two-Point keeps verticals vertical and navigates like Perspective: tilting moves the camera up or down around what you look at and shifts the lens, up to 65° (steeper stretches the picture). Using browser navigation turns off **Follow Rhino**.

## Walk and fly

Drag the person button onto the map and drop it where you want to stand, as in Google Maps: on your model or on the map, with or without a model. Or select the person, then click a spot. The view flies down to eye level.

| Control | Action |
| --- | --- |
| W A S D or arrow keys | Walk (4.4 m/s) |
| Double-tap W (on a Mac, also Control) | Sprint (11.9 m/s) until you stop |
| Shift | Sneak (1.3 m/s) |
| Space | Jump |
| Double-tap Space | Fly, as in Minecraft creative mode; double-tap again to drop |
| While flying | Space rises, Shift sinks (9.4 m/s); W A S D fly at 13.6 m/s, sprinting at 27 m/s; nothing is in the way |
| Two fingers or right-drag | Look around |
| Esc or the person button | Return to the previous view |

You walk as a 1.80 m person with eyes at 1.65 m. On foot, walls and ceilings stop you and you slide along them. Flying has no collision: you pass through buildings, trees, your model and the ground, and dropping out of a flight under the map stands you on the surface above. Steps up to 45 cm are climbed and stairs are followed down. Collisions use what is drawn: your exported model mesh and the loaded Google map. Where **Hide map underneath** removes the map, you stand at the level of the set's base. Section cuts disable Walk. On Windows, Control does not sprint, because Ctrl + W closes the browser tab.

## Sun and views

Open **Sun** to control sunlight, date, time, and dynamic shadows. Turning sunlight off uses neutral lighting and hides the time controls. Shadows photographed into Google's imagery remain part of the map texture.

With the sun low the map turns warm, and at night dark blue, with stars and a dim moonlight on your model; shadows fade out as the sun reaches the horizon. (The map is a daytime photograph: it is tinted, not relit.) **Sync with Rhino** exchanges the sun's enabled state and time. Rhino's current sun is used when connecting or reconnecting synchronization. Time uses the browser computer's time zone, including the selected date's daylight-saving offset.

Save named views in Rhino or the viewer: they are always the same in both. A view saved, updated, renamed or deleted in the viewer changes in Rhino's Named Views panel, and the other way round. Saved views retain the camera, projection, lens, and sun time; recalling a time does not switch sunlight on.

## Design sets and display

- Send selections as separate named sets; show, hide, compare, or style them independently.
- Materials, Clay, and Ghost control model display. Materials shows your Rhino render materials lit like Rhino's Rendered mode (measured on the same colour swatches): colours, image and procedural textures with their box or planar mapping, glass and other see-through materials, emission. It is a real-time picture: there are no ray-traced reflections or refraction, and polished metal shows mostly its own colour.
- **Edit** a set (select its name) to place it on the site: drag it on the map (**Move on map**), type its East / North / Up offset in metres, or rotate it about the centre of its base with the slider or an exact angle. The same card has **Update when it changes in Rhino** (SendToEarth's Live option) and **Update now**, so you do not need Rhino's command line to refresh a set. Changes show at once and are saved automatically; there is no Apply step and nothing is exported again. Placement is an EarthLink layer kept with the set in your Rhino file: your Rhino geometry never moves, so you can keep modelling on Rhino's own grid. **Original position** puts the set back where it is in Rhino. While you drag or rotate, **Hide map underneath** pauses and returns when you stop.
- **Hide map underneath** is set for each design set (the scissors next to its eye). It removes Google content only where the set meets the ground: the outline of the set's lowest surfaces, within 1 cm of its lowest point. An overhang, a cantilever or a set that widens upward keeps the map beneath it. Concave edges, separate pieces and courtyards over 1 m² are preserved. Ground is removed as well as buildings and vegetation. Around the base, within 3 m, the map's own ground is graded to the base's level, so the map meets the model with no gap and no separate patch; trees and buildings more than about 4 m above or below the base keep their height. The grading is a presentation fill, not survey data. Sets more than about 400 m apart share one cut-out and its edge gets coarser.
- **Section cut** clips the uploaded model. **Measure** uses two clicked points; Esc clears the measurement.

## Capture and share

Open **Capture** to choose image size, detail, and full/context/model passes. The model pass has a transparent background. Capture the current view or all saved views. Images include camera metadata.

**Share** exports a static viewer ZIP with the current sets and views. Serve its extracted folder through a web server. Visitors use their own map token unless you explicitly include one; restrict an included token to the shared site. Keep required map attribution visible.

## Commands

| Command | Purpose |
| --- | --- |
| `SendToEarth` | Send selected geometry, choose sets and Live behavior |
| `EarthLinkViewer` | Open the viewer |
| `EarthLinkSync` | Configure views, viewport following, and sun sync |
| `EarthLinkSettings` | Set map credentials, capture folder, and Earth Pro options |

## Manuals and development

- [User manual](docs/USER_MANUAL.md): installation, full workflow, troubleshooting, and limitations.
- [Agent guide](docs/AGENT_GUIDE.md): safe operation and development guidance for assistants.
- [Architecture](docs/ARCHITECTURE.md) and [development](docs/DEVELOPMENT.md): source structure, tests, builds, and releases.
- [Third-party services and licenses](docs/THIRD_PARTY.md).

EarthLink uses Rhino 8 Python, a separate local Python server, CesiumJS 1.140, and a browser viewer with no frontend build step. Original EarthLink code is MIT licensed; bundled dependencies retain their own licenses.

This preview has unit, API and browser tests and was checked on a Mac GPU over Google's tiles. Windows integration still needs a separate check. Map content is visual context, not survey data. Known issues are listed in the user manual.
