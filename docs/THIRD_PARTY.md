# Third-party services and licenses

EarthLink's own code is MIT licensed (see `LICENSE`). That license covers no third-party software, map content, accounts or trademarks.

| Used for | Source | Terms |
| --- | --- | --- |
| 3D engine | CesiumJS 1.140, loaded from a CDN | [License and notices](https://github.com/CesiumGS/cesium/blob/1.140/LICENSE.md) |
| Photorealistic map | Google Photorealistic 3D Tiles, through your own Cesium ion token or Google Maps Platform key | [Map Tiles API policies](https://developers.google.com/maps/documentation/tile/policies) and your account's terms |
| Buildings, roads, railways, water | OpenStreetMap: its map download, or public Overpass servers as a fallback | © OpenStreetMap contributors, [Open Database License](https://www.openstreetmap.org/copyright); [API usage policy](https://operations.osmfoundation.org/policies/api/) |
| Terrain and contours | Terrain Tiles on [AWS Open Data](https://registry.opendata.aws/terrain-tiles/) | [Attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md) (USGS 3DEP, SRTM and others) |
| Parcels | New York State tax parcels (NYS ITS, public service) | Provided as is, by the counties that share their data |
| Rhino 8, RhinoCommon | McNeel | Not redistributed |
| Optional export | Google Earth Pro | A separate application, not redistributed |

- No map content is stored in this repository.
- The photorealistic map is shown in the viewer only; no EarthLink feature exports it.
- Site downloads for Rhino are single requests, started by you, for a small area, identified by an EarthLink User-Agent.
- Keep the map credits visible.
- Credit OpenStreetMap in drawings made from its data.
- Check each provider's rules before publishing captured images; a capture is not a rights clearance.
