"""GLB (Rhino glTF export, Y-up, metres) -> Z-up textured COLLADA for Google Earth Pro."""
import os, json, math, struct

def _read_glb(path):
    data = open(path, "rb").read()
    if data[:4] != b"glTF":
        raise ValueError("not a GLB")
    off, js, binc = 12, None, b""
    while off < len(data):
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif typ == 0x004E4942:
            binc = chunk
        off += 8 + ln
    return js, binc


_CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _accessor(js, binc, idx):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, size = _CT[a["componentType"]]
    n = _NC[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0) or size * n
    out = []
    if stride == size * n:
        flat = struct.unpack_from("<%d%s" % (a["count"] * n, fmt), binc, start)
        for i in range(a["count"]):
            out.append(flat[i * n:(i + 1) * n])
    else:
        for i in range(a["count"]):
            out.append(struct.unpack_from("<%d%s" % (n, fmt), binc, start + i * stride))
    return out


def _mat4_mul(a, b):  # column-major 4x4
    r = [0.0] * 16
    for c in range(4):
        for rr in range(4):
            r[c * 4 + rr] = sum(a[k * 4 + rr] * b[c * 4 + k] for k in range(4))
    return r


def _node_matrix(nd):
    if "matrix" in nd:
        return list(nd["matrix"])
    t = nd.get("translation", [0, 0, 0])
    q = nd.get("rotation", [0, 0, 0, 1])
    s = nd.get("scale", [1, 1, 1])
    x, y, z, w = q
    rot = [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
           2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
           2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0,
           0, 0, 0, 1]
    for c in range(3):
        for rr in range(3):
            rot[c * 4 + rr] *= s[c]
    rot[12], rot[13], rot[14] = t
    return rot


def _xp(m, p):
    x, y, z = p
    return (m[0] * x + m[4] * y + m[8] * z + m[12],
            m[1] * x + m[5] * y + m[9] * z + m[13],
            m[2] * x + m[6] * y + m[10] * z + m[14])


def _xv(m, v):
    x, y, z = v
    r = (m[0] * x + m[4] * y + m[8] * z, m[1] * x + m[5] * y + m[9] * z, m[2] * x + m[6] * y + m[10] * z)
    l = math.sqrt(r[0] ** 2 + r[1] ** 2 + r[2] ** 2) or 1.0
    return (r[0] / l, r[1] / l, r[2] / l)


