# EarthLink user manual

For EarthLink 0.2.0-beta.10, a preview for Rhino 8 (a PackageManager pre-release). The stable release is 0.1.1. Read the limitations below before relying on a result. Windows integration testing is pending.

## 1. What EarthLink does

EarthLink sends selected Rhino geometry to a browser viewer and places it using the Rhino file's EarthAnchorPoint. The viewer combines your design with Google Photorealistic 3D Tiles through CesiumJS. It can also export a live link for Google Earth Pro.

Rhino is the owner of the model. The browser is a viewing and coordination tool. Placing a design set in the viewer never changes Rhino geometry; the placement is two numbers (a rotation and an offset) stored with the set and applied by the viewer on top of the exported geometry. Removing a set removes its EarthLink association, not the source geometry.

## 2. Install

You need Rhino 8, an internet-connected browser for map context, and your own map-access credentials. Google Earth Pro is optional.

Run `PackageManager` in Rhino, search **EarthLink**, install it, and restart Rhino when convenient. For this beta, tick *Include pre-releases*. McNeel's Yak command-line tool supports `yak install /absolute/path/to/file.yak`; see the [official CLI reference](https://developer.rhino3d.com/guides/yak/yak-cli-reference/).

After loading the plugin, the commands are:

| Command | Purpose |
| --- | --- |
| `SendToEarth` | Select and send geometry; choose a design set and live behavior |
| `EarthLinkViewer` | Start the local server if needed and open the browser viewer |
| `EarthLinkSync` | Configure follow viewport and sun sync (named views are always shared) |
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
5. If the file has no anchor, choose **PickOnMap**. Find the site, or type exact `latitude, longitude`, click where the model should stand, then choose **Apply to Rhino**. The bottom centre of what you sent is put on that spot, wherever the geometry is in the Rhino file: it becomes the EarthAnchorPoint's model base point (a base point you already set there is kept, and later sends and site moves do not change it). The model is shown at the new site at once and stays there while Rhino takes it over. The site does not rotate the model: Rhino's north (EarthAnchorPoint) is left as it is; turn a set with **Edit**. The selected design set is sent after Rhino applies the anchor.
6. Check orientation, scale, and height against a known reference. Use **Fit** to frame the design.

A new picked anchor uses GroundLevel at zero elevation. Editing an existing anchor preserves its elevation and reference. Clicking an elevated surface can pick a roof or tree; inspect the chosen height. **Height offset** (metres, in **Site**) raises or lowers the whole model. **Re-sample ground** estimates ground around the model; use the height controls to inspect placement. The browser height adjustment changes viewer placement only; it does not write a new Rhino EarthAnchorPoint elevation.

For site edits later, use Rhino's `EarthAnchorPoint` command or the viewer's **Site → Edit**. Latitude, longitude, and rotation changes applied from the viewer reach Rhino, and anchor edits in Rhino trigger re-export while sync is active.

## 5. Design sets and live updates

A design set is a named selection of Rhino object IDs. Use separate sets for schemes, landscape, or other groups. To replace its selection, select the desired objects, run `SendToEarth`, and choose the same set name. Saving the Rhino file preserves the set associations and project ID.

- **Show/hide** changes a set's viewer visibility.
- **Compare** cycles through sets one at a time.
- **Edit → Name** renames the association in the viewer and Rhino.
- **Display** chooses Materials, Clay, or Ghost for that set; Default follows the overall display style.
- **Remove** forgets a set without deleting the Rhino geometry.
- **Live=On** watches the recorded objects and sends changes after a short delay, roughly one second while idle. New objects are not automatically added to the selection; send the desired selection again.

