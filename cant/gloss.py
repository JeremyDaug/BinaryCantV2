"""Text gloss syntax <-> model.

    ; comment to end of line
    speaker(1)
    STATEMENT<Assertion,Honest,Direct>{
        null.act<V,Present>
        int(3) sophont.obj<S,Numbered>
        rgb(#FF0000) TO_VERB<Present,^3>
    }

Lexical word : root.cat<flags>          (root = lexicon key or 0xHEX; cat = obj|rel|act|loc)
External     : type(args)               (see `cant types` / SPEC.md section 6)
Operation    : NAME or NAME<flags>      (flags only on TO_* casts)
Sentence     : QUERY<sub,aff,evi>{...}  or  STATEMENT<sub,aff,evi>{...}
"""

import re

from . import fields as F
from .externals import BY_NAME as EXT_BY_NAME, ExternalError, REGISTRY, _split_args
from .lexicon import Lexicon, LexiconError
from .model import CantError, Conversation, External, Grammar, Lexical, Operation, Sentence
from .ops import BY_NAME as OP_BY_NAME, OPCODES, is_cast


class GlossError(CantError):
    pass


# ----------------------------------------------------------------- tokenizer
def tokenize(text):
    toks, i, line = [], 0, 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
        elif ch.isspace():
            i += 1
        elif ch == ";":
            while i < n and text[i] != "\n":
                i += 1
        elif ch in "{}":
            toks.append((ch, ch, line))
            i += 1
        elif ch in "<(":
            close = ">" if ch == "<" else ")"
            j, depth, q = i + 1, 1, False
            while j < n:
                c = text[j]
                if q:
                    if c == "\\":
                        j += 1
                    elif c == '"':
                        q = False
                elif c == '"':
                    q = True
                elif c == ch:
                    depth += 1
                elif c == close:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= n:
                raise GlossError(f"line {line}: unclosed '{ch}'")
            toks.append(("flags" if ch == "<" else "args", text[i + 1:j], line))
            line += text[i:j].count("\n")
            i = j + 1
        else:
            m = re.match(r"[A-Za-z0-9_.+\-]+", text[i:])
            if not m:
                raise GlossError(f"line {line}: unexpected character {ch!r}")
            toks.append(("word", m.group(0), line))
            i += m.end()
    return toks


# ----------------------------------------------------------------- flags
def _lex_flag_table():
    t = {}
    for i, (a, r) in enumerate(zip(F.ROLE_ABBR, F.ROLES)):
        if a:
            t[a] = ("role", i)
            t[r] = ("role", i)
    for name, lst in (("temporal", F.TEMPORAL), ("progress", F.PROGRESSION),
                      ("recur", F.RECURRENCE), ("degree", F.DEGREE), ("plural", F.PLURALITY)):
        for i, v in enumerate(lst):
            t[v] = (name, i)
    t.update({"!": ("emph", 1), "Emphasized": ("emph", 1), "Unemphasized": ("emph", 0),
              "Specific": ("det", 1), "Nonspecific": ("det", 0)})
    return t


LEX_FLAGS = _lex_flag_table()


def parse_grammar(text, line, allow_role=True):
    g, seen = Grammar(), set()
    for tok in (t.strip() for t in text.split(",")):
        if not tok:
            continue
        if tok.startswith("^"):
            key, val = "link", tok[1:]
            if not val.isdigit() or int(val) == 0:
                raise GlossError(f"line {line}: link '{tok}' must be ^N with N >= 1")
            val = int(val)
        elif tok in LEX_FLAGS:
            key, val = LEX_FLAGS[tok]
        else:
            raise GlossError(f"line {line}: unknown word flag '{tok}'")
        if key in seen:
            raise GlossError(f"line {line}: flag '{tok}' repeats the {key} field")
        if key == "role" and not allow_role:
            raise GlossError(f"line {line}: casts take their role from the opcode; drop '{tok}'")
        seen.add(key)
        setattr(g, key, val)
    if allow_role and "role" not in seen:
        raise GlossError(f"line {line}: every lexical word needs a grammar role (S,O,T,V,M,R,F)")
    return g


def parse_header(kind, text, line):
    statement = kind == "STATEMENT"
    subs = F.STATEMENT_SUBTYPES if statement else F.QUERY_SUBTYPES
    sub = aff = evi = None
    for tok in (t.strip() for t in text.split(",")):
        if not tok:
            continue
        tok_e = F.EVIDENTIALITY_ALIASES.get(tok, tok)
        if tok in subs:
            if sub is not None:
                raise GlossError(f"line {line}: two sentence subtypes")
            sub = subs.index(tok)
        elif tok in F.AFFECTIONS:
            if aff is not None:
                raise GlossError(f"line {line}: two affections")
            aff = F.AFFECTIONS.index(tok)
        elif tok_e in F.EVIDENTIALITY:
            if evi is not None:
                raise GlossError(f"line {line}: two evidentialities")
            evi = F.EVIDENTIALITY.index(tok_e)
        else:
            raise GlossError(f"line {line}: '{tok}' is not a {kind.lower()} subtype, affection or "
                             f"evidentiality (subtypes: {', '.join(subs)})")
    if sub is None:
        raise GlossError(f"line {line}: {kind} needs a subtype ({', '.join(subs)})")
    return Sentence(statement, sub, aff or 0, evi or 0)


