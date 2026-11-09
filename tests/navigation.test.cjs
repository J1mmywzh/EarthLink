const {test}=require('node:test');
const assert=require('node:assert/strict');
let N; try { N=require('../shared/viewer/navigation.js'); } catch {}
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
test('orbit keeps target and radius and a level frame',()=>{
  assert.ok(N,'navigation module exists'); const o=new N.Orbit({target:[3,4,5],distance:20});
  for(let i=0;i<30;i++)o.orbit(12,1);
  const p=o.pose(); assert.deepEqual(o.target,[3,4,5]); near(Math.hypot(...p.position.map((v,i)=>v-o.target[i])),20);
  near(p.direction.reduce((v,x,i)=>v+x*p.up[i],0),0); near(p.right[2],0);
});
test('north preserves target tilt and distance',()=>{
  assert.ok(N);const o=new N.Orbit({target:[4,5,6],distance:12,heading:123,tilt:40});o.north();
  assert.equal(o.heading,0);assert.equal(o.tilt,40);assert.equal(o.distance,12);assert.deepEqual(o.target,[4,5,6]);
});
test('pan and inverse pan restore camera target',()=>{
  assert.ok(N);const o=new N.Orbit({heading:75,tilt:35,target:[0,0,0]});o.pan(3,4);o.pan(-3,-4);o.target.forEach(v=>near(v,0));
});
test('parallel zoom changes width without changing distance',()=>{
  assert.ok(N);const o=new N.Orbit({projection:'parallel',distance:20,halfHeight:8});o.zoom(.5);assert.equal(o.halfHeight,4);assert.equal(o.distance,20);
});
test('two point stays level and clamps singular endpoints',()=>{
  assert.ok(N);const o=new N.Orbit({projection:'two_point',tilt:0});o.orbit(0,-10000);const p=o.pose();assert.equal(p.direction[2],0);assert.deepEqual(p.up,[0,0,1]);assert.ok(Number.isFinite(p.shift));assert.ok(Math.abs(p.shift)<6);
});
test('nonfinite input cannot poison a camera',()=>{
  assert.ok(N);const o=new N.Orbit({distance:10});o.orbit(NaN,Infinity);o.pan(Infinity,0);o.zoom(NaN);o.pose().position.forEach(v=>assert.ok(Number.isFinite(v)));
});
test('wheel normalizes pinch, pixel trackpad and coarse mouse input',()=>{
  assert.ok(N);assert.equal(N.wheelAction({deltaY:5,deltaX:2,deltaMode:0,ctrlKey:false},'trackpad').type,'orbit');
  assert.equal(N.wheelAction({deltaY:100,deltaX:0,deltaMode:1},'mouse').type,'zoom');
  assert.equal(N.wheelAction({deltaY:3,deltaX:0,ctrlKey:true},'trackpad').type,'zoom');
  assert.equal(N.wheelAction({deltaY:5,deltaX:2,deltaMode:0,shiftKey:true},'trackpad').type,'pan');
});
