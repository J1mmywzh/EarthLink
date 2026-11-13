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

def _tris(g):
    v=g['vertices'];return sorted(tuple(sorted(tuple(v[k]) for k in g['indices'][i:i+3])) for i in range(0,len(g['indices']),3))

def test_merge_makes_one_piece_per_material_without_changing_the_shape(tmp_path):
    p=tmp_path/'m.glb';make_glb(p)
    data=p.read_bytes();n=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+n]);binary=data[28+n:]
    # many objects sharing two materials, some moved or turned, nested like a block
    for k in range(20):
        j['nodes'].append({'mesh':k%2,'translation':[40*k,0,0],'rotation':[0,0.3826834,0,0.9238795] if k%3==0 else [0,0,0,1]})
    j['nodes'].append({'children':[len(j['nodes'])-1],'translation':[0,5,0]});j['scenes'][0]['nodes']+=list(range(2,len(j['nodes'])-2))+[len(j['nodes'])-1]
    js=json.dumps(j).encode();js+=b' '*(-len(js)%4)
    p.write_bytes(b'glTF'+struct.pack('<II',2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary)
    before=geometry.derive(p)
    assert geometry.merge_glb(p)==(22,2)
    after=geometry.derive(p)
    a,b=_tris(after),_tris(before)
    assert len(a)==len(b) and all(abs(x-y)<1e-3 for ta,tb in zip(a,b) for pa,pb in zip(ta,tb) for x,y in zip(pa,pb))
    data=p.read_bytes();n=struct.unpack_from('<I',data,12)[0];j=json.loads(data[20:20+n])
    assert len(j['materials'])==2 and sorted(m['primitives'][0]['material'] for m in j['meshes'])==[0,1]
    assert all('min' in j['accessors'][m['primitives'][0]['attributes']['POSITION']] for m in j['meshes'])

def test_glass_and_other_see_through_materials_become_transparent(tmp_path):
    from earthlink import collada
    p=tmp_path/'m.glb';make_glb(p);js,binary=collada._read_glb(str(p))
    js['materials']=[
        {'name':'glass','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1]},'extensions':{'KHR_materials_transmission':{'transmissionFactor':1.0},'KHR_materials_ior':{'ior':1.52}}},
        {'name':'polycarbonate','pbrMetallicRoughness':{'baseColorFactor':[.8,.9,.9,1]},'extensions':{'KHR_materials_transmission':{'transmissionFactor':0.7}}},
        {'name':'plaster','pbrMetallicRoughness':{'baseColorFactor':[.9,.9,.9,1]},'extensions':{'KHR_materials_transmission':{}}}]
    geometry._write_glb(p,js,bytes(binary))
    before=geometry.derive(p)
    assert geometry.screen_materials(p)==2
    glass,poly,plaster=collada._read_glb(str(p))[0]['materials']
    assert glass['alphaMode']=='BLEND' and glass['doubleSided'] and glass['pbrMetallicRoughness']['baseColorFactor'][3]==pytest.approx(0.12)
    assert 'KHR_materials_transmission' not in glass['extensions'] and glass['extensions']['KHR_materials_ior']['ior']==1.52
    assert poly['pbrMetallicRoughness']['baseColorFactor'][:3]==[.8,.9,.9] and poly['pbrMetallicRoughness']['baseColorFactor'][3]==pytest.approx(0.384)
    assert 'alphaMode' not in plaster and plaster['pbrMetallicRoughness']['baseColorFactor'][3]==1,'opaque materials are untouched'
    assert geometry.derive(p)==before,'the shape is unchanged'
    assert geometry.screen_materials(p)==0,'running it again changes nothing'
