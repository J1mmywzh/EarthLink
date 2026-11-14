const{test,before,after}=require('node:test');
const assert=require('node:assert/strict');
const{chromium}=require(process.env.EARTHLINK_PLAYWRIGHT||'playwright');
const base=process.argv[2]||'http://127.0.0.1:8765/';let browser;
before(async()=>{browser=await chromium.launch({headless:true,executablePath:process.env.EARTHLINK_CHROME||undefined,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});});
after(async()=>{await browser?.close();});
async function pageFor(t,setup,controls){const p=await browser.newPage({viewport:{width:1280,height:800},ignoreHTTPSErrors:!!process.env.EARTHLINK_IGNORE_HTTPS});t.after(()=>p.close());await p.addInitScript(()=>localStorage.setItem('earthlink:skipKeys','true'));if(setup)await setup(p);const u=new URL(base);if(controls)u.searchParams.set('controls',controls);await p.goto(u.href);await p.waitForFunction(()=>window.EL&&EL.models.Main?._elGeometry,null,{timeout:60000});return p;}
async function startWalk(p){await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});const roof=await p.evaluate(()=>{const M=EL.models.Main.modelMatrix,world=Cesium.Matrix4.multiplyByPoint(M,new Cesium.Cartesian3(15,2.5,10),new Cesium.Cartesian3()),p=Cesium.SceneTransforms.worldToWindowCoordinates(EL.viewer.scene,world);return{x:p.x,y:p.y};});await p.getByRole('button',{name:'Walk',exact:true}).click();await p.mouse.click(roof.x,roof.y);await p.waitForFunction(()=>EL.walk?.body,null,{timeout:15000});}
test('the orbit pivot is the centre of the current view, also after panning',async t=>{const p=await pageFor(t);const centre=()=>p.evaluate(()=>{const s=EL.viewer.scene,ray=EL.viewer.camera.getPickRay(new Cesium.Cartesian2(s.canvas.clientWidth/2,s.canvas.clientHeight/2)),t=EL.surfaceHit(ray),q=t===null?null:Cesium.Ray.getPoint(ray,t);return q&&[q.x,q.y,q.z];});await p.mouse.move(640,400);await p.mouse.down({button:'right'});await p.keyboard.down('Shift');await p.mouse.move(560,380,{steps:6});await p.keyboard.up('Shift');await p.mouse.up({button:'right'});await p.waitForTimeout(400);const c0=await centre();await p.mouse.down({button:'right'});await p.mouse.move(700,400,{steps:6});await p.mouse.up({button:'right'});await p.waitForTimeout(400);const c1=await centre();assert.ok(c0&&c1&&Math.hypot(...c0.map((v,i)=>v-c1[i]))<1.5);});
test('upward Two-Point framing survives zooming',async t=>{const p=await pageFor(t);await p.evaluate(()=>{const c=EL.captureCamera('up');EL.applyView({...c,projection:'two_point',dir:[0,1,0],up:[0,0,1],shift:.5},0);EL.nav.zoomStep(-1);});await p.waitForTimeout(500);assert.ok(Math.abs(await p.evaluate(()=>EL.viewer.camera.frustum._elShift)-.5)<.001);});
test('choosing a projection leaves Walk',async t=>{const p=await pageFor(t);await startWalk(p);await p.getByRole('button',{name:'Parallel',exact:true}).click();assert.equal(await p.evaluate(()=>!!EL.walk),false);assert.equal(await p.evaluate(()=>EL.captureCamera('p').projection),'parallel');});
test('changing cutout releases the walking body and contacts',async t=>{const p=await pageFor(t);await startWalk(p);await p.getByRole('button',{name:'Hide the map underneath this set',exact:true}).first().click();assert.equal(await p.evaluate(()=>!!EL.walk),false);assert.equal(await p.getByRole('button',{name:'Walk',exact:true}).getAttribute('aria-pressed'),'false');});
test('an older delayed export cannot replace the latest live model',async t=>{
 let release;const gate=new Promise(r=>release=r);let latestVersion,lateSent;
 const p=await pageFor(t,async p=>{const meta=await(await p.request.get(new URL('/api/meta',base).href)).json(),newer=JSON.parse(JSON.stringify(meta));newer.version++;latestVersion=newer.sets.Main.version+100;newer.sets.Main.version=latestVersion;const binary=await(await p.request.get(new URL('/live/'+meta.sets.Main.glb,base).href)).body();
 await p.route('**/events',route=>route.fulfill({status:200,contentType:'text/event-stream',body:'retry: 100000\n\nevent: model\ndata: '+JSON.stringify(meta)+'\n\nevent: model\ndata: '+JSON.stringify(newer)+'\n\n'}));
 await p.route('**/live/'+meta.sets.Main.glb+'?v='+meta.sets.Main.version,async route=>{await gate;await route.fulfill({status:200,contentType:'model/gltf-binary',body:binary});lateSent=true;});});
 await p.waitForFunction(v=>EL.models.Main?._elVersion===v,latestVersion,{timeout:15000});release();await p.waitForTimeout(1200);assert.equal(lateSent,true);assert.equal(await p.evaluate(()=>EL.models.Main._elVersion),latestVersion);
});

