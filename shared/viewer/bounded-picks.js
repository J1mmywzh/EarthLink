/* Version-pinned Cesium 1.140 query adapter. Keep offscreen preloading local. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.EarthLinkBoundedPicks=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  class Queries{
    constructor(scene){
      const p=scene?._picking,f=p?._pickOffscreenView?.camera?.frustum;
      if(!Array.isArray(p?._mostDetailedRayPicks)||!f||!Number.isFinite(f.far)||typeof scene.pickFromRayMostDetailed!=='function')throw Error('Walk is unavailable in this browser.');
      this.scene=scene;this.picking=p;this.frustum=f;this.jobs=new Set();this.active=false;this.closed=false;this.generation=0;
    }
    acquire(){
      if(this.active)return;
      if(this.picking._earthLinkOwner||this.picking._mostDetailedRayPicks.length)throw Error('Surface loading. Try again.');
      this.saved={near:this.frustum.near,far:this.frustum.far};this.frustum.near=.01;this.frustum.far=3.05;
      this.picking._earthLinkOwner=this;this.active=true;this.generation++;
    }
    async cast(ray,exclude,width){
      if(this.closed)return null;
      this.acquire();const generation=this.generation,list=this.picking._mostDetailedRayPicks,count=list.length;
      const promise=this.scene.pickFromRayMostDetailed(ray,exclude,width),job=list.length>count?list[list.length-1]:null;
      if(job)this.jobs.add(job);
      try{const result=await promise;return this.active&&generation===this.generation?result:null;}
      finally{if(job)this.jobs.delete(job);}
    }
    cancelPending(){
      this.generation++;const list=this.picking._mostDetailedRayPicks;
      for(const job of this.jobs){const i=list.indexOf(job);if(i>=0)list.splice(i,1);}this.jobs.clear();
    }
    stop(){
      this.closed=true;
      this.cancelPending();if(!this.active)return;
      if(this.picking._earthLinkOwner===this){this.frustum.near=this.saved.near;this.frustum.far=this.saved.far;delete this.picking._earthLinkOwner;}
      this.active=false;
    }
  }
  return{Queries};
});
