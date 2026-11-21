import os

from cant import Lexicon, decode, encode, format_conversation, parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = Lexicon()


def enc(text, file=False):
    return encode(parse(text, LEX), file=file)


def roundtrip(text, file=False):
    """gloss -> words -> model -> canonical gloss -> words; returns (words, canonical)."""
    w = enc(text, file)
    canon = format_conversation(decode(w, file=file), LEX)
    w2 = enc(canon, file)
    assert w == w2, (text, canon)
    return w, canon
