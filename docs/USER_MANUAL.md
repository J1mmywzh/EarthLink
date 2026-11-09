# EarthLink user manual

For EarthLink 0.2.0-beta.3, a preview for Rhino 8 (a PackageManager pre-release). The stable release is 0.1.1. Read the limitations below before relying on a result. Windows integration testing is pending.

## 1. What EarthLink does

EarthLink sends selected Rhino geometry to a browser viewer and places it using the Rhino file's EarthAnchorPoint. The viewer combines your design with Google Photorealistic 3D Tiles through CesiumJS. It can also export a live link for Google Earth Pro.

Rhino is the owner of the model. The browser is a viewing and coordination tool. Placing a design set in the viewer never changes Rhino geometry; the placement is stored with the set and applied on export. Removing a set removes its EarthLink association, not the source geometry.

## 2. Install

You need Rhino 8, an internet-connected browser for map context, and your own map-access credentials. Google Earth Pro is optional.

Run `PackageManager` in Rhino, search **EarthLink**, install it, and restart Rhino when convenient. For this beta, tick *Include pre-releases*. McNeel's Yak command-line tool supports `yak install /absolute/path/to/file.yak`; see the [official CLI reference](https://developer.rhino3d.com/guides/yak/yak-cli-reference/).

After loading the plugin, the commands are:

| Command | Purpose |
| --- | --- |
| `SendToEarth` | Select and send geometry; choose a design set and live behavior |
| `EarthLinkViewer` | Start the local server if needed and open the browser viewer |
| `EarthLinkSync` | Configure named views, follow viewport, and sun sync |
| `EarthLinkSettings` | Enter map credentials, manage sets, choose capture folder, or stop the viewer server |

If commands are missing, confirm the package is installed for the Rhino version you are running and that Rhino has been restarted since installation. Running scripts from the source tree is a development workflow and does not verify the installed package.

## 3. Connect the map

Open the viewer or run `EarthLinkSettings`. Enter either your Cesium ion access token or a Google Maps Platform API key with Map Tiles API access. The viewer prompts for credentials if none are configured. You can choose **Not Now** to work without photorealistic context.

EarthLink stores credentials in local application data, not in the Rhino model. The browser uses them to request the external map services. Do not paste credentials into public issues, source files, screenshots, or a shared viewer. Sharing with an embedded token is an explicit option; use an appropriately restricted token if you choose it.

## 4. Place your first model

1. Save your Rhino file and check its model units.
2. Select exportable geometry. Meshes, surfaces, polysurfaces, extrusions, SubDs, and blocks containing those objects are handled. Curves, annotations, and other unsupported object types do not become visible geometry.
3. Run `SendToEarth`. For a first send, use `Set=Main`, `Viewer=On`, `EarthPro=Off`. Choose `Live=On` if you want edits watched automatically.
4. If the file already has an EarthAnchorPoint, the model is sent at that anchor. Check the latitude, longitude, model base point, north, elevation, and elevation reference first.
5. If the file has no anchor, choose **PickOnMap**. Find the site, or type exact `latitude, longitude`, click the model's base-point location on the map, optionally rotate it, then choose **Apply to Rhino**. The selected design set is sent after Rhino applies the anchor.
6. Check orientation, scale, and height against a known reference. Use **Fit** to frame the design.

A new picked anchor uses GroundLevel at zero elevation. Editing an existing anchor preserves its elevation and reference. Clicking an elevated surface can pick a roof or tree; inspect the chosen height. **Re-sample** estimates ground around the model; use the height controls to inspect placement. The browser height adjustment changes viewer placement only; it does not write a new Rhino EarthAnchorPoint elevation.

For site edits later, use Rhino's `EarthAnchorPoint` command or the viewer's **Site → Edit**. Latitude, longitude, and rotation changes applied from the viewer reach Rhino, and anchor edits in Rhino trigger re-export while sync is active.

## 5. Design sets and live updates

A design set is a named selection of Rhino object IDs. Use separate sets for schemes, landscape, or other groups. To replace its selection, select the desired objects, run `SendToEarth`, and choose the same set name. Saving the Rhino file preserves the set associations and project ID.

- **Show/hide** changes a set's viewer visibility.
- **Compare** cycles through sets one at a time.
- **Edit → Name** renames the association in the viewer and Rhino.
- **Display** chooses Materials, Clay, or Ghost for that set; Default follows the overall display style.
- **Remove** forgets a set without deleting the Rhino geometry.
- **Live=On** watches the recorded objects and sends changes after a short delay, roughly one second while idle. New objects are not automatically added to the selection; send the desired selection again.