const cam=p=>p.evaluate(()=>{EL.viewer.render();const c=EL.viewer.camera;return{pos:[c.positionWC.x,c.positionWC.y,c.positionWC.z],dir:[c.directionWC.x,c.directionWC.y,c.directionWC.z],heading:Cesium.Math.toDegrees(c.heading)};});
const d3=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i])),turn=d=>((d%360)+540)%360-180;
const roofPoint=p=>p.evaluate(()=>{const M=EL.models.Main.modelMatrix,w=Cesium.Matrix4.multiplyByPoint(M,new Cesium.Cartesian3(15,2.5,10),new Cesium.Cartesian3()),q=Cesium.SceneTransforms.worldToWindowCoordinates(EL.viewer.scene,w);return{x:q.x,y:q.y};});
test('Windows: two-finger scrolling zooms, as in Rhino for Windows',async t=>{const p=await pageFor(t,null,'windows');await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(400);
 const a=await cam(p);await p.evaluate(async()=>{const c=EL.viewer.scene.canvas,r=c.getBoundingClientRect();for(let i=0;i<20;i++){c.dispatchEvent(new WheelEvent('wheel',{deltaX:0,deltaY:-4,deltaMode:0,clientX:r.left+r.width/2,clientY:r.top+r.height/2,bubbles:true,cancelable:true}));await new Promise(f=>setTimeout(f,16));}});await p.waitForTimeout(500);
 const b=await cam(p);assert.ok(Math.abs(turn(b.heading-a.heading))<0.05,'no orbit');assert.ok(d3(a.pos,b.pos)>0.5,'zoomed');});
test('Rhino keys: arrows rotate, Page Down zooms out',async t=>{const p=await pageFor(t,null,'windows');await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(400);
 const a=await cam(p);for(let i=0;i<3;i++)await p.keyboard.press('ArrowLeft');await p.waitForTimeout(500);const b=await cam(p);assert.ok(Math.abs(turn(b.heading-a.heading))>12,'arrows rotate '+turn(b.heading-a.heading));
 const c0=await p.evaluate(()=>{const s=EL.viewer.scene,r=EL.viewer.camera.getPickRay(new Cesium.Cartesian2(s.canvas.clientWidth/2,s.canvas.clientHeight/2));return EL.surfaceHit(r);});
 await p.keyboard.press('PageDown');await p.waitForTimeout(600);
 const c1=await p.evaluate(()=>{const s=EL.viewer.scene,r=EL.viewer.camera.getPickRay(new Cesium.Cartesian2(s.canvas.clientWidth/2,s.canvas.clientHeight/2));return EL.surfaceHit(r);});assert.ok(c1>c0*1.2,'Page Down zooms out '+c0+' '+c1);});
test('Rhino mouse: Alt + right-drag dollies, Ctrl + Alt + right-drag turns the camera in place',async t=>{const p=await pageFor(t,null,'windows');await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(400);
 const drag=async(mods,dx,dy)=>{for(const m of mods)await p.keyboard.down(m);await p.mouse.move(640,400);await p.mouse.down({button:'right'});await p.mouse.move(640+dx,400+dy,{steps:8});await p.mouse.up({button:'right'});for(const m of mods)await p.keyboard.up(m);await p.waitForTimeout(500);};
 let a=await cam(p);await drag(['Alt'],0,-80);let b=await cam(p);assert.ok(d3(a.pos,b.pos)>0.5&&d3(a.dir,b.dir)<1e-3,'dolly moves along the view');
 a=await cam(p);await drag(['Control','Alt'],80,0);b=await cam(p);assert.ok(d3(a.pos,b.pos)<0.5&&Math.abs(turn(b.heading-a.heading))>3,'camera turns where it stands '+JSON.stringify({moved:d3(a.pos,b.pos),turned:turn(b.heading-a.heading)}));});
