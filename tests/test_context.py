import json,math,struct,time,zlib
import pytest
from earthlink import context as C, env, server

LAT,LON=42.4405,-76.5108
BOUNDS={'west':LON-0.0015,'east':LON+0.0015,'south':LAT-0.001,'north':LAT+0.001}

def png(w,h,px):
    raw=b''.join(b'\x00'+b''.join(bytes(px(x,y)) for x in range(w)) for y in range(h))
    ch=lambda t,d:struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b'')

def terrarium(elev):
    v=elev+32768.0;return (int(v//256),int(v)%256,int((v%1)*256))

def world(slope=0.0):
    """Elevation 250 m plus `slope` m per metre northward; one square building and one road through the site."""
    def fetch(url,data=None,timeout=0):
        if 'terrarium' in url:
            z,x,y=[int(v) for v in url.split('terrarium/')[1][:-4].split('/')]
            def px(i,j):
                n=2.0**z;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*(y+(j+0.5)/256)/n))))
                return terrarium(250.0+slope*(lat-LAT)*111000.0)
            return png(256,256,px)
        if 'api.openstreetmap.org' in url:raise OSError('unreachable')   # these tests answer as the Overpass fallback does
        d=0.0002
        sq=[{'lat':LAT+a*d,'lon':LON+b*d*1.4} for a,b in ((-1,-1),(-1,1),(1,1),(1,-1),(-1,-1))]
        far=[{'lat':LAT+0.01+a*d,'lon':LON+b*d} for a,b in ((-1,-1),(-1,1),(1,1),(1,-1),(-1,-1))]
        return json.dumps({'elements':[
            {'type':'way','id':1,'tags':{'building':'yes','building:levels':'4','name':'Hall'},'geometry':sq},
            {'type':'way','id':2,'tags':{'building':'yes'},'geometry':[{'lat':p['lat']+0.0006,'lon':p['lon']} for p in sq]},
            {'type':'way','id':3,'tags':{'building':'yes','height':'30'},'geometry':far},
            {'type':'way','id':4,'tags':{'highway':'residential','name':'Main St'},'geometry':[{'lat':LAT,'lon':LON-0.01},{'lat':LAT,'lon':LON+0.01}]}]}).encode()
    return fetch

ANCHOR={'lat':LAT,'lon':LON,'elev':0.0,'zero':'GroundLevel'}

def test_flat_ground_lands_on_the_site_ground_and_curves_with_the_earth():
    out=C.build(BOUNDS,ANCHOR,{},fetch=world())
    t=out['terrain'];pts=t['points'];nx,ny=t['nx'],t['ny']
    assert out['size']==[pytest.approx(246.8,abs=0.5),pytest.approx(222.2,abs=0.5)]
    assert len(pts)==nx*ny and max(nx,ny)<=C.GRID+1
    centre=min(pts,key=lambda p:p[0]**2+p[1]**2)
    assert abs(centre[2])<0.01,'the terrain passes through the site ground at the site location'
    corner=pts[0];assert corner[0]==pytest.approx(-123.4,abs=0.3) and corner[1]==pytest.approx(-111.1,abs=0.3)
    assert -0.01<corner[2]<0,'166 m away the ground is 2 mm lower: the Earth curves, as the map does'
    assert out['attribution'].startswith('Buildings, roads, railways and water (c) OpenStreetMap')

def test_sloping_ground_buildings_and_roads():
    out=C.build(BOUNDS,ANCHOR,{},fetch=world(slope=0.1))
    north=max(out['terrain']['points'],key=lambda p:p[1]);assert north[2]==pytest.approx(0.1*north[1],abs=0.3)
    assert out['counts']['buildings']==2,'only buildings centred in the rectangle, never a cut one'
    hall,other=out['buildings']
    assert hall['name']=='Hall' and hall['height']==pytest.approx(12.8) and hall['assumed'] is False and len(hall['outer'])==4
    assert other['height']==C.DEFAULT_HEIGHT and other['assumed'] is True
    lowest=min(p[1] for p in hall['outer'])*0.1;assert hall['base']==pytest.approx(lowest,abs=0.3),'a building stands on its lowest corner'
    road=out['roads'][0];assert road['name']=='Main St' and road['kind']=='residential'
    assert road['pts'][0][0]==pytest.approx(-123.4,abs=0.3) and road['pts'][-1][0]==pytest.approx(123.4,abs=0.3),'roads are cut at the rectangle'