To place a set on the site: open **Edit**, drag it on the map or use the east/north/up nudges and rotation, check the preview, then choose **Apply**. The placement is an EarthLink-only transform saved with the set (in the file's Document User Text) and applied every time the set is sent, including Live updates, cutouts, walking and Earth Pro. Your Rhino geometry never moves: model on Rhino's own grid at 0,0 and the site placement follows. Moves add up; **Original position** removes the placement. Nudge distances are metres east/north/up regardless of Rhino model units. To move the whole site instead, edit the EarthAnchorPoint (Site → Edit).

## 6. Cameras, named views, and sun

Run `EarthLinkSync` and configure:

| Setting | Behavior |
| --- | --- |
| NamedViews | Two-way saved named views: create, update, rename, and delete |
| FollowViewport | Browser camera follows the synced Rhino document's active viewport |
| Sun | Viewer time and Rhino Sun date/time synchronize; the anchor supplies Rhino Sun location and north |

**FollowViewport is one-way.** Navigating the browser does not continuously drive Rhino's active viewport. A view saved in the browser can become a Rhino named view through named-view sync. Browser navigation automatically leaves Follow Rhino. Enable Follow again to resume it.

In **Views**, select a saved view to recall it, or use **Save View**. Browser-saved views include camera, projection/lens, and sun time. Perspective, Two-Point, and Parallel projections are supported. Two-Point keeps verticals vertical using lens shift. The Lens control displays a 35 mm equivalent. Two-Point uses Vertical framing; true top-down tilt is available in Perspective and Parallel.

On first named-view reconciliation, Rhino wins conflicting cameras with the same name. Afterwards, the changed side wins; simultaneous conflicting edits favor Rhino. Because deletes also synchronize, avoid editing the same named view independently in both apps at once.

The Sun panel controls sunlight, date, all 24 hours, and dynamic shadows. Sunlight off uses neutral illumination and hides date/time controls. Sync with Rhino exchanges both the enabled state and UTC time; Rhino is authoritative when connecting or reconnecting. The browser computer's per-date time-zone offset is sent to Rhino. This is not an independent site-time-zone scheduler. Photographed shadows in Google's textures cannot be removed by disabling dynamic sunlight.

When switching Rhino documents, run SendToEarth or EarthLinkViewer/Sync for the file you intend to link. One local viewer/exchange area is active at a time. Keep Rhino open and responsive for two-way requests.

## Search, navigation and walking

**Search** (top left) works like Google Earth: Google suggestions refine as you type, recent searches appear first, and names drop postcodes and "USA" ("180 Cayuga Park Lane, Ithaca, NY"). Enter or a click flies there; exact `lat, lon` also works, and while placing a site it sets the picked point. With the field empty, the first result flies to your site. Recent searches stay in this browser only.

**Navigation follows Rhino 8 for Mac.** In Perspective and Two-Point: two fingers or right-drag orbit about the point at the centre of the view; Shift + either pans, with the ground following your fingers; pinch, the wheel or Ctrl + right-drag zoom toward the cursor (toward the centre at globe scale). In Parallel: two fingers or right-drag pan, with or without Shift; pinch or the wheel zoom; rotate with the Tilt/Heading sliders. Trackpad and mouse are recognized automatically, per gesture.

The horizon never rolls. A gesture keeps one mode until it ends, including momentum after your fingers lift, so releasing Shift early cannot turn a pan into an orbit. Motion is eased per frame. Pan moves the ground exactly under your fingers and zoom is proportional to distance, so the same Sensitivity works from orbit to a room. The camera is kept above Google's surface. Parallel cameras sit far back along their axis so nothing near the camera is cut away.

The compass shows north; it opens **Tilt** (Two-Point: **Vertical framing**), **Heading**, **Sensitivity** (one value for orbit, pan, zoom and look) and **Reset to north**. **Fit** frames visible sets, keeping your heading. Click − / + for a smooth step or hold them to zoom continuously.

**Walk:** select the person button and click where to stand, on your model or on the map, with or without a model. WASD/arrows walk at 3.5 m/s, Shift sprints at 9.5 m/s, Space jumps, two fingers or right-drag look, Esc or the person button returns to the previous camera and projection. You are 1.80 m tall with eyes at 1.65 m. Walls and ceilings stop you and you slide along them; steps up to 0.45 m are climbed and stairs are followed down; you fall from edges. These are navigation parameters, not building-code criteria.

Collisions use what is drawn: your exported model mesh (both face sides) and the loaded Google tiles, tested on the CPU each frame. Nothing is extracted or stored from Google's data. Where the map has not loaded yet you hold your position. Inside **Hide map under model** cutouts the map is ignored, so include a floor or site surface. Section cuts disable Walk; changing geometry, visibility or projection exits it.

## 7. Display and measurement

- **Materials**, **Clay**, and **Ghost** change viewer appearance without changing Rhino materials.
- **Section cut** clips the displayed model at a chosen local height.
- **Hide map under model** clips all Google geometry within the union of visible uploaded geometry projected horizontally. Concave outlines, disconnected pieces, and uncovered courtyard holes are preserved. Ground is removed too. Resend legacy sets after upgrading; no bounding rectangle is used as fallback. Coverage follows the exported render mesh within its meshing and raster precision.
- **Measure** picks two visible surface points and reports distance in metres and feet/inches plus height difference. Press Esc to clear. Photorealistic mesh picking is approximate and is not a survey measurement.

## 8. Capture images

Open **Capture**, choose a preset or custom pixel size, and select one or more passes:

| Pass | Result |
| --- | --- |
| Full | Visible model and context |
| Context only | Context with the design hidden |
| Model · transparent | Design on a transparent background |

Choose Standard/High/Max detail and a default folder or **Ask each time**. **Capture** uses the current view; **All Saved Views** captures the selected passes for each stored view. Camera data is embedded in PNG files; default-folder captures also get a camera JSON sidecar. Context imagery, map logos, and attribution require checking before public reuse; the capture feature is not a usage-rights clearance.

The default capture folder is `Pictures/EarthLink`. Chrome/Edge can offer file or folder pickers; Safari/Firefox may use browser downloads when Ask each time is selected. Large output is limited by the browser/GPU renderbuffer size. Keep FollowViewport off during a deliberate independent capture. For compositing, match the saved camera and output dimensions in Rhino and compare a test overlay before a full batch.

## 9. Share a viewer

Use **Capture → Share…** to write a ZIP containing the viewer, current models, views, and settings. Choose whether to include a map token. Without one, visitors enter their own credentials. The ZIP is a static viewer snapshot: it has no live connection back to your Rhino document.

Extract and serve it on a static web host, or follow its README to start a local web server. Opening the HTML directly from disk is not supported. The package contains your selected geometry and anchor coordinates, so review those before sharing. This export does not bundle Google's tile dataset for offline use.

## 10. Google Earth Pro

Install Google Earth Pro separately. Choose `EarthPro=On` in SendToEarth or change the default in EarthLinkSettings. EarthLink converts the GLB to COLLADA and writes a local KML network link. The application is opened when the link is first sent in that Rhino session.

The browser is the primary viewer. Earth Pro support is optional. In this preview, browser-only updates can delete an older Earth Pro conversion during version cleanup. Re-send with EarthPro enabled to refresh the conversion and its textures.

## 11. Local files and privacy

| Data | macOS | Windows |
| --- | --- | --- |
| Settings, views, exchange files | `~/Library/Application Support/EarthLink/` | `%APPDATA%/EarthLink/` |
| Default captures | `~/Pictures/EarthLink/` | User's `Pictures/EarthLink/` |
| Per-file project/set associations | Rhino Document User Text, section EarthLink | Same |

The server binds to `127.0.0.1:8765` by default; it is not a public hosting service. **StopViewerServer** stops that server. Close the browser tab separately. Credentials and exported model files persist locally until you remove them; stopping the server does not erase them.

## 12. Troubleshooting and limitations

| Symptom | Check or workaround |
| --- | --- |
| Map missing | Check credentials, network access, and service access; Not Now skips tiles |
| Model missing | Check set visibility, supported geometry, units, anchor, and Fit; read Rhino command output |
| Model floats or is buried | Check anchor reference/elevation; Re-sample for each new site; inspect surface picked on the map |
| Wrong orientation | Check EarthAnchorPoint model north and base point; use Edit Location's rotation |
| Browser says Rhino not reachable | Run EarthLinkViewer; check Rhino is responsive and port 8765 is not occupied by another app |
| Live set does not change | Check Live is on, objects are still in the recorded set, and Rhino is idle; send selection again |
| Deleted all objects but old model remains | Remove that empty set in the viewer; automatic empty-set export is a known issue |
| Named views or sun do not sync | Check the relevant toggle and linked document; restart sync with EarthLinkSync if it paused after errors |
| Earth Pro model disappears | Re-send with EarthPro enabled to regenerate its retained files |
| Commands work from source only | Verify the installed package separately; source execution is not an installed-plugin check |

The stable 0.1.1 release retains the author-tested 0.1.0 runtime. This preview adds unit, API and browser tests and was checked on a Mac GPU over Google's tiles; Windows integration remains a separate check. Scanned context is not survey data; walking on the map follows Google's mesh, including its holes and roughness.

## 13. For an agent assisting a user

Read [AGENT_GUIDE.md](AGENT_GUIDE.md) before operating or changing EarthLink. Establish the user's intended document, selection, set, and site before exporting. A source review, build, local installation, external map request, model move, or public upload are different actions. Use the authorization provided for the actual task; ask when a necessary location or intended change is missing. Use disposable fixture data for tests and never overwrite the user's runtime folder with test fixtures.
