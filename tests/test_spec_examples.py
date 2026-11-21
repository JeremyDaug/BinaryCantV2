"""Every ```cant block in SPEC.md must encode to the ```hex block that follows it."""

import os
import re
import unittest

from cant import decode, format_conversation
from tests.helpers import LEX, ROOT, enc


def spec_examples():
    with open(os.path.join(ROOT, "SPEC.md"), encoding="utf-8") as fh:
        text = fh.read()
    pairs = re.findall(r"```cant\n(.*?)```\n```hex\n(.*?)```", text, re.S)
    return [(g, [int(h, 16) for h in hx.split()]) for g, hx in pairs]


class SpecExamples(unittest.TestCase):
    def test_examples_present(self):
        self.assertGreaterEqual(len(spec_examples()), 10)

    def test_examples_encode_exactly(self):
        for gloss, words in spec_examples():
            is_file = gloss.lstrip().startswith("; file")
            with self.subTest(gloss=gloss.splitlines()[0 if not is_file else 1]):
                self.assertEqual([f"{w:016X}" for w in enc(gloss, file=is_file)],
                                 [f"{w:016X}" for w in words])
                # and decode back to an equivalent gloss
                canon = format_conversation(decode(words, file=is_file), LEX)
                self.assertEqual(enc(canon, file=is_file), words)

    def test_doc_v1_word_survives(self):
        # Doc V1: Nothing<Verb, Present, ...> = 0x1C00 / 0x0002 ; V2.1 keeps both halves' meaning
        w = enc("STATEMENT<Assertion>{ null.act<V,Present> }")
        self.assertEqual(w[1] >> 48, 0x1C00)
        self.assertEqual(w[1] & 0xFFFF, 0x0002)

    def test_example_files_match(self):
        d = os.path.join(ROOT, "examples")
        for name in os.listdir(d):
            if name.endswith(".cant"):
                with open(os.path.join(d, name), encoding="utf-8") as fh:
                    text = fh.read()
                enc(text, file=text.startswith("; file"))


if __name__ == "__main__":
    unittest.main()
