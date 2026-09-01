// TOMAGI 1.0 OpenCL C kernel. One transition per work-item.
typedef struct { uint4 q; uint4 v; uint4 topo; uint4 outv; } State64;
typedef struct { uint4 head; uint4 args; uint4 tail; } Cell48;

#define RHO_N (1u<<20)
#define THETA_N (1u<<18)
#define TIME_N (1u<<14)
#define PHI_N (1u<<12)
#define STATUS_HALT 1u
#define STATUS_ZERO 2u
#define STATUS_WRAP 4u
#define STATUS_EMIT 8u
#define STATUS_CONE 16u
#define STATUS_SPHERE 32u
#define STATUS_REKEY_MISS 64u
#define STATUS_PHI_WRAP 128u
#define FLAG_REKEY (1u<<31)

static uint mix32(uint x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;x^=x>>16;return x;}
static uint rotl32(uint x,uint r){r&=31u;return(x<<r)|(x>>((32u-r)&31u));}
static int normi(int x,int n){int r=x%n;return r<0?r+n:r;}
static int floordiv(int x,int n){int q=x/n;int r=x%n;return r<0?q-1:q;}
static int cycdelta(int x,int c,int n){int d=normi(x-c,n);return d>=n/2?d-n:d;}
static int imax(int a,int b){return a>b?a:b;}
static uint2 pack_key(State64 s){uint r=(uint)normi(as_int(s.q.x),(int)RHO_N),t=(uint)normi(as_int(s.q.y),(int)THETA_N),x=(uint)normi(as_int(s.q.z),(int)TIME_N),p=(uint)normi(as_int(s.q.w),(int)PHI_N);return(uint2)((r<<12)|(t>>6),((t&63u)<<26)|(x<<12)|p);}
static State64 normalize_state(State64 s){s.q.y=as_uint(normi(as_int(s.q.y),(int)THETA_N));s.q.z=as_uint(normi(as_int(s.q.z),(int)TIME_N));s.q.w=as_uint(normi(as_int(s.q.w),(int)PHI_N));s.topo.x&=1u;s.topo.z&=1u;return s;}
static State64 set_field(State64 s,uint i,int v,int add){uint u=as_uint(v);if(i==0)s.q.x=add?s.q.x+u:u;else if(i==1)s.q.y=add?s.q.y+u:u;else if(i==2)s.q.z=add?s.q.z+u:u;else if(i==3)s.q.w=add?s.q.w+u:u;else if(i==4)s.v.x=add?s.v.x+u:u;else if(i==5)s.v.y=add?s.v.y+u:u;else if(i==6)s.v.z=add?s.v.z+u:u;else if(i==7)s.v.w=add?s.v.w+u:u;else if(i==8)s.topo.x=add?s.topo.x+u:u;else if(i==9)s.topo.y=add?s.topo.y+u:u;else if(i==10)s.topo.z=add?s.topo.z+u:u;else if(i==11)s.topo.w=add?s.topo.w+u:u;else if(i==12)s.outv.x=add?s.outv.x+u:u;else if(i==13)s.outv.y=add?s.outv.y+u:u;else if(i==14)s.outv.z=add?s.outv.z+u:u;else if(i==15)s.outv.w=add?s.outv.w+u:u;return s;}
static int cmp_key(uint ah,uint al,uint bh,uint bl){if(ah<bh)return-1;if(ah>bh)return 1;if(al<bl)return-1;if(al>bl)return 1;return 0;}
static uint find_key(__global const Cell48* cells,uint n,uint hi,uint lo,int* ok){uint l=0,r=n;while(l<r){uint m=l+(r-l)/2;Cell48 c=cells[m];if(cmp_key(c.head.x,c.head.y,hi,lo)<0)l=m+1;else r=m;}*ok=(l<n&&cmp_key(cells[l].head.x,cells[l].head.y,hi,lo)==0);return l;}