test('each set has its own Hide map underneath switch',async t=>{const p=await pageFor(t);const btn=p.locator('#sets .item').first().getByRole('button',{name:'Hide the map underneath this set',exact:true});
 const sets=async()=>(await(await p.request.get(new URL('/api/settings',base).href)).json()).clip_sets||[];   // an earlier test may have left it on
 const was=(await sets()).includes('Main');
 await btn.click();await p.waitForTimeout(300);assert.equal((await sets()).includes('Main'),!was);assert.equal(await btn.getAttribute('aria-pressed'),String(!was));
 await btn.click();await p.waitForTimeout(300);assert.equal((await sets()).includes('Main'),was);});
test('drag the person onto the map to stand there; double-tap Space to fly',async t=>{const p=await pageFor(t);await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(400);
 const roof=await roofPoint(p),btn=await p.getByRole('button',{name:'Walk',exact:true}).boundingBox();
 await p.mouse.move(btn.x+btn.width/2,btn.y+btn.height/2);await p.mouse.down();await p.mouse.move(roof.x,roof.y,{steps:12});
 assert.equal(await p.locator('#peg').isVisible(),true,'the person follows the pointer');await p.mouse.up();
 await p.waitForFunction(()=>EL.walk?.body,null,{timeout:15000});await p.waitForTimeout(1200);
 assert.equal(await p.locator('#peg').isVisible(),false);
 const tap2=()=>p.evaluate(()=>{for(let i=0;i<2;i++)for(const n of['keydown','keyup'])document.dispatchEvent(new KeyboardEvent(n,{code:'Space',key:' ',bubbles:true,cancelable:true}));});   // two taps with no renderer delay between them
 await tap2();assert.equal(await p.evaluate(()=>EL.walk.body.flying),true,'flying');await p.waitForTimeout(500);
 await tap2();assert.equal(await p.evaluate(()=>EL.walk.body.flying),false,'double-tap again drops');});

// ---- regressions measured on 2026-11-13 (camera jumps, placement glitches)
const view=(p,eye,tgt)=>p.evaluate(([eye,tgt])=>{const C3=Cesium.Cartesian3,M=EL.models.Main.modelMatrix,W=a=>Cesium.Matrix4.multiplyByPoint(M,new C3(...a),new C3()),e=W(eye),t=W(tgt);
  EL.nav.stop();EL.viewer.camera.setView({destination:e,orientation:{direction:C3.normalize(C3.subtract(t,e,new C3()),new C3()),up:C3.normalize(Cesium.Matrix4.multiplyByPointAsVector(M,C3.UNIT_Z,new C3()),new C3())}});EL.viewer.render();},[eye,tgt]);
const swipe=(p,dx,dy,n,o={})=>p.evaluate(async([dx,dy,n,o])=>{const c=EL.viewer.scene.canvas,r=c.getBoundingClientRect(),C3=Cesium.Cartesian3,cam=EL.viewer.camera;let prev=cam.positionWC.clone(),max=0;
  const off=EL.viewer.scene.postRender.addEventListener(()=>{max=Math.max(max,C3.distance(prev,cam.positionWC));prev=cam.positionWC.clone();});
  for(let i=0;i<n;i++){c.dispatchEvent(new WheelEvent('wheel',{deltaX:dx,deltaY:dy,deltaMode:0,clientX:r.left+r.width/2,clientY:r.top+r.height/2,bubbles:true,cancelable:true,...o}));await new Promise(f=>requestAnimationFrame(f));}
  const pivot=EL.nav.pivot&&C3.distance(EL.nav.pivot,cam.positionWC);for(let i=0;i<30;i++)await new Promise(f=>requestAnimationFrame(f));await new Promise(f=>setTimeout(f,260));off();return{maxStep:max,pivot};},[dx,dy,n,o]);
