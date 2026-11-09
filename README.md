# EarthLink for Rhino 8

**0.1.0 — initial preview; the installable package has not yet been published to Yak.**
The PackageManager installation below becomes available after publication.


EarthLink connects a Rhino model to a browser viewer in its real-world 3D context. It grew out of an architectural studio workflow: checking a design against its surroundings without repeatedly exporting and placing it by hand.
Select geometry, run **`SendToEarth`**, and it appears at its real-world location in your browser (and optionally
in Google Earth Pro). With Live enabled, edits update the browser model. Built for Rhino 8 on macOS and Windows; Windows testing is pending.

## Start here

- **Using EarthLink:** read the [step-by-step user manual](docs/USER_MANUAL.md).
- **Helping as an agent:** read the [agent guide](docs/AGENT_GUIDE.md).
- **Developing or building:** read the [architecture](docs/ARCHITECTURE.md) and [development guide](docs/DEVELOPMENT.md).

## Quick start

1. Install the `.yak` package into Rhino 8 and restart Rhino when convenient.
2. Run `EarthLinkViewer` or `EarthLinkSettings` and enter your own map token/key.
3. Select geometry, run `SendToEarth`, and use `Set=Main`, `Viewer=On`.
4. If no EarthAnchorPoint exists, choose PickOnMap and apply your site location to Rhino.
5. Inspect the result; choose Live=On for watched edits and EarthLinkSync for views, camera following, and sun.

For command options, capture passes, sharing, troubleshooting, data locations, and preview limitations, use the full manual linked above. FollowViewport sends Rhino’s camera to the browser; it is not continuous browser-to-Rhino viewport control.

## The project

Developed by Jimmy Wang as an architecture and software project. EarthLink brings model placement, design alternatives, camera views, and sun studies into one workflow. The code is shared to make that workflow inspectable and open to improvement.

Python handles Rhino geometry, export, and synchronization; CesiumJS handles the browser viewer. The local server runs as a separate process, while Rhino updates run on its UI timer. See [architecture](docs/ARCHITECTURE.md), [development](docs/DEVELOPMENT.md), and [third-party services](docs/THIRD_PARTY.md).

## Preview status
- macOS: integration testing was reported for the internal 0.2.0 build. The rebuilt 0.1.0 package still needs an installed-plugin check.
- Windows: supported by the implementation, but testing remains pending.
- Re-sample ground height when changing sites. Deleting every object in a live set can leave its last exported geometry visible; remove the set in the viewer to clear it.
- Re-export to Earth Pro after browser-only updates; older Earth Pro files can be pruned.

## Install
Rhino → `PackageManager` → search **EarthLink** → Install → restart Rhino.

## First use
1. **Map access (once per computer):** create a free [Cesium ion](https://ion.cesium.com) account → Access Tokens →
   copy the Default token. Paste it when the viewer asks, or run `EarthLinkSettings` → `CesiumToken`.
   (A Google Maps Platform key with the Map Tiles API also works.) EarthLink stores the token locally; the browser uses it to access the external map service.
2. **Site location (once per file)** — either way works and both stay in step:
   - run `SendToEarth` on a file without a location and choose **PickOnMap**: search the place (or type `lat, lon`)
     in the viewer, click where the model's base point should sit, turn the model if needed, **Apply to Rhino**; or
   - run Rhino's `EarthAnchorPoint` as usual.

   The viewer's **Site → Edit Location** writes Rhino's EarthAnchorPoint (latitude, longitude, north), and any change made
   with `EarthAnchorPoint` re-sends the model to the new spot. An existing anchor keeps its elevation settings.

## Commands
| Command | What it does |
|---|---|
| `SendToEarth` | Send selected objects. `Set=` design set (Main, Scheme B…), `Live=On` re-sends the set ~1 s after you edit it, `Viewer`, `EarthPro`. |
| `EarthLinkViewer` | Open the viewer. |
| `EarthLinkSync` | `NamedViews` two-way named views · `FollowViewport` viewer follows Rhino's camera · `Sun` viewer sun ⇄ Rhino Sun. |
| `EarthLinkSettings` | Token/key, Earth Pro default, rename or remove a design set, screenshot folder, data folder, stop the server. |

## Viewer
- **Design Sets** — any number of groups on the same page (`SendToEarth Set=…`). Show/hide each, **Compare** shows one
  at a time. **Edit** a set to rename it (renames it in Rhino too), give it its own display (Materials / Clay / Ghost),
  or move it: drag on the map, nudge east/north/up, rotate — previewed in the viewer, then **Apply to Rhino** moves
  those objects in your file as one undo step and re-sends them. Remove a set (Rhino geometry untouched).
- **Views** — synced with Rhino named views both ways (save, rename, update, delete in either app).
- **Display** — Materials, **Clay** (white massing) or **Ghost** (adjustable opacity); **Section cut** at any height.
- **Camera** — Perspective, Two-Point (verticals stay vertical) or Parallel; lens in degrees and 35 mm equivalent;
  follow Rhino viewport; sync named views; **sync sun with Rhino** (Rhino's Sun also gets the site's location and north).
- **Site** — location, edit on the map, height adjustment and ground re-sampling.
- **Measure** (ruler button) — click two points; metres and feet-inches, with height difference.
- **Capture** — presets or a custom size at exact pixels; **Full / Context only / Model only (transparent)** passes;
  default folder or **Ask each time**; camera embedded in each PNG. **Share…** exports a self-contained viewer (zip)
  for any static web host.

### Rendering workflow
Save views (viewer or Rhino) → with *Sync sun* on, Rhino's Sun matches the viewer → render those named views in Rhino at
the same pixel size → layer the render over the **Context only** capture, using **Model only** as a mask.

## How it works
- Export happens in a hidden Rhino document: your file, selection and undo history are never touched.
- EarthLink keeps a small record in the file's Document User Text (section `EarthLink`): a project id (views follow the
  project, not the file name) and the objects in each design set.
- The viewer server is a separate process on `127.0.0.1:8765`, run on Rhino's bundled Python; it only answers the
  EarthLink page. Sync runs on Rhino's UI timer — no background threads inside Rhino.
- Keep Draco compression off in Rhino's glTF export options (the default) for the Earth Pro link.
- Map data © Google, shown through Cesium; attributions appear in the viewer. Each user uses their own token/key.

## Develop / release
`commands/` one script per command · `earthlink/` shared package (embedded in the plugin) · `shared/viewer/index.html` ·
`icons/` · `tests/` · `EarthLink.rhproj` (Rhino Script Editor project).

```
python3 -m pytest tests                    # server + Earth Pro conversion (no Rhino needed)
python3 tools/build.py 0.1.0 --push-test   # build + push to McNeel's test server (wiped nightly)
python3 tools/build.py 0.1.0 --push        # publish (after `yak login`)
```
GitHub Actions (`.github/workflows/ci.yml`) runs the tests on macOS, Windows and Linux plus a headless viewer check.
Bump the version for every release (published versions can't be replaced) and add a line to `CHANGELOG.md`.
