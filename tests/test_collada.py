import os, re, sys, xml.dom.minidom
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from earthlink import collada  # noqa: E402
from tests.fixtures import make_glb  # noqa: E402


def test_glb_to_dae_is_valid_and_z_up(tmp_path):
    glb = tmp_path / "m.glb"
    make_glb(str(glb))
    tris = collada.glb_to_dae(str(glb), str(tmp_path))
    assert tris == 24
    dae = (tmp_path / "model.dae").read_text()
    doc = xml.dom.minidom.parseString(dae)
    assert doc.getElementsByTagName("up_axis")[0].firstChild.data == "Z_UP"
    assert len(doc.getElementsByTagName("geometry")) == 2
    # the tall box (Rhino z 0..30, y 5..20) must come back Z-up with north = +Y
    arrays = re.findall(r'<float_array id="g\d+-pa" count="\d+">([^<]*)', dae)
    pts = [float(v) for v in arrays[1].split()]
    xs, ys, zs = pts[0::3], pts[1::3], pts[2::3]
    assert (min(zs), max(zs)) == (0.0, 30.0)
    assert (min(ys), max(ys)) == (5.0, 20.0)
    assert (min(xs), max(xs)) == (0.0, 5.0)
