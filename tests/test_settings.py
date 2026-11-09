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

def test_concurrent_settings_updates_preserve_other_controls(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path))
    patches=[{'nudge':1.0},{'ground_h':2.0},{'sync_views':False},{'style':'clay'}]
    barrier=Barrier(4)
    def update(patch):
        barrier.wait();env.save_settings(patch)
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(update,patches))
    settings=env.load_settings()
    assert {k:settings[k] for k in ('nudge','ground_h','sync_views','style')}=={'nudge':1.0,'ground_h':2.0,'sync_views':False,'style':'clay'}
