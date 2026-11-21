"""Rule-based English -> Binary Cant.

Covers simple clauses: declaratives, yes/no and wh- questions, imperatives, conditionals
("If A, B."), SVO with adjectives/adverbs, articles, plurals, numbers, tenses (past /
present / future with 'will'), progressive, perfect, negation, possessives, prepositional
phrases, comparatives, coordination of noun phrases with 'and', and colour words.
Unknown words become text() externals with a warning.  See TRANSLATION.md.
"""

import re

from .. import fields as F
from ..externals import BY_NAME as EXT
from ..model import Conversation, External, Grammar, Lexical, Operation, Sentence
from ..ops import BY_NAME as OPS
from . import morph
from .colours import COLOURS
from .enlex import EnglishLexicon

S, O, T, V, M, R, FU = range(7)
PRESENT, PAST, FUTURE = 2, 1, 3
INPROG, COMPLETE = 2, 3
DEG_NONE = 1

BE = {"am": PRESENT, "is": PRESENT, "are": PRESENT, "was": PAST, "were": PAST}
DO = {"do": PRESENT, "does": PRESENT, "did": PAST}
HAVE = {"have": PRESENT, "has": PRESENT, "had": PAST}
AUX = set(BE) | set(DO) | set(HAVE) | {"will", "shall"}
MODALS = {"can", "could", "should", "must", "would", "may", "might"}
WH = {"who": 0, "whom": 1, "what": None, "when": 3, "where": 4, "why": 5, "how": 6, "which": 7}
ARTICLES = {"the": "the", "a": "a", "an": "a"}
EVIDENTIAL = {"reportedly": 1, "apparently": 1, "presumably": 2, "therefore": 3, "so": 3,
              "generally": 4, "hypothetically": 5, "theoretically": 5}
UNCERTAIN = {"perhaps", "maybe", "possibly"}
CONTRACTIONS = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not", "isn't": "is not", "aren't": "are not",
    "wasn't": "was not", "weren't": "were not", "won't": "will not", "can't": "can not", "cannot": "can not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not", "i'm": "i am", "you're": "you are",
    "we're": "we are", "they're": "they are", "i've": "i have", "you've": "you have", "we've": "we have",
    "they've": "they have", "i'll": "i will", "you'll": "you will", "we'll": "we will", "they'll": "they will",
    "he'll": "he will", "she'll": "she will", "it'll": "it will", "let's": "let us",
}
IS_CONTRACT = {"he", "she", "it", "that", "this", "there", "here", "what", "where", "who", "how", "when", "why"}


class Tok:
    __slots__ = ("w", "orig")

    def __init__(self, w, orig):
        self.w, self.orig = w, orig

    def __repr__(self):
        return self.w


class ParseError(ValueError):
    pass


# ------------------------------------------------------------------ tokenising
def split_sentences(text):
    parts = re.findall(r"(?:\d\.\d|[^.?!])+(?:[.?!]+(?:\s*\([a-z ]+\)[.?!]?)?)?", text.strip())
    return [p.strip() for p in parts if p.strip(" .?!")]


def tokenize(sentence):
    s = sentence.replace("\u2019", "'").strip()
    punct = ""
    m = re.search(r"([.?!]+)\s*$", s)
    if m:
        punct = m.group(1)[-1]
        s = s[:m.start()]
    toks = []
    for raw in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?(?<=s)'|[A-Za-z]+(?:'[A-Za-z]+)?|\d+\.\d+|\d+|,|#[0-9A-Fa-f]{6}", s):
        low = raw.lower()
        if low in CONTRACTIONS:
            for part in CONTRACTIONS[low].split():
                toks.append(Tok(part, part))
            continue
        if low.endswith("'s"):
            stem = raw[:-2]
            if stem.lower() in IS_CONTRACT:
                toks += [Tok(stem.lower(), stem), Tok("is", "is")]
            else:
                toks += [Tok(stem.lower(), stem), Tok("'s", "'s")]
            continue
        if low.endswith("s'") or low.endswith("'"):
            toks += [Tok(low.rstrip("'"), raw.rstrip("'")), Tok("'s", "'s")]
            continue
        toks.append(Tok(low, raw))
    return toks, punct


