# Third-party services and attribution

EarthLink's original source is distributed under the MIT license in the repository root. That license does not grant rights to third-party software, map content, accounts, or trademarks.

- **CesiumJS 1.140.0** is loaded from a CDN. See the [upstream license and notices](https://github.com/CesiumGS/cesium/blob/1.140/LICENSE.md).
- **Google Photorealistic 3D Tiles** are requested through the viewer using each user's own Cesium ion token or Google Maps Platform key. Map content is not included in this source repository. Follow the [Map Tiles API policies](https://developers.google.com/maps/documentation/tile/policies) and the terms applicable to your account.
- **Rhino 8 / RhinoCommon** are supplied by McNeel and are not redistributed here.
- **Google Earth Pro** is an optional external application and is not redistributed here.

Preserve required attribution in the viewer. Before adding map-based screenshots or recordings to a public portfolio, check the applicable service's imagery and attribution requirements. Capture features in this preview do not constitute a rights clearance for the resulting images.

## Bundled browser libraries

- [Rapier 3D compatibility build 0.19.3](https://github.com/dimforge/rapier.js), Apache-2.0: character collision and movement. Bundled as vendor/rapier.mjs with the Apache license.
- [polygon-clipping 0.15.7](https://github.com/mfogel/polygon-clipping), MIT: projected footprint union.
- [earcut 2.2.4](https://github.com/mapbox/earcut), ISC: courtyard-preserving decomposition for Cesium's pinned clipping API.

The corresponding license texts are retained under shared/viewer/vendor and in static shares/packages. Library source is version pinned; map meshes, credentials, captures and user model exports are not bundled.