# ----------------------------------------------------------------- parser
def parse(text, lexicon=None):
    lex = lexicon or Lexicon()
    toks = tokenize(text)
    pos = 0

    def peek(k=0):
        return toks[pos + k] if pos + k < len(toks) else (None, None, toks[-1][2] if toks else 1)

    def items_until(closer):
        nonlocal pos
        out = []
        while True:
            kind, val, line = peek()
            if kind is None:
                if closer:
                    raise GlossError(f"line {line}: missing '}}'")
                return out
            if kind == "}":
                if not closer:
                    raise GlossError(f"line {line}: unexpected '}}'")
                pos += 1
                return out
            out.append(item())

    def item():
        nonlocal pos
        kind, val, line = peek()
        if kind != "word":
            raise GlossError(f"line {line}: unexpected {val!r}")
        pos += 1
        nk, nv, _ = peek()
        if val in ("QUERY", "STATEMENT"):
            if nk != "flags":
                raise GlossError(f"line {line}: {val} needs <subtype,affection,evidentiality>")
            s = parse_header(val, nv, line)
            pos += 1
            if peek()[0] != "{":
                raise GlossError(f"line {line}: {val}<...> must be followed by {{ ... }} (use {{}} for a wordless sentence)")
            pos += 1
            s.items = items_until(True)
            return s
        if val in OP_BY_NAME:
            code = OP_BY_NAME[val]
            operand = 0
            if nk == "flags":
                if not is_cast(code):
                    raise GlossError(f"line {line}: only TO_* casts take flags")
                operand = parse_grammar(nv, line, allow_role=False).pack_high() >> 32
                pos += 1
            return Operation(code, operand)
        if val in EXT_BY_NAME:
            if nk != "args":
                raise GlossError(f"line {line}: external {val} needs (arguments)")
            pos += 1
            t = EXT_BY_NAME[val]
            try:
                payload, conts = t.encode(_split_args(nv))
            except ExternalError as e:
                raise GlossError(f"line {line}: {val}(): {e}") from None
            if peek()[0] == "flags":
                raise GlossError(f"line {line}: externals carry no grammar; apply a TO_* cast after it")
            return External(t.code, payload, conts)
        if "." in val:
            try:
                root, cat = lex.resolve(val)
            except LexiconError as e:
                raise GlossError(f"line {line}: {e}") from None
            if nk != "flags":
                raise GlossError(f"line {line}: word '{val}' needs <flags> with at least a role")
            pos += 1
            return Lexical(parse_grammar(nv, line), root, cat)
        if val.isupper():
            raise GlossError(f"line {line}: unknown operation or keyword '{val}'")
        raise GlossError(f"line {line}: '{val}' is not a word (root.cat), external type(...) or operation")

    return Conversation(items_until(False))


# ----------------------------------------------------------------- formatter
def grammar_flags(g, with_role=True):
    out = [F.ROLE_ABBR[g.role]] if with_role else []
    for name, lst in (("temporal", F.TEMPORAL), ("progress", F.PROGRESSION),
                      ("recur", F.RECURRENCE), ("degree", F.DEGREE)):
        v = getattr(g, name)
        if v:
            out.append(lst[v])
    if g.emph:
        out.append("!")
    if g.det:
        out.append("Specific")
    if g.plural:
        out.append(F.PLURALITY[g.plural])
    if g.link:
        out.append(f"^{g.link}")
    return out


def format_item(it, lex):
    if isinstance(it, Lexical):
        return f"{lex.name(it.root, it.cat)}<{','.join(grammar_flags(it.grammar))}>"
    if isinstance(it, External):
        return f"{it.type.name}({it.type.args(it.payload, it.conts)})"
    if isinstance(it, Operation):
        name = OPCODES[it.opcode][0]
        if is_cast(it.opcode) and it.operand:
            return f"{name}<{','.join(grammar_flags(it.cast_grammar(), with_role=False))}>"
        return name
    if isinstance(it, Sentence):
        subs = F.STATEMENT_SUBTYPES if it.statement else F.QUERY_SUBTYPES
        return (f"{'STATEMENT' if it.statement else 'QUERY'}<{subs[it.subtype]},"
                f"{F.AFFECTIONS[it.affection]},{F.EVIDENTIALITY[it.evidence]}>")
    raise TypeError(it)


def annotate(it, lex):
    """Short English annotation for a single item."""
    if isinstance(it, Lexical):
        g = it.grammar
        return f"{F.ROLES[g.role]}: {lex.gloss(it.root, it.cat)}"
    if isinstance(it, External):
        return it.type.describe(it.payload, it.conts)
    if isinstance(it, Operation):
        name, arity, kind = OPCODES[it.opcode]
        return f"operation {name} (pops {arity}; not counted)"
    if isinstance(it, Sentence):
        return f"{it.type_name}, {it.count} word(s), span {it.span}"
    return ""


def format_conversation(conv, lex=None, comments=False, indent="    "):
    lex = lex or Lexicon()
    lines = []

    def emit(items, depth):
        for it in items:
            pad = indent * depth
            if isinstance(it, Sentence):
                head = format_item(it, lex) + "{"
                if not it.items:
                    lines.append(pad + head + "}" + (f"  ; {annotate(it, lex)}" if comments else ""))
                    continue
                lines.append(pad + head + (f"  ; {annotate(it, lex)}" if comments else ""))
                emit(it.items, depth + 1)
                lines.append(pad + "}")
            else:
                s = pad + format_item(it, lex)
                if comments:
                    s += f"  ; {annotate(it, lex)}"
                lines.append(s)

    emit(conv.items, 0)
    return "\n".join(lines) + "\n"
