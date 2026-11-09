const{test}=require('node:test');const assert=require('node:assert/strict');
let W;try{W=require('../shared/viewer/walking.js');}catch{}
function mesh(boxes=[]){const vertices=[[-20,-20,0],[20,-20,0],[20,20,0],[-20,20,0]],indices=[0,1,2,0,2,3];
 for(const[x,y,z,w,d,h]of boxes){const k=vertices.length;vertices.push([x,y,z],[x+w,y,z],[x+w,y+d,z],[x,y+d,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+d,z+h],[x,y+d,z+h]);for(const[a,b,c,d]of[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])indices.push(k+a,k+b,k+c,k+a,k+c,k+d);}return{schema:1,vertices,indices};}
async function make(g=mesh(),feet=[0,0,.02]){assert.ok(W,'walking module exists');return W.create(g,{feet});}
const settle=w=>{for(let i=0;i<30;i++)w.step({},1/60);};
test('person grounds on floor at eye height above feet',async()=>{const w=await make();settle(w);assert.ok(w.grounded);assert.ok(Math.abs(w.feet[2])<.03);assert.ok(Math.abs(w.eye[2]-w.feet[2]-1.65)<1e-6);w.free();});
test('diagonal movement is normalized and sprint is faster',async()=>{const a=await make(),b=await make(),c=await make();[a,b,c].forEach(settle);for(let i=0;i<60;i++){a.step({x:1},1/60);b.step({x:1,y:1},1/60);c.step({x:1,sprint:true},1/60);}assert.ok(Math.abs(Math.hypot(...b.feet.slice(0,2))-a.feet[0])<.03);assert.ok(c.feet[0]>a.feet[0]*2);[a,b,c].forEach(w=>w.free());});
test('a thin wall blocks a sprint without tunneling',async()=>{const w=await make(mesh([[1,-4,0,.04,8,4]]));settle(w);for(let i=0;i<120;i++)w.step({x:1,sprint:true},1/60);assert.ok(w.feet[0]<.72);w.free();});
test('ordinary stair rises are stepped but a tall wall is not',async()=>{const w=await make(mesh([[.8,-1,0,1,2,.18],[1.8,-1,0,1,2,.36],[2.8,-1,0,1,2,1.2]]));settle(w);let top=0;for(let i=0;i<150;i++){w.step({x:1},1/60);top=Math.max(top,w.feet[2]);}assert.ok(top>.34);assert.ok(w.feet[0]<2.55);w.free();});
test('jump rises and lands without allowing a second airborne jump',async()=>{const w=await make();settle(w);let peak=0;w.step({jump:true},1/60);for(let i=0;i<120;i++){w.step({jump:true},1/60);peak=Math.max(peak,w.feet[2]);}assert.ok(peak>.3&&peak<.6);assert.ok(Math.abs(w.feet[2])<.03);w.free();});
test('floor below a roof remains the supporting floor and ceiling stops jump',async()=>{const w=await make(mesh([[-3,-3,2.1,6,6,.3]]));settle(w);assert.ok(w.feet[2]<.03);let top=0;w.step({jump:true},1/60);for(let i=0;i<80;i++){w.step({},1/60);top=Math.max(top,w.feet[2]);}assert.ok(top<.32);assert.ok(w.feet[2]<.03);w.free();});
test('resuming after a long pause does not leap through obstacles',async()=>{const w=await make(mesh([[1,-4,0,.04,8,4]]));settle(w);w.step({x:1,sprint:true},60);assert.ok(w.feet[0]<.72);w.free();});
test('invalid geometry and unsupported spawn fail explicitly',async()=>{assert.ok(W);await assert.rejects(()=>W.create({schema:1,vertices:[],indices:[]},{feet:[0,0,0]}));});
test('unknown floor is distinguishable from real support',async()=>{const w=await make();settle(w);assert.equal(w.supportedAt([0,0,0]),true);assert.equal(w.supportedAt([50,50,0]),false);w.free();});
test('transient map contacts support a person without an invented infinite plane',async()=>{assert.ok(W);const M=require('../shared/viewer/map-contacts.js');const context=await M.sample([0,0,0],async(o,d,max)=>d[2]<0?[o[0],o[1],0]:null);const w=await W.create({schema:1,vertices:[],indices:[]},{context,feet:[0,0,0]});settle(w);assert.ok(w.grounded);assert.equal(w.supportedAt([5,5,0]),false);w.free();});
test('a jump pulse survives frames shorter than one physics tick',async()=>{const w=await make();settle(w);w.step({jump:true},1/240);let peak=0;for(let i=0;i<240;i++){w.step({},1/240);peak=Math.max(peak,w.feet[2]);}assert.ok(peak>.3);w.free();});
test('rolling sampled contacts climb ordinary stairs and block a tall step',async()=>{
 const M=require('../shared/viewer/map-contacts.js'),source=await make(mesh([[.8,-1,0,1,2,.18],[1.8,-1,0,1,2,.36],[2.8,-1,0,1,2,1.2]]),[-5,0,.02]);
 const ray=async(o,d,max)=>{const r=new source.R.Ray({x:o[0],y:o[1],z:o[2]},{x:d[0],y:d[1],z:d[2]}),h=source.world.castRayAndGetNormal(r,max,true,undefined,undefined,source.collider);return h?o.map((n,i)=>n+d[i]*h.timeOfImpact):null;};
 let context=await M.sample([0,0,0],ray);const w=await W.create({schema:1,vertices:[],indices:[]},{feet:[0,0,0],context});settle(w);let top=0;
 for(let i=0;i<240;i++){if(Math.abs(w.feet[0]-context.center[0])>.12){context=await M.sample(w.feet,ray);w.updateContext(context);}w.step({x:1},1/60);top=Math.max(top,w.feet[2]);}
 assert.ok(top>.32,`stairs climbed: ${top}`);assert.ok(w.feet[0]<2.55,`tall step blocked: ${w.feet[0]}`);w.free();source.free();
});
