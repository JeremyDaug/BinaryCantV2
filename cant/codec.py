"""Binary encoder/decoder and validator for Binary Cant V2.1."""

import struct

from . import fields as F
from .externals import REGISTRY, OPERATION_CODE, CONTROL_CODES, NUMERIC_CODES, ExternalError, ext_word
from .model import CantError, Conversation, External, Grammar, Lexical, Operation, Sentence
from .ops import OPCODES, EvalError, arith


# ------------------------------------------------------------------ bytes
def to_bytes(words):
    return b"".join(struct.pack(">Q", w) for w in words)


def from_bytes(data):
    if len(data) % 8:
        raise CantError(f"input is {len(data)} bytes; a Binary Cant stream is a whole number of 64-bit words")
    return [struct.unpack(">Q", data[i:i + 8])[0] for i in range(0, len(data), 8)]


def file_header(length):
    if length >= 1 << 40:
        raise CantError("conversation longer than 2^40 words")
    return ext_word(0x00, (F.FILE_VERSION << 48) | length)


# ------------------------------------------------------------------ encode
def encode(conv, file=True):
    """Conversation -> list of 64-bit words (validated)."""
    validate(conv)
    body = []
    for item in conv.items:
        body.extend(item.pack())
    words = ([file_header(len(body))] if file else []) + body
    check_pointers(conv, words=words)
    return words


# ------------------------------------------------------------------ decode
class _Reader:
    def __init__(self, words, base):
        self.w, self.base = words, base
        self.starts = {}       # id(item) -> absolute word index
        self.trace = []        # (index, depth, item, role) for dump

    def idx(self, pos):
        return pos + self.base


def decode(words, file=None):
    """List of 64-bit words -> Conversation. `file=None` auto-detects a file header."""
    if not words:
        raise CantError("empty input")
    if file is None:
        file = F.word_class(words[0]) == F.CLASS_EXTERNAL and F.field(words[0], 56, 6) == 0x00
    pos = 0
    r = _Reader(words, 0 if file else 1)
    if file:
        h = words[0]
        if F.word_class(h) != F.CLASS_EXTERNAL or F.field(h, 56, 6) != 0:
            raise CantError("word 0 is not a conversation file header (expected top byte 0x40)")
        if F.field(h, 48, 8) != F.FILE_VERSION:
            v = F.field(h, 48, 8)
            raise CantError(f"unsupported version {v >> 4}.{v & 0xF} (this codec reads 2.1)")
        if F.field(h, 40, 8):
            raise CantError("file header reserved bits 47..40 must be zero")
        length = F.field(h, 0, 40)
        if length != len(words) - 1:
            raise CantError(f"file header says {length} words follow, but {len(words) - 1} do")
        r.trace.append((0, 0, None, "file"))
        pos = 1
    conv = Conversation()
    while pos < len(words):
        item, pos = _read_item(r, pos, len(words), 0, top=True)
        conv.items.append(item)
    conv._starts, conv._trace = r.starts, r.trace
    validate(conv)
    check_pointers(conv, words=words, starts=r.starts)
    return conv


