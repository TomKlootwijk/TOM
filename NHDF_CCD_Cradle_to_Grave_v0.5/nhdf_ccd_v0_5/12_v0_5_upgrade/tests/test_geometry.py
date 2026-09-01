import math
import unittest
from nhdf_ccd_v05.geometry import point_triangle_distance2, segment_segment_distance2
from nhdf_ccd_v05.model import Vec3


class GeometryTests(unittest.TestCase):
    def test_point_inside_triangle(self):
        r = point_triangle_distance2(Vec3(0.25, 0.25, 1.0), Vec3(0,0,0), Vec3(1,0,0), Vec3(0,1,0))
        self.assertAlmostEqual(r.distance2, 1.0, places=12)
        self.assertAlmostEqual(sum(r.barycentric), 1.0, places=12)

    def test_point_triangle_degenerate(self):
        r = point_triangle_distance2(Vec3(0.5, 1, 0), Vec3(0,0,0), Vec3(1,0,0), Vec3(2,0,0))
        self.assertTrue(r.degenerate)
        self.assertAlmostEqual(r.distance2, 1.0, places=12)

    def test_segment_crossing(self):
        r = segment_segment_distance2(Vec3(-1,0,0), Vec3(1,0,0), Vec3(0,-1,0), Vec3(0,1,0))
        self.assertLessEqual(r.distance2, 1e-24)
        self.assertAlmostEqual(r.s, 0.5, places=12)
        self.assertAlmostEqual(r.t, 0.5, places=12)

    def test_parallel_segments(self):
        r = segment_segment_distance2(Vec3(0,0,0), Vec3(1,0,0), Vec3(0,1,0), Vec3(1,1,0))
        self.assertAlmostEqual(r.distance2, 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
