#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace nhdf::ccd::v05 {

struct Vec3 {
    double x{}, y{}, z{};
};
inline Vec3 operator+(Vec3 a, Vec3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
inline Vec3 operator-(Vec3 a, Vec3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
inline Vec3 operator*(Vec3 a,double s){return {a.x*s,a.y*s,a.z*s};}
inline double dot(Vec3 a,Vec3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline double norm(Vec3 a){return std::sqrt(std::max(0.0,dot(a,a)));}
inline Vec3 normalized(Vec3 a){double n=norm(a); return n>0? a*(1.0/n):Vec3{};}

struct RigidMotionBound {
    Vec3 linear_velocity{};
    double angular_speed{};
    double support_radius{};
};

double relative_speed_bound(const RigidMotionBound& a,const RigidMotionBound& b);
double rotational_margin(double angular_speed,double support_radius,double dt);

struct IntervalContact {
    std::string pair_id;
    double lo{};
    double hi{};
};
struct Event {
    std::size_t id{};
    double lo{};
    double hi{};
    std::vector<IntervalContact> contacts;
};
std::vector<Event> group_events(std::vector<IntervalContact> contacts,double tolerance);

struct Body {
    std::string id;
    double mass{};
    Vec3 velocity{};
};
struct ImpulseResult {
    Body a,b;
    double magnitude{};
    bool applied{};
};
ImpulseResult frictionless_impulse(Body a,Body b,Vec3 normal_b_to_a,double restitution);

} // namespace nhdf::ccd::v05
