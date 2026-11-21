"""JSON API handlers for the web UI.

Each handler takes a dict (the parsed JSON request body or query string) and returns a
JSON-serialisable dict.  Handlers raise ApiError for bad input; the server turns that into
HTTP 400 with {"error": message}.  They are plain functions so tests can call them directly.
"""

import base64
import re

from .. import fields as F
from ..codec import decode, encode, from_bytes, to_bytes
from ..dump import breakdown
from ..english import EnglishLexicon, cant2en, en2cant
from ..gloss import annotate, format_conversation, format_item, parse
from ..lexicon import Lexicon, LexiconError
from ..model import CantError, External, Lexical, Operation, Sentence
from ..ops import OPCODES
from ..semantic import DOMAINS, hamming, split_root, tree_distance


class ApiError(ValueError):
    pass


class Api:
    def __init__(self, lex=None):
        self.lex = lex or Lexicon()
        self.en = EnglishLexicon(self.lex)

    # ------------------------------------------------------------ helpers
    def _words_from(self, req):
        """Accept {"hex": "..."} or {"base64": "..."} (raw .cant bytes)."""
        if req.get("base64"):
            try:
                data = base64.b64decode(req["base64"], validate=True)
            except ValueError:
                raise ApiError("base64 payload is not valid base64") from None
            return from_bytes(data)
        text = req.get("hex", "")
        digits = re.sub(r"\s|0x|,|_", "", text)
        if not digits:
            raise ApiError("no hex words given")
        if not re.fullmatch(r"[0-9A-Fa-f]+", digits):
            raise ApiError("hex input contains non-hex characters")
        if len(digits) % 16:
            raise ApiError(f"hex input has {len(digits)} digits; need a multiple of 16 (64-bit words)")
        return [int(digits[i:i + 16], 16) for i in range(0, len(digits), 16)]

    def _report(self, conv, file=True):
        words = encode(conv, file=file)
        decoded = decode(words, file=file)
        rows = []
        lookup = words if file else [None] + words   # bare-stream trace indices start at 1
        for idx, depth, item, role in decoded._trace:
            w = lookup[idx]
            if role == "file":
                v = F.field(w, 48, 8)
                text, note = "FILE", f"conversation file v{v >> 4}.{v & 0xF}, {F.field(w, 0, 40)} words follow"
            elif role.startswith("cont"):
                text, note = "…", f"continuation {int(role[4:]) + 1} of {item.type.name}"
            else:
                text, note = format_item(item, self.lex), annotate(item, self.lex)
            rows.append({"index": idx, "depth": depth, "hex": f"{w:016X}", "gloss": text, "note": note,
                         "kind": role if role in ("file",) or role.startswith("cont") else _kind(item),
                         "fields": word_fields(w, cont=role.startswith("cont")),
                         "segments": segments(w, cont=role.startswith("cont") or role == "file")})
        return {"gloss": format_conversation(decoded, self.lex),
                "hex": [f"{w:016X}" for w in words],
                "words": rows,
                "base64": base64.b64encode(to_bytes(words)).decode("ascii")}

    # ------------------------------------------------------------ handlers
    def en2cant(self, req):
        text = (req.get("text") or "").strip()
        if not text:
            raise ApiError("no English text given")
        conv, warnings = en2cant(text, self.en)
        out = self._report(conv)
        out["warnings"] = warnings
        out["english"] = cant2en(conv, self.en)
        return out

    def cant2en(self, req):
        conv = self._conv_from(req)
        return {"english": cant2en(conv, self.en), **self._report(conv)}

    def encode(self, req):
        gloss = req.get("gloss", "")
        if not gloss.strip():
            raise ApiError("no gloss given")
        try:
            conv = parse(gloss, self.lex)
            return self._report(conv, file=not req.get("bare"))
        except (CantError, LexiconError) as ex:
            raise ApiError(str(ex)) from None

    def decode(self, req):
        try:
            conv = decode(self._words_from(req), file=None)
        except CantError as ex:
            raise ApiError(str(ex)) from None
        out = self._report(conv)
        out["english"] = cant2en(conv, self.en)
        return out

    def _conv_from(self, req):
        try:
            if req.get("gloss", "").strip():
                return parse(req["gloss"], self.lex)
            if req.get("hex") or req.get("base64"):
                return decode(self._words_from(req), file=None)
            text = (req.get("text") or "").strip()
            if not text:
                raise ApiError("give gloss, hex or base64")
            if re.fullmatch(r"(0x)?[0-9A-Fa-f\s,_x]+", text) and len(re.sub(r"\s|0x|,|_", "", text)) % 16 == 0:
                return decode(self._words_from({"hex": text}), file=None)
            return parse(text, self.lex)
        except (CantError, LexiconError) as ex:
            raise ApiError(str(ex)) from None

    def lexicon(self, req):
        q = (req.get("q") or "").lower().strip()
        dom = req.get("domain")
        cat = req.get("category")
        english = {}
        for e in self.en.entries:
            english.setdefault(e.root, []).append(e.english)
        rows = []
        for e in self.lex:
            if dom not in (None, "", "all") and e.domain != int(dom):
                continue
            if cat not in (None, "", "all") and not e.sense(F.CATEGORIES.index(cat)):
                continue
            words = sorted(set(english.get(e.root, [])))
            hay = " ".join([e.key, *e.senses, *words]).lower()
            if q and q not in hay:
                continue
            rows.append({"key": e.key, "root": f"0x{e.root:08X}", "domain": e.domain, "cluster": e.cluster,
                         "concept": e.concept, "senses": dict(zip(F.CATEGORIES, e.senses)),
                         "proposed": [c for c in F.CATEGORIES if e.sense(F.CATEGORIES.index(c))
                                      and e.is_proposed(F.CATEGORIES.index(c))],
                         "english": words, "source": e.source})
        return {"total": len(self.lex), "count": len(rows), "entries": rows,
                "domains": {str(k): v for k, v in sorted(DOMAINS.items())}}

    def distance(self, req):
        a, b = self._semantic(req.get("a", "")), self._semantic(req.get("b", ""))
        diff = a["semantic"] ^ b["semantic"]
        levels = ["identical", "same root (sibling sense)", "same cluster", "same domain", "different domain"]
        bits = [i for i in range(31, -1, -1) if diff >> i & 1]
        td = tree_distance(a["semantic"], b["semantic"])
        return {"a": a, "b": b, "hamming": hamming(a["semantic"], b["semantic"]), "differing_bits": bits,
                "fields": {"domain": [i for i in bits if i >= 24], "cluster": [i for i in bits if 16 <= i < 24],
                           "concept": [i for i in bits if 2 <= i < 16], "category": [i for i in bits if i < 2]},
                "tree": td, "tree_label": levels[td]}

    def _semantic(self, token):
        token = token.strip()
        if not token:
            raise ApiError("give two words (key.cat, English word, or 0xSEMANTIC)")
        try:
            if re.fullmatch(r"0x[0-9A-Fa-f]{1,8}", token):
                s = int(token, 16)
            elif "." in token:
                root, cat = self.lex.resolve(token)
                s = (root << 2) | cat
            else:
                hits = self.en.forms.get(token.lower())
                if not hits:
                    raise ApiError(f"'{token}' is neither a lexicon key.cat nor a known English word")
                e = hits[0][0]
                s = (e.root << 2) | e.cat
        except LexiconError as ex:
            raise ApiError(str(ex)) from None
        root, cat = s >> 2, s & 3
        d, c, k = split_root(root)
        return {"input": token, "name": self.lex.name(root, cat), "gloss": self.lex.gloss(root, cat),
                "semantic": s, "hex": f"0x{s:08X}", "bits": f"{s:032b}", "domain": d, "cluster": c,
                "concept": k, "category": F.CATEGORIES[cat]}

    def meta(self, req):
        return {"version": "2.2", "roots": len(self.lex), "english_entries": len(self.en.entries),
                "domains": {str(k): v for k, v in sorted(DOMAINS.items())}, "categories": F.CATEGORIES}