def test_height_reference_follows_the_anchor():
    ground=C.build(BOUNDS,dict(ANCHOR,elev=2.0),{'nudge':0.5},buildings=False,roads=False,fetch=world())
    assert min(ground['terrain']['points'],key=lambda p:p[0]**2+p[1]**2)[2]==pytest.approx(-2.5,abs=0.01),'base point 2 m above ground, nudged 0.5 m up'
    sea=C.build(BOUNDS,dict(ANCHOR,elev=240.0,zero='MeanSeaLevel'),{},buildings=False,roads=False,fetch=world())
    assert min(sea['terrain']['points'],key=lambda p:p[0]**2+p[1]**2)[2]==pytest.approx(10.0,abs=0.01)

def test_rectangles_are_checked():
    with pytest.raises(C.ContextError,match='limit'):C.check_bounds({'west':LON-0.03,'east':LON+0.03,'south':LAT,'north':LAT+0.001})
    with pytest.raises(C.ContextError,match='small'):C.check_bounds({'west':LON,'east':LON+0.00001,'south':LAT,'north':LAT+0.001})
    with pytest.raises(C.ContextError):C.check_bounds({'west':'x'})
    with pytest.raises(C.ContextError,match='Place the model'):C.build(BOUNDS,{},{},fetch=world())

def test_osm_details():
    assert C.building_height({'height':'40 ft'})[0]==pytest.approx(12.19,abs=0.01)
    assert C.building_height({'height':'tall'})==(C.DEFAULT_HEIGHT,True)
    ring=lambda *p:[{'lat':a,'lon':b} for a,b in p]
    rel={'elements':[{'type':'relation','tags':{'building':'yes','type':'multipolygon'},'members':[
        {'type':'way','role':'outer','geometry':ring((0,0),(0,4),(4,4))},{'type':'way','role':'outer','geometry':ring((4,4),(4,0),(0,0))},
        {'type':'way','role':'inner','geometry':ring((1,1),(1,2),(2,2),(2,1),(1,1))}]}]}
    b,_=C.parse_osm(rel);assert len(b)==1 and len(b[0]['outer'])==4 and len(b[0]['inners'])==1,'outer ways are joined; the courtyard is kept'
    assert C.clip_line([(0,-5),(0,5)],{'west':-1,'east':1,'south':-1,'north':1})==[[(0.0,-1.0),(0.0,1.0)]]
    assert C.clip_line([(5,5),(6,6)],{'west':-1,'east':1,'south':-1,'north':1})==[]

def test_server_runs_the_import_and_hands_it_to_rhino(tmp_path,monkeypatch):
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path));import os;os.makedirs(env.live_dir(),exist_ok=True)
    env.write_json(env.live_file('meta.json'),{'project':'p1','version':1,'sets':{},'anchor':ANCHOR})
    server._CONTEXT.clear();server._CONTEXT.update(state='idle')
    bad=server._context_start({'bounds':{'west':0,'east':1,'south':0,'north':1}});assert bad['state']=='error' and 'limit' in bad['message']
    started=server._context_start({'bounds':BOUNDS,'roads':False},build=lambda b,a,s,progress,**want:(progress('Reading'),C.build(b,a,s,fetch=world(),**want))[1])
    assert started['state']=='working'
    for _ in range(200):
        if server._context_status()['state']!='working':break
        time.sleep(0.05)
    st=server._context_status();assert st['state']=='sent' and st['counts']['buildings']==2 and st['counts']['roads']==0
    reqs=os.listdir(env.live_file('requests'));req=env.read_json(os.path.join(env.live_file('requests'),reqs[0]))
    assert req['type']=='context' and req['project']=='p1' and os.path.exists(env.live_file(req['file']))
    server._CONTEXT['sent_at']=time.time()-200                       # long past the wait, but Rhino has picked it up: no clock while it adds
    env.write_json(env.live_file('context_result.json'),{'file':req['file'],'started':True})
    assert server._context_status()['state']=='sent' and os.path.exists(env.live_file(req['file']))
    env.write_json(env.live_file('context_result.json'),{'file':req['file'],'ok':True,'message':'Rhino added terrain.'})
    assert server._context_status()=={'state':'done','message':'Rhino added terrain.','job':req['file'],'counts':st['counts'],'progress':0.9}


