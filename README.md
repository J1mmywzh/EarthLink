# EarthLink

EarthLink connects Rhino to an interactive browser viewer on Google Photorealistic 3D Tiles. Send selected geometry to its real-world location, then see design changes update live. Synchronize named views and sun settings, capture images, and optionally export to Google Earth Pro.

**Development preview: 0.2.0-beta.1.** The published PackageManager release is 0.1.1. The navigation and walking changes described below require this development preview.

## Install

In Rhino 8, run **PackageManager**, search **EarthLink**, and install. Restart Rhino when ready. For a development build, install its `.yak` package locally instead.

You need your own Cesium ion token or Google Maps Platform key with Map Tiles API access. Enter it in **EarthLinkSettings** or the viewer's connection dialog. Google Earth Pro is optional.

## Send a model

1. Check the Rhino file's units and EarthAnchorPoint.
2. Select geometry and run **SendToEarth**.
3. Choose a design set. Enable **Live** to update it as you edit.
4. If the file has no location, choose **PickOnMap**, select the site, and apply it to Rhino.
5. Inspect the model in the browser. Use **Fit model** to frame it.

Meshes, surfaces, polysurfaces, extrusions, SubDs, and nested blocks are supported. Curves and annotations are not exported as surfaces.

After upgrading from 0.1.x, send each set once to generate the geometry needed for precise cutouts and walking.

## Navigate

| Action | Trackpad | Mouse |
| --- | --- | --- |
| Orbit | Two-finger slide | Right-drag |
| Pan | Shift + two fingers | Shift + right-drag |
| Zoom | Pinch | Wheel |

Parallel views pan by default; hold Ctrl/Command while right-dragging to rotate. The horizon stays level. The compass opens heading and tilt controls, **Reset to north**, and an input-device preference. Mac defaults to Trackpad; select Mouse when using a mouse. **Fit model** frames visible design sets. **− / +** zoom out and in.

Two-Point preserves verticals and provides **Vertical framing** instead of top-down tilt. For a true top view, use Perspective or Parallel.

Using browser navigation turns off **Follow Rhino**. Enable it again to follow the Rhino viewport.

## Walk

Choose the person button, then click a floor or map surface.

| Control | Action |
| --- | --- |
| W A S D or arrow keys | Move |
| Shift | Sprint |
| Space | Jump |
| Right-drag or two-finger slide | Look |
| Esc or person button | Return to the previous orbit view |

Walking uses a 1.80 m person with the camera about 1.65 m above the floor. Walls and ceilings block movement; ordinary steps up to 0.20 m are climbed automatically. There is no head bob. Save a view or capture an image from the walking camera as usual.

Collision against your model uses the exported mesh. Scanned-map contacts are approximate; missing or unloaded surfaces can pause movement. A cutout removes Google's ground too, so include a floor or site surface where the design replaces it. Section cuts disable Walk. Changing the displayed geometry or recalling a view leaves Walk safely.

## Sun and views

Open **Sun** to control sunlight, date, time, and dynamic shadows. Turning sunlight off uses neutral lighting and hides the time controls. Shadows photographed into Google's imagery remain part of the map texture.

**Sync with Rhino** exchanges the sun's enabled state and time. Rhino's current sun is used when connecting or reconnecting synchronization. Time uses the browser computer's time zone, including the selected date's daylight-saving offset.

Save named views in Rhino or the viewer. With view sync enabled, they appear in both. Saved views retain the camera, projection, lens, and sun time; recalling a time does not switch sunlight on.

## Design sets and display

- Send selections as separate named sets; show, hide, compare, or style them independently.
- Materials, Clay, and Ghost control model display.
- Viewer moves remain a preview until **Apply to Rhino**. Applied moves are one Rhino undo step.
- **Hide map under model** removes Google content within the visible model's projected geometry, preserving concave edges, separate pieces, and uncovered courtyards. It removes ground as well as buildings and vegetation. It does not use a padded bounding rectangle.
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

This preview has synthetic geometry/API/browser tests. Installed-Rhino acceptance, real trackpad feel, and Windows integration require separate checks. Map content and collision samples are visual context, not survey data. Known retained issues are listed in the user manual.