const height=p=>p.evaluate(()=>Cesium.Cartographic.fromCartesian(EL.viewer.camera.positionWC).height);
const baseCentre=p=>p.evaluate(()=>{const b=EL.meta.sets.Main.bbox_m,w=Cesium.Matrix4.multiplyByPoint(EL.models.Main.modelMatrix,new Cesium.Cartesian3((b[0][0]+b[1][0])/2,(b[0][1]+b[1][1])/2,b[0][2]),new Cesium.Cartesian3());return[w.x,w.y,w.z];});
test('nothing but EarthLink moves the camera, and looking up does not snap it',async t=>{const p=await pageFor(t,null,'mac');await p.evaluate(()=>EL.setProjection('perspective'));
 assert.equal(await p.evaluate(()=>EL.viewer.scene.screenSpaceCameraController.enableCollisionDetection),false);
 await view(p,[15,-25,1.7],[15,2.5,9]);await p.waitForTimeout(400);const h0=await height(p);
 const r=await swipe(p,0,-1,3);assert.ok(r.maxStep<0.5,'tilt of 3 px moved the camera '+r.maxStep.toFixed(2)+' m in one frame');assert.ok(Math.abs(await height(p)-h0)<0.6);
 const down=await swipe(p,0,6,40);assert.ok(down.maxStep<3,'tilting on is smooth: '+down.maxStep);});
test('the pivot stays at the model when the centre of the view runs to the horizon',async t=>{const p=await pageFor(t,null,'mac');await p.evaluate(()=>EL.setProjection('perspective'));
 await view(p,[15,-140,6],[60,400,8]);await p.waitForTimeout(400);const r=await swipe(p,-3,0,8);
 assert.ok(r.pivot&&r.pivot<400,'pivot '+Math.round(r.pivot)+' m away');assert.ok(r.maxStep<3,'step '+r.maxStep);
 await p.evaluate(()=>EL.setProjection('two_point'));await p.waitForTimeout(400);const two=await swipe(p,-3,0,8);
 assert.ok(two.pivot&&two.pivot<400,'two-point pivot '+Math.round(two.pivot));assert.ok(two.maxStep<3,'two-point step '+two.maxStep);await p.evaluate(()=>EL.setProjection('perspective'));});
test('placing a set is instant, exports nothing and is kept by the server',async t=>{const p=await pageFor(t);const meta0=await p.evaluate(()=>EL.meta.sets.Main);
 const c0=await baseCentre(p);await p.evaluate(()=>EL.setPlacement('Main',0,[5,0,0]));const c1=await baseCentre(p);assert.ok(Math.abs(d3(c0,c1)-5)<1e-3,'moved 5 m at once');
 await p.evaluate(()=>EL.rotateSet('Main',40));const c2=await baseCentre(p);assert.ok(d3(c1,c2)<1e-3,'turning keeps the base centre where it is');
 await p.waitForFunction(()=>EL.meta.sets.Main.placement&&!EL.place.Main,null,{timeout:8000});
 const m=await p.evaluate(()=>EL.meta.sets.Main);assert.equal(m.placement.rot,40);assert.equal(m.glb,meta0.glb,'no new export');assert.ok(d3(c2,await baseCentre(p))<1e-3,'no jump when the server answers');
 await p.evaluate(()=>EL.setPlacement('Main',0,[0,0,0]));await p.waitForFunction(()=>!EL.meta.sets.Main.placement&&!EL.place.Main,null,{timeout:8000});assert.ok(d3(c0,await baseCentre(p))<1e-3);});
test('dragging a set near the horizon cannot fling it away',async t=>{const p=await pageFor(t);await p.evaluate(()=>EL.setProjection('perspective'));
 await view(p,[15,-90,3],[15,2.5,3]);await p.evaluate(()=>{EL.openSetCard('Main');const d=document.getElementById('dragOn');d.checked=true;d.dispatchEvent(new Event('change'));});
 const box=await p.locator('canvas').first().boundingBox(),x=box.x+box.width/2,y=box.y+box.height*0.52;
 await p.mouse.move(x,y);await p.mouse.down();await p.mouse.move(x+30,box.y+box.height*0.5,{steps:10});await p.mouse.move(x+30,box.y+box.height*0.3,{steps:10});await p.mouse.up();
 const moved=await p.evaluate(()=>{const q=EL.placementOf('Main');return Math.hypot(q.t[0],q.t[1]);});assert.ok(moved<800,'moved '+Math.round(moved)+' m');
 await p.evaluate(()=>EL.setPlacement('Main',0,[0,0,0]));await p.waitForTimeout(600);});
