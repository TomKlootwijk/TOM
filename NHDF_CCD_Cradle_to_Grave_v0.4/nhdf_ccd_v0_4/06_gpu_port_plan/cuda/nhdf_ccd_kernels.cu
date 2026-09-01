// NHDF-CCD v0.4 CUDA design skeleton
// Not compiled in the release environment. This file is intentionally limited
// to an exact linear sphere-sphere batch to avoid implying a complete GPU port.

#include <cuda_runtime.h>
#include <math.h>
#include <stdint.h>

struct SphereQuery {
    double3 p;       // relative center at t=0: B - A
    double3 v;       // relative linear velocity: vB - vA
    double radius;   // rA + rB
};

enum CcdStatus : uint8_t { HIT=0, NO_HIT=1, INITIAL_OVERLAP=2, INVALID_INPUT=3 };

struct SphereCertificate {
    CcdStatus status;
    double toi;
};

__device__ double dot3(double3 a, double3 b) {
    return a.x*b.x + a.y*b.y + a.z*b.z;
}

__global__ void sphere_sphere_linear_batch(
    const SphereQuery* queries,
    SphereCertificate* out,
    size_t count,
    double distance_tolerance,
    double time_tolerance) {
    const size_t i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= count) return;
    const SphereQuery q = queries[i];
    const double c = dot3(q.p, q.p) - q.radius*q.radius;
    if (c < -distance_tolerance) { out[i] = {INITIAL_OVERLAP, 0.0}; return; }
    if (c <= distance_tolerance) { out[i] = {HIT, 0.0}; return; }
    const double a = dot3(q.v, q.v);
    const double b = 2.0 * dot3(q.p, q.v);
    if (!(a > 0.0) || !isfinite(a) || !isfinite(b) || !isfinite(c)) {
        out[i] = {a == 0.0 ? NO_HIT : INVALID_INPUT, 0.0};
        return;
    }
    const double disc = b*b - 4.0*a*c;
    if (disc < 0.0) { out[i] = {NO_HIT, 0.0}; return; }
    const double s = sqrt(fmax(0.0, disc));
    const double t0 = (-b - s) / (2.0*a);
    const double t1 = (-b + s) / (2.0*a);
    double t = t0;
    if (t < -time_tolerance) t = t1;
    if (t >= -time_tolerance && t <= 1.0 + time_tolerance) {
        out[i] = {HIT, fmin(1.0, fmax(0.0, t))};
    } else {
        out[i] = {NO_HIT, 0.0};
    }
}
