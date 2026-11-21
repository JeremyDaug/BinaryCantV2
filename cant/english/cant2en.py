"""Binary Cant -> English renderer.

Works on any valid conversation, not only ones produced by en2cant.  Word order,
articles, agreement, tense and question form are chosen from the grammar flags.
Senses with no English entry fall back to the lexicon's sense gloss in [brackets].
"""

import re

from .. import fields as F
from ..externals import NUMERIC_CODES
from ..model import Conversation, External, Grammar, Lexical, Operation, Sentence
from ..ops import OPCODES
from . import morph
from .colours import nearest
from .enlex import EnglishLexicon

S, O, T, V, M, R, FU = range(7)
REL = 1
DEGREE_ADVERB = {1: "not", 2: "barely", 3: "slightly", 4: "moderately", 5: "", 6: "very", 7: "completely"}
EVIDENCE_PREFIX = {1: "Reportedly, ", 2: "Presumably, ", 3: "Therefore, ", 4: "Generally, ",
                   5: "Hypothetically, ", 6: "In my opinion, "}
AFFECT_SUFFIX = {1: "dishonestly", 2: "happily", 3: "sadly", 4: "fearfully", 5: "angrily", 6: "eagerly",
                 7: "in surprise", 8: "kindly", 9: "maliciously", 10: "in pain", 11: "with pleasure"}
RECUR_ADVERB = {1: "sometimes", 2: "continually", 3: "usually"}
WH_WORD = {0: "who", 1: "what", 2: "what", 3: "when", 4: "where", 5: "why", 6: "how", 7: "which"}
ARITH_SYM = {"ADD": "plus", "SUB": "minus", "MUL": "times", "DIV": "divided by", "POW": "to the power of"}


class Unit:
    def __init__(self, kind, role=None, g=None, idx=None, **kw):
        self.kind, self.role, self.g, self.idx = kind, role, g or Grammar(), idx
        self.root = self.cat = None
        self.ext = self.sent = self.text = None
        self.mods, self.appos, self.possessor, self.number = [], [], None, None
        self.attached = False
        self.__dict__.update(kw)

    def __repr__(self):
        return f"U({self.kind},{self.role},{self.root},{self.cat})"