# ------------------------------------------------------------------ phrase objects
class NP:
    def __init__(self):
        self.kind = None          # 'lex' | 'pron' | 'text' | 'dem'
        self.entry = None
        self.root = self.cat = None
        self.text = None
        self.plural = False
        self.number = None
        self.det = None           # 'the' | 'a' | None
        self.mods = []            # ('adj', root, cat, degree) | ('rgb', hex)
        self.quant = None         # degree on amount
        self.demo = None          # this/that entry used as determiner
        self.possessor = None

    def __repr__(self):
        return f"NP({self.kind}:{self.entry or self.text} pl={self.plural} n={self.number} det={self.det})"


class Clause:
    def __init__(self):
        self.subjects = []
        self.verb = None          # EnEntry for v / rv
        self.verb_text = None     # unknown verb text
        self.copula = False
        self.pred = None
        self.existential = False
        self.tense = None
        self.prog = self.perf = self.neg = False
        self.objects = []
        self.adverbs = []         # (root, cat, grammar-kwargs)
        self.pps = []             # (prep entry, NP)


# ------------------------------------------------------------------ the parser
class Parser:
    def __init__(self, en=None):
        self.en = en or EnglishLexicon()
        self.lex = self.en.lex
        self.warnings = []
        self.null_root = self.lex.by_key["null"].root
        self.amount = self.lex.by_key["amount"].root
        self.existence = self.lex.by_key["existence"].root

    def warn(self, msg):
        if msg not in self.warnings:
            self.warnings.append(msg)

    # --- lookups ------------------------------------------------------------
    def L(self, tok, pos):
        return self.en.lookup(tok.w, pos) if tok is not None else []

    def is_known(self, tok):
        return bool(self.en.lookup(tok.w)) or tok.w in AUX or tok.w in WH or tok.w in ARTICLES \
            or morph.number_value(tok.w) is not None or tok.w in COLOURS or tok.w in ("not", "and", "very", "extremely", "please", "'s", "than", "more", "there", "if", "then", ",")

    # --- noun phrases --------------------------------------------------------
    def np_start(self, toks, i):
        if i >= len(toks):
            return False
        t = toks[i]
        if t.w in ARTICLES or t.w in COLOURS or morph.number_value(t.w) is not None or t.w == "very":
            return True
        if self.L(t, ("n", "rn", "pron", "dem", "q", "a", "pl")):
            return True
        if not self.is_known(t):
            return True
        return False

    def parse_np(self, toks, i, allow_pred_adj=False):
        """Parse one noun phrase at toks[i]. Returns (NP, next_index) or (None, i)."""
        start = i
        np = NP()
        n = len(toks)
        if i >= n:
            return None, i
        t = toks[i]
        # pronoun
        pr = self.L(t, ("pron",))
        if pr:
            e, kind = pr[0]
            if kind in ("poss", "plposs"):
                np2, j = self.parse_np(toks, i + 1)
                if np2 is None:
                    raise ParseError(f"'{t.orig}' must be followed by a noun")
                own = NP()
                own.kind, own.entry, own.root, own.cat = "pron", e, e.root, e.cat
                own.plural = kind == "plposs"
                inner = np2                       # "my friend's house": 'my' owns the innermost possessor
                while inner.possessor is not None:
                    inner = inner.possessor
                inner.possessor = own
                return self._possessive_tail(toks, np2, j)
            np.kind, np.entry, np.root, np.cat = "pron", e, e.root, e.cat
            np.plural = kind in ("pl", "plobj") or (e.english == "they")
            return self._possessive_tail(toks, np, i + 1)
        # determiners
        if t.w in ARTICLES:
            np.det = ARTICLES[t.w]
            i += 1
        elif self.L(t, ("dem",)):
            e, kind = self.L(t, ("dem",))[0]
            nxt = toks[i + 1] if i + 1 < n else None
            if nxt is not None and self.np_start(toks, i + 1) and not (nxt.w in AUX or nxt.w in MODALS):
                np.demo = e
                np.plural = kind == "pl"
                i += 1
            else:
                np.kind, np.entry, np.root, np.cat = "dem", e, e.root, e.cat
                np.plural = kind == "pl"
                return np, i + 1
        elif self.L(t, ("q",)) and not self.L(t, ("n",)):
            e, _ = self.L(t, ("q",))[0]
            np.quant = e.flags["degree"]
            i += 1
            if i < n and (toks[i].w in ARTICLES or any(k in ("poss", "plposs") for _, k in self.L(toks[i], ("pron",)))):
                np2, j = self.parse_np(toks, i)      # "all my friends", "all the dogs"
                if np2 is not None:
                    np2.quant = np.quant
                    return np2, j
        if i < n and morph.number_value(toks[i].w) is not None:
            v = morph.number_value(toks[i].w)
            if toks[i].w in morph.TENS and i + 1 < n and toks[i + 1].w in morph.NUMBER_WORDS[1:10]:
                i += 1                                  # forty-two
                v += morph.number_value(toks[i].w)
            i += 1
            while i < n and toks[i].w in ("hundred", "thousand"):
                v *= morph.number_value(toks[i].w)
                i += 1
            np.number = v
        # adjectives (and colours)
        while i < n:
            very = 0
            j = i
            while j < n and toks[j].w in ("very", "extremely"):
                very += 1 if toks[j].w == "very" else 2
                j += 1
            if j >= n:
                break
            tj = toks[j]
            if tj.w in COLOURS and (j + 1 < n and self.np_head_ok(toks[j + 1])):
                np.mods.append(("rgb", COLOURS[tj.w]))
                i = j + 1
                continue
            adj = self.L(tj, ("a",))
            if adj and adj[0][1] == "base" and j + 1 < n and self.np_head_ok(toks[j + 1]) \
                    and not self.L(tj, ("n",)):
                e = adj[0][0]
                np.mods.append(("adj", e.root, e.cat, self.bump(e.flags["degree"], very)))
                i = j + 1
                continue
            break
        # head noun
        if i >= n:
            if np.number is not None and not np.mods:
                np.kind, np.text = "number", None
                return np, i
            return None, start
        t = toks[i]
        nouns = self.L(t, ("n", "rn", "pl"))
        if nouns:
            e, kind = nouns[0]
            np.kind, np.entry, np.root, np.cat = "lex", e, e.root, e.cat
            np.plural = np.plural or kind == "pl"
            i += 1
        elif not self.is_known(t) and t.w not in MODALS:
            np.kind, np.text = "text", t.orig
            if t.orig[:1].isupper():
                self.warn(f"'{t.orig}' is not in the English lexicon; kept as a name (text external)")
            else:
                self.warn(f"'{t.orig}' is not in the English lexicon; kept as raw text")
                if t.w.endswith("s") and len(t.w) > 3 and (np.number not in (None, 1) or np.det is None):
                    np.plural = True
            i += 1
        else:
            if np.number is not None and not np.mods and np.det is None:
                np.kind = "number"
                return np, i
            return None, start
        if np.number is not None and np.number != 1:
            np.plural = True
        return self._possessive_tail(toks, np, i)

    def _possessive_tail(self, toks, np, i):
        if i < len(toks) and toks[i].w == "'s":
            owned, j = self.parse_np(toks, i + 1)
            if owned is None:
                raise ParseError("possessive 's must be followed by a noun")
            inner = owned                      # "Mary's friend's house": Mary owns the friend
            while inner.possessor is not None:
                inner = inner.possessor
            inner.possessor = np
            return owned, j
        return np, i

    def np_head_ok(self, tok):
        return bool(self.L(tok, ("n", "rn", "a", "pl"))) or tok.w in COLOURS or tok.w == "very" \
            or not self.is_known(tok)

    @staticmethod
    def bump(degree, very):
        for _ in range(very):
            degree = {5: 6, 6: 7, 3: 2}.get(degree, degree)
        return degree

    def parse_np_list(self, toks, i):
        nps = []
        np, i = self.parse_np(toks, i)
        if np is None:
            return nps, i
        nps.append(np)
        while i < len(toks) and toks[i].w == "and" and self.np_start(toks, i + 1):
            np2, j = self.parse_np(toks, i + 1)
            if np2 is None:
                break
            nps.append(np2)
            i = j
        return nps, i

    # --- verb phrases --------------------------------------------------------
    def parse_vp(self, toks, i, clause, preset=None):
        n = len(toks)
        seq = ([Tok(preset, preset)] if preset else []) + toks[i:]
        k = 0
        aux_seen = False

        def nxt(o=1):
            return seq[k + o] if k + o < len(seq) else None

        while k < len(seq):
            w = seq[k].w
            if w in ("will", "shall"):
                clause.tense = FUTURE
            elif w in DO:
                clause.tense = clause.tense or DO[w]
            elif w in HAVE and (nxt() is not None and (self.verb_form(nxt(), "pp") or nxt().w in ("been", "not"))):
                clause.tense = clause.tense or HAVE[w]
                clause.perf = True
            elif w == "have" and clause.tense == FUTURE and nxt() is not None and self.verb_form(nxt(), "pp"):
                clause.perf = True
            elif w in BE or w in ("be", "been"):
                if w in BE:
                    clause.tense = clause.tense or BE[w]
                nn = nxt()
                if nn is not None and nn.w == "going" and nxt(2) is not None and nxt(2).w == "to" \
                        and nxt(3) is not None and self.verb_form(nxt(3), "base"):
                    clause.tense = FUTURE
                    k += 3
                    aux_seen = True
                    continue
                clause.copula = True
            elif w == "not":
                clause.neg = True
            elif w in MODALS:
                self.warn(f"modal '{w}' is not supported yet; dropped")
            else:
                break
            aux_seen = True
            k += 1
        rest = seq[k:]
        j = 0
        # main verb?
        if j < len(rest):
            t = rest[j]
            forms = self.L(t, ("v", "rv"))
            if clause.copula and forms and any(kind == "ing" for _, kind in forms):
                e = [e for e, kind in forms if kind == "ing"][0]
                clause.copula = False
                clause.prog = True
                clause.verb = e
                j += 1
            elif not clause.copula and forms:
                pref = [x for x in forms if x[1] != "pp"] if not clause.perf else [x for x in forms if x[1] == "pp"] or forms
                e, kind = (pref or forms)[0]
                if clause.tense is None:
                    clause.tense = PAST if kind == "past" else PRESENT
                clause.verb = e
                j += 1
            elif not clause.copula and not clause.verb and t.w not in ("there",) and not self.is_known(t) \
                    and not self.np_start_strict(rest, j):
                clause.verb_text = t.orig
                self.warn(f"verb '{t.orig}' is not in the English lexicon; kept as raw text")
                if clause.tense is None:
                    clause.tense = PAST if t.w.endswith("ed") else PRESENT
                j += 1
            elif not clause.copula and not aux_seen and not clause.verb:
                pass
        if clause.copula and not clause.verb:
            j = self.parse_predicate(rest, j, clause)
        else:
            groups = 0
            while j < len(rest) and not self.L(rest[j], ("p", "adv", "tadv")):
                objs, j2 = self.parse_np_list(rest, j)
                if not objs:
                    break
                clause.objects += objs
                groups += 1
                j = j2
            clause.coordinated = groups < 2
        j = self.parse_tail(rest, j, clause)
        if j < len(rest):
            raise ParseError("could not understand '" + " ".join(x.orig for x in rest[j:]) + "'")
        return clause

    def np_start_strict(self, toks, j):
        t = toks[j]
        return t.w in ARTICLES or bool(self.L(t, ("pron", "dem")))

    def verb_form(self, tok, kind):
        return any(k == kind for _, k in self.L(tok, ("v", "rv")))

    def parse_predicate(self, toks, j, clause):
        n = len(toks)
        if j >= n:
            return j
        t = toks[j]
        very = 0
        while j < n and toks[j].w in ("very", "extremely"):
            very += 1 if toks[j].w == "very" else 2
            j += 1
        t = toks[j] if j < n else t
        # comparative: X-er than NP / more X than NP
        if t.w == "more" and j + 2 < n and toks[j + 2].w == "than":
            a = self.L(toks[j + 1], ("a",))
            if a:
                return self._comparative(toks, j + 3, a[0][0], clause)
        cmp = [e for e, k in self.L(t, ("a",)) if k == "cmp"]
        if cmp and j + 1 < n and toks[j + 1].w == "than":
            return self._comparative(toks, j + 2, cmp[0], clause)
        if cmp and j + 1 >= n:
            return self._comparative(toks, j + 1, cmp[0], clause, need_np=False)
        if t.w in COLOURS and (j + 1 >= n or not self.np_head_ok(toks[j + 1])):
            clause.pred = ("rgb", COLOURS[t.w])
            return j + 1
        adj = self.L(t, ("a",))
        if adj and adj[0][1] == "base" and (j + 1 >= n or not self.np_head_ok(toks[j + 1])):
            e = adj[0][0]
            clause.pred = ("adj", e.root, e.cat, self.bump(e.flags["degree"], very))
            return j + 1
        place = self.L(t, ("pl",))
        if place and not (j + 1 < n and self.L(toks[j + 1], ("n",))):
            clause.pred = ("place", place[0][0])
            return j + 1
        prep = self.L(t, ("p",))
        if prep:
            np, k = self.parse_np(toks, j + 1)
            if np is None:
                raise ParseError(f"preposition '{t.orig}' needs a noun phrase")
            clause.pred = ("pp", prep[0][0], np)
            return k
        np, k = self.parse_np(toks, j)
        if np is not None:
            clause.pred = ("np", np)
            return k
        return j

    def _comparative(self, toks, j, adj, clause, need_np=True):
        rel = (adj.root, F.CATEGORIES.index("rel"))
        if not self.lex.by_root[adj.root].sense(1):
            raise ParseError(f"no comparative relation for '{adj.english}'")
        np, k = self.parse_np(toks, j) if need_np else (None, j)
        if np is None and need_np:
            raise ParseError("'than' needs a noun phrase")
        clause.pred = ("cmp", rel, np)
        return k

    def parse_tail(self, toks, j, clause):
        n = len(toks)
        while j < n:
            t = toks[j]
            if t.w == ",":
                j += 1
                continue
            prep = self.L(t, ("p",))
            if prep:
                np, k = self.parse_np(toks, j + 1)
                if np is None:
                    raise ParseError(f"preposition '{t.orig}' needs a noun phrase")
                clause.pps.append((prep[0][0], np))
                j = k
                continue
            very = 0
            k = j
            while k < n and toks[k].w == "very":
                very += 1
                k += 1
            if k < n:
                adv = self.L(toks[k], ("adv", "tadv"))
                if adv:
                    e = adv[0][0]
                    g = dict(e.flags)
                    if "degree" in g:
                        g["degree"] = self.bump(g["degree"], very)
                    clause.adverbs.append((e.root, e.cat, g))
                    j = k + 1
                    continue
                pl = self.L(toks[k], ("pl",))
                if pl and very == 0:
                    clause.pps.append((None, pl[0][0]))
                    j = k + 1
                    continue
            break
        return j

    def extract_adverbs(self, toks, clause):
        """Pull leading adverbs ('Yesterday, ...', 'Quickly ...') into the clause."""
        while toks and (self.L(toks[0], ("adv", "tadv")) or toks[0].w == ","):
            if toks[0].w != ",":
                e = self.L(toks[0], ("adv", "tadv"))[0][0]
                clause.adverbs.append((e.root, e.cat, dict(e.flags)))
            toks = toks[1:]
        return toks

    # --- clauses -------------------------------------------------------------
    def parse_declarative(self, toks):
        c = Clause()
        toks = self.extract_adverbs(toks, c)
        if toks and toks[0].w == "there" and len(toks) > 1 and toks[1].w in set(BE) | {"will"}:
            c.existential = True
            self.parse_vp(toks, 1, c)
            if c.copula and c.pred and c.pred[0] == "np":
                c.subjects = [c.pred[1]]
                c.pred = None
            # 'there are dogs and cats'
            return c
        subj, i = self.parse_np_list(toks, 0)
        if not subj:
            raise ParseError("no subject found")
        c.subjects = subj
        self.parse_vp(toks, i, c)
        if not (c.verb or c.verb_text or c.copula):
            raise ParseError("no verb found")
        return c

    def parse_imperative(self, toks):
        c = Clause()
        toks = self.extract_adverbs(toks, c)
        self.parse_vp(toks, 0, c)
        if not (c.verb or c.verb_text or c.copula):
            raise ParseError("no verb found")
        c.tense = None
        return c

    def starts_with_verb(self, toks):
        if not toks:
            return False
        t = toks[0]
        if t.w in ("do", "be"):
            return True
        forms = self.L(t, ("v", "rv"))
        return any(k == "base" for _, k in forms)

    def parse_sentence(self, toks, punct):
        """Returns (subtype_info, clause) where subtype_info = (statement, subtype, evidence)."""
        evidence, statement, subtype = 0, True, 0
        while toks and (toks[0].w in EVIDENTIAL or toks[0].w in UNCERTAIN or toks[0].w == ","):
            if toks[0].w in EVIDENTIAL:
                evidence = EVIDENTIAL[toks[0].w]
            elif toks[0].w in UNCERTAIN:
                subtype = 6
            toks = toks[1:]
        if len(toks) > 3 and [t.w for t in toks[:3]] == ["in", "my", "opinion"]:
            evidence = 6
            toks = [t for t in toks[3:] if t.w != ","] if toks[3].w == "," else toks[3:]
        if not toks:
            raise ParseError("empty sentence")
        first = toks[0].w
        if punct == "?":
            return self.parse_question(toks, evidence)
        if toks[0].w == "please":
            toks = [t for t in toks[1:] if t.w != ","]
            c = self.parse_imperative(toks)
            return (True, 4, evidence), c
        if self.starts_with_verb(toks):
            try:
                c = self.parse_declarative(toks)
                return (True, 6 if subtype == 6 else 0, evidence), c
            except ParseError:
                c = self.parse_imperative(toks)
                return (True, 4, evidence), c
        c = self.parse_declarative(toks)
        if punct == "!" and subtype == 0:
            subtype = 5
        return (True, subtype, evidence), c

    def parse_question(self, toks, evidence):
        w = toks[0].w
        c = Clause()
        if w in WH:
            rest = toks[1:]
            if w == "which":
                subj, i = self.parse_np_list(rest, 0)
                if not subj:
                    raise ParseError("'which' must be followed by a noun")
                c.subjects = subj
                self.parse_vp(rest, i, c)
                return (False, 7, evidence), c
            if rest and rest[0].w in AUX:
                aux = rest[0].w
                subj, i = self.parse_np_list(rest, 1)
                if not subj:
                    raise ParseError("question has no subject")
                c.subjects = subj
                self.parse_vp(rest, i, c, preset=aux)
                if w in ("what", "who", "whom"):
                    if c.copula and c.pred is None:
                        return (False, 2, evidence), c         # What is X?
                    return (False, 1, evidence), c             # What does X eat?
                return (False, WH[w], evidence), c
            # wh + verb: subject question
            self.parse_vp(rest, 0, c)
            return (False, 0, evidence), c
        if w in AUX:
            subj, i = self.parse_np_list(toks, 1)
            if not subj:
                raise ParseError("question has no subject")
            c.subjects = subj
            self.parse_vp(toks, i, c, preset=w)
            return (False, 2, evidence), c
        c = self.parse_declarative(toks)
        return (False, 2, evidence), c


