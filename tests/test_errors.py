import unittest

from cant import CantError, decode
from tests.helpers import enc


class GlossErrors(unittest.TestCase):
    def bad(self, text, pattern):
        with self.assertRaisesRegex(CantError, pattern):
            enc(text)

    def test_missing_role(self):
        self.bad("STATEMENT<Assertion>{ self.obj<Present> }", "needs a grammar role")

    def test_duplicate_field(self):
        self.bad("STATEMENT<Assertion>{ self.obj<S,O> }", "repeats the role")

    def test_unknown_root(self):
        self.bad("STATEMENT<Assertion>{ hand.obj<S> }", "unknown root 'hand'")

    def test_undefined_sense(self):
        self.bad("STATEMENT<Assertion>{ sophont.act<V> }", "no defined act sense")

    def test_missing_category(self):
        self.bad("STATEMENT<Assertion>{ self<S> }", "is not a word|category")

    def test_unknown_flag(self):
        self.bad("STATEMENT<Assertion>{ self.obj<S,Purple> }", "unknown word flag")

    def test_header_without_subtype(self):
        self.bad("STATEMENT<Honest>{}", "needs a subtype")

    def test_query_subtype_on_statement(self):
        self.bad("STATEMENT<Verb>{}", "not a statement subtype")

    def test_unclosed(self):
        self.bad("STATEMENT<Assertion>{ self.obj<S>", "missing '}'")

    def test_word_at_top_level(self):
        self.bad("self.obj<S>", "inside a sentence")

    def test_speaker_inside_sentence(self):
        self.bad("STATEMENT<Assertion>{ speaker(1) }", "only allowed at conversation level")

    def test_ext_with_flags(self):
        self.bad("STATEMENT<Assertion>{ int(1)<S> }", "carry no grammar")

    def test_op_underflow(self):
        self.bad("STATEMENT<Assertion>{ int(1) ADD }", "needs 2 operand")

    def test_op_cannot_reach_parent_scope(self):
        self.bad("STATEMENT<Assertion>{ int(1) STATEMENT<Assertion>{ int(2) ADD } }", "needs 2 operand")

    def test_arith_type(self):
        self.bad("STATEMENT<Assertion>{ self.obj<S> int(2) ADD }", "must be numbers")

    def test_link_too_far(self):
        self.bad("STATEMENT<Assertion>{ self.obj<S> mover.act<V,^2> }", "before the start")

    def test_numbered_needs_number(self):
        self.bad("STATEMENT<Assertion>{ self.obj<S> sophont.obj<S,Numbered> }", "Numbered")

    def test_cast_with_role(self):
        self.bad("STATEMENT<Assertion>{ int(1) TO_VERB<S> }", "take their role from the opcode")

    def test_flags_on_non_cast(self):
        self.bad("STATEMENT<Assertion>{ int(1) int(1) ADD<Present> }", "only TO_")

    def test_forward_pointer(self):
        self.bad("STATEMENT<Assertion>{ ptr(9) }", "point backwards")

    def test_pointer_into_middle(self):
        self.bad('STATEMENT<Assertion>{ text("0123456789") } STATEMENT<Assertion>{ ptr(3) }', "start of an item")

    def test_reserved_affection_in_gloss(self):
        self.bad("STATEMENT<Assertion,Empty>{}", "not a statement subtype, affection")


class BinaryErrors(unittest.TestCase):
    def bad(self, words, pattern):
        with self.assertRaisesRegex(CantError, pattern):
            decode(words, file=False)

    def test_count_mismatch(self):
        w = enc("STATEMENT<Assertion>{ self.obj<S> mover.act<V> }")
        w[0] = (w[0] & ~(0xFFFFF << 32)) | (3 << 32)
        self.bad(w, "word count is 3 but")

    def test_span_overrun(self):
        w = enc("STATEMENT<Assertion>{ self.obj<S> }")
        w[0] += 1
        self.bad(w, "runs past the end")

    def test_nested_span_overrun(self):
        w = enc("STATEMENT<Assertion>{ STATEMENT<Assertion>{ self.obj<S> } }")
        w[1] += 1
        self.bad(w, "runs past the end of its parent")

    def test_reserved_role(self):
        self.bad([0xC000000100000001, 0x3800000000000000], "role 7 is reserved")

    def test_reserved_lexical_bits(self):
        self.bad([0xC000000100000001, 0x0000000100000000], "reserved bits 34..32")

    def test_link_flag_mismatch(self):
        self.bad([0xC000000100000001, 0x0000200000000000], "link flag")

    def test_reserved_affection(self):
        self.bad([0xC600000000000000], "affection 12 is reserved")

    def test_reserved_evidentiality(self):
        self.bad([0xC070000000000000], "evidentiality 7 is reserved")

    def test_unknown_external(self):
        self.bad([0xC000000100000001, 0x7F00000000000000], "reserved/unknown")

    def test_unknown_opcode(self):
        self.bad([0xC000000100000002, 0x4800000000000001, 0x7EFFFF0000000000], "unknown opcode")

    def test_truncated_continuation(self):
        self.bad([0xC000000100000001, 0x4A00000000000000], "continuation")

    def test_not_word_aligned(self):
        from cant import from_bytes
        with self.assertRaisesRegex(CantError, "whole number of 64-bit words"):
            from_bytes(b"\x00" * 9)


if __name__ == "__main__":
    unittest.main()