test('Edit Set: typed offsets and rotation place the set; the Rhino switches are sent',async t=>{const p=await pageFor(t);
 await p.evaluate(()=>EL.setPlacement('Main',0,[0,0,0]));await p.waitForFunction(()=>!EL.meta.sets.Main.placement&&!EL.place.Main,null,{timeout:8000});const c0=await baseCentre(p);   // whatever an earlier run left
 await p.evaluate(()=>EL.openSetCard('Main'));await p.locator('#setE').fill('4');await p.locator('#setU').fill('1.5');
 assert.ok(Math.abs(d3(c0,await baseCentre(p))-Math.hypot(4,1.5))<1e-3,'typed offset applied at once');
 await p.locator('#setRotN').fill('90');const q=await p.evaluate(()=>EL.placementOf('Main'));assert.equal(q.rot,90);
 assert.ok(Math.abs(d3(c0,await baseCentre(p))-Math.hypot(4,1.5))<1e-3,'the base centre stays put while turning');
 assert.equal(+await p.locator('#setE').inputValue(),4);
 await p.locator('#setLive').check({force:true});await p.waitForFunction(()=>EL.meta.sets.Main.live===true,null,{timeout:8000});
 await p.waitForFunction(()=>document.querySelector('#sets .item .t')?.textContent.includes('Live'),null,{timeout:4000});
 await p.locator('#setLive').uncheck({force:true});await p.waitForFunction(()=>EL.meta.sets.Main.live===false,null,{timeout:8000});
 await p.locator('#setOriginal').click();await p.waitForFunction(()=>!EL.meta.sets.Main.placement&&!EL.place.Main,null,{timeout:8000});assert.ok(d3(c0,await baseCentre(p))<1e-3);});
test('set actions: delete is leftmost, then edit; the Navigation pop-up is gone and the compass resets north',async t=>{const p=await pageFor(t);const row=p.locator('#sets .item').first();await row.hover();const titles=await row.locator('.acts button').evaluateAll(b=>b.map(x=>x.title));assert.deepEqual(titles.map(s=>s.split(':')[0]),['Remove from EarthLink','Edit']);assert.equal(await p.locator('#navCard').count(),0);assert.equal(await p.locator('#syncViews').count(),0,'named views are always shared');await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);EL.nav.turn(0,0,true);EL.nav.turn(70,0);});await p.waitForTimeout(300);assert.ok(Math.abs(await p.evaluate(()=>Cesium.Math.toDegrees(EL.viewer.camera.heading))%360)>20);await p.getByRole('button',{name:'North up',exact:true}).click();await p.waitForFunction(()=>{const h=Cesium.Math.toDegrees(EL.viewer.camera.heading);return Math.min(h,360-h)<0.5;},null,{timeout:20000});});
test('Two-Point is the same camera with a level axis: rotating moves it, the picture never rolls, the shift is limited',async t=>{const p=await pageFor(t);await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(500);await p.getByRole('button',{name:'Two-Point',exact:true}).click();await p.waitForTimeout(500);const st=()=>p.evaluate(()=>{const c=EL.viewer.camera;return{pitch:Cesium.Math.toDegrees(c.pitch),roll:Cesium.Math.toDegrees(c.roll),shift:c.frustum._elShift||0,h:Cesium.Cartographic.fromCartesian(c.positionWC).height,pos:[c.positionWC.x,c.positionWC.y,c.positionWC.z]};});const a=await st();await p.evaluate(()=>{EL.nav.turn(0,0,true);EL.nav.turn(0,-12);});await p.waitForTimeout(300);const b=await st();assert.ok(Math.abs(b.pitch)<1e-6&&Math.abs(((b.roll+180)%360)-180)<1e-6,'axis level, no roll');assert.ok(Math.abs(b.h-a.h)>1,'tilting moves the camera up or down: '+(b.h-a.h));assert.ok(Math.abs(b.shift-a.shift)>0.05,'and the lens shift follows');await p.evaluate(()=>{EL.nav.turn(40,0);});await p.waitForTimeout(300);const c=await st();assert.ok(Math.abs(c.shift-b.shift)<1e-6&&Math.abs(c.pitch)<1e-6,'turning keeps the framing');assert.ok(Math.hypot(...c.pos.map((v,i)=>v-b.pos[i]))>1,'and moves the camera around the pivot');await p.evaluate(()=>{for(let i=0;i<40;i++)EL.nav.turn(0,6);});await p.waitForTimeout(300);const d=await st();assert.ok(Math.abs(d.shift)<=Math.tan(65*Math.PI/180)+1e-6,'shift limited: '+d.shift);});
test('time of day: at night the model is tinted dark blue and shadows are off; by day it is untouched',async t=>{const p=await pageFor(t);const at=async m=>{await p.evaluate(m=>{const d=document.getElementById('date'),h=document.getElementById('hour');d.value='2026-06-21';h.value=m;h.dispatchEvent(new Event('input'));},m);await p.waitForTimeout(700);return p.evaluate(()=>{const c=EL.models.Main.color;return{c:[c.red,c.green,c.blue],shadows:EL.viewer.shadows,stars:EL.viewer.scene.skyBox.show,light:EL.viewer.scene.light.intensity};});};if(!(await p.evaluate(()=>document.getElementById('sunOn').checked)))await p.evaluate(()=>document.getElementById('sunOn').click());const day=await at(720),night=await at(60);assert.deepEqual(day.c,[1,1,1]);assert.equal(day.shadows,true);assert.equal(day.stars,false,'no stars by day');assert.ok(night.c.every(v=>v<0.6)&&night.c[2]>night.c[0],'tinted: '+night.c);assert.equal(night.shadows,false);assert.equal(night.stars,true);});

