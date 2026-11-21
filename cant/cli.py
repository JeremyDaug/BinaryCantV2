"""Command line interface: python -m cant {encode,decode,dump,explain,lexicon,distance,types,translate,serve}."""

import argparse
import re
import sys

from . import fields as F
from .codec import decode, encode, from_bytes, to_bytes
from .dump import dump, breakdown
from .externals import REGISTRY
from .gloss import format_conversation, parse
from .lexicon import Lexicon, LexiconError
from .model import CantError
from .ops import OPCODES
from .semantic import DOMAINS, hamming, split_root, tree_distance


def _read_words(args):
    if args.hex is not None:
        text = args.hex
    else:
        data = sys.stdin.buffer.read() if args.input == "-" else open(args.input, "rb").read()
        stripped = re.sub(rb"\s|0x|,|_", b"", data)
        if stripped and re.fullmatch(rb"[0-9A-Fa-f]+", stripped) and data.strip()[:1] in b"0123456789abcdefABCDEF":
            text = data.decode("ascii")
        else:
            return from_bytes(data)
    digits = re.sub(r"\s|0x|,|_", "", text)
    if len(digits) % 16:
        raise CantError(f"hex input has {len(digits)} digits; need a multiple of 16 (64-bit words)")
    try:
        return [int(digits[i:i + 16], 16) for i in range(0, len(digits), 16)]
    except ValueError:
        raise CantError("hex input contains non-hex characters") from None


def cmd_encode(a, lex):
    text = a.expr if a.expr is not None else (sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read())
    words = encode(parse(text, lex), file=not a.bare)
    if a.output:
        with open(a.output, "wb") as f:
            f.write(to_bytes(words))
        print(f"wrote {len(words)} words ({8 * len(words)} bytes) to {a.output}", file=sys.stderr)
    else:
        print("\n".join(f"{w:016X}" for w in words))


def cmd_decode(a, lex):
    conv = decode(_read_words(a), file=None)
    sys.stdout.write(format_conversation(conv, lex, comments=not a.plain))


def cmd_dump(a, lex):
    words = _read_words(a)
    conv = decode(words, file=None)
    if words and not (F.word_class(words[0]) == 1 and F.field(words[0], 56, 6) == 0):
        # bare stream: trace indices start at 1; prepend a phantom so indices line up
        words = [None] + words
    sys.stdout.write(dump(conv, words, lex))


def cmd_lexicon(a, lex):
    for e in lex:
        if a.key and e.key != a.key:
            continue
        if a.key:
            print(f"{e.key}  root=0x{e.root:08X}  domain={e.domain} ({DOMAINS.get(e.domain, '?')})  "
                  f"cluster={e.cluster}  concept={e.concept}  source={e.source}")
            for c, s in enumerate(e.senses):
                tag = " [proposed]" if s and e.is_proposed(c) else ""
                print(f"  .{F.CATEGORIES[c]}  0x{(e.root << 2) | c:08X}  {s or '(undefined)'}{tag}")
            if e.notes:
                print(f"  notes: {e.notes}")
        else:
            senses = " | ".join(s or "-" for s in e.senses)
            print(f"0x{e.root:08X}  {e.key:24s} {senses}")
    if a.key and a.key not in lex.by_key:
        raise LexiconError(f"unknown root '{a.key}'")


def _semantic_of(token, lex):
    if re.fullmatch(r"(0x)?[0-9A-Fa-f]{9,16}", token):
        w = int(token, 16)
        if w >> 62:
            raise CantError(f"{token} is not a lexical word (class bits must be 00)")
        return w & 0xFFFFFFFF, w
    if re.fullmatch(r"0x[0-9A-Fa-f]{1,8}", token):
        return int(token, 16), None
    root, cat = lex.resolve(token)
    return (root << 2) | cat, None


def cmd_distance(a, lex):
    sa, wa = _semantic_of(a.a, lex)
    sb, wb = _semantic_of(a.b, lex)
    na, nb = lex.name(sa >> 2, sa & 3), lex.name(sb >> 2, sb & 3)
    print(f"{na:28s} 0x{sa:08X}  {lex.gloss(sa >> 2, sa & 3)}")
    print(f"{nb:28s} 0x{sb:08X}  {lex.gloss(sb >> 2, sb & 3)}")
    levels = ["identical", "same root (sibling sense)", "same cluster", "same domain", "different domain"]
    print(f"semantic Hamming distance: {hamming(sa, sb)} / 32")
    print(f"tree distance: {tree_distance(sa, sb)} ({levels[tree_distance(sa, sb)]})")
    if wa is not None and wb is not None:
        print(f"full 64-bit Hamming distance: {hamming(wa, wb)} / 64")


def cmd_types(a, lex):
    print("External types (top byte):")
    for code, t in sorted(REGISTRY.items()):
        print(f"  0x{0x40 | code:02X}  {t.name:10s} {t.title}")
    print("  0x7E  (operation)")
    print("Operations (opcode):")
    for code, (name, ar, kind) in sorted(OPCODES.items()):
        print(f"  0x{code:04X}  {name:12s} arity {ar}  {kind}")


