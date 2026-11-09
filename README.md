# EarthLink

EarthLink connects Rhino to an interactive browser viewer on Google Photorealistic 3D Tiles. Send selected geometry to its real-world location, then see design changes update live. Synchronize named views and sun settings, capture images, and optionally export to Google Earth Pro.

**Preview: 0.2.0-beta.6** (a pre-release in PackageManager: tick *Include pre-releases*). The stable release is 0.1.1.

## Install

In Rhino 8, run **PackageManager**, search **EarthLink** (tick *Include pre-releases* for this beta), and install. Restart Rhino when ready.

You need your own Cesium ion token or Google Maps Platform key with Map Tiles API access. Enter it in **EarthLinkSettings** or the viewer's connection dialog. Google Earth Pro is optional.

## Send a model

1. Check the Rhino file's units and EarthAnchorPoint.
2. Select geometry and run **SendToEarth**.
3. Choose a design set. Enable **Live** to update it as you edit.
4. If the file has no location, choose **PickOnMap**, select the site, and apply it to Rhino.
5. Inspect the model in the browser. Use **Fit** to frame it.

Meshes, surfaces, polysurfaces, extrusions, SubDs, and nested blocks are supported. Curves and annotations are not exported as surfaces.

After upgrading from 0.1.x, send each set once to generate the geometry needed for precise cutouts and walking on your model.

## Find a place

Type in the search bar (top left). Suggestions from Google refine as you type, under your **Recent searches**; names read like Google Earth's ("180 Cayuga Park Lane, Ithaca, NY"). Press Enter or pick a result to fly there, or type exact `lat, lon`. With the field empty, the first result is your site. Search needs your Cesium ion token or Google key; coordinates always work.

## Navigate

Controls follow Rhino 8 for Mac.

| Action | Trackpad | Mouse |
| --- | --- | --- |
| Orbit (about the point at the centre of the view) | Two fingers | Right-drag |
| Pan (the ground follows your fingers) | Shift + two fingers | Shift + right-drag, or middle-drag |
| Zoom (toward the cursor) | Pinch | Wheel, or Ctrl + right-drag |

In **Parallel** views two fingers and right-drag pan, with or without Shift; pinch or the wheel zoom. Rotate a parallel view with the Tilt and Heading sliders.

The horizon always stays level. Each gesture keeps one mode until it ends, including its momentum, and movement is eased frame by frame. Pan and zoom scale with distance and orbit is angular, so one swipe feels the same from orbit to a single room.

The compass shows north; select it for **Tilt**, **Heading**, **Sensitivity** and **Reset to north**. **Fit** frames the visible design sets. Click **− / +** for a step, or hold them to zoom continuously. Trackpad and mouse are recognized automatically.

Two-Point keeps verticals vertical and offers **Vertical framing** instead of tilt. Using browser navigation turns off **Follow Rhino**.

## Walk

Choose the person button, then click where to stand: your model or the map, with or without a model.

| Control | Action |
| --- | --- |
| W A S D or arrow keys | Walk (3.5 m/s) |
| Shift | Sprint (9.5 m/s) |
| Space | Jump |
| Two fingers or right-drag | Look around |
| Esc or the person button | Return to the previous view |

You walk as a 1.80 m person with eyes at 1.65 m. Walls and ceilings stop you and you slide along them; steps up to 45 cm are climbed and stairs are followed down. Collisions use what is drawn: your exported model mesh and the loaded Google map. Where **Hide map under model** removes the ground, include a floor or site surface in your model. Section cuts disable Walk.

## Sun and views

Open **Sun** to control sunlight, date, time, and dynamic shadows. Turning sunlight off uses neutral lighting and hides the time controls. Shadows photographed into Google's imagery remain part of the map texture.

**Sync with Rhino** exchanges the sun's enabled state and time. Rhino's current sun is used when connecting or reconnecting synchronization. Time uses the browser computer's time zone, including the selected date's daylight-saving offset.

Save named views in Rhino or the viewer. With view sync enabled, they appear in both. Saved views retain the camera, projection, lens, and sun time; recalling a time does not switch sunlight on.

## Design sets and display

- Send selections as separate named sets; show, hide, compare, or style them independently.
- Materials, Clay, and Ghost control model display.
- **Edit** a set to place it on the site: drag, nudge or rotate, then **Apply**. Placement is an EarthLink layer saved with the set in your Rhino file and applied on every update; your Rhino geometry never moves, so you can keep modelling on Rhino's grid at 0,0. **Original position** removes the placement.
- **Hide map under model** removes Google content within the visible model's plan outline (traced on a grid of about two million cells over the model's plan, a few decimetres for a city block, never short of the model), preserving concave edges, separate pieces, and uncovered courtyards over 1 m². It removes ground as well as buildings and vegetation. It does not use a padded bounding rectangle.
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
