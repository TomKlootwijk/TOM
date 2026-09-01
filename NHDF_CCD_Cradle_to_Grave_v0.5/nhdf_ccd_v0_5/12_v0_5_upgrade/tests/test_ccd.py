import math
import random
import unittest
from nhdf_ccd_v05.ccd import edge_edge_ccd, sphere_sphere_ccd, vertex_face_ccd
from nhdf_ccd_v05.model import LinearPoint, Status, Vec3


def lp(a, b=None):
    if b is None:
        b = a
    return LinearPoint(Vec3(*a), Vec3(*b))


class CCDTests(unittest.TestCase):
    def test_vertex_face_tunnelling(self):
        cert = vertex_face_ccd(
            lp((0.2,0.2,1),(0.2,0.2,-1)),
            lp((0,0,0)), lp((1,0,0)), lp((0,1,0)),
            geom_tol=1e-10,
        )
        self.assertEqual(cert.status, Status.HIT)
        self.assertAlmostEqual(cert.toi_upper, 0.5, delta=1e-8)
        self.assertIsNotNone(cert.witness)

    def test_vertex_face_outside_miss(self):
        cert = vertex_face_ccd(
            lp((2,2,1),(2,2,-1)),
            lp((0,0,0)), lp((1,0,0)), lp((0,1,0)),
        )
        self.assertEqual(cert.status, Status.MISS)

    def test_vertex_face_initial_overlap(self):
        cert = vertex_face_ccd(lp((0.2,0.2,0)), lp((0,0,0)), lp((1,0,0)), lp((0,1,0)))
        self.assertEqual(cert.status, Status.INITIAL_OVERLAP)

    def test_edge_edge_tunnelling(self):
        cert = edge_edge_ccd(
            lp((-1,0,0)), lp((1,0,0)),
            lp((0,-1,1),(0,-1,-1)), lp((0,1,1),(0,1,-1)),
            geom_tol=1e-10,
        )
        self.assertEqual(cert.status, Status.HIT)
        self.assertAlmostEqual(cert.toi_upper, 0.5, delta=1e-8)

    def test_edge_edge_miss(self):
        cert = edge_edge_ccd(
            lp((-1,0,0)), lp((1,0,0)),
            lp((2,-1,1),(2,-1,-1)), lp((2,1,1),(2,1,-1)),
        )
        self.assertEqual(cert.status, Status.MISS)

    def test_persistent_coplanar_fallback_hit(self):
        cert = edge_edge_ccd(
            lp((-1,0,0)), lp((1,0,0)),
            lp((0,-1,0)), lp((0,1,0)),
            geom_tol=1e-12, time_tol=1e-6,
        )
        self.assertEqual(cert.status, Status.INITIAL_OVERLAP)

    def test_sphere_sphere(self):
        cert = sphere_sphere_ccd(lp((-2,0,0),(2,0,0)), 0.5, lp((0,0,0)), 0.5)
        self.assertEqual(cert.status, Status.HIT)
        self.assertAlmostEqual(cert.toi_upper, 0.25, places=12)

    def test_constructed_vertex_face_crossings(self):
        rng = random.Random(19071990)
        for i in range(100):
            x = rng.uniform(0.05, 0.8)
            y = rng.uniform(0.05, 0.8-x if x < 0.75 else 0.1)
            y = min(y, 0.9-x)
            t_expected = rng.uniform(0.05, 0.95)
            z0 = rng.uniform(0.5, 2.0)
            z1 = -z0 * (1-t_expected) / t_expected
            cert = vertex_face_ccd(lp((x,y,z0),(x,y,z1)), lp((0,0,0)), lp((1,0,0)), lp((0,1,0)), geom_tol=1e-8)
            self.assertIn(cert.status, {Status.HIT, Status.INITIAL_OVERLAP}, msg=(i, cert.to_dict(False)))
            self.assertAlmostEqual(cert.toi_upper, t_expected, delta=2e-7)

    def test_constructed_edge_edge_crossings(self):
        rng = random.Random(10071990)
        for i in range(100):
            t_expected = rng.uniform(0.05, 0.95)
            z0 = rng.uniform(0.5, 2.0)
            z1 = -z0 * (1-t_expected) / t_expected
            cert = edge_edge_ccd(
                lp((-1,0,0)), lp((1,0,0)),
                lp((0,-1,z0),(0,-1,z1)), lp((0,1,z0),(0,1,z1)),
                geom_tol=1e-8,
            )
            self.assertIn(cert.status, {Status.HIT, Status.INITIAL_OVERLAP}, msg=(i, cert.to_dict(False)))
            self.assertAlmostEqual(cert.toi_upper, t_expected, delta=2e-7)


if __name__ == "__main__":
    unittest.main()