def test_an_import_rhino_never_picked_up_is_withdrawn(tmp_path,monkeypatch):
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path));import os;os.makedirs(env.live_dir(),exist_ok=True)
    env.write_json(env.live_file('context_7.json'),{'terrain':{}})
    server._CONTEXT.clear();server._CONTEXT.update(state='sent',job='context_7.json',message='Rhino is adding it',sent_at=time.time()-91)
    st=server._context_status();assert st['state']=='error' and 'did not answer' in st['message']
    assert not os.path.exists(env.live_file('context_7.json'))      # Rhino, back later, finds nothing to add beside the next import


def osm_map(limit=None):
    """OpenStreetMap's own map download: points, ways and relations listed separately. With `limit`, an area wider
    than that many degrees answers 'too many nodes', as the real server does for crowded areas."""
    calls=[]
    def fetch(url,data=None,timeout=0):
        if 'terrarium' in url:return world()(url)
        assert 'api.openstreetmap.org/api/0.6/map.json?bbox=' in url and data is None,'the map download comes first: '+url
        w,s_,e,n=[float(v) for v in url.split('bbox=')[1].split(',')];calls.append((w,s_,e,n))
        if limit and e-w>limit:raise C.ContextError('HTTP 400 You requested too many nodes (limit is 50000). Either request a smaller area, or use planet.osm')
        d=0.0002;nodes=[];ways=[]
        def way(i,tags,pts,close=True):
            ids=[]
            for k,(la,lo) in enumerate(pts):nodes.append({'type':'node','id':i*100+k,'lat':la,'lon':lo});ids.append(i*100+k)
            ways.append({'type':'way','id':i,'nodes':ids+(ids[:1] if close else []),'tags':tags})
        sq=lambda la,lo,k=1.0:[(la-d*k,lo-d*k),(la-d*k,lo+d*k),(la+d*k,lo+d*k),(la+d*k,lo-d*k)]
        way(1,{'building':'yes','height':'12 m'},sq(LAT,LON-0.0008))
        way(2,{'highway':'service'},[(LAT+0.0005,LON-0.01),(LAT+0.0005,LON-0.0025),(LAT+0.0005,LON+0.01)],close=False)   # one point just outside the rectangle, none inside
        way(3,{},sq(LAT,LON+0.0008,2.0));way(4,{},sq(LAT,LON+0.0008,0.5))               # a courtyard building: outer and inner ring
        ways.append({'type':'way','id':5,'nodes':[999001,999002],'tags':{'building':'yes'}})       # its points are not in the answer: skipped
        rel={'type':'relation','id':9,'tags':{'type':'multipolygon','building':'yes','building:levels':'3'},'members':[{'type':'way','ref':3,'role':'outer'},{'type':'way','ref':4,'role':'inner'}]}
        inside=lambda el:any(w<=x['lon']<=e and s_<=x['lat']<=n for x in nodes if x['id']//100==el['id'])
        keep=[x for x in ways if x['id']==5 or inside(x)]
        return json.dumps({'version':'0.6','elements':nodes+keep+[rel]}).encode()
    return fetch,calls

def test_openstreetmaps_own_map_download_is_read_first():
    fetch,calls=osm_map();out=C.build(BOUNDS,ANCHOR,{},terrain=False,fetch=fetch)
    pad_lat=C.PAD/111320.0;assert len(calls)==1 and calls[0][1]==pytest.approx(BOUNDS['south']-pad_lat) and calls[0][3]==pytest.approx(BOUNDS['north']+pad_lat)
    assert calls[0][0]<BOUNDS['west']-0.002 and calls[0][2]>BOUNDS['east']+0.002,'a wider area is asked for, so that a street crossing between two of its points is found'
    assert out['counts']['buildings']==2 and out['counts']['roads']==1
    plain=[b for b in out['buildings'] if not b['inners']][0];yard=[b for b in out['buildings'] if b['inners']][0]
    assert plain['height']==12.0 and len(plain['outer'])==4
    assert yard['height']==pytest.approx(3*C.LEVEL) and len(yard['inners'])==1 and len(yard['inners'][0])==4
    assert out['roads'][0]['kind']=='service'

def test_a_crowded_area_is_downloaded_in_quarters_and_nothing_comes_twice():
    fetch,calls=osm_map(limit=0.005);out=C.build(BOUNDS,ANCHOR,{},terrain=False,fetch=fetch)
    assert len(calls)==5,'the whole rectangle once, then its four quarters'
    assert out['counts']['buildings']==2 and out['counts']['roads']==1,'the road crosses two quarters and is still one road'

def test_without_openstreetmap_the_message_says_so():
    def fetch(url,data=None,timeout=0):
        if 'terrarium' in url:return world()(url)
        raise OSError('timed out')
    with pytest.raises(C.ContextError,match='OpenStreetMap could not be reached'):C.build(BOUNDS,ANCHOR,{},fetch=fetch)


def test_contours_at_round_heights_and_chosen_building_heights():
    out=C.build(BOUNDS,ANCHOR,{},fetch=world(slope=0.1),contours=2.0,default_height=10.0,level_height=4.0)
    cs=out['contours'];assert out['contour_interval']==2.0 and out['counts']['contours']==len(cs)>=8
    assert all(abs(c['elevation']/2.0-round(c['elevation']/2.0))<1e-9 for c in cs),'lines at multiples of the interval above sea level'
    ground=250.0                                            # the site ground is 250 m above sea level and is height 0 of the model
    for c in cs:
        assert len(c['pts'])>=2 and all(abs(p[2]-(c['elevation']-ground))<0.02 for p in c['pts']),'each line lies at its own height'
        assert abs(c['pts'][0][1]-c['pts'][-1][1])<1.0 and abs(c['pts'][0][0]-c['pts'][-1][0])>200,'on ground rising to the north the lines run east-west, right across'
        assert abs(c['pts'][0][1]-(c['elevation']-ground)/0.1)<1.5,'where the ground has that height'
    hall,other=out['buildings'];assert hall['height']==pytest.approx(16.0) and other['height']==10.0 and other['assumed']
    assert hall['tags']['building:levels']=='4' and out['roads'][0]['tags']['highway']=='residential'
    only=C.build(BOUNDS,ANCHOR,{},fetch=world(slope=0.1),terrain=False,buildings=False,roads=False,contours=5.0)
    assert only['terrain'] is None and len(only['contours'])>=3
    flat=C.build(BOUNDS,ANCHOR,{},fetch=world(),contours=1.0,buildings=False,roads=False);assert flat['contours']==[],'flat ground has no contour lines'

def test_contour_lines_close_around_a_hill():
    nx=ny=21;val=lambda i,j:10.0-((i-10)**2+(j-10)**2)**0.5
    lines=C.contour_lines(nx,ny,val,lambda fi,fj,e:[fi,fj,e],2.0)
    assert [l['elevation'] for l in lines]==[-4.0,-2.0,0.0,2.0,4.0,6.0,8.0] or len(lines)>=5
    ring=[l for l in lines if l['elevation']==6.0];assert len(ring)==1,'one closed ring per height'
    p=ring[0]['pts'];assert abs(p[0][0]-p[-1][0])<1e-6 and abs(p[0][1]-p[-1][1])<1e-6 and all(abs(((q[0]-10)**2+(q[1]-10)**2)**0.5-4.0)<0.35 for q in p)


def lines_world(slope=0.0, extra=()):
    """world(), with a primary road, a footway, a bridge over a 20 m deep dip, a railway, a stream, a pond and a lake
    that OpenStreetMap's map download gives only in part (its relation is fetched whole from Overpass)."""
    base=world(slope)
    E=lambda *p:[{'lat':LAT+a,'lon':LON+b} for a,b in p]
    lake=E((-0.003,-0.003),(-0.003,0.0005),(-0.0006,0.0005),(-0.0006,-0.003),(-0.003,-0.003))
    island=E((-0.0009,-0.0005),(-0.0009,-0.0003),(-0.0007,-0.0003),(-0.0007,-0.0005),(-0.0009,-0.0005))
    calls=[]
    def fetch(url,data=None,timeout=0):
        calls.append((url,data))
        if 'terrarium' in url:
            z,x,y=[int(v) for v in url.split('terrarium/')[1][:-4].split('/')]
            def px(i,j):
                n=2.0**z;lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*(y+(j+0.5)/256)/n))));lon=(x+(i+0.5)/256)/n*360-180
                dip=-20.0 if abs(lat-(LAT+0.0005))<0.00012 else 0.0          # a gorge running east-west north of the site
                return terrarium(250.0+slope*(lat-LAT)*111000.0+dip)
            return png(256,256,px)
        if 'api.openstreetmap.org' in url:raise OSError('unreachable')
        if data and b'relation%28id' in data:                  # the lake, whole
            return json.dumps({'elements':[{'type':'relation','id':77,'tags':{'natural':'water','name':'Lake'},'members':[
                {'type':'way','role':'outer','geometry':lake},{'type':'way','role':'inner','geometry':island}]}]}).encode()
        els=json.loads(base(url,data))['elements']+[
            {'type':'way','id':10,'tags':{'highway':'primary','lanes':'4'},'geometry':E((-0.0003,-0.01),(-0.0003,0.01))},
            {'type':'way','id':11,'tags':{'highway':'footway'},'geometry':E((-0.0009,-0.0005),(0.0009,-0.0005))},
            {'type':'way','id':12,'tags':{'highway':'tertiary','bridge':'yes','width':'9'},'geometry':E((0.0002,0.0008),(0.0008,0.0008))},
            {'type':'way','id':13,'tags':{'highway':'construction'},'geometry':E((0,0),(0.0005,0.0005))},
            {'type':'way','id':14,'tags':{'railway':'rail','name':'Line'},'geometry':E((0.0009,-0.01),(0.0009,0.01))},
            {'type':'way','id':15,'tags':{'railway':'abandoned'},'geometry':E((0.0008,-0.01),(0.0008,0.01))},
            {'type':'way','id':16,'tags':{'waterway':'stream'},'geometry':E((-0.001,0.001),(0.001,0.0012))},
            {'type':'way','id':17,'tags':{'natural':'water','water':'pond'},'geometry':E((0.0003,0.001),(0.0003,0.0012),(0.0005,0.0012),(0.0005,0.001),(0.0003,0.001))},
            {'type':'relation','id':77,'tags':{'natural':'water'},'members':[{'type':'way','role':'outer','geometry':[]}]}]+list(extra)
        return json.dumps({'elements':els}).encode()
    return fetch,calls

