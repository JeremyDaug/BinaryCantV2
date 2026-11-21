"""Web UI JSON API: direct handler calls plus a live server on an ephemeral port."""
import base64
import json
import threading
import unittest
import urllib.error
import urllib.request

from cant.web.api import Api, ApiError
from cant.web.server import make_server
from tests.helpers import LEX

API = Api(LEX)


class Handlers(unittest.TestCase):
    def test_en2cant(self):
        r = API.en2cant({"text": "The cat sleeps."})
        self.assertEqual(r["english"], "The cat sleeps.")
        self.assertEqual(r["hex"][0][:4], "4021")            # file header, v2.1 layout
        self.assertEqual(len(r["words"]), len(r["hex"]))
        lex = [w for w in r["words"] if w["kind"] == "lexical"]
        self.assertEqual(lex[0]["fields"]["role"], "Subject")
        self.assertEqual(lex[1]["fields"]["tense"], "Present")
        for w in r["words"]:
            self.assertEqual("".join(s["bits"] for s in w["segments"]), f"{int(w['hex'], 16):064b}")

    def test_en2cant_warnings(self):
        r = API.en2cant({"text": "The glorp eats bread."})
        self.assertTrue(any("glorp" in w for w in r["warnings"]))

    def test_cant2en_accepts_hex_and_gloss(self):
        hx = " ".join(API.en2cant({"text": "Where do you live?"})["hex"])
        self.assertEqual(API.cant2en({"text": hx})["english"], "Where do you live?")
        self.assertEqual(API.cant2en({"gloss": "STATEMENT<Assertion>{ null.act<V,Present> }"})["english"],
                         "Nothing happens.")

    def test_encode_decode_roundtrip(self):
        e = API.encode({"gloss": "STATEMENT<Assertion>{ cat.obj<S> sleep.act<V,Present> }"})
        d = API.decode({"hex": "".join(e["hex"])})
        self.assertEqual(d["hex"], e["hex"])
        self.assertEqual(d["english"], "Cat sleeps.")
        b = API.decode({"base64": e["base64"]})
        self.assertEqual(b["hex"], e["hex"])
        bare = API.encode({"gloss": "STATEMENT<Assertion>{ null.act<V,Present> }", "bare": True})
        self.assertEqual(bare["hex"], ["C000000100000001", "1C00000000000002"])

    def test_validation_errors(self):
        for fn, req in ((API.encode, {"gloss": "STATEMENT<Assertion>{ nosuchword.obj<S> }"}),
                        (API.encode, {"gloss": ""}),
                        (API.decode, {"hex": "123"}),
                        (API.decode, {"hex": "zz"}),
                        (API.decode, {"base64": "!!"}),
                        (API.en2cant, {"text": ""}),
                        (API.distance, {"a": "cat", "b": "nosuchword"})):
            with self.subTest(req=req):
                with self.assertRaises(ApiError):
                    fn(req)

    def test_lexicon(self):
        r = API.lexicon({})
        self.assertEqual(r["count"], r["total"])
        self.assertGreaterEqual(r["total"], 250)
        dog = API.lexicon({"q": "dog"})
        self.assertTrue(any(e["key"] == "dog" for e in dog["entries"]))
        d8 = API.lexicon({"domain": "8"})
        self.assertTrue(d8["entries"])
        self.assertTrue(all(e["domain"] == 8 for e in d8["entries"]))
        rel = API.lexicon({"category": "rel"})
        self.assertTrue(all(e["senses"]["rel"] for e in rel["entries"]))

    def test_distance(self):
        r = API.distance({"a": "cat", "b": "dog"})
        self.assertEqual(r["hamming"], len(r["differing_bits"]))
        self.assertLessEqual(r["hamming"], 3)
        far = API.distance({"a": "dog.obj", "b": "0x00000000"})
        self.assertGreater(far["hamming"], r["hamming"])
        self.assertEqual(API.distance({"a": "cat", "b": "cat"})["hamming"], 0)


class LiveServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = make_server("127.0.0.1", 0, LEX)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())

    def test_index(self):
        with urllib.request.urlopen(self.base + "/", timeout=5) as r:
            html = r.read().decode()
        self.assertIn("BINARY", html)
        self.assertNotIn("http://", html.replace("http://127", ""))   # no CDN / external assets
        self.assertNotIn("https://", html)

    def test_post_endpoints(self):
        s, r = self.post("/api/en2cant", {"text": "I have five friends."})
        self.assertEqual((s, r["english"]), (200, "I have five friends."))
        s, r = self.post("/api/cant2en", {"text": " ".join(r["hex"])})
        self.assertEqual(r["english"], "I have five friends.")
        s, r = self.post("/api/distance", {"a": "cat", "b": "dog"})
        self.assertEqual(s, 200)

    def test_get_lexicon_and_meta(self):
        with urllib.request.urlopen(self.base + "/api/lexicon?q=river", timeout=5) as r:
            self.assertTrue(json.loads(r.read())["entries"])
        with urllib.request.urlopen(self.base + "/api/meta", timeout=5) as r:
            self.assertEqual(json.loads(r.read())["version"], "2.2")

    def test_errors_are_json_400(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post("/api/decode", {"hex": "123"})
        self.assertEqual(cm.exception.code, 400)
        self.assertIn("error", json.loads(cm.exception.read()))
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post("/api/nope", {})
        self.assertEqual(cm.exception.code, 404)
        req = urllib.request.Request(self.base + "/api/encode", data=b"not json")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 400)

    def test_binary_upload_roundtrip(self):
        s, r = self.post("/api/en2cant", {"text": "The dog runs to the river."})
        s, d = self.post("/api/decode", {"base64": r["base64"]})
        self.assertEqual(d["english"], "The dog runs to the river.")
        self.assertEqual(base64.b64decode(r["base64"])[:2], b"\x40\x21")


if __name__ == "__main__":
    unittest.main()
