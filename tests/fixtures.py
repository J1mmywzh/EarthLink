"""Test helpers: a tiny two-box GLB in Rhino's export convention, and a temporary EarthLink data folder."""
import json, os, struct


def make_glb(path):
    """Two boxes, Y-up metres like Rhino's glTF export (Rhino (x, y, z) -> glTF (x, z, -y))."""
    def box(x0, y0, z0, x1, y1, z1):
        P = [(x, z, -y) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        I = []
        for a, b, c, d in [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]:
            I += [a, b, c, a, c, d]
        return P, I
    parts = [box(0, 0, 0, 30, 5, 10), box(0, 5, 0, 5, 20, 30)]
    cols = [[0.86, 0.24, 0.2, 1], [0.95, 0.78, 0.16, 1]]
    bin_, bvs, accs, meshes = b"", [], [], []
    for (P, I), _ in zip(parts, cols):
        for data, target in ((b"".join(struct.pack("<3f", *p) for p in P), 34962), (b"".join(struct.pack("<H", i) for i in I), 34963)):
            bin_ += b"\0" * (-len(bin_) % 4)
            bvs.append({"buffer": 0, "byteOffset": len(bin_), "byteLength": len(data), "target": target})
            bin_ += data
        accs.append({"bufferView": len(bvs) - 2, "componentType": 5126, "count": len(P), "type": "VEC3",
                     "min": [min(p[k] for p in P) for k in range(3)], "max": [max(p[k] for p in P) for k in range(3)]})
        accs.append({"bufferView": len(bvs) - 1, "componentType": 5123, "count": len(I), "type": "SCALAR"})
        meshes.append({"primitives": [{"attributes": {"POSITION": len(accs) - 2}, "indices": len(accs) - 1, "material": len(meshes)}]})
    bin_ += b"\0" * (-len(bin_) % 4)
    js = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0, 1]}], "nodes": [{"mesh": 0}, {"mesh": 1}],
          "meshes": meshes, "materials": [{"pbrMetallicRoughness": {"baseColorFactor": c}} for c in cols],
          "accessors": accs, "bufferViews": bvs, "buffers": [{"byteLength": len(bin_)}]}
    j = json.dumps(js).encode()
    j += b" " * (-len(j) % 4)
    with open(path, "wb") as fh:
        fh.write(b"glTF" + struct.pack("<II", 2, 28 + len(j) + len(bin_)) + struct.pack("<II", len(j), 0x4E4F534A) + j
                 + struct.pack("<II", len(bin_), 0x004E4942) + bin_)


def make_live(home):
    """A data folder with a two-set project, as SendToEarth would leave it."""
    live = os.path.join(home, "AppData", "Roaming", "EarthLink", "live") if os.name == "nt" else \
        os.path.join(home, "Library", "Application Support", "EarthLink", "live")
    for sd, v in (("set_Main", 1), ("set_Scheme_B", 2)):
        os.makedirs(os.path.join(live, sd, "v%05d" % v), exist_ok=True)
        make_glb(os.path.join(live, sd, "v%05d" % v, "model.glb"))
    meta = {"version": 2, "project": "p-test", "name": "TestModel", "sent_at": "2026-11-08 20:40:00",
            "anchor": {"lat": 42.4405, "lon": -76.5108, "elev": 0.0, "zero": "GroundLevel", "north": 90.0, "base": [0, 0, 0]},
            "sets": {"Main": {"glb": "set_Main/v00001/model.glb", "version": 1, "objects": 2, "bbox_m": [[0, 0, 0], [30, 20, 30]], "sent_at": "x"},
                     "Scheme B": {"glb": "set_Scheme_B/v00002/model.glb", "version": 2, "objects": 2, "bbox_m": [[0, 0, 0], [30, 20, 30]], "sent_at": "x"}}}
    with open(os.path.join(live, "meta.json"), "w") as fh:
        json.dump(meta, fh)
    return live