def test_roads_are_sorted_like_cadmapper_with_their_widths_and_rails_and_water_on_their_own():
    fetch,calls=lines_world()
    out=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False)
    by={r['kind']:r for r in out['roads']}
    assert set(by)=={'residential','primary','footway','tertiary'},'a road under construction is left out'
    assert by['primary']['class']=='major' and by['primary']['width']==pytest.approx(13.2),'four lanes'
    assert by['residential']['class']=='minor' and by['residential']['width']==7.0 and by['footway']['class']=='path'
    assert by['tertiary']['width']==9.0,'a width OpenStreetMap gives wins'
    assert out['counts']['roads']==3 and out['counts']['paths']==1
    pts=by['residential']['pts'];assert len(pts)>=100 and max(math.hypot(q[0]-p[0],q[1]-p[1]) for p,q in zip(pts,pts[1:]))<=2.01,'lines get points every few metres, to follow the ground'
    bridge=by['tertiary']['pts'];assert max(abs(p[2]) for p in bridge)<0.05,'a bridge runs straight between its ends, over the dip'
    assert min(p[2] for p in by['footway']['pts'])<-15 and max(abs(p[2]) for p in out['railways'][0]['pts'])<0.05,'other lines follow the ground, down into the dip'
    assert [r['kind'] for r in out['railways']]==['rail'] and out['railways'][0]['name']=='Line','an abandoned line is left out'
    stream=[w for w in out['water'] if not w.get('closed')];assert len(stream)==1 and stream[0]['kind']=='stream'
    pond=[w for w in out['water'] if w.get('kind')=='pond'];assert len(pond)==1 and len(pond[0]['pts'])==4
    lake=[w for w in out['water'] if w.get('name')=='Lake' and not w.get('island')]
    assert len(lake)==1 and any(b'relation%28id%3A77' in (d or b'') for u,d in calls),'the lake is fetched whole'
    xs=[p[0] for p in lake[0]['pts']];ys=[p[1] for p in lake[0]['pts']]
    assert min(xs)==pytest.approx(-123.4,abs=0.3) and min(ys)==pytest.approx(-111.1,abs=0.3),'and cut at the rectangle'
    assert max(p[2] for p in lake[0]['pts'])-min(p[2] for p in lake[0]['pts'])<0.01,'flat, at the water level (but for the curve of the Earth)'
    assert any(w.get('island') for w in out['water']),'an island stays an island'
    only=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False,paths=False,railways=False,water=False)
    assert {r['class'] for r in only['roads']}=={'major','minor'} and only['railways']==[] and only['water']==[]
    q=C.overpass_query(BOUNDS,True,True,True,True);assert '["railway"]' in q and '["natural"="water"]' in q

