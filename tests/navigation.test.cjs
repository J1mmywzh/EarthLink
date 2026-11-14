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
  assert.ok(N.RATE.orbit>0&&N.RATE.orbit<0.3);assert.ok(N.RATE.tilt<N.RATE.orbit);assert.ok(N.RATE.pan>0.85&&N.RATE.pan<=1);
  assert.ok(Math.abs(N.RATE.orbit/0.144-0.81)<0.01&&Math.abs(N.RATE.tilt/0.13-0.81)<0.01&&Math.abs(N.RATE.orbitMouse/0.27-0.81)<0.01&&Math.abs(N.RATE.pan/1.1-0.81)<0.01&&Math.abs(N.RATE.pinch/0.0135-0.81)<0.01&&Math.abs(N.RATE.wheel/0.0032-0.81)<0.02,'two steps of 10% less than beta.9: rotate, tilt, pan and zoom');
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
test('the pivot is what is at the centre of the view; at the horizon, the model or a limit',()=>{
  const P=N.pivotDistance;
  assert.equal(P(95,100,400),95,'the surface at the centre');
  assert.equal(P(250,100,400),250,'ground behind the model but near: still what you look at');
  assert.equal(P(1700,100,400),100,'a shallow view past the model: the model depth');
  assert.equal(P(null,100,400),100,'sky: the model depth');
  assert.equal(P(12,100,400),12,'a detail closer than the model');
  assert.equal(P(5000,null,480),480,'no model in view: limited');
  assert.equal(P(null,null,400),null);
});
test('a pinch has to be meant: the small pinches of scrolling or resting fingers are dropped, a real pinch zooms at once',()=>{
  const l=new N.WheelLatch();let t=0;
  assert.equal(l.read(pad(0,6),'perspective',t).mode,'orbit');
  for(let i=0;i<40;i++){t+=16;assert.equal(l.read(pad(1,5),'perspective',t).mode,'orbit');           // two fingers tilting, drifting apart a little
    t+=1;assert.equal(l.read(pad(0,-0.5,{ctrlKey:true}),'perspective',t).skip,true,'stray pinch dropped while scrolling');}
  for(let i=0;i<30;i++){t+=16;assert.equal(l.read(pad(0,i%2?0.15:-0.15,{ctrlKey:true}),'perspective',t).skip,true,'fingers resting on the pad: their drift is dropped');}
  t+=16;assert.equal(l.read(pad(0,4),'perspective',t).mode,'orbit','and the rotation carries on');
  t+=400;                                                                                               // fingers lifted
  let z=l.read(pad(0,-2,{ctrlKey:true}),'perspective',t);assert.equal(z.skip,true,'the first 3 % of a pinch decide that it is one');
  t+=16;z=l.read(pad(0,-2,{ctrlKey:true}),'perspective',t);assert.equal(z.mode,'zoom');assert.ok(!z.skip&&z.start,'the pinch zooms');
  t+=16;assert.equal(l.read(pad(3,0),'perspective',t).skip,true,'a stray scroll during the pinch is dropped');
  t+=16;assert.equal(l.read(pad(0,-2,{ctrlKey:true}),'perspective',t).mode,'zoom');
  t+=200;assert.equal(l.read(pad(0,5),'perspective',t).mode,'orbit','scrolling takes over once the pinch is quiet');
  for(let i=0;i<4;i++){t+=16;l.read(pad(0,5),'perspective',t);}
  let took=false;for(let i=0;i<6&&!took;i++){t+=16;took=!l.read(pad(0,-6,{ctrlKey:true}),'perspective',t).skip;}   // a firm pinch right after a flick, its glide still running
  assert.ok(took,'a firm pinch takes over from a scroll that is still running');
  {const s=new N.WheelLatch();let u=0,began=-1;for(let i=0;i<180&&began<0;i++){u+=16;if(!s.read(pad(0,-0.15,{ctrlKey:true}),'perspective',u).skip)began=i;}
   assert.ok(began>0&&began<=22,'a slow pinch (9 % a second) starts within a third of a second: '+began);}
  {const s=new N.WheelLatch();let u=0,any=false;for(let i=0;i<300;i++){u+=16;any=any||!s.read(pad(0,i%2?0.4:-0.4,{ctrlKey:true}),'perspective',u).skip;}assert.equal(any,false,'jitter back and forth never zooms, however long');}
  assert.equal(new N.WheelLatch().read({deltaX:0,deltaY:-100,deltaMode:0,ctrlKey:true,shiftKey:false},'perspective',0).mode,'zoom','Ctrl + mouse wheel zooms from the first notch');
});
test('the device is corrected when the first event misleads, and remembered',()=>{
  const ev=(deltaY,wheelDeltaY,deltaX=0)=>({deltaX,deltaY,deltaMode:0,wheelDeltaY,ctrlKey:false,shiftKey:false});
  let l=new N.WheelLatch();                                // a zoomed page: a trackpad step of 40 looks like a wheel notch
  assert.equal(l.read(ev(36.36,-120),'perspective',0).mode,'zoom');
  const r=l.read(ev(30,-99),'perspective',16);assert.equal(r.mode,'orbit');assert.equal(r.start,true,'restarts as a rotation');
  assert.equal(l.read(ev(20,-66),'perspective',32).mode,'orbit');
  assert.equal(l.read(ev(40,-120),'perspective',1000).mode,'orbit','remembered: an ambiguous start is a trackpad');
  l=new N.WheelLatch();                                    // a wheel whose first notch moved exactly 40
  assert.equal(l.read(ev(40,-120),'perspective',0).mode,'orbit');
  l.read(ev(52,-120),'perspective',30);assert.equal(l.read(ev(64,-240),'perspective',60).mode,'zoom','two sure wheel notches');
  assert.equal(l.read(ev(40,-120),'perspective',2000).mode,'zoom','remembered');
  l=new N.WheelLatch();assert.equal(l.read(ev(4,-120),'perspective',0,false).mode,'zoom');
});
test('the glide after the fingers lift keeps its length and counts for less; moving fingers count in full',()=>{
  let c=new N.Coast(),sum=0,raw=0,gains=[];
  for(const m of [4,9,14,20,26,30,31,33])assert.equal(c.gain(0,m),1);          // fingers speeding up
  for(let m=32;m>=0.5;m*=0.93){const g=c.gain(0,m);gains.push(g);sum+=m*g;raw+=m;}            // the glide
  assert.ok(sum<0.8*raw&&sum>0.55*raw,'the glide turns less than the system sends: '+(sum/raw).toFixed(2));
  assert.ok(Math.min(...gains)>=0.55-1e-9,'and never dies away: it comes to rest as the system\'s glide does, not suddenly');
  for(let i=1;i<gains.length;i++)assert.ok(gains[i-1]-gains[i]<0.12,'no step in its weight');
  const back=[c.gain(0,6),c.gain(0,7),c.gain(0,8),c.gain(0,9),c.gain(0,10),c.gain(0,11),c.gain(0,12),c.gain(0,13),c.gain(0,14),c.gain(0,15),c.gain(0,16)];
  assert.ok(back[0]>0.7&&back[back.length-1]===1,'steps that grow again are the fingers: full weight within a few events '+back.map(v=>v.toFixed(2)));
  c=new N.Coast();for(let i=0;i<60;i++)assert.equal(c.gain(2,0),1,'a steady slow rotation is untouched');
  c=new N.Coast();for(const m of [9,8,8,7,9,8,7,7,6,8,7,6,6,7])assert.equal(c.gain(m,0),1,'noisy fingers slowing down');
});
test('zoom is released more slowly than a turn, and still exactly',()=>{
  const e=new N.Ease();e.add('zoom',1);e.add('heading',1);let z=0,h=0,nz=0,nh=0,out;
  while((out=e.take(1/60))){if(out.zoom){z+=out.zoom;nz++;}if(out.heading){h+=out.heading;nh++;}}
  assert.ok(Math.abs(z-1)<1e-9&&Math.abs(h-1)<1e-9);assert.ok(nz>1.5*nh&&nz<70,'frames: zoom '+nz+', turn '+nh);
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
test('time of day: the map is untouched by day, warm at sunset, dark blue at night; no shadows from a set sun',()=>{
  const D=N.daylight,day=D(45),set=D(1),night=D(-12);
  assert.deepEqual(day.tint,[1,1,1]);assert.equal(day.night,0);assert.equal(day.shadow,1);
  assert.ok(set.tint[0]>set.tint[2]+0.2,'warm');assert.ok(set.shadow<0.05,'a sun on the horizon casts almost no shadow');
  assert.equal(night.night,1);assert.ok(night.tint.every(v=>v<0.3)&&night.tint[2]>night.tint[0],'dark and blue');assert.equal(night.shadow,0);
  assert.ok(night.sky.every(v=>v<0.05));
  let last=D(20).tint[0]+D(20).tint[1]+D(20).tint[2];
  for(let e=19;e>=-10;e--){const t=D(e).tint,sum=t[0]+t[1]+t[2];assert.ok(sum<=last+1e-9,'darkens steadily: '+e);last=sum;}
});