def _kind(item):
    if isinstance(item, Sentence):
        return "header"
    if isinstance(item, Lexical):
        return "lexical"
    if isinstance(item, Operation):
        return "op"
    return "external"


def word_fields(w, cont=False):
    """Named, decoded fields for the breakdown table."""
    if cont:
        return {"class": "continuation"}
    if F.is_header(w):
        st = F.field(w, F.H_QS_SHIFT, 1)
        return {"class": "statement" if st else "query",
                "subtype": (F.STATEMENT_SUBTYPES if st else F.QUERY_SUBTYPES)[F.field(w, F.H_SUB_SHIFT, 3)],
                "affection": F.AFFECTIONS[F.field(w, F.H_AFF_SHIFT, 4)] or "reserved",
                "evidentiality": F.EVIDENTIALITY[F.field(w, F.H_EVI_SHIFT, 3)] or "reserved",
                "count": F.field(w, F.H_COUNT_SHIFT, F.H_COUNT_W), "span": F.field(w, 0, 32)}
    if F.word_class(w) == F.CLASS_LEXICAL:
        g = lambda s, n: F.field(w, s, n)
        root = g(F.ROOT_SHIFT, F.ROOT_W)
        d, c, k = split_root(root)
        return {"class": "lexical", "role": F.ROLES[g(F.ROLE_SHIFT, 3)] or "reserved",
                "tense": F.TEMPORAL[g(F.TEMPORAL_SHIFT, 2)], "progression": F.PROGRESSION[g(F.PROGRESS_SHIFT, 2)],
                "recurrence": F.RECURRENCE[g(F.RECUR_SHIFT, 2)], "degree": F.DEGREE[g(F.DEGREE_SHIFT, 3)],
                "emphasis": bool(g(F.EMPH_SHIFT, 1)), "determinative": bool(g(F.DET_SHIFT, 1)),
                "plurality": F.PLURALITY[g(F.PLURAL_SHIFT, 2)],
                "link": g(F.LINK_OFF_SHIFT, F.LINK_OFF_W) if g(F.LINK_FLAG_SHIFT, 1) else None,
                "domain": d, "cluster": c, "concept": k, "category": F.CATEGORIES[g(0, 2)]}
    code = F.field(w, 56, 6)
    if code == 0x3E:
        op = F.field(w, F.OP_CODE_SHIFT, 16)
        return {"class": "operation", "opcode": f"0x{op:04X}", "op": OPCODES.get(op, ("?",))[0],
                "operand": f"0x{w & 0xFFFFFFFF:08X}"}
    return {"class": "external", "type": f"0x{0x40 | code:02X}", "payload": f"0x{w & F.PAYLOAD_MASK:014X}"}


def segments(w, cont=False):
    """Bit segments [name, width, value-bits] from MSB to LSB, for the coloured 64-bit view."""
    b = f"{w:064b}"
    def cut(spec):
        out, pos = [], 0
        for name, width in spec:
            out.append({"name": name, "bits": b[pos:pos + width]})
            pos += width
        return out
    if cont:
        return cut([("data", 64)])
    if F.is_header(w):
        return cut([("class", 2), ("subtype", 3), ("affection", 4), ("evidence", 3), ("count", 20), ("span", 32)])
    if F.word_class(w) == F.CLASS_LEXICAL:
        return cut([("class", 2), ("role", 3), ("tense", 2), ("progress", 2), ("recur", 2), ("degree", 3),
                    ("emph", 1), ("det", 1), ("plural", 2), ("link", 1), ("offset", 10), ("rsv", 3),
                    ("domain", 8), ("cluster", 8), ("concept", 14), ("cat", 2)])
    if F.field(w, 56, 6) == 0x3E:
        return cut([("class", 2), ("type", 6), ("opcode", 16), ("rsv", 8), ("operand", 32)])
    return cut([("class", 2), ("type", 6), ("payload", 56)])
