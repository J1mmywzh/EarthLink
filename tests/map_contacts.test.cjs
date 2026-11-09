const{test}=require('node:test');const assert=require('node:assert/strict');
let M;try{M=require('../shared/viewer/map-contacts.js');}catch{}
const floor=async(o,d,max)=>d[2]<0&&o[2]>=0&&o[2]<=max?[o[0],o[1],0]:null;
test('local support is sampled from feet rather than above roofs',async()=>{
 assert.ok(M,'map contact adapter exists');let origins=[];
 const contacts=await M.sample([0,0,0],async(o,d,max)=>{origins.push(o);return floor(o,d,max);});
 assert.ok(contacts.indices.length>0);assert.ok(origins.filter(p=>p[2]<.3).length>=25);
 assert.equal(contacts.vertices.some(p=>p[2]>2),false);
});
test('unknown map space creates no invisible floor',async()=>{assert.ok(M);const c=await M.sample([0,0,0],async()=>null);assert.equal(c.indices.length,0);assert.equal(c.supported,false);});
test('a missing sample cannot be bridged by a floor triangle',async()=>{assert.ok(M);const c=await M.sample([0,0,0],async(o,d,max)=>Math.abs(o[0])<.1&&Math.abs(o[1])<.1?null:floor(o,d,max));assert.equal(c.supported,false);});
test('long-distance ray hits do not become local collisions',async()=>{assert.ok(M);const c=await M.sample([0,0,0],async()=>[0,0,-100]);assert.equal(c.indices.length,0);});
