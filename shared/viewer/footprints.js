/* Union projected render triangles; preserve concavities, islands and holes. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./vendor/polygon-clipping.js'),require('./vendor/earcut.js'));else root.EarthLinkFootprints=factory(root.polygonClipping,root.earcut);})(typeof globalThis!=='undefined'?globalThis:this,function(clipping,earcut){
  'use strict';
  function derive(mesh){
    if(mesh?.schema!==1||!Array.isArray(mesh.vertices)||!Array.isArray(mesh.indices)||mesh.indices.length%3)throw Error('Invalid geometry');
    const v=mesh.vertices,ix=mesh.indices,polys=[];
    for(let i=0;i<ix.length;i+=3){
      const t=ix.slice(i,i+3).map(k=>{if(!Number.isInteger(k)||k<0||!v[k]||v[k].length!==3||!v[k].every(Number.isFinite))throw Error('Invalid mesh position');return v[k].slice(0,2);});
      const area=(t[1][0]-t[0][0])*(t[2][1]-t[0][1])-(t[1][1]-t[0][1])*(t[2][0]-t[0][0]);
      if(Math.abs(area)>1e-10)polys.push([[...t,t[0]]]);
    }
    if(!polys.length)return [];
    let level=polys.map(p=>[p]);
    while(level.length>1){const next=[];for(let i=0;i<level.length;i+=32)next.push(clipping.union(...level.slice(i,i+32)));level=next;}
    const result=[];
    for(const polygon of level[0]){
      if(polygon.length===1)result.push(polygon[0].slice(0,-1));
      else {const flat=earcut.flatten(polygon),triangles=earcut(flat.vertices,flat.holes,flat.dimensions);for(let i=0;i<triangles.length;i+=3)result.push(triangles.slice(i,i+3).map(k=>[flat.vertices[k*2],flat.vertices[k*2+1]]));}
      if(result.length>4096)throw Error('Footprint is too complex');
    }
    return result;
  }
  return {derive};
});
