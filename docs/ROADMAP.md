# Roadmap

What comes after 1.0, most useful first. Each item can ship on its own.

## Next

| Item | Why |
| --- | --- |
| Bundle the 3D engine | The viewer loads CesiumJS from the internet; behind a firewall the page stays blank |
| Shadows from every Rhino light | Only the two brightest point lights or spotlights cast shadows today |
| Sun time in the site's time zone | The time follows the computer's time zone, which is wrong for a site in another zone |
| Progress and cancel for large sends | A large export blocks Rhino with no progress bar |
| Parcels beyond New York State | Parcel data is published county by county; add more public sources |
| Roof shapes for imported buildings | OpenStreetMap records many roof shapes; imported buildings are flat-topped |
| One-click map sign-in | Sign in to Cesium ion instead of copying a token |
| A per-launch secret for the local server | Other programs on the same computer can read the map key from it |
| One writer for `meta.json` | Rhino and the server both write it; a set removed during an export can come back |

## Ideas

- A toolbar for the four commands and a first-run guide.
- Restore the camera and sun after capturing all saved views; warn when the map had not finished loading.
- Step through sets one at a time ("solo next").
- Parks and green areas in **Surroundings to Rhino**.

## Not planned

- Exporting the photorealistic map to Rhino: its terms do not allow it. **Surroundings to Rhino** uses open data instead.
- Removing the map credits: the providers' terms require them.
