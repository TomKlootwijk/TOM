#include "nhdf_ccd/ccd.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>

namespace nhdf::ccd {
namespace {

Vec3 add(const Vec3& a, const Vec3& b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
Vec3 sub(const Vec3& a, const Vec3& b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
Vec3 mul(const Vec3& a, double s) { return {a.x * s, a.y * s, a.z * s}; }
double dot(const Vec3& a, const Vec3& b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
double norm(const Vec3& a) { return std::sqrt(dot(a, a)); }
Vec3 normalized(const Vec3& a) {
    const double n = norm(a);
    return n > 1e-15 ? mul(a, 1.0 / n) : Vec3{1.0, 0.0, 0.0};
}

} // namespace

Certificate sphere_sphere_linear(
    const Sphere& a,
    const LinearMotion& motion_a,
    const Sphere& b,
    const LinearMotion& motion_b,
    const double distance_tolerance,
    const double time_tolerance) {
    if (!(a.radius >= 0.0 && b.radius >= 0.0 && distance_tolerance > 0.0 && time_tolerance > 0.0)) {
        return {Status::invalid_input, 0.0, 0.0, {}, "invalid radius or tolerance"};
    }
    const Vec3 p = sub(motion_b.origin, motion_a.origin);
    const Vec3 v = sub(motion_b.velocity, motion_a.velocity);
    const double radius = a.radius + b.radius;
    const double separation0 = norm(p) - radius;
    if (separation0 < -distance_tolerance) {
        return {Status::initial_overlap, 0.0, 0.0, normalized(p), "negative initial separation"};
    }
    if (separation0 <= distance_tolerance) {
        return {Status::hit, 0.0, 0.0, normalized(p), "initial contact"};
    }
    const double qa = dot(v, v);
    const double qb = 2.0 * dot(p, v);
    const double qc = dot(p, p) - radius * radius;
    if (qa <= std::numeric_limits<double>::epsilon()) {
        return {Status::no_hit, 0.0, 0.0, normalized(p), "zero relative speed"};
    }
    const double disc = qb * qb - 4.0 * qa * qc;
    if (disc < 0.0) {
        return {Status::no_hit, 0.0, 0.0, normalized(p), "quadratic has no real roots"};
    }
    const double root_disc = std::sqrt(std::max(0.0, disc));
    const double q = -0.5 * (qb + std::copysign(root_disc, qb));
    std::vector<double> roots;
    if (std::abs(q) <= 1e-30) {
        roots.push_back(-qb / (2.0 * qa));
    } else {
        roots.push_back(q / qa);
        roots.push_back(qc / q);
    }
    std::sort(roots.begin(), roots.end());
    for (const double root : roots) {
        if (root >= -time_tolerance && root <= 1.0 + time_tolerance) {
            const double toi = std::clamp(root, 0.0, 1.0);
            const Vec3 delta = add(p, mul(v, toi));
            return {Status::hit, toi, toi, normalized(delta), "earliest quadratic root"};
        }
    }
    return {Status::no_hit, 0.0, 0.0, normalized(p), "roots outside the step"};
}

} // namespace nhdf::ccd
