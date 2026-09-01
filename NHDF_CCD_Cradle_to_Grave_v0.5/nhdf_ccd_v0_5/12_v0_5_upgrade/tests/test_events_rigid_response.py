import unittest
from nhdf_ccd_v05.events import group_contact_events
from nhdf_ccd_v05.model import Certificate, Status, Vec3
from nhdf_ccd_v05.response import BodyState, advance_split_step, apply_frictionless_impulse
from nhdf_ccd_v05.rigid import RigidMotionBound, conservative_advance_step, relative_speed_bound, rotational_margin


class EventRigidResponseTests(unittest.TestCase):
    def cert(self, lo, hi, pair):
        return Certificate(Status.HIT, "test", pair_id=pair, toi_lower=lo, toi_upper=hi, method="fixture", termination_reason="fixture")

    def test_event_transitive_grouping(self):
        c = [self.cert(.1,.2,"b"), self.cert(.2000000005,.25,"a"), self.cert(.4,.41,"c")]
        groups = group_contact_events(c, merge_tolerance=1e-9)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0].pair_ids, ("a","b"))
        self.assertAlmostEqual(groups[0].toi_upper, .25)

    def test_grouping_deterministic(self):
        c = [self.cert(.2,.2,"z"), self.cert(.2,.2,"a")]
        self.assertEqual(group_contact_events(c)[0].pair_ids, ("a","z"))

    def test_rigid_relative_bound(self):
        a = RigidMotionBound(Vec3(1,0,0), 2.0, 3.0)
        b = RigidMotionBound(Vec3(-1,0,0), 1.0, 4.0)
        self.assertAlmostEqual(relative_speed_bound(a,b), 12.0)

    def test_rotational_margin(self):
        self.assertAlmostEqual(rotational_margin(1.0, 2.0, .25), .5)
        self.assertAlmostEqual(rotational_margin(100.0, 2.0, 1.0), 4.0)

    def test_advance_step(self):
        self.assertAlmostEqual(conservative_advance_step(1.0,2.0), .45)

    def test_frictionless_impulse_equal_masses(self):
        a = BodyState("a", 1.0, Vec3(-1,0,0), Vec3(1,0,0))
        b = BodyState("b", 1.0, Vec3(1,0,0), Vec3(-1,0,0))
        r = apply_frictionless_impulse(a,b,Vec3(-1,0,0), restitution=1.0)
        self.assertTrue(r.applied)
        self.assertAlmostEqual(r.body_a.velocity.x, -1.0)
        self.assertAlmostEqual(r.body_b.velocity.x, 1.0)

    def test_split_step(self):
        a = BodyState("a", 1.0, Vec3(-2,0,0), Vec3(2,0,0))
        b = BodyState("b", 1.0, Vec3(2,0,0), Vec3(-2,0,0))
        r = advance_split_step(a,b,.375,1.0,Vec3(-1,0,0),restitution=1.0)
        self.assertTrue(r.applied)
        self.assertLess(r.body_a.position.x, r.body_b.position.x)


if __name__ == "__main__":
    unittest.main()
