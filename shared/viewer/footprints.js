/* The plan outline of a model, for "Hide map under model".

   Every triangle is painted onto a fine grid (seen from above), the painted area's edges are traced into
   rings, straightened, and returned as simple polygons Cesium can clip with. Courtyards, separate buildings
   and concave corners are kept. Painting is conservative: the outline may reach up to one grid cell past the
   model, never short of it. The cell is chosen from the model's size (about 2 million cells at most). */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.EarthLinkFootprints=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const MAX_POLYGONS=4096;

  function triangles(mesh){
    if(mesh?.schema!==1||!Array.isArray(mesh.vertices)||!Array.isArray(mesh.indices)||mesh.indices.length%3)throw Error('Invalid geometry');
    const v=mesh.vertices,ix=mesh.indices,out=[];
    for(const k of ix)if(!Number.isInteger(k)||k<0||!v[k]||v[k].length!==3||!v[k].every(Number.isFinite))throw Error('Invalid mesh position');
    for(let i=0;i<ix.length;i+=3){
      const a=v[ix[i]],b=v[ix[i+1]],c=v[ix[i+2]];
      const area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
      if(Math.abs(area)>1e-9)out.push(a[0],a[1],b[0],b[1],c[0],c[1]);   // walls seen edge-on cover nothing
    }
    return out;
  }

  // Paint every cell a triangle touches. Row by row: the triangle's x-extent within the row's band.
  function paint(t,x0,y0,cell,nx,ny){
    const g=new Uint8Array(nx*ny);
    for(let i=0;i<t.length;i+=6){
      const P=[[t[i],t[i+1]],[t[i+2],t[i+3]],[t[i+4],t[i+5]]];
      const ymin=Math.min(P[0][1],P[1][1],P[2][1]),ymax=Math.max(P[0][1],P[1][1],P[2][1]);
      const r0=Math.max(0,Math.floor((ymin-y0)/cell)),r1=Math.min(ny-1,Math.floor((ymax-y0)/cell));
      for(let r=r0;r<=r1;r++){
        const lo=y0+r*cell,hi=lo+cell;let a=Infinity,b=-Infinity;
        for(let k=0;k<3;k++){
          const p=P[k],q=P[(k+1)%3];
          if(p[1]>=lo&&p[1]<=hi){a=Math.min(a,p[0]);b=Math.max(b,p[0]);}
          for(const y of [lo,hi])if((p[1]-y)*(q[1]-y)<0){const x=p[0]+(q[0]-p[0])*(y-p[1])/(q[1]-p[1]);a=Math.min(a,x);b=Math.max(b,x);}
        }
        if(a>b)continue;
        const c0=Math.max(0,Math.floor((a-x0)/cell)),c1=Math.min(nx-1,Math.floor((b-x0)/cell));
        g.fill(1,r*nx+c0,r*nx+c1+1);
      }
    }
    return g;
  }

  // Edges between painted and empty cells, linked into closed rings (painted area on the left).
  function trace(g,stride,c0,nx,ny){                  // columns c0 .. c0+nx-1 of the grid
    const at=(c,r)=>c>=0&&r>=0&&c<nx&&r<ny&&g[r*stride+c0+c]===1;
    const next=new Map(),key=(x,y)=>y*(nx+1)+x;
    const edge=(ax,ay,bx,by)=>{const k=key(ax,ay);(next.get(k)||next.set(k,[]).get(k)).push([bx,by]);};
    for(let r=0;r<ny;r++)for(let c=0;c<nx;c++){
      if(!at(c,r))continue;
      if(!at(c,r-1))edge(c,r,c+1,r);
      if(!at(c+1,r))edge(c+1,r,c+1,r+1);
      if(!at(c,r+1))edge(c+1,r+1,c,r+1);
      if(!at(c-1,r))edge(c,r+1,c,r);
    }
    const rings=[];
    for(const [k0,list] of next){
      while(list.length){
        const ring=[[k0%(nx+1),Math.floor(k0/(nx+1))]];let [x,y]=list.pop(),prev=ring[0];
        while(!(x===ring[0][0]&&y===ring[0][1])){
          ring.push([x,y]);
          const out=next.get(key(x,y));
          // at a corner shared by two diagonal cells, turn left so rings never cross
          let j=0;if(out.length>1){const dx=x-prev[0],dy=y-prev[1];j=out.findIndex(([u,v])=>(dx*(v-y)-dy*(u-x))>0);if(j<0)j=0;}
          prev=[x,y];[x,y]=out.splice(j,1)[0];
        }
        rings.push(ring);
      }
    }
    return rings;
  }

  function simplify(ring,tol,fixed){                    // Douglas-Peucker on a closed ring; fixed points stay
    const n=ring.length;if(n<4)return ring;
    let far=0,fd=-1;for(let i=1;i<n;i++){const d=Math.hypot(ring[i][0]-ring[0][0],ring[i][1]-ring[0][1]);if(d>fd){fd=d;far=i;}}
    const keep=new Uint8Array(n);keep[0]=keep[far]=1;
    if(fixed){const on=ring.map(fixed);for(let i=0;i<n;i++)if(on[i]&&!(on[(i+n-1)%n]&&on[(i+1)%n]))keep[i]=1;}   // ends of runs
    const run=(a,b)=>{                                   // b may wrap to n (= 0)
      const stack=[[a,b]];
      while(stack.length){
        const [i,j]=stack.pop(),A=ring[i],B=ring[j%n],dx=B[0]-A[0],dy=B[1]-A[1],L=Math.hypot(dx,dy)||1;
        let m=-1,md=tol;
        for(let k=i+1;k<j;k++){const P=ring[k],d=Math.abs(dx*(A[1]-P[1])-dy*(A[0]-P[0]))/L;if(d>md){md=d;m=k;}}
        if(m>=0){keep[m]=1;stack.push([i,m],[m,j]);}
        else for(let k=i+1;k<j;k++)if(keep[k]){stack.push([i,k],[k,j]);break;}   // split at a fixed point
      }
    };
    run(0,far);run(far,n);
    return ring.filter((_,i)=>keep[i]);
  }
  const signed=r=>r.reduce((s,p,i)=>{const q=r[(i+1)%r.length];return s+p[0]*q[1]-q[0]*p[1];},0)/2;

  /* Cesium's clipping polygons have no holes. Instead of triangulating a courtyard's surroundings (thousands of
     pieces, each slowing every frame), cut the plan into strips at every courtyard: each courtyard is crossed by
     a cut, so every strip's outline is a plain polygon, and the strips meet exactly. */
  function outline(t,cell){
    let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
    for(let i=0;i<t.length;i+=2){x0=Math.min(x0,t[i]);x1=Math.max(x1,t[i]);y0=Math.min(y0,t[i+1]);y1=Math.max(y1,t[i+1]);}
    x0-=cell;y0-=cell;
    const nx=Math.ceil((x1-x0)/cell)+2,ny=Math.ceil((y1-y0)/cell)+2;
    const g=paint(t,x0,y0,cell,nx,ny),minHole=Math.max(1,cell*cell*2)/(cell*cell);   // gaps under 1 m² are not courtyards
    const cuts=new Set();
    for(const r of trace(g,nx,0,nx,ny))if(-signed(r)>=minHole){
      let a=Infinity,b=-Infinity;for(const p of r){a=Math.min(a,p[0]);b=Math.max(b,p[0]);}
      cuts.add(Math.floor((a+b)/2));
    }
    const edges=[0,...[...cuts].sort((a,b)=>a-b),nx],result=[];
    for(let k=0;k+1<edges.length;k++){
      const c0=edges[k],w=edges[k+1]-c0;if(w<=0)continue;
      for(const r of trace(g,nx,c0,w,ny)){
        if(signed(r)<=0)continue;                        // a small gap left inside a strip is covered
        const q=simplify(r,1,([c])=>(c===0&&c0>0)||(c===w&&c0+w<nx));   // strips keep their shared edges exact
        if(q.length>=3)result.push(q.map(([c,rr])=>[x0+(c0+c)*cell,y0+rr*cell]));
      }
    }
    return result;
  }

  function derive(mesh){
    const t=triangles(mesh);if(!t.length)return [];
    let x0=Infinity,y0=Infinity,x1=-Infinity,y1=-Infinity;
    for(let i=0;i<t.length;i+=2){x0=Math.min(x0,t[i]);x1=Math.max(x1,t[i]);y0=Math.min(y0,t[i+1]);y1=Math.max(y1,t[i+1]);}
    let cell=Math.max(Math.sqrt((x1-x0)*(y1-y0)/2e6),Math.max(x1-x0,y1-y0)/4000,0.01);
    for(let i=0;i<6;i++,cell*=2){const r=outline(t,cell);if(r.length<=MAX_POLYGONS)return r;}
    throw Error('Footprint is too complex');
  }
  return {derive};
});