def _read_item(r, pos, end, depth, top):
    w = r.w[pos]
    cls = F.word_class(w)
    at = f"word {r.idx(pos)} (0x{w:016X})"
    if F.is_header(w):
        stmt = bool(F.field(w, F.H_QS_SHIFT, 1))
        s = Sentence(stmt, F.field(w, F.H_SUB_SHIFT, 3), F.field(w, F.H_AFF_SHIFT, 4), F.field(w, F.H_EVI_SHIFT, 3))
        count, span = F.field(w, F.H_COUNT_SHIFT, F.H_COUNT_W), F.field(w, F.H_SPAN_SHIFT, F.H_SPAN_W)
        if F.AFFECTIONS[s.affection] is None:
            raise CantError(f"{at}: affection {s.affection} is reserved")
        if F.EVIDENTIALITY[s.evidence] is None:
            raise CantError(f"{at}: evidentiality {s.evidence} is reserved")
        if pos + 1 + span > end:
            raise CantError(f"{at}: sentence span {span} runs past the end of its "
                            f"{'conversation' if depth == 0 else 'parent sentence'}")
        r.starts[id(s)] = r.idx(pos)
        r.trace.append((r.idx(pos), depth, s, "header"))
        p, stop = pos + 1, pos + 1 + span
        while p < stop:
            item, p = _read_item(r, p, stop, depth + 1, top=False)
            s.items.append(item)
        if s.count != count:
            raise CantError(f"{at}: header word count is {count} but the sentence contains {s.count} "
                            f"counted words (operations excluded, nested sentences/externals = 1)")
        return s, stop
    if cls == F.CLASS_LEXICAL:
        try:
            g = Grammar.unpack_high(w)
        except CantError as e:
            raise CantError(f"{at}: {e}") from None
        item = Lexical(g, F.field(w, F.ROOT_SHIFT, F.ROOT_W), F.field(w, F.CAT_SHIFT, F.CAT_W))
        r.starts[id(item)] = r.idx(pos)
        r.trace.append((r.idx(pos), depth, item, "lex"))
        return item, pos + 1
    # external
    code, payload = F.field(w, F.EXT_TYPE_SHIFT, F.EXT_TYPE_W), w & F.PAYLOAD_MASK
    if code == OPERATION_CODE:
        if F.field(payload, F.OP_RES_SHIFT, F.OP_RES_W):
            raise CantError(f"{at}: operation reserved bits 39..32 must be zero")
        item = Operation(F.field(payload, F.OP_CODE_SHIFT, 16), payload & 0xFFFFFFFF)
        r.starts[id(item)] = r.idx(pos)
        r.trace.append((r.idx(pos), depth, item, "op"))
        return item, pos + 1
    t = REGISTRY.get(code)
    if t is None:
        raise CantError(f"{at}: external type 0x{0x40 | code:02X} is reserved/unknown")
    if code == 0x00:
        raise CantError(f"{at}: a file header may only appear as word 0")
    n = t.n_continuations(payload)
    if pos + 1 + n > end:
        raise CantError(f"{at}: {t.name} needs {n} continuation word(s) but its scope ends first")
    item = External(code, payload, list(r.w[pos + 1:pos + 1 + n]))
    try:
        t.check(payload, item.conts)
    except ExternalError as e:
        raise CantError(f"{at}: {e}") from None
    r.starts[id(item)] = r.idx(pos)
    r.trace.append((r.idx(pos), depth, item, "ext"))
    for k in range(n):
        r.trace.append((r.idx(pos + 1 + k), depth, item, f"cont{k}"))
    return item, pos + 1 + n


# ------------------------------------------------------------------ validate
def validate(conv):
    """Semantic validation shared by encoder and decoder."""
    _validate_scope(conv.items, top=True, path="conversation")
    # sentence-level checks
    def walk(items, path):
        for i, it in enumerate(items):
            if isinstance(it, Sentence):
                p = f"{path} > {it.type_name}#{i}"
                _validate_scope(it.items, top=False, path=p)
                walk(it.items, p)
    walk(conv.items, "conversation")


class _Tok:
    __slots__ = ("kind", "value", "item")
    def __init__(self, kind, value=None, item=None):
        self.kind, self.value, self.item = kind, value, item