def test_road_outlines_and_surfaces_are_meshes_cut_to_the_rectangle():
    fetch,_=lines_world(slope=0.05)
    lines=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False)
    assert 'road_meshes' not in lines and lines['road_styles']==['lines']
    out=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False,road_style='surfaces')
    assert out['road_styles']==['surfaces'] and set(out['road_meshes'])=={'major','minor','path'}
    for cls,m in out['road_meshes'].items():
        v,f=m['v'],m['f'];assert v and f and all(len(x) in (3,4) and max(x)<len(v) for x in f)
        assert all(-123.5<=p[0]<=123.5 and -111.2<=p[1]<=111.2 for p in v),'nothing beyond the rectangle'
        for x in f:                                          # faces point up
            a,b,c=(v[i] for i in x[:3]);assert (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])>=-1e-6
    major=out['road_meshes']['major']['v'];ys=sorted({round(p[1],1) for p in major})
    road_y=out['roads'][[r['kind'] for r in out['roads']].index('primary')]['pts'][0][1]
    assert max(ys)-min(ys)==pytest.approx(13.2,abs=0.05) and (max(ys)+min(ys))/2==pytest.approx(road_y,abs=0.05),'as wide as the road, on its line'
    for q in major:assert q[2]==pytest.approx(0.05*q[1]+C.LIFT['major'],abs=0.05),'on the ground right across, a little above it'
    over=[q for q in out['road_meshes']['minor']['v'] if 60<q[0]<72 and 50<q[1]<60]
    assert over and all(abs(q[2]-(0.05*q[1]+C.LIFT['minor']))<0.3 for q in over),'the bridge stays up, right across, over the 20 m dip'
    outl=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False,road_style='outlines')
    assert outl['road_meshes'].keys()==out['road_meshes'].keys(),'Rhino draws outlines around the same surfaces'

