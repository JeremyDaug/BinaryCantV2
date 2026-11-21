"""Lexicon: maps human-readable root keys to 30-bit root IDs and sense glosses."""

import csv
import os

from .fields import CATEGORIES
from .semantic import make_root

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lexicon.csv")
SENSE_COLUMNS = ["object", "relation", "action", "location"]  # same order as CATEGORIES


class LexiconError(ValueError):
    pass


class Entry:
    __slots__ = ("root", "key", "domain", "cluster", "concept", "senses", "source", "proposed", "notes")

    def __init__(self, row):
        self.key = row["key"]
        self.root = int(row["root"], 16)
        self.domain, self.cluster, self.concept = int(row["domain"]), int(row["cluster"]), int(row["concept"])
        if make_root(self.domain, self.cluster, self.concept) != self.root:
            raise LexiconError(f"lexicon entry '{self.key}': root {row['root']} does not match "
                               f"domain/cluster/concept {self.domain}/{self.cluster}/{self.concept}")
        self.senses = [row[c] for c in SENSE_COLUMNS]
        self.source = row["source"]
        self.proposed = set(filter(None, row["proposed_senses"].split(";")))
        self.notes = row["notes"]

    def sense(self, cat):
        return self.senses[cat]

    def is_proposed(self, cat):
        return self.source == "proposed" or CATEGORIES[cat] in self.proposed


class Lexicon:
    def __init__(self, path=None):
        self.path = path or os.environ.get("CANT_LEXICON") or DEFAULT_PATH
        self.by_key, self.by_root = {}, {}
        with open(self.path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                e = Entry(row)
                if e.key in self.by_key:
                    raise LexiconError(f"duplicate lexicon key '{e.key}'")
                if e.root in self.by_root:
                    raise LexiconError(f"root 0x{e.root:08X} assigned to both "
                                       f"'{self.by_root[e.root].key}' and '{e.key}'")
                self.by_key[e.key] = e
                self.by_root[e.root] = e

    def __iter__(self):
        return iter(sorted(self.by_root.values(), key=lambda e: e.root))

    def __len__(self):
        return len(self.by_key)

    def lookup_key(self, key):
        try:
            return self.by_key[key]
        except KeyError:
            raise LexiconError(f"unknown root '{key}' (not in {os.path.basename(self.path)}; "
                               f"use a raw root like 0x1234.obj)") from None

    def resolve(self, name):
        """'key.cat' or '0xROOT.cat' -> (root, cat). Lexicon senses must be defined."""
        if "." not in name:
            raise LexiconError(f"word '{name}' needs a category suffix: .obj .rel .act or .loc")
        base, cat_name = name.rsplit(".", 1)
        if cat_name not in CATEGORIES:
            raise LexiconError(f"word '{name}': unknown category '.{cat_name}' (use .obj .rel .act .loc)")
        cat = CATEGORIES.index(cat_name)
        if base.lower().startswith("0x"):
            root = int(base, 16)
            if root >= 1 << 30:
                raise LexiconError(f"raw root {base} does not fit in 30 bits")
            return root, cat
        e = self.lookup_key(base)
        if not e.sense(cat):
            raise LexiconError(f"'{base}' has no defined {cat_name} sense in the lexicon "
                               f"(Clarity rule: no undefined meanings; use a raw root to force it)")
        return e.root, cat

    def name(self, root, cat):
        e = self.by_root.get(root)
        if e is not None:
            return f"{e.key}.{CATEGORIES[cat]}"
        return f"0x{root:08X}.{CATEGORIES[cat]}"

    def gloss(self, root, cat):
        e = self.by_root.get(root)
        if e is None:
            return "(not in lexicon)"
        s = e.sense(cat) or "(undefined sense)"
        return s + (" [proposed]" if e.sense(cat) and e.is_proposed(cat) else "")
