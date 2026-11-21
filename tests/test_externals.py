import math
import unittest

from cant import CantError, decode
from cant.externals import REGISTRY
from tests.helpers import enc, roundtrip

CASES = [
    "int(0)", "int(-1)", "int(36028797018963967)", "int(-36028797018963968)",
    "float(1.5)", "float(-0.0)", "float64(3.141592653589793)", "complex(3,-4)", "rational(-3/4)",
    "bigint(123456789012345678901234567890)", "bigint(-5)",
    "rgb(#FF0000)", "rgba(#11223344)", "hsl(#808080)", "yuv(#102030)", "ycbcr(#405060)",
    "rgba14(16383,0,8000,1)",
    "dir(16384,0,0)", "dir(0,100,0,relative,to,frame=listener)", "dir(1,2,3,to)",
    "atom(6,6,6)", "compound(6/6/4/none/0; 1/0/0/covalent/1; 1/0/0/covalent/1; 1/0/0/covalent/1; 1/0/0/covalent/1)",
    "compound(8/8/2/none/0; 1/0/0/covalent/1; 1/0/0/covalent/1/ionic/1)",
    "time(1700000000)", "time(-1)", "duration(3600)", "datetime(2026-11-20T23:41:00-06:00)",
    "datetime(-0500-01-01T00:00:00Z)", "time_ns(1700000000123456789)",
    "id(42)", 'sig(ed25519,00112233445566778899)', "coord(41.8781136,-87.6297982)",
    'uri("https://example.com/thatplace/thisDir/something.jpg")', 'text("Ave Omnissiah ✓")', 'text("")',
    "bytes(png,89504e470d0a1a0a)", "char(U+2699)", 'char("A")',
]


class ExternalRoundTrip(unittest.TestCase):
    def test_all_cases(self):
        seen = set()
        for c in CASES:
            w, canon = roundtrip(f"STATEMENT<Assertion>{{ {c} TO_OBJECT }}")
            seen.add((w[1] >> 56) & 0x3F)
        for code, t in REGISTRY.items():
            if code not in (0x00, 0x01, 0x02, 0x30):
                self.assertIn(code, seen, f"no round-trip case for {t.name}")

    def test_pointer(self):
        roundtrip("STATEMENT<Assertion>{ tool.obj<S> } STATEMENT<Deletion>{ ptr(1) TO_OBJECT }")

    def test_int_value(self):
        w = enc("STATEMENT<Assertion>{ int(-2) }")
        self.assertEqual(w[1], 0x48FFFFFFFFFFFFFE)

    def test_float_value(self):
        w = enc("STATEMENT<Assertion>{ float(1.0) }")
        self.assertEqual(w[1], 0x490000003F800000)

    def test_coord_precision(self):
        w, canon = roundtrip("STATEMENT<Assertion>{ coord(41.8781136,-87.6297982) }")
        lat, lon = canon.split("coord(")[1].split(")")[0].split(",")
        self.assertLess(abs(float(lat) - 41.8781136), 2e-6)
        self.assertLess(abs(float(lon) + 87.6297982), 2e-6)

    def test_text_padding_must_be_zero(self):
        w = enc('STATEMENT<Assertion>{ text("abc") }')
        w[2] |= 1
        with self.assertRaisesRegex(CantError, "padding"):
            decode(w, file=False)

    def test_compound_tree_validation(self):
        with self.assertRaisesRegex(CantError, "incomplete"):
            enc("STATEMENT<Assertion>{ compound(6/6/4/none/0; 1/0/0/covalent/1) }")
        with self.assertRaisesRegex(CantError, "parent bond"):
            enc("STATEMENT<Assertion>{ compound(6/6/0/covalent/1) }")

    def test_range_errors(self):
        for bad in ["int(36028797018963968)", "rgb(#FFF)", "rational(1/0)", "atom(70000,0,0)",
                    "datetime(2026-13-01T00:00:00Z)", "coord(91,0)", "char(U+110000)", 'char("ab")',
                    "dir(0,0,0,frame=listener)", "datetime(2026-01-01T00:00:00+05:07)"]:
            with self.assertRaises(CantError, msg=bad):
                enc(f"STATEMENT<Assertion>{{ {bad} }}")

    def test_arithmetic_eval(self):
        enc("STATEMENT<Assertion>{ int(8) int(2) LOG }")
        with self.assertRaisesRegex(CantError, "division by zero"):
            enc("STATEMENT<Assertion>{ int(1) int(0) DIV }")


if __name__ == "__main__":
    unittest.main()