// ---- beta.10: surroundings to Rhino (open data inside a rectangle), feedback
test('Surroundings to Rhino: a dragged rectangle is sent as bounds, the import is followed to the end, Escape puts the tool away',async t=>{
 let posted=null,polls=0;
 const p=await pageFor(t,async p=>{await p.route('**/api/context',async route=>{const r=route.request();
   if(r.method()==='POST'){posted=JSON.parse(r.postData());return route.fulfill({json:{state:'working',message:'Reading the terrain'}});}
   polls++;return route.fulfill({json:polls<2?{state:'working',message:'Reading OpenStreetMap'}:polls<3?{state:'sent',counts:{terrain:100,buildings:12,roads:5}}:{state:'done',message:"added terrain (100 faces), 12 buildings, 5 road lines on layer 'EarthLink Context'"}});});});
 await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(500);
 const before=await cam(p);
 await p.getByRole('button',{name:'Bring the surroundings into Rhino',exact:true}).click();
 assert.equal(await p.locator('#contextCard').isVisible(),true);assert.equal(await p.locator('#cxImport').isDisabled(),true,'nothing to import before a rectangle is drawn');
 await p.mouse.move(420,330);await p.mouse.down();await p.mouse.move(700,560,{steps:10});await p.mouse.up();await p.waitForTimeout(300);
 const after=await cam(p);assert.ok(d3(before.pos,after.pos)<1e-6&&d3(before.dir,after.dir)<1e-9,'dragging the rectangle does not move the camera');
 assert.match(await p.locator('#cxSize').innerText(),/\d+ × \d+ m/);
 const size=await p.evaluate(()=>document.getElementById('cxSize').textContent.match(/([\d,]+) × ([\d,]+) m/).slice(1).map(v=>+v.replace(/,/g,'')));
 assert.ok(size[0]>20&&size[1]>20&&size[0]<3000&&size[1]<3000,'a sensible size: '+size);
 await p.locator('label.chip:has(#cxRoads)').click();await p.locator('#cxImport').click();
 await p.waitForFunction(()=>/Rhino added terrain/.test(document.getElementById('cxStatus').textContent),null,{timeout:15000});
 assert.ok(posted&&posted.terrain===true&&posted.buildings===true&&posted.roads===false,'the choices are sent');
 const b=posted.bounds;assert.ok(b.west<b.east&&b.south<b.north,'west/south/east/north in order');
 const here=await p.evaluate(()=>EL.meta.anchor);assert.ok(Math.abs((b.south+b.north)/2-here.lat)<0.05&&Math.abs((b.west+b.east)/2-here.lon)<0.05,'the rectangle is at the site');
 assert.equal(await p.locator('#cxImport').isEnabled(),true,'ready for another import');
 await p.keyboard.press('Escape');assert.equal(await p.locator('#contextCard').isVisible(),false);
 assert.equal(await p.evaluate(()=>document.body.classList.contains('cropping')),false);});
