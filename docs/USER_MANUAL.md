# EarthLink user manual

For EarthLink 0.1.0, an initial preview for Rhino 8. Read the preview limitations below before relying on a result. Windows integration testing is pending.

## 1. What EarthLink does

EarthLink sends selected Rhino geometry to a browser viewer and places it using the Rhino file's EarthAnchorPoint. The viewer combines your design with Google Photorealistic 3D Tiles through CesiumJS. It can also export a live link for Google Earth Pro.

Rhino is the owner of the model. The browser is a viewing and coordination tool. A design-set move only changes Rhino geometry when you choose **Apply to Rhino**. Removing a set removes its EarthLink association, not the source geometry.

## 2. Install

You need Rhino 8, an internet-connected browser for map context, and your own map-access credentials. Google Earth Pro is optional.

After the package is published to Yak: run `PackageManager` in Rhino, search **EarthLink**, install it, and restart Rhino when convenient. While it is unpublished, obtain the `.yak` file from the project's release download and install that local package. McNeel's Yak command-line tool supports `yak install /absolute/path/to/file.yak`; see the [official CLI reference](https://developer.rhino3d.com/guides/yak/yak-cli-reference/).

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
6. Check orientation, scale, and height against a known reference. Use **Go to model** to frame the design.

A new picked anchor uses GroundLevel at zero elevation. Editing an existing anchor preserves its elevation and reference. Clicking an elevated surface can pick a roof or tree; inspect the chosen height. **Re-sample** estimates ground around the model; use the height controls to inspect placement. The browser height adjustment changes viewer placement only; it does not write a new Rhino EarthAnchorPoint elevation.

For site edits later, use Rhino's `EarthAnchorPoint` command or the viewer's **Site → Edit Location**. Latitude, longitude, and rotation changes applied from the viewer reach Rhino, and anchor edits in Rhino trigger re-export while sync is active.

## 5. Design sets and live updates

A design set is a named selection of Rhino object IDs. Use separate sets for schemes, landscape, or other groups. To replace its selection, select the desired objects, run `SendToEarth`, and choose the same set name. Saving the Rhino file preserves the set associations and project ID.

- **Show/hide** changes a set's viewer visibility.
- **Compare** cycles through sets one at a time.
- **Edit → Name** renames the association in the viewer and Rhino.
- **Display** chooses Materials, Clay, or Ghost for that set; Default follows the overall display style.
- **Remove** forgets a set without deleting the Rhino geometry.
- **Live=On** watches the recorded objects and sends changes after a short delay, roughly one second while idle. New objects are not automatically added to the selection; send the desired selection again.

To move a set: open **Edit**, use map dragging or east/north/up nudges and rotation, inspect the preview, then choose **Apply to Rhino**. Nudge distances are metres in the east/north/up frame regardless of Rhino model units. A move is recorded as one Rhino undo operation. Use Rhino's **Edit → Undo** to reverse it. Keep sync active so the viewer receives Undo/Redo updates.

## 6. Cameras, named views, and sun

Run `EarthLinkSync` and configure:

| Setting | Behavior |
| --- | --- |
| NamedViews | Two-way saved named views: create, update, rename, and delete |
| FollowViewport | Browser camera follows the synced Rhino document's active viewport |
| Sun | Viewer time and Rhino Sun date/time synchronize; the anchor supplies Rhino Sun location and north |

**FollowViewport is one-way.** Navigating the browser does not continuously drive Rhino's active viewport. A view saved in the browser can become a Rhino named view through named-view sync. For free browser navigation, turn Follow Rhino viewport off.

In **Views**, select a saved view to recall it, or use **Save View**. Browser-saved views include camera, projection/lens, and sun time. Perspective, Two-Point, and Parallel projections are supported. Two-Point keeps verticals vertical using lens shift. The lens control reports a vertical field of view and a 35 mm equivalent.

On first named-view reconciliation, Rhino wins conflicting cameras with the same name. Afterwards, the changed side wins; simultaneous conflicting edits favor Rhino. Because deletes also synchronize, avoid editing the same named view independently in both apps at once.

The viewer clock uses the browser computer's local time zone. For the selected date, its time-zone offset is sent to Rhino. The current time slider covers 05:00–21:00. Full nighttime times and differing computer/site time zones need care; this preview is not an unrestricted site-time-zone sun scheduler.

When switching Rhino documents, run SendToEarth or EarthLinkViewer/Sync for the file you intend to link. One local viewer/exchange area is active at a time. Keep Rhino open and responsive for two-way requests.

## 7. Display and measurement

- **Materials**, **Clay**, and **Ghost** change viewer appearance without changing Rhino materials.
- **Section cut** clips the displayed model at a chosen local height.
- **Hide existing buildings in the footprint** clips map context within the visible sets' bounding footprints, not exact building outlines.
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
| Model missing | Check set visibility, supported geometry, units, anchor, and Go to model; read Rhino command output |
| Model floats or is buried | Check anchor reference/elevation; Re-sample for each new site; inspect surface picked on the map |
| Wrong orientation | Check EarthAnchorPoint model north and base point; use Edit Location's rotation |
| Browser says Rhino not reachable | Run EarthLinkViewer; check Rhino is responsive and port 8765 is not occupied by another app |
| Live set does not change | Check Live is on, objects are still in the recorded set, and Rhino is idle; send selection again |
| Deleted all objects but old model remains | Remove that empty set in the viewer; automatic empty-set export is a known issue |
| Named views or sun do not sync | Check the relevant toggle and linked document; restart sync with EarthLinkSync if it paused after errors |
| Earth Pro model disappears | Re-send with EarthPro enabled to regenerate its retained files |
| Commands work from source only | Verify the installed package separately; source execution is not an installed-plugin check |

The development handover reported extensive macOS integration tests for internal 0.2.0. Initial public 0.1.0 uses the same runtime implementation, with updated release metadata/docs. Installed 0.1.0, Windows, and full current end-to-end validation remain pending. No claim of map accuracy, survey accuracy, or production readiness is made by the initial-preview label.

## 13. For an agent assisting a user

Read [AGENT_GUIDE.md](AGENT_GUIDE.md) before operating or changing EarthLink. Establish the user's intended document, selection, set, and site before exporting. A source review, build, local installation, external map request, model move, or public upload are different actions. Use the authorization provided for the actual task; ask when a necessary location or intended change is missing. Use disposable fixture data for tests and never overwrite the user's runtime folder with test fixtures.
