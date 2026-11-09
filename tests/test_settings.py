import json
from earthlink import env

def test_legacy_shadows_off_becomes_global_sun_off(tmp_path,monkeypatch):
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path))
    (tmp_path/'settings.json').write_text(json.dumps({'shadows':False}))
    assert env.load_settings()['sun_enabled'] is False
    env.save_settings({'sun_enabled':True})
    assert env.load_settings()['sun_enabled'] is True

def test_concurrent_settings_writes_keep_a_valid_atomic_file(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda i:env.save_settings({'sun_enabled':bool(i%2)}),range(40)))
    assert isinstance(json.loads((tmp_path/'settings.json').read_text())['sun_enabled'],bool)
