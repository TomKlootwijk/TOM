import json
import unittest
from nhdf_ccd_v05.model import Certificate, Status


class CertificateTests(unittest.TestCase):
    def test_digest_determinism(self):
        a = Certificate(Status.MISS, "vf", pair_id="x", method="m", termination_reason="r")
        b = Certificate(Status.MISS, "vf", pair_id="x", method="m", termination_reason="r")
        self.assertEqual(a.digest(), b.digest())

    def test_invalid_interval(self):
        c = Certificate(Status.HIT, "vf", toi_lower=.6, toi_upper=.5, method="m", termination_reason="r")
        with self.assertRaises(ValueError):
            c.validate()

    def test_json_roundtrip_shape(self):
        c = Certificate(Status.MISS, "vf", method="m", termination_reason="r")
        p = json.loads(c.canonical_json())
        self.assertEqual(p["status"], "MISS")
        self.assertEqual(p["query_type"], "vf")


if __name__ == "__main__":
    unittest.main()
