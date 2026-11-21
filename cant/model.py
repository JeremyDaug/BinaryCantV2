"""In-memory model of a Binary Cant conversation."""

from dataclasses import dataclass, field as dfield
from typing import List

from . import fields as F
from .externals import REGISTRY, ext_word, OPERATION_CODE


class CantError(ValueError):
    """Any encoding, decoding or validation error."""


@dataclass
class Grammar:
    """The 32-bit grammar/relational half (also the operand of cast ops)."""
    role: int = 0
    temporal: int = 0
    progress: int = 0
    recur: int = 0
    degree: int = 0
    emph: int = 0
    det: int = 0
    plural: int = 0
    link: int = 0          # 0 = implicit (adjacency rules); k = k-th counted item back

    def pack_high(self):
        """Return bits 63..32 of a lexical word (class bits = 00)."""
        if self.role == 7:
            raise CantError("grammar role 7 is reserved")
        if not 0 <= self.link < (1 << F.LINK_OFF_W):
            raise CantError(f"link offset {self.link} does not fit in {F.LINK_OFF_W} bits (max 1023)")
        w = (F.put(self.role, F.ROLE_SHIFT, 3) | F.put(self.temporal, F.TEMPORAL_SHIFT, 2)
             | F.put(self.progress, F.PROGRESS_SHIFT, 2) | F.put(self.recur, F.RECUR_SHIFT, 2)
             | F.put(self.degree, F.DEGREE_SHIFT, 3) | F.put(self.emph, F.EMPH_SHIFT, 1)
             | F.put(self.det, F.DET_SHIFT, 1) | F.put(self.plural, F.PLURAL_SHIFT, 2))
        if self.link:
            w |= (1 << F.LINK_FLAG_SHIFT) | (self.link << F.LINK_OFF_SHIFT)
        return w

    @classmethod
    def unpack_high(cls, w):
        if F.field(w, F.LEX_RESERVED_SHIFT, F.LEX_RESERVED_W):
            raise CantError("lexical reserved bits 34..32 must be zero")
        flag, off = F.field(w, F.LINK_FLAG_SHIFT, 1), F.field(w, F.LINK_OFF_SHIFT, F.LINK_OFF_W)
        if flag != (off != 0):
            raise CantError("link flag (bit 45) and link offset (bits 44..35) disagree")
        role = F.field(w, F.ROLE_SHIFT, 3)
        if role == 7:
            raise CantError("grammar role 7 is reserved")
        return cls(role, F.field(w, F.TEMPORAL_SHIFT, 2), F.field(w, F.PROGRESS_SHIFT, 2),
                   F.field(w, F.RECUR_SHIFT, 2), F.field(w, F.DEGREE_SHIFT, 3), F.field(w, F.EMPH_SHIFT, 1),
                   F.field(w, F.DET_SHIFT, 1), F.field(w, F.PLURAL_SHIFT, 2), off)


@dataclass
class Lexical:
    grammar: Grammar
    root: int
    cat: int

    @property
    def n_words(self):
        return 1

    def pack(self):
        if not 0 <= self.root < (1 << 30):
            raise CantError("root does not fit in 30 bits")
        return [self.grammar.pack_high() | (self.root << 2) | self.cat]


@dataclass
class External:
    code: int
    payload: int
    conts: List[int] = dfield(default_factory=list)

    @property
    def type(self):
        return REGISTRY[self.code]

    @property
    def n_words(self):
        return 1 + len(self.conts)

    def pack(self):
        return [ext_word(self.code, self.payload)] + list(self.conts)


@dataclass
class Operation:
    opcode: int
    operand: int = 0   # for casts: Grammar.pack_high() >> 32 with role bits zero

    @property
    def n_words(self):
        return 1

    def pack(self):
        return [ext_word(OPERATION_CODE, F.put(self.opcode, F.OP_CODE_SHIFT, 16) | F.put(self.operand, 0, 32))]

    def cast_grammar(self):
        return Grammar.unpack_high(self.operand << 32)


@dataclass
class Sentence:
    statement: bool
    subtype: int
    affection: int = 0
    evidence: int = 0
    items: list = dfield(default_factory=list)

    @property
    def count(self):
        return sum(1 for i in self.items if not isinstance(i, Operation))

    @property
    def span(self):
        return sum(i.n_words for i in self.items)

    @property
    def n_words(self):
        return 1 + self.span

    def header(self):
        if F.AFFECTIONS[self.affection] is None:
            raise CantError(f"affection value {self.affection} is reserved ([Empty] in the doc)")
        if F.EVIDENTIALITY[self.evidence] is None:
            raise CantError(f"evidentiality value {self.evidence} is reserved ([Empty] in the doc)")
        if self.count >= 1 << F.H_COUNT_W:
            raise CantError(f"sentence has {self.count} words; max is {(1 << F.H_COUNT_W) - 1}")
        if self.span >= 1 << F.H_SPAN_W:
            raise CantError("sentence span exceeds 32 bits")
        return ((1 << 63) | (int(self.statement) << F.H_QS_SHIFT) | (self.subtype << F.H_SUB_SHIFT)
                | (self.affection << F.H_AFF_SHIFT) | (self.evidence << F.H_EVI_SHIFT)
                | (self.count << F.H_COUNT_SHIFT) | self.span)

    def pack(self):
        out = [self.header()]
        for i in self.items:
            out.extend(i.pack())
        return out

    @property
    def type_name(self):
        return ("STATEMENT." + F.STATEMENT_SUBTYPES[self.subtype]) if self.statement \
            else ("QUERY." + F.QUERY_SUBTYPES[self.subtype])


@dataclass
class Conversation:
    items: list = dfield(default_factory=list)

    @property
    def length(self):
        return sum(i.n_words for i in self.items)
