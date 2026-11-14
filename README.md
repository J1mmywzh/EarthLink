# EarthLink

**See your Rhino 8 model on a photorealistic 3D map of the real site, live, in your browser.**

Free and open source, for Rhino 8 on Mac and Windows.

- **Place** a model on its site with a click, and it updates as you model.
- **Explore** with Rhino's own navigation: orbit, pan, zoom, Two-Point and Parallel views, or walk at eye level.
- **Light** the scene with the sun at any date and time, or at night with your model's own Rhino lights.
- **Share views with Rhino**: a named view saved on either side appears on the other.
- **Capture** high-resolution images of the current view or every saved view, with or without the context.
- **Bring the site into Rhino**: terrain, contours, buildings, roads, railways, water and parcels.

## Get started

1. **Install.** In Rhino 8, run `PackageManager`, search for **EarthLink**, install it and restart Rhino.
2. **Connect the map** (once, free). Run `EarthLinkViewer`. The viewer opens in your browser and walks you through creating a free Cesium ion account and pasting its access token.
3. **Send a model.** Select geometry and run `SendToEarth`. Pick a base point (Enter for the bottom centre), find your site in the viewer, click where the base point goes and press **Apply to Rhino**.

That's it: the model stands on the site. Turn on **Live** in `SendToEarth` and it follows your edits.

## Commands

| Command | What it does |
| --- | --- |
| `SendToEarth` | Send the selected geometry to the viewer as a design set |
| `EarthLinkViewer` | Open the viewer |
| `EarthLinkSync` | Follow Rhino's viewport and sync the sun |
| `EarthLinkSettings` | Map connection, capture folder, design sets, stop the viewer |

## Documentation

- [User manual](docs/USER_MANUAL.md): everything EarthLink does, step by step.
- [Architecture](docs/ARCHITECTURE.md): how the plugin, the local server and the viewer fit together.
- [Development](docs/DEVELOPMENT.md): tests, builds and releases.
- [Changelog](CHANGELOG.md) and [roadmap](docs/ROADMAP.md).
- [Third-party services and licenses](docs/THIRD_PARTY.md).

## Requirements and privacy

- Rhino 8, a current browser (Chrome, Edge, Safari or Firefox) and an internet connection for the map.
- The viewer runs on your own computer at `127.0.0.1:8765`. Your model is never uploaded.
- The map is requested with your own Cesium ion token or Google Maps Platform key, which stays on your computer.
- Site data for Rhino comes from open sources (OpenStreetMap, open elevation tiles, public parcel records), fetched only when you press **Import**.

## Feedback

Use **Send feedback** in the viewer, open an [issue](https://github.com/J1mmywzh/EarthLink/issues), or email rhinoearthlink@gmail.com.

## License

EarthLink is MIT licensed. Map content belongs to its providers and keeps their attribution on screen; see [third-party services](docs/THIRD_PARTY.md).
