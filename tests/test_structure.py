import unittest

from cant import CantError, decode, fields as F
from cant.codec import file_header
from tests.helpers import enc, roundtrip


class Nesting(unittest.TestCase):
    def test_nested_sentence_counts_as_one(self):
        w = enc("STATEMENT<Assertion>{ self.obj<S> STATEMENT<Assertion>{ mover.act<V> tool.obj<O> self.obj<S> } }")
        self.assertEqual(F.field(w[0], F.H_COUNT_SHIFT, 20), 2)
        self.assertEqual(F.field(w[0], 0, 32), 5)       # 1 + nested header + 3
        self.assertEqual(F.field(w[2], F.H_COUNT_SHIFT, 20), 3)
        self.assertEqual(F.field(w[2], 0, 32), 3)

    def test_external_with_continuations_counts_as_one(self):
        w = enc('STATEMENT<Assertion>{ text("hello, binary world") TO_OBJECT }')
        self.assertEqual(F.field(w[0], F.H_COUNT_SHIFT, 20), 1)
        self.assertEqual(F.field(w[0], 0, 32), 1 + 3 + 1)

    def test_deep_nesting_roundtrip(self):
        text = "self.obj<S>"
        for _ in range(12):
            text = f"STATEMENT<Assertion>{{ {text} mover.act<V> }}"
        w, _ = roundtrip(text)
        self.assertEqual(len(w), 12 * 2 + 1)

    def test_scope_ops_bind_inside_nested_sentence(self):
        # TO_OBJECT after the nested sentence's last word belongs to the outer sentence because the
        # inner span ends before it (span framing removes the ambiguity).
        w = enc("STATEMENT<Assertion>{ STATEMENT<Assertion>{ int(1) } TO_OBJECT }")
        self.assertEqual(F.field(w[1], 0, 32), 1)
        self.assertEqual(F.field(w[0], 0, 32), 3)

    def test_wordless_sentence(self):
        self.assertEqual(enc("STATEMENT<Imperative>{}"), [0xE000000000000000])


class FileFormat(unittest.TestCase):
    def test_file_header(self):
        w = enc("STATEMENT<Assertion>{ null.act<V,Present> }", file=True)
        self.assertEqual(w[0], 0x4021000000000002)
        conv = decode(w)
        self.assertEqual(conv.length, 2)

    def test_dialogue_and_narrator(self):
        roundtrip("STATEMENT<Assertion>{ that.obj<T> } speaker(1) QUERY<Verb>{} speaker(2) "
                  "STATEMENT<Assertion>{ that.obj<S> tool.obj<V> } speaker(0)", file=True)

    def test_file_length_mismatch(self):
        w = enc("STATEMENT<Assertion>{ null.act<V> }", file=True)
        with self.assertRaisesRegex(CantError, "says 2 words follow"):
            decode(w + [0xE000000000000000])

    def test_bad_version(self):
        w = enc("STATEMENT<Assertion>{}", file=True)
        w[0] = (w[0] & ~(0xFF << 48)) | (0x20 << 48)
        with self.assertRaisesRegex(CantError, "unsupported version 2.0"):
            decode(w)

    def test_header_only_at_start(self):
        w = enc("STATEMENT<Assertion>{}", file=False) + [file_header(0)]
        with self.assertRaisesRegex(CantError, "file header"):
            decode(w, file=False)

    def test_bytes_roundtrip(self):
        from cant import to_bytes, from_bytes
        w = enc("STATEMENT<Assertion>{ null.act<V> }", file=True)
        b = to_bytes(w)
        self.assertEqual(b[:2], b"\x40\x21")    # big-endian: class/type byte first
        self.assertEqual(from_bytes(b), w)


class Conditionals(unittest.TestCase):
    def test_if_else(self):
        roundtrip("STATEMENT<Condition>{ self.obj<S> } STATEMENT<Result>{ self.obj<S> } "
                  "STATEMENT<Result>{ other.obj<S> } IF_ELSE")

    def test_logic_combines_conditions(self):
        roundtrip("STATEMENT<Condition>{ self.obj<S> } STATEMENT<Condition>{ other.obj<S> } AND "
                  "STATEMENT<Result>{ tool.obj<S> } IF")

    def test_if_requires_result(self):
        with self.assertRaisesRegex(CantError, "Result sentences"):
            enc("STATEMENT<Condition>{} STATEMENT<Assertion>{} IF")

    def test_if_requires_condition(self):
        with self.assertRaisesRegex(CantError, "Condition sentence"):
            enc("STATEMENT<Assertion>{} STATEMENT<Result>{} IF")


if __name__ == "__main__":
    unittest.main()
