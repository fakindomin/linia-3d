/* ===== STANDARD: modele z profilu linii (dynia, bałwan). Profil, pasma żeber i porty pochodzą z line.json (Python = źródło prawdy) ===== */
function lineTab(id){
  const t=LINE.models[id].R,n=t.length,zs=new Float64Array(n),rs=new Float64Array(n);
  for(let i=0;i<n;i++){zs[i]=t[i][0];rs[i]=t[i][1];}
  return z=>{
    if(z<=zs[0])return rs[0];if(z>=zs[n-1])return rs[n-1];
    let lo=0,hi=n-1;while(hi-lo>1){const m=(lo+hi)>>1;if(zs[m]<=z)lo=m;else hi=m;}
    const d=zs[hi]-zs[lo];return d<1e-9?rs[hi]:rs[lo]+(rs[hi]-rs[lo])*(z-zs[lo])/d;
  };
}
/* bryła obrotowa z pasmami żeber: F = R + amp*fade(R)*sum(w_i*rib_i(N_i th)) - rho, ograniczona płaszczyznami zlo / zhi (i opcjonalnie o.top(rho)) */
function latheBands(G,o){
  const{nx,ny,nz,v,F}=G,nc=nx*ny,bs=o.bands,fd=o.fade,{rho}=colInfo(G,0,1),ribs=bs.map(b=>colInfo(G,b.N,o.pow).rib),W=new Float64Array(bs.length);
  for(let k=0;k<nz;k++){
    const z=G.z0+k*v;if(z<o.zlo-2*v||z>o.zhi+2*v)continue;
    const R=o.R(z),pl=Math.min(z-o.zlo,o.zhi-z),a=o.amp*clamp((R-fd[0])/(fd[1]-fd[0]),0,1),off=k*nc,b=R-1e-3;
    let any=false;
    for(let i=0;i<bs.length;i++){const q=bs[i];let w=1;if(q.up)w*=sstep(z,q.up[0],q.up[1]);if(q.down)w*=1-sstep(z,q.down[0],q.down[1]);W[i]=a*w;if(W[i]!==0)any=true;}
    for(let c=0;c<nc;c++){
      let m=0;if(any)for(let i=0;i<bs.length;i++)if(W[i]!==0)m+=W[i]*ribs[i][c];
      let val=b+m-rho[c];if(val>pl)val=pl;
      if(o.top){const t=o.top(rho[c])-z;if(t<val)val=t;}
      F[off+c]=val;
    }
  }
}
/* szerokość domyślna = średnica po grzbietach żeber (2 * promień profilu + głębokość rowków z linii) */
function lineW0(id){let m=0;for(const p of LINE.models[id].R)if(p[1]>m)m=p[1];return 2*m+2*LINE.models[id].ribs.amp;}
/* skala: albo jedna (P.scale, bałwan), albo osobno szerokość (sw, z P.width) i wysokość (sh, z P.height) (dynia); N żeber rośnie z szerokością, rozstaw zostaje */
function lineSpec(id,P){
  const L=LINE.models[id],R0=lineTab(id);
  let rmax0=0;for(const p of L.R)if(p[1]>rmax0)rmax0=p[1];
  const sw=P.width!=null?(P.width-P.ribDepth)/(2*rmax0):P.scale,sh=P.height!=null?P.height/L.H:P.scale,sc=a=>a&&a.map(x=>x*sh);
  const ports={};
  for(const k in L.ports){const f=L.ports[k].frame;ports[k]={O:[f.O[0]*sw,f.O[1]*sw,f.O[2]*sh],A:f.A,B:f.B,C:f.C};}
  const S={L,s:sw,sw,sh,H:L.H*sh,rmax:rmax0*sw,R:z=>sw*R0(z/sh),ports,
    bands:L.ribs.bands.map(b=>({N:Math.max(1,Math.round(b.N*sw)),up:sc(b.up),down:sc(b.down)})),fade:L.ribs.fade,top:null};
  if(L.top){const T=L.top,rs=T.R_SH*sw;S.top=rho=>{const q=Math.min(rho/rs,1);return sh*T.H_TOP-sh*T.DIP*Math.pow(1-q*q,1.5);};}
  /* przybliżona odległość do koperty korpusu (do przycinania dodatków): promień + ENV_PAD / normalna, a nad dnem zagłębienia wysokość */
  S.sdf=(x,y,z)=>{const R=S.R(z),dR=(S.R(z+0.3)-S.R(z-0.3))/0.6;let d=(R+LINE.const.ENV_PAD*0.6-Math.sqrt(x*x+y*y))/Math.sqrt(1+dR*dR);
    if(S.top)d=Math.min(d,S.top(Math.sqrt(x*x+y*y))+LINE.const.PAD_MIN-z);return d;};
  return S;
}
function lineGrid(id,P,vox){
  const S=lineSpec(id,P),h=S.rmax+P.ribDepth/2+3,G=mkGrid(-h,h,-h,h,-1,S.H+1.5,vox);
  latheBands(G,{R:S.R,bands:S.bands,amp:P.ribDepth/2,pow:P.ribPow,fade:S.fade,zlo:0,zhi:S.H,top:S.top});
  for(const k in S.ports)localField(G,S.ports[k],socketF,[-5,5],[-9,2],[-1,6],'cut');
  return{G,S};
}
/* dodatek lokalny (ogonek, nos): siatka w ramce portu; ex = wersja do druku (płaska strona c=0 na stole), g = w modelu */
function linePart(name,S,port,fn,ar,br,cr,vox,ex,flip){
  const fr=S.ports[port],v=clamp(vox*0.6,0.22,0.45),G=mkGrid(ar[0],ar[1],br[0],br[1],cr[0],cr[1],v);
  localField(G,IDM,fn,ar,br,cr,'max');
  const m=surfaceNets(G),exm={p:m.p.slice(),i:m.i.slice()};
  if(flip)xf(exm,(a,b,c)=>[a,c,-b]);toPage(exm);                     /* ogonek: do druku końcem na stole (jak w skrypcie) */
  const g=frameXf(fr,{p:m.p,i:m.i});toPage(g);
  if(ex){const B=fr.B,k=ex*0.5;translate(g,B[0]*k,B[2]*k,-B[1]*k);}
  return{name,m:g,ex:exm,g:name};
}
function buildLine(id,P,vox,ex,parts,warn){
  const{G,S}=lineGrid(id,P,vox);
  parts.push({name:'korpus',m:meshFromGrid(G),g:'korpus'});
  if(id==='dynia'){
    const T=LINE.models.dynia.stem;
    const fn=(a,b,c)=>{
      const t=clamp(b/T.H,0,1),xc=T.bend*t*t,r=T.RT+(T.R0-T.RT)*Math.pow(1-t,3),y=2.5-c,dx=a-xc,rho=Math.hypot(dx,y);
      const q=Math.cos(T.N*Math.atan2(y,dx));
      let f=Math.min(r+T.amp*sgnPow(q,0.8)-1e-3-rho,T.H-b,b+3.0);
      const fr=S.ports.stem,X=fr.O[0]+a*fr.A[0]+b*fr.B[0]+c*fr.C[0],Y=fr.O[1]+a*fr.A[1]+b*fr.B[1]+c*fr.C[1],Z=fr.O[2]+a*fr.A[2]+b*fr.B[2]+c*fr.C[2];
      f=Math.min(f,-(S.sdf(X,Y,Z)+GAP));
      return Math.max(f,rboxF(a,b,c,[-PEG_W/2,-PEG_L,0],[PEG_W/2,1,PEG_W],PEG_R));
    };
    const p=linePart('ogonek',S,'stem',fn,[-12,12],[-9,T.H+1],[-9,14],vox,ex,true);parts.push(p);
  }else{
    const n=LINE.models.balwan.nose;
    const fn=(a,b,c)=>{
      const r=n.RT+(n.R0-n.RT)*clamp(1-b/n.L,0,1),cc=0.7*r;
      let f=Math.min(r-Math.hypot(a,c-cc),n.L-b,c,b+3.0);
      const fr=S.ports.nose,X=fr.O[0]+a*fr.A[0]+b*fr.B[0]+c*fr.C[0],Y=fr.O[1]+a*fr.A[1]+b*fr.B[1]+c*fr.C[1],Z=fr.O[2]+a*fr.A[2]+b*fr.B[2]+c*fr.C[2];
      f=Math.min(f,-(S.sdf(X,Y,Z)+GAP));
      return Math.max(f,rboxF(a,b,c,[-PEG_W/2,-PEG_L,0],[PEG_W/2,1,PEG_W],PEG_R));
    };
    parts.push(linePart('nos',S,'nose',fn,[-6,6],[-9,n.L+1],[-1,10],vox,ex,false));
  }
  return{parts,warn};
}
