# EarthLink user manual

EarthLink shows your Rhino 8 model on a photorealistic 3D map of its real site, in your browser. Rhino stays the owner of the model: the viewer never changes your geometry.

**Contents**

1. [Install](#1-install)
2. [Connect the map](#2-connect-the-map)
3. [Place your model](#3-place-your-model)
4. [Design sets](#4-design-sets)
5. [Navigate](#5-navigate)
6. [Walk and fly](#6-walk-and-fly)
7. [Views, sun and lights](#7-views-sun-and-lights)
8. [Display, section and measure](#8-display-section-and-measure)
9. [Surroundings to Rhino](#9-surroundings-to-rhino)
10. [Capture and share](#10-capture-and-share)
11. [Your files and privacy](#11-your-files-and-privacy)
12. [Troubleshooting](#12-troubleshooting)

## 1. Install

1. In Rhino 8, run `PackageManager`, search for **EarthLink** and install it.
2. Restart Rhino.

EarthLink adds four commands:

| Command | What it does |
| --- | --- |
| `SendToEarth` | Send the selected geometry to the viewer as a design set |
| `EarthLinkViewer` | Open the viewer (it starts the local server if needed) |
| `EarthLinkSync` | Follow Rhino's viewport; sync the sun |
| `EarthLinkSettings` | Map connection, capture folder, design sets, stop the viewer's server |

## 2. Connect the map

The photorealistic map needs a free access key, entered once.

1. Run `EarthLinkViewer`. The viewer opens with a **Connect map** dialog.
2. **Create a free Cesium ion account**, then **Open your access tokens** and copy the **Default Token**.
3. Paste it and press **Connect**. EarthLink checks the token at once.

A Google Maps Platform key with the Map Tiles API also works (**Use a Google Maps key instead**). Change the connection later under **Site > Map connection** or with `EarthLinkSettings > ConnectMap`. **Not now** opens the viewer without the map.

The key is kept on your computer, never in the Rhino file. Do not paste it into issues, screenshots or shared viewers.

## 3. Place your model

1. Save the Rhino file and check its units.
2. Select the geometry to show: meshes, surfaces, polysurfaces, extrusions, SubDs and blocks of these. Curves and annotations are not shown.
3. Run `SendToEarth` and choose a design set name (for example `Main`).
4. The first time, EarthLink asks for a **base point**, the point of your model that sits on the site. Object snaps work; Enter takes the bottom centre of the selection.
5. In the viewer, search for the site (an address, a place or `latitude, longitude`), click where the base point goes, and press **Apply to Rhino**.

The site is saved as the file's EarthAnchorPoint. Later sets from the same file keep their position relative to the first. To type a location instead, run Rhino's `EarthAnchorPoint` first.

**Height.** The model's base sits on the map's ground at the site. **Height offset** (under **Site**) raises or lowers it. **Re-sample ground** measures the ground again. When the site moves in Rhino, the ground is measured again automatically.

## 4. Design sets

A design set is a named group of Rhino objects. Use sets for schemes, landscape or anything you want to show, hide or compare separately. Running `SendToEarth` with an existing set name replaces its objects.

| In the viewer | What it does |
| --- | --- |
| Eye | Show or hide the set |
| Dashed square | **Hide map underneath**: removes the map where the set meets the ground |
| Name | Opens **Edit** |
| **Compare** | Shows one set at a time |

**Edit** a set to:

- **Place it**: drag it on the map, type an East / North / Up offset in metres, or rotate it about the centre of its base. Changes show at once and are saved with the set. Your Rhino geometry never moves. **Original position** puts it back.
- **Update when it changes in Rhino** (Live): the set follows your edits about a second after Rhino goes idle. New objects are not added by themselves; send the selection again.
- **Update now**: send the set again.
- Rename it, choose its display (Materials, Clay or Ghost), or remove it. Removing a set never deletes Rhino objects.

**Hide map underneath** cuts the map only where the set's base touches the ground, so overhangs keep the map below them. Courtyards and separate pieces are kept. Within 3 m around the base, the map's ground is graded to meet the model without a gap. This is a presentation fill, not survey data.

Hidden objects and objects on layers that are off are not sent.

## 5. Navigate

Navigation follows Rhino 8, including its Mac and Windows differences. **Mod** is ⌘ on a Mac and Ctrl on Windows; **Alt** is Option on a Mac.

| Action | Mouse | Mac trackpad | Windows touchpad |
| --- | --- | --- | --- |
| Rotate | Right-drag | Two fingers | Right-drag |
| Pan | Shift + right-drag, or middle-drag | Shift + two fingers | Shift + right-drag |
| Zoom toward the cursor | Wheel, or Mod + right-drag | Pinch | Two-finger scroll or pinch |
| Dolly | Alt + right-drag | | |
| Rotate a Parallel view | Mod + Shift + right-drag | | |
| Look around from where you stand | Mod + Alt + right-drag | | |
| Lens length | Mod + Shift + Alt + right-drag | | |

**Keys:** arrows rotate, Shift + arrows pan, Page Up / Page Down zoom, Shift + Page Up / Page Down change the lens.

- Rotation turns about what is at the centre of the view, like Rhino's camera target.
- Pressing Shift during a drag locks it to one direction.
- In a Parallel view, right-drag and two fingers pan, as in Rhino.
- The horizon always stays level.
- Each gesture does one thing until it ends: a stray pinch inside a two-finger rotation is ignored.
- Strokes that end at speed come to rest smoothly instead of stopping dead.

**Compass.** It shows north. Click it for **Heading**, **Tilt** and **Sensitivity**, each with a slider and a typed value, plus **North up**. Drag it to turn and tilt; double-click it for north.

**Other controls.** **Fit** frames the visible sets. **− / +** zoom a step, or hold them to keep zooming. **Lens** (under Camera) is the lens length on a 35 mm camera: 12 to 200 mm on the slider, 6 to 1200 mm typed.

**Projections.** Perspective, Two-Point (verticals stay vertical, tilting up to 65°) and Parallel.

On a Mac, a Magic Mouse or smooth-scrolling mouse scrolls like the trackpad (it rotates). Choose **Scroll: Zooms** in the compass panel if you use one.

## 6. Walk and fly

Drag the person button onto the map and drop it where you want to stand, on the map or on your model. The view comes down to eye level.

| Key | Action |
| --- | --- |
| W A S D or arrows | Walk (4.4 m/s) |
| Double-tap W | Sprint (11.9 m/s) |
| Shift | Sneak (1.3 m/s) |
| Space | Jump |
| Double-tap Space | Fly (double-tap again to land); Space rises, Shift sinks |
| Two fingers or right-drag | Look around |
| Esc | Return to the previous view |

You are 1.80 m tall with eyes at 1.65 m. On foot, walls stop you, steps up to 45 cm are climbed and stairs are followed down. Flying passes through everything. Walking follows what is drawn: your model and the map, including any holes in the map's scan.

## 7. Views, sun and lights

**Named views.** **Save View** in the viewer and Rhino's Named Views are always the same: saving, updating, renaming or deleting a view on either side changes it on the other within a second. A view keeps its camera, projection, lens and sun time.

**Follow Rhino.** `EarthLinkSync > FollowViewport` makes the viewer follow Rhino's active viewport. Navigating in the viewer turns it off.

**Sun.** The sun panel sets sunlight, date, time and shadows. The map darkens toward evening and turns to night with stars. The map is a daytime photograph, so it is tinted, not relit, and shadows in its imagery stay. **Sync with Rhino** shares the sun's date, time and on/off state with Rhino's Sun. Time follows your computer's time zone.

**Lights.** Your Rhino lights (point, spot, directional, rectangular and linear) light the model and the map as Rhino's Rendered mode does. A change to a light in Rhino reaches the viewer within a second.

- A light belongs to the nearest design set: it moves with the set and is off while the set is hidden.
- The two brightest point lights or spotlights cast shadows.
- Up to 32 lights are drawn.
- **Lights** in the sun panel turns them off.

## 8. Display, section and measure

- **Materials** shows your Rhino render materials, lit to match Rhino's Rendered mode: colours, textures and their mapping, transparency and emission. There are no ray-traced reflections or refraction.
- **Clay** and **Ghost** are plain display styles. Each set can have its own.
- **Section cut** clips the model at a chosen height.
- **Measure**: click two points for the distance and height difference. Esc clears it. Map surfaces are approximate.

## 9. Surroundings to Rhino

Bring the area around your site into Rhino as geometry to model against.

1. Click the dashed square with an arrow (right-hand tools).
2. Click two opposite corners of a rectangle on the map (20 m to 3 km a side). With a mouse you can also drag it. Esc forgets the first corner.
3. Choose what to include, then press **Import**. The bar shows the progress and the time left.

The model must be placed first, because everything is positioned from the file's EarthAnchorPoint. The panel remembers your choices.

| Include | Settings |
| --- | --- |
| Terrain | |
| Contours | Interval (every fifth line on its own sublayer) |
| Buildings | **Default building height**, for buildings with no known height (7 m) |
| Roads, Paths | Geometry: any of **Centerlines**, **Outlines** and **Surfaces** |
| Railways, Water | |
| Parcels | (off until ticked) |

**Road geometry:**

- **Centerlines**: one line along each road.
- **Outlines**: the road edges, joined where roads meet, so a street grid becomes one outline with each block as a hole.
- **Surfaces**: one mesh per road layer.

Outlines and surfaces use each road's real width where it is recorded, otherwise the usual width for its kind (14 m for a motorway, 7 m for a residential street, 2 m for a footway). Bridges stay level.

Everything is added in place, in the file's units, on layer **EarthLink Context**, as one Undo step:

| Layer | Content |
| --- | --- |
| Terrain | One mesh of the ground (1 m cells up to 200 m a side, coarser beyond), passing through the map's ground at your site |
| Contours | Lines at round heights above sea level; every fifth on **Index** |
| Buildings | Solids standing on the terrain, with their recorded height (or 3.2 m a storey) |
| Buildings (height assumed) | Buildings with no known height, at the default height |
| Major roads | Motorways, trunk, primary and secondary roads |
| Minor roads | Other streets, service roads and tracks |
| Paths | Footways, paths, cycleways, steps |
| Railways | Rail, light rail, tram and subway lines |
| Water | Lakes, ponds and rivers as closed curves at the water level; streams as lines |
| Parcels | Lot lines on the ground, named with their address |

Each road layer has a sublayer per geometry you ticked, for example **Major roads::Outlines**. Each object's user text holds what the source records about it: names, use, storeys and width (`osm:` keys), or a lot's parcel number, municipality, property class and acreage (`parcel:` keys). Importing again adds another copy, so delete the old layer first to replace it.

**Sources.** Buildings, roads, railways and water are from OpenStreetMap (© OpenStreetMap contributors; credit them when you publish). Terrain comes from open elevation tiles. Parcels come from New York State's public tax parcels, which cover 38 counties and New York City (2026). Outside them, the import says no parcels were found. Owners' names are never fetched.

**Limits.** This is open data, not a survey. Terrain is roughly 10 m data in most places, so kerbs and retaining walls are not in it. Roofs are flat. Lot lines are as accurate as the county's tax map. The photorealistic map itself is never exported: its terms do not allow it.

## 10. Capture and share

**Capture** saves images of the current view or of **All Saved Views**.

| Pass | Result |
| --- | --- |
| Full | Model and map |
| Context only | The map without the model |
| Model · transparent | The model on a transparent background |

Choose a size, a detail level (Standard, High, Max) and whether to save to a folder (default `Pictures/EarthLink`) or be asked each time. Images carry their camera in the file. Check the map providers' attribution rules before publishing images.

**Share** (in Capture) writes a ZIP with a stand-alone viewer of the current sets and views. Put the unzipped folder on any web host. Visitors enter their own map key unless you include one; if you do, restrict it to that site. The ZIP holds your geometry and site location, so review it before sharing.

**Google Earth Pro (optional).** With `EarthPro=On` in `SendToEarth`, EarthLink also writes the set for Google Earth Pro and opens it there.

## 11. Your files and privacy

| What | Where |
| --- | --- |
| Settings, map key, views, exported models | Mac: `~/Library/Application Support/EarthLink/`<br>Windows: `%APPDATA%\EarthLink\` |
| Captures | `Pictures/EarthLink/` |
| Sets, placement, viewer state, site | In the Rhino file (Document User Text, section EarthLink) |

- The viewer's server listens only on your computer (`127.0.0.1:8765`). `EarthLinkSettings > StopViewerServer` stops it.
- Your model is never uploaded.
- The map is requested from Cesium or Google with your key.
- **Surroundings to Rhino** sends the rectangle's corners to OpenStreetMap, the elevation tiles' host and, if Parcels is ticked, New York State's parcel service. Nothing is sent before you press **Import**.
- **Send feedback** opens a filled-in GitHub issue or email for you to send yourself. Its system details contain no location.

**Reopening a file.** The Rhino file remembers its sets, their placement and display, the height offset, the sun, the lights switch and the last camera. Open it, run `EarthLinkViewer`, and the viewer is as you left it. Save the file to keep changes. A copy made with Save As becomes a project of its own and starts with the original's views.

## 12. Troubleshooting

| Problem | Try |
| --- | --- |
| No map | Check the key under **Site > Map connection** and your internet connection |
| Model missing | Check the set is visible, the geometry type is supported, and press **Fit** |
| Model floats or is buried | **Re-sample ground**, then adjust **Height offset** |
| Model faces the wrong way | Turn the set with **Edit**, or check north in `EarthAnchorPoint` |
| "Rhino is not reachable" | Run `EarthLinkViewer`; make sure Rhino is not busy and port 8765 is free |
| A Live set does not update | Check **Update when it changes in Rhino**; send the selection again if you added objects |
| Views or sun do not sync | Run `EarthLinkSync` for the file you are working on |
| Rhino lights do not show | The light must be on and its layer visible; display must be Materials; **Lights** on |
| Surroundings: OpenStreetMap not reached | Its servers may be busy: try again in a minute |
| Surroundings: all buildings 7 m | OpenStreetMap has no heights there; they are on **Buildings (height assumed)** |
| Google Earth Pro shows an old model | Send again with `EarthPro=On` |
