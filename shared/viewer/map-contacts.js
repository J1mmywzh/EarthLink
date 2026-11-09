/* Transient local contacts from rendered map ray queries; no tile mesh extraction or storage. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.EarthLinkMapContacts=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  async function sample(feet,ray,cache=new Map()){
    const center=[Math.round(feet[0]*4)/4,Math.round(feet[1]*4)/4,feet[2]],vertices=[],indices=[];
    const hit=async(o,d,max)=>{const p=await ray(o,d,max);if(!p||!p.every(Number.isFinite))return null;const t=p.reduce((s,v,i)=>s+(v-o[i])*d[i],0);return t>=-.001&&t<=max+.001&&Math.hypot(...p.map((v,i)=>v-o[i]))<=max+.002?p:null;};
    const grid=await Promise.all(Array.from({length:7},(_,i)=>Promise.all(Array.from({length:7},async(_,j)=>{
      const x=center[0]+(i-3)*.25,y=center[1]+(j-3)*.25,key=`${x}/${y}/${Math.floor(feet[2]*5)}`,old=cache.get(key),now=Date.now();
      if(old&&now-old.t<2000)return old.p;
      const p=await hit([x,y,feet[2]+.21],[0,0,-1],3);cache.set(key,{p,t:now});return p;
    }))));
    const tri=(a,b,c)=>{const k=vertices.length;vertices.push(a,b,c);indices.push(k,k+1,k+2);};
    for(let i=0;i<6;i++)for(let j=0;j<6;j++){const a=grid[i][j],b=grid[i+1][j],c=grid[i+1][j+1],d=grid[i][j+1];if(a&&b&&c&&d){tri(a,b,c);tri(a,c,d);}}
    const floorCount=indices.length;
    await Promise.all(Array.from({length:8},async(_,i)=>{
      const angle=i*Math.PI/4,d=[Math.cos(angle),Math.sin(angle),0],side=[-d[1]*.24,d[0]*.24,0];
      for(const h of [.35,1.6]){
        const p=await hit([center[0],center[1],feet[2]+h],d,1.1);if(!p)continue;
        const a=[p[0]+side[0],p[1]+side[1],feet[2]-.05],b=[p[0]-side[0],p[1]-side[1],feet[2]-.05],c=[b[0],b[1],feet[2]+1.85],e=[a[0],a[1],feet[2]+1.85];tri(a,b,c);tri(a,c,e);
      }
    }));
    const ceiling=await hit([center[0],center[1],feet[2]+1.79],[0,0,1],.8);
    if(ceiling){const[x,y,z]=ceiling;tri([x-.4,y-.4,z],[x+.4,y+.4,z],[x+.4,y-.4,z]);tri([x-.4,y-.4,z],[x-.4,y+.4,z],[x+.4,y+.4,z]);}
    while(cache.size>400)cache.delete(cache.keys().next().value);
    return{schema:1,vertices,indices,center,supported:!!grid[3][3]&&floorCount>0,radius:.45};
  }
  return{sample};
});
