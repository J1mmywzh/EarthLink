const {test}=require('node:test');
const assert=require('node:assert/strict');
const {Walker,W}=require('../shared/viewer/walk.js');

// A tiny ray-cast world of axis-aligned boxes [minx,miny,minz,maxx,maxy,maxz].
function world(boxes){
  return (o,d,max)=>{let best=null;
    for(const b of boxes){let t0=0,t1=max;
      for(let i=0;i<3;i++){if(Math.abs(d[i])<1e-12){if(o[i]<b[i]||o[i]>b[i+3]){t0=Infinity;break;}continue;}
        let a=(b[i]-o[i])/d[i],c=(b[i+3]-o[i])/d[i];if(a>c)[a,c]=[c,a];t0=Math.max(t0,a);t1=Math.min(t1,c);}
      if(t0<=t1&&t0>=0&&(best==null||t0<best))best=t0;}
    return best;};
}
const floor=[-100,-100,-1,100,100,0];
const run=(w,input,s)=>{for(let i=0;i<s*60;i++)w.step(input,1/60);return w.feet;};

test('walks at 3.5 m/s and sprints at 9.5 m/s',()=>{
  const w=new Walker(world([floor]));run(w,{x:0,y:1},2);const a=w.feet[1];run(w,{x:0,y:1},1);
  assert.ok(Math.abs(w.feet[1]-a-W.walk)<0.05);
  const s=new Walker(world([floor]));run(s,{x:1,y:0,sprint:true},2);const b=s.feet[0];run(s,{x:1,y:0,sprint:true},1);
  assert.ok(Math.abs(s.feet[0]-b-W.sprint)<0.05);assert.ok(W.walk>=3.5&&W.sprint>=9.5);
});
test('starts and stops smoothly (no jump in speed)',()=>{
  const w=new Walker(world([floor]));w.step({x:1,y:0},1/60);assert.ok(w.vel[0]<W.walk*0.2);
});
test('walls stop you and you slide along them',()=>{
  const w=new Walker(world([floor,[2,-50,0,3,50,5]]));run(w,{x:1,y:1},3);
  assert.ok(w.feet[0]<2-W.radius+0.05,'blocked');assert.ok(w.feet[1]>3,'slid along the wall');
});
test('climbs stairs, follows them down, and is stopped by a tall step',()=>{
  const stairs=[floor];for(let i=1;i<=5;i++)stairs.push([i,-5,0,30,5,0.18*i]);
  const w=new Walker(world(stairs));run(w,{x:1,y:0},4);assert.ok(Math.abs(w.feet[2]-0.9)<0.01);
  run(w,{x:-1,y:0},5);assert.ok(Math.abs(w.feet[2])<0.01);assert.ok(w.grounded);
  const t=new Walker(world([floor,[1,-5,0,3,5,0.8]]));run(t,{x:1,y:0},2);assert.ok(t.feet[0]<1&&t.feet[2]===0);
});
test('jumps about half a metre and lands; ceilings stop the jump',()=>{
  const w=new Walker(world([floor]));let top=0;w.step({jump:true},1/60);
  for(let i=0;i<90;i++){w.step({},1/60);top=Math.max(top,w.feet[2]);}
  assert.ok(top>0.4&&top<0.6);assert.ok(w.grounded&&w.feet[2]===0);
  const c=new Walker(world([floor,[-5,-5,2,5,5,3]]));let h=0;c.step({jump:true},1/60);for(let i=0;i<90;i++){c.step({},1/60);h=Math.max(h,c.feet[2]);}
  assert.ok(h<0.25,'head hits the 2 m ceiling');
});
test('falls off an edge and lands below',()=>{
  const w=new Walker(world([[-10,-10,2,1,10,3],[ -100,-100,-1,100,100,0]]),[0,0,3]);run(w,{x:1,y:0},2);
  assert.ok(w.grounded);assert.ok(Math.abs(w.feet[2])<0.01);
});
test('nothing drawn below: holds position instead of falling forever',()=>{
  const w=new Walker(world([]));run(w,{x:0,y:0},1);assert.equal(w.feet[2],0);
});
test('rises onto a map surface that refines upward just after placing',()=>{
  const w=new Walker(world([[-100,-100,1.19,100,100,1.2]]));w.step({},1/60);assert.ok(Math.abs(w.feet[2]-1.2)<0.01);
});

test('creative flight: take off, rise, fly at Minecraft speeds, land by sinking',()=>{
  const w=new Walker(world([floor]));
  assert.equal(w.toggleFly(),true);
  run(w,{x:0,y:0,jump:true},2);assert.ok(w.feet[2]>12&&w.feet[2]<16,'rose about 7.5 m/s: '+w.feet[2]);
  run(w,{x:0,y:0},2);const h=w.feet[2];run(w,{x:0,y:0},2);assert.ok(Math.abs(w.feet[2]-h)<1e-6,'hovers without gravity');
  run(w,{x:0,y:1},2);const a=w.feet[1];run(w,{x:0,y:1},1);assert.ok(Math.abs(w.feet[1]-a-W.fly)<0.1,'flies 10.9 m/s');
  run(w,{x:0,y:1,sprint:true},2);const b=w.feet[1];run(w,{x:0,y:1,sprint:true},1);assert.ok(Math.abs(w.feet[1]-b-W.flySprint)<0.2,'sprint-flies 21.6 m/s');
  run(w,{x:0,y:0,sneak:true},4);assert.equal(w.flying,false,'touching the ground lands');assert.ok(Math.abs(w.feet[2])<1e-6);
});
test('stopping flight drops to the ground below, however far',()=>{
  const w=new Walker(world([floor]));w.toggleFly();run(w,{x:0,y:0,jump:true},12);assert.ok(w.feet[2]>80);
  w.toggleFly();run(w,{x:0,y:0},8);assert.ok(Math.abs(w.feet[2])<1e-6&&w.grounded,'fell to the floor: '+w.feet[2]);
});
test('flight stops at a ceiling and at walls',()=>{
  const w=new Walker(world([floor,[-5,-5,4,5,5,5],[-5,3,0,5,4,20]]));w.toggleFly();
  run(w,{x:0,y:0,jump:true},3);assert.ok(w.feet[2]+W.head<=4.01,'head under the ceiling');
  run(w,{x:0,y:1},3);assert.ok(w.feet[1]<3-W.radius+0.01,'wall stops forward flight');
});
test('Shift sneaks slowly on the ground',()=>{
  const w=new Walker(world([floor]));run(w,{x:0,y:1,sneak:true},2);const a=w.feet[1];run(w,{x:0,y:1,sneak:true},1);
  assert.ok(Math.abs(w.feet[1]-a-W.sneak)<0.05);
});