To place a set on the site: select the set's name to open **Edit**, then drag it on the map (**Move on map**: left button; navigation stays on the right button and the trackpad), type the East / North / Up offset in metres, or rotate it with the slider or an exact angle; rotation turns the set about the centre of its base. **Update when it changes in Rhino** is SendToEarth's Live option for that set, and **Update now** makes Rhino send the set again. Every change shows immediately and is saved automatically: the viewer applies the placement itself, so nothing is exported again and there is no Apply step. The card shows how far the base centre is from its Rhino position and the total rotation. The placement is an EarthLink-only layer kept with the set in the .3dm (Rhino's Undo restores it); the Rhino geometry and its grid never move. **Original position** returns the set to where it is in Rhino. While a set is being moved, **Hide map underneath** pauses and comes back when you stop. Dragging needs a view that looks down at the site: near the horizon a pixel is kilometres, so the drag does not start there. Changing only the site location, or a placement, exports no geometry; sets sent by versions before 0.2.0-beta.9 are sent once more automatically.

## 6. Cameras, named views, and sun

Run `EarthLinkSync` and configure:

| Setting | Behavior |
| --- | --- |
| FollowViewport | Browser camera follows the synced Rhino document's active viewport |
| Sun | Viewer time and Rhino Sun date/time synchronize; the anchor supplies Rhino Sun location and north |

**FollowViewport is one-way.** Navigating the browser does not continuously drive Rhino's active viewport. A view saved in the browser is a Rhino named view at once. Browser navigation automatically leaves Follow Rhino. Enable Follow again to resume it.

In **Views**, select a saved view to recall it, or use **Save View**. Named views are always the same in Rhino and the viewer: saving, updating, renaming or deleting one in either app changes it in the other within about a second (there is no switch for this). Browser-saved views include camera, projection/lens, and sun time. Perspective, Two-Point, and Parallel projections are supported. Two-Point keeps verticals vertical using lens shift, up to 65° of tilt. The Lens control displays a 35 mm equivalent; true top-down views are available in Perspective and Parallel.

On first named-view reconciliation, Rhino wins conflicting cameras with the same name. Afterwards, the changed side wins; simultaneous conflicting edits favor Rhino. Because deletes also synchronize, avoid editing the same named view independently in both apps at once.

The Sun panel controls sunlight, date, all 24 hours, and dynamic shadows. The map is a daytime photograph, so the time of day tints it: warm with the sun under about 12°, dark blue once it is 8° under the horizon, with stars and a dim moonlight on your model, which takes the same tint; emissive materials keep glowing. Cast shadows fade out as the sun comes down to the horizon (a sun on the horizon would streak the whole map). By day the sky overhead is blue with no stars. Sunlight off uses neutral illumination and hides date/time controls. Sync with Rhino exchanges both the enabled state and UTC time; Rhino is authoritative when connecting or reconnecting. The browser computer's per-date time-zone offset is sent to Rhino. This is not an independent site-time-zone scheduler. Photographed shadows in Google's textures cannot be removed by disabling dynamic sunlight.

**Lights.** The lights of the Rhino model (point, spot, directional, rectangular and linear, switched on and visible) are drawn as Rhino 8's Rendered mode draws them, measured there on a white matte plane: colour x intensity x the cosine of the angle to the surface; the fall-off set in Rhino (Constant by default: none; Linear and Inverse squared are taken in model units, as Rhino takes them, so they are dark beyond a few units); a spotlight cut off at its cone and fading from its axis as cos^exponent (its hot spot); a rectangular or a linear light acting as a point light at its centre. They light the model and the map. A change to a light in Rhino reaches the viewer within about a second without a resend. A light belongs to the design set nearest to it: it moves and turns with that set's placement and is dark while the set is hidden. Turn them off with **Lights** in the Sun panel (shown when the model has lights). Limits: no shadows from these lights yet (in Rhino, point, spot and directional lights cast them); up to 32 lights; on the map a light without fall-off fades between one and two times the size of its set (at least 12 m); Clay display does not show them; the sun and the skylight are not Rhino lights here, they follow the viewer's time of day.

When switching Rhino documents, run SendToEarth or EarthLinkViewer/Sync for the file you intend to link. One local viewer/exchange area is active at a time. Keep Rhino open and responsive for two-way requests.

## Search, navigation and walking

**Search** (top left) works like Google Earth: Google suggestions refine as you type, recent searches appear first, and names drop postcodes and "USA" ("180 Cayuga Park Lane, Ithaca, NY"). Enter or a click flies there; exact `lat, lon` also works, and while placing a site it sets the picked point. With the field empty, the first result flies to your site. Recent searches stay in this browser only.

**Navigation follows Rhino 8's defaults** (McNeel's Rhino 8 help and Mac user guide), including their Mac/Windows differences; Mod is ⌘ on a Mac and Ctrl on Windows, Alt is Option on a Mac. Mouse, both platforms: right-drag rotates (pans in Parallel); Shift + right-drag pans (pressing Shift during a drag locks it to one direction); Mod + right-drag zooms (drag up = in); Alt + right-drag dollies; Mod + Shift + right-drag rotates even a Parallel view; Mod + Alt + right-drag turns the camera where it stands; Mod + Shift + Alt + right-drag changes the lens; the wheel zooms toward the cursor (toward the centre at globe scale); middle-drag pans (Option + middle rotates on a Mac, Alt + middle dollies on Windows). Mac trackpad: two fingers rotate (pan in Parallel), Shift + two fingers pan, pinch zooms. Windows touchpad: two-finger scrolling and pinch zoom, as in Rhino for Windows; rotate and pan with the touchpad's right-drag. Keys: arrows rotate (pan in Parallel), Shift + arrows pan, Page Up / Page Down zoom, Shift + Page Up / Page Down change the lens. The platform is detected from the browser; add `?controls=mac` or `?controls=windows` to the viewer address to choose. Rhino's roll (Shift + Alt + right-drag) is not used.

