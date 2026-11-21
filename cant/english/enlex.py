"""English <-> root mapping table (en_lexicon.csv)."""

import csv
import os
from collections import defaultdict

from .. import fields as F
from ..lexicon import Lexicon
from . import morph

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "en_lexicon.csv")

FIELD_TABLES = {"degree": F.DEGREE, "temporal": F.TEMPORAL, "progress": F.PROGRESSION,
                "recur": F.RECURRENCE, "plural": F.PLURALITY}


class EnEntry:
    __slots__ = ("english", "pos", "key", "cat", "root", "flags", "forms", "render")

    def __init__(self, row, lex):
        self.english = row["english"]
        self.pos = row["pos"]
        self.key, cat = row["root"].rsplit(".", 1)
        self.cat = F.CATEGORIES.index(cat)
        self.root = lex.lookup_key(self.key).root
        self.flags = {}
        for kv in filter(None, row["flags"].split(";")):
            k, v = kv.split("=")
            self.flags[k] = FIELD_TABLES[k].index(v)
        self.forms = dict(kv.split("=") for kv in filter(None, row["forms"].split(";")))
        self.render = row["render"] != "no"

    def __repr__(self):
        return f"<{self.pos} {self.english} -> {self.key}.{F.CATEGORIES[self.cat]} {self.flags}>"

    # inflected forms --------------------------------------------------------
    def noun_forms(self):
        return {"sg": self.english, "pl": morph.plural(self.english, self.forms)}

    def verb_forms(self):
        w, f = self.english, self.forms
        return {"base": w, "3sg": morph.third(w, f), "past": morph.past(w, f),
                "pp": morph.participle(w, f), "ing": morph.gerund(w, f)}


class EnglishLexicon:
    def __init__(self, lex=None, path=PATH):
        self.lex = lex or Lexicon()
        self.entries = []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                self.entries.append(EnEntry(row, self.lex))
        self.forms = defaultdict(list)     # surface form -> [(entry, formtype)]
        self.by_sense = defaultdict(list)  # (root, cat) -> [entry] in file order
        for e in self.entries:
            for form, kind in self._surface(e):
                self.forms[form].append((e, kind))
            self.by_sense[(e.root, e.cat)].append(e)

    def _surface(self, e):
        if e.pos in ("n", "rn"):
            for k, v in e.noun_forms().items():
                yield v, k
        elif e.pos in ("v", "rv"):
            for k, v in e.verb_forms().items():
                yield v, k
        elif e.pos == "a":
            yield e.english, "base"
            c = morph.comparative(e.english, e.forms)
            if c:
                yield c, "cmp"
        elif e.pos == "pron":
            yield e.english, "subj"
            for k in ("obj", "poss", "pl", "plobj", "plposs"):
                if k in e.forms:
                    yield e.forms[k], k
        elif e.pos == "dem":
            yield e.english, "sg"
            if "pl" in e.forms:
                yield e.forms["pl"], "pl"
        else:
            yield e.english, "base"

    def lookup(self, word, pos=None):
        """All (entry, formtype) for a lowercase surface form, optionally restricted to POS set."""
        out = self.forms.get(word, [])
        if pos:
            out = [x for x in out if x[0].pos in pos]
        return out

    def render_entry(self, root, cat, grammar=None, pos=None):
        """Best English entry for a sense: render=yes, flags all satisfied, most specific wins."""
        best, score = None, -1
        for e in self.by_sense.get((root, cat), []):
            if not e.render or (pos and e.pos not in pos):
                continue
            ok = True
            for k, v in e.flags.items():
                if grammar is None or getattr(grammar, k) != v:
                    ok = False
            if ok and len(e.flags) > score:
                best, score = e, len(e.flags)
        return best

    def scalar_entries(self, root, cat, pos=("a", "adv")):
        return [e for e in self.by_sense.get((root, cat), []) if e.pos in pos and e.render and "degree" in e.flags]