def test_strip_turns_and_ends():
    m=C.Mesh([]);m.strip([(0,0,0),(10,0,0),(10,10,1)],4.0)
    xs=[p[0] for p in m.v];ys=[p[1] for p in m.v]
    assert min(xs)==pytest.approx(-2) and max(xs)==pytest.approx(12) and max(ys)==pytest.approx(12),'round ends: half the width beyond each end'
    corner=[p for p in m.v if p[0]>11.9 and p[1]<-1.9];assert corner,'the outer corner is mitred, the road keeps its width'
    sharp=C.Mesh([]);sharp.strip([(0,0,0),(10,0,0),(0,1,0)],2.0);assert max(p[0] for p in sharp.v)<=11.01,'a hairpin gets a round corner, no spike'
    assert C.clip_ring([(0,-5),(0,5),(5,5),(5,-5)],{'west':-1,'east':1,'south':-1,'north':1})==[(0,-1.0),(0,1.0),(1.0,1.0),(1.0,-1.0)] or len(C.clip_ring([(0,-5),(0,5),(5,5),(5,-5)],{'west':-1,'east':1,'south':-1,'north':1}))==4

def test_buildings_without_a_known_height_can_stay_footprints():
    out=C.build(BOUNDS,ANCHOR,{},fetch=world(),terrain=False,roads=False,assume_height=False)
    hall,other=out['buildings'];assert hall['height']==pytest.approx(12.8) and other['assumed'] and other['height']==0.0

