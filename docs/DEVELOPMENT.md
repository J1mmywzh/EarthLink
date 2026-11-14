# Development

Requires Rhino 8 for commands and package builds. The server and COLLADA tests run without Rhino.

```sh
python3 -m pip install pytest
python3 -m pytest -q tests
node --test tests/navigation.test.cjs tests/walk.test.cjs tests/footprints.test.cjs
python3 tools/build.py 0.2.0-beta.2
```

For browser checks, install `playwright@1.65.0` and Chromium, start `python3 tests/serve_fixture.py --port 8765`, then run these checks sequentially (CI runs only the smoke test; the gesture checks are timing-sensitive on CI's software renderer, so run them locally before each release):

```sh
node tests/viewer_smoke.mjs http://127.0.0.1:8765/
node tests/viewer_controls.cjs http://127.0.0.1:8765/
node tests/viewer_review.cjs http://127.0.0.1:8765/
```

The fixture server creates a temporary data folder and has no map credentials. Set EARTHLINK_PLAYWRIGHT or EARTHLINK_CHROME when test dependencies or the browser executable live outside the default locations. Node 20 or newer is required. Do not generate fixtures in a real user profile.

Tests cover API behavior, GLB transforms, placement maths, footprint topology, gesture latching, walking (synthetic ray world) and browser behaviour with real wheel events. The smoke test captures two passes. Real input feel, streamed map quality, installed Rhino and Windows behavior still require separate checks; the private map fixture (placeholder site, your own token) covers Google tiles on a real GPU. CI pins Ubuntu 24.04, Windows 2022 and macOS 15 Intel so the Python 3.9 compatibility target does not follow an incompatible latest-runner migration.

## Build and release

The package appears under `build/rh8/`. Its manifest, archive filename, and plugin build version must agree. Keep the plugin GUID unchanged across releases. Build tools include public README, changelog, and license files in the Yak package.

Only push a package after reviewing its contents and testing it. To try a release on McNeel's disposable test server:

```sh
python3 tools/build.py 0.2.0-beta.2 --push-test
```

This command uploads externally and requires Yak authentication. Production publication uses `--push` and is a separate action. Published version/distribution combinations cannot be overwritten. See [McNeel's publishing guide](https://developer.rhino3d.com/guides/yak/pushing-a-package-to-the-server/).

0.1.0 is the initial public preview number. Earlier internal development builds used 0.2.0; they are not part of a published upgrade sequence. If a higher EarthLink version has already been published to Yak, check ownership/version history before using a lower public number.

## Trying changes in Rhino: EarthLink Dev

EarthLink Dev is a second, separate plugin for trying changes before a release, beside the released EarthLink.

- Build it once on a computer with Rhino 8 running: `python3 tools/build_dev.py`, then drag `build_dev/EarthLinkDev.rhp`
  into a Rhino window. It rarely needs rebuilding: its commands are launchers.
- Commands: `DevSendToEarth`, `DevEarthLinkViewer`, `DevEarthLinkSync`, `DevEarthLinkSettings` (the released commands,
  run from the source) and `DevEarthLinkUpdate` (moves the source to a branch: type its name, e.g. `beta13`).
- The source lives in `~/EarthLinkDev` (set `EARTHLINK_DEV_SRC` to use another checkout); it is cloned from GitHub on
  first use. After an update, or after editing files there, the next Dev command loads the new code: no restart.
- It is its own plugin in everything EarthLink keeps: viewer on port 8766, data in `EarthLink Dev` (settings, views,
  live files; the map keys are copied once from the released settings), its own section in the .3dm (`EarthLinkDev`)
  and its own sync timer. Shared, because Rhino holds them: the EarthAnchorPoint, named views and the Sun. Placing a
  file with DevSendToEarth therefore sets the file's site for the released EarthLink too.
- To switch it off, untick EarthLinkDev in Rhino's Options > Plug-ins (after a restart its commands are gone), or
  uninstall it there. `tools/devloader.py` holds the rules that keep the copy apart; `tests/test_devloader.py` checks them.

## Working across computers

Use a GitHub clone on each computer. Pull before editing; review, commit, and push after a completed change; pull on the other computer before continuing. GitHub Desktop provides these actions without Terminal. Git transfers committed source, not unsaved edits, ignored private notes, local credentials, or Rhino runtime data.

Keep keys in EarthLinkSettings or the viewer's connection dialog. Do not commit settings, exported models, local captures, or precise project locations. The included test coordinates are the development placeholder, not a user's project dataset.

All viewer modules and vendor license files must appear in EarthLink.rhproj resources and server.VIEWER_ASSETS. When adding a resource, verify a built Yak archive and an exported static share. The pinned Cesium private ray APIs used for walking require explicit checks before changing engine versions.

The Rhino builder flattens shared-resource folders. `finish_package()` restores the paths from the viewer resource URIs, including `shared/vendor/`, so relative imports also work in installed packages.
