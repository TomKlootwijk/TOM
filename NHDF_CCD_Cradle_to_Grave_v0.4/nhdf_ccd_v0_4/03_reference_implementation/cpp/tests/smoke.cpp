#include "nhdf_ccd/ccd.hpp"

#include <cmath>
#include <cstdlib>
#include <iostream>

int main() {
    using namespace nhdf::ccd;
    const Sphere a{1.0};
    const Sphere b{1.0};
    const LinearMotion ma{{0.0, 0.0, 0.0}, {0.0, 0.0, 0.0}};
    const LinearMotion mb{{-10.0, 0.0, 0.0}, {20.0, 0.0, 0.0}};
    const Certificate c = sphere_sphere_linear(a, ma, b, mb);
    if (c.status != Status::hit || std::abs(c.toi_lower - 0.4) > 1e-12) {
        std::cerr << "unexpected certificate: " << c.reason << " toi=" << c.toi_lower << '\n';
        return EXIT_FAILURE;
    }
    std::cout << "NHDF-CCD C++ smoke test passed; toi=" << c.toi_lower << '\n';
    return EXIT_SUCCESS;
}
