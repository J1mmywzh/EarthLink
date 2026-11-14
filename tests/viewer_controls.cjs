// Runs against a disposable fixture server; never needs a map key. Gestures are sent as real wheel/pointer events.
const {chromium}=require(process.env.EARTHLINK_PLAYWRIGHT||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.EARTHLINK_CHROME||undefined,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1280,height:800},ignoreHTTPSErrors:!!process.env.EARTHLINK_IGNORE_HTTPS});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>localStorage.setItem('earthlink:skipKeys','true'));
 {const u=new URL(process.argv[2]||'http://127.0.0.1:8877/');u.searchParams.set('controls','mac');await page.goto(u.href);}   // Rhino for Mac gestures (Windows: viewer_review.cjs)
 await page.waitForFunction(()=>window.EL&&Object.keys(EL.models).length>0,null,{timeout:60000});
 const settle=()=>page.waitForTimeout(450);
 const wheel=(list,gap=16)=>page.evaluate(async([list,gap])=>{const c=EL.viewer.scene.canvas,r=c.getBoundingClientRect();
   for(const w of list){c.dispatchEvent(new WheelEvent('wheel',{deltaX:w.x||0,deltaY:w.y||0,deltaMode:0,shiftKey:!!w.shift,ctrlKey:!!w.ctrl,clientX:r.left+r.width/2,clientY:r.top+r.height/2,bubbles:true,cancelable:true}));if(gap>=0)await new Promise(f=>setTimeout(f,gap));}},[list,gap]);
 const cam=()=>page.evaluate(()=>{EL.viewer.render();const c=EL.viewer.camera,s=EL.viewer.scene,w=s.canvas.clientWidth,h=s.canvas.clientHeight,ray=c.getPickRay(new Cesium.Cartesian2(w/2,h/2)),t=EL.surfaceHit(ray),ctr=t===null?null:Cesium.Ray.getPoint(ray,t);
   return{pos:[c.positionWC.x,c.positionWC.y,c.positionWC.z],dir:[c.directionWC.x,c.directionWC.y,c.directionWC.z],up:[c.upWC.x,c.upWC.y,c.upWC.z],right:[c.rightWC.x,c.rightWC.y,c.rightWC.z],
     heading:Cesium.Math.toDegrees(c.heading),roll:Cesium.Math.toDegrees(c.roll),pitch:Cesium.Math.toDegrees(c.pitch),centre:ctr?[ctr.x,ctr.y,ctr.z]:null,width:c.frustum.width};});
 const dist=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i])),dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0),turn=d=>((d%360)+540)%360-180;
 await page.evaluate(()=>EL.fit(0));await settle();

 // Heading, tilt and sensitivity are in the compass pop-up; nothing about navigation in the sidebar
 assert.equal(await page.locator('#navCard').count(),1);assert.equal(await page.locator('#sidebar #sens, #sidebar #navHelp').count(),0);
 assert.equal(await page.locator('#inputDevice').count(),0);

 // two fingers orbit about the centre of the view, level horizon
 let a=await cam();
 const orbitCheck=await page.evaluate(async()=>{const s=EL.viewer.scene,cv=s.canvas,r=cv.getBoundingClientRect(),out=[];
   const ev=()=>cv.dispatchEvent(new WheelEvent('wheel',{deltaX:-8,clientX:r.left+r.width/2,clientY:r.top+r.height/2,bubbles:true,cancelable:true}));
   const look=()=>{const p=EL.nav.pivot;if(!p)return null;const q=Cesium.SceneTransforms.worldToWindowCoordinates(s,p);return{off:Math.hypot(q.x-cv.clientWidth/2,q.y-cv.clientHeight/2),d:Cesium.Cartesian3.distance(p,EL.viewer.camera.positionWC),x:p.x};};
   for(let i=0;i<20;i++){ev();await new Promise(f=>setTimeout(f,16));if(i===3)out.push(look());}
   await new Promise(f=>setTimeout(f,450));out.push(look());return out;});
 let b=await cam();const [p0,p1]=orbitCheck;
 assert.ok(turn(b.heading-a.heading)>5,'fingers right turn the view');assert.ok(Math.abs(b.roll)<0.05,'no roll');
 assert.ok(p0&&p1&&p0.off<1&&p1.off<1,'orbits about the point at the centre of the view '+JSON.stringify(orbitCheck));
 await wheel(Array(15).fill({y:-6}));await settle();assert.ok(Math.abs((await cam()).roll)<0.05,'tilt keeps the horizon level');

 // Shift pans; releasing Shift during the momentum tail cannot turn the pan into an orbit
 a=await cam();await wheel([...Array(8).fill({x:6,shift:true}),...Array(12).fill({x:4})],-1);await settle();b=await cam();
 assert.ok(Math.abs(turn(b.heading-a.heading))<0.05,'no orbit after Shift is released');
 {const d=b.pos.map((v,i)=>v-a.pos[i]);assert.ok(dot(d,a.right)>0.5,'fingers left move the scene left '+JSON.stringify({right:dot(d,a.right),up:dot(d,a.up),fwd:dot(d,a.dir),dh:turn(b.heading-a.heading),roll:b.roll,pitch:b.pitch}));}

 // a fast trackpad swipe is not read as a mouse wheel (no zoom)
 a=await cam();
{const sw=await page.evaluate(async()=>{const c=EL.viewer.scene.canvas,r=c.getBoundingClientRect(),out={mouse:[],pivot:null};
   for(const y of [4,120,110]){const e=new WheelEvent('wheel',{deltaX:0,deltaY:y,deltaMode:0,clientX:r.left+r.width/2,clientY:r.top+r.height/2,bubbles:true,cancelable:true});
     out.mouse.push(EarthLinkNavigation.isMouseWheel(e));c.dispatchEvent(e);}
   for(let i=0;i<30&&!out.pivot;i++){await new Promise(f=>requestAnimationFrame(f));const p=EL.nav.pivot;if(p)out.pivot=[p.x,p.y,p.z];}
   return out;});
 await settle();b=await cam();const pv=sw.pivot||a.centre;
 assert.ok(pv&&Math.abs(dist(b.pos,pv)/dist(a.pos,pv)-1)<0.01,'an orbit, not a zoom '+JSON.stringify({mouse:sw.mouse,pivot:!!sw.pivot,centre:!!a.centre,ratio:pv&&dist(b.pos,pv)/dist(a.pos,pv)}));}

 // Reset to north
 await page.getByRole('button',{name:'Compass',exact:true}).click();await page.getByRole('button',{name:'North up',exact:true}).click();
 await page.waitForFunction(()=>{const h=Cesium.Math.toDegrees(EL.viewer.camera.heading);return Math.abs(((h%360)+540)%360-180)<0.5;},null,{timeout:30000}).catch(()=>{});
 {const hh=(await cam()).heading;assert.ok(Math.abs(turn(hh))<0.5,'north '+hh);}

 // +/-: a click is a smooth step, holding zooms continuously
 a=await cam();await page.locator('#zoomIn').click();await settle();b=await cam();
 assert.ok(dist(b.pos,b.centre)<dist(a.pos,a.centre)*0.75,'zoom in step');
 await page.evaluate(()=>EL.nav.stop());await page.evaluate(()=>EL.nav.hold(1));await page.waitForTimeout(5000);await page.evaluate(()=>EL.nav.release());await settle();const c=await cam();
 {const pv=await page.evaluate(()=>{const p=EL.nav.pivot;return p&&[p.x,p.y,p.z];});
  assert.ok(pv&&dist(c.pos,pv)>dist(b.pos,pv)*1.3,'hold zooms out continuously '+JSON.stringify([pv&&dist(b.pos,pv),pv&&dist(c.pos,pv)]));}

 // globe scale: pinch zoom never turns the Earth
 await page.evaluate(()=>EL.viewer.camera.setView({destination:Cesium.Cartesian3.fromDegrees(-76.5,42.4,9e6),orientation:{heading:0.5,pitch:-1.4,roll:0}}));
 a=await cam();await wheel(Array(12).fill({y:-6,ctrl:true}));await settle();b=await cam();
 assert.ok(dot(a.dir,b.dir)>0.999999&&dot(a.up,b.up)>0.999999,'orientation unchanged');assert.ok(dist(b.pos,[0,0,0])<dist(a.pos,[0,0,0])-1e5,'zoomed in');
 await page.evaluate(()=>EL.fit(0));await settle();

 // Parallel: two fingers pan (no orbit), Shift + scroll and pinch zoom, the tilt slider still works
 await page.getByRole('button',{name:'Parallel',exact:true}).click();await settle();
 a=await cam();await wheel(Array(10).fill({x:6}));await settle();b=await cam();
 assert.ok(Math.abs(turn(b.heading-a.heading))<0.05&&dist(a.pos,b.pos)>0.5,'parallel scroll pans');
 a=await cam();await wheel(Array(10).fill({x:6,shift:true}));await settle();b=await cam();assert.ok(Math.abs(b.width-a.width)<1e-6&&dist(a.pos,b.pos)>0.5,'Shift + two fingers still pans');
 a=b;await wheel(Array(10).fill({y:-6,ctrl:true}));await settle();b=await cam();assert.ok(b.width<a.width*0.9,'pinch zooms');
 const t0=await page.evaluate(()=>EL.nav.headingTilt().tilt);
 await page.keyboard.press('Escape');await page.evaluate(()=>document.getElementById('navCard').classList.remove('open'));
 {const box=await page.getByRole('button',{name:'Compass',exact:true}).boundingBox(),cx=box.x+box.width/2,cy=box.y+box.height/2;
  await page.mouse.move(cx,cy);await page.mouse.down();await page.mouse.move(cx,cy+(t0>30?60:-60),{steps:6});await page.mouse.up();await settle();}
 assert.ok(Math.abs(await page.evaluate(()=>EL.nav.headingTilt().tilt)-t0)>10,'dragging the compass tilts, also in Parallel');
 await page.getByRole('button',{name:'Perspective',exact:true}).click();

 // Sun: one switch; no permanent time bar
 await page.getByRole('button',{name:'Sun',exact:true}).click();
 await page.getByRole('checkbox',{name:'Sunlight',exact:true}).uncheck();
 assert.equal(await page.getByLabel('Date',{exact:true}).isVisible(),false);
 assert.equal(await page.locator('#timebar').count(),0);
 await page.getByRole('checkbox',{name:'Sunlight',exact:true}).check();
 await page.locator('[data-close=sunCard]').click();

 // Walk on the model's roof, then on open ground with no model under you
 await page.evaluate(()=>EL.fit(0));await settle();
 const before=await cam();
 const at=local=>page.evaluate(l=>{const w=Cesium.Matrix4.multiplyByPoint(EL.models.Main.modelMatrix,new Cesium.Cartesian3(...l),new Cesium.Cartesian3());const p=Cesium.SceneTransforms.worldToWindowCoordinates(EL.viewer.scene,w);return{x:p.x,y:p.y};},local);
 for(const spot of [[15,2.5,10],null]){
   const s=spot?await at(spot):{x:640,y:760};   // null: open ground near the bottom of the view
   await page.getByRole('button',{name:'Walk',exact:true}).click();await page.mouse.click(s.x,s.y);
   await page.waitForFunction(()=>EL.walk?.body,null,{timeout:15000});
   const f0=await page.evaluate(()=>EL.walk.body.feet.slice());await page.keyboard.down('d');
   await page.waitForFunction(f=>{const p=EL.walk?.body?.feet;return p&&Math.hypot(p[0]-f[0],p[1]-f[1])>1.5;},f0,{timeout:30000}).catch(()=>{});await page.keyboard.up('d');
   const f1=await page.evaluate(()=>EL.walk.body.feet.slice());   // speed itself is covered by walk.test.cjs (this renderer is slow)
   assert.ok(Math.hypot(f1[0]-f0[0],f1[1]-f0[1])>1.5,`walks (${spot||'ground'})`);assert.ok(Math.abs(f1[2]-f0[2])<0.3,'stays on the surface');
   await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>EL.walk),null);
   assert.ok(dist((await cam()).pos,before.pos)<1e-3,'Esc returns to the camera before walking');
 }
 assert.deepEqual(errors,[]);
 await browser.close();console.log('viewer controls passed');
})().catch(e=>{console.error(e);process.exit(1);});