The pivot is what is at the centre of the view when you start turning, like Rhino's camera target. It stays the same from one rotation to the next until you pan, zoom or fly, so a tree passing in front of the centre does not move it; at the horizon or in the sky it is your model's depth when the model is in view, or a limited distance. Tilt runs from straight down to straight up, so you can look up at a facade from the street. Two-Point is the same camera drawn with a level axis and a shifted lens: every gesture works as in Perspective, and the tilt stops at 65°. The camera passes through trees and buildings; it rests only on a surface it descends onto from above, follows ground that rises no faster than the camera moves, and cannot sink further while inside something solid. No other rule moves the camera (Cesium's own camera collision is off). A Magic Mouse cannot be told from a trackpad by a web page, so on a Mac its swipe rotates; a wheel mouse zooms, and a device guessed wrong from its first event is corrected by the next ones. The horizon never rolls. A gesture does one thing until it ends: releasing Shift early cannot turn a pan into an orbit, and a pinch that macOS reports in the middle of a two-finger rotation (fingers drifting apart) is ignored unless it takes over for more than a tenth of a second. The glide macOS adds after your fingers lift is faded out, so a flick does not keep turning the view. Motion is eased per frame. Pan moves the ground under your fingers and zoom is proportional to distance, so the same Sensitivity works from orbit to a room. Parallel cameras sit far back along their axis so nothing near the camera is cut away.

The compass shows north. Click it for a small panel with **Heading**, **Tilt** and **Sensitivity** (sliders and typed values) and **North up**; drag the compass sideways to turn and up or down to tilt; double-click it for north. **Fit** frames visible sets, keeping your heading. Click − / + for a smooth step or hold them to zoom continuously. Lens length (Camera) is in millimetres as on a 35 mm camera: 12 to 200 mm on the slider, 6 to 1200 mm typed.

**Walk:** drag the person button onto the map and drop it where to stand, as in Google Maps (or select it and click a spot), on your model or on the map, with or without a model; the view flies down to eye level. Minecraft controls: W A S D or arrows walk at 4.4 m/s; double-tap W (on a Mac, also Control) sprints at 11.9 m/s until you stop; Shift sneaks at 1.3 m/s; Space jumps. Double-tap Space to fly as in Minecraft creative mode: no gravity and no collision (you pass through buildings, trees, your model and the ground), Space rises and Shift sinks at 9.4 m/s, W A S D fly at 13.6 m/s (sprint 27 m/s) with a short glide, and double-tapping Space again drops you onto the ground below, or onto the surface above if you are under the map. Two fingers or right-drag look; Esc or the person button returns to the previous camera and projection. You are 1.80 m tall with eyes at 1.65 m. On foot, walls and ceilings stop you and you slide along them; steps up to 0.45 m are climbed and stairs are followed down; you fall from edges. These are navigation parameters, not building-code criteria. On Windows, Control does not sprint, because Ctrl + W closes the browser tab.

Collisions use what is drawn: your exported model mesh (both face sides) and the loaded Google tiles, tested on the CPU each frame. Nothing is extracted or stored from Google's data. Where the map has not loaded yet you hold your position. Rays follow what **Hide map underneath** does to the map: around a cut set you stand on the graded ground, and inside its base at the base's level. Section cuts disable Walk; changing geometry, visibility or projection exits it.

## 7. Display and measurement

- **Materials**, **Clay**, and **Ghost** change viewer appearance without changing Rhino materials. **Materials** shows your Rhino render materials, lit to match Rhino 8's Rendered mode: on the same colour swatches under the same sun, a sunlit white is white, a face turned from the sun keeps about 0.87 of its colour and a cast shadow about 0.68, within a few percent of Rhino. What carries over: colours, image textures and Rhino's procedural textures (baked by Rhino), with the object's box, planar or other texture mapping; glass, polycarbonate and any transparent material (see-through, as transparent as the material says); emission; an object with no material is white, as in Rendered mode. What a real-time viewer cannot do: ray-traced reflections and refraction (glass does not bend light, and a polished metal has no studio to reflect, so it is drawn mostly as its own colour with a sheen), displacement, and decals. Sets sent by an earlier version are sent once more automatically.
- **Section cut** clips the displayed model at a chosen local height.
- **Hide map underneath** is chosen per design set (the dashed square beside its eye in **Design Sets**). It removes Google geometry only under the set's base: every triangle is cut 1 cm above the set's lowest point and the part below is projected to plan, so overhangs, cantilevers and sets that widen upward keep the map under them. Concave outlines, disconnected pieces and courtyard holes are preserved, and ground is removed too. Resend legacy sets after upgrading; no bounding rectangle is used as fallback. Gaps under 1 m² are covered. Older settings with one switch for all sets carry over as on for every set. The map itself is reshaped as it is drawn: inside the base it is not drawn, and within 3 m around it the map's own ground is graded to the base's level, so its own pixels meet the model with no gap, no separate patch and nothing photographed (earlier previews moved the camera for an instant to photograph the ground, which showed as a jump and as white patches). Trees, buildings and slopes more than about 4 m above or below the base keep their height, fading in up to 8 m. All cut sets share one mask (20 pixels per metre up to about 100 m across, coarser beyond; sets more than about 400 m apart get a visibly coarser edge). The grading is a presentation fill, not survey data. If a graphics driver cannot draw the map this way, the viewer reloads once without it and says the cut-out is unavailable.
- **Measure** picks two visible surface points and reports distance in metres and feet/inches plus height difference. Press Esc to clear. Photorealistic mesh picking is approximate and is not a survey measurement.

## Surroundings to Rhino

The **Surroundings to Rhino** tool imports terrain, building massing and road centre lines for a rectangle you drag on the map (20 m to 3 km a side). Rhino must be running with this file linked; the model must be placed (SendToEarth) first, because the import is positioned from the EarthAnchorPoint.

| Layer | Content |
| --- | --- |
| EarthLink Context::Terrain | One mesh; 1 m cells up to 200 m a side, then at most 200 cells along the longer side. Its height at the site equals the map's ground there |
| EarthLink Context::Buildings | Closed solids with a height from OpenStreetMap (`height`, or `building:levels` x 3.2 m) |
| EarthLink Context::Buildings (height assumed) | Buildings OpenStreetMap gives no height for: 7 m |
| EarthLink Context::Roads | Centre lines on the terrain, cut at the rectangle; the name and the `highway` kind are in the object's name and user text |

Everything is in the file's units, in place, grouped, and one Undo removes it. Each object's user text records its source; the attribution is on the parent layer. Importing again adds another copy: delete the old layer first if you want to replace it.

Sources and privacy: buildings and roads come from OpenStreetMap (its own map download, the one openstreetmap.org's Export uses; the public Overpass servers if that fails), terrain from Terrain Tiles on AWS Open Data. The rectangle's corner coordinates are sent to those services when you press Import, from your computer; EarthLink has no server. Google's map is never exported: its terms forbid it. Credit "© OpenStreetMap contributors" when you publish drawings made from it.

Limits: a preview of open data, not a survey. Terrain is about 10 m data in much of the world (finer in parts of the US), so kerbs and retaining walls are not in it. Roofs are flat. A very crowded 3 km square is downloaded in up to 16 parts and can take a minute.

## Feedback

**Send feedback** collects a comment, an optional screenshot and system details and hands them to GitHub (a filled-in issue at github.com/J1mmywzh/EarthLink) or to your mail app (to rhinoearthlink@gmail.com). You see exactly what will be shared and nothing leaves the computer until you submit the issue or send the email. The screenshot shows your site and model; the system details hold no location. Your draft is kept if you close the card.

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

## Reopening a file

The Rhino file keeps what the viewer shows for it (Document User Text, section EarthLink): project identity, sets and their placement, and the viewer's state for this file: each set's display and cut-out, hidden sets, the height offset and ground sample, the sun's date, time and switches, the lights switch, and the last camera and lens. Named views are Rhino named views. Open the file, run **EarthLinkViewer**: its sets are exported again and the viewer returns to that state. The state is written to the file a few seconds after it changes, which marks the file as modified; save the file to keep it.

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
| Wrong orientation | Check EarthAnchorPoint model north and base point; turn a set with **Edit** on the set |
| Browser says Rhino not reachable | Run EarthLinkViewer; check Rhino is responsive and port 8765 is not occupied by another app |
| Live set does not change | Check Live is on, objects are still in the recorded set, and Rhino is idle; send selection again |
| Deleted all objects but old model remains | Remove that empty set in the viewer; automatic empty-set export is a known issue |
| Named views or sun do not sync | Named views are always shared; for the sun check its **Sync with Rhino** switch. Check the linked document, and restart sync with EarthLinkSync if it paused after errors |
| Lights from Rhino do not show | Check the light is on and its layer visible, **Lights** is on in the Sun panel, and the display is Materials; a Linear or Inverse squared fall-off in a millimetre file is dark, as in Rhino |
| Surroundings import says OpenStreetMap could not be reached | Its servers are busy or blocked on your network: try again in a minute. Terrain alone still imports |
| Imported buildings are all 7 m | OpenStreetMap has no heights there; they are on **Buildings (height assumed)** for you to adjust |
| Earth Pro model disappears | Re-send with EarthPro enabled to regenerate its retained files |
| Commands work from source only | Verify the installed package separately; source execution is not an installed-plugin check |

The stable 0.1.1 release retains the author-tested 0.1.0 runtime. This preview adds unit, API and browser tests and was checked on a Mac GPU over Google's tiles; Windows integration remains a separate check. Scanned context is not survey data; walking on the map follows Google's mesh, including its holes and roughness.

## 13. For an agent assisting a user

Read [AGENT_GUIDE.md](AGENT_GUIDE.md) before operating or changing EarthLink. Establish the user's intended document, selection, set, and site before exporting. A source review, build, local installation, external map request, model move, or public upload are different actions. Use the authorization provided for the actual task; ask when a necessary location or intended change is missing. Use disposable fixture data for tests and never overwrite the user's runtime folder with test fixtures.