__kernel void tomagi_step(__global State64* states,__global const Cell48* cells,uint state_count,uint cell_count,uint seed){
 uint gid=get_global_id(0);if(gid>=state_count)return;State64 s=states[gid];if((s.outv.w&STATUS_HALT)||s.topo.w>=cell_count)return;uint ci=s.topo.w;Cell48 c=cells[ci];uint2 k=pack_key(s);uint op=c.head.z,fl=c.head.w;int4 a=as_int4(c.args);
 if(op==1)s=set_field(s,fl&15u,a.x,0);else if(op==2){uint h=mix32(seed^k.x^rotl32(k.y,13)^s.q.z^c.tail.w);s.topo.z=popcount(h)&1u;s=set_field(s,fl&15u,s.topo.z?a.x:-a.x,1);}else if(op==3){s.v+=c.args;s.q+=s.v;}
 else if(op==4){int raw=as_int(s.q.w)+a.x,w=floordiv(raw,(int)PHI_N);s.q.w=as_uint(raw-w*(int)PHI_N);if((w&1)&&(fl&(1u<<4)))s.topo.x^=1u;if(w)s.outv.w|=STATUS_PHI_WRAP;else s.outv.w&=~STATUS_PHI_WRAP;s.topo.z=(fl&(1u<<5))?((s.q.w>>11)&1u):((uint)w&1u);}
 else if(op==5){int raw=as_int(s.q.z)+a.x,w=floordiv(raw,(int)TIME_N);s.q.z=as_uint(raw-w*(int)TIME_N);s.topo.z=(uint)w&1u;if(w)s.outv.x=mix32(s.outv.x^(uint)w^c.tail.w);}else if(op==6){s.outv.z=0;s.outv.w|=STATUS_ZERO;s.topo.z=1;}
 else if(op==7){int rho=normi(as_int(s.q.x),(int)RHO_N),th=normi(as_int(s.q.y),(int)THETA_N),res=imax(imax(a.x-rho,rho-a.y),abs(cycdelta(th,normi(a.z,(int)THETA_N),(int)THETA_N))-abs(a.w));s.outv.z=as_uint(res);s.topo.z=res<=0;if(s.topo.z)s.outv.w|=STATUS_CONE;else s.outv.w&=~STATUS_CONE;}
 else if(op==8){int rho=normi(as_int(s.q.x),(int)RHO_N),ph=normi(as_int(s.q.w),(int)PHI_N),res=abs(rho-a.x)-abs(a.y);if(a.w>=0)res=imax(res,abs(cycdelta(ph,normi(a.z,(int)PHI_N),(int)PHI_N))-abs(a.w));s.outv.z=as_uint(res);s.topo.z=res<=0;if(s.topo.z)s.outv.w|=STATUS_SPHERE;else s.outv.w&=~STATUS_SPHERE;}
 else if(op==9){int rho=as_int(s.q.x),w=floordiv(rho,(int)RHO_N);s.q.x=as_uint(rho-w*(int)RHO_N);uint odd=(uint)w&1u;if(odd){s.q.y=(fl&1u)?s.q.y+THETA_N/2:as_uint((int)(THETA_N/2)-as_int(s.q.y));s.q.w=as_uint(-as_int(s.q.w));s.topo.x^=1u;if(fl&2u)s.topo.y^=1u;s.outv.w|=STATUS_WRAP;}else s.outv.w&=~STATUS_WRAP;s.topo.z=odd;s=normalize_state(s);}
 else if(op==10){uint bi=(uint)a.x;s.topo.z=bi<32?((k.y>>bi)&1u):((k.x>>(bi-32))&1u);}else if(op==11&&s.topo.z){s.q+=c.args;if(fl&1u)s.topo.x^=1u;if(fl&2u)s.topo.y^=1u;s=normalize_state(s);}else if(op==12){int sh=clamp(a.y,0,30),d=1<<sh,chir=(s.topo.x&1)?-1:1,sgn=(s.topo.z&1)?1:-1;s.q.w=as_uint(normi(as_int(s.q.w)+chir*sgn*a.x,(int)PHI_N));s.v=as_uint4(as_int4(s.v)/d);}else if(op==13)s.outv.y=c.tail.z;else if(op==14){s.outv.y=c.tail.z;s.outv.w|=STATUS_EMIT;if(fl&1u)s.outv.w|=STATUS_HALT;}else if(op==15)s.outv.w|=STATUS_HALT;
 s=normalize_state(s);s.outv.x=mix32(s.outv.x^c.tail.z^c.tail.w^k.x^rotl32(k.y,7)^s.topo.z^ci);if(!(s.outv.w&STATUS_HALT)){if(fl&FLAG_REKEY){uint2 nk=pack_key(s);int ok;uint idx=find_key(cells,cell_count,nk.x,nk.y,&ok);if(ok){s.outv.w&=~STATUS_REKEY_MISS;s.topo.w=idx;}else{s.outv.w|=STATUS_REKEY_MISS;s.topo.w=s.topo.z?c.tail.y:c.tail.x;}}else s.topo.w=s.topo.z?c.tail.y:c.tail.x;}states[gid]=s;
}
