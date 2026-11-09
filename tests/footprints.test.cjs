const{test}=require('node:test');const assert=require('node:assert/strict');
let F;try{F=require('../shared/viewer/footprints.js');}catch{}
const mesh=rects=>{const vertices=[],indices=[];for(const[x,y,w,h]of rects){let k=vertices.length;vertices.push([x,y,0],[x+w,y,0],[x+w,y+h,0],[x,y+h,0]);indices.push(k,k+1,k+2,k,k+2,k+3);}return{schema:1,vertices,indices};};
const area=polys=>polys.reduce((s,p)=>s+Math.abs(p.reduce((a,v,i)=>{const q=p[(i+1)%p.length];return a+v[0]*q[1]-q[0]*v[1];},0))/2,0);
const hit=(p,x,y)=>{let c=false;for(let i=0,j=p.length-1;i<p.length;j=i++){if((p[i][1]>y)!=(p[j][1]>y)&&x<(p[j][0]-p[i][0])*(y-p[i][1])/(p[j][1]-p[i][1])+p[i][0])c=!c;}return c;};
test('L shaped coverage does not fill its missing corner',()=>{assert.ok(F,'footprint module exists');const p=F.derive(mesh([[0,0,4,1],[0,1,1,3]]));assert.equal(area(p),7);assert.equal(p.some(r=>hit(r,2,2)),false);});
test('courtyard is preserved when decomposed for Cesium 1.140',()=>{assert.ok(F);const p=F.derive(mesh([[0,0,4,1],[0,3,4,1],[0,1,1,2],[3,1,1,2]]));assert.equal(area(p),12);assert.equal(p.some(r=>hit(r,2,2)),false);assert.equal(p.some(r=>hit(r,.4,2)),true);});
test('disconnected pieces do not cut the gap',()=>{assert.ok(F);const p=F.derive(mesh([[0,0,1,1],[10,0,1,1]]));assert.equal(area(p),2);assert.equal(p.some(r=>hit(r,5,.5)),false);});
test('vertical and degenerate triangles make no map hole',()=>{assert.ok(F);assert.deepEqual(F.derive({schema:1,vertices:[[0,0,0],[0,0,1],[1,0,1]],indices:[0,1,2]}),[]);});
test('invalid meshes fail instead of clipping their bounds',()=>{assert.ok(F);assert.throws(()=>F.derive({schema:1,vertices:[[0,0,0]],indices:[0,1,2]}));});