test('Surroundings to Rhino: a rectangle over 3 km a side cannot be imported; an error from the server is shown',async t=>{
 const p=await pageFor(t,async p=>{await p.route('**/api/context',route=>route.fulfill({json:{state:'error',message:'OpenStreetMap could not be reached (timed out). Try again in a minute.'}}));});
 await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);});await p.waitForTimeout(500);
 await p.getByRole('button',{name:'Bring the surroundings into Rhino',exact:true}).click();
 await p.mouse.move(420,330);await p.mouse.down();await p.mouse.move(700,560,{steps:6});await p.mouse.up();await p.waitForTimeout(200);
 await p.locator('#cxImport').click();await p.waitForFunction(()=>/could not be reached/.test(document.getElementById('cxStatus').textContent),null,{timeout:8000});
 assert.equal(await p.evaluate(()=>document.getElementById('cxStatus').classList.contains('bad')),true);
 await p.evaluate(()=>{const c=EL.viewer.camera,up=Cesium.Cartesian3.normalize(c.positionWC,new Cesium.Cartesian3());c.setView({destination:Cesium.Cartesian3.add(c.positionWC,Cesium.Cartesian3.multiplyByScalar(up,9000,new Cesium.Cartesian3()),new Cesium.Cartesian3()),orientation:{heading:0,pitch:-Math.PI/2,roll:0}});});await p.waitForTimeout(500);
 await p.mouse.move(350,340);await p.mouse.down();await p.mouse.move(880,770,{steps:6});await p.mouse.up();await p.waitForTimeout(200);
 assert.match(await p.locator('#cxHint').innerText(),/Too large/);assert.equal(await p.locator('#cxImport').isDisabled(),true);});
test('Feedback: the comment, screenshot note and system details go to a filled-in GitHub issue or an email; no location is included',async t=>{
 const p=await pageFor(t);await p.evaluate(()=>{window.__opened=[];window.open=(u)=>{window.__opened.push(u);return null;};});
 await p.getByRole('button',{name:'Send feedback',exact:true}).click();
 assert.equal(await p.locator('#fbGithub').isDisabled(),true,'nothing to send without words');
 await p.locator('#fbText').fill('Zooming jumps when I pinch\nsecond line');
 await p.waitForFunction(()=>document.getElementById('fbThumb').classList.contains('on'),null,{timeout:15000});
 const info=await p.locator('#fbInfo').innerText(),site=await p.evaluate(()=>EL.meta.anchor);
 assert.match(info,/EarthLink 0\.2\.0/);assert.ok(!info.includes(String(site.lat).slice(0,6))&&!info.includes(String(site.lon).slice(0,6)),'no coordinates in the details');
 const dl=p.waitForEvent('download');await p.locator('#fbGithub').click();assert.equal((await dl).suggestedFilename(),'earthlink-feedback.png');
 const url=await p.evaluate(()=>window.__opened[0]),q=new URL(url);
 assert.equal(q.origin+q.pathname,'https://github.com/J1mmywzh/EarthLink/issues/new');assert.equal(q.searchParams.get('title'),'Zooming jumps when I pinch');
 assert.match(q.searchParams.get('body'),/second line[\s\S]*Screenshot[\s\S]*EarthLink 0\.2\.0/);
 assert.equal(await p.locator('#feedbackCard').isVisible(),false);
 assert.equal(await p.locator('#fbEmail').evaluate(b=>b.hidden),false,'email is offered');});

// ---- beta.10: the Rhino model's lights
const pixel=(p,x,y)=>p.evaluate(async([x,y])=>{const s=EL.viewer.scene,frame=()=>new Promise(r=>{const off=s.postRender.addEventListener(()=>{off();r();});s.requestRender();});for(let i=0;i<4;i++)await frame();   // a changed shader is drawn a frame later
  return await new Promise(r=>{const off=s.postRender.addEventListener(()=>{off();const c=s.canvas,g=s.context._gl,o=new Uint8Array(4);g.readPixels(Math.round(x*c.width/c.clientWidth),c.height-Math.round(y*c.height/c.clientHeight),1,1,g.RGBA,g.UNSIGNED_BYTE,o);r([o[0],o[1],o[2]]);});s.requestRender();});},[x,y]);