def cmd_explain(a, lex):
    for w in _read_words(a):
        print(f"{w:016X}  {breakdown(w)}")


def _load_cant(source, lex):
    """Auto-detect: an existing file (binary .cant, hex text or gloss), else inline hex, else inline gloss."""
    import os
    if os.path.isfile(source):
        with open(source, "rb") as f:
            data = f.read()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return decode(from_bytes(data), file=None)
        if "\x00" in text or (len(data) % 8 == 0 and data[:1] and data[0] >= 0x80 and not text.lstrip().startswith(("S", "Q", ";"))):
            return decode(from_bytes(data), file=None)
        source = text
    digits = re.sub(r"\s|0x|,|_", "", source)
    if digits and re.fullmatch(r"[0-9A-Fa-f]+", digits):
        if len(digits) % 16:
            raise CantError(f"hex input has {len(digits)} digits; need a multiple of 16 (64-bit words)")
        return decode([int(digits[i:i + 16], 16) for i in range(0, len(digits), 16)], file=None)
    return parse(source, lex)


def cmd_translate(a, lex):
    from .english import EnglishLexicon, cant2en, en2cant
    en = EnglishLexicon(lex)
    if a.direction == "en2cant":
        text = " ".join(a.text) if a.text else sys.stdin.read()
        conv, warnings = en2cant(text, en)
        words = encode(conv, file=True)
        if a.output:
            with open(a.output, "wb") as f:
                f.write(to_bytes(words))
            print(f"wrote {len(words)} words ({8 * len(words)} bytes) to {a.output}", file=sys.stderr)
        if a.format in ("all", "gloss"):
            sys.stdout.write(format_conversation(conv, lex))
        if a.format == "all":
            print()
        if a.format in ("all", "hex"):
            print(" ".join(f"{w:016X}" for w in words))
        if a.format == "all":
            print(f"\n-> {cant2en(conv, en)}")
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
    else:
        source = " ".join(a.text) if a.text else sys.stdin.read()
        print(cant2en(_load_cant(source, lex), en))


def cmd_serve(a, lex):
    from .web.server import serve
    serve(a.host, a.port, lex)


def main(argv=None):
    p = argparse.ArgumentParser(prog="cant", description="Binary Cant v2.2 reference codec, translator and UI")
    p.add_argument("--lexicon", help="path to lexicon.csv (default: repository lexicon.csv)")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("encode", help="gloss text -> binary (or hex)")
    e.add_argument("input", nargs="?", default="-", help="gloss file ('-' = stdin)")
    e.add_argument("-e", "--expr", help="gloss given inline")
    e.add_argument("-o", "--output", help="write big-endian binary here (default: print hex words)")
    e.add_argument("--bare", action="store_true", help="omit the conversation file header")
    e.set_defaults(fn=cmd_encode)

    for name, fn, hlp in (("decode", cmd_decode, "binary/hex -> annotated gloss"),
                          ("dump", cmd_dump, "annotated hex listing with per-field breakdown"),
                          ("explain", cmd_explain, "context-free field breakdown of each word")):
        d = sub.add_parser(name, help=hlp)
        d.add_argument("input", nargs="?", default="-", help="binary or hex text file ('-' = stdin)")
        d.add_argument("-x", "--hex", help="hex words given inline")
        if name == "decode":
            d.add_argument("--plain", action="store_true", help="no annotation comments")
        d.set_defaults(fn=fn)

    l = sub.add_parser("lexicon", help="list lexicon roots, or one root's senses")
    l.add_argument("key", nargs="?")
    l.set_defaults(fn=cmd_lexicon)

    ds = sub.add_parser("distance", help="bit distance between two words (key.cat, 0xSEMANTIC or 64-bit hex)")
    ds.add_argument("a")
    ds.add_argument("b")
    ds.set_defaults(fn=cmd_distance)

    t = sub.add_parser("types", help="list external types and operations")
    t.set_defaults(fn=cmd_types)

    tr = sub.add_parser("translate", help="English <-> Cant (rule-based; see TRANSLATION.md)")
    tr.add_argument("direction", choices=["en2cant", "cant2en"])
    tr.add_argument("text", nargs="*", help="en2cant: English text; cant2en: hex words, gloss, or a file "
                                            "(binary .cant, hex or gloss). Default: stdin")
    tr.add_argument("-f", "--format", choices=["all", "gloss", "hex"], default="all",
                    help="en2cant output: gloss + hex + round-trip English (default), or one of them")
    tr.add_argument("-o", "--output", help="en2cant: also write the binary .cant file here")
    tr.set_defaults(fn=cmd_translate)

    sv = sub.add_parser("serve", help="start the local web UI (stdlib http.server)")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    sv.set_defaults(fn=cmd_serve)

    a = p.parse_args(argv)
    try:
        lex = Lexicon(a.lexicon)
        a.fn(a, lex)
    except (CantError, LexiconError, OSError) as ex:
        print(f"cant: error: {ex}", file=sys.stderr)
        return 1
    return 0
