# Third-party services and attribution

EarthLink's original source is distributed under the MIT license in the repository root. That license does not grant rights to third-party software, map content, accounts, or trademarks.

- **CesiumJS 1.140.0** is loaded from a CDN. See the [upstream license and notices](https://github.com/CesiumGS/cesium/blob/1.140/LICENSE.md).
- **Google Photorealistic 3D Tiles** are requested through the viewer using each user's own Cesium ion token or Google Maps Platform key. Map content is not included in this source repository. Follow the [Map Tiles API policies](https://developers.google.com/maps/documentation/tile/policies) and the terms applicable to your account.
- **OpenStreetMap** data (buildings, roads) is downloaded on request by **Surroundings to Rhino**, from api.openstreetmap.org and, as a fallback, public Overpass API servers. © OpenStreetMap contributors, [Open Database License](https://www.openstreetmap.org/copyright). Credit OpenStreetMap in work made from it. Requests are single, user-started downloads of a small area, identified by an EarthLink User-Agent, in line with the [API usage policy](https://operations.osmfoundation.org/policies/api/).
- **Terrain Tiles** (Mapzen elevation tiles on [AWS Open Data](https://registry.opendata.aws/terrain-tiles/)) supply the terrain for the same tool; see their [attribution](https://github.com/tilezen/joerd/blob/master/docs/attribution.md) (USGS 3DEP, SRTM and other sources).
- Google's map content is **not** exported to Rhino by any EarthLink feature.
- **Rhino 8 / RhinoCommon** are supplied by McNeel and are not redistributed here.
- **Google Earth Pro** is an optional external application and is not redistributed here.

Preserve required attribution in the viewer. Before adding map-based screenshots or recordings to a public portfolio, check the applicable service's imagery and attribution requirements. Capture features in this preview do not constitute a rights clearance for the resulting images.
