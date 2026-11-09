const{test}=require('node:test');const assert=require('node:assert/strict');
let B;try{B=require('../shared/viewer/bounded-picks.js');}catch{}
function fixture(){let resolve;const scene={_picking:{_mostDetailedRayPicks:[],_pickOffscreenView:{camera:{frustum:{near:.1,far:1e9}}}},pickFromRayMostDetailed(){this._picking._mostDetailedRayPicks.push({});return new Promise(r=>resolve=r);}};return{scene,resolve:v=>resolve(v)};}
test('contact queries limit the actual offscreen volume rather than only filtering results',async()=>{assert.ok(B,'bounded map adapter exists');const f=fixture(),q=new B.Queries(f.scene);const promise=q.cast({},[],.05);assert.equal(f.scene._picking._pickOffscreenView.camera.frustum.far,3.05);f.resolve({position:[0,0,0]});await promise;q.stop();assert.equal(f.scene._picking._pickOffscreenView.camera.frustum.far,1e9);});
test('leaving walk cancels only its requests and restores query settings',async()=>{assert.ok(B);const f=fixture(),q=new B.Queries(f.scene),promise=q.cast({},[],.05),other={};f.scene._picking._mostDetailedRayPicks.push(other);q.stop();assert.deepEqual(f.scene._picking._mostDetailedRayPicks,[other]);assert.equal(f.scene._picking._pickOffscreenView.camera.frustum.near,.1);f.resolve({position:[1,2,3]});assert.equal(await promise,null);});
test('unsupported engine internals fail explicitly',()=>{assert.ok(B);assert.throws(()=>new B.Queries({}));});
test('a sample stopped between floor and obstacle phases cannot reacquire ownership',async()=>{
 const M=require('../shared/viewer/map-contacts.js');let calls=0,q;const f=fixture();
 f.scene.pickFromRayMostDetailed=function(ray){calls++;const job={};this._picking._mostDetailedRayPicks.push(job);queueMicrotask(()=>{const i=this._picking._mostDetailedRayPicks.indexOf(job);if(i>=0)this._picking._mostDetailedRayPicks.splice(i,1);});if(calls===49)queueMicrotask(()=>q.stop());return Promise.resolve({position:ray.direction[2]<0?[ray.origin[0],ray.origin[1],0]:null});};
 q=new B.Queries(f.scene);await M.sample([0,0,0],async(o,d)=>{const r=await q.cast({origin:o,direction:d},[],.05);return r?.position;});
 assert.equal(calls,49);assert.equal(f.scene._picking._earthLinkOwner,undefined);assert.equal(f.scene._picking._pickOffscreenView.camera.frustum.far,1e9);
});
