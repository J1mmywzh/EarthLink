# EarthLink

**Your Rhino 8 model on Google's photorealistic 3D map, live, in the browser.** Free, for Mac and Windows.

Send geometry from Rhino and it stands on the real site. Change it in Rhino and it updates. Move the sun, go to night with your model's lights, save views that Rhino shares, capture images, walk around at eye level, and bring the surrounding terrain, buildings and roads back into Rhino as geometry.

**Preview: 0.2.0-beta.11** (a pre-release in Package Manager: tick *Include pre-releases*). The stable release is 0.1.1.

## Quick start

1. **Install.** In Rhino 8, run `PackageManager`, tick *Include pre-releases*, search **EarthLink**, install, restart Rhino. The commands are typed (there is no toolbar): `SendToEarth`, `EarthLinkViewer`, `EarthLinkSync`, `EarthLinkSettings`.
2. **Connect the map** (once, about two minutes, free). Run `EarthLinkViewer`. The viewer opens in your browser with a dialog:
   - *Create a free Cesium ion account* opens [ion.cesium.com/signup](https://ion.cesium.com/signup).
   - *Open your access tokens* opens [ion.cesium.com/tokens](https://ion.cesium.com/tokens): copy the **Default Token**.
   - Paste it. EarthLink checks it with Cesium at once and says so if it is wrong. Press **Connect**.

   A Google Maps Platform key with the Map Tiles API works too (*Use a Google Maps key instead*). Change it later under **Site > Map connection**, or with `EarthLinkSettings > ConnectMap`.
3. **Send a model.** Select geometry, run `SendToEarth`, choose **PickOnMap** and click where it should stand. That is all: the model is on the site.

What you need: Rhino 8, an internet connection (the map and the viewer's 3D engine are loaded from the web), and a current Chrome, Edge, Safari or Firefox. The viewer runs on your own computer at `127.0.0.1:8765`; your model is not uploaded anywhere.

| Then try | Where |
| --- | --- |
| Update while you model | `SendToEarth` with **Live**, or **Edit** on a set |
| Clear the site under the model | the dashed square beside a set's eye |
| Sun, shadows, night with your Rhino lights | the sun button |
| Views shared with Rhino's Named Views | **Save View** |
| Images of every saved view | the camera button |
| Terrain, buildings, roads and contours into Rhino | the dashed square with an arrow |
| Walk at eye level | the person, bottom right |

## Send a model

1. Check the Rhino file's units and EarthAnchorPoint.
2. Select geometry and run **SendToEarth**.
3. Choose a design set. Enable **Live** to update it as you edit.
4. If the file has no location, choose **PickOnMap**, click where the model should stand, and apply it to Rhino. The bottom centre of what you sent goes on that spot, wherever the geometry is in the Rhino file (it becomes the EarthAnchorPoint's model base point; a base point you set yourself is kept). To turn a set on the map, use **Edit** on the set (Rhino's north is not changed).
5. Inspect the model in the browser. Use **Fit** to frame it.

Meshes, surfaces, polysurfaces, extrusions, SubDs, and nested blocks are supported. Hidden objects and objects on layers that are off are left out. Curves and annotations are not exported as surfaces.

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

Rotation turns about what is at the centre of the view when you start, like Rhino's camera target, and keeps that point from one rotation to the next until you pan, zoom or fly (a tree passing in front does not move it). While your model reaches the middle of the view the point stays within the model's depth, even when the exact centre of the view passes it and lands on ground far behind. A trackpad sends small pinches while two fingers scroll or rest, and a burst when they lift: these are dropped, and a pinch zooms once it is clearly meant (about 3 % of spread). When the centre of the view runs to far ground or sky it is your model's depth. A gesture does one thing from start to finish: a pinch that slips into a two-finger rotation is ignored, and the glide after your fingers lift is shortened. You can tilt below the horizon to look up at a facade. The camera passes through trees and buildings on the map, as in Rhino; it only comes to rest when it descends onto a surface from above, and it follows gently rising ground. Nothing lifts the camera by itself.

On a Mac a web page cannot tell a Magic Mouse or a smooth-scrolling mouse from the trackpad, so their scrolling rotates like two fingers on the trackpad (in Rhino it zooms). Choose **Scroll: Zooms** in the compass panel if you use one. A notched wheel mouse zooms. In Safari a trackpad pinch is handled too.

The compass shows north. Click it for **Heading**, **Tilt** and **Sensitivity**, each with a slider and a field you can type in, and **North up**; drag the compass itself to turn (sideways) and tilt (up and down); double-click it for north. **Fit** frames the visible design sets. Click **− / +** for a step, or hold them to zoom continuously. **Lens** (Camera, in the sidebar) is the lens length in millimetres as on a 35 mm camera, like Rhino's: the slider runs from 12 to 200 mm, and any length from 6 to 1200 mm can be typed. The time of day can be typed as well as dragged.

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

With the sun low the map turns warm, and at night dark blue under a dark sky with stars, with a dim moonlight on your model so the scene stays readable; shadows fade out as the sun reaches the horizon. (The map is a daytime photograph: it is tinted, not relit.) **Sync with Rhino** exchanges the sun's enabled state and time. On connecting, a Sun that is on in Rhino sets the viewer's date and time; a Sun that is off in Rhino (the default in a new file) leaves the viewer's sunlight as it was, and changing the time in the viewer does not switch Rhino's Sun on (the Sunlight switch does). Time uses the browser computer's time zone, including the selected date's daylight-saving offset.

**Lights.** The lights in your Rhino model (point, spot, directional, rectangular, linear) light the model and the map around it, as Rhino's Rendered mode draws them: the light's colour times its intensity times the cosine of its angle to the surface, with the fall-off chosen in Rhino (none by default), a spotlight fading from its axis by its hot spot, and a rectangular or linear light acting as a point light at its centre. Add, move, recolour, switch or delete a light in Rhino and the viewer follows within a second; nothing is exported again. A light belongs to the nearest design set: it moves with that set's placement and goes dark when the set is hidden. The **Lights** switch in the Sun panel turns them off. Differences from Rhino: a spotlight's hard cone edge is softened and very strong light levels off instead of clipping to flat white, so that a lamp reads as light; the two brightest point lights or spotlights cast shadows from your model and the map (hard-edged, as in Rhino; the Shadows switch in the Sun panel turns them off with the sun's), the other lights cast none, so a third lamp in a room also lights the ground outside the wall; and on the map a light with no fall-off fades out one to two times its set's size away, so that a lamp does not light the whole city.

Save named views in Rhino or the viewer: they are always the same in both. A view saved, updated, renamed or deleted in the viewer changes in Rhino's Named Views panel, and the other way round. Saved views retain the camera, projection, lens, and sun time; recalling a time does not switch sunlight on.

## Design sets and display

- Send selections as separate named sets; show, hide, compare, or style them independently.
- Materials, Clay, and Ghost control model display. Materials shows your Rhino render materials lit like Rhino's Rendered mode (measured on the same colour swatches): colours, image and procedural textures with their box or planar mapping, glass and other see-through materials, emission. It is a real-time picture: there are no ray-traced reflections or refraction, and polished metal shows mostly its own colour.
- **Edit** a set (select its name) to place it on the site: drag it on the map (**Move on map**), type its East / North / Up offset in metres, or rotate it about the centre of its base with the slider or an exact angle. The same card has **Update when it changes in Rhino** (SendToEarth's Live option) and **Update now**, so you do not need Rhino's command line to refresh a set. Changes show at once and are saved automatically; there is no Apply step and nothing is exported again. Placement is an EarthLink layer kept with the set in your Rhino file: your Rhino geometry never moves, so you can keep modelling on Rhino's own grid. **Original position** puts the set back where it is in Rhino. While you drag or rotate, **Hide map underneath** pauses and returns when you stop.
- **Hide map underneath** is set for each design set (the dashed square next to its eye). It removes Google content only where the set meets the ground: the outline of the set's lowest surfaces, within 1 cm of its lowest point. An overhang, a cantilever or a set that widens upward keeps the map beneath it. Concave edges, separate pieces and courtyards over 1 m² are preserved. Ground is removed as well as buildings and vegetation. Around the base, within 3 m, the map's own ground is graded to the base's level, so the map meets the model with no gap and no separate patch; trees and buildings more than about 4 m above or below the base keep their height. The grading is a presentation fill, not survey data. Sets more than about 400 m apart share one cut-out and its edge gets coarser.
- **Section cut** clips the uploaded model. **Measure** uses two clicked points; Esc clears the measurement.

## Bring the surroundings into Rhino

**Surroundings to Rhino** (the dashed square with an arrow, right-hand tools) brings the area around your site into the Rhino file as geometry you can model against. Drag a rectangle on the map (20 m to 3 km a side), choose **Terrain**, **Buildings**, **Roads** and **Contours**, and press **Import**; a bar shows the progress. **Options** holds the contour interval, the height given to buildings OpenStreetMap has no height for (7 m unless you change it) and the storey height used when it gives storeys. Rhino adds, on layer **EarthLink Context**, in place and as one Undo step:

- **Terrain**: a mesh of the ground (cells of 1 m, coarser for areas over 200 m a side), placed so that it passes through the map's ground at your site.
- **Buildings**: closed solids from each building's outline, standing on the terrain. The height comes from OpenStreetMap (its height, or 3.2 m per storey); where it has none, 7 m is assumed and the building goes on its own layer, **Buildings (height assumed)**. Whole buildings only: those centred in the rectangle.
- **Roads**: centre lines draped on the terrain, cut at the rectangle, named and tagged with their kind.
- **Contours**: lines at round heights above sea level at your interval, every fifth on its own layer, each named with its height.

Everything OpenStreetMap records about a building or road (use, storeys, material, name) is in the object's user text, as `osm:` keys.

This is open data, not Google's map, which its terms do not allow to be exported: buildings and roads © OpenStreetMap contributors (ODbL), terrain from Terrain Tiles on AWS Open Data. Pressing Import sends the rectangle (with 200 m around it) to OpenStreetMap's servers and the terrain tiles' server, and nothing before that. It is massing and context, not a survey: outlines are as accurate as OpenStreetMap is there, usually a metre or two.

## The file remembers

What you set up for a Rhino file is kept in that file: the site, each set's objects and placement, named views, and (new) each set's display and cut-out, the height offset, the sun's date and time, the lights switch and the last camera and lens. Open the file later, run **EarthLinkViewer**, and the viewer shows it as you left it; the sets are exported again by themselves. Nothing has to be placed or imported twice.

## Send feedback

**Send feedback** (the speech bubble, right-hand tools) opens a card with your comment, an optional screenshot of the view and system details (version, system, browser, graphics card, view size; no location; they are sent, not listed on the card). **Open on GitHub** opens a filled-in issue for you to submit (a GitHub account is needed); **Email** opens your mail app with the message addressed to rhinoearthlink@gmail.com. Nothing is sent until you submit or send it yourself. A web page cannot attach a file for you, so the screenshot is put on the clipboard (paste it into the issue) and saved as `earthlink-feedback.png` in Downloads (attach it to the email).

## Capture and share

Open **Capture** to choose image size, detail, and full/context/model passes. The model pass has a transparent background. Capture the current view or all saved views. Images include camera metadata.

**Share** exports a static viewer ZIP with the current sets and views. Serve its extracted folder through a web server. Visitors use their own map token unless you explicitly include one; restrict an included token to the shared site. Keep required map attribution visible.

## Commands

| Command | Purpose |
| --- | --- |
| `SendToEarth` | Send selected geometry, choose sets and Live behavior |
| `EarthLinkViewer` | Open the viewer |
| `EarthLinkSync` | Viewport following and sun sync |
| `EarthLinkSettings` | Map connection, capture folder, Earth Pro, sets, stop the viewer's server |

## Manuals and development

- [User manual](docs/USER_MANUAL.md): installation, full workflow, troubleshooting, and limitations.
- [Agent guide](docs/AGENT_GUIDE.md): safe operation and development guidance for assistants.
- [Architecture](docs/ARCHITECTURE.md) and [development](docs/DEVELOPMENT.md): source structure, tests, builds, and releases.
- [Third-party services and licenses](docs/THIRD_PARTY.md).

EarthLink uses Rhino 8 Python, a separate local Python server, CesiumJS 1.140, and a browser viewer with no frontend build step. Original EarthLink code is MIT licensed; CesiumJS is loaded from a CDN under its own license.

This preview has unit, API and browser tests and was checked on a Mac GPU over Google's tiles. Windows integration still needs a separate check. Map content is visual context, not survey data. Known issues are listed in the user manual.
