import tempfile
import unittest
from pathlib import Path
from nhdf_ccd_v05.corpus import load_sample_queries, corpus_statistics


NEGATIVE_BLOCK = """0,1,0,1,1,1,0
0,1,0,1,0,1,0
1,1,0,1,0,1,0
0,1,1,1,0,1,0
0,1,0,1,-1,1,0
0,1,0,1,0,1,0
1,1,0,1,0,1,0
0,1,1,1,0,1,0
"""


class CorpusTests(unittest.TestCase):
    def test_parse_vf_block(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.csv"
            p.write_text(NEGATIVE_BLOCK)
            q = load_sample_queries(p, "vertex-face")
            self.assertEqual(len(q), 1)
            self.assertFalse(q[0].label)
            self.assertEqual(corpus_statistics(q), {"queries":1,"positive":0,"negative":1})

    def test_reject_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.csv"
            p.write_text("0,1,0,1,0,1,0\n")
            with self.assertRaises(ValueError):
                load_sample_queries(p, "edge-edge")

    def test_reject_label_mismatch(self):
        text = NEGATIVE_BLOCK.replace(",0\n", ",1\n", 1)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "q.csv"
            p.write_text(text)
            with self.assertRaises(ValueError):
                load_sample_queries(p, "vertex-face")


if __name__ == "__main__":
    unittest.main()
