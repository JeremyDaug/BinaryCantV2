import unittest

from cant import fields as F
from cant.codec import decode, encode
from cant.model import Conversation, Grammar, Lexical, Sentence
from tests.helpers import LEX, roundtrip, enc


def lex_word(**kw):
    g = Grammar(**kw)
    s = Sentence(True, 0, 0, 0, [Lexical(Grammar(role=1), 5, 0), Lexical(g, 0x1234567, 2)])
    w = encode(Conversation([s]), file=False)
    back = decode(w, file=False).items[0].items[1]
    return w[2], back


class LexicalFieldRoundTrip(unittest.TestCase):
    def check(self, name, values, shift, width):
        for v in values:
            word, back = lex_word(**{name: v}) if name != "link" else lex_word(role=4, link=v)
            self.assertEqual(getattr(back.grammar, name), v, (name, v))
            if name == "link":
                self.assertEqual(F.field(word, F.LINK_FLAG_SHIFT, 1), 1)
            self.assertEqual(F.field(word, shift, width), v)
            self.assertEqual(back.root, 0x1234567)
            self.assertEqual(back.cat, 2)

    def test_role(self):
        self.check("role", range(7), F.ROLE_SHIFT, 3)

    def test_temporal(self):
        self.check("temporal", range(4), F.TEMPORAL_SHIFT, 2)

    def test_progress(self):
        self.check("progress", range(4), F.PROGRESS_SHIFT, 2)

    def test_recurrence(self):
        self.check("recur", range(4), F.RECUR_SHIFT, 2)

    def test_degree(self):
        self.check("degree", range(8), F.DEGREE_SHIFT, 3)

    def test_emphasis_determinative(self):
        self.check("emph", range(2), F.EMPH_SHIFT, 1)
        self.check("det", range(2), F.DET_SHIFT, 1)

    def test_plurality(self):
        self.check("plural", range(3), F.PLURAL_SHIFT, 2)   # 3 (Numbered) needs a number; see below
        w = enc("STATEMENT<Assertion>{ int(7) sophont.obj<S,Numbered> }")
        self.assertEqual(F.field(w[2], F.PLURAL_SHIFT, 2), 3)

    def test_link(self):
        self.check("link", [1], F.LINK_OFF_SHIFT, F.LINK_OFF_W)

    def test_categories_and_root(self):
        for cat in range(4):
            for root in (0, 1, 0x2AAAAAAA, (1 << 30) - 1):
                w = enc(f"STATEMENT<Assertion>{{ 0x{root:X}.{F.CATEGORIES[cat]}<S> }}")
                self.assertEqual(w[1] & 0xFFFFFFFF, (root << 2) | cat)
                self.assertEqual(w[1] >> 62, 0)

    def test_gloss_flag_names_roundtrip(self):
        for flags in ["S", "O,Past", "T,Future,Complete", "V,Present,InProgress,Habitual,Total,!,Specific,Plural",
                      "M,Irregular,None", "R,Continuous,Minimal,Singular", "F,Unstarted,Large"]:
            roundtrip(f"STATEMENT<Assertion>{{ mover.act<{flags}> }}")


class HeaderFieldRoundTrip(unittest.TestCase):
    def test_header_byte_values_match_v2_doc(self):
        # Doc V2.0 table: query subtypes 0x80..0xB8, statement subtypes 0xC0..0xF8
        for i, name in enumerate(F.QUERY_SUBTYPES):
            w = enc(f"QUERY<{name}>{{}}")[0]
            self.assertEqual(w >> 56, 0x80 + 8 * i, name)
        for i, name in enumerate(F.STATEMENT_SUBTYPES):
            w = enc(f"STATEMENT<{name}>{{}}")[0]
            self.assertEqual(w >> 56, 0xC0 + 8 * i, name)

    def test_affection_values_match_v2_doc(self):
        # Doc: Honest 0x800, Dishonest 0x808, ... Pleasure 0x858 (top 12 bits of a query/Subject header)
        for i, name in enumerate(F.AFFECTIONS[:12]):
            w = enc(f"QUERY<Subject,{name}>{{}}")[0]
            self.assertEqual(w >> 52, 0x800 + 8 * i, name)

    def test_evidentiality_values_match_v2_doc(self):
        for i, name in enumerate(F.EVIDENTIALITY[:7]):
            w = enc(f"QUERY<Subject,{name}>{{}}")[0]
            self.assertEqual(w >> 52, 0x800 + i, name)
        self.assertEqual(enc("QUERY<Subject,Observation>{}"), enc("QUERY<Subject,Direct>{}"))

    def test_all_header_combinations_roundtrip(self):
        for st, subs in (("QUERY", F.QUERY_SUBTYPES), ("STATEMENT", F.STATEMENT_SUBTYPES)):
            for sub in subs:
                for aff in F.AFFECTIONS[:12]:
                    for evi in F.EVIDENTIALITY[:7]:
                        roundtrip(f"{st}<{sub},{aff},{evi}>{{ self.obj<S> }}")

    def test_count_and_span_fields(self):
        w = enc("STATEMENT<Assertion>{ int(1) int(2) ADD TO_SUBJECT float64(2.5) TO_OBJECT }")
        self.assertEqual(F.field(w[0], F.H_COUNT_SHIFT, F.H_COUNT_W), 3)   # ops not counted
        self.assertEqual(F.field(w[0], 0, 32), 7)                          # 2 + 2 ops + 2 (float64) + 1 op
        self.assertEqual(len(w), 8)


if __name__ == "__main__":
    unittest.main()
