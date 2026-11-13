const {test}=require('node:test');
const assert=require('node:assert/strict');
const N=require('../shared/viewer/navigation.js');
const pad=(dx,dy,o={})=>({deltaX:dx,deltaY:dy,deltaMode:0,ctrlKey:false,shiftKey:false,...o});

test('Rhino for Mac mapping: two fingers orbit, Shift pans, pinch zooms',()=>{
  assert.equal(new N.WheelLatch().read(pad(3,2),'perspective',0).mode,'orbit');
  assert.equal(new N.WheelLatch().read(pad(3,2,{shiftKey:true}),'perspective',0).mode,'pan');
  assert.equal(new N.WheelLatch().read(pad(0,-4,{ctrlKey:true}),'perspective',0).mode,'zoom');
  assert.equal(new N.WheelLatch().read(pad(3,2),'two_point',0).mode,'orbit');
});
test('Parallel: two fingers pan with or without Shift; only pinch zooms',()=>{
  assert.equal(new N.WheelLatch().read(pad(3,2),'parallel',0).mode,'pan');
  assert.equal(new N.WheelLatch().read(pad(6,0,{shiftKey:true}),'parallel',0).mode,'pan');
  assert.equal(new N.WheelLatch().read(pad(0,6,{shiftKey:true}),'parallel',0).mode,'pan');
  assert.equal(new N.WheelLatch().read(pad(0,-3,{ctrlKey:true}),'parallel',0).mode,'zoom');
});
test('a gesture keeps its mode through the momentum tail, even if Shift is released',()=>{
  const l=new N.WheelLatch();
  assert.equal(l.read(pad(5,0,{shiftKey:true}),'perspective',0).mode,'pan');
  for(let t=16;t<900;t+=16)assert.equal(l.read(pad(2,0),'perspective',t).mode,'pan');
  assert.equal(l.read(pad(2,0),'perspective',900+300).mode,'orbit','a pause ends the gesture');
});
test('fast trackpad swipes are not mistaken for a mouse wheel',()=>{
  const l=new N.WheelLatch();l.read(pad(0,4),'perspective',0);
  assert.equal(l.read(pad(0,120),'perspective',16).mode,'orbit');
  assert.equal(N.isMouseWheel(pad(0,100,{wheelDeltaY:-120})),true);
  assert.equal(N.isMouseWheel(pad(0,3,{deltaMode:1})),true);
  assert.equal(N.isMouseWheel(pad(2,60)),false);
  assert.equal(N.isMouseWheel(pad(0,4)),false);
});
test('easing releases exactly what was added, smoothly, and stops',()=>{
  const e=new N.Ease();e.add('heading',10);let sum=0,first=null,n=0,out;
  while((out=e.take(1/60))){sum+=out.heading;first=first??out.heading;n++;}
  assert.ok(Math.abs(sum-10)<1e-9);assert.ok(first<5,'no jump on the first frame');assert.ok(n<60,'settles within a second');
  e.add('px',NaN);assert.equal(e.take(1/60),null,'non-finite input is ignored');
});
test('one sensitivity scale: the same swipe turns the same angle at any distance',()=>{
  assert.ok(N.RATE.orbit>0&&N.RATE.orbit<0.3);assert.ok(N.RATE.tilt<N.RATE.orbit);assert.ok(N.RATE.pan>=1);
});
test('neutral light is a unit vector from behind the viewer',()=>{
  const d=N.neutralDirection([0,1,0],[0,0,1]);assert.ok(Math.abs(Math.hypot(...d)-1)<1e-12);assert.ok(d[2]<0&&d[1]>0);
});

test('a mouse wheel is told from a trackpad by its legacy delta (Chrome, Safari)',()=>{
  const ev=(deltaY,wheelDeltaY,deltaX=0)=>({deltaX,deltaY,deltaMode:0,wheelDeltaY});
  assert.equal(N.isMouseWheel(ev(4.000244140625,-120)),true,'a slow notch on a Mac');
  assert.equal(N.isMouseWheel(ev(100,-120)),true,'a notch on Windows');
  assert.equal(N.isMouseWheel(ev(40,-120)),false,'a trackpad step of exactly 40');
  assert.equal(N.isMouseWheel(ev(80,-240)),false);assert.equal(N.isMouseWheel(ev(3,-9)),false);
  assert.equal(N.isMouseWheel(ev(100,-120,2)),false,'sideways motion: a trackpad');
});
test('the pivot stays at what you look at, not the far ground behind it',()=>{
  const P=N.pivotDistance;
  assert.equal(P(95,null,100),95,'the surface at the centre, near the model');
  assert.equal(P(1700,null,100),100,'a shallow view past the model: the model depth');
  assert.equal(P(null,null,100),100,'sky: the model depth');
  assert.equal(P(12,null,100),12,'a detail closer than the model');
  assert.equal(P(1700,150,null),150,'no model in view: the last focus');
  assert.equal(P(400,150,null),400);assert.equal(P(5000,null,null,480),480,'nothing known: limited');
  assert.equal(P(null,null,null),null);
});
test('the ground rule never lifts the camera suddenly',()=>{
  let f=new N.Floor();f.h=50;
  assert.equal(f.step(50,60,0),50,'a gesture that starts under a surface is left alone');assert.equal(f.inside,true);
  assert.equal(f.step(49,60,1),50,'inside something solid: not further down');assert.equal(f.step(52,60,1),52,'but up');
  assert.equal(f.step(70,60,1),70);assert.equal(f.inside,false);
  f=new N.Floor();f.step(70,60,0);
  assert.equal(f.step(60.1,60,0.2),60.3,'descending onto a surface: rest on it');
  assert.equal(f.step(59,60,0.2),60.3);
  f=new N.Floor();f.step(62,60,0);
  assert.equal(f.step(62,62.2,3),62.5,'ground rising gently under a sideways move: ride up');
  assert.equal(f.step(62.5,80,1),62.5,'a wall or a tree: pass through');assert.equal(f.inside,true);
  assert.equal(f.step(61,80,1,60),61,'under a tree: free above the ground beneath');
  assert.equal(f.step(59.9,80,1,60),60.3,'and resting on that ground');
  assert.equal(f.step(60.3,80,1,null),60.3);assert.equal(f.step(55,80,1,null),60.3,'inside a building: no way down under the map');
  assert.equal(f.step(62.5,61,1),62.5);assert.equal(f.inside,false);
  f=new N.Floor();f.step(70,60,0);assert.equal(f.step(40,null,1),40,'no map there: no rule');
});