def _validate_scope(items, top, path):
    stack, counted = [], 0
    for i, it in enumerate(items):
        where = f"{path}, item {i}"
        if isinstance(it, Sentence):
            if it.subtype >= 8:
                raise CantError(f"{where}: bad subtype")
            it.header()  # range checks
            stack.append(_Tok("sent", it, it))
            counted += 1
        elif isinstance(it, Lexical):
            if top:
                raise CantError(f"{where}: lexical words must be inside a sentence")
            g = it.grammar
            g.pack_high()
            if g.link > counted:
                raise CantError(f"{where}: link ^{g.link} reaches before the start of the sentence "
                                f"(only {counted} earlier word(s))")
            if g.plural == 3 and not (stack and stack[-1].kind == "num"):
                raise CantError(f"{where}: plurality 'Numbered' requires a number (or arithmetic "
                                f"result) immediately before the word")
            stack.append(_Tok("lex", None, it))
            counted += 1
        elif isinstance(it, External):
            if it.code not in REGISTRY:
                raise CantError(f"{where}: unknown external type")
            if it.code == 0x00:
                raise CantError(f"{where}: a file header may only appear as word 0")
            if it.code in CONTROL_CODES and not top:
                raise CantError(f"{where}: {it.type.name}() markers are only allowed at conversation level")
            if top and it.code not in CONTROL_CODES:
                raise CantError(f"{where}: {it.type.name}() must be inside a sentence")
            try:
                it.type.check(it.payload, it.conts)
                if len(it.conts) != it.type.n_continuations(it.payload):
                    raise ExternalError("continuation count does not match the head word")
            except ExternalError as e:
                raise CantError(f"{where}: {e}") from None
            if it.code in CONTROL_CODES:
                continue   # top-level markers are not operands and not counted
            if it.code in NUMERIC_CODES:
                stack.append(_Tok("num", it.type.value(it.payload, it.conts), it))
            else:
                stack.append(_Tok("ext", it.code, it))
            counted += 1
        elif isinstance(it, Operation):
            spec = OPCODES.get(it.opcode)
            if spec is None:
                raise CantError(f"{where}: unknown opcode 0x{it.opcode:04X}")
            name, arity, kind = spec
            if len(stack) < arity:
                raise CantError(f"{where}: {name} needs {arity} operand(s) but only {len(stack)} "
                                f"exist in this scope (RPN: operate only when everything exists)")
            args = stack[-arity:]
            del stack[-arity:]
            if kind == "cast":
                if it.operand >> 30 or (it.operand >> (F.ROLE_SHIFT - 32)) & 7:
                    raise CantError(f"{where}: cast operand class/role bits must be zero")
                try:
                    g = it.cast_grammar()
                except CantError as e:
                    raise CantError(f"{where}: {e}") from None
                if g.link > counted:
                    raise CantError(f"{where}: link ^{g.link} reaches before the start of the sentence")
                if g.plural == 3:
                    raise CantError(f"{where}: casts cannot carry plurality 'Numbered'")
                if args[0].kind == "eval":
                    raise CantError(f"{where}: cannot cast an evaluated conditional")
                stack.append(_Tok("cast", None, it))
                continue
            if it.operand:
                raise CantError(f"{where}: {name} takes no operand bits")
            if kind == "arith":
                if any(a.kind != "num" for a in args):
                    raise CantError(f"{where}: {name} operands must be numbers")
                try:
                    v = arith(name, [a.value for a in args])
                except EvalError as e:
                    raise CantError(f"{where}: {e}") from None
                stack.append(_Tok("num", v, it))
            elif kind == "logic":
                for a in args:
                    if not (a.kind == "logic" or (a.kind == "sent" and a.value.statement and a.value.subtype == 2)):
                        raise CantError(f"{where}: {name} operands must be Condition sentences or logic results")
                stack.append(_Tok("logic", None, it))
            elif kind == "cond":
                c = args[0]
                if not (c.kind == "logic" or (c.kind == "sent" and c.value.statement and c.value.subtype == 2)):
                    raise CantError(f"{where}: {name} first operand must be a Condition sentence or logic result")
                for a in args[1:]:
                    if not (a.kind == "sent" and a.value.statement and a.value.subtype == 3):
                        raise CantError(f"{where}: {name} branches must be Result sentences")
                stack.append(_Tok("eval", None, it))
        else:
            raise CantError(f"{where}: unknown item {it!r}")


def check_pointers(conv, words, starts=None):
    """ptr() must point backwards at the start of an item, header, or the file header."""
    if starts is None:
        starts, pos = {}, 1   # item indices: word 0 is (or would be) the file header
        def lay(items):
            nonlocal pos
            for it in items:
                starts[id(it)] = pos
                if isinstance(it, Sentence):
                    pos += 1
                    lay(it.items)
                else:
                    pos += it.n_words
        lay(conv.items)
    valid = set(starts.values()) | {0}
    def walk(items):
        for it in items:
            if isinstance(it, Sentence):
                walk(it.items)
            elif isinstance(it, External) and it.code == 0x30:
                me = starts[id(it)]
                if it.payload >= me:
                    raise CantError(f"word {me}: ptr({it.payload}) must point backwards "
                                    f"(you say what something is before it exists)")
                if it.payload not in valid:
                    raise CantError(f"word {me}: ptr({it.payload}) does not point at the start of an item")
    walk(conv.items)
