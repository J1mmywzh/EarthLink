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
