import json,zipfile
from pathlib import Path
import pytest
from tools import build

@pytest.mark.parametrize('original,expected',[
 ('earthlink-0.2.0-beta+930-rh8-any.yak','earthlink-0.2.0-beta.1-rh8-any.yak'),
 ('earthlink-0.2.0-beta.1+930-rh8_4-mac.yak','earthlink-0.2.0-beta.1-rh8_4-mac.yak'),
 ('earthlink-0.2.0+930-rh8-any.yak','earthlink-0.2.0-beta.1-rh8-any.yak')])
def test_finish_package_keeps_prerelease_and_distribution_separate(tmp_path,monkeypatch,original,expected):
    monkeypatch.setattr(build,'ROOT',str(tmp_path))
    (tmp_path/'EarthLink.rhproj').write_text(json.dumps({'identity':{'name':'EarthLink','publisher':{'name':'Publisher'}}}))
    p=tmp_path/original
    with zipfile.ZipFile(p,'w') as z:z.writestr('manifest.yml','name: EarthLink\nversion: 0.2.0-beta+930\nauthors:\n- Publisher\n')
    result=build.finish_package(str(p),'0.2.0-beta.1')
    assert Path(result).name==expected
    with zipfile.ZipFile(result) as z:assert 'version: 0.2.0-beta.1\n' in z.read('manifest.yml').decode()


def test_finish_package_preserves_nested_viewer_resource_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(build, 'ROOT', str(tmp_path))
    vendor = tmp_path / 'shared/viewer/vendor'
    vendor.mkdir(parents=True)
    (vendor / 'rapier.mjs').write_text('export default {};')
    project = {'identity': {'name': 'EarthLink'}, 'resources': [{'uri': 'shared/viewer/vendor/rapier.mjs'}]}
    (tmp_path / 'EarthLink.rhproj').write_text(json.dumps(project))
    package = tmp_path / 'earthlink-0.2.0+930-rh8-any.yak'
    with zipfile.ZipFile(package, 'w') as z:
        z.writestr('manifest.yml', 'name: EarthLink\nversion: 0.2.0+930\n')
        z.writestr('shared/rapier.mjs', 'export default {};')
    result = build.finish_package(str(package), '0.2.0-beta.1')
    with zipfile.ZipFile(result) as z:
        assert z.read('shared/vendor/rapier.mjs') == (vendor / 'rapier.mjs').read_bytes()
        assert 'shared/rapier.mjs' not in z.namelist()
