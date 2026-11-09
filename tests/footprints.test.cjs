const{test}=require('node:test');const assert=require('node:assert/strict');
let F;try{F=require('../shared/viewer/footprints.js');}catch{}
const mesh=rects=>{const vertices=[],indices=[];for(const[x,y,w,h]of rects){let k=vertices.length;vertices.push([x,y,0],[x+w,y,0],[x+w,y+h,0],[x,y+h,0]);indices.push(k,k+1,k+2,k,k+2,k+3);}return{schema:1,vertices,indices};};
const area=polys=>polys.reduce((s,p)=>s+Math.abs(p.reduce((a,v,i)=>{const q=p[(i+1)%p.length];return a+v[0]*q[1]-q[0]*v[1];},0))/2,0);
const near=(a,b,tol=0.1)=>assert.ok(a>=b*0.999&&a<=b*(1+tol),`area ${a} vs ${b}`);
const hit=(p,x,y)=>{let c=false;for(let i=0,j=p.length-1;i<p.length;j=i++){if((p[i][1]>y)!=(p[j][1]>y)&&x<(p[j][0]-p[i][0])*(y-p[i][1])/(p[j][1]-p[i][1])+p[i][0])c=!c;}return c;};
test('L shaped coverage does not fill its missing corner',()=>{assert.ok(F,'footprint module exists');const p=F.derive(mesh([[0,0,4,1],[0,1,1,3]]));near(area(p),7);assert.equal(p.some(r=>hit(r,2,2)),false);});
test('courtyard is preserved when decomposed for Cesium 1.140',()=>{assert.ok(F);const p=F.derive(mesh([[0,0,4,1],[0,3,4,1],[0,1,1,2],[3,1,1,2]]));near(area(p),12);assert.equal(p.some(r=>hit(r,2,2)),false);assert.equal(p.some(r=>hit(r,.4,2)),true);});
test('disconnected pieces do not cut the gap',()=>{assert.ok(F);const p=F.derive(mesh([[0,0,1,1],[10,0,1,1]]));near(area(p),2);assert.equal(p.some(r=>hit(r,5,.5)),false);});
test('vertical and degenerate triangles make no map hole',()=>{assert.ok(F);assert.deepEqual(F.derive({schema:1,vertices:[[0,0,0],[0,0,1],[1,0,1]],indices:[0,1,2]}),[]);});
test('invalid meshes fail instead of clipping their bounds',()=>{assert.ok(F);assert.throws(()=>F.derive({schema:1,vertices:[[0,0,0]],indices:[0,1,2]}));});
test('a single projected triangle is covered, never short of it',()=>{assert.ok(F);const p=F.derive({schema:1,vertices:[[0,0,0],[1,0,0],[0,1,0]],indices:[0,1,2]});near(area(p),.5,0.12);assert.equal(p.some(r=>hit(r,.8,.8)),false);});
test('a large, finely split model stays fast and simple',()=>{const r=[];for(let x=0;x<200;x+=0.5)for(let y=0;y<280;y+=0.5)if(!(x>80&&x<120&&y>100&&y<140))r.push([x,y,0.5,0.5]);const t=Date.now(),p=F.derive(mesh(r));assert.ok(Date.now()-t<15000,'took '+(Date.now()-t)+' ms');assert.ok(p.length<=4096);near(area(p),200*280-40*40,0.02);assert.equal(p.some(q=>hit(q,100,120)),false);});
test('only the base is cut: an upside-down trapezoid keeps the map under its overhang',()=>{
  // closed solid: 2 x 2 m base at z=0, 6 x 6 m top at z=3
  const b=[[-1,-1,0],[1,-1,0],[1,1,0],[-1,1,0]],t=[[-3,-3,3],[3,-3,3],[3,3,3],[-3,3,3]],vertices=[...b,...t],indices=[0,2,1,0,3,2,4,5,6,4,6,7];
  for(let i=0;i<4;i++){const j=(i+1)%4;indices.push(i,j,4+j,i,4+j,4+i);}
  const p=F.derive({schema:1,vertices,indices});near(area(p),4,0.06);
  assert.equal(p.some(r=>hit(r,2,0)),false,'overhang keeps the map');assert.ok(p.some(r=>hit(r,0,0)),'base is cut');
});
test('a model resting a few millimetres off true still cuts its base',()=>{
  const p=F.derive({schema:1,vertices:[[0,0,0.004],[2,0,0],[2,2,0.006],[0,2,0],[0,0,3],[2,0,3],[2,2,3]],indices:[0,1,2,0,2,3,4,5,6]});
  near(area(p),4,0.06);
});
test('a margin widens the cut; the rings keep the true base, courtyards included',()=>{
  const m=mesh([[0,0,10,2],[0,8,10,2],[0,2,2,6],[8,2,2,6]]),a=F.deriveAll(m,0),b=F.deriveAll(m,0.4);
  near(area(a.polygons),64);assert.ok(area(b.polygons)>area(a.polygons)+10,'wider');
  assert.ok(b.polygons.some(r=>hit(r,-0.3,5))&&!b.polygons.some(r=>hit(r,-0.6,5)),'0.4 m past the edge, not more');
  assert.equal(b.polygons.some(r=>hit(r,5,5)),false,'courtyard stays');
  assert.equal(b.rings.length,2);const sa=b.rings.map(r=>r.reduce((s,p,i)=>{const q=r[(i+1)%r.length];return s+p[0]*q[1]-q[0]*p[1];},0)/2).sort((x,y)=>x-y);
  assert.ok(Math.abs(sa[1]-100)<4&&Math.abs(sa[0]+36)<3,'outer ring counter-clockwise, courtyard ring clockwise '+sa);assert.equal(b.base,0);
});
