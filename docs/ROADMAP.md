# Roadmap

What is planned after 0.2.0-beta.11, most valuable first. Each item is small enough to ship by itself. The list comes from the author's requests and from an independent code review of beta.10 (2026-11-14).

## Next

| Item | Why |
| --- | --- |
| Shadows from more Rhino lights | Two point lights or spotlights cast shadows (beta.11); Rhino casts them from every point, spot and directional light, so a third lamp in a room still lights the ground outside the wall |
| Sun time in the site's time zone | The time slider uses the computer's time zone; a site in another zone shows the sun of the wrong hour |
| Copies of a file share one project | A file saved under a new name keeps the project id: both copies write the same views and sets. Give a copy its own id |
| One writer for `meta.json` | Rhino and the server both read, change and write it; a set deleted in the viewer during an export can come back |
| Live sets notice material and layer changes | The change signature covers geometry, not a material edited in place or a layer's material |
| Sign in with Cesium ion | One click instead of copying a token (OAuth with PKCE); needs EarthLink registered with Cesium and a check that ion accepts a redirect to the local viewer |
| The 3D engine bundled with the plugin | CesiumJS is loaded from a CDN: no internet or a firewall means a blank page. Bundle it and say so when it fails |
| A secret for the local server | Any program on the same computer can read the map token from the local server; hand the page a per-launch secret |
| Progress and Esc for sends and imports | A large send or a 3 km import blocks Rhino with no bar and no way out |
| Surroundings: roof shapes, road widths, water and green areas | OpenStreetMap has them; today buildings are flat-topped and roads are centre lines |

## Ideas

- A toolbar with the four commands, and a first-run guide.
- Capture: restore the camera and the sun after **All Saved Views**; warn when the map had not finished loading.
- "Solo next" instead of "Compare" for stepping through sets.
- Replace or add when SendToEarth is run on an existing set with another selection.
- Wheel zoom in equal steps per notch on every platform.
- A demo video and a short guide for the Cesium ion token (see the demo plan).

## Not planned

- Exporting Google's map to Rhino: its terms forbid it. **Surroundings to Rhino** uses open data instead.
- Removing the map credits: Google's and Cesium's terms require them.
