/* Site-local, roll-free camera math. Angles are degrees; lengths are metres. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.EarthLinkNavigation=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const rad=Math.PI/180,clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
  class Orbit {
    constructor(o={}) {
      this.target=(o.target||[0,0,0]).slice();this.distance=o.distance||100;
      this.heading=o.heading||0;this.tilt=o.tilt??35;this.projection=o.projection||'perspective';
      this.halfHeight=o.halfHeight||30;this.constrain();
    }
    constrain(){this.heading=((this.heading%360)+360)%360;this.tilt=clamp(this.tilt,this.projection==='two_point'?10:0,85);this.distance=clamp(this.distance,.05,1e8);this.halfHeight=clamp(this.halfHeight,.01,1e8);}
    orbit(dx,dy){if(Number.isFinite(dx)&&Number.isFinite(dy)){this.heading+=dx;this.tilt+=dy;this.constrain();}return this;}
    pan(x,y){if(!Number.isFinite(x)||!Number.isFinite(y))return this;const p=this.pose();this.target=this.target.map((v,i)=>v+p.right[i]*x+p.up[i]*y);return this;}
    zoom(factor){if(Number.isFinite(factor)&&factor>0){if(this.projection==='parallel')this.halfHeight*=factor;else this.distance*=factor;this.constrain();}return this;}
    north(){this.heading=0;return this;}
    pose(){
      this.constrain();const h=this.heading*rad,t=this.tilt*rad;
      const virtual=[Math.sin(h)*Math.sin(t),Math.cos(h)*Math.sin(t),-Math.cos(t)];
      const right=[Math.cos(h),-Math.sin(h),0];
      return {position:this.target.map((v,i)=>v-virtual[i]*this.distance),
        direction:this.projection==='two_point'?[Math.sin(h),Math.cos(h),0]:virtual,
        up:this.projection==='two_point'?[0,0,1]:[Math.sin(h)*Math.cos(t),Math.cos(h)*Math.cos(t),Math.sin(t)],
        right,shift:this.projection==='two_point'?Math.tan((this.tilt-90)*rad):0,halfHeight:this.halfHeight};
    }
  }
  function wheelAction(e,device='auto') {
    const scale=e.deltaMode===1?16:e.deltaMode===2?200:1;
    const x=(Number.isFinite(e.deltaX)?e.deltaX:0)*scale,y=(Number.isFinite(e.deltaY)?e.deltaY:0)*scale;
    const mouse=device==='mouse'||(device==='auto'&&!e.deltaX&&(e.deltaMode>0||Math.abs(e.deltaY)>=45));
    if(e.ctrlKey||mouse)return {type:'zoom',factor:Math.exp(clamp(y,-200,200)*.008)};
    return {type:e.shiftKey?'pan':'orbit',x,y};
  }
  return {Orbit,wheelAction};
});
