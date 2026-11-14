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

def test_first_ever_settings_writes_can_start_together(tmp_path,monkeypatch):
    # Rhino and the viewer's server both save settings the first time EarthLink runs: no lock file exists yet.
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    for round_ in range(25):
        d=tmp_path/str(round_);d.mkdir();monkeypatch.setattr(env,'data_dir',lambda d=d:str(d))
        barrier=Barrier(6)
        def update(i):
            barrier.wait();env.save_settings({'nudge':float(i)})
        with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(update,range(6)))
        assert env.load_settings()['nudge'] in {float(i) for i in range(6)}

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


def test_a_copy_of_a_file_is_told_from_a_renamed_or_moved_one():
    there=lambda p:p=='/a/tower.3dm'
    assert env.is_copy('/a/tower.3dm','/a/tower v2.3dm',there)            # Save As: the original is still there
    assert not env.is_copy('/a/tower.3dm','/a/tower.3dm',there)
    assert not env.is_copy('/a/tower.3dm','/a/./tower.3dm',there)         # the same file, written another way
    assert not env.is_copy('/old/tower.3dm','/a/tower.3dm',there)         # renamed or moved: the old path is gone
    assert not env.is_copy(None,'/a/tower.3dm',there) and not env.is_copy('/a/tower.3dm','',there)

def test_a_copy_shown_in_the_viewer_stays_shown_with_its_views_and_camera(tmp_path,monkeypatch):
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path))
    import os
    os.makedirs(env.live_dir(),exist_ok=True)
    env.write_json(os.path.join(env.live_dir(),'meta.json'),{'project':'old','name':'tower','sets':{'Main':{}}})
    env.save_views('old',[{'name':'Street'}]);env.save_settings({'view':{'project':'old','cam':[1,2,3]}})
    assert env.follow_copy('old','new','tower v2') is True
    assert env.current_project()=='new' and env.current_meta()['name']=='tower v2' and env.current_meta()['sets']=={'Main':{}}
    assert env.load_views('new')==[{'name':'Street'}] and env.load_views('old')==[{'name':'Street'}]   # the original keeps its own
    assert env.load_settings()['view']=={'project':'new','cam':[1,2,3]}
    env.save_views('new',[{'name':'Roof'}])
    assert env.follow_copy('old','newer') is False and env.load_views('newer')==[{'name':'Street'}]   # not shown: only the views come along
    assert env.load_views('new')==[{'name':'Roof'}]