class Renderer:
    def __init__(self, en=None):
        self.en = en or EnglishLexicon()
        self.lex = self.en.lex
        k = self.lex.by_key
        self.null, self.existence, self.amount = k["null"].root, k["existence"].root, k["amount"].root

    # ------------------------------------------------------------ units
    def units(self, items):
        stack, counted = [], 0
        for it in items:
            if isinstance(it, Lexical):
                u = Unit("lex", it.grammar.role, it.grammar, counted, root=it.root, cat=it.cat)
                if it.grammar.plural == 3 and stack and stack[-1].kind == "num" and stack[-1].role is None:
                    u.number = stack.pop()
                stack.append(u)
                counted += 1
            elif isinstance(it, External):
                kind = "num" if it.code in NUMERIC_CODES else "ext"
                u = Unit(kind, None, None, counted, ext=it)
                if kind == "num":
                    u.text = self.ext_text(it)
                    u.value = it.type.value(it.payload, it.conts)
                stack.append(u)
                counted += 1
            elif isinstance(it, Sentence):
                stack.append(Unit("clause", None, None, counted, sent=it))
                counted += 1
            elif isinstance(it, Operation):
                name, arity, kind = OPCODES[it.opcode]
                if len(stack) < arity:
                    continue
                args = stack[-arity:]
                del stack[-arity:]
                if kind == "cast":
                    u = args[0]
                    g = it.cast_grammar()
                    g.role = it.opcode & 7
                    u.role, u.g = g.role, g
                    u.link_base = counted        # links on casts count from the operation
                    stack.append(u)
                elif kind == "arith":
                    if name in ARITH_SYM:
                        txt = f"{args[0].text} {ARITH_SYM[name]} {args[1].text}"
                    elif name == "LOG":
                        txt = f"the base-{args[1].text} logarithm of {args[0].text}"
                    else:
                        txt = f"the {'natural' if name == 'LN' else 'binary'} logarithm of {args[0].text}"
                    stack.append(Unit("num", None, None, args[0].idx, text=txt, value=None))
                else:
                    stack.append(Unit("logic", None, None, args[0].idx, text=name, args=args))
        return stack

    def link_target(self, u, by_idx):
        if not u.g.link:
            return None
        base = getattr(u, "link_base", u.idx)
        return by_idx.get(base - u.g.link)

    def is_genitive(self, u):
        return u.role == R and not (u.kind == "lex" and u.cat == REL)

    def attach(self, units):
        by_idx = {u.idx: u for u in units}
        for u in units:
            if u.number is not None:
                by_idx.setdefault(u.number.idx, u.number)
        head = None
        for u in units:
            if u.role in (M, FU) or self.is_genitive(u):
                tgt = self.link_target(u, by_idx) or head
                if tgt is not None:
                    u.attached = True
                    if self.is_genitive(u):
                        tgt.possessor = u
                        head = u      # later modifiers/genitives describe the possessor: my old friend's house
                    else:
                        tgt.mods.append(u)
                continue
            if u.role in (S, O, T) and u.g.link:
                tgt = self.link_target(u, by_idx)
                if tgt is not None:
                    tgt.appos.append(u)
                    u.attached = True
                    continue
            head = u
        return by_idx

    # ------------------------------------------------------------ words
    def ext_text(self, e):
        t = e.type
        if t.name == "rgb":
            return nearest(t.args(e.payload, e.conts))[0]
        if t.name in ("text", "uri"):
            return t.args(e.payload, e.conts)[1:-1]
        if t.name == "id":
            return f"entity-{e.payload}"
        if t.name == "int":
            v = t.value(e.payload, e.conts)
            return morph.number_words(v) if 0 <= v < 100 else str(v)
        if t.numeric:
            return t.args(e.payload, e.conts)
        if t.name == "ptr":
            return f"the statement at word {e.payload}"
        return f"{t.name}({t.args(e.payload, e.conts)})"

    def sense_fallback(self, root, cat):
        e = self.lex.by_root.get(root)
        if e and e.sense(cat):
            return "[" + re.sub(r"\s*\(.*?\)", "", e.sense(cat)) + "]"
        return "[" + self.lex.name(root, cat) + "]"

    def is_pronoun(self, u):
        return u.kind == "lex" and self.en.render_entry(u.root, u.cat, None, ("pron",)) is not None

    def pron_form(self, u, case):
        e = self.en.render_entry(u.root, u.cat, None, ("pron",))
        pl = u.g.plural == 2
        key = {"subj": "pl" if pl else None, "obj": "plobj" if pl else "obj",
               "poss": "plposs" if pl else "poss"}[case]
        w = e.forms.get(key, e.english) if key else e.english
        return "I" if w == "i" else w

    def agreement(self, units):
        if len(units) != 1:
            return "pl"
        u = units[0]
        if u.kind == "lex":
            e = self.en.render_entry(u.root, u.cat, None, ("pron",))
            if e is not None:
                if e.english == "i":
                    return "pl" if u.g.plural == 2 else "1sg"
                if e.english in ("you", "they"):
                    return "pl"
            if u.g.plural == 2 or (u.g.plural == 3 and u.number is not None and getattr(u.number, "value", None) != 1):
                return "pl"
        return "3sg"

    def modifier_words(self, u):
        """Adjectives/colours placed before a noun, plus negation flag."""
        pre, neg = [], False
        for m in u.mods:
            if m.kind == "lex" and m.root == self.null and m.cat == 2:
                neg = True
                continue
            if m.kind == "lex" and m.root == self.amount:
                continue
            w = self.adjective(m)
            if w:
                pre.append(w)
        return pre, neg

    def adjective(self, m, adverb=False):
        if m.kind == "ext" and m.ext.type.name == "rgb":
            return self.ext_text(m.ext)
        if m.kind != "lex":
            return self.np(m, "obj")
        pos = ("adv", "a") if adverb else ("a",)
        e = (self.en.render_entry(m.root, m.cat, m.g, ("adv",)) if adverb else None) \
            or self.en.render_entry(m.root, m.cat, m.g, ("a",))
        if e is not None and "degree" in e.flags:
            return e.english
        w = self.scalar_word(m.root, m.cat, m.g.degree, ("adv",) if adverb else ("a",))
        if w is None and adverb:
            w = self.scalar_word(m.root, m.cat, m.g.degree, ("a",))
        if w is not None:
            return w
        noun = self.en.render_entry(m.root, m.cat, None, ("n", "pl"))
        if noun is not None:
            return noun.english + "-like"
        v = self.en.render_entry(m.root, m.cat, None, ("v",))
        if v is not None:
            return v.verb_forms()["ing"]
        return self.sense_fallback(m.root, m.cat)

    def scalar_word(self, root, cat, degree, pos):
        """Scalar adjective for any degree: exact entry, else nearest pole + intensifier."""
        ents = self.en.scalar_entries(root, cat, pos)
        if not ents:
            return None
        by = {x.flags["degree"]: x.english for x in ents}
        if degree in by:
            return by[degree]
        big, small = by.get(5), by.get(3)
        if degree == 2 and small:
            return "very " + small
        if degree == 6 and big:
            return "very " + big
        if degree == 7 and big:
            return "extremely " + big
        if degree == 1 and big:
            return "not " + big
        pole = big or small or ents[0].english
        adv = DEGREE_ADVERB.get(degree, "")
        return (adv + " " if adv else "") + pole

    def determiner(self, u, word, question_which=False):
        """Composes head determiner (which / possessor / demonstrative), quantity and number:
        'my two dogs', 'these three cats', 'all my friends', 'which two dogs'."""
        head = None
        if question_which:
            head = "which"
        elif u.possessor is not None:
            p = u.possessor
            if self.is_pronoun(p):
                head = self.pron_form(p, "poss")
            else:
                owner = self.np(p, "obj")
                head = owner + ("'" if owner.endswith("s") and p.g.plural in (2, 3) else "'s")
        else:
            for a in u.appos:
                if a.kind == "lex":
                    e = self.en.render_entry(a.root, a.cat, None, ("dem",))
                    if e is not None:
                        head = e.forms.get("pl", e.english) if u.g.plural == 2 or u.number is not None else e.english
                        break
        quant = None
        for m in u.mods:
            if m.kind == "lex" and m.root == self.amount:
                e = self.en.render_entry(m.root, m.cat, m.g, ("q",))
                if e is not None:
                    quant = e.english
                    break
        num = u.number.text if u.number is not None else None
        if head is not None:
            return " ".join(x for x in ["all" if quant == "all" else None, head, num] if x)
        if quant is not None:
            return quant
        if num is not None:
            return num
        if u.g.det:
            return "the"
        if u.g.plural == 1:
            return morph.article(word)
        return ""

    def np(self, u, case="subj", which=False):
        if u.kind == "num":
            return u.text
        if u.kind == "ext":
            base = self.ext_text(u.ext)
            if u.ext.type.name == "text" and u.g.plural == 1 and not base[:1].isupper():
                base = morph.article(base) + " " + base
            return base
        if u.kind == "clause":
            return "that " + self.sentence_text(u.sent, embedded=True)
        if u.kind == "logic":
            return u.text
        # lexical
        if self.is_pronoun(u):
            return self.pron_form(u, case)
        dem = self.en.render_entry(u.root, u.cat, None, ("dem",))
        if dem is not None and not u.mods:
            return dem.forms.get("pl", dem.english) if u.g.plural == 2 else dem.english
        e = self.en.render_entry(u.root, u.cat, u.g, ("n", "rn", "pl"))
        pre, _ = self.modifier_words(u)
        emph = "*" if u.g.emph else ""
        if e is None:
            word = self.sense_fallback(u.root, u.cat)
            place = False
        else:
            many = u.g.plural == 2 or (u.g.plural == 3 and getattr(u.number, "value", 2) != 1)
            word = e.noun_forms()["pl"] if (many and e.pos != "pl") else e.english
            place = e.pos == "pl"
        if place and not pre and u.possessor is None:
            return emph + word + emph
        det = self.determiner(u, (pre[0] if pre else word), which)
        if det in ("a", "an") and pre:
            det = morph.article(pre[0])
        return " ".join(x for x in [det] + pre + [emph + word + emph] if x)

    def join(self, parts):
        parts = [p for p in parts if p]
        if len(parts) <= 1:
            return "".join(parts)
        return ", ".join(parts[:-1]) + " and " + parts[-1]

    # ------------------------------------------------------------ verbs
    def predicate(self, u):
        """-> ('verb', EnEntry|text, extra_adverb) or ('be', complement)."""
        g = u.g
        if u.kind == "ext":
            name = u.ext.type.name
            if name == "text":
                if g.plural:
                    return ("be", self.np(u))
                return ("verb", self.ext_text(u.ext), "")
            return ("be", self.ext_text(u.ext))
        if u.kind == "num":
            return ("be", u.text)
        if u.kind == "clause":
            return ("be", "that " + self.sentence_text(u.sent, embedded=True))
        if u.cat == 2:   # action
            e = self.en.render_entry(u.root, u.cat, g, ("v",))
            if e is None:
                return ("verb", self.sense_fallback(u.root, u.cat), "")
            extra = ""
            if g.degree not in (0, 1) and "degree" not in e.flags:
                extra = DEGREE_ADVERB[g.degree]
            return ("verb", e, extra)
        if u.cat == 3:   # location: be at
            e = self.en.render_entry(u.root, u.cat, None, ("pl", "n"))
            place = e.english if (e and e.pos == "pl") else "at " + (self.np_from_sense(u, 0) or self.sense_fallback(u.root, u.cat))
            if g.progress in (1, 2):
                return ("go", place)
            if g.progress == 3:
                return ("arrive", place)
            return ("be", place)
        if u.cat == 1:   # relation as verb: acts like a
            return ("verb", "act as " + self.rel_noun(u), "")
        # object as verb: to be (adjective or noun)
        scal = [x for x in self.en.scalar_entries(u.root, u.cat, ("a",))]
        if scal:
            fake = Unit("lex", M, Grammar(role=M, degree=g.degree if g.degree != 1 else 5), root=u.root, cat=u.cat)
            return ("be", self.adjective(fake))
        g2 = Grammar(**{**g.__dict__})
        g2.degree = 0
        if g2.plural == 0 and not g2.det:
            g2.plural = 1
        v = Unit("lex", O, g2, root=u.root, cat=u.cat)
        v.mods, v.possessor, v.appos = u.mods, u.possessor, u.appos
        return ("be", self.np(v, "obj"))

    def np_from_sense(self, u, cat):
        e = self.en.render_entry(u.root, cat, None, ("n",))
        return ("the " + e.english) if e else None

    def rel_noun(self, u):
        e = self.en.render_entry(u.root, u.cat, None, ("rn", "n"))
        return morph.article(e.english) + " " + e.english if e else self.sense_fallback(u.root, u.cat)

    def is_negated(self, u):
        return u.g.degree == 1 or any(m.kind == "lex" and m.root == self.null and m.cat == 2 for m in u.mods)

    def conjugate(self, kind, lemma, g, agr, neg, question=False, imperative=False):
        """Returns list of words; if question, first word is the inverted auxiliary (or do-support)."""
        tense = g.temporal if g.temporal else 2
        prog = g.progress
        if imperative:
            if kind == "be":
                return ["do", "not", "be"] if neg else ["be"]
            base = lemma if isinstance(lemma, str) else lemma.english
            return ["do", "not", base] if neg else [base]
        be_now = {"1sg": "am", "3sg": "is", "pl": "are"}[agr]
        be_past = "was" if agr in ("1sg", "3sg") else "were"
        have_now = "has" if agr == "3sg" else "have"
        if kind == "go":
            kind, lemma = "verb", self.en.lookup("go", ("v",))[0][0]
            prog = 2 if prog in (1, 2) else prog
        elif kind == "arrive":
            kind, lemma, prog = "verb", self.en.lookup("arrive", ("v",))[0][0], 3
        if kind == "be":
            if prog == 3:
                aux = ["will", "have", "been"] if tense == 3 else [have_now if tense == 2 else "had", "been"]
            elif tense == 3:
                aux = ["will", "be"]
            else:
                aux = [be_now if tense == 2 else be_past]
            if neg:
                aux.insert(1, "not")
            return aux
        if isinstance(lemma, str):        # raw text verb
            forms = {"base": lemma, "3sg": lemma, "past": lemma, "pp": lemma, "ing": lemma}
        else:
            forms = lemma.verb_forms()
        if prog == 2:
            aux = (["will", "be"] if tense == 3 else [be_now if tense == 2 else be_past]) + [forms["ing"]]
        elif prog == 3:
            aux = (["will", "have"] if tense == 3 else [have_now if tense == 2 else "had"]) + [forms["pp"]]
        elif prog == 1:
            aux = (["will", "be"] if tense == 3 else [be_now if tense == 2 else be_past]) + ["about", "to", forms["base"]]
        elif tense == 3:
            aux = ["will", forms["base"]]
        else:
            if neg or question:
                do = "did" if tense == 1 else ("does" if agr == "3sg" else "do")
                aux = [do, forms["base"]]
            else:
                aux = [forms["past"] if tense == 1 else (forms["3sg"] if agr == "3sg" else forms["base"])]
        if neg:
            aux.insert(1, "not")
        if g.recur in RECUR_ADVERB:
            aux.insert(len(aux) - 1 if len(aux) > 1 else 0, RECUR_ADVERB[g.recur])
        return aux

    # ------------------------------------------------------------ clauses
    def sentence_text(self, sent, embedded=False):
        units = self.units(sent.items)
        by_idx = self.attach(units)
        free = [u for u in units if not u.attached]
        subjects = [u for u in free if u.role == S]
        objects = [u for u in free if u.role == O]
        topics = [u for u in free if u.role == T]
        verbs = [u for u in free if u.role == V]
        rels = [u for u in free if u.role == R]
        loose = [u for u in free if u.role is None and u.kind in ("clause", "ext", "num")]
        linked = [r for r in rels if r.g.link]
        unlinked = [r for r in rels if not r.g.link]
        pps, used = [], set()
        for r in linked:
            tgt = self.link_target(r, by_idx)
            if tgt is not None:
                used.add(id(tgt))
                pps.append((r, tgt))
        objects = [o for o in objects if id(o) not in used]

        query = not sent.statement
        qtype = sent.subtype if query else None
        imperative = sent.statement and sent.subtype == 4
        clauses = []

        def subj_text(us, which=False):
            return self.join([self.np(u, "subj", which and k == 0) for k, u in enumerate(us)])

        def obj_text(us):
            return self.join([self.np(u, "obj") for u in us])

        def adverbs_of(v):
            manner, when = self._adverbs(v)
            return manner + when

        def adverbs_of_old(v):
            out = []
            for m in v.mods:
                if m.kind == "lex" and m.root == self.null and m.cat == 2:
                    continue
                e = self.en.render_entry(m.root, m.cat, m.g, ("tadv",))
                if e is not None:
                    out.append(e.english)
                    continue
                out.append(self.adjective(m, adverb=True))
            return out

        def pp_text(prs):
            out = []
            for r, tgt in prs:
                e = self.en.render_entry(r.root, r.cat, None, ("p",))
                prep = e.english if e else self.sense_fallback(r.root, r.cat)
                out.append(prep + " " + self.np(tgt, "obj"))
            return out

        def vp(pred_unit, subj_units, objs, extra_after, wh=None):
            kind, *rest = self.predicate(pred_unit)
            lemma = rest[0]
            extra = rest[1] if len(rest) > 1 else ""
            neg = self.is_negated(pred_unit) and not (kind == "verb" and not isinstance(lemma, str)
                                                      and pred_unit.g.degree == 1 and False)
            agr = self.agreement(subj_units) if subj_units else ("3sg" if wh == "subj" else "pl")
            is_q = query and wh not in ("subj", "which")
            words = self.conjugate(kind, lemma, pred_unit.g, agr, neg, question=is_q, imperative=imperative)
            complement = []
            if kind in ("be", "go", "arrive"):
                complement.append(lemma if kind == "be" else rest[0])
            tail = [obj_text(objs)] if objs else []
            manner, when = self._adverbs(pred_unit)
            tail += ([extra] if extra else []) + manner + extra_after + when
            if pred_unit.g.emph and words:
                words[-1] = "*" + words[-1] + "*"
            return words, complement + tail

        def assemble(subj, words, tail, invert):
            if invert and words:
                return " ".join(x for x in [words[0], subj] + words[1:] + tail if x)
            return " ".join(x for x in [subj] + words + tail if x)

        topic_prefix = ""
        if topics:
            topic_prefix = "concerning " + self.join([self.np(t, "obj") for t in topics])

        main_subjects = subjects
        verb = verbs[0] if verbs else None
        extra_verbs = verbs[1:]
        actor = self.link_target(verb, by_idx) if verb is not None and verb.g.link else None
        # relations without links become their own clauses
        rel_used = set()
        for r in unlinked:      # doc rule: a relation applies to ALL preceding Subjects x Objects
            r_subj = [s for s in subjects if s.idx < r.idx] or subjects
            r_obj = [o for o in objects if o.idx < r.idx]
            clauses.append(self.relation_clause(r, r_subj, r_obj, query, imperative, qtype))
            rel_used.update(id(o) for o in r_obj)
        objects = [o for o in objects if id(o) not in rel_used]
        if verb is not None and verb.kind == "lex" and verb.root == self.existence and verb.cat == 2 and not query:
            words = self.conjugate("be", None, verb.g, self.agreement(main_subjects), self.is_negated(verb))
            clauses.append(" ".join(x for x in ["there"] + words + [subj_text(main_subjects), obj_text(objects)]
                                    + adverbs_of(verb) + pp_text(pps) if x))
            verb = None
            pps = []
        elif verb is not None:
            vsubj = [actor] if actor is not None else main_subjects
            if verb.kind == "lex" and verb.root == self.null and verb.cat == 2 and not vsubj:
                vsubj_txt = "nothing"
                vsubj = []
                agr_units = None
            else:
                vsubj_txt = subj_text(vsubj, which=qtype == 7)
            wh = None
            if query:
                if qtype == 0:
                    wh = "subj"
                elif qtype == 7:
                    wh = "which"
            if not vsubj_txt and not imperative and not query:
                vsubj_txt = "something"
            words, tail = vp(verb, vsubj if vsubj else ([] if vsubj_txt != "nothing" else []), objects,
                             pp_text(pps), wh)
            if vsubj_txt == "nothing":
                words = self.conjugate(*self.predicate(verb)[:2], verb.g, "3sg", self.is_negated(verb),
                                       question=query) if self.predicate(verb)[0] == "verb" else words
            for xv in extra_verbs:
                w2, t2 = vp(xv, vsubj, [], [], wh)
                tail += ["and"] + w2[-1:] + t2
            if query:
                q = WH_WORD[qtype]
                if qtype == 0:
                    clauses.append(assemble("who", words, tail, False))
                elif qtype == 7:
                    clauses.append(assemble(vsubj_txt, words, tail, False))
                elif qtype == 2:
                    clauses.append(assemble(vsubj_txt, words, tail, True))
                else:
                    if qtype == 1 and objects:
                        pass
                    clauses.append(q + " " + assemble(vsubj_txt, words, tail, True))
            else:
                clauses.append(assemble(vsubj_txt, words, tail, False))
            pps = []
        elif not clauses:
            # no verb, no unlinked relations
            if pps:
                g = pps[0][0].g
                words = self.conjugate("be", None, g, self.agreement(main_subjects), self.is_negated(pps[0][0]),
                                       question=query)
                s_txt = subj_text(main_subjects, qtype == 7) or "something"
                if query and qtype not in (0, 7):
                    q = (WH_WORD[qtype] + " ") if qtype != 2 else ""
                    clauses.append(q + assemble(s_txt, words, pp_text(pps), True))
                else:
                    clauses.append(assemble(s_txt, words, pp_text(pps), False))
                pps = []
            elif query and main_subjects:
                tense_src = main_subjects[0].g
                words = self.conjugate("be", None, Grammar(temporal=tense_src.temporal or 2),
                                       self.agreement(main_subjects), False, question=True)
                clauses.append(WH_WORD[qtype] + " " + " ".join([words[0], subj_text(main_subjects)] + words[1:]))
            elif query:
                clauses.append(WH_WORD[qtype])
            elif main_subjects:
                g = main_subjects[0].g
                words = self.conjugate("verb", self.en.lookup("exist", ("v",))[0][0],
                                       Grammar(temporal=g.temporal or 2), self.agreement(main_subjects), False)
                clauses.append(assemble(subj_text(main_subjects), words, [obj_text(objects)], False))
            elif objects:
                clauses.append(obj_text(objects))
        if pps:
            clauses[-1] += " " + " ".join(pp_text(pps))
        for lu in loose:
            if lu.kind == "clause":
                clauses.append("(" + self.sentence_text(lu.sent, embedded=True) + ")")
            else:
                clauses.append("(" + self.np(lu) + ")")
        body = ", and ".join(c for c in clauses if c)
        if topic_prefix:
            body = topic_prefix + (", " + body if body else "")
        if embedded:
            return body
        return body

    def _adverbs(self, v):
        manner, when = [], []
        for m in v.mods:
            if m.kind == "lex" and m.root == self.null and m.cat == 2:
                continue
            e = self.en.render_entry(m.root, m.cat, m.g, ("tadv",))
            if e is not None:
                when.append(e.english)
            else:
                manner.append(self.adjective(m, adverb=True))
        return manner, when

    def relation_clause(self, r, subj, objs, query, imperative, qtype=None):
        e = self.en.render_entry(r.root, r.cat, r.g, ("rv", "p", "rn"))
        neg = self.is_negated(r)
        if query and qtype == 0:
            subj, agr, s_txt = [], "3sg", "who"
        else:
            agr = self.agreement(subj)
            s_txt = self.join([self.np(s, "subj", qtype == 7 and k == 0) for k, s in enumerate(subj)]) \
                or ("" if imperative else "something")
        invert = query and qtype not in (0, 7)
        wh = (WH_WORD[qtype] + " ") if query and qtype not in (0, 2, 7) else ""
        o_txt = self.join([self.np(o, "obj") for o in objs])
        if e is not None and e.pos == "rv":
            words = self.conjugate("verb", e, r.g, agr, neg, question=invert, imperative=imperative)
            if invert:
                return wh + " ".join(x for x in [words[0], s_txt] + words[1:] + [o_txt] if x)
            return " ".join(x for x in [s_txt] + words + [o_txt] if x)
        if e is not None and e.pos == "p":
            comp = e.english + " " + o_txt
        elif e is not None and e.pos == "rn":
            word = e.noun_forms()["pl"] if agr == "pl" and e.english != "family" else e.english
            comp = f"the {word} of {o_txt}"
        else:
            scal = [x for x in self.en.scalar_entries(r.root, 0, ("a",)) if x.flags["degree"] == 5]
            if scal:
                c = morph.comparative(scal[0].english, scal[0].forms)
                comp = (c if c else "more " + scal[0].english) + (" than " + o_txt if o_txt else "")
            else:
                comp = self.sense_fallback(r.root, r.cat) + " " + o_txt
        words = self.conjugate("be", None, r.g, agr, neg, question=invert, imperative=imperative)
        if invert:
            return wh + " ".join(x for x in [words[0], s_txt] + words[1:] + [comp] if x)
        return " ".join(x for x in [s_txt] + words + [comp] if x)

    # ------------------------------------------------------------ sentences
    def finish(self, sent, body):
        st, sub = sent.statement, sent.subtype
        prefix = EVIDENCE_PREFIX.get(sent.evidence, "")
        if st and sub == 6:
            prefix += "perhaps "
        elif st and sub == 1:
            prefix += "retract: "
        elif st and sub == 7:
            prefix += "correction: "
        elif st and sub == 2:
            prefix += "suppose "
        elif st and sub == 3:
            prefix += "then "
        text = (prefix + body).strip()
        if not text:
            text = WH_WORD.get(sub, "") if not st else "..."
        text = text[0].upper() + text[1:] if text else text
        if sent.affection:
            text += f" ({AFFECT_SUFFIX.get(sent.affection, 'with feeling')})"
        end = "?" if not st else ("!" if sub == 5 else ".")
        return text + end

    def render_sentence(self, sent):
        return self.finish(sent, self.sentence_text(sent))

    def render(self, conv):
        lines, stack, speaker, any_speaker = [], [], None, False
        has_markers = any(isinstance(i, External) and i.code in (0x01,) for i in conv.items)
        current = "Narrator" if has_markers else None
        for it in conv.items:
            if isinstance(it, External) and it.code == 0x01:
                current = "Narrator" if it.payload == 0 else f"Speaker {it.payload}"
                continue
            if isinstance(it, External) and it.code == 0x02:
                lines.append((current, f"(to {'everyone' if it.payload == 0 else 'speaker ' + str(it.payload)})"))
                continue
            if isinstance(it, Sentence):
                stack.append((it, current))
                lines.append((current, None))
                lines[-1] = (current, it)
                continue
            if isinstance(it, Operation):
                name, arity, kind = OPCODES[it.opcode]
                if kind == "cond" and len(stack) >= arity:
                    parts = stack[-arity:]
                    del stack[-arity:]
                    for p in parts:
                        lines = [x for x in lines if x[1] is not p[0]]
                    c = self.sentence_text(parts[0][0])
                    r = self.sentence_text(parts[1][0])
                    txt = f"If {c}, then {r}"
                    if arity == 3:
                        txt += f"; otherwise, {self.sentence_text(parts[2][0])}"
                    lines.append((parts[0][1], txt + "."))
        out = []
        for who, x in lines:
            txt = self.render_sentence(x) if isinstance(x, Sentence) else x
            out.append(f"{who}: {txt}" if who else txt)
        sep = "\n" if has_markers else " "
        return sep.join(out)


def cant2en(conv, en=None):
    if isinstance(conv, Sentence):
        conv = Conversation([conv])
    return Renderer(en).render(conv)
