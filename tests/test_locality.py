import unittest

from cant.semantic import RM13, gray, hamming, make_root, split_root
from tests.helpers import LEX
from tools.locality_report import stats


class SemanticLocality(unittest.TestCase):
    def test_related_closer_than_unrelated(self):
        s = stats(LEX)
        self.assertLess(s["related"][1], s["unrelated"][1])
        self.assertLessEqual(s["related"][2], 2)     # some related pairs are 1-2 bits apart

    def test_domain_code_distance(self):
        for i, a in enumerate(RM13):
            for b in RM13[i + 1:]:
                self.assertGreaterEqual(hamming(a, b), 4)

    def test_gray_siblings(self):
        for k in range(100):
            self.assertEqual(hamming(gray(k), gray(k + 1)), 1)

    def test_root_split(self):
        r = make_root(3, 5, 77)
        self.assertEqual(split_root(r), (3, 5, 77))

    def test_lexicon_roots_consistent(self):
        for e in LEX:
            self.assertEqual(make_root(e.domain, e.cluster, e.concept), e.root)

    def test_reserved_roots(self):
        self.assertEqual(LEX.by_key["null"].root, 0)
        self.assertEqual(LEX.by_key["everything"].root, (1 << 30) - 1)


if __name__ == "__main__":
    unittest.main()
