#!/usr/bin/env python3
"""Report semantic bit-distance statistics over the seeded lexicon.

related   = two defined senses of the same root, or two roots in the same cluster
unrelated = two defined senses whose roots are in different domains
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cant.lexicon import Lexicon  # noqa: E402
from cant.semantic import hamming, tree_distance  # noqa: E402


def senses(lex):
    for e in lex:
        for cat, s in enumerate(e.senses):
            if s:
                yield e, cat, (e.root << 2) | cat


def stats(lex=None):
    lex = lex or Lexicon()
    buckets = {1: [], 2: [], 3: [], 4: []}
    for (ea, ca, a), (eb, cb, b) in itertools.combinations(list(senses(lex)), 2):
        buckets[tree_distance(a, b)].append(hamming(a, b))
    related = buckets[1] + buckets[2]
    unrelated = buckets[4]
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    return {
        "same_root": (len(buckets[1]), mean(buckets[1])),
        "same_cluster": (len(buckets[2]), mean(buckets[2])),
        "same_domain": (len(buckets[3]), mean(buckets[3])),
        "different_domain": (len(buckets[4]), mean(buckets[4])),
        "related": (len(related), mean(related), min(related), max(related)),
        "unrelated": (len(unrelated), mean(unrelated), min(unrelated), max(unrelated)),
    }


if __name__ == "__main__":
    s = stats()
    print("pairs of defined senses, Hamming distance on the 32-bit semantic half")
    for k in ("same_root", "same_cluster", "same_domain", "different_domain"):
        n, m = s[k]
        print(f"  {k:17s} n={n:5d}  mean={m:.2f}")
    for k in ("related", "unrelated"):
        n, m, lo, hi = s[k]
        print(f"  {k:17s} n={n:5d}  mean={m:.2f}  min={lo}  max={hi}")