def test_the_panels_choices_reach_the_build(tmp_path,monkeypatch):
    monkeypatch.setattr(env,'data_dir',lambda:str(tmp_path));import os;os.makedirs(env.live_dir(),exist_ok=True);env.write_json(env.live_file('meta.json'),{'anchor':ANCHOR,'project':'p'})
    seen=[]
    def build(b,a,s,progress,**want):
        seen.append(want);raise C.ContextError('stop here')
    for n,ask in enumerate(({'road_styles':['surfaces','outlines','zigzag'],'paths':False,'water':False,'assume_height':False,'parcels':True},{'road_style':'zigzag','parcels':'yes'})):
        server._CONTEXT.clear();server._context_start(dict(ask,bounds=BOUNDS),build=build)
        for _ in range(100):
            if len(seen)>n:break
            time.sleep(0.02)
    a,b=seen
    assert a['road_style']==['outlines','surfaces'] and a['parcels'] is True and a['paths'] is False and a['water'] is False and a['assume_height'] is False and a['railways'] is True
    assert b['road_style']==['lines'] and b['paths'] and b['water'] and b['assume_height'],'anything else: centrelines, everything in'
    assert b['parcels'] is False,'parcels come from another server: only when asked for in so many words'


def parcel_service(features, calls, error=None):
    def fetch(url,data=None,timeout=0):
        calls.append(url)
        if error:raise C.ContextError(error)
        return json.dumps({'type':'FeatureCollection','features':features}).encode()
    return fetch

def test_parcels_come_as_lot_lines_on_the_ground_with_their_address_and_never_their_owner():
    sq=lambda la,lo,d:[[lo,la],[lo+d,la],[lo+d,la+d],[lo,la+d],[lo,la]]
    feats=[{'type':'Feature','properties':{'PARCEL_ADDR':'100 Main St','SWIS_SBL_ID':'500700-1.-1-1','ACRES':0.3,'PRIMARY_OWNER':'Someone'},
            'geometry':{'type':'Polygon','coordinates':[sq(LAT-0.0002,LON-0.0002,0.0004)]}},
           {'type':'Feature','properties':{'PARCEL_ADDR':'Farm'},'geometry':{'type':'MultiPolygon','coordinates':[[sq(LAT-0.01,LON-0.01,0.02)]]}}]
    calls=[];base=world(slope=0.1)
    svc=parcel_service(feats,calls)
    fetch=lambda url,data=None,timeout=0:svc(url) if 'nysgeohub' in url else base(url,data)
    out=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False,roads=False,paths=False,railways=False,water=False,parcels=True)
    assert len(calls)==1 and 'outFields=' in calls[0] and 'OWNER' not in calls[0] and 'MAIL' not in calls[0],'owners and mailing addresses are never asked for'
    assert 'esriGeometryEnvelope' in calls[0] and 'outSR=4326' in calls[0]
    lot,farm=out['parcels'];assert lot['address']=='100 Main St' and lot['id']=='500700-1.-1-1' and 'PRIMARY_OWNER' not in lot['tags']
    assert len(lot['pts'])>=4 and all(p[2]==pytest.approx(0.1*p[1],abs=0.3) for p in lot['pts']),'on the ground'
    xs=[p[0] for p in farm['pts']];assert min(xs)==pytest.approx(-123.4,abs=0.3) and max(xs)==pytest.approx(123.4,abs=0.3),'a big lot is cut at the rectangle'
    assert out['counts']['parcels']==2 and 'Parcels:' in out['attribution'] and 'parcel_note' not in out
    none=C.build(BOUNDS,ANCHOR,{},fetch=world(),terrain=False,buildings=False,roads=False,paths=False,railways=False,water=False)
    assert none['parcels']==[],'not asked for: nothing is sent to the parcel service'
    far=C.check_bounds({'west':2.29,'east':2.30,'south':48.85,'north':48.86})
    calls2=[];assert C.fetch_parcels(far,parcel_service(feats,calls2))==[] and calls2==[],'outside New York State the service is not asked'
    with pytest.raises(C.ContextError,match='parcel service could not be reached'):C.fetch_parcels(BOUNDS,parcel_service([],[],error='HTTP 500'))
    empty=C.build(BOUNDS,ANCHOR,{},fetch=lambda u,d=None,t=0:parcel_service([],[])(u) if 'nysgeohub' in u else base(u,d),terrain=False,buildings=False,roads=False,paths=False,railways=False,water=False,parcels=True)
    assert 'no parcels found' in empty['parcel_note']

def test_several_road_geometries_at_once():
    fetch,_=lines_world()
    out=C.build(BOUNDS,ANCHOR,{},fetch=fetch,terrain=False,buildings=False,road_style=['lines','surfaces','outlines'])
    assert out['road_styles']==['lines','outlines','surfaces'] and out['roads'] and set(out['road_meshes'])=={'major','minor','path'}
