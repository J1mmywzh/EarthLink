"""Rhino-free geometry: merging the exported GLB into one piece per material, the cutout mesh derived from
it, and design-set placement maths.

Positions are local east/north/up metres, exactly as rendered after glTF's Y-up
conversion. No model bounds are substituted for missing or unsupported geometry.
"""
import array
import json
import math
import os
import struct
from . import collada

MAX_TRIANGLES = 500000


def derive(path):
    try:
        return _derive(path)
    except (KeyError, IndexError, TypeError, struct.error, OverflowError) as exc:
        raise ValueError("invalid exported mesh") from exc


def _derive(path):
    js, binary = collada._read_glb(str(path))
    if not js or js.get("asset", {}).get("version") != "2.0":
        raise ValueError("unsupported GLB")
    if "KHR_draco_mesh_compression" in js.get("extensionsUsed", []):
        raise ValueError("compressed mesh is unsupported")
    vertices, indices, lookup = [], [], {}
    nodes = js.get("nodes", [])
    identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]

    def add_vertex(p):
        # The exported file is Y-up metres, independent of the Rhino file's units.
        p = (round(p[0], 4), round(-p[2], 4), round(p[1], 4))   # 0.1 mm: a smaller file, same shape
        if not all(math.isfinite(c) for c in p):
            raise ValueError("nonfinite mesh position")
        if p not in lookup:
            lookup[p] = len(vertices)
            vertices.append(list(p))
        return lookup[p]

    def walk(ni, parent, ancestors):
        if ni in ancestors or len(ancestors) > 128:
            raise ValueError("cyclic or excessively nested scene")
        nd = nodes[ni]
        if "skin" in nd or "EXT_mesh_gpu_instancing" in nd.get("extensions", {}):
            raise ValueError("unsupported animated or instanced mesh extension")
        matrix = collada._mat4_mul(parent, collada._node_matrix(nd))
        if "mesh" in nd:
            for primitive in js["meshes"][nd["mesh"]]["primitives"]:
                mode = primitive.get("mode", 4)
                if mode not in (4,5,6):
                    continue
                if primitive.get("targets"):
                    raise ValueError("morph targets are unsupported")
                positions = collada._accessor(js, binary, primitive["attributes"]["POSITION"])
                remap = [add_vertex(collada._xp(matrix,p)) for p in positions]
                ix = [x[0] for x in collada._accessor(js,binary,primitive["indices"])] if "indices" in primitive else list(range(len(positions)))
                if mode == 4:
                    if len(ix) % 3:
                        raise ValueError("incomplete triangle")
                    triangles = zip(ix[::3],ix[1::3],ix[2::3])
                elif mode == 5:
                    triangles = ((ix[i+1],ix[i],ix[i+2]) if i%2 else (ix[i],ix[i+1],ix[i+2]) for i in range(len(ix)-2))
                else:
                    triangles = ((ix[0],ix[i],ix[i+1]) for i in range(1,len(ix)-1))
                for tri in triangles:
                    if any(not isinstance(i,int) or i<0 or i>=len(remap) for i in tri):
                        raise ValueError("invalid triangle index")
                    mapped = [remap[i] for i in tri]
                    if len(set(mapped)) == 3:
                        indices.extend(mapped)
                    if len(indices)//3 > MAX_TRIANGLES:
                        raise ValueError("mesh exceeds navigation geometry limit")
        for child in nd.get("children", []):
            walk(child,matrix,ancestors|{ni})

    scenes = js.get("scenes", [])
    if scenes:
        roots = scenes[js.get("scene",0)].get("nodes",[])
    else:
        children = {c for n in nodes for c in n.get("children",[])}
        roots = [i for i in range(len(nodes)) if i not in children]
    for root in roots:
        walk(root,identity,set())
    if not indices:
        raise ValueError("no surface mesh")
    return {"schema":1,"vertices":vertices,"indices":indices}