# ------------------------------------------------------------------ emitting Cant
class Builder:
    def __init__(self, parser):
        self.p = parser
        self.items = []
        self.counted = 0

    def add(self, item):
        self.items.append(item)
        if isinstance(item, Operation):
            return None
        self.counted += 1
        return self.counted - 1

    def cast(self, role, g):
        g = Grammar(**{**g.__dict__, "role": 0})
        self.add(Operation(OPS["TO_" + F.ROLES[role].upper()], g.pack_high() >> 32))

    @staticmethod
    def number_ext(v):
        t = EXT["float64"] if isinstance(v, float) else EXT["int"]   # decimals: exact binary64
        return External(t.code, *t.encode([repr(v) if isinstance(v, float) else str(v)]))

    def np(self, np, role, **extra):
        g = Grammar(role=role, **extra)
        if np.kind == "number":
            idx = self.add(self.number_ext(np.number))
            self.cast(role, g)
            return idx
        if np.number is not None:
            if np.kind == "text":
                g.plural = 2
            else:
                self.add(self.number_ext(np.number))
                g.plural = 3
        elif np.kind in ("pron", "dem"):
            g.plural = 2 if np.plural else 1
            g.det = 1
        elif np.plural:
            g.plural = 2
        elif np.det or np.demo or np.possessor or np.quant is not None:
            g.plural = 1
        if np.det == "the" or np.demo or np.possessor:
            g.det = 1
        if np.kind == "text":
            payload, conts = EXT["text"].encode(['"' + np.text.replace('"', '\\"') + '"'])
            head = self.add(External(EXT["text"].code, payload, conts))
            self.cast(role, g)
        else:
            head = self.add(Lexical(g, np.root, np.cat))
        for m in np.mods:
            if m[0] == "adj":
                self.add(Lexical(Grammar(role=M, degree=m[3]), m[1], m[2]))
            else:
                self.add(External(EXT["rgb"].code, *EXT["rgb"].encode([m[1]])))
                self.cast(M, Grammar())
        if np.quant is not None:
            self.add(Lexical(Grammar(role=M, degree=np.quant), self.p.amount, 0))
        if np.possessor is not None:
            self.np(np.possessor, R)
        if np.demo is not None:
            link = self.counted - head
            self.add(Lexical(Grammar(role=role, det=1, plural=2 if np.plural else 1, link=link),
                             np.demo.root, np.demo.cat))
        return head

    def negate_after(self):
        self.add(Lexical(Grammar(role=M), self.p.null_root, 2))

    def clause(self, c, query_missing_verb=False):
        tense = c.tense or 0
        prog = INPROG if c.prog else (COMPLETE if c.perf else 0)
        no_pred = not (c.verb or c.verb_text or (c.copula and c.pred) or c.existential)
        if c.verb is not None and c.verb.root == self.p.null_root and len(c.subjects) == 1 \
                and c.subjects[0].kind == "lex" and c.subjects[0].entry.key == "nothing":
            c.subjects = []      # 'Nothing happens' is the doc's single word null.act<V>
        for k, s in enumerate(c.subjects):
            extra = {"temporal": tense} if no_pred and k == 0 and tense and c.tense != PRESENT else {}
            self.np(s, S, **extra)
        vg = dict(temporal=tense, progress=prog)

        def verb_word(root, cat, role, flags=None, neg=c.neg, link=0):
            g = Grammar(role=role, **vg)
            for kk, vv in (flags or {}).items():
                setattr(g, kk, vv)
            later_neg = False
            if neg:
                if g.degree == 0:
                    g.degree = DEG_NONE
                else:
                    later_neg = True
            g.link = link
            self.add(Lexical(g, root, cat))
            if later_neg:
                self.negate_after()

        def adverbs():
            for root, cat, g in c.adverbs:
                self.add(Lexical(Grammar(role=M, **g), root, cat))

        if c.existential:
            verb_word(self.p.existence, 2, V)
            adverbs()
        elif c.verb is not None and c.verb.pos == "v":
            verb_word(c.verb.root, c.verb.cat, V, c.verb.flags)
            adverbs()
            objs = c.objects
            if len(objs) == 2 and not getattr(c, "coordinated", False):
                c.pps.insert(0, (self.p.en.lookup("to", ("p",))[0][0], objs[0]))
                objs = objs[1:]
            for o in objs:
                self.np(o, O)
        elif c.verb is not None and c.verb.pos == "rv":
            for o in c.objects:
                self.np(o, O)
            verb_word(c.verb.root, c.verb.cat, R, c.verb.flags)
            adverbs()
        elif c.verb_text is not None:
            payload, conts = EXT["text"].encode(['"' + c.verb_text + '"'])
            self.add(External(EXT["text"].code, payload, conts))
            g = Grammar(**vg)
            if c.neg:
                g.degree = DEG_NONE
            self.cast(V, g)
            adverbs()
            for o in c.objects:
                self.np(o, O)
        elif c.copula and c.pred is not None:
            kind = c.pred[0]
            if kind == "adj":
                verb_word(c.pred[1], c.pred[2], V, {"degree": c.pred[3]})
            elif kind == "rgb":
                self.add(External(EXT["rgb"].code, *EXT["rgb"].encode([c.pred[1]])))
                g = Grammar(**vg)
                self.cast(V, g)
                if c.neg:
                    self.negate_after()
            elif kind == "place":
                e = c.pred[1]
                verb_word(e.root, e.cat, V)
            elif kind == "np":
                np = c.pred[1]
                g = dict(vg)
                if c.neg:
                    g["degree"] = DEG_NONE
                self.np(np, V, **g)
            elif kind == "pp":
                idx = self.np(c.pred[2], O)
                verb_word(c.pred[1].root, c.pred[1].cat, R, link=self.counted - idx)
            elif kind == "cmp":
                if c.pred[2] is not None:
                    self.np(c.pred[2], O)
                verb_word(c.pred[1][0], c.pred[1][1], R)
            adverbs()
        else:
            adverbs()
            for o in c.objects:
                self.np(o, O)
        for prep, np in c.pps:
            if prep is None:      # bare place word after the verb ('go home', 'eat here')
                self.add(Lexical(Grammar(role=O), np.root, np.cat))
                continue
            idx = self.np(np, O)
            self.add(Lexical(Grammar(role=R, link=self.counted - idx), prep.root, prep.cat))