test("Rhino lights: a light brightens the faces turned to it, follows its set and Rhino's fall-off, and goes with the switch",async t=>{const p=await pageFor(t);
 await p.evaluate(()=>{EL.setProjection('perspective');EL.fit(0);const d=document.getElementById('date'),h=document.getElementById('hour');if(!document.getElementById('sunOn').checked)document.getElementById('sunOn').click();d.value='2026-06-21';h.value=60;h.dispatchEvent(new Event('input'));});await p.waitForTimeout(700);
 const at=[[640,580],[450,300]],read=async()=>[await pixel(p,...at[0]),await pixel(p,...at[1])],sum=c=>c[0]+c[1]+c[2];
 const dark=await read();
 await p.evaluate(()=>{const b=EL.meta.sets.Main.bbox_m;EL.meta.lights=[{id:'a',kind:'point',pos:[b[0][0]-6,b[0][1]-6,b[1][2]+4],dir:[0,0,-1],color:[1,0.85,0.6],intensity:1,att:[1,0,0]}];EL.applyLights();});
 const lit=await read();assert.ok(sum(lit[0])>sum(dark[0])+30&&sum(lit[1])>sum(dark[1])+60,'lit '+JSON.stringify([dark,lit]));
 assert.ok(lit[1][0]>lit[1][2]+40,'a warm light gives a warm face: '+lit[1]);
 assert.equal(await p.evaluate(()=>EL.lamps.n),1);
 await p.evaluate(()=>{const l=EL.meta.lights[0];l.intensity=0.4;EL.applyLights();});const dim=await read();assert.ok(sum(dim[1])<sum(lit[1])-25&&sum(dim[1])>sum(dark[1])+15,'intensity scales the light');
 await p.evaluate(()=>{EL.meta.lights[0].intensity=1;EL.meta.lights[0].att=[0,1000,0];EL.applyLights();});assert.deepEqual(await read(),dark,"Rhino's fall-off is followed: 1/d in millimetres is dark at this distance");
 await p.evaluate(()=>{EL.meta.lights[0].att=[1,0,0];EL.applyLights();});
 // the light is nearest to both sets' boxes here; move it with a placement: its position in the site frame follows
 const before=await p.evaluate(()=>Array.from(EL.lamps.data.slice(0,3)));
 await p.evaluate(()=>{EL.setPlacement('Main',0,[5,0,0]);EL.setPlacement('Scheme B',0,[5,0,0]);EL.applyLights();});
 const after=await p.evaluate(()=>Array.from(EL.lamps.data.slice(0,3)));assert.ok(Math.abs(after[0]-before[0]-5)<1e-3&&Math.abs(after[1]-before[1])<1e-3,'the light moved 5 m east with its set: '+before+' -> '+after);
 await p.evaluate(()=>{EL.setPlacement('Main',0,[0,0,0]);EL.setPlacement('Scheme B',0,[0,0,0]);});await p.waitForTimeout(1500);
 await p.evaluate(()=>{const b=EL.meta.sets.Main.bbox_m;EL.meta.lights=[{id:'a',kind:'point',pos:[b[0][0]-6,b[0][1]-6,b[1][2]+4],dir:[0,0,-1],color:[1,0.85,0.6],intensity:1,att:[1,0,0]}];EL.applyLights();});   // (the fixture's own meta has no lights)
 await p.locator('#shadows').click();assert.equal(await p.locator('#lampRow').isVisible(),true);assert.match(await p.locator('#lampCount').innerText(),/1 from Rhino/);
 await p.locator('label.switch:has(#lampsOn)').click();assert.deepEqual(await read(),dark,'switched off: as before');assert.equal(await p.evaluate(()=>!!EL.models.Main.customShader),false,'and the stock shader is back');
 await p.locator('label.switch:has(#lampsOn)').click();assert.ok(sum((await read())[1])>sum(dark[1])+60,'switched on again');
 await p.evaluate(()=>{EL.meta.lights=[{id:'s',kind:'spot',pos:[-8,10,15],dir:[1,0,0],color:[1,1,1],intensity:1,att:[1,0,0],angle:0.05,exp:1},{id:'r',kind:'rect',pos:[-100,-100,-50],length:[2,0,0],width:[0,2,0],dir:[0,0,-1],color:[1,1,1],intensity:1,att:[0,1000,0]},{id:'d',kind:'directional',pos:[0,0,0],dir:[0,0,1],color:[1,1,1],intensity:1,att:[1,0,0]}];EL.applyLights();});
 assert.equal(await p.evaluate(()=>EL.lamps.n),3,'spot, rectangular and directional lights are all drawn');
 const kinds=await p.evaluate(()=>[0,1,2].map(i=>EL.lamps.data[i*16+3]));assert.deepEqual(kinds,[1,0,2],'a rectangular light is a point at its centre, as in Rhino');
 assert.deepEqual(await p.evaluate(()=>Array.from(EL.lamps.data.slice(16,19))),[-99,-99,-50]);});
