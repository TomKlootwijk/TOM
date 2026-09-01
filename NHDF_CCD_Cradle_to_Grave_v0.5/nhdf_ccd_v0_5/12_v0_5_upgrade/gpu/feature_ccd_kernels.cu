// NHDF-CCD v0.5 CUDA translation skeleton.
// Not compiled or validated in this release. Semantics must be matched against
// CPU certificates before any GPU conformance claim.
#include <cuda_runtime.h>
#include <stdint.h>

struct Vec3d { double x,y,z; };
struct LinearPointGPU { Vec3d p0,p1; };
struct CandidateGPU {
    uint32_t query_type; // 1 = vertex-face, 2 = edge-edge
    uint32_t index;
    LinearPointGPU p[4];
};
struct ResultGPU {
    uint32_t status;
    double toi_lo, toi_hi;
    uint32_t root_count;
    uint32_t flags; // degeneracy, budget, nonfinite, etc.
};

__device__ inline Vec3d sub(Vec3d a,Vec3d b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
__device__ inline double dot(Vec3d a,Vec3d b){return a.x*b.x+a.y*b.y+a.z*b.z;}
__device__ inline Vec3d cross(Vec3d a,Vec3d b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}

__global__ void build_coplanarity_coefficients(const CandidateGPU* queries,double4* coeffs,size_t n){
    const size_t i=blockIdx.x*blockDim.x+threadIdx.x;
    if(i>=n) return;
    const CandidateGPU q=queries[i];
    const Vec3d r0=sub(q.p[0].p0,q.p[1].p0);
    const Vec3d r1=sub(sub(q.p[0].p1,q.p[0].p0),sub(q.p[1].p1,q.p[1].p0));
    const Vec3d u0=sub(q.p[2].p0,q.p[1].p0);
    const Vec3d u1=sub(sub(q.p[2].p1,q.p[2].p0),sub(q.p[1].p1,q.p[1].p0));
    const Vec3d v0=sub(q.p[3].p0,q.p[1].p0);
    const Vec3d v1=sub(sub(q.p[3].p1,q.p[3].p0),sub(q.p[1].p1,q.p[1].p0));
    const Vec3d c0=cross(u0,v0);
    const Vec3d c1={cross(u1,v0).x+cross(u0,v1).x,cross(u1,v0).y+cross(u0,v1).y,cross(u1,v0).z+cross(u0,v1).z};
    const Vec3d c2=cross(u1,v1);
    coeffs[i]=make_double4(dot(r0,c0),dot(r1,c0)+dot(r0,c1),dot(r1,c1)+dot(r0,c2),dot(r1,c2));
}

// Root isolation, containment, deterministic compaction, certificate emission,
// and CPU/GPU replay comparison are intentionally absent until implemented and tested.