# ------------------------------------------------------------------ public API
AFFECT_WORDS = {"dishonestly": 1, "happily": 2, "sadly": 3, "fearfully": 4, "angrily": 5, "eagerly": 6,
                "in surprise": 7, "kindly": 8, "maliciously": 9, "in pain": 10, "with pleasure": 11}


def en2cant(text, en=None):
    """English text -> (Conversation, warnings)."""
    p = Parser(en)
    conv = Conversation()
    for sent in split_sentences(text):
        affection = 0
        m = re.search(r"\s*\(([a-z ]+)\)\s*([.?!]?)\s*$", sent)
        if m and m.group(1) in AFFECT_WORDS:
            affection = AFFECT_WORDS[m.group(1)]
            sent = sent[:m.start()] + m.group(2)
        toks, punct = tokenize(sent)
        try:
            if toks and toks[0].w == "if" and any(t.w == "," for t in toks):
                ci = [k for k, t in enumerate(toks) if t.w == ","][0]
                cond_toks, res_toks = toks[1:ci], toks[ci + 1:]
                if res_toks and res_toks[0].w == "then":
                    res_toks = res_toks[1:]
                (_, _, ev1), c1 = p.parse_sentence(cond_toks, ".")
                (_, _, ev2), c2 = p.parse_sentence(res_toks, ".")
                for st, cl, ev in ((2, c1, ev1), (3, c2, ev2)):
                    b = Builder(p)
                    b.clause(cl)
                    conv.items.append(Sentence(True, st, 0, ev, b.items))
                conv.items.append(Operation(OPS["IF"]))
                continue
            (statement, subtype, ev), clause = p.parse_sentence(toks, punct)
            b = Builder(p)
            b.clause(clause)
            conv.items.append(Sentence(statement, subtype, affection, ev, b.items))
        except ParseError as e:
            p.warn(f"could not parse \"{sent}\" ({e}); kept the whole sentence as text")
            raw = sent.strip().rstrip(".?!").strip()
            payload, conts = EXT["text"].encode(['"' + raw.replace('"', '\\"') + '"'])
            items = [External(EXT["text"].code, payload, conts),
                     Operation(OPS["TO_TOPIC"], 0)]
            conv.items.append(Sentence(True, 0, 0, 0, items))
    return conv, p.warnings
