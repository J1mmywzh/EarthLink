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
