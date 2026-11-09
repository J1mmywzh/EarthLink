/* Physical walking over the user's exported geometry. Streamed-map support is gated separately. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.EarthLinkWalking=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  let library;
  const vec=p=>({x:p[0],y:p[1],z:p[2]});
  async function create(mesh,options={}){
    if(mesh?.schema!==1||(!mesh.indices?.length&&!options.context?.indices?.length)||mesh.indices.length%3||!mesh.vertices)throw Error('No walkable mesh');
    if(!mesh.vertices.every(p=>p.length===3&&p.every(Number.isFinite))||!mesh.indices.every(i=>Number.isInteger(i)&&i>=0&&i<mesh.vertices.length))throw Error('Invalid walk mesh');
    library=library||(async()=>{const m=await import('./vendor/rapier.mjs');const R=m.default||m;await R.init();return R;})();
    const R=await library;
    return new Walker(R,mesh,options);
  }
  class Walker{
    constructor(R,mesh,{feet=[0,0,0],context=null}={}){
      if(!feet.every(Number.isFinite))throw Error('Invalid walking position');
      this.R=R;this.world=new R.World({x:0,y:0,z:-9.81});this.world.timestep=1/60;
      if(mesh.indices.length)this.world.createCollider(R.ColliderDesc.trimesh(new Float32Array(mesh.vertices.flat()),new Uint32Array(mesh.indices)));
      this.contextCollider=null;
      if(context)this.updateContext(context);
      this.world.step();
      const support=this.world.castRayAndGetNormal(new R.Ray({x:feet[0],y:feet[1],z:feet[2]+.22},{x:0,y:0,z:-1}),.5,true);
      if(!support||support.normal.z<Math.cos(Math.PI/4)){this.world.free();throw Error('Choose a floor');}
      const ground=feet[2]+.22-support.timeOfImpact;
      this.body=this.world.createRigidBody(R.RigidBodyDesc.kinematicPositionBased().setTranslation(feet[0],feet[1],ground+.91));
      this.collider=this.world.createCollider(R.ColliderDesc.capsule(.6,.3).setRotation({x:Math.SQRT1_2,y:0,z:0,w:Math.SQRT1_2}),this.body);
      this.world.step();
      if(this.world.intersectionWithShape(this.body.translation(),this.collider.rotation(),this.collider.shape,undefined,undefined,this.collider)){
        this.world.free();throw Error('Not enough room');
      }
      this.controller=this.world.createCharacterController(.01);this.controller.setUp({x:0,y:0,z:1});
      this.controller.enableAutostep(.2,.2,false);this.controller.enableSnapToGround(.25);
      this.controller.setMaxSlopeClimbAngle(Math.PI/4);this.controller.setMinSlopeSlideAngle(Math.PI/3);
      this.velocity=0;this.grounded=true;this.accumulator=0;this.jumpHeld=false;this.queuedJump=false;
    }
    get feet(){const p=this.body.translation();return[p.x,p.y,p.z-.9];}
    get eye(){const p=this.feet;return[p[0],p[1],p[2]+1.65];}
    supportedAt(feet,depth=3){
      const hit=this.world.castRayAndGetNormal(new this.R.Ray({x:feet[0],y:feet[1],z:feet[2]+.21},{x:0,y:0,z:-1}),depth,true,undefined,undefined,this.collider);
      return !!hit&&hit.normal.z>=Math.cos(Math.PI/4)-.001;
    }
    updateContext(mesh){
      if(this.contextCollider){this.world.removeCollider(this.contextCollider,true);this.contextCollider=null;}
      if(mesh?.indices?.length)this.contextCollider=this.world.createCollider(this.R.ColliderDesc.trimesh(new Float32Array(mesh.vertices.flat()),new Uint32Array(mesh.indices)));
      this.world.step();
    }
    step(input={},dt=1/60){
      if(!Number.isFinite(dt)||dt<=0)return this.feet;
      const jump=!!input.jump&&!this.jumpHeld;this.jumpHeld=!!input.jump;
      if(jump)this.queuedJump=true;
      this.accumulator=Math.min(.1,this.accumulator+Math.min(.1,dt));
      while(this.accumulator>=1/60-1e-10){
        this.accumulator-=1/60;
        let x=Number.isFinite(input.x)?input.x:0,y=Number.isFinite(input.y)?input.y:0;
        const length=Math.max(1,Math.hypot(x,y)),speed=input.sprint?3.8:1.4;x=x/length*speed/60;y=y/length*speed/60;
        if(this.queuedJump&&this.grounded){this.velocity=Math.sqrt(2*9.81*.45);this.grounded=false;}this.queuedJump=false;
        this.velocity-=9.81/60;
        const desired={x,y,z:this.velocity/60};
        this.controller.computeColliderMovement(this.collider,desired);
        const movement=this.controller.computedMovement(),p=this.body.translation();
        this.body.setNextKinematicTranslation({x:p.x+movement.x,y:p.y+movement.y,z:p.z+movement.z});this.world.step();
        this.grounded=this.controller.computedGrounded();
        if(this.grounded&&this.velocity<0)this.velocity=0;
        if(this.velocity>0&&movement.z<desired.z-.0001)this.velocity=0;
      }
      return this.feet;
    }
    free(){this.world.free();}
  }
  return{create};
});
