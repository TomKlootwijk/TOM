#include "nhdf_ccd_v05.hpp"

namespace nhdf::ccd::v05 {

double relative_speed_bound(const RigidMotionBound& a,const RigidMotionBound& b){
    if(a.angular_speed<0||b.angular_speed<0||a.support_radius<0||b.support_radius<0) throw std::invalid_argument("invalid rigid bound");
    return norm(a.linear_velocity-b.linear_velocity)+a.angular_speed*a.support_radius+b.angular_speed*b.support_radius;
}

double rotational_margin(double angular_speed,double support_radius,double dt){
    if(angular_speed<0||support_radius<0||dt<0) throw std::invalid_argument("negative bound input");
    return std::min(2.0*support_radius,support_radius*angular_speed*dt);
}

std::vector<Event> group_events(std::vector<IntervalContact> contacts,double tolerance){
    if(tolerance<0) throw std::invalid_argument("negative tolerance");
    std::sort(contacts.begin(),contacts.end(),[](const auto& a,const auto& b){
        return std::tie(a.lo,a.hi,a.pair_id)<std::tie(b.lo,b.hi,b.pair_id);
    });
    std::vector<Event> events;
    for(const auto& c:contacts){
        if(events.empty()||c.lo>events.back().hi+tolerance){
            events.push_back(Event{events.size(),c.lo,c.hi,{c}});
        }else{
            auto& e=events.back();
            e.lo=std::min(e.lo,c.lo); e.hi=std::max(e.hi,c.hi); e.contacts.push_back(c);
        }
    }
    return events;
}

ImpulseResult frictionless_impulse(Body a,Body b,Vec3 normal_b_to_a,double restitution){
    if(restitution<0||restitution>1) throw std::invalid_argument("invalid restitution");
    const Vec3 n=normalized(normal_b_to_a);
    const double inv_a=a.mass==0?0:1.0/a.mass;
    const double inv_b=b.mass==0?0:1.0/b.mass;
    const double vn=dot(a.velocity-b.velocity,n);
    const double denom=inv_a+inv_b;
    if(norm(n)==0||vn>=0||denom<=0) return {a,b,0,false};
    const double j=-(1.0+restitution)*vn/denom;
    a.velocity=a.velocity+n*(j*inv_a);
    b.velocity=b.velocity-n*(j*inv_b);
    return {a,b,j,true};
}

} // namespace nhdf::ccd::v05
