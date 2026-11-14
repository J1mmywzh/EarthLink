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
    assert out['attribution'].startswith('Buildings and roads (c) OpenStreetMap')

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
    env.write_json(env.live_file('context_result.json'),{'file':req['file'],'ok':True,'message':'Rhino added terrain.'})
    assert server._context_status()=={'state':'done','message':'Rhino added terrain.','job':req['file'],'counts':st['counts'],'progress':0.9}


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
