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
  assert.ok(Math.abs(N.RATE.orbit/0.144-0.81)<0.01&&Math.abs(N.RATE.tilt/0.13-0.81)<0.01&&Math.abs(N.RATE.orbitMouse/0.27-0.81)<0.01&&Math.abs(N.RATE.pan/1.1-0.81)<0.01,'two steps of 10% less than beta.9: rotate, tilt and pan');
  assert.ok(Math.abs(N.RATE.pinch/0.0135-1.0247)<0.01&&Math.abs(N.RATE.wheel/0.0032-1.0247)<0.02&&Math.abs(N.RATE.scroll/0.0068-1.0247)<0.01,'zoom: then 10 % and 15 % faster (2026-11-14)');
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
  assert.equal(P(95,100),95,'the surface at the centre, near the model');
  assert.equal(P(1700,100,480),100,'a shallow view past the model: the model depth');
  assert.equal(P(null,100),100,'sky: the model depth');
  assert.equal(P(12,100),12,'a detail closer than the model');
  assert.equal(P(400,null,480),400);assert.equal(P(5000,null,480),480,'no model in view: limited');
  assert.equal(P(40,2000,480),40,'a model far behind the surface you see (placed too low, behind a hill): the surface');
  assert.equal(P(null,null),null);
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
test('inside a tree the camera may come down to the ground around it, no further',()=>{
  const f=new N.Floor(0.3);
  assert.equal(f.step(40,20),40);assert.equal(f.step(30,20),30);                       // above a 20 m tree
  f.inside=true;f.base=8;                                                               // the controller found it stands out of ground at 8 m
  assert.equal(f.step(18,20),18);assert.equal(f.step(12,20),12);assert.equal(f.step(5,20),8.3,'the ground around it carries the camera');
  assert.equal(f.step(9,8),9);assert.equal(f.base,null,'out of it: forgotten');
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
// Two strokes recorded on a MacBook trackpad in Chrome (120 events a second): [ms since the last event, deltaX, deltaY].
// The first tilts and is cut at 27 px per event by the next stroke 71 ms later; the second is cut and then reversed.
const STROKE_A=[[8,0,-31],[8,0,-31],[9,0,-30],[8,0,-33],[9,0,-34],[8,0,-31],[8,0,-30],[8,0,-30],[9,0,-28],[4,0,-27],[71,-1,0],[9,-4,2],[8,-3,1],[9,-6,2],[8,-10,2],[8,-11,2],[8,-12,2],[9,-13,2],[8,-14,2],[8,-15,2],[9,-25,3],[8,-7,1],[9,-20,2]];
const STROKE_B=[[8,0,-28],[8,0,-28],[9,0,-27],[8,0,-26],[9,0,-25],[8,0,-24],[8,0,-23],[9,0,-21],[8,0,-21],[67,0,1],[8,0,3],[1,0,1],[8,1,5],[8,1,8],[8,1,12],[9,1,20],[8,1,23],[8,1,26],[8,1,29],[10,2,49],[7,1,13],[9,2,36],[8,1,9],[9,1,25]];
function play(strokes,soft,lead=40){              // steady motion first, then the recorded events; returns what a 120 Hz screen shows per frame (px)
  const e=new N.Ease(),ev=[];let t=0;
  for(let i=0;i<lead;i++){t+=8.33;ev.push([t,strokes[0][1],strokes[0][2]]);}
  for(const [gap,dx,dy] of strokes){t+=gap;ev.push([t,dx,dy]);}
  const frames=[];let k=0,sum=[0,0],fed=[0,0];
  for(let now=0;now<t+900;now+=1000/120){
    while(k<ev.length&&ev[k][0]<=now){e.add('px',ev[k][1],soft);e.add('py',ev[k][2],soft);fed[0]+=ev[k][1];fed[1]+=ev[k][2];k++;}
    const m=e.take(1/120)||{px:0,py:0};sum[0]+=m.px;sum[1]+=m.py;frames.push([now,m.px,m.py]);
  }
  return {frames,sum,fed,end:t,cut:lead*8.33+strokes.slice(0,strokes.findIndex(q=>q[0]>40)).reduce((a,q)=>a+q[0],0)};
}
test('the system\'s glide counts in full: every scroll event turns the view by what it says',()=>{
  const L=new N.WheelLatch();let t=0;
  for(const m of [4,9,14,20,26,30,31,33])assert.equal(L.read({deltaX:0,deltaY:m,deltaMode:0,wheelDeltaY:-3*m},'perspective',t+=8).gain,1);
  for(let m=32;m>=0.5;m*=0.96){const r=Math.round(m);assert.equal(L.read({deltaX:0,deltaY:r,deltaMode:0,wheelDeltaY:-3*r},'perspective',t+=8).gain,1,'the glide after the fingers lift is what brings the turn to rest');}
});
test('a stroke cut short at speed comes to rest; it does not stop dead',()=>{
  const hard=play(STROKE_A,false),soft=play(STROKE_A,true);
  const at=(r,ms)=>{const f=r.frames.find(q=>q[0]>=r.cut+ms);return Math.abs(f[2]);};
  const before=at(soft,-10);assert.ok(before>26&&before<36,'steady before the cut: '+before);
  assert.ok(Math.abs(at(hard,-10)-before)<0.5,'and the same as without the soft release: steady motion is untouched');
  assert.ok(at(hard,50)<0.35*before,'released as it is, the view has all but stopped 50 ms after the cut: '+at(hard,50));
  assert.ok(at(soft,50)>0.55*before&&at(soft,50)<0.8*before,'with the soft release it is still at two thirds: '+at(soft,50));
  assert.ok(at(soft,150)>0.15*before&&at(soft,150)<0.45*before,'and fading at 150 ms: '+at(soft,150));
  let worst=0;for(let i=1;i<soft.frames.length;i++)if(soft.frames[i][0]>soft.cut-100)worst=Math.max(worst,Math.abs(soft.frames[i][2]-soft.frames[i-1][2]));
  assert.ok(worst<0.12*before,'no step in speed from one frame to the next: '+worst.toFixed(2)+' of '+before.toFixed(1));
  const over=Math.abs(soft.sum[1]-soft.fed[1]);assert.ok(over>40&&over<300,'it glides on by a little: '+over.toFixed(0)+' px');
  const side=soft.sum[0]-soft.fed[0];assert.ok(side<=0.5&&side>-90,'the next stroke, sideways, arrives in full (and glides on a little itself when it is cut): '+soft.sum[0].toFixed(1)+' of '+soft.fed[0]);
});
test('turning back: the old motion fades under the new one, and the new one counts in full',()=>{
  const r=play(STROKE_B,true),hard=play(STROKE_B,false);
  const ys=r.frames.filter(q=>q[0]>r.cut-20&&q[0]<r.cut+260).map(q=>q[2]);
  const hy=hard.frames.filter(q=>q[0]>r.cut-20&&q[0]<r.cut+260).map(q=>q[2]),jump=a=>Math.max(...a.slice(1).map((v,i)=>Math.abs(v-a[i])));
  assert.ok(jump(ys)<=jump(hy)+1.5,'no harder a change of speed than the fingers make themselves: '+jump(ys).toFixed(1)+' vs '+jump(hy).toFixed(1)+' | '+ys.map(v=>v.toFixed(0)).join(' '));
  const lull=a=>a.filter(v=>Math.abs(v)<3).length;assert.ok(lull(ys)<lull(hy),'and no standstill between the two strokes: '+lull(ys)+' frames near rest, '+lull(hy)+' without');
  assert.ok(Math.min(...ys)<-20&&Math.max(...ys)>12,'from one direction to the other');
  assert.ok(Math.abs((r.sum[1]-r.fed[1])-(hard.sum[1]-hard.fed[1]))<220);
});
test('moving fingers are followed exactly: steady, uneven or slow input gains nothing',()=>{
  let e=new N.Ease(),sum=0,fed=0;                                    // events and frames out of step, as on a real trackpad
  for(let i=0,t=0,next=0;i<1500;i++){t+=1000/120;while(next<=t){const d=(20+((i*7)%5))*Math.min(1,(1500-i)/300);e.add('heading',d,true);fed+=d;next+=7+((i*3)%4);}const m=e.take(1/120);if(m)sum+=m.heading;}   // uneven, then slowing down
  for(let i=0;i<200;i++){const m=e.take(1/120);if(m)sum+=m.heading;}
  assert.ok(Math.abs(sum-fed)/fed<0.004,'steady: '+sum.toFixed(1)+' of '+fed);
  e=new N.Ease();sum=0;fed=0;                                         // a careful stop: the fingers slow down themselves
  for(let i=0;i<300;i++){const d=Math.max(0,0.5-i*0.004);if(d){e.add('heading',d,true);fed+=d;}const m=e.take(1/120);if(m)sum+=m.heading;}
  for(let i=0;i<200;i++){const m=e.take(1/120);if(m)sum+=m.heading;}
  assert.ok(Math.abs(sum-fed)<0.02,'a slow, careful stop lands where the fingers stopped: '+(sum-fed).toFixed(4));
  e=new N.Ease();sum=0;e.add('zoom',0.26);for(let i=0;i<400;i++){const m=e.take(1/120);if(m)sum+=m.zoom;}
  assert.ok(Math.abs(sum-0.26)<1e-9,'a wheel notch zooms by exactly its step');
  e=new N.Ease();sum=0;for(let i=0;i<60;i++){e.add('heading',3);const m=e.take(1/120);if(m)sum+=m.heading;}for(let i=0;i<300;i++){const m=e.take(1/120);if(m)sum+=m.heading;}
  assert.ok(Math.abs(sum-180)<1e-6,'a mouse drag (not soft) stops where the mouse stopped');
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

test('the view may tilt freely near the ground, less higher up, not at all from space',()=>{
  assert.equal(N.maxTilt(500),180);assert.equal(N.maxTilt(N.GLOBE.low),180);assert.equal(N.maxTilt(N.GLOBE.high),0);assert.equal(N.maxTilt(2e7),0);
  let last=180;for(let h=N.GLOBE.low*1.01;h<N.GLOBE.high;h*=1.3){const t=N.maxTilt(h);assert.ok(t<=last&&t>=0);last=t;}
  assert.ok(N.GLOBE.spin>N.GLOBE.low&&N.GLOBE.spin<N.GLOBE.high);
});
