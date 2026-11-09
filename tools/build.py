#!/usr/bin/env python3
"""Build (and optionally publish) the EarthLink Rhino package. Works on macOS and Windows.

  python3 tools/build.py 0.1.2                 # build build/rh8/EarthLink-0.1.2-rh8-any.yak
  python3 tools/build.py 0.1.2 --push-test     # ... and push to McNeel's test server (wiped nightly)
  python3 tools/build.py 0.1.2 --push          # ... and publish for real (run `yak login` once first)

Versions must go up every release: a published version can never be overwritten.
"""
import glob, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sys.platform == "darwin":
    BIN = "/Applications/Rhino 8.app/Contents/Resources/bin"
    RHINOCODE, YAK = os.path.join(BIN, "rhinocode"), os.path.join(BIN, "yak")
else:
    BIN = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Rhino 8", "System")
    RHINOCODE, YAK = os.path.join(BIN, "rhinocode.exe"), os.path.join(BIN, "Yak.exe")


def finish_package(pkg, version):
    """Complete the manifest rhinocode writes: authors (required by Yak) from the project's publisher, the plain
    version (rhinocode appends +build data), the url, and the package icon. Renames the .yak to match."""
    import json, re, zipfile
    ident = json.load(open(os.path.join(ROOT, "EarthLink.rhproj"), encoding="utf-8"))["identity"]
    author = (ident.get("publisher") or {}).get("name") or "unknown"
    with zipfile.ZipFile(pkg) as z:
        files = {n: z.read(n) for n in z.namelist()}
    m = files["manifest.yml"].decode("utf-8")
    m = re.sub(r"(?m)^version:.*$", "version: " + version, m)
    m = re.sub(r"(?m)^authors:\n(?:- .*\n)+", "authors:\n- " + json.dumps(author) + "\n", m)
    if ident.get("url"):
        m = re.sub(r"(?m)^url:.*$", "url: " + json.dumps(ident["url"]), m)
    icon = os.path.join(ROOT, "icons", "icon.png")
    if os.path.exists(icon) and not re.search(r"(?m)^icon:", m):
        m = m.rstrip("\n") + "\nicon: icon.png\n"
        files["icon.png"] = open(icon, "rb").read()
    for name in ("README.md", "CHANGELOG.md", "LICENSE"):
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                files[name] = fh.read()
    docs = os.path.join(ROOT, "docs")
    if os.path.isdir(docs):
        for name in sorted(os.listdir(docs)):
            if name.endswith(".md"):
                with open(os.path.join(docs, name), "rb") as fh:
                    files["docs/" + name] = fh.read()
    files["manifest.yml"] = m.encode("utf-8")
    base = os.path.basename(pkg)
    hit = re.match(r"^(.+?)-\d[^-]*-(.+)$", base)
    out = os.path.join(os.path.dirname(pkg), "%s-%s-%s" % (hit.group(1), version, hit.group(2)) if hit else base)
    tmp = out + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
    if os.path.abspath(pkg) != os.path.abspath(out):
        os.remove(pkg)
    os.replace(tmp, out)
    with open(os.path.join(os.path.dirname(out), "manifest.yml"), "w", encoding="utf-8") as f:
        f.write(m)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    version = sys.argv[1]
    # rhinocode's launcher splits paths containing spaces, so build from a space-free temp copy
    import shutil, tempfile
    tmp = os.path.join(tempfile.gettempdir(), "EarthLink_build")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    inputs = ("EarthLink.rhproj", "commands", "earthlink", "shared", "icons", "tools",
              "README.md", "CHANGELOG.md", "LICENSE", "docs")
    for name in inputs:
        src, dst = os.path.join(ROOT, name), os.path.join(tmp, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif os.path.isfile(src):
            shutil.copy2(src, dst)
    subprocess.check_call([RHINOCODE, "project", "build", os.path.join(tmp, "EarthLink.rhproj"),
                           "--buildversion", version, "--buildtarget", "8.*", "--buildpath", os.path.join(tmp, "build")])
    build = os.path.join(ROOT, "build")
    shutil.rmtree(build, ignore_errors=True)
    shutil.copytree(os.path.join(tmp, "build"), build, ignore=shutil.ignore_patterns("src", "libs"))
    yaks = sorted(glob.glob(os.path.join(build, "**", "*.yak"), recursive=True), key=os.path.getmtime)
    if not yaks:
        sys.exit("no .yak produced")
    pkg = finish_package(yaks[-1], version)
    print("built", pkg)
    if "--push-test" in sys.argv:
        subprocess.check_call([YAK, "push", pkg, "--source", "https://test.yak.rhino3d.com"])
        print("pushed to the TEST server")
    elif "--push" in sys.argv:
        subprocess.check_call([YAK, "push", pkg])
        print("published")


if __name__ == "__main__":
    main()
