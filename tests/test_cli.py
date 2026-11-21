import os
import subprocess
import sys
import tempfile
import unittest

from tests.helpers import ROOT


def run(*args, stdin=None):
    return subprocess.run([sys.executable, "-m", "cant", *args], cwd=ROOT, input=stdin,
                          capture_output=True, text=True)


class CLI(unittest.TestCase):
    def test_encode_decode_dump_binary(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.cant.bin")
            r = run("encode", "examples/dialogue.cant", "-o", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(os.path.getsize(out), 80)
            r = run("decode", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("tool.obj<V,Present>", r.stdout)
            r = run("dump", out)
            self.assertIn("FILE v2.1, 9 words follow", r.stdout)
            self.assertIn("count=2 span=2", r.stdout)

    def test_decode_hex_string(self):
        r = run("decode", "--hex", "C000000100000001 1C00000000000002")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("null.act<V,Present>", r.stdout)
        self.assertIn("Nothing (happening)", r.stdout)

    def test_error_exit(self):
        r = run("encode", "-e", "STATEMENT<Assertion>{ self.obj<Present> }")
        self.assertEqual(r.returncode, 1)
        self.assertIn("needs a grammar role", r.stderr)

    def test_lexicon_and_distance(self):
        r = run("lexicon", "manipulator")
        self.assertIn("at manipulator", r.stdout)
        r = run("distance", "mover.act", "mover.obj")
        self.assertIn("semantic Hamming distance: 1 / 32", r.stdout)
        self.assertIn("same root", r.stdout)

    def test_types(self):
        r = run("types")
        self.assertIn("0x7A  char", r.stdout)
        self.assertIn("IF_ELSE", r.stdout)