def glb_to_dae(glb_path, out_dir):
    """Convert a Rhino-exported GLB (Y-up, metres) into a Z-up COLLADA for Google Earth."""
    js, binc = _read_glb(glb_path)
    if "KHR_draco_mesh_compression" in js.get("extensionsUsed", []):
        raise ValueError("GLB uses Draco compression - turn it off in Rhino's glTF export options")

    # images -> files
    img_files = []
    for i, im in enumerate(js.get("images", [])):
        ext = ".jpg" if "jpeg" in im.get("mimeType", "") else ".png"
        name = "tex_%02d%s" % (i, ext)
        if "bufferView" in im:
            bv = js["bufferViews"][im["bufferView"]]
            o = bv.get("byteOffset", 0)
            open(os.path.join(out_dir, name), "wb").write(binc[o:o + bv["byteLength"]])
            img_files.append(name)
        else:
            img_files.append(None)

    # materials
    mats = []
    for i, m in enumerate(js.get("materials") or []):
        pbr = m.get("pbrMetallicRoughness", {})
        col = list(pbr.get("baseColorFactor", [0.8, 0.8, 0.8, 1.0]))
        tex = None
        if "baseColorTexture" in pbr:
            t = js["textures"][pbr["baseColorTexture"]["index"]]
            if "source" in t and t["source"] < len(img_files):
                tex = img_files[t["source"]]
        alpha = col[3] if m.get("alphaMode") == "BLEND" else 1.0
        trans = m.get("extensions", {}).get("KHR_materials_transmission", {}).get("transmissionFactor", 0)
        if trans:
            alpha = min(alpha, max(0.25, 1.0 - 0.7 * trans))
        mats.append({"id": "mat%d" % i, "color": col[:3], "alpha": alpha, "tex": tex})
    if not mats:
        mats.append({"id": "mat0", "color": [0.8, 0.8, 0.8], "alpha": 1.0, "tex": None})

    # walk scene, bake transforms, Y-up -> Z-up : (x, y, z) -> (x, -z, y)
    geoms, nodes_xml = [], []
    yup = [1, 0, 0, 0, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 1]

    def walk(ni, parent):
        nd = js["nodes"][ni]
        m = _mat4_mul(parent, _node_matrix(nd))
        if "mesh" in nd:
            for pi, prim in enumerate(js["meshes"][nd["mesh"]]["primitives"]):
                if prim.get("mode", 4) != 4:
                    continue
                at = prim["attributes"]
                pos = [_xp(m, p) for p in _accessor(js, binc, at["POSITION"])]
                nor = [_xv(m, v) for v in _accessor(js, binc, at["NORMAL"])] if "NORMAL" in at else None
                uv = [(u, 1.0 - v) for (u, v) in _accessor(js, binc, at["TEXCOORD_0"])] if "TEXCOORD_0" in at else None
                if "indices" in prim:
                    idx = [i[0] for i in _accessor(js, binc, prim["indices"])]
                else:
                    idx = list(range(len(pos)))
                geoms.append((pos, nor, uv, idx, prim.get("material", 0)))
        for c in nd.get("children", []):
            walk(c, m)

    scene = js["scenes"][js.get("scene", 0)]
    for ni in scene["nodes"]:
        walk(ni, yup)

    def f(v):
        return "%.4f" % v

    lib_geo, lib_nodes = [], []
    for gi, (pos, nor, uv, idx, mi) in enumerate(geoms):
        gid = "g%d" % gi
        mid = mats[mi if mi < len(mats) else 0]["id"]
        inputs = ['<input semantic="VERTEX" source="#%s-v" offset="0"/>' % gid]
        src = ['<source id="%s-p"><float_array id="%s-pa" count="%d">%s</float_array><technique_common><accessor source="#%s-pa" count="%d" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>'
               % (gid, gid, len(pos) * 3, " ".join(f(c) for p in pos for c in p), gid, len(pos))]
        off = 1
        if nor:
            src.append('<source id="%s-n"><float_array id="%s-na" count="%d">%s</float_array><technique_common><accessor source="#%s-na" count="%d" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>'
                       % (gid, gid, len(nor) * 3, " ".join("%.3f" % c for p in nor for c in p), gid, len(nor)))
            inputs.append('<input semantic="NORMAL" source="#%s-n" offset="%d"/>' % (gid, off)); off += 1
        if uv:
            src.append('<source id="%s-t"><float_array id="%s-ta" count="%d">%s</float_array><technique_common><accessor source="#%s-ta" count="%d" stride="2"><param name="S" type="float"/><param name="T" type="float"/></accessor></technique_common></source>'
                       % (gid, gid, len(uv) * 2, " ".join(f(c) for p in uv for c in p), gid, len(uv)))
            inputs.append('<input semantic="TEXCOORD" source="#%s-t" offset="%d" set="0"/>' % (gid, off)); off += 1
        p = " ".join(" ".join([str(i)] * off) for i in idx)
        lib_geo.append('<geometry id="%s"><mesh>%s<vertices id="%s-v"><input semantic="POSITION" source="#%s-p"/></vertices><triangles material="%s" count="%d">%s<p>%s</p></triangles></mesh></geometry>'
                       % (gid, "".join(src), gid, gid, mid, len(idx) // 3, "".join(inputs), p))
        lib_nodes.append('<node id="n%d"><instance_geometry url="#%s"><bind_material><technique_common><instance_material symbol="%s" target="#%s"><bind_vertex_input semantic="UVSET0" input_semantic="TEXCOORD" input_set="0"/></instance_material></technique_common></bind_material></instance_geometry></node>'
                         % (gi, gid, mid, mid))

    lib_img, lib_fx, lib_mat = [], [], []
    for m in mats:
        mid = m["id"]
        if m["tex"]:
            lib_img.append('<image id="%s-img"><init_from>%s</init_from></image>' % (mid, m["tex"]))
            diffuse = ('<newparam sid="%s-surf"><surface type="2D"><init_from>%s-img</init_from></surface></newparam>'
                       '<newparam sid="%s-samp"><sampler2D><source>%s-surf</source></sampler2D></newparam>') % (mid, mid, mid, mid)
            dif = '<diffuse><texture texture="%s-samp" texcoord="UVSET0"/></diffuse>' % mid
        else:
            diffuse = ""
            dif = '<diffuse><color>%s 1</color></diffuse>' % " ".join("%.4f" % c for c in m["color"])
        tr = '<transparent opaque="A_ONE"><color>1 1 1 1</color></transparent><transparency><float>%.3f</float></transparency>' % m["alpha"] if m["alpha"] < 0.999 else ""
        lib_fx.append('<effect id="%s-fx"><profile_COMMON>%s<technique sid="common"><lambert>%s%s</lambert></technique></profile_COMMON></effect>' % (mid, diffuse, dif, tr))
        lib_mat.append('<material id="%s"><instance_effect url="#%s-fx"/></material>' % (mid, mid))

    dae = ('<?xml version="1.0" encoding="utf-8"?>\n'
           '<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">'
           '<asset><contributor><authoring_tool>EarthLink SendToEarth</authoring_tool></contributor>'
           '<unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>'
           '<library_images>%s</library_images><library_effects>%s</library_effects>'
           '<library_materials>%s</library_materials><library_geometries>%s</library_geometries>'
           '<library_visual_scenes><visual_scene id="scene">%s</visual_scene></library_visual_scenes>'
           '<scene><instance_visual_scene url="#scene"/></scene></COLLADA>'
           % ("".join(lib_img), "".join(lib_fx), "".join(lib_mat), "".join(lib_geo), "".join(lib_nodes)))
    with open(os.path.join(out_dir, "model.dae"), "w", encoding="utf-8") as fh:
        fh.write(dae)
    return sum(len(g[3]) // 3 for g in geoms)


