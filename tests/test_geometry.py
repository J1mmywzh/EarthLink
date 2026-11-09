import json,struct
from pathlib import Path
import pytest
from tests.fixtures import make_glb
try:
    from earthlink import geometry
except ImportError:
    geometry=None

def test_exported_geometry_is_metres_enu_and_preserves_l_shape(tmp_path):
    assert geometry is not None,'geometry derivation exists'
    p=tmp_path/'m.glb';make_glb(p);g=geometry.derive(p)
    assert g['schema']==1
    assert len(g['indices'])==72
    assert [max(v[k] for v in g['vertices']) for k in range(3)]==[30,20,30]
    assert [min(v[k] for v in g['vertices']) for k in range(3)]==[0,0,0]

def test_node_transforms_and_repeated_mesh_instances_are_baked(tmp_path):
    assert geometry is not None
    p=tmp_path/'m.glb';make_glb(p)
    data=p.read_bytes();n=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+n]);binary=data[28+n:]
    j['nodes'][0]['translation']=[10,2,-3]
    j['nodes'].append({'mesh':0,'translation':[100,0,0]});j['scenes'][0]['nodes'].append(2)
    js=json.dumps(j).encode();js+=b' '*(-len(js)%4)
    p.write_bytes(b'glTF'+struct.pack('<II',2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary)
    g=geometry.derive(p)
    assert len(g['indices'])==108
    assert [10,3,2] in g['vertices']
    assert max(v[0] for v in g['vertices'])==130

def test_invalid_glb_fails_without_inventing_bounds(tmp_path):
    assert geometry is not None
    p=tmp_path/'bad.glb';p.write_bytes(b'no model')
    with pytest.raises(ValueError):geometry.derive(p)