def compose_placement(p, dx=0.0, dy=0.0, dz=0.0, rot=0.0, pivot=(0, 0, 0)):
    """A set's EarthLink placement {rot, t}: turned `rot` degrees clockwise on the map, then moved by `t`
    (metres east/north/up). Returns `p` followed by a viewer move: turn `rot` clockwise about `pivot`, move by d."""
    p = p or {}
    r0, t0 = float(p.get("rot", 0.0)), [float(v) for v in (p.get("t") or [0.0, 0.0, 0.0])][:3]
    a = math.radians(-rot)
    vx, vy = t0[0] - pivot[0], t0[1] - pivot[1]
    t = [pivot[0] + vx * math.cos(a) - vy * math.sin(a) + dx, pivot[1] + vx * math.sin(a) + vy * math.cos(a) + dy, t0[2] + dz]
    out = {"rot": round((r0 + rot + 180.0) % 360.0 - 180.0, 6), "t": [round(v, 6) for v in t]}
    return None if not out["rot"] and not any(out["t"]) else out


# ----------------------------------------------------------------- draw-call merge
def merge_glb(path):
    """Rewrite a GLB so it holds one mesh piece per material instead of one per object face.

    Rhino's glTF writer emits a primitive for every Brep face (tens of thousands for a building), and a browser
    draws each one separately every frame. Node transforms are baked into the vertices; materials, textures and
    the rendered look are unchanged. Returns (pieces before, pieces after); a file it cannot merge safely is left
    as it is and reported as (n, n)."""
    js, binary = collada._read_glb(str(path))
    before = sum(len(m.get("primitives", [])) for m in js.get("meshes", []))
    if (js.get("extensionsRequired") or js.get("skins") or js.get("animations")
            or any("targets" in p for m in js.get("meshes", []) for p in m.get("primitives", []))
            or any("EXT_mesh_gpu_instancing" in n.get("extensions", {}) for n in js.get("nodes", []))):
        return before, before
    nodes = js.get("nodes", [])
    textured = {i for i, m in enumerate(js.get("materials", [])) if "Texture" in str(m)}
    drawn = [0]
    groups = {}            # (material, kind) -> {"p": [], "n": [], "uv": [], "i": [], "has_n": bool, "has_uv": bool}

    def add(prim, m):
        mode = prim.get("mode", 4)
        kind = 4 if mode in (4, 5, 6) else 1 if mode in (1, 2, 3) else 0
        attrs = prim["attributes"]
        pos = collada._accessor(js, binary, attrs["POSITION"])
        idx = [x[0] for x in collada._accessor(js, binary, prim["indices"])] if "indices" in prim else list(range(len(pos)))
        if mode == 5:
            idx = [k for i in range(len(idx) - 2) for k in ((idx[i + 1], idx[i], idx[i + 2]) if i % 2 else idx[i:i + 3])]
        elif mode == 6:
            idx = [k for i in range(1, len(idx) - 1) for k in (idx[0], idx[i], idx[i + 1])]
        elif mode in (2, 3):
            idx = [k for i in range(len(idx) - 1 + (mode == 2)) for k in (idx[i], idx[(i + 1) % len(idx)])]
        key = (prim.get("material"), kind)
        g = groups.setdefault(key, {"p": [], "n": [], "uv": [], "i": [], "has_n": True, "has_uv": True})
        base = len(g["p"])
        if m == IDENTITY:
            g["p"].extend(pos)
        else:
            g["p"].extend(collada._xp(m, p) for p in pos)
        if "NORMAL" in attrs and g["has_n"]:
            nm = _normal_matrix(m)
            nr = collada._accessor(js, binary, attrs["NORMAL"])
            g["n"].extend(nr if nm is None else (collada._xv(nm, v) for v in nr))
        else:
            g["has_n"], g["n"] = False, []
        if "TEXCOORD_0" in attrs and g["has_uv"]:
            g["uv"].extend(collada._accessor(js, binary, attrs["TEXCOORD_0"]))
        else:
            g["has_uv"], g["uv"] = False, []
        g["i"].extend(k + base for k in idx)

    def walk(ni, parent, seen):
        if ni in seen or len(seen) > 128:
            raise ValueError("cyclic scene")
        nd = nodes[ni]
        m = collada._mat4_mul(parent, collada._node_matrix(nd))
        if "mesh" in nd:
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                add(prim, m)
                drawn[0] += 1
        for c in nd.get("children", []):
            walk(c, m, seen | {ni})

    scenes = js.get("scenes", [])
    roots = scenes[js.get("scene", 0)].get("nodes", []) if scenes else [
        i for i in range(len(nodes)) if i not in {c for n in nodes for c in n.get("children", [])}]
    try:
        for r in roots:
            walk(r, IDENTITY, set())
    except (KeyError, IndexError, TypeError, ValueError, struct.error):
        return before, before

    out, views, accessors = bytearray(), [], []

    def view(data, target=None):
        while len(out) % 4:
            out.append(0)
        v = {"buffer": 0, "byteOffset": len(out), "byteLength": len(data)}
        if target:
            v["target"] = target
        out.extend(data)
        views.append(v)
        return len(views) - 1

    def accessor(values, n, ctype, typ, target, bounds=False):
        flat = [c for v in values for c in v] if n > 1 else values
        code = {5126: "f", 5125: "I", 5123: "H"}[ctype]
        a = {"bufferView": view(array.array(code, flat).tobytes(), target), "componentType": ctype,
             "count": len(values), "type": typ}
        if bounds:
            a["min"] = [min(v[k] for v in values) for k in range(n)]
            a["max"] = [max(v[k] for v in values) for k in range(n)]
        accessors.append(a)
        return len(accessors) - 1

    images = []
    for im in js.get("images", []):
        im = dict(im)
        if "bufferView" in im:
            bv = js["bufferViews"][im["bufferView"]]
            s = bv.get("byteOffset", 0)
            im["bufferView"] = view(binary[s:s + bv["byteLength"]])
        images.append(im)
    meshes, new_nodes = [], []
    mats = js.get("materials", [])
    for (mat, kind), g in groups.items():
        if not g["p"] or not g["i"]:
            continue
        attrs = {"POSITION": accessor(g["p"], 3, 5126, "VEC3", 34962, True)}
        if g["has_n"] and len(g["n"]) == len(g["p"]):
            attrs["NORMAL"] = accessor(g["n"], 3, 5126, "VEC3", 34962)
        if g["has_uv"] and len(g["uv"]) == len(g["p"]) and mat in textured:
            attrs["TEXCOORD_0"] = accessor(g["uv"], 2, 5126, "VEC2", 34962)
        big = len(g["p"]) > 65535
        prim = {"attributes": attrs, "mode": kind,
                "indices": accessor(g["i"], 1, 5125 if big else 5123, "SCALAR", 34963)}
        if mat is not None:
            prim["material"] = mat
        name = (mats[mat].get("name") if mat is not None and mat < len(mats) else None) or "default"
        meshes.append({"name": name, "primitives": [prim]})
        new_nodes.append({"name": name, "mesh": len(meshes) - 1})
    if not meshes:
        return before, before
    js = {k: v for k, v in js.items() if k not in ("nodes", "meshes", "accessors", "bufferViews", "buffers", "scenes", "scene", "images")}
    js.update(nodes=new_nodes, meshes=meshes, accessors=accessors, bufferViews=views, scenes=[{"nodes": list(range(len(new_nodes)))}],
              scene=0, buffers=[{"byteLength": len(out)}])
    if images:
        js["images"] = images
    _write_glb(path, js, bytes(out))
    return drawn[0], len(meshes)


IDENTITY = [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0]


def _normal_matrix(m):
    """Inverse-transpose of the upper 3x3 (column-major 4x4 result), or None when it is the identity."""
    if m == IDENTITY:
        return None
    a, b, c, d, e, f, g, h, i = m[0], m[4], m[8], m[1], m[5], m[9], m[2], m[6], m[10]   # rows of the 3x3
    cof = [e * i - f * h, -(d * i - f * g), d * h - e * g,
           -(b * i - c * h), a * i - c * g, -(a * h - b * g),
           b * f - c * e, -(a * f - c * d), a * e - b * d]          # cofactor matrix, row-major
    # inverse-transpose = cofactor / det; the scale does not matter (normals are renormalised)
    return [cof[0], cof[3], cof[6], 0, cof[1], cof[4], cof[7], 0, cof[2], cof[5], cof[8], 0, 0, 0, 0, 1]


def _write_glb(path, js, binary):
    j = json.dumps(js, separators=(",", ":")).encode("utf-8")
    j += b" " * (-len(j) % 4)
    binary += b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(j) + 8 + len(binary)
    tmp = str(path) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(j), 0x4E4F534A) + j)
        f.write(struct.pack("<II", len(binary), 0x004E4942) + binary)
    os.replace(tmp, str(path))
