#pragma once

#include <array>
#include <cstdint>
#include <string>

namespace nhdf::ccd {

struct Vec3 {
    double x{};
    double y{};
    double z{};
};

struct Sphere {
    double radius{};
};

struct LinearMotion {
    Vec3 origin{};
    Vec3 velocity{};
};

enum class Status : std::uint8_t {
    hit,
    no_hit,
    initial_overlap,
    invalid_input,
};

struct Certificate {
    Status status{Status::invalid_input};
    double toi_lower{};
    double toi_upper{};
    Vec3 normal{1.0, 0.0, 0.0};
    std::string reason{};
};

[[nodiscard]] Certificate sphere_sphere_linear(
    const Sphere& a,
    const LinearMotion& motion_a,
    const Sphere& b,
    const LinearMotion& motion_b,
    double distance_tolerance = 1e-8,
    double time_tolerance = 1e-10);

} // namespace nhdf::ccd
