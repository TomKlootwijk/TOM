#include "nhdf_ccd_v05.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace nhdf::ccd::v05;
int main(){
    RigidMotionBound a{{1,0,0},2,3}, b{{-1,0,0},1,4};
    assert(std::abs(relative_speed_bound(a,b)-12.0)<1e-12);
    assert(std::abs(rotational_margin(1,2,.25)-.5)<1e-12);
    auto events=group_events({{"b",.1,.2},{"a",.2000000005,.25},{"c",.4,.41}},1e-9);
    assert(events.size()==2 && events[0].contacts.size()==2);
    Body ba{"a",1,{1,0,0}}, bb{"b",1,{-1,0,0}};
    auto r=frictionless_impulse(ba,bb,{-1,0,0},1.0);
    assert(r.applied && std::abs(r.a.velocity.x+1)<1e-12 && std::abs(r.b.velocity.x-1)<1e-12);
    std::cout << "C++17 v0.5 smoke PASS\n";
}
