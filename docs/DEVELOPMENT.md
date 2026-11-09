# Development

Requires Rhino 8 for commands and package builds. The server and COLLADA tests run without Rhino.

```sh
python3 -m pip install pytest
python3 -m pytest -q tests
python3 tools/build.py 0.1.1
```

For the browser smoke check, follow `.github/workflows/ci.yml`: create isolated fixture data, start `earthlink/server.py` with an explicit `--viewer` pointing to this source's `shared/viewer`, install Playwright and Chromium, then run `node tests/viewer_smoke.mjs http://127.0.0.1:8765/`. Do not run fixture generation against your real home folder or runtime data.

The local test suite covers server API behavior and basic COLLADA geometry. It does not establish Rhino geometry/undo behavior or full browser correctness. The browser smoke test loads fixture models and captures two passes. Rhino integration must be checked in Rhino.

## Build and release

The package appears under `build/rh8/`. Its manifest, archive filename, and plugin build version must agree. Keep the plugin GUID unchanged across releases. Build tools include public README, changelog, and license files in the Yak package.

Only push a package after reviewing its contents and testing it. To try a release on McNeel's disposable test server:

```sh
python3 tools/build.py 0.1.1 --push-test
```

This command uploads externally and requires Yak authentication. Production publication uses `--push` and is a separate action. Published version/distribution combinations cannot be overwritten. See [McNeel's publishing guide](https://developer.rhino3d.com/guides/yak/pushing-a-package-to-the-server/).

0.1.0 is the initial public preview number. Earlier internal development builds used 0.2.0; they are not part of a published upgrade sequence. If a higher EarthLink version has already been published to Yak, check ownership/version history before using a lower public number.

## Working across computers

Use a GitHub clone on each computer. Pull before editing; review, commit, and push after a completed change; pull on the other computer before continuing. GitHub Desktop provides these actions without Terminal. Git transfers committed source, not unsaved edits, ignored private notes, local credentials, or Rhino runtime data.

Keep keys in EarthLinkSettings or the viewer's connection dialog. Do not commit settings, exported models, local captures, or precise project locations. The included test coordinates are the development placeholder, not a user's project dataset.
