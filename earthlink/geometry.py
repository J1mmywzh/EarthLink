"""Derive clipping/collision geometry from the final Rhino GLB, without Rhino imports.

Positions are local east/north/up metres, exactly as rendered after glTF's Y-up
conversion. No model bounds are substituted for missing or unsupported geometry.
"""
import math
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
        p = (p[0], -p[2], p[1])
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
